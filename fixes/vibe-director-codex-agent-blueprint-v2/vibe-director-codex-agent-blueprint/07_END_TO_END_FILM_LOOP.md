# End-to-end film creation, defect inspection and retakes

## Complete job loop
A user authorizes making a film. The Director:
1. **Discover**: project story/brief, graph facts, existing character masters/voices, locations, prior takes, output folder and engine readiness. Do not redo finished assets unnecessarily.
2. **Plan**: scenes + shot/video beats + estimated final runtime. Distinguish storyboard panels from shots and clips. Per generator choose duration constraints and reference limits. Store editable plan and ask user approval.
3. **Build preproduction**: script/dialogue timing, styles (optional jackets), master character Z-Image prompts/images, world/location references and shot-background prompts only as needed. Let user skip.
4. **Storyboard optionally**: fast comic-page layout with image per visual beat, action/dialogue/timing as editable UI text. A scene's panels can describe ONE continuous 15-second generation clip.
5. **Prepare model-specific clips**: T2V/R2V/FFLF/existing footage or image hold. Generate per-clip reference manifest with real assets and transient labels, exact timestamps, explicit camera/blocking and sound. Use video continuation last frame when a supported actual frame input exists, not just a generic ref label.
6. **Execute** approved generate jobs, capture immutable request and job IDs; poll real status; keep original source even if LTX disabled.
7. **Inspect** original/final clip: metadata probe plus actual sampled visual/audio inspection; record evidence and bounded defect intervals. Compare against desired action/dialogue/reference storyboard and last/first-frame continuity. Confidence and limitations visible.
8. **Decide** per defect: accept, edit (trim/retime, stabilize, audio replacement, crop, transition), regenerate specific clip, use new image/master, or change plan. Preserve prior takes and compute costs.
9. **Handoff** approved selection to Vibe Editor with ordered clips/asset IDs, ranges, per-clip defect report, editorial notes, audio placements, transitions, captions and soundtrack policies.
10. **Assemble and review** edited preview; inspect final dialogue/sync/cuts, verify total runtime and output media; export/publish, mark film task finished only now.

## Quality findings taxonomy
- `character_identity_drift` (appearance changed despite master)
- `scale_spatial_continuity` (mouse/lion ratio, tree/net geometry, camera continuity)
- `motion_physics` (teleport, paw sliding, impossible leap, rope magically disappears)
- `narrative_coverage` (missing/extra event, wrong emotional beat)
- `camera_composition` (cut in continuous shot, subject off-screen)
- `dialogue_wording`, `speaker_misassignment`, `lip_sync`, `audio_gibberish`
- `audio_mix`, `audio_pop`, `music_mismatch`
- `visual_artifacts` (deformed anatomy, flicker, object morph)
- `technical_integrity` (resolution, fps, duration, streams, corruption)

Each finding has `take_id`, `start_s`, `end_s`, `category`, `severity`, `confidence`, `evidence_source` (actual samples/transcript/analysis output), `desired_state`, `recommendation`, `status`. Never claim to hear gibberish just by inferring a bad line from the screenplay. An automated visual/audio QA score is evidence for REVIEW, not grounds to discard takes without approval.

## Retake selection
Prefer a retake when character identity/physical event is fundamentally wrong; prefer Editor when timing, order, simple visual effects, transitions or audio replace are sufficient. Use existing `POST /api/video/retakes/{id}` to prepare a new draft; it does not itself regenerate. New request with new idempotency key and parentage, preserving old attempt. If prompt change alone is likely enough, keep refs and modify beat timing; if refs wrong, fix manifests/first frame and identify downstream clip continuity risk.

## Clip composition contract
A screenplay scene may have multiple shots; a shot may require multiple generation clips; one generation clip may be represented by multiple comic storyboard panels. Existing still/image holds and retrieved footage must coexist with generated clips in the final editorial timeline. Do NOT force arbitrary existing media to have accepted screenplay take slots. The editor consumes a unified timeline draft, while legacy strict screenplay assembly remains available for its own exact-coverage workflow.

## Sound and voices
Voice sample (TTS Audio Suite) is identity/timbre reference, not a dialogue WAV. For each spoken line record speaker, text, delivery, expected window, actual generated audio reference and lip-sync status. A model might not support combined first-frame, character refs and voice samples; dynamically select supported route and offer post-production TTS repair rather than promising impossible combination.
