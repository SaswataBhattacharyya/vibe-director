export type RuntimeGuard = {
  monitor_available: boolean; safe_to_submit: boolean; temperature_cutoff_c: number;
  graphics_clock_ceiling_mhz: number; operating_point?: { temperature_c: number; graphics_clock_mhz: number } | null;
  reason?: string | null;
};
export type ComfyQueueStatus = { checked: boolean; running: number | null; pending: number | null; reason?: string | null };
export type LocalJobQueueStatus = {
  checked: boolean; pending: number | null; active: number | null; attention: number | null; reason?: string;
  sources: Array<{ id: string; checked: boolean; pending?: number; active?: number; attention?: number; reason?: string }>;
};
export type HostMemoryDiagnostic = { total_gib: number; available_gib: number; swap_total_gib: number; swap_free_gib: number };
export type GpuAdmission = { available: boolean; checked: boolean; free_gib?: number | null; required_gib?: number; checked_at?: string; reason?: string | null; host_memory?: HostMemoryDiagnostic | null };
export type StatusWorkflow = {
  workflow_id: string; label: string; category?: string; version?: number;
  state: 'usable' | 'unavailable' | 'not_integrated' | 'not_checked'; available: boolean; workflow_available?: boolean; workflow_reason?: string | null; worker_available?: boolean; worker_reason?: string | null; reason?: string | null;
  feature_enabled?: boolean; graph_present?: boolean | null; models?: { present: number; required: number } | null;
  render_verified?: boolean; acceptance?: 'not_recorded'; automation_available?: boolean; automation_reason?: string | null;
  nodes?: { checked: boolean; missing_count: number }; input_roles: string[];
  duration_seconds?: { min: number; max: number; unit: string };
  outputs?: { preset: number; width: number; height: number }[];
  fixed_parameters?: Record<string, string | number>;
  prompt_limit: { max?: number | null; value?: number | null; unit: string; basis?: string; reason?: string };
  input_limits?: Record<string, { max: number; unit: string; basis: string }>;
  input_contract?: string;
};
export type WorkloadPolicy = { allow_simultaneous_runs: boolean };
export type GpuSafetyHold = { termination_unknown: boolean; recorded_at?: string; workload_id?: string; reason?: string };
export type WorkflowStatus = {
  workload_policy?: WorkloadPolicy;
  gpu_safety_hold?: GpuSafetyHold;
  schema_version: number; backend: { connected: boolean }; comfyui: { reachable: boolean; reason?: string | null };
  comfyui_queue?: ComfyQueueStatus;
  local_queue?: LocalJobQueueStatus;
  runtime_guard: RuntimeGuard; dispatch: { enabled: boolean; running: boolean; available: boolean; worker_state: string; reason?: string | null };
  workflows: StatusWorkflow[];
};
export async function getComfyQueueStatus(): Promise<ComfyQueueStatus> {
  const response = await fetch('/api/comfyui/queue', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`ComfyUI queue request failed (${response.status}).`);
  return response.json();
}
export async function getLocalJobQueueStatus(): Promise<LocalJobQueueStatus> {
  const response = await fetch('/api/jobs/queue', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Vibe Director queue request failed (${response.status}).`);
  return response.json();
}
export async function getWorkflowStatus(): Promise<WorkflowStatus> {
  const response = await fetch('/api/status', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Status request failed (${response.status}).`);
  return response.json();
}
export async function getRuntimeGuard(): Promise<RuntimeGuard> {
  const response = await fetch('/api/video/runtime', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Runtime monitor request failed (${response.status}).`);
  return response.json();
}
export async function getWorkerDispatch(): Promise<WorkflowStatus['dispatch']> {
  const response = await fetch('/api/video/worker', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Worker status request failed (${response.status}).`);
  return response.json();
}
export async function getGpuAdmission(): Promise<GpuAdmission> {
  const response = await fetch('/api/video-summariser/capabilities?check_gpu_admission=1', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Runtime readiness check failed (${response.status}).`);
  const value = await response.json();
  if (!value.gpu_admission?.checked) throw new Error('The connected API does not provide runtime readiness checks. Restart the Vibe Director backend from this checkout, then recheck.');
  return value.gpu_admission as GpuAdmission;
}

export async function setWorkloadPolicy(allowSimultaneousRuns: boolean): Promise<WorkloadPolicy> {
  const response = await fetch('/api/runtime/workload-policy', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ allow_simultaneous_runs: allowSimultaneousRuns }),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error?.message || `Workload setting could not be saved (${response.status}).`);
  return value;
}

export async function clearGpuSafetyHold(): Promise<{ cleared: boolean }> {
  const response = await fetch('/api/runtime/safety-hold', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ verified_idle: true }),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error?.message || `GPU safety hold could not be cleared (${response.status}).`);
  return value;
}
