import {managedProjectId} from './lib/media-workspace';
import { T2V_QUALITIES, ALL_VIDEO_QUALITIES, VIDEO_ASPECT_RATIOS, VideoAspectRatio } from './lib/video-quality';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowRight, Check, RefreshCw, Save } from 'lucide-react';
import { getAssistedStageSkips, setAssistedStageSkip, getProductionSetup, getStoryScreenplay, getStoryWorkspace, ProductionImageSettings, ProductionSetup, ProductionSetupState, saveProductionSetup } from './lib/story-api';
import { getImageWorkflows, ImageWorkflow } from './lib/image-api';
import './production-setup.css';
import './production-style-video.css';

const stepInfo = [
  ['character_images', 'Character image generation'],
  ['character_voice', 'Character-to-audio selection'],
  ['world_images', 'World-building image generation'],
  ['frame_images', 'Frame image generation'],
  ['video', 'Video generation'],
] as const;
const defaults = (): ProductionSetup => ({ mode: 'assisted_manual', automate_steps: {
  character_images: false, character_voice: false, world_images: false, frame_images: false, video: false,
}, video_quality: 't2v_standard', aspect_ratio: '16:9', duration_policy: { kind: 'fixed', seconds: 6 }, style_video_references: [] });
const imageSteps = ['character_images', 'world_images', 'frame_images'] as const;
type ImageStep = typeof imageSteps[number];
const fallbackImageSetting: ProductionImageSettings = { workflow_id: 'z_image_turbo', width: 1280, height: 720, steps: 8, cfg: 1 };
const imageSettingDefaults = (step: ImageStep): ProductionImageSettings => ({
  ...fallbackImageSetting, ...(step === 'world_images' ? { world_view_count: 4 as const } : {}),
});

export default function ProductionSetupPage() {
  const [workspaceId, setWorkspaceId] = useState('');
  const [screenplayRevisionId, setScreenplayRevisionId] = useState('');
  const [draft, setDraft] = useState<ProductionSetup>(defaults);
  const [skips, setSkips] = useState<ImageStep[]>([]);
  const [savedSkips, setSavedSkips] = useState<ImageStep[]>([]);
  const [saved, setSaved] = useState<ProductionSetupState | null>(null);
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [notice, setNotice] = useState('');
  const [imageWorkflows, setImageWorkflows] = useState<ImageWorkflow[]>([]);
  const loadGeneration = useRef(0);

  const refresh = async () => {
    const loadId = ++loadGeneration.current;
    setBusy(true); setSaving(false); setLoadError(''); setSaveError(''); setNotice(''); setSaved(null); setScreenplayRevisionId('');
    try {
      const requestedWorkspace = new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || '';
      const id = managedProjectId() || requestedWorkspace || localStorage.getItem('vibe-story-selected-v1') || '';
      if (!id.startsWith('story-')) { if(!requestedWorkspace)localStorage.removeItem('vibe-story-selected-v1'); throw new Error('Open a saved story first.'); }
      setWorkspaceId(id);
      const workspace = await getStoryWorkspace(id);
      if (loadId !== loadGeneration.current) return;
      const sourceRevisionId = workspace.current_revision_id || workspace.current_revision?.revision_id;
      if (!sourceRevisionId) throw new Error('This story has no current source revision.');
      const screenplay = await getStoryScreenplay(id, sourceRevisionId);
      if (loadId !== loadGeneration.current) return;
      if (!screenplay.accepted) throw new Error('Review and accept the current screenplay before saving production setup.');
      const state = await getProductionSetup(id, screenplay.screenplay_revision_id);
      const skipState = await getAssistedStageSkips(id, screenplay.screenplay_revision_id);
      if (loadId !== loadGeneration.current) return;
      const catalog = await getImageWorkflows().catch(() => ({ workflows: [] }));
      if (loadId !== loadGeneration.current) return;
      const supportedWorkflows = catalog.workflows.filter(item => ['qwen_image_2512', 'z_image_turbo', 'qwen_image_edit_2511'].includes(item.workflow_id));
      setImageWorkflows(supportedWorkflows);
      setScreenplayRevisionId(screenplay.screenplay_revision_id);
      const normalized = state.setup ? { ...state.setup, style_video_references: state.setup.style_video_references || [] } : defaults();
      if (normalized.mode === 'assisted_manual') {
        const firstWorkflow = supportedWorkflows.find(item => item.workflow_id === 'z_image_turbo') || supportedWorkflows[0];
        normalized.image_stage_settings = Object.fromEntries(imageSteps
          .filter(step => normalized.automate_steps[step])
          .map(step => [step, { ...imageSettingDefaults(step), ...(firstWorkflow ? {
            workflow_id: firstWorkflow.workflow_id as ProductionImageSettings['workflow_id'], ...firstWorkflow.defaults,
          } : {}), ...normalized.image_stage_settings?.[step] }])) as ProductionSetup['image_stage_settings'];
      }
      setSkips(skipState.skipped); setSavedSkips(skipState.skipped);
      setSaved(state); setDraft(normalized);
    } catch (e) {
      if (loadId === loadGeneration.current) { setSaved(null); if((e as Error & {status?:number}).status===404&&!new URLSearchParams(window.location.hash.split('?')[1]||'').has('workspace_id')){localStorage.removeItem('vibe-story-selected-v1');setWorkspaceId('');setLoadError('The previously selected story was removed. Open a saved story.');}else setLoadError((e as Error).message); }
    } finally {
      if (loadId === loadGeneration.current) setBusy(false);
    }
  };
  useEffect(() => {
    void refresh();
    const onHashChange = () => void refresh();
    const onStorage = (event: StorageEvent) => {
      if (event.key === 'vibe-story-selected-v1') void refresh();
    };
    window.addEventListener('hashchange', onHashChange);
    window.addEventListener('storage', onStorage);
    return () => {
      loadGeneration.current += 1;
      window.removeEventListener('hashchange', onHashChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  // Older saved setups omit this optional field. Treat omission and an empty
  // selection as equivalent so legacy setups remain reviewable without a
  // no-op save that would change their setup hash.
  const comparableSetup = (value: ProductionSetup) => {
    const normalized = { ...value };
    if (!normalized.style_video_references?.length) delete normalized.style_video_references;
    if (!Object.keys(normalized.image_stage_settings || {}).length) delete normalized.image_stage_settings;
    return normalized;
  };
  const dirty = useMemo(() => !saved?.setup || JSON.stringify(comparableSetup(draft)) !== JSON.stringify(comparableSetup(saved.setup)) || JSON.stringify([...skips].sort()) !== JSON.stringify([...savedSkips].sort()), [draft, saved, skips, savedSkips]);
  const automatedCount = draft.mode === 'fully_automated' ? 'Text-to-video route' : `${Object.values(draft.automate_steps).filter(Boolean).length} of 5 steps automated`;
  const save = async () => {
    if (!workspaceId || !screenplayRevisionId || busy || saving) return;
    const saveGeneration = loadGeneration.current;
    const saveWorkspaceId = workspaceId;
    const saveScreenplayRevisionId = screenplayRevisionId;
    setSaving(true); setSaveError(''); setNotice('');
    try {
      const payload = comparableSetup(draft);
      if (payload.mode === 'fully_automated') {
        payload.automate_steps = defaults().automate_steps;
        delete payload.image_stage_settings;
        delete payload.video_workflow_id;
      }
      const state = await saveProductionSetup(saveWorkspaceId, saveScreenplayRevisionId, {...payload, style_video_references: []});
      // Keep the existing revision-scoped skip store; Continue stays locked if any save fails.
      const desiredSkips = payload.mode === 'assisted_manual' ? skips : [];
      for (const step of imageSteps) {
        if (payload.mode === 'assisted_manual' && !payload.automate_steps[step])
          await setAssistedStageSkip(saveWorkspaceId, saveScreenplayRevisionId, step, desiredSkips.includes(step));
      }
      if (saveGeneration === loadGeneration.current) {
        setSavedSkips(desiredSkips); setSkips(desiredSkips);
        setSaved(state); setDraft(state.setup || defaults()); setNotice('Setup saved for this accepted screenplay revision.');
      }
    } catch (e) {
      if (saveGeneration === loadGeneration.current) setSaveError((e as Error).message);
    }
    finally { if (saveGeneration === loadGeneration.current) setSaving(false); }
  };
  const toggle = (key: keyof ProductionSetup['automate_steps']) => {
    setSkips(values => values.filter(step => step !== key));
    setDraft(current => {
    const enabled = !current.automate_steps[key];
    const imageSettings = { ...current.image_stage_settings };
    if (enabled && imageSteps.includes(key as ImageStep) && !imageSettings[key as ImageStep]) {
      const workflow = imageWorkflows.find(item => item.workflow_id === 'z_image_turbo') || imageWorkflows[0];
      imageSettings[key as ImageStep] = workflow
        ? { ...imageSettingDefaults(key as ImageStep), workflow_id: workflow.workflow_id as ProductionImageSettings['workflow_id'], ...workflow.defaults }
        : imageSettingDefaults(key as ImageStep);
    }
    if (!enabled && imageSteps.includes(key as ImageStep)) delete imageSettings[key as ImageStep];
    const next = { ...current, automate_steps: { ...current.automate_steps, [key]: enabled }, image_stage_settings: imageSettings };
    if (enabled && key === 'video' && !next.video_workflow_id) next.video_workflow_id = 'minimax_h3_t2v_local_v1';
    if (!enabled && key === 'video') delete next.video_workflow_id;
    return next;
  });
  };
  const skipStage = (step: ImageStep) => {
    setSkips(values => values.includes(step) ? values.filter(value => value !== step) : [...values, step]);
    setDraft(current => { const settings = {...current.image_stage_settings}; delete settings[step]; return {...current, automate_steps: {...current.automate_steps, [step]: false}, image_stage_settings: settings}; });
  };
  const updateImageSetting = (step: ImageStep, patch: Partial<ProductionImageSettings>) => setDraft(value => ({
    ...value, image_stage_settings: { ...value.image_stage_settings, [step]: { ...imageSettingDefaults(step), ...value.image_stage_settings?.[step], ...patch } },
  }));
  const fixedDuration = draft.duration_policy.kind === 'fixed' ? draft.duration_policy.seconds : null;
  const minDuration = draft.duration_policy.kind === 'director_selected' ? draft.duration_policy.min_seconds : 5;
  const maxDuration = draft.duration_policy.kind === 'director_selected' ? draft.duration_policy.max_seconds : 30;

  return <main className="content-wrap production-setup-page"><section className="card" style={{marginBottom:24}}><div className="story-panel-title"><div><h2>Storyboard production</h2><p>Choose optional stages, prepare one image per shot and build a scene storyboard. FFLF remains available manually; automatic endpoint images and FFLF video are paused.</p></div><a className="quiet-button" href="#/shot-frames">Configure storyboard & shot frames</a></div></section>
    <div className="page-heading"><div><div className="eyebrow">SCREENPLAY SETUP</div><h1>Automation &amp; Parameters</h1><p>{screenplayRevisionId ? `Accepted screenplay · ${screenplayRevisionId}` : 'Choose how the stages will run.'}</p></div><button className="quiet-button" type="button" onClick={() => void refresh()} disabled={busy || saving}><RefreshCw size={15}/> Reload</button></div>
    {(loadError || saveError) && <p className="error-banner" role="alert">{loadError || saveError}</p>}{notice && <p className="production-setup-notice" role="status"><Check size={15}/>{notice}</p>}
    {busy ? <section className="card">Loading the current accepted screenplay and saved setup…</section> : loadError ? <section className="card production-setup-blocked"><b>Setup is locked</b><p>Return to Screenplay, save the latest edits, then review and accept the current revision.</p><a className="quiet-button" href="#/screenplay">Open Screenplay <ArrowRight size={15}/></a></section> : <>
      <section className="card production-mode-card"><div className="production-setup-section-title"><div><h2>Choose a production mode</h2><p>Assisted manual lets you automate any combination of the five steps.</p></div><span className="production-setup-count">{automatedCount}</span></div>
        <div className="production-mode-options" role="radiogroup" aria-label="Production mode">
          <button type="button" role="radio" aria-checked={draft.mode === 'assisted_manual'} disabled={saving} className={draft.mode === 'assisted_manual' ? 'selected' : ''} onClick={() => setDraft(value => ({ ...value, mode: 'assisted_manual' }))}><b>Assisted manual</b><span>Choose which stages run automatically. Leave every box unchecked to guide each step yourself.</span></button>
          <button type="button" role="radio" aria-checked={draft.mode === 'fully_automated'} disabled={saving} className={draft.mode === 'fully_automated' ? 'selected' : ''} onClick={() => setDraft(value => ({ ...value, mode: 'fully_automated', video_quality: 't2v_standard' }))}><b>Fully automated</b><span>Generate every clip with text to video. The Director describes the setting, characters, dialogue and action in each prompt.</span></button>
        </div>
      </section>
      {draft.mode === 'assisted_manual' && <section className="card production-steps-card"><div className="production-setup-section-title"><div><h2>Automate these steps</h2><p>Checked means automatic; unchecked means manual. Use Skip to bypass an image stage. Skipping every image stage is allowed; voices are handled separately.</p></div></div>
        <div className="production-step-list">{stepInfo.map(([key, label]) => <div className="production-step" key={key}><label><input type="checkbox" checked={draft.automate_steps[key]} disabled={saving || (key === 'frame_images' && !draft.automate_steps[key])} onChange={() => toggle(key)}/><span><b>{label}</b><small>{skips.includes(key as ImageStep) ? 'Skipped. Existing images are preserved.' : draft.automate_steps[key] ? 'Runs automatically when its inputs are ready.' : 'You review the prompt and choose when to generate.'}</small></span></label>{imageSteps.includes(key as ImageStep) && <button type="button" className="quiet-button" disabled={saving} aria-pressed={skips.includes(key as ImageStep)} onClick={() => skipStage(key as ImageStep)}>{skips.includes(key as ImageStep) ? 'Undo skip' : 'Skip'}</button>}</div>)}</div><p>For filmmaking, cinematic frame preparation is experimental and currently unreliable. Skip it to continue from Worlds to Video Create with text to video. Frame tools and first/last-frame video remain available when you choose to use them.</p>
        {imageSteps.filter(step => draft.automate_steps[step]).map(step => {
          const setting = draft.image_stage_settings?.[step] || fallbackImageSetting;
          const workflow = imageWorkflows.find(item => item.workflow_id === setting.workflow_id);
          const stepWorkflows = step === 'frame_images'
            ? imageWorkflows
            : imageWorkflows.filter(item => item.workflow_id !== 'qwen_image_edit_2511');
          const options = stepWorkflows.length ? stepWorkflows : [{ workflow_id: 'z_image_turbo', label: 'Z-Image Turbo · text to image', version: '1', available: false, disabled_reason: 'Workflow status could not be loaded.', defaults: fallbackImageSetting } as ImageWorkflow];
          return <fieldset className="production-image-settings" key={step} disabled={saving}><legend>{stepInfo.find(([key]) => key === step)?.[1]} · confirm parameters</legend>
            <label>Workflow<select aria-label={`${step} workflow`} value={setting.workflow_id} onChange={event => {
              const selected = options.find(item => item.workflow_id === event.target.value);
              updateImageSetting(step, selected ? { workflow_id: selected.workflow_id as ProductionImageSettings['workflow_id'], ...selected.defaults } : { workflow_id: event.target.value as ProductionImageSettings['workflow_id'] });
            }}>{options.map(item => <option key={item.workflow_id} value={item.workflow_id}>{item.label}{item.available ? '' : ' · check status'}</option>)}</select></label>
            <label>Width<input aria-label={`${step} width`} type="number" min="256" max="2048" step="8" value={setting.width} onChange={event => updateImageSetting(step, { width: Number(event.target.value) })}/></label>
            <label>Height<input aria-label={`${step} height`} type="number" min="256" max="2048" step="8" value={setting.height} onChange={event => updateImageSetting(step, { height: Number(event.target.value) })}/></label>
            <label>Steps<input aria-label={`${step} steps`} type="number" min={setting.workflow_id === 'z_image_turbo' ? 4 : 20} max={setting.workflow_id === 'z_image_turbo' ? 16 : 80} value={setting.steps} onChange={event => updateImageSetting(step, { steps: Number(event.target.value) })}/></label>
            <label>CFG<input aria-label={`${step} CFG`} type="number" min="0.1" max={setting.workflow_id === 'z_image_turbo' ? 2 : 8} step="0.1" value={setting.cfg} onChange={event => updateImageSetting(step, { cfg: Number(event.target.value) })}/></label>
            {step === 'world_images' && <label>World directions<select aria-label="world_images world directions" value={setting.world_view_count || 4} onChange={event => updateImageSetting(step, { world_view_count: Number(event.target.value) as 2|3|4|8 })}><option value={2}>2 · left, right</option><option value={3}>3 · left, right, back</option><option value={4}>4 · front, right, back, left</option><option value={8}>8 · include diagonal views</option></select><small>After one base location image is selected, generate these views with Qwen Multi-angle.</small></label>}
            {workflow?.available === false && <small className="production-image-unavailable">{workflow.disabled_reason || 'Workflow is not ready on this machine.'} You can save the parameters and resolve readiness before generation.</small>}
          </fieldset>;
        })}
        {draft.automate_steps.video && <fieldset className="production-image-settings" disabled={saving}>
          <legend>Video Generation · choose one workflow for this run</legend>
          <label>Workflow<select aria-label="Automated video workflow" value={draft.video_workflow_id || ''} onChange={event => setDraft(value => ({ ...value, video_quality: 't2v_standard', video_workflow_id: event.target.value ? event.target.value as NonNullable<ProductionSetup['video_workflow_id']> : undefined }))}>
            <option value="">Choose workflow</option><option value="minimax_h3_t2v_local_v1">Text to video (no references)</option><option value="minimax_h3_fl2va_first_last_v1" disabled>First and last frame · automatic use paused</option><option value="minimax_h3_r2v_dynamic_v1">Reference to video (R2V)</option>
          </select></label>
          <small>Applies to this Assisted manual run. Text to video needs no references. Choose FFLF or R2V only when you want to select references for each clip.</small>
        </fieldset>}
      </section>}
      {draft.mode === 'fully_automated' && <section className="card production-steps-card"><h2>Fully automated route</h2><p className="production-setup-explainer">Every clip uses text to video with self-contained setting, character and dialogue instructions. No image, video or audio references are attached. Quality and duration follow the saved settings below.</p></section>}
      <section className="card production-parameters-card"><div className="production-setup-section-title"><div><h2>Confirm video settings</h2><p>These settings apply to automated video generation.</p></div>{saved && !dirty && <span className="production-setup-confirmed"><Check size={14}/> Confirmed</span>}</div>
        <div className="production-parameter-grid"><label>Aspect ratio<select aria-label="Video aspect ratio" disabled={saving} value={draft.aspect_ratio || '16:9'} onChange={event => setDraft(value => ({...value, aspect_ratio: event.target.value as VideoAspectRatio}))}>{VIDEO_ASPECT_RATIOS.map(item => <option key={item.value} value={item.value}>{item.value} · {item.label}</option>)}</select></label><label>Final quality<select aria-label="Video quality" disabled={saving} value={draft.video_quality} onChange={event => setDraft(value => ({ ...value, video_quality: event.target.value as ProductionSetup['video_quality'] }))}>{<option hidden value={draft.video_quality}>Saved · {ALL_VIDEO_QUALITIES.find(item => item.key === draft.video_quality)?.label}</option>}{T2V_QUALITIES.map(item => <option key={item.key} value={item.key}>{item.label} · {item.width} × {item.height}</option>)}</select></label>
          <fieldset disabled={saving}><legend>Duration policy</legend><label><input type="radio" name="duration-policy" checked={draft.duration_policy.kind === 'fixed'} onChange={() => setDraft(value => ({ ...value, duration_policy: { kind: 'fixed', seconds: fixedDuration ?? 6 } }))}/> Fixed length</label><label><input type="radio" name="duration-policy" checked={draft.duration_policy.kind === 'director_selected'} onChange={() => setDraft(value => ({ ...value, duration_policy: { kind: 'director_selected', min_seconds: minDuration, max_seconds: maxDuration } }))}/> Director chooses each clip within the shared 5–30 sec T2V range</label>
            {draft.duration_policy.kind === 'fixed' ? <label>Length<select aria-label="Fixed duration" disabled={saving} value={draft.duration_policy.seconds} onChange={event => setDraft(value => ({ ...value, duration_policy: { kind: 'fixed', seconds: Number(event.target.value) } }))}>{Array.from({ length: 26 }, (_, i) => i + 5).map(seconds => <option key={seconds} value={seconds}>{seconds} seconds</option>)}</select></label> : <div className="production-duration-range"><label>Shortest<select aria-label="Shortest duration" disabled={saving} value={draft.duration_policy.min_seconds} onChange={event => setDraft(value => ({ ...value, duration_policy: { kind: 'director_selected', min_seconds: Number(event.target.value), max_seconds: Math.max(Number(event.target.value), draft.duration_policy.kind === 'director_selected' ? draft.duration_policy.max_seconds : 30) } }))}>{Array.from({ length: 26 }, (_, i) => i + 5).map(seconds => <option key={seconds} value={seconds}>{seconds} seconds</option>)}</select></label><label>Longest<select aria-label="Longest duration" disabled={saving} value={draft.duration_policy.max_seconds} onChange={event => setDraft(value => ({ ...value, duration_policy: { kind: 'director_selected', min_seconds: Math.min(Number(event.target.value), draft.duration_policy.kind === 'director_selected' ? draft.duration_policy.min_seconds : 5), max_seconds: Number(event.target.value) } }))}>{Array.from({ length: 26 }, (_, i) => i + 5).map(seconds => <option key={seconds} value={seconds}>{seconds} seconds</option>)}</select></label></div>}
          </fieldset>
        </div>
        <p className="production-setup-explainer">This setup saves the selected quality and duration limits. It does not start image or video generation.</p>
      </section>
      <div className="production-setup-actions"><button className="generate-button" type="button" onClick={() => void save()} disabled={saving || !dirty}>{saving ? 'Saving…' : saved && !dirty ? <><Check size={15}/> Setup saved</> : <><Save size={15}/> Save setup</>}</button><a className="quiet-button" href={`#/prompts?workspace_id=${encodeURIComponent(workspaceId)}`} aria-disabled={!saved?.setup || dirty || saving} onClick={event => { if (!saved?.setup || dirty || saving) event.preventDefault(); }} title={!saved?.setup || dirty ? 'Save setup before continuing.' : ''}>Continue to Prompt Preparation <ArrowRight size={15}/></a></div>
      <p className="production-setup-footnote">Setup is saved per workspace and accepted screenplay revision. A new screenplay revision needs its own confirmation.</p>
    </>}
  </main>;
}
