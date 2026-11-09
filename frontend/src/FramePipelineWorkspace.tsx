import {useEffect, useRef, useState} from 'react';
import {TaskCard} from './DirectorConversation';
import {agentRequest, exactApproval, type AgentTask} from './lib/agent-tasks';
import MediaSourcePicker from './MediaSourcePicker';
import './frame-pipeline.css';

type Key = {key_id:string;review:string;job_status?:string;request?:{prompt:string;seed:number};error?:{message?:string};image?:{asset_id:string;width:number;height:number}};
type Take = {take_id:string;revision:number;keys:Key[];parent?:{take_id:string;key_id:string}};
type State = {takes:Take[];interpolation:{models:string[];reason?:string}};

export default function FramePipelineWorkspace({workspaceId}:{workspaceId:string}) {
  return <FramePanel key={workspaceId} owner={workspaceId}/>;
}
function FramePanel({owner}:{owner:string}) {
  const controller=useRef(new AbortController());
  const [data,setData]=useState<State>({takes:[],interpolation:{models:[]}}), [takeId,setTakeId]=useState('');
  const [prompt,setPrompt]=useState(''),[seed,setSeed]=useState(1),[model,setModel]=useState('rife');
  const [multiplier,setMultiplier]=useState(4),[fps,setFps]=useState(24),[hold,setHold]=useState(0);
  const [normalize,setNormalize]=useState(true);
  const [task,setTask]=useState<AgentTask|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const take=data.takes.find(t=>t.take_id===takeId)||data.takes[0];
  const api=async<T,>(path='',body?:unknown):Promise<T>=>{
    const response=await fetch(`/api/frame-pipeline/${encodeURIComponent(owner)}${path}`,{signal:controller.current.signal,
      ...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
    const result=await response.json();if(!response.ok)throw new Error(result?.error?.message||'Frame request failed.');return result;
  };
  const refresh=async()=>setData(await api<State>());
  useEffect(()=>{
    const current=new AbortController();controller.current=current;
    void Promise.all([refresh(),agentRequest<{tasks:AgentTask[]}>(owner,'tasks',current.signal).then(result=>{
      if(current.signal.aborted)return;
      const found=result.tasks.find(t=>['image.generate_next_keyframe','video.interpolate_keyframes','video.export_frame_sequence'].includes(t.plan.tool_id));if(found)setTask(found);
    })]).catch(e=>{if(!current.signal.aborted)setError(e.message);});
    return()=>current.abort();
  },[]);
  const action=async(work:()=>Promise<void>)=>{setBusy(true);setError('');try{await work();}catch(e){if(!controller.current.signal.aborted)setError((e as Error).message);}finally{if(!controller.current.signal.aborted)setBusy(false);}};
  useEffect(()=>{
    if(!task?.invocation?.job_id)return;
    let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{try{
      const next=await agentRequest<AgentTask>(owner,`tasks/${task.task_id}`,controller.current.signal);setTask(next);
      await refresh();
      if(['running','submitting','cancel_requested'].includes(next.status))timer=setTimeout(()=>void poll(),2000);
    }catch(e){if(!controller.current.signal.aborted)setError((e as Error).message);}};
    void poll();return()=>clearTimeout(timer);
  },[task?.task_id,task?.invocation?.job_id,task?.status]);
  useEffect(()=>{if(!take?.keys.some(k=>k.job_status&&['queued','preparing','submitting','running'].includes(k.job_status)))return;const timer=setTimeout(()=>void action(refresh),2500);return()=>clearTimeout(timer);},[data]);
  const change=async(body:object)=>{if(!take)return;const result=await api<Take>(`/takes/${take.take_id}`,{revision:take.revision,...body});setTakeId(result.take_id);await refresh();};
  const propose=async(tool_id:string,settings:object)=>{if(!take)return;setTask(await api<AgentTask>('/propose',{tool_id,settings:{take_id:take.take_id,revision:take.revision,...settings}}));};
  const control=async(row:AgentTask,verb:'approve'|'run'|'cancel')=>action(async()=>{
    setTask(await agentRequest<AgentTask>(owner,`tasks/${row.task_id}/${verb}`,controller.current.signal,verb==='cancel'?{}:exactApproval(row)));await refresh();
  });
  const active=take?.keys.filter(k=>k.review!=='rejected')||[],ready=active.length>0&&active.every(k=>k.review==='approved');
  const sequence=task?.plan.tool_id==='video.interpolate_keyframes'&&task.status==='completed'?task.invocation?.job_id:null;
  return <details className="card frame-pipeline"><summary>Reviewed keyframes → silent video</summary>
    <p>Develop one continuous shot. Kontext is recommended for changing an approved frame while preserving its visual identity. Review each candidate; branch from an earlier approved key to rewind without deleting work.</p>
    <p>Kontext uses native aspect buckets. Prepare the starting canvas before editing; the original remains in your library. Interpolation connects approved keys within one shot; it does not infer movement across cuts.</p>
    {error&&<p role="alert">{error}</p>}
    <div className="frame-pipeline-controls"><button disabled={busy} onClick={()=>void action(refresh)}>Refresh takes</button>
      <label>Take<select value={take?.take_id||''} disabled={busy} onChange={e=>{setTakeId(e.target.value);setTask(null);}}><option value="">Choose a take</option>{data.takes.map(t=><option key={t.take_id} value={t.take_id}>{t.take_id.slice(-8)} · revision {t.revision}{t.parent?' · branch':''}</option>)}</select></label>
    </div>
    <label><input type="checkbox" checked={normalize} onChange={e=>setNormalize(e.target.checked)}/> Prepare new take in a Kontext aspect bucket (CPU resize and center crop; separate image for review)</label>
    <MediaSourcePicker workspaceId={owner} kinds={['image']} compact disabled={busy}
      destination={{kind:'model_reference',slot:'new take starting image',capacity:1,onSelect:items=>action(async()=>{
        const result=await api<Take>('/takes',{asset_id:items[0].asset_id,normalize});setTakeId(result.take_id);setTask(null);await refresh();
      })}}/>
    {take&&<>
      <MediaSourcePicker workspaceId={owner} kinds={['image']} compact disabled={busy||!ready&&active.length>0}
        destination={{kind:'model_reference',slot:'append candidate to current take',capacity:1,onSelect:items=>action(()=>change({operation:'append',asset_id:items[0].asset_id}))}}/>
      <div className="frame-pipeline-keys">{take.keys.map((key,index)=><article key={key.key_id}>
        {key.image&&<a href={`/api/media/${encodeURIComponent(owner)}/assets/${key.image.asset_id}/content`} target="_blank" rel="noreferrer"><img src={`/api/media/${encodeURIComponent(owner)}/assets/${key.image.asset_id}/content`} alt={`Keyframe ${index+1}`}/></a>}
        <b>Key {index+1} · {key.review}</b><small>{key.image?`${key.image.width} × ${key.image.height}`:key.job_status||'queued'}</small>
        {key.request&&<small>{key.request.prompt}<br/>Seed {key.request.seed}</small>}
        {key.error?.message&&<small>{key.error.message}</small>}
        {key.review==='candidate'&&<div><button disabled={busy||!key.image} onClick={()=>void action(()=>change({operation:'review',key_id:key.key_id,decision:'approved'}))}>Approve key</button><button disabled={busy||!key.image&&!['failed','cancelled'].includes(key.job_status||'')} onClick={()=>void action(()=>change({operation:'review',key_id:key.key_id,decision:'rejected'}))}>Reject</button></div>}
        {key.review==='approved'&&<button disabled={busy} onClick={()=>void action(()=>change({operation:'branch',key_id:key.key_id}))}>Branch here</button>}
      </article>)}</div>
      <label>Next-frame edit<textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Describe what changes; specify what should stay the same."/></label>
      <div className="frame-pipeline-controls"><label>Seed<input type="number" min="0" max="4294967295" value={seed} onChange={e=>setSeed(Number(e.target.value))}/></label><button disabled={busy||!ready||!prompt.trim()} onClick={()=>void action(()=>propose('image.generate_next_keyframe',{prompt,seed}))}>Prepare Kontext candidate task</button></div>
      <div className="frame-pipeline-controls"><label>Interpolator<select value={model} onChange={e=>setModel(e.target.value)}><option value="rife">RIFE</option><option value="film">FILM</option></select></label><label>Multiplier<input type="number" min="2" max="16" value={multiplier} onChange={e=>setMultiplier(Number(e.target.value))}/></label><label>Frames / second<input type="number" min="1" max="60" value={fps} onChange={e=>setFps(Number(e.target.value))}/></label><label>Hold at each end (seconds)<input type="number" min="0" max="10" step="0.1" value={hold} onChange={e=>setHold(Number(e.target.value))}/></label></div>
      <p>{data.interpolation.models.length?`Installed interpolators: ${data.interpolation.models.join(', ')}`:data.interpolation.reason||'No interpolation model detected.'} Duration = ((keys − 1) × multiplier + 1) / fps, plus rounded endpoint holds.</p>
      {active.length>=2&&Number.isFinite(fps)&&fps>0&&<p>Planned output: {(active.length-1)*multiplier+1+2*Math.round(hold*fps)} frames · {(((active.length-1)*multiplier+1+2*Math.round(hold*fps))/fps).toFixed(2)} seconds, including holds.</p>}
      {ready&&active.length>=2&&<a href={`#/video?workspace_id=${encodeURIComponent(owner)}&frame_take=${take.take_id}&frame_revision=${take.revision}`}>Use approved endpoints in a new First + Last Frame video draft</a>}
      <button disabled={busy||!ready||active.length<2||!data.interpolation.models.includes(model)} onClick={()=>void action(()=>propose('video.interpolate_keyframes',{model,multiplier,fps,hold}))}>Prepare interpolation task</button>
      {sequence&&<button disabled={busy} onClick={()=>void action(()=>propose('video.export_frame_sequence',{sequence_job_id:sequence}))}>Prepare MP4 + lossless export</button>}
    </>}
    {task&&<TaskCard task={task} busy={busy} control={control}/>}
    {task?.status==='recovery_required'&&task.plan.tool_id==='video.interpolate_keyframes'&&task.invocation?.job_id&&<button disabled={busy} onClick={()=>void action(async()=>{
      await api(`/jobs/${task.invocation!.job_id}/reconcile`,{});
      setTask(await agentRequest<AgentTask>(owner,`tasks/${task.task_id}`,controller.current.signal));
    })}>Reconcile saved interpolation (no resubmission)</button>}
    {task?.status==='completed'&&task.plan.tool_id==='video.export_frame_sequence'&&task.invocation?.job_id&&<a href={`/api/frame-pipeline/${encodeURIComponent(owner)}/jobs/${task.invocation.job_id}/lossless`}>Download lossless FFV1 master</a>}
  </details>;
}
