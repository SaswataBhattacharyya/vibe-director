# Test guide — current UX04/MED/compact-layout plans

Existing R01/R02/UX01/UX02/UX03 tests ran in previous Codex batch and its reported results are in fixes/R01_UX03_RESULTS.md. This document update does not rerun them. No reason to redo the feature patches.

## UX04: one shared agent composer per route
Use current frontend/tests/director-runtime.spec.mjs, create-panes.spec.mjs, and dedicated new route tests. For each Screenplay, Prompt, Video Create, Image Assets, Text-to-Image, TRELLIS, Media Prep route, verify exactly one LIVE AI conversation composer (shared Director) while keeping genuine task fields, model settings and search inputs. Mock valid agent proposal, render correct before/after and Apply, check source revision CAS, old archived chat history readable, unknown/unavailable action visibly blocked. Switch project/session during pending request, no late write to wrong target.

## MED01 picker parity
Tests with mixed image/video/audio and two project owners. All/current/other projects, folder, downloaded, extracted, generated, voice-only, analyzed indexed, newest/oldest/name sort, keyword/semantic availability, cards/list/carousel, keyboard and selection persistence. Assert a chat attachment does NOT fill R2V model slots or Editor range; explicit model ref validates exact workflow/role/limit. Safe folder choice requires user consent; unknown file is not registered until import. Generic picker must not offer permanent delete.

## MED02/MED03 backend
Extend existing test_media_catalogue.py, test_media_selection_scope.py (if present), test_media_search... and project Save/Load tests. Browse filters before pagination (25th item, no duplicate), stale analysis badge false, missing files, source folder scanner budget and authorized roots. Cross-project reference reuse does not copy bytes unless selected, preserves SHA, returns proper project IDs and membership names, missing source/relink, edits to one project's tags do not leak to other, archived/delete one membership does not remove original, frozen job still resolves, moved checkpoint handles missing external source. Preserve old API tests.

## UX05/06/07/08 visual and state
At 1440×900, 1280×720, 900×768 and 390×844 with outer panes expanded, measure horizontal overflow, clipped action buttons/footer, focus/keyboard and modal layering. Image Assets canvas not nested, no old ImageAssetsDirectorChat, main Generate and candidates visible; output path compact but Change opens all existing options. Current Take player once, real mocked status and accepted/retake/next, batch/full-run pause/retry, thumbnails, saved playback position, no media job duplicate or re-admission when toggling details. Re-open advanced settings, errors and relink states. Media Prep processing regression remains required.

## Cleanup and permission
Use tempfile.TemporaryDirectory and fixture-owned project folders for dummy PNG/WAV/MP4/TXT. Cleanup after success AND injected failure, verify absence and no user project path touched. Playwright mocked proxy must not point at live local backend. No paid provider/GPU without separate owner authorization. Report actual commands, results and limitations; screenshot inspection/mock tests cannot prove actual video/audio quality.
