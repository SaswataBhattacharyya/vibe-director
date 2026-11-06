import {useState, type Dispatch, type SetStateAction} from 'react';
import {ArrowUp, MessageSquare, PanelLeftClose, RefreshCw, SlidersHorizontal} from 'lucide-react';
import {useProject} from './ProjectController';
import ProjectKnowledge from './ProjectKnowledge';
import type {AgentDiscovery} from './lib/agent-api';
import type {AgentMessage, AgentTask} from './lib/agent-tasks';

type Props = {
  access: 'app' | 'project' | 'full'; setAccess: (value: 'app' | 'project' | 'full') => void;
  messages: AgentMessage[]; tasks: AgentTask[]; discovery: AgentDiscovery | null;
  text: string; setText: (value: string) => void; selected: string[]; skills: string[];
  setSelected: Dispatch<SetStateAction<string[]>>; setSkills: Dispatch<SetStateAction<string[]>>;
  busy: boolean; error: string; send: () => void; loadContext: () => void; refresh: () => void;
  control: (task: AgentTask, action: 'approve' | 'run' | 'cancel') => void;
};
function TaskCard({task, busy, control}: Pick<Props, 'busy' | 'control'> & {task: AgentTask}) {
  return <article className="director-task" aria-label={`Task ${task.task_id}`}>
    <div className="director-task-heading"><strong>{task.plan.tool_id === 'computer.execute' ? 'Codex computer task' : task.plan.tool_id === 'video.continuity_last_frame' ? 'Extract continuity frame' : 'Extract MP3'}</strong><span className="director-status">{task.status.replaceAll('_', ' ')}</span></div>
    <p>{task.plan.scope}</p>
    {task.plan.settings.access_mode && <><strong>{task.plan.settings.access_mode === 'full' ? 'Full access' : 'Project only'}</strong>
      <small className="director-job">{task.plan.settings.workspace_path} · {task.plan.settings.model}</small>
      <pre style={{whiteSpace: 'pre-wrap'}}>{task.plan.settings.instruction}</pre></>}
    {task.report && <><small>Codex report · deliverables require inspection</small><pre style={{whiteSpace: 'pre-wrap'}}>{task.report}</pre></>}
    <ul>{task.plan.assets.map(asset => <li key={asset.asset_id}>{asset.filename}</li>)}</ul>
    <small>{task.plan.settings.quality !== undefined && `Quality ${task.plan.settings.quality} · `}revision {task.current_revision} · {task.plan_hash.slice(0, 10)}</small>
    {task.invocation?.job_id && <small className="director-job">Job {task.invocation.job_id}</small>}
    <div className="director-task-actions">
      {task.status === 'draft' && <button disabled={busy} onClick={() => control(task, 'approve')}>Approve this plan</button>}
      {task.status === 'approved' && <button disabled={busy} onClick={() => control(task, 'run')}>Run approved task</button>}
      {['draft', 'approved', 'running', 'submitting', 'cancel_requested', 'recovery_required'].includes(task.status) && <button disabled={busy} onClick={() => control(task, 'cancel')}>Cancel task</button>}
      {task.status === 'recovery_required' && <button disabled={busy} onClick={() => control(task, 'run')}>Reconcile existing job</button>}
    </div>
    {task.outputs?.map(asset => <div className="director-output" key={asset.asset_id}>
      <a href={asset.content_url}>{asset.filename}</a>
      {task.plan.tool_id === 'video.continuity_last_frame' ? <img src={asset.content_url} alt="Extracted last frame" style={{maxWidth: '100%', borderRadius: 8}}/> : <><audio controls preload="none" src={asset.content_url}/>
      <button onClick={() => {sessionStorage.setItem('vibe-editor-pending-audio', JSON.stringify({workspace_id: task.project_id, asset})); window.dispatchEvent(new Event('vibe-editor-audio-offer')); location.hash = '#/editor';}}>Offer audio to Editor</button></>}
    </div>)}
    {task.events.length > 0 && <details><summary>Activity · {task.events.length}</summary><ol>{task.events.map(event => <li key={event.sequence}>{event.event_type.replaceAll('_', ' ')} <time>{event.created_at}</time></li>)}</ol></details>}
  </article>;
}
export default function DirectorConversation(props: Props) {
  const {title} = useProject();
  const [open, setOpen] = useState(true), [contextOpen, setContextOpen] = useState(false);
  const toggle = (items: string[], id: string) => items.includes(id) ? items.filter(item => item !== id) : [...items, id];
  return <section className={`director-conversation ${open ? '' : 'director-collapsed'}`} aria-label="Project Director conversation">
    <header className="director-conversation-header"><MessageSquare size={18}/><div><strong>Director</strong><small>{title}</small></div>
      <button className="director-icon" aria-label="Refresh Director conversation" disabled={props.busy} onClick={props.refresh}><RefreshCw size={16}/></button>
      <button className="director-icon" aria-label={open ? 'Hide Director conversation' : 'Show Director conversation'} aria-expanded={open} onClick={() => setOpen(value => !value)}><PanelLeftClose size={16}/></button>
    </header>
    <div className="director-body" hidden={!open}>
      <div className="director-transcript" role="log" aria-label="Director conversation history" aria-live="polite">
        {!props.messages.length && <div className="director-welcome"><span className="director-kicker">YOUR FILM WORKSPACE</span><h2>What are we making?</h2><p>Plan a scene, develop a shot, or work with your project’s media.</p><p className="director-hint">Chat can discuss your film and propose MP3 or last-frame extraction. Other production tools remain available in the work surface.</p></div>}
        {props.messages.map(message => <article className="director-message" key={message.request_id}>
          <div className="director-user-message">{message.text}</div>
          {message.reply && <p>{message.reply}</p>}
          {message.status === 'thinking' && <p className="director-hint">Response pending. Refresh to check the saved conversation; an interrupted request will not be sent again automatically.</p>}
          {message.status === 'interrupted' && <p role="status">This response was interrupted. Your message is saved. Send a new message to continue.</p>}
        </article>)}
        {props.tasks.map(task => <TaskCard key={task.task_id} task={task} busy={props.busy} control={props.control}/>)}
      </div>
      <div className="director-composer-wrap">
        {props.error && <p role="alert" className="director-error">{props.error}</p>}
        <button className="director-context-button" aria-expanded={contextOpen} onClick={() => {setContextOpen(value => !value); if (!props.discovery) props.loadContext();}}><SlidersHorizontal size={15}/> Context & skills{props.selected.length ? ` · ${props.selected.length} selected` : ''}</button>
        {contextOpen && <div className="director-context"><p>Tools are shared across projects. Media, selected skills and conversation belong to the open project.</p>
          {!props.discovery ? <p role="status">Load project context using Refresh after resolving any connection error.</p> : <>
            <fieldset><legend>Audio / video inputs · whole assets</legend>{props.discovery.context.nodes.filter(node => node.kind === 'asset' && /\.(wav|mp3|flac|ogg|aac|m4a|mp4|mov|mkv|webm|avi)$/i.test(node.label)).map(node => <label key={node.id}><input type="checkbox" checked={props.selected.includes(node.source_id)} onChange={() => props.setSelected(items => toggle(items, node.source_id))}/>{node.label}</label>)}</fieldset>
            <fieldset><legend>Skills for this message · up to six</legend>{props.discovery.skills.filter(skill => skill.available).map(skill => <label key={skill.ref}><input type="checkbox" disabled={props.skills.length >= 6 && !props.skills.includes(skill.ref)} checked={props.skills.includes(skill.ref)} onChange={() => props.setSkills(items => toggle(items, skill.ref))}/><span>{skill.id}<small>{skill.scope} · {skill.provider}</small></span></label>)}</fieldset>
          </>}
          <button disabled={props.busy} onClick={props.loadContext}>Refresh context</button>
          <ProjectKnowledge/>
        </div>}
        <label className="director-access">Access
          <select aria-label="Director access mode" value={props.access} disabled={props.busy} onChange={event => props.setAccess(event.target.value as Props['access'])}>
            <option value="app">Application tools</option><option value="project">Project only</option><option value="full">Full access</option>
          </select>
        </label>
        {props.access !== 'app' && <p className="director-hint">{props.access === 'full' ? 'Codex can access local files outside the project and the network.' : 'Codex can work in this project; unrelated user files and network are blocked.'} Sending prepares a task for approval. Terminal, coding and filesystem are available through the installed CLI; interactive browser control is unavailable.</p>}
        <form className="director-composer" onSubmit={event => {event.preventDefault(); props.send();}}>
          <label htmlFor="project-director-message" className="director-sr-only">Message the project Director</label>
          <textarea id="project-director-message" rows={3} placeholder="Describe your next scene or ask for a plan…" value={props.text} onChange={event => props.setText(event.target.value)} disabled={props.busy}/>
          <div><small>{props.busy ? 'Working on your request…' : 'Review a plan before running it.'}</small><button aria-label="Send to project Director" disabled={props.busy || !props.text.trim()}><ArrowUp size={18}/></button></div>
        </form>
      </div>
    </div>
  </section>;
}
