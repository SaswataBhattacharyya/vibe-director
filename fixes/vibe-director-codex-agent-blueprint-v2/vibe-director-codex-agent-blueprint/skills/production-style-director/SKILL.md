---
name: production-style-director
description: Define optional production-type, visual-style and directing-language guidelines for film, animation, advertisements, documentaries and other outputs. Apply chosen creative guidance consistently to screenplay, Z-Image characters/backgrounds, comic storyboards and video prompts without blocking direct generation or enforcing a wizard.
metadata:
  product: Vibe Director
  version: '1.0.0'
---

# Production Style Director

## Purpose
Translate a user's creative request into an **editable, optional creative brief**. A production TYPE describes the deliverable and narrative conventions; a VISUAL STYLE describes the look; DIRECTING LANGUAGE describes camera, editing, lighting and performance conventions. These are independent dimensions, not mutually exclusive workflow routes.

Example: `type=short_film`, `visual_style=anime`, `direction=cinematic`, `tone=gentle_fable`. A cinematic camera is not a competing alternative to anime visuals.

## When to load
- Choosing or changing Production Type & Style.
- Generating or revising story/screenplay, character, background, storyboard or video prompts where a style brief has been selected.
- User says “make it cinematic”, “turn this into anime”, “make a kids' fable”, or requests consistency across a project.
- Style advice from the Director/Editor chat, or a per-scene override.

## Inputs
Current project and optional story; selected output category and genre; visual-art direction; camera/lighting/pacing preferences; reference images or videos; target audience and format; user-approved style rules; relevant model capability. All fields may be absent. Never require an accepted screenplay merely to choose a style or generate media.

## Output contract — CreativeBrief
Maintain a versioned, editable record with these fields (illustrative schema; map to existing versioned style selection before introducing fields):

- `project_id`, `brief_id`, `revision`, `source_selection_id?`
- `production_type?`: film, short film, animation, advertisement, documentary, educational, corporate, music video, presentation, custom
- `genre?`, `audience?`, `story_goal?`, `runtime_target?`
- `visual_style?`: cinematic realism, 2D anime, 3D stylized, watercolor, stop motion, comic book, custom
- `camera_language?`: camera movement and shot-grammar guidance
- `lighting_palette?`, `character_motion_style?`, `dialogue_style?`, `editing_rhythm?`
- `reference_assets[]`: approved actual asset IDs, not guessed filenames
- `positive_rules[]`, `avoid_rules[]`, `per_scene_overrides[]`
- `approved_by_user?`, `version_origin`, `updated_at`

A `CreativeBrief` is **advice**, never an execution prerequisite for manual Video Create. Existing accepted production/style snapshots remain intact for historical frozen jobs. Changing a draft brief does not rewrite already generated work.

## Guidelines by type
- **Film / short film:** character goal, conflict, causal action, strong scene transitions, emotional beats, playable dialogue and visual subtext. Estimate total runtime and split into clips matching the selected generator's limits.
- **Animated fable:** clear physical actions, expressive faces, readable silhouettes, simple cause-and-effect and concise dialogue. Avoid excessive narration if characters can act.
- **Advertisement:** hook, value proof, claim safety, product legibility, call to action. Do not invent unsupported product claims.
- **Documentary / news:** factual sourcing, uncertainty, attribution, coherent chronology. Don't fabricate footage or quotes.
- **Educational:** clear explanation sequence, pacing for comprehension, definitions and accurate visuals.
- **Music video:** performance/edit rhythm aligned to supplied music; audio must be actually provided or generated separately.
- **Custom:** interpret user brief; do not force an existing category.

## Rules by visual style
- **Anime:** stylized proportions, 2D/illustrated line quality, cel shading, readable expressions, key poses and limited-but-intentional motion. 'Cinematic' can coexist as camera/lighting grammar.
- **Cinematic realism:** plausible physics, controlled lens/depth, natural texture/lighting and motivated camera movement.
- **Stylized 3D:** consistent modeling language, controlled materials and clear character silhouettes.
- **Comic book:** coherent panel composition, action readability, dialogues/captions rendered as UI text rather than generated into artwork unless requested.
- **Watercolor/stop motion/etc.:** select medium-specific material and motion cues without overwriting core story facts.

## Propagation across six existing skills
1. **Screenplay Writer:** type controls story structure, rhythm and dialogue guidance. Style controls performance/camera suggestions. Keep story facts unchanged.
2. **Character Designer:** inject visual style and identity constraints into Z-Image prompts. Identity features remain separately stored and reusable.
3. **Environment Designer:** maintain locations, palettes, lighting and spatial landmarks across Z-Image world/background prompts.
4. **Storyboard Director:** use the selected drawing aesthetic for comic panels, while panel text remains editable UI content.
5. **Cinematic Prompt Director:** include only the relevant short style clauses in an exact-time, model-specific prompt. Preserve `<Picture N>`/`<audioN>` bindings and generator limits.
6. **Continuity Director:** compare visual/style reference snapshots across shots; warn about unintentional jumps and propose a bridge shot when useful.

## Operational constraints
- User may skip the brief, choose defaults, override a single shot or work directly in Video Create/Editor.
- Choosing “film” must never force 'cinematic realism'; choosing “anime” must never imply one production type.
- A style setting only influences a generation if its chosen version is actually attached to the prompt or corresponding validated engine request; don't falsely claim backend enforcement.
- Describe which assets or style fields will change. Apply edits through reviewed/versioned project actions, not by mutating frozen jobs.
- Respect actual generation mode: for this MiniMax H3 R2V workflow a clip is at most 15s and prompt strictly below 7,000 Unicode codepoints according to the reviewed contract. Modes have different reference semantics. Voice-sample reference is not a prerecorded dialogue track.
- Use the user's requested style above a default, but never violate supplied story facts or actual asset constraints.
- If user asks to perform an action, discover the registered application tool first; a skill is guidance, not executable permission.

## Compact output for UI
Show type, style, directing language as 3 independent editable selectors and an optional 'Production guidelines' disclosure. Provide short downstream examples: “Screenplay”, “Character image”, “Storyboard”, “Video prompt”. Present a 'Use for project' or 'This shot only' choice. Offer 'Skip' without penalty.
