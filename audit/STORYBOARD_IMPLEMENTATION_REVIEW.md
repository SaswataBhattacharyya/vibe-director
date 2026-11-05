# Storyboard implementation review — 2026-11-04

Scope: the current storyboard/screenplay addition, not the entire dirty repository. Task-start copies under `/tmp/storyboard-implementation-baseline` isolate existing-file changes where available. The Video job service already contained unrelated changes and has no task-start copy. New source is first-party; no OpenMontage/Backlot/Hyperframes code was copied.

## Implemented behavior

Whole-screenplay instruction/propose/review/select/apply uses existing revisions and preserves evidence. Legacy shots default to Video; Image classification and two-second still holds are supported. Frame per shot and Storyboard are project-linked pages. A scene has combined description/dialogue at left and ordered shot images at right, with responsive spacing and shared theme variables. Optional stages and Manual/Director ownership are explicit. Character/background/shot image preparation uses existing durable image jobs and approved references. Auto frame preparation freezes each request before submitting and recovers completed jobs. New automatic image admissions retain smoke-evidence checks. Both automated FFLF image preparation and video execution are paused by one quality policy; explicit manual FFLF remains available.

Storyboard saves retain earlier revisions and use compare-and-swap. Current project Save/Open captures board records, media and Director proposals. Unsaved browser drafts remain recoverable. Finished HTML exports embed images and escape text; browser Print/Save PDF uses the scene layout. Saved individual video shots open in existing Video generation. Ordered completed media imports into a normal Vibe Editor session; reopening preserves Editor edits.

## Source-traced flows and impact

- Screenplay page → whole-Director API → FieldEditProposals → StoryAuthoring.edit_screenplay → new ledger revision → acceptance/Video lineage checks.
- Frame page → saved request → existing image jobs/admission/worker → shared media asset → saved storyboard → Video handoff → existing durable Video job service. Runtime generation engines and final-only LTX publication are retained.
- Board → ordered media selection → existing Editor project API → normal Editor session. Scene/shot order comes from the screenplay, independent of JSON key order.
- Board/proposal rows → projects.sql_snapshot → portable folder checkpoint → open_project → current project/UI reads.
- Legacy automated endpoint/frame and FFLF video paths → shared quality-policy helper. Manual workflow readiness and original media ownership remain separate.

Graphify was force-refreshed: 4,529 nodes, 14,138 edges, 466 code files. `graphify query Storyboard` traversed depth 2 and returned 175 discovery nodes. Import/library/generic nodes were filtered; the bounded affected service/UI/persistence map below is source-grounded. JSON workflow graph content is outside the code-only extraction. No TESTED_BY edge or measured branch coverage is claimed.

Overall impact priority: **high (0.60; possible 0.70 with unknown caller counts)** because new persisted records and accepted-revision boundaries feed existing execution paths. Scores prioritize review; they are not defect probabilities. SQL/persistence nodes receive the security-boundary factor. Test-gap factors use static associations, not coverage measurements.

## Validation and review findings

- 57 CPU backend checks passed across storyboard, story graph and project restore. The 11 storyboard checks passed again after final media-kind/route validation tightened.
- 89 storyboard/image workflow/admission checks passed before the final extra ordering test and validation assertions. Old image test fixtures were corrected for the actual services/production database path and complete provider response. Existing FFLF builder tests explicitly enable the future policy while separate tests assert today's pause.
- TypeScript/production build passed. Six isolated browser interaction tests passed: layout/mobile, stage ownership/manual FFLF, draft recovery, proposal-before-apply, auto frame freezing/resume, Editor session selection.
- Live isolated browser loaded trial 1 scar, the whole-screenplay instruction area, Frame per shot and 22 storyboard scenes. No page errors or horizontal overflow. Project-memory writes were intercepted to preserve owner browser memory. No generation/proposal/save clicks were made on owner data.
- Browser MCP could not acquire its occupied browser profile; isolated Playwright provided the browser checks. Screenshots: `/tmp/vibe-live-screenplay.png`, `/tmp/vibe-live-shot-frames.png`, `/tmp/vibe-live-storyboard.png`, `/tmp/vibe-storyboard-mobile.png`.
- Corrected an actual undefined `manifest` reference in the R2V request builder to the supplied `setup` aspect ratio; a focused 9:16 test exercises it. Earlier history cannot establish when that defect entered the dirty tree.
- Broader R2V contract suite is **not green**: 18 tests, 6 failures and 4 errors, involving retired workflow versions, pinned hashes and four-step Turbo/LTX expectations. See `/tmp/vibe-r2v-contract-tests.log`. The captured baseline log `/tmp/vibe-r2v-contract-baseline.log` reports the same ten failing test names (14 tests, 6 failures/4 errors); the current suite has four additional passing tests. Those failures were not bypassed by weakening runtime guards. Full unrelated Video compatibility remains unresolved by this task.

No additional confirmed defect remains in the bounded new storyboard paths after review and focused fixes. This is not an exhaustive security audit. GPU generation, provider output quality, real manual FFLF generation and final mixed-video/audio acceptance remain untested.

## Remaining plan work — do not treat as implemented

The fully automated choice currently configures Director ownership and automatic frame preparation; video shots still require the owner's normal Generate action. A durable server-side mixed Image/T2V/R2V scheduler, automatic video-result association, per-reference dependency invalidation/review, automatic character-master reuse across shots, timestamped sourced-clip selection, automatic music/SFX/dialogue timing and final-composition orchestration remain future plan items. No standalone raster-page exporter or native PDF renderer is implemented; current finished export is embedded HTML plus browser PDF printing. Do not promise a complete autonomous film pipeline from these controls.

## Conversational screenplay follow-up — 2026-11-04

The original box requested edits without discussion. Send message now supports normal user/Director turns. Prepare agreed changes uses the discussion to prepare a proposal; only Apply selected changes writes a screenplay revision. Conversation history persists across revisions and project Save/Open. Distinct request field keys prevent discussion replies being applied as edits. Completed requests replay without duplicate provider calls. Context uses the last 20 completed/request records within a bounded text budget. Existing proposal history remains readable.

Animated LoaderCircle icons indicate loading, thinking, preparing and saving. The shared StudioChat used by Media Prep audio and Trellis also gains a thinking icon without changing its API. The screenplay indicator respects reduced-motion settings. Shared palette variables, message spacing and responsive widths preserve the studio appearance.

Checks: 12 storyboard CPU tests passed, including contextual discussion/no-write, idempotent replay, explicit apply and fresh-root project/chat restoration; production build passed; seven browser tests passed, including multi-turn replies, thinking animation, reload and no automatic proposal/application from Send. Live trial 1 scar loaded its chat without page errors or horizontal overflow. Project-memory writes were intercepted during inspection. Browser MCP could not acquire its occupied profile; isolated Playwright performed the checks. No validation sent a live provider or GPU generation request.

Current limit: existing shot fields are editable; automatic insertion/splitting of shots is not implemented. The discussion prompt discloses that limit when relevant. Broader video/audio pipeline and baseline R2V issues above remain unchanged.

## Verified affected-node map

Current source anchors appear below; factors and evidence are in `.review/storyboard-findings.json`. Caller counts and measured coverage remain unknown. Maximum known score remains 0.60 (high); shared StudioChat's unmeasured test association allows an upper bound of 0.80. Its change is limited to the loading indicator. Scores prioritize review and are not defect probabilities.

| Risk | Node | File | Anchor | Reason |
| --- | --- | --- | --- | --- |
| 0.60–0.70 | storyboard.py::__init__ | backend/story_builder/services/storyboard.py:39 | `    def __init__(self, ledger, story, root):` | direct; execution flow; cross-module consumer |
| 0.60–0.70 | storyboard.py::get | backend/story_builder/services/storyboard.py:62 | `    def get(self, workspace, revision):` | direct; execution flow; cross-module consumer |
| 0.60–0.70 | storyboard.py::save | backend/story_builder/services/storyboard.py:153 | `    def save(self, workspace, revision, payload):` | direct; execution flow; cross-module consumer |
| 0.60–0.70 | storyboard.py::conversations | backend/story_builder/services/storyboard.py:275 | `    def conversations(self, workspace, revision):` | direct; execution flow; cross-module consumer |
| 0.60–0.70 | storyboard.py::apply | backend/story_builder/services/storyboard.py:291 | `    def apply(self, workspace, revision, payload):` | direct; execution flow; cross-module consumer |
| 0.60–0.70 | isolated_video_jobs.py::_validate_story_source_lineage | backend/story_builder/services/isolated_video_jobs.py:145 | `def _validate_story_source_lineage(db, story, workspace, clip, request, supplied, media_root=None):` | direct; execution flow; cross-module consumer |
| 0.60–0.70 | projects.py::sql_snapshot | backend/story_builder/services/projects.py:102 | `def sql_snapshot(path, workspace):` | consumer; execution flow; cross-module consumer |
| 0.60–0.70 | projects.py::open_project | backend/story_builder/services/projects.py:424 | `def open_project(root, folder):` | consumer; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::automatic_route_allowed | backend/story_builder/services/storyboard.py:22 | `def automatic_route_allowed(route):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::text | backend/story_builder/services/storyboard.py:27 | `def text(value, label, limit=16000):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::validate_shot_kind | backend/story_builder/services/storyboard.py:33 | `def validate_shot_kind(shot):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::screenplay | backend/story_builder/services/storyboard.py:50 | `    def screenplay(self, workspace, revision):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::assets | backend/story_builder/services/storyboard.py:53 | `    def assets(self, workspace):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::validate | backend/story_builder/services/storyboard.py:91 | `    def validate(self, workspace, revision, value):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::readiness | backend/story_builder/services/storyboard.py:168 | `    def readiness(self, workspace, revision):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::propose | backend/story_builder/services/storyboard.py:219 | `    def propose(self, workspace, revision, payload, provider):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::changes | backend/story_builder/services/storyboard.py:251 | `    def changes(screenplay, replacement):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::export | backend/story_builder/services/storyboard.py:311 | `    def export(self, workspace, revision):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::editor_handoff | backend/story_builder/services/storyboard.py:334 | `    def editor_handoff(self, workspace, revision):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::digest | backend/story_builder/services/storyboard.py:370 | `    def digest(value):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::video_handoff | backend/story_builder/services/storyboard.py:373 | `    def video_handoff(self, workspace, revision, key):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::direct | backend/story_builder/services/storyboard.py:406 | `    def direct(self, workspace, revision, payload, provider):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | isolated_server.py::storyboard = Storyboard | backend/story_builder/isolated_server.py:352 | `    storyboard = Storyboard(ledger, story, root)` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | story_authoring.py::edit_screenplay | backend/story_builder/services/story_authoring.py:1893 | `    def edit_screenplay(self, *, workspace_id: str, screenplay_revision_id: str,` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | isolated_video_jobs.py::_full_r2v_request | backend/story_builder/services/isolated_video_jobs.py:468 | `    def _full_r2v_request(cls, *, setup, prompt, duration_seconds=None, continuity=None,` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | production_image_admission.py::build_clip_frame_image_batches | backend/story_builder/services/production_image_admission.py:102 | `def build_clip_frame_image_batches(*, workspace_id: str, screenplay: dict[str, Any],` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | StoryboardPage.tsx::StoryboardPage | frontend/src/StoryboardPage.tsx:11 | `export default function StoryboardPage({view}:{view:'frames'\|'storyboard'}){` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | ScreenplayDirector.tsx::ScreenplayDirector | frontend/src/ScreenplayDirector.tsx:7 | `export default function ScreenplayDirector({workspace, revision, disabled, onApplied}: {` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | ProjectController.tsx::const prefix= | frontend/src/ProjectController.tsx:12 | `const prefix=/^vibe-(project-settings:\|session:\|video-\|story-\|create-chat:\|selected-take:\|take-position:\|image-\|text-to-image-\|editor-\|ace-\|studio-chat-\|screenplay-\|board-\|field-edit:\|t2v-batch:\|trellis-\|pixal-\|jukebox-\|production-\|style-setup-context\|3d-)/;` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard-api.ts::export const saveBoard= | frontend/src/lib/storyboard-api.ts:12 | `export const saveBoard=(state:BoardState,body:BoardBody)=>request<BoardState>(base(state.workspace_id,state.screenplay_revision_id),{expected_revision:state.revision,body},'PUT');` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::discussion_context | backend/story_builder/services/storyboard.py:180 | `    def discussion_context(self, workspace, revision):` | direct; execution flow; cross-module consumer |
| 0.40–0.50 | storyboard.py::chat | backend/story_builder/services/storyboard.py:187 | `    def chat(self, workspace, revision, payload, provider):` | direct; execution flow; cross-module consumer |
| 0.40–0.80 | StudioChat.tsx::StudioChat | frontend/src/StudioChat.tsx:10 | `export default function StudioChat({name,context,onApply}:{name:string;context:unknown;onApply?:(settings:Record<string,number>)=>void}) {` | direct; execution flow; cross-module consumer |

Bundled citation verifier: 33 anchors, zero rejected. Citation checks do not verify dependency claims or measured coverage.

## Prompt Director chat, image briefs and explicit learning — 2026-11-04

Prompt Preparation now has discussion-first project chat, history and animated thinking, reviewed prompt proposals, character/location image briefs, and explicitly approved reusable rules. Rules are scoped to video, characters, environments or all prompts. New shot drafting, assisted clip planning and image prompt preparation consume applicable approved rules. Export SKILL.md produces a portable skill; it does not install a global skill or retrain a model. Image briefs follow the accepted screenplay and canonical asset identities. The existing Characters/Worlds pages adapt saved briefs to exact workflow guidance and actual references.

Chat never implicitly applies or learns. Applying reviewed shot changes updates local drafts; Save prompt drafts remains required before production. Image briefs and learning use compare-and-swap persistence. Project Save/Open snapshots restore new data and conversation history. Existing jobs, selections, source media, frozen plans/requests, GPU admission and final-output publication remain on their existing paths.

Validation: 66 focused CPU tests, ten mocked prompt/storyboard/image-cache browser checks, production TypeScript/Vite build, and read-only live project loading passed. Live trial 1 scar exposes 20 canonical character records and 12 location records; existing source aliases remain separate records. Desktop/390px layouts were inspected; navigation can be hidden on narrow screens. The browser MCP profile was occupied, so isolated Playwright performed inspection with project writes intercepted. No validation initiated provider/GPU work.

Broader limits: the image UI suite finished with 11 pass and 28 failures, including removed workspace selectors and incomplete project mocks; these have not all been baseline-isolated, so whole-app regression health is unresolved. Four clip-plan tests (three failures/one error) also fail against unchanged HEAD: selected_style_video_changes_each_scene_start_to_r2v, splits_shot_into_stable_ordered_clips_and_restarts_t2v_at_scene, verified_character_reference_routes_only_reached_scene_start_to_r2v, generates_each_scene_separately_and_validates_combined_plan. Do not weaken guards to satisfy stale contracts. New automatic-world adapter and assisted-plan adapter lack direct branch execution evidence; their downstream prompt preparation/callback behavior has focused tests. Real model prompt quality remains owner acceptance.

Code review found no further confirmed defect in this bounded patch after correcting optional image-drafter output validation and preventing rule approval/removal from saving unrelated unsaved image edits. This is not a whole-repository correctness claim. Global rules installation, per-shot background dependency orchestration and complete autonomous assembly remain separate scope.

Graph refresh: 4,574 nodes / 14,292 edges, full code-only extraction; graph skipped unsupported/empty files and docs. The table below is the manually confirmed scoped map, rather than a claim that every discovered graph neighbour is a real dependency. Maximum known score 0.60 (high); unknown caller counts/adapter test evidence permit 0.80. SQL persistence and cross-module execution drive priority. Focused tests are test evidence, not measured coverage.

| Risk | Node | File | Anchor | Reason |
| --- | --- | --- | --- | --- |
| 0.40–0.80 | automated image prompt adapter | backend/story_builder/isolated_server.py:2881 | `                    def draft_entity_image(*, target, idempotency_key):` | direct; character/world admission consumes saved briefs and scoped rules; callback unit evidence, new world closure branch not directly covered |
| 0.40–0.80 | assisted clip-plan preparation | backend/story_builder/services/isolated_video_jobs.py:819 | `                prompt_guidance=read_guidance(self.ledger, workspace, 'video'))` | direct caller; only new plans consume rules; frozen requests unchanged; specific adapter branch not directly exercised |
| 0.60–0.70 | read_guidance | backend/story_builder/services/prompt_director.py:14 | `def read_guidance(ledger, workspace, scope):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.60–0.70 | image_brief | backend/story_builder/services/prompt_director.py:29 | `def image_brief(ledger, workspace, revision, target):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.60–0.70 | PromptDirector.__init__ | backend/story_builder/services/prompt_director.py:36 | `    def __init__(self, ledger, story, workflow_knowledge=None):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.60–0.70 | PromptDirector.get | backend/story_builder/services/prompt_director.py:60 | `    def get(self, workspace, revision):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.60–0.70 | PromptDirector.save | backend/story_builder/services/prompt_director.py:79 | `    def save(self, workspace, revision, payload):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.60–0.70 | sql_snapshot | backend/story_builder/services/projects.py:102 | `def sql_snapshot(path, workspace):` | indirect persistence consumer; fresh-root checkpoint test restores rules, image briefs and history |
| 0.60–0.70 | open_project | backend/story_builder/services/projects.py:424 | `def open_project(root, folder):` | indirect project restoration consumer; project-specific rows restored by generic snapshot schema |
| 0.60–0.70 | FieldEditProposals.propose | backend/story_builder/services/field_edit_proposals.py:57 | `    def propose(self, workspace_id, payload, provider_call):` | indirect; unchanged durable idempotency ledger used by discussions and proposals |
| 0.45–0.55 | PromptDirector.conversations | backend/story_builder/services/prompt_director.py:105 | `    def conversations(self, workspace):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.40–0.50 | PromptDirector.discuss | backend/story_builder/services/prompt_director.py:122 | `    def discuss(self, workspace, revision, mode, payload, provider):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.40–0.50 | PromptDirector.export | backend/story_builder/services/prompt_director.py:197 | `    def export(self, workspace, revision):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.40–0.50 | HTTP prompt Director routes | backend/story_builder/isolated_server.py:2449 | `                if len(parts) in (3, 4) and parts[1] == "prompt-director":` | direct; validates project/revision; durable discussion and approval API |
| 0.40–0.50 | manual image prompt adapter | backend/story_builder/isolated_server.py:2887 | `                        def image_prompt_provider(*, temperature, prompt):` | direct; HTTP test verifies exact saved character brief, scope and workflow guidance |
| 0.40–0.50 | PromptDrafts.prepare | backend/story_builder/services/prompt_drafts.py:105 | `    def prepare(self, workspace_id, revision_id, shot_key, workflow_id, *, setup_snapshot=None,` | direct; approved video rules reach new drafts; focused scope-isolation test |
| 0.40–0.50 | generate_clip_plan | backend/story_builder/services/fully_automated_clip_plan.py:33 | `def generate_clip_plan(*, workspace_id: str, screenplay_revision_id: str,` | direct; optional guidance supplied only by new assisted planning; default stays empty |
| 0.40–0.50 | build_entity_image_batches | backend/story_builder/services/production_image_admission.py:18 | `def build_entity_image_batches(*, workspace_id: str, screenplay: dict[str, Any],` | direct; optional world drafting callback; tests verify prompt replacement, settings preservation and invalid output rejection |
| 0.40–0.50 | PromptDirector UI | frontend/src/PromptDirector.tsx:6 | `export default function PromptDirector({workspace,revision,shotPrompts,shotWorkflows,disabled,onApplyShots,onBusy}:{` | direct; chat, animation, review, lessons and image briefs tested with mocked APIs |
| 0.40–0.50 | Prompt Preparation integration | frontend/src/PromptPreparationPage.tsx:263 | `      <PromptDirector key={`${workspaceId}:${revision.screenplay_revision_id}`} workspace={workspaceId} revision={revision.screenplay_revision_id}` | direct; accepted-project chat proposals update local shot drafts, require explicit existing Save |
| 0.40–0.50 | ImageAssetsPage guidance version | frontend/src/ImageAssetsPage.tsx:541 | `  const projectPromptKey=`${workspaceId.trim()}:${acceptedScreenplayId}`;` | direct; image prompt cache retains owner edits per guidance version; existing frozen job path preserved |
| 0.40–0.50 | prompt Director API client | frontend/src/lib/prompt-director-api.ts:12 | `export const getPromptGuidance=(w:string,r:string)=>request<PromptGuidance>(path(w,r));` | direct; project/revision API, save CAS, discussion and portable skill download |
| 0.25–0.35 | PromptDirector.targets | backend/story_builder/services/prompt_director.py:46 | `    def targets(self, workspace, revision):` | direct; prompt execution flow; focused behavioral test evidence |
| 0.25–0.35 | PromptDirector.validate_lessons | backend/story_builder/services/prompt_director.py:70 | `    def validate_lessons(lessons):` | direct; prompt execution flow; focused behavioral test evidence |

Full factors and source citations: `.review/prompt-director-findings.json`. Source anchors are checked with the bundled blast-radius citation verifier; source-line checks do not establish runtime readiness.

Additional verification: image drafts retain owner edits on reload and refresh for a new approved-guidance revision; rule approval preserves unrelated unsaved image changes. Exported SKILL.md passes the skill-creator validator. Bundled blast-radius verifier accepts all 24 cited source anchors.
