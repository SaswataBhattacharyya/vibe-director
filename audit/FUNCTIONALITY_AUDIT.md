# Vibe Director functionality audit and code review

Reviewed 2026-11-03 against the current working tree. This file records observed structure, contracts, review findings and validation. It assigns no collaborators, model roles, handoffs or milestone schedules. It is not a claim that every feature is complete or every runtime works. The latest requested redesign remains separately in `plans/editor_media_output_ace_plan.md`.

## Review scope and limits

Architecture/source inventory covers the top-level router, first-party UI/service entrypoints, explicit Markdown readers and documentation deletion references. Detailed correctness review covers ACE state restoration, Editor asset attachments/selections, panel navigation, output destinations/export and relevant regression tests. Other feature rows below are source maps, not exhaustive correctness/security reviews of all functions.

The current graph has 21 nodes and 128 edges and does not cover the requested scope. Manual source tracing supplemented the graph. The review initially made no existing-file changes. The subsequently approved documentation cleanup is recorded below; application code is unchanged. No user media, saved session, model, provider or GPU generation was touched. This report supersedes the earlier narrow documentation-deletion audit for the cleanup decision.

## Current functionality map

This table identifies implementation entrypoints, not promises of live readiness. Preserve implementation, storage formats, IDs and consumer contracts while redesigning the UI. Use source and focused tests when changing a row rather than loading every document.

| Area | Frontend entrypoints | Backend source under `backend/story_builder/services/` | Contracts to preserve |
| --- | --- | --- | --- |
| Shell and navigation | `App.tsx`, `StudioShell.tsx`, `DirectorSettings.tsx` | `reasoning_status.py`, `studio_checkpoints.py` | Hash routes, persisted context, separate provider and workflow choices. |
| Story authoring/import | `StoryPage.tsx` | `story_authoring.py`, `story_imports.py`, `production_story_revisions.py` | Source revisions; explicit import preview/apply; original source and stale-revision recovery. |
| Screenplay and direction | `ScreenplayPage.tsx` | `screenplay_schema.py`, `story_authoring.py`, `director_skills.py` | Structured screenplay and source lineage; explicit directing skills in prompts. |
| Storyboard preparation and whole-screenplay Director | `StoryboardPage.tsx`, `ScreenplayDirector.tsx` | `storyboard.py`, existing image/Video/Editor services | Revisioned project records, selected proposal apply, scene text/images, saved request recovery, manual-only FFLF. Scoped evidence and limitations: [implementation review](STORYBOARD_IMPLEMENTATION_REVIEW.md). |
| Production styles | `ProductionStylesPage.tsx` | `production_styles.py`, `style_sources.py`, `prompt_styles.py` | Style identity, source references and saved choices; style documents are user input. |
| Automation and production setup | `ProductionSetupPage.tsx`, `AssistedClipPlanPanel.tsx` | `production_setup.py`, `fully_automated_clip_plan.py`, `production_authority.py`, `production_job_worker.py` | Setup hashes, planned clip identity, prerequisite and stale-state checks. |
| Prompt preparation | `PromptPreparationPage.tsx`, `ShotReferenceDirector.tsx` | `prompt_drafts.py`, `workflow_knowledge.py`, `workflow_knowledge_catalog.py` | Model-specific prompting, references and frozen request lineage. `#/prompts` is currently reachable in code; historical prose saying otherwise does not remove it. |
| Video creation and review | `App.tsx` VideoWorkspace, `TakeWorkspace.tsx`, `T2VBatchPanel.tsx` | `isolated_video_jobs.py`, `production_t2v_capability.py`, `production_fl2va_capability.py`, `production_r2v_capability.py`, `t2v_batches.py`, `t2v_pipeline.py` | T2V/first-last-frame/reference contracts, durable requests, take acceptance, retake as editable draft, recovery before resubmission. |
| Characters, worlds and frames | `ImageAssetsPage.tsx`, `CharacterVoicesPage.tsx` | `production_image_selection.py`, `production_image_jobs.py`, `character_voice_bindings.py` | Shared asset identity, image/voice associations and lineage. |
| Text to image | `TextToImagePage.tsx`, `LocalImageFolderBrowser.tsx` | `image_prompt_drafts.py`, `production_image_admission.py`, `production_image_workflows.py`, `production_image_worker.py` | Workflow-specific inputs, folder references, saved settings and generated-asset registration. |
| 3D tools | `TrellisPage.tsx`, `MultiViewInputs.tsx` | `trellis_studio.py`, `multiview_3d.py` | Distinct TRELLIS/Pixal backends, multi-view roles, original outputs and independent runtime readiness. |
| Media library and Search | `MediaLibraryPage.tsx`, `MediaPrepPage.tsx`, `MediaSourcePicker.tsx` | `media_library.py`, `media_semantic_search.py`, `storage_paths.py` | Shared IDs, reference/copy semantics, explicit deletion, annotations/search, scoped selection, source provenance. |
| Analysis/download/preparation | `MediaPrepPage.tsx` | `video_repertoire.py`, `video_repertoire_worker.py`, `video_summarizer_results.py`, `image_detailer.py`, `sam_audio_vibe.py` | Existing jobs/artifacts, index state, source relinking and selected-media consumers. |
| Audio/voice tools | `VoiceStudioTools.tsx`, `VoiceConversion.tsx`, `VoiceRecorder.tsx`, `AudioSceneSurgery.tsx`, `MusicSoundPage.tsx` | `audio_tts.py`, `audio_reconstruct.py`, `audio_effects.py`, `audio_utilities.py`, `audio_scene.py`, `voice_studio.py`, `control_foley.py` | Recordings and reference assets, job state, preview/save boundaries, output registration. |
| ACE-Step | `AceStudioPage.tsx`, `AceGeneratedAudio.tsx`, `ace-folder-upload.ts` | `ace_studio_api.py`, `ace_studio.py`, `ace_studio_runner.py`, `ace_studio_presets.py` | Saved projects/revisions, generation versus fine-tuning, validated datasets/adapters, reference modes, confirmation and job recovery. |
| Music Jukebox | `MusicJukebox.tsx`, `JukeboxDJ.tsx`, `lib/jukebox-engine.ts` | `music_jukebox_api.py`, `music_jukebox.py` | Composition/playback/edit/export; keep bundled Tone and MIDI notices. |
| Vibe Editor | `VibeEditorPage.tsx`, `EditorWorkspace.tsx`, `EditorClipEffects.tsx` | `vibe_editor_api.py`, `vibe_editor.py`, `vibe_editor_render.py`, `editor_effects.py` | Brief then plan approvals; selected ranges; style versions; render/retry/pause/stop; validated output and export. |
| Assembly | `AssemblyPreviewPanel.tsx` | `assembly.py`, `assembly_renderer.py` | Accepted take selections, audio tracks, assembly snapshot and durable export metadata. |
| Cross-tool output folders | `OutputDestination.tsx` | `output_destinations.py`, `studio_tools_api.py` | Explicit folder grants, saved preferences, frozen job destination, verified publication and missing-folder relink. |
| Runtime, status and diagnostics | `StatusPage.tsx`, `ProviderStatus.tsx`, `PerformancePanel.tsx`, `DebugPanel.tsx` | `media_jobs.py`, `gpu_runtime.py`, `gpu_watchdog.py`, `provider_exec_guard.py`, `reasoning_provider.py`, `debug_journal.py`, `performance_journal.py` | Shared job/GPU controls, typed provider results, cancellation/recovery and honest readiness. |

Frontend names are relative to `frontend/src/`. The HTTP dispatcher is `backend/story_builder/isolated_server.py`; Editor/ACE also use their named API modules. This map is a redesign preservation checklist, not a requirement to retain the current layouts or terminology.

## Durable technical facts

- The app explicitly reads directing Markdown via `backend/story_builder/services/director_skills.py:17` and `backend/story_builder/services/vibe_editor.py:392`. Preserve `skills/` and all of `design/vibe-editor/skills/`, including upstream reference/assets trees. Skill-associated examples/recipes are retained. Their presence does not authorize external tools or paid generation.
- Repository coding-agent instructions and app reasoning prompts are distinct. `reasoning_provider.py` starts its command in an isolated temporary directory and receives an explicit prompt; repository plans are not a runtime knowledge-base loader.
- Source references to the proposed deletions have no identified runtime reader. The obsolete ACE setup-help path was removed during the authorized ACE/Editor implementation; the legacy `tools/migrate_local_layout.py` maps legacy documents into plans and can recreate destinations when explicitly rerun with those inputs.
- Output-folder UI can be simplified without deleting internal asset/session identifiers. Preserve shared destination freezing (`backend/story_builder/services/output_destinations.py:90`) and Editor's separate final export (`backend/story_builder/services/vibe_editor.py:441`), including collision confirmation, no-clobber publication and protection against replacing the source.
- Editor validates up to 100 selected ranges; plans use selected video/image clips plus optional selected audio, supported dimensions/frame rates, finite ranges and bounded duration/transitions. Plans must stay inside the chosen ranges. Renderer uses validated JSON and a network-isolated bubblewrap process, not arbitrary provider-authored code.
- GPU policy is currently `GPU_RENDER_TEMP_CUTOFF = 90.0` and `GPU_RENDER_CLOCK_CEILING_MHZ = 2100.0` in `gpu_runtime.py:22–23`. Preserve admission/watchdog behavior and do not alter clocks during UI work. Existing instructions require owner-started acceptance for new generation workflows; tests here used mocks/CPU only.
- Runtime state, original media, models, secrets and installed tool environments are outside this Markdown cleanup. Deleting documentation must not delete those directories.
- Keep third-party license notices and actual license/lock/manifests. `plans/openmontage_licensing.md` records a historical AGPL source/integration decision; no independent legal/license-compliance audit was performed here. Its factual provenance should be checked against actual imports/licenses before any covered source is copied. Removing the old note does not grant a new license.

## Code-review status — updated after ACE/Editor implementation

The initial review found ACE intent/panel mismatch, an obsolete attachment-test selector, missing Editor folder/selection/drop/removal controls, expanded Open controls and obsolete ACE setup-help text. These are now resolved in the authorized application patch. Fresh/new ACE sessions open Create/Generate; restored training sessions select Fine-tune without losing datasets/settings. The Editor now supports recursive selected-kind imports, Search-like selection/deletion/views, internal drag/drop and hover/focus attachment removal. Session/source popovers overlay the page; output folders support path entry and choosing. Saved ownership and backend contracts are preserved.

The code review also caught and fixed first-import partial-success visibility, deletion status overwritten by refresh and Audio Studio recording reuse after removal of workspace setup. The documentation entrypoint no longer mandates removed ledgers or collaboration. Full current impact map, changes, test evidence and limitations are in [ACE/Editor impact and review](ACE_EDITOR_IMPACT.md). No further actionable defect was found in that bounded patch review; this does not establish whole-app correctness.

## Validation performed

- Current frontend typecheck and production build passed (the existing large-bundle warning remains).
- Current focused mocked browser coverage: **13 distinct cases passed** across `ace-editor-ux`, `editor-assets`, `editor-effects`, `output-destinations`, `project-pruning-recovery` and `media-source-picker`. The original stale selector was fixed and its paste/drop/reload/chat checks passed. The obsolete unnamed-workspace test fixture was corrected to a currently valid workspace.
- Current CPU/mocked backend: **50 passed** across `test_ace_studio`, `test_media_catalogue`, `test_media_library` and `test_output_destinations`.
- Full code-only Graphify rebuild completed: 4,364 nodes, 13,432 edges after a sparse incremental result. A depth-2 query from the four main components found 164 candidates; source confirmed the bounded impact map. Source anchors are checked separately in `audit/review-findings.json` and `audit/ace-editor-impact.json`.
- Interactive Playwright MCP could not initialize: `Browser is already in use for /home/riki/.cache/ms-playwright-mcp/mcp-chrome-c9ae093, use --isolated to run multiple instances of the same browser`. Mocked CLI browser checks and screenshots were used; no interactive/live-backend acceptance is claimed.
- No provider/GPU generation, real rendering/training, native folder-dialog acceptance, repository-wide test suite, full security audit, all-feature acceptance or token/latency benchmark was performed. No direct backend tests for the Editor validator/export/renderer were found in the searched test tree. Those unchanged services remain an explicit coverage-evidence gap.

## Completed Markdown cleanup

The owner approved this exact file list, and the 71 listed Markdown files have now been deleted. This was not a wildcard deletion. The full machine-readable deletion list, preserved files and rewrite results are in `audit/documentation-cleanup.json`. Runtime/vendor caches and media are excluded. Existing plans and design proposals do not constrain the redesign once removed; the retained latest plan states the owner's current requested changes. This audit supplies the functionality map without preserving old role assignments or implementation schedules.

Keep the complete skill/reference/recipe trees, license notices, `design/VIBE_DIRECTOR_FOUNDATION.md`, the latest Editor/ACE plan and this audit. The foundation is retained as general design guidance, not a rule freezing routes or workspace UI. It contains dated proposals, so source/current owner requests take precedence. Do not require reading it for every coding task.

`AGENTS.md` now contains concise repository instructions; root `README.md` contains actual run/setup facts. Both 3D workflow READMEs remain as functionality/setup references: the TRELLIS stale integration link was replaced with current source locations; Pixal required no change. The old backend/frontend READMEs were deleted. The foundation, project-director skill and latest change plan had obsolete references repaired while retaining functional guidance.

**71 Markdown files deleted:**

- `.review/plans-deletion-impact.md`
- `COLLABORATION.md`
- `backend/README.md`
- `design/ux-shared-video-review.md`
- `design/vibe-editor/ACQUISITION_AND_SECURITY.md`
- `design/vibe-editor/PLAN.md`
- `frontend/README.md`
- `plans/BATCH_PIPELINE_AUDIT_2026_10_25.md`
- `plans/CHUNKED_BATCH_PAUSE_AUDIT_2026_10_25.md`
- `plans/COMFYUI_H3_TURBO_READINESS_REPORT_2026-10-23.md`
- `plans/GLOSSARY.md`
- `plans/GOAL.md`
- `plans/GRAPHIFY_GUIDE.md`
- `plans/GUIDED_TURBO_LTX_INTEGRATION.md`
- `plans/H3_CHUNKED_LTX_INTEGRATION.md`
- `plans/H3_SPEED_OPTIONS.md`
- `plans/LTX_COMFYUI_INSTALLATION_PROMPT.md`
- `plans/MANUAL_ACCEPTANCE.md`
- `plans/OWNER_DUMMY_RUNS.md`
- `plans/README.md`
- `plans/T2V_BATCH_FORMAT.md`
- `plans/T2V_TURBO_LTX_INTEGRATION.md`
- `plans/ace_step_bgm_dataset.md`
- `plans/ace_step_bgm_expansion.md`
- `plans/ace_step_studio.md`
- `plans/assembly.md`
- `plans/automation.md`
- `plans/char_world.md`
- `plans/cleanup_2026_10_22.md`
- `plans/cleanup_ui_repair_2026-11-01.md`
- `plans/development_workflow.md`
- `plans/donor_independence.md`
- `plans/implementation/G2_isolated_video_reuse.md`
- `plans/implementation/analyzer_memory_fix_2026_10_14.md`
- `plans/implementation/ashu_ui_adaptation.md`
- `plans/implementation/isolated_execution_decision.md`
- `plans/implementation/isolated_video_ui.md`
- `plans/implementation/pr22_design_foundation.md`
- `plans/implementation/status_catalog.md`
- `plans/implementation/story_creation_recovery.md`
- `plans/implementation/story_import_api.md`
- `plans/implementation/story_revision_reuse.md`
- `plans/implementation/story_ui.md`
- `plans/implementation/style_setup_foundation.md`
- `plans/implementation/style_workspace_link.md`
- `plans/implementation/v2_graph_screenplay_reuse.md`
- `plans/integration.md`
- `plans/local_data_cleanup.md`
- `plans/media_prep.md`
- `plans/media_prep_parity.md`
- `plans/media_selection_storage.md`
- `plans/model_selection.md`
- `plans/multiview_3d_integration.md`
- `plans/music_jukebox.md`
- `plans/music_jukebox_implementation.md`
- `plans/notes.md`
- `plans/openmontage_comparison.md`
- `plans/openmontage_licensing.md`
- `plans/post_transfer_code_audit_2026_10_22.md`
- `plans/production_styles.md`
- `plans/rectifications.md`
- `plans/resource_consolidation_2026_10_22.md`
- `plans/runtime_and_providers.md`
- `plans/screenplay.md`
- `plans/text_to_image_folder_references.md`
- `plans/trellis_tts.md`
- `plans/trellis_tts_implementation.md`
- `plans/ui_action_state_matrix.md`
- `plans/ui_improvement.md`
- `plans/ux_shared.md`
- `plans/video_gen.md`

**Retained entrypoints reviewed for concise factual content:**

- `AGENTS.md`
- `README.md`
- `backend/story_builder/workflows/api/three_d/multiview/pixal3d_multiview/README.md`
- `backend/story_builder/workflows/api/three_d/multiview/trellis2_multiview/README.md`

## Source evidence

Exact current-source anchors for review findings/contracts are saved in `audit/review-findings.json`. The bundled blast-radius verifier checks locations and anchors only; it does not certify dependency completeness, measured test coverage or defect severity.

The original documentation-cleanup scores below describe the initial review priority, with resolved statuses shown explicitly. They are not current open defects. The separate [current ACE/Editor impact report](ACE_EDITOR_IMPACT.md) has the application-patch scores and test-evidence gaps. All anchors below match the current source; initial observations are retained in JSON.

| Initial risk range | Node | Current status | File | Verbatim full-line anchor |
| --- | --- | --- | --- | --- |
| 0.40–0.70 | ACE restored intent versus selected panel | RESOLVED | frontend/src/AceStudioPage.tsx:55 | <code>    setConfig({...extras,...project.settings,...(same?saved!.config:{})});const restoredIntent=project.id?(same?saved!.intent:project.intent):&#x27;generate&#x27;;setIntent(restoredIntent);setTab(current=&gt;current===&#x27;settings&#x27;&#124;&#124;current===&#x27;dataset&#x27;?restoredIntent===&#x27;finetune&#x27;?&#x27;dataset&#x27;:&#x27;settings&#x27;:current);setDraft(same?saved!.draft:&#x27;&#x27;);setLoadedKey(&#96;${project.id}:${project.revision}&#96;);setLog(&#x27;&#x27;);</code> |
| 0.40–0.70 | Editor attachment regression test selector | RESOLVED | frontend/tests/editor-assets.spec.mjs:26 | <code>  await page.getByRole(&#x27;navigation&#x27;,{name:&#x27;Editor panels&#x27;}).getByRole(&#x27;button&#x27;,{name:&#x27;Asset selection&#x27;,exact:true}).click();</code> |
| 0.40–0.70 | Editor panel navigation | RESOLVED | frontend/src/VibeEditorPage.tsx:107 | <code>    &lt;nav className=&quot;editor-tabs&quot; aria-label=&quot;Editor panels&quot;&gt;{[&#x27;preview&#x27;,&#x27;media&#x27;,&#x27;timeline&#x27;,&#x27;style&#x27;,&#x27;export&#x27;].map(t=&gt;&lt;button key={t} aria-pressed={tab===t} onClick={()=&gt;chooseTab(t)}&gt;{t===&#x27;media&#x27;?&#x27;Asset selection&#x27;:t}&lt;/button&gt;)}&lt;/nav&gt;</code> |
| 0.40–0.70 | Internal asset drag/drop gap | RESOLVED | frontend/src/VibeEditorPage.tsx:128 | <code>      &lt;form className=&quot;editor-composer&quot; onSubmit={submit} onDragOver={e=&gt;{if(e.dataTransfer.types.includes(&#x27;Files&#x27;)&#124;&#124;e.dataTransfer.types.includes(editorAssetMime))e.preventDefault();}} onDrop={e=&gt;{if(locked)return;if(e.dataTransfer.types.includes(editorAssetMime)){e.preventDefault();const payload=e.dataTransfer.getData(editorAssetMime);void attempt(async()=&gt;{const ids:unknown=JSON.parse(payload);if(!Array.isArray(ids)&#124;&#124;!ids.every(id=&gt;typeof id===&#x27;string&#x27;&amp;&amp;assets.some(a=&gt;a.asset_id===id)))throw new Error(&#x27;Choose assets from this editing session.&#x27;);await attachAssets(assets.filter(a=&gt;ids.includes(a.asset_id)));});return;}if(e.dataTransfer.files.length){e.preventDefault();void attempt(()=&gt;attachFiles(Array.from(e.dataTransfer.files)));}}} onPaste={e=&gt;{const files=Array.from(e.clipboardData.files);if(files.length){e.preventDefault();void attempt(()=&gt;attachFiles(files));}}}&gt;</code> |
| 0.40–0.70 | Composer removal control gap | RESOLVED | frontend/src/VibeEditorPage.tsx:129 | <code>        &lt;div className=&quot;editor-chat-attachments&quot; aria-label=&quot;Chat attachments&quot;&gt;{project.selection.map((r,i)=&gt;&lt;span className=&quot;editor-attachment-chip&quot; key={&#96;${r.asset_id}:${i}&#96;}&gt;&lt;button type=&quot;button&quot; title=&quot;View attachment&quot; onClick={()=&gt;chooseTab(&#x27;media&#x27;)}&gt;{r.filename&#124;&#124;assets.find(a=&gt;a.asset_id===r.asset_id)?.filename&#124;&#124;r.asset_id} · {r.start}–{r.end}s&lt;/button&gt;&lt;button className=&quot;editor-attachment-remove&quot; type=&quot;button&quot; aria-label={&#96;Remove attachment ${i+1}&#96;} disabled={locked} onClick={()=&gt;void attempt(()=&gt;updateSelection(project.selection.filter((_,n)=&gt;n!==i)))}&gt;×&lt;/button&gt;&lt;/span&gt;)}&lt;/div&gt;</code> |
| 0.40–0.70 | Editor media browser gap | RESOLVED | frontend/src/VibeEditorPage.tsx:111 | <code>      &lt;EditorAssetBrowser assets={assets} kind={kind} disabled={locked} onImport={files=&gt;void attempt(()=&gt;attachFiles(files,false))} onAttach={items=&gt;void attempt(()=&gt;attachAssets(items))} onDelete={ids=&gt;void attempt(async()=&gt;{let message=&#x27;&#x27;;try{message=await deleteSelectedMedia(project.workspace_id,ids);}finally{await search();}setNotice(message);})} onPreview={a=&gt;{setSelected(a);setStart(0);setEnd(a.media?.duration_seconds?Math.min(5,a.media.duration_seconds):5);}}/&gt;</code> |
| 0.40–0.70 | Shared output contract | PRESERVED_CONTRACT | backend/story_builder/services/output_destinations.py:90 | <code>def freeze(root, tool, request):</code> |
| 0.40–0.70 | Editor export contract | PRESERVED_CONTRACT | backend/story_builder/services/vibe_editor.py:441 | <code>def export_video(root, project_id, body):</code> |
| 0.40–0.70 | Project directing Markdown reader | PRESERVED_CONTRACT | backend/story_builder/services/director_skills.py:17 | <code>        content = (_ROOT / relative).read_text(encoding=&quot;utf-8&quot;)</code> |
| 0.40–0.70 | Editor directing Markdown reader | PRESERVED_CONTRACT | backend/story_builder/services/vibe_editor.py:392 | <code>    guides = (HUB / &quot;skills&quot; / &quot;vibe-editor-director&quot; / &quot;SKILL.md&quot;).read_text()</code> |
| 0.70–0.70 | Coding instructions conflict | RESOLVED | AGENTS.md:5 | <code>Read only the source, tests and documentation relevant to the task. &#96;audit/FUNCTIONALITY_AUDIT.md&#96; maps current components, preservation contracts and review findings; consult the relevant section when redesigning. &#96;plans/editor_media_output_ace_plan.md&#96; contains the latest requested Editor/ACE changes. Neither document proves live runtime readiness. Current source and user instructions supersede historical proposals.</code> |
| 0.40–0.70 | ACE obsolete setup help | RESOLVED | frontend/src/AceStudioPage.tsx:156 | <code>    {tab===&#x27;runtime&#x27;&amp;&amp;&lt;&gt;&lt;h2&gt;Standalone ACE-Step&lt;/h2&gt;&lt;p&gt;{state?.runtime.reason&#124;&#124;&#x27;Connection has not loaded.&#x27;}&lt;/p&gt;&lt;p&gt;Training encoders: {state?.runtime.training_encoders_cached?&#x27;cached&#x27;:&#x27;MERT / mHuBERT not cached&#x27;}&lt;/p&gt;{Object.entries(state?.runtime.checks&#124;&#124;{}).map(([k,v])=&gt;&lt;p key={k}&gt;{v?&#x27;✓&#x27;:&#x27;–&#x27;} {k}&lt;/p&gt;)}&lt;details&gt;&lt;summary&gt;Runtime locations&lt;/summary&gt;&lt;pre className=&quot;ace-format&quot;&gt;{JSON.stringify({source:state?.runtime.source,python:state?.runtime.python,checkpoints:state?.runtime.checkpoints},null,2)}&lt;/pre&gt;&lt;/details&gt;&lt;p&gt;Check the connection and runtime locations above before starting a job.&lt;/p&gt;&lt;button disabled={busy} onClick={()=&gt;void attempt(refresh)}&gt;Check connection&lt;/button&gt;&lt;/&gt;}</code> |

Cleanup verification: all 71 exact targets are absent; all 100 protected Markdown files remain. Protected content is unchanged except for the documented reference repairs to the foundation, project-director skill and latest plan. The pre-cleanup originals are in `local_data/reports/documentation-cleanup-20261103T054501Z/before-cleanup.tar.gz`. No application code was changed during the documentation cleanup itself. The later authorized ACE/Editor task removed the obsolete setup-help path and implemented the retained plan as described above.


## Project folders and Video library recovery — implementation review, 2026-11-03

The former planning-only investigation is superseded by the implemented folder checkpoint/controller changes. [PROJECT_STORAGE_REVIEW.md](PROJECT_STORAGE_REVIEW.md) contains current behavior, preserved contracts, limitations and the complete 62-boundary impact table. [project-storage-impact.json](project-storage-impact.json) contains verified source anchors; [project-validation.json](project-validation.json) records the baseline comparison and focused checks.

Global New/Open/Save now supplies page context, project-specific settings/chat and output defaults. Existing application ledgers and execution services remain authoritative working storage. Save/Open copies only scoped project state and owned media/results; it does not change project_root, migrate user files, rewrite frozen requests or bundle models/secrets. Editor asset/attachment/Open controls and ACE Create initialization are included. Video libraries preserve successful kinds when another kind fails and no longer depend on stale page-owned workspace selection.

64 unique focused backend cases and 49 unique mocked UI cases pass; production build passes. The broader 136-case suite has 54 failing cases, all also failing at isolated HEAD (56 failing cases). No new failing case names were observed; the repository-wide suite is not green. A complete live all-page project round trip, native folder dialog and generated-media acceptance remain unverified.

Current Graphify refresh: 4,433 nodes / 13,767 edges across 451 code files. Two-hop discovery: 2,567 candidates; 62 boundaries source-confirmed. All 62 anchors pass the bundled citation verifier. Overall impact risk is high, maximum .60 known / 1.00 possible with unknown coverage/caller factors. The graph is an aid, not an exhaustive runtime dependency proof.

Earlier read-only evidence is retained in `project-storage-live-check.json`: 268 registered owner/asset pairs resolved to files. That historical check did not verify decoding or prove directory cleanup caused every screenshot symptom. No user-data migration, provider/GPU run or service restart occurred during this implementation.

## R2V readiness false negative — 2026-11-03

The live installed `MiniMaxH3ReferenceToVideo` exposes `vae` and `audio_vae` as optional sockets, but `validate_comfy_capabilities` checked only required sockets. Both sockets exist and the pinned workflow connects both. The validator now checks their presence across required and optional sockets and names genuinely missing sockets in its error. Reference-group, loader, model, feature-flag, worker and GPU guards remain intact.

Four focused regression tests pass (current optional-VAEs schema, legacy required-VAEs schema, every missing base socket, missing reference groups/video loader). The actual installed `/object_info` passes the patched validator. The broader R2V contract module retains six failures/four errors also present at isolated HEAD, with no new failing case names. No generation was submitted. The selected `male_muscles.png`, `gym_background.png` and `bench_press_reference.mp4` imports existed and matched registered hashes during diagnosis.

Impact is medium (.40 known/.50 possible), scoped to validator → R2V capability → server worker/readiness → Video UI. Source anchors and limits are in `.review/r2v-socket-findings.json`. Graph refreshed after this patch: 4,439 nodes, 13,791 edges.

Live acceptance of readiness only: after API reload and launcher restoration, GET R2V capabilities reports `available: true`, video worker reports available/running, and frontend responds. Automated generation remains gated by verified R2V output; no render was run. The launcher cleanup stopped frontend/workers during the reload; the standard launcher restored them (session 94072).

## Frozen video output destination rejected during preparation — 2026-11-03

Owner-submitted R2V job `cee0bdf6-fac3-4008-9344-71aac127c5f2` failed before engine submission: its valid durable request also contained server-added `output_destination`, which the strict workflow compiler rejected. The earlier socket/readiness repair exposed this separate untested boundary. The same defect was reproduced for T2V and first/last-frame preparation, and in direct retake normalization.

A shared internal projection removes only publication metadata for worker preparation and editable/direct retakes. Preparation verifies the full frozen snapshot hash first. Public input validation remains strict. The ledger, request history, output destination and publication collector retain the complete original snapshot. No workflow graph, engine configuration or GPU guard changed.

Validation: 15 focused CPU tests pass, including all three current workflow modes with/without destination, destination tamper rejection, unknown-field rejection, job creation/idempotency/retake lifecycle, publication recovery and R2V socket checks. Exact failed-job snapshot compiles with mocked staging for its two images and one video. No GPU generation was submitted. Following an idle-queue check, the standard launcher restored API/frontend/image/video workers; live R2V availability is true, automation remains gated, and the failed job is unchanged. Actual generated-media acceptance remains outstanding for the owner's Generate click.

Scoped review: `audit/VIDEO_DESTINATION_REVIEW.md`, `.review/video-destination-findings.json`; 13 source anchors verified, overall high impact priority (.60 known/.70 possible) because frozen job/retake/publication boundaries are shared. No further actionable defect found in this patch review; no measured coverage or exhaustive repository claim. Graph refreshed: 4,450 nodes / 13,827 edges across 455 code files.

## LTX input preview mistaken for final output — 2026-11-03

The stalled owner-submitted R2V job completed its first enhanced chunk, but Comfy history listed the lower-resolution LoadVideo input preview before the SaveVideo output. The collector tried to validate that input as an enhanced chunk, raised a dimension mismatch and retried collection indefinitely. The shared collector now supports opt-in output-only filtering, enabled only by video collection; six other image/audio service callers retain their default behavior. No LTX workflow graph or dimension guard was changed.

13 focused tests pass, including a real CPU/FFmpeg three-chunk overlap stitch with original audio and final-only publication. After a standard service reload, normal recovery accepted the existing completed chunk and resumed the remaining two windows without regenerating the base. The same job `d4ac1943-ea19-44a1-98f7-04b4d3fb7fdc` now has one final output and status `needs_review`: 1344×768, 144 frames at 24 fps, 6-second video, original audio. Saved-file hash verified and local playback returns HTTP 206. The final is saved under `local_data/projects/little-gorilla/d4ac1943-ea19-44a1-98f7-04b4d3fb7fdc/pa-7c5e31fe0d52478e.mp4`. Browser tooling had no connected browser, so visual UI playback remains unverified.

Review and impact evidence: `audit/LTX_COLLECTION_REVIEW.md`, `.review/ltx-collection-findings.json`; 15 verified source anchors, high shared-boundary impact priority (.60 known/.70 possible), no further actionable defect found in the scoped review. Graph refreshed: 4,457 nodes / 13,858 edges across 458 code files.


## Project restoration repair — 2026-11-04

The earlier all-page live-acceptance limitation is narrowed by the [project restoration review](PROJECT_RESTORE_REVIEW.md). Opening the actual `trial 1 scar` folder restores its original accepted screenplay (22 scenes); Save, fresh-browser reload and independent checkpoint restoration into isolated app storage passed. Existing internal folders retain their stable identity, portable manifests expose relative checkpoint paths, server memory takes precedence over stale browser archives, and project-owned Editor/ACE sessions restore when browser selection is missing.

38 focused backend cases, 13 focused browser cases and TypeScript checking passed. The owner project has no generated clips or Editor/ACE sessions for live acceptance; fixture checks cover these boundaries. Native folder-dialog and new generation acceptance remain outstanding. Internal ledgers remain the working store, and Save creates the portable checkpoint. See [validation results](project-restore-validation.json). No whole-repository correctness claim is made.


## Generate rejected pasted audio tag spelling — 2026-11-05

Actual Lion_mouse project draft contained three image references and two voice references, but its edited final prompt used `<audio1>` and `<audio2>`. Existing compiler recognizes `<Audio 1>` and `<Audio 2>`; live CPU Preview returned HTTP 422 `prompt_reference_tags_mismatch`. No new render was running. The rejection message appeared above the scrolled creation controls, making Generate appear unresponsive.

The final prompt now canonicalizes equivalent Picture/Video/Audio tag spellings before speaker binding and request creation. Indices are preserved, so unavailable references still reject. New pending payloads contain canonical spelling; existing frozen attempts are not rewritten. Submission feedback is beside Generate on Create and remains at the top on Current Take. Engines, workflow graphs, admission guards, asset identities, output publication and backend contracts are unchanged.

Live saved-draft Preview now succeeds (15.0833-second aligned duration, 1344×768 final dimensions). No job was created or GPU generation run. Existing retake source is present and `needs_review` with matching project/clip identity. Separate retained stale screenplay preparation/interrupted field-edit notices remain; this patch does not regenerate source prompts or apply interrupted suggestions. The old debug journal is full and contains no current failure evidence; diagnosis uses the actual CPU validation response.

Checks: two new browser regressions pass for canonical submission and invalid-index rejection beside Generate. Video UI suite initially had 29 passes and two duplicate-feedback failures; restricting Create feedback to Create fixes those, and both failures plus both new tests pass on focused rerun. TypeScript and production build pass (existing bundle-size warning). No real rendered-media acceptance claim.

Scoped blast radius: medium, maximum priority 0.40. Source traversal covers final prompt → request builder → Preview/Generate → validation API → existing compiler, plus frozen recovery. Graphify omits nested callbacks, so source is authoritative. No measured coverage claim. Verified citations: `.review/generate-tag-findings.json`.

| Risk | Node | File | Anchor | Reason |
| --- | --- | --- | --- | --- |
| 0.40 | VideoWorkspace | frontend/src/App.tsx:129 | <code>function VideoWorkspace({ view='create', visible=true, workspaceId }: { view?: 'create'&#124;'take'; visible?: boolean; workspaceId: string }) {</code> | Shared Create/Take renderer; feedback appears once at the relevant action area. Existing Next/review regressions pass. |
| 0.25 | bindR2vSpeakers | frontend/src/App.tsx:413 | <code>  const bindR2vSpeakers = (prompt: string) =&gt; {</code> | Canonicalizes numeric tag spelling before speaker binding; new valid/invalid-index UI cases pass. |
| 0.25 | makeRequest | frontend/src/App.tsx:630 | <code>  const makeRequest = (): VideoRequest =&gt; isR2v</code> | Canonical prompt consumed by preview and generation; reference IDs, hashes and order retained. |
| 0.25 | preparePreview | frontend/src/App.tsx:819 | <code>  const preparePreview = async () =&gt; {</code> | Same request builder as Generate; actual live saved draft rejects before patch and passes after. |
| 0.25 | generate | frontend/src/App.tsx:826 | <code>  const generate = async () =&gt; {</code> | Validates before job submission; pending frozen requests and idempotency recovery are unchanged. |
| 0.40 | validateRequest | frontend/src/lib/video-api.ts:39 | <code>export function validateRequest(request: VideoRequest) { return api&lt;any&gt;('/api/video/validations', { method: 'POST', body: JSON.stringify({ request }) }); }</code> | Existing API receives canonical prompt; no endpoint or request schema change. |
| 0.40 | lint_prompt_tags | backend/story_builder/services/minimax_h3_graph_compiler.py:307 | <code>def lint_prompt_tags(prompt: str, reference_map: ResolvedReferenceMap) -&gt; None:</code> | Existing compiler remains strict about connected reference indices and voice bindings. |

## Manual Video recommendations do not gate generation — 2026-11-05

Manual POST `/api/video/jobs` now treats screenplay provenance as advisory: current valid linkage remains, while stale/malformed recommendations cannot reject an otherwise valid prompt, references or duration. Retakes inherit original durable provenance; manual idempotent replay ignores browser recommendation changes but still rejects a different frozen render. Full/Assisted automation keeps strict saved-run admission and cannot opt into the manual mode. Project/media ownership, originals, GPU guards and Turbo → LTX publication paths are unchanged.

Planned clip duration is editable in Video Create. An explicit final R2V prompt does not require a separate main prompt or collation. Definite pre-admission media/contract/readiness failures identify `not_created`, allowing the UI to clear its pending attempt; uncertain responses still retain recovery to prevent duplicate rendering. A pending attempt from before this fix can be recovered with the same saved request/key.

Evidence: new CPU tests cover manual T2V and image/audio R2V, malformed/stale recommendations, valid provenance, retake inheritance, stable replay, changed-request conflicts and the HTTP rejection boundary; worker destination tests also pass. Focused browser tests cover planned duration, custom final prompt, rejection editability, lost responses and retakes. Production build passes with the existing bundle-size warning. No GPU generation run. Detailed impact citations: `.review/manual-video-freedom-findings.json`. Free manual clips without valid provenance remain project media, but are not falsely matched to screenplay slots automatically.

Manual Video recovery follow-up: unsubmitted attempts can now return to editing; delayed submission is fenced atomically, while already admitted jobs are recovered. Missing pending jobs release on reload. See `audit/MANUAL_VIDEO_FREEDOM_REVIEW.md` for the stale-lock cause, focused checks and current live evidence.
