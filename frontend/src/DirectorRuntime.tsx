import {createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {useProject} from './ProjectController';
import {agentRequest, computerGrant, exactApproval, type AgentMessage, type AgentTask} from './lib/agent-tasks';
import {discoverAgent, type AgentDiscovery} from './lib/agent-api';
import DirectorConversation from './DirectorConversation';
import {useProjectState} from './lib/project-state';
import './director-runtime.css';
import {DirectorEditor, type EditorBridge} from './DirectorEditor';

const Slot = createContext<(element: HTMLDivElement | null) => void>(() => {});
type Panes = {chat: boolean; work: boolean};
const PaneContext = createContext<{panes: Panes; togglePane: (pane: keyof Panes) => void; openPane: (pane: keyof Panes) => void} | null>(null);
export function useDirectorPanes() {
  const value = useContext(PaneContext);
  if (!value) throw new Error('Director panes require DirectorRuntime.');
  return value;
}
export function DirectorSlot({hidden = false}: {hidden?: boolean}) {
  const setSlot = useContext(Slot);
  const element = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const node = element.current;
    if (!node) return;
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const footer = document.querySelector('.studio-taskbar')?.getBoundingClientRect().height || 64;
        node.style.setProperty('--director-height', `${Math.max(240, innerHeight - Math.max(0, node.getBoundingClientRect().top) - footer)}px`);
      });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(node.parentElement!);
    window.addEventListener('resize', measure); window.addEventListener('scroll', measure);
    measure();
    return () => {observer.disconnect(); cancelAnimationFrame(frame); window.removeEventListener('resize', measure); window.removeEventListener('scroll', measure);};
  }, []);
  const register = useCallback((node: HTMLDivElement | null) => {element.current = node; setSlot(node);}, [setSlot]);
  return <div className="director-slot" hidden={hidden} ref={register}/>;
}
export default function DirectorRuntime({children}: {children: ReactNode}) {
  const {workspace_id: owner} = useProject();
  const [slot, setSlot] = useState<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]), [tasks, setTasks] = useState<AgentTask[]>([]);
  const [discovery, setDiscovery] = useState<AgentDiscovery | null>(null);
  const [text, setText] = useProjectState('DirectorRuntime:text', '');
  const [selected, setSelected] = useProjectState<string[]>('DirectorRuntime:assets', []);
  const [skills, setSkills] = useProjectState<string[]>('DirectorRuntime:skills', ['application/vibe/vibe-director']);
  const [access, setAccess] = useProjectState<'app' | 'project' | 'full'>('DirectorRuntime:access', 'app');
  const [savedPanes, setPanes] = useProjectState<Panes>('DirectorWorkspace:panes', {chat: true, work: true});
  const panes = {chat: savedPanes?.chat !== false, work: savedPanes?.work !== false};
  const togglePane = (pane: keyof Panes) => setPanes(old => ({chat: old?.chat !== false, work: old?.work !== false, [pane]: old?.[pane] === false}));
  const openPane = (pane: keyof Panes) => setPanes(old => ({chat: old?.chat !== false, work: old?.work !== false, [pane]: true}));
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const abort = useRef(new AbortController());
  const pending = useRef<{id: string; key: string} | null>(null);
  const editor = useRef<EditorBridge | null>(null);
  const refresh = useCallback(async (signal: AbortSignal) => {
    const [history, listing] = await Promise.all([
      agentRequest<{messages: AgentMessage[]}>(owner, 'conversation', signal),
      agentRequest<{tasks: AgentTask[]}>(owner, 'tasks', signal),
    ]);
    if (signal.aborted) return;
    if (!Array.isArray(history.messages) || !Array.isArray(listing.tasks)) throw new Error('Restart the backend to load the Director runtime.');
    const reconciled = await Promise.all(listing.tasks.map(task => task.invocation ?
      agentRequest<AgentTask>(owner, `tasks/${task.task_id}`, signal) : Promise.resolve(task)));
    if (!signal.aborted) {setMessages(history.messages); setTasks(reconciled);}
    if (!signal.aborted && reconciled.some(task => task.plan.tool_id === 'editor.prepare_brief')) await editor.current?.refresh();
  }, [owner]);
  useEffect(() => {
    const controller = new AbortController(); abort.current = controller;
    void refresh(controller.signal).catch(e => {if (!controller.signal.aborted) setError(e.message);});
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    if (!tasks.some(task => ['submitting', 'running', 'cancel_requested'].includes(task.status))) return;
    const timer = window.setInterval(() => void refresh(abort.current.signal).catch(e => {
      if (!abort.current.signal.aborted) setError(e.message);
    }), 2500);
    return () => window.clearInterval(timer);
  }, [tasks, refresh]);
  async function attempt(action: (signal: AbortSignal) => Promise<void>) {
    const signal = abort.current.signal;
    if (busy || signal.aborted) return;
    setBusy(true); setError('');
    try {await action(signal);} catch (e) {if (!signal.aborted) setError((e as Error).message);}
    finally {if (!signal.aborted) setBusy(false);}
  }
  const loadContext = () => attempt(async signal => {
    const value = await discoverAgent(owner, signal);
    if (!signal.aborted) setDiscovery(value);
  });
  const send = () => attempt(async signal => {
    if (access !== 'app') {
      const token = await computerGrant(signal);
      await agentRequest<AgentTask>(owner, 'tasks', signal, {tool_id: 'computer.execute', asset_ids: [],
        settings: {instruction: text, access_mode: access, skill_refs: skills}}, token);
      if (!signal.aborted) {setText(''); await refresh(signal);}
      return;
    }
    const editing = location.hash.startsWith('#/editor');
    if (editing && !editor.current) throw new Error('Wait for the Editor session to load.');
    const target = editing ? await editor.current!.prepareTarget() : undefined;
    if (signal.aborted) return;
    const payload = {text, asset_ids: selected, skill_refs: skills,
      surface: editing ? 'editor' : 'director', ...(target ? {target} : {})};
    const key = JSON.stringify(payload);
    if (!pending.current || pending.current.key !== key) pending.current = {id: crypto.randomUUID(), key};
    const result = await agentRequest<{messages: AgentMessage[]}>(owner, 'conversation', signal, {
      request_id: pending.current.id, ...payload,
    });
    if (!signal.aborted) {setMessages(result.messages); setText(''); pending.current = null; await refresh(signal);}
  });
  const control = (task: AgentTask, action: 'approve' | 'run' | 'cancel') => attempt(async signal => {
    const token = task.plan.tool_id === 'computer.execute' ? await computerGrant(signal) : undefined;
    const updated = await agentRequest<AgentTask>(owner, `tasks/${task.task_id}/${action}`, signal, action === 'cancel' ? {} : exactApproval(task), token);
    if (!signal.aborted) setTasks(rows => rows.map(row => row.task_id === updated.task_id ? updated : row));
    if (!signal.aborted && updated.plan.tool_id === 'editor.prepare_brief') await editor.current?.refresh();
  });
  return <DirectorEditor.Provider value={editor}><PaneContext.Provider value={{panes, togglePane, openPane}}><Slot.Provider value={setSlot}>{children}{slot && createPortal(<DirectorConversation
    access={access} setAccess={setAccess} messages={messages} tasks={tasks} discovery={discovery} text={text} setText={setText}
    selected={selected} setSelected={setSelected} skills={skills} setSkills={setSkills}
    busy={busy} error={error} send={send} control={control} loadContext={loadContext}
    onCollapse={() => togglePane('chat')} refresh={() => void attempt(refresh)}/>, slot)}</Slot.Provider></PaneContext.Provider></DirectorEditor.Provider>;
}
