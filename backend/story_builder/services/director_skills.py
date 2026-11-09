"""Read versioned project craft guidance; no inference, discovery or submission."""
from __future__ import annotations

from .agent_skills import read_content
import hashlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "skills"


def director_skill_context(*, video: bool = False, image_workflow: str | None = None) -> str:
    paths = ["vibe-director/SKILL.md"]
    if video or image_workflow:
        paths += ["prompt-craft/SKILL.md", "prompt-craft/references/visual-glossary.md"]
    if image_workflow == "z_image_turbo":
        paths.append("z-image-prompting/SKILL.md")
    elif image_workflow in {"qwen_image_edit_2511", "qwen_image_multi_angle_2511"}:
        paths.append("qwen-image-edit-prompting/SKILL.md")
    if image_workflow == "flux_kontext_dev":
        paths.append("flux-kontext-prompting/SKILL.md")
    if video:
        paths += ["video-prompting/SKILL.md", "video-prompting/references/minimax-h3.md",
                  "video-prompting/references/examples.md"]
    sections = []
    for relative in paths:
        try:
            content = read_content(_ROOT, relative)
        except ValueError as exc:
            raise ValueError(f"Project directing skill exceeds its context budget: {relative}") from exc
        digest = hashlib.sha256(content.encode()).hexdigest()[:16]
        sections.append(f"PROJECT SKILL {relative} sha256:{digest}\n{content}")
    return "\n\n".join(sections)


def bind_h3_reference_prompt(prompt: str, instructions: list[str]) -> str:
    """Attach actual media bindings without breaking newly prepared H3 sections.

    Legacy owner-edited prose remains verbatim after its reference preamble.
    """
    import re

    bindings = "\n".join(instructions)
    retention = re.search(r"(?m)^retention_analysis\s*:", prompt)
    if retention:
        return prompt[:retention.end()] + "\n" + bindings + "\n" + prompt[retention.end():]
    base = re.fullmatch(
        r"\s*integrated_multimodal_description\s*:(.*?)\n\s*overall_soundscape\s*:(.*?)\n\s*non_diegetic_music\s*:(.*)",
        prompt, re.DOTALL,
    )
    if base:
        visual, sound, music = (part.strip() for part in base.groups())
        return ("subject_definitions: Use only the screenplay identities described below; attached image roles are listed in retention_analysis.\n"
            "summary: [reference generation] Generate the next screenplay action with the attached appearance/world references.\n"
            f"retention_analysis: {bindings}\n"
            f"detailed_description: {visual}\n"
            f"overall_soundscape: {sound}\nnon_diegetic_music: {music}")
    return bindings + "\n\n" + prompt
