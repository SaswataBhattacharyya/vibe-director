# Vibe Director tool glossary

The Director should choose among all application capabilities, use the appropriate supported service and return the result to the ongoing conversation. A limitation of its renderer must never be described as a limitation of the whole application.

Reviewed against source on **2026-11-05**. This folder is an on-demand knowledge pack and proposed routing vocabulary; it does **not** install model-callable tools or change runtime prompts. Existing endpoints are application capabilities, not proof that every Director can call them today. No generation/training was run to prepare it.

## Read only what the task needs

1. Use the decision table below to choose a capability.
2. Read its domain guide for inputs, outputs and usage.
3. Use [API_HELPERS.md](API_HELPERS.md) and [HTTP_ROUTES.md](HTTP_ROUTES.md) to locate the exact contract; read source/types before executing.
4. Follow [DIRECTOR_USAGE.md](DIRECTOR_USAGE.md) for orchestration and [INTEGRATION.md](INTEGRATION.md) for the missing runtime wiring.

[Machine-readable catalogue](catalog.json) contains the same glossary entries. [COMPONENTS.md](COMPONENTS.md) indexes every current backend service module, including internal helpers that should not be exposed as tools.

## Choose the right tool

| ID | Use for | Guide |
|---|---|---|
| `project.manage` | New / Load / Save project | [projects](01_PROJECTS.md) |
| `output.destination` | Output folder selection and relink | [projects](01_PROJECTS.md) |
| `story.styles` | Production type and directing style | [story](02_STORY_AND_PROMPTS.md) |
| `story.author` | Story write, import, edit and revisions | [story](02_STORY_AND_PROMPTS.md) |
| `story.graph` | Story facts and entity graph | [story](02_STORY_AND_PROMPTS.md) |
| `story.screenplay` | Screenplay preparation and whole-screenplay chat | [story](02_STORY_AND_PROMPTS.md) |
| `story.board` | Frame per shot and storyboard | [story](02_STORY_AND_PROMPTS.md) |
| `production.setup` | Automation and assisted production setup | [story](02_STORY_AND_PROMPTS.md) |
| `prompts.prepare` | Shot, clip, character and world prompting | [story](02_STORY_AND_PROMPTS.md) |
| `images.generate` | Text-to-image and image editing | [images](03_IMAGES.md) |
| `images.production` | Character, world, first/last-frame assets and selections | [images](03_IMAGES.md) |
| `images.inspect` | Image Detailer | [images](03_IMAGES.md) |
| `images.training` | Image training and adapter catalogue | [images](03_IMAGES.md) |
| `video.t2v` | Text to video | [video](04_VIDEO.md) |
| `video.r2v` | Reference to video | [video](04_VIDEO.md) |
| `video.fflf` | First + last frame video | [video](04_VIDEO.md) |
| `video.review` | Take review, accept, retake and continuity | [video](04_VIDEO.md) |
| `video.runs` | Assisted and fully automated production runs / batches | [video](04_VIDEO.md) |
| `video.assembly` | Accepted clip assembly and final export | [video](04_VIDEO.md) |
| `media.browse` | Library, source catalogue and imports | [media](05_MEDIA_AND_SEARCH.md) |
| `media.semantic` | Semantic search, indexing and annotations | [media](05_MEDIA_AND_SEARCH.md) |
| `media.download` | YouTube search/URL resolution and download | [media](05_MEDIA_AND_SEARCH.md) |
| `media.analyse_video` | Video Summariser / audio-video analysis | [media](05_MEDIA_AND_SEARCH.md) |
| `media.style_frames` | Style reference frames and associations | [media](05_MEDIA_AND_SEARCH.md) |
| `media.delete` | Archive and permanent media deletion | [media](05_MEDIA_AND_SEARCH.md) |
| `audio.extract` | Extract MP3 from video/audio | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.utilities` | Noise cleanup and stem separation | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.isolate` | SAM audio event isolation | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.speech` | Timed TTS / dialogue generation | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.voices` | Record, enrol and bind character voices | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.effects` | Voice effects, repair, conversion and simple CPU effects | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.voice_studio` | Specialist voice studio and RVC training | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.scene` | Audio scene surgery: split and stitch | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.reconstruct` | Dialogue reconstruction and take selection | [audio](06_AUDIO_AND_MUSIC.md) |
| `audio.finetune` | F5 dataset preparation | [audio](06_AUDIO_AND_MUSIC.md) |
| `music.generate` | Music and Foley generation | [audio](06_AUDIO_AND_MUSIC.md) |
| `music.ace` | ACE-Step studio, generation and fine-tuning | [audio](06_AUDIO_AND_MUSIC.md) |
| `music.jukebox` | Music Jukebox / composition / DJ / export | [audio](06_AUDIO_AND_MUSIC.md) |
| `editor.edit` | Vibe Editor: chat, selected ranges and rendering | [editor](07_EDITOR.md) |
| `editor.styles` | Editor style memory and lessons | [editor](07_EDITOR.md) |
| `editor.export` | Editor save final MP4 | [editor](07_EDITOR.md) |
| `models.3d` | TRELLIS.2 and Pixal3D image-to-3D | [models](08_3D.md) |
| `system.status` | Readiness, provider, jobs and GPU safety | [system](09_SYSTEM_AND_KNOWLEDGE.md) |
| `system.knowledge` | Prompt workflow knowledge and installed Director skills | [system](09_SYSTEM_AND_KNOWLEDGE.md) |

## Inventory scope

44 capability groups, 199 exported API helper declarations and 161 HTTP route literals/patterns. Route count includes prefixes/regex branches, not a count of verified endpoints. Backend service index includes internal validators, job workers, renderers, persistence and safety components. This is a source inventory and usage glossary, not a whole-app correctness audit or live availability certificate.

The current [integration architecture](../fixes/INTEGRATION_ARCHITECTURE.md) and [test-first task queue](../fixes/ACTIVE_FIXES.md) describe the requested persistent Director and specialist workspaces. This folder supplies tool-selection knowledge; it does not grant runtime execution. Existing runtime skills remain unchanged.
