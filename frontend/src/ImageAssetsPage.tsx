import {managedProjectId} from './lib/media-workspace';
import OutputDestination from './OutputDestination';
import ZImageLoraControls,{ZImageLora} from './ZImageLoraControls';
import SelectionToggle from './SelectionToggle';
import MediaSourcePicker from './MediaSourcePicker';
import LocalImageFolderBrowser from './LocalImageFolderBrowser';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Check, ChevronLeft, ChevronRight, Clock3, Image as ImageIcon, LoaderCircle, RefreshCw, Sparkles } from 'lucide-react';
import { ImageApiError, acceptImageCandidate, deleteTemporaryImageAsset, getImageBatch, getImageSelection, getImageWorker, getImageWorkflows, ImageBatch, ImageWorkflow, ImageStageAdmission, ImagePromptDraft, ImageGpuAdmission, validateImageRequest, prepareImagePrompt, createImageBatch, stageTemporaryImageReference, startAutomatedImageStage } from './lib/image-api';
import { getRuntimeGuard, RuntimeGuard } from './lib/status-api';
import { listMediaAssets, MediaAsset, rankMediaAssets } from './lib/media-api';
import { getCharacterVoiceState, getAssistedStageSkips, getFramePreparationSkips, getProductionSetup, getStoryGraphSnapshot, getStoryScreenplayRevision, listStoryScreenplays, listStoryWorkspaces, prepareStoryPrompt, saveStoryPromptShot, saveProductionSetup, setAssistedStageSkip, setFramePreparationSkip, StoryGraphRecord, StoryWorkspace } from './lib/story-api';
import { FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID, WORKFLOW_ID } from './lib/video-api';
import './image-assets.css';
import CharacterVoicesPage from './CharacterVoicesPage';
import SceneBackgroundVariant from './SceneBackgroundVariant';
import SelectionMicroEdit from './SelectionMicroEdit';
import {getPromptGuidance} from './lib/prompt-director-api';
import DirectorImageReview from './DirectorImage';
import { preferredMediaWorkspaceId } from './lib/media-workspace';

type Role = 'character_master'|'world_master'|'character_view'|'world_view'|'first_frame'|'last_frame';
type FrameTarget = { scene_number: number; shot_number: number; clip_id: string; scene_title: string; summary: string; dialogue: string; camera: string; lighting: string; mood: string };
const DRAFT_KEY = 'vibe-image-draft-v1';
const PROMPTS_KEY = 'vibe-image-target-prompts-v1';
const ACTIVE_KEY = 'vibe-image-active-v1';
const PENDING_KEY = 'vibe-image-pending-request-v1';
const STORY_VIDEO_HANDOFF_KEY = 'vibe-story-video-handoff-v1';
const newKey = () => crypto.randomUUID();
const imageToken = () => crypto.randomUUID().replaceAll('-', '');
const readDraft = () => { try { return JSON.parse(localStorage.getItem(DRAFT_KEY)||'{}'); } catch { return {}; } };
const readActive = () => { try { return JSON.parse(localStorage.getItem(ACTIVE_KEY)||'null'); } catch { return null; } };
const readPending = () => { try { return JSON.parse(localStorage.getItem(PENDING_KEY)||'null'); } catch { return null; } };
const stageLabel:Record<Role,string> = {character_master:'Character image',world_master:'Scene background / base location',character_view:'Character side view',world_view:'Location directional view',first_frame:'First frame',last_frame:'Last frame'};
const IMAGE_PROMPT_MAX_CODEPOINTS = 6999;
async function storyClipId(workspaceId: string, screenplayId: string, sceneNumber: number, shotNumber: number) {
  const value = `${workspaceId}\0${screenplayId}\0${sceneNumber}\0${shotNumber}`;
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  const hex = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  return `story-${hex.slice(0, 40)}`;
}

function ImageStageNext({ workspaceId, revisionId, step, records, frames, setup, refresh, onVideoNext, videoReady, videoWorkflowId, skippedStages }: {
  workspaceId:string; revisionId:string; step:string; records:StoryGraphRecord[]; frames:FrameTarget[];
  setup:import('./lib/story-api').ProductionSetup|null; refresh:number; onVideoNext:()=>void; videoReady:boolean; videoWorkflowId:string; skippedStages:Array<'character_images'|'world_images'|'frame_images'>;
}) {
  const [missing,setMissing]=useState<string[]>(['Checking saved selections…']);
  const [checking,setChecking]=useState(false);
  const context=JSON.stringify([workspaceId,revisionId,step,records.map(row=>row.record_id),frames.map(row=>row.clip_id),setup,videoWorkflowId,skippedStages]);
  const [checkedContext,setCheckedContext]=useState('');
  const check=useCallback(async()=>{
    const [media,skips,voices,frameSkips]=await Promise.all([
      listMediaAssets(workspaceId,'image'), getAssistedStageSkips(workspaceId,revisionId),
      step==='character_images'?getCharacterVoiceState(workspaceId,revisionId):Promise.resolve(null),
      step==='frame_images'?getFramePreparationSkips(workspaceId,revisionId):Promise.resolve(null),
    ]);
    const gaps:string[]=[];
    const imageIds=new Set(media.assets.map(asset=>asset.asset_id));
    if(!skips.skipped.includes(step as 'character_images'|'world_images'|'frame_images')){
      if(step==='character_images'||step==='world_images'){
        const type=step==='character_images'?'character':'location';
        const targets=records.filter(record=>record.type.toLowerCase()===type);
        const selections=await Promise.all(targets.map(record=>getImageSelection(workspaceId,revisionId,type,record.record_id)));
        targets.forEach((record,index)=>{if(!imageIds.has(selections[index].selection?.asset_id||''))gaps.push(`Select one image for ${record.name}.`);});
      } else if(videoWorkflowId===FL2VA_WORKFLOW_ID){
        for(const frame of frames){
          if(frameSkips?.skipped.some(row=>row.scene_number===frame.scene_number&&row.shot_number===frame.shot_number))continue;
          for(const role of ['first_frame','last_frame']){
            if(!media.assets.some(asset=>{
              const lineage=asset.metadata?.production_image_job?.settings?.lineage;
              return asset.roles.includes(role)&&lineage?.screenplay_revision_id===revisionId&&lineage?.clip_id===frame.clip_id;
            }))gaps.push(`Select the ${role.replace('_',' ')} for Scene ${frame.scene_number}, Shot ${frame.shot_number}.`);
          }
        }
      }
    }
    if(voices){
      const bound=new Set(voices.bindings.map(row=>row.character_id));
      const silent=new Set((voices.speech_statuses||[]).filter(row=>row.status==='not_speaking').map(row=>row.character_id));
      voices.characters.forEach(character=>{if(!silent.has(character.record_id)&&!bound.has(character.record_id))gaps.push(`Choose a voice for ${character.name}.`);});
    }
    return gaps;
  },[context]);
  useEffect(()=>{
    let alive=true;let running=false;
    setCheckedContext('');setMissing(['Checking saved selections…']);
    const update=async()=>{
      if(running)return;running=true;
      try{const gaps=await check();if(alive){setMissing(gaps);setCheckedContext(context);}}
      catch(error){if(alive){setMissing([`Could not check saved selections: ${(error as Error).message}`]);setCheckedContext(context);}}
      finally{running=false;}
    };
    void update();const timer=window.setInterval(()=>void update(),5000);
    window.addEventListener('vibe-character-voices-changed',update);
    window.addEventListener('vibe-image-master-selected',update);
    return()=>{alive=false;window.clearInterval(timer);window.removeEventListener('vibe-character-voices-changed',update);window.removeEventListener('vibe-image-master-selected',update);};
  },[check,refresh]);
  const destination=(skips:string[])=>step==='character_images'&&!skips.includes('world_images')?'worlds':step!=='frame_images'&&!skips.includes('frame_images')?'frames':'video';
  const nextDestination=destination(skippedStages);
  const next=async()=>{
    setChecking(true);
    try{
      const revisions=await listStoryScreenplays(workspaceId,0,100);
      if(!revisions.items.some(row=>row.screenplay_revision_id===revisionId&&row.accepted&&!row.stale))throw new Error('The screenplay changed. Reload this stage.');
      const gaps=await check();setMissing(gaps);if(gaps.length)return;
      const skips=await getAssistedStageSkips(workspaceId,revisionId);
      const target=destination(skips.skipped);
      if(target==='video'){if(!videoReady)throw new Error('Choose a planned shot and video workflow below.');onVideoNext();}
      else window.location.hash=`#/${target}?step=${target==='worlds'?'world_images':'frame_images'}&workspace_id=${encodeURIComponent(workspaceId)}`;
    }catch(error){setMissing([(error as Error).message]);}
    finally{setChecking(false);}
  };
  const label=nextDestination==='worlds'?'Scene Backgrounds':nextDestination==='frames'?'First & last frames':'Video Create';
  return <section className="card image-stage-continuation" aria-label="Continue to the next image stage"><div><b>Next: {label}</b><p aria-live="polite">{missing.length?missing.join(' '):nextDestination==='video'&&!videoReady?'Choose a planned shot and video workflow below.':'Minimum selections saved. Optional side views are not required.'}</p></div><button type="button" className="generate-button" disabled={checking||checkedContext!==context||missing.length>0||(nextDestination==='video'&&!videoReady)} onClick={()=>void next()}>{checking?'Checking…':`Next: ${label}`}</button></section>;
}

function ImageAssetsContent({ section, onSection, legacyRoute }: { section: 'characters'|'worlds'|'frames'; onSection: (value: 'characters'|'worlds'|'frames') => void; legacyRoute: boolean }) {
  const query = new URLSearchParams(window.location.hash.split('?')[1] || '');
  const explicitStepKey = query.get('step');
  const requestedStepKey = explicitStepKey || (!legacyRoute ? (section === 'worlds' ? 'world_images' : section === 'frames' ? 'frame_images' : 'character_images') : null);
  const requestedStoryStep = explicitStepKey === 'character_images' || explicitStepKey === 'world_images' || explicitStepKey === 'frame_images';
  const requestedRole: Role = requestedStepKey === 'world_images' ? 'world_master' : requestedStepKey === 'frame_images' ? (query.get('role') === 'last_frame' ? 'last_frame' : 'first_frame') : 'character_master';
  const requestedWorkspace = query.get('workspace_id') || '';
  const saved = readDraft();
  const [workspaceId,setWorkspaceId] = useState<string>(()=>{
    let videoWorkspace = '';
    try { videoWorkspace = JSON.parse(localStorage.getItem('vibe-video-draft-v1') || '{}').workspaceId || ''; } catch { /* Use the shared media workspace. */ }
    const cached = saved.workspaceId || videoWorkspace;
    return preferredMediaWorkspaceId([], requestedWorkspace || (cached==='tool-library'||cached?.startsWith('story-')?cached:''));
  });
  const [,setWorkspaces] = useState<StoryWorkspace[]>([]);
  const [role,setRole] = useState<Role>(requestedStoryStep ? requestedRole : legacyRoute && Object.hasOwn(stageLabel, saved.role) ? saved.role : section === 'worlds' ? 'world_master' : section === 'frames' ? (saved.role === 'last_frame' ? 'last_frame' : 'first_frame') : 'character_master');
  useEffect(() => { if (!requestedStoryStep && !legacyRoute) setRole(section === 'worlds' ? 'world_master' : section === 'frames' ? (role === 'last_frame' ? 'last_frame' : 'first_frame') : 'character_master'); }, [section]);
  const sameSavedStage = (legacyRoute && !requestedStoryStep) || (requestedStepKey === 'frame_images' ? ['first_frame','last_frame'].includes(saved.role) : saved.role?.startsWith(requestedStepKey === 'world_images' ? 'world_' : 'character_'));
  const [workflowId,setWorkflowId] = useState(sameSavedStage ? saved.workflowId || (section==='frames'?'qwen_image_edit_2511':'z_image_turbo') : section==='frames'?'qwen_image_edit_2511':'z_image_turbo');
  const [prompt,setPrompt] = useState(sameSavedStage ? saved.prompt || '' : '');
  const [promptKnowledge,setPromptKnowledge] = useState<ImagePromptDraft|null>(sameSavedStage ? saved.promptKnowledge || null : null);
  const [candidateCount,setCandidateCount] = useState<1|4|8>([1,4,8].includes(saved.candidateCount) ? saved.candidateCount : 4);
  const [zimageLora,setZimageLora]=useState<ZImageLora|null>(null);
  const [seed,setSeed] = useState<number>(saved.seed ?? 42);
  const [workflows,setWorkflows] = useState<ImageWorkflow[]>([]);
  const [runtime,setRuntime] = useState<RuntimeGuard|null>(null);
  const [gpuAdmission,setGpuAdmission] = useState<ImageGpuAdmission|null>(null);
  const [workerReady,setWorkerReady] = useState(false);
  const [batch,setBatch] = useState<ImageBatch|null>(null);
  const [assets,setAssets] = useState<MediaAsset[]>([]);
  const [folderReferences,setFolderReferences] = useState<Array<{asset:MediaAsset;token:string}>>([]);
  const [imagePreview,setImagePreview] = useState<MediaAsset|null>(null);
  const generationForm = useRef<HTMLDivElement|null>(null);
  const imagePreviewTrigger = useRef<HTMLElement|null>(null);
  const imagePreviewCloseButton = useRef<HTMLButtonElement|null>(null);
  const [sourceReferenceIds,setSourceReferenceIds] = useState<string[]>(sameSavedStage ? saved.sourceReferenceIds || [] : []);
  const [worldViewCount,setWorldViewCount] = useState<2|3|4|8>([2,3,4,8].includes(saved.worldViewCount) ? saved.worldViewCount : 4);
  const [preview,setPreview] = useState<any>(null);
  const [busy,setBusy] = useState(false);
  const [preparingPrompt,setPreparingPrompt] = useState(false);
  const [promptNeedsPreparation,setPromptNeedsPreparation] = useState(false);
  const [loadedPromptKey,setLoadedPromptKey] = useState('');
  const promptContextRef = useRef('');
  const [message,setMessage] = useState('');
  const [pending,setPending] = useState<any>(()=>readPending());
  const [selectingId,setSelectingId] = useState('');
  const [refresh,setRefresh] = useState(0);
  const [acceptedScreenplayId,setAcceptedScreenplayId] = useState<string>(saved.acceptedScreenplayId || '');
  const [targetRecords,setTargetRecords] = useState<StoryGraphRecord[]>([]);
  const [targetRecordId,setTargetRecordId] = useState<string>(saved.targetRecordId || '');
  const [masterSelections,setMasterSelections] = useState<Record<string,string>>({});
  const selectionKey = (revision:string,type:string,target:string) => JSON.stringify([revision,type,target]);
  const [frameTargets,setFrameTargets] = useState<FrameTarget[]>([]);
  const [frameTargetKey,setFrameTargetKey] = useState('');
  const [skippedFrameClipKeys,setSkippedFrameClipKeys] = useState<string[]>([]);
  const [frameSkipsReady,setFrameSkipsReady] = useState(!requestedStoryStep || requestedStepKey !== 'frame_images');
  const [frameSkipBusyContext,setFrameSkipBusyContext] = useState('');
  const [skippedAssistedStages,setSkippedAssistedStages] = useState<Array<'character_images'|'world_images'|'frame_images'>>([]);
  const [stageSkipBusy,setStageSkipBusy] = useState(false);
  const frameSkipContextKey = requestedStepKey === 'frame_images' && acceptedScreenplayId
    ? `${workspaceId.trim()}\0${acceptedScreenplayId}` : '';
  const frameSkipContextRef = useRef(frameSkipContextKey);
  frameSkipContextRef.current = frameSkipContextKey;
  const frameSkipBusy = !!frameSkipContextKey && frameSkipBusyContext === frameSkipContextKey;
  const [lineageStatus,setLineageStatus] = useState('');
  const [automatedStage,setAutomatedStage] = useState<ImageStageAdmission|null>(null);
  const [automatedStageBusy,setAutomatedStageBusy] = useState(false);
  const [automatedStageError,setAutomatedStageError] = useState('');
  const autoAdmissionKey = useRef('');
  const setupWorkflowKey = useRef('');
  const autoWorldViewKey = useRef('');
  const [manualStepStatus,setManualStepStatus] = useState<'loading'|'ready'|'blocked'|''>(requestedStoryStep ? 'loading' : '');
  const [manualStepReason,setManualStepReason] = useState('');
  const [storySetupMode,setStorySetupMode] = useState<string>('');
  const [loadedStoryContextKey,setLoadedStoryContextKey] = useState('');
  const previewCandidates = (batch?.jobs || automatedStage?.batches.flatMap(item=>item.jobs) || [])
    .map(candidate=>assets.find(asset=>asset.asset_id===candidate.output_asset_id)).filter((asset):asset is MediaAsset=>!!asset);
  const previewIndex = previewCandidates.findIndex(asset=>asset.asset_id===imagePreview?.asset_id);
  const movePreview = (offset:number) => {
    if(previewCandidates.length>1) setImagePreview(previewCandidates[(previewIndex+offset+previewCandidates.length)%previewCandidates.length]);
  };
  const previewOpen = !!imagePreview;
  useEffect(() => {
    if (!previewOpen) return;
    imagePreviewTrigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    imagePreviewCloseButton.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setImagePreview(null);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => {
      window.removeEventListener('keydown', closeOnEscape);
      imagePreviewTrigger.current?.focus();
      imagePreviewTrigger.current = null;
    };
  }, [previewOpen]);
  useEffect(()=>{
    if(!previewOpen)return;
    const navigate=(event:KeyboardEvent)=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();movePreview(event.key==='ArrowLeft'?-1:1);}};
    window.addEventListener('keydown',navigate);
    return()=>window.removeEventListener('keydown',navigate);
  },[previewOpen,previewIndex,previewCandidates.map(asset=>asset.asset_id).join(',')]);
  const [storySetup,setStorySetup] = useState<import('./lib/story-api').ProductionSetup|null>(null);
  const [videoWorkflowId,setVideoWorkflowId] = useState('');
  const [openingVideoShot,setOpeningVideoShot] = useState(false);
  const [videoShotError,setVideoShotError] = useState('');
  const active = readActive();
  const workflow = workflows.find(item=>item.workflow_id===workflowId);
  const visibleWorkflows = workflows.filter(item => item.workflow_id !== 'qwen_image_multi_angle_2511' || legacyRoute || section !== 'frames');
  useEffect(() => { let active = true; void listStoryWorkspaces().then(result => { if (active) {setWorkspaces(result.items || []);if(!requestedWorkspace)setWorkspaceId(current=>managedProjectId() ?? (current==='tool-library'||result.items.some(row=>row.workspace_id===current)?current:'tool-library'));} }).catch(() => { if (active) setWorkspaces([]); }); return () => { active = false; }; },[]);
  useEffect(() => {
    if (workflowId === 'qwen_image_multi_angle_2511' && !legacyRoute && section === 'frames') {
      setWorkflowId('z_image_turbo');
      setSourceReferenceIds([]);
      setPreview(null);
    }
  }, [workflowId, section, legacyRoute]);
  useEffect(() => {
    if (managedProjectId()===undefined && requestedWorkspace.trim() && requestedWorkspace.trim() !== workspaceId.trim())
      setWorkspaceId(requestedWorkspace.trim());
    if (requestedStoryStep) setRole(requestedRole);
  }, [requestedWorkspace, requestedStoryStep, requestedRole]);
  const targetType=role==='character_master'?'character':'location';
  const compatibleRecords=targetRecords.filter(record=>record.type.toLowerCase()===targetType);
  const selectedMasterId = masterSelections[selectionKey(acceptedScreenplayId,targetType,targetRecordId)] || '';
  const selectedTarget = compatibleRecords.find(record=>record.record_id===targetRecordId);
  const selectedFrameTarget = frameTargets.find(target=>`${target.scene_number}.${target.shot_number}`===frameTargetKey);
  const selectedFrameSkipped = skippedFrameClipKeys.includes(frameTargetKey);
  const roleMatchesStep = requestedStepKey === 'frame_images' ? ['first_frame','last_frame'].includes(role) : role === requestedRole;
  const effectiveWorkspaceId = managedProjectId() || requestedWorkspace.trim() || workspaceId.trim();
  const currentStoryContextKey = acceptedScreenplayId
    ? `${effectiveWorkspaceId}:${requestedStepKey}:${acceptedScreenplayId}` : '';
  const linkedStoryStage = requestedStoryStep || (!!acceptedScreenplayId && (!!targetRecordId || !!selectedFrameTarget));
  const manualStepReady = !linkedStoryStage || (!skippedAssistedStages.includes(requestedStepKey as 'character_images'|'world_images'|'frame_images') && manualStepStatus === 'ready' && currentStoryContextKey !== '' && loadedStoryContextKey === currentStoryContextKey && roleMatchesStep && !!acceptedScreenplayId &&
    (requestedStepKey === 'frame_images' ? frameSkipsReady && !!selectedFrameTarget && !selectedFrameSkipped : !!targetRecordId));
  const stageIsAutomatic = linkedStoryStage && manualStepStatus === 'blocked' && manualStepReason.endsWith('is automated from the saved setup.');
  const promptLength = Array.from(prompt).length;
  const effectiveRole:Role = workflowId === 'qwen_image_multi_angle_2511' ? (role === 'character_master' || role === 'character_view' ? 'character_view' : 'world_view') : role;
  const [destinationReady,setDestinationReady]=useState(false);
  const canGenerate = destinationReady && (!!workflow?.available && runtime?.safe_to_submit===true && gpuAdmission?.available===true && workerReady && (pending || (!promptNeedsPreparation && manualStepReady && !!workspaceId.trim() && !!prompt.trim() && promptLength <= IMAGE_PROMPT_MAX_CODEPOINTS))) && !(requestedStepKey === 'frame_images' && selectedFrameSkipped);

  const load = useCallback(async () => {
    try {
      const [catalog,gpu,worker] = await Promise.all([getImageWorkflows(true),getRuntimeGuard(),getImageWorker()]);
      setWorkflows(catalog.workflows); setRuntime(gpu); setGpuAdmission(catalog.gpu_admission || null); setWorkerReady(worker.available);
      if (!catalog.workflows.some(row=>row.workflow_id===workflowId)) setWorkflowId(catalog.workflows[0]?.workflow_id || 'z_image_turbo');
    } catch(error) { setMessage(`Readiness unavailable: ${(error as Error).message}`); setRuntime(null); setGpuAdmission(null); setWorkerReady(false); }
  },[workflowId]);
  useEffect(()=>{ void load(); },[load,refresh]);
  useEffect(()=>{ localStorage.setItem(DRAFT_KEY,JSON.stringify({workspaceId,role,workflowId,prompt,promptKnowledge,seed,targetRecordId,acceptedScreenplayId,sourceReferenceIds,worldViewCount,candidateCount})); },[workspaceId,role,workflowId,prompt,promptKnowledge,seed,targetRecordId,acceptedScreenplayId,sourceReferenceIds,worldViewCount,candidateCount]);
  useEffect(()=>{
    let alive=true; setLineageStatus('Loading screenplay targets…');
    const contextWorkspace = effectiveWorkspaceId;
    {
      setManualStepStatus('loading'); setManualStepReason('');
      setLoadedStoryContextKey(''); setAutomatedStage(null); setStorySetup(null); setStorySetupMode('');
    }
    if (requestedStepKey === 'frame_images') { setFrameSkipsReady(false); setSkippedFrameClipKeys([]); }
    if(!contextWorkspace.startsWith('story-')) {setAcceptedScreenplayId('');setTargetRecords([]);setLineageStatus('Standalone images · no story linked.');setManualStepStatus('ready');return ()=>{alive=false;};}
    const loadCharacters=async()=>{
      try {
        const revisions=await listStoryScreenplays(contextWorkspace,0,100);
        const accepted=revisions.items.find(item=>item.accepted&&!item.stale);
        if(!accepted){if(alive){setAcceptedScreenplayId('');setTargetRecords([]);setLineageStatus('No current accepted screenplay. Standalone images remain available.');if(requestedStoryStep){setManualStepStatus('blocked');setManualStepReason('No current accepted screenplay is available for this image stage.');}}return;}
        const screenplay=await getStoryScreenplayRevision(contextWorkspace,accepted.screenplay_revision_id);
        if (requestedStepKey === 'frame_images') {
          setFrameSkipsReady(false);
          const skipState = await getFramePreparationSkips(contextWorkspace, screenplay.screenplay_revision_id);
          if (alive) {
            setSkippedFrameClipKeys(skipState.skipped.map(item=>`${item.scene_number}.${item.shot_number}`));
            setFrameSkipsReady(true);
          }
        }
        {
          const setupKey = (requestedStoryStep ? requestedStepKey : role === 'character_master' ? 'character_images' : role === 'world_master' ? 'world_images' : 'frame_images') as 'character_images'|'world_images'|'frame_images';
          const stageName = setupKey === 'world_images' ? 'World image' : setupKey === 'frame_images' ? 'Clip frame' : 'Character image';
          try {
            const setupState = await getProductionSetup(contextWorkspace, screenplay.screenplay_revision_id);
            const stageSkips = await getAssistedStageSkips(contextWorkspace, screenplay.screenplay_revision_id);
            if (alive) setSkippedAssistedStages(stageSkips.skipped);
            if (alive && setupWorkflowKey.current !== `${contextWorkspace}:${screenplay.screenplay_revision_id}:${setupKey}`) {
              setupWorkflowKey.current = `${contextWorkspace}:${screenplay.screenplay_revision_id}:${setupKey}`;
              const configuredWorkflow = setupState.setup?.image_stage_settings?.[setupKey]?.workflow_id;
              if (configuredWorkflow) setWorkflowId(configuredWorkflow);
            }
            if (alive) { setStorySetupMode(setupState.setup?.mode || ''); setStorySetup(setupState.setup); setVideoWorkflowId(current => current || (setupState.setup?.automate_steps.video ? setupState.setup.video_workflow_id : '') || (stageSkips.skipped.includes('character_images') && stageSkips.skipped.includes('world_images') ? WORKFLOW_ID : stageSkips.skipped.includes('frame_images') ? R2V_WORKFLOW_ID : FL2VA_WORKFLOW_ID)); }
            const validManualStep = setupState.setup?.mode === 'assisted_manual' && setupState.setup.automate_steps[setupKey] === false;
            const selectedForAutomation = setupState.setup?.mode === 'assisted_manual' && setupState.setup.automate_steps[setupKey] === true;
            const automatedExecutorReady = ['character_images','world_images','frame_images'].includes(setupKey);
            if (alive) {
              setManualStepStatus(validManualStep ? 'ready' : 'blocked');
              setManualStepReason(!setupState.setup ? 'Save Automation & Parameters before generating a screenplay image.' : setupState.setup.mode !== 'assisted_manual' ? 'Image preparation is skipped in Fully automated mode.' : selectedForAutomation && automatedExecutorReady ? `${stageName} generation is automated from the saved setup.` : selectedForAutomation ? `${stageName} generation is selected for automation, but its executor is not connected yet.` : '');
            }
          } catch (error) {
            if (alive) {
              setManualStepStatus('blocked');
              setManualStepReason(`Could not verify the saved ${stageName.toLowerCase()} setup: ${(error as Error).message}`);
            }
            throw error;
          }
        }
        const graph=await getStoryGraphSnapshot(contextWorkspace,screenplay.graph_snapshot_id);
        if(graph.snapshot_id!==screenplay.graph_snapshot_id) throw new Error('Accepted screenplay graph snapshot could not be loaded exactly.');
        const rows=graph.records.filter(record=>record.kind==='entity'&&['character','location'].includes(record.type.toLowerCase()));
        const plannedFrames = await Promise.all((screenplay.screenplay?.scenes || []).flatMap(scene => (scene.shots || []).map(async shot => ({
          scene_number: scene.scene_number, shot_number: shot.shot_number,
          clip_id: await storyClipId(contextWorkspace, screenplay.screenplay_revision_id, scene.scene_number, shot.shot_number),
          scene_title: scene.slugline, summary: shot.action || scene.summary,
          dialogue: shot.dialogue, camera: shot.direction.camera, lighting: shot.direction.lighting, mood: shot.direction.mood,
        }))));
        if(alive){setAcceptedScreenplayId(screenplay.screenplay_revision_id);setTargetRecords(rows);setTargetRecordId(current=>rows.some(record=>record.record_id===current&&record.type.toLowerCase()===(role==='character_master'?'character':'location'))?current:(requestedStoryStep||!legacyRoute)?(rows.find(record=>record.type.toLowerCase()===(role==='character_master'?'character':'location'))?.record_id||''):'');setFrameTargets(plannedFrames);setFrameTargetKey(current=>current&&plannedFrames.some(target=>`${target.scene_number}.${target.shot_number}`===current)?current:(plannedFrames[0]?`${plannedFrames[0].scene_number}.${plannedFrames[0].shot_number}`:''));setLineageStatus(requestedStepKey==='frame_images'?`Accepted screenplay · ${screenplay.screenplay_revision_id} · ${plannedFrames.length} planned shot clips`:rows.length?`Accepted screenplay · ${screenplay.screenplay_revision_id}`:'Older graph has no canonical character or location targets. Standalone images remain available.');setLoadedStoryContextKey(`${contextWorkspace}:${requestedStepKey}:${screenplay.screenplay_revision_id}`);}
      } catch(error){if(alive){setLineageStatus(`Story targets unavailable: ${(error as Error).message}`);if(requestedStoryStep){setManualStepStatus('blocked');setManualStepReason(`Could not verify the accepted screenplay and setup: ${(error as Error).message}`);}}}
    };
    void loadCharacters(); return ()=>{alive=false;};
  },[workspaceId,requestedStepKey==='frame_images'?'frame':role,requestedWorkspace,requestedStoryStep,requestedStepKey,requestedRole,refresh]);
  const toggleAssistedStageSkip = async () => {
    if (!requestedStepKey || !acceptedScreenplayId || !['character_images','world_images','frame_images'].includes(requestedStepKey) || stageSkipBusy) return;
    const step = requestedStepKey as 'character_images'|'world_images'|'frame_images';
    const skip = !skippedAssistedStages.includes(step);
    setStageSkipBusy(true);
    try {
      const result = await setAssistedStageSkip(workspaceId.trim(), acceptedScreenplayId, step, skip);
      setSkippedAssistedStages(result.skipped);
      setRefresh(value=>value+1);
      setMessage(skip ? 'This optional stage is explicitly skipped for the accepted screenplay.' : 'Stage skip removed. Complete this manual stage before continuing.');
    } catch (error) {
      setMessage(`Could not save stage skip: ${(error as Error).message}`);
    } finally { setStageSkipBusy(false); }
  };
  const openStoryVideoShot = async () => {
    if (!workspaceId.trim() || !acceptedScreenplayId || !selectedFrameTarget || !videoWorkflowId || openingVideoShot) return;
    setOpeningVideoShot(true); setVideoShotError('');
    try {
      const revisions = await listStoryScreenplays(workspaceId.trim(), 0, 100);
      const currentAccepted = revisions.items.find(item => item.accepted && !item.stale);
      if (currentAccepted?.screenplay_revision_id !== acceptedScreenplayId) throw new Error('The accepted screenplay changed. Reload this stage and choose the shot again.');
      const [screenplay, setupState] = await Promise.all([
        getStoryScreenplayRevision(workspaceId.trim(), acceptedScreenplayId),
        getProductionSetup(workspaceId.trim(), acceptedScreenplayId),
      ]);
      const setup = setupState.setup;
      if (!screenplay.accepted || setup?.mode !== 'assisted_manual' || setup.automate_steps.video) throw new Error('Video Create is available here only when the saved setup is Assisted manual with video automation unchecked.');
      const shotKey = `${selectedFrameTarget.scene_number}.${selectedFrameTarget.shot_number}`;
      const shotExists = screenplay.screenplay.scenes.some(scene => scene.scene_number === selectedFrameTarget.scene_number && scene.shots.some(shot => shot.shot_number === selectedFrameTarget.shot_number));
      if (!shotExists) throw new Error('That shot is no longer in the accepted screenplay. Reload and choose another shot.');
      const prepared = await prepareStoryPrompt(workspaceId.trim(), acceptedScreenplayId, shotKey, videoWorkflowId);
      if (prepared.shot_key !== shotKey || prepared.workflow_id !== videoWorkflowId || !prepared.prompt.trim()) throw new Error('The prepared prompt did not match the selected shot and workflow. Nothing was opened in Video Create.');
      const saved = await saveStoryPromptShot(workspaceId.trim(), acceptedScreenplayId, setup, shotKey, {
        prompt: prepared.prompt, workflow_id: prepared.workflow_id, knowledge_ref: prepared.knowledge_ref,
      });
      const savedDraft = saved.drafts[shotKey];
      if (!saved.setup_matches_current || saved.screenplay_revision_id !== acceptedScreenplayId || !savedDraft || savedDraft.prompt !== prepared.prompt || savedDraft.workflow_id !== videoWorkflowId) throw new Error('The saved prompt could not be verified against this screenplay and setup. Nothing was opened in Video Create.');
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${workspaceId.trim()}\0${acceptedScreenplayId}\0${selectedFrameTarget.scene_number}\0${selectedFrameTarget.shot_number}`));
      const clipId = `story-${Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('').slice(0, 40)}`;
      const promptDigest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(savedDraft.prompt));
      const sourcePromptSha256 = Array.from(new Uint8Array(promptDigest), byte => byte.toString(16).padStart(2, '0')).join('');
      localStorage.setItem(STORY_VIDEO_HANDOFF_KEY, JSON.stringify({
        workspace_id: workspaceId.trim(), screenplay_revision_id: acceptedScreenplayId, setup_hash: saved.setup_hash,
        scene_number: selectedFrameTarget.scene_number, shot_number: selectedFrameTarget.shot_number,
        source_prompt_sha256: sourcePromptSha256, workflow_id: videoWorkflowId,
        knowledge_ref: savedDraft.knowledge_ref, prompt: savedDraft.prompt, clip_id: clipId,
      }));
      window.location.hash = '#/video';
    } catch (error) { setVideoShotError((error as Error).message); }
    finally { setOpeningVideoShot(false); }
  };

  const retryAutomatedStage=useCallback(async()=>{
    if(!workspaceId.trim()||!acceptedScreenplayId||!(requestedStepKey==='character_images'||requestedStepKey==='world_images'||requestedStepKey==='frame_images'))return;
    setAutomatedStageBusy(true);setAutomatedStageError('');
    try {
      const result=await startAutomatedImageStage(workspaceId.trim(),acceptedScreenplayId,requestedStepKey);
      setAutomatedStage(current=>current&&current.step===result.step?{...result,batches:[...current.batches,...result.batches.filter(batch=>!current.batches.some(existing=>existing.batch_id===batch.batch_id))]}:result);
    }
    catch(error){setAutomatedStageError((error as Error).message);}
    finally{setAutomatedStageBusy(false);}
  },[workspaceId,acceptedScreenplayId]);
  useEffect(()=>{
    if(!requestedStoryStep||manualStepStatus==='loading'||!manualStepReason.endsWith('is automated from the saved setup.')||!acceptedScreenplayId||loadedStoryContextKey!==`${effectiveWorkspaceId}:${requestedStepKey}:${acceptedScreenplayId}`)return;
    const key=`${effectiveWorkspaceId}:${acceptedScreenplayId}:${requestedStepKey}`;
    if(autoAdmissionKey.current===key)return;
    autoAdmissionKey.current=key;
    void retryAutomatedStage();
  },[requestedStoryStep,manualStepStatus,manualStepReason,effectiveWorkspaceId,acceptedScreenplayId,requestedStepKey,loadedStoryContextKey,retryAutomatedStage]);
  useEffect(()=>{
    if(requestedStepKey!=='world_images'||!automatedStage?.batches?.length||automatedStage.step!=='world_images')return;
    const masters=automatedStage.batches.flatMap(batch=>batch.jobs).filter(job=>job.asset_role==='world_master');
    if(!masters.length||masters.some(job=>job.status==='queued'||job.status==='running'||
      job.director_review?.resolution_status==='reviewing'||job.director_review?.resolution_status==='review_recovery_pending'||
      job.director_review?.resolution_status==='retake_queued'))return;
    const accepted=masters.filter(job=>job.director_review?.resolution_status==='accepted');
    if(!accepted.length)return;
    const key=`${workspaceId}:${accepted.map(job=>job.job_id).sort().join(',')}`;
    if(autoWorldViewKey.current===key)return;
    autoWorldViewKey.current=key;
    void retryAutomatedStage();
  },[requestedStepKey,automatedStage?.batches,automatedStage?.step,workspaceId,retryAutomatedStage]);
  useEffect(()=>{
    if(!automatedStage?.batches?.length||!workspaceId.trim())return;
    let alive=true;
    const poll=async()=>{
      try {
        const updated=await Promise.all(automatedStage.batches.map(async batch=>({
          ...batch,...await getImageBatch(workspaceId.trim(),batch.batch_id),
        })));
        if(alive){setAutomatedStage(current=>current?{...current,batches:updated}:current);const rows=await listMediaAssets(workspaceId.trim(),'image');if(alive)setAssets(rows.assets);}
      }catch(error){if(alive)setAutomatedStageError((error as Error).message);}
    };
    void poll();const timer=window.setInterval(()=>void poll(),3000);
    return()=>{alive=false;window.clearInterval(timer);};
  },[automatedStage?.run_id,automatedStage?.batches.map(batch=>batch.batch_id).join(','),workspaceId]);
  useEffect(()=>{
    if(!active?.workspaceId || !active?.batchId || active.workspaceId!==workspaceId.trim()) {setBatch(null);return;}
    let alive=true;
    const poll=async()=>{ try { const value=await getImageBatch(active.workspaceId,active.batchId); if(alive){const stageRole=legacyRoute?(role.startsWith('world_')?'world':['first_frame','last_frame'].includes(role)?'frame':'character'):requestedStepKey==='world_images'?'world':requestedStepKey==='frame_images'?'frame':'character'; const belongs=value.jobs.some(job=>stageRole==='frame'?['first_frame','last_frame'].includes(job.asset_role||''):(job.asset_role||'').startsWith(stageRole+'_'));setBatch(belongs?value:null); const rows=await listMediaAssets(active.workspaceId,'image'); if(alive)setAssets(rows.assets);} } catch(error){ if(alive)setMessage(`Could not refresh candidate batch: ${(error as Error).message}`); } };
    void poll(); const timer=window.setInterval(()=>void poll(),3000); return ()=>{alive=false;window.clearInterval(timer);};
  },[active?.workspaceId,active?.batchId,workspaceId,requestedStepKey,legacyRoute,role,refresh]);
  useEffect(()=>{
    let alive=true;
    const targets = new Map<string,{revision:string;type:string;target:string}>();
    if (acceptedScreenplayId && targetRecordId && ['character_master','world_master'].includes(role))
      targets.set(selectionKey(acceptedScreenplayId,targetType,targetRecordId),{revision:acceptedScreenplayId,type:targetType,target:targetRecordId});
    for (const candidate of batch?.jobs || []) {
      const frozen = candidate.settings?.lineage || assets.find(asset=>asset.asset_id===candidate.output_asset_id)?.metadata?.production_image_job?.settings?.lineage;
      if (frozen?.screenplay_revision_id && frozen.target_record_id && ['character','location'].includes(frozen.target_type || ''))
        targets.set(selectionKey(frozen.screenplay_revision_id,frozen.target_type!,frozen.target_record_id),{revision:frozen.screenplay_revision_id,type:frozen.target_type!,target:frozen.target_record_id});
    }
    if (acceptedScreenplayId && ['world_images','frame_images'].includes(requestedStepKey||'')) {
      for (const record of targetRecords.filter(record=>requestedStepKey==='frame_images'||record.type.toLowerCase()==='location')) {
        const type=record.type.toLowerCase();
        targets.set(selectionKey(acceptedScreenplayId,type,record.record_id),{revision:acceptedScreenplayId,type,target:record.record_id});
      }
    }
    if(acceptedScreenplayId && requestedStepKey==='frame_images') {
      for(const frame of frameTargets) for(const type of ['first_frame','last_frame'])
        targets.set(selectionKey(acceptedScreenplayId,type,frame.clip_id),{revision:acceptedScreenplayId,type,target:frame.clip_id});
    }
    void Promise.all([...targets].map(async ([key,target])=> {
      try { const value=await getImageSelection(workspaceId.trim(),target.revision,target.type,target.target);
        return [key,value.selection?.asset_id || ''] as const;
      } catch { return [key,''] as const; }
    })).then(rows=>{if(alive)setMasterSelections(Object.fromEntries(rows));});
    return ()=>{alive=false;};
  },[workspaceId,acceptedScreenplayId,targetRecordId,role,targetType,requestedStepKey,JSON.stringify(frameTargets.map(frame=>frame.clip_id)),JSON.stringify(targetRecords.map(record=>[record.record_id,record.type])),JSON.stringify(batch?.jobs.map(job=>[job.job_id,job.output_asset_id,job.settings?.lineage])),JSON.stringify(assets.map(asset=>[asset.asset_id,asset.metadata?.production_image_job?.settings?.lineage])),refresh]);
  const assetById=useMemo(()=>new Map(assets.map(asset=>[asset.asset_id,asset])),[assets]);
  const lineage=['character_master','world_master'].includes(role)&&targetRecordId&&acceptedScreenplayId?{workspace_id:workspaceId.trim(),screenplay_revision_id:acceptedScreenplayId,target_record_id:targetRecordId,asset_role:role}:['first_frame','last_frame'].includes(role)&&selectedFrameTarget&&acceptedScreenplayId?{workspace_id:workspaceId.trim(),screenplay_revision_id:acceptedScreenplayId,scene_number:selectedFrameTarget.scene_number,shot_number:selectedFrameTarget.shot_number,clip_id:selectedFrameTarget.clip_id,asset_role:role}:{};
  useEffect(()=>{let alive=true;if(!workspaceId.trim())return()=>{alive=false;};void listMediaAssets(workspaceId.trim(),'image').then(result=>{if(alive)setAssets(result.assets);}).catch(error=>{if(alive)setMessage(`Could not load image references: ${(error as Error).message}`);});return()=>{alive=false;};},[workspaceId]);
  const frameReferenceFlow=requestedStepKey==='frame_images' && !!acceptedScreenplayId;
  const referencesRequired=['qwen_image_edit_2511','qwen_image_multi_angle_2511'].includes(workflowId);
  const maxReferences=workflowId==='qwen_image_multi_angle_2511'?1:3;
  const selectedFrameReferenceIds=new Set(targetRecords.map(record=>masterSelections[selectionKey(acceptedScreenplayId,record.type.toLowerCase(),record.record_id)]).filter(Boolean));
  const openingFrameId=selectedFrameTarget?masterSelections[selectionKey(acceptedScreenplayId,'first_frame',selectedFrameTarget.clip_id)]:'';
  if(role==='last_frame' && openingFrameId) selectedFrameReferenceIds.add(openingFrameId);
  const referenceAssets=rankMediaAssets(workflowId==='qwen_image_multi_angle_2511'?assets.filter(asset=>asset.roles.includes(effectiveRole==='character_view'?'character_master':'world_master') && (!targetRecordId || asset.asset_id===selectedMasterId)):frameReferenceFlow?assets.filter(asset=>{
    if(selectedFrameReferenceIds.has(asset.asset_id))return true;
    const frozen=asset.metadata?.production_image_job?.settings?.lineage;
    return asset.roles.some(role=>['character_view','world_view'].includes(role)) && frozen?.screenplay_revision_id===acceptedScreenplayId && targetRecords.some(record=>record.record_id===frozen.target_record_id);
  }):assets,'','newest');
  const allowedReferenceIds=new Set(referenceAssets.map(asset=>asset.asset_id));
  const selectedReferences=sourceReferenceIds.filter(id=>!frameReferenceFlow||allowedReferenceIds.has(id)).map(id=>assets.find(asset=>asset.asset_id===id)).filter((asset):asset is MediaAsset=>!!asset);
  const useFolderReferences=async(files:File[])=>{
    if(workflowId!=='qwen_image_edit_2511'){setMessage('Choose Qwen Image Edit 2511 to attach folder images as references.');return;}
    const remaining=Math.max(0,3-selectedReferences.length);
    const chosen=files.filter(file=>['image/png','image/jpeg','image/webp'].includes(file.type.toLowerCase())||/\.(png|jpe?g|webp)$/i.test(file.name)).slice(0,remaining);
    if(!chosen.length){setMessage(remaining?'Choose PNG, JPEG or WebP image files.':'This edit request already has three references.');return;}
    setBusy(true);
    const added:Array<{asset:MediaAsset;token:string}>=[];
    try{
      for(const file of chosen){const token=imageToken();const asset=await stageTemporaryImageReference(workspaceId.trim(),file,token);added.push({asset,token});}
      setFolderReferences(current=>[...current,...added]);
      setAssets(current=>[...added.map(item=>item.asset),...current.filter(asset=>!added.some(item=>item.asset.asset_id===asset.asset_id))]);
      setSourceReferenceIds(current=>[...current,...added.map(item=>item.asset.asset_id)].slice(0,3));setPreview(null);
      setMessage(`${added.length} temporary folder reference${added.length===1?'':'s'} added to Qwen Image Edit.`);
    }catch(error){await Promise.allSettled(added.map(item=>deleteTemporaryImageAsset(workspaceId.trim(),item.asset.asset_id,item.token)));setMessage(`Could not stage folder reference: ${(error as Error).message}`);}
    finally{setBusy(false);}
  };
  const updateReferences=(next:string[])=>{
    const retained=new Set(next);
    const removed=folderReferences.filter(item=>!retained.has(item.asset.asset_id));
    setFolderReferences(current=>current.filter(item=>retained.has(item.asset.asset_id)));
    if(removed.length){void Promise.allSettled(removed.map(item=>deleteTemporaryImageAsset(workspaceId.trim(),item.asset.asset_id,item.token)));setAssets(current=>current.filter(asset=>!removed.some(item=>item.asset.asset_id===asset.asset_id)));}
    setSourceReferenceIds(next);setPreview(null);
  };
  useEffect(()=>{
    if(!folderReferences.length||!batch?.jobs?.length||batch.jobs.some(job=>!['completed','failed','cancelled'].includes(job.status)))return;
    const stale=folderReferences;
    setFolderReferences([]);setSourceReferenceIds(current=>current.filter(id=>!stale.some(item=>item.asset.asset_id===id)));
    void Promise.allSettled(stale.map(item=>deleteTemporaryImageAsset(workspaceId.trim(),item.asset.asset_id,item.token)));
    setAssets(current=>current.filter(asset=>!stale.some(item=>item.asset.asset_id===asset.asset_id)));
  },[batch?.batch_id,batch?.jobs?.map(job=>`${job.job_id}:${job.status}`).join(','),folderReferences.length,workspaceId]);
  const sourceReferences=selectedReferences.map(asset=>({asset_id:asset.asset_id,sha256:asset.sha256}));
  const currentPromptGuidance = workflows.find(item=>item.workflow_id===workflowId)?.prompt_knowledge_ref;
  const [projectPromptVersion,setProjectPromptVersion]=useState<{key:string;revision:number}|null>(null);
  const projectPromptKey=`${workspaceId.trim()}:${acceptedScreenplayId}`;
  useEffect(()=>{
    if(!acceptedScreenplayId)return;
    let alive=true;
    void getPromptGuidance(workspaceId.trim(),acceptedScreenplayId).then(value=>{if(alive)setProjectPromptVersion({key:projectPromptKey,revision:value.revision});})
      .catch(()=>{if(alive)setProjectPromptVersion({key:projectPromptKey,revision:0});});
    return()=>{alive=false;};
  },[projectPromptKey]);
  const promptContextKey = workflows.some(item=>item.workflow_id===workflowId) && storySetupMode === 'assisted_manual' && (!requestedStoryStep || loadedStoryContextKey === currentStoryContextKey) && acceptedScreenplayId && (!requestedStoryStep || roleMatchesStep) &&
    (requestedStepKey === 'frame_images' ? !!selectedFrameTarget : !!selectedTarget)
    ? JSON.stringify([requestedStepKey==='frame_images'?'frame-brief-v4':workflowId==='qwen_image_multi_angle_2511'?'asset-brief-v6':'asset-brief-v3', workspaceId.trim(), acceptedScreenplayId, role, requestedStepKey==='frame_images'?'':targetRecordId, frameTargetKey, workflowId, currentPromptGuidance?.knowledge_id,
        referencesRequired ? sourceReferences : [], workflowId === 'qwen_image_multi_angle_2511' ? worldViewCount : null,
        ...(projectPromptVersion?.key===projectPromptKey&&projectPromptVersion.revision>0?['prompt-rules',projectPromptVersion.revision]:[])]) : '';
  promptContextRef.current = promptContextKey;
  const promptContextReady = !requestedStoryStep || !!promptContextKey;
  const promptLoading = preparingPrompt || (!!promptContextKey && loadedPromptKey !== promptContextKey);
  const draftRequest = () => ({workspace_id:workspaceId.trim(),workflow_id:workflowId,prompt,
    ...(workflowId==='qwen_image_multi_angle_2511'?{world_view_count:worldViewCount}:{}),
    ...(referencesRequired?{source_references:sourceReferences}:{}),...lineage,asset_role:effectiveRole});
  useEffect(() => {
    if (!promptContextKey || pending || skippedAssistedStages.includes(requestedStepKey as 'character_images'|'world_images'|'frame_images')) {
      setPreparingPrompt(false);
      return;
    }
    if(projectPromptVersion?.key!==projectPromptKey)return;
    let alive = true;
    let cached;
    try { cached = JSON.parse(localStorage.getItem(PROMPTS_KEY) || '{}')[promptContextKey]; } catch { /* Recover with a new draft. */ }
    setPreview(null);
    if (cached?.prompt?.trim() && cached.knowledge) {
      setPrompt(cached.prompt); setPromptKnowledge(cached.knowledge); setPromptNeedsPreparation(false); setLoadedPromptKey(promptContextKey);
      setPreparingPrompt(false);
      return;
    }
    setPrompt(''); setPromptKnowledge(null); setPreparingPrompt(true);
    if (referencesRequired && (sourceReferences.length < 1 || sourceReferences.length > maxReferences)) {
      setPreparingPrompt(false); setLoadedPromptKey(promptContextKey);
      setMessage('Choose the reference images to prepare this workflow’s prompt.');
      return;
    }
    setMessage('Director is preparing an editable prompt for this target and workflow…');
    void prepareImagePrompt({...draftRequest(), prompt: ''}).then(result => {
      if (!alive) return;
      setPrompt(result.prompt); setPromptKnowledge(result); setPromptNeedsPreparation(false);
      setMessage('Director prompt ready. Review or edit it before generating images.');
    }).catch(error => { if (alive) setMessage(`Prompt was not prepared: ${(error as Error).message}. Use Prepare prompt to retry.`); })
      .finally(() => { if (alive) { setPreparingPrompt(false); setLoadedPromptKey(promptContextKey); } });
    return () => { alive = false; };
  }, [promptContextKey, !!pending, JSON.stringify(skippedAssistedStages),projectPromptVersion?.key,projectPromptKey]);
  useEffect(() => {
    if (!promptContextKey || loadedPromptKey !== promptContextKey || preparingPrompt || !prompt.trim() || !promptKnowledge) return;
    try {
      const drafts = JSON.parse(localStorage.getItem(PROMPTS_KEY) || '{}');
      drafts[promptContextKey] = {prompt, knowledge: promptKnowledge};
      localStorage.setItem(PROMPTS_KEY, JSON.stringify(drafts));
    } catch { /* The current draft remains editable if local storage is full. */ }
  }, [promptContextKey, loadedPromptKey, preparingPrompt, prompt, promptKnowledge]);
  const preparePrompt=async()=>{
    const context = promptContextKey;
    setBusy(true);setMessage('');
    try {
      const result=await prepareImagePrompt(draftRequest());
      if (promptContextRef.current !== context) return;
      setPrompt(result.prompt);setPromptKnowledge(result); setPromptNeedsPreparation(false);setPreview(null);
      setMessage(`Prompt draft prepared from workflow guidance v${result.knowledge_ref.guidance_version}. Review or edit it before generation.`);
    } catch(error) { if (promptContextRef.current === context) setMessage(`Prompt was not prepared: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const useManualStage = async () => {
    if (!storySetup || !acceptedScreenplayId || !requestedStepKey || automatedStageBusy || busy) return;
    const step = requestedStepKey as 'character_images'|'world_images'|'frame_images';
    const imageStageSettings = {...storySetup.image_stage_settings};
    delete imageStageSettings[step];
    setBusy(true);
    try {
      const result = await saveProductionSetup(workspaceId.trim(), acceptedScreenplayId,
        {...storySetup, automate_steps: {...storySetup.automate_steps, [step]: false}, image_stage_settings: imageStageSettings});
      setStorySetup(result.setup); setManualStepStatus('ready'); setManualStepReason('');
      setAutomatedStage(null); setAutomatedStageError('');
      setMessage('This stage now uses manual generation. Review the Director prompt, generate candidates, then select your preferred image.');
    } catch(error) { setMessage(`Could not change this stage: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const checkPrompt=async()=>{ setBusy(true);setMessage('');try{const result=await validateImageRequest({zimage_lora:zimageLora,workflow_id:workflowId,initial_candidate_count:candidateCount,prompt,control_mode:'assisted_manual',seed,output_prefix:`${workspaceId||'isolated'}/${effectiveRole}`,workspace_id:workspaceId.trim(),...(workflowId==='qwen_image_multi_angle_2511'?{world_view_count:worldViewCount}:{}),...(referencesRequired?{source_references:sourceReferences}:{}),...lineage,asset_role:effectiveRole});setPreview(result);setMessage(workflowId==='qwen_image_multi_angle_2511'?`Compiled ${worldViewCount} separately labeled directional views. Preview only; no ComfyUI job was submitted.`:`Compiled ${candidateCount} candidates. Preview only; no ComfyUI job was submitted.`);}catch(error){setPreview(null);setMessage((error as Error).message);}finally{setBusy(false);} };
  const selectCandidate=async(jobId:string, candidateRole:Role = effectiveRole)=>{
    setSelectingId(jobId);setMessage('');
    try {
      const candidate=batch?.jobs.find(job=>job.job_id===jobId);
      const frozen=candidate?.settings?.lineage || assetById.get(candidate?.output_asset_id || '')?.metadata?.production_image_job?.settings?.lineage;
      const selectedLineage=frozen ? {screenplay_revision_id:frozen.screenplay_revision_id!,
        ...(frozen.target_record_id?{target_record_id:frozen.target_record_id}: {scene_number:frozen.scene_number,shot_number:frozen.shot_number,clip_id:frozen.clip_id}),asset_role:candidateRole} : undefined;
      const result=await acceptImageCandidate(active?.workspaceId||workspaceId,jobId,candidateRole,selectedLineage);
      setAssets(current=>[result.asset,...current.filter(asset=>asset.asset_id!==result.asset.asset_id)]);
      if(result.target_selection && frozen) setMasterSelections(current=>({...current,
        [selectionKey(frozen.screenplay_revision_id!,['first_frame','last_frame'].includes(candidateRole)?candidateRole:frozen.target_type!,frozen.clip_id||frozen.target_record_id!)]:result.target_selection!.asset_id}));
      if(result.target_selection && frozen) window.dispatchEvent(new CustomEvent('vibe-image-master-selected',{detail:{workspaceId:active?.workspaceId||workspaceId,revisionId:frozen.screenplay_revision_id,targetId:frozen.target_record_id,targetType:frozen.target_type,asset:result.asset}}));
      setMessage(`${stageLabel[candidateRole]} saved in the workspace library. You can choose a different master at any time.`);
    }catch(error){setMessage(`Could not select image: ${(error as Error).message}`);}
    finally{setSelectingId('');}
  };
  const generate=async()=>{
    if(!canGenerate||busy)return;
    setBusy(true);setMessage('');
    let submissionStarted=false;
    try {
      let request=pending;
      if(!request){
        const [catalog,gpu,worker]=await Promise.all([getImageWorkflows(true),getRuntimeGuard(),getImageWorker()]);
        const exact=catalog.workflows.find(item=>item.workflow_id===workflowId);
        if(!exact?.available||gpu.safe_to_submit!==true||catalog.gpu_admission?.available!==true||!worker.available)throw new Error(exact?.disabled_reason||gpu.reason||catalog.gpu_admission?.reason||worker.reason||'Workflow, runtime checks and image worker must all be ready.');
        const promptKnowledgeRef=promptKnowledge&&promptKnowledge.workflow_id===workflowId?promptKnowledge.knowledge_ref:undefined;
        request={zimage_lora:zimageLora,workflow_id:workflowId,initial_candidate_count:candidateCount,prompt,control_mode:'assisted_manual',seed,output_prefix:`${workspaceId}/${effectiveRole}`,workspace_id:workspaceId.trim(),idempotency_key:newKey(),asset_role:effectiveRole,...(promptKnowledgeRef?{prompt_knowledge_ref:promptKnowledgeRef}:{}),...(workflowId==='qwen_image_multi_angle_2511'?{world_view_count:worldViewCount}:{}),...(referencesRequired?{source_references:sourceReferences}:{}),...(workflowId==='qwen_image_multi_angle_2511'&&targetRecordId&&acceptedScreenplayId?{screenplay_revision_id:acceptedScreenplayId,target_record_id:targetRecordId,asset_role:effectiveRole}:workflowId==='qwen_image_multi_angle_2511'?{}:lineage)};
      }
      if(!pending && request.screenplay_revision_id){
        const currentSetup=await getProductionSetup(request.workspace_id,request.screenplay_revision_id);
        const step=['character_master','character_view'].includes(request.asset_role)?'character_images':['world_master','world_view'].includes(request.asset_role)?'world_images':'frame_images';
        if(currentSetup.setup?.mode!=='assisted_manual'||currentSetup.setup.automate_steps[step]!==false){
          localStorage.removeItem(PENDING_KEY);setPending(null);setRefresh(value=>value+1);
          throw new Error('This stage is configured for automation. Use its stage controls or choose Use manual generation for this stage.');
        }
      }
      const compiled=request===pending?null:await validateImageRequest(request);
      // Freeze only at the submission boundary; validation never queues work.
      localStorage.setItem(PENDING_KEY,JSON.stringify(request));setPending(request);
      submissionStarted=true;
      const result=await createImageBatch(request);
      localStorage.setItem(ACTIVE_KEY,JSON.stringify({workspaceId:request.workspace_id,batchId:result.batch_id}));
      localStorage.removeItem(PENDING_KEY);setPending(null);setBatch({batch_id:result.batch_id,jobs:result.jobs,generation_policy:compiled?.generation_policy||{}});
      setMessage('Candidate batch queued. Progress will reconnect after reload.');setRefresh(value=>value+1);
    }catch(error){
      if(error instanceof ImageApiError && error.code==='image_prompt_guidance_changed' && error.admissionState==='not_created'){
        localStorage.removeItem(PENDING_KEY);setPending(null);
        try {
          const cached=JSON.parse(localStorage.getItem(PROMPTS_KEY)||'{}');
          delete cached[promptContextKey];localStorage.setItem(PROMPTS_KEY,JSON.stringify(cached));
        } catch { /* Preparation can replace an unreadable cache. */ }
        setPromptKnowledge(null);setPromptNeedsPreparation(true);setLoadedPromptKey('');setPreview(null);
        setMessage('No job was queued. Workflow guidance changed; prepare the prompt again, review it, then Generate.');
      } else if(error instanceof ImageApiError && error.admissionState==='not_created'){
        localStorage.removeItem(PENDING_KEY);setPending(null);setRefresh(value=>value+1);
        setMessage(`No job was queued: ${error.message}`);
      } else setMessage(submissionStarted
        ? `Generation was not confirmed: ${(error as Error).message}. Retry resumes the exact saved request.`
        : `Generation was not started: ${(error as Error).message}`);
    }
    finally{setBusy(false);}
  };
  const settled=batch?.jobs.every(job=>['completed','failed','cancelled','recovery_required'].includes(job.status));
  const automatedCandidates=automatedStage?.batches.flatMap(stageBatch=>stageBatch.jobs)||[];
  const imageSettings=<div className="image-settings">
    <OutputDestination tool="image-generation" workspaceId={workspaceId} disabled={busy||!!pending} onReady={setDestinationReady}/>

    <details className="card image-workflow-info"><summary>Workflow details</summary>
      {workflow ? <><b>{workflow.label}</b><dl><div><dt>Output</dt><dd>{workflow.defaults.width} × {workflow.defaults.height}</dd></div><div><dt>Steps</dt><dd>{workflow.defaults.steps}</dd></div><div><dt>CFG</dt><dd>{workflow.defaults.cfg}</dd></div><div><dt>Manual generation</dt><dd>{stageIsAutomatic ? 'Stage set to automatic' : !manualStepReady ? 'Stage not ready' : workflow.available ? 'Ready' : 'Blocked'}</dd></div><div><dt>Assisted automation</dt><dd>{workflow.automation_available ? 'Verified' : 'Needs one successful manual run'}</dd></div></dl></> : <p>Checking workflow catalog…</p>}
      <p>Image generation is skipped in Fully automated mode. Qwen Edit uses the selected 1–3 workspace images.</p>
    </details>
    <details className="card image-reference-folder-details"><summary>Reference folder images</summary><LocalImageFolderBrowser title="Browse local reference images" maxReferences={Math.max(0,3-selectedReferences.length)} referencesEnabled={workflowId==='qwen_image_edit_2511'} onUseAsReference={files=>void useFolderReferences(files)}/></details>

  </div>;
  return <div className="content-wrap image-assets-page">
    <div className="page-heading"><div><div className="eyebrow">CHARACTERS & ASSETS</div><h1>{requestedStoryStep ? requestedStepKey === 'frame_images' ? 'Clip frame step' : requestedRole === 'world_master' ? 'Scene background step' : 'Character image step' : legacyRoute ? 'Characters, scene backgrounds & frames' : section === 'characters' ? 'Characters & voices' : section === 'worlds' ? 'Scene Backgrounds' : 'First & last frames'}</h1><p>{requestedStoryStep ? requestedStepKey === 'frame_images' ? 'Prepare optional first or last frame references for an accepted screenplay shot.' : requestedRole === 'world_master' ? 'Generate and review location references for this accepted screenplay.' : 'Generate and review character references for this accepted screenplay.' : section === 'characters' ? 'Create character portraits and assign a saved voice to each character.' : section === 'worlds' ? 'Create a base location, then use it for scene-specific conditions and directional views.' : 'Create first and last frame candidates for each planned shot.'}</p></div><button className="quiet-button" onClick={()=>setRefresh(value=>value+1)} disabled={busy}><RefreshCw size={15}/> Check readiness</button></div>
    {acceptedScreenplayId && <section className="card" role={manualStepStatus === 'blocked' && !manualStepReason.endsWith('is automated from the saved setup.') ? 'alert' : 'status'}>{manualStepStatus === 'loading' ? 'Checking the saved Assisted manual setup…' : manualStepStatus === 'blocked' ? manualStepReason : skippedAssistedStages.includes(requestedStepKey as 'character_images'|'world_images'|'frame_images') ? 'This optional stage is explicitly skipped for the accepted screenplay.' : requestedStepKey === 'frame_images' ? selectedFrameSkipped ? 'This clip’s frame preparation is skipped. No image asset was created.' : `Assisted manual · frame images are unchecked. Choose a planned clip and first or last frame, review the prompt, then generate and select a candidate. You may skip this clip without creating an asset.` : `Assisted manual · ${requestedRole === 'world_master' ? 'world image' : 'character image'} generation is unchecked. Choose a ${requestedRole === 'world_master' ? 'location' : 'character'}, review the prompt, generate candidates, then select one to save it to this screenplay.`}{manualStepReason.endsWith('is automated from the saved setup.')&&<><p>Automatic candidate generation and Director review require a verified workflow and a running image worker.</p><button className="quiet-button" onClick={()=>void retryAutomatedStage()} disabled={automatedStageBusy}>{automatedStageBusy?'Checking…':'Check stage status'}</button>{!automatedStage?.run_id&&<button type="button" className="quiet-button" onClick={()=>void useManualStage()} disabled={busy||automatedStageBusy}>Use manual generation for this stage</button>}</>}{storySetupMode === 'assisted_manual' && storySetup?.automate_steps[requestedStepKey as 'character_images'|'world_images'|'frame_images'] === false && <p><button type="button" className="quiet-button" onClick={()=>void toggleAssistedStageSkip()} disabled={manualStepStatus !== 'ready' || stageSkipBusy || !!pending}>{stageSkipBusy ? 'Saving…' : skippedAssistedStages.includes(requestedStepKey as 'character_images'|'world_images'|'frame_images') ? 'Undo skip for this stage' : 'Skip this optional stage'}</button></p>}</section>}
    {acceptedScreenplayId && loadedStoryContextKey === currentStoryContextKey && storySetupMode === 'assisted_manual' && <ImageStageNext workspaceId={workspaceId} revisionId={acceptedScreenplayId} step={requestedStepKey || 'character_images'} records={targetRecords} frames={frameTargets} setup={storySetup} refresh={refresh} videoWorkflowId={videoWorkflowId} skippedStages={skippedAssistedStages} videoReady={!openingVideoShot && (storySetup?.automate_steps.video === true || (!!selectedFrameTarget && !!videoWorkflowId))} onVideoNext={()=>{if(storySetup?.automate_steps.video === false)void openStoryVideoShot();else window.location.hash=`#/video?workspace_id=${encodeURIComponent(workspaceId)}`;}} /> }
    {storySetupMode === 'assisted_manual' && storySetup?.automate_steps.video === false && (requestedStepKey === 'frame_images' || (skippedAssistedStages.includes('frame_images') && (requestedStepKey === 'world_images' || skippedAssistedStages.includes('world_images')))) && <section className="card assisted-video-shot-entry" aria-label="Open a screenplay shot in Video Create"><div><b>Open a shot in Video Create</b><p>Choose a shot and workflow. Its prompt will be prepared and saved for review; no video job will start.</p></div><label>Planned shot<select aria-label="Video planned shot" value={frameTargetKey} onChange={event=>setFrameTargetKey(event.target.value)}>{frameTargets.map(target=><option key={target.clip_id} value={`${target.scene_number}.${target.shot_number}`}>Scene {target.scene_number} · Shot {target.shot_number} · {target.summary}</option>)}</select></label><label>Video workflow<select aria-label="Video workflow for selected shot" value={videoWorkflowId} onChange={event=>setVideoWorkflowId(event.target.value)}><option value="">Choose a workflow</option><option value={WORKFLOW_ID}>Text to video</option><option value={FL2VA_WORKFLOW_ID}>First and last frame</option><option value={R2V_WORKFLOW_ID}>Reference to video</option></select></label>{openingVideoShot && <p role="status">Preparing this shot…</p>}{videoShotError && <p role="alert">{videoShotError}</p>}</section>}
    {automatedStageError&&<div className="notice" role="alert">Automated stage: {automatedStageError}</div>}
    {automatedStage&&<section className="card"><div className="section-title"><div><h2>Automated targets</h2><p>{automatedCandidates.length ? requestedStepKey==='frame_images'?'Director review selects at most one first frame and one last frame per clip.':'Director review selects no more than one master per character or location.' : automatedStage.message||'No image target requires generation.'}</p></div><button className="quiet-button" onClick={()=>void retryAutomatedStage()} disabled={automatedStageBusy}><RefreshCw size={14}/> Check stage status</button></div>{automatedCandidates.length>0&&<div className="image-candidate-grid">{automatedCandidates.map(candidate=>{const asset=candidate.output_asset_id?assetById.get(candidate.output_asset_id):undefined;const lineage=candidate.settings?.lineage||asset?.metadata?.production_image_job?.settings?.lineage;const review=candidate.director_review;const reviewReason=review?.error?.message||review?.decision?.reason;const candidateRole=(candidate.asset_role||role) as Role;return <article className="card image-candidate" key={candidate.job_id}><div className="image-candidate-preview">{asset?<button type="button" className="image-candidate-image-open" aria-label={`View full-size ${lineage?.target_name||'screenplay target'} image candidate ${candidate.candidate_index}`} onClick={()=>setImagePreview(asset)}><img src={asset.content_url} alt={`Reference image for ${lineage?.target_name||'screenplay target'}`}/></button>:candidate.status==='running'?<LoaderCircle className="spin" role="img" aria-label="Generating image"/>:candidate.status==='queued'?<Clock3 role="img" aria-label="Waiting to generate"/>:candidate.status==='recovery_required'?<AlertTriangle role="img" aria-label="Generation needs attention"/>:<ImageIcon/>}</div><div className="image-candidate-details"><b>{lineage?.target_name||'Screenplay target'} · candidate {candidate.candidate_index}</b><span>{candidate.status.replaceAll('_',' ')}{review?.resolution_status?` · Director ${review.resolution_status.replaceAll('_',' ')}`:''}</span>{reviewReason&&<small>{reviewReason}</small>}{candidate.error?.message&&<small>{candidate.error.message}</small>}{review?.resolution_status==='blocked'&&<small>This candidate was kept in the library but not selected. Check readiness or use the manual image step to continue.</small>}{asset&&<small>{asset.roles.includes(candidateRole)?`Selected as ${stageLabel[candidateRole]}`:'Saved to workspace library'}</small>}</div></article>;})}</div>}</section>}
    {!requestedStoryStep && !legacyRoute && <div className="studio-subtabs" aria-label="Image production pages"><button type="button" className={section === 'characters' ? 'generate-button' : 'quiet-button'} aria-current={section === 'characters' ? 'page' : undefined} onClick={() => onSection('characters')}><ImageIcon size={15}/> Characters & voices</button><button type="button" className={section === 'worlds' ? 'generate-button' : 'quiet-button'} aria-current={section === 'worlds' ? 'page' : undefined} onClick={() => onSection('worlds')}><ImageIcon size={15}/> Scene Backgrounds</button><button type="button" className={section === 'frames' ? 'generate-button' : 'quiet-button'} aria-current={section === 'frames' ? 'page' : undefined} onClick={() => onSection('frames')}><ImageIcon size={15}/> First & last frames</button></div>}
    {message&&<div className="notice" role="status">{message}</div>}
    {pending&&<div className="notice" role="status">A request may already have reached the queue. Retry sends its saved prompt and settings unchanged. <button className="quiet-button" onClick={()=>{localStorage.removeItem(PENDING_KEY);setPending(null);setRefresh(value=>value+1);setMessage('Saved retry discarded.');}}>Discard saved retry</button></div>}
    {!requestedStoryStep && section === 'worlds' && <SceneBackgroundVariant assets={assets} disabled={busy || !!pending || promptLoading} onPrepare={(base, variantPrompt) => {
      setWorkflowId('qwen_image_edit_2511'); setSourceReferenceIds([base.asset_id]);
      setTargetRecordId(''); setPrompt(variantPrompt); setPromptKnowledge(null); setPreview(null);
      setMessage('Scene variation prepared from the base image. Review the reference, prompt and settings before Generate.');
      generationForm.current?.scrollIntoView({behavior: 'auto', block: 'start'});
    }}/>}
    <div className="image-creation-workspace">
      <DirectorImageReview request={draftRequest()} disabled={busy||promptLoading||!!pending} onApply={draft=>{setPrompt(draft.prompt);setPromptKnowledge(draft);setPromptNeedsPreparation(false);setPreview(null);setMessage('Director prompt applied. Review it before generating.');}}/>
      <div ref={generationForm} className="card image-form">
        <div className="section-title"><div><h2>{workflowId==='qwen_image_multi_angle_2511'?'Generate directional views':'Generate an image'}</h2><p>{workflowId==='qwen_image_multi_angle_2511'?'One separately labelled image is made for each chosen direction from the selected master image.':'Choose 1, 4 or 8 candidates. Each runs one at a time from consecutive seeds.'}</p></div><span className="mode-pill"><Sparkles size={13}/> Assisted manual</span></div>
        <div className="image-fields">
          <MediaSourcePicker workspaceId={workspaceId} kinds={['image']} compact disabled={busy||!!pending}
            onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}
            destination={workflowId==='qwen_image_edit_2511'&&!frameReferenceFlow?{kind:'model_reference',slot:'image references',capacity:Math.max(0,3-selectedReferences.length),onSelect:items=>{
              if(items.some(asset=>asset.workspace_id!==workspaceId||asset.kind!=='image'))throw new Error('Choose registered image references for this project.');
              const ids=[...new Set([...sourceReferenceIds,...items.map(asset=>asset.asset_id)])];
              if(ids.length>3)throw new Error('Qwen Image Edit accepts up to three references.');
              updateReferences(ids);setPromptKnowledge(null);
            }}:undefined}/>
          <p className="project-context-label">Current project · change with New project or Load project above</p>
          {requestedStepKey === 'frame_images' && <label>Planned clip<select aria-label="Planned clip" value={frameTargetKey} onChange={event=>setFrameTargetKey(event.target.value)}><option value="">Choose a screenplay shot</option>{frameTargets.map(target=><option key={target.clip_id} value={`${target.scene_number}.${target.shot_number}`}>Scene {target.scene_number} · Shot {target.shot_number} · Clip {target.clip_id.slice(-8)}</option>)}</select>{selectedFrameTarget&&<small>{selectedFrameTarget.scene_title} · {selectedFrameTarget.summary}</small>}</label>}
          {['character_master','world_master'].includes(role)&&<label>{role==='character_master'?'Character target':'Location target'}<select aria-label={role==='character_master'?'Character target':'Location target'} value={targetRecordId} onChange={event=>{const id=event.target.value;setTargetRecordId(id);if(workflowId==='qwen_image_multi_angle_2511')setSourceReferenceIds([masterSelections[selectionKey(acceptedScreenplayId,targetType,id)]].filter(Boolean));const record=compatibleRecords.find(item=>item.record_id===id);if(!requestedStoryStep&&record&&!prompt.trim())setPrompt(`${role==='character_master'?'Character reference portrait':'Base location reference image'}: ${record.name}. ${record.detail}`.trim());}}><option value="">{requestedStoryStep ? `Choose a ${targetType}` : 'Standalone image · no screenplay link'}</option>{compatibleRecords.map(record=><option key={record.record_id} value={record.record_id}>{record.name}</option>)}</select><small>{compatibleRecords.length?lineageStatus:`${lineageStatus} No canonical ${targetType} target is available; standalone generation still works.`}</small>{selectedTarget?.detail&&<small>Story description: {selectedTarget.detail}</small>}<small>{role==='character_master'?'Character assets: one character on a plain white background.':'Scene backgrounds: environment only, without characters.'}</small></label>}
          {requestedStepKey === 'frame_images' || (!requestedStoryStep && section === 'frames') ? <label>Frame role<select value={role} onChange={event=>{setRole(event.target.value as Role);setTargetRecordId('');setPreview(null);}}>{(['first_frame','last_frame'] as Role[]).map(value=><option key={value} value={value}>{stageLabel[value]}</option>)}</select></label> : legacyRoute ? <label>Asset role<select value={role} onChange={event=>{setRole(event.target.value as Role);setTargetRecordId('');setPreview(null);}}>{Object.entries(stageLabel).filter(([value])=>!['character_view','world_view'].includes(value)).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label> : <input type="hidden" value={role} readOnly aria-label="Asset role" />}
          <label>Image workflow<select value={workflowId} onChange={event=>{setWorkflowId(event.target.value);setPromptKnowledge(null);setPreview(null);}}>{visibleWorkflows.map(item=><option key={item.workflow_id} value={item.workflow_id}>{item.label}{item.available?'':' · unavailable'}</option>)}</select></label>
          {workflowId!=='qwen_image_multi_angle_2511'&&<label>Number of candidates<select aria-label="Number of candidates" value={candidateCount} disabled={!!pending||busy} onChange={event=>{setCandidateCount(Number(event.target.value) as 1|4|8);setPreview(null);}}>{[1,4,8].map(count=><option key={count} value={count}>{count} {count===1?'image':'images'}</option>)}</select></label>}
          <label>Starting seed<input type="number" min="0" max={4294967296-(workflowId==='qwen_image_multi_angle_2511'?worldViewCount:candidateCount)} value={seed} onChange={event=>setSeed(Number(event.target.value))}/></label>
        </div>
        {['character_master','world_master','character_view','world_view'].includes(role)&&<ZImageLoraControls enabled={workflowId==='z_image_turbo'} onChange={setZimageLora} onTrigger={text=>setPrompt((current:string)=>[text,current].filter(Boolean).join(', '))}/>}
        {workflowId==='qwen_image_multi_angle_2511'&&<label>Directional views<select value={worldViewCount} onChange={event=>setWorldViewCount(Number(event.target.value) as 2|3|4|8)}><option value={2}>2 views · left, right</option><option value={3}>3 views · left, right, back</option><option value={4}>4 views · front, right, back, left</option><option value={8}>8 views · include diagonal angles</option></select><small>Choose the saved base image below. This creates one separately labeled image per direction.</small></label>}
        {requestedStepKey==='frame_images' && selectedFrameTarget && <section className="card" aria-label="Shot description for frame references">
          <h3>Scene {selectedFrameTarget.scene_number} · Shot {selectedFrameTarget.shot_number} — {role==='last_frame'?'Last frame':'First frame'}</h3>
          <p>{selectedFrameTarget.scene_title}</p>
          <p><b>Action: </b>{selectedFrameTarget.summary}</p>
          {selectedFrameTarget.dialogue&&<p><b>Dialogue: </b>{selectedFrameTarget.dialogue}</p>}
          {selectedFrameTarget.camera&&<p><b>Camera: </b>{selectedFrameTarget.camera}</p>}
          {selectedFrameTarget.lighting&&<p><b>Lighting: </b>{selectedFrameTarget.lighting}</p>}
          {selectedFrameTarget.mood&&<p><b>Mood: </b>{selectedFrameTarget.mood}</p>}
          <p>Choose the characters and location needed for this shot. {role==='last_frame'?'Use its selected first frame to keep the ending consistent.':'The first frame shows the opening of this shot.'}</p>
        </section>}
        {referencesRequired&&<fieldset className="image-reference-picker"><legend>Reference image · {workflowId==='qwen_image_multi_angle_2511'?'choose one master image':'choose 1–3 images'}</legend><p>{workflowId==='qwen_image_multi_angle_2511'?'Select the current master. Each output uses it as the shared identity or location reference.':frameReferenceFlow?'Only selected character/world masters and saved side views are shown. For a last frame, the selected first frame of this clip is also available. Choose up to three references; Director prepares the opening or ending prompt automatically.':'Choose saved workspace images or open Reference folder images below. The selected IDs and file hashes are frozen with the request.'}</p>{maxReferences===1?<button type="button" className="quiet-button" disabled={!!pending||!sourceReferenceIds.length} onClick={()=>updateReferences([])}>Clear reference</button>:<SelectionToggle selected={sourceReferenceIds} shown={referenceAssets.map(asset=>asset.asset_id)} capacity={maxReferences} disabled={!!pending} onChange={ids=>updateReferences(ids)}/>}<div className="image-reference-grid">{referenceAssets.map(asset=><label key={asset.asset_id} className={sourceReferenceIds.includes(asset.asset_id)?'selected':''}><input type="checkbox" checked={sourceReferenceIds.includes(asset.asset_id)} disabled={!!pending||(!sourceReferenceIds.includes(asset.asset_id)&&selectedReferences.length>=maxReferences)} onChange={event=>{updateReferences(event.target.checked?(workflowId==='qwen_image_multi_angle_2511'?[asset.asset_id]:[...sourceReferenceIds.filter(id=>!frameReferenceFlow||allowedReferenceIds.has(id)),asset.asset_id]):sourceReferenceIds.filter(id=>id!==asset.asset_id));}}/><img src={asset.content_url} alt=""/><span>{asset.asset_id===openingFrameId?'Selected first frame':asset.metadata?.production_image_job?.settings?.lineage?.target_name||asset.filename}</span>{asset.recommended&&<small>Style reference</small>}</label>)}{!referenceAssets.length&&<small>{workflowId==='qwen_image_multi_angle_2511'?'Generate and select a master image first.':frameReferenceFlow?'Select character and world images in their asset pages first.':'No workspace images yet.'}</small>}</div></fieldset>}
        {workspaceId.trim() ? <div className="image-prompt-label"><SelectionMicroEdit label="Image prompt" value={prompt} surface="prompt" workspaceId={workspaceId.trim()} revisionId={acceptedScreenplayId || `image-draft-${role}-${targetRecordId || 'standalone'}`} fieldKey={`${requestedStepKey || 'isolated'}.${role}.${requestedStepKey === 'frame_images' ? frameTargetKey || 'unselected' : targetRecordId || 'unselected'}`} disabled={busy || promptLoading || (requestedStoryStep && !promptContextReady) || !!pending} onChange={value=>{setPrompt(value);setPreview(null);}}/><small aria-live="polite" className={promptLength > IMAGE_PROMPT_MAX_CODEPOINTS ? 'prompt-over-limit' : undefined}>{promptLength.toLocaleString()} / 6,999 characters{promptLength > IMAGE_PROMPT_MAX_CODEPOINTS ? ' · shorten this prompt to continue' : ''}</small></div> : <label className="image-prompt-label">Prompt<textarea value={prompt} onChange={event=>{setPrompt(event.target.value);setPreview(null);}} rows={7} placeholder="Describe the character, location, or frame. Include visual details and continuity cues."/><small aria-live="polite" className={promptLength > IMAGE_PROMPT_MAX_CODEPOINTS ? 'prompt-over-limit' : undefined}>{promptLength.toLocaleString()} / 6,999 characters{promptLength > IMAGE_PROMPT_MAX_CODEPOINTS ? ' · shorten this prompt to continue' : ''}</small></label>}
        {workflow&&!workflow.available&&<div className="image-warning"><AlertTriangle size={16}/><span>{workflow.disabled_reason||'This workflow is not verified for generation.'}</span></div>}
        <div className="image-readiness"><span className={runtime?.safe_to_submit?'ready':''}><i/>{runtime?.safe_to_submit?'GPU temperature/clock safe':'GPU temperature/clock not cleared'}</span><span className={gpuAdmission?.available?'ready':''}><i/>{gpuAdmission?.available?`GPU ready · ${gpuAdmission.free_gib?.toFixed(1)??'free-memory reading unavailable'}${typeof gpuAdmission.free_gib==='number'?' GiB reported free (informational)':' (diagnostic only)'}`:`GPU runtime blocked · ${gpuAdmission?.reason || 'checking or backend needs restart'}`}</span><span className={workerReady?'ready':''}><i/>{workerReady?'Image worker ready':'Image worker off'}</span></div>
        {gpuAdmission?.host_memory&&<small className="image-readiness-memory-note">Host memory context (informational only): {gpuAdmission.host_memory.available_gib} GiB available of {gpuAdmission.host_memory.total_gib} GiB RAM; {gpuAdmission.host_memory.swap_free_gib} GiB swap free. This does not change GPU admission.</small>}
        {promptKnowledge&&promptKnowledge.workflow_id===workflowId&&<details className="image-knowledge-note"><summary>Prompt sources · guidance v{promptKnowledge.knowledge_ref.guidance_version}</summary><ul>{promptKnowledge.sources.map((source,index)=><li key={`${source.uri}-${index}`}>{source.uri} · {source.section}</li>)}</ul></details>}
        {linkedStoryStage && !manualStepReady && !pending && <div className="notice" role="status"><p>{manualStepReason || (manualStepStatus === 'loading' ? 'Checking the saved stage setup…' : 'Choose a screenplay target before generating.')}</p>{stageIsAutomatic && !automatedStage?.run_id && <button type="button" className="quiet-button" onClick={()=>void useManualStage()} disabled={busy||automatedStageBusy}>Switch this stage to manual generation</button>}{stageIsAutomatic && automatedStage?.run_id && <p>An automatic run exists for this stage. Review its status above before starting manual generation.</p>}</div>}
        <div className="image-actions"><button className="quiet-button" onClick={()=>void preparePrompt()} disabled={busy||promptLoading||!promptContextReady||!workspaceId.trim()||(!requestedStoryStep&&!promptContextKey&&!prompt.trim())||promptLength>IMAGE_PROMPT_MAX_CODEPOINTS||!!pending||(referencesRequired&&(sourceReferences.length<1||sourceReferences.length>maxReferences))}><Sparkles size={15}/> Prepare prompt</button><button className="quiet-button" title="Validate prompt, settings and seeds without generating images or submitting a GPU job" onClick={()=>void checkPrompt()} disabled={busy||promptLoading||!manualStepReady||!prompt.trim()||promptLength>IMAGE_PROMPT_MAX_CODEPOINTS||!!pending||(referencesRequired&&(sourceReferences.length<1||sourceReferences.length>maxReferences))}><ImageIcon size={15}/> Check generation request</button><button className="generate-button" onClick={()=>void generate()} disabled={!canGenerate||busy||promptLoading||(!pending&&referencesRequired&&(sourceReferences.length<1||sourceReferences.length>maxReferences))}>{busy?<LoaderCircle size={15} className="spin"/>:<Sparkles size={15}/>} {pending?'Resume saved request':workflowId==='qwen_image_multi_angle_2511'?`Generate ${worldViewCount} views`:candidateCount===4?'Generate four':`Generate ${candidateCount} ${candidateCount===1?'image':'images'}`}</button>{requestedStepKey==='frame_images'&&<button type="button" className="quiet-button" disabled={busy||!!pending||frameSkipBusy||!frameSkipsReady||!selectedFrameTarget||manualStepStatus!=='ready'} onClick={()=>{if(!selectedFrameTarget)return;const requestWorkspace=workspaceId.trim();const requestScreenplay=acceptedScreenplayId;const requestTarget={...selectedFrameTarget};const requestContextKey=`${requestWorkspace}\0${requestScreenplay}`;const requestSkipped=!selectedFrameSkipped;setFrameSkipBusyContext(requestContextKey);void setFramePreparationSkip(requestWorkspace,requestScreenplay,requestTarget.scene_number,requestTarget.shot_number,requestSkipped).then(result=>{if(frameSkipContextRef.current!==requestContextKey)return;setSkippedFrameClipKeys(result.skipped.map(item=>`${item.scene_number}.${item.shot_number}`));setPreview(null);setMessage(requestSkipped?'Frame preparation skipped for this clip. No asset was created.':'Frame preparation restored for this clip. No asset was created.');}).catch(error=>{if(frameSkipContextRef.current===requestContextKey)setMessage(`Could not save frame skip: ${(error as Error).message}`);}).finally(()=>setFrameSkipBusyContext(current=>current===requestContextKey?'':current));}}>{frameSkipBusy?'Saving…':selectedFrameSkipped?'Undo skip for this clip':'Skip this clip’s frames'}</button>}</div>
      </div>
      {imageSettings}
    </div>
    {preview&&<section className="card image-preview-panel"><div><h2>Compiled preview</h2><span>{preview.initial_candidate_count} candidates · no generation submitted</span></div><pre>{JSON.stringify({workflow_id:preview.workflow_id,workflow_version:preview.workflow_version,settings:preview.settings,prompt:preview.prompt,candidates:preview.candidates?.map((item:any)=>({seed:item.seed,...(item.world_view?{view:item.world_view,direction_instruction:item.direction_instruction}:{}),graph_nodes:Object.keys(item.graph||{}).length}))},null,2)}</pre></section>}
    {batch&&<section className="image-candidate-section"><div className="section-title"><div><h2>Candidate batch</h2><p>{settled?'All jobs settled.':batch.jobs[0]?.settings?.multi_angle_batch===true?'One multi-angle workflow is running. All views appear when it finishes.':'Candidates run one at a time. Updates every three seconds.'} Batch {batch.batch_id}</p></div><button className="quiet-button" onClick={()=>setRefresh(value=>value+1)}><RefreshCw size={14}/> Refresh</button></div><div className="image-candidate-grid">{batch.jobs.map(candidate=>{const asset=candidate.output_asset_id?assetById.get(candidate.output_asset_id):undefined;const lineage=candidate.settings?.lineage||asset?.metadata?.production_image_job?.settings?.lineage;const candidateRole:Role=(candidate.asset_role||asset?.metadata?.production_image_job?.intended_role||role) as Role;const view=asset?.metadata?.production_image_job?.world_view||candidate.settings?.world_views?.[candidate.candidate_index-1];const selected=!!asset && (['first_frame','last_frame'].includes(candidateRole)&&lineage?.screenplay_revision_id&&lineage.clip_id?masterSelections[selectionKey(lineage.screenplay_revision_id,candidateRole,lineage.clip_id)]===asset.asset_id:['world_view','character_view'].includes(candidateRole)?asset?.roles.includes(candidateRole)===true:lineage?.target_record_id&&lineage?.screenplay_revision_id?masterSelections[selectionKey(lineage.screenplay_revision_id,lineage.target_type!,lineage.target_record_id)]===asset?.asset_id:asset?.roles.includes(candidateRole)===true);const target=lineage?.target_name;const candidateLabel=view?.label?`${view.label} view`:`${stageLabel[candidateRole]} candidate ${candidate.candidate_index}`;return <article className="card image-candidate" key={candidate.job_id}><div className="image-candidate-preview">{asset?<button type="button" className="image-candidate-image-open" aria-label={`View full-size ${candidateLabel}`} onClick={()=>setImagePreview(asset)}><img src={asset.content_url} alt={candidateLabel}/></button>:candidate.status==='running'?<LoaderCircle className="spin" role="img" aria-label="Generating image"/>:candidate.status==='queued'?<Clock3 role="img" aria-label="Waiting to generate"/>:candidate.status==='recovery_required'?<AlertTriangle role="img" aria-label="Generation needs attention"/>:<ImageIcon/>}</div><div className="image-candidate-details"><b>{candidateLabel}</b><span>{candidate.status.replaceAll('_',' ')}</span>{view&&candidate.status==='completed'&&<small>Requested direction · check the facing before selecting.</small>}{target&&<small>For {lineage?.target_type==='location'?'location':'character'}: {target}</small>}{candidate.error?.message&&<small>{candidate.error.message}</small>}{asset&&<small>{selected?`Selected as ${stageLabel[candidateRole]}`:'Saved in workspace library · not selected'}</small>}</div>{candidate.status==='completed'&&<button className={selected?'quiet-button':'generate-button'} onClick={()=>void selectCandidate(candidate.job_id,candidateRole)} disabled={selectingId!==''}>{selectingId===candidate.job_id?<LoaderCircle size={14} className="spin"/>:selected?<Check size={14}/>:null}{selected?'Selected':`Use as ${stageLabel[candidateRole]}`}</button>}</article>;})}</div></section>}
    {requestedStepKey === 'world_images' && acceptedScreenplayId && <section className="image-candidate-section" aria-label="Selected world images">
      <div className="section-title"><div><h2>Selected world images</h2><p>Your saved master image for each location. Choose another candidate to replace it.</p></div></div>
      <div className="image-candidate-grid">{targetRecords.filter(record=>record.type.toLowerCase()==='location').map(record=>{
        const asset=assetById.get(masterSelections[selectionKey(acceptedScreenplayId,'location',record.record_id)]);
        return <article className="card image-candidate" key={record.record_id}>
          <div className="image-candidate-preview">{asset?<button type="button" className="image-candidate-image-open" aria-label={`View selected world image for ${record.name}`} onClick={()=>setImagePreview(asset)}><img src={asset.content_url} alt={`Selected world image for ${record.name}`}/></button>:<ImageIcon aria-label="No image selected"/>}</div>
          <div className="image-candidate-details"><b>{record.name}</b><span>{asset?'Selected master image':'No image selected yet'}</span>{record.detail&&<small>{record.detail}</small>}</div>
        </article>;
      })}</div>
    </section>}
    {requestedStepKey==='frame_images' && acceptedScreenplayId && frameTargets.length>0 && <section className="image-candidate-section" aria-label="Selected first and last frames">
      <div className="section-title"><div><h2>Selected first & last frames</h2><p>Your saved frame pair for each shot. Choose another candidate to replace a frame.</p></div></div>
      {frameTargets.map(target=><section key={target.clip_id} aria-label={`Saved frames for Scene ${target.scene_number} Shot ${target.shot_number}`}>
        <h3>Scene {target.scene_number} · Shot {target.shot_number}</h3>
        <p>{target.scene_title} · {target.summary}</p>
        <div className="image-candidate-grid">{(['first_frame','last_frame'] as const).map(frameRole=>{
          const asset=assetById.get(masterSelections[selectionKey(acceptedScreenplayId,frameRole,target.clip_id)]);
          const label=`${stageLabel[frameRole]} · Scene ${target.scene_number} · Shot ${target.shot_number}`;
          return <article className="card image-candidate" key={frameRole}>
            <div className="image-candidate-preview">{asset?<button type="button" className="image-candidate-image-open" aria-label={`View selected ${label}`} onClick={()=>setImagePreview(asset)}><img src={asset.content_url} alt={label}/></button>:<ImageIcon aria-label="No frame selected"/>}</div>
            <div className="image-candidate-details"><b>{stageLabel[frameRole]}</b><span>{asset?'Selected frame':'No frame selected yet'}</span></div>
          </article>;
        })}</div>
      </section>)}
    </section>}
    {selectedMasterId && ['character_master','world_master'].includes(role) && <section className="card" aria-label="Optional side views"><h2>Optional side views</h2><p>One master is selected for {selectedTarget?.name || 'this target'}. You can change it using another candidate. Add 2, 3, 4 or 8 Qwen 2511 views if you need other angles, or continue without them.</p><button type="button" className="quiet-button" disabled={busy||promptLoading||!!pending} onClick={()=>{setSourceReferenceIds([selectedMasterId]);setPreview(null);if(workflowId==='qwen_image_multi_angle_2511'){void preparePrompt();}else{setMessage('Opening side-view settings. Director is preparing the prompt…');setWorkflowId('qwen_image_multi_angle_2511');}generationForm.current?.scrollIntoView({block:'start',behavior:'smooth'});}}>{(promptLoading||busy)&&workflowId==='qwen_image_multi_angle_2511'?<><LoaderCircle size={14} className="spin"/> Preparing side views…</>:'Prepare side views from selected master'}</button>{workflowId==='qwen_image_multi_angle_2511'&&<p role={promptLoading||busy?'status':'note'}>{promptLoading||busy?'Director is preparing the side-view prompt…':message||'Side-view settings are open above. Review the prompt, choose 2, 3, 4 or 8 views, then Generate.'}{!promptLoading&&workflow?.available===false&&` Workflow unavailable: ${workflow.disabled_reason||'Check Status for missing requirements.'}`}</p>}{workflowId==='qwen_image_multi_angle_2511'&&<button type="button" className="quiet-button" disabled={busy||!!pending} onClick={()=>{setWorkflowId('z_image_turbo');setSourceReferenceIds([]);setPreview(null);}}>Return to master image generation</button>}</section>}
    {(requestedStepKey === 'character_images' || (!requestedStoryStep && section === 'characters')) && workspaceId && <CharacterVoicesPage key={workspaceId} contextWorkspaceId={workspaceId} embedded />}
    {imagePreview&&<div className="image-viewer-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)setImagePreview(null);}}><section className="image-viewer-dialog" role="dialog" aria-modal="true" aria-labelledby="image-viewer-title"><button ref={imagePreviewCloseButton} type="button" className="quiet-button image-viewer-close" onClick={()=>setImagePreview(null)} aria-label="Close image preview">Close</button><h2 id="image-viewer-title">{imagePreview.filename}</h2><img src={imagePreview.content_url} alt={imagePreview.filename}/>{previewCandidates.length>1&&<nav className="image-viewer-navigation" aria-label="Candidate preview navigation"><button type="button" className="quiet-button" aria-label="Previous candidate image" onClick={()=>movePreview(-1)}><ChevronLeft size={20}/> Previous</button><span aria-live="polite">{previewIndex+1} / {previewCandidates.length}</span><button type="button" className="quiet-button" aria-label="Next candidate image" onClick={()=>movePreview(1)}>Next <ChevronRight size={20}/></button></nav>}<p>Full-size candidate preview · {imagePreview.roles.map(item=>stageLabel[item as Role]||item).join(', ')||'Not yet selected'}</p></section></div>}
  </div>;
}

export default function ImageAssetsPage({ initialSection = 'characters', legacyRoute = false }: { initialSection?: 'characters'|'worlds'|'frames'; legacyRoute?: boolean }) {
  const [locationHash, setLocationHash] = useState(() => window.location.hash);
  useEffect(() => {
    const updateLocationHash = () => setLocationHash(window.location.hash);
    window.addEventListener('hashchange', updateLocationHash);
    return () => window.removeEventListener('hashchange', updateLocationHash);
  }, []);
  const routeQuery = new URLSearchParams(locationHash.split('?')[1] || '');
  const requestedStepKey = routeQuery.get('step');
  const requestedStoryStep = requestedStepKey === 'character_images' || requestedStepKey === 'world_images' || requestedStepKey === 'frame_images';
  const [section, setSection] = useState<'characters'|'worlds'|'frames'>(() => requestedStepKey === 'world_images' ? 'worlds' : requestedStepKey === 'frame_images' ? 'frames' : initialSection);
  useEffect(() => {
    if (requestedStepKey === 'world_images') setSection('worlds');
    else if (requestedStepKey === 'frame_images') setSection('frames');
    else if (requestedStoryStep) setSection('characters');
    else setSection(initialSection);
  }, [initialSection, requestedStepKey, requestedStoryStep]);
  return <ImageAssetsContent key={`${locationHash}:${section}`} section={section} onSection={setSection} legacyRoute={legacyRoute}/>;
}
