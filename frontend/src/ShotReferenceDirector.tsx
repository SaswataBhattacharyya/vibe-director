import { VIDEO_QUALITIES } from './lib/video-quality';
import { useEffect, useRef, useState } from 'react';
import type { Draft } from './App';
import { getProductionSetup, getStoryPromptDrafts, getStoryScreenplay, getStoryWorkspace, listStoryScreenplays, prepareStoryPrompt, saveStoryPromptShot, getAssistedVideoClipPlan, prepareAssistedVideoClipPlan, saveProductionSetup, AssistedPlannedClip, ProductionSetup, ScreenplayRevision, StoryPromptDraftState } from './lib/story-api';
import { MediaAsset } from './lib/media-api';
import { listAllJobs, Job, WORKFLOW_ID } from './lib/video-api';

type Context = { screenplay: ScreenplayRevision; setup: ProductionSetup };
type Props = { visible: boolean; refreshKey: string; draft: Draft; assets: MediaAsset[]; assetsReady: boolean; locked: boolean; onChange: (change: (draft: Draft) => Draft) => void; onBusy: (busy: boolean) => void; onAssetsChanged: () => void };
const hash = async (text: string) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))), byte => byte.toString(16).padStart(2, '0')).join('');
export default function ShotReferenceDirector({ visible, refreshKey, draft, locked, onChange, onBusy }: Props) {
  const [context, setContext] = useState<Context | null>(null);
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [clips, setClips] = useState<AssistedPlannedClip[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [reload, setReload] = useState(0);
  const latest = useRef(draft); latest.current = draft;
  const epoch = useRef(0);
  const retryShot = useRef('');
  useEffect(() => {
    const token = ++epoch.current;
    setContext(null); setClips([]); setJobs([]); setError(''); setLoading(visible);
    if (!visible || !draft.workspaceId.startsWith('story-')) {setLoading(false);return;}
    void (async () => {
      const workspace = await getStoryWorkspace(draft.workspaceId);
      const source = workspace.current_revision_id || workspace.current_revision?.revision_id;
      if (!source) return;
      const screenplay = await getStoryScreenplay(draft.workspaceId, source);
      const [revisions, state] = await Promise.all([listStoryScreenplays(draft.workspaceId), getProductionSetup(draft.workspaceId, screenplay.screenplay_revision_id)]);
      if (!screenplay.accepted || !revisions.items.some(row => row.screenplay_revision_id === screenplay.screenplay_revision_id && row.accepted && !row.stale) || state.setup?.mode !== 'assisted_manual') return;
      const [plan, ledger] = await Promise.all([getAssistedVideoClipPlan(draft.workspaceId, screenplay.screenplay_revision_id), listAllJobs(draft.workspaceId)]);
      if (token === epoch.current) { setContext({screenplay, setup:state.setup}); setClips(plan.clips); setJobs(ledger.jobs); }
    })().catch(reason => { if (token === epoch.current) setError(`Could not load screenplay reference context: ${reason.message}`); })
      .finally(() => { if (token === epoch.current) setLoading(false); });
    return () => { epoch.current++; };
  }, [visible, draft.workspaceId, refreshKey, reload]);

  const accepted = (clip: AssistedPlannedClip) => jobs.find(job=>job.clip_id===clip.clip_id && job.status==='accepted' && job.candidate_disposition!=='discard_requested');
  const unlocked = (index: number) => clips.slice(0,index).every(clip=>Boolean(accepted(clip)));
  const planClips = async () => {
    if (!context || working || locked) return;
    setWorking(true);onBusy(true);setError(''); const token=epoch.current;
    try {
      let setup=context.setup;
      if (setup.automate_steps.video) {
        const {video_workflow_id:_workflow,...manual}=setup;
        setup={...manual,automate_steps:{...manual.automate_steps,video:false}};
        await saveProductionSetup(draft.workspaceId,context.screenplay.screenplay_revision_id,setup);
        if(token===epoch.current)setContext(previous=>previous?{...previous,setup}:previous);
        window.dispatchEvent(new Event('vibe-production-setup-changed'));
      }
      const state=await getStoryPromptDrafts(draft.workspaceId,context.screenplay.screenplay_revision_id);
      for (const scene of context.screenplay.screenplay.scenes) for (const shot of scene.shots) {
        if(token!==epoch.current)return;
        const key=`${scene.scene_number}.${shot.shot_number}`;
        const saved=state.setup_matches_current?state.drafts[key]:undefined;
        if(saved?.workflow_id===WORKFLOW_ID && saved.prompt.trim())continue;
        const prompt=await prepareStoryPrompt(draft.workspaceId,context.screenplay.screenplay_revision_id,key,WORKFLOW_ID);
        await saveStoryPromptShot(draft.workspaceId,context.screenplay.screenplay_revision_id,setup,key,{workflow_id:prompt.workflow_id,prompt:prompt.prompt,knowledge_ref:prompt.knowledge_ref,style_ref:prompt.style_ref});
      }
      await prepareAssistedVideoClipPlan(draft.workspaceId,context.screenplay.screenplay_revision_id);
      if(token===epoch.current){onChange(previous=>({...previous,directorPrepared:false,sourceLineage:undefined}));setReload(value=>value+1);}
    }catch(reason){if(token===epoch.current)setError(`Clip preparation failed: ${(reason as Error).message}`);}
    finally{setWorking(false);onBusy(false);}
  };

  const prepare = async (key: string, rebuild = false) => {
    if (!context || working || locked) return;
    const {screenplay, setup} = context;
    const planned=clips.find(clip=>clip.clip_id===key);
    if(!planned || !unlocked(clips.indexOf(planned)))return;
    const {scene_number:sceneNo,shot_number:shotNo}=planned;
    const shotKey=`${sceneNo}.${shotNo}`;
    const scene = screenplay.screenplay.scenes.find(row => row.scene_number === sceneNo);
    const shot = scene?.shots.find(row => row.shot_number === shotNo);
    if (!scene || !shot) return;
    if (rebuild && !window.confirm('Restore this clip’s planned prompt and clear its reference overrides?')) return;
    const origin = latest.current;
    const token = epoch.current;
    retryShot.current = key; setWorking(true); onBusy(true); setError('');
    try {
      let promptState: StoryPromptDraftState = await getStoryPromptDrafts(origin.workspaceId, screenplay.screenplay_revision_id);
      let saved = promptState.setup_matches_current ? promptState.drafts[shotKey] : undefined;
      if (!saved?.prompt.trim() || saved.workflow_id !== WORKFLOW_ID) throw new Error('The saved T2V shot prompt changed. Prepare screenplay clips again before continuing.');
      const sourceHash = await hash(saved.prompt);
      if (token !== epoch.current || latest.current.workspaceId !== origin.workspaceId || latest.current.clipId !== origin.clipId) return;
      onChange(previous => ({...previous, clipId:planned.clip_id, workflowId:planned.workflow_id, prompt:planned.prompt, r2vMainPrompt:planned.prompt, r2vCollatedPrompt:undefined,
        r2vImages:[],r2vAudios:[],r2vVideos:[],directorPrepared:true,directorWarnings:[],referenceReviews:{},
        duration:planned.duration_seconds,
        resolution:VIDEO_QUALITIES.find(item => item.key === setup.video_quality)!.preset,
        sourceLineage:{planned_clip_id:planned.clip_id,screenplay_revision_id:screenplay.screenplay_revision_id,setup_hash:promptState.setup_hash,scene_number:sceneNo,shot_number:shotNo,source_prompt_sha256:sourceHash,knowledge_ref:saved.knowledge_ref,style_ref:saved.style_ref},
        firstFrameAssetId:undefined,lastFrameAssetId:undefined,retakeOf:undefined,keepOriginal:undefined}));
    } catch (reason) { if (token === epoch.current) setError(`Shot preparation failed: ${(reason as Error).message}`); }
    finally { setWorking(false); onBusy(false); }
  };
  const lineage = draft.sourceLineage;
  const currentKey=lineage?.planned_clip_id || '';
  const selectedClip=clips.find(clip=>clip.clip_id===currentKey);
  useEffect(() => {
    if (visible && context && !locked && !working && !context.setup.automate_steps.video && (!lineage || lineage.screenplay_revision_id === context.screenplay.screenplay_revision_id) && (!draft.directorPrepared || !selectedClip) && !error && clips.length) void prepare(currentKey || clips.find((_,index)=>unlocked(index) && !accepted(clips[index]))?.clip_id || clips[0].clip_id);
  }, [visible, context, locked, working, currentKey, draft.directorPrepared, draft.workflowId, error, clips]);
  if (!visible) return null;
  if (loading) return <section className="card" role="status">Loading shot design and saved assignments…</section>;
  if (!context && !error) return null;
  const scene = context?.screenplay.screenplay.scenes.find(row => row.scene_number === lineage?.scene_number);
  const shot = scene?.shots.find(row => row.shot_number === lineage?.shot_number);
  const linked=Boolean(selectedClip) && lineage?.screenplay_revision_id===context?.screenplay.screenplay_revision_id;
  return <section className="card settings-card shot-director" aria-label="Shot design and Director references">
    <h3>Shot design &amp; Director references</h3>
    {context && (context.setup.automate_steps.video || !clips.length) && <><p>{context.setup.automate_steps.video?'Video automation is currently checked. Use this action to save manual video control and prepare T2V clips from your screenplay.':'Prepare duration-bounded screenplay clips. Text to video is the default. Choose references explicitly if needed. No video is submitted.'}</p><button className="primary" disabled={locked || working} onClick={()=>void planClips()}>{context.setup.automate_steps.video?'Use shot-by-shot manual T2V':'Prepare screenplay clips'}</button></>}
    {context && !context.setup.automate_steps.video && clips.length>0 && <label className="field">Screenplay shot<select aria-label="Screenplay shot" value={linked ? currentKey : ''} disabled={locked || working} onChange={event => {
      if (!event.target.value) onChange(previous => ({...previous,clipId:crypto.randomUUID(),sourceLineage:undefined,directorPrepared:false,directorWarnings:[],referenceReviews:{},prompt:'',r2vMainPrompt:'',r2vCollatedPrompt:undefined,r2vImages:[],r2vAudios:[],r2vVideos:[]}));
      else void prepare(event.target.value);
    }}><option value="">Choose current clip</option>{clips.map((clip,index)=><option key={clip.clip_id} value={clip.clip_id} disabled={!unlocked(index)}>Scene {clip.scene_number} · Shot {clip.shot_number} · Clip {clip.clip_number} · {clip.duration_seconds}s{!unlocked(index)?' · accept previous video first':''}</option>)}</select></label>}
    {linked && shot && <><b>{scene?.slugline} · {selectedClip?.duration_seconds || draft.duration}s</b><p>{selectedClip?.source_spans.filter(span=>span.field==='action').map(span=>span.text).join(' ') || shot.action}</p>{selectedClip?.source_spans.filter(span=>span.field==='dialogue').map((span,index)=><p key={index}><b>Dialogue:</b> {span.text}</p>)}<dl>{Object.entries(shot.direction).filter(([,value])=>value).map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
      <button className="quiet-button" disabled={locked || working} onClick={()=>void prepare(currentKey,true)}>Rebuild Director choices</button>
      <p>No references are attached automatically. Choose a reference workflow and add media below if needed. Changes affect this shot only and are saved on this device.</p>
      {draft.directorWarnings?.map(warning=><p role="status" key={warning}>{warning}</p>)}</>}
    {working && <p role="status">Preparing shot prompt and references…</p>}
    {error && <div role="alert">{error} <button className="quiet-button" disabled={working || locked} onClick={()=>{if(context && retryShot.current) void prepare(retryShot.current); else {setError('');setReload(value=>value+1);}}}>Retry shot context</button>{context && <button className="quiet-button" disabled={working || locked} onClick={()=>void planClips()}>Prepare screenplay clips again</button>}</div>}
  </section>;
}
