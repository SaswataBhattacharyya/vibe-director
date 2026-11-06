# Typed client contracts — current planned work after Editor bridge

At latest reviewed source 603b1fcb, agent-api.ts, agent-context.ts and agent-tasks.ts exist and the Editor target bridge in DirectorRuntime/DirectorEditor has been implemented. Do not reset to old five-field-only assumptions or rebuild Editor brief adapter.

**See:** fixes/UNIFIED_MEDIA_AND_PROJECT_ASSETS.md and fixes/PAGE_BY_PAGE_CHAT_AND_LAYOUT.md.

## MED01 — one picker, distinct typed destinations
Re-use lib/media-api.ts MediaAsset, browseMediaCatalogue, reuseCatalogueAsset, uploadMediaAsset, searchMediaSemantically; use existing EditorRange from lib/editor-api.ts and R2VReferenceDraft from App.tsx (may extract a type-only module if proven useful).

Proposed types (not current API):
- MediaPickerQuery: target workspace, allowed kinds, source/scope/folder, tags, role/category, indexing status, order, paging, selected IDs.
- MediaChoice: source_workspace_id, asset_id, expected_sha256, intent ("chat_attachment" / "model_reference" / "editor_range" / "tool_input" / "project_membership"), workflow/slot/role/intent if applicable.
- MediaBindingResult: selected target project asset ID/SHA plus role, target revision or explicit unsupported reason.
No raw path-only model bindings. Unregistered browser File requires approved import/registration first. Cancel/late response must not bind to newly selected project/session. R2V image/audio/video separate caps, speaker map and FL2VA true endpoints stay as now.

## MED02 — truthful query and index filters
Current browseMediaCatalogue has source/owner/folder/query/order offset only; backend browse_catalogue supports newest/oldest but not name sort or voice-only/analyzed status. Add optional v2 filter parameters after corresponding backend implementation and validation; avoid UI chips that merely filter the current page of 24 returned records. Semantic search is workspace-scoped today; don't advertise global semantic until verified.

## MED03 — membership handling
Current reuseCatalogueAsset can reference shared storage locations, but project-upload assets without shareable location may be copied. Do not fake a "linked" label on a copy result. Preserve old pa-* IDs and sha256. Add explicit membership provenance/status in backend response only after impact and snapshot review. One asset can have several project memberships; unlinking project membership must not be a delete-physical command.

## UX04 — shared Director page context
Keep Editor versioned target. For screenplay/prompt/image/video/3D add surface-specific typed target with actual revision/CAS, field hash, allowed asset roles, idempotency/recovery identities. The central chat's attachments are just selected input refs, not model references. No second chat store. On route switch focus current target while keeping conversation history; invalidate stale selection when project changes.

**Tests:** current/all-project source, stale hash/grant, recorded shot refs, R2V slot count, wrong Editor session, index unavailable, permitted role, latency/paging, result cleanup and save/reload. Preserve API response compatibility and frozen requests.
