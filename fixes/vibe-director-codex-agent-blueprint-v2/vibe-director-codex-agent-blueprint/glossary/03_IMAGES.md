# Images tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## images.generate — Text-to-image and image editing

**Choose when:** Create an image from text or edit images using a supported reference workflow.

**UI:** #/text-to-image

**Inputs:** Available workflow, prompt, dimensions/settings, asset role, references and ownership/lineage where required.

**Outputs:** Batch/candidate jobs, validated generated image assets and optional export.

**How to use:** getImageWorkflows/getImageWorker → prepareImagePrompt or user prompt → validateImageRequest → createImageBatch → getImageBatch → acceptImageCandidate/exportImageAsset. Inspect current workflow schemas; Qwen editing uses references and is distinct from pure T2I.

**Source:** [image-api.ts](../frontend/src/lib/image-api.ts), [TextToImagePage.tsx](../frontend/src/TextToImagePage.tsx), [production_image_workflows.py](../backend/story_builder/services/production_image_workflows.py), [production_image_jobs.py](../backend/story_builder/services/production_image_jobs.py)

## images.production — Character, world, first/last-frame assets and selections

**Choose when:** Prepare identities/backgrounds or explicitly requested first/last images for production.

**UI:** #/characters, #/worlds, #/frames

**Inputs:** Screenplay targets, target role/record, selected masters/references, clip/shot IDs and workflow settings.

**Outputs:** Generated images, selected target associations and lineage.

**How to use:** Use image batch/selection APIs and ImageAssetsPage stage flow. First/last images are an optional manual path; do not infer FFLF automation is enabled. Reuse selected assets instead of silently generating substitutes.

**Source:** [ImageAssetsPage.tsx](../frontend/src/ImageAssetsPage.tsx), [image-api.ts](../frontend/src/lib/image-api.ts), [production_image_selection.py](../backend/story_builder/services/production_image_selection.py)

## images.inspect — Image Detailer

**Choose when:** Describe an image for search or inspect its content.

**UI:** #/media-prep → Images → Image Detailer

**Inputs:** Image asset ID and quick/balanced/deep mode.

**Outputs:** Analysis job and image analysis/annotations.

**How to use:** media-api.ts startImageDetailerJob/getImageDetailerJob with cancel/retry; saveImageAnalysis where appropriate. Check model/runtime availability before claiming vision.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [image_detailer.py](../backend/story_builder/services/image_detailer.py)

## images.training — Image training and adapter catalogue

**Choose when:** Explicitly requested image model/LoRA training workflow or checkpoint selection.

**UI:** Training controls exposed by image tools; inspect current UI

**Inputs:** Training configuration in training UI, checkpoint/adapter information.

**Outputs:** Training launch/status, adapter/checkpoint catalogue and published adapter.

**How to use:** /api/studio-tools/training and /training/launch; /loras, /loras/checkpoints, /loras/publish. This is not needed to save a prompting lesson. Inspect image_training.py; launching a training UI is not a completed training run.

**Source:** [image_training.py](../backend/story_builder/services/image_training.py), [studio_tools_api.py](../backend/story_builder/services/studio_tools_api.py)
