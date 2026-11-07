import {useEffect, useRef, useState} from 'react';
import {editorApi, type EditorProject} from './lib/editor-api';

type Segment = {start:number; end:number; text:string; avg_logprob:number; no_speech_prob:number};
type Source = {task_id:string; job_id:string; asset_id:string; sha256:string; filename:string;
  transcript:{duration_seconds:number; segments:Segment[]}};

/** Playback and exact segment selection; the server derives all retained ranges. */
export default function EditorSpeechReview({project, disabled, onSaved}:{
  project:EditorProject; disabled:boolean; onSaved:()=>Promise<void>;
}) {
  const [sources,setSources]=useState<Source[]>([]), [sourceId,setSourceId]=useState('');
  const [chosen,setChosen]=useState<number[]>([]), [busy,setBusy]=useState(false), [message,setMessage]=useState('');
  const player=useRef<HTMLVideoElement>(null), version=useRef(0);
  useEffect(()=>{version.current++;setSources([]);setSourceId('');setChosen([]);setMessage('');setBusy(false);
    return()=>{version.current++;};},[project.id,project.revision]);
  const source=sources.find(row=>row.task_id===sourceId);
  const load=async()=>{
    const request=version.current;setBusy(true);setMessage('');
    try {
      const result=await editorApi<{revision:number; sources:Source[]}>(`projects/${project.id}/speech`);
      if(request!==version.current)return;
      if(result.revision!==project.revision)throw new Error('Editor revision changed. Refresh saved state first.');
      setSources(result.sources);setSourceId(result.sources[0]?.task_id||'');setChosen([]);
      if(!result.sources.length)setMessage('No completed speech evidence for the selected sources. Ask the Director to analyze the complete source, approve and run the task, then load evidence here.');
    }catch(error){if(request===version.current)setMessage((error as Error).message);}
    finally{if(request===version.current)setBusy(false);}
  };
  const save=async()=>{
    if(!source)return;
    const request=version.current;setBusy(true);setMessage('');
    try {
      await editorApi(`projects/${project.id}/speech-cuts`,'POST',{
        revision:project.revision, task_id:source.task_id, segment_indices:chosen,
      });
      if(request===version.current)await onSaved();
    }catch(error){if(request===version.current)setMessage((error as Error).message);}
    finally{if(request===version.current)setBusy(false);}
  };
  return <details className="editor-speech-review"><summary>Review speech and propose cuts</summary>
    <p>Review the original playback before selecting speech to remove. Confidence alone does not identify a mistake. Only selected edit ranges are retained; use the complete source range in Asset selection when needed.</p>
    <button disabled={disabled||busy||!project.id} onClick={()=>void load()}>Load completed speech evidence</button>
    {message&&<p role="status">{message}</p>}
    {!!sources.length&&<label>Analyzed source<select disabled={disabled||busy} value={sourceId} onChange={e=>{setSourceId(e.target.value);setChosen([]);}}>{sources.map(row=><option key={row.task_id} value={row.task_id}>{row.filename}</option>)}</select></label>}
    {source&&<>
      <video ref={player} key={source.task_id} controls playsInline preload="metadata" aria-label="Speech source playback"
        src={`/api/media/${encodeURIComponent(project.workspace_id)}/assets/${encodeURIComponent(source.asset_id)}/content`}/>
      <small>{source.filename} · complete source {source.transcript.duration_seconds.toFixed(2)}s · {source.task_id} · {source.sha256.slice(0,12)}</small>
      <div className="editor-speech-segments">{source.transcript.segments.map((row,i)=>
        <div key={i} className="editor-speech-segment">
          <label><input type="checkbox" disabled={disabled||busy} checked={chosen.includes(i)} aria-label={`Remove speech segment ${i+1}`}
            onChange={e=>setChosen(ids=>e.target.checked?[...ids,i]:ids.filter(n=>n!==i))}/><span>{row.start.toFixed(3)}–{row.end.toFixed(3)}s · {row.text}</span></label>
          <button type="button" disabled={busy} onClick={()=>{if(player.current){player.current.currentTime=row.start;void player.current.play().catch(()=>{});}}}>Play segment {i+1}</button>
          <small>Average log probability {row.avg_logprob.toFixed(2)} · no-speech probability {row.no_speech_prob.toFixed(2)}</small>
        </div>)}</div>
      <p>{chosen.length} segment(s) marked for removal. All other selected footage and its original audio stay in order. This creates a new proposal; clearance 2 is required before rendering.</p>
      {!project.brief&&<p>Approve the creative brief before saving cuts.</p>}
      <button disabled={disabled||busy||!chosen.length||!project.brief} onClick={()=>void save()}>Save reviewed cuts as proposal</button>
    </>}
  </details>;
}
