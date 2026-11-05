---
name: vibe-compact-code-craft
description: Engineer concise, readable, tested and flexible TypeScript/React and Python service changes for Vibe Director without duplicating engines or bloating large files.
---
# Compact, flexible code for Vibe Director

Optimize for small cohesive responsibilities, explicit correctness and maintainable change scope; **do not** optimize for character count or compress everything into one-line code.

## Engineering method
1. Read current module, consumers, types and tests before editing.
2. Reuse existing APIs/adapters: Media Prep audio utility, media library, project storage, durable production ledger, exact video validators, HyperFrames renderer. Avoid two ways to submit the same job.
3. Prefer small modules with a narrow stable interface. React: presentational components plus typed hooks/client. Python: pure validation/planning helpers and thin service adapters. Keep global request dispatch only as route mapping.
4. Every field crossing UI↔backend must have one explicit schema/validator and stable errors; fail closed on unexpected keys. Avoid deeply nested anonymous objects and blanket exception catches.
5. Keep data ownership and authority clear. Skills are instructions; tools are executable adapters; project graph is a projection of existing facts; frozen jobs remain immutable.
6. Use direct readable control flow and descriptive names; remove duplicate checks by factoring only true shared behavior. Avoid speculative generic frameworks and arbitrary dependency installation.
7. Prefer small focused patches over appending hundreds of lines to App.tsx, isolated_server.py or VibeEditorPage.tsx; test the affected contracts before extracting.
8. Preserve async cancellation and idempotency; unexpected responses require recovery, not blind retry.
9. Test success, bad input, unavailable capability, stale revision, wrong project and cleanup. Dummy TXT/PNG/WAV/MP4 must be temporary and deleted after tests, including failures.
10. Record actual tests, measured code-change size, affected files and rollback. Leave user media, project identity and existing good UX untouched.

## Code review checklist
- Does the patch have a single responsibility?
- Are data types and error messages explicit?
- Could an existing service be called instead of duplicated?
- Will users be able to skip the screenplay/board without admission errors?
- Will a saved job/project still recover and remain hash-valid?
- Are permissions scoped to the currently approved task and project?
- Do Editor and Director share the gateway and skill registry?
- Is the UI small, accessible and in the existing design language?
- Is every new branch covered by focused tests and clean fixture deletion?

Output a small file-level patch plan before coding; implement only approved scope using actual available tools. Never equate terse code with good code.
