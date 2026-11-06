import {createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {useProject} from './ProjectController';
import {agentRequest, computerGrant, exactApproval, type AgentMessage, type AgentTask} from './lib/agent-tasks';
import {discoverAgent, type AgentDiscovery} from './lib/agent-api';
import DirectorConversation from './DirectorConversation';
import {useProjectState} from './lib/project-state';
import './director-runtime.css';

const Slot = createContext<(element: HTMLDivElement | null) => void>(() => {});
export function DirectorSlot() {
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
  return <div className="director-slot" ref={register}/>;
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
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const abort = useRef(new AbortController());
  const pending = useRef<{id: string; key: string} | null>(null);
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
    const payload = {text, asset_ids: selected, skill_refs: skills,
      surface: location.hash.startsWith('#/editor') ? 'editor' : 'director'};
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
  });
  return <Slot.Provider value={setSlot}>{children}{slot && createPortal(<DirectorConversation
    access={access} setAccess={setAccess} messages={messages} tasks={tasks} discovery={discovery} text={text} setText={setText}
    selected={selected} setSelected={setSelected} skills={skills} setSkills={setSkills}
    busy={busy} error={error} send={send} control={control} loadContext={loadContext}
    refresh={() => void attempt(refresh)}/>, slot)}</Slot.Provider>;
}
