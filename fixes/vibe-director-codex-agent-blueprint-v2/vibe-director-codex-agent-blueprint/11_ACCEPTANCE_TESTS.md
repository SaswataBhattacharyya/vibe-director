# Required acceptance tests (BDD-style)

## Planning and approval
- Given a film request, when user asks "give plan first", no GPU job, code edit or output publication happens; plan includes assets, shots/clips, resources/refs, tools and checks.
- Given approved plan v2, when user says "implement steps 1–2", only authorized steps run. Unapproved external/cost/destructive operations block with precise pending request.
- Given changed story or selected style, old frozen job remains unchanged; plan update creates a new revision.

## Manual freedom
- From blank project, open Video Create, supply prompt and valid references and generate; no accepted screenplay required.
- From existing uploaded video, go straight to Vibe Editor and export a cut, never visit Story/Storyboard.
- Create/edit comic storyboard before screenplay; it stores independent editable user-supplied panels and can later link a screenplay scene.
- Left sidebar and all Media Prep operations remain functional; layout unchanged unless selected work pane is embedded.

## Tool calls and project state
- Director and Editor discover exactly same authorized `audio.extract` operation; Editor can extract through existing service and return a playable registered output.
- Wrong project ID or archived hash fails without data leakage. Switching project while job runs displays result only in original project; user can restore it later.
- Task/job status survives page reload and interruption. Reconcile uncertain GPU submit before retry; no duplicate generation.
- Computer runtime disconnected -> explicit "not connected", no fake command success. Connected with R1 approval -> sandbox code patch/test with visible diff and test output.

## Creative requirements
- Choose film+anime+cinematic together; propagate to screenplay, Z-Image characters, comic board and H3 prompt where relevant, without changing canonical character appearance unprompted.
- H3 R2V prompt <7000 Unicode code points; <=15s; all time ranges contiguous; accurate reference ordering and voice sample roles.
- Previous take final frame is extracted via verified tool; if selected workflow cannot accept true first-frame input, UI explains it and offers valid alternative.
- Dialogue timing + lip sync reviewed by real audio/video samples; no guessed transcript or invalid broad confidence.

## Quality/retakes/editor
- Original take retained after retake; selected take mapped to timeline with per-clip notes, defect markers and provenance.
- Clip defect classification suggests edit vs retake and doesn't discard previous usable media without user decision.
- Editor can receive selected clip order and outputs, run validated HyperFrames edit and publish verified MP4. Finish film only after final playback/probe.
- LTX OFF actually skips enhancement jobs and publishes validated Turbo-only original with correct audio/duration/frames; existing LTX jobs continue unchanged. LTX ON retains existing recovery/validation.

## External/negative tests
- OpenMontage/Backlot/Studio feature flags OFF -> basic app unaffected.
- Model-produced shell text, retrieved transcripts and source file comments cannot bypass tool schemas or authorization.
- Missing ffmpeg, ComfyUI nodes, GPU admission and browser sandbox each show specific readiness block; no fake "Ready" and silent failed execution.
- Preserve project save/open and portable restore of conversations, graph projections, selected references, tool results and file associations.

## Test evidence labels
Mark `static_verified`, `mock_verified`, `cpu_runtime_verified`, `gpu_runtime_verified`, `user_creative_reviewed` separately. Successful schema validation is not evidence of high-quality animation or correct dialogue.
