# Notes for Codex / implementation agents

This directory contains **six Agent Skills** for the planned Vibe Director assistant, plus supporting contracts. It is NOT the app code.

Before changing the Vibe Director app:
1. Read `README.md`, `shared/CONTRACT.md`, and `DIRECTOR_INTEGRATION.md`.
2. Inspect the user's forthcoming app review Markdown and source ZIP to determine actual implementation, routes, services, model profiles and existing utilities.
3. **Preserve existing Media Prep audio tools** and Vibe Editor capabilities; make them callable by the Director through an audited capability registry.
4. Make stages skippable and cross-linked. Never make a wizard hard requirement.
5. Add real first/last-frame extraction and true LTX-upscaling OFF behavior where absent.
6. Wire the six `skills/*/SKILL.md` files into the app's skill loader on demand. Do not hardcode tool names from illustrative examples; map them to verified code.
7. Add tests for prompt length ≤ 7000, duration ≤ 15s for the selected MiniMax H3 profile, reference-slot correctness, model compatibility, voice sample mapping, last-frame/first-frame semantics, and safe persistent settings changes.

Do not claim all app components are integrated until adapters have been implemented and tested.
