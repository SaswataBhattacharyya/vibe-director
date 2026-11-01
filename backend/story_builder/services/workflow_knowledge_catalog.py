"""Version-pinned prompt guidance for local ComfyUI workflow graphs.

Video records cite pinned vendor guidance and the matching local graph. Image
records combine local graph/adapter facts with separately labeled, sourced
vendor examples. Neither record asserts that ComfyUI has its model files or
runtime nodes installed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from story_builder.services.workflow_knowledge import WorkflowKnowledge
from story_builder.services.production_image_workflows import IMAGE_PROMPT_MAX_CODEPOINTS, SPECS as IMAGE_SPECS

ROOT = Path(__file__).resolve().parents[1]
_BASE_COMMIT = "ce18b0e8462a05d7dbf960e3e3a3517570f20b07"
_REF_COMMIT = "4ae026f2ceb16f16e0aad0e7c5c5fb2699e67dae"
_GUIDANCE = {
    "minimax_h3_t2v_local_v1": {
        "workflow": "minimax_h3_turbo_t2v_api.json", "version": "2",
        "guide": "https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/" + _BASE_COMMIT + "/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md",
        "guide_version": _BASE_COMMIT, "guide_section": "Prompt structure and integrated multimodal description",
        "facts": [
            ("shot_description", "Describe one coherent shot with explicit subject, action, setting, and camera behavior."),
            ("soundscape", "When sound is relevant, distinguish in-scene sound from non-diegetic music; keep the visual and audio direction aligned."),
        ],
    },
    "minimax_h3_fl2va_first_last_v1": {
        "workflow": "minimax_h3_fl2va_first_last_api.json", "version": "1",
        "guide": "https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/" + _BASE_COMMIT + "/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md",
        "guide_version": _BASE_COMMIT, "guide_section": "First-and-last-frame video generation",
        "facts": [
            ("frame_interpolation", "Describe the continuous action that connects the supplied first frame to the supplied last frame; preserve their intended visual continuity."),
            ("shot_description", "Describe one coherent shot with explicit subject, action, setting, and camera behavior."),
        ],
    },
    "minimax_h3_r2v_dynamic_v1": {
        "workflow": "minimax_h3_r2v_api.json", "version": "1",
        "guide": "https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/" + _REF_COMMIT + "/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md",
        "guide_version": _REF_COMMIT, "guide_section": "Reference labels and six-part prompt structure",
        "facts": [
            ("reference_labels", "Use the model's indexed Subject, Picture, Video, and Audio reference labels only when those references are actually supplied, and keep each reference's intended role explicit."),
            ("reference_intent", "Describe how each selected reference should guide the new clip; do not imply that an unselected reference is available to the model."),
            ("shot_description", "Organize reference-video direction around the requested subject, visual content, motion, and audio intent while preserving one coherent shot."),
        ],
    },
}


def seed_minimax_h3_workflow_knowledge(store: WorkflowKnowledge) -> list[dict]:
    """Idempotently publish facts bound to the current local API JSON hashes."""
    from story_builder.services import isolated_fl2va_contract, isolated_r2v_contract, isolated_video_contract
    from story_builder.services import minimax_h3_graph_compiler

    preset_text = lambda presets: ", ".join(
        f"{key:g}={width}x{height}" for key, (width, height) in sorted(presets.items()))
    local_contracts = {
        "minimax_h3_t2v_local_v1": (
            "Local request contract: prompt is under 7,000 Unicode code points; duration 5–30 seconds (above the installed node’s ~15-second trained range is untested); aspect ratios 16:9, 9:16, 4:3, 3:4, 1:1; "
            f"resolution presets {preset_text(isolated_video_contract.T2V_RESOLUTION_PRESETS)} describe final output; H3 Turbo 4 steps then low-noise LTX 3 steps with original H3 audio; seed fixed at 1; no references.",
            ["isolated_video_contract.py", "minimax_h3_graph_compiler.py"]),
        "minimax_h3_fl2va_first_last_v1": (
            "Local request contract: prompt is under 7,000 Unicode code points; duration 5–15 seconds; 16:9 only; "
            f"resolution presets {preset_text(isolated_fl2va_contract.RESOLUTION_PRESETS)}; steps fixed at 20; seed fixed at 1; "
            "both first_frame and last_frame are required workspace asset IDs with SHA-256 hashes. Compiled frames are aligned to the model's 17k+5 frame rule at 24 fps.",
            ["isolated_fl2va_contract.py"]),
        "minimax_h3_r2v_dynamic_v1": (
            "Local request contract: prompt is under 7,000 Unicode code points; duration 5–15 seconds; 16:9 only; "
            f"resolution presets {preset_text(minimax_h3_graph_compiler.RESOLUTION_PRESETS)}; steps 8–40; seed is unsigned 32-bit; "
            f"ref_image_size is match or max; at most {minimax_h3_graph_compiler.MAX_IMAGES} images, "
            f"{minimax_h3_graph_compiler.MAX_VIDEOS} videos and {minimax_h3_graph_compiler.MAX_AUDIOS} standalone audio refs; "
            f"each selected video excerpt is at most {minimax_h3_graph_compiler.MAX_REFERENCE_SECONDS:g} seconds. References use workspace asset IDs and frozen SHA-256 hashes.",
            ["isolated_r2v_contract.py", "minimax_h3_graph_compiler.py"]),
    }
    published = []
    for workflow_id, item in _GUIDANCE.items():
        graph_path = ROOT / "workflows" / "api" / item["workflow"]
        if not graph_path.is_file():
            continue
        workflow_hash = (isolated_video_contract.pipeline_digest() if workflow_id == "minimax_h3_t2v_local_v1"
            else hashlib.sha256(graph_path.read_bytes()).hexdigest())
        sources = []
        nodes = []
        edges = []
        for index, (kind, text) in enumerate(item["facts"], start=1):
            node_id = f"{kind}_{index}"
            guide_source = f"guide_{index}"
            graph_source = f"graph_{index}"
            evidence_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            nodes.append({"node_id": node_id, "kind": kind, "text": text,
                "source_ids": [guide_source, graph_source]})
            for source_id, uri, version, section in (
                (guide_source, item["guide"], item["guide_version"], item["guide_section"]),
                (graph_source, graph_path.relative_to(ROOT).as_posix(), workflow_hash,
                    "Pinned local ComfyUI API graph SHA-256"),
            ):
                sources.append({"source_id": source_id, "uri": uri, "version": version,
                    "section": section, "sha256": evidence_hash})
            if index > 1:
                edges.append({"from": f"{item['facts'][index-2][0]}_{index-1}",
                    "relation": "used_with", "to": node_id})
        contract_text, contract_files = local_contracts[workflow_id]
        contract_node_id = "local_parameter_contract"
        contract_source_ids = ["local_graph_contract"]
        evidence_hash = hashlib.sha256(contract_text.encode("utf-8")).hexdigest()
        nodes.append({"node_id": contract_node_id, "kind": "parameter_contract",
            "text": contract_text, "source_ids": contract_source_ids.copy()})
        sources.append({"source_id": "local_graph_contract",
            "uri": graph_path.relative_to(ROOT).as_posix(), "version": workflow_hash,
            "section": "Pinned local ComfyUI API graph and adapter input contract",
            "sha256": evidence_hash})
        for contract_file in contract_files:
            path = ROOT / "services" / contract_file
            if not path.is_file():
                continue
            source_id = f"contract_{path.stem}"
            contract_source_ids.append(source_id)
            sources.append({"source_id": source_id,
                "uri": path.relative_to(ROOT).as_posix(),
                "version": hashlib.sha256(path.read_bytes()).hexdigest(),
                "section": "Local request validation and graph compilation contract",
                "sha256": evidence_hash})
        nodes[-1]["source_ids"] = contract_source_ids
        edges.append({"from": item["facts"][-1][0] + "_" + str(len(item["facts"])),
            "relation": "constrained_by", "to": contract_node_id})
        published.append(store.publish(model_id="minimax_h3", workflow_id=workflow_id,
            workflow_version=item["version"], workflow_sha256=workflow_hash,
            graph={"sources": sources, "nodes": nodes, "edges": edges}))
    return published


_IMAGE_GUIDANCE = {
    "qwen_image_2512": {
        "model_id": "qwen_image_2512",
        "prompt_rule": "This text-to-image graph sends the prompt string to its CLIPTextEncode node; it has no LoadImage reference input.",
        "reference_rule": "Do not describe an image as attached: this graph has no image reference input.",
    },
    "z_image_turbo": {
        "model_id": "z_image_turbo",
        "prompt_rule": "This text-to-image graph sends the prompt string to its CLIPTextEncode node; it has no LoadImage reference input.",
        "reference_rule": "Do not describe an image as attached: this graph has no image reference input.",
    },
    "qwen_image_edit_2511": {
        "model_id": "qwen_image_edit_2511",
        "prompt_rule": "This image-edit graph sends the prompt string to TextEncodeQwenImageEditPlus and requires a primary LoadImage input; the adapter accepts up to two additional images.",
        "reference_rule": "Only describe reference images when they are selected; this adapter compiles one to three image inputs.",
    },
    "qwen_image_multi_angle_2511": {
        "model_id": "qwen_image_edit_2511",
        "prompt_rule": "Native QwenMultiangleCameraNode outputs pass through easy promptList into one sampler execution. Camera prompts plus explicit per-view facing instructions control each direction. Left/right character profiles specify opposite screen-edge nose directions. Generated orientation still requires visual review; successful execution is not proof of correct orientation. The shared Director prompt must only preserve identity/environment, without side/front/back or camera/framing instructions.",
        "reference_rule": "This workflow requires one saved character or world master. One execution returns two, three, four or eight ordered images, each retained as a separate directional asset.",
    },
}

# Vendor examples/advice are kept distinct from local workflow contracts.
# Current moving vendor pages use a dated capture; immutable vendor commits use
# their short Git revision. Neither type defines local ComfyUI node syntax.
_IMAGE_VENDOR_GUIDANCE = {
    "qwen_image_2512": [
        ("vendor_prompt_example",
         "The official 2512 prompt example describes a complete scene in natural language. Its optional rewrite guide says to preserve the user's intent, add only logically consistent visual detail, and specify exact visible text when the image is meant to contain text. Treat this as rewrite guidance, not required model syntax.",
         "https://github.com/QwenLM/Qwen-Image/blob/6b5e1f5/src/examples/tools/prompt_utils_2512.py",
         "commit:6b5e1f5", "Qwen-Image-2512 prompt rewrite guidance"),
    ],
    "z_image_turbo": [
        ("vendor_prompt_example",
         "The official Turbo example uses a natural-language scene description naming the subject, appearance, setting, and visual details. This is an example, not a required prompt template.",
         "https://github.com/Tongyi-MAI/Z-Image",
         "capture:2026-10-11", "Z-Image-Turbo Diffusers example"),
        ("parameter_compatibility_note",
         "The official Diffusers example uses 9 configured steps (8 DiT forwards) and guidance_scale 0.0 for Turbo. Vibe's local ComfyUI graph currently defaults to 8 steps and CFG 1.0; do not overwrite local settings with Diffusers values without verifying the ComfyUI graph and sampler semantics.",
         "https://github.com/Tongyi-MAI/Z-Image",
         "capture:2026-10-11", "Z-Image-Turbo parameter example"),
    ],
    "qwen_image_edit_2511": [
        ("vendor_edit_example",
         "The official Edit 2511 example gives a natural-language instruction alongside supplied image inputs and demonstrates using multiple images. Its Figure 1/Figure 2 wording is example text, not a proven requirement for Vibe's ComfyUI prompt format.",
         "https://github.com/QwenLM/Qwen-Image/blob/6b5e1f5/README.md",
         "commit:6b5e1f5", "Qwen-Image-Edit-2511 multiple-image example"),
        ("parameter_compatibility_note",
         "The official Diffusers edit example uses 40 steps and true_cfg_scale 4.0; Vibe's local graph uses a 4-step Lightning LoRA with CFG 1.0. These settings belong to different inference setups and must not be copied across without graph-specific verification.",
         "https://github.com/QwenLM/Qwen-Image/blob/6b5e1f5/README.md",
         "commit:6b5e1f5", "Qwen-Image-Edit-2511 Diffusers example and local Lightning graph comparison"),
    ],
    "qwen_image_multi_angle_2511": [
        ("vendor_edit_example",
         "The official Edit 2511 examples support natural-language image-edit instructions with supplied images. Vibe's local multi-angle adapter uses installed native camera-node direction syntax; the vendor example does not document or validate that local direction syntax.",
         "https://github.com/QwenLM/Qwen-Image/blob/6b5e1f5/README.md",
         "commit:6b5e1f5", "Qwen-Image-Edit-2511 image-edit examples"),
    ],
}


def seed_image_workflow_knowledge(store: WorkflowKnowledge) -> list[dict]:
    """Publish local graph contracts plus distinct vendor-source guidance.

    Local facts hash-pin the exact graph and adapter. Vendor statements cite
    official documentation and remain examples/advice, not local requirements.
    """
    from story_builder.services.production_image_workflows import PROJECT_ROOT as IMAGE_ROOT

    published = []
    for workflow_id, item in _IMAGE_GUIDANCE.items():
        spec = IMAGE_SPECS[workflow_id]
        graph_path = IMAGE_ROOT / "workflows" / "api" / spec["graph"]
        adapter_path = Path(__file__).resolve()
        if not graph_path.is_file():
            continue
        graph_hash = hashlib.sha256(graph_path.read_bytes()).hexdigest()
        adapter_hash = hashlib.sha256(adapter_path.read_bytes()).hexdigest()
        evidence = [
            ("prompt_contract", item["prompt_rule"], "local ComfyUI API graph and Vibe image adapter", None, None),
            ("reference_contract", item["reference_rule"], "local ComfyUI API graph and Vibe image adapter", None, None),
        ]
        step_limits = (4, 16) if workflow_id in {"z_image_turbo", "qwen_image_edit_2511"} else (20, 80)
        cfg_max = 2.0 if workflow_id == "z_image_turbo" else 8.0
        dimension_contract = {
            "qwen_image_2512": "Width and height are applied directly to the EmptySD3LatentImage node.",
            "z_image_turbo": "Width and height are applied directly to the EmptySD3LatentImage node.",
            "qwen_image_edit_2511": "Width and height are converted to a target megapixel count (0.3–2.0) for source-image scaling; output aspect ratio follows the source image, so these values do not set exact output dimensions.",
            "qwen_image_multi_angle_2511": "Width and height are applied directly to the EmptySD3LatentImage node.",
        }[workflow_id]
        evidence.append(("parameter_contract",
            f"Vibe adapter validates width and height from 256 to 2048 in multiples of 8; {dimension_contract} steps {step_limits[0]} to {step_limits[1]}; CFG {0.1:g} to {cfg_max:g}; unsigned 32-bit seed. Defaults in this workflow version: {spec['defaults']}.",
            "Image adapter validation and exact workflow graph defaults", None, None))
        evidence.append(("prompt_limit_contract",
            f"Vibe adapter permits image prompt strings of 1 to {IMAGE_PROMPT_MAX_CODEPOINTS:,} Unicode code points; oversized prompts are rejected, never silently truncated.",
            "Image adapter prompt validation", None, None))
        evidence.extend((kind, text, section, uri, version)
            for kind, text, uri, version, section in _IMAGE_VENDOR_GUIDANCE.get(workflow_id, []))
        sources = []
        nodes = []
        for index, (kind, text, section, vendor_uri, vendor_version) in enumerate(evidence, start=1):
            node_id = f"{kind}_{index}"
            nodes.append({"node_id": node_id, "kind": kind, "text": text, "source_ids": []})
            captured_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if vendor_uri:
                source_id = f"vendor_{index}"
                nodes[-1]["source_ids"].append(source_id)
                sources.append({"source_id": source_id, "uri": vendor_uri,
                    "version": vendor_version, "section": section, "sha256": captured_hash})
            else:
                graph_source, adapter_source = f"graph_{index}", f"adapter_{index}"
                nodes[-1]["source_ids"].extend([graph_source, adapter_source])
                sources.extend([
                    {"source_id": graph_source, "uri": graph_path.relative_to(IMAGE_ROOT).as_posix(),
                        "version": graph_hash, "section": section, "sha256": captured_hash},
                    {"source_id": adapter_source, "uri": adapter_path.name,
                        "version": adapter_hash, "section": "Image workflow validation and graph compilation", "sha256": captured_hash},
                ])
        edges = [{"from": left["node_id"],
            "relation": "constrained_by" if right["kind"] == "reference_contract" else "supplemented_by",
            "to": right["node_id"]} for left, right in zip(nodes, nodes[1:])]
        published.append(store.publish(model_id=item["model_id"], workflow_id=workflow_id,
            workflow_version=spec["version"], workflow_sha256=graph_hash,
            graph={"sources": sources, "nodes": nodes,
                "edges": edges}))
    return published


def seed_audio_workflow_knowledge(store: WorkflowKnowledge) -> list[dict]:
    """Pin copied audio workflow inputs and Vibe-side validation contracts."""
    from story_builder.services import audio_effects, audio_tts, control_foley, music_sound

    contracts = {
        "ace_step_music_v1": {
            "model_id": "ace_step_1_3_5b",
            "graph": music_sound.ACE_WORKFLOW,
            "adapter": Path(music_sound.__file__),
            "prompt": (
                "Local prompt contract: the workflow has separate tags and lyrics inputs. Tags are required for both modes; "
                "song mode requires lyrics, while instrumental mode supplies the adapter's [instrumental] value. "
                "These are Vibe graph inputs, not a claim about undocumented vendor prompt syntax."
            ),
            "references": (
                "Local reference contract: this ACE-Step adapter does not accept image, video or reference-audio inputs. "
                "Do not describe unselected media as attached to the music request."
            ),
            "text": (
                "Vibe input contract: tags are required; mode is instrumental or song; song mode requires lyrics; "
                "duration is 5–240 seconds. The local graph receives tags, lyrics and lyrics_strength separately; "
                "steps are clamped to 1–100, CFG to 1–20, shift to 1–10, and lyrics_strength to 0–1. "
                "Seed, sampler and scheduler are forwarded by the local adapter."
            ),
        },
        "control_foley_text_audio_v1": {
            "model_id": "control_foley",
            "graph": control_foley.WORKFLOWS["text_audio"],
            "adapter": Path(control_foley.__file__),
            "prompt": (
                "Local prompt contract: provide a sound description in the prompt field; the adapter also forwards an optional "
                "negative_prompt. This mode has no video or reference-audio input. No vendor-specific syntax is asserted."
            ),
            "references": "Local reference contract: text-to-audio accepts no video or reference audio.",
            "text": (
                "Vibe input contract: text-to-audio requires a sound description and accepts no video or reference audio. "
                "Duration is 0.7–30 seconds, guidance 0–20, FPS 1–120, seed unsigned 32-bit, and steps are fixed or 1–100."
            ),
        },
        "control_foley_text_video_audio_v1": {
            "model_id": "control_foley",
            "graph": control_foley.WORKFLOWS["text_video_audio"],
            "adapter": Path(control_foley.__file__),
            "prompt": (
                "Local prompt contract: provide a sound description in the prompt field; the adapter also forwards an optional "
                "negative_prompt. The selected video is a separate required input. No vendor-specific syntax is asserted."
            ),
            "references": "Local reference contract: text-plus-video mode requires one video and accepts no reference audio.",
            "text": (
                "Vibe input contract: text-plus-video audio requires a sound description and a video; reference audio is not accepted. "
                "Duration is 0.7–30 seconds, guidance 0–20, FPS 1–120, seed unsigned 32-bit, and steps are fixed or 1–100."
            ),
        },
        "control_foley_reference_video_audio_v1": {
            "model_id": "control_foley",
            "graph": control_foley.WORKFLOWS["reference_video_audio"],
            "adapter": Path(control_foley.__file__),
            "prompt": (
                "Local prompt contract: prompt text is optional and negative_prompt is forwarded separately. A prompt cannot "
                "replace either required media input. No vendor-specific syntax is asserted."
            ),
            "references": "Local reference contract: reference-audio-plus-video mode requires both one video and one reference-audio input.",
            "text": (
                "Vibe input contract: reference-audio-plus-video generation requires both reference audio and video; "
                "a text prompt is optional and is not a substitute for either input. Duration is 0.7–30 seconds, "
                "guidance 0–20, FPS 1–120, seed unsigned 32-bit, and steps are fixed or 1–100."
            ),
        },
        "chatterbox_timed_multichar_v1": {
            "model_id": "chatterbox_timed_multichar",
            "graph": audio_tts.WORKFLOW_PATH,
            "adapter": Path(audio_tts.__file__),
            "prompt": (
                "Local text contract: the input is timestamped SRT dialogue, not a free-form generation prompt. "
                "Speaker tags are mapped to the assigned voice and language by the Vibe adapter. Pause tags "
                "accepted by the adapter are preserved for the workflow; they are not speaker names. "
                "This describes the pinned local graph and adapter, not vendor documentation."
            ),
            "references": (
                "Local reference contract: each tagged character must map to a discoverable voice file. "
                "Untagged dialogue requires a mapped Narrator voice. This workflow has no image, video, "
                "or reference-audio input; assigned voice files are its speaker references."
            ),
            "text": (
                "Vibe input contract: SRT must contain at least one timestamp range; character tags must "
                "resolve to saved characters and discoverable voices. Supported timing modes are "
                "stretch_to_fit, pad_with_silence, smart_natural, and concatenate. Local bounds are seed "
                "0–4294967295, exaggeration 0.25–2, temperature 0.05–5, cfg_weight 0–1, fade 0–0.1, "
                "max_stretch_ratio 0.5–5, min_stretch_ratio 0.1–2, timing_tolerance 0.5–10, and batch_size 0–32."
            ),
        },
    }
    effect_contracts = {
        "noise_cleanup": "Select one of the adapter's four installed UVR/MelBand cleanup models; aggressiveness is 0–20. The adapter produces cleaned and removed audio outputs.",
        "voice_repair": "Restoration mode is 0 (original), 1 (high-frequency removal), or 2 (train mode); CUDA use is a boolean local setting.",
        "voice_changer": "Requires a discoverable target voice file. Refinement passes are 1–5, maximum chunk duration 0–300 seconds, and chunk method is smart or fixed.",
        "rvc": "Requires a locally discovered RVC model and, if selected, a compatible local index; downloads are disabled. Pitch is −14 to 14, index ratio and volume envelope are 0–1, consonant protection is 0–0.5, refinement passes are 1–5, and maximum chunk duration is 0–300 seconds.",
        "emotion": "Requires exact transcript text; source audio must be 0.5–30 seconds. Iterations are 1–5 and emotion is selected from the adapter's fixed supported list.",
        "style": "Requires exact transcript text; source audio must be 0.5–30 seconds. Iterations are 1–5 and style is selected from the adapter's fixed supported list.",
    }
    for operation, graph in audio_effects.OPERATION_WORKFLOWS.items():
        workflow_id = f"audio_effects_{operation}_v1"
        contracts[workflow_id] = {
            "model_id": "audio_effects_local",
            "graph": graph,
            "adapter": Path(audio_effects.__file__),
            "prompt": (
                "This is an audio transformation, not a free-form text-to-audio prompt. "
                "The local adapter uses the source audio and operation-specific controls; "
                "transcript text is required only for emotion and style editing. No vendor prompt syntax is asserted."
            ),
            "references": (
                "Local reference contract: one source audio input is required. Voice changing additionally uses "
                "one discoverable reference voice; other operation controls do not attach image, video, or audio references."
                if operation == "voice_changer" else
                "Local reference contract: one source audio input is required; this operation accepts no separate reference media."
            ),
            "text": f"Vibe input contract for {operation}: {effect_contracts[operation]}",
        }
    published = []
    for workflow_id, item in contracts.items():
        graph_path, adapter_path = item["graph"], item["adapter"]
        if not graph_path.is_file() or not adapter_path.is_file():
            continue
        graph_hash = hashlib.sha256(graph_path.read_bytes()).hexdigest()
        adapter_hash = hashlib.sha256(adapter_path.read_bytes()).hexdigest()
        nodes = []
        for node_kind, node_id, text in (
            ("prompt_contract", "local_prompt_contract", item["prompt"]),
            ("reference_contract", "local_reference_contract", item["references"]),
            ("parameter_contract", "local_parameter_contract", item["text"]),
        ):
            nodes.append({"node_id": node_id, "kind": node_kind, "text": text,
                "source_ids": ["local_graph", "local_adapter"]})
        captured = "\n".join(sorted(node["text"] for node in nodes))
        evidence_hash = hashlib.sha256(captured.encode("utf-8")).hexdigest()
        sources = [
            {"source_id": "local_graph", "uri": graph_path.relative_to(ROOT).as_posix(),
             "version": graph_hash, "section": "Pinned local ComfyUI API graph SHA-256",
             "sha256": evidence_hash},
            {"source_id": "local_adapter", "uri": adapter_path.relative_to(ROOT).as_posix(),
             "version": adapter_hash, "section": "Vibe audio validation and workflow compilation",
             "sha256": evidence_hash},
        ]
        published.append(store.publish(model_id=item["model_id"], workflow_id=workflow_id,
            workflow_version="1", workflow_sha256=graph_hash,
            graph={
                "sources": sources,
                "nodes": nodes,
                "edges": [
                    {"from": "local_prompt_contract", "relation": "constrained_by", "to": "local_reference_contract"},
                    {"from": "local_reference_contract", "relation": "constrained_by", "to": "local_parameter_contract"},
                ],
            }))
    return published
