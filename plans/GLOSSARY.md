# Story Builder production language

These definitions resolve the ambiguous terms in the current plans. They describe the intended product; adapters may need to translate existing legacy records.

## Authored story and direction

**Story revision:** A saved version of the written/pasted story. Its source spans and graph snapshot identify the facts used for screenplay preparation.

**Screenplay revision:** The readable, structured plan containing scenes, action, dialogue, shots and integrated direction. It is the canonical creative source for production records.

**Scene:** A dramatic unit with coherent setting/time/action. It contains ordered shots and their clips. A camera-angle change does not by itself create a new scene.

**Beat:** A meaningful dramatic action, reaction, reveal or dialogue turn. A beat can span shots and a shot can include several beats; it is not a mandatory parent folder for a shot.

**Shot:** A planned continuous camera view or setup in a scene, with action, camera, lighting, dialogue and sound context. A long shot may need several model-generated clips to cover its duration.

**Cut:** A transition between shots. It is not a separate authored scene or a parent of shots.

**Sub-scene:** A legacy/informal term. New records use Scene, Shot and Clip; imported sub-scenes are mapped according to whether they describe a camera unit or generation segment. Do not create duplicate editable objects for equivalent content.

## Generation and references

**Clip plan:** One duration-bounded render unit linked to a scene and shot. It identifies the action/dialogue span, planned duration, workflow, opening/ending state and continuity predecessor where applicable. Splitting a long shot creates clips without rewriting its creative intent.

**Take:** One generation attempt for a clip plan, with its exact prompt, settings, references, result and source lineage. Several takes can represent the same planned clip; only one output may be chosen for its ordered story sequence.

**Clip asset:** The playable video output of a take. Completion, retention, sequence selection and human approval are separate recorded states.

**Workflow:** A versioned backend graph/input contract for text-to-video, first/last-frame or reference-to-video. It defines accepted inputs, parameters and verified limits.

**Reference manifest:** The selected assets, their roles, instructions, speaker/character mappings and deterministic model tags for a generation request. Recommendations are not selected references.

**Character voice binding:** A character-to-voice-file link used to recommend compatible video/audio reference inputs. Several characters may share a voice file; this does not imply distinct vocal identities or automatic attachment to a render.

**Direction override:** An explicit creative difference used for one take without changing the screenplay. Updating screenplay direction instead creates a screenplay revision and affects dependent drafts/outputs through targeted stale detection.

**Execution wrapper:** Manual, Semi or Full scheduling policy configured on the post-screenplay Automation & Parameters page. It controls shared generation screens; the same screens also accept isolated tasks without a story.

**Media library:** Shared storage/catalogue for generated, uploaded and auxiliary-prepared image/video/audio assets, with stable identities, JSON metadata, readable descriptions and searchable annotations.

## Identities and numbering

Display Scene 1 → Shot 1.1 → Clip 1.1.1, with Take 1, Take 2, etc. where alternatives exist. Stable IDs survive display renumbering. Beats and dialogue have stable IDs and links to their relevant screenplay/clip spans.

A scene may have one or many shots; a shot may have one or many clips. Clip outputs generated without explicit camera changes can continue the same shot. An ordered sequence does not imply a final stitched film.

**Automatic duration policy:** Either a fixed clip duration or a Director-selected duration within confirmed bounds. It is the only generation parameter allowed to vary under Director control per automatic video clip; initial quality remains fixed.

**Isolated task:** Generation with a local user brief/prompt and selected assets, without required story/screenplay identities. It uses the shared forms, job services and output catalogue.
