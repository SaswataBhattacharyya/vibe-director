import OutputDestination from './OutputDestination';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { listStoryScreenplays } from './lib/story-api';
import { listMediaAssets, type MediaAsset } from './lib/media-api';

type Take = { job_id: string; created_at?: string; outputs: Array<{ playback_url: string }> };
type Clip = { clip_id?: string; scene_number: number; shot_number: number; clip_number: number; accepted_takes: Take[]; review_takes: Take[]; missing_accepted_take: boolean };
type Preview = { screenplay_revision_id: string; clips: Clip[]; missing_clip_count: number; planning_incomplete: boolean; warnings: string[] };
type AudioTrack = { asset_id: string; sha256: string; start_seconds: number; trim_start_seconds: number; trim_end_seconds: number; gain: number };
type AssemblySnapshot = { snapshot_id:string; snapshot_sha256:string; created_at:string; snapshot:{state:string} };
type ExportManifest = { manifest_id:string; manifest_sha256:string; created_at:string; manifest:{state:string;export_settings:Record<string,unknown>} };
type ExportJob = { job_id:string; manifest_id:string; state:string; progress_percent:number; error?:string|null; output_asset_id?:string|null; created_at:string };

export default function AssemblyPreviewPanel() {
  const [workspaceId, setWorkspaceId] = useState('');
  const [destinationReady,setDestinationReady]=useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectionSaved, setSelectionSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showAudioLibrary, setShowAudioLibrary] = useState(false);
  const [audioAssets, setAudioAssets] = useState<MediaAsset[]>([]);
  const [audioTracks, setAudioTracks] = useState<AudioTrack[]>([]);
  const [audioSaved, setAudioSaved] = useState(false);
  const [audioSaving, setAudioSaving] = useState(false);
  const [audioError, setAudioError] = useState('');
  const [snapshots, setSnapshots] = useState<AssemblySnapshot[]>([]);
  const [snapshotSaving, setSnapshotSaving] = useState(false);
  const [snapshotError, setSnapshotError] = useState('');
  const [exportManifests, setExportManifests] = useState<ExportManifest[]>([]);
  const [exportSettings, setExportSettings] = useState({resolution:'1080p',frame_rate:24,quality:22,audio_policy:'preserve_and_mix'});
  const [manifestSaving, setManifestSaving] = useState(false);
  const [manifestError, setManifestError] = useState('');
  const [exportJobs, setExportJobs] = useState<ExportJob[]>([]);
  const [exportActionError, setExportActionError] = useState('');

  const load = useCallback(async () => {
    const id = localStorage.getItem('vibe-story-selected-v1') || '';
    setWorkspaceId(id);
    setPreview(null);
    setSelected({});
    setSelectionSaved(false);
    setShowAudioLibrary(false);
    setAudioAssets([]);
    setAudioTracks([]);
    setAudioSaved(false);
    setAudioError('');
    setSnapshots([]);
    setExportManifests([]);
    setExportJobs([]);
    setSnapshotError('');
    setError('');
    setNotice('');
    if (!id) return;
    setLoading(true);
    try {
      const page = await listStoryScreenplays(id, 0, 50);
      const accepted = page.items.find(item => item.accepted && !item.stale);
      if (!accepted) { setNotice('Accept a screenplay before assembling its clips.'); return; }
      const response = await fetch(`/api/story/workspaces/${encodeURIComponent(id)}/assembly-preview?screenplay_revision_id=${encodeURIComponent(accepted.screenplay_revision_id)}`);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || body?.error?.message || `Could not load clips (${response.status}).`);
      setPreview(body as Preview);
      const savedResponse = await fetch(`/api/story/workspaces/${encodeURIComponent(id)}/assembly-selection?screenplay_revision_id=${encodeURIComponent(accepted.screenplay_revision_id)}`);
      const savedBody = await savedResponse.json().catch(() => ({}));
      if (!savedResponse.ok) throw new Error(savedBody?.detail || savedBody?.error?.message || `Could not load saved clip choices (${savedResponse.status}).`);
      setSelected(savedBody.selections && typeof savedBody.selections === 'object' ? savedBody.selections : {});
      setSelectionSaved(true);
      try {
        const [library, audioResponse, snapshotResponse, exportResponse, jobResponse] = await Promise.all([
          listMediaAssets(id, 'audio'),
          fetch(`/api/story/workspaces/${encodeURIComponent(id)}/assembly-audio?screenplay_revision_id=${encodeURIComponent(accepted.screenplay_revision_id)}`),
          fetch(`/api/story/workspaces/${encodeURIComponent(id)}/assembly-snapshots?screenplay_revision_id=${encodeURIComponent(accepted.screenplay_revision_id)}`),
          fetch(`/api/story/workspaces/${encodeURIComponent(id)}/assembly-exports?screenplay_revision_id=${encodeURIComponent(accepted.screenplay_revision_id)}`),
          fetch(`/api/story/workspaces/${encodeURIComponent(id)}/assembly-export-jobs?screenplay_revision_id=${encodeURIComponent(accepted.screenplay_revision_id)}`),
        ]);
        const audioBody = await audioResponse.json().catch(() => ({}));
        if (!audioResponse.ok) throw new Error(audioBody?.detail || audioBody?.error?.message || `Could not load audio choices (${audioResponse.status}).`);
        const snapshotBody = await snapshotResponse.json().catch(() => ({}));
        if (!snapshotResponse.ok) throw new Error(snapshotBody?.detail || snapshotBody?.error?.message || `Could not load assembly snapshots (${snapshotResponse.status}).`);
        const exportBody = await exportResponse.json().catch(() => ({}));
        if (!exportResponse.ok) throw new Error(exportBody?.detail || exportBody?.error?.message || `Could not load export manifests (${exportResponse.status}).`);
        const jobBody = await jobResponse.json().catch(() => ({}));
        if (!jobResponse.ok) throw new Error(jobBody?.detail || jobBody?.error?.message || `Could not load export jobs (${jobResponse.status}).`);
        setAudioAssets(library.assets);
        setAudioTracks(Array.isArray(audioBody.audio_tracks) ? audioBody.audio_tracks : []);
        setSnapshots(Array.isArray(snapshotBody.snapshots) ? snapshotBody.snapshots : []);
        setExportManifests(Array.isArray(exportBody.manifests) ? exportBody.manifests : []);
        setExportJobs(Array.isArray(jobBody.jobs) ? jobBody.jobs : []);
        setAudioSaved(true); setAudioError('');
      } catch (err) { setAudioError(err instanceof Error ? err.message : String(err)); }
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setLoading(false); }
  }, []);

  const saveSelection = async () => {
    if (!preview || !workspaceId || saving) return;
    setSaving(true); setError('');
    try {
      const response = await fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/assembly-selection`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screenplay_revision_id: preview.screenplay_revision_id, selections: selected }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || body?.error?.message || `Could not save clip choices (${response.status}).`);
      setSelected(body.selections || selected); setSelectionSaved(true);
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setSaving(false); }
  };

  const saveAudio = async () => {
    if (!preview || !workspaceId || audioSaving) return;
    setAudioSaving(true); setAudioError('');
    try {
      const response = await fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/assembly-audio`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screenplay_revision_id: preview.screenplay_revision_id, audio_tracks: audioTracks }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || body?.error?.message || `Could not save audio tracks (${response.status}).`);
      setAudioTracks(body.audio_tracks || audioTracks); setAudioSaved(true);
    } catch (err) { setAudioError(err instanceof Error ? err.message : String(err)); }
    finally { setAudioSaving(false); }
  };

  const saveSnapshot = async () => {
    if (!preview || !workspaceId || snapshotSaving || !complete || !selectionSaved || !audioSaved) return;
    setSnapshotSaving(true); setSnapshotError('');
    try {
      const response = await fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/assembly-snapshots`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({screenplay_revision_id:preview.screenplay_revision_id, selections:selected}),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || body?.error?.message || `Could not freeze assembly choices (${response.status}).`);
      setSnapshots(current => current.some(item => item.snapshot_id === body.snapshot_id) ? current : [body, ...current]);
    } catch (err) { setSnapshotError(err instanceof Error ? err.message : String(err)); }
    finally { setSnapshotSaving(false); }
  };

  const prepareExport = async (snapshotId: string) => {
    if (!preview || !workspaceId || manifestSaving) return;
    setManifestSaving(true); setManifestError('');
    try {
      const response = await fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/assembly-exports`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({screenplay_revision_id:preview.screenplay_revision_id,snapshot_id:snapshotId,settings:exportSettings}),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || body?.error?.message || `Could not prepare export (${response.status}).`);
      setExportManifests(current => current.some(item => item.manifest_id === body.manifest_id) ? current : [body, ...current]);
    } catch (err) { setManifestError(err instanceof Error ? err.message : String(err)); }
    finally { setManifestSaving(false); }
  };

  const startExport = async (manifestId: string) => {
    if (!preview || !workspaceId) return;
    setExportActionError('');
    try {
      const response = await fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/assembly-export-jobs`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({screenplay_revision_id:preview.screenplay_revision_id,manifest_id:manifestId}),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || body?.error?.message || `Could not queue export (${response.status}).`);
      setExportJobs(current => [body, ...current.filter(job => job.job_id !== body.job_id)]);
    } catch (err) { setExportActionError(err instanceof Error ? err.message : String(err)); }
  };

  const hasActiveExportJobs = exportJobs.some(job => ['queued','rendering'].includes(job.state));
  useEffect(() => {
    if (!preview || !workspaceId || !hasActiveExportJobs) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/assembly-export-jobs?screenplay_revision_id=${encodeURIComponent(preview.screenplay_revision_id)}`);
        const body = await response.json();
        if (response.ok) setExportJobs(Array.isArray(body.jobs) ? body.jobs : []);
      } catch { /* Keep the last durable status visible until the next poll. */ }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [preview, workspaceId, hasActiveExportJobs]);

  const addAudioTrack = (asset: MediaAsset) => {
    const duration = asset.media?.duration_seconds;
    if (audioTracks.some(track => track.asset_id === asset.asset_id)) return;
    if (typeof duration !== 'number' || duration <= 0) { setAudioError(`${asset.filename} has no verified duration and cannot be placed yet.`); return; }
    setAudioTracks(current => [...current, { asset_id: asset.asset_id, sha256: asset.sha256,
      start_seconds: 0, trim_start_seconds: 0, trim_end_seconds: duration, gain: 1 }]);
    setAudioSaved(false); setAudioError('');
  };

  useEffect(() => { void load(); }, [load]);
  const complete = useMemo(() => !!preview && !preview.planning_incomplete && preview.clips.length > 0
    && preview.clips.every(clip => Boolean(selected[clip.clip_id || `${clip.scene_number}.${clip.shot_number}.${clip.clip_number}`])), [preview, selected]);

  return <section className="card assembly-preview" aria-label="Assemble story clips">
    <header className="assembly-preview-head"><div><span className="eyebrow">EXPORT</span><h2>Assemble story clips</h2><p>Choose one accepted take for every clip, in screenplay order.</p></div><button className="quiet-button" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button></header>
    {!workspaceId && <p>Select a story in the Story workspace to assemble its clips.</p>}
    {loading && <p role="status">Loading screenplay clips…</p>}
    {notice && <p>{notice}</p>}
    {error && <p role="alert">{error}</p>}
    {preview && <>
      {preview.warnings.map(warning => <p className="assembly-warning" key={warning}>{warning}</p>)}
      <div className="assembly-clip-list">{preview.clips.map(clip => {
        const key = clip.clip_id || `${clip.scene_number}.${clip.shot_number}.${clip.clip_number}`;
        return <article className="assembly-clip" key={key}>
          <div className="assembly-clip-heading"><b>Scene {clip.scene_number} · Shot {clip.shot_number} · Clip {clip.clip_number}</b>{clip.accepted_takes.length === 0 && <span>Needs an accepted take</span>}</div>
          {clip.accepted_takes.map(take => <label className="assembly-take-option" key={take.job_id}>
            <input type="radio" name={`assembly-${key}`} value={take.job_id} checked={selected[key] === take.job_id} onChange={() => { setSelected(current => ({ ...current, [key]: take.job_id })); setSelectionSaved(false); }}/>
            <span>Take {take.job_id.slice(0, 8)}{take.created_at ? ` · ${new Date(take.created_at).toLocaleString()}` : ''}</span>
            <video muted playsInline preload="metadata" src={take.outputs[0]?.playback_url}/>
          </label>)}
          {clip.review_takes.length > 0 && <small>{clip.review_takes.length} take{clip.review_takes.length === 1 ? '' : 's'} still need acceptance.</small>}
        </article>;
      })}</div>
      <section className="assembly-audio" aria-label="Optional audio tracks">
        <div className="assembly-audio-head"><div><h3>Optional audio tracks</h3><p>Clip audio is preserved. Added tracks are mixed over it after an explicit selection.</p></div><button className="quiet-button" onClick={() => void saveAudio()} disabled={audioSaving || loading || audioSaved}>{audioSaving ? 'Saving…' : audioSaved ? 'Audio saved' : 'Save audio choices'}</button></div>
        {audioError && <p role="alert">{audioError}</p>}
        <button className="quiet-button" aria-expanded={showAudioLibrary} onClick={() => setShowAudioLibrary(current => !current)}>{showAudioLibrary ? 'Hide audio library' : 'Add an optional audio track'}</button>
        {showAudioLibrary && (audioAssets.length === 0 ? <p>No audio files are saved in this workspace yet.</p> : <div className="assembly-audio-library">{audioAssets.map(asset => <article key={asset.asset_id} className="assembly-audio-asset"><audio controls preload="none" src={asset.content_url}/><span title={asset.filename}>{asset.filename}</span><small>{asset.audio_category || 'Audio'}{asset.media?.duration_seconds ? ` · ${asset.media.duration_seconds.toFixed(1)} s` : ''}</small><button className="quiet-button" onClick={() => addAudioTrack(asset)} disabled={audioTracks.some(track => track.asset_id === asset.asset_id)}>Add</button></article>)}</div>)}
        {audioTracks.map((track, index) => {
          const asset = audioAssets.find(item => item.asset_id === track.asset_id);
          const update = (field: keyof AudioTrack, value: number) => { setAudioTracks(current => current.map((item, i) => i === index ? {...item, [field]: value} : item)); setAudioSaved(false); };
          return <article className="assembly-audio-track" key={track.asset_id}>
            <b>{asset?.filename || track.asset_id}</b><button className="text-button" onClick={() => { setAudioTracks(current => current.filter((_, i) => i !== index)); setAudioSaved(false); }}>Remove</button>
            <label>Starts at (s)<input type="number" min="0" step="0.1" value={track.start_seconds} onChange={event => update('start_seconds', Number(event.target.value))}/></label>
            <label>Trim in (s)<input type="number" min="0" step="0.1" value={track.trim_start_seconds} onChange={event => update('trim_start_seconds', Number(event.target.value))}/></label>
            <label>Trim out (s)<input type="number" min="0" step="0.1" max={asset?.media?.duration_seconds} value={track.trim_end_seconds} onChange={event => update('trim_end_seconds', Number(event.target.value))}/></label>
            <label>Level<input type="number" min="0" max="2" step="0.05" value={track.gain} onChange={event => update('gain', Number(event.target.value))}/></label>
          </article>;
        })}
      </section>
      <footer className="assembly-preview-footer"><span>{Object.keys(selected).length} of {preview.clips.length} clips selected{selectionSaved ? ' · Saved' : ' · Unsaved'}</span><div><button className="quiet-button" onClick={() => void saveSelection()} disabled={saving || loading || selectionSaved}>{saving ? 'Saving…' : 'Save choices'}</button></div></footer>
      <section className="assembly-snapshots" aria-label="Frozen assembly choices">
        <div><h3>Frozen assembly choices</h3><p>Saves the selected takes and audio instructions as an immutable snapshot. Export settings are still required before rendering.</p></div>
        {snapshotError && <p role="alert">{snapshotError}</p>}
        <button className="quiet-button" onClick={() => void saveSnapshot()} disabled={snapshotSaving || !complete || !selectionSaved || !audioSaved}>{snapshotSaving ? 'Saving…' : 'Freeze assembly choices'}</button>
        {snapshots.map(snapshot => <article key={snapshot.snapshot_id}><b>{snapshot.snapshot_id}</b><span>{snapshot.snapshot.state.replaceAll('_', ' ')} · {new Date(snapshot.created_at).toLocaleString()}</span><code>{snapshot.snapshot_sha256}</code></article>)}
      </section>
      <section className="assembly-snapshots" aria-label="Export settings and manifest">
        <div><h3>Export settings</h3><p>Choose the output profile and audio treatment. Preparing a manifest does not start rendering.</p></div>
        <OutputDestination tool="assembly-export" workspaceId={workspaceId} onReady={setDestinationReady}/>
        <label>Resolution<select value={exportSettings.resolution} onChange={event => setExportSettings(current => ({...current,resolution:event.target.value}))}><option value="720p">720p</option><option value="1080p">1080p</option><option value="1440p">1440p</option></select></label>
        <label>Frame rate<select value={exportSettings.frame_rate} onChange={event => setExportSettings(current => ({...current,frame_rate:Number(event.target.value)}))}><option value={24}>24 fps</option><option value={30}>30 fps</option><option value={60}>60 fps</option></select></label>
        <label>H.264 quality (CRF)<input type="number" min="18" max="28" step="1" value={exportSettings.quality} onChange={event => setExportSettings(current => ({...current,quality:Number(event.target.value)}))}/></label>
        <label>Audio treatment<select value={exportSettings.audio_policy} onChange={event => setExportSettings(current => ({...current,audio_policy:event.target.value}))}><option value="preserve_and_mix">Keep clip audio and mix selected tracks</option><option value="selected_tracks_only">Use selected tracks only</option><option value="mute">Mute all audio</option></select></label>
        {manifestError && <p role="alert">{manifestError}</p>}
        {snapshots.map(snapshot => <button className="quiet-button" key={snapshot.snapshot_id} onClick={() => void prepareExport(snapshot.snapshot_id)} disabled={manifestSaving}>{manifestSaving ? 'Preparing…' : `Prepare export from ${snapshot.snapshot_id.slice(0,16)}`}</button>)}
        {exportActionError && <p role="alert">{exportActionError}</p>}
        {exportManifests.map(manifest => {
          const job = exportJobs.find(item => item.manifest_id === manifest.manifest_id);
          return <article key={manifest.manifest_id}><b>{manifest.manifest_id}</b><span>{manifest.manifest.state.replaceAll('_', ' ')}{job ? ` · ${job.state}` : ''}</span><code>{manifest.manifest_sha256}</code>
            {job?.state === 'queued' && <small role="status">Waiting for the export worker.</small>}
            {job?.state === 'rendering' && <><small role="status">Rendering export… {job.progress_percent}%</small><progress aria-label="Export rendering" value={job.progress_percent} max={100}/></>}
            {!job && <button className="generate-button" disabled={!destinationReady} onClick={() => void startExport(manifest.manifest_id)}>Render export</button>}
            {job?.state === 'failed' && <><p role="alert">{job.error || 'Export failed.'}</p><button className="quiet-button" onClick={() => void fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/assembly-export-jobs/${encodeURIComponent(job.job_id)}/retry`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({screenplay_revision_id:preview.screenplay_revision_id})}).then(async response => { const body=await response.json(); if (!response.ok) throw new Error(body?.detail || 'Retry failed.'); setExportJobs(current=>current.map(item=>item.job_id===job.job_id?body:item)); }).catch(err=>setExportActionError(err instanceof Error?err.message:String(err)))}>Retry</button></>}
            {job?.state === 'completed' && job.output_asset_id && <div className="assembly-export-result">
              <video controls preload="metadata" src={`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(job.output_asset_id)}/content`}/>
              <a className="quiet-button" href={`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(job.output_asset_id)}/content`} download="vibe-director-export.mp4">Download MP4</a>
            </div>}
          </article>;
        })}
      </section>
      <p className="assembly-note">{complete ? 'Accepted clips are ready to render in screenplay order.' : 'Select one accepted take for each clip.'}</p>
    </>}
  </section>;
}
