# Project Open/Save restoration fix

Status: implemented and validated for the scoped project-restoration repair, 2026-11-04. This repair precedes the new storyboard pipeline.

## Required behavior

New/Open/Save controls one active project throughout Vibe Director. Opening a project restores its story, saved screenplay and acceptance state, media, generation history and selected takes, Editor sessions/revisions, production settings, output preferences and project-specific Director/Editor memory. Pages query that project's records and restore valid saved selections. A missing browser selection cannot make existing saved content disappear.

Standalone tools remain available. Project folder and output folder are distinct: output defaults inside the saved project, with a visible override. Existing projects must remain openable without first creating a replacement project or regenerating their work.

## One-folder persistence contract

The project folder contains `vibe-project.json`, the stable project ID and relative pointers to the current immutable checkpoint's `state.json`, `content/` and `runtime/` directories. `state.json` carries project-scoped ledger rows, browser memory, tool/output preferences and a hash-verified file inventory. Registered external media is materialized into the checkpoint without changing asset IDs. Save publishes the main JSON only after copying and validating the checkpoint; prior checkpoints remain recoverable.

Existing application ledgers remain the working store for current engines. Opening a saved folder restores its checkpoint into those services on a fresh installation; on the same installation newer local records win. This stage avoids moving live databases or redirecting every generation engine. Project-folder saves are durable snapshots, not continuous mirrors. Save before transferring the folder. Shared repertoire indexing remains independent; the project carries its owned media copies and references, rather than bundling unrelated repertoire items.

Session selection: valid saved selections win. Without any saved selection, Editor/ACE display the first project-owned session from the service's ordered list. An explicitly selected New session remains blank. Browser archives never replace returned server memory during project switching; conflicting cached drafts remain in recovery storage.

## Confirmed evidence and remaining uncertainty

- `trial 1 scar` is `story-f4e3e594089b`; the current ledger contains its story source and one `story_screenplay_revisions` row.
- The running `/api/projects/current` returned `tool-library` / Standalone tools, matching the screenshot. Screenplay cannot display this story while standalone is selected.
- Its internal content folder is `local_data/projects/trial 1 scar`. The legacy registry maps the project ID to this folder name; `media/workspace.json` carries the same ID.
- That folder has no `vibe-project.json`. Current `projects.open_project` requires this checkpoint format, after rejecting folders inside source/application data through `validate_folder`.
- `ProjectController` already exposes an Existing projects list through `/api/projects/select`. Folder opening needs compatibility with those same existing identities rather than another independent project model.
- Browser caches can override returned browser memory. This is a restoration risk to investigate; it is not yet established as the cause of this particular screenshot.
- This evidence establishes an integration gap and preserved screenplay data. It does not establish what happened during the user's last Open click, whether that screenplay is currently accepted, or that every historical artifact/session exists. Check those facts read-only before implementation.

## 1. Inventory the existing project before changes

Read the target project's source/screenplay revisions, acceptance pointers, generation jobs, asset registry, Editor sessions, style snapshots and chat/memory records. Record counts and identities without copying story text into diagnostics. Compare registered paths with real files and distinguish missing content from hidden content. Check current server selection and browser selections separately.

Use the relevant sections of `audit/FUNCTIONALITY_AUDIT.md`; source and actual records remain authoritative. Inventory all project-specific page readers, not just Story and Screenplay. Include global indexes pointing to project-owned sessions and assets. Do not infer ownership from a display title or filename.

## 2. Give Open project one recognition path

Recognize the selected folder before applying destination-only rules:

1. Supported portable project with `vibe-project.json`: validate its checkpoint and existing identity using current integrity checks.
2. Existing internal project folder: resolve against the authoritative legacy project-folder registry and ledger; corroborate ownership metadata where available. Open that existing identity using the same activation service as the Existing projects list.
3. Unknown, ambiguous, deleted or unsupported folder: give a precise reason and recovery/import choice. Never create an empty replacement project silently.

Permit opening a verified internal project folder as a narrowly scoped compatibility path. Keep New destination restrictions. Save may also checkpoint the exact verified existing internal project folder; prune project-data and checkpoint helpers from input enumeration to prevent recursive saves. No other source/runtime destination is permitted. A marker file alone is insufficient authority to select arbitrary data. Preserve tombstone/deletion checks, path validation and identity validation.

Make Existing projects discoverable in the same compact New/Open control, with title, location and whether a portable save exists. Selecting either an existing entry or its folder must activate the same project ID. Read the complete paginated list; the current first-100 query cannot be assumed exhaustive.

## 3. Restore saved records and valid page selections

The backend active project is authoritative for ownership. Restore drafts and UI preferences only after confirming their owning project. Audit `ProjectController.capture/install/action`, `managedProjectId`, `useProjectState`, URL parameters and page-level storage readers.

- Story loads the existing source revision; Screenplay loads the saved accepted/current revision according to existing revision rules and exposes revision history.
- Do not auto-accept an unaccepted screenplay. If only a draft exists, display it as a draft.
- Video pages restore this project's jobs/takes and accepted choices; frozen requests keep their original inputs.
- Editor lists this project's sessions and restores its valid last session. If none is selected, show available sessions instead of implying that the project has no Editor work.
- Media/audio/image/3D tools, setup pages and project memory resolve through the same active identity. Global user preferences remain global.
- Restore a valid saved selection first; otherwise derive an appropriate selection from authoritative saved records. Missing browser keys cannot erase or suppress server records. Where several sessions exist, show the chooser with a clear default rather than guessing unrelated ownership.
- Project switching clears stale rendered page context while retaining the previous project's unsaved recovery drafts. Progress updates and delayed requests from the previous project must not overwrite the new selection.

Define cache precedence explicitly: saved server records determine content; project-scoped recoverable drafts remain separately visible; UI cache selects only valid records belonging to that project. Do not unconditionally replace fresh returned state with an older local cache. Preserve conflicted drafts for review rather than discarding them.

## 4. Save existing projects without rewriting history

Opening an internal project activates it immediately and displays its folder. Save project writes a portable checkpoint there; the editable path/Choose folder can instead save to an external project folder. Save copies its existing identity and related records/media into the supported checkpoint format; no new story ID, regenerated screenplay or reassigned assets.

Inventory and extend Save/Open serialization wherever project-owned records are omitted. Explicitly cover ledger relationships, acceptance pointers, generated media, edited derivatives, Editor session files/indexes/styles, project memory, per-tool state and output grants. Models, environments, secrets and unrelated projects stay outside the checkpoint.

Keep atomic checkpoint publication, source hashes, no-clobber output publication and recovery behavior. Verify checkpoint completeness before reporting a successful Save. Preserve original internal content during compatibility adoption. Do not move/delete user files as part of opening a project.

Retain the current protection against rolling back newer local work when reopening an older checkpoint. Detect a real checkpoint conflict and explain it; restoring an older checkpoint must be explicit. Missing/corrupt files produce actionable diagnostics and leave the currently active project intact. Audit activation/restore for partial writes and ensure failed restoration cannot leave mixed project state.

## 5. Clear UI feedback

The top bar shows active project title, location and save state. Standalone appears only when standalone is actually active. Open gives a loading/restoring state followed by the restored project; failure keeps the prior project visible and displays the specific error.

Replace generic guidance that rejects all internal project locations with contextual guidance: existing internal projects can open and save in place; new projects require a separate user project folder. Source, project storage and output destination labels must be clear. Preserve current palette, compact popover and keyboard/focus behavior.

No page should ask users to select another workspace after a successful Open. Distinguish “no saved screenplay,” “draft available,” “failed to load” and “no project open.” The repair must make data discoverable rather than hiding errors behind an empty page.

## Implementation scope and impact checks

| Area | Paths / consumers to trace | Main preservation concern |
| --- | --- | --- |
| Project recognition/activation | `services/projects.py`, `storage_paths.py`, legacy folder registry, dispatcher | Stable identity, path/deletion validation, activation after successful restore |
| Browser switching/state | `frontend/src/ProjectController.tsx`, `lib/media-workspace.ts`, `lib/project-state.ts`, App routes | Draft isolation, stale async responses, cache precedence and page refresh |
| Story/screenplay | StoryPage, ScreenplayPage, story APIs and ledger readers | Source/revision/acceptance lineage and existing saved draft visibility |
| Generation/media | Video Create/Current Take, image/audio/3D pages, shared asset/job readers | Frozen requests, histories, selected takes, outputs and source paths |
| Editor/assembly | Editor pages/services, session indexes, assembly selections/exports | Revisions, approvals, owned assets and accepted take links |
| Save/restore | `projects.sql_snapshot`, `owned_files`, `save`, `open_project`, output destinations | Complete checkpoint, related records, portable assets and safe publication |

Overall planning assessment: high regression consequence because this is shared ownership/persistence code. This is not a numerical blast-radius result or a claim of full coverage. Before code changes, perform a scoped blast-radius analysis of the proposed diff, use the local Graphify graph as a discovery aid, confirm coverage/freshness and trace actual callers plus persisted consumers. Save verified source anchors and test evidence in a task-specific review artifact. Do not mix unrelated existing changes into the assessment.

## Focused validation and completion criteria

Extend existing `backend/story_builder/tests/test_projects.py`, `test_named_project_storage.py` and `frontend/tests/projects.spec.mjs` where appropriate; inspect neighboring project pruning/restored-library tests. Test evidence must distinguish synthetic fixtures, browser behavior and actual saved-project acceptance.

1. Read-only baseline confirms the target's saved screenplay identity and state before repair.
2. Open its registered internal folder and select its existing-project entry: both activate `story-f4e3e594089b`, and Screenplay displays the existing revision without generation.
3. Switch A → B → standalone → A; source, screenplay, takes, Editor sessions, media and memory stay scoped. Include conflicting browser cache, absent cache and stale URL selection.
4. A fresh browser restores saved content from backend/project state without requiring old localStorage.
5. Save a fixture project containing story, screenplay, media/jobs, Editor work and memory; restore from its checkpoint in isolated app storage and compare identities, relationships and file hashes. Reopening on the same installation alone does not prove checkpoint completeness.
6. Move a portable fixture folder and relink external sources; preserve asset identities/frozen requests and valid output preferences.
7. Unknown folders, forged identity markers, deleted projects, corrupt/incomplete checkpoints, failed saves and active-job restrictions retain safe behavior and useful error messages.
8. Verify existing standalone tools, direct generation, Editor approvals, cancellation/retry, final enhancement/stitch publication and output destination behavior through focused regression checks. No incidental GPU/provider execution.
9. Browser acceptance verifies the project label, Story/Screenplay content, Editor session chooser, media/take list and compact Open/Save controls. Do not activate the owner's project or write a portable save as an incidental read-only diagnostic; perform owner-data acceptance as part of the authorized repair with recovery drafts preserved.
10. Refresh Graphify after meaningful code changes and report actual checks plus unverified workflows. Existing real media may be inspected without launching new generation.

The fix is complete when a single Open restores coherent existing work across pages and a portable save can independently restore that same work. Showing the project title alone is insufficient.


## Implementation and acceptance evidence — 2026-11-04

Implemented exact existing-folder recognition, compatible in-place checkpoints, relative manifest pointers, authoritative server memory restoration, and project-scoped Editor/ACE session fallback. Existing working ledgers and generation engines remain in place.

The actual `trial 1 scar` project opened with its original accepted screenplay and all 22 scenes. Save, clearing browser storage and reload preserved it. Copying the saved checkpoint into isolated application storage independently restored the same project, source revision, accepted screenplay revision and 22 scenes.

Validation: 38 focused backend cases, 13 focused browser cases and TypeScript checking passed. The scoped review traces 29 boundaries with verified source citations; Graphify was refreshed fully. See [project restoration review](../audit/PROJECT_RESTORE_REVIEW.md) and [validation results](../audit/project-restore-validation.json).

The owner's project has no saved generated clips or Editor/ACE sessions available for live acceptance; those restore paths were checked with fixtures. Native folder dialogs and new generated-media acceptance were not exercised. No GPU/provider generation was started. Project folders are saved checkpoints: Save before moving a project to another installation.

## New project folder creation — implemented 2026-11-04

New project defaults its parent to `local_data/projects`. Entering a name creates a new named child folder, writes its checkpoint, and activates the returned child path. A separate Create in field allows an external parent override. Open project retains an exact existing-folder path. Duplicate names never overwrite existing folders. Internal canonical folders register the stable workspace identity before saving; existing exact-folder API clients remain supported. Project identity, saved content and output defaults continue through the existing services.

Validation: 22 backend project tests, 7 browser project tests and production build passed. Named-child creation/save/reopen, duplicate rejection, external parent and path boundaries are covered. The live app returns the default projects parent; no real user project was created or switched for validation. Scoped impact map: `audit/PROJECT_CREATION_FOLDER_REVIEW.md`.

## Separate New/Load dialogs and timeout — implemented 2026-11-05

New project and Load project now have separate toolbar dialogs. New asks for name and Save location (editable path or Choose parent folder), creates the named child and activates it. Load asks for the existing project folder (editable path or Choose folder), then opens it. Save project and all existing ownership/restoration behavior remain. Related page guidance names the new controls.

Shared reasoning calls allow 30 minutes; graph/screenplay durable claims allow 35 minutes before being marked uncertain, with no silent retry. Focused validation: 58 backend tests, 8 browser cases and build passed. No actual model call or native desktop folder picker was run. See [scoped review](../audit/TIMEOUT_PROJECT_DIALOG_REVIEW.md).
