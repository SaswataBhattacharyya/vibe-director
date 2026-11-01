import {useEffect,useState} from 'react';
type Status={provider:string;model:string;quota:string;quota_note:string;context_note:string;context_remaining_percent:number|null;checked_at:number;windows:Array<{bucket:string;window:string;used_percent:number;remaining_percent:number;window_minutes:number|null;resets_at:number|null}>;last_request?:{input_tokens:number|null;output_tokens:number|null;recorded_at:number}|null};
export default function ProviderStatus({onClose}:{onClose:()=>void}){
  const [status,setStatus]=useState<Status|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function load(){setBusy(true);setError('');try{const response=await fetch('/api/director/status');if(!response.ok)throw new Error('Usage unavailable. Retry shortly.');setStatus(await response.json());}catch{setError('Usage unavailable. Check the backend connection and retry.');}finally{setBusy(false);}}
  useEffect(()=>{void load();const changed=()=>{setStatus(null);void load();};window.addEventListener('director-model-changed',changed);return()=>window.removeEventListener('director-model-changed',changed);},[]);
  return <section className="card provider-status" role="region" aria-label="Model usage" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();onClose();}}}>
    <strong>Model usage</strong> <button type="button" onClick={onClose}>Close status</button>
    {busy&&<p role="status">Checking usage…</p>}{error&&<p role="alert">{error}</p>}
    {status&&<><p>{status.provider} / {status.model}</p><p>{status.quota_note}</p>
      {status.windows.map(w=><p key={`${w.bucket}:${w.window}`}><b>{w.bucket}</b> · {w.window_minutes?`${w.window_minutes} min`:w.window}: {w.used_percent}% used · {w.remaining_percent}% remaining{w.resets_at?` · resets ${new Date(w.resets_at*1000).toLocaleString()}`:''}</p>)}
      <p><b>Context remaining: {status.context_remaining_percent===null?'Not reported':`${status.context_remaining_percent}%`}</b><br/>{status.context_note}</p>
      {status.last_request&&<p>Last request · input: {status.last_request.input_tokens??'not reported'} tokens · output: {status.last_request.output_tokens??'not reported'} tokens. {new Date(status.last_request.recorded_at*1000).toLocaleString()}</p>}
      <small>Checked {new Date(status.checked_at*1000).toLocaleTimeString()}. Account readings are cached for up to 30 seconds. Last-request counts cover this server process only.</small></>}
    <div><button type="button" disabled={busy} onClick={()=>void load()}>Refresh usage</button></div>
  </section>;
}
