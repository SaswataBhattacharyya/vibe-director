# Vibe Director — active Codex entry (2026-11-07)

**Read this, not the old dated fix notes.** Current audited branch: `vibe-director-current`, baseline `9180a01376a6eb254ef6c171f9d3977e4d388dfb`. Confirm local `git status` / HEAD first; newer source wins over this audit. These are **implementation guides, not evidence that changes work live**.

## The only current handoff reading order

1. [CODEX_START_HERE.md](CODEX_START_HERE.md) — exact next actions, sequence and scope.
2. [ACTIVE_FIXES.md](ACTIVE_FIXES.md) — live task cards; do NOT reopen marked-done foundation.
3. [INTEGRATION_ARCHITECTURE.md](INTEGRATION_ARCHITECTURE.md) — HyperFrames, OpenMontage, shared chat/media, capability contracts.
4. [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) — tests and stop conditions by slice.
5. [COMPLETED_BASELINE.md](COMPLETED_BASELINE.md) — what source currently implements versus what is still unverified.
6. `AGENTS.md`, relevant source/tests, and their colocated `change_readme.md` only when editing that area.

**Historical files deleted from this folder are recoverable from Git history**, not active prerequisites. DO NOT read past dated reviews, Q/R/UX result essays, old change matrices, or package handoff prompts unless debugging an historical regression.

## Product decision

- **One Vibe Director project + one persistent central chat.** No new independent chat composer, asset database or separate project owner for either integration.
- **Vibe Editor right workspace:** `AI Editor` and `Visual Editor` modes; start with an isolated proof of HyperFrames Studio compatibility, then embed selected controls if feasible. A full-workspace expansion is required for timeline work. Separate-tab mode is fallback, not a second disconnected application.
- **Storyboard:** preserve existing manual storyboard; optionally add a `Production Board` backed by verified OpenMontage/Backlot capabilities. Do not promise OpenMontage Studio as an embeddable public GUI.
- **Media:** register once, reference by owned asset ID and hash, explicitly bind to editor session/range/composition. Chat attachment ≠ selected Editor input ≠ image/video model reference.
- **AI:** a selected skill and glossary entry provide instructions; only live, typed, installed and authorized tool adapters execute. Never tell the user “no audio extraction” when the existing MP3 adapter is ready; equally, do not claim transcription or time-coded detection merely because extraction exists.

## Safety and done policy

No code changes or runtime test executions were made as part of this documentation-only cleanup. The user authorized **these GitHub documentation deletions/updates**; this does not authorize deleting project media, silently rewriting approvals, GPU/paid calls, launching unrestricted computer access or making permanent output changes.

Only mark a card DONE after its code, focused backend/UI regressions, project reload, output verification and explicit remaining limitations are recorded. Remove completed task prose from `ACTIVE_FIXES.md` in future cleanups; retain a short entry in `COMPLETED_BASELINE.md`. Preserve the nested `fixes/vibe-director-codex-agent-blueprint-v2/...` package: `services/agent_skills.py` loads 13 runtime skill packages and `shared/CONTRACT.md` from it.
