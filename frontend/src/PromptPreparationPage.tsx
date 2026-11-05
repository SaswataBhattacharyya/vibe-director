import {managedProjectId} from './lib/media-workspace';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Copy, RefreshCw } from 'lucide-react';
import SelectionMicroEdit from './SelectionMicroEdit';
import PromptDirector from './PromptDirector';
import type {PromptChange} from './lib/prompt-director-api';
import { FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID, WORKFLOW_ID } from './lib/video-api';
import { getProductionSetup, getStoryPromptDrafts, getStoryScreenplay, getStoryWorkspace, prepareStoryPrompt, ProductionSetupState, saveStoryPromptDrafts, ScreenplayRevision, StoryPromptDraft, StoryPromptKnowledgeRef, StoryPromptStyleRef } from './lib/story-api';
import { listMediaAssets, MediaAsset } from './lib/media-api';
import { AssistedClipPlanState, AssistedVideoReference, AssistedVideoReferenceMap, getAssistedVideoClipPlan, prepareAssistedVideoClipPlan, saveAssistedVideoClipReferences, saveAssistedVideoClipPrompt } from './lib/story-api';
import './prompt-preparation.css';

type WorkflowId = typeof WORKFLOW_ID | typeof FL2VA_WORKFLOW_ID | typeof R2V_WORKFLOW_ID;
type PromptDraft = { prompt: string; workflowId: WorkflowId; knowledgeRef?: StoryPromptKnowledgeRef; styleRef?: StoryPromptStyleRef };
const VIDEO_HANDOFF_KEY = 'vibe-story-video-handoff-v1';
const workflowNames: Record<WorkflowId, string> = { [WORKFLOW_ID]: 'Text to video (T2V)', [FL2VA_WORKFLOW_ID]: 'First and last frame (FFL2VA)', [R2V_WORKFLOW_ID]: 'Reference to video (R2V)' };
const codepoints = (text: string) => Array.from(text).length;
async function storyClipId(workspaceId: string, revisionId: string, scene: number, shot: number) {
  const bytes = new TextEncoder().encode(`${workspaceId}\0${revisionId}\0${scene}\0${shot}`);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const hex = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
  return `story-${hex.slice(0, 40)}`;
}
async function promptSha256(prompt: string) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(prompt));
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

function basePrompt(scene: ScreenplayRevision['screenplay']['scenes'][number], shot: ScreenplayRevision['screenplay']['scenes'][number]['shots'][number], workflowId: WorkflowId) {
  const lines = [
    `Scene ${scene.scene_number}: ${scene.slugline}`,
    scene.summary && `Story context: ${scene.summary}`,
    shot.action && `Action: ${shot.action}`,
    shot.dialogue && `Dialogue: ${shot.dialogue}`,
    shot.direction.camera && `Camera: ${shot.direction.camera}`,
    shot.direction.lighting && `Lighting: ${shot.direction.lighting}`,
    shot.direction.mood && `Mood: ${shot.direction.mood}`,
    shot.direction.sfx && `Sound effects: ${shot.direction.sfx}`,
    shot.direction.music && `Music: ${shot.direction.music}`,
  ].filter(Boolean) as string[];
  const instruction = workflowId === FL2VA_WORKFLOW_ID
    ? 'Connect the supplied first and last frames into one continuous shot. Preserve the action and visual direction above.'
    : workflowId === R2V_WORKFLOW_ID
      ? 'Use the selected reference media according to its stated role and intent. Follow this shot direction for the generated video.'
      : 'Create one continuous cinematic video shot that follows this screenplay direction.';
  return [...lines, instruction].join('\n\n');
}

export default function PromptPreparationPage() {
  const [workspaceId, setWorkspaceId] = useState('');
  const [revision, setRevision] = useState<ScreenplayRevision | null>(null);
  const [setup, setSetup] = useState<ProductionSetupState | null>(null);
  const [drafts, setDrafts] = useState<Record<string, PromptDraft>>({});
  const [savedDrafts, setSavedDrafts] = useState<Record<string, PromptDraft>>({});
  const [savedSetupHash, setSavedSetupHash] = useState('');
  const [savingNow, setSaving] = useState(false);
  const [directorBusy, setDirectorBusy] = useState(false);
  const saving = savingNow || directorBusy;
  const [preparingShot, setPreparingShot] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [referenceAssets, setReferenceAssets] = useState<MediaAsset[]>([]);
  const [assistedPlan, setAssistedPlan] = useState<AssistedClipPlanState | null>(null);
  const [clipEdits, setClipEdits] = useState<Record<string,string>>({});
  const [savingClip, setSavingClip] = useState('');
  const [planningClips, setPlanningClips] = useState(false);
  const [planError, setPlanError] = useState('');
  const [referenceMaps, setReferenceMaps] = useState<Record<string, AssistedVideoReference[]>>({});
  const [savedReferenceMaps, setSavedReferenceMaps] = useState<Record<string, AssistedVideoReference[]>>({});
  const [referenceChoice, setReferenceChoice] = useState<Record<string, string>>({});
  const [savingReferenceMaps, setSavingReferenceMaps] = useState(false);
  const refreshInFlight = useRef(false);
  const saveInFlight = useRef(false);
  const hasUnsavedDrafts = JSON.stringify(drafts) !== JSON.stringify(savedDrafts);

  const refresh = async () => {
    if (refreshInFlight.current || saveInFlight.current) return;
    refreshInFlight.current = true;
    setLoading(true); setError(''); setNotice('');
    try {
      const id = managedProjectId() || new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || localStorage.getItem('vibe-story-selected-v1') || '';
      if (!id) throw new Error('Open a saved story and accept its current screenplay first.');
      setWorkspaceId(id);
      const workspace = await getStoryWorkspace(id);
      const sourceId = workspace.current_revision_id || workspace.current_revision?.revision_id;
      if (!sourceId) throw new Error('This story has no current source revision.');
      const current = await getStoryScreenplay(id, sourceId);
      if (!current.accepted) throw new Error('Review and accept the current screenplay before preparing prompts.');
      const [setupState, revisions] = await Promise.all([
        getProductionSetup(id, current.screenplay_revision_id),
        fetch(`/api/story/workspaces/${encodeURIComponent(id)}/screenplay/revisions?limit=50&offset=0`).then(async response => {
          if (!response.ok) throw new Error(`Could not check screenplay revision status (${response.status}).`);
          return response.json() as Promise<{ items: Array<{ screenplay_revision_id: string; source_revision_id: string; accepted: boolean; stale: boolean }> }>;
        }),
      ]);
      const latest = revisions.items?.find(item => item.source_revision_id === sourceId && !item.stale);
      if (!latest || latest.screenplay_revision_id !== current.screenplay_revision_id || !latest.accepted) throw new Error('This is not the latest accepted screenplay for the current story. Return to Screenplay and accept the current revision.');
      if (!setupState.setup) throw new Error('Save Automation & Parameters before preparing prompts.');
      setRevision(current); setSetup(setupState);
      if (setupState.setup) {
        const workflow = setupState.setup.video_workflow_id;
        const [images, maps, videos, audios] = await Promise.all([
          setupState.setup.mode === 'assisted_manual' ? listMediaAssets(id, 'image') : Promise.resolve({assets:[]}), getAssistedVideoClipPlan(id, current.screenplay_revision_id),
          workflow === R2V_WORKFLOW_ID ? listMediaAssets(id, 'video') : Promise.resolve({assets:[]}),
          workflow === R2V_WORKFLOW_ID ? listMediaAssets(id, 'audio') : Promise.resolve({assets:[]}),
        ]);
        setReferenceAssets([...images.assets, ...videos.assets, ...audios.assets]);
        setAssistedPlan(maps); setClipEdits({});
        setReferenceMaps(maps.references || {}); setSavedReferenceMaps(maps.references || {});
      } else {
        setReferenceAssets([]); setAssistedPlan(null); setReferenceMaps({}); setSavedReferenceMaps({});
      }
      const saved = await getStoryPromptDrafts(id, current.screenplay_revision_id);
      setSavedSetupHash(saved.setup_hash);
      const restored = Object.fromEntries(Object.entries(saved.drafts || {}).map(([key, value]) => [key, { prompt: value.prompt, workflowId: value.workflow_id as WorkflowId, knowledgeRef: value.knowledge_ref, styleRef: value.style_ref }]));
      setSavedDrafts(saved.setup_matches_current ? restored : {});
      if (saved.setup_matches_current && Object.keys(restored).length) {
        setDrafts(restored);
      } else {
        const initial: Record<string, PromptDraft> = {};
        current.screenplay.scenes.forEach(scene => scene.shots.forEach(shot => {
          const id = `${scene.scene_number}.${shot.shot_number}`;
          const workflowId = setupState.setup?.mode === 'fully_automated'
            ? WORKFLOW_ID
            : setupState.setup?.automate_steps.video
              ? setupState.setup.video_workflow_id as WorkflowId
              : WORKFLOW_ID;
          initial[id] = { workflowId, prompt: basePrompt(scene, shot, workflowId) };
        }));
        setDrafts(initial);
        if (Object.keys(restored).length && !saved.setup_matches_current) setNotice('Setup changed since these prompts were saved. Review and save refreshed drafts for the current setup.');
      }
    } catch (e) { setRevision(null); setSetup(null); setError((e as Error).message); }
    finally { refreshInFlight.current = false; setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);
  const reload = () => {
    if (preparingShot) return;
    if (hasUnsavedDrafts && !window.confirm('Discard unsaved prompt edits and reload the current screenplay and setup?')) return;
    void refresh();
  };

  const update = (shotKey: string, value: Partial<PromptDraft>) => setDrafts(current => {
    const previous = current[shotKey];
    const next = { ...previous, ...value };
    if (value.workflowId && value.workflowId !== previous?.workflowId) { delete next.knowledgeRef; delete next.styleRef; }
    return { ...current, [shotKey]: next };
  });
  const prepareWithCodex = async (shotKey: string, workflowId: WorkflowId) => {
    if (!workspaceId || !revision || preparingShot || saving || loading) return;
    setPreparingShot(shotKey); setError(''); setNotice('');
    try {
      const result = await prepareStoryPrompt(workspaceId, revision.screenplay_revision_id, shotKey, workflowId);
      if (drafts[shotKey]?.workflowId !== workflowId) return;
      update(shotKey, { prompt: result.prompt, workflowId: result.workflow_id as WorkflowId, knowledgeRef: result.knowledge_ref, styleRef: result.style_ref });
      setNotice(`Prepared Scene/Shot ${shotKey} using workflow guidance v${result.knowledge_ref.guidance_version} and ${result.sources.length} linked source entries. Review, edit, then save.`);
    } catch (e) { setError((e as Error).message); }
    finally { setPreparingShot(''); }
  };
  const save = async () => {
    if (!workspaceId || !revision || !setup?.setup || saving || loading || preparingShot || saveInFlight.current || refreshInFlight.current) return;
    saveInFlight.current = true;
    setSaving(true); setError(''); setNotice('');
    try {
      const outgoing: Record<string, StoryPromptDraft> = Object.fromEntries(Object.entries(drafts).map(([key, value]) => [key, { prompt: value.prompt, workflow_id: value.workflowId, ...(value.knowledgeRef ? { knowledge_ref: value.knowledgeRef } : {}), ...(value.styleRef ? { style_ref: value.styleRef } : {}) }]));
      const result = await saveStoryPromptDrafts(workspaceId, revision.screenplay_revision_id, setup.setup, outgoing);
      setSavedDrafts(Object.fromEntries(Object.entries(outgoing).map(([key, value]) => [key, { prompt: value.prompt, workflowId: value.workflow_id as WorkflowId, knowledgeRef: value.knowledge_ref, styleRef: value.style_ref }]))); setSavedSetupHash(result.setup_hash); setNotice(`Prompt drafts saved for screenplay ${result.screenplay_revision_id} and the current setup.`);
    } catch (e) { setError((e as Error).message); }
    finally { saveInFlight.current = false; setSaving(false); }
  };
  const updateReferenceIntent = (key: string, assetId: string, intent: string) => setReferenceMaps(current => ({
    ...current, [key]: (current[key] || []).map(ref => ref.asset_id === assetId ? {...ref, intent} as AssistedVideoReference : ref),
  }));
  const updateReferenceSpeaker = (key: string, assetId: string, speaker_id: string | null) => setReferenceMaps(current => ({
    ...current, [key]: (current[key] || []).map(ref => ref.asset_id === assetId && ref.kind === 'audio' ? {...ref, speaker_id} : ref),
  }));
  const addReference = (key: string, role = 'character') => {
    const asset = referenceAssets.find(item => item.asset_id === referenceChoice[key]);
    if (!asset || (referenceMaps[key] || []).some(ref => ref.asset_id === asset.asset_id)) return;
    const ref: AssistedVideoReference = asset.kind === 'image'
      ? {kind:'image', asset_id:asset.asset_id, sha256:asset.sha256, role, intent:role === 'first_frame' || role === 'last_frame' ? `Use as the clip's ${role.replace('_',' ')}.` : 'Use this image as a visual reference.'}
      : asset.kind === 'video'
        ? {kind:'video', asset_id:asset.asset_id, sha256:asset.sha256, role:'style', intent:'Use this video as a visual reference.', start_sec:null, end_sec:null, include_paired_soundtrack:false, audio_intent:''}
        : {kind:'audio', asset_id:asset.asset_id, sha256:asset.sha256, role:'voice', intent:'Use this audio as a voice reference.', speaker_id:null};
    setReferenceMaps(current => ({...current, [key]: [...(current[key] || []), ref]}));
  };
  const setClipFrame = (clipId: string, role: 'first_frame'|'last_frame') => {
    const asset = referenceAssets.find(item => item.asset_id === referenceChoice[clipId] && item.kind === 'image');
    if (!asset) return;
    const ref: AssistedVideoReference = {kind:'image',asset_id:asset.asset_id,sha256:asset.sha256,role,
      intent:`Use as the clip's ${role.replace('_',' ')}.`};
    setReferenceMaps(current => ({...current,[clipId]:[...(current[clipId] || []).filter(item => item.kind !== 'image' || item.role !== role),ref]}));
  };
  const saveReferences = async () => {
    if (!workspaceId || !revision || !assistedPlan?.clips.length || savingReferenceMaps || JSON.stringify(referenceMaps) === JSON.stringify(savedReferenceMaps)) return;
    setSavingReferenceMaps(true); setError('');
    try {
      const clips: AssistedVideoReferenceMap[] = assistedPlan.clips.map(clip => ({clip_id:clip.clip_id, references:referenceMaps[clip.clip_id] || []}));
      const result = await saveAssistedVideoClipReferences(workspaceId, revision.screenplay_revision_id, clips);
      setAssistedPlan(result);
      const saved = result.references || {};
      setReferenceMaps(saved); setSavedReferenceMaps(saved); setNotice('References saved for each planned clip.');
    } catch (e) { setError((e as Error).message); }
    finally { setSavingReferenceMaps(false); }
  };
  const planAssistedClips = async () => {
    if (!workspaceId || !revision || planningClips || hasUnsavedDrafts) return;
    const discardReferences = Object.keys(savedReferenceMaps).length > 0;
    if (discardReferences && !window.confirm('Replanning discards the references mapped to the current clips. Continue?')) return;
    setPlanningClips(true); setPlanError('');
    try {
      const result = await prepareAssistedVideoClipPlan(workspaceId, revision.screenplay_revision_id, discardReferences);
      setAssistedPlan(result); setReferenceMaps(result.references || {}); setSavedReferenceMaps(result.references || {});
      setClipEdits({}); setNotice(`${result.clips.length} clip prompts prepared. Review, edit and save them before continuing.`);
    } catch (e) { setPlanError((e as Error).message); }
    finally { setPlanningClips(false); }
  };
  const saveClip = async (clipId: string) => {
    const clip = assistedPlan?.clips.find(item => item.clip_id === clipId);
    if (!clip || !revision || savingClip) return;
    setSavingClip(clipId); setPlanError('');
    try {
      const result = await saveAssistedVideoClipPrompt(workspaceId, revision.screenplay_revision_id, clipId, clip.prompt, clipEdits[clipId] ?? clip.prompt);
      setAssistedPlan(result); setClipEdits(current => { const next = {...current}; delete next[clipId]; return next; });
      setNotice('Clip prompt saved. Generation will use this exact text.');
    } catch(e) { setPlanError((e as Error).message); }
    finally { setSavingClip(''); }
  };
  const copyPrompt = async (key: string) => {
    try { await navigator.clipboard.writeText(drafts[key]?.prompt || ''); setNotice(`Copied Scene/Shot ${key} prompt.`); }
    catch { setNotice('Clipboard access is unavailable. Select and copy the prompt text.'); }
  };
  const openInVideo = async (key: string, workflowId: WorkflowId) => {
    if (!workspaceId || !revision || !setup || !savedSetupHash) return;
    const saved = savedDrafts[key];
    const draft = drafts[key];
    if (!saved || !draft || saved.prompt !== draft.prompt || saved.workflowId !== draft.workflowId) return;
    const [sceneNumber, shotNumber] = key.split('.').map(Number);
    const [clipId, sourcePromptSha256] = await Promise.all([
      storyClipId(workspaceId, revision.screenplay_revision_id, sceneNumber, shotNumber),
      promptSha256(saved.prompt),
    ]);
    localStorage.setItem(VIDEO_HANDOFF_KEY, JSON.stringify({ workspace_id: workspaceId,
      screenplay_revision_id: revision.screenplay_revision_id, setup_hash: savedSetupHash,
      scene_number: sceneNumber, shot_number: shotNumber, source_prompt_sha256: sourcePromptSha256, workflow_id: workflowId,
      knowledge_ref: saved.knowledgeRef,
      style_ref: saved.styleRef,
      prompt: saved.prompt, clip_id: clipId }));
    window.location.hash = '#/video';
  };
  const summary = useMemo(() => revision?.screenplay.scenes.reduce((total, scene) => total + scene.shots.length, 0) || 0, [revision]);

  const unsavedClips = assistedPlan?.clips.some(clip => clipEdits[clip.clip_id] !== undefined && clipEdits[clip.clip_id] !== clip.prompt);
  const unsavedReferences = JSON.stringify(referenceMaps) !== JSON.stringify(savedReferenceMaps);
  // Asset preparation precedes the final clip plan in assisted mode. Only the
  // route into Current Take requires a current production clip plan here.
  const requiresClipPlan = setup?.setup?.mode === 'fully_automated';
  const continueBlockedReason = loading || saving || preparingShot || planningClips || savingClip || savingReferenceMaps
    ? 'Wait for the current operation to finish.'
    : hasUnsavedDrafts || unsavedClips || unsavedReferences
      ? 'Save your prompt and reference edits before continuing.'
      : requiresClipPlan && (!assistedPlan?.clips.length || !assistedPlan.setup_matches_current)
        ? 'Prepare and review the per-clip prompts before continuing to Current Take.'
        : '';
  const canContinue = !continueBlockedReason;

  return <main className="content-wrap prompt-preparation-page">
    <div className="page-heading"><div><div className="eyebrow">STORY WORKFLOW · PROMPTS</div><h1>Prompt Preparation</h1><p>{revision ? `${revision.screenplay.title} · accepted screenplay ${revision.screenplay_revision_id}` : 'Prompts derived from the accepted screenplay.'}</p></div><button className="quiet-button" type="button" onClick={reload} disabled={loading || saving || Boolean(preparingShot)} title={hasUnsavedDrafts ? 'Reloading will ask before discarding unsaved prompt edits.' : ''}><RefreshCw size={15}/> Reload</button></div>
    {error && <section className="card prompt-blocked" role="alert"><b>{revision && setup ? 'Prompt save failed' : 'Prompt preparation is locked'}</b><p>{error}</p>{!(revision && setup) && <a className="quiet-button" href="#/setup">Automation &amp; Parameters</a>}</section>}
    {notice && <p role="status" className="prompt-notice">{notice}</p>}
    {loading && <section className="card">Loading the current screenplay and saved setup…</section>}
    {revision && setup && <>
      <PromptDirector key={`${workspaceId}:${revision.screenplay_revision_id}`} workspace={workspaceId} revision={revision.screenplay_revision_id}
        shotPrompts={Object.fromEntries(Object.entries(drafts).map(([key,value])=>[key,value.prompt]))}
        shotWorkflows={Object.fromEntries(Object.entries(drafts).map(([key,value])=>[key,value.workflowId]))}
        disabled={savingNow||loading||!!preparingShot||planningClips||!!savingClip}
        onBusy={setDirectorBusy} onApplyShots={(changes:PromptChange[])=>{
          setDrafts(current=>{
            const next={...current};
            for(const change of changes){const key=change.key.slice(5);if(next[key]?.prompt===change.before)next[key]={...next[key],prompt:change.value};}
            return next;
          });
        }}/>
      <section className="card prompt-stage-summary"><div><b>{summary} shot prompts</b><span>Derived from scene action, dialogue, camera, lighting, mood, sound effects and music.</span></div><span className="prompt-revision-badge">{setup.setup?.mode === 'fully_automated' ? 'Fully automated route' : 'Assisted manual'}</span></section>
      <p className="prompt-boundary-note">Save the shot briefs, then prepare and review each production clip below. Start run uses the saved clip prompts. Changed screenplay or settings require preparing the clips again.</p>
      {revision.screenplay.scenes.map((scene, sceneIndex) => <section className="card prompt-scene" key={`${scene.scene_number}-${sceneIndex}`}>
        <header><div><div className="eyebrow">SCENE {scene.scene_number}</div><h2>{scene.slugline}</h2><p>{scene.summary}</p></div></header>
        {scene.shots.map(shot => {
          const key = `${scene.scene_number}.${shot.shot_number}`;
          const draft = drafts[key] || { prompt: basePrompt(scene, shot, WORKFLOW_ID), workflowId: WORKFLOW_ID };
          const count = codepoints(draft.prompt);
          const fullAutomatic = setup.setup?.mode === 'fully_automated';
          const workflowLocked = fullAutomatic || (setup.setup?.mode === 'assisted_manual' && setup.setup.automate_steps.video);
          const videoAutomated = workflowLocked;
          return <article className="prompt-shot" key={key}>
            <div className="prompt-shot-heading"><div><h3>Shot {shot.shot_number}</h3><span>{draft.workflowId === WORKFLOW_ID ? 'Text prompt' : draft.workflowId === FL2VA_WORKFLOW_ID ? 'Prompt plus first/last frame inputs' : 'Base prompt; references are added in Video'}</span></div>
              <label>Workflow<select aria-label={`Workflow for scene ${scene.scene_number} shot ${shot.shot_number}`} disabled={workflowLocked || saving || loading || Boolean(preparingShot)} value={draft.workflowId} onChange={event => { const workflowId = event.target.value as WorkflowId; update(key, { workflowId }); }}>
                {Object.entries(workflowNames).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
              </select></label>
            </div>
            {setup.setup?.mode === 'assisted_manual' && setup.setup.automate_steps.video && <p className="prompt-route-note">All shot prompts use the run's selected {setup.setup.video_workflow_id === FL2VA_WORKFLOW_ID ? 'FFLF' : 'R2V'} workflow.</p>}
            {!fullAutomatic && <button type="button" className="text-button" disabled={saving || loading || Boolean(preparingShot)} onClick={() => update(key, { prompt: basePrompt(scene, shot, draft.workflowId) })}>Reset prompt from screenplay</button>}
            <button type="button" className="quiet-button" disabled={saving || loading || Boolean(preparingShot)} onClick={() => void prepareWithCodex(key, draft.workflowId)}>{preparingShot === key ? 'Preparing with Codex…' : 'Prepare with Codex'}</button>
            <p className="prompt-route-note">{draft.knowledgeRef ? `Workflow guidance v${draft.knowledgeRef.guidance_version} · linked to this prompt` : 'Not yet prepared with the selected workflow guidance.'}</p>
            {fullAutomatic && <p className="prompt-route-note">Fully automated uses text to video for every clip. Background, characters, speakers, dialogue and sound must be described in text. No media references are supplied.</p>}
            <SelectionMicroEdit label={`Prompt for scene ${scene.scene_number} shot ${shot.shot_number}`} value={draft.prompt} surface="prompt" workspaceId={workspaceId} revisionId={revision.screenplay_revision_id} fieldKey={key} disabled={saving||loading||Boolean(preparingShot)} onChange={value=>update(key,{prompt:value})}/>
            <div className="prompt-shot-footer"><span className={count >= 7000 ? 'prompt-count prompt-count-error' : 'prompt-count'}>{count.toLocaleString()} / 6,999 characters</span><button type="button" className="quiet-button" disabled={saving || loading || Boolean(preparingShot)} onClick={() => void copyPrompt(key)}><Copy size={14}/> Copy prompt</button>{!videoAutomated && <button type="button" className="quiet-button" disabled={saving || loading || Boolean(preparingShot) || count >= 7000 || !savedSetupHash || !savedDrafts[key] || savedDrafts[key].prompt !== draft.prompt || savedDrafts[key].workflowId !== draft.workflowId} onClick={() => void openInVideo(key, draft.workflowId)}>Open in Video</button>}</div>
            {videoAutomated && <p className="prompt-route-note">Per-shot manual submission is disabled for this automated video run.</p>}
            {count >= 7000 && <p className="prompt-limit-error" role="alert">MiniMax prompts must be shorter than 7,000 Unicode code points. Shorten this prompt before using it in Video.</p>}
          </article>;
        })}
      </section>)}
      {<section className="card assisted-clip-plan" aria-label="Assisted clip plan">
        <header><div><div className="eyebrow">PRODUCTION CLIP PROMPTS</div><h2>Prepare and review every clip</h2><p>The Director splits each shot into clips within the saved duration limits. Each saved prompt is the text sent for generation.</p></div>
          <button type="button" className="generate-button" onClick={() => void planAssistedClips()} disabled={planningClips || hasUnsavedDrafts || saving || loading}>{planningClips ? 'Planning…' : assistedPlan?.clips.length ? 'Prepare clips again' : 'Prepare per-clip prompts'}</button>
        </header>
        {planError && <p role="alert" className="prompt-limit-error">{planError}</p>}
        {assistedPlan?.clips.length && !assistedPlan.setup_matches_current ? <p role="alert">Saved clip prompts are stale. Save the current shot briefs and prepare clips again.</p> : null}
        {assistedPlan?.clips.map(clip => <article className="prompt-reference-map" key={clip.clip_id} aria-label={`References for Scene ${clip.scene_number}, Shot ${clip.shot_number}, Clip ${clip.clip_number}`}>
          <h3>Scene {clip.scene_number} · Shot {clip.shot_number} · Clip {clip.clip_number}</h3><p>{clip.duration_seconds}s · {clip.duration_reason}</p>
          <p>{clip.source_spans.map(span => span.text).join(' ')}</p><SelectionMicroEdit label={`Prompt for planned clip ${clip.clip_id}`} value={clipEdits[clip.clip_id] ?? clip.prompt} surface="prompt" workspaceId={workspaceId} revisionId={revision.screenplay_revision_id} fieldKey={clip.clip_id} disabled={Boolean(savingClip) || planningClips || hasUnsavedDrafts || !assistedPlan.setup_matches_current} onChange={value => setClipEdits(current => ({...current,[clip.clip_id]:value}))}/>
          <button type="button" className="quiet-button" disabled={Boolean(savingClip) || planningClips || hasUnsavedDrafts || !assistedPlan.setup_matches_current || !clipEdits[clip.clip_id]?.trim() || codepoints(clipEdits[clip.clip_id]) >= 7000 || clipEdits[clip.clip_id] === clip.prompt} onClick={() => void saveClip(clip.clip_id)}>{savingClip === clip.clip_id ? 'Saving…' : 'Save clip prompt'}</button>
          {clip.workflow_id === R2V_WORKFLOW_ID ? <>
            {(setup.setup?.style_video_references || []).map(ref => <p className="prompt-route-note" key={ref.asset_id}>Run-level style video · {referenceAssets.find(asset => asset.asset_id === ref.asset_id)?.filename || ref.asset_id}: {ref.intent}</p>)}
            <div className="prompt-reference-add"><select aria-label={`Reference asset for clip ${clip.clip_id}`} value={referenceChoice[clip.clip_id] || ''} onChange={event => setReferenceChoice(current => ({...current,[clip.clip_id]:event.target.value}))}>
              <option value="">Choose a workspace asset</option>{referenceAssets.filter(asset => !(setup.setup?.style_video_references || []).some(ref => ref.asset_id === asset.asset_id)).map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.kind} · {asset.filename}</option>)}
            </select><button type="button" className="quiet-button" disabled={!referenceChoice[clip.clip_id]} onClick={() => addReference(clip.clip_id)}>Add reference</button></div>
            {(referenceMaps[clip.clip_id] || []).map(ref => <div className={`prompt-reference-row${ref.kind === 'audio' ? ' audio-reference-row' : ''}`} key={ref.asset_id}>
              <span>{ref.kind} · {referenceAssets.find(asset => asset.asset_id === ref.asset_id)?.filename || ref.asset_id}</span>
              <input aria-label={`Reference intent for ${ref.asset_id}`} value={ref.intent} maxLength={500} onChange={event => updateReferenceIntent(clip.clip_id, ref.asset_id, event.target.value)} />
              {ref.kind === 'audio' && <input aria-label={`Speaker ID for ${ref.asset_id}`} value={ref.speaker_id || ''} placeholder="Speaker ID (optional)" maxLength={80} onChange={event => updateReferenceSpeaker(clip.clip_id, ref.asset_id, event.target.value.trim() || null)} />}
              <button type="button" className="text-button" onClick={() => setReferenceMaps(current => ({...current,[clip.clip_id]:(current[clip.clip_id] || []).filter(item => item.asset_id !== ref.asset_id)}))}>Remove</button>
            </div>)}
          </> : clip.workflow_id === FL2VA_WORKFLOW_ID ? <>
            <div className="prompt-reference-add"><select aria-label={`Frame image for clip ${clip.clip_id}`} value={referenceChoice[clip.clip_id] || ''} onChange={event => setReferenceChoice(current => ({...current,[clip.clip_id]:event.target.value}))}>
              <option value="">Choose a frame image</option>{referenceAssets.filter(asset => asset.kind === 'image').map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}
            </select><div><button type="button" className="quiet-button" disabled={!referenceChoice[clip.clip_id]} onClick={() => setClipFrame(clip.clip_id,'first_frame')}>Set first frame</button> <button type="button" className="quiet-button" disabled={!referenceChoice[clip.clip_id]} onClick={() => setClipFrame(clip.clip_id,'last_frame')}>Set last frame</button></div></div>
            {(referenceMaps[clip.clip_id] || []).map(ref => ref.kind === 'image' && <p key={ref.role}>{ref.role === 'first_frame' ? 'First frame' : 'Last frame'} · {referenceAssets.find(asset => asset.asset_id === ref.asset_id)?.filename || ref.asset_id} <button type="button" className="text-button" onClick={() => setReferenceMaps(current => ({...current,[clip.clip_id]:(current[clip.clip_id] || []).filter(item => item.asset_id !== ref.asset_id)}))}>Remove</button></p>)}
          </> : <p className="prompt-route-note">Text to video · no media references.</p>}
        </article>)}
      </section>}
      <div className="prompt-stage-actions"><button type="button" className="generate-button" onClick={() => void save()} disabled={saving || loading || Boolean(preparingShot) || Object.keys(drafts).length === 0 || !hasUnsavedDrafts}>{saving ? 'Saving prompts…' : !hasUnsavedDrafts ? 'Prompt drafts saved' : 'Save prompt drafts'}</button>
        {setup.setup?.mode === 'assisted_manual' && setup.setup.automate_steps.video && <button type="button" className="quiet-button" onClick={() => void saveReferences()} disabled={loading || savingReferenceMaps || !assistedPlan?.clips.length || JSON.stringify(referenceMaps) === JSON.stringify(savedReferenceMaps)}>{savingReferenceMaps ? 'Saving references…' : 'Save per-clip references'}</button>}
        <a className="quiet-button" href={`#/setup?workspace_id=${encodeURIComponent(workspaceId)}`}>Previous · Automation &amp; Parameters</a>
        <a className="generate-button" href={setup.setup?.mode === 'fully_automated' ? `#/take?workspace_id=${encodeURIComponent(workspaceId)}` : `#/characters?step=character_images&workspace_id=${encodeURIComponent(workspaceId)}`} aria-disabled={!canContinue} aria-describedby={!canContinue ? 'prompt-continue-status' : undefined} onClick={event => { if (!canContinue) event.preventDefault(); }}>{setup.setup?.mode === 'fully_automated' ? 'Continue to Current Take' : 'Continue to Characters & Voices'}</a>
        {!canContinue && <span id="prompt-continue-status" role="status">{continueBlockedReason}</span>}
      </div>
    </>}
  </main>;
}
