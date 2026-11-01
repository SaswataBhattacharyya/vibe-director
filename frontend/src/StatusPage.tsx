import PerformancePanel from './PerformancePanel';
import DebugPanel from './DebugPanel';
import { useCallback, useEffect, useState } from 'react';
import { Activity, Check, Copy, Gauge, RefreshCw, Server, Workflow, XCircle } from 'lucide-react';
import { setWorkloadPolicy, clearGpuSafetyHold, getComfyQueueStatus, getGpuAdmission, getLocalJobQueueStatus, getRuntimeGuard, getWorkerDispatch, GpuAdmission, getWorkflowStatus, LocalJobQueueStatus, RuntimeGuard, StatusWorkflow, WorkflowStatus } from './lib/status-api';

const groups = [
  ['video', 'Video workflows'], ['image', 'Image workflows'], ['audio', 'Audio workflows'],
] as const;
const isKnownLimit = (workflow: StatusWorkflow) => workflow.prompt_limit.max !== undefined && workflow.prompt_limit.max !== null;
const textInputRoles = (workflow: StatusWorkflow) => workflow.input_roles.filter(role => /prompt|text|tags?|lyrics?|dialogue|transcript/i.test(role));
const canGenerate = (workflow: StatusWorkflow) => workflow.state !== 'not_integrated' && (workflow.category === 'video' || workflow.category === 'image' || workflow.workflow_id === 'minimax_h3_t2v_local_v1');
const hasCurrentStatusContract = (status: WorkflowStatus) => status.comfyui_queue !== undefined
  && status.local_queue !== undefined
  && status.workflows.some(workflow => workflow.workflow_id === 'minimax_h3_t2v_local_v1' && workflow.automation_available !== undefined);
const markStatusStale = (status: WorkflowStatus): WorkflowStatus => ({
  ...status, backend: { connected: false },
  comfyui_queue: { checked: false, running: null, pending: null, reason: 'Queue status is stale; refresh to confirm.' },
  local_queue: { checked: false, pending: null, active: null, attention: null, reason: 'Vibe Director queue status is stale; refresh to confirm.', sources: (status.local_queue?.sources || []).map(source => ({ id: source.id, checked: false })) },
  dispatch: { ...status.dispatch, available: false, worker_state: 'unknown', reason: 'Worker status is stale; refresh to confirm availability.' },
  runtime_guard: { ...status.runtime_guard, monitor_available: false, safe_to_submit: false, reason: 'Runtime status is stale; refresh to confirm safety.' },
  workflows: status.workflows.map(item => canGenerate(item) ? { ...item, available: false, state: 'unavailable', reason: 'Status is stale; refresh before relying on workflow readiness.' } : item),
});

const withCurrentReadiness = (status: WorkflowStatus, runtime: RuntimeGuard, dispatch: WorkflowStatus['dispatch']): WorkflowStatus => ({
  ...status, runtime_guard: runtime, dispatch,
  workflows: status.workflows.map(item => {
    if (!canGenerate(item)) return item;
    const backendReady = status.backend.connected;
    const workflowReady = item.workflow_available === true;
    const runtimeReady = runtime.monitor_available && runtime.safe_to_submit;
    const workerReady = item.workflow_id === 'minimax_h3_t2v_local_v1'
      ? dispatch.available
      : item.worker_available === true && (item.category !== 'video' || dispatch.available);
    const available = backendReady && workflowReady && runtimeReady && workerReady;
    const reason = !backendReady ? 'Backend status is stale; refresh to confirm readiness.'
      : !workflowReady ? item.workflow_reason || item.reason || 'Workflow preflight did not pass.'
      : !runtimeReady ? runtime.reason || 'GPU safety monitor has not admitted rendering.'
      : !workerReady ? item.worker_reason || dispatch.reason || 'Generation worker is unavailable.'
      : null;
    return { ...item, available, state: available ? 'usable' as const : 'unavailable' as const, reason };
  }),
});

export default function StatusPage() {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [localQueue, setLocalQueue] = useState<LocalJobQueueStatus | null>(null);
  const [runtime, setRuntime] = useState<RuntimeGuard | null>(null);
  const [workerReason, setWorkerReason] = useState<string | null>(null);
  const [gpuAdmission, setGpuAdmission] = useState<GpuAdmission | null>(null);
  const [gpuAdmissionBusy, setGpuAdmissionBusy] = useState(false);
  const [gpuAdmissionError, setGpuAdmissionError] = useState('');
  const [policyBusy, setPolicyBusy] = useState(false);
  const [policyError, setPolicyError] = useState('');
  const [safetyHoldBusy, setSafetyHoldBusy] = useState(false);
  const [safetyHoldError, setSafetyHoldError] = useState('');
  const [clockCopy, setClockCopy] = useState('');
  const copyClockCommand = async () => {
    try {
      await navigator.clipboard.writeText(`sudo nvidia-smi -i 0 --lock-gpu-clocks=0,${runtime?.graphics_clock_ceiling_mhz}`);
      setClockCopy('Copied');
    } catch { setClockCopy('Copy failed. Select the command and copy it manually.'); }
  };
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const value = await getWorkflowStatus();
      setStatus(withCurrentReadiness(value, value.runtime_guard, value.dispatch)); setLocalQueue(value.local_queue || null); setRuntime(value.runtime_guard); setWorkerReason(value.dispatch.reason || null); setStale(false);
    } catch (cause) {
      setStale(true);
      setStatus(previous => previous ? markStatusStale(previous) : previous);
      setRuntime(previous => previous ? { ...previous, monitor_available: false, safe_to_submit: false, reason: 'Runtime status is stale; refresh to confirm safety.' } : null);
      setError((cause as Error).message || 'Status service is unavailable.');
    }
    finally { setLoading(false); }
  }, []);
  const changeWorkloadPolicy = async (allow: boolean) => {
    setPolicyBusy(true); setPolicyError('');
    try {
      const policy = await setWorkloadPolicy(allow);
      setStatus(previous => previous ? { ...previous, workload_policy: policy } : previous);
    } catch (cause) { setPolicyError((cause as Error).message); }
    finally { setPolicyBusy(false); }
  };
  const checkGpuAdmission = async () => {
    setGpuAdmissionBusy(true); setGpuAdmissionError(''); setGpuAdmission(null);
    try { setGpuAdmission(await getGpuAdmission()); }
    catch (cause) { setGpuAdmissionError((cause as Error).message || 'Runtime readiness could not be checked.'); }
    finally { setGpuAdmissionBusy(false); }
  };
  const recoverSafetyHold = async () => {
    const confirmed = window.confirm('Only continue after verifying that the affected workload and any shared Ollama or SAM service are idle. Clear the admission hold?');
    if (!confirmed) return;
    setSafetyHoldBusy(true); setSafetyHoldError('');
    try {
      await clearGpuSafetyHold();
      setStatus(previous => previous ? { ...previous, gpu_safety_hold: { termination_unknown: false } } : previous);
    } catch (cause) { setSafetyHoldError((cause as Error).message); }
    finally { setSafetyHoldBusy(false); }
  };
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      // These lightweight reads refresh live runtime/worker state. They do not
      // repeat ComfyUI object_info, model hashing, or the full workflow preflight.
      void Promise.all([getRuntimeGuard(), getWorkerDispatch(), getComfyQueueStatus()]).then(([guard, worker, queue]) => {
        setRuntime(guard); setWorkerReason(worker.reason || null);
        setStatus(previous => previous ? withCurrentReadiness({ ...previous, comfyui_queue: queue }, guard, worker) : previous);
      }).catch(() => {
        setStale(true);
        setStatus(previous => previous ? markStatusStale(previous) : previous);
        setRuntime(previous => previous ? { ...previous, monitor_available: false, safe_to_submit: false, reason: 'Runtime status is stale; refresh to confirm safety.' } : null);
        setError('Runtime monitor is unavailable; the last snapshot is shown as stale and generation is not confirmed.');
      });
      void getLocalJobQueueStatus().then(value => {
        setLocalQueue(value);
        setStatus(previous => previous ? { ...previous, local_queue: value } : previous);
      }).catch(() => {
        const unknown: LocalJobQueueStatus = { checked: false, pending: null, active: null, attention: null,
          reason: 'Vibe Director job queue could not be checked.', sources: [] };
        setLocalQueue(unknown);
        setStatus(previous => previous ? { ...previous, local_queue: unknown } : previous);
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
      {workflow.prompt_limit.unit !== 'not applicable' && textInputRoles(workflow).length > 0 && <span><b>{textInputRoles(workflow).some(role => /prompt|tags?|lyrics?/i.test(role)) ? 'Prompt limit' : 'Text input limit'}</b>{isKnownLimit(workflow) ? `≤ ${workflow.prompt_limit.max!.toLocaleString()} ${workflow.prompt_limit.unit}` : `Unknown (${workflow.prompt_limit.unit})`}</span>}
      {workflow.prompt_limit.basis && <span><b>Limit source</b>{workflow.prompt_limit.basis}</span>}
      {workflow.input_limits && Object.entries(workflow.input_limits).map(([name, limit]) => <span key={name}><b>{name.replaceAll('_', ' ')} limit</b>≤ {limit.max.toLocaleString()} {limit.unit}</span>)}
    </div>
    {workflow.input_contract && <details className="status-queue-details workflow-contract"><summary>Local input contract</summary><p>{workflow.input_contract}</p></details>}
    <div className="evidence-facts">
      {workflow.feature_enabled !== undefined && <span><b>Opt-in feature</b>{workflow.feature_enabled ? 'Enabled' : 'Disabled'}</span>}
      <span><b>Versioned graph</b>{workflow.graph_present == null ? 'Not checked' : workflow.graph_present ? 'Present' : 'Missing'}</span>
      {workflow.models && <span><b>Required models</b>{workflow.models.present} / {workflow.models.required} present</span>}
      {workflow.nodes && <span><b>Required nodes</b>{workflow.nodes.checked ? workflow.nodes.missing_count === 0 ? 'Checked · all present' : `${workflow.nodes.missing_count} missing` : 'Not checked · ComfyUI unavailable'}</span>}
      <span><b>Verified render</b>{workflow.render_verified ? 'Recorded by preflight' : 'Not confirmed'}</span>
      {workflow.automation_available !== undefined && <span><b>Full automation</b>{workflow.automation_available ? 'Available' : workflow.available ? 'Waiting for verified render' : 'Not ready'}</span>}
      <span><b>Your acceptance test</b>Not recorded</span>
    </div>
    {stale && workflow.workflow_id === 'minimax_h3_t2v_local_v1' && <p className="workflow-reason">Last reported: {workflow.workflow_reason || 'Workflow evidence shown below is from the last successful snapshot; current usability is unconfirmed.'}</p>}
    {workflow.reason && <p className="workflow-reason">{workflow.reason}</p>}
    {workflow.automation_available === false && workflow.automation_reason && <p className="workflow-reason">Full mode is still blocked: {workflow.automation_reason}</p>}
  </article>;

  return <div className="app-shell status-shell legacy-inner">
    <main className="main-content">
      <div className="content-wrap status-content"><div className="page-heading"><div><div className="eyebrow">WORKSPACE / STATUS</div><h1>Connections & workflows</h1></div><div className="top-actions"><span className="local-pill"><span className={`status-dot ${status?.backend.connected ? 'green' : ''}`}/> {loading && !status ? 'Loading status' : stale ? 'Status stale' : status?.backend.connected ? 'Backend connected' : 'Backend unavailable'}</span><button className="quiet-button status-refresh" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''}/> Refresh status</button></div></div>
        {error && <div className="notice notice-warn" role="alert">{error}</div>}
        {!status && <div className="card status-empty" role="status">{loading ? <><RefreshCw size={20} className="spin"/><b>Loading status</b><span>Checking backend and local workflow state…</span></> : <><XCircle size={20}/><b>Backend unavailable</b><span>Status could not be loaded. Refresh to try again. No workflow is assumed ready.</span></>}</div>}
        <DebugPanel/><PerformancePanel/>
        {status && <>
          {!hasCurrentStatusContract(status) && <div className="notice notice-warn" role="alert">The API response does not include the workflow and queue status fields this UI expects. Readiness may be incomplete; reconcile the API serving this page before relying on it.</div>}
          {stale && <div className="notice notice-warn" role="status">Showing last successful values as stale. Workflow readiness and GPU safety are unknown until status refresh succeeds.</div>}
          <section className="status-overview" aria-label="Runtime overview">
            <article className="status-metric card"><div className="metric-label"><Server size={15}/> Backend</div><strong className="metric-value"><span className={`status-dot ${status.backend.connected ? 'green' : 'red'}`}/>{status.backend.connected ? 'Connected' : stale ? 'Unknown · stale' : 'Unavailable'}</strong><small></small></article>
            <article className="status-metric card"><div className="metric-label"><Activity size={15}/> ComfyUI</div><strong className="metric-value"><span className={`status-dot ${status.comfyui.reachable ? 'green' : 'red'}`}/>{stale ? 'Unknown · stale' : status.comfyui.reachable ? 'Reachable' : 'Unreachable'}</strong><small>{stale ? `Last reported: ${status.comfyui.reason || (status.comfyui.reachable ? 'Node catalog reachable.' : 'Node catalog unreachable.')}` : status.comfyui.reason || 'Node catalog reachable.'}</small></article>
            <article className="status-metric card"><div className="metric-label"><Workflow size={15}/> Video worker</div><strong className="metric-value"><span className={`status-dot ${status.dispatch.available ? 'green' : 'red'}`}/>{stale ? 'Unknown · stale' : status.dispatch.available ? 'Dispatch available' : status.dispatch.worker_state.replaceAll('_', ' ')}</strong><small>{workerReason || 'Worker reports ready for explicitly requested jobs.'}</small></article>
            <article className="status-metric card"><div className="metric-label"><Activity size={15}/> ComfyUI queue</div><strong className="metric-value"><span className={`status-dot ${!stale && status.comfyui_queue?.checked && status.comfyui_queue.running === 0 && status.comfyui_queue.pending === 0 ? 'green' : 'red'}`}/>{stale || !status.comfyui_queue?.checked ? 'Unknown' : `${status.comfyui_queue.running} running · ${status.comfyui_queue.pending} pending`}</strong><small>{stale ? 'Queue status is stale; refresh to confirm.' : status.comfyui_queue?.reason || 'ComfyUI queue only. Vibe Director jobs may also be waiting in its own queue.'}</small></article>
            <article className="status-metric card"><div className="metric-label"><Activity size={15}/> Vibe Director jobs</div><strong className="metric-value"><span className={`status-dot ${!stale && localQueue?.checked && localQueue.pending === 0 && localQueue.active === 0 && localQueue.attention === 0 ? 'green' : 'red'}`}/>{stale || !localQueue?.checked ? 'Unknown' : `${localQueue.active} active · ${localQueue.pending} pending`}</strong><small>{stale ? 'Queue status is stale; refresh to confirm.' : !localQueue?.checked ? localQueue?.reason || 'One or more job stores could not be checked.' : `${localQueue.attention} needs attention across ${localQueue.sources.length} job stores.`}</small>{localQueue?.sources?.length ? <details className="status-queue-details"><summary>Queue breakdown</summary><ul>{localQueue.sources.map(source => <li key={source.id}><b>{({video_production:'Video production',image_production:'Image production',video_exports:'Video exports',media_prep:'Media Prep'})[source.id] || source.id}</b><span>{source.checked ? `${source.active} active · ${source.pending} pending · ${source.attention} attention` : source.reason || 'Unknown'}</span></li>)}</ul></details> : null}</article>
          </section>
          <section className="runtime-card card" aria-label="Workload scheduling">
            <h2>Workload scheduling</h2>
            <label><input type="checkbox" role="switch" checked={status.workload_policy?.allow_simultaneous_runs === true} disabled={stale || policyBusy || !status.workload_policy} onChange={event => void changeWorkloadPolicy(event.target.checked)}/> Allow simultaneous Vibe Director workloads</label>
            <p>{status.workload_policy?.allow_simultaneous_runs ? 'Vibe Director may run multiple of its own workloads together. Enable this only when your machine has enough capacity.' : 'One Vibe Director workload at a time across all workspaces. Generation, analysis, audio processing and export share a slot; waiting jobs do no processing or model loading.'}</p>
            <p>Default: off. Applies across workspaces and survives a restart. Change it when workloads are idle.</p>
            {!status.workload_policy && <p role="status">Restart the backend from this checkout to load workload scheduling.</p>}
            {policyBusy && <p role="status">Saving workload setting…</p>}
            {policyError && <p role="alert">{policyError}</p>}
          </section>
          {status.gpu_safety_hold?.termination_unknown && <section className="runtime-card card blocked" aria-label="GPU safety recovery" role="alert">
            <h2>GPU workload stopped with unknown termination</h2>
            <p>{status.gpu_safety_hold.reason || 'A workload may still be active.'}</p>
            <p>New Vibe Director GPU work is held until you verify the shared services are idle.</p>
            {status.gpu_safety_hold.recorded_at && <p>Recorded {new Date(status.gpu_safety_hold.recorded_at).toLocaleString()} · {status.gpu_safety_hold.workload_id}</p>}
            <p>Check the affected workload and shared Ollama or SAM service. Clear this hold only after confirming they are idle.</p>
            <button className="quiet-button" onClick={() => void recoverSafetyHold()} disabled={safetyHoldBusy || stale}>{safetyHoldBusy ? 'Clearing hold…' : 'I verified services are idle — clear hold'}</button>
            {safetyHoldError && <p role="alert">{safetyHoldError}</p>}
          </section>}
          <section className={`runtime-card card ${runtime?.monitor_available && runtime.safe_to_submit ? 'safe' : 'blocked'}`} aria-label="GPU runtime status"><div className="runtime-title"><Gauge size={18}/><div><h2>GPU safety monitor</h2><p>{runtime?.monitor_available && runtime.safe_to_submit ? 'GPU readings are within the configured operating limits.' : runtime?.reason || 'Runtime safety is not confirmed.'}</p><p className="runtime-scope-note">This checks GPU safety only. Workflow availability and a completed video render are shown separately below.</p></div><span className={`workflow-state ${runtime?.monitor_available && runtime.safe_to_submit ? 'usable' : 'unavailable'}`}>{runtime?.monitor_available && runtime.safe_to_submit ? 'GPU safe now' : 'generation blocked'}</span></div>
            <div className="runtime-values"><span><b>Current temperature</b>{runtime?.operating_point ? `${runtime.operating_point.temperature_c} °C` : 'Unavailable'}</span><span><b>Temperature cutoff</b>{runtime ? `${runtime.temperature_cutoff_c} °C` : '—'}</span><span><b>Graphics clock</b>{runtime?.operating_point ? `${runtime.operating_point.graphics_clock_mhz} MHz` : 'Unavailable'}</span><span><b>Clock ceiling</b>{runtime ? `${runtime.graphics_clock_ceiling_mhz} MHz` : '—'}</span></div>
            {!stale && runtime?.operating_point && Number.isFinite(runtime.graphics_clock_ceiling_mhz) && runtime.graphics_clock_ceiling_mhz > 0 && runtime.operating_point.graphics_clock_mhz > runtime.graphics_clock_ceiling_mhz && <aside className="gpu-clock-help" role="alert" aria-label="GPU clock limit guidance">
              <h3>Lower the GPU clock to continue</h3>
              <p>The GPU is running at {runtime.operating_point.graphics_clock_mhz} MHz. Vibe’s limit is {runtime.graphics_clock_ceiling_mhz} MHz, so new GPU jobs are blocked.</p>
              <p>Run this command in your PC’s terminal:</p>
              <div className="gpu-clock-command"><code>{`sudo nvidia-smi -i 0 --lock-gpu-clocks=0,${runtime.graphics_clock_ceiling_mhz}`}</code><button type="button" className="quiet-button" aria-label="Copy GPU clock command" title="Copy command" onClick={() => void copyClockCommand()}><Copy size={18} aria-hidden="true"/><span>Copy</span></button></div>
              {clockCopy && <p className="gpu-clock-copy-result" role="status">{clockCopy}</p>}
              <p>Then refresh Status, check runtime readiness and retry your job.</p>
              <details><summary>Command help and undo</summary>
                <p>Requires administrator access and driver support. This page does not run the command. If you see “Not Supported”, share that message.</p>
                <p>Check the clock:</p><code>nvidia-smi --query-gpu=clocks.current.graphics --format=csv,noheader</code>
                <p>Restore driver defaults:</p><code>sudo nvidia-smi -i 0 --reset-gpu-clocks</code>
                <p>Restoring defaults may put the clock above Vibe’s limit again.</p>
              </details>
            </aside>}
            <div className="runtime-admission" aria-label="GPU runtime readiness"><div><b>Runtime readiness</b><p>Checks runtime health and GPU operating limits. Reported free memory is informational; there is no fixed VRAM minimum. This check does not start a job.</p></div><button className="quiet-button" onClick={() => void checkGpuAdmission()} disabled={gpuAdmissionBusy}><RefreshCw size={14} className={gpuAdmissionBusy ? 'spin' : ''}/>{gpuAdmissionBusy ? 'Checking runtime…' : 'Check runtime readiness'}</button>{gpuAdmission && <div className="runtime-admission-result" role="status"><span className={`workflow-state ${gpuAdmission.available ? 'usable' : 'unavailable'}`}>{gpuAdmission.available ? 'Runtime ready' : 'Runtime blocked'}</span><span>{typeof gpuAdmission.free_gib === 'number' ? `${gpuAdmission.free_gib} GiB reported free (informational).` : gpuAdmission.available ? 'Free-memory reading unavailable (diagnostic only).' : gpuAdmission.reason || 'The runtime checks did not pass.'}</span>{gpuAdmission.host_memory && <small>Host memory context (informational only): {gpuAdmission.host_memory.available_gib} GiB available of {gpuAdmission.host_memory.total_gib} GiB RAM; {gpuAdmission.host_memory.swap_free_gib} GiB swap free. CPU and GPU share this memory on unified-memory systems.</small>}{gpuAdmission.checked_at && <small>Checked {new Date(gpuAdmission.checked_at).toLocaleTimeString()}</small>}</div>}{gpuAdmissionError && <p className="workflow-reason" role="alert">{gpuAdmissionError}</p>}</div>
          </section>
          <section className="status-catalog"><div className="section-title"><div><h2>Workflow catalog</h2><p>A ready workflow means its checks passed. It does not mean a video has been generated; look for “Verified render” on each workflow.</p></div></div>
            {groups.map(([category, title]) => { const rows = status.workflows.filter(workflow => workflow.category === category || (!workflow.category && category === 'video' && ['minimax_h3_t2v_local_v1', 'first_last_frame', 'reference_to_video'].includes(workflow.workflow_id))); return rows.length ? <div className="workflow-group" key={category}><h3>{title}</h3><div className="catalog-list">{rows.map(renderWorkflow)}</div></div> : null; })}
          </section>
          <p className="status-footnote"><Check size={14}/> Runtime updates every 5 seconds. Refresh to check workflows.</p>
        </>}
      </div>
    </main>
  </div>;
}
