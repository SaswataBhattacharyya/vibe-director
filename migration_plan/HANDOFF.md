# Migration planning handoff

**Milestone:** planning audit complete, 7 October 2026.

## Objective and direction

Migrate/reorganize the existing working Story Builder website into the sole Vibe Director project directory, reusing code/workflows/assets. Thoroughly inspect Story Builder and inspect installed ComfyUI dependencies as required. Deliver capability inventory, UI/customer journeys and code/API/data migration plans in Markdown. User explicitly rejected a scratch rebuild.

## Authoritative planning files

`/home/riki/Documents/ChatGPT/Vibe Director/migration_plan/00_READ_ME_FIRST.md` indexes the capability catalog, journeys, UI/routes, copy/API plan, runtime/data plan, small-PR backlog, glossary/decisions and complete source index. Earlier 3 October PLAN/REUSE_AUDIT are historical and superseded for migration direction.

## Completed

- Read-only source/AST/JSON audit: 71 top-level services, 224 HTTP routes plus lifecycle, frontend pages/navigation, 90 workflow JSONs including nested subgraph definitions.
- 115 capability entries distinguish integrated, recorded acceptance, standalone, workflow, engine-only and partial/gated features.
- Installed model inspection enumerated 305 weight entries; no model binaries loaded.
- Preserved evidence limits: source reports 803 backend/14 frontend tests and browser 24 pass/8 skip; this audit did not rerun them.
- Planned one existing React/FastAPI package copy, independent modes/routes, modular routers and safe data/evidence preservation.
- Identified pause-tag adapter issue, partial pipeline dispatch/reconstruction/Canvas, raw-output manifest acceptance gap and missing-smoke/data/startup hazards.

## Next work

Review the planning documents, choose first implementation PR from backlog and create a source/data manifest. No product migration, runtime install, renderer/provider invocation or remote write was performed. Copying product code and applying UI changes are future implementation work.

## Permissions and context

Owner SaswataBhattacharyya, collaborator ashucodesbio, private-repo preference. No external message/invitation/issue/PR created. Source directories must remain intact. No subagents were used. The old empty Vibe Director 2 checkout was previously moved to `/tmp/vibe-director-2-empty-backup-20261003`; environment cwd still points at its former location, so commands must set a valid workdir explicitly.

The writable-root list still names the old directory; final document writes into Vibe Director require a scoped sandbox escalation. It is already authorized by the user's request to save the plan there. Planning output was staged under `/tmp/vd_migration_plan`.

## Live handles / blockers

This audit created no background processes or model jobs. Source release mentions launcher session 83317; historical only, not inspected here. Current engine/job state must be checked before later live cutover. Preserve source-recorded acceptance holds and `/tmp/storybuilder-full-controller-acceptance-20261006-nlmgwm4y` evidence before cleanup. No blocker for delivering the planning files.
