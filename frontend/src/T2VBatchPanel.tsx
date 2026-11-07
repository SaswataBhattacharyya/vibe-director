import {DockedVideo} from './TakeWorkspace';
import {useEffect, useRef, useState} from 'react';
import {LoaderCircle} from 'lucide-react';
import {ApiError,createT2VBatch,controlT2VBatch,listT2VBatches,validateT2VBatch,T2VBatch,T2VBatchEntry} from './lib/video-api';
import {qualityDimensions, VideoResolution, VideoAspectRatio} from './lib/video-quality';

type Pending = {key:string;source:string;choices?:Record<string,'overwrite'|'new_take'>};
export default function T2VBatchPanel({workspaceId, editor=false, disabled=false, showVideos=true, onStarted, onActive}:{workspaceId:string;editor?:boolean;disabled?:boolean;showVideos?:boolean;onStarted?:()=>void;onActive?:(active:boolean)=>void}) {
  const storageKey = `vibe-t2v-batch:${workspaceId}`;
  const read = () => { try {return JSON.parse(localStorage.getItem(storageKey)||'{}');} catch {return {};} };
  const [source,setSource] = useState<string>(()=>read().source||'');
  const [pending,setPending] = useState<Pending|undefined>(()=>read().pending);
  const [batches,setBatches] = useState<T2VBatch[]>([]);
  const [preview,setPreview] = useState<T2VBatchEntry[]>([]);
  const [busy,setBusy] = useState(false);
  const [loaded,setLoaded] = useState(false);
  const [error,setError] = useState('');
  const [statusError,setStatusError] = useState('');
  const [checked,setChecked] = useState('');
  const mounted = useRef(true);
  const active = batches.some(b=>!['completed','stopped'].includes(b.state));
  // A paused batch reserves its manifest, but does not own the single-prompt
  // composer once its current clip has settled. Keep unresolved jobs protected.
  const blocksSingle = batches.some(b=>!['completed','stopped'].includes(b.state) &&
    (b.state !== 'paused' || b.entries.some(e=>e.job_missing || (e.job &&
      !['accepted','needs_review','failed','stale','rejected','cancelled','refinement_pending'].includes(e.job.status)))));
  useEffect(()=>{onActive?.(blocksSingle);return()=>onActive?.(false);},[blocksSingle,onActive]);
  useEffect(()=>{localStorage.setItem(storageKey,JSON.stringify({source,pending}));},[storageKey,source,pending]);
  async function refresh() {
    try {const result=await listT2VBatches(workspaceId);if(mounted.current){setBatches(result.batches);setLoaded(true);setStatusError('');setChecked(new Date().toLocaleTimeString());}}
    catch(e){if(mounted.current){setStatusError(`Could not read batch status: ${(e as Error).message}`);setLoaded(false);}}
  }
  useEffect(()=>{mounted.current=true;void refresh();const timer=window.setInterval(()=>void refresh(),4000);return()=>{mounted.current=false;window.clearInterval(timer);};},[workspaceId]);
  const changeSource=(value:string)=>{setSource(value);setPreview([]);setError('');};
  async function validate() {setBusy(true);setError('');try{const result=await validateT2VBatch(source,workspaceId);setPreview(result.entries);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  async function start() {
    setBusy(true);setError('');
    let attempt=pending;
    if(!attempt) {
      try {
        const validated=await validateT2VBatch(source,workspaceId);
        const choices:Record<string,'overwrite'|'new_take'>={};
        for(const id of validated.conflicts) {
          choices[id]=window.confirm(`Prompt ${id} already exists in this project. Overwrite ${id}.mp4?\nOK: overwrite after successful generation. Cancel: keep it and create the next numbered take.`)?'overwrite':'new_take';
        }
        attempt={key:crypto.randomUUID(),source,choices};
      } catch(e) {setError((e as Error).message);setBusy(false);return;}
    }
    // Save before POST. A lost response must be retried with the same manifest/key.
    localStorage.setItem(storageKey,JSON.stringify({source,pending:attempt}));setPending(attempt);
    try{const batch=await createT2VBatch(workspaceId,attempt.key,attempt.source,attempt.choices);setBatches(prev=>[batch,...prev.filter(b=>b.batch_id!==batch.batch_id)]);setPending(undefined);localStorage.setItem(storageKey,JSON.stringify({source}));onStarted?.();}
    catch(e){
      if(e instanceof ApiError && [400,409,422,503].includes(e.status)) {
        setPending(undefined);localStorage.setItem(storageKey,JSON.stringify({source}));
        setError(`Batch was not started: ${e.message}`);
      } else setError(`Start was not confirmed. Recover the same start; it cannot submit a duplicate batch. ${(e as Error).message}`);
    }
    finally{setBusy(false);}
  }
  async function control(batch:T2VBatch, action:'pause'|'resume'|'stop') {
    setBusy(true);setError('');try{const updated=await controlT2VBatch(batch.batch_id,action);setBatches(prev=>prev.map(b=>b.batch_id===updated.batch_id?updated:b));}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  if(!editor&&!batches.length&&!error&&!statusError) return null;
  return <section className="card settings-card" aria-label="Text to video batch">
    <h3>Text to video batch</h3>
    {editor&&<p>Generate and validate all H3 Turbo originals one at a time, then confirm model unloading. Refine all videos with LTX one at a time, then unload. Models stay loaded within each phase. Only one generation runs at a time. No references are attached.</p>}
    {editor&&<>
      <label className="field" style={{display:'grid',gap:8,marginBlock:12}}>Batch file (.md, .txt or .json)<input type="file" accept=".md,.txt,.json,text/plain,text/markdown,application/json" disabled={busy||active||!!pending} onChange={async event=>{const file=event.target.files?.[0];event.target.value='';if(!file)return;if(file.size>1_000_000){setError('Choose a file smaller than 1 MB.');return;}try{changeSource(await file.text());}catch(e){setError(`Could not read file: ${(e as Error).message}`);}}}/></label>
      <label className="field" style={{display:'grid',gap:8,marginBlock:12}}>Batch prompts<textarea style={{width:'100%',boxSizing:'border-box'}} rows={12} value={source} disabled={busy||active||!!pending} onChange={e=>changeSource(e.target.value)} placeholder={'#prompt 1: time=15sec, AR=9:16, Q1=0.6 Q2=0.98\n"Your prompt"'}/></label>
      <small>IDs can be numbers or names (letters, digits, hyphens, underscores; 1–64 characters). IDs must be unique in this file; generation follows file order. Existing project IDs offer overwrite or a new take. 5–30 seconds per clip. Q1 sets H3 source quality; Q2 sets final LTX quality. Each uses the preset’s native dimensions. Legacy Quality files keep automatic source sizing. Final quality: 0.8 Low, 0.98 Standard, 1.5 High, 2 Max. Legacy 0.4 and 0.6 keep their original smaller sizes. JSON: {`{"prompts":[{"id":1,"time":10,"AR":"9:16","Q1":0.6,"Q2":0.98,"prompt":"Your prompt"}]}`}</small>
      <div className="generation-footer"><button className="quiet-button" disabled={busy||active||!!pending||!source.trim()} onClick={()=>void validate()}>Validate batch</button><button className="generate-button" disabled={busy||disabled||!loaded||(!pending&&(active||!preview.length))} onClick={()=>void start()}>{busy?'Working…':pending?'Recover batch start':'Start batch'}</button></div>
      {!!preview.length&&<details open><summary>{preview.length} prompts validated</summary>{preview.map(e=><div key={e.number}><b>Prompt {e.number} · {e.request.duration_seconds}s · {e.request.aspect_ratio} · {e.request.source_resolution_preset!==undefined&&`H3: ${qualityDimensions(e.request.source_resolution_preset,e.request.aspect_ratio)} → `}LTX: {qualityDimensions(e.request.resolution_preset as VideoResolution,e.request.aspect_ratio as VideoAspectRatio)}</b><p style={{whiteSpace:'pre-wrap'}}>{e.request.prompt}</p></div>)}</details>}
    </>}
    <button className="quiet-button" onClick={()=>void refresh()} disabled={busy}>Refresh batch status</button>{checked&&<small role="status"> Checked at {checked}. Refresh only reads progress.</small>}
    {statusError&&<p role="alert" className="error-text">{statusError}</p>}
    {error&&<p role="alert" className="error-text">{error}</p>}
    {batches.map(batch=><div key={batch.batch_id} className="card" aria-label="Saved batch">
      <h4>{batch.completed} / {batch.entries.length} complete · {batch.state.replaceAll('_',' ')}</h4>
      {batch.reason&&<p role="status">{batch.reason}</p>}
      {!['completed','stopped','stopping'].includes(batch.state)&&<div className="generation-footer"><button className="quiet-button" disabled={busy} onClick={()=>void control(batch,batch.state==='paused'?'resume':'pause')}>{batch.state==='paused'?'Resume batch':'Pause after current clip'}</button><button className="quiet-button" disabled={busy} onClick={()=>void control(batch,'stop')}>Stop batch</button></div>}
      <details className="batch-log"><summary>Prompt log ({batch.entries.length})</summary>{batch.entries.map(entry=>{
        const job=entry.job;const video=job?.outputs?.find(o=>o.kind==='video'&&o.available!==false&&o.playback_url);
        const statusLabel=job?.status==='refinement_pending'?'Waiting for LTX video refinement':job?.status.replaceAll('_',' ')||'Waiting';
        const generating=job&&!['accepted','needs_review','failed','stale','rejected','cancelled'].includes(job.status);
        return <details key={entry.number} open={!!job&&generating}>
          <summary>Prompt {entry.number}{entry.filename?` → ${entry.filename}`:""} · {entry.request.duration_seconds}s · {entry.request.aspect_ratio} · {entry.request.source_resolution_preset!==undefined&&`Q1 ${entry.request.source_resolution_preset} · `}Q2 {entry.request.resolution_preset} · {entry.job_missing?'Saved job missing':statusLabel}</summary>
          <p style={{whiteSpace:'pre-wrap'}}>{entry.request.prompt}</p>
          {generating&&<p role="status">{!['refinement_pending','queued','recovery_required'].includes(job.status)&&<LoaderCircle size={18} className="spin"/>} {job.status==='refinement_pending'?statusLabel:job.progress?.phase||statusLabel}</p>}
          {job?.outputs?.some(o=>o.kind==='video'&&o.available===false)&&<p role="alert">Video file missing. No next prompt will be submitted.</p>}
          {job?.error&&<p role="alert">{typeof job.error==='string'?job.error:job.error.message}</p>}
          {showVideos&&video&&<DockedVideo src={video.playback_url!} label={`Batch prompt ${entry.number} video`}/>}
        </details>;
      })}</details>
    </div>)}
  </section>;
}
