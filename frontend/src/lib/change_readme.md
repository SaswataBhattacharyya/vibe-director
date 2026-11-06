# Frontend lib — remaining typed handoff additions

The Q06 `agent-api.ts` and `agent-context.ts`, Q07 task client and existing media/editor/video clients **already exist**. Do not recreate or fork their request logic. Read [current UX spec](../../../fixes/UNIFIED_CHAT_AND_PANES.md).

## Needed: typed page/session context for the ONE shared chat
`DirectorRuntime.send` currently passes `{text,asset_ids,skill_refs,surface}`; `surface:'editor'` alone is not enough. Add a versioned, typed context that can carry:
```ts
type AgentTarget = {
  surface: 'editor'|'screenplay'|'storyboard'|'video'|'image'|'prompt'|'tools';
  editor_session_id?: string;
  expected_revision?: number;
  selected_ranges?: Array<{asset_id:string;start:number;end:number}>;
  scene_id?: string; shot_id?: string;
  draft_hash?: string; source_revision_id?: string;
};
```
This is a **proposal**, not a new API that already exists. Reuse `EditorRange` from `editor-api.ts`, `StoryVideoLineage` from `video-api.ts`, and current asset IDs/hashes. Type validation must also happen server-side. Version request payload/idempotency carefully to avoid corrupting history from previous five-field messages. A target identifies context, **not** permission to submit a render.
 
Expose minimal shared actions to page components such as `setAgentTarget(target)` and `focusDirector()`; do not have pages mount `StudioChat` or send hidden requests on navigation. Keep media selection/Editor state authoritative in current services and invalidate stale targets on project/session switch.

**Tests:** owner A/B, no stale asset from former Editor session, validated ranges, selected shot revision, chat persistence across route, no duplicate fetch handler. Page collapse must not clear drafts. `studioRequest` export in `StudioChat.tsx` has other consumers, so extract only after enumerating imports and testing.
