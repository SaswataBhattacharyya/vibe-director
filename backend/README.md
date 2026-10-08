# Isolated MiniMax H3 T2V backend slice

This Vibe Director draft contains a CPU request/compiler slice and a story-free durable job facade over the existing SQLite production ledger and worker. The localhost WSGI server exposes validation, readiness/runtime status, job creation/retrieval/events, retake draft/accept and byte-range playback routes. It does **not** start a worker at server startup. `POST /api/video/jobs` is the explicit user Generate action; it checks T2V capability, the live GPU guard and an explicitly enabled healthy worker before persisting a job. Actual ComfyUI submission is consumed by a separate operator-started process. No provider, Comfy render, or GPU operation was run for this implementation.

## Run focused CPU checks

From this directory:

```sh
PYTHONPATH=. python -m unittest discover -s story_builder/tests -v
```

The 20 standard-library tests cover the Card 1 compiler contract and Card 2 idempotency/restart/concurrency, atomic metadata creation, full snapshot/retake behavior, non-mutating lost-response lookup, worker-dispatch/runtime admission guards, and an injected ambiguous-submit worker path. All Comfy queue/history/POST responses in worker tests are fakes. No GPU, provider, external Comfy endpoint, model, browser or broad Story Builder legacy suite is invoked.

## API and storage

Start the HTTP adapter explicitly with `PYTHONPATH=. python -m story_builder.isolated_server` after setting `VIBE_DIRECTOR_DATA_DIR` to a product-owned data directory. Optional `VIBE_DIRECTOR_LEDGER_PATH` must remain inside that root; otherwise the database is `<data-dir>/storage/production/ledger.sqlite3`. Optional `VIBE_DIRECTOR_GRAPH_PATH` selects the exact graph file, which must match the pinned hash. Server binds only `127.0.0.1` (default port `3020`, override `VIBE_DIRECTOR_PORT`). It does not consult Story Builder's ledger default or start any worker. Set `COMFYUI_ROOT`, `COMFYUI_URL`, `STORY_BUILDER_ENABLE_H3_T2V=1`, and optionally `STORY_BUILDER_H3_T2V_SMOKE_MANIFEST` when the operator explicitly configures a runtime. Readiness is checked only on `GET /api/video/capabilities` or an explicit `POST /api/video/jobs`; server startup itself makes no runtime request.

To explicitly enable the durable consumer, run a separate terminal with the same `VIBE_DIRECTOR_DATA_DIR`, optional ledger/graph paths and runtime settings: `PYTHONPATH=. python -m story_builder.isolated_worker --enable-worker`. The alternative is `VIBE_DIRECTOR_ENABLE_WORKER=1` when invoking that module. Without this explicit opt-in the API capability reports `dispatch.available=false` and new job POSTs fail closed. The worker uses the existing `ProductionWorkerSupervisor`; it observes known prompt IDs after restart and never re-submits an uncertain prompt. It will leave queued jobs untouched while T2V or GPU readiness is unavailable, and checks readiness again in prepare. `GET /api/video/worker` exposes its local process heartbeat/status.

Routes:

- `POST /api/video/validations` with `{ "request": ... }` returns the normalized immutable request, canonical hash and predicted compile preview; it performs no readiness request or submit.
- `GET /api/video/capabilities` reuses the source T2V model/node/feature-flag/hash-verified smoke checks and adds the host GPU guard plus worker dispatch status. `GET /api/video/runtime` returns read-only temperature/clock status. Generation is blocked if telemetry is unavailable, temperature is at/above 83 C, or graphics clock is above 2100 MHz. These values preserve source safeguards; no clocks are changed.
- `POST /api/video/jobs` with workspace/clip/idempotency key/request (and for retakes `retake_of_job_id` plus `keep_original`) is an explicit Generate operation. It requires capability `available=true`, including a live worker consumer; otherwise it returns 503 without creating a ledger run/job.
- `GET /api/video/jobs/{job_id}`, `GET /api/video/jobs/{job_id}/events` and `GET /api/video/jobs/by-idempotency/{key}?workspace_id=...` are read-only. The idempotency lookup recovers a lost create response and never re-POSTs.
- `POST /api/video/retakes/{job_id}` with an explicit `{ "keep_original": true|false }` returns an editable saved-request draft and creates no job. A later Generate POST creates the retake. `POST /api/video/jobs/{job_id}/accept` accepts a reviewable output. “Discard” only marks a prior asset as a garbage-collection candidate after acceptance; this slice performs no deletion, and referenced assets are tracked separately.
- `GET /api/video/assets/{asset_id}` serves verified product-owned video bytes with HTTP range support for playback.

The adapter aliases `workspace_id` to the ledger's `project_id` and `clip_id` to `shot_id`; run configuration is `control_mode=manual`, `entry=isolated`, with Director gates disabled. It creates no screenplay, scene, or story canon. The full normalized request is stored in both the ledger snapshot and facade metadata. The same SQLite database holds isolated identity/idempotency/retake metadata and asset/reference records; it is not a second execution state machine. Retakes use independent takes with a metadata lineage link, never the ledger's predecessor-wait chain. `recovery_required` cannot be retaken until reconciliation resolves it.

Output collection is injected into the reused worker, downloads Comfy outputs into a temporary area using `media_jobs.collect_outputs`, requires native ffprobe video+audio streams, hashes and atomically stores valid media under `<data-dir>/assets/<workspace>/`, and returns stable content-derived asset IDs. Output paths are not returned to the browser. This collection code has not been exercised against a live Comfy output in this package.

## Reuse provenance

Reference repository: [`mooV_E_maker`](https://github.com/SaswataBhattacharyya/mooV_E_maker), pinned commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db`. Parent verified these selected sources against that commit. Hashes below identify the local source bytes; exact copies retain their corresponding Git blob IDs. The ledger and capability have narrowly documented adaptations, so their current SHA256 differs from upstream.

| Source path | Upstream Git blob SHA | Source SHA256 | Draft use |
|---|---|---|---|
| `services/minimax_h3_t2v.py` | `78b9642aaf0e04b7934c2fdaace3c72f712f3644` | `c17ba00efb7b873bd256afa978d7b2eee13ac18395d92d48ee1e63151d88d712` | Exact compiler copy |
| `services/minimax_h3_graph_compiler.py` | `fdaa830a1206e3f7feaf34737200e34db45de570` | `a1355882cf07f395a0ce5ba561c290e7e8e64e989d27ac4f59b0404e01cfaef3` | Exact shared compiler copy |
| `workflows/api/minimax_h3_t2v_api.json` | `476bdadbbe880fef4f32bcfeb25bacfa0b552dec` | `4735e3662333493d488bc2ba6970810e620c13196ccac15b1155010e8cf3e1f9` | Exact graph copy |
| `services/production_authority.py` | `f6aa938593d86eeb6adb39671d14b1390fe8d6f2` | `e1f99ad3fe69a378d30d1f5cb61e8354510dd0e8a237955ef57458adfd31f71c` | Exact copy; manual isolated config disables Director gates |
| `services/production_ledger.py` | `64a4cc1b92dc18ad454481ac45c5e8437afe0de2` | Source `39d2fc7eccd9fa288f5096a4cbbd13ab3c444396c0b911c8224f91905e510bab`; adapted `c7c460952e1f7b00604cca68ecbd74c8b684f70965c7432e9d80a8228c3d5fab` | Added optional `queue_take(..., on_create=...)` hook so facade metadata and queued ledger row commit atomically |
| `services/production_job_worker.py` | `ebea1b9f083a953a59f122a673c40a30728f8087` | `f1da73d22e595868405e0ebddcf03e965453613a7c6d3da95c763dfef873228b` | Exact serialized worker and recovery logic |
| `services/media_jobs.py` | `fcf7012e6c1689f6ddb02e98216a6f0ef8462386` | `c76608d880d09f966e914ee283999f44d06905731332ebc7321cf0d9bb6a98e0` | Exact queue guard/output fetch helpers |
| `services/gpu_runtime.py` | `b52eb47ca3128b416b91d8669f3d4fb021a48ad4` | `1afb61596068b4594c3f9c5e555ed2476b5955c22ebec98a59a7aa8a78524d32` | Exact GPU admission/telemetry helpers |
| `services/gpu_watchdog.py` | `42b6f0ba65d69dda304acf74f5ab890413b4c113` | `f4f4ccfe5d148620456ca0d94f3903755867528a2980b843d9348d800c7ec7cc` | Exact independent prompt watchdog |
| `services/production_reconciliation.py` | `7ddb1390b14a3d8e7baac9866996b3c1d77d0cd6` | `ee675285e93b18edd0157bae7360a8781f9c7daa9616fb7c40c4aa10a62bb20e` | Exact known-prompt read-only reconciliation helpers |
| `services/production_t2v_capability.py` | `53c796ba06732615d0270f217f2c6ea46579a100` | Source `2637d6b4fc881596c5a0b0efdcab1b084da9a7bd2835e6cd732a14fa4404272e`; adapted `2cfbd7ca5f965564f30356ad9dd9c589576bbfa70408491821a1a358fada1382` | Preserves T2V checks and checks every class_type in the pinned graph; Comfy root and smoke-manifest location configurable without copying large `audio_catalog.py` |

The reference checkout was a local read-only tree without Git metadata; parent separately verified the upstream blobs. The upstream root at the pinned commit had no root `LICENSE` or `NOTICE`, and the selected compiler/workflow sources have no explicit headers. The owner authorized reuse of their own source. This is not a third-party license conclusion. No OpenMontage/AGPL source, model weights, runtime, provider credential, sample media or ComfyUI installation was copied. OpenMontage remains excluded pending its separate license decision.

## Boundaries and remaining work

Current CPU checks establish request validation, deterministic compilation, durable idempotent identity, service restart/concurrency behavior, atomic facade metadata, retake snapshot preservation, output retention metadata, API no-consumer/runtime gating and no-resubmit handling with injected fakes. They do not establish successful Comfy rendering, actual media collection/playback, recovery through a real backend restart, user-browser usability, or operator-safe GPU generation. Current real host snapshot reported by parent was 48 C / 2431 MHz; because this exceeds the preserved 2100 MHz ceiling, live T2V availability is currently blocked. Do not change GPU clocks. The independent watchdog retains its source behavior and only exists during an explicitly started real worker prompt.

Next work: integrate the UI API client with the agreed product screen, configure product data/runtime paths, separately enable a supervised worker only after readiness and GPU guard pass, and perform user-clicked supervised media acceptance. Do not broaden to story canon, reference workflows, provider adapters or final assembly in this card. GitHub #2/#5 remain open; this backend slice is not an issue-completion claim.
