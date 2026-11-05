# Story tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## story.styles — Production type and directing style

**Choose when:** Choose production format, creative treatment or learn style from sources.

**UI:** #/styles

**Inputs:** Production type/version, directing style/version, context/project; optional uploaded style sources or selected images and intent.

**Outputs:** Selection snapshot, published style or source-analysis proposal.

**How to use:** Use styles-api.ts catalogue/selections/publishing and source/media analysis helpers. Preview proposals before adopting; styles are guidance, not an execution tool.

**Source:** [styles-api.ts](../frontend/src/lib/styles-api.ts), [ProductionStylesPage.tsx](../frontend/src/ProductionStylesPage.tsx), [production_styles.py](../backend/story_builder/services/production_styles.py), [style_sources.py](../backend/story_builder/services/style_sources.py)

## story.author — Story write, import, edit and revisions

**Choose when:** Create/import story text or revise it without losing history.

**UI:** #/story

**Inputs:** Title, source text or import file; selected text offsets, expected text, instruction and base revision for edits.

**Outputs:** Source revision, import preview, edit proposal or restored revision.

**How to use:** Use story-api.ts uploadStoryFile then applyStoryImport; source draft/revision helpers; proposeStoryEdit then accept/discard. Preserve optimistic revision checks and idempotency.

**Source:** [story-api.ts](../frontend/src/lib/story-api.ts), [story_imports.py](../backend/story_builder/services/story_imports.py), [story_authoring.py](../backend/story_builder/services/story_authoring.py)

## story.graph — Story facts and entity graph

**Choose when:** Inspect extracted facts, search story context or resolve character/location identities.

**UI:** #/story → Story graph

**Inputs:** Source revision, graph snapshot; query or record edits; identity-decision fingerprints/head.

**Outputs:** Graph records, search hits or identity decision.

**How to use:** Use buildStoryGraph/getStoryGraph/searchStoryGraph/updateStoryGraphRecord/decideStoryGraphIdentity. Extraction coverage is not proof every narrative fact was found.

**Source:** [story-api.ts](../frontend/src/lib/story-api.ts), [story_authoring.py](../backend/story_builder/services/story_authoring.py)

## story.screenplay — Screenplay preparation and whole-screenplay chat

**Choose when:** Draft screenplay or discuss a change across all scenes/shots.

**UI:** #/screenplay

**Inputs:** Story revision/graph snapshot, screenplay revision, instruction/history; selected proposal changes.

**Outputs:** Structured screenplay revision, conversation, proposal and explicitly applied revision.

**How to use:** Use draftStoryScreenplay and screenplay revision/save/accept helpers; storyboard-api.ts conversation/chat/propose/apply for whole-screenplay direction. Discussion and applying changes are separate operations.

**Source:** [story-api.ts](../frontend/src/lib/story-api.ts), [storyboard-api.ts](../frontend/src/lib/storyboard-api.ts), [ScreenplayDirector.tsx](../frontend/src/ScreenplayDirector.tsx), [storyboard.py](../backend/story_builder/services/storyboard.py)

## story.board — Frame per shot and storyboard

**Choose when:** Prepare optional shot imagery or a scene-based finished storyboard.

**UI:** #/shot-frames or #/storyboard

**Inputs:** Screenplay revision, board revision, shot descriptions/dialogue, chosen image assets and optional preparation choices.

**Outputs:** Revisioned board records and scene text/image presentation.

**How to use:** getBoard/saveBoard with expected_revision. Frame generation delegates to image services; current board automatic framing includes browser orchestration, not one universal backend tool.

**Source:** [storyboard-api.ts](../frontend/src/lib/storyboard-api.ts), [StoryboardPage.tsx](../frontend/src/StoryboardPage.tsx), [storyboard.py](../backend/story_builder/services/storyboard.py)

## production.setup — Automation and assisted production setup

**Choose when:** Choose production mode, optional stages and saved generation parameters.

**UI:** #/setup

**Inputs:** Screenplay revision, mode, automate_steps and workflow/duration/output settings per current schema.

**Outputs:** Saved setup/hash, stage skips and planned work.

**How to use:** Use getProductionSetup/saveProductionSetup and assisted-stage/frame skip helpers. Inspect production_setup.py: current fully automated policy differs from manual reference workflows. Do not promise every optional stage is accepted in every mode.

**Source:** [story-api.ts](../frontend/src/lib/story-api.ts), [ProductionSetupPage.tsx](../frontend/src/ProductionSetupPage.tsx), [production_setup.py](../backend/story_builder/services/production_setup.py)

## prompts.prepare — Shot, clip, character and world prompting

**Choose when:** Prepare/edit generation instructions or teach reusable prompting preferences.

**UI:** #/prompts

**Inputs:** Revision/setup, shot or asset target, workflow ID, current prompts, instruction; proposed lessons.

**Outputs:** Prompt drafts, per-clip prompts, character/world guidance, proposed lessons and exported skill text.

**How to use:** Use prepareStoryPrompt, prompt draft saves and assisted clip planning. prompt-director-api.ts supports chat/propose/learn and exportPromptSkill; review/save lessons explicitly. Read model-specific guidance before preparation. Learning is saved guidance, not model training.

**Source:** [prompt-director-api.ts](../frontend/src/lib/prompt-director-api.ts), [story-api.ts](../frontend/src/lib/story-api.ts), [prompt_director.py](../backend/story_builder/services/prompt_director.py), [workflow_knowledge.py](../backend/story_builder/services/workflow_knowledge.py), [SKILL.md](../skills/video-prompting/SKILL.md)
