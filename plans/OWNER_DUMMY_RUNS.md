# Owner-clicked dummy runs and acceptance

**2026-10-13 owner correction:** release manual sessions only after planned copying/coding/UI work is complete. See [MANUAL_ACCEPTANCE.md](MANUAL_ACCEPTANCE.md) for the Debug journal and ordered preparation packet. Session B is now prepared for the owner's first click; later sessions remain unreleased until their own readiness and exact inputs are prepared.

**Latest release update — 2026-10-13 14:06 UTC:** C1–C12 and the consolidated Sol review are recorded complete; the later C11 Debug cross-tab fix passes its focused regression and build. The first bounded Session B (one already imported video analysis) is prepared in `MANUAL_ACCEPTANCE.md`. Live Status/Analyze preflight is Ready, serial workloads OFF, Debug ON, ComfyUI 0/0 and Vibe jobs 0/0 with one historical attention item. The analyzer reports 3.7 GiB free informationally. These values expire; refresh immediately before the owner clicks. No job was started.

Updated 2026-10-11. Read `remaining_app.md` first. Luna prepares; the owner starts the process using its actual UI button. These sessions demonstrate complete small journeys, not hundreds of regression tests. Preserve existing passed legacy evidence and test only changed risks.

## Two kinds of evidence

**Mock walkthrough:** clearly labelled mock responses/stub worker, no engine/provider/GPU execution. Suitable for navigation, pending/failed/recovery states, selection and autosave. Never label a mock result generated or engine-ready.

**Live small acceptance run:** actual configured Codex/ComfyUI/tool backend and real saved outputs. Small story, existing Story Builder assets, lowest useful supported duration/quality and bounded job count chosen before the owner clicks. A dummy story with a real GPU job is still a live generation. The owner starts one clearly described job or bounded automated run; do not secretly submit a second batch. An explicitly started automatic run may progress through its confirmed stages without another click for every job.

## Preparation checklist for every owner session

1. Restore the intended workspace/page in the existing UI, occasionally rather than repeatedly. Preserve the owner's drafts; use a clearly named local test workspace.
2. Fill exact prompt, references and per-reference instructions, workflow, parameters and expected count. Show what the click will do and whether it uses GPU/provider resources.
3. Verify backend/worker/ComfyUI, graph/nodes/models, reference bytes/capacity, prompt limits, queue and existing independent GPU monitoring. Reuse current cutoff policy (code currently 83°C/2100 MHz); do not alter clocks or assume historical operator guidance replaces code. Audio/video analysis using GPU needs supervision too.
4. Ask the owner to click the actual button. Do not simulate clicks or submit through API as a substitute for acceptance.
5. Observe truthful job state, output preview, persistence and recovery; save result/job IDs and exact request evidence in HANDOFF. Report failure as failure with retained inputs.
6. If another click/job is needed, explain why and prepare it. Combine compatible checks in one small session; skip previously verified unchanged engines.

## Compact sessions

| Session | Prepared page and fixture | Owner action | Evidence to capture |
|---|---|---|---|
| A — readable authoring | Small saved story with two characters/two scenes, a chosen style, import text/PDF fixture, populated editor | Generate screenplay; select a passage, request and apply a micro-edit | Internal graph preparation, readable integrated direction, exact edit, saved/reloaded state; history is compact |
| B — Media Prep | Existing donor video/image/audio, no new asset generation; nested tool pages and Search | Analyze a selected fixture; enroll a known voice; search/play results | Correct tool outputs, shared registration, names/semantics readiness, voice vs clip separation, sort/views/hover; preserve offline behavior |
| C — characters and worlds | Existing style refs and known voice; character/world prompts and chosen graph ready | Generate character/base candidates; select; generate labelled world views | Four manual candidates and independent voice binding; four/eight world directions; no automatic generation to prove setup |
| D — video and retake | T2V or R2V with existing donor refs; reference instructions collated | Generate; Retake; Next as needed | Current Take request/output, retained retake draft, new next-clip prompt, no lost refs on page changes; restrict actual retakes to an agreed small count |
| E — automation | Small confirmed run; all inputs preflighted; show total stages/clips and policy | Start Assisted or Full run | Checked/unchecked stage behavior, reference mapping, ordered chain, duration/quality, reload/pause/retry, bounded derived-frame inspection if supported |
| F — FFLF near end | First/last selected images, compatible prompt and verified graph; existing assets whenever possible | Generate one FFLF video | Endpoint inputs actually used, saved take and playback; CPU mocks do not replace this check |
| G — export | Existing accepted clips, explicit order and optional existing audio | Export | Playable ordered file, correct audio placement, retained original clips and registered output |

## Session B preparation — imported-video analysis

**Status: prepared, owner start required.** Use the already imported YouTube video `90s Kids Discover 2026 Social Media…` in the **Standalone media workspace**; it is selectable and has been confirmed playable in Search. No new download is needed. On the Analyze page, select its checkbox (current view starts with 0 selected). This analyzer has no free-text prompt field, so there is no prompt to invent. The latest preflight is recorded at the top of `MANUAL_ACCEPTANCE.md`.

Reported free CUDA memory is diagnostic; the retired fixed 20 GiB floor is not an admission requirement. The 14:06 UTC preflight passed at 3.7 GiB reported free; Status showed **Allow simultaneous runs OFF** and **Debug ON**. Before the owner clicks, recheck Status/runtime and queues; stop if another Vibe job is active, the app reports a runtime/thermal/driver block, or backend/ComfyUI/analyzer readiness fails. The configured thermal/clock guard is 83 °C / 2100 MHz; do not change clocks. Preserve current analyzer defaults for the first run: audio analysis, transcript/speech, diarization, music/SFX/ambience events, audio and video search data on; source separation Automatic; scene sampling 4 FPS, threshold 0.08, redundant-sample reduction and scene anchors on, temporary decode samples off; cut subdivisions on, sensitivity 0.18, minimum 0.5 seconds; reusable Voice/Music/SFX clip saving off. Historical failed-job messages citing 20 GiB predate this fix; do not retry the historical failure.

After the owner clicks **Analyze selected videos**, capture job/run ID, truthful completion state, saved scenes/frames/audio assets and their source/time lineage. Then verify the generated result opens and plays. Only after an actual content index exists, try a grounded semantic query using a distinctive visible event or spoken phrase from this video and compare the returned clip with its timestamp; title search alone is not semantic evidence. Keep the original and imported video intact. This one bounded analysis does not authorize a separate SAM isolation, TTS, generation or export job.

Sessions are not a mandatory repeat of every donor engine. Run only the unverified/new seam for each journey. Generation counts for four candidates/world views must be shown before starting; do not call a twelve-job batch a one-job check. Zero-checkbox, mixed, all-checkbox and Full setup rules can be checked with focused mock/CPU tests; use the smallest bounded live run needed to validate newly wired execution.

## Finish evidence

For each session record planned/ready/owner-started/passed/failed/blocked, actual input/output IDs, source/model/workflow versions, monitor evidence and remaining gap. A prepared form is not a passed test. Owner-clicked sessions may remain pending while implementation continues on independent work. Do not mark the overall goal complete until required acceptance is finished or the owner explicitly changes scope.
