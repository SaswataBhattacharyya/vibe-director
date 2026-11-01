import { useEffect, useMemo, useState } from 'react';
import { AudioSceneCapabilities, AudioSceneClip, AudioSceneJob, createAudioSceneSplit, createAudioSceneStitch, getAudioSceneCapabilities, getAudioSceneSplit, getAudioSceneStitch, listAudioSceneSplits, listAudioSceneStitches, MediaAsset } from './lib/media-api';

type EditRange = {start:number;end:number;text:string};

export function AudioSceneSurgery({workspaceId,assets}:{workspaceId:string;assets:MediaAsset[]}) {
  const audioAssets = useMemo(()=>assets.filter(asset=>asset.kind==='audio'),[assets]);
  const [sourceId,setSourceId]=useState('');
  const [edits,setEdits]=useState<EditRange[]>([{start:0,end:1,text:''}]);
  const [transcript,setTranscript]=useState('');
  const [mode,setMode]=useState<'simple'|'timed'>('simple');
  const [replacements,setReplacements]=useState<Record<number,string>>({});
  const [gaps,setGaps]=useState<Record<number,number>>({});
  const [capabilities,setCapabilities]=useState<AudioSceneCapabilities|null>(null);
  const [split,setSplit]=useState<AudioSceneJob|null>(null);
  const [stitch,setStitch]=useState<AudioSceneJob|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');

  useEffect(()=>{void getAudioSceneCapabilities().then(setCapabilities).catch(reason=>setError((reason as Error).message));},[]);

  useEffect(()=>{if(!workspaceId){setSplit(null);setStitch(null);return;}let live=true;void Promise.all([listAudioSceneSplits(workspaceId),listAudioSceneStitches(workspaceId)]).then(([splits,stitches])=>{if(live){setSplit(splits.find(job=>['queued','running'].includes(job.status))||splits[0]||null);setStitch(stitches.find(job=>['queued','running'].includes(job.status))||stitches[0]||null);}}).catch(reason=>{if(live)setError((reason as Error).message);});return()=>{live=false;}},[workspaceId]);
  useEffect(()=>{if(!workspaceId||!split||!['queued','running'].includes(split.status))return;const timer=window.setInterval(()=>void getAudioSceneSplit(workspaceId,split.job_id).then(setSplit).catch(reason=>setError((reason as Error).message)),1500);return()=>window.clearInterval(timer);},[workspaceId,split?.job_id,split?.status]);
  useEffect(()=>{if(!workspaceId||!stitch||!['queued','running'].includes(stitch.status))return;const timer=window.setInterval(()=>void getAudioSceneStitch(workspaceId,stitch.job_id).then(setStitch).catch(reason=>setError((reason as Error).message)),1500);return()=>window.clearInterval(timer);},[workspaceId,stitch?.job_id,stitch?.status]);
  const clips:AudioSceneClip[]=split?.result?.manifest?.clips||[];
  const runSplit=async()=>{setBusy(true);setError('');try{setSplit(await createAudioSceneSplit(workspaceId,sourceId,edits,transcript||undefined));setStitch(null);}catch(reason){setError((reason as Error).message);}finally{setBusy(false);}};
  const runStitch=async()=>{if(!split)return;setBusy(true);setError('');try{setStitch(await createAudioSceneStitch(workspaceId,split.job_id,mode,replacements,gaps));}catch(reason){setError((reason as Error).message);}finally{setBusy(false);}};
  return <section className="card timed-tts-panel" aria-label="Audio scene surgery">
    <h2>Split and stitch</h2><p>Split a library clip into editable ranges, optionally replace clips, then join them.</p>
    {!workspaceId?<p>Select a workspace to use Scene Surgery.</p>:<>
      {capabilities&&<p className={capabilities.checks.split.available?'media-prep-state':'summariser-error'} role="status">{capabilities.checks.split.available?'Split tool ready':'Split tool unavailable: donor script not found.'}</p>}
      {!capabilities&&<p>Checking the copied Scene Surgery scripts…</p>}
      <label>Source audio<select aria-label="Scene surgery source audio" value={sourceId} onChange={event=>setSourceId(event.target.value)}><option value="">Choose an audio clip</option>{audioAssets.map(asset=><option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}</select></label>
      <div className="summariser-toolbar"><h3>Edit ranges</h3><button className="quiet-button" type="button" onClick={()=>setEdits(rows=>{const start=rows.length?rows[rows.length-1].end:0;return [...rows,{start,end:start+1,text:''}];})}>Add range</button></div>
      {edits.map((edit,index)=><div className="timed-tts-speaker" key={index}><label>Start (seconds)<input aria-label={`Edit ${index+1} start`} type="number" min={0} step={0.01} value={edit.start} onChange={event=>setEdits(rows=>rows.map((row,i)=>i===index?{...row,start:Number(event.target.value)}:row))}/></label><label>End (seconds)<input aria-label={`Edit ${index+1} end`} type="number" min={0} step={0.01} value={edit.end} onChange={event=>setEdits(rows=>rows.map((row,i)=>i===index?{...row,end:Number(event.target.value)}:row))}/></label><label>Replacement dialogue (optional)<input aria-label={`Edit ${index+1} text`} value={edit.text} onChange={event=>setEdits(rows=>rows.map((row,i)=>i===index?{...row,text:event.target.value}:row))}/></label><button className="quiet-button" type="button" disabled={edits.length===1} aria-label={`Remove edit ${index+1}`} onClick={()=>setEdits(rows=>rows.filter((_,i)=>i!==index))}>Remove</button></div>)}
      <label>Optional transcript<textarea aria-label="Scene surgery transcript" value={transcript} onChange={event=>setTranscript(event.target.value)} maxLength={500000}/></label>
      {error&&<p className="summariser-error" role="alert">{error}</p>}
      <button className="generate-button" type="button" disabled={busy||!capabilities?.checks.split.available||!sourceId||!edits.length||['queued','running'].includes(split?.status||'')} onClick={()=>void runSplit()}>{busy?'Working…':'Split audio'}</button>
      {split&&<p role="status">{split.message} · {split.status} · {split.progress}%</p>}{split?.error&&<p className="summariser-error">{split.error}</p>}
      {clips.length>0&&<><h3>Split clips</h3>{clips.map(clip=>{const asset=split?.result?.clips?.find(row=>row.clip_index===clip.clip_index)?.asset;return <article className="audio-scene-clip" key={clip.clip_index}><strong>Clip {clip.clip_index}</strong><span>{clip.start}s–{clip.end}s · {clip.duration}s</span>{asset&&<audio controls preload="metadata" src={asset.content_url}/>}<label>Replace with<select aria-label={`Replace clip ${clip.clip_index}`} value={replacements[clip.clip_index]||''} onChange={event=>setReplacements(current=>({...current,[clip.clip_index]:event.target.value}))}><option value="">Keep split clip</option>{audioAssets.filter(item=>item.asset_id!==sourceId).map(item=><option key={item.asset_id} value={item.asset_id}>{item.filename}</option>)}</select></label>{mode==='timed'&&<label>Gap after clip (seconds)<input type="number" min={0} max={3600} step={0.1} value={gaps[clip.clip_index]||0} onChange={event=>setGaps(current=>({...current,[clip.clip_index]:Number(event.target.value)}))}/></label>}</article>;})}
        <label>Stitch mode<select aria-label="Audio stitch mode" value={mode} onChange={event=>setMode(event.target.value as 'simple'|'timed')}><option value="simple">Simple</option><option value="timed">Timed gaps</option></select></label>{capabilities&&<p>{mode==='timed'?capabilities.checks.timed_stitch.available?'Timed stitch ready':'Timed stitch script unavailable.':capabilities.checks.simple_stitch.available?'Simple stitch ready':'Simple stitch script unavailable.'}</p>}<button className="generate-button" type="button" disabled={busy||!capabilities?.checks[mode==='timed'?'timed_stitch':'simple_stitch'].available||['queued','running'].includes(stitch?.status||'')} onClick={()=>void runStitch()}>{busy?'Working…':'Stitch clips'}</button>
      </>}
      {stitch&&<p role="status">{stitch.message} · {stitch.status} · {stitch.progress}%</p>}{stitch?.error&&<p className="summariser-error">{stitch.error}</p>}{stitch?.result?.asset&&<audio controls preload="metadata" src={stitch.result.asset.content_url}/>}
    </>}
  </section>;
}
