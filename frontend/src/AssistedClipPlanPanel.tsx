import RunClipLiveView from './RunClipLiveView';
import { useEffect, useRef, useState } from 'react';
import { listMediaAssets, MediaAsset, rankMediaAssets } from './lib/media-api';
import {
  AssistedClipPlanState, AssistedVideoReference, AssistedVideoReferenceMap, AssistedVideoRunState,
  getAssistedVideoClipPlan, getProductionSetup, getStoryScreenplay, getStoryWorkspace,
  listStoryScreenplays, prepareAssistedVideoClipPlan, ProductionSetup, saveAssistedVideoClipReferences,
  getStoryPromptDrafts, prepareStoryPrompt, saveStoryPromptShot, ScreenplayRevision, saveAssistedVideoClipPrompt,
  getAssistedVideoRun, startAssistedVideoRun, retryAssistedVideoClip, getCharacterVoiceState, CharacterVoiceState,
} from './lib/story-api';
import { WORKFLOW_ID, R2V_WORKFLOW_ID } from './lib/video-api';
import SelectionMicroEdit from './SelectionMicroEdit';
import './prompt-preparation.css';

type Context = { workspaceId: string; revisionId: string; setup: ProductionSetup; screenplay: ScreenplayRevision };
const promptCodepoints = (value: string) => Array.from(value).length;

export default function AssistedClipPlanPanel({ visible }: { visible: boolean }) {
  const [context, setContext] = useState<Context | null>(null);
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [voiceState, setVoiceState] = useState<CharacterVoiceState | null>(null);
  const [voiceSuggestionsUnavailable, setVoiceSuggestionsUnavailable] = useState(false);
  const [plan, setPlan] = useState<AssistedClipPlanState | null>(null);
  const [run, setRun] = useState<AssistedVideoRunState | null>(null);
  const [maps, setMaps] = useState<Record<string, AssistedVideoReference[]>>({});
  const [savedMaps, setSavedMaps] = useState<Record<string, AssistedVideoReference[]>>({});
  const [continuity, setContinuity] = useState<Record<string, boolean>>({});
  const [savedContinuity, setSavedContinuity] = useState<Record<string, boolean>>({});
  const [clipPrompts, setClipPrompts] = useState<Record<string, string>>({});
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef(0);

  const refresh = async () => {
    const currentRequest = ++requestId.current;
    const requestedWorkspace = new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || '';
    const workspaceId = requestedWorkspace || localStorage.getItem('vibe-story-selected-v1') || '';
    setContext(null); setPlan(null); setRun(null); setMaps({}); setSavedMaps({}); setContinuity({}); setSavedContinuity({}); setClipPrompts({}); setChoice({}); setError(''); setLoading(false);
    if (!workspaceId || !visible) return;
    setLoading(true);
    try {
      const workspace = await getStoryWorkspace(workspaceId);
      const sourceId = workspace.current_revision_id || workspace.current_revision?.revision_id;
      if (!sourceId) return;
      const screenplay = await getStoryScreenplay(workspaceId, sourceId);
      const [revisions, setupState] = await Promise.all([
        listStoryScreenplays(workspaceId), getProductionSetup(workspaceId, screenplay.screenplay_revision_id),
      ]);
      const acceptedCurrent = screenplay.accepted && revisions.items.some(item => item.screenplay_revision_id === screenplay.screenplay_revision_id
        && item.source_revision_id === sourceId && item.accepted && !item.stale);
      if (!acceptedCurrent || setupState.setup?.mode !== 'assisted_manual' || !setupState.setup.automate_steps.video) return;
      if (currentRequest !== requestId.current) return;
      setContext({ workspaceId, revisionId: screenplay.screenplay_revision_id, setup: setupState.setup, screenplay });
      const [images, videos, audios, existing, existingRun, voices] = await Promise.all([
        setupState.setup.video_workflow_id === WORKFLOW_ID ? Promise.resolve({ assets: [] as MediaAsset[] }) : listMediaAssets(workspaceId, 'image'),
        setupState.setup.video_workflow_id === R2V_WORKFLOW_ID ? listMediaAssets(workspaceId, 'video') : Promise.resolve({ assets: [] as MediaAsset[] }),
        setupState.setup.video_workflow_id === R2V_WORKFLOW_ID ? listMediaAssets(workspaceId, 'audio') : Promise.resolve({ assets: [] as MediaAsset[] }),
        getAssistedVideoClipPlan(workspaceId, screenplay.screenplay_revision_id),
        getAssistedVideoRun(workspaceId, screenplay.screenplay_revision_id),
        setupState.setup.video_workflow_id === R2V_WORKFLOW_ID
          ? getCharacterVoiceState(workspaceId, screenplay.screenplay_revision_id).catch(() => null)
          : Promise.resolve(null),
      ]);
      if (currentRequest !== requestId.current) return;
      setAssets([...images.assets, ...videos.assets, ...audios.assets]);
      setVoiceState(voices);
      setVoiceSuggestionsUnavailable(setupState.setup.video_workflow_id === R2V_WORKFLOW_ID && voices === null);
      const savedContinuityMap = Object.fromEntries(existing.clips.map(clip => [clip.clip_id, Boolean(clip.continue_previous_clip)]));
      setPlan(existing); setRun(existingRun); setMaps(existing.references || {}); setSavedMaps(existing.references || {});
      setContinuity(savedContinuityMap); setSavedContinuity(savedContinuityMap);
      setClipPrompts(Object.fromEntries(existing.clips.map(clip => [clip.clip_id, clip.prompt])));
    } catch (e) {
      if (currentRequest === requestId.current) setError((e as Error).message);
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  };

  useEffect(() => {
    const onHashChange = () => { void refresh(); };
    void refresh();
    window.addEventListener('hashchange', onHashChange);
    window.addEventListener('vibe-production-setup-changed', onHashChange);
    return () => { requestId.current += 1; window.removeEventListener('hashchange', onHashChange); window.removeEventListener('vibe-production-setup-changed', onHashChange); };
  }, [visible]);
  useEffect(() => {
    if (!visible || !context || !run || !['running', 'waiting_for_readiness'].includes(run.run_state)) return;
    const timer = window.setInterval(() => {
      void getAssistedVideoRun(context.workspaceId, context.revisionId).then(setRun).catch(e => setError((e as Error).message));
    }, 3000);
    return () => window.clearInterval(timer);
  }, [visible, context, run?.run_state]);
  if (!visible || (!loading && !context && !error)) return null;

  const addReference = (clipId: string) => {
    const asset = assets.find(item => item.asset_id === choice[clipId]);
    if (!asset || (maps[clipId] || []).some(ref => ref.asset_id === asset.asset_id)) return;
    const reference: AssistedVideoReference = asset.kind === 'image'
      ? { kind: 'image', asset_id: asset.asset_id, sha256: asset.sha256,
          role: asset.recommended ? 'visual_style' : 'character',
          intent: asset.recommended ? 'Use this image for visual style; preserve the screenplay characters and action.' : 'Use this image as a visual reference.' }
      : asset.kind === 'video'
        ? { kind: 'video', asset_id: asset.asset_id, sha256: asset.sha256, role: 'style',
            intent: asset.recommended ? 'Use this video for visual style; preserve the screenplay characters and action.' : 'Use this video as a visual reference.',
            start_sec: null, end_sec: null, include_paired_soundtrack: false, audio_intent: '' }
        : { kind: 'audio', asset_id: asset.asset_id, sha256: asset.sha256,
            role: asset.recommended ? 'style' : 'voice',
            intent: asset.recommended ? 'Use this audio for style; preserve the screenplay dialogue and action.' : 'Use this audio as a voice reference.', speaker_ids: [] };
    setMaps(current => ({ ...current, [clipId]: [...(current[clipId] || []), reference] }));
  };
  const clipCharacters = (clip: NonNullable<typeof plan>['clips'][number]) => {
    const shot = context?.screenplay.screenplay.scenes.find(scene => scene.scene_number === clip.scene_number)?.shots
      .find(item => item.shot_number === clip.shot_number);
    return (shot?.character_record_ids || []).flatMap(id => {
      const character = voiceState?.characters.find(item => item.record_id === id);
      return character ? [{ id, name: character.name || id }] : [];
    });
  };
  const addBoundVoice = (clipId: string, character: { id: string; name: string }, asset: MediaAsset) => setMaps(current => {
    const refs = current[clipId] || [];
    const present = refs.find(ref => ref.asset_id === asset.asset_id);
    if (present?.kind === 'audio') {
      const speaker_ids = [...new Set([...(present.speaker_ids || (present.speaker_id ? [present.speaker_id] : [])), character.id])];
      const { speaker_id: _legacySpeakerId, ...sharedReference } = present;
      return { ...current, [clipId]: refs.map(ref => ref.asset_id === asset.asset_id ? { ...sharedReference, speaker_ids } : ref) };
    }
    if (present) return current;
    return { ...current, [clipId]: [...refs, { kind: 'audio', asset_id: asset.asset_id, sha256: asset.sha256,
      role: 'voice', intent: `Use this shared voice reference for ${character.name}. It does not imply a distinct voice for other characters using the same asset.`,
      speaker_ids: [character.id] }] };
  });
  const updateReference = (clipId: string, assetId: string, patch: Partial<AssistedVideoReference>) => setMaps(current => ({
    ...current, [clipId]: (current[clipId] || []).map(ref => ref.asset_id === assetId ? { ...ref, ...patch } as AssistedVideoReference : ref),
  }));
  const setFrame = (clipId: string, role: 'first_frame' | 'last_frame') => {
    const asset = assets.find(item => item.asset_id === choice[clipId] && item.kind === 'image');
    if (!asset) return;
    const reference: AssistedVideoReference = { kind: 'image', asset_id: asset.asset_id, sha256: asset.sha256, role,
      intent: `Use as the clip's ${role.replace('_', ' ')}.` };
    setMaps(current => ({ ...current, [clipId]: [...(current[clipId] || []).filter(item => item.kind !== 'image' || item.role !== role), reference] }));
  };
  const removeReference = (clipId: string, assetId: string, role?: string) => setMaps(current => ({
    ...current, [clipId]: (current[clipId] || []).filter(ref => ref.asset_id !== assetId || (role !== undefined && ref.role !== role)),
  }));
  const recommendedAssets = rankMediaAssets(assets, '', 'newest');
  const planClips = async () => {
    if (!context || working || saving) return;
    const discardPromptEdits = Boolean(plan?.clips.some(clip => (clipPrompts[clip.clip_id] ?? clip.prompt) !== clip.prompt));
    const discardReferences = Object.values(savedMaps).some(refs => refs.length > 0);
    const hasReferences = discardReferences || Object.values(maps).some(refs => refs.length > 0)
      || Object.values(continuity).some(Boolean) || Object.values(savedContinuity).some(Boolean);
    if ((hasReferences || discardPromptEdits) && !window.confirm(`Replanning discards the current clip references${discardPromptEdits ? ' and unsaved prompt edits' : ''}. Continue?`)) return;
    const operationId = requestId.current;
    setWorking(true); setError('');
    try {
      // Planning needs shot drafts; prepare only here, never during page loading.
      const state = await getStoryPromptDrafts(context.workspaceId, context.revisionId);
      if (operationId !== requestId.current) return;
      const drafts = state.setup_matches_current ? { ...state.drafts } : {};
      const workflowId = context.setup.video_workflow_id!;
      for (const scene of context.screenplay.screenplay.scenes) {
        for (const shot of scene.shots) {
          const key = `${scene.scene_number}.${shot.shot_number}`;
          const saved = drafts[key];
          if (saved?.prompt?.trim() && saved.workflow_id === workflowId) continue;
          const prepared = await prepareStoryPrompt(context.workspaceId, context.revisionId, key, workflowId);
          if (operationId !== requestId.current) return;
          if (prepared.shot_key !== key || prepared.workflow_id !== workflowId || !prepared.prompt.trim()) {
            throw new Error('Prepared prompt does not match the selected shot and workflow. No clips were planned.');
          }
          const persisted = await saveStoryPromptShot(context.workspaceId, context.revisionId, context.setup, key, {
            workflow_id: prepared.workflow_id, prompt: prepared.prompt, knowledge_ref: prepared.knowledge_ref, style_ref: prepared.style_ref,
          });
          if (operationId !== requestId.current) return;
          Object.assign(drafts, persisted.drafts);
        }
      }
      await prepareAssistedVideoClipPlan(context.workspaceId, context.revisionId, discardReferences);
      if (operationId !== requestId.current) return;
      const next = await getAssistedVideoClipPlan(context.workspaceId, context.revisionId);
      if (next.clips.length && next.clips.every(clip => clip.workflow_id === WORKFLOW_ID)) {
        await saveAssistedVideoClipReferences(context.workspaceId, context.revisionId, next.clips.map(clip => ({clip_id: clip.clip_id, references: [], continue_previous_clip: false})));
        next.references = Object.fromEntries(next.clips.map(clip => [clip.clip_id, []]));
      }
      if (operationId === requestId.current) {
        const nextContinuity = Object.fromEntries(next.clips.map(clip => [clip.clip_id, Boolean(clip.continue_previous_clip)]));
        setPlan(next); setMaps(next.references || {}); setSavedMaps(next.references || {});
        setContinuity(nextContinuity); setSavedContinuity(nextContinuity);
        setClipPrompts(Object.fromEntries(next.clips.map(clip => [clip.clip_id, clip.prompt])));
      }
    } catch (e) { if (operationId === requestId.current) setError((e as Error).message); }
    finally { setWorking(false); }
  };
  const save = async () => {
    if (!context || !plan?.clips.length || saving || working || (JSON.stringify(maps) === JSON.stringify(savedMaps)
        && JSON.stringify(continuity) === JSON.stringify(savedContinuity))) return;
    const operationId = requestId.current;
    setSaving(true); setError('');
    try {
      const clips: AssistedVideoReferenceMap[] = plan.clips.map(clip => ({ clip_id: clip.clip_id,
        references: maps[clip.clip_id] || [], continue_previous_clip: continuity[clip.clip_id] || false }));
      const result = await saveAssistedVideoClipReferences(context.workspaceId, context.revisionId, clips);
      if (operationId === requestId.current) {
        const savedContinuityMap = Object.fromEntries(result.clips.map(clip => [clip.clip_id, Boolean(clip.continue_previous_clip)]));
        setPlan(result); setMaps(result.references || {}); setSavedMaps(result.references || {});
        setContinuity(savedContinuityMap); setSavedContinuity(savedContinuityMap);
      }
    } catch (e) { if (operationId === requestId.current) setError((e as Error).message); }
    finally { setSaving(false); }
  };
  const savePrompt = async (clipId: string) => {
    if (!context || !plan || saving || working || runFrozen) return;
    const clip = plan.clips.find(item => item.clip_id === clipId);
    const prompt = clipPrompts[clipId] ?? clip?.prompt ?? '';
    if (!clip || prompt === clip.prompt || !prompt.trim() || promptCodepoints(prompt) >= 7000) return;
    const operationId = requestId.current;
    setSaving(true); setError('');
    try {
      const result = await saveAssistedVideoClipPrompt(context.workspaceId, context.revisionId, clipId, clip.prompt, prompt);
      if (operationId === requestId.current) {
        setPlan(result);
        setClipPrompts(Object.fromEntries(result.clips.map(item => [item.clip_id, item.prompt])));
      }
    } catch (e) { if (operationId === requestId.current) setError((e as Error).message); }
    finally { if (operationId === requestId.current) setSaving(false); }
  };
  const startRun = async () => {
    if (!context || !plan?.clips.length || working || saving || JSON.stringify(maps) !== JSON.stringify(savedMaps)
        || JSON.stringify(continuity) !== JSON.stringify(savedContinuity)
        || plan.clips.some(clip => (clipPrompts[clip.clip_id] ?? clip.prompt) !== clip.prompt)) return;
    setWorking(true); setError('');
    try {
      if (plan.clips.every(clip => clip.workflow_id === WORKFLOW_ID)) {
        await saveAssistedVideoClipReferences(context.workspaceId, context.revisionId,
          plan.clips.map(clip => ({clip_id: clip.clip_id, references: [], continue_previous_clip: false})));
      }
      await startAssistedVideoRun(context.workspaceId, context.revisionId);
      setRun(await getAssistedVideoRun(context.workspaceId, context.revisionId));
    } catch (e) { setError((e as Error).message); }
    finally { setWorking(false); }
  };
  const retryClip = async (clipId: string) => {
    if (!context || working) return;
    setWorking(true); setError('');
    try {
      const result = await retryAssistedVideoClip(context.workspaceId, context.revisionId, clipId);
      setRun(result.run);
    } catch (e) { setError((e as Error).message); }
    finally { setWorking(false); }
  };
  const mapsComplete = Boolean(plan?.clips.length && plan.clips.every(clip => {
    const refs = savedMaps[clip.clip_id] || [];
    return clip.workflow_id === WORKFLOW_ID ? refs.length === 0 : clip.workflow_id === R2V_WORKFLOW_ID ? (refs.length > 0 || Boolean(savedContinuity[clip.clip_id]))
      : refs.some(ref => ref.kind === 'image' && ref.role === 'first_frame')
        && refs.some(ref => ref.kind === 'image' && ref.role === 'last_frame');
  }));
  const promptsDirty = Boolean(plan?.clips.some(clip => (clipPrompts[clip.clip_id] ?? clip.prompt) !== clip.prompt));
  const runFrozen = Boolean(run && run.run_state !== 'not_started');

  return <section className="card assisted-clip-plan" aria-label="Assisted clip plan">
    <header><div><div className="eyebrow">ASSISTED VIDEO</div><h2>Plan clips and map references</h2><p>The Director may split a screenplay shot into clips. Text to video needs no media. When you choose a reference workflow, select the references for each clip. Planning and saving references do not submit video jobs.</p></div>
      <button type="button" className="generate-button" onClick={() => void planClips()} disabled={loading || working || saving || runFrozen || !context}>{loading ? 'Loading…' : working ? 'Planning…' : plan?.clips.length ? 'Replan clips' : 'Plan clips'}</button>
    </header>
    {error && <p role="alert">{error}</p>}
    {runFrozen && <section className="card" aria-label="Assisted video run status">
      <h3>Run {run?.run_state.replaceAll('_', ' ')}</h3>
      <p>{run?.completed_count || 0} of {run?.planned_count || plan?.clips.length || 0} clips ready for review.</p>
      {run?.error && <p role="alert">{run.error}</p>}
      {run?.clips.map((item, index) => <div key={item.clip_id}>
        <p>Scene {item.scene_number} · Shot {item.shot_number} · Clip {item.clip_number}: {item.state}</p>
        <RunClipLiveView job={item.job} workspaceId={context?.workspaceId || run.workspace_id}/>
        {item.job.outputs?.filter(output => output.kind === 'video' && output.playback_url).map(output => <video key={output.playback_url} controls playsInline preload="none" src={output.playback_url} aria-label={`Completed clip ${item.clip_number}`} style={{width:'100%',maxWidth:720}}/>)}
        {run.run_state === 'paused' && index === run.clips.length - 1
          && ['failed', 'cancelled', 'stale', 'recovery_required'].includes(item.state)
          && <button type="button" className="quiet-button" disabled={working} onClick={() => void retryClip(item.clip_id)}>
            {working ? 'Retrying…' : 'Retry latest clip'}
          </button>}
      </div>)}
    </section>}
    {plan?.clips.map((clip, clipIndex) => <article className="prompt-reference-map" key={clip.clip_id} aria-label={`References for Scene ${clip.scene_number}, Shot ${clip.shot_number}, Clip ${clip.clip_number}`}>
      <h3>Scene {clip.scene_number} · Shot {clip.shot_number} · Clip {clip.clip_number}</h3><p>{clip.duration_seconds}s · {clip.duration_reason}</p>
      <p>{clip.source_spans.map(span => span.text).join(' ')}</p>
      <SelectionMicroEdit label={`Prompt for planned clip ${clip.clip_id}`} value={clipPrompts[clip.clip_id] ?? clip.prompt}
        surface="prompt" workspaceId={context?.workspaceId || ''} revisionId={context?.revisionId || ''}
        fieldKey={`assisted-clip:${clip.clip_id}`} disabled={saving || working || runFrozen}
        onChange={value => setClipPrompts(current => ({ ...current, [clip.clip_id]: value }))}/>
      <small>{promptCodepoints(clipPrompts[clip.clip_id] ?? clip.prompt).toLocaleString()}/6,999 characters</small>
      <button type="button" className="quiet-button" onClick={() => void savePrompt(clip.clip_id)}
        disabled={!context || saving || working || runFrozen || (clipPrompts[clip.clip_id] ?? clip.prompt) === clip.prompt
          || !(clipPrompts[clip.clip_id] ?? clip.prompt).trim() || promptCodepoints(clipPrompts[clip.clip_id] ?? clip.prompt) >= 7000}>
        {saving ? 'Saving prompt…' : 'Save clip prompt'}
      </button>
      {clip.workflow_id === WORKFLOW_ID ? <p>Text to video. No media references are attached.</p> : clip.workflow_id === R2V_WORKFLOW_ID ? <>
        {clipIndex > 0 && plan.clips[clipIndex - 1].scene_number === clip.scene_number && <label className="checkbox-row"><input type="checkbox"
          aria-label={`Continue from previous clip for ${clip.clip_id}`} checked={Boolean(continuity[clip.clip_id])}
          disabled={saving || working || runFrozen} onChange={event => setContinuity(current => ({ ...current, [clip.clip_id]: event.target.checked }))}/>
          Use the previous clip’s last frame as a continuity reference (optional)</label>}
        {clipCharacters(clip).length > 0 && <div className="reference-recommendations" role="group" aria-label={`Recommended references for clip ${clip.clip_id}`}>
          <b>Recommended for this shot</b>
          {clipCharacters(clip).map(character => {
            const voiceId = voiceState?.bindings.find(binding => binding.character_id === character.id)?.voice_asset_id;
            const voiceAsset = assets.find(asset => asset.asset_id === voiceId && asset.kind === 'audio');
            const characterImages = assets.filter(asset => asset.kind === 'image' && asset.roles.includes('character_master')
              && asset.metadata?.production_image_job?.settings?.lineage?.target_record_id === character.id);
            return <div className="reference-recommendation" key={character.id}>
              <span><strong>{character.name}</strong> · {voiceAsset ? `Bound voice: ${voiceAsset.filename}` : 'No voice is bound'} · {characterImages.length ? `${characterImages.length} character image${characterImages.length === 1 ? '' : 's'}` : 'No character image found'}</span>
              {voiceAsset && <button type="button" className="text-button" disabled={saving || working || runFrozen}
                onClick={() => addBoundVoice(clip.clip_id, character, voiceAsset)}>{(maps[clip.clip_id] || []).some(ref => ref.asset_id === voiceAsset.asset_id) ? 'Add character mapping' : 'Add voice reference'}</button>}
              {characterImages.map(asset => <button type="button" className="text-button" key={asset.asset_id}
                disabled={saving || working || runFrozen || (maps[clip.clip_id] || []).some(ref => ref.asset_id === asset.asset_id)}
                onClick={() => setMaps(current => ({ ...current, [clip.clip_id]: [...(current[clip.clip_id] || []), { kind: 'image', asset_id: asset.asset_id, sha256: asset.sha256, role: 'character', intent: `Use this as the appearance reference for ${character.name}.` }] }))}>
                Add image · {asset.filename}</button>)}
            </div>;
          })}
          {voiceSuggestionsUnavailable && <small>Character voice bindings could not be loaded. You can still choose references below.</small>}
        </div>}
        <div className="prompt-reference-add"><select aria-label={`Reference asset for clip ${clip.clip_id}`} disabled={saving || working || runFrozen} value={choice[clip.clip_id] || ''} onChange={event => setChoice(current => ({ ...current, [clip.clip_id]: event.target.value }))}>
          <option value="">Choose a workspace asset</option>{recommendedAssets.map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.recommended ? 'Recommended style · ' : ''}{asset.kind} · {asset.filename}</option>)}
        </select><button type="button" className="quiet-button" disabled={!choice[clip.clip_id] || saving || working || runFrozen} onClick={() => addReference(clip.clip_id)}>Add reference</button></div>
        {(maps[clip.clip_id] || []).map(ref => <div className={`prompt-reference-row${ref.kind === 'audio' ? ' audio-reference-row' : ''}`} key={ref.asset_id}>
          <span>{ref.kind} · {assets.find(asset => asset.asset_id === ref.asset_id)?.filename || ref.asset_id}</span>
          <input aria-label={`Reference intent for ${ref.asset_id}`} maxLength={500} value={ref.intent} disabled={saving || working || runFrozen} onChange={event => updateReference(clip.clip_id, ref.asset_id, { intent: event.target.value })}/>
          {ref.kind === 'audio' && <input aria-label={`Speaker IDs for ${ref.asset_id}`} value={(ref.speaker_ids || (ref.speaker_id ? [ref.speaker_id] : [])).join(', ')} placeholder="Speaker IDs (optional, comma-separated)" maxLength={1000} disabled={saving || working || runFrozen} onChange={event => updateReference(clip.clip_id, ref.asset_id, { speaker_ids: [...new Set(event.target.value.split(',').map(value => value.trim()).filter(Boolean))] })}/>}
          <button type="button" className="text-button" disabled={saving || working || runFrozen} onClick={() => removeReference(clip.clip_id, ref.asset_id)}>Remove</button>
        </div>)}
      </> : <>
        <div className="prompt-reference-add"><select aria-label={`Frame image for clip ${clip.clip_id}`} disabled={saving || working || runFrozen} value={choice[clip.clip_id] || ''} onChange={event => setChoice(current => ({ ...current, [clip.clip_id]: event.target.value }))}>
          <option value="">Choose a frame image</option>{assets.filter(asset => asset.kind === 'image').map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}
        </select><div><button type="button" className="quiet-button" disabled={!choice[clip.clip_id] || saving || working || runFrozen} onClick={() => setFrame(clip.clip_id, 'first_frame')}>Set first frame</button> <button type="button" className="quiet-button" disabled={!choice[clip.clip_id] || saving || working || runFrozen} onClick={() => setFrame(clip.clip_id, 'last_frame')}>Set last frame</button></div></div>
        {(maps[clip.clip_id] || []).filter(ref => ref.kind === 'image').map(ref => <p key={ref.role}>{ref.role === 'first_frame' ? 'First frame' : 'Last frame'} · {assets.find(asset => asset.asset_id === ref.asset_id)?.filename || ref.asset_id} <button type="button" className="text-button" disabled={saving || working || runFrozen} onClick={() => removeReference(clip.clip_id, ref.asset_id, ref.role)}>Remove</button></p>)}
      </>}
    </article>)}
    {plan?.clips.length ? <>
      <button type="button" className="quiet-button" onClick={() => void save()} disabled={loading || saving || working || runFrozen || (JSON.stringify(maps) === JSON.stringify(savedMaps) && JSON.stringify(continuity) === JSON.stringify(savedContinuity))}>{saving ? 'Saving clip choices…' : 'Save per-clip choices'}</button>
      <button type="button" className="generate-button" onClick={() => void startRun()} disabled={loading || saving || working || runFrozen || !mapsComplete || promptsDirty || JSON.stringify(maps) !== JSON.stringify(savedMaps) || JSON.stringify(continuity) !== JSON.stringify(savedContinuity)}>{working ? 'Starting…' : 'Start video run'}</button>
      {promptsDirty && <p>Save each edited clip prompt before starting the run.</p>}
    </> : null}
  </section>;
}
