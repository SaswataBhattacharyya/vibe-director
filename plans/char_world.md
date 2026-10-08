# Character, world, frame, and voice planning for Story Builder

**Status:** Current product plan; planned workflow. Use `README.md`, `GLOSSARY.md`, and `automation.md` for authority, terminology and execution wrappers.  
**Position in the journey:** Follows the accepted, readable screenplay and its validated production breakdown. This plan organizes image asset creation and character-to-voice assignment into a small number of focused pages rather than reproducing Story Builder's scattered legacy controls.

## 1. Goal

After the screenplay and its derived scene/shot/clip records are usable under the selected wrapper, give the Director a clear place to create and approve the visual assets needed to stage the story:

1. Character reference images.
2. World/location/background images for scenes.
3. Optional first and last frames for each video-generation clip, grouped under scene and shot.

When used, provide one voice assignment page where each character can be bound to a selected voice file. The visual and voice pages consume the same canonical screenplay, character, world, and scene identities. They should not become separate sources of story truth.

## 2. Place in the full workflow

```text
Story + knowledge graph
  → accepted screenplay with scene / beat / shot / dialogue direction
  → validated production breakdown
  → Automation & Parameters (before model prompts)
  → Character images
  → World / location backgrounds
  → Optional first and last clip frames (Skip available)
  → Character-to-voice assignment
  → Shot-level image/video/audio generation
```

Each stage should show its screenplay and production references so the user knows why an asset is needed and where it will be used. Generated assets remain candidates until explicitly accepted.

## 3. Visual asset pages

Use three focused pages, with a shared stage header showing sequence, completion, links to the screenplay and a Skip option. Visual preparation is optional when the intended workflow does not need it; fully automatic mode skips image generation entirely. Two pages may be combined later if usability testing shows the combined page remains clear; keep the data and approvals separate by asset type.

### Page 1 — Character images

Show one card/row per canonical character from the accepted story and screenplay:

- Display name, stable character ID, role, short description, wardrobe baseline, and key visual/continuity traits.
- Generate one or more character reference image candidates from the approved character description, selected visual style, and applicable references.
- Keep image creation and review usable without reading prompt JSON. Show a readable **Prompt and references** panel on each candidate, with the exact text prompt, selected reference thumbnails/names, and the role each reference plays.
- Allow direct prompt editing before generation and precise annotation: the user selects a phrase or prompt segment, enters an instruction in a contextual chat box, and receives a proposed targeted edit. Show the revised prompt and let the user accept or continue editing before regeneration. Preserve the original and each accepted revision.
- Allow candidate comparison, regeneration, accept/reject, and optional notes.
- Keep approved character references attached to that character ID so scene images and shots can reuse them.
- Show characters with no image, conflicting visual descriptions, or unapproved candidates as actionable status.

Character images establish visual identity. They do not automatically determine voice identity.

### Page 2 — World and scene backgrounds

Show canonical worlds/locations and the scenes that use them:

- Group scenes by shared location/world so a single approved location reference can support several scenes.
- Display scene slugline, time/weather, mood, lighting direction, relevant screenplay description, and continuity requirements.
- Generate background/world image candidates for a location. Allow scene-specific variants where story time, weather, damage, or lighting materially changes the setting.
- For every candidate, expose the exact editable prompt and reference assets used (thumbnail, asset name, and intended influence). Support selected-text annotation through a contextual chat box for precise changes. Proposed edits are reviewable; they do not overwrite the prompt until accepted.
- Accept a stable world/location master image and optionally scene-specific background variants.
- Show which scenes use each image; flag a location whose appearance changes without an explained screenplay reason.
- Avoid duplicating a separate background image for every scene when scenes share the same world and conditions.

### Page 3 — Optional first and last frames for each clip

Show an ordered scene list with nested shots/clips. Each planned video clip can have its own first/last pair:

- Scene number/title/slugline, summary, characters present, action at the start and end, lighting/mood, and linked approved character/world references.
- Generate and compare a **first frame** and **last frame** for the selected clip, keeping their roles distinct. Label them Scene 1 / Shot 1.1 / Clip 1.1.1 / First or Last. Optional scene-level overview images are not substitutes for clip anchors.
- The first frame establishes the clip's opening composition/state; the last frame establishes its ending state. Preserve the scene/shot continuity context around both.
- For each frame candidate, show the exact prompt and all reference images used. Let the user edit the prompt directly or select a phrase/segment and request a precise change in a contextual chat box. Present the proposed prompt revision for review before regenerating. Keep prompt revisions and asset lineage with the candidate.
- Accept each frame independently; support regenerate, reject, compare, and notes.
- Preserve scene/shot/clip order and stable IDs rather than relying on visible numbering.
- Validate that required characters/locations have approved references or clearly allow the user to proceed with a disclosed missing-reference warning.
- Once accepted, expose the frames as continuity references to shot-level image/video generation; do not silently replace them after downstream shots exist.

A first/last-frame pair anchors one video-generation clip. Skip frame generation when using text-to-video or other references; selecting first/last-frame mode later requires supplying its two inputs, including by upload. Skipping a page does not fabricate completion or force a fallback workflow.

## 4. Character-to-voice page

Provide one dedicated **Voices** page after the visual-reference stage. It is a binding interface, not a voice-generation tool by default.

### Character list

For every active character, show:

- Character image thumbnail and name/role.
- Short approved character description and any voice guidance from the screenplay/story bible.
- A searchable dropdown of available voice files/assets, with preview/playback, voice name, language/style metadata, and any permitted sample.
- Current binding state: selected voice, unassigned, or unavailable.

### Binding behavior

- Each character may select a voice file independently.
- The same voice file **may be selected for multiple characters**; do not enforce unique voice selection or auto-reserve a voice after it is assigned.
- Search/filter the available voice assets by name and supported metadata. Keep the dropdown usable for large libraries.
- A voice binding links `character_id` to `voice_asset_id`; it should not copy the audio file into each character record.
- Support a clear/unassign action and indicate where the binding is used in dialogue/audio generation.
- Show warnings for characters with dialogue and no voice assignment. Narrator and non-speaking characters should be labeled distinctly so lack of a voice assignment is not treated as an error.
- Changing a binding affects future voice generation and previews. It must not rewrite existing approved audio outputs without an explicit regeneration action.

Voice identity is separate from visual identity. A character's voice can be reassigned without changing the character image or screenplay description.

## 5. Shared interaction and state rules

- Every generated asset is a candidate until the user accepts it; maintain candidate history and the accepted asset ID.
- Save each prompt revision, chosen references, generation settings, and output against project, screenplay revision, graph snapshot, source hash, and relevant character/world/scene IDs. The candidate detail view must make the actual prompt and actual reference set inspectable, not merely show a reconstructed approximation.
- Annotation is a precise prompt-editing interaction: selection identifies the target span; the user's instruction is applied to that span while preserving unrelated prompt content. Show the before/after text and require acceptance before it becomes the next generation prompt.
- Reference changes, prompt edits, and model/workflow changes create a new candidate/revision; never silently mutate the lineage of an existing generated image.
- If a screenplay edit changes a character's appearance, a location, or scene opening/ending, mark only related assets as potentially stale and explain why.
- If the underlying approved screenplay changes, preserve the previously accepted assets and offer targeted regeneration. Never silently overwrite them.
- Keep images, descriptions, prompts, and reference roles connected to the canonical story graph, but let users work through cards and previews instead of graph IDs or JSON.
- Provide consistent status labels: not started, generating, candidates ready, needs review, accepted, stale, failed.
- Support manual creation/upload, assisted generation, and automatic generation using the same asset records and review rules.
- Keep approved project references distinct from unapproved candidates. Downstream shot generation should receive approved references by default.

## 6. Generation context and prompt assembly

For each candidate, assemble relevant inputs from approved project data:

- **Character image:** character description, wardrobe/appearance continuity, visual style, and user-selected references.
- **World/background:** canonical location description, applicable scene conditions, mood/lighting, and approved world references.
- **Clip first/last frames:** action at the clip boundary, scene/shot continuity, cast, selected character/world images, camera/composition direction and screenplay lighting/mood.

Show the final assembled prompt and reference list before generation, with each reference's intended influence. Prompt assembly should not infer or change screenplay facts silently. When an LLM proposes prompt wording, preserve the user's screenplay facts and make changes reviewable. Prompt and reference provenance must travel with the generated candidate into downstream video generation.

## 7. Suggested page layout

```text
Visual preparation
  1. Characters       [images + identity continuity + prompt/reference inspector]
  2. Worlds           [locations + backgrounds + prompt/reference inspector]
  3. Clip frames      [optional first/last pair per clip, grouped by scene/shot; Skip]

Voices
  Character | Reference image | Description | Searchable voice selector | Preview | Status
```

The three visual pages can be reached in sequence, skipped and revisited independently. Voice assignment is an optional single page after visual preparation, with a persistent character list and clear save state. Full does not wait at these skipped/manual asset stages.

## 8. Implementation boundaries

These are planned responsibilities, not existing API names:

- **Character asset workspace:** candidate generation/review and accepted reference binding to character IDs.
- **World/location asset workspace:** reusable location masters and scene-condition variants.
- **Clip frame workspace:** optional first/last frame candidate and approval records keyed by clip ID, linked to scene and shot IDs.
- **Prompt revision and annotation service:** target-span edits, before/after review, and prompt revision lineage shared by all three visual asset workspaces.
- **Voice binding workspace:** searchable voice catalog, preview, and reusable character bindings.
- **Asset lineage service:** candidate history, approvals, prompt/reference provenance, stale detection, and downstream-use references.
- **Generation adapters:** build image/audio requests from approved screenplay fields and approved references; return outputs as candidates until accepted.

The UI should call shared asset and prompt services and store role/type metadata explicitly. It should not duplicate generation logic or create a separate production controller for each page.

## 9. Delivery order

1. Define character, world/location, scene-frame, voice-asset, binding, prompt revision, and reference records with stable IDs and screenplay lineage.
2. Build the character image page with visible/editable prompts, precise annotation, candidate review, and approval/reuse behavior.
3. Build world/location backgrounds with reusable masters, scene-specific variants, and the same prompt/reference editing controls.
4. Build the scene frame page with first/last candidate generation, precise prompt annotation, and independent approval.
5. Build the searchable voice library selector and reusable character bindings.
6. Connect approved visual and voice references to shot-level generation; implement stale detection and explicit regeneration behavior.
7. Migrate useful legacy assets into the new records, preserving their provenance and marking approval status accurately.

## 10. Acceptance criteria

- A Director can find all canonical characters, locations, and scenes without searching through unrelated controls.
- Character references can be generated, compared, approved, and reused across scenes.
- Each image candidate exposes the prompt and references that actually produced it.
- The Director can make a precise selected-text prompt edit, review the before/after result, and regenerate without losing the prior prompt/candidate lineage.
- Shared locations can reuse one master background, with scene variants when justified.
- Every planned clip can have independently reviewed first/last frame anchors with stable scene/shot/clip links; the frame stage can be skipped and supplied later when needed.
- Every character appears on the voice page with image and description, and can select a voice via search.
- One voice asset can be assigned to multiple characters without warnings or uniqueness constraints.
- Unassigned speaking characters are visible; non-speaking characters are not incorrectly flagged.
- Accepted outputs are traceable to the screenplay revision and are not silently replaced when source material changes.

## 11. Planning boundary

This plan describes a clean Story Builder workflow for visual preparation and voice assignment. The legacy Story Builder contains related generation utilities, but their presence does not mean this focused page sequence, shared asset lineage, prompt annotation workflow, review states, or voice-binding behavior is already implemented.

## 12. Recommended video references and model-aware prompts

For a character present in the current clip, show its bound voice asset and available character image at the top of compatible video reference pickers under **Recommended**, with the character name and reason. Recommend them together for appearance/voice consistency. Do not select or attach them merely because a binding exists. Semi automated video may select them under its explicitly confirmed reference policy; manual pickers still leave them unselected. The same voice file may remain bound to multiple characters.

The video adapter must reconcile shared voice bindings with the local compiler's duplicate-asset/single-speaker assumptions: attach a shared media file once and represent the intended character mappings explicitly, or expose a supported alternative. Do not promise distinct vocal identities when characters share the same voice source. Unsupported multi-character mapping must be visible rather than silently duplicating the reference slot.

Text-only and first/last workflows must not claim to use these references if they have no compatible input. Show recommendations as unavailable for that workflow with the reason, or let the user explicitly choose reference-to-video. Full mode uses the story-only route described in `automation.md` and does not require character image/voice selection.

Build image prompts for the selected image model/workflow and actual references. Changing model, selected references or generation settings refreshes a reviewable prompt proposal, preserving accepted user edits and lineage. Enforce that model's documented/configured prompt budget (characters, tokens or encoder limit as appropriate); verify the exact model limit during integration rather than inventing one universal image limit. Show usage, and offer meaning-preserving refinement when over budget; never silently truncate. Prompt changes that alter screenplay direction offer **Update screenplay** or **This take only**, using the shared revision/override rules.

## 13. Manual/Semi scheduling and isolated creation

The post-screenplay Automation & Parameters page defines whether character images, world images, clip-frame images and character-to-audio selection execute manually or automatically. Every selected automatic stage confirms a concrete preset/policy before execution. Manual stages expose the exact editable prompt with annotation/microediting before Generate.

Checking character-to-audio selection authorizes automatic voice binding according to the confirmed library/matching policy. This is distinct from automatically selecting the bound file as a video reference. Unchecked binding is manual; Full skips these image/binding steps. Semi automated video lets the Director choose FFLF or R2V using available prepared assets. Frames support FFLF; character/voice/world references support compatible R2V, where the Director may also choose the preceding clip for continuity. Optional unused images/frames can be skipped.

Each image page is also reachable directly for isolated creation. Accept a user-authored character/world/frame description, selected compatible model/settings and optional uploaded/library references without requiring a story or screenplay. Save ordinary asset/prompt provenance; do not invent source scene/character IDs. Generic first/last images can be supplied to an isolated FLF task without a story association. Where no character records exist, voice selection can prepare/reuse voice assets through Media Prep rather than requiring a story character map.


## 14. Shared UI and implementation reuse

Apply `ux_shared.md` to the character/world/frame/voice pages: persistent saved context, thumbnails/playback, prompt/ref details, direct recovery from missing inputs and distinct empty/offline/failed states. Keep manual fields editable/saveable while the generation engine is unavailable. Clearly distinguish optional skipped preparation from missing inputs required by a selected video workflow.

Use `integration.md` for extraction of working Story Builder services and any verified supporting helpers. Retain a single asset library and canonical voice-binding map; do not create an upstream-specific second library or required preparation funnel.
