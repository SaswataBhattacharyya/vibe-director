---
name: qwen-image-edit-prompting
description: Write Qwen Image Edit 2511 instructions that specify requested changes and preserve reference identity.
version: 1
---

For qwen_image_edit_2511, describe the edit to supplied images rather than rewriting an unrelated text-to-image scene. Identify the selected image and what to change, then state the important features to preserve: identity, pose, clothing, geometry, framing or lighting as appropriate. Ask what should change if the edit is ambiguous. Never invent an attachment, imply an unseen image was inspected, or borrow an unselected reference.

For multiple inputs, map each actual input to its intended role in validated request order. Describe the desired final spatial relationship; avoid vague "combine these" instructions. For text changes, specify exact replacement text and preserve relevant typography/placement. Keep instructions focused; unrelated atmosphere/detail can unintentionally request a broader redesign.

Scene backgrounds can have scene-specific states (damage, slime, weather) while preserving a reusable base location's architecture/layout. Change only the requested state. Keep base and derived asset identities distinct through existing tools.

For qwen_image_multi_angle_2511, native camera nodes supply direction: shared prose preserves identity/environment and must not specify front/side/back/profile, camera angle, zoom or framing. Do not apply ordinary editing composition advice to this shared prompt. Preserve existing reference count and graph constraints. Vibe's Lightning graph settings differ from the vendor Diffusers example; never change them as a prompting side effect.

Use prompt-craft for clarification and reviewed, project-scoped feedback. Official source checked 2026-11-07: [Qwen Image Edit 2511 model card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511). Original guidance, not a copied vendor skill.
