import { useEffect, useRef, useState } from 'react';
import { Check, RotateCcw, Sparkles, X } from 'lucide-react';

type Proposal = { proposal_id: string; replacement: string; expected_text: string; start_codepoint: number; end_codepoint: number; field_sha256: string; revision_id: string; field_key: string; explanation?: string };
type RequestState = { idempotency_key: string; workspace_id: string; status: string; proposal?: Proposal; recovery_message?: string };
type Props = { label: string; value: string; surface: 'screenplay'|'prompt'; workspaceId: string; revisionId: string; fieldKey: string; disabled?: boolean; multiline?: boolean; onChange: (value: string) => void };
const cpLength = (value: string) => Array.from(value).length;
const cpToUtf16 = (value: string, offset: number) => Array.from(value).slice(0, offset).join('').length;
const storageKey = (p: Props) => `vibe-field-edit:${p.workspaceId}:${p.surface}:${p.revisionId}:${p.fieldKey}`;

export default function SelectionMicroEdit({label,value,surface,workspaceId,revisionId,fieldKey,disabled=false,multiline=true,onChange}:Props) {
  const input = useRef<HTMLTextAreaElement | HTMLInputElement>(null);
  const [selection,setSelection] = useState<{start:number;end:number;text:string}|null>(null);
  const [instruction,setInstruction] = useState('');
  const [proposal,setProposal] = useState<Proposal|null>(null);
  const [requestKey,setRequestKey] = useState('');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [baseValue,setBaseValue] = useState('');
  const currentStorageKey=storageKey({workspaceId,surface,revisionId,fieldKey} as Props);
  const activeStorageKey=useRef(currentStorageKey); activeStorageKey.current=currentStorageKey;
  const requestEpoch=useRef(0);
  useEffect(()=>()=>{requestEpoch.current++;},[currentStorageKey]);
  useEffect(()=>{
    setSelection(null); setInstruction(''); setProposal(null); setRequestKey(''); setBaseValue(''); setBusy(false); setError('');
    try { const saved=localStorage.getItem(currentStorageKey); if(saved) { const value=JSON.parse(saved); if(value?.payload) { setRequestKey(value.payload.idempotency_key); setBaseValue(value.payload.field_text); setSelection({start:value.payload.start_codepoint,end:value.payload.end_codepoint,text:value.payload.expected_text}); setInstruction(value.payload.instruction); if(value.proposal) setProposal(value.proposal); else setError('An edit request was interrupted. Check its status to recover the suggestion safely.'); } } } catch { /* malformed local recovery state is ignored */ }
  },[workspaceId,surface,revisionId,fieldKey]);
  const syncSelection = () => {
    if(busy) return;
    const el=input.current; if(!el || el.selectionStart==null || el.selectionEnd==null || el.selectionStart===el.selectionEnd) { setSelection(null); return; }
    const start=el.selectionStart, end=el.selectionEnd, text=value.slice(start,end);
    if(selection?.start===cpLength(value.slice(0,start)) && selection?.end===cpLength(value.slice(0,end)) && baseValue===value) return;
    setBaseValue(value); setSelection({start:cpLength(value.slice(0,start)),end:cpLength(value.slice(0,end)),text});
    setProposal(null); setRequestKey(''); setError('');
  };
  const send = async () => {
    if(!selection || !instruction.trim()) return;
    const epoch=++requestEpoch.current;
    const isCurrent=()=>activeStorageKey.current===currentStorageKey && requestEpoch.current===epoch;
    const key=crypto.randomUUID();
    const payload={surface,revision_id:revisionId,field_key:fieldKey,field_text:baseValue,start_codepoint:selection.start,end_codepoint:selection.end,expected_text:selection.text,instruction,idempotency_key:key};
    try { localStorage.setItem(currentStorageKey,JSON.stringify({payload})); }
    catch { setError('This browser could not save the edit recovery key. Check browser storage and try again.'); return; }
    setBusy(true); setError(''); setRequestKey(key);
    try {
      const response=await fetch(`/api/story/workspaces/${encodeURIComponent(workspaceId)}/field-edit-proposals`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const body=await response.json(); if(!response.ok) throw new Error(body.detail||body.error||`Edit request failed (${response.status}).`);
      if(isCurrent()) setProposal(body);
      try { localStorage.setItem(currentStorageKey,JSON.stringify({payload,proposal:body})); }
      catch { if(isCurrent()) setError('Suggestion received. Browser recovery could not be updated; keep this page open until you apply or discard it.'); }
    } catch(e) {
      // Keep the key so status can be checked without accidentally repeating a model call.
      if(isCurrent()) setError((e as Error).message);
    } finally {if(isCurrent()) setBusy(false);}
  };
  const recover = async () => {
    if(!requestKey) return; setBusy(true); setError('');
    const epoch=++requestEpoch.current;
    const isCurrent=()=>activeStorageKey.current===currentStorageKey && requestEpoch.current===epoch;
    try { const response=await fetch(`/api/story/field-edit-requests/by-key/${encodeURIComponent(requestKey)}`); const body:RequestState=await response.json(); if(!isCurrent()) return; if(!response.ok) throw new Error((body as any).detail||`Could not check edit status (${response.status}).`); if(body.proposal) { setProposal(body.proposal); try { const saved=JSON.parse(localStorage.getItem(currentStorageKey)||'{}'); localStorage.setItem(currentStorageKey,JSON.stringify({...saved,proposal:body.proposal})); } catch { /* in-memory proposal remains usable */ } } else setError(body.recovery_message||`Request status: ${body.status}. Start a new edit only after reviewing this result.`); }
    catch(e) {if(isCurrent()) setError((e as Error).message);} finally {if(isCurrent()) setBusy(false);}
  };
  const apply = () => {
    if(!proposal || proposal.revision_id!==revisionId || proposal.field_key!==fieldKey || value!==baseValue || !selection || proposal.expected_text!==selection.text || proposal.start_codepoint!==selection.start || proposal.end_codepoint!==selection.end) {setError('This field changed after the suggestion. Select the text again to make a fresh edit.');return;}
    const start=cpToUtf16(value,proposal.start_codepoint), end=cpToUtf16(value,proposal.end_codepoint);
    onChange(value.slice(0,start)+proposal.replacement+value.slice(end));
    try { localStorage.removeItem(currentStorageKey); } catch { /* applied text remains in the parent draft */ }
    setProposal(null);setSelection(null);setInstruction('');setRequestKey('');setError('');
  };
  const cancel = () => {try { localStorage.removeItem(currentStorageKey); } catch { /* best-effort cleanup */ } setSelection(null);setProposal(null);setInstruction('');setError('');setRequestKey('');};
  const inputProps={ref:input as any,value,onChange:(e:any)=>onChange(e.target.value),onMouseUp:syncSelection,onKeyUp:syncSelection,onSelect:syncSelection,disabled,'aria-label':label,className:multiline?undefined:'',rows:multiline?4:undefined};
  return <div className="selection-micro-edit"><label>{label}{multiline?<textarea {...inputProps}/>:<input {...inputProps}/>}</label>
    {selection && !disabled && <section className="selection-edit-popover" aria-label={`Edit selected text in ${label}`}>
      <div className="selection-edit-quote"><small>Selected text</small><q>{selection.text}</q></div>
      {!proposal ? <><label>Change this passage<textarea aria-label={`Instruction for ${label}`} value={instruction} onChange={e=>setInstruction(e.target.value)} placeholder="What should change?" rows={2}/></label>
        <div className="story-editor-actions"><button type="button" className="generate-button" onClick={()=>void send()} disabled={busy||!instruction.trim()||Boolean(requestKey&&error)}><Sparkles size={14}/>{busy?'Working…':'Suggest edit'}</button>{requestKey&&error&&<button type="button" className="quiet-button" onClick={()=>void recover()} disabled={busy}><RotateCcw size={14}/>Check status</button>}<button type="button" className="quiet-button" onClick={cancel} disabled={busy}><X size={14}/>Cancel</button></div></>
       : <><div className="selection-edit-quote"><small>Suggested replacement</small><p>{proposal.replacement}</p>{proposal.explanation&&<small>{proposal.explanation}</small>}</div><div className="story-editor-actions"><button type="button" className="generate-button" onClick={apply}><Check size={14}/>Apply to draft</button><button type="button" className="quiet-button" onClick={cancel}><X size={14}/>Discard</button></div></>}
      {error&&<p role="alert">{error}</p>}
    </section>}
  </div>;
}
