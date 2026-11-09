---
name: kdenlive-clip-continuity-and-stitching
description: Compare repeated footage across two consecutive clips and prepare a reviewed Kdenlive MCP join in Vibe Director or Vibe Editor.
---

Use ordered sources A then B; ask about order if unclear. A matching still frame does not establish duplicated action. Propose `video.compare_clip_overlap` with two distinct shared video asset IDs. It reads complete-source boundaries, with a default three-second search window (configurable 0.5–10 seconds). Approve and run through existing task controls; never claim to have inspected video before completed evidence exists.

Read the completed comparison supplied in conversation context. Explain match, no_match or inconclusive, the search window and sampling uncertainty. Similarity is a measurement, not a probability. Static, looping, nearly identical backgrounds and sparse motion can be ambiguous. No-match only describes the searched windows. Do not invent a trim for uncertain evidence. Source times are estimates on a common grid, including for unequal/variable frame rates; inspect original playback.

For a requested join, use the saved Editor session and exactly those two sources in the same order. Select A through its real end and B from zero with enough footage after the repeated opening. Propose `editor.prepare_clip_join` with the current Editor target and completed comparison task ID. Preparation uses real Kdenlive MCP, preserves originals, and retains linked source audio. An unavailable backend must produce a blocker, never a renamed HyperFrames execution.

Review the creative brief if required, then the join preview and exact retained ranges. Check picture continuity and audio at the cut; a visual match alone does not ensure seamless sound. Final rendering requires the separate Editor media/tool plan approval. Output is currently a hard-cut 1080p/30fps sequence with normal speed, contain framing and original audio. For effects, replacement audio or more clips, explain this adapter's limits and use the existing manual editor deliberately.

After verified rendering, use the registered final video and downloadable editable Kdenlive project. The desktop Kdenlive GUI is separate from the browser. Keep exported project alongside its managed media on this machine. Do not claim Flatpak GUI compatibility until the owner opens it successfully.

If sources, selection, style or revision change, compare/review again. Stop/cancel uses existing durable jobs. On uncertain external mutation acknowledgement, inspect/reconcile the saved MCP execution; do not blindly repeat the mutation. Skills provide guidance and cannot grant filesystem or computer access.
