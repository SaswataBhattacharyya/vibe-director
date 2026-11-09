---
name: frame-interpolation
description: Review keyframes, choose FILM or RIFE, and export verified silent video through shared Director and Editor tasks.
---

Use the Reviewed keyframes panel in First & Last Frames or Vibe Editor. Import a
starting image, explicitly prepare its Kontext canvas if needed, then ask the owner
to review it. `image.generate_next_keyframe` queues one Kontext candidate from the
approved head; the image worker finishes it separately. A queued task is not a
finished image. Wait for visual approval before continuing. Rejected keys stay in
history. Branch from an approved key to rewind without deleting descendants.

For `video.interpolate_keyframes`, use only the chosen project's take ID and exact
revision. Every active key must be approved, unchanged and the same dimensions.
Keys must describe a single continuous shot, never a cut. Default RIFE; FILM is an
alternative only when its model is installed. Ask about intended movement or
ambiguous take selection. More interpolation cannot repair incorrect poses.

Choose integer multiplier 2–16, fps 1–60 and endpoint hold 0–10 seconds.
N keys produce (N−1)×M+1 frames. Round each hold to whole frames. Four keys at
M=16, 24fps, 0.5-second holds produce 73 frames, approximately 3.04 seconds.
Changing fps changes playback duration; it does not generate extra movement.

`video.export_frame_sequence` requires the completed interpolation job for that
exact take revision. It creates a silent H.264 preview in the shared media library
and a separate downloadable FFV1 master. Audio remains a separate workflow.
Both Director and Editor use the same exact-plan approval and explicit Run.
Never claim visual quality based on file verification or approve frames yourself.
An uncertain engine receipt must be reconciled using saved history, never blindly
resubmitted. Do not interrupt unrelated GPU work or claim ControlNet is enabled.

Use the panel's approved-endpoints link for existing First + Last Frame generation.
The owner explicitly creates a new video draft; existing requests stay frozen.
