import { ReactNode, useContext, useEffect, useRef, useState } from 'react';
import type { Draft } from './App';
import {DirectorVideo, type VideoPromptTarget} from './DirectorVideo';
import {useProjectState} from './lib/project-state';
import { R2V_WORKFLOW_ID } from './lib/video-api';

type Suggestion = { replacement: string; explanation?: string };
type Exchange = { instruction: string; base: string; context: string; requestKey: string; suggestion?: Suggestion; applied?: boolean };

export default function CreateWorkspace({ enabled, draft, disabled, onPrompt, children }: {
  enabled: boolean; draft: Draft; disabled: boolean; onPrompt: (text: string) => void; children: ReactNode;
}) {
  if (!enabled) return <>{children}</>;
  return <div className="create-tools">
    {children}
    <details className="create-prompt-assistant">
      <summary>Shot prompt assistant</summary>
      <CreateChat draft={draft} disabled={disabled} onPrompt={onPrompt}/>
    </details>
  </div>;
}

function CreateChat({draft, disabled, onPrompt}: {draft: Draft; disabled: boolean; onPrompt: (text: string)=>void}) {
  const key = `vibe-create-chat:${draft.workspaceId}:${draft.clipId}`;
  const [exchanges, setExchanges] = useState<Exchange[]>(()=>{try {return JSON.parse(localStorage.getItem(key)||'[]');} catch {return [];}});
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const director=useContext(DirectorVideo);
  const [dismissed,setDismissed]=useProjectState<string[]>('CreateWorkspace:dismissed',[]);
  const prompt = draft.workflowId === R2V_WORKFLOW_ID ? (draft.r2vMainPrompt ?? draft.prompt) : draft.prompt;
  const settings = {workflow: draft.workflowId, duration: draft.duration, resolution: draft.resolution, aspectRatio: draft.aspectRatio,
    images:draft.r2vImages, videos:draft.r2vVideos, audio:draft.r2vAudios, firstFrame:draft.firstFrameAssetId, lastFrame:draft.lastFrameAssetId};
  const context = JSON.stringify(settings);
  useEffect(()=>{try {localStorage.setItem(key,JSON.stringify(exchanges));} catch {setError('Chat could not be saved in this browser. Keep this page open.');}},[key,exchanges]);
  const readResponse = async (response: Response) => {
    const body=await response.json();
    if(!response.ok) throw new Error(body.detail || body.error?.message || 'Prompt suggestion failed.');
    return body;
  };
  const interrupted:Exchange[]=director?.messages.flatMap(item=>item.video_target?.workspace_id===draft.workspaceId&&item.video_target.clip_id===draft.clipId
    &&!item.proposal&&!exchanges.some(row=>row.requestKey===item.request_id)?[{instruction:item.text,base:item.video_target.prompt,
      context:JSON.stringify(item.video_target.settings),requestKey:item.request_id}]:[])||[];
  const unresolved = [...exchanges,...interrupted].some(item=>!item.suggestion);
  const recover = async (item: Exchange) => {
    setBusy(true);setError('');
    try {
      const body=await readResponse(await fetch(`/api/story/field-edit-requests/by-key/${encodeURIComponent(item.requestKey)}`));
      if(!body.proposal) throw new Error(body.recovery_message || `Request is ${body.status}. Check again before sending another request.`);
      setExchanges(items=>[...items.filter(row=>row.requestKey!==item.requestKey),{...item,suggestion:body.proposal}]);
    } catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  };
  const latest=useRef({draft,prompt,settings,disabled,busy,unresolved,exchanges,messages:director?.messages||[]});
  latest.current={draft,prompt,settings,disabled,busy,unresolved,exchanges,messages:director?.messages||[]};
  useEffect(()=>{
    if(!director)return;
    const bridge={prepareTarget:():VideoPromptTarget=>{
      const value=latest.current;
      if(value.disabled||value.busy||value.unresolved)throw new Error('Finish the active operation or check the saved suggestion status before requesting a new shot prompt.');
      const history=[...value.exchanges.map(item=>({user:item.instruction,prompt:item.suggestion?.replacement})),
        ...value.messages.flatMap(item=>item.proposal?.surface==='video'&&item.proposal.target.clip_id===value.draft.clipId
          ?[{user:item.text,prompt:item.proposal.suggestion.replacement}]:[])].slice(-4);
      return {version:1,workspace_id:value.draft.workspaceId,clip_id:value.draft.clipId,
        revision_id:value.draft.sourceLineage?.screenplay_revision_id||value.draft.clipId,prompt:value.prompt,settings:value.settings,history};
    }};
    director.bridge.current=bridge;
    return()=>{if(director.bridge.current===bridge)director.bridge.current=null;};
  },[director?.bridge]);
  const proposals=director?.messages.flatMap(item=>item.proposal?.surface==='video'&&item.proposal.target.workspace_id===draft.workspaceId
    &&item.proposal.target.clip_id===draft.clipId&&!dismissed.includes(item.request_id)?[{...item,proposal:item.proposal}]:[])||[];
  return <div className="create-chat">
    <h2>Refine this shot</h2><p>Ask the shared Director for a shot-prompt change, then review and apply it here.</p>
    <div role="log" aria-label="Video creation conversation" aria-live="polite">
      {[...exchanges,...interrupted].map(item=><article className="card" key={item.requestKey}>
        <b>You</b><p>{item.instruction}</p>
        {item.suggestion ? <><b>Director</b><p>{item.suggestion.replacement}</p>{item.suggestion.explanation&&<p>{item.suggestion.explanation}</p>}
          <button type="button" disabled={disabled||busy||item.applied||item.base!==prompt||item.context!==context} onClick={()=>{onPrompt(item.suggestion!.replacement);setExchanges(items=>items.map(row=>row.requestKey===item.requestKey?{...row,applied:true}:row));}}>{item.applied?'Applied':'Apply prompt'}</button>
          {!item.applied&&(item.base!==prompt||item.context!==context)&&<small>The draft changed. Request a fresh suggestion.</small>}
        </> : <button type="button" disabled={busy} onClick={()=>void recover(item)}>{busy?'Working…':'Check suggestion status'}</button>}
      </article>)}
    </div>
    {proposals.map(item=>{
      const proposal=item.proposal;
      const current=proposal.target.prompt===prompt&&JSON.stringify(proposal.target.settings)===context
        &&proposal.target.revision_id===(draft.sourceLineage?.screenplay_revision_id||draft.clipId);
      return <article className="card" key={item.request_id}><p>{proposal.suggestion.replacement}</p><p>{proposal.suggestion.explanation}</p>
        {!current&&<small>The draft changed. Request a fresh suggestion.</small>}
        <div className="studio-action-row"><button type="button" disabled={disabled||busy||!current} onClick={()=>{onPrompt(proposal.suggestion.replacement);setDismissed(old=>[...old,item.request_id]);}}>Apply prompt</button>
          <button type="button" disabled={busy} onClick={()=>setDismissed(old=>[...old,item.request_id])}>Discard suggestion</button></div>
      </article>;
    })}
    {error&&<p role="alert">{error}</p>}
  </div>;
}
