# Skills — integrate existing, global and project skills without losing history

Currently live paths: skills/vibe-director/SKILL.md, skills/video-prompting/SKILL.md (including its references), and design/vibe-editor/skills/vibe-editor-director/SKILL.md. The 13 additional SKILL.md files are documentation under fixes/vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/skills/ until explicitly installed/bound in a new resolver.

## Change only AFTER shared agent skill service is tested
1. Keep the existing live three craft skills and references intact. Do not overwrite their behavior with a flattened concatenated prompt.
2. Review the 13 blueprint skills individually; install under unique stable IDs in app skills/ directory OR register their approved package roots. Validate frontmatter, relative links and any assumed tools. Do not auto-install them merely because fixes folder exists.
3. Build ONE backend skill resolver for BOTH Director and Editor: discover metadata from configured global installed skill providers, bundled application skill roots and project-owned versioned SKILL.md/guidance records. Global skills can be dynamically installed/removed/refreshed without code changes if the provider permits discovery.
4. Metadata first, then selected relevant Markdown/reference reads with safe path roots, size/context budget, source/provider/hash/version, project ownership and clear collision rules. No arbitrary whole-home-directory scan or copying global private skills/secrets into portable project archives.
5. Precedence only for creative advice: explicit user request > approved project style jackets > selected globally/bundled creative guidance > default. App security, actual tool permissions, ownership and exact workflow validators outrank all skill text.
6. Update backend/story_builder/services/director_skills.py as a compatibility facade over shared resolver; keep previous video-prompting output format stable until regression tests pass. Editor can select its specialist craft skill through the SAME resolver but its render-only JSON adapter stays non-executable.
7. Integrate optional independent production type, visual style and directing style as project-scoped/versioned **jackets**; existing production_styles.py and production_director_profiles.py retain published historical snapshots. User can choose None/Inherit and edit a project-specific jacket without changing global defaults.
8. Project Save/Load stores project-owned skill content, referenced global IDs/hashes and chosen jacket version. Missing global skill on later load triggers review, not silent replacement.

## Safety and tests
A global computer/coding skill cannot magically grant terminal access: separately authorized sandboxed computer runtime and typed tool policy are required. Test unknown provider, skill hash drift, project A/B separation, symlink/path traversal, malicious Markdown, context cap, collision display, Editor/Director parity, global provider refresh and the old three loader paths. Remove temporary test-owned skill directories/rows after tests.
