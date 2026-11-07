import {useProjectState} from './lib/project-state';
import {useProject} from './ProjectController';
import {useContext, useEffect, useRef, useState} from 'react';
import {DirectorStudio, type StudioTarget} from './DirectorStudio';
export async function studioRequest(path:string,body?:unknown) {
 const response=await fetch(path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const result=await response.json();if(!response.ok)throw new Error(result.error?.message||'Studio request failed.');return result;
}
export default function StudioChat({name,context,onApply,disabled=false}:{name:'trellis'|'audio';context:Record<string,unknown>;onApply?:(settings:Record<string,number>)=>void;disabled?:boolean}) {
 const {workspace_id:owner}=useProject();
 const director=useContext(DirectorStudio);
 const key=`vibe-studio-chat-${name}:${owner}`;
 const [rows,setRows]=useState<Array<{text:string;reply:string;settings:Record<string,number>}>>([]);
 const [attachments,setAttachments]=useState<File[]>([]);
 const [previews,setPreviews]=useState<string[]>([]);
 const [draft]=useProjectState(`StudioChat:${name}:text`,'');
 const [dismissed,setDismissed]=useProjectState<string[]>(`StudioChat:${name}:dismissed`,[]);
 useEffect(()=>{try{setRows(JSON.parse(localStorage.getItem(key)||'[]'));}catch{setRows([]);}setAttachments([]);},[key]);
 useEffect(()=>{const urls=attachments.map(f=>URL.createObjectURL(f));setPreviews(urls);return()=>urls.forEach(URL.revokeObjectURL);},[attachments]);
 const target:StudioTarget={version:1,workspace_id:owner,name,context:{settings:context,attachments:attachments.map(f=>({name:f.name,bytes:f.size,type:f.type}))},history:rows.slice(-12).map(({text,reply})=>({text,reply}))};
 const latest=useRef({target,disabled});latest.current={target,disabled};
 useEffect(()=>{
   if(!director)return;
   const bridge={prepareTarget:()=>{if(latest.current.disabled)throw new Error('Wait for the current studio operation to finish.');return latest.current.target;}};
   director.bridge.current=bridge;return()=>{if(director.bridge.current===bridge)director.bridge.current=null;};
 },[director?.bridge,owner,name]);
 const suggestions=(director?.messages||[]).flatMap(message=>message.proposal?.surface==='studio'&&message.proposal.target.workspace_id===owner&&message.proposal.target.name===name&&!dismissed.includes(message.request_id)?[{message,proposal:message.proposal}]:[]);
 const dismiss=(id:string)=>setDismissed(old=>[...old,id]);
 return <section className="studio-guidance" aria-label="Studio suggestions">
   <p className="muted">Discuss these controls in the project Director. Suggestions require Apply; generation stays manual.</p>
   {(rows.length>0||draft)&&<details><summary>Previous studio conversation</summary>{rows.map((row,i)=><article key={i}><b>{row.text}</b><p>{row.reply}</p>{Object.keys(row.settings||{}).length>0&&<pre>{JSON.stringify(row.settings,null,2)}</pre>}</article>)}{draft&&<p>Earlier unsent draft: {draft}</p>}</details>}
   {suggestions.map(({message,proposal})=>{const stale=JSON.stringify(proposal.target.context)!==JSON.stringify(target.context);return <article className="card" key={message.request_id}><p>{message.reply}</p>{Object.keys(proposal.settings).length>0&&<pre>{JSON.stringify(proposal.settings,null,2)}</pre>}{stale&&<p role="status">Studio controls changed; request a fresh suggestion.</p>}{onApply&&Object.keys(proposal.settings).length>0&&<button disabled={disabled||stale} onClick={()=>{onApply(proposal.settings);dismiss(message.request_id);}}>Apply suggested settings</button>}<button onClick={()=>dismiss(message.request_id)}>Discard suggestion</button></article>;})}
   <details onDragOver={event=>event.preventDefault()} onDrop={event=>{event.preventDefault();setAttachments(old=>[...old,...Array.from(event.dataTransfer.files).filter(file=>file.type.startsWith('image/'))].slice(0,6));}}><summary>Studio attachment context</summary><label>Chat images<input type="file" accept="image/*" multiple onChange={e=>setAttachments(old=>[...old,...Array.from(e.target.files||[])].slice(0,6))}/></label><small>The Director receives filenames and settings, not visual analysis. Choose generation inputs separately.</small><div className="studio-chat-attachments">{attachments.map((file,i)=><span key={i}><img src={previews[i]} alt=""/>{file.name}<button aria-label={`Remove ${file.name}`} onClick={()=>setAttachments(old=>old.filter((_,index)=>index!==i))}>Remove</button></span>)}</div></details>
 </section>;
}
