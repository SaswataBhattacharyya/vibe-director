# Native Studio and Backlot

The fixed milestone is native HyperFrames Studio, native OpenMontage Backlot and one verified workflow through both. Vibe remains the authority for project assets, saved revisions, approvals, jobs and final outputs. Native interfaces introduce no alternate media library. Standalone storyboard outlines use the additive `story_board_sources` table in the existing project database; project snapshots include it by workspace ownership.

## Open the interfaces

Restart the backend after updating application code; the launcher may otherwise reuse an older backend. Start normally with `./start_vibe_director.sh`.

- **Vibe Editor → Open Visual Editor → Open HyperFrames Studio.** Select media and save a media/tool plan first. A plan containing filters, speed changes or transitions must use Vibe's existing visual editor; Studio synchronization currently accepts sequential 1× cuts. Native trim edits, clip ordering, captions (500 characters) and contain/cover framing return via **Import Studio edits as proposal**. Review and approve that new proposal in Vibe before rendering. Import does not start generation. Closing or navigating away discards unimported Studio edits.
- **Storyboard → Start from a brief or project media.** Write one shot per line or select images/videos in shot order. Create and reopen saved outlines without accepting a screenplay. Existing screenplay-based boards remain available. Save edits before switching boards.
- **Storyboard → Open OpenMontage Backlot.** Save the board first. The Vibe-specific editing extension appears beside native Backlot, with staged playable images/audio/video. Edit shot prompts, video prompts, duration and notes; choose **Send edits for review in Vibe**, then **Review Backlot edits** in Vibe. Inspect the proposal, choose **Use proposal as editable draft**, then **Save storyboard**. Importing never saves or generates automatically. Stale proposals fail without replacing saved data. Saved changes synchronize into the native board every five seconds; **Sync saved storyboard** refreshes immediately.
- **Final films in Backlot.** Assemble the saved storyboard in Vibe Editor, complete its existing approvals and render. Backlot synchronization publishes the registered, verified Editor output into its native renders list. Publication records both the film's source storyboard revision and the current board revision; an older film is never relabeled as a newer cut. Older Editor sessions without storyboard lineage are not guessed or auto-associated.

These are optional workspaces. The left navigation, Media Prep, standalone tools, existing timeline, renderer and approvals remain independent. The Backlot button is on Storyboard because it consumes a saved board; other creation tools gain no screenplay/storyboard prerequisites.

## Runtime and licensing

Studio uses the existing installed HyperFrames **0.8.199** Apache-2.0 runtime under `local_data/runtimes/editor/node_modules/hyperframes`. Its React 19 UI runs on a separate loopback origin; the application stays on React 18. Studio bundle filenames are pinned to this verified version. Existing runtime setup is documented in `design/vibe-editor/change_readme.md`; the new adapter does not download dependencies automatically.

Backlot uses the unmodified public OpenMontage revision **d21f5d4eaa08422b09c7091757a05affcbabb35b**, AGPL-3.0. The pinned runtime is installed in this checkout. On another checkout, run from the repository root:

```sh
conda run -n react python scripts/setup_production_interfaces.py
```

This explicit installer downloads thirteen pinned source/license files, records their hashes and refuses to overwrite an existing runtime. It downloads no models and invokes no provider. FastAPI, uvicorn and watchfiles must be available in the backend environment. Source and license remain in `local_data/runtimes/openmontage`; attribution is in `third_party_licenses/OpenMontage/`. Keep upstream licensing/source notices with distributions.

## Interfaces and preservation

| Caller | Operation | Contract |
| --- | --- | --- |
| Editor | `POST /api/editor/projects/{id}/studio` | Exactly `{revision, plan}`; selected owned ranges, current revision and registered byte hashes checked before staging. |
| Editor | `POST /api/editor/projects/{id}/studio-action` | Exactly `{token, action}`; actions `keepalive`, `import`, `close`. Import rechecks original hashes and uses the existing revisioned `propose_plan` seam. Stale imports fail without replacing the Vibe draft. |
| Storyboard | `POST /api/story/workspaces/{workspace}/storyboard/{screenplay}/backlot` | Exactly `{expected_revision}`; uses existing production manifest ownership, revision and hash checks. |
| Storyboard | Same prefix, `/backlot-action` | Exactly `{token, action}`; `sync`, `proposal` or `close`. Owner/root/source must match. Proposals modify only typed preparation fields and require explicit adoption/save. |

`interface_sessions.py` owns only the processes/folders it creates. Each workspace has a random capability, unique HttpOnly cookie, dedicated loopback port and temporary copied media. Provider credentials and the owner's HOME are not passed to specialist runtimes. Close/unmount, backend shutdown and thirty-minute idle expiry clean owned folders/processes; a failed launch cleans immediately. Abrupt OS termination can bypass backend shutdown cleanup.

Studio's native server is never exposed directly. `native_studio.mjs` permits selected reads and bounded element edits. Whole-document persistence is accepted only when the parsed DOM differs in supported typed fields; script changes, additional layers, arbitrary styles, raw uploads and direct native render/AI/export actions are blocked. Imported HTML is never executed by the Vibe renderer: supported fields become a normal JSON proposal. Unsupported native controls can still appear upstream and return an unavailable-action error. Caption timing follows its clip in Vibe; independent caption layers, arbitrary GSAP/graphic animation, native undo/history edits, new media imports and soundtrack edits are outside this adapter.

Backlot reads an owned mirror with local media paths and original Vibe identities/hashes. The application-owned editing extension leaves upstream source unmodified and sends bounded, same-origin JSON proposals. It preserves shot/media identities. It does not support arbitrary timeline edits, inserting/deleting/reordering shots or replacing media. It runs no OpenMontage generation pipeline; checkpoint panels can therefore be empty. Native file watchers notify its board after mirror updates. Verified final Editor films are published into the native renders list, including playable media.

## Shared Director generation tools

Director and Editor share the existing exact-plan task gateway. New executable adapters are `image.generate` (Z Image, Qwen Image, Qwen Edit, FLUX Kontext), `video.generate` (one native T2V/R2V candidate), `music.generate` (a reviewed ACE generation session), `voice.speak`, `voice.design`, and `3d.generate` (one TRELLIS image). Chat receives local versioned model defaults; installed runtime readiness is checked at execution. Discovery never authorizes a run. Music training and output acceptance remain separate. Reference voices, ACE references, attachments and installed image graphs are frozen/rechecked before submission. Missing acknowledgements do not trigger another generation request.

This is expanded tool access, not complete application-tool coverage: timed dialogue, Foley, audio effects, multi-view/Pixal3D and additional analysis/render operations still need dedicated reviewed adapters. Active image/video cancellation is not exposed by these adapters; the interface reports that limit rather than claiming cancellation.

## Verification and rollback

Implementation locations for the shared-generation/standalone-storyboard/Backlot-extension batch (other working-tree changes predate this batch):

| Area | Files |
| --- | --- |
| Shared generation | `backend/story_builder/services/agent_generation_tools.py`, `agent_native_tools.py`, `agent_tasks.py`, `agent_tools.py`, `agent_conversation.py`, `video_repertoire.py` |
| Source persistence and routes | `backend/story_builder/services/storyboard_sources.py`, `storyboard.py`, `backend/story_builder/isolated_server.py` |
| Backlot extension and publication | `backend/story_builder/services/backlot_editor.html`, `native_backlot.py`, `production_board.py` |
| Frontend | `frontend/src/StoryboardStart.tsx`, `StoryboardPage.tsx`, `App.tsx`, `NativeWorkspace.tsx`, `lib/storyboard-api.ts`, `lib/native-workspace.ts` |
| Focused checks | `backend/story_builder/tests/test_agent_generation_tools.py`, `test_agent_native_tools.py`, `test_storyboard_sources.py`, `frontend/tests/storyboard.spec.mjs`, `native-interfaces.manual.mjs` |
| Documentation/discovery | This guide, `.review/director-storyboard-backlot-impact.json`, refreshed generated `graphify-out/` graph/manifest/cache |

Focused backend tests: `story_builder.tests.test_native_interfaces`, `test_editor_preview`, `test_production_manifest`. Mocked browser checks: `native-workspace.spec.mjs`, `editor-visual.spec.mjs`, `editor-effects.spec.mjs`, `storyboard.spec.mjs`. Frontend production build/typecheck pass. These checks do not establish owner-media creative acceptance.

The real native acceptance test is repeatable from the repository root:

```sh
node frontend/tests/native-interfaces.manual.mjs
```

It uses system Chromium (H264 support), the `react` environment, installed native runtimes and FFmpeg. It creates isolated test projects/database and a five-second synthetic blue H264/AAC clip; plays it in Backlot; stages extension edits without changing saved data; verifies live saved-board refresh; edits and reloads a native Studio caption; checks simultaneous localhost embedding and rejected executable writes; trims to 3.5 seconds; imports a Vibe proposal; approves only that synthetic fixture and renders through the existing CPU renderer. It verifies output picture, audio/video streams and duration, then publishes and plays the final film in native Backlot. `finally` closes servers and removes the fixture projects/database/media, even on assertion failure, and asserts cleanup. No paid/provider or model generation runs.

Rollback requires no destructive data conversion: close native workspaces and stop new task submissions before reverting their adapters, UI integrations and HTTP branches. Keep additive source/task records so saved standalone boards and in-flight receipts can be recovered after restoring the feature. Existing accepted-screenplay boards, sessions, plans, assets and jobs remain ordinary Vibe records. Leave runtimes installed or remove only their known installation folders after closing; never delete user projects, media or history as a rollback step.
