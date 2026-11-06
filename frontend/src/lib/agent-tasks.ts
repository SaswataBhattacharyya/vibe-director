import type {MediaAsset} from './media-api';
import type {EditorTarget} from '../DirectorEditor';
export type AgentTask = {
  project_id: string; task_id: string; status: string; current_revision: number; plan_hash: string;
  plan: {tool_id: string; scope: string; assets: Array<{asset_id: string; filename: string; sha256: string}>; settings: {quality?: number; instruction?: string; access_mode?: 'project' | 'full'; workspace_path?: string; model?: string; target?: EditorTarget}};
  invocation: {invocation_id: string; job_id: string | null; state: string} | null;
  events: Array<{sequence: number; event_type: string; created_at: string}>;
  outputs?: MediaAsset[]; job_status?: string; report?: string;
};
export type AgentMessage = {request_id: string; text: string; reply: string; status: string; task_id: string | null};
export async function agentRequest<T>(workspace: string, resource: string, signal: AbortSignal, body?: unknown, computerToken?: string): Promise<T> {
  const response = await fetch(`/api/agent/projects/${encodeURIComponent(workspace)}/${resource}`, {
    signal, ...(body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', ...(computerToken ? {'X-Vibe-Computer-Token': computerToken} : {})}, body: JSON.stringify(body)}),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value?.error?.message || 'Director request failed.');
  if (value.workspace_id && value.workspace_id !== workspace || value.project_id && value.project_id !== workspace) {
    throw new Error('Director returned a different project.');
  }
  return value;
}
export const exactApproval = (task: AgentTask) => ({revision: task.current_revision, plan_hash: task.plan_hash});

export async function computerGrant(signal: AbortSignal): Promise<string> {
  const response = await fetch('/api/agent/computer-access', {signal});
  const value = await response.json();
  if (!response.ok || !value.available || !value.session_token) throw new Error(value?.error?.message || 'Installed Codex computer runtime is unavailable.');
  return value.session_token;
}
