# Vibe Director handoff: reviewed keyframes → interpolated video

## Existing backend — reuse it

Repository: `/home/riki/web_dev/setup_comfy_and-stuff`.
Host API: `http://127.0.0.1:3008`, existing container `comfy-stack`.
ComfyUI is already configured; do not install another instance or update its
Python/CUDA packages. If Vibe Director runs in a container, localhost is that
container: use an explicitly configured address that reaches this backend.

The workflows and models are installed in ComfyUI. Vibe Director application
code has NOT been modified; implement its adapter/UI using the contract below.
Probe `/object_info` for required nodes/model choices before enabling a feature.

## Files to use

Canonical editable files: `workflows/ricky/` in this repository.
Registered UI copies: `ComfyUI/user/default/workflows/ricky/` (visible under
Workflows → ricky). Keep copies synchronized when changing a workflow.

| Feature | ComfyUI UI graph | REST graph |
|---|---|---|
| Previous frame + instruction → next frame | `flux_kontext_recursive_frame.json` | `api/flux_kontext_recursive_frame.api.json` |
| FILM interpolation | `film_frame_interpolation.json` | `api/film_frame_interpolation.api.json` |
| RIFE interpolation | `rife_frame_interpolation.json` | `api/rife_frame_interpolation.api.json` |

These are ordinary ComfyUI graphs without Krita inputs/outputs. Submit the API
graph object to `/prompt`, not the UI graph's `nodes`/`links` serialization.
Image widgets now default to ComfyUI's existing `example.png`; replace with real
user inputs. The former test images and generated demos have been deleted.

## REST adapter contract

1. Upload input image with multipart `POST /upload/image` (`image` file field).
   Use returned `subfolder/name` in LoadImage. Do not submit a host absolute path.
2. Deep-copy the chosen API graph and fill its inputs below. Assign a unique
   output prefix per project/shot/take/frame to avoid filename collisions.
3. `POST /prompt` with `{"prompt": graph, "client_id": unique_client_id}`.
   Persist prompt ID and exact graph before waiting. Inspect `node_errors`.
4. Poll `GET /history/<prompt_id>` or use `/ws` for progress. Check terminal
   status, including `execution_error`; a prompt receipt is not success.
5. Download actual SaveImage `outputs[node_id].images` with
   `GET /view?filename=...&subfolder=...&type=output`. Websocket preview records
   are not downloadable `/view` files. Persist downloaded image and SHA256.
6. On resume, reuse a recorded prompt ID; do not resubmit a timed-out job blindly.
   An interrupted POST with no receipt has an uncertain outcome: reconcile queue
   and history first. Avoid global interrupt/queue clearing on this shared server.

### Kontext graph bindings

| Node | Editable input |
|---|---|
| `1` LoadImage | `image`: uploaded previous approved frame |
| `7` CLIPTextEncode | `text`: action/edit plus preservation instruction |
| `8` FluxGuidance | `guidance`: default 2.5 |
| `11` KSampler | `seed`, `steps` (20), `cfg` (1), `denoise` (1); Euler/simple |
| `13` SaveImage | `filename_prefix`; read generated image here |

The graph uses `FluxKontextImageScale → VAEEncode → ReferenceLatent` for actual
image conditioning. Do not replace this with plain Flux text-to-image or an
unrelated CLIP reference. Negative conditioning is zeroed; put preservation
requests in the positive instruction. `FluxKontextImageScale` chooses a native
aspect bucket; normalize the initial frame deliberately so later keys have
identical dimensions (our 768×512 source mapped to 1248×832).

Installed weights under `ComfyUI/models/`:
- `diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors`
- `text_encoders/clip_l.safetensors`
- `text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors`
- `vae/ae.safetensors`

### FILM/RIFE graph bindings

| Node | Editable input |
|---|---|
| `1`, `2` LoadImage | two uploaded, ordered, equal-size keyframes |
| `4` FrameInterpolationModelLoader | `model_name` |
| `5` FrameInterpolate | integer `multiplier`, native range 2–16 |
| `6` SaveImage | `filename_prefix`; read ordered PNG sequence here |

Weights: `frame_interpolation/film_net_fp16.safetensors` and
`frame_interpolation/rife_v4.26.safetensors`. No third-party interpolation
environment is needed. To interpolate more than two keys, build an ordered
ImageBatch chain as the existing `interpolate_frames.py` does. Enforce identical
dimensions before ImageBatch, which can otherwise resize mismatched images.

For N keys and multiplier M, expect `(N-1)*M+1` frames. Preserve original keys
at indexes `0,M,2M,...`; avoid duplicate boundary frames between segments. FPS
sets playback timing; it does not generate motion. Do not interpolate shot cuts.

## Existing reusable runners

Run from the repository root (or use absolute script paths). These use the REST
API and standard library; final video export needs the existing ffmpeg.

```bash
python3 workflows/ricky/recursive_frames.py --input /path/start.png --prompts /path/prompts.json --run /path/project/take01
python3 workflows/ricky/recursive_frames.py --run /path/project/take01 --approve-current
# Repeat review/approve for each generated key. Approve the last key too.
python3 workflows/ricky/finish_shot.py --run /path/project/take01 --out /path/project/render01 --model rife --multiplier 16 --fps 24 --hold 0.5
```

Prompts JSON is an ordered list of strings or objects:
`[{"prompt":"Raise her right hand slightly. Preserve the scene and camera.","seed":81109,"steps":20,"denoise":1.0}]`.
The runner generates one key per invocation, then waits. It supports
`--rewind N --branch /new/take`, logged `--override /edited.png`, and explicit
`--auto-approve` for unattended experiments. Default is deliberate review.

The finalizer requires approved, unchanged source hashes. It saves `preview.mp4`,
lossless RGB `lossless.mkv`, PNG `sequence/`, manifests, job histories and ffprobe
metadata. Four keys at 16× yield 49 frames; at 24fps plus two half-second holds
the result is about 3.04s. Design keyframe spacing/duration explicitly.

## Vibe Director implementation requirements

Add separate Generate next keyframe and Interpolate approved keys actions.
Maintain shot/take/frame IDs; previous-frame lineage; prompt, seed and settings;
prompt ID, image hashes and approval/rejection state. Show side-by-side review,
manual replacement and rewind/branch controls. Render only an approved sequence;
never recursively overwrite accepted images. Serialize GPU jobs initially because
Krita shares this backend. Save project outputs in project storage and download
them before applying any ComfyUI output-retention policy.

Expose FILM/RIFE, multiplier, FPS and endpoint holds. Default to RIFE for this
anime use case, with FILM as an alternative. Reuse existing models and API graphs;
do not interpret historic test files as application assets.

## Optional ControlNet/keyframe preparation

Use ControlNet to prepare a keyframe in its matching model family, then feed the
approved resulting PNG to Kontext. Do not attach arbitrary SDXL/Noob controls
directly to Kontext. Existing tested resources include:

| Family | Matching base | Tested guidance |
|---|---|---|
| SDXL Xinsir | existing SDXL, e.g. `zavychromaxl_v80.safetensors` | standalone Scribble and Union ProMax Scribble |
| Noob/Illustrious | `novaAnimeXL_ilV125.safetensors` (epsilon) | Scribble, anime Lineart, OpenPose; matching Noob IPAdapter reference |
| SD1.5 | `flat2DAnimerge_v45Sharp.safetensors` | Scribble, segmentation with an actual ADE20K map |
| Z-Image Turbo | existing `z_image_turbo_bf16.safetensors` | Fun lite2601 sketch via ModelPatchLoader/ZImageFunControlnet |
| Qwen Image 2512 | existing `qwen_image_2512_bf16.safetensors` | Fun Union2602 sketch via ControlNetLoader/ControlNetApplyAdvanced |
| Anima Base1 | existing `anima-base-v1.0.safetensors` | LLLite v2 sketch; quality varies |

For conventional SDXL/Noob controls, use matching `ControlNetLoader` and
`ControlNetApplyAdvanced`, correctly processed control maps, then sampling and
decoding. Union mode must match its version. Noob reference uses matching
IPAdapterAdvanced/vision architecture. See the retained exact paths/mode matrix:
`env_setup/shared_krita_vibe_20261108/MODEL_MATRIX.csv`.

These ControlNet paths have backend/Krita validation, but no new dedicated
Vibe Director ControlNet adapter is implemented. Krita's six installed graphs
remain at `/home/riki/.local/share/krita/ai_diffusion/workflows/`; their Krita
input/output nodes must not be submitted as ordinary Vibe REST graph inputs.
Qwen Edit2511 supports the existing masked reference-edit path; it is not the
Qwen2512 ControlNet base. Composite masks to preserve unselected pixels.

## Honest capability limits

Actual tests completed: three successive Kontext generations, FILM/RIFE 2×/4×,
16× final videos, six Krita graph imports/expansions and real inference.
Kontext changed pose and camera framing despite preservation prompts. Lower
denoise0.7 suppressed the requested motion. Interpolation showed hand ghosting/
warping; it cannot correct wrong keyframes. No temporal-consistency guarantee.
Sample 768×512 four-key batch times: FILM 1.354s/1.838s at 2×/4×; RIFE
0.562s/0.908s. Kontext 20-step generations took about 46–50s on GB10.
These are individual samples, not performance guarantees or model VRAM peaks.

MOSAIC is **not installed/operational**: source imports were probed, but its
separate true FLUX.1-dev base is absent/gated and no model inference was run.
The disposable probe was removed during cleanup. FLUX.1-dev Union, FLUX.2 Fun
and Qwen Image2.1 Fun remain deferred. Do not advertise these as available.
Kontext dev model use has noncommercial/nonproduction restrictions; review
the model terms retained in INSTALL_REPORT.md before deployment. Anima also
has noncommercial restrictions.

## Cleanup and retained records

Generated test images/videos, raw test logs, copied plugin sources, abandoned
MOSAIC probe/venv, staging graphs/styles and completed installer/test scripts
were removed after installed-copy verification. `ComfyUI/output/video/` and
unrelated projects remain. Installed models/nodes/environments were preserved.
Retained compact provenance, environment/rollback records and validation summary
are under `env_setup/shared_krita_vibe_20261108/`; exact deleted paths and byte
counts are in `cleanup-manifest.json`. Historical reports may describe deleted
demo artifacts; they are historical evidence, not current file availability.
