import {useProjectState} from './lib/project-state';
import OutputDestination from './OutputDestination';
import MediaSourcePicker from './MediaSourcePicker';
import {useEffect,useState} from 'react';
import {Music2} from 'lucide-react';
import {createMusicJob,getMusicCapabilities,getMusicJob,getWorkflowGuidance,listMediaAssets,listMusicJobs,MediaAsset,MusicCapabilities,MusicJob,WorkflowGuidance} from './lib/media-api';
import {listStoryWorkspaces,StoryWorkspace} from './lib/story-api';
import {preferredMediaWorkspaceId,defaultMediaWorkspaceId} from './lib/media-workspace';
import AceStudioPage from './AceStudioPage';
import MusicJukebox from './MusicJukebox';

export default function MusicSoundPage({onBack}:{onBack:()=>void}) {
  const [tool,setTool]=useState<'ace'|'jukebox'|'foley'>('ace');
  useEffect(()=>{const open=()=>setTool('jukebox');window.addEventListener('vibe-jukebox-open',open);return()=>window.removeEventListener('vibe-jukebox-open',open);},[]);
  return <><button className="quiet-button summariser-back" type="button" onClick={onBack}>← Audio tools</button><nav className="summariser-tabs" aria-label="Music and sound tools"><button type="button" className={tool==='ace'?'selected':''} onClick={()=>setTool('ace')}>ACE-Step Music</button><button type="button" className={tool==='jukebox'?'selected':''} onClick={()=>setTool('jukebox')}>Music Jukebox</button><button type="button" className={tool==='foley'?'selected':''} onClick={()=>setTool('foley')}>Control-Foley</button></nav>{tool==='ace'?<AceStudioPage/>:tool==='jukebox'?<MusicJukebox onAce={()=>setTool('ace')}/>:<ControlFoleyPage onBack={onBack}/>}</>;
}
function ControlFoleyPage({onBack}:{onBack:()=>void}) {
  const [,setWorkspaces]=useState<StoryWorkspace[]>([]);const [workspaceId,setWorkspaceId]=useState(defaultMediaWorkspaceId);
  const [cap,setCap]=useState<MusicCapabilities|null>(null);const [assets,setAssets]=useState<MediaAsset[]>([]);
  const [workflowGuidance,setWorkflowGuidance]=useState<WorkflowGuidance|null>(null);const [guidanceError,setGuidanceError]=useState('');
  const [jobs,setJobs]=useState<MusicJob[]>([]);const [active,setActive]=useState<MusicJob|null>(null);
  const [videoId,setVideoId]=useState('');const [audioId,setAudioId]=useState('');const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
  const [foley,setFoley]=useProjectState<{mode:string;prompt:string;negative_prompt:string;duration:number;seed:number;steps:'fixed'|number;guidance:number;fps:number;device:string;precision:string}>('ControlFoley:settings',{mode:'text_audio',prompt:'',negative_prompt:'',duration:8,seed:42,steps:'fixed',guidance:4.5,fps:24,device:'auto',precision:'bf16'});
  useEffect(()=>{void Promise.all([listStoryWorkspaces(),getMusicCapabilities()]).then(([result,ready])=>{
    const rows=result.items||[];setWorkspaces(rows);const requestedWorkspace=new URLSearchParams(window.location.hash.split('?')[1]||'').get('workspace_id')||'';setWorkspaceId(preferredMediaWorkspaceId(rows,requestedWorkspace));setCap(ready);
  }).catch(error=>setMessage((error as Error).message));},[]);
  useEffect(()=>{if(!workspaceId)return;let live=true;void Promise.all([listMediaAssets(workspaceId,'video'),listMediaAssets(workspaceId,'audio'),listMusicJobs(workspaceId,'control-foley')]).then(([videos,audios,rows])=>{
    if(!live)return;setAssets([...videos.assets,...audios.assets]);setJobs(rows);setActive(current=>current?rows.find(row=>row.job_id===current.job_id)||current:rows[0]||null);
  }).catch(error=>{if(live)setMessage((error as Error).message);});return()=>{live=false;};},[workspaceId]);
  const guidanceWorkflow=foley.mode==='text_audio'?'control_foley_text_audio_v1':foley.mode==='text_video_audio'?'control_foley_text_video_audio_v1':'control_foley_reference_video_audio_v1';
  const guidanceModel='control_foley';
  const currentGuidance=workflowGuidance?.workflow_id===guidanceWorkflow&&workflowGuidance.model_id===guidanceModel?workflowGuidance:null;
  useEffect(()=>{let live=true;setWorkflowGuidance(null);setGuidanceError('');void getWorkflowGuidance(guidanceWorkflow,guidanceModel).then(value=>{if(live)setWorkflowGuidance(value);}).catch(error=>{if(live)setGuidanceError((error as Error).message);});return()=>{live=false;};},[guidanceWorkflow,guidanceModel]);
  useEffect(()=>{if(!workspaceId||!active||!['queued','running','cancel_requested'].includes(active.status))return;let live=true;const timer=window.setInterval(()=>void getMusicJob(workspaceId,'control-foley',active.job_id).then(job=>{if(live){setActive(job);setJobs(rows=>[job,...rows.filter(row=>row.job_id!==job.job_id)]);}}).catch(error=>{if(live)setMessage((error as Error).message);}),2500);return()=>{live=false;window.clearInterval(timer);};},[workspaceId,active?.job_id,active?.status]);
  const promptKnowledgeRef=currentGuidance?.retrieval_status==='matched'&&currentGuidance.knowledge_id&&currentGuidance.guidance_version!==null&&currentGuidance.workflow_sha256?{knowledge_id:currentGuidance.knowledge_id,guidance_version:currentGuidance.guidance_version,workflow_sha256:currentGuidance.workflow_sha256}:null;
  const [destinationReady,setDestinationReady]=useState(false);
  const submit=async()=>{if(!promptKnowledgeRef){setMessage('Wait for matching workflow guidance before generating audio.');return;}setBusy(true);setMessage('');try{const job=await createMusicJob(workspaceId,'control-foley',foley,promptKnowledgeRef,{video_asset_id:videoId||undefined,audio_asset_id:audioId||undefined});setActive(job);setJobs(rows=>[job,...rows.filter(row=>row.job_id!==job.job_id)]);}catch(error){setMessage((error as Error).message);}finally{setBusy(false);}};
  const ready=cap?.control_foley.status==='available'&&cap.workflow_files.control_foley;
  const videoOptions=assets.filter(asset=>asset.kind==='video');const audioOptions=assets.filter(asset=>asset.kind==='audio');
  const foleyNeedsPrompt=foley.mode!=='reference_video_audio';const missingFoleyInput=(foleyNeedsPrompt&&!foley.prompt.trim())||(foley.mode!=='text_audio'&&!videoId)||(foley.mode==='reference_video_audio'&&!audioId);
  const guidanceSources=currentGuidance?.sources.reduce<typeof currentGuidance.sources>((rows,source)=>{
    if(!rows.some(row=>row.uri===source.uri&&row.section===source.section&&row.version===source.version))rows.push(source);
    return rows;
  },[])||[];
  const guidancePanel=<details className="workflow-guidance" open><summary>Workflow guidance</summary><p>Source-linked facts from this Vibe adapter and workflow. They describe local inputs and limits, not undocumented vendor prompt syntax.</p>{guidanceError?<p role="status">Guidance could not be loaded: {guidanceError}</p>:!currentGuidance?<p role="status">Loading guidance…</p>:currentGuidance.retrieval_status!=='matched'?<p role="status">No curated guidance is available for this workflow and model.</p>:<><p>Guidance v{currentGuidance.guidance_version} · workflow {currentGuidance.workflow_version}</p><ul>{currentGuidance.nodes.map(node=><li key={node.node_id}><strong>{node.kind.replaceAll('_',' ')}:</strong> {node.text}</li>)}</ul><details><summary>Evidence sources</summary><ul>{guidanceSources.map((source,index)=><li key={`${source.uri}:${source.section}:${index}`}>{source.uri} · {source.section} · {source.version}</li>)}</ul></details></>}</details>;
  return <section className="card summariser-page" aria-label="Music and Sound">
    <button className="quiet-button summariser-back" type="button" onClick={onBack}>← Audio tools</button>
    <header className="summariser-heading"><div><div className="eyebrow">MEDIA PREP / MUSIC &amp; SOUND</div><h1>Control-Foley</h1><p>Generate sound effects with ComfyUI.</p></div><span className="media-prep-state">{ready?'Ready':cap?'Workflow unavailable':'Connection not loaded'}</span></header>
    {message&&<p className="notice" role="status">{message}</p>}
    <p className="project-context-label">Current project · change with New project or Load project above</p>
    {foley.mode!=='text_audio'&&<MediaSourcePicker workspaceId={workspaceId} kinds={foley.mode==='reference_video_audio'?['video','audio']:['video']} disabled={busy} onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/>}
    <section className="card audio-music-form"><h2>Control-Foley</h2><p>Describe a sound or guide it with media from this workspace.</p>
      {guidancePanel}
      <label>Mode<select aria-label="Control-Foley mode" value={foley.mode} onChange={event=>{setFoley(row=>({...row,mode:event.target.value}));setVideoId('');setAudioId('');}}><option value="text_audio">Text → Audio</option><option value="text_video_audio">Text + Video → Audio</option><option value="reference_video_audio">Reference Audio + Video → Audio</option></select></label>
      {foleyNeedsPrompt&&<label>Sound description<textarea aria-label="Sound description" maxLength={4000} value={foley.prompt} onChange={event=>setFoley(row=>({...row,prompt:event.target.value}))} placeholder="Describe the sound to create"/></label>}
      {foley.mode!=='text_audio'&&<label>Video reference<select aria-label="Foley video reference" value={videoId} onChange={event=>setVideoId(event.target.value)}><option value="">Choose a project video</option>{videoOptions.map(asset=><option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}</select></label>}
      {foley.mode==='reference_video_audio'&&<label>Audio reference<select aria-label="Foley audio reference" value={audioId} onChange={event=>setAudioId(event.target.value)}><option value="">Choose a project audio clip</option>{audioOptions.map(asset=><option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}</select></label>}
      <div className="summariser-toolbar"><label>Duration (0.7–30 sec)<input type="number" min={0.7} max={30} step="0.1" value={foley.duration} onChange={event=>setFoley(row=>({...row,duration:Number(event.target.value)}))}/></label><label>Seed<input type="number" min={0} value={foley.seed} onChange={event=>setFoley(row=>({...row,seed:Number(event.target.value)}))}/></label><label>Guidance<input type="number" min={0} max={20} step="0.1" value={foley.guidance} onChange={event=>setFoley(row=>({...row,guidance:Number(event.target.value)}))}/></label><label>FPS<input type="number" min={1} max={120} value={foley.fps} onChange={event=>setFoley(row=>({...row,fps:Number(event.target.value)}))}/></label></div>
      <details><summary>Advanced settings</summary><div className="summariser-toolbar"><label>Negative prompt<textarea aria-label="Control-Foley negative prompt" maxLength={4000} value={foley.negative_prompt} onChange={event=>setFoley(row=>({...row,negative_prompt:event.target.value}))} placeholder="Describe sounds to avoid"/></label><label>Inference steps<select aria-label="Control-Foley inference steps" value={String(foley.steps)} onChange={event=>setFoley(row=>({...row,steps:event.target.value==='fixed'?'fixed':event.target.value==='custom'?40:Number(event.target.value)}))}><option value="fixed">Workflow default</option><option value="20">20</option><option value="30">30</option><option value="50">50</option><option value="custom">Custom</option></select></label>{typeof foley.steps==='number'&&![20,30,50].includes(foley.steps)&&<label>Custom inference steps (1–100)<input aria-label="Custom Control-Foley inference steps" type="number" min={1} max={100} value={foley.steps} onChange={event=>setFoley(row=>({...row,steps:Number(event.target.value)}))}/></label>}</div></details>
      {cap?.control_foley&&<details><summary>Workflow readiness</summary><p>{cap.control_foley.status}; model {cap.control_foley.model_ready?'found':'missing'}; API workflows {cap.control_foley.workflow_ready?'found':'missing'}; missing nodes: {cap.control_foley.missing_nodes.join(', ')||'none'}{cap.control_foley.reason?`; ${cap.control_foley.reason}`:''}</p></details>}
    </section>
    <OutputDestination tool="control-foley" onReady={setDestinationReady} workspaceId={workspaceId} disabled={busy}/>
    <button className="generate-button" type="button" disabled={busy||!destinationReady||!ready||!workspaceId||!promptKnowledgeRef||missingFoleyInput} onClick={()=>void submit()}><Music2 size={15}/>{busy?'Starting…':'Generate audio'}</button>
    {active&&<article className="card summariser-job-detail"><h3>{active.message}</h3><p>{active.status} · {active.progress}%</p><progress max="100" value={active.progress}/>{active.error&&<pre className="summariser-error">{active.error.slice(0,2000)}</pre>}{active.result?.asset&&<><h3>Saved to Audio Clips</h3><p>{active.result.asset.filename}</p><audio src={active.result.asset.content_url} controls preload="metadata"/></>}</article>}
    {jobs.length>1&&<details><summary>Earlier Music &amp; Sound jobs ({jobs.length-1})</summary>{jobs.slice(1).map(job=><p key={job.job_id}>{job.message} · {job.status}</p>)}</details>}
  </section>;
}
