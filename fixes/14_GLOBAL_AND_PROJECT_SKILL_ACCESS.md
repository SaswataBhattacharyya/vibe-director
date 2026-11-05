# Shared global + project-specific skill discovery and use

**Mandatory architecture contract for both Vibe Director and Vibe Editor.** Skills are reusable instructions, not executable capabilities or permission grants. The agents can plan, write code, execute tools, and automate desktop/browser workflows only through installed, authorized runtimes and validated tool adapters.

## Skill source layers

| Layer | Storage/discovery | Persistence | Example |
|---|---|---|---|
| Global installed | Configured supported agent skill registries, installed skill roots or plugin APIs; discover at runtime | Reference by provider, ID, version/hash; not copied into projects | coding, browser, computer, research skills |
| Bundled application | Versioned repository `skills/` plus existing approved Editor/video-directing skills | Versioned with deployment | screenplay writer, continuity, video prompting |
| Project-specific | Project-owned skill records and Markdown content or approved project instruction snapshots | Saved/restored with project; owner-scoped | film style jacket, character bible guidance, production preferences |
| Per-task directives | Current user's request and approved plan | Task/revision-scoped | 'use this reference, no music, only 15 seconds' |

All layers are discoverable by **both agents** through one interface. Only enabled, authorized, available sources are usable. A missing global provider appears as `unavailable`, not an invented skill path.

## Required service contract

`SkillRegistry` (server side; no UI-only truth):
- `list_skills(project_id, actor_id, filters?)` — metadata only; scope, name, description, provider, version/hash, availability, enabled state.
- `search_skills(query, project_id, actor_id)` — rank by task intent; no unrestricted reading of unrelated project data.
- `get_skill(skill_ref, project_id, actor_id)` — validated skill metadata and permitted doc references.
- `load_skill_context(skill_refs, task_id, project_id, actor_id, budget)` — bounded, selected Markdown with provenance hash and source URIs; resist path traversal and symlinks outside declared allowed roots.
- `refresh_skill_sources(source?)` — find newly installed, changed, disabled or removed skills; emit version-aware UI updates.
- `bind_project_skill`/`unbind_project_skill` — reversible, revisioned, authorized project changes with expected-version checks.

Do **not** infer global skill sources by scanning the entire home directory; use configured roots and real installed-provider interfaces. Availability reflects runtime truth. Cache by `(provider, skill_id, content_hash, project_id where relevant)` and invalidate on change or explicit refresh.

### Minimal metadata record (illustrative, not a new mandatory backend schema)

```json
{
  "skill_id": "cinematic-prompt-director",
  "source": "project",
  "provider": "vibe-project",
  "project_id": "story-example",
  "version": "3",
  "sha256": "content-hash",
  "enabled": true,
  "status": "available",
  "description": "Model-aware reference and camera prompt authoring",
  "content_ref": "project-owned-safe-skill-reference"
}
```

The Director and Editor may load the same skill metadata/content; they may select different skill **sets** based on task. Project-specific creative styles are modifiers (not a second agent), may be layered (e.g. film + anime + cinematic), and must be tied to a versioned creative brief. Skill conflict policy: explicit current user instruction > applicable project creative jacket > global/bundled creative guidance. Security, permission, compliance, provenance, app model contracts and reality always take priority over skill prose. Flag incompatible instructions, don't silently pick a dangerous winner.

## Runtime and trust boundaries

- Reading a skill is a **read operation**, not approval to execute its instructions. External/global/project skill content is considered untrusted input when it contains commands, paths, URLs or text from outside sources.
- Tool calls must use typed schemas, live capability and ownership checks, and per-operation authorization. Computer/terminal/network/GUI access requires an available runtime and configured sandbox/permission profile; never grant shell access merely because a global coding skill is installed.
- No skill may change frozen generation jobs, bypass media hash checks, cross project boundaries, GPU watchdog, editor approval, export grant or tool validation.
- The agent must provide inspectable evidence: which skills were loaded, which tool calls were actually executed, and their outputs/status. Missing tool support must be reported instead of simulated.
- Avoid model context floods: metadata retrieval first, load only relevant complete skill files plus permitted references, size-cap with refusal/selection if over budget; include provenance/hash in task logs.

## Project ownership and portability

Record project-owned skill content and bindings in existing project checkpoint mechanism or a versioned companion record with validated roots, project ID, revision and content hashes. Resolve registered global skills at runtime after Load; if absent or changed, show a reconnect/review prompt, preserving historical references and any frozen creative decisions. Never copy global secrets, private instructions or entire global installations into portable project exports. A project switch must atomically switch visible skill bindings and prevent late responses/results from carrying another project's instructions.

## UI expectations

- Shared Skills panel/filter in Director and Editor chats: search, scope badge (Global / Bundled / Project), version, enabled/available status, inspect/load/refresh.
- User can say: 'Use my global coding skill with this project's film-style jacket' and see actual selection in the plan.
- User can add or disable project creative guidance without editing application source. A global skill install/update/removal is discoverable after refresh.
- Preserve existing left navigation and Media Prep UI; expose skills through chat and compact tool context, not another mandatory wizard.

## Integration order and acceptance

1. Read current `director_skills.py`, `skills/vibe-director`, `skills/video-prompting`, and `design/vibe-editor/skills/vibe-editor-director`, plus repo/global skill-provider contracts before modifying anything.
2. Implement metadata-only listing/search across actual configured sources and shared permission/provenance model; initially read-only.
3. Add project bindings/versioning and on-demand context loader; connect **both** chats to the same interfaces. Keep legacy skill paths functioning via adapter/fallback.
4. Test installing/removing/updating a **temporary test-owned global skill**, creating a **temporary project skill**, collision reporting, selective loading, hash invalidation, project switch/isolation, Save/Load and missing-global handling. Remove temporary skill directories/records when tests finish.
5. Prove global skill availability does not magically expose commands: shell/browser requests remain blocked until actual runtime authorization. Demonstrate one authorized small tool call for Director and Editor through shared gateway.

**Completion criterion:** both agents can discover, inspect, selectively load and apply the same installed global and project-specific skills, with scoped continuity, provenance and tool security; installing a new skill needs no application code change.
