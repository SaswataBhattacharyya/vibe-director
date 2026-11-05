export type PromptLesson = {scope:'all'|'video'|'character'|'world';rule:string};
export type PromptChange = {key:string;before:string;value:string};
export type PromptTurn = {key:string;revision_id:string;instruction:string;mode:'chat'|'propose'|'learn';status:string;reply:string;proposal?:{changes?:PromptChange[];lessons?:PromptLesson[]}|null};
export type PromptGuidance = {revision:number;lessons:PromptLesson[];assets:Record<string,string>;targets:Record<string,{scope:'character'|'world';name:string;detail:string}>;items:PromptTurn[]};
const path=(w:string,r:string)=>`/api/story/workspaces/${encodeURIComponent(w)}/prompt-director/${encodeURIComponent(r)}`;
async function request<T>(url:string,method='GET',body?:unknown):Promise<T>{
  const response=await fetch(url,{method,headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const result=await response.json();
  if(!response.ok)throw new Error(typeof result.error==='string'?result.error:result.error?.message||'Prompt Director request failed.');
  return result;
}
export const getPromptGuidance=(w:string,r:string)=>request<PromptGuidance>(path(w,r));
export const savePromptGuidance=(w:string,r:string,version:number,lessons:PromptLesson[],assets:Record<string,string>)=>request<PromptGuidance>(path(w,r),'PUT',{expected_revision:version,lessons,assets});
export const discussPrompts=(w:string,r:string,mode:PromptTurn['mode'],instruction:string,prompts:Record<string,string>,workflows:Record<string,string>,key:string)=>request<PromptTurn>(`${path(w,r)}/${mode}`,'POST',{instruction,prompts,workflows,idempotency_key:key});
export const exportPromptSkill=(w:string,r:string)=>request<{filename:string;text:string}>(`${path(w,r)}/skill`);
