import type {ScreenplayRevision} from './story-api';
import type {NativeSession,NativeAction} from './native-workspace';
export type Stage = 'worlds'|'shot_frames'|'storyboard'|'first_last';
export type ShotPreparation = {presentation:'image'|'video';duration:number;route:'image'|'t2v'|'r2v'|'fflf'|'existing';control:'manual'|'auto';image_asset_id:string;media_asset_id:string;reference_ids:string[];background_asset_id:string;first_frame_id:string;last_frame_id:string;prompt:string;video_prompt:string;batch_id:string;request_key:string;image_request:string;batch_target:'image'|'background'|'character';notes:string};
export type BoardBody = {mode:'assisted_manual'|'fully_automated';deliverable:'storyboard'|'storyboard_video'|'video';stages:Record<Stage,{enabled:boolean;control:'manual'|'auto'}>;scenes:Record<string,{description:string;dialogue:string}>;shots:Record<string,ShotPreparation>};
export type BoardState = {workspace_id:string;screenplay_revision_id:string;revision:number;body:BoardBody};
export type ProductionManifest = {schema:'vibe-director.production-manifest';version:1;
 project:{workspace_id:string;screenplay_revision_id:string;storyboard_revision:number;title:string};
 capabilities:{metadata_only:true;media_bundled:false;write_back:false;timing:string};
 upstream:{repository:string;revision:string;license:string;interface:string};
 shot_mapping:Record<string,unknown>[];artifacts:Record<string,unknown>};
export type Change = {scene_number:number;shot_number:number;field:string;value:string|number;before:unknown};
export type Conversation = {key:string;revision_id?:string;instruction:string;status:string;reply?:string|null;proposal:{explanation:string;changes:Change[]}|null};
async function request<T>(path:string, value?:unknown, method='POST'):Promise<T>{const response=await fetch(path,value===undefined?undefined:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||`Request failed (${response.status})`);return data;}
const base=(w:string,r:string)=>`/api/story/workspaces/${encodeURIComponent(w)}/storyboard/${encodeURIComponent(r)}`;
const director=(w:string,r:string,action:string)=>`/api/story/workspaces/${encodeURIComponent(w)}/screenplay-director/${encodeURIComponent(r)}/${action}`;
export const getBoard=(w:string,r:string)=>request<BoardState>(base(w,r));
export const saveBoard=(state:BoardState,body:BoardBody)=>request<BoardState>(base(state.workspace_id,state.screenplay_revision_id),{expected_revision:state.revision,body},'PUT');
export const exportProductionManifest=(state:BoardState)=>request<ProductionManifest>(base(state.workspace_id,state.screenplay_revision_id)+'/production-manifest',{expected_revision:state.revision});
export const openBacklot=(state:BoardState)=>request<NativeSession>(base(state.workspace_id,state.screenplay_revision_id)+'/backlot',{expected_revision:state.revision});
export const operateBacklot=(w:string,r:string,token:string,action:NativeAction)=>request<unknown>(base(w,r)+'/backlot-action',{token,action});
export const getConversation=(w:string,r:string)=>request<{items:Conversation[]}>(director(w,r,'conversation'));
export const chatScreenplay=(w:string,r:string,instruction:string,key:string)=>request<Conversation>(director(w,r,'chat'),{instruction,idempotency_key:key});
export const proposeScreenplay=(w:string,r:string,instruction:string,key:string)=>request<Conversation['proposal']>(director(w,r,'propose'),{instruction,idempotency_key:key});
export const applyScreenplay=(w:string,r:string,key:string,selected:number[],idempotency_key:string)=>request<ScreenplayRevision>(director(w,r,'apply'),{request_key:key,selected,idempotency_key});

export type BoardSource = Pick<ScreenplayRevision,'screenplay_revision_id'|'screenplay'|'accepted'> & {source_kind?:'brief_media'};
export type BoardSourceResult = {source:BoardSource;board:BoardState};
export const createBoardSource=(w:string,value:{request_id:string;title:string;brief:string;asset_ids:string[]})=>request<BoardSourceResult>(`/api/storyboards/${encodeURIComponent(w)}`,value);
export const openBoardSource=(w:string,id:string)=>request<BoardSourceResult>(`/api/storyboards/${encodeURIComponent(w)}/${encodeURIComponent(id)}`);

export const listBoardSources=(w:string)=>request<{sources:{source_id:string;title:string}[]}>(`/api/storyboards/${encodeURIComponent(w)}`);
