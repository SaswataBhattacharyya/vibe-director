import {useEffect,useRef,useState} from 'react';
import {studioRequest} from './StudioChat';

type Choice={mode:'default'|'workspace'|'folder';grant?:string;path:string;available?:boolean};
/** A saved output choice is frozen by the backend when the job is created. */
export default function OutputDestination({tool,workspaceId,disabled=false,onReady}:{tool:string;workspaceId:string;disabled?:boolean;onReady?:(ready:boolean)=>void}) {
 const scope=useRef('');scope.current=tool+'--'+workspaceId;
 const [choice,setChoice]=useState<Choice|null>(null),[path,setPath]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[editing,setEditing]=useState(false);
 useEffect(()=>{let live=true;setChoice(null);setBusy(false);setError('');setEditing(false);onReady?.(false);
  void studioRequest('/api/studio-tools/output-destination',{tool,workspace_id:workspaceId||'tool-library'}).then(next=>{if(live){setChoice(next);setPath(next.path);onReady?.(next.available!==false);}}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};
 },[tool,workspaceId]);
 const save=async(next:Partial<Choice>,key=scope.current)=>{if(scope.current!==key)return;setBusy(true);setError('');onReady?.(false);try{const resolved=await studioRequest('/api/studio-tools/output-destination',{tool,workspace_id:workspaceId||'tool-library',choice:next});if(scope.current===key){setChoice(resolved);setPath(resolved.path);onReady?.(resolved.available!==false);}}catch(e){if(scope.current===key)setError((e as Error).message);}finally{if(scope.current===key)setBusy(false);}};
 const choose=async(manual=false)=>{const key=scope.current;setBusy(true);setError('');onReady?.(false);try{const selected=await studioRequest('/api/studio-tools/output-folder',manual?{path}:{});if(scope.current!==key)return;setPath(selected.path);if(choice?.available===false){const restored=await studioRequest('/api/studio-tools/output-relink',{tool,workspace_id:workspaceId||'tool-library',grant:selected.grant});if(scope.current===key){setChoice(restored);setPath(restored.path);onReady?.(restored.available!==false);}}else await save({mode:'folder',grant:selected.grant},key);}catch(e){if(scope.current===key){setError((e as Error).message);onReady?.(!!choice&&choice.available!==false);}}finally{if(scope.current===key)setBusy(false);}};
 return <section className="output-destination" aria-label={`${tool} output destination`}>
  <div className="output-destination-summary">
   <span className="output-destination-path">{choice?.available===false?'Unavailable: ':'Saved to: '}<span>{choice?.path||'Reading saved destination…'}</span></span>
   <button type="button" className="quiet-button" aria-expanded={editing||choice?.available===false} onClick={()=>setEditing(value=>!value)}>{editing?'Close':'Change'}</button>
  </div>
  {choice?.available===false&&<p role="alert">Locate the saved folder to restore existing references. Its files will be verified before relinking. No fallback folder is used.</p>}
  <div hidden={!editing&&choice?.available!==false}>
   <div className="studio-action-row">
    <label>Output folder path<input aria-label={`${tool} output folder path`} value={path} disabled={disabled||busy} placeholder="/home/…" onChange={e=>setPath(e.target.value)}/></label>
    <button type="button" disabled={disabled||busy} onClick={()=>void choose()}>{busy?'Please wait…':'Choose folder'}</button>
    <button type="button" disabled={disabled||busy||!path.trim()||path===choice?.path&&choice?.available!==false} onClick={()=>void choose(true)}>Use this folder</button>
   </div>
   <small>Changing the folder affects new jobs only. Choose a folder inside this project to keep new outputs together.</small>
  </div>
  {error&&<p role="alert">{error}</p>}
 </section>;
}
