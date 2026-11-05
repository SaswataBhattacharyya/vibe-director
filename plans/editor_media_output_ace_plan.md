# Projects, output folders, Video recovery and Editor/ACE changes

Status — 2026-11-03: implemented in the working checkout with focused CPU and mocked browser checks. Live generation and every-page runtime acceptance remain unverified. Current source and owner instructions supersede previous proposals. The complete impact/review and test limitations are in [PROJECT_STORAGE_REVIEW.md](../audit/PROJECT_STORAGE_REVIEW.md).

## Product contract

1. **New / Open / Save project:** one selected folder saves the story/storyboard, project media, settings, sessions and project-specific Director/Editor/tool memory.
2. **Output folder:** editable path plus Choose folder. Defaults inside the project, with an explicit override. Output changes affect new work; existing jobs retain frozen destinations.
3. **Standalone tools:** work without project/workspace setup. Story-based features still require their actual story/revision inputs.
4. **Storage separation:** source, saved project content/outputs, shared application data and runtime/model installations have separate responsibilities. Internal ownership IDs remain implementation details.

## Editor and ACE requirements


- **Choose files or folder.** In Vibe Editor Asset selection, offer explicit file and folder choices. A folder includes files recursively through every nested subfolder. Filter by the selected Images, Videos or Audio type. Show matching files with clear loading, empty and failure states. Preserve originals and reuse existing file/folder registration and catalogue services.
- **Use Search's asset browser.** Reuse its visible select/deselect, Select all shown, Deselect all, selected count, confirmed permanent deletion, named sorting and card/list/carousel viewing controls. Select all applies to the current filtered results. Keep previews distinct from selection. Replace the bare down-arrow with a properly labelled control consistent with Search.
- **Attach to chat.** Allow selected assets and dragging an asset into the chat box, retaining existing file drop/paste. Show attached items with a small × revealed on hover or keyboard focus; provide an accessible touch equivalent. Removing an attachment updates the saved selection without deleting the file. Preserve clip ranges, duplicate handling, partial-upload recovery and reload persistence. Selection/drop alone must not send chat or start processing.
- **Choose output folder.** Show an editable output-folder path plus Choose folder, matching the existing output-folder pattern. A standalone Editor must not require choosing/creating a story workspace. Keep saved tool conversations/settings and asset identities intact. Input folders, output destination and an optional actual story association have separate meanings; internal ownership IDs are not a user setup requirement.
- **Audit similar places.** Find other standalone tools that require a workspace merely to use the tool or set its output. Record each affected page and apply the same simple output-folder pattern where appropriate. Preserve genuine story associations and storage/recovery contracts. This is not permission to rename backend ownership fields indiscriminately or migrate/delete user data.
- **Compact Open media.** Make Open media and the expanded Open/session chooser a dropdown or anchored popover that does not push the editor panels down. This records the previously stated interpretation of the owner's wording; no screenshot-specific behavior has been verified here.
- **ACE-Step fresh entry.** First visit opens Create → Generate song/instrumental. The active tab and content must agree. Preserve Fine-tune settings, datasets, styles, saved sessions and explicitly selected Fine-tune navigation; do not reset those to disguise an initialization bug.

## Implemented project folder contract

```text
Chosen project folder/
  vibe-project.json          # stable identity, version, committed checkpoint pointer
  project-data/<checkpoint>/
    state.json               # scoped SQL, browser memory, grants/preferences/index
    content/                 # existing project documents, revisions, sessions, media
    runtime/                 # owned settled jobs, results, inputs, adapters/datasets
  outputs/
    videos/ images/ audio/ edits/ analyses/ models/
```

Existing application ledgers and tool services remain the working copy. Save checkpoints their project-scoped state; Open imports into those same services. This avoids moving local_data or rewriting worker engines. A registered local project preserves newer local edits on reopen. Conflicting copies of the same identity are rejected. No Save As with a new identity is exposed.

Save verifies content and detects edits during checkpoint creation before atomically replacing the manifest. A failed Save retains the previous checkpoint. Active/pending/recovery jobs block switching and imported unsettled jobs are rejected; Open cannot replay them. Folder imports validate schema, ownership, hashes, containment and symlinks. SQL/new-file conflicts roll back before commit. Postcommit registry IO and abrupt power loss remain documented limits.

Registered assets retain IDs and hashes. Portable fallback copies are used only when the original location is absent. Completed 3D GLBs and music exports are included even without library registration. Project ACE datasets and trained adapters are included; base models, secrets, provider configuration, environments and unrelated projects/shared libraries are excluded.

Project-internal output grants rebase when the folder moves. External destinations are recorded and need Choose/Locate on a fresh runtime. Repeated saves retain complete checkpoints and media, increasing disk usage. No automatic data deletion or migration was performed.

## Page adoption and verification

| Page family | Implementation | Evidence / remaining limit |
| --- | --- | --- |
| App shell and shared context | Global New/Open/Save, active owner before pages mount, persist/remount on switch, autosync memory | Mocked A→B→A, cleared storage, blocked switch, desktop/narrow controls pass |
| Story, screenplay, setup, prompt preparation | Active project controls ownership; first story revision saves into a blank project; old URL cannot override active owner | Backend story round trip and mocked stale links pass; full accepted production-run restore not executed |
| Video Create, R2V, FFLF, Current Take | Managed context, retained frozen recovery record, independent media-kind load/retry, existing jobs unchanged | 29 Video UI cases pass, including partial-kind failure, missing references, retake and lost responses; no live generation |
| Characters/Worlds/Frames and text-to-image | Shared context/output control; image settings and chat scoped/restored | Image A/B/restoration and asset selection mocks pass; native chooser/model acceptance pending |
| Search, Media Prep, analysis | Independent destination picker removed; shared sources remain available; project-scoped tool settings and analysis history included | Media/source/output and backend studio cases pass; not every analysis mode exercised live |
| Audio, Foley, reconstruction/utilities | Shared owner/output preferences and project-scoped tool/chat settings | Audio utilities mocks and studio backend cases pass; no real engine generation |
| ACE and music | Owner-filtered sessions; Create default; preserved Fine-tune; Jukebox explicit cross-project source copying and restored exports | ACE/Editor and music UI cases; ACE dataset/adapter and music export round trips pass |
| Vibe Editor | Owner-filtered sessions; typed recursive asset browser, attachment/drop/removal, compact Open, project edit output default | Editor UX/asset mocks and saved-session round trip pass; no real render acceptance |
| TRELLIS/Pixal3D/multiview | Managed owner, scoped settings/jobs, default models output, portable inputs and completed results | Studio/multiview CPU cases and TRELLIS UI pass; no GPU generation |
| Assembly/history/status | Existing ledgers, frozen requests and export contracts preserved; scoped records in checkpoint; status remains application-wide | Source trace and baseline comparison; full assembly production journey not verified |

## Investigation and blast radius

The screenshots correspond to the deleted-project guard being reached through stale browser ownership. Earlier read-only checks found all 268 registered owner/asset pairs had files; this did not establish decoding/hashes or prove the historical directory cleanup was the sole cause. Details remain in `audit/project-storage-live-check.json`.

Used ponytail to adapt existing ownership, output grants, session registries and execution services. Blast-radius covers 62 source-confirmed boundaries, including unchanged downstream consumers. The refreshed AST graph has 4,433 nodes and 13,767 edges; two-hop discovery yielded 2,567 candidates. The impact map is bounded and dynamic references require source review. All 62 source anchors pass the citation verifier. Overall prioritization risk is high (known max .60, possible max 1.00 with unknown coverage/caller factors).

## Checks and owner acceptance remaining

64 unique focused backend cases and 49 unique affected UI cases pass across focused runs. TypeScript/production build passes. The broader 136-case suite still has 54 failing cases, all also failing on isolated HEAD; no newly failing case names. [Validation evidence](../audit/project-validation.json) records this comparison.

Native folder selection, a complete live project journey through every tool, decoded generated media and owner-clicked provider/GPU acceptance remain outstanding. No live services were restarted, and no real user data was moved or deleted as part of this implementation. Existing fixtures do not establish live runtime readiness.
