# Video destination boundary impact review

high (.60 known / .70 possible)

Scoped to worker preparation, retakes and frozen output metadata. Source trace plus fresh Graphify discovery; two dependency levels, with the publication consumer checked separately. No measured coverage claimed.

| Risk | Node | File | Anchor | Reason |
| --- | --- | --- | --- | --- |
| 0.60–0.70 | isolated_video_jobs.py::prepare_isolated_take | backend/story_builder/services/isolated_video_jobs.py:2859 | `def prepare_isolated_take(take: dict[str, Any], *, graph_path: Path | None = None,` | build_worker.prepare -> prepare_isolated_take -> preview dispatch; entire saved snapshot hash verified before projection. All three graph compilers exercised by new tests. |
| 0.60–0.70 | isolated_video_jobs.py::retake_draft | backend/story_builder/services/isolated_video_jobs.py:2632 | `def retake_draft(self, job_id: str, *, keep_original: bool) -> dict[str, Any]:` | isolated_server retake-draft route returns editable workflow fields; publication choice remains saved in source take. |
| 0.60–0.70 | isolated_video_jobs.py::create_retake | backend/story_builder/services/isolated_video_jobs.py:2716 | `def create_retake(self, job_id: str, *, idempotency_key: str,` | Direct retake -> strict normalization -> create_job; regression covers server metadata in existing saved request_json. |
| 0.60–0.70 | isolated_video_jobs.py::create_job | backend/story_builder/services/isolated_video_jobs.py:2145 | `def create_job(self, *, workspace_id: str, clip_id: str, idempotency_key: str,` | Retake -> create_job -> queue_take; frozen output destination and idempotency retained; new lifecycle regression passes. |
| 0.60–0.70 | production_ledger.py::queue_take | backend/story_builder/services/production_ledger.py:232 | `def queue_take(self, *, project_id: str, run_id: str, shot_id: str, take_id: str,` | create_job persists full snapshot/hash including output destination; no migration or rewrite. |
| 0.60–0.70 | isolated_video_jobs.py::make_output_collector | backend/story_builder/services/isolated_video_jobs.py:3013 | `def make_output_collector(*, data_root: Path, ledger: ProductionLedger, comfy_url: str,` | Nested collect reads take.input_snapshot.output_destination for verified output relocation; preparation never mutates take. |
| 0.40–0.50 | isolated_video_jobs.py::_workflow_request | backend/story_builder/services/isolated_video_jobs.py:2817 | `def _workflow_request(snapshot: Mapping[str, Any]) -> dict[str, Any]:` | Three internal consumers: prepare, editable retake draft, direct retake. Only output_destination is excluded; unknown workflow fields still fail. |
| 0.40–0.50 | isolated_video_jobs.py::build_worker | backend/story_builder/services/isolated_video_jobs.py:2938 | `def build_worker(ledger: ProductionLedger, *, comfy_url: str,` | ProductionJobWorker.process_one -> nested prepare -> prepare_isolated_take; no scheduling, guards or engine POST changed. |
| 0.40–0.50 | production_job_worker.py::process_one | backend/story_builder/services/production_job_worker.py:118 | `def process_one(self) -> dict[str, Any]:` | Worker executes prepare before engine submission; failed live job has no engine prompt ID. |
| 0.40–0.50 | isolated_video_jobs.py::_compile_workflow_preview | backend/story_builder/services/isolated_video_jobs.py:2837 | `def _compile_workflow_preview(request: Mapping[str, Any], t2v_graph: Path,` | Dispatch still calls original strict T2V/FL2VA/R2V compilers; all three tested with/without frozen destination. |
| 0.40–0.50 | isolated_video_contract.py::compile_preview | backend/story_builder/services/isolated_video_contract.py:157 | `def compile_preview(payload: Mapping[str, Any], *, graph_path: Path = T2V_GRAPH_PATH) -> dict[str, Any]:` | T2V dispatched compile consumer; public schema remains strict. |
| 0.40–0.50 | isolated_fl2va_contract.py::compile_preview | backend/story_builder/services/isolated_fl2va_contract.py:139 | `def compile_preview(payload: Mapping[str, Any], *, graph_path: Path = FL2VA_GRAPH_PATH) -> dict[str, Any]:` | First/last-frame dispatched compile consumer; staged loader path rewrite retained. |
| 0.40–0.50 | isolated_r2v_contract.py::compile_preview | backend/story_builder/services/isolated_r2v_contract.py:180 | `def compile_preview(payload: Mapping[str, Any], *, graph_path: Path = GRAPH_PATH) -> dict[str, Any]:` | R2V dispatched compile consumer; two-image/one-video fixture and exact failed snapshot compile with mocked staging. |

15 focused CPU tests pass. Exact failed-job snapshot compiles with mocked staging. Original failure reproduced in all three modes when metadata projection is bypassed. No engine submission. No additional actionable defect found in the final scoped patch review.

Bounded two-hop trace from worker and retake paths; publication consumer inspected additionally. Not exhaustive repository analysis.
Graph rebuilt: 4450 nodes/13827 edges across 455 files; graph lacks measured test coverage and is not runtime readiness proof.
CPU compilation and mocked staging, not real generated-media acceptance.
