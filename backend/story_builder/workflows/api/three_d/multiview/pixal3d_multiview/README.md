# Native Pixal3D multi-view

Use `Pixal3D_MV_front_back_bounded.ui.json` first. Four-view variant adds genuine left/right views. The matching `.api.json` files are executable Comfy API prompts, not UI documents. Original official sheet workflow is retained unchanged as `.upstream.ui.json`.

Host: `/home/riki/web_dev/setup_comfy_and-stuff/workflows/ricky/3d_stuff/pixal3d_multiview/`.
Container: `/workspace/workflows/ricky/3d_stuff/pixal3d_multiview/`.
Already exposed in the Comfy workflow browser through `user/default/workflows/3d_stuff`.

Input bindings: front=400, back=401 in the two-view graph. In four-view graph front=400,left=401,back=402,right=403. Replace each `LoadImage.inputs.image` with the name/subfolder returned by `/upload/image`. Technical placeholder files are labelled and must never be treated as real anatomy inputs. Node324 `fov` defaults20 degrees and is an assumed horizontal orbit, not an estimated camera calibration. Views must depict the same subject/pose/scale with front canonical. No three-quarter image in a left/right slot.

Prepare transparent/black-background source images together using `../trellis2_multiview/scripts/prepare_views.py`; review common scale and ground line. Opaque backgrounds are retained by that script and must be removed first. The graph deliberately bypasses independent crop-to-mask resizing so relative framing is preserved. Each subject should span approximately1/1.1 of its square frame. The native node composites alpha if supplied, but LoadImage may expose alpha as a separate mask; prepared RGB on black avoids relying on that behavior.

Model node319 selects `pixal3d_multiview_int8_convrot.safetensors`. Existing shape/texture VAEs and DINO+NAF encoder are reused. Do not replace with a single-view checkpoint.

Output node372 `filename_prefix`: `3d/ricky_pixal3d_multiview/<profile>/REPLACE_JOB_ID`. Set a unique job UUID before submission. Original exported GLB is preserved. Read actual `/history/<prompt_id>` output records; do not guess the final counter filename. Output root on host is `ComfyUI/output/3d/ricky_pixal3d_multiview/`.

Published sampling settings retained; bounded deviations: UDF remesh256, 2M precluster vertices,100k final faces,1024 textures. Official obsolete `solid` remesh widget was mapped explicitly to the live schema. These bounds are starting profiles, not GPU memory guarantees.

CPU validation uses actual backend `execution.validate_prompt` with `--cpu`; no `/prompt` request is made. Owner GPU and anatomical quality acceptance remain pending. Placeholder-based CPU success does not qualify real inputs or output quality.

Vibe must reserve the GPU across Comfy, TRELLIS, Ollama and training, then upload actual views, patch graph bindings/seed/output prefix, submit once, track history, verify nonempty GLB and expose a GLB viewer/download. Never suppress driver allocation errors or blindly retry a timed-out job.
