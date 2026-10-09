import { useCallback, useEffect, useState } from 'react';
import { Activity, Check, Clapperboard, Database, Film, Gauge, RefreshCw, Server, Workflow, XCircle } from 'lucide-react';
import { getRuntimeGuard, getWorkerDispatch, getWorkflowStatus, RuntimeGuard, StatusWorkflow, WorkflowStatus } from './lib/status-api';

const groups = [
  ['video', 'Video workflows'], ['image', 'Image workflows'], ['audio', 'Audio workflows'],
] as const;
const isKnownLimit = (workflow: StatusWorkflow) => workflow.prompt_limit.max !== undefined && workflow.prompt_limit.max !== null;
const markStatusStale = (status: WorkflowStatus): WorkflowStatus => ({
  ...status, backend: { connected: false },
  dispatch: { ...status.dispatch, available: false, worker_state: 'unknown', reason: 'Worker status is stale; refresh to confirm availability.' },
  runtime_guard: { ...status.runtime_guard, monitor_available: false, safe_to_submit: false, reason: 'Runtime status is stale; refresh to confirm safety.' },
  workflows: status.workflows.map(item => item.workflow_id === 'minimax_h3_t2v_local_v1' ? { ...item, available: false, state: 'unavailable', reason: 'Status is stale; refresh before relying on workflow readiness.' } : item),
});

const withCurrentReadiness = (status: WorkflowStatus, runtime: RuntimeGuard, dispatch: WorkflowStatus['dispatch']): WorkflowStatus => ({
  ...status, runtime_guard: runtime, dispatch,
  workflows: status.workflows.map(item => item.workflow_id !== 'minimax_h3_t2v_local_v1' ? item : {
    ...item,
    available: status.backend.connected && item.workflow_available === true && runtime.monitor_available && runtime.safe_to_submit && dispatch.available,
    state: status.backend.connected && item.workflow_available === true && runtime.monitor_available && runtime.safe_to_submit && dispatch.available ? 'usable' : 'unavailable',
    reason: !status.backend.connected ? 'Backend status is stale; refresh to confirm readiness.' : item.workflow_reason || (!runtime.monitor_available || !runtime.safe_to_submit ? runtime.reason || 'GPU safety monitor has not admitted rendering.' : !dispatch.available ? dispatch.reason || 'Explicit worker dispatch is unavailable.' : null),
  }),
});

export default function StatusPage() {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [runtime, setRuntime] = useState<RuntimeGuard | null>(null);
  const [workerReason, setWorkerReason] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const value = await getWorkflowStatus();
      setStatus(withCurrentReadiness(value, value.runtime_guard, value.dispatch)); setRuntime(value.runtime_guard); setWorkerReason(value.dispatch.reason || null); setStale(false);
    } catch (cause) {
      setStale(true);
      setStatus(previous => previous ? markStatusStale(previous) : previous);
      setRuntime(previous => previous ? { ...previous, monitor_available: false, safe_to_submit: false, reason: 'Runtime status is stale; refresh to confirm safety.' } : null);
      setError((cause as Error).message || 'Status service is unavailable.');
    }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      // These lightweight reads refresh live runtime/worker state. They do not
      // repeat ComfyUI object_info, model hashing, or the full workflow preflight.
      void Promise.all([getRuntimeGuard(), getWorkerDispatch()]).then(([guard, worker]) => {
        setRuntime(guard); setWorkerReason(worker.reason || null);
        setStatus(previous => previous ? withCurrentReadiness(previous, guard, worker) : previous);
      }).catch(() => {
        setStale(true);
        setStatus(previous => previous ? markStatusStale(previous) : previous);
        setRuntime(previous => previous ? { ...previous, monitor_available: false, safe_to_submit: false, reason: 'Runtime status is stale; refresh to confirm safety.' } : null);
        setError('Runtime monitor is unavailable; the last snapshot is shown as stale and generation is not confirmed.');
      });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const renderWorkflow = (workflow: StatusWorkflow) => <article className="status-workflow card" key={workflow.workflow_id}>
    <div className="status-workflow-head"><div><h3>{workflow.label}</h3><small>{workflow.workflow_id}</small></div><span className={`workflow-state ${workflow.state}`}>{workflow.state.replaceAll('_', ' ')}</span></div>
    <div className="workflow-facts">
      <span><b>Inputs</b>{workflow.input_roles.join(', ')}</span>
      {workflow.duration_seconds && <span><b>Duration</b>{workflow.duration_seconds.min}–{workflow.duration_seconds.max} {workflow.duration_seconds.unit}</span>}
      {workflow.outputs && <span><b>Outputs</b>{workflow.outputs.map(item => `${item.preset} · ${item.width} × ${item.height}`).join('  /  ')}</span>}
      {workflow.fixed_parameters && <span><b>Fixed</b>{Object.entries(workflow.fixed_parameters).map(([key, value]) => `${key} ${value}`).join(' · ')}</span>}
      <span><b>Prompt limit</b>{isKnownLimit(workflow) ? `≤ ${workflow.prompt_limit.max!.toLocaleString()} ${workflow.prompt_limit.unit}` : `Unknown (${workflow.prompt_limit.unit})`}</span>
    </div>
    {workflow.workflow_id === 'minimax_h3_t2v_local_v1' && <div className="evidence-facts">
      <span><b>Opt-in feature</b>{workflow.feature_enabled ? 'Enabled' : 'Disabled'}</span>
      <span><b>Versioned graph</b>{workflow.graph_present ? 'Present' : 'Missing'}</span>
      <span><b>Required models</b>{workflow.models?.present ?? 0} / {workflow.models?.required ?? 0} present</span>
      <span><b>Required nodes</b>{workflow.nodes?.checked ? workflow.nodes.missing_count === 0 ? 'Checked · all present' : `${workflow.nodes.missing_count} missing` : 'Not checked · ComfyUI unavailable'}</span>
    </div>}
    {stale && workflow.workflow_id === 'minimax_h3_t2v_local_v1' && <p className="workflow-reason">Last reported: {workflow.workflow_reason || 'Workflow evidence shown below is from the last successful snapshot; current usability is unconfirmed.'}</p>}
    {workflow.reason && <p className="workflow-reason">{workflow.reason}</p>}
  </article>;

  return <div className="app-shell status-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><Clapperboard size={18}/></div><div><strong>Vibe Director</strong><span>LOCAL STUDIO</span></div></div>
      <div className="workspace-label">WORKSPACE</div><nav aria-label="Main navigation">
        <a className="nav-item" href="#/video"><Film size={17}/> Video</a>
        <a className="nav-item" href="#/story"><Workflow size={17}/> Story</a>
        <a className="nav-item disabled" aria-disabled="true"><Database size={17}/> Assets <span className="soon">Soon</span></a>
        <a className="nav-item disabled" aria-disabled="true"><Server size={17}/> Media <span className="soon">Soon</span></a>
        <a className="nav-item" href="#/status" aria-current="page"><Activity size={17}/> Status <span className="nav-current"/></a>
      </nav><div className="sidebar-spacer"/><div className="profile"><div className="avatar">VD</div><div><b>Local session</b><span>Drafts stay on this device</span></div></div>
    </aside>
    <main className="main-content"><header className="topbar"><div className="breadcrumbs"><span>Workspace</span><span className="crumb-divider">/</span><b>Status</b></div><div className="top-actions"><span className="local-pill"><span className={`status-dot ${status?.backend.connected ? 'green' : ''}`}/> {loading && !status ? 'Loading status' : stale ? 'Status stale' : status?.backend.connected ? 'Backend connected' : 'Backend unavailable'}</span><button className="quiet-button status-refresh" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''}/> Refresh status</button></div></header>
      <div className="content-wrap status-content"><div className="page-heading"><div><div className="eyebrow">WORKSPACE / STATUS</div><h1>Connections & workflows</h1><p>Read-only view of workflow usability, configured limits, and current local runtime state.</p></div></div>
        {error && <div className="notice notice-warn" role="alert">{error}</div>}
        {!status && <div className="card status-empty" role="status">{loading ? <><RefreshCw size={20} className="spin"/><b>Loading status</b><span>Checking backend and local workflow state…</span></> : <><XCircle size={20}/><b>Backend unavailable</b><span>Status could not be loaded. Refresh to try again. No workflow is assumed ready.</span></>}</div>}
        {status && <>
          {stale && <div className="notice notice-warn" role="status">Showing last successful values as stale. Workflow readiness and GPU safety are unknown until status refresh succeeds.</div>}
          <section className="status-overview" aria-label="Runtime overview">
            <article className="status-metric card"><div className="metric-label"><Server size={15}/> Backend</div><strong className="metric-value"><span className={`status-dot ${status.backend.connected ? 'green' : 'red'}`}/>{status.backend.connected ? 'Connected' : stale ? 'Unknown · stale' : 'Unavailable'}</strong><small>Responded to this read-only status request.</small></article>
            <article className="status-metric card"><div className="metric-label"><Activity size={15}/> ComfyUI</div><strong className="metric-value"><span className={`status-dot ${status.comfyui.reachable ? 'green' : 'red'}`}/>{stale ? 'Unknown · stale' : status.comfyui.reachable ? 'Reachable' : 'Unreachable'}</strong><small>{stale ? `Last reported: ${status.comfyui.reason || (status.comfyui.reachable ? 'Node catalog reachable.' : 'Node catalog unreachable.')}` : status.comfyui.reason || 'Node catalog reachable.'}</small></article>
            <article className="status-metric card"><div className="metric-label"><Workflow size={15}/> Video worker</div><strong className="metric-value"><span className={`status-dot ${status.dispatch.available ? 'green' : 'red'}`}/>{stale ? 'Unknown · stale' : status.dispatch.available ? 'Dispatch available' : status.dispatch.worker_state.replaceAll('_', ' ')}</strong><small>{workerReason || 'Worker reports ready for explicitly requested jobs.'}</small></article>
          </section>
          <section className={`runtime-card card ${runtime?.monitor_available && runtime.safe_to_submit ? 'safe' : 'blocked'}`} aria-label="GPU runtime status"><div className="runtime-title"><Gauge size={18}/><div><h2>GPU safety monitor</h2><p>{runtime?.monitor_available && runtime.safe_to_submit ? 'Within the configured operating limits.' : runtime?.reason || 'Runtime safety is not confirmed.'}</p></div><span className={`workflow-state ${runtime?.monitor_available && runtime.safe_to_submit ? 'usable' : 'unavailable'}`}>{runtime?.monitor_available && runtime.safe_to_submit ? 'safe now' : 'generation blocked'}</span></div>
            <div className="runtime-values"><span><b>Current temperature</b>{runtime?.operating_point ? `${runtime.operating_point.temperature_c} °C` : 'Unavailable'}</span><span><b>Temperature cutoff</b>{runtime ? `${runtime.temperature_cutoff_c} °C` : '—'}</span><span><b>Graphics clock</b>{runtime?.operating_point ? `${runtime.operating_point.graphics_clock_mhz} MHz` : 'Unavailable'}</span><span><b>Clock ceiling</b>{runtime ? `${runtime.graphics_clock_ceiling_mhz} MHz` : '—'}</span></div>
          </section>
          <section className="status-catalog"><div className="section-title"><div><h2>Workflow catalog</h2><p>Only the exact verified workflow is marked usable by this application.</p></div></div>
            {groups.map(([category, title]) => { const rows = status.workflows.filter(workflow => workflow.category === category || (!workflow.category && category === 'video' && ['minimax_h3_t2v_local_v1', 'first_last_frame', 'reference_to_video'].includes(workflow.workflow_id))); return rows.length ? <div className="workflow-group" key={category}><h3>{title}</h3><div className="catalog-list">{rows.map(renderWorkflow)}</div></div> : null; })}
          </section>
          <p className="status-footnote"><Check size={14}/> Status checks are read-only. Opening or refreshing this page does not submit jobs. Runtime and worker summaries refresh every 5 seconds; full workflow evidence refreshes only on page entry or Refresh status.</p>
        </>}
      </div>
    </main>
  </div>;
}
