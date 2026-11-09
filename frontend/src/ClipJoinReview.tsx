import {useEffect, useRef, useState} from 'react';
import {TaskCard} from './DirectorConversation';
import {agentRequest, exactApproval, type AgentTask} from './lib/agent-tasks';
import {editorApi, type EditorProject} from './lib/editor-api';
import './clip-join.css';

type Evidence = {task_id:string;comparison:{status:string;reason:string;score:number|null;overlap_seconds:number|null;
  timing_uncertainty_seconds:number;limitations:string;evidence:Array<{a_seconds:number;b_seconds:number}>;
  suggested_ranges:Array<{start:number;end:number}>|null}};

/** Uses the same task approvals and Editor revision as the shared Director. */
export default function ClipJoinReview({project, disabled, capability, onChanged}:{project:EditorProject;disabled:boolean;
  capability?:{ready:boolean;message:string};onChanged:()=>Promise<void>}) {
  const [task,setTask]=useState<AgentTask|null>(null), [evidence,setEvidence]=useState<Evidence|null>(null);
  const [busy,setBusy]=useState(false), [error,setError]=useState('');
  const generation=useRef(0), players=useRef<Array<HTMLVideoElement|null>>([]);
  const ids=project.selection.map(r=>r.asset_id), identity=JSON.stringify(ids);
  const valid=ids.length===2&&ids[0]!==ids[1]&&project.selection.every(r=>r.mime?.startsWith('video/'));
  useEffect(()=>{
    const current=++generation.current, controller=new AbortController();
    setTask(null);setEvidence(null);setError('');setBusy(false);
    if(valid)void agentRequest<{tasks:AgentTask[]}>(project.workspace_id,'tasks',controller.signal).then(result=>{
      if(current!==generation.current)return;
      const found=result.tasks.find(t=>t.plan.tool_id==='video.compare_clip_overlap'&&JSON.stringify(t.plan.assets.map(a=>a.asset_id))===identity);
      if(found)setTask(found);
    }).catch(e=>{if(!controller.signal.aborted)setError(e.message);});
    return()=>{generation.current++;controller.abort();};
  },[project.id,project.revision,identity,valid]);
  useEffect(()=>{
    if(!task?.invocation?.job_id)return;
    const controller=new AbortController(), current=generation.current;
    let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{
      try{
        const row=await agentRequest<AgentTask>(project.workspace_id,`tasks/${task.task_id}`,controller.signal);
        if(current!==generation.current)return;
        setTask(row);
        if(row.status==='completed'){
          const result=await editorApi<{revision:number;sources:Evidence[]}>(`projects/${project.id}/overlap`);
          if(current===generation.current&&result.revision===project.revision)setEvidence(result.sources[0]||null);
        }else if(['running','submitting','cancel_requested'].includes(row.status))timer=setTimeout(()=>void poll(),1200);
      }catch(e){if(!controller.signal.aborted&&current===generation.current)setError((e as Error).message);}
    };
    void poll();return()=>{controller.abort();clearTimeout(timer);};
  },[task?.task_id,task?.invocation?.job_id,project.revision]);
  const action=async(work:()=>Promise<void>)=>{
    const current=generation.current;setBusy(true);setError('');
    try{await work();}catch(e){if(current===generation.current)setError((e as Error).message);}
    finally{if(current===generation.current)setBusy(false);}
  };
  const compare=()=>action(async()=>{
    const current=generation.current;
    const row=await agentRequest<AgentTask>(project.workspace_id,'tasks',new AbortController().signal,
      {tool_id:'video.compare_clip_overlap',asset_ids:ids,settings:{window_seconds:3}});
    if(current===generation.current){setTask(row);setEvidence(null);}
  });
  const control=(row:AgentTask, name:'approve'|'run'|'cancel')=>void action(async()=>{
    const current=generation.current;
    const result=await agentRequest<AgentTask>(project.workspace_id,`tasks/${row.task_id}/${name}`,new AbortController().signal,
      name==='cancel'?{}:exactApproval(row));
    if(current===generation.current)setTask(result);
  });
  return <details className="clip-join-review"><summary>Compare and stitch two clips · Kdenlive</summary>
    <p>Attach exactly two videos in order: A then B. Compare searches the last three seconds of A against the first three seconds of B. Approval runs CPU analysis only.</p>
    <ol>{project.selection.map((r,i)=><li key={i}>{i===0?'A':i===1?'B':i+1} · {r.filename||r.asset_id} · selected {r.start}–{r.end}s</li>)}</ol>
    <button disabled={disabled||busy||!valid||Boolean(task&&['running','submitting','cancel_requested'].includes(task.status))} onClick={()=>void compare()}>Compare clip boundaries</button>
    {!valid&&<p>Select two distinct video sources to compare their boundaries.</p>}
    {task&&<TaskCard task={task} busy={busy||disabled} control={control}/>}
    {error&&<p role="alert">{error}</p>}
    {evidence&&<section aria-label="Clip overlap evidence"><h3>{evidence.comparison.status.replaceAll('_',' ')}</h3>
      <p>{evidence.comparison.reason}</p><p>{evidence.comparison.limitations}</p>
      {evidence.comparison.overlap_seconds!==null&&<p>Repeated sequence: approximately {evidence.comparison.overlap_seconds.toFixed(3)}s · sampling uncertainty ±{evidence.comparison.timing_uncertainty_seconds.toFixed(3)}s. Similarity {evidence.comparison.score}.</p>}
      <div className="clip-join-players">{ids.map((id,i)=><video key={id} ref={node=>{players.current[i]=node;}} aria-label={`Overlap source ${i===0?'A':'B'}`} controls playsInline preload="metadata" src={`/api/media/${encodeURIComponent(project.workspace_id)}/assets/${encodeURIComponent(id)}/content`}/>)}</div>
      {evidence.comparison.evidence.map((pair,i)=><button key={i} onClick={()=>{players.current.forEach((p,n)=>{if(p){p.pause();p.currentTime=n===0?pair.a_seconds:pair.b_seconds;}});}}>Inspect A {pair.a_seconds.toFixed(3)}s / B {pair.b_seconds.toFixed(3)}s</button>)}
      {evidence.comparison.suggested_ranges?<><p>Keep A through its end. Remove B’s repeated opening, retaining {evidence.comparison.suggested_ranges[1].start.toFixed(3)}–{evidence.comparison.suggested_ranges[1].end.toFixed(3)}s within your selection. Original audio stays linked; review for an audible click.</p>
        <button disabled={disabled||busy||!capability?.ready} onClick={()=>void action(async()=>{await editorApi(`projects/${project.id}/join`,'POST',{revision:project.revision,task_id:evidence.task_id});await onChanged();})}>Prepare Kdenlive join preview</button>
      </>:<p>No automatic trim proposed. Choose ranges manually in the visual editor.</p>}
    </section>}
    {!capability?.ready&&<p>{capability?.message||'Kdenlive runtime status unavailable. Refresh saved state.'}</p>}
    {project.join_preview?.revision===project.revision&&<figure><figcaption>Kdenlive join preview · inspect picture and audio before approving clearance 2</figcaption><video controls playsInline src={project.join_preview.asset.content_url} aria-label="Kdenlive join preview"/></figure>}
    {project.output?.backend==='kdenlive'&&<a href={`/api/editor/projects/${project.id}/kdenlive-project`} download>Download editable Kdenlive project</a>}
  </details>;
}
