# HTTP route source index

Literal/regex route strings extracted from the main dispatcher and named API handlers, 2026-11-05. These include prefixes and patterns, not only complete callable endpoints. **Do not send regexes as URLs.** Read the linked branch for HTTP methods, body schema, ownership, readiness and response. Dynamic paths assembled without an `/api/` literal may require further source tracing.

## isolated_server.py

| Route literal or pattern | Source |
|---|---|
| `/api/projects/` | [isolated_server.py:485](../backend/story_builder/isolated_server.py#L485) |
| `/api/jukebox/` | [isolated_server.py:488](../backend/story_builder/isolated_server.py#L488) |
| `/api/studio-tools/` | [isolated_server.py:491](../backend/story_builder/isolated_server.py#L491) |
| `/api/trellis/` | [isolated_server.py:491](../backend/story_builder/isolated_server.py#L491) |
| `/api/ace/` | [isolated_server.py:494](../backend/story_builder/isolated_server.py#L494) |
| `/api/editor/` | [isolated_server.py:497](../backend/story_builder/isolated_server.py#L497) |
| `/api/director/status` | [isolated_server.py:500](../backend/story_builder/isolated_server.py#L500) |
| `/api/director/settings` | [isolated_server.py:503](../backend/story_builder/isolated_server.py#L503) |
| `/api/video-summariser/capabilities` | [isolated_server.py:508](../backend/story_builder/isolated_server.py#L508) |
| `/api/audio/scene-surgery/capabilities` | [isolated_server.py:532](../backend/story_builder/isolated_server.py#L532) |
| `/api/image-detailer/` | [isolated_server.py:535](../backend/story_builder/isolated_server.py#L535) |
| `/api/audio/capabilities` | [isolated_server.py:593](../backend/story_builder/isolated_server.py#L593) |
| `/api/audio/finetune/f5/preflight` | [isolated_server.py:606](../backend/story_builder/isolated_server.py#L606) |
| `/api/audio/` | [isolated_server.py:608](../backend/story_builder/isolated_server.py#L608) |
| `/api/audio/music/capabilities` | [isolated_server.py:670](../backend/story_builder/isolated_server.py#L670) |
| `/api/audio/utilities/capabilities` | [isolated_server.py:695](../backend/story_builder/isolated_server.py#L695) |
| `/api/audio/effects/capabilities` | [isolated_server.py:698](../backend/story_builder/isolated_server.py#L698) |
| `/api/audio/` | [isolated_server.py:708](../backend/story_builder/isolated_server.py#L708) |
| `/api/audio/` | [isolated_server.py:760](../backend/story_builder/isolated_server.py#L760) |
| `/api/audio/` | [isolated_server.py:830](../backend/story_builder/isolated_server.py#L830) |
| `/api/audio/` | [isolated_server.py:886](../backend/story_builder/isolated_server.py#L886) |
| `/api/audio/` | [isolated_server.py:929](../backend/story_builder/isolated_server.py#L929) |
| `/api/audio/voices` | [isolated_server.py:1022](../backend/story_builder/isolated_server.py#L1022) |
| `/api/audio/voices/content?id=` | [isolated_server.py:1025](../backend/story_builder/isolated_server.py#L1025) |
| `/api/audio/` | [isolated_server.py:1031](../backend/story_builder/isolated_server.py#L1031) |
| `/api/audio/voices/content` | [isolated_server.py:1054](../backend/story_builder/isolated_server.py#L1054) |
| `/api/audio/models` | [isolated_server.py:1065](../backend/story_builder/isolated_server.py#L1065) |
| `/api/audio/` | [isolated_server.py:1069](../backend/story_builder/isolated_server.py#L1069) |
| `/api/audio/voices/refresh` | [isolated_server.py:1134](../backend/story_builder/isolated_server.py#L1134) |
| `/api/audio/` | [isolated_server.py:1141](../backend/story_builder/isolated_server.py#L1141) |
| `/api/audio/` | [isolated_server.py:1184](../backend/story_builder/isolated_server.py#L1184) |
| `/api/video-summariser/` | [isolated_server.py:1229](../backend/story_builder/isolated_server.py#L1229) |
| `/api/story/` | [isolated_server.py:1482](../backend/story_builder/isolated_server.py#L1482) |
| `/api/story/imports` | [isolated_server.py:1484](../backend/story_builder/isolated_server.py#L1484) |
| `/api/story/imports` | [isolated_server.py:1488](../backend/story_builder/isolated_server.py#L1488) |
| `/api/media/` | [isolated_server.py:1489](../backend/story_builder/isolated_server.py#L1489) |
| `/api/styles/sources` | [isolated_server.py:1490](../backend/story_builder/isolated_server.py#L1490) |
| `/api/media/` | [isolated_server.py:1493](../backend/story_builder/isolated_server.py#L1493) |
| `/api/styles/catalog` | [isolated_server.py:1750](../backend/story_builder/isolated_server.py#L1750) |
| `/api/styles/sources` | [isolated_server.py:1752](../backend/story_builder/isolated_server.py#L1752) |
| `/api/styles/sources` | [isolated_server.py:1761](../backend/story_builder/isolated_server.py#L1761) |
| `/api/styles/sources/analyze` | [isolated_server.py:1771](../backend/story_builder/isolated_server.py#L1771) |
| `/api/styles/media/analyze` | [isolated_server.py:1782](../backend/story_builder/isolated_server.py#L1782) |
| `/api/styles/sources/` | [isolated_server.py:1840](../backend/story_builder/isolated_server.py#L1840) |
| `/api/styles/sources/` | [isolated_server.py:1841](../backend/story_builder/isolated_server.py#L1841) |
| `/api/styles/types` | [isolated_server.py:1849](../backend/story_builder/isolated_server.py#L1849) |
| `/api/styles/directing-styles` | [isolated_server.py:1856](../backend/story_builder/isolated_server.py#L1856) |
| `/api/styles/selections` | [isolated_server.py:1920](../backend/story_builder/isolated_server.py#L1920) |
| `/api/styles/selections` | [isolated_server.py:1939](../backend/story_builder/isolated_server.py#L1939) |
| `/api/styles/selections/` | [isolated_server.py:1951](../backend/story_builder/isolated_server.py#L1951) |
| `/api/styles/selections/` | [isolated_server.py:1952](../backend/story_builder/isolated_server.py#L1952) |
| `/api/story/workspaces` | [isolated_server.py:1960](../backend/story_builder/isolated_server.py#L1960) |
| `/api/story/workspaces` | [isolated_server.py:1965](../backend/story_builder/isolated_server.py#L1965) |
| `/api/story/creations/by-idempotency/` | [isolated_server.py:1978](../backend/story_builder/isolated_server.py#L1978) |
| `/api/story/creations/by-idempotency/` | [isolated_server.py:1979](../backend/story_builder/isolated_server.py#L1979) |
| `/api/story/imports` | [isolated_server.py:1981](../backend/story_builder/isolated_server.py#L1981) |
| `/api/story/imports/` | [isolated_server.py:1995](../backend/story_builder/isolated_server.py#L1995) |
| `/api/story/imports/` | [isolated_server.py:1996](../backend/story_builder/isolated_server.py#L1996) |
| `/api/story/workspaces/` | [isolated_server.py:2023](../backend/story_builder/isolated_server.py#L2023) |
| `/api/story/workspaces/` | [isolated_server.py:2024](../backend/story_builder/isolated_server.py#L2024) |
| `/api/story/edit-requests/by-key/` | [isolated_server.py:2650](../backend/story_builder/isolated_server.py#L2650) |
| `/api/story/edit-requests/by-key/` | [isolated_server.py:2651](../backend/story_builder/isolated_server.py#L2651) |
| `/api/story/field-edit-requests/by-key/` | [isolated_server.py:2653](../backend/story_builder/isolated_server.py#L2653) |
| `/api/story/field-edit-requests/by-key/` | [isolated_server.py:2654](../backend/story_builder/isolated_server.py#L2654) |
| `/api/workflow-guidance` | [isolated_server.py:2656](../backend/story_builder/isolated_server.py#L2656) |
| `/api/video/capabilities` | [isolated_server.py:2662](../backend/story_builder/isolated_server.py#L2662) |
| `/api/images/workflows` | [isolated_server.py:2667](../backend/story_builder/isolated_server.py#L2667) |
| `/api/images/assets/export` | [isolated_server.py:2693](../backend/story_builder/isolated_server.py#L2693) |
| `/api/images/worker` | [isolated_server.py:2757](../backend/story_builder/isolated_server.py#L2757) |
| `/api/images/automated-stage` | [isolated_server.py:2759](../backend/story_builder/isolated_server.py#L2759) |
| `/api/images/selections` | [isolated_server.py:2982](../backend/story_builder/isolated_server.py#L2982) |
| `/api/images/validations` | [isolated_server.py:2993](../backend/story_builder/isolated_server.py#L2993) |
| `/api/images/temporary-references/` | [isolated_server.py:3028](../backend/story_builder/isolated_server.py#L3028) |
| `/api/images/temporary-references/` | [isolated_server.py:3029](../backend/story_builder/isolated_server.py#L3029) |
| `/api/images/temporary-assets/` | [isolated_server.py:3046](../backend/story_builder/isolated_server.py#L3046) |
| `/api/images/temporary-assets/` | [isolated_server.py:3047](../backend/story_builder/isolated_server.py#L3047) |
| `/api/images/prompts/prepare` | [isolated_server.py:3055](../backend/story_builder/isolated_server.py#L3055) |
| `/api/images/jobs` | [isolated_server.py:3138](../backend/story_builder/isolated_server.py#L3138) |
| `/api/images/batches/` | [isolated_server.py:3308](../backend/story_builder/isolated_server.py#L3308) |
| `/api/images/batches/` | [isolated_server.py:3309](../backend/story_builder/isolated_server.py#L3309) |
| `/api/images/jobs/` | [isolated_server.py:3314](../backend/story_builder/isolated_server.py#L3314) |
| `/api/images/jobs/` | [isolated_server.py:3315](../backend/story_builder/isolated_server.py#L3315) |
| `/api/performance` | [isolated_server.py:3358](../backend/story_builder/isolated_server.py#L3358) |
| `/api/performance/log` | [isolated_server.py:3365](../backend/story_builder/isolated_server.py#L3365) |
| `/api/debug` | [isolated_server.py:3369](../backend/story_builder/isolated_server.py#L3369) |
| `/api/debug/events` | [isolated_server.py:3376](../backend/story_builder/isolated_server.py#L3376) |
| `/api/debug/log` | [isolated_server.py:3378](../backend/story_builder/isolated_server.py#L3378) |
| `/api/runtime/workload-policy` | [isolated_server.py:3382](../backend/story_builder/isolated_server.py#L3382) |
| `/api/runtime/safety-hold` | [isolated_server.py:3393](../backend/story_builder/isolated_server.py#L3393) |
| `/api/status` | [isolated_server.py:3408](../backend/story_builder/isolated_server.py#L3408) |
| `/api/comfyui/queue` | [isolated_server.py:3437](../backend/story_builder/isolated_server.py#L3437) |
| `/api/jobs/queue` | [isolated_server.py:3439](../backend/story_builder/isolated_server.py#L3439) |
| `/api/video/runtime` | [isolated_server.py:3441](../backend/story_builder/isolated_server.py#L3441) |
| `/api/video/worker` | [isolated_server.py:3443](../backend/story_builder/isolated_server.py#L3443) |
| `/api/video/batches/validate` | [isolated_server.py:3445](../backend/story_builder/isolated_server.py#L3445) |
| `/api/video/batches` | [isolated_server.py:3448](../backend/story_builder/isolated_server.py#L3448) |
| `/api/video/batches/([a-f0-9-]{36})(/control)?` | [isolated_server.py:3459](../backend/story_builder/isolated_server.py#L3459) |
| `/api/video/validations` | [isolated_server.py:3465](../backend/story_builder/isolated_server.py#L3465) |
| `/api/video/jobs` | [isolated_server.py:3469](../backend/story_builder/isolated_server.py#L3469) |
| `/api/video/jobs` | [isolated_server.py:3532](../backend/story_builder/isolated_server.py#L3532) |
| `/api/video/attempts/release` | [isolated_server.py:3544](../backend/story_builder/isolated_server.py#L3544) |
| `/api/video/jobs/by-idempotency/` | [isolated_server.py:3548](../backend/story_builder/isolated_server.py#L3548) |
| `/api/video/jobs/by-idempotency/` | [isolated_server.py:3549](../backend/story_builder/isolated_server.py#L3549) |
| `/api/video/jobs/` | [isolated_server.py:3554](../backend/story_builder/isolated_server.py#L3554) |
| `/api/video/jobs/` | [isolated_server.py:3555](../backend/story_builder/isolated_server.py#L3555) |
| `/api/video/retakes/` | [isolated_server.py:3572](../backend/story_builder/isolated_server.py#L3572) |
| `/api/video/retakes/` | [isolated_server.py:3573](../backend/story_builder/isolated_server.py#L3573) |
| `/api/video/assets/` | [isolated_server.py:3579](../backend/story_builder/isolated_server.py#L3579) |
| `/api/video/assets/` | [isolated_server.py:3580](../backend/story_builder/isolated_server.py#L3580) |
| `/api/video/jobs` | [isolated_server.py:3603](../backend/story_builder/isolated_server.py#L3603) |
| `/api/video/jobs` | [isolated_server.py:3610](../backend/story_builder/isolated_server.py#L3610) |
| `/api/images/` | [isolated_server.py:3613](../backend/story_builder/isolated_server.py#L3613) |
| `/api/story/` | [isolated_server.py:3614](../backend/story_builder/isolated_server.py#L3614) |
| `/api/styles/` | [isolated_server.py:3615](../backend/story_builder/isolated_server.py#L3615) |
| `/api/video/jobs` | [isolated_server.py:3628](../backend/story_builder/isolated_server.py#L3628) |
| `/api/media/` | [isolated_server.py:3633](../backend/story_builder/isolated_server.py#L3633) |
| `/api/story/` | [isolated_server.py:3638](../backend/story_builder/isolated_server.py#L3638) |
| `/api/styles/` | [isolated_server.py:3640](../backend/story_builder/isolated_server.py#L3640) |
| `/api/video/jobs` | [isolated_server.py:3642](../backend/story_builder/isolated_server.py#L3642) |
| `/api/styles/media/analyze` | [isolated_server.py:3645](../backend/story_builder/isolated_server.py#L3645) |
| `/api/styles/sources/analyze` | [isolated_server.py:3645](../backend/story_builder/isolated_server.py#L3645) |
| `/api/story/workspaces/` | [isolated_server.py:3649](../backend/story_builder/isolated_server.py#L3649) |

## vibe_editor_api.py

| Route literal or pattern | Source |
|---|---|
| `/api/editor/state` | [vibe_editor_api.py:15](../backend/story_builder/services/vibe_editor_api.py#L15) |
| `/api/editor/projects` | [vibe_editor_api.py:18](../backend/story_builder/services/vibe_editor_api.py#L18) |
| `/api/editor/styles` | [vibe_editor_api.py:20](../backend/story_builder/services/vibe_editor_api.py#L20) |
| `/api/editor/styles/([\w-]+)` | [vibe_editor_api.py:22](../backend/story_builder/services/vibe_editor_api.py#L22) |
| `/api/editor/projects/([\w-]+)(?:/(command&#124;plan&#124;export))?` | [vibe_editor_api.py:26](../backend/story_builder/services/vibe_editor_api.py#L26) |

## ace_studio_api.py

| Route literal or pattern | Source |
|---|---|
| `/api/ace/state` | [ace_studio_api.py:8](../backend/story_builder/services/ace_studio_api.py#L8) |
| `/api/ace/projects` | [ace_studio_api.py:10](../backend/story_builder/services/ace_studio_api.py#L10) |
| `/api/ace/projects/([\w-]+)/(command&#124;dataset&#124;log)` | [ace_studio_api.py:12](../backend/story_builder/services/ace_studio_api.py#L12) |

## studio_tools_api.py

| Route literal or pattern | Source |
|---|---|
| `/api/trellis/upload` | [studio_tools_api.py:9](../backend/story_builder/services/studio_tools_api.py#L9) |
| `/api/studio-tools/output-folder` | [studio_tools_api.py:15](../backend/story_builder/services/studio_tools_api.py#L15) |
| `/api/studio-tools/output-destination` | [studio_tools_api.py:18](../backend/story_builder/services/studio_tools_api.py#L18) |
| `/api/studio-tools/output-relink` | [studio_tools_api.py:21](../backend/story_builder/services/studio_tools_api.py#L21) |
| `/api/studio-tools/checkpoints` | [studio_tools_api.py:24](../backend/story_builder/services/studio_tools_api.py#L24) |
| `/api/studio-tools/checkpoints/delete` | [studio_tools_api.py:25](../backend/story_builder/services/studio_tools_api.py#L25) |
| `/api/studio-tools/voice/capabilities` | [studio_tools_api.py:26](../backend/story_builder/services/studio_tools_api.py#L26) |
| `/api/studio-tools/voice/jobs` | [studio_tools_api.py:27](../backend/story_builder/services/studio_tools_api.py#L27) |
| `/api/studio-tools/voice/jobs` | [studio_tools_api.py:28](../backend/story_builder/services/studio_tools_api.py#L28) |
| `/api/studio-tools/voice/jobs/(voice-studio-[a-f0-9]{12})(?:/(cancel&#124;resume))?` | [studio_tools_api.py:29](../backend/story_builder/services/studio_tools_api.py#L29) |
| `/api/studio-tools/training` | [studio_tools_api.py:39](../backend/story_builder/services/studio_tools_api.py#L39) |
| `/api/studio-tools/training/launch` | [studio_tools_api.py:40](../backend/story_builder/services/studio_tools_api.py#L40) |
| `/api/studio-tools/loras` | [studio_tools_api.py:41](../backend/story_builder/services/studio_tools_api.py#L41) |
| `/api/studio-tools/loras/checkpoints` | [studio_tools_api.py:42](../backend/story_builder/services/studio_tools_api.py#L42) |
| `/api/studio-tools/loras/publish` | [studio_tools_api.py:43](../backend/story_builder/services/studio_tools_api.py#L43) |
| `/api/trellis/service` | [studio_tools_api.py:44](../backend/story_builder/services/studio_tools_api.py#L44) |
| `/api/trellis/state` | [studio_tools_api.py:47](../backend/story_builder/services/studio_tools_api.py#L47) |
| `/api/trellis/output-folder` | [studio_tools_api.py:56](../backend/story_builder/services/studio_tools_api.py#L56) |
| `/api/trellis/jobs` | [studio_tools_api.py:58](../backend/story_builder/services/studio_tools_api.py#L58) |
| `/api/trellis/input/([a-f0-9]{32})` | [studio_tools_api.py:59](../backend/story_builder/services/studio_tools_api.py#L59) |
| `/api/trellis/jobs/(trellis-[a-f0-9]{12})(?:/(cancel&#124;resume&#124;recover&#124;blender&#124;model&#124;folder)(?:/(\d+))?)?` | [studio_tools_api.py:63](../backend/story_builder/services/studio_tools_api.py#L63) |
| `/api/studio-tools/chat` | [studio_tools_api.py:101](../backend/story_builder/services/studio_tools_api.py#L101) |

## music_jukebox_api.py

| Route literal or pattern | Source |
|---|---|
| `/api/jukebox/projects/(jukebox-[a-f0-9]{12})/render` | [music_jukebox_api.py:10](../backend/story_builder/services/music_jukebox_api.py#L10) |
| `/api/jukebox/state` | [music_jukebox_api.py:16](../backend/story_builder/services/music_jukebox_api.py#L16) |
| `/api/jukebox/folder` | [music_jukebox_api.py:17](../backend/story_builder/services/music_jukebox_api.py#L17) |
| `/api/jukebox/projects` | [music_jukebox_api.py:18](../backend/story_builder/services/music_jukebox_api.py#L18) |
| `/api/jukebox/projects/(jukebox-[a-f0-9]{12})/jobs` | [music_jukebox_api.py:19](../backend/story_builder/services/music_jukebox_api.py#L19) |
| `/api/jukebox/projects/(jukebox-[a-f0-9]{12})(?:/(save&#124;export&#124;copy))?` | [music_jukebox_api.py:22](../backend/story_builder/services/music_jukebox_api.py#L22) |
| `/api/jukebox/jobs/(music-jukebox-[a-f0-9]{12})(?:/(cancel))?` | [music_jukebox_api.py:39](../backend/story_builder/services/music_jukebox_api.py#L39) |
| `/api/jukebox/exports/(music-jukebox-[a-f0-9]{12})` | [music_jukebox_api.py:44](../backend/story_builder/services/music_jukebox_api.py#L44) |
| `/api/jukebox/chat` | [music_jukebox_api.py:52](../backend/story_builder/services/music_jukebox_api.py#L52) |

