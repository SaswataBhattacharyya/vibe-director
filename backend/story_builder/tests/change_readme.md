# Regression and disposable test-media change README

Do NOT write any dummy files into real project media folders. Keep existing backend tests; add focused new files only when matching service code lands.

## Baseline and blast-radius gates
Before each phase run (or inspect if dependencies are missing) these existing tests:
- test_projects.py, test_named_project_storage.py, test_local_layout_migration.py — Save/Load and project isolation.
- test_audio_utilities_integration.py — real Media Prep extract_mp3 job contract and CPU-only extraction.
- test_video_continuity.py — actual final-frame extraction and hash-bound caching.
- test_isolated_video_contract.py, test_isolated_r2v_contract.py, test_isolated_fl2va_contract.py, test_isolated_video_jobs.py — **different** exact request schemas, hash and admission.
- test_storyboard.py, test_story_style_link.py, test_prompt_director.py, test_production_styles.py, test_production_setup.py — creative revisions and strict legacy run behavior.
- test_video_final_collection.py, test_t2v_phase_handoff.py, test_assembly_renderer.py — worker final output, audio and stitching.
- Relevant editor tests should be discovered by repository search; do not invent a test filename.

A reviewed graphify-out/graph.json contains 145 nodes and 634 edges and does NOT cover every service or caller; supplement with source-wide import/call searches and API contract tracing. After each meaningful implementation step use AGENTS.md instructions to regenerate Graphify only if its dependency environment is installed.

## Add small test modules by implementation slice
1. NEW test_agent_tools.py: metadata and real availability, exact fields, wrong-project rejection, read vs submit permission, unsupported tool blocked, duplicate invocation/reconciliation.
2. NEW test_agent_skills.py: global/app/project skill discovery; provider absent, changed hash, collision, path traversal/symlink; Editor and Director parity and context-budget behavior; untrusted skill cannot grant shell.
3. NEW test_agent_tasks.py: plan does not submit; approval binds plan hash and project; stale revision rejected; pause/resume, failed job, lost response lookup and idempotent recovery; plan updates require new approval.
4. NEW test_agent_project_graph.py: actual source ID/hash provenance, no invented assets, same asset in multiple shots, versions, project A/B isolation, checkpoint Save/Load without overwriting more recent work.
5. NEW test_agent_editor_tool_handoff.py: a video in Editor is passed to shared Extract MP3, original not changed, a registered audio asset returned, selected range preserved, Editor second clearance still required for render, no soundtrack auto-replacement.
6. NEW test_agent_video_prompt.py: R2V exact image/video/audio slots, true FL2VA first-last, no R2V fake first_frame; T2V blank refs; duration/codepoint cap and voice identity vs prerecorded track.
7. LTX OFF only AFTER new contract: new-version per mode, zero refinement chunk enqueue, valid final Turbo audio/video, old version resumes LTX unchanged, cancellation and hash/drift failures.

## Disposable synthetic fixture pattern (runnable example)
Use Python unittest + tempfile; a fixture project and ledger/database must live entirely under the temporary root.

    from pathlib import Path
    from tempfile import TemporaryDirectory
    import subprocess
    import shutil

    def test_short_synthetic_video():
        with TemporaryDirectory(prefix="vibe-agent-fixture-") as temp:
            root = Path(temp)
            video = root / "synthetic.mp4"
            if shutil.which("ffmpeg"):
                subprocess.run(
                    ["ffmpeg", "-v", "error", "-f", "lavfi",
                     "-i", "color=c=blue:s=64x64:r=4:d=1",
                     "-c:v", "libx264", "-y", str(video)],
                    check=True, timeout=20, capture_output=True)
                assert video.exists()
        assert not root.exists()

Do not use this short silent video to test a pipeline contract that requires an audio stream: build a compatible generated WAV/audio stream in temp if necessary. The example itself is only a disposable fixture exercise.

## Cleanup guarantees
- Tag every test-owned project, DB and file with unique temp root and run marker. Keep source tests in repo, delete *generated* media after execution.
- Use try/finally or TemporaryDirectory/pytest tmp_path so failures still clean.
- Never use rm -rf against live projects, Downloads, shared repertoire or unmarked paths.
- If a worker remains alive, stop/reconcile only the owned test job; report leftover instead of deleting uncertain external work.
- Verify root removed and no test-only rows remain in isolated test storage. A simulated/mocked test does NOT prove a live GPU render.
- No paid/provider or live GPU generation without explicit owner approval.

## Code-quality acceptance
Proposed fix must have a small explicit API, type/schema tests, one place for business logic, a backward-compatibility test, a failure-path test, and a cleanup assertion. Prefer short pure functions and shared adapters over redundant abstractions and giant dispatcher/page modifications.
