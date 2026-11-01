import { useState } from 'react';
import { LoaderCircle } from 'lucide-react';
import { qualityDimensions } from './lib/video-quality';
import type { Job } from './lib/video-api';
import './run-clip-live.css';

function ReferenceImage({ url, label }: { url: string; label: string }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return failedUrl === url ? <p role="status">{label}: preview unavailable. The saved reference ID is shown below.</p>
    : <a href={url} target="_blank" rel="noreferrer"><img src={url} alt={label} loading="lazy" onError={() => setFailedUrl(url)}/></a>;
}

/** Read-only view of the frozen request, never draft or inferred reference media. */
export default function RunClipLiveView({ job, workspaceId }: { job: Job; workspaceId: string }) {
  const request = job.request ?? job.request_snapshot;
  const workspace = job.workspace_id || workspaceId;
  const mediaUrl = (assetId: string) => `/api/media/${encodeURIComponent(workspace)}/assets/${encodeURIComponent(assetId)}/content`;
  const waiting = ['queued', 'pending', 'preparing', 'submitting', 'submitted', 'running', 'recovering', 'refinement_pending'].includes(job.status);
  const missing = job.outputs?.some(output => output.kind === 'video' && output.available === false);
  const phase = missing ? 'Video file missing' : job.status === 'refinement_pending' ? 'Waiting for LTX video refinement' : job.status === 'running' ? job.pipeline?.stage === 'ltx_refinement' ? 'Refining final video with LTX' : 'Generating video'
    : job.status === 'queued' ? 'Queued for generation'
    : job.status === 'recovery_required' ? 'Checking the saved job; connection recovery is required'
    : job.status === 'needs_review' || job.status === 'accepted' ? 'Video ready'
    : job.status.replaceAll('_', ' ');
  const images = [
    ...(request?.first_frame ? [{ ...request.first_frame, label: 'First frame', role: 'first frame', intent: '' }] : []),
    ...(request?.last_frame ? [{ ...request.last_frame, label: 'Last frame', role: 'last frame', intent: '' }] : []),
    ...(request?.images ?? []).map((ref, index) => ({ ...ref, label: `Picture ${index + 1}` })),
  ];
  return <section className="run-clip-live" aria-label="Live clip details">
    <p className="run-clip-phase" role="status">{waiting && <LoaderCircle className="run-clip-spinner" size={20} aria-hidden="true"/>}{phase}</p>
    {missing && <p>The generated file was removed or is unavailable. The saved prompt and run history are preserved; no replacement generation has started.</p>}
    {job.updated_at && <small>Job updated: {job.updated_at}</small>}
    {!request ? <p>The saved request has not been received yet. It will appear on the next status update.</p> : <>
      <p>Prepared · {request.workflow_id} · {request.duration_seconds}s · {qualityDimensions(request.resolution_preset, request.aspect_ratio)} final. References and prompt below are the submitted request.</p>
      <div className="run-clip-references">
        {images.map(ref => <figure key={`${ref.label}:${ref.asset_id}`}>
          <ReferenceImage url={mediaUrl(ref.asset_id)} label={`${ref.label} · ${ref.role}`}/>
          <figcaption><strong>{ref.label} · {ref.role}</strong><p>{ref.intent}</p><small>{ref.asset_id}</small></figcaption>
        </figure>)}
      </div>
      {!images.length && <p>No image references attached to this clip.</p>}
      {!request.images?.some(ref => ref.role === 'character_identity') && <p>No character crop attached to this request. A pending visibility review is not an attached reference.</p>}
      {(request.videos ?? []).map((ref, index) => <figure key={`video:${ref.asset_id}`}><video controls preload="none" src={mediaUrl(ref.asset_id)} aria-label={`Video reference ${index + 1}`}/><figcaption>Video {index + 1} · {ref.role} · {ref.intent}</figcaption></figure>)}
      {(request.audios ?? []).map((ref, index) => <figure key={`audio:${ref.asset_id}`}><audio controls preload="none" src={mediaUrl(ref.asset_id)} aria-label={`Audio reference ${index + 1}`}/><figcaption>Audio {index + 1} · {ref.role} · {ref.intent}</figcaption></figure>)}
      <details open={waiting}><summary>Exact submitted prompt</summary><pre>{request.prompt}</pre></details>
    </>}
    {waiting && <p>Progress refreshes automatically. The completed video appears here after output validation.</p>}
  </section>;
}
