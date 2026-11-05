---
name: character-designer
description: Design and maintain consistent film characters, especially Z-Image-friendly character prompts, reference portraits and character sheets. Use when creating a character from text, refining a supplied character image, generating views/expressions, or preparing reusable image references for storyboards and video models.
metadata:
  version: "1.0.0"
  product: "Vibe Director"
---

# Character Designer (Z-Image)

## Mission
Give each character a stable, reusable visual identity and image-generation-ready prompt. A good image reference must be distinguishable, readable, compositionally clear, and consistent across all future video clips.

## Runtime integration
Follow `../../shared/CONTRACT.md`. Look up character records, reference images, active model capabilities, image-generation settings and asset library. Do not assume a Z-Image endpoint or negative-prompt field exists: inspect model profile and invoke the **registered** image-generation component only when supported. Accept user-uploaded images as authoritative. Users can start here without a screenplay.

## Procedure
1. **Create a character bible entry:** stable `character_id`, name/role, species, age impression if relevant, size relative to others, silhouette, anatomy, body proportions, face, coloring/markings, accessories, wardrobe, personality expressed visually, style family and prohibited changes.
2. **Lock invariants vs. variants.** Fixed: unique markings, proportions, ear shape, mane shape, palette, costume signature. Variable: pose, expression, framing, lighting. Never silently alter locked traits.
3. **Compose Z-Image prompt** in this order: subject identity → distinctive anatomy/markings → art style → pose and emotion → camera/framing → lighting and background → quality/composition constraints. Use positive, specific language. Put exclusions in a separate negative field **only if supported**; otherwise phrase them as positive framing constraints.
4. **Prepare reference capture.** Prefer full-body three-quarter neutral view on a simple contrasting background for first reference; request profile, front, back, expression sheets as separate outputs when consistency benefits. Avoid multiple characters in a single reference unless intentionally creating a lineup.
5. **Generate or draft.** If a compatible image tool is registered and user requested actual generation, invoke it with supplied references/settings. Otherwise output the ready-to-paste prompt and required asset list; don't claim an image was created.
6. **Check and register:** number of legs, eyes, paws, tails, relative scale, markings, accessory placement, and visual style. Store approved image `asset_id`, provenance, model settings, prompt, version, crop and role. Distinguish drafts from approved references.
7. **Reuse approved assets** instead of reconstructing from memory. When changing a character, offer a new version with an explicit continuity-impact note for already-generated clips.

## Output format
- `character_id`, `identity_lock`, `palette` (hex if useful), `scale_notes`, `style_id`, `approved_reference_asset_ids`, `consistency_rules`
- `z_image_prompt`: a clean prose prompt for **one image request**
- `negative_prompt` only if supported and requested/beneficial
- `recommended_outputs`: `hero_full_body`, `front`, `side`, `three_quarter`, `expression_sheet` as applicable
- `reference_instructions`: a short instruction suitable for attaching character image to video generation.

## Example — Lion (illustrative, customize to user's actual image)
**Z-Image prompt:** "Single friendly adult male lion, full body, three-quarter view, warm honey-gold fur, rich chestnut-brown rounded mane framing broad face, amber eyes, strong paws, natural expressive feline anatomy, gentle alert expression. Stylized cinematic 3D family-animation look with soft detailed fur, balanced proportions, clean readable silhouette. Standing on simple muted warm-gray seamless background, soft studio key light and subtle rim light, whole tail and all four paws visible, centered character reference image, no typography, no extra animals."

**Video reference instruction:** "Preserve this lion's precise face, mane silhouette, fur tones, relative proportions and scale. Animate pose and expression without redesign."

## Quality gate
- One unambiguous main character per asset (unless a lineup was specifically requested).
- Distinct body and silhouette across characters; mouse much smaller than lion in shared scenes.
- Full figure and tail not accidentally cut off where turnaround is needed.
- Prompt does not request contradictory views or mutually exclusive expressions in one image.
- Image-generation limitations are reported honestly; approved IDs persist across the project.
