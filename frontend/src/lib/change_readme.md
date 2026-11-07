# Frontend typed client contracts — active (2026-11-07)

See `fixes/INTEGRATION_ARCHITECTURE.md` and `fixes/ACTIVE_FIXES.md`. Existing `lib/media-api.ts`, `lib/editor-api.ts`, `lib/agent-api.ts`, `lib/agent-context.ts`, `lib/agent-tasks.ts` are sources of truth; do not replace them wholesale or manufacture new unvalidated APIs.

**Proposed, not yet shipped:** typed `MediaRef`, `EditSelection`, `StudioComposition` bridge between Vibe Editor's existing saved JSON plan and the HyperFrames visual timeline, with asset owner ID/SHA, Editor session/revision, supported role/slot and exact time ranges. Persist via current backend validators; do not pass raw local paths or silently bind chat attachments to model slots. React 18.3.1 / Studio compatibility is a gated spike, not an installed dependency.

The `MediaSourcePicker` destination mechanism is partially present. Respect R2V per-modality caps, FFLF first/last roles, Qwen reference counts, optional audio, deleted/remote asset status, project switch cancellation and frozen job snapshots. Full-asset analysis must not silently inherit a first-five-seconds preview selection.

One shared Director's page-specific target is an explicit typed context, not a second freeform conversation state. Always revalidate owner, revision and hashes on task review/Run.
