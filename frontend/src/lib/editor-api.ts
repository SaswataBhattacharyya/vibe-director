import type { MediaAsset } from './media-api';
export type EditorRange = {asset_id:string;start:number;end:number;filename?:string;mime?:string;caption?:string;fit?:string;effect?:{preset:string;strength:number};speed?:{start:number;end:number};transition?:{kind:string;duration:number};render_duration?:number};
export type EditorPlan = {summary:string;tools:string[];width:number;height:number;fps:number;clips:EditorRange[];audio:EditorRange|null};
export type EditorStyle = {id:string;name:string;version:number;rules:Array<{id:string;text:string;confirmed:boolean}>};
export type EditorProject = {id:string;name:string;workspace_id:string;style_id:string|null;revision:number;messages:Array<{id:string;role:string;content:string;at:string}>;revisions:Array<{kind:string;revision:number;value:unknown;style_snapshot?:{id:string;version:number}}> ;selection:EditorRange[];overrides:Record<string,string>;brief?:{summary:string;questions:string[]};pending?:{kind:'brief'|'plan';revision:number;value:any};job_id?:string;job?:{status:string;stage:string;message:string;error?:string;progress:number};pause_requested?:boolean;output?:{asset:MediaAsset};view?:Record<string,unknown>;last_export?:{path:string}};
export type EditorState = {projects:EditorProject[];styles:EditorStyle[];runtime:{ready:boolean;version:string;checks:Record<string,boolean>;message:string}};
export async function editorApi<T>(path:string, method='GET', body?:unknown):Promise<T> {
  const response=await fetch(`/api/editor/${path}`, {method, ...(body===undefined?{}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
  const value=await response.json();
  if(!response.ok) throw new Error(value?.error?.message || 'Editor request failed.');
  return value;
}
