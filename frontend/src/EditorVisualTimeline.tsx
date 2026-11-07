import {useEffect, useRef, useState} from 'react';
import {editorApi, type EditorPlan, type EditorProject, type EditorRange} from './lib/editor-api';
import EditorClipEffects from './EditorClipEffects';

type Preview = {revision:number; duration:number; document:string};
export default function EditorVisualTimeline({project, plan, disabled, onChange, onSave, canSave}:{
  project:EditorProject; plan:EditorPlan; disabled:boolean; onChange:(plan:EditorPlan)=>void; onSave:()=>void; canSave:boolean;
}) {
  const [selected,setSelected]=useState(0),[expanded,setExpanded]=useState(false);
  const [preview,setPreview]=useState<Preview|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const [position,setPosition]=useState(0),[playing,setPlaying]=useState(false),[ready,setReady]=useState(false);
  const frame=useRef<HTMLIFrameElement>(null),version=useRef(0);
  const fingerprint=JSON.stringify(plan);
  const needsCpuPreview=plan.clips.some(clip=>(clip.effect?.preset||'none')!=='none'||(clip.speed?.start??1)!==1||(clip.speed?.end??1)!==1);
  // A response to an older plan/session may never replace the current preview.
  useEffect(()=>{version.current++;setPreview(null);setReady(false);setPlaying(false);setPosition(0);setLoading(false);setError('');},[fingerprint,project.id,project.revision]);
  useEffect(()=>{
    const receive=(event:MessageEvent)=>{
      if(event.source!==frame.current?.contentWindow||event.data?.type!=='vibe-editor-preview')return;
      if(event.data.error){setError(String(event.data.error));setReady(false);return;}
      if(Number.isFinite(event.data.time)){setReady(true);setPosition(event.data.time);setPlaying(Boolean(event.data.playing));}
    };
    window.addEventListener('message',receive);
    return()=>{version.current++;window.removeEventListener('message',receive);};
  },[]);
  useEffect(()=>{
    if(!expanded)return;
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')setExpanded(false);};
    window.addEventListener('keydown',escape);return()=>window.removeEventListener('keydown',escape);
  },[expanded]);
  const loadPreview=async()=>{
    const current=++version.current;setLoading(true);setError('');
    try{const result=await editorApi<Preview>(`projects/${project.id}/preview`,'POST',{revision:project.revision,plan});
      if(current===version.current){setPreview(result);setReady(false);}}
    catch(e){if(current===version.current)setError((e as Error).message);}
    finally{if(current===version.current)setLoading(false);}
  };
  const transport=(action:string,time?:number)=>frame.current?.contentWindow?.postMessage({type:'vibe-editor-transport',action,time},'*');
  const index=Math.min(selected,plan.clips.length-1),clip=plan.clips[index];
  const change=(patch:Partial<EditorRange>)=>onChange({...plan,clips:plan.clips.map((row,i)=>i===index?{...row,...patch}:row)});
  const move=(step:number)=>{
    const next=index+step;if(next<0||next>=plan.clips.length)return;
    const clips=[...plan.clips];[clips[index],clips[next]]=[clips[next],clips[index]];
    clips[clips.length-1]={...clips[clips.length-1],transition:{kind:'cut',duration:0}};
    onChange({...plan,clips});setSelected(next);
  };
  return <section className={`editor-visual ${expanded?'editor-visual-expanded':''}`} aria-label="Visual timeline">
    <div className="editor-visual-toolbar"><h2>Visual Editor</h2><button type="button" aria-expanded={expanded} onClick={()=>setExpanded(value=>!value)}>{expanded?'Collapse visual editor':'Expand visual editor'}</button></div>
    <p>Edit the shared plan, then save it below for a new media and tool clearance. Preview does not save or render.</p>
    <div className="editor-visual-preview" style={{aspectRatio:`${plan.width}/${plan.height}`}}>
      {preview?<iframe title="HyperFrames plan preview" ref={frame} sandbox="allow-scripts" srcDoc={preview.document}/>:<p>Load a preview of this timeline.</p>}
    </div>
    <div className="editor-visual-toolbar"><button disabled={disabled||loading||needsCpuPreview} onClick={()=>void loadPreview()}>{loading?'Loading preview…':'Load HyperFrames preview'}</button>
      <button disabled={!ready} onClick={()=>transport(playing?'pause':'play')}>{playing?'Pause timeline':'Play timeline'}</button>
      <output>{position.toFixed(2)} / {(preview?.duration||0).toFixed(2)} s</output>
    </div>
    <input type="range" aria-label="Seek timeline preview" min="0" max={preview?.duration||0} step={1/plan.fps} value={position} disabled={!ready} onChange={e=>{setPosition(Number(e.target.value));transport('seek',Number(e.target.value));}}/>
    {error&&<p role="alert">{error}</p>}
    {needsCpuPreview&&<p role="status">The selected plan contains filters or speed changes. Review and approve the plan for a CPU render to see those effects accurately.</p>}
    <small>HyperFrames-powered preview supports unfiltered 1× clips, captions and transitions. The complete native HyperFrames Studio GUI is not connected yet.</small>
    <div className="editor-visual-track" aria-label="Visual clip order">{plan.clips.map((row,i)=><button type="button" key={i} aria-pressed={i===index} onClick={()=>setSelected(i)} style={{flexGrow:Math.max(.1,row.render_duration??row.end-row.start)}}>
      <b>{i+1}. {row.filename||row.asset_id}</b><span>{row.start.toFixed(2)}–{row.end.toFixed(2)} s</span>
    </button>)}</div>
    {clip&&<fieldset disabled={disabled}><legend>Selected visual clip {index+1}</legend><div className="editor-visual-fields">
      <label>Source in (seconds)<input type="number" min="0" step=".01" value={clip.start} onChange={e=>change({start:Number(e.target.value)})}/></label>
      <label>Source out (seconds)<input type="number" min=".01" step=".01" value={clip.end} onChange={e=>change({end:Number(e.target.value)})}/></label>
      <label>Visual caption<input value={clip.caption||''} onChange={e=>change({caption:e.target.value})}/></label>
      <label>Visual framing<select value={clip.fit||'contain'} onChange={e=>change({fit:e.target.value})}><option value="contain">Contain</option><option value="cover">Cover</option></select></label>
    </div><EditorClipEffects clip={clip} last={index===plan.clips.length-1} onChange={updated=>onChange({...plan,clips:plan.clips.map((row,i)=>i===index?updated:row)})}/><button disabled={index===0} onClick={()=>move(-1)}>Move selected clip earlier</button><button disabled={index===plan.clips.length-1} onClick={()=>move(1)}>Move selected clip later</button></fieldset>}
    <button disabled={disabled||!canSave} onClick={onSave}>Save visual timeline proposal</button>
  </section>;
}
