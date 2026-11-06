# Frontend Playwright acceptance — whole-app Director, media and compact UX

**New test guidance at reviewed source 603b1fcb (2026-11-06).** Existing tests in frontend/tests/director-runtime.spec.mjs, create-panes.spec.mjs, media-source-picker.spec.mjs, media-library.spec.mjs, editor-assets.spec.mjs, media-search-analysis-bridge.spec.mjs, media-selection-scope.spec.mjs, output-destinations.spec.mjs, image-assets.spec.mjs, video-ui.spec.mjs and other routes are authoritative baseline tests. Read fixes/ACTIVE_FIXES_2026-11-06.md, fixes/PAGE_BY_PAGE_CHAT_AND_LAYOUT.md, fixes/UNIFIED_MEDIA_AND_PROJECT_ASSETS.md and fixes/COMPACT_CREATIVE_WORKSPACE_UX.md.

## UX04: one active AI composer, all routes

For Screenplay, Prompt Preparation, Video Create, Image Assets/Scene Backgrounds, Text-to-Image, TRELLIS/Pixal and Media Prep:
- Exactly one live AI message composer (the persistent middle Director), not duplicate page-specific "Director chat", "Prompt chat" or StudioChat forms. Distinguish manual prompt editors, SRT input, search and user-facing non-chat forms.
- Create a real draft with old input path and assert resulting shared chat proposal/diff/learn rule is identical in semantic effect; only Apply triggers a durable revision/field change. Historical old messages accessible read-only with correct project/revision; no old Send.
- Reload, switch route, collapse all panes, change project, then return: chat history, work-page unsaved prompt, selected model refs and pending approved plan remain intact; no wrong-owner action or focus trap.
- Regression: the already completed Vibe Editor still uses only central chat while brief/plan clearances, timeline, media and export work.

## MED01: shared picker and correct target action

Make fixture library with voice WAV, SFX WAV, generated video MP4, downloaded video MP4, image PNG, a second project and one folder source. Verify Current project / All projects / Shared and source filters, type chips image/audio/video, voice-only, analyzed-only (no false positives), chronological sort and supported view modes. Search returns stable selected IDs; one selected item can be attached to chat or bound to R2V model but NOT both by accident.

R2V reference binding keeps individual image/audio/video caps, role+intent and expected source SHA. FL2VA uses true first/last slot; image-only Qwen edit accepts valid 1–3 references; 3D uses image inputs, not video/audio by implication. Editor selected clips use start/end ranges, not voice-ref slots. Cross-project browse asks for verified reusable/importable ID; no filename-only link or source loss.

An unregistered local file is imported only after user consent and completes registration; closing picker does not register it. Universal picker never exposes permanent delete as a primary selection action. Re-check Media Prep original source picker/indexing flows.

## MED02/MED03: realistic search/memberships

Filters must apply to entire result set BEFORE 24-item pagination, including 25th result. Keyword/semantic mode explains unavailable index; indexing a stale/changed file updates source SHA/provenance. Cross-project reuse displays distinct project membership chips; removing one membership does not hide/delete the underlying physical source from another project. A project moved/renamed should recover/refuse stale external path rather than silently copy or leak.

## UX05: images/backgrounds

At 1280×720 with left nav and Director open, image creation page does not show nested two-column squeezing. Main target/prompt/Generate/candidates reachable, reference selector and output chip compact, workflow info opened via keyboard, and **old image chat absent after parity**. Voice tasks and SceneBackgroundVariant base/condition workflow accessible. Generating is disabled by real existing readiness; source change prompts appropriate review.

## UX06: Current Take

Test queued/running (real job state, no fake percent), completed, failed/recovery, accepted, retake, next (standalone/story), full run. One selected video player with saved position, thumbnail selection, Accept/Retake/Next visible, frozen prompt/history/details accessible but not cluttering default. Toggle details / collapse outer work or Director without requeuing or resetting job. Do not add duplicate video media streams on layout switches. Retake preserves old original under existing policy.

## UX07/UX08: destinations and aesthetics

Current valid project output appears as one short badge, full path accessible with keyboard/tooltip, Change opens old path/grant/relink behavior, unavailable grant visibly blocked, old frozen jobs keep destinations. Screenshot routes at 1440×900, 1280×720, 900×768 and 390×844; check overlays, footer/scroll, no horizontal overflow, focus/ARIA, reduced motion and minimum touch targets. Cards progress, media first, metadata under Details; errors/approval never buried.

## Safety/isolation

No GPU/paid-provider execution in Playwright. Use mocked endpoints with explicit traffic isolation (previous tests use loopback port 1 to reject escaped requests). Generate disposable synthetic images/videos/audio/text and project roots; clean in fixture teardown or finally, including failed tests; assert no fixture directories remain. Never delete real media. Report actual test run and failures, not an inferred pass from this guidance.
