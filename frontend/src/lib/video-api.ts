export const WORKFLOW_ID = 'minimax_h3_t2v_local_v1';
export const WORKFLOW_SHA256 = '4735e3662333493d488bc2ba6970810e620c13196ccac15b1155010e8cf3e1f9';
export type VideoRequest = {
  workflow_id: string; workflow_version: number; workflow_sha256: string;
  prompt: string; duration_seconds: number; aspect_ratio: '16:9';
  resolution_preset: 0.98 | 0.4; steps: 20; seed: 1; references: [];
};
export type Capability = { available: boolean; disabled_reason?: string | null; checks?: { id: string; ok: boolean; detail?: string }[]; settings?: Record<string, unknown>; dispatch?: { enabled: boolean; running: boolean; available: boolean; reason?: string | null }; runtime_guard?: { monitor_available: boolean; safe_to_submit: boolean; temperature_cutoff_c: number; graphics_clock_ceiling_mhz: number; operating_point?: { temperature_c: number; graphics_clock_mhz: number } | null; reason?: string | null } };
export type Job = {
  job_id: string; workspace_id?: string; clip_id?: string; status: string; request?: VideoRequest; request_snapshot?: VideoRequest;
  outputs?: { asset_id?: string; kind?: string; playback_url?: string; mock?: boolean }[];
  error?: { message?: string } | string | null; retake_of_job_id?: string | null; attempt?: number;
  keep_original?: boolean; progress?: { phase?: string; fraction?: number | null };
};
export class ApiError extends Error { constructor(message: string, readonly status: number) { super(message); } }
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body?.detail || body?.error?.message || `Backend returned ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}
export function getCapability() { return api<Capability>('/api/video/capabilities'); }
export function validateRequest(request: VideoRequest) { return api<any>('/api/video/validations', { method: 'POST', body: JSON.stringify({ request }) }); }
export function createJob(workspaceId: string, clipId: string, idempotencyKey: string, request: VideoRequest, retake?: { retake_of_job_id: string; keep_original: boolean }) {
  return api<Job>('/api/video/jobs', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ workspace_id: workspaceId, clip_id: clipId, idempotency_key: idempotencyKey, request, ...retake }) });
}
export function getJob(jobId: string) { return api<Job>(`/api/video/jobs/${encodeURIComponent(jobId)}`); }
export function prepareRetake(jobId: string, keepOriginal: boolean) { return api<any>(`/api/video/retakes/${encodeURIComponent(jobId)}`, { method: 'POST', body: JSON.stringify({ keep_original: keepOriginal }) }); }
export function acceptJob(jobId: string) { return api<Job>(`/api/video/jobs/${encodeURIComponent(jobId)}/accept`, { method: 'POST', body: JSON.stringify({}) }); }
export function findJobByIdempotency(workspaceId: string, idempotencyKey: string) {
  return api<Job>(`/api/video/jobs/by-idempotency/${encodeURIComponent(idempotencyKey)}?workspace_id=${encodeURIComponent(workspaceId)}`);
}
