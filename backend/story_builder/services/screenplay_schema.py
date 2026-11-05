"""Codex structured-output contract; semantic/evidence validation stays in StoryAuthoring."""

def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}

_STRING = {"type": "string"}
_IDS = {"type": "array", "items": _STRING}
_SHOT = _object({**{key: _STRING for key in ("action", "dialogue", "camera", "lighting", "mood", "sfx", "music")},
                 "presentation": {"type":"string", "enum":["image","video"]},
                 "planned_duration_seconds": {"type": ["number", "null"]},
                 "evidence_record_ids": _IDS, "character_record_ids": _IDS})
_SCENE = _object({"slugline": _STRING, "summary": _STRING,
                  "continues_previous_scene": {"type": "boolean"},
                  "shots": {"type": "array", "items": _SHOT}})
SCREENPLAY_RESPONSE_SCHEMA = _object({"scenes": {"type": "array", "items": _SCENE}})
