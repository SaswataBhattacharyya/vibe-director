import {useEffect, useId, useState} from 'react';
import {useProject} from './ProjectController';
import {discoverAgent, type AgentDiscovery} from './lib/agent-api';
import './agent-inspector.css';

export default function AgentInspector() {
  const {workspace_id, title} = useProject();
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<{owner: string; value: AgentDiscovery} | null>(null);
  const [error, setError] = useState('');
  const panelId = useId();
  useEffect(() => {
    setResult(null);
    setError('');
    if (!open) return;
    const controller = new AbortController();
    discoverAgent(workspace_id, controller.signal).then(value => {
      if (!controller.signal.aborted) setResult({owner: workspace_id, value});
    }).catch(error => {
      if (!controller.signal.aborted) setError(error.message || 'Agent discovery failed.');
    });
    return () => controller.abort();
  }, [open, workspace_id]);
  const data = result?.owner === workspace_id ? result.value : null;
  return <section className="agent-inspector" aria-label="Agent discovery">
    <button type="button" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(value => !value)}>
      {open ? 'Hide' : 'Show'} agent capabilities
    </button>
    {open && <div id={panelId} className="agent-inspector-panel">
      <h2>Agent capabilities · {title}</h2>
      <p>Tools are shared across projects. Skills provide guidance. Approve and run supported tasks in the Director conversation.</p>
      {error ? <p role="alert">{error}</p> : !data ? <p role="status">Loading capabilities…</p> : <>
        <h3>Shared tools</h3>
        <ul>{data.tools.map(tool => <li key={tool.id}><b>{tool.id}</b> · {tool.status} · {tool.effect}
          {tool.reason && <p>{tool.reason}</p>}</li>)}</ul>
        <h3>Skills</h3>
        <ul>{data.skills.map(skill => <li key={skill.ref}><b>{skill.ref}</b> · {skill.available ? 'available' : 'unavailable'}
          <p>{skill.description || skill.reason || 'No description supplied.'}</p>
          {skill.version && <small>Version {skill.version} · </small>}{skill.sha256 && <small>SHA-256 {skill.sha256.slice(0, 12)}</small>}</li>)}</ul>
        {data.skillsTruncated && <p>Skill listing reached its limit.</p>}
        <h3>Project context</h3>
        <ul>{data.context.nodes.map(node => <li key={node.id}><b>{node.kind}</b> · {node.label}
          <small> {node.source_id} · {node.provenance}{node.revision != null ? ` · revision ${node.revision}` : ''}</small></li>)}</ul>
        {data.context.truncated.length > 0 && <p>Context limited: {data.context.truncated.join(', ')}.</p>}
      </>}
    </div>}
  </section>;
}
