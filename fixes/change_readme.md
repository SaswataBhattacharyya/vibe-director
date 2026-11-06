# Vibe Director implementation guide

Current local implementation: [Q01–Q06 results](Q01_Q06_RESULTS.md), [Q07–Q08 results, schema, tests and remaining work](Q07_Q08_RESULTS.md). This is not completion of the entire blueprint.

## Start from the current source and authorization

1. Read repository `AGENTS.md` and the results above before the historical [source assessment](SOURCE_ASSESSMENT.md).
2. Locate relevant source, callers, persisted contracts and tests through [the matrix](FILE_CHANGE_MATRIX.md). The guides describe intended behavior; they are not executable fixes.
3. The owner has authorized a larger batch and continuation through the fixes. Do not re-request per-card approval during that authorized work. Ask for unresolved contradictions or genuinely required manual guidance. Paid/provider or GPU execution and new sensitive runtime permissions require their own authorization.
4. Keep changes reviewable, run focused isolated checks and verify cleanup. Preserve earlier local work. A future request for only one card still limits that future task to that card.

For architecture decisions, read relevant documents, the 13 skills and tool glossary in [the V2 package](vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/README.md). A bounded repair follows its card's reading list rather than loading the whole package on every run. Historical reviews are maps, not live runtime proof.

## Shared architecture and preservation

Director and specialist Editor share project context, skill resolution, typed tools and a durable agent runtime. They differ in creative context, not permission authority. Existing engines remain authoritative:

```text
Director chat / Editor specialist chat / independent manual pages
                    |
     project context + shared skills + typed tool adapters
                    |
       exact plan approval + durable invocation tracking
                    |
 story/image/audio/video/Editor services -> existing workers
                    |
 verified registered assets -> inspection/retake -> Editor/export
```

Manual pages keep their existing services and independent entry points. Preserve sidebar, Media Prep, originals, IDs/hashes, saved sessions/revisions, frozen requests, destination grants, retries/recovery and GPU guards (90°C/2100 MHz; never change clocks). No screenplay, storyboard or agent-plan gate for independent creation.

## Canonical implementation phases

Earlier blueprint/matrix numbering conflicts. Use this table for these change guides; the blueprint remains the product specification. Engineering order is not a user wizard.

| Phase | Outcome | Task boundary |
| --- | --- | --- |
| Preflight repair | Staged audio stays out of browsing | Q01; implemented |
| 1 | Shared discovery, derived project context, compact inspector | Q03 → Q04 → Q05 → Q06; no chat execution or DB migration |
| 2 | Both chats perform one approved, durable MP3 operation | Q01 first; Q02 → Q07 → Q08; durability before agent submission |
| 3 | Persistent Codex shell, general task loop, knowledge/bindings | Shell/chat/notes implemented; general task loop remains |
| 4 | Optional jackets, screenplay proposals, comic storyboard | Existing revisions; independent board drafts need schema design |
| 5 | Model-aware generation and continuity | Exact contracts; LTX-off is a separately approved versioned pipeline |
| 6 | Evidence-backed QA, retakes, mixed-media film assembly/export | Existing Editor/assembly; inspect renderer/audio limits first |
| 7 | Computer/coding/browser runtime and optional external specialists | Installed capability, scoped permissions, license/auth validation |

Q01–Q08 are implemented bounded cards. Phase 3 has a shared shell, persistent conversation and notes foundation; its general task loop and the remaining phases are still outstanding. Inspect actual sources before extending the runtime; do not replace existing working services with the proposal snippets.

## Engineering skills

- **blast-radius:** trace callers, persistence and consumers. Graph evidence is partial; see assessment.
- **ponytail:** smallest complete fix, current services/dependencies, no speculative plugin framework.
- **code-simplification:** equivalent refactors only, separate from behavior changes. Preserve return types, async errors, side effects, validation and ordering; examples are not automatic rewrite rules.
- **writing-for-agents:** one canonical task definition; directory guides route to it.

These global skills exist in this owner's Codex environment. Other environments must discover their actual availability. Local `fixes/skills/` engineering proposals are guidance, not automatically active skills. No automatic skill install, delegation or model assignment. A global Codex skill is distinct from the app's current fixed-path readers.

## Tests and rollback

Follow the [test guide](../backend/story_builder/tests/change_readme.md). No paid/provider or GPU generation without explicit authorization; owner-started acceptance remains required for new generation workflows. Documentation edits need no service startup, graph regeneration or whole-app test sweep.

Revert only the task's edits; never reset existing work or delete media/history. DB changes need backups and compatibility tests. Disable new execution first on rollback; do not drop records or abandon active jobs.

Current continuation: approved CPU last-frame PNG and scoped Codex computer tasks are implemented alongside MP3. Both surfaces offer Application tools, Project only and Full access; each computer task freezes scope and requires exact approval. Offline sandbox and mocked worker tests differ from unperformed live model acceptance. Browser/desktop automation and general film orchestration remain incomplete. See `Q07_Q08_RESULTS.md` for evidence and changed files.
