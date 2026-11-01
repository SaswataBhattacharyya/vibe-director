import { ReactNode, useEffect, useState } from 'react';
import type { Draft } from './App';
import EditorWorkspace from './EditorWorkspace';
import ModelSelector, { consumeModelCommand } from './ModelSelector';
import { R2V_WORKFLOW_ID } from './lib/video-api';

type Suggestion = { replacement: string; explanation?: string };
type Exchange = { instruction: string; base: string; context: string; requestKey: string; suggestion?: Suggestion; applied?: boolean };

export default function CreateWorkspace({ enabled, draft, disabled, onPrompt, children }: {
  enabled: boolean; draft: Draft; disabled: boolean; onPrompt: (text: string) => void; children: ReactNode;
}) {
  if (!enabled) return <>{children}</>;
  return <EditorWorkspace name="create" rightLabel="creation controls" preview={children}>
    <CreateChat draft={draft} disabled={disabled} onPrompt={onPrompt}/>
  </EditorWorkspace>;
}

function CreateChat({draft, disabled, onPrompt}: {draft: Draft; disabled: boolean; onPrompt: (text: string)=>void}) {
  const key = `vibe-create-chat:${draft.workspaceId}:${draft.clipId}`;
  const [exchanges, setExchanges] = useState<Exchange[]>(()=>{try {return JSON.parse(localStorage.getItem(key)||'[]');} catch {return [];}});
  const [input, setInput] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState(''), [modelOpen,setModelOpen] = useState(false);
  const prompt = draft.workflowId === R2V_WORKFLOW_ID ? (draft.r2vMainPrompt ?? draft.prompt) : draft.prompt;
  const context = JSON.stringify({workflow: draft.workflowId, duration: draft.duration, resolution: draft.resolution, aspectRatio: draft.aspectRatio,
    images:draft.r2vImages, videos:draft.r2vVideos, audio:draft.r2vAudios, firstFrame:draft.firstFrameAssetId, lastFrame:draft.lastFrameAssetId});
  useEffect(()=>{try {localStorage.setItem(key,JSON.stringify(exchanges));} catch {setError('Chat could not be saved in this browser. Keep this page open.');}},[key,exchanges]);
  const readResponse = async (response: Response) => {
    const body=await response.json();
    if(!response.ok) throw new Error(body.detail || body.error?.message || 'Prompt suggestion failed.');
    return body;
  };
  const unresolved = exchanges.some(item=>!item.suggestion);
  const recover = async (item: Exchange) => {
    setBusy(true);setError('');
    try {
      const body=await readResponse(await fetch(`/api/story/field-edit-requests/by-key/${encodeURIComponent(item.requestKey)}`));
      if(!body.proposal) throw new Error(body.recovery_message || `Request is ${body.status}. Check again before sending another request.`);
      setExchanges(items=>items.map(row=>row.requestKey===item.requestKey?{...row,suggestion:body.proposal}:row));
    } catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  };
  const send = async () => {
    if(disabled || busy || unresolved || !input.trim()) return;
    // Reuse the durable field-edit service; a seed sentence permits drafting from an empty field.
    const base=prompt || 'Write a new video shot prompt.';
    const instruction=`Prepare only the video prompt text. Do not run tools or claim generation. Keep the selected workflow, references and settings unchanged. Use the conversation to interpret the latest request.\nSettings and reference metadata: ${context}\nConversation: ${JSON.stringify(exchanges.slice(-4).map(item=>({user:item.instruction,prompt:item.suggestion?.replacement})))}\nLatest request: ${input}`;
    if(instruction.length>4000) {setError('This request and its context are too long. Shorten the message or use the prompt’s focused edit.');return;}
    const item:Exchange={instruction:input.trim(),base:prompt,context,requestKey:crypto.randomUUID()};
    try {localStorage.setItem(key,JSON.stringify([...exchanges,item]));} catch {setError('Save the chat recovery key before sending. Browser storage is unavailable.');return;}
    setExchanges(items=>[...items,item]);setInput('');setBusy(true);setError('');
    try {
      const suggestion=await readResponse(await fetch(`/api/story/workspaces/${encodeURIComponent(draft.workspaceId)}/field-edit-proposals`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({surface:'prompt',revision_id:draft.sourceLineage?.screenplay_revision_id || draft.clipId,field_key:`video.${draft.clipId}.chat`,field_text:base,start_codepoint:0,end_codepoint:Array.from(base).length,expected_text:base,instruction,idempotency_key:item.requestKey})}));
      setExchanges(items=>items.map(row=>row.requestKey===item.requestKey?{...row,suggestion}:row));
    } catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  };
  return <div className="create-chat">
    <h2>Director</h2><p>Describe your clip or ask for a prompt change. Review and apply it, then use Generate in the right pane.</p>
    <div role="log" aria-label="Video creation conversation" aria-live="polite">
      {exchanges.map(item=><article className="card" key={item.requestKey}>
        <b>You</b><p>{item.instruction}</p>
        {item.suggestion ? <><b>Director</b><p>{item.suggestion.replacement}</p>{item.suggestion.explanation&&<p>{item.suggestion.explanation}</p>}
          <button type="button" disabled={disabled||busy||item.applied||item.base!==prompt||item.context!==context} onClick={()=>{onPrompt(item.suggestion!.replacement);setExchanges(items=>items.map(row=>row.requestKey===item.requestKey?{...row,applied:true}:row));}}>{item.applied?'Applied':'Apply prompt'}</button>
          {!item.applied&&(item.base!==prompt||item.context!==context)&&<small>The draft changed. Request a fresh suggestion.</small>}
        </> : <button type="button" disabled={busy} onClick={()=>void recover(item)}>{busy?'Working…':'Check suggestion status'}</button>}
      </article>)}
    </div>
    <ModelSelector open={modelOpen} onClose={()=>setModelOpen(false)} disabled={busy} returnFocusId="create-chat-message"/>
    <label htmlFor="create-chat-message">Message the Director</label>
    <textarea id="create-chat-message" rows={5} value={input} disabled={busy||disabled} onChange={e=>setInput(consumeModelCommand(e.target.value,()=>setModelOpen(true),"create-chat-message"))} placeholder="Describe the shot, or type /model"/>
    <button type="button" className="generate-button" disabled={disabled||busy||unresolved||!input.trim()} onClick={()=>void send()}>{busy?'Working…':'Send'}</button>
    {error&&<p role="alert">{error}</p>}
  </div>;
}
