import type {MediaAsset} from './media-api';
import type {EditorTarget} from '../DirectorEditor';
import type {VideoPromptProposal, VideoPromptTarget} from '../DirectorVideo';
import type {StudioProposal} from '../DirectorStudio';
import type {ImageProposal} from '../DirectorImage';
import type {StoryTarget} from '../DirectorStory';
export type AgentTask = {
  project_id: string; task_id: string; status: string; current_revision: number; plan_hash: string;
  plan: {tool_id: string; scope: string; assets: Array<{asset_id: string; filename: string; sha256: string}>; settings: {name?: string; quality?: number; dry?: number; stems?: number; device?: 'cpu'; instruction?: string; access_mode?: 'project' | 'full'; workspace_path?: string; model?: string; target?: EditorTarget}};
  invocation: {invocation_id: string; job_id: string | null; state: string} | null;
  events: Array<{sequence: number; event_type: string; created_at: string}>;
  outputs?: MediaAsset[]; job_status?: string; report?: string;
};
export type DirectorGoal = {request_id: string; objective: string; status: string;
  state: {phase: string; progress: string; stop_reason: string | null; authorization: string; dependencies: string[]};
  steps: Array<{tool: string; task_id: string | null; status: string}>};
export type AgentMessage = {request_id: string; text: string; reply: string; status: string; task_id: string | null; goal?: DirectorGoal; attachments?: Array<{asset_id:string;filename:string;sha256:string}>; story_target?: StoryTarget; video_target?: VideoPromptTarget; proposal?: ImageProposal | VideoPromptProposal | StudioProposal};
export async function agentRequest<T>(workspace: string, resource: string, signal: AbortSignal, body?: unknown, computerToken?: string): Promise<T> {
  const response = await fetch(`/api/agent/projects/${encodeURIComponent(workspace)}/${resource}`, {
    signal, ...(body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', ...(computerToken ? {'X-Vibe-Computer-Token': computerToken} : {})}, body: JSON.stringify(body)}),
  });
  const value = await response.json();
  if (!response.ok) {
    const message = value?.error?.message;
    if (resource === 'conversation' && message === 'Supply request_id, text, asset_ids, skill_refs and surface.' && body && typeof body === 'object' && 'target' in body) {
      throw new Error('The running backend is older than this Director interface and cannot accept creative-tool context. Let active jobs finish, restart Vibe Director using its launcher, then send this message again. Your draft has been kept.');
    }
    throw new Error(message || 'Director request failed.');
  }
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
