import {createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {useProject} from './ProjectController';
import {agentRequest, computerGrant, exactApproval, type AgentMessage, type AgentTask} from './lib/agent-tasks';
import {discoverAgent, type AgentDiscovery} from './lib/agent-api';
import DirectorConversation from './DirectorConversation';
import {useProjectState} from './lib/project-state';
import './director-runtime.css';
import {DirectorEditor, type EditorBridge} from './DirectorEditor';
import {DirectorStory, type StoryTarget} from './DirectorStory';
import {DirectorMusic, type MusicTarget} from './DirectorMusic';
import {DirectorStudio, type StudioTarget} from './DirectorStudio';
import {DirectorVideo, type VideoPromptTarget} from './DirectorVideo';
import {DirectorImage, type ImageBridge} from './DirectorImage';
import {DirectorScreenplay, DirectorPrompts, type ScreenplayBridge, type PromptBridge} from './DirectorScreenplay';

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
  const [harnessOwner, setHarnessOwner] = useState<string | null>(null);
  const [harnessModel, setHarnessModel] = useState<string | null>(null);
  const [discovery, setDiscovery] = useState<AgentDiscovery | null>(null);
  const [text, setText] = useProjectState('DirectorRuntime:text', '');
  const [selected, setSelected] = useProjectState<string[]>('DirectorRuntime:assets', []);
  const [skills, setSkills] = useProjectState<string[]>('DirectorRuntime:skills', ['application/vibe/vibe-director']);
  const [access, setAccess] = useProjectState<'app' | 'project' | 'full'>('DirectorRuntime:access', 'app');
  const [savedPanes, setPanes] = useProjectState<Panes>('DirectorWorkspace:panes', {chat: true, work: true});
  const panes = {chat: savedPanes?.chat !== false, work: savedPanes?.work !== false};
  const togglePane = (pane: keyof Panes) => setPanes(old => ({chat: old?.chat !== false, work: old?.work !== false, [pane]: old?.[pane] === false}));
  const openPane = (pane: keyof Panes) => setPanes(old => ({chat: old?.chat !== false, work: old?.work !== false, [pane]: true}));
  const [busy, setBusy] = useState(false), [thinking, setThinking] = useState(false), [error, setError] = useState('');
  const abort = useRef(new AbortController());
  const pending = useRef<{id: string; key: string} | null>(null);
  const editor = useRef<EditorBridge | null>(null);
  const image = useRef<ImageBridge | null>(null);
  const story = useRef<{prepareTarget:()=>StoryTarget}|null>(null);
  const screenplay = useRef<ScreenplayBridge | null>(null);
  const prompts = useRef<PromptBridge | null>(null);
  const music = useRef<{prepareTarget:()=>Promise<MusicTarget>;refresh:()=>Promise<unknown>}|null>(null);
  const studio = useRef<{prepareTarget:()=>StudioTarget}|null>(null);
  const video = useRef<{prepareTarget:()=>VideoPromptTarget}|null>(null);
  const refresh = useCallback(async (signal: AbortSignal) => {
    const [history, listing] = await Promise.all([
      agentRequest<{messages: AgentMessage[]; runtime?: {harness_enabled: boolean; harness_model?: string}}>(owner, 'conversation', signal),
      agentRequest<{tasks: AgentTask[]}>(owner, 'tasks', signal),
    ]);
    if (signal.aborted) return;
    if (!Array.isArray(history.messages) || !Array.isArray(listing.tasks)) throw new Error('Restart the backend to load the Director runtime.');
    const reconciled = await Promise.all(listing.tasks.map(task => task.invocation ?
      agentRequest<AgentTask>(owner, `tasks/${task.task_id}`, signal) : Promise.resolve(task)));
    if (!signal.aborted) {
      setMessages(history.messages); setTasks(reconciled);
      setHarnessOwner(history.runtime?.harness_enabled ? owner : null);
      setHarnessModel(history.runtime?.harness_model || null);
    }
    if (!signal.aborted && reconciled.some(task => task.plan.tool_id === 'editor.prepare_brief')) await editor.current?.refresh();
  }, [owner]);
  useEffect(() => {
    const controller = new AbortController(); abort.current = controller;
    void refresh(controller.signal).catch(e => {if (!controller.signal.aborted) setError(e.message);});
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    if (!messages.some(message => message.goal?.status === 'running') &&
        !tasks.some(task => ['submitting', 'running', 'cancel_requested'].includes(task.status))) return;
    const timer = window.setInterval(() => void refresh(abort.current.signal).catch(e => {
      if (!abort.current.signal.aborted) setError(e.message);
    }), 2500);
    return () => window.clearInterval(timer);
  }, [tasks, messages, refresh]);
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
  const send = () => {
    setThinking(true);
    return attempt(async signal => {
      if (access !== 'app') {
        if (selected.length) throw new Error('Chat attachments are available in Application tools mode. Switch back to discuss these files, or remove the attachments before preparing a computer task.');
        const token = await computerGrant(signal);
        await agentRequest<AgentTask>(owner, 'tasks', signal, {tool_id: 'computer.execute', asset_ids: [],
          settings: {instruction: text, access_mode: access, skill_refs: skills}}, token);
        if (!signal.aborted) {setText(''); await refresh(signal);}
        return;
      }
      const postMessage = async (payload: {text: string; asset_ids: string[]; skill_refs: string[]; surface: string; target?: unknown}) => {
        const key = JSON.stringify(payload);
        if (!pending.current || pending.current.key !== key) pending.current = {id: crypto.randomUUID(), key};
        const result = await agentRequest<{messages: AgentMessage[]}>(owner, 'conversation', signal, {
          request_id: pending.current.id, ...payload,
        });
        if (!signal.aborted) {setMessages(result.messages); setText(''); pending.current = null; await refresh(signal);}
      };
      const editing = location.hash.startsWith('#/editor');
      if (harnessOwner === owner) {
        // Read-only context getter: starting chat must not create an Editor session
        // or require a screenplay/creative form before the agent can discover media.
        const target = editing ? editor.current?.currentTarget?.() : undefined;
        await postMessage({text, asset_ids: selected, skill_refs: skills,
          surface: target ? 'editor' : 'director', ...(target ? {target} : {})});
        return;
      }
      if (editing && !editor.current) throw new Error('Wait for the Editor session to load.');
      const inStory = location.hash.split('?')[0] === '#/story';
      if (inStory && !story.current) throw new Error('Wait for the Story workspace to load.');
      const storyTarget = inStory ? story.current!.prepareTarget() : undefined;
      if (storyTarget && storyTarget.workspace_id !== owner) throw new Error('Wait for the current project’s story to load.');
      const screenplayTarget = !editing && !storyTarget ? screenplay.current?.prepareTarget() : undefined;
      if (screenplayTarget && screenplayTarget.workspace_id !== owner) throw new Error('Wait for the current project’s screenplay to load.');
      const promptTarget = !editing && !storyTarget && !screenplayTarget ? prompts.current?.prepareTarget() : undefined;
      if (promptTarget && promptTarget.workspace_id !== owner) throw new Error('Wait for the current project’s prompts to load.');
      const imageTarget = !editing && !storyTarget && !screenplayTarget && !promptTarget ? image.current?.prepareTarget() : undefined;
      if (imageTarget && imageTarget.request.workspace_id !== owner) throw new Error('Wait for the current project’s image controls to load.');
      const videoTarget = location.hash.split('?')[0] === '#/video' && !screenplayTarget && !promptTarget && !imageTarget ? video.current?.prepareTarget() : undefined;
      if (videoTarget && videoTarget.workspace_id !== owner) throw new Error('Wait for the current project’s video controls to load.');
      const studioTarget = !editing && !storyTarget && !screenplayTarget && !promptTarget && !imageTarget && !videoTarget ? studio.current?.prepareTarget() : undefined;
      if (studioTarget && studioTarget.workspace_id !== owner) throw new Error('Wait for the current studio to load.');
      const musicTarget = !editing && !storyTarget && !screenplayTarget && !promptTarget && !imageTarget && !videoTarget && !studioTarget ? await music.current?.prepareTarget() : undefined;
      if (musicTarget && musicTarget.workspace_id !== owner) throw new Error('Wait for the current music session to load.');
      const target = editing ? await editor.current!.prepareTarget() : storyTarget || screenplayTarget || promptTarget || imageTarget || videoTarget || studioTarget || musicTarget;
      if (signal.aborted) return;
      const payload = {text, asset_ids: selected, skill_refs: skills,
        surface: editing ? 'editor' : storyTarget ? 'story' : screenplayTarget ? 'screenplay' : promptTarget ? 'prompt' : imageTarget ? 'image' : videoTarget ? 'video' : studioTarget ? 'studio' : musicTarget ? 'music' : 'director', ...(target ? {target} : {})};
      await postMessage(payload);
      if (!signal.aborted) {
        if (!signal.aborted && screenplayTarget) await screenplay.current?.refresh();
        if (!signal.aborted && promptTarget) await prompts.current?.refresh();
        if (!signal.aborted && musicTarget) await music.current?.refresh();
      }
    }).finally(() => setThinking(false));
  };
  const control = (task: AgentTask, action: 'approve' | 'run' | 'cancel') => attempt(async signal => {
    const goalLinked = messages.some(message => message.goal?.steps.some(step => step.task_id === task.task_id));
    const token = task.plan.tool_id === 'computer.execute' || goalLinked ? await computerGrant(signal) : undefined;
    const updated = await agentRequest<AgentTask>(owner, `tasks/${task.task_id}/${action}`, signal, action === 'cancel' ? {} : exactApproval(task), token);
    if (!signal.aborted) setTasks(rows => rows.map(row => row.task_id === updated.task_id ? updated : row));
    if (!signal.aborted && updated.plan.tool_id === 'editor.prepare_brief') await editor.current?.refresh();
    if (!signal.aborted && goalLinked) await refresh(signal);
  });
  return <DirectorStory.Provider value={{bridge:story,messages}}><DirectorMusic.Provider value={music}><DirectorStudio.Provider value={{bridge:studio,messages}}><DirectorVideo.Provider value={{bridge:video,messages}}><DirectorPrompts.Provider value={prompts}><DirectorScreenplay.Provider value={screenplay}><DirectorImage.Provider value={{bridge: image, messages}}><DirectorEditor.Provider value={editor}><PaneContext.Provider value={{panes, togglePane, openPane}}><Slot.Provider value={setSlot}>{children}{slot && createPortal(<DirectorConversation
    access={access} setAccess={setAccess} messages={messages} tasks={tasks} discovery={discovery} text={text} setText={setText}
    selected={selected} setSelected={setSelected} skills={skills} setSkills={setSkills}
    busy={busy} thinking={thinking} error={error} send={send} control={control} loadContext={loadContext}
    harnessModel={harnessOwner === owner ? harnessModel : null}
    goalControl={(request, action) => void attempt(async signal => {
      await agentRequest(owner, `conversation/${request}/${action}`, signal, {}); await refresh(signal);
    })}
    onCollapse={() => togglePane('chat')} refresh={() => void attempt(refresh)}/>, slot)}</Slot.Provider></PaneContext.Provider></DirectorEditor.Provider></DirectorImage.Provider></DirectorScreenplay.Provider></DirectorPrompts.Provider></DirectorVideo.Provider></DirectorStudio.Provider></DirectorMusic.Provider></DirectorStory.Provider>;
}
