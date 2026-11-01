## 2026-10-25 — Small T2V source / completed pause audit (supersedes earlier live snapshot)

- Owner-requested T2V source policy implemented in `backend/story_builder/services/minimax_h3_t2v.py`: final qualities .4/.6/.8/.98/1.5 use the earlier .4 Turbo source budget (576×320 landscape, 320×576 portrait); Max2.0 uses896×512 /512×896. Other ratios keep existing32px-grid fitting. Final preset values/dimensions, supplied prompt, duration, seed, four steps and legacy graphs unchanged. Standard final1344×768 /768×1344. Guided FFLF/R2V unchanged.
- Latest batch sequence: all validated H3 originals → confirmed release → all LTX finals → confirmed release; retain each model within its phase. Source policy changes only newly prepared H3 graphs; saved originals and final media are preserved. LTX sets its own exact final canvas independently; no fixed1.5x constraint in the adapter.

# Mandatory T2V Turbo → LTX integration — 2026-10-24

## Owner contract
All new T2V jobs use the tested H3 Turbo four-step graph, then the preferred low-noise LTX 2.3 three-step refinement with Sol attention. FFLF/R2V retain their current graphs. Screenplay and authored prompts remain intact. User duration, aspect ratio and quality describe the final output, never the intermediate canvas.

Final landscape sizes: Low 1216×672; Standard 1344×768; High 1664×928; Max 1920×1088. Portrait swaps axes; tablet/square preserve pixel area on a 32-pixel grid. Historical numeric batch presets remain readable, with their original final sizes. No silent reinterpretation of frozen jobs.

## Implementation
1. Copy only tested API graphs from setup_comfy_and-stuff/workflows/ricky/h3_ltx; retain provenance and model names. Reuse the shared Docker installation, weights and custom nodes. No model downloads or duplicated runtime.
2. Pin version 2 to both graphs. H3 uses an approximately two-thirds-size aligned canvas, four steps; LTX resizes to the exact final dimensions and uses sigmas 0.421875,0.28,0.14,0. Preserve authored scene/style in refinement and remove the sample soup prompt and style-biased negative prompt.
3. Extend the existing durable worker/ledger with an original-ready/refinement-pending stage. Preserve source hashes and both Comfy prompt identities, resume each stage after restart, keep existing GPU/queue guards, and never submit an ambiguous stage twice.
4. Standalone jobs refine immediately. Pure-T2V automated stories generate originals first, then refine serially. Standalone batches generate all validated H3 originals, confirm unloading, refine all originals serially with LTX, then confirm final unloading; saved originals remain reusable on recovery (owner correction 2026-10-25). Pause blocks the next stage; Stop cancels pending stages and interrupts only the owned active prompt. Final readiness/review is published only after refinement.
5. Reuse the tested CPU tail-padding and original-audio remux approach. Validate final dimensions, frame rate, frame count and audio before registering the final asset. Intermediate files remain distinct from final media.
6. Update T2V UI quality choices, final-size previews, saved setup producers, batch parser and live stage feedback. Keep reference workflows unchanged.

## Evidence and boundaries
The setup recipe was exercised for a short 896×512 H3 source → 1344×768 LTX result. The other requested sizes, aspect ratios and long durations have not been rendered in Vibe. LTX is generative refinement and can change details; it is not the unavailable official pixel x4 upscaler. No speed guarantee is inferred from a five-second test. Retain one serial GPU service and source audio.

No generation or provider call during implementation. Owner will manually submit one prompt after build/source checks. Preserve all saved screenplay and user media. Report any missing dependency/readiness rather than falling back to base H3.

## Implementation status
Implemented in the existing contract, ledger, worker, setup/preview and T2V UI. Frontend build and Python/JSON syntax checks passed. Shared ComfyUI has all required node types; model files present. Idle API and video worker reloaded; no generation submitted. Playwright browser profile lock prevented interaction verification. Owner acceptance remains: one chosen prompt, then dimensions/audio/duration/stage recovery and batch/story behavior. Larger sizes, alternate aspect ratios and longer clips remain unrendered.
