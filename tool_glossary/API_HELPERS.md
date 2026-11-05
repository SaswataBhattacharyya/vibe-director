# API helper index

Source inventory generated 2026-11-05. Each row is an exported function declaration with an exact source link. Read its body and TypeScript types before calling; declarations are not a registered LLM tool schema. Constants/types are excluded.

## editor-api.ts

### `editorApi`

[Source declaration](../frontend/src/lib/editor-api.ts#L7)

```typescript
export async function editorApi<T>(path:string, method='GET', body?:unknown):Promise<T> {
```


## image-api.ts

### `getImageWorkflows`

[Source declaration](../frontend/src/lib/image-api.ts#L18)

```typescript
export const getImageWorkflows = (checkGpuAdmission = false) => request<ImageWorkflows>(`/api/images/workflows${checkGpuAdmission?'?check_gpu_admission=1':''}`);
```

### `getImageWorker`

[Source declaration](../frontend/src/lib/image-api.ts#L19)

```typescript
export const getImageWorker = () => request<ImageWorker>('/api/images/worker');
```

### `getImageSelection`

[Source declaration](../frontend/src/lib/image-api.ts#L20)

```typescript
export const getImageSelection = (workspaceId:string,revisionId:string,targetType:string,targetId:string) => request<{selection:{asset_id:string;authority:string;job_id:string}|null}>(`/api/images/selections?workspace_id=${encodeURIComponent(workspaceId)}&screenplay_revision_id=${encodeURIComponent(revisionId)}&target_type=${encodeURIComponent(targetType)}&target_record_id=${encodeURIComponent(targetId)}`);
```

### `validateImageRequest`

[Source declaration](../frontend/src/lib/image-api.ts#L21)

```typescript
export const validateImageRequest = (value:Record<string,unknown>) => request<any>('/api/images/validations',post(value));
```

### `prepareImagePrompt`

[Source declaration](../frontend/src/lib/image-api.ts#L22)

```typescript
export const prepareImagePrompt = (value:Record<string,unknown>) => request<ImagePromptDraft>('/api/images/prompts/prepare',post(value));
```

### `createImageBatch`

[Source declaration](../frontend/src/lib/image-api.ts#L23)

```typescript
export const createImageBatch = (value:Record<string,unknown>) => request<{batch_id:string;jobs:ImageCandidate[];reused:boolean}>('/api/images/jobs',post(value));
```

### `startAutomatedImageStage`

[Source declaration](../frontend/src/lib/image-api.ts#L24)

```typescript
export const startAutomatedImageStage = (workspaceId:string,screenplayRevisionId:string,step:'character_images'|'world_images'|'frame_images') => request<ImageStageAdmission>('/api/images/automated-stage',post({workspace_id:workspaceId,screenplay_revision_id:screenplayRevisionId,step}));
```

### `getImageBatch`

[Source declaration](../frontend/src/lib/image-api.ts#L25)

```typescript
export const getImageBatch = (workspaceId:string,batchId:string) => request<ImageBatch>(`/api/images/batches/${encodeURIComponent(batchId)}?workspace_id=${encodeURIComponent(workspaceId)}`);
```

### `acceptImageCandidate`

[Source declaration](../frontend/src/lib/image-api.ts#L26)

```typescript
export const acceptImageCandidate = (workspaceId:string,jobId:string,assetRole:string,lineage?:{screenplay_revision_id:string;target_record_id?:string;scene_number?:number;shot_number?:number;clip_id?:string;asset_role?:string}) => request<{job_id:string;asset:import('./media-api').MediaAsset;selected:boolean;target_selection?:{asset_id:string}|null}>(`/api/images/jobs/${encodeURIComponent(jobId)}/accept`,post({workspace_id:workspaceId,asset_role:assetRole,...lineage}));
```

### `exportImageAsset`

[Source declaration](../frontend/src/lib/image-api.ts#L27)

```typescript
export const exportImageAsset = (value:{workspace_id:string;asset_id:string;folder:string;filename:string;overwrite?:boolean;existing_sha256?:string}) => request<{path?:string;collision?:boolean;existing_sha256?:string}>('/api/images/assets/export',post(value));
```

### `stageTemporaryImageReference`

[Source declaration](../frontend/src/lib/image-api.ts#L28)

```typescript
export async function stageTemporaryImageReference(workspaceId:string,file:File,token:string) {
```

### `deleteTemporaryImageAsset`

[Source declaration](../frontend/src/lib/image-api.ts#L32)

```typescript
export const deleteTemporaryImageAsset=(workspaceId:string,assetId:string,token:string)=>request<{deleted:boolean}>(`/api/images/temporary-assets/${encodeURIComponent(workspaceId)}/${encodeURIComponent(assetId)}`,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
```


## media-api.ts

### `listF5PreparationJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L33)

```typescript
export const listF5PreparationJobs = (workspaceId:string) => request<F5PreparationJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/finetune/f5/jobs`);
```

### `getF5PreparationJob`

[Source declaration](../frontend/src/lib/media-api.ts#L34)

```typescript
export const getF5PreparationJob = (workspaceId:string,jobId:string) => request<F5PreparationJob>(`/api/audio/${encodeURIComponent(workspaceId)}/finetune/f5/jobs/${encodeURIComponent(jobId)}`);
```

### `createF5PreparationJob`

[Source declaration](../frontend/src/lib/media-api.ts#L35)

```typescript
export const createF5PreparationJob = (workspaceId:string,payload:{dataset_name:string;base_model:string;samples:Array<{asset_id:string;text:string}>}) => request<F5PreparationJob>(`/api/audio/${encodeURIComponent(workspaceId)}/finetune/f5/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
```

### `listStagedDonorVideos`

[Source declaration](../frontend/src/lib/media-api.ts#L55)

```typescript
export function listStagedDonorVideos(workspaceId:string) {
```

### `importStagedDonorVideos`

[Source declaration](../frontend/src/lib/media-api.ts#L59)

```typescript
export function importStagedDonorVideos(workspaceId:string, assetIds:string[]) {
```

### `getStagedDonorAnalysis`

[Source declaration](../frontend/src/lib/media-api.ts#L65)

```typescript
export function getStagedDonorAnalysis(workspaceId:string, assetId:string) {
```

### `importStagedDonorAnalysisAudio`

[Source declaration](../frontend/src/lib/media-api.ts#L69)

```typescript
export function importStagedDonorAnalysisAudio(workspaceId:string, assetId:string, audioAssetIds:string[]) {
```

### `listMediaAssets`

[Source declaration](../frontend/src/lib/media-api.ts#L97)

```typescript
export function listMediaAssets(workspaceId: string, kind: string, includeArchived = false, styleContextId = '') {
```

### `setMediaAssetArchived`

[Source declaration](../frontend/src/lib/media-api.ts#L111)

```typescript
export function setMediaAssetArchived(workspaceId:string,assetId:string,archived:boolean) {
```

### `searchMediaSemantically`

[Source declaration](../frontend/src/lib/media-api.ts#L115)

```typescript
export function searchMediaSemantically(workspaceId: string, kind: string, query: string) {
```

### `listVideoAnalysisJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L121)

```typescript
export function listVideoAnalysisJobs(workspaceId: string) {
```

### `getVideoAnalysisJob`

[Source declaration](../frontend/src/lib/media-api.ts#L125)

```typescript
export function getVideoAnalysisJob(workspaceId: string, jobId: string) {
```

### `startVideoAnalysis`

[Source declaration](../frontend/src/lib/media-api.ts#L129)

```typescript
export function startVideoAnalysis(workspaceId: string, assetIds: string[], settings: Record<string, unknown> = {}) {
```

### `cancelVideoAnalysis`

[Source declaration](../frontend/src/lib/media-api.ts#L135)

```typescript
export function cancelVideoAnalysis(workspaceId: string, jobId: string) {
```

### `deleteVideoAnalysis`

[Source declaration](../frontend/src/lib/media-api.ts#L139)

```typescript
export function deleteVideoAnalysis(workspaceId: string, jobId: string) {
```

### `retryVideoAnalysis`

[Source declaration](../frontend/src/lib/media-api.ts#L143)

```typescript
export function retryVideoAnalysis(workspaceId: string, jobId: string) {
```

### `getSamAudioCapability`

[Source declaration](../frontend/src/lib/media-api.ts#L149)

```typescript
export function getSamAudioCapability() {
```

### `isolateVideoAudioEvent`

[Source declaration](../frontend/src/lib/media-api.ts#L152)

```typescript
export function isolateVideoAudioEvent(workspaceId:string,runId:string,eventId:string,prompt:string) {
```

### `saveSamAudioPreview`

[Source declaration](../frontend/src/lib/media-api.ts#L157)

```typescript
export function saveSamAudioPreview(workspaceId:string,temporaryId:string) {
```

### `discardSamAudioPreview`

[Source declaration](../frontend/src/lib/media-api.ts#L162)

```typescript
export function discardSamAudioPreview(workspaceId:string,temporaryId:string) {
```

### `listImageDetailerJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L166)

```typescript
export function listImageDetailerJobs(workspaceId: string) {
```

### `getImageDetailerJob`

[Source declaration](../frontend/src/lib/media-api.ts#L170)

```typescript
export function getImageDetailerJob(workspaceId: string, jobId: string) {
```

### `startImageDetailerJob`

[Source declaration](../frontend/src/lib/media-api.ts#L174)

```typescript
export function startImageDetailerJob(workspaceId: string, assetId: string, mode: 'quick'|'balanced'|'deep') {
```

### `cancelImageDetailerJob`

[Source declaration](../frontend/src/lib/media-api.ts#L180)

```typescript
export function cancelImageDetailerJob(workspaceId: string, jobId: string) {
```

### `retryImageDetailerJob`

[Source declaration](../frontend/src/lib/media-api.ts#L184)

```typescript
export function retryImageDetailerJob(workspaceId: string, jobId: string) {
```

### `resolveYoutubeSources`

[Source declaration](../frontend/src/lib/media-api.ts#L188)

```typescript
export function resolveYoutubeSources(workspaceId: string, value: {mode:'search'|'paste'; query?:string; count?:number; urls_text?:string}) {
```

### `listYoutubeJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L194)

```typescript
export function listYoutubeJobs(workspaceId: string) {
```

### `getYoutubeJob`

[Source declaration](../frontend/src/lib/media-api.ts#L198)

```typescript
export function getYoutubeJob(workspaceId: string, jobId: string) {
```

### `startYoutubeDownload`

[Source declaration](../frontend/src/lib/media-api.ts#L202)

```typescript
export function startYoutubeDownload(workspaceId: string, urls: YoutubeCandidate[], sourceMode: string) {
```

### `cancelYoutubeJob`

[Source declaration](../frontend/src/lib/media-api.ts#L208)

```typescript
export function cancelYoutubeJob(workspaceId: string, jobId: string) {
```

### `uploadMediaAsset`

[Source declaration](../frontend/src/lib/media-api.ts#L212)

```typescript
export function uploadMediaAsset(workspaceId: string, file: File, role: string, storage: 'workspace' | 'recording' = 'workspace') {
```

### `linkMediaAssetToStyle`

[Source declaration](../frontend/src/lib/media-api.ts#L218)

```typescript
export function linkMediaAssetToStyle(workspaceId: string, assetId: string, directingStyleId: string) {
```

### `extractMediaStyleFrames`

[Source declaration](../frontend/src/lib/media-api.ts#L224)

```typescript
export function extractMediaStyleFrames(workspaceId: string, assetId: string, directingStyleId: string, timestampsSeconds: number[]) {
```

### `getStyleFrameJob`

[Source declaration](../frontend/src/lib/media-api.ts#L232)

```typescript
export const getStyleFrameJob = (workspaceId:string,jobId:string) => request<StyleFrameJob>(`/api/media/${encodeURIComponent(workspaceId)}/style-frame-jobs/${encodeURIComponent(jobId)}`);
```

### `cancelStyleFrameJob`

[Source declaration](../frontend/src/lib/media-api.ts#L233)

```typescript
export const cancelStyleFrameJob = (workspaceId:string,jobId:string) => request<StyleFrameJob>(`/api/media/${encodeURIComponent(workspaceId)}/style-frame-jobs/${encodeURIComponent(jobId)}/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
```

### `updateMediaAnnotations`

[Source declaration](../frontend/src/lib/media-api.ts#L235)

```typescript
export function updateMediaAnnotations(workspaceId: string, assetId: string, value: {
```

### `indexMediaAssetAnnotations`

[Source declaration](../frontend/src/lib/media-api.ts#L243)

```typescript
export function indexMediaAssetAnnotations(workspaceId: string, assetId: string) {
```

### `createMediaContentIndexJob`

[Source declaration](../frontend/src/lib/media-api.ts#L250)

```typescript
export const createMediaContentIndexJob = (workspaceId:string, assetId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/semantic-content-index`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
```

### `getMediaContentIndexJob`

[Source declaration](../frontend/src/lib/media-api.ts#L251)

```typescript
export const getMediaContentIndexJob = (workspaceId:string, jobId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs/${encodeURIComponent(jobId)}`);
```

### `listMediaContentIndexJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L252)

```typescript
export const listMediaContentIndexJobs = (workspaceId:string) => request<SemanticIndexJob[]>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs`);
```

### `retryMediaContentIndexJob`

[Source declaration](../frontend/src/lib/media-api.ts#L253)

```typescript
export const retryMediaContentIndexJob = (workspaceId:string, jobId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs/${encodeURIComponent(jobId)}/retry`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
```

### `cancelMediaContentIndexJob`

[Source declaration](../frontend/src/lib/media-api.ts#L254)

```typescript
export const cancelMediaContentIndexJob = (workspaceId:string, jobId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs/${encodeURIComponent(jobId)}/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
```

### `saveImageAnalysis`

[Source declaration](../frontend/src/lib/media-api.ts#L256)

```typescript
export function saveImageAnalysis(workspaceId: string, assetId: string, value: {
```

### `listAudioVoices`

[Source declaration](../frontend/src/lib/media-api.ts#L265)

```typescript
export function listAudioVoices() { return request<AudioVoice[]>('/api/audio/voices'); }
```

### `importComfyVoiceToWorkspace`

[Source declaration](../frontend/src/lib/media-api.ts#L266)

```typescript
export function importComfyVoiceToWorkspace(workspaceId:string,voiceId:string) {
```

### `listAudioModels`

[Source declaration](../frontend/src/lib/media-api.ts#L271)

```typescript
export function listAudioModels() { return request<AudioModel[]>('/api/audio/models'); }
```

### `getAudioCapabilities`

[Source declaration](../frontend/src/lib/media-api.ts#L272)

```typescript
export function getAudioCapabilities() { return request<AudioCapabilities>('/api/audio/capabilities'); }
```

### `refreshAudioVoices`

[Source declaration](../frontend/src/lib/media-api.ts#L273)

```typescript
export function refreshAudioVoices(expectedVoiceId?:string) {
```

### `getAudioUtilityCapabilities`

[Source declaration](../frontend/src/lib/media-api.ts#L283)

```typescript
export const getAudioUtilityCapabilities = () => request<AudioUtilityCapabilities>('/api/audio/utilities/capabilities');
```

### `listAudioUtilityJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L284)

```typescript
export const listAudioUtilityJobs = (workspaceId:string) => request<AudioUtilityJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/utilities/jobs`);
```

### `getAudioUtilityJob`

[Source declaration](../frontend/src/lib/media-api.ts#L285)

```typescript
export const getAudioUtilityJob = (workspaceId:string,jobId:string) => request<AudioUtilityJob>(`/api/audio/${encodeURIComponent(workspaceId)}/utilities/jobs/${encodeURIComponent(jobId)}`);
```

### `createAudioUtilityJob`

[Source declaration](../frontend/src/lib/media-api.ts#L286)

```typescript
export const createAudioUtilityJob = (workspaceId:string,operation:AudioUtilityOperation['id'],asset_ids:string[],settings:Record<string,unknown>={}) => request<AudioUtilityJob>(`/api/audio/${encodeURIComponent(workspaceId)}/utilities/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,asset_ids,settings})});
```

### `getMusicCapabilities`

[Source declaration](../frontend/src/lib/media-api.ts#L287)

```typescript
export const getMusicCapabilities = () => request<MusicCapabilities>('/api/audio/music/capabilities');
```

### `getWorkflowGuidance`

[Source declaration](../frontend/src/lib/media-api.ts#L288)

```typescript
export const getWorkflowGuidance = (workflowId:string,modelId:string) => {
```

### `listMusicJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L292)

```typescript
export const listMusicJobs = (workspaceId:string,kind:'ace-music'|'control-foley') => request<MusicJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/${kind==='ace-music'?'music':'control-foley'}/jobs`);
```

### `createMusicJob`

[Source declaration](../frontend/src/lib/media-api.ts#L293)

```typescript
export const createMusicJob = (workspaceId:string,kind:'ace-music'|'control-foley',settings:Record<string,unknown>,references:PromptKnowledgeRef,mediaReferences?:{video_asset_id?:string;audio_asset_id?:string}) => request<MusicJob>(`/api/audio/${encodeURIComponent(workspaceId)}/${kind==='ace-music'?'music':'control-foley'}/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({settings,prompt_knowledge_ref:references,...(mediaReferences?{references:mediaReferences}:{})})});
```

### `getMusicJob`

[Source declaration](../frontend/src/lib/media-api.ts#L294)

```typescript
export const getMusicJob = (workspaceId:string,kind:'ace-music'|'control-foley',jobId:string) => request<MusicJob>(`/api/audio/${encodeURIComponent(workspaceId)}/${kind==='ace-music'?'music':'control-foley'}/jobs/${encodeURIComponent(jobId)}`);
```

### `enrollAudioVoice`

[Source declaration](../frontend/src/lib/media-api.ts#L295)

```typescript
export function enrollAudioVoice(workspaceId:string,assetId:string,name:string,transcript:string) {
```

### `getReconstructionSession`

[Source declaration](../frontend/src/lib/media-api.ts#L301)

```typescript
export const getReconstructionSession = (workspaceId:string) => request<ReconstructionSession>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct`);
```

### `saveReconstructionCalibration`

[Source declaration](../frontend/src/lib/media-api.ts#L302)

```typescript
export const saveReconstructionCalibration = (workspaceId:string,character_name:string,sentence:string) => request<ReconstructionSession>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/calibration`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({character_name,sentence,settings:{}})});
```

### `createReconstructionPart`

[Source declaration](../frontend/src/lib/media-api.ts#L303)

```typescript
export const createReconstructionPart = (workspaceId:string,payload:{part_id:string;character_name:string;sequence:number;expected_text:string}) => request<ReconstructionPart>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/parts`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
```

### `addReconstructionTake`

[Source declaration](../frontend/src/lib/media-api.ts#L304)

```typescript
export const addReconstructionTake = (workspaceId:string,partId:string,asset_id:string,transcript:string) => request<ReconstructionTake>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/parts/${encodeURIComponent(partId)}/takes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_id,transcript})});
```

### `acceptReconstructionTake`

[Source declaration](../frontend/src/lib/media-api.ts#L305)

```typescript
export const acceptReconstructionTake = (workspaceId:string,partId:string,takeId:string) => request<{part:ReconstructionPart;take:ReconstructionTake;session:ReconstructionSession;asset:MediaAsset}>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/parts/${encodeURIComponent(partId)}/accept/${encodeURIComponent(takeId)}`,{method:'POST'});
```

### `getAudioEffectCapabilities`

[Source declaration](../frontend/src/lib/media-api.ts#L315)

```typescript
export const getAudioEffectCapabilities = () => request<AudioEffectCapabilities>('/api/audio/effects/capabilities');
```

### `listAudioEffectJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L316)

```typescript
export const listAudioEffectJobs = (workspaceId:string) => request<AudioEffectJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/effects/jobs`);
```

### `getAudioEffectJob`

[Source declaration](../frontend/src/lib/media-api.ts#L317)

```typescript
export const getAudioEffectJob = (workspaceId:string,jobId:string) => request<AudioEffectJob>(`/api/audio/${encodeURIComponent(workspaceId)}/effects/jobs/${encodeURIComponent(jobId)}`);
```

### `createAudioEffectJob`

[Source declaration](../frontend/src/lib/media-api.ts#L318)

```typescript
export const createAudioEffectJob = (workspaceId:string,operation:AudioEffectOperation['id'],asset_id:string,settings:Record<string,unknown>={}) => request<AudioEffectJob>(`/api/audio/${encodeURIComponent(workspaceId)}/effects/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,asset_id,settings})});
```

### `getAudioSceneCapabilities`

[Source declaration](../frontend/src/lib/media-api.ts#L323)

```typescript
export const getAudioSceneCapabilities = () => request<AudioSceneCapabilities>('/api/audio/scene-surgery/capabilities');
```

### `createAudioSceneSplit`

[Source declaration](../frontend/src/lib/media-api.ts#L324)

```typescript
export const createAudioSceneSplit = (workspaceId:string,asset_id:string,edits:Array<{start:number;end:number;text?:string}>,transcript?:string) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_id,edits,transcript})});
```

### `listAudioSceneSplits`

[Source declaration](../frontend/src/lib/media-api.ts#L325)

```typescript
export const listAudioSceneSplits = (workspaceId:string) => request<AudioSceneJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/jobs`);
```

### `getAudioSceneSplit`

[Source declaration](../frontend/src/lib/media-api.ts#L326)

```typescript
export const getAudioSceneSplit = (workspaceId:string,jobId:string) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/jobs/${encodeURIComponent(jobId)}`);
```

### `createAudioSceneStitch`

[Source declaration](../frontend/src/lib/media-api.ts#L327)

```typescript
export const createAudioSceneStitch = (workspaceId:string,split_job_id:string,mode:'simple'|'timed',replacement_asset_ids:Record<number,string>,gaps:Record<number,number>) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/stitch-jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({split_job_id,mode,replacement_asset_ids,gaps})});
```

### `listAudioSceneStitches`

[Source declaration](../frontend/src/lib/media-api.ts#L328)

```typescript
export const listAudioSceneStitches = (workspaceId:string) => request<AudioSceneJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/stitch-jobs`);
```

### `getAudioSceneStitch`

[Source declaration](../frontend/src/lib/media-api.ts#L329)

```typescript
export const getAudioSceneStitch = (workspaceId:string,jobId:string) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/stitch-jobs/${encodeURIComponent(jobId)}`);
```

### `listTimedTTSJobs`

[Source declaration](../frontend/src/lib/media-api.ts#L330)

```typescript
export function listTimedTTSJobs(workspaceId:string) {
```

### `createTimedTTSJob`

[Source declaration](../frontend/src/lib/media-api.ts#L333)

```typescript
export function createTimedTTSJob(workspaceId:string,payload:{srt_content:string;characters:Array<{name:string;reference_voice_id:string;language:string}>;settings:Record<string,unknown>}) {
```

### `getTimedTTSJob`

[Source declaration](../frontend/src/lib/media-api.ts#L337)

```typescript
export function getTimedTTSJob(workspaceId:string,jobId:string) {
```

### `listMediaSeoStyles`

[Source declaration](../frontend/src/lib/media-api.ts#L341)

```typescript
export function listMediaSeoStyles(workspaceId: string) {
```

### `saveMediaSeoStyle`

[Source declaration](../frontend/src/lib/media-api.ts#L345)

```typescript
export function saveMediaSeoStyle(workspaceId: string, value: Omit<MediaSeoStyle, 'style_id'|'created_at'>, styleId?: string) {
```

### `deleteMediaSeoStyle`

[Source declaration](../frontend/src/lib/media-api.ts#L352)

```typescript
export function deleteMediaSeoStyle(workspaceId: string, styleId: string) {
```

### `rankMediaAssets`

[Source declaration](../frontend/src/lib/media-api.ts#L356)

```typescript
export function rankMediaAssets(assets: MediaAsset[], query: string, order: 'newest'|'oldest', style?: MediaSeoStyle) {
```

### `deleteExtractedMediaAsset`

[Source declaration](../frontend/src/lib/media-api.ts#L376)

```typescript
export function deleteExtractedMediaAsset(workspaceId:string, assetId:string) {
```

### `browseMediaCatalogue`

[Source declaration](../frontend/src/lib/media-api.ts#L381)

```typescript
export function browseMediaCatalogue(workspaceId:string, options:{kinds:string;source:string;owner:string;query:string;offset:number;order:string;folder?:string}) {
```

### `reuseCatalogueAsset`

[Source declaration](../frontend/src/lib/media-api.ts#L385)

```typescript
export function reuseCatalogueAsset(workspaceId:string, asset:MediaAsset, role?:string, mode:'reference'|'copy' = 'reference') {
```

### `refreshDownloadCatalogue`

[Source declaration](../frontend/src/lib/media-api.ts#L392)

```typescript
export const refreshDownloadCatalogue = (workspaceId:string) => request<{added:number;errors:{filename:string;message:string}[]}>(`/api/media/${encodeURIComponent(workspaceId||'global')}/assets/catalogue-refresh`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
```

### `nameMediaWorkspace`

[Source declaration](../frontend/src/lib/media-api.ts#L393)

```typescript
export const nameMediaWorkspace = (workspaceId:string,name:string) => request<{workspace_id:string;name:string}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/workspace-name`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
```

### `previewMediaDeletion`

[Source declaration](../frontend/src/lib/media-api.ts#L396)

```typescript
export function previewMediaDeletion(workspaceId:string, assetId:string) {
```

### `permanentlyDeleteMedia`

[Source declaration](../frontend/src/lib/media-api.ts#L399)

```typescript
export function permanentlyDeleteMedia(workspaceId:string, preview:MediaDeletion) {
```


## prompt-director-api.ts

### `getPromptGuidance`

[Source declaration](../frontend/src/lib/prompt-director-api.ts#L12)

```typescript
export const getPromptGuidance=(w:string,r:string)=>request<PromptGuidance>(path(w,r));
```

### `savePromptGuidance`

[Source declaration](../frontend/src/lib/prompt-director-api.ts#L13)

```typescript
export const savePromptGuidance=(w:string,r:string,version:number,lessons:PromptLesson[],assets:Record<string,string>)=>request<PromptGuidance>(path(w,r),'PUT',{expected_revision:version,lessons,assets});
```

### `discussPrompts`

[Source declaration](../frontend/src/lib/prompt-director-api.ts#L14)

```typescript
export const discussPrompts=(w:string,r:string,mode:PromptTurn['mode'],instruction:string,prompts:Record<string,string>,workflows:Record<string,string>,key:string)=>request<PromptTurn>(`${path(w,r)}/${mode}`,'POST',{instruction,prompts,workflows,idempotency_key:key});
```

### `exportPromptSkill`

[Source declaration](../frontend/src/lib/prompt-director-api.ts#L15)

```typescript
export const exportPromptSkill=(w:string,r:string)=>request<{filename:string;text:string}>(`${path(w,r)}/skill`);
```


## status-api.ts

### `getComfyQueueStatus`

[Source declaration](../frontend/src/lib/status-api.ts#L37)

```typescript
export async function getComfyQueueStatus(): Promise<ComfyQueueStatus> {
```

### `getLocalJobQueueStatus`

[Source declaration](../frontend/src/lib/status-api.ts#L42)

```typescript
export async function getLocalJobQueueStatus(): Promise<LocalJobQueueStatus> {
```

### `getWorkflowStatus`

[Source declaration](../frontend/src/lib/status-api.ts#L47)

```typescript
export async function getWorkflowStatus(): Promise<WorkflowStatus> {
```

### `getRuntimeGuard`

[Source declaration](../frontend/src/lib/status-api.ts#L52)

```typescript
export async function getRuntimeGuard(): Promise<RuntimeGuard> {
```

### `getWorkerDispatch`

[Source declaration](../frontend/src/lib/status-api.ts#L57)

```typescript
export async function getWorkerDispatch(): Promise<WorkflowStatus['dispatch']> {
```

### `getGpuAdmission`

[Source declaration](../frontend/src/lib/status-api.ts#L62)

```typescript
export async function getGpuAdmission(): Promise<GpuAdmission> {
```

### `setWorkloadPolicy`

[Source declaration](../frontend/src/lib/status-api.ts#L70)

```typescript
export async function setWorkloadPolicy(allowSimultaneousRuns: boolean): Promise<WorkloadPolicy> {
```

### `clearGpuSafetyHold`

[Source declaration](../frontend/src/lib/status-api.ts#L80)

```typescript
export async function clearGpuSafetyHold(): Promise<{ cleared: boolean }> {
```


## story-api.ts

### `listStoryWorkspaces`

[Source declaration](../frontend/src/lib/story-api.ts#L51)

```typescript
export const listStoryWorkspaces = (offset = 0, limit = 50) => json<Page<StoryWorkspace>>(`/api/story/workspaces?limit=${limit}&offset=${offset}`);
```

### `createStoryWorkspace`

[Source declaration](../frontend/src/lib/story-api.ts#L52)

```typescript
export const createStoryWorkspace = (title: string, source_text: string, idempotency_key: string, style_selection_snapshot_id?: string) => json<StoryCreation>('/api/story/workspaces', body({ title, source_text, idempotency_key, ...(style_selection_snapshot_id ? { style_selection_snapshot_id } : {}) }));
```

### `getStoryCreation`

[Source declaration](../frontend/src/lib/story-api.ts#L53)

```typescript
export const getStoryCreation = (key: string) => json<StoryCreation>(`/api/story/creations/by-idempotency/${encodeURIComponent(key)}`);
```

### `getStoryWorkspace`

[Source declaration](../frontend/src/lib/story-api.ts#L54)

```typescript
export const getStoryWorkspace = (id: string) => json<StoryWorkspace>(`/api/story/workspaces/${encodeURIComponent(id)}`);
```

### `getStorySourceDraft`

[Source declaration](../frontend/src/lib/story-api.ts#L55)

```typescript
export const getStorySourceDraft = async (id: string) => (await json<{ draft: StorySourceDraft | null }>(`/api/story/workspaces/${encodeURIComponent(id)}/draft`)).draft;
```

### `saveStorySourceDraft`

[Source declaration](../frontend/src/lib/story-api.ts#L56)

```typescript
export const saveStorySourceDraft = (id: string, source_text: string, base_revision_id: string) => json<StorySourceDraft>(`/api/story/workspaces/${encodeURIComponent(id)}/draft`, body({ source_text, base_revision_id }, 'PUT'));
```

### `discardStorySourceDraft`

[Source declaration](../frontend/src/lib/story-api.ts#L57)

```typescript
export const discardStorySourceDraft = (id: string) => json<{ discarded: boolean }>(`/api/story/workspaces/${encodeURIComponent(id)}/draft`, { method: 'DELETE', headers: { Accept: 'application/json' } });
```

### `getStoryRevision`

[Source declaration](../frontend/src/lib/story-api.ts#L58)

```typescript
export const getStoryRevision = (id: string, revisionId: string) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/revisions/${encodeURIComponent(revisionId)}`);
```

### `saveStoryRevision`

[Source declaration](../frontend/src/lib/story-api.ts#L59)

```typescript
export const saveStoryRevision = (id: string, source_text: string, expected_current_revision_id: string | null) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/revisions`, body({ source_text, expected_current_revision_id }));
```

### `listStoryRevisions`

[Source declaration](../frontend/src/lib/story-api.ts#L60)

```typescript
export const listStoryRevisions = (id: string, offset = 0, limit = 50) => json<Page<StoryRevisionSummary>>(`/api/story/workspaces/${encodeURIComponent(id)}/revisions?limit=${limit}&offset=${offset}`);
```

### `restoreStoryRevision`

[Source declaration](../frontend/src/lib/story-api.ts#L61)

```typescript
export const restoreStoryRevision = (id: string, revision_id: string, expected_current_revision_id: string | null) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/restore`, body({ revision_id, expected_current_revision_id }));
```

### `uploadStoryFile`

[Source declaration](../frontend/src/lib/story-api.ts#L62)

```typescript
export const uploadStoryFile = (file: File) => json<StoryImport>(`/api/story/imports?filename=${encodeURIComponent(file.name)}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', Accept: 'application/json' }, body: file });
```

### `applyStoryImport`

[Source declaration](../frontend/src/lib/story-api.ts#L63)

```typescript
export const applyStoryImport = (id: string, title: string, source_text: string, idempotency_key: string, style_selection_snapshot_id?: string) => json<StoryCreation>(`/api/story/imports/${encodeURIComponent(id)}/apply`, body({ title, source_text, idempotency_key, ...(style_selection_snapshot_id ? { style_selection_snapshot_id } : {}) }));
```

### `proposeStoryEdit`

[Source declaration](../frontend/src/lib/story-api.ts#L64)

```typescript
export const proposeStoryEdit = (id: string, input: { base_revision_id: string; start_codepoint: number; end_codepoint: number; expected_text: string; instruction: string; idempotency_key: string; context_scope?: 'story' }) => json<StoryEditProposal>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals`, body(input));
```

### `getStoryEditRequest`

[Source declaration](../frontend/src/lib/story-api.ts#L65)

```typescript
export const getStoryEditRequest = (key: string) => json<{ status: string; workspace_id: string; proposal?: StoryEditProposal; recovery_message?: string }>(`/api/story/edit-requests/by-key/${encodeURIComponent(key)}`);
```

### `getStoryEditProposal`

[Source declaration](../frontend/src/lib/story-api.ts#L66)

```typescript
export const getStoryEditProposal = (id: string, proposalId: string) => json<StoryEditProposal>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals?id=${encodeURIComponent(proposalId)}`);
```

### `acceptStoryEdit`

[Source declaration](../frontend/src/lib/story-api.ts#L67)

```typescript
export const acceptStoryEdit = (id: string, proposal_id: string, expected_current_revision_id: string | null) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals/accept`, body({ proposal_id, expected_current_revision_id }));
```

### `discardStoryEdit`

[Source declaration](../frontend/src/lib/story-api.ts#L68)

```typescript
export const discardStoryEdit = (id: string, proposal_id: string) => json<StoryEditProposal>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals/discard`, body({ proposal_id }));
```

### `buildStoryGraph`

[Source declaration](../frontend/src/lib/story-api.ts#L69)

```typescript
export const buildStoryGraph = (id: string, source_revision_id: string, idempotency_key: string) => json<StoryGraph>(`/api/story/workspaces/${encodeURIComponent(id)}/graph`, body({ source_revision_id, idempotency_key }));
```

### `getStoryGraph`

[Source declaration](../frontend/src/lib/story-api.ts#L70)

```typescript
export const getStoryGraph = (id: string, source_revision_id: string) => json<StoryGraph>(`/api/story/workspaces/${encodeURIComponent(id)}/graph?revision_id=${encodeURIComponent(source_revision_id)}`);
```

### `getStoryGraphSnapshot`

[Source declaration](../frontend/src/lib/story-api.ts#L71)

```typescript
export const getStoryGraphSnapshot = (id: string, snapshot_id: string) => json<StoryGraph>(`/api/story/workspaces/${encodeURIComponent(id)}/graph?snapshot_id=${encodeURIComponent(snapshot_id)}`);
```

### `searchStoryGraph`

[Source declaration](../frontend/src/lib/story-api.ts#L72)

```typescript
export const searchStoryGraph = (id: string, source_revision_id: string, query: string) => json<StoryGraphSearch>(`/api/story/workspaces/${encodeURIComponent(id)}/graph/search?revision_id=${encodeURIComponent(source_revision_id)}&q=${encodeURIComponent(query)}`);
```

### `updateStoryGraphRecord`

[Source declaration](../frontend/src/lib/story-api.ts#L73)

```typescript
export const updateStoryGraphRecord = (id: string, record_id: string, input: { name: string; detail: string; status: StoryGraphRecord['status'] }) => json<Pick<StoryGraphRecord, 'record_id'|'name'|'detail'|'status'|'user_modified'>>(`/api/story/workspaces/${encodeURIComponent(id)}/graph/records/${encodeURIComponent(record_id)}`, body(input, 'PATCH'));
```

### `decideStoryGraphIdentity`

[Source declaration](../frontend/src/lib/story-api.ts#L74)

```typescript
export const decideStoryGraphIdentity = (id: string, input: { snapshot_id:string; left_record_id:string; right_record_id:string; action:'alias'|'distinct'|'undo'; idempotency_key:string; expected_head:number; left_fingerprint?:string; right_fingerprint?:string; target_decision_id?:string }) => json<{decision_id:string;sequence:number;replayed:boolean}>(`/api/story/workspaces/${encodeURIComponent(id)}/graph/identity-decisions`, body(input));
```

### `draftStoryScreenplay`

[Source declaration](../frontend/src/lib/story-api.ts#L75)

```typescript
export const draftStoryScreenplay = (id: string, source_revision_id: string, graph_snapshot_id: string, idempotency_key: string) => json<ScreenplayRevision | ScreenplayDraftTask>(`/api/story/workspaces/${encodeURIComponent(id)}/screenplay`, body({ source_revision_id, graph_snapshot_id, idempotency_key }));
```

### `getStoryScreenplay`

[Source declaration](../frontend/src/lib/story-api.ts#L76)

```typescript
export const getStoryScreenplay = (id: string, source_revision_id: string) => json<ScreenplayRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/screenplay?revision_id=${encodeURIComponent(source_revision_id)}`);
```

### `listStoryScreenplays`

[Source declaration](../frontend/src/lib/story-api.ts#L77)

```typescript
export const listStoryScreenplays = (id: string, offset = 0, limit = 50) => json<Page<ScreenplayRevisionSummary>>(`/api/story/workspaces/${encodeURIComponent(id)}/screenplay/revisions?limit=${limit}&offset=${offset}`);
```

### `getStoryScreenplayRevision`

[Source declaration](../frontend/src/lib/story-api.ts#L78)

```typescript
export const getStoryScreenplayRevision = (id: string, revisionId: string) => json<ScreenplayRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/screenplay/revisions/${encodeURIComponent(revisionId)}`);
```

### `acceptStoryScreenplay`

[Source declaration](../frontend/src/lib/story-api.ts#L79)

```typescript
export const acceptStoryScreenplay = (id: string, revisionId: string) => json<ScreenplayRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/screenplay/revisions/${encodeURIComponent(revisionId)}/accept`, body({}));
```

### `saveStoryScreenplay`

[Source declaration](../frontend/src/lib/story-api.ts#L80)

```typescript
export const saveStoryScreenplay = (id: string, revisionId: string, screenplay: Screenplay, idempotency_key: string) => json<ScreenplayRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/screenplay/revisions/${encodeURIComponent(revisionId)}`, body({ screenplay, idempotency_key }, 'PATCH'));
```

### `getCharacterVoiceState`

[Source declaration](../frontend/src/lib/story-api.ts#L81)

```typescript
export const getCharacterVoiceState = (id: string, screenplayRevisionId: string) => json<CharacterVoiceState>(`/api/story/workspaces/${encodeURIComponent(id)}/voice-bindings?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`);
```

### `setCharacterVoice`

[Source declaration](../frontend/src/lib/story-api.ts#L82)

```typescript
export const setCharacterVoice = (id: string, screenplayRevisionId: string, characterId: string, voiceAssetId: string | null) => json<CharacterVoiceState>(`/api/story/workspaces/${encodeURIComponent(id)}/voice-bindings`, body({ screenplay_revision_id: screenplayRevisionId, character_id: characterId, voice_asset_id: voiceAssetId }));
```

### `runAutomaticCharacterVoiceMatching`

[Source declaration](../frontend/src/lib/story-api.ts#L83)

```typescript
export const runAutomaticCharacterVoiceMatching = (id: string, screenplayRevisionId: string) => json<CharacterVoiceState>(`/api/story/workspaces/${encodeURIComponent(id)}/voice-bindings/auto-match`, body({ screenplay_revision_id: screenplayRevisionId }));
```

### `getProductionSetup`

[Source declaration](../frontend/src/lib/story-api.ts#L84)

```typescript
export const getProductionSetup = (id: string, screenplayRevisionId: string) => json<ProductionSetupState>(`/api/story/workspaces/${encodeURIComponent(id)}/production-setup?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`);
```

### `saveProductionSetup`

[Source declaration](../frontend/src/lib/story-api.ts#L85)

```typescript
export const saveProductionSetup = (id: string, screenplayRevisionId: string, setup: ProductionSetup) => json<ProductionSetupState>(`/api/story/workspaces/${encodeURIComponent(id)}/production-setup`, body({ screenplay_revision_id: screenplayRevisionId, setup }, 'PUT'));
```

### `getFramePreparationSkips`

[Source declaration](../frontend/src/lib/story-api.ts#L87)

```typescript
export const getFramePreparationSkips = (id: string, screenplayRevisionId: string) => json<FramePreparationSkips>(`/api/story/workspaces/${encodeURIComponent(id)}/frame-preparation-skips?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`);
```

### `setFramePreparationSkip`

[Source declaration](../frontend/src/lib/story-api.ts#L88)

```typescript
export const setFramePreparationSkip = (id: string, screenplayRevisionId: string, sceneNumber: number, shotNumber: number, skipped: boolean) => json<FramePreparationSkips>(`/api/story/workspaces/${encodeURIComponent(id)}/frame-preparation-skips`, body({ screenplay_revision_id: screenplayRevisionId, scene_number: sceneNumber, shot_number: shotNumber, skipped }, 'PUT'));
```

### `getAssistedStageSkips`

[Source declaration](../frontend/src/lib/story-api.ts#L90)

```typescript
export const getAssistedStageSkips = (id: string, screenplayRevisionId: string) => json<AssistedStageSkips>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-stage-skips?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`);
```

### `setAssistedStageSkip`

[Source declaration](../frontend/src/lib/story-api.ts#L91)

```typescript
export const setAssistedStageSkip = (id: string, screenplayRevisionId: string, step: 'character_images'|'world_images'|'frame_images', skipped: boolean) => json<AssistedStageSkips>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-stage-skips`, body({ screenplay_revision_id: screenplayRevisionId, step, skipped }, 'PUT'));
```

### `getStoryPromptDrafts`

[Source declaration](../frontend/src/lib/story-api.ts#L92)

```typescript
export const getStoryPromptDrafts = (id: string, screenplayRevisionId: string) => json<StoryPromptDraftState>(`/api/story/workspaces/${encodeURIComponent(id)}/prompt-drafts?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`);
```

### `saveStoryPromptDrafts`

[Source declaration](../frontend/src/lib/story-api.ts#L93)

```typescript
export const saveStoryPromptDrafts = (id: string, screenplayRevisionId: string, setup: ProductionSetup, drafts: Record<string, StoryPromptDraft>) => json<StoryPromptDraftState>(`/api/story/workspaces/${encodeURIComponent(id)}/prompt-drafts`, body({ screenplay_revision_id: screenplayRevisionId, setup, drafts }, 'PUT'));
```

### `saveStoryPromptShot`

[Source declaration](../frontend/src/lib/story-api.ts#L94)

```typescript
export const saveStoryPromptShot = (id: string, screenplayRevisionId: string, setup: ProductionSetup, shotKey: string, draft: StoryPromptDraft) => json<StoryPromptDraftState>(`/api/story/workspaces/${encodeURIComponent(id)}/prompt-drafts/shot`, body({ screenplay_revision_id: screenplayRevisionId, setup, shot_key: shotKey, draft }, 'PUT'));
```

### `prepareStoryPrompt`

[Source declaration](../frontend/src/lib/story-api.ts#L95)

```typescript
export const prepareStoryPrompt = (id: string, screenplayRevisionId: string, shotKey: string, workflowId: string) => json<PreparedStoryPrompt>(`/api/story/workspaces/${encodeURIComponent(id)}/prompt-drafts/prepare`, body({ screenplay_revision_id: screenplayRevisionId, shot_key: shotKey, workflow_id: workflowId }));
```

### `getAutomatedFirstClip`

[Source declaration](../frontend/src/lib/story-api.ts#L96)

```typescript
export const getAutomatedFirstClip = (id: string, screenplayRevisionId: string, signal?: AbortSignal) => json<AutomatedFirstClipState>(`/api/story/workspaces/${encodeURIComponent(id)}/automated-first-clip?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`, { signal });
```

### `startAutomatedFirstClip`

[Source declaration](../frontend/src/lib/story-api.ts#L97)

```typescript
export const startAutomatedFirstClip = (id: string, screenplayRevisionId: string) => json<AutomatedFirstClipState>(`/api/story/workspaces/${encodeURIComponent(id)}/automated-first-clip`, body({ screenplay_revision_id: screenplayRevisionId }));
```

### `retryAutomatedRunShot`

[Source declaration](../frontend/src/lib/story-api.ts#L98)

```typescript
export const retryAutomatedRunShot = (id: string, screenplayRevisionId: string, sceneNumber: number, shotNumber: number, clipNumber = 1) => json<{ status: string; job: import('./video-api').Job; run: AutomatedFirstClipState }>(`/api/story/workspaces/${encodeURIComponent(id)}/automated-run-retry`, body({ screenplay_revision_id: screenplayRevisionId, scene_number: sceneNumber, shot_number: shotNumber, clip_number: clipNumber }));
```

### `resumeAutomatedRun`

[Source declaration](../frontend/src/lib/story-api.ts#L99)

```typescript
export const resumeAutomatedRun = (id: string, screenplayRevisionId: string) => json<AutomatedFirstClipState>(`/api/story/workspaces/${encodeURIComponent(id)}/automated-run-resume`, body({ screenplay_revision_id: screenplayRevisionId }));
```

### `getAssistedVideoClipPlan`

[Source declaration](../frontend/src/lib/story-api.ts#L100)

```typescript
export const getAssistedVideoClipPlan = (id: string, screenplayRevisionId: string) => json<AssistedClipPlanState>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-video-clip-plan?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`);
```

### `prepareAssistedVideoClipPlan`

[Source declaration](../frontend/src/lib/story-api.ts#L101)

```typescript
export const prepareAssistedVideoClipPlan = (id: string, screenplayRevisionId: string, discard_references = false) => json<AssistedClipPlanState>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-video-clip-plan`, body({screenplay_revision_id: screenplayRevisionId, discard_references}));
```

### `saveAssistedVideoClipPrompt`

[Source declaration](../frontend/src/lib/story-api.ts#L102)

```typescript
export const saveAssistedVideoClipPrompt = (id: string, screenplayRevisionId: string, clipId: string, expectedPrompt: string, prompt: string) => json<AssistedClipPlanState>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-video-clip-prompt`, body({screenplay_revision_id: screenplayRevisionId, clip_id: clipId, expected_prompt: expectedPrompt, prompt}, 'PUT'));
```

### `saveAssistedVideoClipReferences`

[Source declaration](../frontend/src/lib/story-api.ts#L103)

```typescript
export const saveAssistedVideoClipReferences = (id: string, screenplayRevisionId: string, clips: AssistedVideoReferenceMap[]) => json<AssistedClipPlanState>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-video-clip-references`, body({screenplay_revision_id: screenplayRevisionId, clips}, 'PUT'));
```

### `getAssistedVideoRun`

[Source declaration](../frontend/src/lib/story-api.ts#L104)

```typescript
export const getAssistedVideoRun = (id: string, screenplayRevisionId: string) => json<AssistedVideoRunState>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-video-run?screenplay_revision_id=${encodeURIComponent(screenplayRevisionId)}`);
```

### `startAssistedVideoRun`

[Source declaration](../frontend/src/lib/story-api.ts#L105)

```typescript
export const startAssistedVideoRun = (id: string, screenplayRevisionId: string) => json<{status:string;job?:import('./video-api').Job;reason?:string}>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-video-run`, body({screenplay_revision_id:screenplayRevisionId}));
```

### `retryAssistedVideoClip`

[Source declaration](../frontend/src/lib/story-api.ts#L106)

```typescript
export const retryAssistedVideoClip = (id: string, screenplayRevisionId: string, clipId: string) => json<{status:string;job:import('./video-api').Job;run:AssistedVideoRunState}>(`/api/story/workspaces/${encodeURIComponent(id)}/assisted-video-run-retry`, body({screenplay_revision_id:screenplayRevisionId,clip_id:clipId}));
```

### `controlAutomatedRun`

[Source declaration](../frontend/src/lib/story-api.ts#L108)

```typescript
export const controlAutomatedRun = (workspaceId: string, revisionId: string, action: 'pause'|'resume'|'stop') => json<AutomatedFirstClipState>(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/automated-run-control`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({screenplay_revision_id:revisionId,action})});
```


## storyboard-api.ts

### `getBoard`

[Source declaration](../frontend/src/lib/storyboard-api.ts#L11)

```typescript
export const getBoard=(w:string,r:string)=>request<BoardState>(base(w,r));
```

### `saveBoard`

[Source declaration](../frontend/src/lib/storyboard-api.ts#L12)

```typescript
export const saveBoard=(state:BoardState,body:BoardBody)=>request<BoardState>(base(state.workspace_id,state.screenplay_revision_id),{expected_revision:state.revision,body},'PUT');
```

### `getConversation`

[Source declaration](../frontend/src/lib/storyboard-api.ts#L13)

```typescript
export const getConversation=(w:string,r:string)=>request<{items:Conversation[]}>(director(w,r,'conversation'));
```

### `chatScreenplay`

[Source declaration](../frontend/src/lib/storyboard-api.ts#L14)

```typescript
export const chatScreenplay=(w:string,r:string,instruction:string,key:string)=>request<Conversation>(director(w,r,'chat'),{instruction,idempotency_key:key});
```

### `proposeScreenplay`

[Source declaration](../frontend/src/lib/storyboard-api.ts#L15)

```typescript
export const proposeScreenplay=(w:string,r:string,instruction:string,key:string)=>request<Conversation['proposal']>(director(w,r,'propose'),{instruction,idempotency_key:key});
```

### `applyScreenplay`

[Source declaration](../frontend/src/lib/storyboard-api.ts#L16)

```typescript
export const applyScreenplay=(w:string,r:string,key:string,selected:number[],idempotency_key:string)=>request<ScreenplayRevision>(director(w,r,'apply'),{request_key:key,selected,idempotency_key});
```


## styles-api.ts

### `getStyleCatalog`

[Source declaration](../frontend/src/lib/styles-api.ts#L50)

```typescript
export const getStyleCatalog = () => json<StyleCatalog & { directing_styles:DirectingStyle[] }>('/api/styles/catalog');
```

### `getStyleSelections`

[Source declaration](../frontend/src/lib/styles-api.ts#L51)

```typescript
export const getStyleSelections = (context: string, workspace_id?: string) => json<{ selections: StyleSelection[] }>(`/api/styles/selections?${workspace_id ? `workspace_id=${encodeURIComponent(workspace_id)}` : `isolated_context_id=${encodeURIComponent(context)}`}`);
```

### `saveStyleSelection`

[Source declaration](../frontend/src/lib/styles-api.ts#L52)

```typescript
export const saveStyleSelection = (isolated_context_id: string, production_type: string, style_version_id: string, directing_style_id:string, directing_style_version_id?:string, workspace_id?: string) => json<StyleSelection>('/api/styles/selections', post({ ...(workspace_id ? { workspace_id } : { isolated_context_id }), production_type, style_version_id, directing_style_id, directing_style_version_id }));
```

### `publishProductionType`

[Source declaration](../frontend/src/lib/styles-api.ts#L53)

```typescript
export const publishProductionType = async (production_type: string, narrative_guidance: Record<string, string>, director_profile: DirectorProfile): Promise<ProductionStyle> => {
```

### `publishDirectingStyle`

[Source declaration](../frontend/src/lib/styles-api.ts#L58)

```typescript
export const publishDirectingStyle = (isolated_context_id:string, style_id:string, display_name:string, guidance:string, evidence:DirectingStyleEvidence[], scope_type:'cross_type'|'production_type'='cross_type', production_type_scope?:string) => json<DirectingStyle>('/api/styles/directing-styles', post({isolated_context_id, style_id, display_name, guidance, evidence, scope_type, production_type_scope}));
```

### `listStyleSources`

[Source declaration](../frontend/src/lib/styles-api.ts#L59)

```typescript
export const listStyleSources = (context:string) => json<{sources:StyleSource[]}>(`/api/styles/sources?isolated_context_id=${encodeURIComponent(context)}`);
```

### `getStyleSource`

[Source declaration](../frontend/src/lib/styles-api.ts#L60)

```typescript
export const getStyleSource = (context:string, sourceId:string) => json<StyleSource>(`/api/styles/sources/${encodeURIComponent(sourceId)}?isolated_context_id=${encodeURIComponent(context)}`);
```

### `analyzeStyleSources`

[Source declaration](../frontend/src/lib/styles-api.ts#L61)

```typescript
export const analyzeStyleSources = (context:string, source_ids:string[], user_intent:string) => json<StyleProposal>('/api/styles/sources/analyze',post({isolated_context_id:context,source_ids,user_intent}));
```

### `analyzeStyleImages`

[Source declaration](../frontend/src/lib/styles-api.ts#L62)

```typescript
export const analyzeStyleImages = (context:string, asset_ids:string[], user_intent:string) => json<ImageStyleProposal>('/api/styles/media/analyze',post({isolated_context_id:context,asset_ids,user_intent}));
```

### `uploadStyleSource`

[Source declaration](../frontend/src/lib/styles-api.ts#L63)

```typescript
export async function uploadStyleSource(context:string, file:File):Promise<StyleSource> {
```


## video-api.ts

### `getCapability`

[Source declaration](../frontend/src/lib/video-api.ts#L38)

```typescript
export function getCapability(workflowId = WORKFLOW_ID, signal?: AbortSignal) { return api<Capability>(`/api/video/capabilities?workflow_id=${encodeURIComponent(workflowId)}`, { signal }); }
```

### `validateRequest`

[Source declaration](../frontend/src/lib/video-api.ts#L39)

```typescript
export function validateRequest(request: VideoRequest) { return api<any>('/api/video/validations', { method: 'POST', body: JSON.stringify({ request }) }); }
```

### `createJob`

[Source declaration](../frontend/src/lib/video-api.ts#L40)

```typescript
export function createJob(workspaceId: string, clipId: string, idempotencyKey: string, request: VideoRequest, retake?: { retake_of_job_id: string; keep_original: boolean }, sourceLineage?: Pick<StoryVideoLineage, 'screenplay_revision_id'|'setup_hash'|'scene_number'|'shot_number'|'source_prompt_sha256'|'knowledge_ref'|'style_ref'|'planned_clip_id'|'board_revision'>) {
```

### `getJob`

[Source declaration](../frontend/src/lib/video-api.ts#L43)

```typescript
export function getJob(jobId: string) { return api<Job>(`/api/video/jobs/${encodeURIComponent(jobId)}`); }
```

### `listJobs`

[Source declaration](../frontend/src/lib/video-api.ts#L44)

```typescript
export function listJobs(workspaceId: string, limit = 200, offset = 0) {
```

### `listAllJobs`

[Source declaration](../frontend/src/lib/video-api.ts#L47)

```typescript
export async function listAllJobs(workspaceId: string) {
```

### `prepareRetake`

[Source declaration](../frontend/src/lib/video-api.ts#L55)

```typescript
export function prepareRetake(jobId: string, keepOriginal: boolean) { return api<any>(`/api/video/retakes/${encodeURIComponent(jobId)}`, { method: 'POST', body: JSON.stringify({ keep_original: keepOriginal }) }); }
```

### `acceptJob`

[Source declaration](../frontend/src/lib/video-api.ts#L56)

```typescript
export function acceptJob(jobId: string) { return api<Job>(`/api/video/jobs/${encodeURIComponent(jobId)}/accept`, { method: 'POST', body: JSON.stringify({}) }); }
```

### `findJobByIdempotency`

[Source declaration](../frontend/src/lib/video-api.ts#L57)

```typescript
export function findJobByIdempotency(workspaceId: string, idempotencyKey: string) {
```

### `releaseVideoAttempt`

[Source declaration](../frontend/src/lib/video-api.ts#L60)

```typescript
export function releaseVideoAttempt(workspaceId: string, idempotencyKey: string) {
```

### `prepareContinuityFrame`

[Source declaration](../frontend/src/lib/video-api.ts#L64)

```typescript
export function prepareContinuityFrame(jobId: string) { return api<{asset_id:string;sha256:string;role:string;intent:string;character_crops?:{character_id:string;asset_id:string;sha256:string}[]}>(`/api/video/jobs/${encodeURIComponent(jobId)}/continuity-frame`, {method:"POST",body:"{}"}); }
```

### `validateT2VBatch`

[Source declaration](../frontend/src/lib/video-api.ts#L68)

```typescript
export const validateT2VBatch = (source:string,workspaceId:string) => api<{entries:T2VBatchEntry[];count:number;conflicts:string[]}>('/api/video/batches/validate', {method:'POST',body:JSON.stringify({source,workspace_id:workspaceId})});
```

### `listT2VBatches`

[Source declaration](../frontend/src/lib/video-api.ts#L69)

```typescript
export const listT2VBatches = (workspaceId:string) => api<{batches:T2VBatch[]}>(`/api/video/batches?workspace_id=${encodeURIComponent(workspaceId)}`);
```

### `createT2VBatch`

[Source declaration](../frontend/src/lib/video-api.ts#L70)

```typescript
export const createT2VBatch = (workspaceId:string,idempotencyKey:string,source:string,choices:Record<string,'overwrite'|'new_take'>={}) => api<T2VBatch>('/api/video/batches', {method:'POST',body:JSON.stringify({workspace_id:workspaceId,idempotency_key:idempotencyKey,source,choices})});
```

### `controlT2VBatch`

[Source declaration](../frontend/src/lib/video-api.ts#L71)

```typescript
export const controlT2VBatch = (id:string,action:'pause'|'resume'|'stop') => api<T2VBatch>(`/api/video/batches/${id}/control`, {method:'POST',body:JSON.stringify({action})});
```

