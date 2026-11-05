# Backend component index

All first-party Python service modules present in `backend/story_builder/services` on 2026-11-05. These are implementation components, **not all user-callable tools**. Helpers/workers/validators must be reached through their supported APIs; do not expose every function to the model. This index prevents support components being mistaken for missing features.

## [ace_studio](../backend/story_builder/services/ace_studio.py)

Standalone ACE-Step studio, using the copied engine and shared job/library services.

Public source functions: [`encoder_paths`](../backend/story_builder/services/ace_studio.py#L50), [`runtime`](../backend/story_builder/services/ace_studio.py#L56), [`state`](../backend/story_builder/services/ace_studio.py#L88), [`project`](../backend/story_builder/services/ace_studio.py#L111), [`current_job`](../backend/story_builder/services/ace_studio.py#L119), [`unlocked`](../backend/story_builder/services/ace_studio.py#L123), [`settings`](../backend/story_builder/services/ace_studio.py#L129), [`available_adapters`](../backend/story_builder/services/ace_studio.py#L154), [`snapshot`](../backend/story_builder/services/ace_studio.py#L159), [`add_project`](../backend/story_builder/services/ace_studio.py#L181), [`message`](../backend/story_builder/services/ace_studio.py#L191), [`reference`](../backend/story_builder/services/ace_studio.py#L196), [`dataset`](../backend/story_builder/services/ace_studio.py#L206), [`command`](../backend/story_builder/services/ace_studio.py#L259), [`run_job`](../backend/story_builder/services/ace_studio.py#L334).

## [ace_studio_api](../backend/story_builder/services/ace_studio_api.py)

HTTP seam for the standalone music workspace.

Public source functions: [`handle`](../backend/story_builder/services/ace_studio_api.py#L6).

## [ace_studio_presets](../backend/story_builder/services/ace_studio_presets.py)

Prompt presets copied from ACE-Step v1 acestep/ui/components.py GENRE_PRESETS.

These are editable text templates, not trained model adapters.

## [ace_studio_runner](../backend/story_builder/services/ace_studio_runner.py)

Owned subprocess execution; no ComfyUI graph is submitted for ACE-Step.

Public source functions: [`launch`](../backend/story_builder/services/ace_studio_runner.py#L19), [`pipeline_arguments`](../backend/story_builder/services/ace_studio_runner.py#L66), [`inference_arguments`](../backend/story_builder/services/ace_studio_runner.py#L82), [`execute`](../backend/story_builder/services/ace_studio_runner.py#L87), [`ensure_current`](../backend/story_builder/services/ace_studio_runner.py#L207).

## [assembly](../backend/story_builder/services/assembly.py)

Build a read-only, screenplay-ordered preview of accepted video takes.

Public source functions: [`clip_key`](../backend/story_builder/services/assembly.py#L12), [`validate_assembly_selection`](../backend/story_builder/services/assembly.py#L18), [`validate_assembly_audio_tracks`](../backend/story_builder/services/assembly.py#L36), [`validate_export_settings`](../backend/story_builder/services/assembly.py#L72), [`build_export_manifest`](../backend/story_builder/services/assembly.py#L93), [`build_assembly_snapshot`](../backend/story_builder/services/assembly.py#L106), [`build_assembly_preview`](../backend/story_builder/services/assembly.py#L411).

## [assembly_renderer](../backend/story_builder/services/assembly_renderer.py)

Render a frozen assembly manifest to a new MP4 without modifying inputs.

Public source functions: [`render_manifest`](../backend/story_builder/services/assembly_renderer.py#L52).

## [audio_catalog](../backend/story_builder/services/audio_catalog.py)

Read-only audio capability, voice, and model discovery for the Audio Studio.

Public source functions: [`comfyui_root`](../backend/story_builder/services/audio_catalog.py#L31), [`tts_suite_root`](../backend/story_builder/services/audio_catalog.py#L35), [`voice_roots`](../backend/story_builder/services/audio_catalog.py#L59), [`user_voice_root`](../backend/story_builder/services/audio_catalog.py#L68), [`install_reference_voice`](../backend/story_builder/services/audio_catalog.py#L72), [`comfy_voice_key`](../backend/story_builder/services/audio_catalog.py#L116), [`refresh_live_voice_catalog`](../backend/story_builder/services/audio_catalog.py#L125), [`discover_voices`](../backend/story_builder/services/audio_catalog.py#L154), [`voice_audio_path`](../backend/story_builder/services/audio_catalog.py#L186), [`discover_models`](../backend/story_builder/services/audio_catalog.py#L201), [`f5_dataset_preparation_preflight`](../backend/story_builder/services/audio_catalog.py#L239), [`audio_blocks`](../backend/story_builder/services/audio_catalog.py#L290), [`system_architecture`](../backend/story_builder/services/audio_catalog.py#L308).

## [audio_effects](../backend/story_builder/services/audio_effects.py)

Fixed ComfyUI audio-effect workflows for Audio Studio and Hermes.

Public source functions: [`utc_now`](../backend/story_builder/services/audio_effects.py#L41), [`effect_capabilities`](../backend/story_builder/services/audio_effects.py#L45), [`discover_rvc_models`](../backend/story_builder/services/audio_effects.py#L54), [`safe_project_source`](../backend/story_builder/services/audio_effects.py#L69), [`stage_source`](../backend/story_builder/services/audio_effects.py#L79), [`build_workflow`](../backend/story_builder/services/audio_effects.py#L104), [`validate_duration`](../backend/story_builder/services/audio_effects.py#L165), [`validate_live_nodes`](../backend/story_builder/services/audio_effects.py#L182), [`extract_text`](../backend/story_builder/services/audio_effects.py#L193), [`simple_filter`](../backend/story_builder/services/audio_effects.py#L207), [`run_simple_effect`](../backend/story_builder/services/audio_effects.py#L220), [`run_effect_job`](../backend/story_builder/services/audio_effects.py#L235), [`new_effect_job`](../backend/story_builder/services/audio_effects.py#L292).

## [audio_finetune](../backend/story_builder/services/audio_finetune.py)

Project-scoped F5-TTS dataset validation and preparation.

Adapted from Story Builder's ``audio_finetune`` service. Dataset preparation
stops before training and writes only inside the selected Vibe workspace.

Public source functions: [`utc_now`](../backend/story_builder/services/audio_finetune.py#L37), [`read_metadata`](../backend/story_builder/services/audio_finetune.py#L60), [`build_metadata`](../backend/story_builder/services/audio_finetune.py#L88), [`validate_audio`](../backend/story_builder/services/audio_finetune.py#L100), [`stage_dataset`](../backend/story_builder/services/audio_finetune.py#L123), [`prepare_dataset`](../backend/story_builder/services/audio_finetune.py#L177), [`new_prepare_job`](../backend/story_builder/services/audio_finetune.py#L213).

## [audio_reconstruct](../backend/story_builder/services/audio_reconstruct.py)

Project-owned dialogue reconstruction maps, parts, and immutable takes.

Public source functions: [`session`](../backend/story_builder/services/audio_reconstruct.py#L47), [`calibrate`](../backend/story_builder/services/audio_reconstruct.py#L51), [`add_part`](../backend/story_builder/services/audio_reconstruct.py#L66), [`add_take`](../backend/story_builder/services/audio_reconstruct.py#L82), [`accept_take`](../backend/story_builder/services/audio_reconstruct.py#L102).

## [audio_scene](../backend/story_builder/services/audio_scene.py)

Project-scoped wrappers for the existing TTS-Audio-Suite scene tools.

Public source functions: [`utc_now`](../backend/story_builder/services/audio_scene.py#L22), [`suite_root`](../backend/story_builder/services/audio_scene.py#L26), [`tools_python`](../backend/story_builder/services/audio_scene.py#L30), [`capabilities`](../backend/story_builder/services/audio_scene.py#L34), [`validate_edits`](../backend/story_builder/services/audio_scene.py#L45), [`safe_project_path`](../backend/story_builder/services/audio_scene.py#L71), [`run_split`](../backend/story_builder/services/audio_scene.py#L100), [`run_stitch`](../backend/story_builder/services/audio_scene.py#L127).

## [audio_tts](../backend/story_builder/services/audio_tts.py)

Prepared Phase 2 timed multi-character TTS execution.

Public source functions: [`utc_now`](../backend/story_builder/services/audio_tts.py#L39), [`comfy_voice_key`](../backend/story_builder/services/audio_tts.py#L43), [`voice_character_name`](../backend/story_builder/services/audio_tts.py#L54), [`validate_srt`](../backend/story_builder/services/audio_tts.py#L58), [`prepare_srt`](../backend/story_builder/services/audio_tts.py#L67), [`build_workflow`](../backend/story_builder/services/audio_tts.py#L128), [`extract_text_output`](../backend/story_builder/services/audio_tts.py#L161), [`validate_live_nodes`](../backend/story_builder/services/audio_tts.py#L169), [`run_timed_job`](../backend/story_builder/services/audio_tts.py#L186), [`new_job`](../backend/story_builder/services/audio_tts.py#L220).

## [audio_utilities](../backend/story_builder/services/audio_utilities.py)

Vibe adapter for Story Builder's deterministic audio utility operations.

Public source functions: [`validate_settings`](../backend/story_builder/services/audio_utilities.py#L28), [`capabilities`](../backend/story_builder/services/audio_utilities.py#L123), [`stage_assets`](../backend/story_builder/services/audio_utilities.py#L134), [`run_job`](../backend/story_builder/services/audio_utilities.py#L161).

## [character_voice_bindings](../backend/story_builder/services/character_voice_bindings.py)

Workspace-scoped voice bindings for canonical screenplay characters.

## [control_foley](../backend/story_builder/services/control_foley.py)

Typed Control-Foley jobs backed by fixed ComfyUI API workflows.

Public source functions: [`utc_now`](../backend/story_builder/services/control_foley.py#L33), [`schema`](../backend/story_builder/services/control_foley.py#L37), [`capabilities`](../backend/story_builder/services/control_foley.py#L52), [`validate_settings`](../backend/story_builder/services/control_foley.py#L75), [`new_job`](../backend/story_builder/services/control_foley.py#L100), [`stage_inputs`](../backend/story_builder/services/control_foley.py#L105), [`build_workflow`](../backend/story_builder/services/control_foley.py#L127), [`run_job`](../backend/story_builder/services/control_foley.py#L141).

## [debug_journal](../backend/story_builder/services/debug_journal.py)

Opt-in, bounded local journal for manual UI investigation; never runs workloads.

Public source functions: [`re_valid_session`](../backend/story_builder/services/debug_journal.py#L79).

## [director_skills](../backend/story_builder/services/director_skills.py)

Read versioned project craft guidance; no inference, discovery or submission.

Public source functions: [`director_skill_context`](../backend/story_builder/services/director_skills.py#L10), [`bind_h3_reference_prompt`](../backend/story_builder/services/director_skills.py#L25).

## [editor_effects](../backend/story_builder/services/editor_effects.py)

Bounded editor effects; source media is never modified.

Public source functions: [`number`](../backend/story_builder/services/editor_effects.py#L12), [`validate`](../backend/story_builder/services/editor_effects.py#L22), [`duration`](../backend/story_builder/services/editor_effects.py#L46), [`filters`](../backend/story_builder/services/editor_effects.py#L52), [`preprocess`](../backend/story_builder/services/editor_effects.py#L63).

## [field_edit_proposals](../backend/story_builder/services/field_edit_proposals.py)

Durable, preview-only selected-text suggestions for non-story fields.

## [fully_automated_clip_plan](../backend/story_builder/services/fully_automated_clip_plan.py)

Validate and freeze a Full-mode duration plan before video admission.

The Director proposes the segmentation. This module enforces ordered, exact
coverage of screenplay action/dialogue and the supported video contract.

Public source functions: [`clip_id`](../backend/story_builder/services/fully_automated_clip_plan.py#L27), [`generate_clip_plan`](../backend/story_builder/services/fully_automated_clip_plan.py#L33), [`generate_scene_clip_plan`](../backend/story_builder/services/fully_automated_clip_plan.py#L158), [`validate_clip_plan`](../backend/story_builder/services/fully_automated_clip_plan.py#L181).

## [fully_automated_identity](../backend/story_builder/services/fully_automated_identity.py)

Deterministic, source-bound frame samples for Full-run identity review.

Public source functions: [`sample_identity_frames`](../backend/story_builder/services/fully_automated_identity.py#L25), [`analyze_identity_frames`](../backend/story_builder/services/fully_automated_identity.py#L84), [`validate_identity_observations`](../backend/story_builder/services/fully_automated_identity.py#L185), [`enqueue_completed_full_run_identity_reviews`](../backend/story_builder/services/fully_automated_identity.py#L604).

## [gpu_runtime](../backend/story_builder/services/gpu_runtime.py)

Host-side GPU admission checks and durable telemetry for local ComfyUI work.

Public source functions: [`comfy_container_name`](../backend/story_builder/services/gpu_runtime.py#L34), [`read_gpu_operating_point`](../backend/story_builder/services/gpu_runtime.py#L48), [`read_host_memory_diagnostic`](../backend/story_builder/services/gpu_runtime.py#L98), [`interrupt_if_owned_prompt`](../backend/story_builder/services/gpu_runtime.py#L199), [`inspect_gpu_runtime`](../backend/story_builder/services/gpu_runtime.py#L217), [`record_gpu_telemetry`](../backend/story_builder/services/gpu_runtime.py#L313).

## [gpu_watchdog](../backend/story_builder/services/gpu_watchdog.py)

Prompt-owned thermal supervision, independent of backend HTTP polling.

Run as a detached child so a backend restart does not abandon an active
ComfyUI prompt. Only the exact sole running prompt may be interrupted.

Public source functions: [`finish_prompt_watchdog`](../backend/story_builder/services/gpu_watchdog.py#L63), [`ensure_prompt_watchdog`](../backend/story_builder/services/gpu_watchdog.py#L68), [`supervise`](../backend/story_builder/services/gpu_watchdog.py#L105).

## [image_detailer](../backend/story_builder/services/image_detailer.py)

Evidence-based image detailer facade used by Story Builder.

The detailer deliberately treats auxiliary CV providers as optional evidence and
lets the local Ollama vision model produce the human-readable synthesis.

Public source functions: [`analyze_image`](../backend/story_builder/services/image_detailer.py#L76).

## [image_prompt_drafts](../backend/story_builder/services/image_prompt_drafts.py)

Prepare one editable image prompt from screenplay context and exact workflow guidance.

Public source functions: [`prepare_image_prompt`](../backend/story_builder/services/image_prompt_drafts.py#L24).

## [image_training](../backend/story_builder/services/image_training.py)

Fixed existing Toolkit launcher and provenance-checked Turbo LoRA catalog.

Public source functions: [`health`](../backend/story_builder/services/image_training.py#L10), [`ensure_idle`](../backend/story_builder/services/image_training.py#L17), [`launch`](../backend/story_builder/services/image_training.py#L32), [`checked`](../backend/story_builder/services/image_training.py#L47), [`catalog`](../backend/story_builder/services/image_training.py#L60), [`selection`](../backend/story_builder/services/image_training.py#L70), [`checkpoints`](../backend/story_builder/services/image_training.py#L78), [`publish`](../backend/story_builder/services/image_training.py#L105).

## [isolated_fl2va_assets](../backend/story_builder/services/isolated_fl2va_assets.py)

Resolve and stage frozen FL2VA frame assets; this module never submits jobs.

Public source functions: [`stage_fl2va_frames`](../backend/story_builder/services/isolated_fl2va_assets.py#L87), [`cleanup_fl2va_staging_job`](../backend/story_builder/services/isolated_fl2va_assets.py#L133).

## [isolated_fl2va_contract](../backend/story_builder/services/isolated_fl2va_contract.py)

CPU-only contract and preview compiler for isolated H3 first/last-frame video.

The compiled graph contains symbolic Comfy input filenames. It is not submit-ready:
the future job adapter must resolve the frozen asset IDs/hashes and stage bytes.

Public source functions: [`request_graph_path`](../backend/story_builder/services/isolated_fl2va_contract.py#L27), [`request_digest`](../backend/story_builder/services/isolated_fl2va_contract.py#L35), [`normalize_request`](../backend/story_builder/services/isolated_fl2va_contract.py#L131), [`compile_preview`](../backend/story_builder/services/isolated_fl2va_contract.py#L139).

## [isolated_image_references](../backend/story_builder/services/isolated_image_references.py)

Validate and stage frozen image references for the Qwen edit workflow.

Public source functions: [`validate_image_references`](../backend/story_builder/services/isolated_image_references.py#L36), [`prepare_image_edit_graph`](../backend/story_builder/services/isolated_image_references.py#L88), [`cleanup_image_reference_staging`](../backend/story_builder/services/isolated_image_references.py#L149).

## [isolated_r2v_assets](../backend/story_builder/services/isolated_r2v_assets.py)

Resolve frozen workspace media IDs and stage H3 R2V inputs per job.

Public source functions: [`stage_r2v_references`](../backend/story_builder/services/isolated_r2v_assets.py#L46), [`cleanup_r2v_staging_job`](../backend/story_builder/services/isolated_r2v_assets.py#L112).

## [isolated_r2v_contract](../backend/story_builder/services/isolated_r2v_contract.py)

CPU-only, workspace-asset contract for isolated MiniMax H3 R2V.

Public source functions: [`request_graph_path`](../backend/story_builder/services/isolated_r2v_contract.py#L25), [`request_digest`](../backend/story_builder/services/isolated_r2v_contract.py#L33), [`normalize_request`](../backend/story_builder/services/isolated_r2v_contract.py#L161), [`plan_from_request`](../backend/story_builder/services/isolated_r2v_contract.py#L169), [`compile_preview`](../backend/story_builder/services/isolated_r2v_contract.py#L180).

## [isolated_video_contract](../backend/story_builder/services/isolated_video_contract.py)

CPU-only contract and preview compiler for isolated MiniMax H3 T2V.

This module validates a proposed UI/API payload and can compile a preview graph.
It does not create jobs, check runtime readiness, access ComfyUI, persist data, or
submit work. Preview results predict frame-derived duration; only output probing
can establish a rendered duration.

Public source functions: [`normalize_request`](../backend/story_builder/services/isolated_video_contract.py#L138), [`canonical_request_hash`](../backend/story_builder/services/isolated_video_contract.py#L151), [`compile_preview`](../backend/story_builder/services/isolated_video_contract.py#L157).

## [isolated_video_jobs](../backend/story_builder/services/isolated_video_jobs.py)

Story-free T2V job facade over the existing durable production ledger.

This module owns identity/snapshots only. It deliberately does not start a
worker, probe ComfyUI, submit a prompt, or delete media during construction.

Public source functions: [`story_clip_id`](../backend/story_builder/services/isolated_video_jobs.py#L87), [`prepare_isolated_take`](../backend/story_builder/services/isolated_video_jobs.py#L2933), [`build_worker`](../backend/story_builder/services/isolated_video_jobs.py#L3012), [`make_output_collector`](../backend/story_builder/services/isolated_video_jobs.py#L3087).

## [job_queue_status](../backend/story_builder/services/job_queue_status.py)

Read-only counts for Vibe Director's durable job stores.

Public source functions: [`local_job_queue_status`](../backend/story_builder/services/job_queue_status.py#L59).

## [ltx_chunks](../backend/story_builder/services/ltx_chunks.py)

Bounded LTX staging/joining adapted from ricky/h3_ltx/run_chunked_flow.py.

The existing production worker owns submissions, monitoring and recovery.

Public source functions: [`probe`](../backend/story_builder/services/ltx_chunks.py#L16), [`windows`](../backend/story_builder/services/ltx_chunks.py#L22), [`detect_cuts`](../backend/story_builder/services/ltx_chunks.py#L39), [`split_input`](../backend/story_builder/services/ltx_chunks.py#L44), [`join_chunks`](../backend/story_builder/services/ltx_chunks.py#L59), [`plan_chunks`](../backend/story_builder/services/ltx_chunks.py#L127), [`collect_chunk`](../backend/story_builder/services/ltx_chunks.py#L135).

## [media_discovery](../backend/story_builder/services/media_discovery.py)

Discover media in authorized source folders without moving the user's files.

Public source functions: [`project_locations`](../backend/story_builder/services/media_discovery.py#L23), [`discover`](../backend/story_builder/services/media_discovery.py#L39), [`available`](../backend/story_builder/services/media_discovery.py#L113).

## [media_jobs](../backend/story_builder/services/media_jobs.py)

Generic media job persistence and ComfyUI execution helpers.

Public source functions: [`get_gpu_safety_hold`](../backend/story_builder/services/media_jobs.py#L63), [`clear_gpu_safety_hold`](../backend/story_builder/services/media_jobs.py#L94), [`get_workload_policy`](../backend/story_builder/services/media_jobs.py#L110), [`set_workload_policy`](../backend/story_builder/services/media_jobs.py#L118), [`gpu_workload_lock`](../backend/story_builder/services/media_jobs.py#L146), [`comfy_submission_guard`](../backend/story_builder/services/media_jobs.py#L184), [`wait_for_comfyui_idle`](../backend/story_builder/services/media_jobs.py#L190), [`gpu_workload_guard`](../backend/story_builder/services/media_jobs.py#L221), [`release_comfyui_models_if_idle`](../backend/story_builder/services/media_jobs.py#L286), [`apply_media_inputs`](../backend/story_builder/services/media_jobs.py#L385), [`submit_and_wait`](../backend/story_builder/services/media_jobs.py#L422), [`collect_outputs`](../backend/story_builder/services/media_jobs.py#L546), [`save_uploaded_asset`](../backend/story_builder/services/media_jobs.py#L601).

## [media_library](../backend/story_builder/services/media_library.py)

Workspace media catalogue adapted from Story Builder's production asset contract.

Public source functions: [`media_root`](../backend/story_builder/services/media_library.py#L57), [`shared_run_referenced`](../backend/story_builder/services/media_library.py#L130), [`public_asset_record`](../backend/story_builder/services/media_library.py#L184), [`register_upload`](../backend/story_builder/services/media_library.py#L243), [`delete_temporary_image_asset`](../backend/story_builder/services/media_library.py#L333), [`list_assets`](../backend/story_builder/services/media_library.py#L385), [`set_asset_archived`](../backend/story_builder/services/media_library.py#L429), [`pinned_style_asset_path`](../backend/story_builder/services/media_library.py#L446), [`assign_role`](../backend/story_builder/services/media_library.py#L469), [`update_annotations`](../backend/story_builder/services/media_library.py#L487), [`semantic_annotation_text`](../backend/story_builder/services/media_library.py#L516), [`save_semantic_annotation_index`](../backend/story_builder/services/media_library.py#L525), [`save_semantic_content_index`](../backend/story_builder/services/media_library.py#L557), [`save_image_analysis`](../backend/story_builder/services/media_library.py#L581), [`list_seo_styles`](../backend/story_builder/services/media_library.py#L620), [`create_seo_style`](../backend/story_builder/services/media_library.py#L652), [`update_seo_style`](../backend/story_builder/services/media_library.py#L664), [`delete_seo_style`](../backend/story_builder/services/media_library.py#L679), [`link_style_reference`](../backend/story_builder/services/media_library.py#L694), [`validate_style_reference_frame_request`](../backend/story_builder/services/media_library.py#L745), [`extract_style_reference_frames`](../backend/story_builder/services/media_library.py#L775), [`asset_path`](../backend/story_builder/services/media_library.py#L821), [`register_generated_image`](../backend/story_builder/services/media_library.py#L891), [`register_downloaded_video`](../backend/story_builder/services/media_library.py#L923), [`register_generated_video`](../backend/story_builder/services/media_library.py#L964), [`register_generated_audio`](../backend/story_builder/services/media_library.py#L1007), [`register_derived_media`](../backend/story_builder/services/media_library.py#L1051), [`delete_analysis_assets`](../backend/story_builder/services/media_library.py#L1156), [`delete_extracted_asset`](../backend/story_builder/services/media_library.py#L1197), [`catalogue_source`](../backend/story_builder/services/media_library.py#L1232), [`name_media_workspace`](../backend/story_builder/services/media_library.py#L1246), [`catalogue_workspace_names`](../backend/story_builder/services/media_library.py#L1254), [`reconcile_download_catalogue`](../backend/story_builder/services/media_library.py#L1273), [`browse_catalogue`](../backend/story_builder/services/media_library.py#L1302), [`reuse_catalogue_asset`](../backend/story_builder/services/media_library.py#L1397), [`relocate_output`](../backend/story_builder/services/media_library.py#L1485), [`deletion_preview`](../backend/story_builder/services/media_library.py#L1526), [`delete_media_file`](../backend/story_builder/services/media_library.py#L1577).

## [media_semantic_search](../backend/story_builder/services/media_semantic_search.py)

Workspace-scoped semantic lookup over analyzed Video Summariser records.

Public source functions: [`index_workspace_asset`](../backend/story_builder/services/media_semantic_search.py#L39), [`search_workspace`](../backend/story_builder/services/media_semantic_search.py#L81).

## [minimax_h3_graph_compiler](../backend/story_builder/services/minimax_h3_graph_compiler.py)

Typed, deterministic compiler for local MiniMax H3 reference-to-video graphs.

This module deliberately does not submit ComfyUI jobs or accept paths from a
browser. Callers must resolve project-scoped asset IDs, stage media into the
ComfyUI input directory, and pass the staged basenames as ``ResolvedAsset``
records. The compiler only adds allowlisted loader nodes to a copied API graph.

Public source functions: [`resolution_dimensions`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L44), [`validate_reference_plan`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L187), [`resolve_reference_assets`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L234), [`lint_prompt_tags`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L307), [`load_base_graph`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L324), [`validate_comfy_capabilities`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L334), [`compile_r2v_graph`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L356), [`plan_to_dict`](../backend/story_builder/services/minimax_h3_graph_compiler.py#L460).

## [minimax_h3_media](../backend/story_builder/services/minimax_h3_media.py)

CPU-side media probing and job-owned video staging for local H3 R2V.

Inputs to this module must already be authorized by a project/repertoire
resolver. Source files are read only. ComfyUI receives only unique normalized
clips, and cleanup trusts a per-owner manifest plus content hashes.

Public source functions: [`sha256_file`](../backend/story_builder/services/minimax_h3_media.py#L101), [`probe_media`](../backend/story_builder/services/minimax_h3_media.py#L118), [`stage_video_reference`](../backend/story_builder/services/minimax_h3_media.py#L228), [`stage_image_reference`](../backend/story_builder/services/minimax_h3_media.py#L316), [`stage_audio_reference`](../backend/story_builder/services/minimax_h3_media.py#L369), [`cleanup_owned_media`](../backend/story_builder/services/minimax_h3_media.py#L423).

## [minimax_h3_t2v](../backend/story_builder/services/minimax_h3_t2v.py)

Deterministic compiler for the installed local MiniMax H3 text-to-video graph.

Public source functions: [`final_dimensions`](../backend/story_builder/services/minimax_h3_t2v.py#L19), [`pipeline_digest`](../backend/story_builder/services/minimax_h3_t2v.py#L31), [`turbo_source_dimensions`](../backend/story_builder/services/minimax_h3_t2v.py#L38), [`compile_t2v_graph`](../backend/story_builder/services/minimax_h3_t2v.py#L49).

## [multiview_3d](../backend/story_builder/services/multiview_3d.py)

Small adapters for the prepared Pixal graphs and isolated TRELLIS service.

Public source functions: [`health`](../backend/story_builder/services/multiview_3d.py#L17), [`ensure_ready`](../backend/story_builder/services/multiview_3d.py#L23), [`release_service_if_idle`](../backend/story_builder/services/multiview_3d.py#L36), [`remote_settings`](../backend/story_builder/services/multiview_3d.py#L44), [`pixal_graph`](../backend/story_builder/services/multiview_3d.py#L56), [`prepare_views`](../backend/story_builder/services/multiview_3d.py#L74), [`remote_render`](../backend/story_builder/services/multiview_3d.py#L90), [`reconcile`](../backend/story_builder/services/multiview_3d.py#L136).

## [music_jukebox](../backend/story_builder/services/music_jukebox.py)

Named CPU music projects. Audio rendering uses the browser's shared audio graph;
encoding runs through the existing durable media worker, never a second controller.

Public source functions: [`home`](../backend/story_builder/services/music_jukebox.py#L18), [`identity`](../backend/story_builder/services/music_jukebox.py#L24), [`project_path`](../backend/story_builder/services/music_jukebox.py#L30), [`write`](../backend/story_builder/services/music_jukebox.py#L40), [`locked`](../backend/story_builder/services/music_jukebox.py#L56), [`number`](../backend/story_builder/services/music_jukebox.py#L62), [`validate`](../backend/story_builder/services/music_jukebox.py#L68), [`save`](../backend/story_builder/services/music_jukebox.py#L148), [`export_path`](../backend/story_builder/services/music_jukebox.py#L177), [`snapshot`](../backend/story_builder/services/music_jukebox.py#L190), [`folder`](../backend/story_builder/services/music_jukebox.py#L204), [`granted`](../backend/story_builder/services/music_jukebox.py#L216), [`stage_export`](../backend/story_builder/services/music_jukebox.py#L223), [`encode`](../backend/story_builder/services/music_jukebox.py#L242), [`claim_export`](../backend/story_builder/services/music_jukebox.py#L273).

## [music_jukebox_api](../backend/story_builder/services/music_jukebox_api.py)

Jukebox HTTP seam. No inference or GPU work occurs during editing/export.

Public source functions: [`handle`](../backend/story_builder/services/music_jukebox_api.py#L8).

## [music_sound](../backend/story_builder/services/music_sound.py)

Fixed ACE-Step music jobs and fine-tuning capability contracts.

Public source functions: [`utc_now`](../backend/story_builder/services/music_sound.py#L31), [`capabilities`](../backend/story_builder/services/music_sound.py#L35), [`ace_finetune_preflight`](../backend/story_builder/services/music_sound.py#L45), [`validate_music_settings`](../backend/story_builder/services/music_sound.py#L54), [`new_music_job`](../backend/story_builder/services/music_sound.py#L74), [`build_ace_workflow`](../backend/story_builder/services/music_sound.py#L79), [`run_music_job`](../backend/story_builder/services/music_sound.py#L89).

## [output_destinations](../backend/story_builder/services/output_destinations.py)

Explicit output-folder grants, saved choices and frozen job publication targets.

Public source functions: [`home`](../backend/story_builder/services/output_destinations.py#L23), [`write`](../backend/story_builder/services/output_destinations.py#L26), [`grant`](../backend/story_builder/services/output_destinations.py#L35), [`granted`](../backend/story_builder/services/output_destinations.py#L48), [`preference_path`](../backend/story_builder/services/output_destinations.py#L57), [`resolve`](../backend/story_builder/services/output_destinations.py#L62), [`preference`](../backend/story_builder/services/output_destinations.py#L72), [`freeze`](../backend/story_builder/services/output_destinations.py#L90), [`target_root`](../backend/story_builder/services/output_destinations.py#L104), [`locate_file`](../backend/story_builder/services/output_destinations.py#L115), [`digest`](../backend/story_builder/services/output_destinations.py#L126), [`copy_verified`](../backend/story_builder/services/output_destinations.py#L129), [`finalize`](../backend/story_builder/services/output_destinations.py#L147), [`run_location`](../backend/story_builder/services/output_destinations.py#L175), [`resolve_run_path`](../backend/story_builder/services/output_destinations.py#L181), [`finalize_analysis`](../backend/story_builder/services/output_destinations.py#L202), [`locate_saved_folder`](../backend/story_builder/services/output_destinations.py#L235).

## [performance_journal](../backend/story_builder/services/performance_journal.py)

Opt-in H3 wall-clock measurements. Recording never changes workload admission.

## [production_authority](../backend/story_builder/services/production_authority.py)

Resolve human/Director decision authority from immutable run configuration.

Public source functions: [`director_controls`](../backend/story_builder/services/production_authority.py#L7).

## [production_director_profiles](../backend/story_builder/services/production_director_profiles.py)

Versioned Director behavior profiles, separate from narrative prompt styles.

Public source functions: [`load_registry`](../backend/story_builder/services/production_director_profiles.py#L19), [`resolve_profile`](../backend/story_builder/services/production_director_profiles.py#L39).

## [production_fl2va_capability](../backend/story_builder/services/production_fl2va_capability.py)

Fail-closed, read-only readiness check for isolated MiniMax H3 FL2VA.

Public source functions: [`smoke_manifest_path`](../backend/story_builder/services/production_fl2va_capability.py#L20), [`record_successful_fl2va_smoke`](../backend/story_builder/services/production_fl2va_capability.py#L26), [`fl2va_capability`](../backend/story_builder/services/production_fl2va_capability.py#L31).

## [production_image_admission](../backend/story_builder/services/production_image_admission.py)

Build deterministic checked-stage image batches from accepted screenplay data.

Public source functions: [`build_entity_image_batches`](../backend/story_builder/services/production_image_admission.py#L18), [`build_clip_frame_image_batches`](../backend/story_builder/services/production_image_admission.py#L104), [`build_world_view_image_batch`](../backend/story_builder/services/production_image_admission.py#L226), [`world_view_batch_digest`](../backend/story_builder/services/production_image_admission.py#L278), [`style_context_sha256`](../backend/story_builder/services/production_image_admission.py#L325).

## [production_image_jobs](../backend/story_builder/services/production_image_jobs.py)

Durable project-scoped queue records for production image candidates.

This store deliberately does not talk to ComfyUI. It makes queued image work
restart-safe and auditable before a renderer is connected to the API.
Unknown submissions are never silently re-enqueued.

## [production_image_selection](../backend/story_builder/services/production_image_selection.py)

Durable screenplay-target image choices; bytes remain in the shared media library.

## [production_image_worker](../backend/story_builder/services/production_image_worker.py)

Serialized ComfyUI worker for durable production image candidates.

Public source functions: [`comfyui_root`](../backend/story_builder/services/production_image_worker.py#L36).

## [production_image_workflows](../backend/story_builder/services/production_image_workflows.py)

Typed, fail-closed adapters for the project's ComfyUI image workflows.

This module only prepares graphs and reports readiness. It does not submit a
ComfyUI prompt or load a model; job dispatch is owned by the production worker.

Public source functions: [`comfyui_root`](../backend/story_builder/services/production_image_workflows.py#L26), [`generation_policy`](../backend/story_builder/services/production_image_workflows.py#L92), [`record_successful_image_smoke`](../backend/story_builder/services/production_image_workflows.py#L113), [`image_workflow_catalog`](../backend/story_builder/services/production_image_workflows.py#L146), [`validate_multi_angle_prompt`](../backend/story_builder/services/production_image_workflows.py#L230), [`compile_image_candidates`](../backend/story_builder/services/production_image_workflows.py#L238), [`names_by_slot`](../backend/story_builder/services/production_image_workflows.py#L403), [`image_output_provenance`](../backend/story_builder/services/production_image_workflows.py#L408).

## [production_job_worker](../backend/story_builder/services/production_job_worker.py)

Serialized, durable, testable ComfyUI worker for production V2 H3 takes.

## [production_ledger](../backend/story_builder/services/production_ledger.py)

Durable, project-scoped ledger for the new production pipeline.

This is deliberately separate from the legacy project JSON store and never
stores media bytes. External ComfyUI submission is not performed here.

Public source functions: [`stable_hash`](../backend/story_builder/services/production_ledger.py#L73).

## [production_r2v_capability](../backend/story_builder/services/production_r2v_capability.py)

Fail-closed readiness for Vibe Director's independent MiniMax H3 R2V.

Public source functions: [`smoke_manifest_path`](../backend/story_builder/services/production_r2v_capability.py#L22), [`record_successful_r2v_smoke`](../backend/story_builder/services/production_r2v_capability.py#L30), [`r2v_capability`](../backend/story_builder/services/production_r2v_capability.py#L88).

## [production_reconciliation](../backend/story_builder/services/production_reconciliation.py)

Read-only ComfyUI reconciliation for durable V2 take records.

This service never submits or cancels work. When the durable prompt ID is not
visible in ComfyUI queue/history, it marks the take recovery-required rather
than blindly submitting a duplicate.

Public source functions: [`request_json`](../backend/story_builder/services/production_reconciliation.py#L18), [`history_reports_interrupted`](../backend/story_builder/services/production_reconciliation.py#L34), [`reconcile_comfyui_takes`](../backend/story_builder/services/production_reconciliation.py#L41).

## [production_setup](../backend/story_builder/services/production_setup.py)

Durable, revision-scoped automation policy before prompt preparation.

## [production_story_revisions](../backend/story_builder/services/production_story_revisions.py)

Atomic, run-scoped story canon revisions for production V2.

Public source functions: [`revision_root`](../backend/story_builder/services/production_story_revisions.py#L15), [`write_revision`](../backend/story_builder/services/production_story_revisions.py#L32), [`load_revision`](../backend/story_builder/services/production_story_revisions.py#L58), [`list_revisions`](../backend/story_builder/services/production_story_revisions.py#L72), [`write_stage_revision`](../backend/story_builder/services/production_story_revisions.py#L84), [`load_stage_revision`](../backend/story_builder/services/production_story_revisions.py#L111), [`list_stage_revisions`](../backend/story_builder/services/production_story_revisions.py#L127).

## [production_styles](../backend/story_builder/services/production_styles.py)

Versioned production style and type setup on the shared production ledger.

This service owns setup snapshots only. It does not extract/analyze media or
submit generation jobs. Guidance and Director profiles are frozen in published
versions; selections are append-only snapshots tied to one context.

## [production_t2v_capability](../backend/story_builder/services/production_t2v_capability.py)

Fail-closed preflight for the separately tested H3 T2V production route.

Public source functions: [`feature_enabled`](../backend/story_builder/services/production_t2v_capability.py#L20), [`smoke_manifest_path`](../backend/story_builder/services/production_t2v_capability.py#L32), [`record_successful_t2v_smoke`](../backend/story_builder/services/production_t2v_capability.py#L43), [`t2v_capability`](../backend/story_builder/services/production_t2v_capability.py#L88).

## [projects](../backend/story_builder/services/projects.py)

Folder checkpoints for one project; existing ledgers and workers remain authoritative.

Only project rows/files are exported. Models, credentials and other projects never
enter a checkpoint. Opening never replaces newer local work.

Public source functions: [`configure`](../backend/story_builder/services/projects.py#L23), [`database_path`](../backend/story_builder/services/projects.py#L26), [`home`](../backend/story_builder/services/projects.py#L32), [`locked`](../backend/story_builder/services/projects.py#L39), [`read`](../backend/story_builder/services/projects.py#L45), [`digest`](../backend/story_builder/services/projects.py#L51), [`identity`](../backend/story_builder/services/projects.py#L56), [`records`](../backend/story_builder/services/projects.py#L62), [`current`](../backend/story_builder/services/projects.py#L66), [`browser_state`](../backend/story_builder/services/projects.py#L91), [`sql_snapshot`](../backend/story_builder/services/projects.py#L102), [`assert_idle`](../backend/story_builder/services/projects.py#L135), [`folder_path`](../backend/story_builder/services/projects.py#L146), [`existing_project`](../backend/story_builder/services/projects.py#L155), [`owned_files`](../backend/story_builder/services/projects.py#L178), [`valid_runtime`](../backend/story_builder/services/projects.py#L279), [`session_grants`](../backend/story_builder/services/projects.py#L287), [`validate_folder`](../backend/story_builder/services/projects.py#L312), [`output_defaults`](../backend/story_builder/services/projects.py#L323), [`save`](../backend/story_builder/services/projects.py#L338), [`activate`](../backend/story_builder/services/projects.py#L418), [`open_project`](../backend/story_builder/services/projects.py#L424), [`handle`](../backend/story_builder/services/projects.py#L647).

## [prompt_director](../backend/story_builder/services/prompt_director.py)

Project-owned prompt discussions, reusable lessons and image briefs. No generation.

Public source functions: [`read_guidance`](../backend/story_builder/services/prompt_director.py#L14), [`image_brief`](../backend/story_builder/services/prompt_director.py#L29).

## [prompt_drafts](../backend/story_builder/services/prompt_drafts.py)

Durable editable prompt drafts tied to the current screenplay and setup.

## [prompt_styles](../backend/story_builder/services/prompt_styles.py)

Versioned production-style prompt packs used by automation runs.

Public source functions: [`list_styles`](../backend/story_builder/services/prompt_styles.py#L23), [`get_style`](../backend/story_builder/services/prompt_styles.py#L33).

## [provider_exec_guard](../backend/story_builder/services/provider_exec_guard.py)

Arm Linux parent-death cleanup before replacing this process with a provider CLI.

Public source functions: [`main`](../backend/story_builder/services/provider_exec_guard.py#L11).

## [reasoning_backends](../backend/story_builder/services/reasoning_backends.py)

Configured OpenCode models and local Ollama; no inference during discovery.

Ollama request/GPU admission adapted from mooV_E_maker/services/ollama_client.py.
OpenCode CLI/config: https://opencode.ai/docs/cli/ and /docs/permissions/.

Public source functions: [`ollama_host`](../backend/story_builder/services/reasoning_backends.py#L24), [`discover`](../backend/story_builder/services/reasoning_backends.py#L29), [`image_files`](../backend/story_builder/services/reasoning_backends.py#L71), [`generate`](../backend/story_builder/services/reasoning_backends.py#L85).

## [reasoning_provider](../backend/story_builder/services/reasoning_provider.py)

Structured reasoning adapter reused from Story Builder for Vibe Director.

This adapter deliberately exposes model reasoning only. Media executors,
ComfyUI jobs, storage writes, and application authorization stay in their
existing services. Codex runs with no project working directory and no
write-enabled agent sandbox.

Public source functions: [`model_catalog`](../backend/story_builder/services/reasoning_provider.py#L41), [`get_settings`](../backend/story_builder/services/reasoning_provider.py#L69), [`save_settings`](../backend/story_builder/services/reasoning_provider.py#L83), [`set_provider`](../backend/story_builder/services/reasoning_provider.py#L115), [`use_provider`](../backend/story_builder/services/reasoning_provider.py#L122), [`activate_provider`](../backend/story_builder/services/reasoning_provider.py#L137), [`reset_provider`](../backend/story_builder/services/reasoning_provider.py#L147), [`provider_catalog`](../backend/story_builder/services/reasoning_provider.py#L160), [`generate_json`](../backend/story_builder/services/reasoning_provider.py#L309), [`test_provider`](../backend/story_builder/services/reasoning_provider.py#L344), [`model_for`](../backend/story_builder/services/reasoning_provider.py#L369).

## [reasoning_status](../backend/story_builder/services/reasoning_status.py)

Read-only provider allowance and last-request telemetry; never starts a turn.

Public source functions: [`record_usage`](../backend/story_builder/services/reasoning_status.py#L18), [`normalize_limits`](../backend/story_builder/services/reasoning_status.py#L75), [`provider_status`](../backend/story_builder/services/reasoning_status.py#L93).

## [sam_audio_vibe](../backend/story_builder/services/sam_audio_vibe.py)

Workspace-scoped SAM Audio preview and explicit save adapter for Vibe.

Public source functions: [`readiness`](../backend/story_builder/services/sam_audio_vibe.py#L36), [`isolate_event`](../backend/story_builder/services/sam_audio_vibe.py#L94), [`preview_path`](../backend/story_builder/services/sam_audio_vibe.py#L133), [`save_preview`](../backend/story_builder/services/sam_audio_vibe.py#L164), [`discard_preview`](../backend/story_builder/services/sam_audio_vibe.py#L203).

## [screenplay_schema](../backend/story_builder/services/screenplay_schema.py)

Codex structured-output contract; semantic/evidence validation stays in StoryAuthoring.

## [source_chunks](../backend/story_builder/services/source_chunks.py)

Provenance-preserving source chunk primitives extracted for story revisions.

Source: mooV_E_maker/services/chunked_generation.py at
2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db (SourceChunk and
split_source_text only). Kept provider-free for source indexing and CPU tests.

Public source functions: [`split_source_text`](../backend/story_builder/services/source_chunks.py#L22).

## [storage_paths](../backend/story_builder/services/storage_paths.py)

Canonical storage and explicit historical-location translation; no filesystem links.

Public source functions: [`checked`](../backend/story_builder/services/storage_paths.py#L7), [`project_folders`](../backend/story_builder/services/storage_paths.py#L19), [`project_identity`](../backend/story_builder/services/storage_paths.py#L35), [`project_root`](../backend/story_builder/services/storage_paths.py#L39), [`media_root`](../backend/story_builder/services/storage_paths.py#L53), [`generated_root`](../backend/story_builder/services/storage_paths.py#L57), [`intermediate_root`](../backend/story_builder/services/storage_paths.py#L61), [`shared_downloads_root`](../backend/story_builder/services/storage_paths.py#L65), [`repertoire_root`](../backend/story_builder/services/storage_paths.py#L69), [`ace_root`](../backend/story_builder/services/storage_paths.py#L73), [`shared_file`](../backend/story_builder/services/storage_paths.py#L77), [`relocated_path`](../backend/story_builder/services/storage_paths.py#L122), [`relocate_record_paths`](../backend/story_builder/services/storage_paths.py#L155), [`load_project_documents`](../backend/story_builder/services/storage_paths.py#L173), [`save_project_documents`](../backend/story_builder/services/storage_paths.py#L192).

## [story_authoring](../backend/story_builder/services/story_authoring.py)

CPU-only story source revisions and exact selected-text edit proposals.

This is a revision foundation, not the Codex collaborator, graph builder, or
screenplay derivation service. Revision files use the reused atomic V2 writer;
SQLite's story index/current pointer is authoritative for current state.

## [story_imports](../backend/story_builder/services/story_imports.py)

Persistent, exact-text story imports for the local story API.

Text and Markdown preserve decoded UTF-8 codepoints and line endings. PDF
extraction uses pdftotext layout output as a preview; it never claims OCR or
reading-order correctness.

## [storyboard](../backend/story_builder/services/storyboard.py)

Revisioned scene/storyboard preparation; generation stays in existing job services.

Public source functions: [`automatic_route_allowed`](../backend/story_builder/services/storyboard.py#L22), [`text`](../backend/story_builder/services/storyboard.py#L27), [`validate_shot_kind`](../backend/story_builder/services/storyboard.py#L33).

## [studio_checkpoints](../backend/story_builder/services/studio_checkpoints.py)

Manage only identified trained artifacts, never datasets or shared base weights.

Public source functions: [`fingerprint`](../backend/story_builder/services/studio_checkpoints.py#L9), [`catalog`](../backend/story_builder/services/studio_checkpoints.py#L20), [`assert_idle`](../backend/story_builder/services/studio_checkpoints.py#L43), [`delete`](../backend/story_builder/services/studio_checkpoints.py#L55).

## [studio_tools_api](../backend/story_builder/services/studio_tools_api.py)

Explicit local studio actions; no generic command execution surface.

Public source functions: [`handle`](../backend/story_builder/services/studio_tools_api.py#L7).

## [style_sources](../backend/story_builder/services/style_sources.py)

Safe text extraction with page/line evidence locators for style references.

Public source functions: [`extract_style_source`](../backend/story_builder/services/style_sources.py#L46), [`store_style_source`](../backend/story_builder/services/style_sources.py#L129), [`list_style_sources`](../backend/story_builder/services/style_sources.py#L152), [`get_style_source`](../backend/story_builder/services/style_sources.py#L169), [`propose_style_guidance`](../backend/story_builder/services/style_sources.py#L182), [`propose_image_style_guidance`](../backend/story_builder/services/style_sources.py#L236).

## [t2v_batches](../backend/story_builder/services/t2v_batches.py)

Sequential T2V manifests; the existing production worker owns all GPU execution.

Public source functions: [`parse_batch`](../backend/story_builder/services/t2v_batches.py#L19).

## [t2v_pipeline](../backend/story_builder/services/t2v_pipeline.py)

CPU preparation and exact-output remux for the pinned Turbo → LTX route.

Adapted from setup_comfy_and-stuff/env_setup/h3_ltx_20261023/scripts/
prepare_ltx_input.py and remux_original_audio.py (local tested recipe).
Models and custom nodes remain in the shared ComfyUI runtime.

Public source functions: [`is_pipeline`](../backend/story_builder/services/t2v_pipeline.py#L20), [`digest`](../backend/story_builder/services/t2v_pipeline.py#L25), [`probe`](../backend/story_builder/services/t2v_pipeline.py#L33), [`video_stream`](../backend/story_builder/services/t2v_pipeline.py#L40), [`prepare_refinement`](../backend/story_builder/services/t2v_pipeline.py#L49), [`remux_final`](../backend/story_builder/services/t2v_pipeline.py#L100).

## [trellis_studio](../backend/story_builder/services/trellis_studio.py)

Image-to-3D adapter using the shared durable dispatcher and GPU guard.

Public source functions: [`home`](../backend/story_builder/services/trellis_studio.py#L18), [`layout`](../backend/story_builder/services/trellis_studio.py#L21), [`write`](../backend/story_builder/services/trellis_studio.py#L25), [`image_path`](../backend/story_builder/services/trellis_studio.py#L28), [`upload`](../backend/story_builder/services/trellis_studio.py#L33), [`compile_graph`](../backend/story_builder/services/trellis_studio.py#L44), [`validate_glb`](../backend/story_builder/services/trellis_studio.py#L57), [`output_folder`](../backend/story_builder/services/trellis_studio.py#L74), [`choose_folder`](../backend/story_builder/services/trellis_studio.py#L82), [`grant_folder`](../backend/story_builder/services/trellis_studio.py#L88), [`create`](../backend/story_builder/services/trellis_studio.py#L95), [`result_path`](../backend/story_builder/services/trellis_studio.py#L140), [`validate_graph`](../backend/story_builder/services/trellis_studio.py#L154), [`run_job`](../backend/story_builder/services/trellis_studio.py#L179), [`open_blender`](../backend/story_builder/services/trellis_studio.py#L292).

## [vibe_editor](../backend/story_builder/services/vibe_editor.py)

Project-local editing state, revision approvals and shared Media Prep jobs.

Public source functions: [`now`](../backend/story_builder/services/vibe_editor.py#L27), [`text`](../backend/story_builder/services/vibe_editor.py#L31), [`ident`](../backend/story_builder/services/vibe_editor.py#L37), [`write`](../backend/story_builder/services/vibe_editor.py#L43), [`state`](../backend/story_builder/services/vibe_editor.py#L54), [`project`](../backend/story_builder/services/vibe_editor.py#L66), [`style`](../backend/story_builder/services/vibe_editor.py#L74), [`clarification_questions`](../backend/story_builder/services/vibe_editor.py#L81), [`snapshot`](../backend/story_builder/services/vibe_editor.py#L95), [`add_project`](../backend/story_builder/services/vibe_editor.py#L106), [`change_style`](../backend/story_builder/services/vibe_editor.py#L116), [`saved_job`](../backend/story_builder/services/vibe_editor.py#L153), [`busy`](../backend/story_builder/services/vibe_editor.py#L162), [`validate_selection`](../backend/story_builder/services/vibe_editor.py#L169), [`update_project`](../backend/story_builder/services/vibe_editor.py#L191), [`message`](../backend/story_builder/services/vibe_editor.py#L219), [`command`](../backend/story_builder/services/vibe_editor.py#L231), [`validate_plan`](../backend/story_builder/services/vibe_editor.py#L322), [`propose_plan`](../backend/story_builder/services/vibe_editor.py#L351), [`run_job`](../backend/story_builder/services/vibe_editor.py#L379), [`export_video`](../backend/story_builder/services/vibe_editor.py#L441).

## [vibe_editor_api](../backend/story_builder/services/vibe_editor_api.py)

Small HTTP seam for editor projects; media still uses the shared library API.

Public source functions: [`handle`](../backend/story_builder/services/vibe_editor_api.py#L7).

## [vibe_editor_render](../backend/story_builder/services/vibe_editor_render.py)

Trusted JSON-to-HyperFrames adapter. No provider-authored HTML or shell execution.

Public source functions: [`capability`](../backend/story_builder/services/vibe_editor_render.py#L22), [`render`](../backend/story_builder/services/vibe_editor_render.py#L54).

## [video_continuity](../backend/story_builder/services/video_continuity.py)

Hash-bound last-frame continuity; no provider calls or video submission.

Public source functions: [`last_frame`](../backend/story_builder/services/video_continuity.py#L13).

## [video_repertoire](../backend/story_builder/services/video_repertoire.py)

Managed video repertoire assets and subprocess jobs.

Public source functions: [`configure_roots`](../backend/story_builder/services/video_repertoire.py#L41), [`youtube_downloads_root`](../backend/story_builder/services/video_repertoire.py#L59), [`analyzer_runs_root`](../backend/story_builder/services/video_repertoire.py#L65), [`utc_now`](../backend/story_builder/services/video_repertoire.py#L79), [`ensure_layout`](../backend/story_builder/services/video_repertoire.py#L83), [`safe_path`](../backend/story_builder/services/video_repertoire.py#L108), [`sha256_file`](../backend/story_builder/services/video_repertoire.py#L130), [`list_staged_donor_videos`](../backend/story_builder/services/video_repertoire.py#L138), [`staged_donor_video_path`](../backend/story_builder/services/video_repertoire.py#L185), [`list_staged_donor_analysis`](../backend/story_builder/services/video_repertoire.py#L256), [`import_staged_donor_analysis_audio`](../backend/story_builder/services/video_repertoire.py#L266), [`import_staged_donor_videos`](../backend/story_builder/services/video_repertoire.py#L317), [`asset_manifest_path`](../backend/story_builder/services/video_repertoire.py#L437), [`register_asset`](../backend/story_builder/services/video_repertoire.py#L441), [`stage_workspace_video_assets`](../backend/story_builder/services/video_repertoire.py#L480), [`list_assets`](../backend/story_builder/services/video_repertoire.py#L537), [`list_audio_assets`](../backend/story_builder/services/video_repertoire.py#L554), [`delete_audio_assets`](../backend/story_builder/services/video_repertoire.py#L656), [`get_asset`](../backend/story_builder/services/video_repertoire.py#L725), [`delete_assets`](../backend/story_builder/services/video_repertoire.py#L732), [`import_legacy_assets`](../backend/story_builder/services/video_repertoire.py#L769), [`create_uploaded_asset`](../backend/story_builder/services/video_repertoire.py#L779), [`job_path`](../backend/story_builder/services/video_repertoire.py#L794), [`create_job`](../backend/story_builder/services/video_repertoire.py#L806), [`read_job`](../backend/story_builder/services/video_repertoire.py#L832), [`list_jobs`](../backend/story_builder/services/video_repertoire.py#L843), [`start_job`](../backend/story_builder/services/video_repertoire.py#L975), [`cancel_job`](../backend/story_builder/services/video_repertoire.py#L991), [`stop_and_delete_analysis_job`](../backend/story_builder/services/video_repertoire.py#L1211), [`delete_analysis_job`](../backend/story_builder/services/video_repertoire.py#L1240), [`capabilities`](../backend/story_builder/services/video_repertoire.py#L1250), [`resolve_youtube_sources`](../backend/story_builder/services/video_repertoire.py#L1305), [`search_records`](../backend/story_builder/services/video_repertoire.py#L1348), [`safe_artifact_path`](../backend/story_builder/services/video_repertoire.py#L1369).

## [video_repertoire_worker](../backend/story_builder/services/video_repertoire_worker.py)

Subprocess worker for Video Repertoire download and analysis jobs.

Public source functions: [`save_job`](../backend/story_builder/services/video_repertoire_worker.py#L86), [`event`](../backend/story_builder/services/video_repertoire_worker.py#L96), [`run_youtube`](../backend/story_builder/services/video_repertoire_worker.py#L249), [`run_analysis`](../backend/story_builder/services/video_repertoire_worker.py#L474), [`run_image_detailer`](../backend/story_builder/services/video_repertoire_worker.py#L686), [`run_style_frames`](../backend/story_builder/services/video_repertoire_worker.py#L712), [`run_semantic_index`](../backend/story_builder/services/video_repertoire_worker.py#L725), [`run_timed_tts`](../backend/story_builder/services/video_repertoire_worker.py#L810), [`publish_completed_result`](../backend/story_builder/services/video_repertoire_worker.py#L1126), [`main`](../backend/story_builder/services/video_repertoire_worker.py#L1135).

## [video_summarizer_capability](../backend/story_builder/services/video_summarizer_capability.py)

Read-only readiness snapshot for the adapted Video Summariser integration.

Public source functions: [`video_summarizer_capability`](../backend/story_builder/services/video_summarizer_capability.py#L34).

## [video_summarizer_results](../backend/story_builder/services/video_summarizer_results.py)

Register canonical analyzer artifacts without making workspace copies.

Public source functions: [`publish_analyzer_outputs`](../backend/story_builder/services/video_summarizer_results.py#L19).

## [voice_studio](../backend/story_builder/services/voice_studio.py)

Additional speech/design/training graphs on the existing durable Comfy dispatcher.

Public source functions: [`node`](../backend/story_builder/services/voice_studio.py#L13), [`compile_graph`](../backend/story_builder/services/voice_studio.py#L23), [`live_ready`](../backend/story_builder/services/voice_studio.py#L53), [`training_artifacts`](../backend/story_builder/services/voice_studio.py#L65), [`progress`](../backend/story_builder/services/voice_studio.py#L90), [`capabilities`](../backend/story_builder/services/voice_studio.py#L101), [`create`](../backend/story_builder/services/voice_studio.py#L119), [`run`](../backend/story_builder/services/voice_studio.py#L141).

## [workflow_knowledge](../backend/story_builder/services/workflow_knowledge.py)

Immutable, source-linked workflow knowledge snapshots.

This is a small SQLite-backed graph store, not a runtime capability check. Its
facts describe the selected workflow's prompt contract and reference rules;
the caller must still check whether the graph, models, nodes, worker and GPU
are available before submitting a job.

## [workflow_knowledge_catalog](../backend/story_builder/services/workflow_knowledge_catalog.py)

Version-pinned prompt guidance for local ComfyUI workflow graphs.

Video records cite pinned vendor guidance and the matching local graph. Image
records combine local graph/adapter facts with separately labeled, sourced
vendor examples. Neither record asserts that ComfyUI has its model files or
runtime nodes installed.

Public source functions: [`seed_minimax_h3_workflow_knowledge`](../backend/story_builder/services/workflow_knowledge_catalog.py#L51), [`seed_image_workflow_knowledge`](../backend/story_builder/services/workflow_knowledge_catalog.py#L195), [`seed_audio_workflow_knowledge`](../backend/story_builder/services/workflow_knowledge_catalog.py#L262).

## [workflow_status](../backend/story_builder/services/workflow_status.py)

Read-only status projection for the isolated UI.

It accepts the established T2V capability snapshot instead of independently
probing ComfyUI, loading models, checking GPU safety, or dispatching work.

Public source functions: [`build_workflow_status`](../backend/story_builder/services/workflow_status.py#L125).

