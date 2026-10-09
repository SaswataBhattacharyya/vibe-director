export type RuntimeGuard = {
  monitor_available: boolean; safe_to_submit: boolean; temperature_cutoff_c: number;
  graphics_clock_ceiling_mhz: number; operating_point?: { temperature_c: number; graphics_clock_mhz: number } | null;
  reason?: string | null;
};
export type StatusWorkflow = {
  workflow_id: string; label: string; category?: string; version?: number;
  state: 'usable' | 'unavailable' | 'not_integrated'; available: boolean; workflow_available?: boolean; workflow_reason?: string | null; reason?: string | null;
  feature_enabled?: boolean; graph_present?: boolean; models?: { present: number; required: number };
  nodes?: { checked: boolean; missing_count: number }; input_roles: string[];
  duration_seconds?: { min: number; max: number; unit: string };
  outputs?: { preset: number; width: number; height: number }[];
  fixed_parameters?: Record<string, string | number>;
  prompt_limit: { max?: number | null; value?: number | null; unit: string; basis?: string; reason?: string };
};
export type WorkflowStatus = {
  schema_version: number; backend: { connected: boolean }; comfyui: { reachable: boolean; reason?: string | null };
  runtime_guard: RuntimeGuard; dispatch: { enabled: boolean; running: boolean; available: boolean; worker_state: string; reason?: string | null };
  workflows: StatusWorkflow[];
};
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
