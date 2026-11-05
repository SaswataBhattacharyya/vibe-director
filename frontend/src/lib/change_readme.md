# Frontend typed client change README

**Edit targets:** NEW `agent-api.ts`, `agent-context.ts`; existing `editor-api.ts`, `video-api.ts`, `storyboard-api.ts`, `media-api.ts` should remain authoritative for their domains. Use generated/API-validated types when available.

## New `agent-api.ts` — narrow fetch client
This is an **illustrative skeleton**, not a claim the endpoint exists yet. Finalize with matching `backend/story_builder/services/agent_api.py` and tests.

```ts
export type ToolStatus = 'available'|'blocked'|'navigation_only';
export type ToolInfo = {
  id: string; status: ToolStatus; reason?: string;
  input_schema: Record<string, unknown>; kinds: string[];
};
export type TaskStatus =
  | 'draft'|'awaiting_approval'|'approved'|'running'
  | 'blocked'|'paused'|'verifying'|'completed'|'failed'|'cancelled';
export type AgentTask = {
  task_id: string; project_id: string; plan_revision: number;
  plan_sha256: string; status: TaskStatus;
  steps: Array<{step_id:string; tool_id:string; status:string; job_id?:string}>;
};
async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init, headers: {'Content-Type':'application/json', ...(init?.headers || {})}
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || `Agent request failed (${response.status})`);
  return data as T;
}
const root = (id:string) => `/api/agent/projects/${encodeURIComponent(id)}`;
export const listAgentTools = (id:string) =>
  req<{tools:ToolInfo[]}>(`/api/agent/tools?workspace_id=${encodeURIComponent(id)}`);
export const getAgentTask = (id:string,task:string) =>
  req<AgentTask>(`${root(id)}/tasks/${encodeURIComponent(task)}`);
export const proposeAgentTask = (id:string,proposal:unknown) =>
  req<AgentTask>(`${root(id)}/tasks`,{
    method:'POST', body:JSON.stringify(proposal)
  });
```

Add `approveAgentTask` and `controlAgentTask` only with exact server-side expected revision/hash, approval scope, and idempotency input. Do **not** add an unsafe generic `POST /api/agent/exec` that accepts arbitrary commands.

## New `agent-context.ts` — stable handoff
Proposed common context (adapt to existing session/project APIs, don't use browser strings as authority):

```ts
export type WorkSurface = 'story'|'screenplay'|'storyboard'|'prompts'|'video'
  |'take'|'editor'|'media-prep'|'characters'|'worlds';
export type AgentHandoff = {
  workspace_id:string;
  surface:WorkSurface;
  asset_ids?:string[];
  ranges?:Array<{asset_id:string;start:number;end:number}>;
  scene_id?:string; shot_id?:string; task_id?:string;
  job_id?:string; editor_session_id?:string;
};
```

Typed context bridges should push **actual selected assets/ranges** to the target page; navigation does not admit a job or substitute unselected audio. Validate all handoffs on server. Persist pending drafts and per-project chat identity separately from visible route. The existing `editor-api.ts` range type can be reused rather than reinvented.

## Video prompts and references
Keep `video-api.ts` exact T2V/R2V/FL2VA unions/serializers. Do not add imaginary `first_frame` to R2V. Reference presenter should show separately numbered image, video and audio slots, corresponding real IDs/hashes and route-aware restrictions. Before changing `VideoRequest`, coordinate with 3 CPU validators, compiler, worker, UI and graph digests.

## Existing clients to reuse unchanged
- `prepareContinuityFrame(jobId)` in `video-api.ts` — already returns registered last-frame asset metadata.
- `listMediaAssets`, `searchMediaSemantically` in `media-api.ts` — reuse, don't fork a private agent media picker.
- `editorApi(...)` with `EditorRange` in `editor-api.ts` — Editor remains a specialist tool, not a hidden second timeline API.
- `storyboard-api.ts` `getBoard/saveBoard` and current screenshot/panel machinery — keep revision checks.

## Frontend tests
Test no automatic network submit on chat planning, exact project switching, lost/slow responses, disabled tool reasons, resume from saved task ID, right-pane navigation preserving selected ranges. Keep chat/composer state per project; redact provider secrets from project snapshots. Component tests may use synthetic 1px PNG and stubbed job events; remove generated outputs.
