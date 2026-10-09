import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ArrowRight, BookOpen, Check, ChevronDown, Film, FolderOpen, Gauge, Image, LoaderCircle, Play, RefreshCw, Sparkles, WandSparkles, X } from 'lucide-react';
import { acceptJob, ApiError, Capability, createJob, findJobByIdempotency, getCapability, getJob, Job, prepareRetake, validateRequest, VideoRequest, WORKFLOW_ID, WORKFLOW_SHA256 } from './lib/video-api';
import StatusPage from './StatusPage';
import StoryPage from './StoryPage';
import ScreenplayPage from './ScreenplayPage';
import './screenplay.css';
import ProductionStylesPage from './ProductionStylesPage';
import StudioShell, { StudioRoute } from './StudioShell';

type Draft = { prompt: string; duration: number; resolution: 0.98 | 0.4; workspaceId: string; clipId: string; pendingKey?: string; pendingRequest?: VideoRequest; retakeOf?: string; keepOriginal?: boolean };
const DRAFT_KEY = 'vibe-video-draft-v1';
const ACTIVE_KEY = 'vibe-video-active-job-v1';
const HISTORY_KEY = 'vibe-video-history-v1';
const unicodeLength = (s: string) => Array.from(s).length;
const id = () => crypto.randomUUID();
const defaultDraft = (): Draft => ({ prompt: '', duration: 6, resolution: 0.98, workspaceId: id(), clipId: id() });
const readDraft = (): Draft => { try { return { ...defaultDraft(), ...JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}') }; } catch { return defaultDraft(); } };
const readActive = (): { jobId: string; snapshot: VideoRequest; retakeOf?: string; keepOriginal?: boolean } | null => { try { return JSON.parse(localStorage.getItem(ACTIVE_KEY) || 'null'); } catch { return null; } };
const savedActive = readActive();
const TERMINAL_STATUSES = new Set(['needs_review','accepted','failed','rejected','stale','cancelled']);
const isTerminalStatus = (status?: string) => !!status && TERMINAL_STATUSES.has(status);
const isReviewable = (status?: string) => status === 'needs_review' || status === 'accepted';
const readHistory = () => { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') as { job: Job; snapshot: VideoRequest }[]; } catch { return []; } };
const openTakeIfOnVideo = () => { if (window.location.hash.split('?')[0] === '#/video') window.location.hash = '#/take'; };

function VideoWorkspace({ view='create' }: { view?: 'create'|'take' }) {
  const [draft, setDraftState] = useState<Draft>(readDraft);
  const [active, setActive] = useState<{ job: Job; snapshot: VideoRequest; retakeOf?: string; keepOriginal?: boolean } | null>(null);
  const [history, setHistory] = useState<{ job: Job; snapshot: VideoRequest }[]>(readHistory);
  const [capability, setCapability] = useState<Capability | null>(null);
  const [capState, setCapState] = useState<'idle'|'loading'|'ready'|'unavailable'>('idle');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [retakeDialog, setRetakeDialog] = useState(false);
  const [retakeKeep, setRetakeKeep] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const hasPendingAttempt = Boolean(draft.pendingKey || draft.pendingRequest);
  const activeUnresolved = Boolean(active && !isTerminalStatus(active.job.status));

  const setDraft = useCallback((update: (prev: Draft) => Draft) => setDraftState(prev => { const next = update(prev); localStorage.setItem(DRAFT_KEY, JSON.stringify(next)); return next; }), []);
  const promptLength = unicodeLength(draft.prompt);
  const errors = useMemo(() => ({ prompt: !draft.prompt.trim() ? 'Add a prompt to describe the shot.' : promptLength >= 7000 ? 'Prompt must be fewer than 7,000 characters.' : '', duration: draft.duration < 5 || draft.duration > 10 ? 'Choose 5 to 10 seconds.' : '' }), [draft.prompt, draft.duration, promptLength]);

  const refreshCapability = async () => {
    setCapState('loading'); setMessage('Checking local T2V workflow readiness…');
    try { const value = await getCapability(); setCapability(value); const safe = value.runtime_guard?.safe_to_submit === true; const dispatch = value.dispatch?.available === true; setCapState(value.available && safe && dispatch ? 'ready' : 'unavailable'); setMessage(!value.available ? value.disabled_reason || 'Local T2V workflow is unavailable.' : !safe ? value.runtime_guard?.reason || 'GPU safety admission has not confirmed the runtime is safe.' : !dispatch ? value.dispatch?.reason || 'The isolated video worker is disabled or unavailable.' : 'Local T2V workflow, GPU admission and worker are ready.'); }
    catch (e) { setCapability(null); setCapState('unavailable'); setMessage(`Backend unavailable: ${String((e as Error).message)}. Your draft is saved on this device.`); }
  };
  useEffect(() => { let alive = true; const resume = async () => { if (savedActive?.jobId) { setActive({ job: { job_id: savedActive.jobId, status: 'recovery_required' }, snapshot: savedActive.snapshot, retakeOf: savedActive.retakeOf, keepOriginal: savedActive.keepOriginal }); try { const job = await getJob(savedActive.jobId); if (alive) { setActive({ job, snapshot: savedActive.snapshot, retakeOf: savedActive.retakeOf, keepOriginal: savedActive.keepOriginal }); openTakeIfOnVideo(); } } catch (e) { if (alive) { const missing = e instanceof ApiError && e.status === 404; setMessage(missing ? `Saved job ${savedActive.jobId} was not found. Its reference and frozen prompt are preserved; no replacement job can start until it is reconciled.` : `Could not reconnect to saved job ${savedActive.jobId}. Its reference and frozen prompt are preserved; no replacement job can start until it is reconciled.`); } } return; } const pending = readDraft(); if (pending.pendingKey && pending.pendingRequest) { try { const job = await findJobByIdempotency(pending.workspaceId, pending.pendingKey); if (!alive) return; localStorage.setItem(ACTIVE_KEY, JSON.stringify({ jobId: job.job_id, snapshot: pending.pendingRequest, retakeOf: pending.retakeOf, keepOriginal: pending.keepOriginal })); setActive({ job, snapshot: pending.pendingRequest, retakeOf: pending.retakeOf, keepOriginal: pending.keepOriginal }); const cleared = { ...pending, pendingKey: undefined, pendingRequest: undefined }; localStorage.setItem(DRAFT_KEY, JSON.stringify(cleared)); setDraftState(cleared); setMessage('Recovered the saved job by its idempotency key. No new job was submitted.'); openTakeIfOnVideo(); } catch (e) { if (alive) setMessage(`Saved attempt could not be reconciled: ${(e as Error).message}. The immutable request and key remain saved; no job was submitted during reload.`); } } }; void resume(); return () => { alive = false; }; }, []);
  useEffect(() => { if (!active || isTerminalStatus(active.job.status)) return; const timer = window.setInterval(() => { getJob(active.job.job_id).then(job => setActive(prev => prev?.job.job_id === job.job_id ? { ...prev, job } : prev)).catch(() => setMessage('Connection interrupted. The same saved job will be checked again; no new job was submitted.')); }, 2500); return () => window.clearInterval(timer); }, [active?.job.job_id, active?.job.status]);

  const makeRequest = (): VideoRequest => ({ workflow_id: WORKFLOW_ID, workflow_version: 1, workflow_sha256: WORKFLOW_SHA256, prompt: draft.prompt, duration_seconds: draft.duration, aspect_ratio: '16:9', resolution_preset: draft.resolution, steps: 20, seed: 1, references: [] });
  const generate = async () => {
    if (busy) return;
    if (errors.prompt || errors.duration) { setMessage(errors.prompt || errors.duration); return; }
    setBusy(true); setMessage('');
    try {
      // Every explicit Generate click rechecks workflow and GPU admission.
      const cap = await getCapability(); setCapability(cap);
      const safe = cap.runtime_guard?.safe_to_submit === true; const dispatch = cap.dispatch?.available === true;
      setCapState(cap.available && safe && dispatch ? 'ready' : 'unavailable');
      if (!cap.available || !safe || !dispatch) throw new Error(!cap.available ? cap.disabled_reason || 'Local workflow is not ready. The draft stays editable.' : !safe ? cap.runtime_guard?.reason || 'GPU safety admission is unavailable. Generation is blocked; the draft stays editable.' : cap.dispatch?.reason || 'The isolated video worker is disabled or unavailable.');
      if (active && !isTerminalStatus(active.job.status)) throw new Error(`Job ${active.job.job_id} is still ${active.job.status.replaceAll('_',' ')}. Its saved request is preserved; wait for it to settle before starting another job.`);

      let frozen = draft.pendingRequest;
      let attemptKey = draft.pendingKey;
      if (Boolean(frozen) !== Boolean(attemptKey)) throw new Error('Saved attempt data is incomplete. Its local record is preserved; no new job was submitted.');
      if (frozen && attemptKey) {
        try {
          const recovered = await findJobByIdempotency(draft.workspaceId, attemptKey);
          localStorage.setItem(ACTIVE_KEY, JSON.stringify({ jobId: recovered.job_id, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal }));
          setActive({ job: recovered, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal });
          const cleared = { ...draft, pendingKey: undefined, pendingRequest: undefined, retakeOf: undefined, keepOriginal: undefined };
          localStorage.setItem(DRAFT_KEY, JSON.stringify(cleared)); setDraftState(cleared);
          setMessage('Recovered the saved job by its idempotency key. No new job was submitted.');
          openTakeIfOnVideo();
          return;
        } catch (e) { if (!(e instanceof ApiError) || e.status !== 404) throw e; }
      } else {
        frozen = makeRequest();
        attemptKey = id();
      }
      if (!frozen || !attemptKey) throw new Error('Could not prepare a saved generation attempt.');
      const validation = await validateRequest(frozen);
      if (validation.valid === false) throw new Error(validation.issues?.map((i: any) => i.message).join(' ') || 'The backend rejected these settings.');
      // Persist the immutable payload and key before the only job-creating POST.
      const savedAttempt = { ...draft, pendingKey: attemptKey, pendingRequest: frozen };
      localStorage.setItem(DRAFT_KEY, JSON.stringify(savedAttempt)); setDraftState(savedAttempt);
      const retake = draft.retakeOf ? { retake_of_job_id: draft.retakeOf, keep_original: draft.keepOriginal !== false } : undefined;
      const job = await createJob(draft.workspaceId, draft.clipId, attemptKey, frozen, retake);
      if (active && isTerminalStatus(active.job.status) && active.job.job_id !== job.job_id) { const nextHistory = [{ job: active.job, snapshot: active.snapshot }, ...history.filter(h => h.job.job_id !== active.job.job_id)]; setHistory(nextHistory); localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory)); }
      const nextActive = { job, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal };
      localStorage.setItem(ACTIVE_KEY, JSON.stringify({ jobId: job.job_id, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal }));
      setActive(nextActive); setMessage('Job saved. Progress will resume from this job if you reload.');
      openTakeIfOnVideo();
      const cleared = { ...draft, pendingKey: undefined, pendingRequest: undefined, retakeOf: undefined, keepOriginal: undefined };
      localStorage.setItem(DRAFT_KEY, JSON.stringify(cleared)); setDraftState(cleared);
    } catch (e) { setMessage((e as Error).message || 'Could not create job. The same saved attempt will be reused if the response was lost.'); }
    finally { setBusy(false); }
  };
  const startRetake = async () => { if (!active) return; const source = active; setBusy(true); try { const result = await prepareRetake(source.job.job_id, retakeKeep); if (result.submission_created !== false) throw new Error('Backend did not confirm that the retake is only a draft.'); const request = result.request as VideoRequest; setDraft(prev => ({ ...prev, workspaceId: source.job.workspace_id || prev.workspaceId, clipId: source.job.clip_id || prev.clipId, prompt: request.prompt, duration: request.duration_seconds, resolution: request.resolution_preset, pendingKey: undefined, pendingRequest: undefined, retakeOf: source.job.job_id, keepOriginal: result.keep_original })); if (isReviewable(source.job.status)) { const nextHistory = [{ job: source.job, snapshot: source.snapshot }, ...history.filter(h => h.job.job_id !== source.job.job_id)]; setHistory(nextHistory); localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory)); } localStorage.removeItem(ACTIVE_KEY); setActive(null); setRetakeDialog(false); setMessage(`Retake draft prepared. ${result.keep_original ? 'The current candidate will be kept.' : 'Deletion is requested for this generated candidate only.'} Nothing has been generated yet.`); window.location.hash = '#/video'; } catch (e) { setMessage(`Could not prepare retake: ${(e as Error).message}`); } finally { setBusy(false); } };
  const isReviewableOutput = isReviewable(active?.job.status);
  const needsReview = active?.job.status === 'needs_review';
  const activeRequest = active?.job.request || active?.job.request_snapshot || active?.snapshot;
  const output = active?.job.outputs?.find(o => o.kind === 'video');
  const playback = output?.playback_url ? (/^https?:\/\//.test(output.playback_url) ? output.playback_url : `${window.location.origin}${output.playback_url}`) : '';
  const statusLabel = !active ? 'Draft' : active.job.status.replaceAll('_', ' ');
  const markAccepted = async () => { if (!active) return; setBusy(true); try { const job = await acceptJob(active.job.job_id); setActive({ ...active, job }); setMessage('Take acceptance saved.'); } catch (e) { setMessage(`Could not save acceptance: ${(e as Error).message}`); } finally { setBusy(false); } };
  
  return <div className={`app-shell legacy-inner legacy-video-inner ${view==='take'?'take-inner':''}`}>
    <main className="main-content">
      <div className="content-wrap"><div className="page-heading"><div><div className="eyebrow">STUDIO / VIDEO</div><h1>{view==='take'?'Current take':'Create video'}</h1><p>{view==='take'?'Review your take.':''}</p></div><button className="quiet-button" onClick={() => { const next = defaultDraft(); setDraftState(next); localStorage.setItem(DRAFT_KEY, JSON.stringify(next)); setMessage(activeUnresolved ? `New draft created. Existing job ${active?.job.job_id} remains active and must settle before another job can start.` : 'New local draft created. Current take and history are preserved.'); }} disabled={hasPendingAttempt}><span>＋</span> New draft</button></div>
      {message && <div className={`notice ${message.toLowerCase().includes('unavailable') || message.toLowerCase().includes('error') || message.toLowerCase().includes('could not') ? 'notice-warn' : ''}`} role="status"><span>{message}</span><button onClick={() => setMessage('')} aria-label="Dismiss"><X size={15}/></button></div>}
      <div className="layout-grid"><section className="composer-column"><div className="section-title"><div><h2>Create a video</h2></div><span className="mode-pill"><Sparkles size={13}/> Text to video</span></div>
        <div className="mode-switch"><button className="mode-option selected"><Film size={16}/><span><b>Text to video</b><small>Prompt only</small></span><Check size={15} className="mode-check"/></button><button className="mode-option off" disabled title="Not integrated yet"><Image size={16}/><span><b>First + last frame</b><small>Not integrated yet</small></span></button><button className="mode-option off" disabled title="Not integrated yet"><FolderOpen size={16}/><span><b>Reference to video</b><small>Not integrated yet</small></span></button></div>
        <div className="card prompt-card"><div className="card-header"><div><label htmlFor="prompt">Shot prompt</label><p>Describe the action and camera movement.</p></div><span className="saved"><span className="status-dot green"/> Auto-saved</span></div>
          <textarea id="prompt" value={draft.prompt} onChange={e => setDraft(p => ({ ...p, prompt: e.target.value }))} disabled={hasPendingAttempt} placeholder="Example: A slow dolly toward a rain-streaked window as amber city lights shimmer outside…" aria-describedby="prompt-help prompt-count" maxLength={8000}/>
          <div className="prompt-footer"><div className="annotation-row"><span className="unavailable-edit" title="Codex editing is not connected"><WandSparkles size={14}/> AI editing unavailable</span></div><div className="prompt-meta"><span id="prompt-help" className="sr-only">Describe the video to generate.</span><span id="prompt-count" className={promptLength >= 7000 ? 'count error-text' : 'count'}>{promptLength.toLocaleString()} / 6,999</span></div></div>
          {errors.prompt && draft.prompt && <div className="inline-error" role="alert">{errors.prompt}</div>}
        </div>
        <div className="card settings-card"><div className="card-header"><div><h3>Output settings</h3></div><button className="collapse-button" onClick={() => setShowAdvanced(s => !s)} aria-expanded={showAdvanced}>Advanced <ChevronDown size={15} className={showAdvanced?'rotated':''}/></button></div>
          <div className="setting-grid"><div className="field"><label htmlFor="duration">Duration</label><div className="select-wrap"><select id="duration" value={draft.duration} disabled={hasPendingAttempt} onChange={e => setDraft(p => ({ ...p, duration: Number(e.target.value) }))}>{Array.from({length:6}, (_,i) => i+5).map(n => <option value={n} key={n}>{n} seconds</option>)}</select><ChevronDown size={15}/></div>{errors.duration && <small className="error-text">{errors.duration}</small>}</div><div className="field"><label htmlFor="resolution">Quality</label><div className="select-wrap"><select id="resolution" value={draft.resolution} disabled={hasPendingAttempt} onChange={e => setDraft(p => ({ ...p, resolution: Number(e.target.value) as 0.98|0.4 }))}><option value={0.98}>High · 1344 × 768</option><option value={0.4}>Standard · 864 × 480</option></select><ChevronDown size={15}/></div></div><div className="field"><label>Aspect ratio</label><div className="static-value">16:9 <span>Widescreen</span></div></div></div>
          {showAdvanced && <div className="advanced-row"><span>Steps <b>20</b></span><span>Seed <b>1</b></span><span>References <b>None</b></span><small>Fixed settings</small></div>}
        </div>
        <div className="video-readiness card"><div className="small-heading">LOCAL ENGINE <span className={`status-dot ${capState==='ready'?'green':capState==='unavailable'?'red':''}`}/></div><p>{capState==='ready' ? 'Workflow + GPU + worker ready' : capState==='loading' ? 'Checking readiness…' : capState==='unavailable' ? 'Unsafe or unavailable' : 'Not checked'}</p><button className="text-button" onClick={refreshCapability} disabled={capState==='loading'}><Activity size={14}/> Check readiness</button></div>
        <div className="generation-footer"><button className="generate-button" onClick={generate} disabled={busy || !!errors.prompt || !!errors.duration || capState!=='ready' || activeUnresolved}>{busy ? <><LoaderCircle size={16} className="spin"/> Preparing…</> : hasPendingAttempt ? <><RefreshCw size={16}/> Recover saved attempt</> : <><Sparkles size={16}/> Generate video <ArrowRight size={16}/></>}</button></div>
        {hasPendingAttempt && <div className="notice notice-warn" role="status"><span>The saved request and idempotency key are locked until the backend reconciles them. Check readiness, then use Recover saved attempt; the UI will look up that key before any retry.</span></div>}
      </section>
      <aside className="result-column"><div className="section-title result-title"><div><h2>Current take</h2><p>Job status and output for this draft.</p></div><button className="icon-button" aria-label="Refresh job" disabled={!active} onClick={() => active && getJob(active.job.job_id).then(job => setActive({ ...active, job })).catch(() => setMessage('Could not refresh job status.'))}><RefreshCw size={16}/></button></div>
        <div className={`preview card ${isReviewableOutput && playback ? 'has-video' : ''}`}>{isReviewableOutput && playback ? <video controls playsInline src={playback} aria-label="Generated video"/> : <div className="preview-empty"><div className="preview-icon">{active ? ['recovery_required','submission_unknown'].includes(active.job.status) ? <Activity size={24}/> : <LoaderCircle size={24} className={['queued','running','submitting','reconciling'].includes(active.job.status)?'spin':''}/> : <Play size={23}/>}</div><b>{active ? active.job.status === 'needs_review' ? 'Ready to review' : active.job.status === 'accepted' ? 'Take accepted' : active.job.status === 'failed' ? 'Generation failed' : active.job.status === 'stale' ? 'Job is stale' : active.job.status === 'cancelled' ? 'Job was cancelled' : active.job.status === 'rejected' ? 'Job was rejected' : ['recovery_required','submission_unknown','reconciling'].includes(active.job.status) ? 'Recovery required' : ['queued','running','submitting'].includes(active.job.status) ? 'Rendering your shot' : `Status: ${active.job.status}` : 'Your video preview'}</b><span>{active ? (active.job.error && typeof active.job.error==='object' ? active.job.error.message : '') || (isReviewableOutput ? 'This job is reviewable, but the backend did not return a playable output URL.' : ['recovery_required','submission_unknown','reconciling'].includes(active.job.status) ? 'The backend is reconciling this saved job. No new job will be submitted.' : active.job.status === 'stale' ? 'The backend marked this job stale. Its request is preserved; no completed output is confirmed.' : active.job.status === 'cancelled' ? 'The backend confirmed cancellation. No completed output is confirmed.' : active.job.status === 'rejected' ? 'The backend rejected this job. Its request remains available in history.' : `Job ${active.job.job_id}`) : 'Your generated video will appear here.'}</span>{active && !isTerminalStatus(active.job.status) && <div className="progress-track"><span className={typeof active.job.progress?.fraction === 'number' ? '' : 'indeterminate'} style={typeof active.job.progress?.fraction === 'number' ? { width: `${Math.max(0,Math.min(100,active.job.progress.fraction*100))}%` } : undefined}/></div>}</div>}<div className="preview-controls"><span><span className={`status-dot ${isReviewableOutput?'green':''}`}/>{statusLabel}</span>{active?.job.attempt && <span>Take {active.job.attempt}</span>}</div></div>
        {active && activeRequest && <div className="snapshot card"><div className="snapshot-head"><div><span className="eyebrow">SAVED REQUEST</span><b>Submitted prompt</b></div><span className="snapshot-lock">Frozen</span></div><p>{activeRequest.prompt}</p><div className="snapshot-tags"><span>{activeRequest.duration_seconds}s</span><span>{activeRequest.resolution_preset===0.98?'1344 × 768':'864 × 480'}</span><span>16:9</span><span>Seed 1</span></div>{active.retakeOf && <small>Retake of {active.retakeOf} · {active.keepOriginal ? 'original candidate kept' : 'deletion requested for this candidate only'}</small>}</div>}
        {isReviewableOutput && <div className="review-actions">{needsReview && <button className="accept-button" onClick={markAccepted} disabled={busy}><Check size={16}/> Accept take</button>}<button className="retake-button" onClick={() => { setRetakeKeep(true); setRetakeDialog(true); }} disabled={busy}><RefreshCw size={15}/> Retake</button><span>{needsReview ? 'Accepting records this take for a later workflow step.' : 'This accepted take remains available while you prepare a retake.'}</span></div>}
        {active?.job.status === 'accepted' && <div className="accepted-status"><Check size={15}/> Accepted and saved</div>}
        {history.length > 0 && <div className="history-list"><h3>Previous takes <span>{history.length}</span></h3>{history.map(item => { const vid = item.job.outputs?.find(o => o.kind === 'video'); const url = vid?.playback_url ? (/^https?:\/\//.test(vid.playback_url) ? vid.playback_url : `${window.location.origin}${vid.playback_url}`) : ''; return <details className="history-item" key={item.job.job_id}><summary><span className="status-dot green"/> Take {item.job.attempt || '—'} · {item.snapshot.duration_seconds}s <span className="history-job">{item.job.job_id}</span></summary><p>{item.snapshot.prompt}</p>{url && <video controls playsInline src={url} aria-label={`Previous take ${item.job.attempt || ''}`}/>}</details>; })}</div>}
        <div className="workflow-note"><Gauge size={16}/><div><b>Local workflow readiness</b><p>{!capability ? 'Readiness is not checked. Generation stays disabled until workflow, GPU safety and worker dispatch checks pass.' : `${!capability.dispatch?.available ? capability.dispatch?.reason || 'Video worker dispatch is disabled or unavailable.' : capability.runtime_guard?.reason || (capability.runtime_guard?.safe_to_submit ? 'H3 T2V and GPU safety checks passed.' : 'GPU safety monitor unavailable.')} Current: ${capability.runtime_guard?.operating_point ? `${capability.runtime_guard.operating_point.temperature_c}°C / ${capability.runtime_guard.operating_point.graphics_clock_mhz} MHz` : 'telemetry unavailable'}. Limits: ${capability.runtime_guard?.temperature_cutoff_c ?? '—'}°C / ${capability.runtime_guard?.graphics_clock_ceiling_mhz ?? '—'} MHz.`}</p><button className="text-button" onClick={refreshCapability} disabled={capState==='loading'}>Check status</button></div></div>
      </aside></div></div>
    </main>
    {retakeDialog && <div className="dialog-backdrop" role="presentation"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="retake-title"><button className="dialog-close" onClick={() => setRetakeDialog(false)} aria-label="Close"><X size={17}/></button><div className="dialog-icon"><RefreshCw size={20}/></div><h2 id="retake-title">Prepare a retake</h2><p>The prompt and settings return to the editor. This only records candidate retention intent; it does not start a job or delete anything.</p><fieldset><legend>Current candidate</legend><label className="radio-option"><input type="radio" checked={retakeKeep} onChange={() => setRetakeKeep(true)}/> Keep this take</label><label className="radio-option"><input type="radio" checked={!retakeKeep} onChange={() => setRetakeKeep(false)}/> Request deletion of this generated candidate only</label><small className="dialog-footnote">The backend reports candidate disposition after retake. Shared and source assets are not candidates for deletion.</small></fieldset><div className="dialog-actions"><button className="quiet-button" onClick={() => setRetakeDialog(false)}>Cancel</button><button className="generate-button" onClick={startRetake} disabled={busy}>Return to editor <ArrowRight size={15}/></button></div></section></div>}
  </div>;
}

export default function App() {
  const parseRoute = (): StudioRoute => { const route = (window.location.hash.split('?')[0].replace(/^#\/?/, '') || 'home') as StudioRoute; return ['home','styles','story','screenplay','setup','prompts','video','take','assets','media','status'].includes(route) ? route : 'home'; };
  const [route, setRoute] = useState<StudioRoute>(parseRoute);
  useEffect(() => {
    const onHashChange = () => setRoute(parseRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  // Keep the video workspace mounted while Status is open so a running job,
  // pending recovery key, and editor state continue untouched in memory.
  const context = 'Video draft · no story linked';
  const unavailable = route==='setup' ? ['Automation & Parameters','Automation is not available yet.'] : route==='prompts' ? ['Prompts','Prompt preparation is not available yet.'] : route==='assets' ? ['Assets','Assets are not available yet.'] : route==='media' ? ['Media Prep & Library','Media tools are not available yet.'] : null;
  return <StudioShell route={route} context={context}>
    {route==='home' && <div className="content-wrap home-content"><div className="page-heading"><div><div className="eyebrow">LOCAL STUDIO</div><h1>What would you like to make?</h1></div></div><div className="entry-cards"><a className="entry-card" href="#/story"><span className="entry-icon"><BookOpen size={20}/></span><b>Develop a story</b><p>Write, upload, or edit your story.</p><span className="entry-cta">Open Story <span>→</span></span></a><a className="entry-card" href="#/video"><span className="entry-icon"><Film size={20}/></span><b>Create a video</b><p>Generate a video from a prompt.</p><span className="entry-cta">Open Video <span>→</span></span></a></div></div>}
    {route==='story' && <><StoryPage/><div className="content-wrap story-video-entry"><section className="card"><div><b>Create a separate video</b><p>This story is not linked to video generation yet.</p></div><a className="generate-button" href="#/video">Open Video <ArrowRight size={15}/></a></section></div></>}
    {route==='screenplay' && <ScreenplayPage/>}
    {route==='status' && <StatusPage/>}
    {route==='styles' && <ProductionStylesPage/>}
    <div className="video-workspace-mount" style={{display:route==='video'||route==='take'?'contents':'none'}} aria-hidden={route==='video'||route==='take'?undefined:true}><VideoWorkspace view={route==='take'?'take':'create'}/></div>
    {unavailable && <div className="content-wrap unavailable-content"><div className="page-heading"><div><div className="eyebrow">COMING SOON</div><h1>{unavailable[0]}</h1><p>{unavailable[1]}</p></div></div><section className="card unavailable-card"><div className="unavailable-links"><a className="quiet-button" href="#/story">Story source editor</a><a className="generate-button" href="#/video">Text to video</a><a className="quiet-button" href="#/status">Status</a></div></section></div>}
  </StudioShell>;
}
