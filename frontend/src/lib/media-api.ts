export type MediaAsset = {
  origin?: 'imported'|'generated';
  catalogue_source?: string;
  asset_id: string; workspace_id: string; kind: 'image'|'video'|'audio'; roles: string[];
  filename: string; media_type: string; sha256: string; size_bytes: number;
  content_url: string; provenance_notes?: string; created_at: string;
  recommended?: boolean; recommendation_source?: 'production_style'; source_workspace_id?: string;
  catalog_only?: boolean;
  archived_at?: string;
  description?: string; tags?: string[]; audio_category?: 'voice'|'sfx'|'music'|'dialogue';
  semantic_annotation_index?: {source:string;source_sha256:string;annotation_sha256:string;model:string;dimension:number};
  semantic_content_index?: {source:'audio_content'|'video_content'|'image_visual_content';source_sha256:string;model:string;dimension:number};
  metadata?: { analysis_summary?: string; sam_audio?: {run_id?:string}; analyzer_run_id?: string; scene_id?: string; frame_id?: string; timestamp_seconds?: number; source_asset_id?: string; source_asset_name?: string; timestamp_start_seconds?: number; timestamp_end_seconds?: number; style_frame_sources?: Array<{parent_video_asset_id: string; parent_video_sha256: string; source_width?: number; source_height?: number; timestamp_seconds: number; style_version_id?: string; directing_style_id?: string; extraction: {method: string; max_width: number; quality: number}}> ; production_image_job?: { intended_role?: string; world_view?: {label:string;azimuth:number}; settings?: { lineage?: {
    target_name?: string; target_record_id?: string; target_type?: string;
    screenplay_revision_id?: string; scene_number?: number; shot_number?: number; clip_id?: string;
    } } }; comfyui_voice_catalog?: {catalog_id:string;name:string}; style_version_ids?: string[]; directing_style_ids?: string[]; image_analyses?: Array<{job_id:string;source_sha256:string;mode:'quick'|'balanced'|'deep';saved_at:string;analysis:Record<string,unknown>}> };
  media?: {width?: number; height?: number; duration_seconds?: number};
};

export type MediaSeoStyle = {
  style_id: string;
  name: string;
  weighted_terms: Array<{term: string; weight: number}>;
  avoid_terms: string[];
  created_at: string;
};

export type AudioVoice = {id:string;name:string;source:string;relative_path:string;has_transcript:boolean;discoverable:boolean;user_managed:boolean;content_url:string;created_at:string;size_bytes:number};
export type AudioVoiceRefresh = {refreshed:boolean;live_count:number;catalog_count:number;discovered_voice_ids:string[];expected_voice_id?:string|null;expected_discovered?:boolean|null;restart_required:boolean};
export type AudioModel = {id:string;family:string;name:string;artifact_count:number;finetune_status:string;aarch64_status:string;one_shot_reference:boolean};
export type AudioCapabilities = {comfyui_url:string;comfyui_online:boolean;comfyui_root_exists:boolean;tts_suite_exists:boolean;timed_tts_workflow_exists:boolean;voice_enrollment:boolean;voice_catalog_is_read_only:boolean;f5_dataset_preparation?:{preparation_ready:boolean;training_enabled:false;python:string;message:string;checks:Array<{name:string;ok:boolean;detail:string}>;base_models:Array<{id:string;available:boolean;checkpoint:string}>}};
export type F5PreparationJob = {job_id:string;status:string;progress:number;stage:string;message:string;result?:{dataset_name?:string;training_enabled?:false;command_blockers?:string[]}|null;error?:string|null};
export const listF5PreparationJobs = (workspaceId:string) => request<F5PreparationJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/finetune/f5/jobs`);
export const getF5PreparationJob = (workspaceId:string,jobId:string) => request<F5PreparationJob>(`/api/audio/${encodeURIComponent(workspaceId)}/finetune/f5/jobs/${encodeURIComponent(jobId)}`);
export const createF5PreparationJob = (workspaceId:string,payload:{dataset_name:string;base_model:string;samples:Array<{asset_id:string;text:string}>}) => request<F5PreparationJob>(`/api/audio/${encodeURIComponent(workspaceId)}/finetune/f5/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});

export type ReconstructionCharacter = {character_id:string;name:string;calibration_sentence?:string;voice_settings?:Record<string,unknown>;status:string;updated_at?:string};
export type ReconstructionPart = {part_id:string;character_name:string;sequence:number;expected_text:string;accepted_take_id?:string|null;accepted_path?:string};
export type ReconstructionTake = {take_id:string;part_id:string;sequence:number;character_name:string;raw_path:string;transcript:string;status:string;created_at:string};
export type ReconstructionSession = {version:number;characters:ReconstructionCharacter[];parts:ReconstructionPart[];takes:ReconstructionTake[];updated_at:string};

export type VideoAnalysisJob = {
  job_id: string; status: 'queued'|'running'|'completed'|'failed'|'interrupted'|'cancelled'|'cancel_requested';
  progress: number; stage: string; message: string; created_at: string; updated_at: string;
  request: {workspace_id: string; source_asset_ids?: string[]; settings?: Record<string, unknown>; urls?: YoutubeCandidate[]; source_mode?: string};
  events: Array<{timestamp: string; stage: string; status: string; message: string; payload?: Record<string, unknown>}>;
  result?: {assets?: Array<Record<string, unknown>>; videos?: Array<{title?: string; summary?: {detailed_video_summary?: string; brief_video_summary?: string}; scenes?: Array<{scene_id:string;start_time_sec:number;end_time_sec:number;summary?:string;transcript?:string}>}>; audio_analysis?: Array<{asset_id:string;status:string;run_id?:string;statuses?:Record<string,string>;media_collection?:{limitations?:Record<string,string>};audio_events?: Array<{event_id:string;event_type?:string;label?:string;confidence?:number;start_time_sec:number;end_time_sec:number}>;summary?:string}>; published_assets?: MediaAsset[]; failures?: Array<{url:string;error:string}>; errors?: string[]; gpu_usage?: {available:boolean;peak_mib?:number;peak_delta_mib?:number}} | null;
  error?: string | null;
};

export type YoutubeCandidate = {url: string; video_id?: string; title?: string; channel?: string};
export type StagedDonorVideo = {asset_id:string;filename:string;title:string;channel:string;created_at:string;size_bytes:number;importable:boolean;sha256:string;source_mode:string;source_url:string};
export type StagedDonorAnalysis = {video_asset_id:string;analysis:null|{analysis_id:string;run_id:string;model:string;revision:string;summary:string};audio_assets:Array<{asset_id:string;category:'voice'|'dialogue'|'sfx'|'music';label:string;filename:string;start_time_sec:number|null;end_time_sec:number|null;size_bytes:number;sha256:string}>};

export function listStagedDonorVideos(workspaceId:string) {
  return request<StagedDonorVideo[]>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/library/donor`);
}

export function importStagedDonorVideos(workspaceId:string, assetIds:string[]) {
  return request<{assets:MediaAsset[]}>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/library/donor/import`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({asset_ids:assetIds}),
  });
}

export function getStagedDonorAnalysis(workspaceId:string, assetId:string) {
  return request<StagedDonorAnalysis>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/library/donor/${encodeURIComponent(assetId)}/analysis`);
}

export function importStagedDonorAnalysisAudio(workspaceId:string, assetId:string, audioAssetIds:string[]) {
  return request<{assets:MediaAsset[]}>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/library/donor/${encodeURIComponent(assetId)}/analysis/import`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({asset_ids:audioAssetIds}),
  });
}

export type ImageDetailerJob = {
  job_id: string; status: 'queued'|'running'|'completed'|'failed'|'interrupted'|'cancelled'|'cancel_requested';
  progress: number; stage: string; message: string; created_at: string; updated_at: string;
  request: {workspace_id: string; asset_id: string; sha256: string; mode: 'quick'|'balanced'|'deep'};
  events: Array<{timestamp: string; stage: string; status: string; message: string}>;
  result?: {asset_id: string; filename: string; sha256: string; mode: string; analysis: {
    input?: {filename?: string; width?: number; height?: number}; model?: string;
    specialist_evidence?: {detections?: unknown[]}; warnings?: string[];
    analysis?: Record<string, any>; frame_card?: Record<string, any>; [key: string]: any;
  }} | null;
  error?: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.error?.message || `Media request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export function listMediaAssets(workspaceId: string, kind: string, includeArchived = false, styleContextId = '') {
  const archived = includeArchived ? '&include_archived=true' : '';
  const styleContext = styleContextId ? `&style_context_id=${encodeURIComponent(styleContextId)}` : '';
  return request<{assets: MediaAsset[]; total: number}>(`/api/media/${encodeURIComponent(workspaceId)}/assets?kind=${encodeURIComponent(kind)}${archived}${styleContext}`).then(async first => {
    const assets = [...first.assets];
    while (assets.length < first.total) {
      const page = await request<{assets: MediaAsset[]; total: number}>(`/api/media/${encodeURIComponent(workspaceId)}/assets?kind=${encodeURIComponent(kind)}&limit=100&offset=${assets.length}${archived}${styleContext}`);
      if (!page.assets.length) break;
      assets.push(...page.assets);
    }
    return { assets, total: first.total };
  });
}

export function setMediaAssetArchived(workspaceId:string,assetId:string,archived:boolean) {
  return request<{asset:MediaAsset}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/${archived?'archive':'restore'}`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
}

export function searchMediaSemantically(workspaceId: string, kind: string, query: string) {
  const params = new URLSearchParams({q: query, kind, limit: '50'});
  return request<{results: Array<{asset: MediaAsset; score: number; text: string}>; reason?: string; query_backend?: string}>(
    `/api/media/${encodeURIComponent(workspaceId)}/assets/search?${params.toString()}`);
}

export function listVideoAnalysisJobs(workspaceId: string) {
  return request<VideoAnalysisJob[]>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/analysis/jobs`);
}

export function getVideoAnalysisJob(workspaceId: string, jobId: string) {
  return request<VideoAnalysisJob>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/analysis/jobs/${encodeURIComponent(jobId)}`);
}

export function startVideoAnalysis(workspaceId: string, assetIds: string[], settings: Record<string, unknown> = {}) {
  return request<VideoAnalysisJob>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/analysis/jobs`, {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({asset_ids: assetIds, settings}),
  });
}

export function cancelVideoAnalysis(workspaceId: string, jobId: string) {
  return request<VideoAnalysisJob>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/analysis/jobs/${encodeURIComponent(jobId)}/cancel`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
}

export function deleteVideoAnalysis(workspaceId: string, jobId: string) {
  return request<{deleted:boolean}>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/analysis/jobs/${encodeURIComponent(jobId)}`, {method:'DELETE'});
}

export function retryVideoAnalysis(workspaceId: string, jobId: string) {
  return request<VideoAnalysisJob>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/analysis/jobs/${encodeURIComponent(jobId)}/retry`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
}

export type SamAudioPreview = {status:string;temporary_id?:string;model?:string;prompt?:string;audio_url?:string;reason?:string;readiness?:Record<string,unknown>};
export type SamAudioCapability = {available:boolean;status:string;model?:string;checkpoint_present:boolean;worker_configured:boolean;authentication_configured:boolean;reason?:string|null};
export function getSamAudioCapability() {
  return request<SamAudioCapability>('/api/video-summariser/sam/capabilities');
}
export function isolateVideoAudioEvent(workspaceId:string,runId:string,eventId:string,prompt:string) {
  return request<SamAudioPreview>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/analysis/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(eventId)}/isolate`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt}),
  });
}
export function saveSamAudioPreview(workspaceId:string,temporaryId:string) {
  return request<{status:string;asset?:MediaAsset;director_review?:Record<string,unknown>}>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/sam/previews/${encodeURIComponent(temporaryId)}/save`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:'{}',
  });
}
export function discardSamAudioPreview(workspaceId:string,temporaryId:string) {
  return request<{status:string}>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/sam/previews/${encodeURIComponent(temporaryId)}`,{method:'DELETE'});
}

export function listImageDetailerJobs(workspaceId: string) {
  return request<ImageDetailerJob[]>(`/api/image-detailer/${encodeURIComponent(workspaceId)}/jobs`);
}

export function getImageDetailerJob(workspaceId: string, jobId: string) {
  return request<ImageDetailerJob>(`/api/image-detailer/${encodeURIComponent(workspaceId)}/jobs/${encodeURIComponent(jobId)}`);
}

export function startImageDetailerJob(workspaceId: string, assetId: string, mode: 'quick'|'balanced'|'deep') {
  return request<ImageDetailerJob>(`/api/image-detailer/${encodeURIComponent(workspaceId)}/jobs`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({asset_id:assetId,mode}),
  });
}

export function cancelImageDetailerJob(workspaceId: string, jobId: string) {
  return request<ImageDetailerJob>(`/api/image-detailer/${encodeURIComponent(workspaceId)}/jobs/${encodeURIComponent(jobId)}/cancel`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
}

export function retryImageDetailerJob(workspaceId: string, jobId: string) {
  return request<ImageDetailerJob>(`/api/image-detailer/${encodeURIComponent(workspaceId)}/jobs/${encodeURIComponent(jobId)}/retry`, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
}

export function resolveYoutubeSources(workspaceId: string, value: {mode:'search'|'paste'; query?:string; count?:number; urls_text?:string}) {
  return request<{source_mode:string;query:string;candidates:YoutubeCandidate[]}>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/youtube/sources`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(value),
  });
}

export function listYoutubeJobs(workspaceId: string) {
  return request<VideoAnalysisJob[]>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/youtube/jobs`);
}

export function getYoutubeJob(workspaceId: string, jobId: string) {
  return request<VideoAnalysisJob>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/youtube/jobs/${encodeURIComponent(jobId)}`);
}

export function startYoutubeDownload(workspaceId: string, urls: YoutubeCandidate[], sourceMode: string) {
  return request<VideoAnalysisJob>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/youtube/jobs`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({urls,source_mode:sourceMode}),
  });
}

export function cancelYoutubeJob(workspaceId: string, jobId: string) {
  return request<VideoAnalysisJob>(`/api/video-summariser/${encodeURIComponent(workspaceId)}/youtube/jobs/${encodeURIComponent(jobId)}/cancel`, {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
}

export function uploadMediaAsset(workspaceId: string, file: File, role: string, storage: 'workspace' | 'recording' = 'workspace') {
  return request<MediaAsset & {deduplicated: boolean}>(`/api/media/${encodeURIComponent(workspaceId)}/assets?filename=${encodeURIComponent(file.name)}&role=${encodeURIComponent(role)}&storage=${storage}`, {
    method: 'POST', headers: {'Content-Type':'application/octet-stream'}, body: file,
  });
}

export function linkMediaAssetToStyle(workspaceId: string, assetId: string, directingStyleId: string) {
  return request<MediaAsset>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/style-reference`, {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({directing_style_id: directingStyleId}),
  });
}

export function extractMediaStyleFrames(workspaceId: string, assetId: string, directingStyleId: string, timestampsSeconds: number[]) {
  return request<StyleFrameJob>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/style-frames`, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({directing_style_id: directingStyleId, timestamps_seconds: timestampsSeconds}),
  });
}

export type StyleFrameJob = {job_id:string;status:'queued'|'running'|'completed'|'failed'|'interrupted'|'cancelled'|'cancel_requested';progress:number;stage:string;message:string;request:{workspace_id:string;asset_id:string;timestamps_seconds:number[]};result?:{frames:MediaAsset[]}|null;error?:string|null};
export const getStyleFrameJob = (workspaceId:string,jobId:string) => request<StyleFrameJob>(`/api/media/${encodeURIComponent(workspaceId)}/style-frame-jobs/${encodeURIComponent(jobId)}`);
export const cancelStyleFrameJob = (workspaceId:string,jobId:string) => request<StyleFrameJob>(`/api/media/${encodeURIComponent(workspaceId)}/style-frame-jobs/${encodeURIComponent(jobId)}/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});

export function updateMediaAnnotations(workspaceId: string, assetId: string, value: {
  description: string; tags: string[]; audio_category: 'voice'|'sfx'|'music'|'dialogue'|null;
}) {
  return request<MediaAsset>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/annotations`, {
    method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify(value),
  });
}

export function indexMediaAssetAnnotations(workspaceId: string, assetId: string) {
  return request<{asset:MediaAsset;indexed:boolean;source:string}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/semantic-index`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:'{}',
  });
}

export type SemanticIndexJob = {job_id:string;kind:'semantic-index';status:'queued'|'running'|'completed'|'failed'|'interrupted'|'cancelled'|'cancel_requested';progress:number;stage:string;message:string;request:{workspace_id:string;asset_id:string;modality:'audio'|'video'|'image'};result?:{dimension?:number;model?:string}|null;error?:string|null};
export const createMediaContentIndexJob = (workspaceId:string, assetId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/semantic-content-index`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
export const getMediaContentIndexJob = (workspaceId:string, jobId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs/${encodeURIComponent(jobId)}`);
export const listMediaContentIndexJobs = (workspaceId:string) => request<SemanticIndexJob[]>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs`);
export const retryMediaContentIndexJob = (workspaceId:string, jobId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs/${encodeURIComponent(jobId)}/retry`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
export const cancelMediaContentIndexJob = (workspaceId:string, jobId:string) => request<SemanticIndexJob>(`/api/media/${encodeURIComponent(workspaceId)}/semantic-index-jobs/${encodeURIComponent(jobId)}/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});

export function saveImageAnalysis(workspaceId: string, assetId: string, value: {
  job_id: string; source_sha256: string; mode: 'quick'|'balanced'|'deep';
  analysis: Record<string, unknown>; description: string; tags: string[];
}) {
  return request<MediaAsset>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/analysis`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(value),
  });
}

export function listAudioVoices() { return request<AudioVoice[]>('/api/audio/voices'); }
export function importComfyVoiceToWorkspace(workspaceId:string,voiceId:string) {
  return request<{asset:MediaAsset}>(`/api/audio/${encodeURIComponent(workspaceId)}/voice-library/import`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({voice_id:voiceId}),
  });
}
export function listAudioModels() { return request<AudioModel[]>('/api/audio/models'); }
export function getAudioCapabilities() { return request<AudioCapabilities>('/api/audio/capabilities'); }
export function refreshAudioVoices(expectedVoiceId?:string) {
  return request<AudioVoiceRefresh>('/api/audio/voices/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_voice_id:expectedVoiceId||null})});
}
export type MusicCapabilities = {ace_step:{comfyui_online:boolean;ace:{status:string;checkpoint:string;checkpoint_size:number;reason?:string};finetune:{status:string;smoke_ready:boolean;full_training_enabled:boolean;checks:Array<{name:string;ok:boolean;detail:string}>}};control_foley:{status:string;comfyui_online:boolean;model_ready:boolean;workflow_ready:boolean;reason?:string;missing_nodes:string[];schema:{modes:Array<{id:string;label:string;requires:string[];properties:Record<string,unknown>}>}};workflow_files:{ace_step:boolean;control_foley:boolean}};
export type WorkflowGuidance = {knowledge_id?:string;workflow_id:string;model_id:string;workflow_version?:string;guidance_version:number|null;workflow_sha256?:string;retrieval_status:'matched'|'not_curated';sources:Array<{source_id:string;uri:string;version:string;section:string;sha256?:string}>;nodes:Array<{node_id:string;kind:string;text:string;source_ids:string[]}>;edges:Array<{from:string;relation:string;to:string}>};
export type PromptKnowledgeRef = {knowledge_id:string;guidance_version:number;workflow_sha256:string};
export type MusicJob = {job_id:string;status:string;progress:number;stage:string;message:string;result?:{asset?:MediaAsset;error?:string}|null;error?:string|null};
export type AudioUtilityOperation = {id:'simple'|'noise_cleanup'|'extract_mp3'|'demucs_stems';status:'available'|'blocked'|'pinned';runtime:string;reason?:string|null};
export type AudioUtilityCapabilities = {operations:AudioUtilityOperation[]};
export type AudioUtilityJob = {job_id:string;status:string;progress:number;stage:string;message:string;created_at:string;updated_at:string;result?:{workspace_id:string;assets:MediaAsset[]}|null;error?:string|null};
export const getAudioUtilityCapabilities = () => request<AudioUtilityCapabilities>('/api/audio/utilities/capabilities');
export const listAudioUtilityJobs = (workspaceId:string) => request<AudioUtilityJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/utilities/jobs`);
export const getAudioUtilityJob = (workspaceId:string,jobId:string) => request<AudioUtilityJob>(`/api/audio/${encodeURIComponent(workspaceId)}/utilities/jobs/${encodeURIComponent(jobId)}`);
export const createAudioUtilityJob = (workspaceId:string,operation:AudioUtilityOperation['id'],asset_ids:string[],settings:Record<string,unknown>={}) => request<AudioUtilityJob>(`/api/audio/${encodeURIComponent(workspaceId)}/utilities/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,asset_ids,settings})});
export const getMusicCapabilities = () => request<MusicCapabilities>('/api/audio/music/capabilities');
export const getWorkflowGuidance = (workflowId:string,modelId:string) => {
  const query=new URLSearchParams({workflow_id:workflowId,model_id:modelId});
  return request<WorkflowGuidance>(`/api/workflow-guidance?${query.toString()}`);
};
export const listMusicJobs = (workspaceId:string,kind:'ace-music'|'control-foley') => request<MusicJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/${kind==='ace-music'?'music':'control-foley'}/jobs`);
export const createMusicJob = (workspaceId:string,kind:'ace-music'|'control-foley',settings:Record<string,unknown>,references:PromptKnowledgeRef,mediaReferences?:{video_asset_id?:string;audio_asset_id?:string}) => request<MusicJob>(`/api/audio/${encodeURIComponent(workspaceId)}/${kind==='ace-music'?'music':'control-foley'}/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({settings,prompt_knowledge_ref:references,...(mediaReferences?{references:mediaReferences}:{})})});
export const getMusicJob = (workspaceId:string,kind:'ace-music'|'control-foley',jobId:string) => request<MusicJob>(`/api/audio/${encodeURIComponent(workspaceId)}/${kind==='ace-music'?'music':'control-foley'}/jobs/${encodeURIComponent(jobId)}`);
export function enrollAudioVoice(workspaceId:string,assetId:string,name:string,transcript:string) {
  return request<{voice:AudioVoice|null;asset:MediaAsset;live_discovery:{refreshed:boolean;restart_required:boolean;error?:string};restart_required:boolean}>(`/api/audio/${encodeURIComponent(workspaceId)}/voices`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_id:assetId,name,transcript}),
  });
}

export const getReconstructionSession = (workspaceId:string) => request<ReconstructionSession>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct`);
export const saveReconstructionCalibration = (workspaceId:string,character_name:string,sentence:string) => request<ReconstructionSession>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/calibration`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({character_name,sentence,settings:{}})});
export const createReconstructionPart = (workspaceId:string,payload:{part_id:string;character_name:string;sequence:number;expected_text:string}) => request<ReconstructionPart>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/parts`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
export const addReconstructionTake = (workspaceId:string,partId:string,asset_id:string,transcript:string) => request<ReconstructionTake>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/parts/${encodeURIComponent(partId)}/takes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_id,transcript})});
export const acceptReconstructionTake = (workspaceId:string,partId:string,takeId:string) => request<{part:ReconstructionPart;take:ReconstructionTake;session:ReconstructionSession;asset:MediaAsset}>(`/api/audio/${encodeURIComponent(workspaceId)}/reconstruct/parts/${encodeURIComponent(partId)}/accept/${encodeURIComponent(takeId)}`,{method:'POST'});

export interface TimedTTSJob {
  job_id:string; status:string; progress:number; stage:string; message:string;
  events:Array<{timestamp:string;stage:string;status:string;message:string}>;
  result?:{asset?:MediaAsset;reports?:Record<string,string>}|null; error?:string|null;
}
export type AudioEffectOperation = {id:'simple'|'noise_cleanup'|'voice_repair'|'voice_changer'|'rvc'|'emotion'|'style';label:string;workflow_exists:boolean;requires_live_validation:boolean};
export type AudioEffectCapabilities = {operations:AudioEffectOperation[];rvc_models:Array<{id:string;name:string;indexes:string[]}>};
export type AudioEffectJob = {job_id:string;status:string;progress:number;stage:string;message:string;events:Array<{timestamp:string;stage:string;status:string;message:string}>;result?:{asset?:MediaAsset;operation?:string;source_info?:Record<string,number>}|null;error?:string|null};
export const getAudioEffectCapabilities = () => request<AudioEffectCapabilities>('/api/audio/effects/capabilities');
export const listAudioEffectJobs = (workspaceId:string) => request<AudioEffectJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/effects/jobs`);
export const getAudioEffectJob = (workspaceId:string,jobId:string) => request<AudioEffectJob>(`/api/audio/${encodeURIComponent(workspaceId)}/effects/jobs/${encodeURIComponent(jobId)}`);
export const createAudioEffectJob = (workspaceId:string,operation:AudioEffectOperation['id'],asset_id:string,settings:Record<string,unknown>={}) => request<AudioEffectJob>(`/api/audio/${encodeURIComponent(workspaceId)}/effects/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,asset_id,settings})});

export type AudioSceneClip = {clip_index:number;start:number;end:number;duration:number;kind?:string;text?:string;relative_path?:string;split_file?:string};
export type AudioSceneCapabilities = {available:boolean;checks:Record<'split'|'simple_stitch'|'timed_stitch',{path:string;available:boolean}>};
export type AudioSceneJob = {job_id:string;status:string;progress:number;stage:string;message:string;error?:string|null;result?:{manifest?:{clips:AudioSceneClip[]};clips?:Array<{clip_index:number;asset:MediaAsset}>;output_path?:string;asset?:MediaAsset}|null};
export const getAudioSceneCapabilities = () => request<AudioSceneCapabilities>('/api/audio/scene-surgery/capabilities');
export const createAudioSceneSplit = (workspaceId:string,asset_id:string,edits:Array<{start:number;end:number;text?:string}>,transcript?:string) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_id,edits,transcript})});
export const listAudioSceneSplits = (workspaceId:string) => request<AudioSceneJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/jobs`);
export const getAudioSceneSplit = (workspaceId:string,jobId:string) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/jobs/${encodeURIComponent(jobId)}`);
export const createAudioSceneStitch = (workspaceId:string,split_job_id:string,mode:'simple'|'timed',replacement_asset_ids:Record<number,string>,gaps:Record<number,number>) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/stitch-jobs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({split_job_id,mode,replacement_asset_ids,gaps})});
export const listAudioSceneStitches = (workspaceId:string) => request<AudioSceneJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/stitch-jobs`);
export const getAudioSceneStitch = (workspaceId:string,jobId:string) => request<AudioSceneJob>(`/api/audio/${encodeURIComponent(workspaceId)}/scene-surgery/stitch-jobs/${encodeURIComponent(jobId)}`);
export function listTimedTTSJobs(workspaceId:string) {
  return request<TimedTTSJob[]>(`/api/audio/${encodeURIComponent(workspaceId)}/timed-tts/jobs`);
}
export function createTimedTTSJob(workspaceId:string,payload:{srt_content:string;characters:Array<{name:string;reference_voice_id:string;language:string}>;settings:Record<string,unknown>}) {
  return request<TimedTTSJob>(`/api/audio/${encodeURIComponent(workspaceId)}/timed-tts/jobs`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
}
export function getTimedTTSJob(workspaceId:string,jobId:string) {
  return request<TimedTTSJob>(`/api/audio/${encodeURIComponent(workspaceId)}/timed-tts/jobs/${encodeURIComponent(jobId)}`);
}

export function listMediaSeoStyles(workspaceId: string) {
  return request<{styles: MediaSeoStyle[]}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/seo-styles`);
}

export function saveMediaSeoStyle(workspaceId: string, value: Omit<MediaSeoStyle, 'style_id'|'created_at'>, styleId?: string) {
  return request<MediaSeoStyle>(`/api/media/${encodeURIComponent(workspaceId)}/assets/seo-styles${styleId ? `/${encodeURIComponent(styleId)}` : ''}`, {
    method: styleId ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({name: value.name, weighted_terms: Object.fromEntries(value.weighted_terms.map(row => [row.term, row.weight])), avoid_terms: value.avoid_terms}),
  });
}

export function deleteMediaSeoStyle(workspaceId: string, styleId: string) {
  return request<{deleted: boolean; style_id: string}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/seo-styles/${encodeURIComponent(styleId)}`, {method:'DELETE'});
}

export function rankMediaAssets(assets: MediaAsset[], query: string, order: 'newest'|'oldest', style?: MediaSeoStyle) {
  const needle = query.trim().toLowerCase();
  return assets.filter(asset => !needle || [asset.filename, asset.description, asset.provenance_notes, ...(asset.roles || []), ...(asset.tags || [])]
    .filter(Boolean).join(' ').toLowerCase().includes(needle)).sort((a,b) => {
      if (a.recommended !== b.recommended) return a.recommended ? -1 : 1;
      if (style) {
        const score = (asset: MediaAsset) => {
          const text = [asset.filename, asset.description, asset.provenance_notes, ...(asset.roles || []), ...(asset.tags || [])].filter(Boolean).join(' ').toLowerCase();
          return style.weighted_terms.reduce((sum, row) => sum + (text.includes(row.term.toLowerCase()) ? row.weight : 0), 0)
            - style.avoid_terms.reduce((sum, term) => sum + (text.includes(term.toLowerCase()) ? 1 : 0), 0);
        };
        const difference = score(b) - score(a);
        if (difference) return difference;
      }
      const createdAtA = a.created_at || '';
      const createdAtB = b.created_at || '';
      return order === 'newest' ? createdAtB.localeCompare(createdAtA) : createdAtA.localeCompare(createdAtB);
    });
}

export function deleteExtractedMediaAsset(workspaceId:string, assetId:string) {
  return request<{deleted:boolean;asset_id:string}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}`, {method:'DELETE'});
}

export type CataloguePage = {assets:(MediaAsset & {source_folder?:string})[];total:number;offset:number;limit:number;workspaces:string[];workspace_names?:Record<string,string>;folders?:string[]};
export function browseMediaCatalogue(workspaceId:string, options:{kinds:string;source:string;owner:string;query:string;offset:number;order:string;folder?:string}) {
  const query=new URLSearchParams({...options,offset:String(options.offset),limit:'24'});
  return request<CataloguePage>(`/api/media/${encodeURIComponent(workspaceId||'global')}/assets/catalogue?${query}`);
}
export function reuseCatalogueAsset(workspaceId:string, asset:MediaAsset, role?:string, mode:'reference'|'copy' = 'reference') {
  return request<MediaAsset>(`/api/media/${encodeURIComponent(workspaceId)}/assets/reuse`, {
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({source_workspace_id:asset.workspace_id,asset_id:asset.asset_id,mode,...(role?{role}:{})}),
  });
}

export const refreshDownloadCatalogue = (workspaceId:string) => request<{added:number;errors:{filename:string;message:string}[]}>(`/api/media/${encodeURIComponent(workspaceId||'global')}/assets/catalogue-refresh`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
export const nameMediaWorkspace = (workspaceId:string,name:string) => request<{workspace_id:string;name:string}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/workspace-name`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});

export type MediaDeletion = {asset_id:string;path:string;sha256:string;references:string[];can_delete:boolean};
export function previewMediaDeletion(workspaceId:string, assetId:string) {
  return request<MediaDeletion>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(assetId)}/deletion`);
}
export function permanentlyDeleteMedia(workspaceId:string, preview:MediaDeletion) {
  return request<{deleted:boolean}>(`/api/media/${encodeURIComponent(workspaceId)}/assets/${encodeURIComponent(preview.asset_id)}/deletion`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sha256:preview.sha256})});
}
