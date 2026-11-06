# Typed agent client and handoff boundaries

Read [Q06](../../../fixes/QUICK_FIX_TASKS.md) and matching backend [API guide](../../../backend/story_builder/change_readme.md). Add `agent-api.ts`/`agent-context.ts` only for implemented endpoints. Existing editor/video/media/storyboard clients stay authoritative.

Phase 1 exposes tool metadata, skill metadata and derived project context only. Proposed tool fields/statuses are in Q03; skill fields in Q04. Match the actual error envelope and runtime response checks. A TypeScript `as T` cast is not validation. Do not build future task/control functions before Q07 exists.

Context carries workspace owner and optional actual asset IDs, scene/shot IDs and Editor session/ranges. Reuse `EditorRange` from `editor-api.ts`; session ID is not workspace owner. Encode route parameters and discard late responses after project change. Server revalidates every handoff; navigation never admits generation.

Q07 lifecycle requests include expected plan revision/hash, approved scope and idempotency identity. No generic exec client. Q08 maps approved typed intent to that lifecycle and returns registered assets.

Reuse current `listMediaAssets`/`searchMediaSemantically`, `editorApi`, `getBoard/saveBoard`, and `prepareContinuityFrame`. The last-frame helper applies to supported generated job outputs; it is not arbitrary uploaded video frame extraction. Do not fork duplicate fetch/business logic or mutate exact video serializer unions for UI convenience.

Test no submit during discovery/planning, project/selection preservation, unsupported fields, slow/lost responses and recovery IDs. Mock responses at the boundary; integration tests must also exercise the real matching backend contract.
