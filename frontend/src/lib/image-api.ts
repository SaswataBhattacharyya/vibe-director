export type ImageWorkflow = { workflow_id: string; label: string; version: string; available: boolean; disabled_reason: string | null; prompt_knowledge_ref?: ImagePromptDraft["knowledge_ref"]; automation_available?: boolean; automation_disabled_reason?: string | null; workflow_sha256?: string | null; live_smoke?: Record<string, unknown> | null; defaults: {width:number;height:number;steps:number;cfg:number} };
export type ImageGpuAdmission = { available:boolean; checked:boolean; free_gib?:number|null; required_gib:number; checked_at:string; reason:string|null; host_memory?:{ total_gib:number; available_gib:number; swap_total_gib:number; swap_free_gib:number }|null };
export type ImageWorkflows = { workflows: ImageWorkflow[]; generation_policy: Record<string, unknown>; gpu_admission?:ImageGpuAdmission };
export type ImageWorker = { enabled:boolean; running:boolean; available:boolean; worker_state:string; reason?:string|null };
export type ImageCandidate = { job_id:string; candidate_index:number; status:string; asset_role?:string; output_asset_id?:string|null; settings?:Record<string,any>; error?:{message?:string;code?:string}|null; director_review?:{resolution_status:string;decision?:{action?:string;reason?:string};error?:{message?:string;code?:string}|null}|null };
export type ImageBatch = { batch_id:string; jobs:ImageCandidate[]; generation_policy:Record<string,unknown> };
export type ImageStageAdmission = { run_id?:string; step:string; target_count?:number; batches:Array<{batch_id:string;reused:boolean;jobs:ImageCandidate[]}>; message?:string };
export type ImagePromptDraft = { workflow_id:string; asset_role:string; prompt:string; knowledge_ref:{knowledge_id:string;guidance_version:number;workflow_sha256:string}; sources:Array<{uri:string;version:string;section:string}> };
export class ImageApiError extends Error {
  constructor(message:string, readonly code?:string, readonly admissionState?:string) { super(message); }
}
async function request<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) { const payload = await response.json().catch(()=>({})); throw new ImageApiError(payload?.error?.message || `Image request failed (${response.status}).`, payload?.error?.code, payload?.admission_state); }
  return response.json() as Promise<T>;
}
const post = (value:unknown) => ({method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(value)});
export const getImageWorkflows = (checkGpuAdmission = false) => request<ImageWorkflows>(`/api/images/workflows${checkGpuAdmission?'?check_gpu_admission=1':''}`);
export const getImageWorker = () => request<ImageWorker>('/api/images/worker');
export const getImageSelection = (workspaceId:string,revisionId:string,targetType:string,targetId:string) => request<{selection:{asset_id:string;authority:string;job_id:string}|null}>(`/api/images/selections?workspace_id=${encodeURIComponent(workspaceId)}&screenplay_revision_id=${encodeURIComponent(revisionId)}&target_type=${encodeURIComponent(targetType)}&target_record_id=${encodeURIComponent(targetId)}`);
export const validateImageRequest = (value:Record<string,unknown>) => request<any>('/api/images/validations',post(value));
export const prepareImagePrompt = (value:Record<string,unknown>) => request<ImagePromptDraft>('/api/images/prompts/prepare',post(value));
export const createImageBatch = (value:Record<string,unknown>) => request<{batch_id:string;jobs:ImageCandidate[];reused:boolean}>('/api/images/jobs',post(value));
export const startAutomatedImageStage = (workspaceId:string,screenplayRevisionId:string,step:'character_images'|'world_images'|'frame_images') => request<ImageStageAdmission>('/api/images/automated-stage',post({workspace_id:workspaceId,screenplay_revision_id:screenplayRevisionId,step}));
export const getImageBatch = (workspaceId:string,batchId:string) => request<ImageBatch>(`/api/images/batches/${encodeURIComponent(batchId)}?workspace_id=${encodeURIComponent(workspaceId)}`);
export const acceptImageCandidate = (workspaceId:string,jobId:string,assetRole:string,lineage?:{screenplay_revision_id:string;target_record_id?:string;scene_number?:number;shot_number?:number;clip_id?:string;asset_role?:string}) => request<{job_id:string;asset:import('./media-api').MediaAsset;selected:boolean;target_selection?:{asset_id:string}|null}>(`/api/images/jobs/${encodeURIComponent(jobId)}/accept`,post({workspace_id:workspaceId,asset_role:assetRole,...lineage}));
export const exportImageAsset = (value:{workspace_id:string;asset_id:string;folder:string;filename:string;overwrite?:boolean;existing_sha256?:string}) => request<{path?:string;collision?:boolean;existing_sha256?:string}>('/api/images/assets/export',post(value));
export async function stageTemporaryImageReference(workspaceId:string,file:File,token:string) {
  const response=await fetch(`/api/images/temporary-references/${encodeURIComponent(workspaceId)}?token=${encodeURIComponent(token)}`,{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Image-Filename':file.name},body:file});
  const value=await response.json(); if(!response.ok)throw new ImageApiError(value?.error?.message||'Could not stage this reference image.'); return value as import('./media-api').MediaAsset;
}
export const deleteTemporaryImageAsset=(workspaceId:string,assetId:string,token:string)=>request<{deleted:boolean}>(`/api/images/temporary-assets/${encodeURIComponent(workspaceId)}/${encodeURIComponent(assetId)}`,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
