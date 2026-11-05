import type { VideoResolution, VideoAspectRatio } from './video-quality';
export const WORKFLOW_ID = 'minimax_h3_t2v_local_v1';
export const WORKFLOW_SHA256 = 'b1c9292f4786baa4ace638b9bb9f455c42a9ed20a6bccb36cdb2b313cabf62d3';
export const FL2VA_WORKFLOW_ID = 'minimax_h3_fl2va_first_last_v1';
export const FL2VA_WORKFLOW_SHA256 = '575afcdef3a80e52828bdb4df07c0c5b27939d4dbc44d074aef665f3bad18fb0';
export const R2V_WORKFLOW_ID = 'minimax_h3_r2v_dynamic_v1';
export const R2V_WORKFLOW_SHA256 = '7c9f2ec6bed283f0b0b761370e7798fe155ee1b1e04feb12a0d91a05c516a6b4';
export type R2VImageReference = { asset_id: string; sha256: string; role: string; intent: string };
export type R2VVideoReference = R2VImageReference & { start_sec: number | null; end_sec: number | null; include_paired_soundtrack: boolean; audio_intent: string };
export type R2VAudioReference = R2VImageReference & ({ speaker_id: string | null } | { speaker_ids: string[] });
export type VideoRequest = {
  workflow_id: string; workflow_version: number; workflow_sha256: string;
  prompt: string; duration_seconds: number; aspect_ratio: VideoAspectRatio;
  resolution_preset: VideoResolution; source_resolution_preset?: VideoResolution; steps?: number; seed?: number; ref_image_size?: 'match'|'max'; references?: [];
  first_frame?: {asset_id: string; sha256: string}; last_frame?: {asset_id: string; sha256: string};
  images?: R2VImageReference[]; videos?: R2VVideoReference[]; audios?: R2VAudioReference[];
};
export type Capability = { workflow_id?: string; available: boolean; render_verified?: boolean; automation_available?: boolean; automation_disabled_reason?: string | null; disabled_reason?: string | null; checks?: { id: string; ok: boolean; detail?: string }[]; settings?: Record<string, unknown>; dispatch?: { enabled: boolean; running: boolean; available: boolean; reason?: string | null }; runtime_guard?: { monitor_available: boolean; safe_to_submit: boolean; temperature_cutoff_c: number; graphics_clock_ceiling_mhz: number; operating_point?: { temperature_c: number; graphics_clock_mhz: number } | null; reason?: string | null } };
export type Job = {
  pipeline?: {stage: string; original_ready: boolean; original_prompt_id?: string};
  job_id: string; workspace_id?: string; clip_id?: string; status: string; request?: VideoRequest; request_snapshot?: VideoRequest;
  source_lineage?: StoryVideoLineage | null; updated_at?: string; engine_prompt_id?: string | null;
  outputs?: { shared_asset_id?: string; sha256?: string; duration_seconds?: number; asset_id?: string; kind?: string; playback_url?: string; available?: boolean; mock?: boolean }[];
  error?: { message?: string } | string | null; retake_of_job_id?: string | null; attempt?: number;
  keep_original?: boolean; progress?: { phase?: string; fraction?: number | null };
  candidate_disposition?: 'keep' | 'discard_requested' | null;
};
export type StoryVideoLineage = { board_revision?: number; planned_clip_id?: string; screenplay_revision_id: string; setup_hash: string; scene_number: number; shot_number: number; workflow_id: string; source_prompt_sha256: string; knowledge_ref?: { knowledge_id: string; guidance_version: number; workflow_sha256: string }; style_ref?: { snapshot_id: string; style_version_id: string; narrative_hash: string; director_profile_hash: string; directing_style_hash: string } };
export class ApiError extends Error { constructor(message: string, readonly status: number, readonly admissionState?: string) { super(message); } }
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body?.detail || body?.error?.message || `Backend returned ${response.status}`, response.status, body?.admission_state);
  }
  return response.json() as Promise<T>;
}
export function getCapability(workflowId = WORKFLOW_ID, signal?: AbortSignal) { return api<Capability>(`/api/video/capabilities?workflow_id=${encodeURIComponent(workflowId)}`, { signal }); }
export function validateRequest(request: VideoRequest) { return api<any>('/api/video/validations', { method: 'POST', body: JSON.stringify({ request }) }); }
export function createJob(workspaceId: string, clipId: string, idempotencyKey: string, request: VideoRequest, retake?: { retake_of_job_id: string; keep_original: boolean }, sourceLineage?: Pick<StoryVideoLineage, 'screenplay_revision_id'|'setup_hash'|'scene_number'|'shot_number'|'source_prompt_sha256'|'knowledge_ref'|'style_ref'|'planned_clip_id'|'board_revision'>) {
  return api<Job>('/api/video/jobs', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ workspace_id: workspaceId, clip_id: clipId, idempotency_key: idempotencyKey, request, ...retake, ...(sourceLineage ? { source_lineage: sourceLineage } : {}) }) });
}
export function getJob(jobId: string) { return api<Job>(`/api/video/jobs/${encodeURIComponent(jobId)}`); }
export function listJobs(workspaceId: string, limit = 200, offset = 0) {
  return api<{ jobs: Job[] }>(`/api/video/jobs?workspace_id=${encodeURIComponent(workspaceId)}&limit=${encodeURIComponent(String(limit))}&offset=${encodeURIComponent(String(offset))}`);
}
export async function listAllJobs(workspaceId: string) {
  const jobs: Job[] = [];
  for (let offset = 0; ; offset += 200) {
    const page = await listJobs(workspaceId, 200, offset);
    jobs.push(...page.jobs);
    if (page.jobs.length < 200) return {jobs};
  }
}
export function prepareRetake(jobId: string, keepOriginal: boolean) { return api<any>(`/api/video/retakes/${encodeURIComponent(jobId)}`, { method: 'POST', body: JSON.stringify({ keep_original: keepOriginal }) }); }
export function acceptJob(jobId: string) { return api<Job>(`/api/video/jobs/${encodeURIComponent(jobId)}/accept`, { method: 'POST', body: JSON.stringify({}) }); }
export function findJobByIdempotency(workspaceId: string, idempotencyKey: string) {
  return api<Job>(`/api/video/jobs/by-idempotency/${encodeURIComponent(idempotencyKey)}?workspace_id=${encodeURIComponent(workspaceId)}`);
}
export function releaseVideoAttempt(workspaceId: string, idempotencyKey: string) {
  return api<{released:boolean;job?:Job}>('/api/video/attempts/release', {method:'POST', body:JSON.stringify({workspace_id:workspaceId,idempotency_key:idempotencyKey})});
}

export function prepareContinuityFrame(jobId: string) { return api<{asset_id:string;sha256:string;role:string;intent:string;character_crops?:{character_id:string;asset_id:string;sha256:string}[]}>(`/api/video/jobs/${encodeURIComponent(jobId)}/continuity-frame`, {method:"POST",body:"{}"}); }

export type T2VBatchEntry = {number:string|number; filename?:string; request:VideoRequest; job_id:string|null; job?:Job; job_missing?:boolean};
export type T2VBatch = {batch_id:string; workspace_id:string; state:string; reason?:string; completed:number; entries:T2VBatchEntry[]};
export const validateT2VBatch = (source:string,workspaceId:string) => api<{entries:T2VBatchEntry[];count:number;conflicts:string[]}>('/api/video/batches/validate', {method:'POST',body:JSON.stringify({source,workspace_id:workspaceId})});
export const listT2VBatches = (workspaceId:string) => api<{batches:T2VBatch[]}>(`/api/video/batches?workspace_id=${encodeURIComponent(workspaceId)}`);
export const createT2VBatch = (workspaceId:string,idempotencyKey:string,source:string,choices:Record<string,'overwrite'|'new_take'>={}) => api<T2VBatch>('/api/video/batches', {method:'POST',body:JSON.stringify({workspace_id:workspaceId,idempotency_key:idempotencyKey,source,choices})});
export const controlT2VBatch = (id:string,action:'pause'|'resume'|'stop') => api<T2VBatch>(`/api/video/batches/${id}/control`, {method:'POST',body:JSON.stringify({action})});
