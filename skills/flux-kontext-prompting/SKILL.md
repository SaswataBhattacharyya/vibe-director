---
name: flux-kontext-prompting
description: Prepare precise FLUX Kontext reference edits and reviewed first/last-frame iterations.
---

Use FLUX Kontext Dev for a specific change to one existing image. Recommend it
for iterative first/last-frame editing when a reference exists. Use a text-to-image
model or import for the initial image. Never claim an unselected image is attached.

Describe the requested visible change first, then preservation constraints for
identity, clothing, art style, background geometry, framing and lighting. For
example: "Raise her right hand slightly. Preserve her face, clothing, camera,
background and lighting." Ask a concise question if the intended change is unclear.
Do not turn a small edit into an unrelated exhaustive scene rewrite. Positive
instructions matter: this graph zeroes negative conditioning. Defaults: 20 steps,
CFG 1, guidance 2.5, denoise 1, Euler/simple. Native aspect buckets follow the
reference; width/height are not exact output controls.

Generate a candidate, then wait for visual approval. Never recursively consume a
rejected or unreviewed frame. Preserve earlier approved assets when branching.
Kontext can drift in pose and framing despite preservation instructions; lower
denoise can suppress the requested change. Do not promise temporal consistency.
FILM/RIFE cannot repair an incorrect keyframe. Learned preferences require explicit
project-knowledge approval and must be scoped to the model and task.

## Reviewed frame tools shared with Vibe Editor

Use the live tool catalogue and project frame takes. `image.generate_next_keyframe`
queues one unreviewed candidate from an approved head; it is not an approved key.
`video.interpolate_keyframes` connects at least two approved, equal-size keys in
one continuous shot using installed FILM or RIFE. Never interpolate across cuts.
`video.export_frame_sequence` creates a silent MP4 preview and FFV1 master from
that exact completed sequence. Every operation requires an exact task approval.

Read take IDs/revisions from project context; never invent them. Ask which take
or movement when ambiguous. Review/branch through the First & Last Frames or
Editor panel. Rejection preserves files and history. Branching rewinds by creating
a new take; it does not delete the original. Interpolation cannot repair incorrect
poses or continuity. A successful file check does not establish creative quality.
Existing FFLF video generation remains a separate explicit workflow: use the
approved-endpoints link to prepare a new draft, or select references manually. Do not attach chat
images, choose endpoints, approve candidates or run GPU work implicitly.
