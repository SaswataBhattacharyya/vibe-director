import {useRef, type CSSProperties, type ReactNode} from 'react';
import {DirectorSlot, useDirectorPanes} from './DirectorRuntime';
import {PanelLeft, PanelRight} from 'lucide-react';
import AgentInspector from './AgentInspector';
import {useProjectState} from './lib/project-state';

export default function DirectorWorkspace({children}: {children: ReactNode}) {
  const {panes, togglePane, openPane} = useDirectorPanes();
  const [width, setWidth] = useProjectState('DirectorWorkspace:width', 34);
  const [surface, setSurface] = useProjectState('DirectorWorkspace:surface', 'workspace');
  const container = useRef<HTMLDivElement>(null);
  const bounded = (value: number) => Math.max(28, Math.min(60, value));
  const percent = typeof width === 'number' && Number.isFinite(width) ? bounded(width) : 34;
  const resize = (clientX: number) => {
    const bounds = container.current?.getBoundingClientRect();
    if (bounds?.width) setWidth(bounded((clientX - bounds.left) / bounds.width * 100));
  };
  return <>
    <div className="director-pane-toolbar" role="group" aria-label="Workspace panes">
      <button aria-label={`${panes.chat ? 'Hide' : 'Show'} Director conversation`} title="Toggle Director conversation" aria-expanded={panes.chat} onClick={() => togglePane('chat')}><PanelLeft size={16}/><span>Director</span></button>
      <button aria-label={`${panes.work ? 'Hide' : 'Show'} workspace`} title="Toggle workspace" aria-expanded={panes.work} onClick={() => togglePane('work')}><PanelRight size={16}/><span>Workspace</span></button>
      <AgentInspector/>
    </div>
    <div className="director-surface-switch" aria-label="Workspace view">
      <button aria-pressed={surface === 'chat' && panes.chat} onClick={() => {openPane('chat'); setSurface('chat');}}>Director chat</button>
      <button aria-pressed={surface !== 'chat' && panes.work} onClick={() => {openPane('work'); setSurface('workspace');}}>Workspace</button>
    </div>
    {!panes.chat && !panes.work && <p className="director-empty-panes" role="status">Both panes are hidden. Use the controls above to restore your workspace.</p>}
    <div ref={container} className="director-workspace" data-surface={!panes.work ? 'chat' : !panes.chat ? 'workspace' : surface} data-chat-open={panes.chat} data-work-open={panes.work}
      style={{'--director-width': `${percent}%`} as CSSProperties}>
      <DirectorSlot hidden={!panes.chat}/>
      <div className="director-resizer" hidden={!panes.chat || !panes.work} role="separator" tabIndex={0} aria-label="Resize Director conversation"
        aria-orientation="vertical" aria-valuemin={28} aria-valuemax={60} aria-valuenow={Math.round(percent)}
        onDoubleClick={() => setWidth(34)}
        onKeyDown={event => {
          const next = {ArrowLeft: percent - 2, ArrowRight: percent + 2, Home: 28, End: 60}[event.key];
          if (next !== undefined) {event.preventDefault(); setWidth(bounded(next));}
        }}
        onPointerDown={event => {if (event.button === 0) {event.currentTarget.setPointerCapture(event.pointerId); resize(event.clientX);}}}
        onPointerMove={event => {if (event.currentTarget.hasPointerCapture(event.pointerId)) resize(event.clientX);}}
        onPointerUp={event => {if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);}}/>
      <div className="studio-page-content" hidden={!panes.work}>{children}</div>
    </div>
  </>;
}
