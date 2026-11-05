---
name: environment-designer
description: Create and maintain cinematic locations, background-image prompts and environment continuity, optimized for Z-Image where selected. Use for location look development, background plates, establishing shots, first-frame generation, and consistent settings across storyboard panels and video clips.
metadata:
  version: "1.0.0"
  product: "Vibe Director"
---

# Environment Designer (Z-Image)

## Mission
Design *places*, not disposable backgrounds. Keep a repeatable spatial map of landmarks, paths, lighting and relative object positions so camera moves and character interactions make physical sense across clips.

## Runtime integration
Read `../../shared/CONTRACT.md`, project location library, style bible, prior shots and model profile. Use any registered image-generation, background-edit, asset or frame-extraction capabilities only when available; start from textual direction if no assets exist. Users may create a location before they write a screenplay.

## Procedure
1. **Define location identity:** `location_id`, name, biome/architecture, palette, time of day, weather, lighting, texture/material language, mood and important landmarks.
2. **Build a continuity map:** relative positions for path, tree, branch, rocks, hidden trap, approach routes, entrances/exits, and clear negative space for characters. Use coordinates only if the user/workflow benefits; otherwise relative directions with a fixed world orientation.
3. **Choose shot intent:** establishing background, clean plate, key action location, first-frame composition, reverse angle, or alternate camera angle. Do not confuse a clean background plate with a character-in-scene first frame.
4. **Write a Z-Image prompt:** location and landmarks → physical layout → camera height/lens/framing → composition/clear action zones → lighting/time/style → continuity constraints. Avoid inserting extra animals or text if generating a reusable empty plate.
5. **Produce variants deliberately:** wide master, low mouse-eye view, lion-height view, alternate angle, day/night variation. Keep the same tree/branch/paths unless the user asks for a new location.
6. **Register** approved background and first-frame assets with IDs, camera viewpoint, landmark map and style version; link shots to their actual location version.
7. **Choose continuity mechanism** when starting another generation: reuse last frame when action continues in place; generate a dedicated new first frame for time jumps, new location, or intentional reblocking; use a location plate for generic context only.

## Output format
`location_id`, `location_bible`, `spatial_landmarks`, `look_palette`, `camera_angle`, `intended_use` (`plate`, `establishing`, `first_frame`, `storyboard_panel`), `z_image_prompt`, `registered_asset_ids` if produced, and `continuity_notes`.

## Example — Lion's forest clearing
**Z-Image prompt:** "Peaceful stylized cinematic woodland clearing in warm late-morning sunlight. A large old tree at the left with a low sloped branch reaching toward a soft grass-covered resting place to the right; narrow forest path crossing the clearing left to right, distinctive pale gray boulder by the tree roots, tall layered grasses at foreground mouse-eye height, dappled sunbeams and warm green canopy. Low three-quarter wide camera composition with open space beneath branch for a large resting animal. Beautiful coherent 3D animated-film environment, consistent world geography, no characters, no traps, no text, no logos."

For a trap scene, declare explicitly whether it is the same clearing or another location. Do not invent a sudden new tree while claiming an exact continuation frame.

## Quality gate
- Spatially possible action: jump takeoff and landing zones exist; camera paths do not jump through solid trees.
- Lighting is consistent when direct continuity is requested.
- Landmark identity persists across reverse angles.
- A first-frame image matches the intended opening composition, not just the general style.
- Return the prompt even when the generator is unavailable; never invent a successful image.
