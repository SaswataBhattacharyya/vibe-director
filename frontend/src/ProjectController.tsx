import {createContext, ReactNode, useContext, useEffect, useRef, useState} from 'react';
import {studioRequest} from './StudioChat';
import CompactPopover from './CompactPopover';
import {setActiveProjectId} from './lib/media-workspace';

type Project={workspace_id:string;title:string;folder?:string;projects_folder?:string;browser_state:Record<string,string>;notice?:string};
const Context=createContext<Project>({workspace_id:'tool-library',title:'Standalone tools',browser_state:{}});
export const useProject=()=>useContext(Context);
const localKey='vibe-project-browser:';
const installedKey='vibe-project-installed';
const sessionKeys=['vibe-editor-pending-audio','vibe-jukebox-pending-audio'];
const prefix=/^vibe-(project-settings:|session:|video-|story-|create-chat:|selected-take:|take-position:|image-|text-to-image-|editor-|ace-|studio-chat-|screenplay-|board-|field-edit:|t2v-batch:|trellis-|pixal-|jukebox-|production-|style-setup-context|3d-)/;
const included=(key:string)=>prefix.test(key)&&!key.startsWith(localKey);
function capture(workspace:string){
 const result:Record<string,string>={};
 for(const key of Object.keys(localStorage)){
  if(!included(key)||key.includes('story-')&&/story-[a-f0-9]{12}/.test(key)&&!key.includes(workspace))continue;
  const value=localStorage.getItem(key);if(value!==null)result[key]=value;
 }
 if(result['vibe-story-draft-v1'])try{const drafts=JSON.parse(result['vibe-story-draft-v1']);result['vibe-story-draft-v1']=JSON.stringify(drafts[workspace]?{[workspace]:drafts[workspace]}:{});}catch{/* Retain malformed input for recovery. */}
 if(result['vibe-story-ui-draft-v1'])try{const ui=JSON.parse(result['vibe-story-ui-draft-v1']);ui.conversations=ui.conversations?.[workspace]?{[workspace]:ui.conversations[workspace]}:{};result['vibe-story-ui-draft-v1']=JSON.stringify(ui);}catch{/* Retain the original draft. */}
 for(const key of sessionKeys){const value=sessionStorage.getItem(key);if(value!==null)result['vibe-session:'+key]=value;}
 return result;
}
function install(project:Project,restore:boolean){
 if(restore){
  for(const key of Object.keys(localStorage))if(included(key))localStorage.removeItem(key);
  for(const key of sessionKeys)sessionStorage.removeItem(key);
  for(const [key,value] of Object.entries(project.browser_state||{}))if(included(key)){if(key.startsWith('vibe-session:'))sessionStorage.setItem(key.slice('vibe-session:'.length),value);else localStorage.setItem(key,value);}
 }
 localStorage.setItem(installedKey,project.workspace_id);
 setActiveProjectId(project.workspace_id);
 localStorage.setItem('vibe-media-active-workspace-v1',project.workspace_id);
 localStorage.setItem('vibe-story-selected-v1',project.workspace_id==='tool-library'?'':project.workspace_id);
 // URL ownership is a legacy deep link, never an independent page selection.
 const [path,query='']=location.hash.split('?');const params=new URLSearchParams(query);
 if(params.has('workspace_id')&&params.get('workspace_id')!==project.workspace_id){params.delete('workspace_id');history.replaceState(null,'',`${path}${params.size?'?'+params:''}`);}
}
export default function ProjectController({children}:{children:ReactNode}){
 const actionBusy=useRef(false);
 const [createParent,setCreateParent]=useState('');
 const [project,setProject]=useState<Project|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[folder,setFolder]=useState(''),[title,setTitle]=useState(''),[version,setVersion]=useState(0),[existing,setExisting]=useState<Array<{workspace_id:string;title:string}>>([]);
 useEffect(()=>{let live=true;void studioRequest('/api/projects/current').then(async (next:Project)=>{
  if(!next||typeof next.workspace_id!=='string')throw new Error('Invalid project service response.');
  void (async()=>{
   const items:Array<{workspace_id:string;title:string}>=[];
   while(live){const page=await studioRequest(`/api/story/workspaces?limit=100&offset=${items.length}`);const batch=page.items||[];items.push(...batch);if(!batch.length||items.length>=(page.total??items.length))break;}
   if(live)setExisting(items);
  })().catch(()=>{});
  const legacy=localStorage.getItem('vibe-media-active-workspace-v1')||localStorage.getItem('vibe-story-selected-v1');
  if(next.workspace_id==='tool-library'&&legacy?.startsWith('story-')&&!next.notice){
   try{next=await studioRequest('/api/projects/select',{workspace_id:legacy});}catch{/* Deleted legacy ownership cannot prevent standalone use. */}
  }
  if(!live)return;
  const cached=localStorage.getItem(localKey+next.workspace_id);
  // On first adoption preserve browser drafts; on a fresh browser restore server memory.
  const installed=localStorage.getItem(installedKey);
  const restore=installed?installed!==next.workspace_id:!Object.keys(localStorage).some(included);
  // Cached drafts remain recoverable; returned project memory wins on a switch.
  if(restore&&cached)localStorage.setItem('vibe-recovery:'+next.workspace_id+':browser',cached);
  // Preserve the old frozen recovery request under its original owner. Only
  // unbound text/settings may be carried into a fresh standalone draft.
  const draftText=localStorage.getItem('vibe-video-draft-v1');
  if(draftText)try{const draft=JSON.parse(draftText);if(draft.workspaceId!==next.workspace_id&&next.workspace_id==='tool-library'){
   localStorage.setItem(`vibe-recovery:${draft.workspaceId}:video`,draftText);
   const safe={prompt:draft.prompt||'',r2vMainPrompt:draft.r2vMainPrompt,duration:draft.duration,aspectRatio:draft.aspectRatio,resolution:draft.resolution,workflowId:draft.workflowId,clipId:crypto.randomUUID(),workspaceId:'tool-library'};
   localStorage.setItem('vibe-video-draft-v1',JSON.stringify(safe));localStorage.setItem('vibe-video-draft-v1:tool-library',JSON.stringify(safe));
   next.browser_state={...next.browser_state,'vibe-video-draft-v1':JSON.stringify(safe),'vibe-video-draft-v1:tool-library':JSON.stringify(safe)};
   next.notice='The previous project is unavailable. Your prompt was retained; attachments and frozen recovery requests remain saved under their original project. Open a project folder or continue with standalone media.';
  }}catch{/* Preserve the original draft. */}
  install(next,restore);setProject(next);setFolder(next.folder||'');setCreateParent(next.projects_folder||'');
 }).catch(e=>{if(live){setError(`Project service unavailable: ${e.message}`);const fallback={workspace_id:'tool-library',title:'Standalone tools',browser_state:{}};install(fallback,false);setProject(fallback);}});return()=>{live=false;};},[]);
 useEffect(()=>{
  if(!project)return;let previous='';let saving=false;
  const save=()=>{if(saving)return;const memory=capture(project.workspace_id),encoded=JSON.stringify(memory);if(previous===encoded)return;saving=true;
   localStorage.setItem(localKey+project.workspace_id,encoded);
   void studioRequest('/api/projects/memory',{workspace_id:project.workspace_id,browser_state:memory}).then(()=>{previous=encoded;}).catch(e=>setError(`Project memory has not synced: ${e.message}`)).finally(()=>{saving=false;});};
  const timer=window.setInterval(save,2000);const unload=()=>{const payload=JSON.stringify({workspace_id:project.workspace_id,browser_state:capture(project.workspace_id)});void fetch('/api/projects/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:payload,keepalive:true});};
  window.addEventListener('pagehide',unload);return()=>{clearInterval(timer);window.removeEventListener('pagehide',unload);};
 },[project?.workspace_id]);
 const action=async(operation:string,target?:string)=>{if(!project||actionBusy.current)return;actionBusy.current=true;setBusy(true);setError('');try{
  const memory=capture(project.workspace_id);localStorage.setItem(localKey+project.workspace_id,JSON.stringify(memory));
  await studioRequest('/api/projects/memory',{workspace_id:project.workspace_id,browser_state:memory});
  // A fresh project must not depend on checkpointing the previous project's media.
  // Its working records and browser memory remain saved under their original owner.
  if(operation!=='save'&&operation!=='new'&&project.folder)await studioRequest('/api/projects/save',{workspace_id:project.workspace_id,folder:project.folder,browser_state:memory});
  const next:Project=await studioRequest(`/api/projects/${operation==='standalone'?'select':operation}`,{workspace_id:operation==='standalone'?'tool-library':target||project.workspace_id,folder,title,browser_state:memory,...(operation==='new'?{parent_folder:createParent}: {})});
  if(operation!=='save'){
   const saved=localStorage.getItem(localKey+next.workspace_id);if(saved)localStorage.setItem('vibe-recovery:'+next.workspace_id+':browser',saved);
   install(next,true);setVersion(v=>v+1);
  }
  setProject(next);setFolder(next.folder||'');
 }catch(e){setError((e as Error).message);}finally{actionBusy.current=false;setBusy(false);}};
 useEffect(()=>{const select=(event:Event)=>{void action('select',(event as CustomEvent<string>).detail);};window.addEventListener('vibe-project-select',select);return()=>window.removeEventListener('vibe-project-select',select);},[project,busy,folder]);
 const choose=async(forNew=false)=>{setBusy(true);try{const result=await studioRequest('/api/projects/choose-folder',{});if(forNew)setCreateParent(result.path);else setFolder(result.path);}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 return <Context.Provider value={project||{workspace_id:'tool-library',title:'Loading project…',browser_state:{}}}>
  <div className="project-toolbar" aria-label="Project controls"><strong>{project?.title||'Loading project…'}</strong>{project?.folder&&<small title={project.folder}>{project.folder}</small>}
   <CompactPopover key={project?.workspace_id} label="New project">
    <label>New project name<input value={title} onChange={e=>setTitle(e.target.value)} disabled={busy}/></label>
    <label>Save location<input aria-label="New project parent folder" value={createParent} placeholder="Application projects folder" onChange={e=>setCreateParent(e.target.value)} disabled={busy}/></label>
    <button disabled={busy} onClick={()=>void choose(true)}>Choose parent folder</button>
    <p>A new folder named after your project will be created here and opened automatically.</p>
    <button disabled={busy||!title.trim()} onClick={()=>void action('new')}>Create project</button>
   </CompactPopover>
   <CompactPopover label="Load project">
    <p>Choose the existing project folder to load its saved work.</p>
    <label>Open project folder<input aria-label="Project folder path" value={folder} onChange={e=>setFolder(e.target.value)} disabled={busy}/></label>
    <div style={{display:'flex',gap:8,flexWrap:'wrap'}}><button disabled={busy} onClick={()=>void choose()}>Choose folder</button>
    <button disabled={busy||!folder.trim()} onClick={()=>void action('open')}>Open project</button><button disabled={busy||!project||project.workspace_id==='tool-library'} onClick={()=>void action('standalone')}>Use standalone tools</button></div>{existing.length>0&&<details><summary>Existing projects in this application</summary>{existing.map(item=><button key={item.workspace_id} disabled={busy||item.workspace_id===project?.workspace_id} onClick={()=>void action('select',item.workspace_id)}>{item.title}</button>)}<p>Choose the project folder containing vibe-project.json to restore its saved work.</p></details>}</CompactPopover>
   <button disabled={busy||!project||project.workspace_id==='tool-library'} onClick={()=>void action('save')}>{busy?'Please wait…':'Save project'}</button>
   {(error||project?.notice)&&<p role="alert">{error||project?.notice}</p>}
  </div>
  {project?<div key={`${project.workspace_id}:${version}`} style={{display:'contents'}}>{children}</div>:<p role="status">Restoring project…</p>}
 </Context.Provider>;
}
