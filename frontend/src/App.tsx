import {managedProjectId} from './lib/media-workspace';
import {useProject} from './ProjectController';
import OutputDestination from './OutputDestination';
import SelectionToggle from './SelectionToggle';
import MediaSourcePicker from './MediaSourcePicker';
import CreateWorkspace from './CreateWorkspace';
import TakeWorkspace, {DockedVideo, TakeReviewSection} from './TakeWorkspace';
import T2VBatchPanel from './T2VBatchPanel';
import RunClipLiveView from './RunClipLiveView';
import { T2V_QUALITIES, ALL_VIDEO_QUALITIES, VIDEO_ASPECT_RATIOS, VideoAspectRatio, VideoResolution, qualityDimensions } from './lib/video-quality';
import { ClipboardEvent, DragEvent, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowRight, AudioLines, BookOpen, Check, ChevronDown, Film, FolderOpen, Gauge, Image, LoaderCircle, Play, RefreshCw, Sparkles, X } from 'lucide-react';
import { acceptJob, ApiError, Capability, createJob, releaseVideoAttempt, findJobByIdempotency, getCapability, getJob, Job, listAllJobs, prepareRetake, validateRequest, VideoRequest, StoryVideoLineage, WORKFLOW_ID, WORKFLOW_SHA256, FL2VA_WORKFLOW_ID, FL2VA_WORKFLOW_SHA256, R2V_WORKFLOW_ID, R2V_WORKFLOW_SHA256 } from './lib/video-api';
import { browseMediaCatalogue, reuseCatalogueAsset, CataloguePage, listMediaAssets, listMediaSeoStyles, MediaAsset, MediaSeoStyle, rankMediaAssets, searchMediaSemantically, uploadMediaAsset } from './lib/media-api';
import { defaultMediaWorkspaceId, mediaWorkspaceOptions, standaloneMediaWorkspaceId } from './lib/media-workspace';
import { getImageSelection } from './lib/image-api';
import { AutomatedFirstClipState, controlAutomatedRun, ProductionSetup, getAssistedVideoClipPlan, getAutomatedFirstClip, getProductionSetup, getStoryPromptDrafts, getStoryScreenplay, getStoryScreenplayRevision, getStoryWorkspace, listStoryWorkspaces, StoryWorkspace, listStoryScreenplays, prepareStoryPrompt, resumeAutomatedRun, retryAutomatedRunShot, saveStoryPromptShot, startAutomatedFirstClip } from './lib/story-api';
import StatusPage from './StatusPage';
import StoryPage from './StoryPage';
import ScreenplayPage from './ScreenplayPage';
import StoryboardPage from './StoryboardPage';
import './screenplay.css';
import ProductionStylesPage from './ProductionStylesPage';
import ProductionSetupPage from './ProductionSetupPage';
import PromptPreparationPage from './PromptPreparationPage';
import ShotReferenceDirector from './ShotReferenceDirector';
import ReferenceReview from './ReferenceReview';
import AssistedClipPlanPanel from './AssistedClipPlanPanel';
import AssemblyPreviewPanel from './AssemblyPreviewPanel';
import MediaLibraryPage from './MediaLibraryPage';
import MediaPrepPage from './MediaPrepPage';
import VibeEditorPage from './VibeEditorPage';
import './media-library.css';
import ImageAssetsPage from './ImageAssetsPage';
import TrellisPage from './TrellisPage';
import TextToImagePage from './TextToImagePage';
import './text-to-image.css';
import SelectionMicroEdit from './SelectionMicroEdit';
import './image-assets.css';
import StudioShell, { StudioRoute } from './StudioShell';
import './video-references.css';

export type R2VReferenceDraft = { speakerIds?: string[]; assetId: string; role: string; intent: string; startSec?: number; endSec?: number; includePairedSoundtrack?: boolean; audioIntent?: string };
type SourceLineage = Pick<StoryVideoLineage, 'screenplay_revision_id'|'setup_hash'|'scene_number'|'shot_number'|'source_prompt_sha256'|'knowledge_ref'|'style_ref'|'planned_clip_id'|'board_revision'>;
type StoryHandoff = SourceLineage & { workspace_id: string; clip_id: string; workflow_id: string; prompt: string; duration?:number; first_frame_id?:string;last_frame_id?:string;r2v_images?:R2VReferenceDraft[] };
export type Draft = { directorPrepared?: boolean; directorWarnings?: string[]; referenceReviews?: Record<string, string>; prompt: string; r2vMainPrompt?: string; r2vCollatedPrompt?: string; r2vImages?: R2VReferenceDraft[]; r2vVideos?: R2VReferenceDraft[]; r2vAudios?: R2VReferenceDraft[]; duration: number; aspectRatio?: VideoAspectRatio; resolution: VideoResolution; workspaceId: string; clipId: string; workflowId: string; sourceLineage?: SourceLineage; firstFrameAssetId?: string; lastFrameAssetId?: string; pendingKey?: string; pendingRequest?: VideoRequest; retakeOf?: string; keepOriginal?: boolean };
const DRAFT_KEY = 'vibe-video-draft-v1';
const shotDraftKey = (draft: Draft) => draft.sourceLineage ? `${DRAFT_KEY}:shot:${draft.workspaceId}:${draft.sourceLineage.screenplay_revision_id}:${draft.sourceLineage.setup_hash}:${draft.workflowId}:${draft.clipId}` : '';
const shotEdits = (draft: Draft) => ({ prompt:draft.prompt,r2vMainPrompt:draft.r2vMainPrompt,r2vCollatedPrompt:draft.r2vCollatedPrompt,r2vImages:draft.r2vImages,r2vAudios:draft.r2vAudios,r2vVideos:draft.r2vVideos,duration:draft.duration,resolution:draft.resolution,aspectRatio:draft.aspectRatio,sourceLineage:draft.sourceLineage,directorPrepared:draft.directorPrepared,directorWarnings:draft.directorWarnings,referenceReviews:draft.referenceReviews });
const ACTIVE_KEY = 'vibe-video-active-job-v1';
const HISTORY_KEY = 'vibe-video-history-v1';
const STORY_HANDOFF_KEY = 'vibe-story-video-handoff-v1';
const STYLE_SETUP_CONTEXT_KEY = 'vibe-style-setup-context-v1';
const currentStyleSetupContext = () => { try { return localStorage.getItem(STYLE_SETUP_CONTEXT_KEY) || ''; } catch { return ''; } };
const unicodeLength = (s: string) => Array.from(s).length;
const id = () => crypto.randomUUID();
const capabilityBlocker = (capability: Capability) => !capability.available
  ? 'The selected video workflow is not ready. Check Status for setup details.'
  : capability.runtime_guard?.safe_to_submit !== true
    ? 'GPU safety has not cleared this system for video generation. Check Status before retrying.'
    : capability.dispatch?.available !== true
      ? 'The video worker is stopped or unavailable. Check Status for setup details.'
      : 'Video generation is ready.';
const capabilityDetails = (capability: Capability) => {
  const reasons = [capability.disabled_reason, capability.runtime_guard?.reason, capability.dispatch?.reason]
    .filter((reason): reason is string => Boolean(reason?.trim()));
  return reasons.filter((reason, index) => reasons.indexOf(reason) === index && !reasons.slice(0, index).some(previous => previous.includes(reason)));
};
const defaultDraft = (): Draft => ({ prompt: '', duration: 6, aspectRatio: '16:9', resolution: 0.98, workspaceId: defaultMediaWorkspaceId(), clipId: id(), workflowId: WORKFLOW_ID });
const requestedVideoWorkspace = () => new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || '';
const readDraft = (workspaceId?: string): Draft => {
  const fallback = defaultDraft();
  try {
    const latest = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null') as Draft | null;
    const selected = workspaceId || managedProjectId() || requestedVideoWorkspace() || latest?.workspaceId || fallback.workspaceId;
    const saved = JSON.parse(localStorage.getItem(`${DRAFT_KEY}:${selected}`) || 'null') as Draft | null;
    return {...fallback, ...(saved?.workspaceId === selected ? saved : latest?.workspaceId === selected ? latest : {}), workspaceId: selected};
  } catch { return {...fallback, workspaceId: workspaceId || fallback.workspaceId}; }
};
type SavedVideo = { job: Job; snapshot: VideoRequest; r2vMainPrompt?: string };
type TakeClip = SavedVideo & { playbackUrl: string };

function TakeClipCard({ clip, selected, onSelect }: { clip: TakeClip; selected: boolean; onSelect: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const preview = (play: boolean) => {
    const player = video.current;
    if (!player) return;
    if (play) { player.muted = true; void player.play().catch(() => {}); }
    else { player.pause(); player.currentTime = 0; }
  };
  return <button type="button" className={`take-clip-card${selected ? ' selected' : ''}`} aria-pressed={selected}
    aria-label={`Take ${clip.job.attempt || '—'} · ${clip.snapshot.duration_seconds}s · ${clip.snapshot.prompt}`} title={clip.snapshot.prompt} onClick={onSelect}
    onMouseEnter={() => preview(true)} onMouseLeave={() => preview(false)} onFocus={() => preview(true)} onBlur={() => preview(false)}>
    <video ref={video} src={clip.playbackUrl} muted loop playsInline preload="metadata" aria-hidden="true" />
    <span>Take {clip.job.attempt || '—'} · {clip.snapshot.duration_seconds}s</span>
  </button>;
}

const readActive = (): { jobId: string; workspaceId?: string; snapshot: VideoRequest; retakeOf?: string; keepOriginal?: boolean; r2vMainPrompt?: string } | null => { try { return JSON.parse(localStorage.getItem(ACTIVE_KEY) || 'null'); } catch { return null; } };
const saveWorkspaceActive = (workspaceId: string, value: string) => {
  const scoped = JSON.stringify({...JSON.parse(value), workspaceId});
  localStorage.setItem(ACTIVE_KEY, scoped);
  localStorage.setItem(`${ACTIVE_KEY}:${workspaceId}`, scoped);
};
const clearWorkspaceActive = (workspaceId: string) => {
  const scoped = readWorkspaceActive(workspaceId);
  if (readActive()?.workspaceId === workspaceId || (scoped && readActive()?.jobId === scoped.jobId)) localStorage.removeItem(ACTIVE_KEY);
  localStorage.removeItem(`${ACTIVE_KEY}:${workspaceId}`);
};
const readWorkspaceActive = (workspaceId: string): ReturnType<typeof readActive> => {
  try {
    const scoped = JSON.parse(localStorage.getItem(`${ACTIVE_KEY}:${workspaceId}`) || 'null');
    if (scoped) return scoped;
    const legacy = readActive();
    return legacy?.workspaceId === workspaceId ? legacy : null;
  } catch { return null; }
};
const TERMINAL_STATUSES = new Set(['needs_review','accepted','failed','rejected','stale','cancelled']);
const isTerminalStatus = (status?: string) => !!status && TERMINAL_STATUSES.has(status);
const isReviewable = (status?: string) => status === 'needs_review' || status === 'accepted';
const readHistory = () => { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') as SavedVideo[]; } catch { return []; } };
const openTakeIfOnVideo = () => { if (window.location.hash.split('?')[0] === '#/video') window.location.hash = `#/take?workspace_id=${encodeURIComponent(readDraft().workspaceId)}`; };
const storyClipId = async (workspaceId: string, revisionId: string, scene: number, shot: number) => {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${workspaceId}\0${revisionId}\0${scene}\0${shot}`));
  const hex = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
  return `story-${hex.slice(0, 40)}`;
};

function VideoWorkspace({ view='create', visible=true, workspaceId }: { view?: 'create'|'take'; visible?: boolean; workspaceId: string }) {
  const [batchMode, setBatchMode] = useState(false);
  const [batchActive, setBatchActive] = useState(false);
  type R2vCarouselKey = 'characters'|'worlds'|'first-frames'|'last-frames'|'voices'|'audio-clips'|'video-clips'|'image-assets'|'imported-images'|'imported-audio'|'source-videos';
  const [draft, setDraftState] = useState<Draft>(() => readDraft(workspaceId));
  const [active, setActive] = useState<SavedVideo & { retakeOf?: string; keepOriginal?: boolean } | null>(null);
  const [history, setHistory] = useState<SavedVideo[]>(readHistory);
  const [selectedTakeJobId, setSelectedTakeJobId] = useState(() => localStorage.getItem(`vibe-selected-take:${workspaceId}`) || '');
  useEffect(() => { if (selectedTakeJobId) localStorage.setItem(`vibe-selected-take:${workspaceId}`, selectedTakeJobId); }, [selectedTakeJobId, workspaceId]);
  const [capability, setCapability] = useState<Capability | null>(null);
  const [capState, setCapState] = useState<'idle'|'loading'|'ready'|'unavailable'>('idle');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [retakeDialog, setRetakeDialog] = useState(false);
  const [retakeKeep, setRetakeKeep] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [preparingShotPrompt, setPreparingShotPrompt] = useState(false);
  const [mediaAssets, setMediaAssets] = useState<MediaAsset[]>([]);
  const [imageLoadError,setImageLoadError] = useState('');
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [assetsError, setAssetsError] = useState('');
  const [libraryRefresh, setLibraryRefresh] = useState(0);
  const [mediaWorkspaceId, setMediaWorkspaceId] = useState('');
  const [workspaces, setWorkspaces] = useState<StoryWorkspace[]>([]);
  const [, setWorkspaceError] = useState('');
  const [knownWorkspaceIds] = useState<string[]>(() => {
    try { return [...new Set([draft.workspaceId, ...Object.keys(localStorage).filter(key => key.startsWith(`${DRAFT_KEY}:`) && !key.startsWith(`${DRAFT_KEY}:shot:`)).map(key => key.slice(DRAFT_KEY.length + 1))])]; }
    catch { return [draft.workspaceId]; }
  });
  const workspaceChoices = mediaWorkspaceOptions(workspaces, draft.workspaceId);
  const standaloneId = standaloneMediaWorkspaceId();
  if (!workspaceChoices.some(row => row.id === standaloneId)) workspaceChoices.push({id: standaloneId, label: 'Standalone media workspace'});
  for (const workspaceId of knownWorkspaceIds) {
    if (!workspaceChoices.some(row => row.id === workspaceId)) workspaceChoices.push({id: workspaceId, label: `Saved video draft · ${workspaceId}`});
  }
  const [currentImageIds, setCurrentImageIds] = useState<Set<string>>(new Set());
  const [uploadingRefs, setUploadingRefs] = useState(false);
  const [uploadingFrameRole, setUploadingFrameRole] = useState<'first_frame'|'last_frame'|null>(null);
  const [r2vSource, setR2vSource] = useState<Record<string,string>>({Images:'characters',Audio:'voices',Videos:'video-clips'});
  const [r2vCatalogue, setR2vCatalogue] = useState<Record<string,CataloguePage>>({});
  const [r2vCatalogueOffset, setR2vCatalogueOffset] = useState<Record<string,number>>({});
  const [r2vCatalogueBusy, setR2vCatalogueBusy] = useState<Record<string,boolean>>({});
  const [r2vCatalogueError, setR2vCatalogueError] = useState<Record<string,string>>({});
  const [r2vWorkspaceNames, setR2vWorkspaceNames] = useState<Record<string,string>>({});
  const [r2vWorkspaceIds, setR2vWorkspaceIds] = useState<string[]>([]);
  const isAnalyzedReference = (asset: MediaAsset) => !!(asset.metadata?.analyzer_run_id || asset.metadata?.sam_audio?.run_id);
  const [r2vSearch, setR2vSearch] = useState<Partial<Record<R2vCarouselKey,string>>>({});
  const [r2vSort, setR2vSort] = useState<Partial<Record<R2vCarouselKey,'newest'|'oldest'>>>({});
  const [r2vPickerSelection, setR2vPickerSelection] = useState<Partial<Record<R2vCarouselKey,string[]>>>({});
  const [r2vSearchMode, setR2vSearchMode] = useState<Partial<Record<R2vCarouselKey,'keyword'|'semantic'>>>({});
  const [r2vSemanticIds, setR2vSemanticIds] = useState<Partial<Record<R2vCarouselKey,string[]>>>({});
  const [r2vSemanticQueries, setR2vSemanticQueries] = useState<Partial<Record<R2vCarouselKey,string>>>({});
  const [r2vSemanticBusy, setR2vSemanticBusy] = useState<Partial<Record<R2vCarouselKey,boolean>>>({});
  const [r2vSeoStyles, setR2vSeoStyles] = useState<MediaSeoStyle[]>([]);
  const [r2vSeoStyleId, setR2vSeoStyleId] = useState('');
  const [preview, setPreview] = useState<any>(null);
  const [fullRunWorkspace, setFullRunWorkspace] = useState('');
  const [fullRunRevision, setFullRunRevision] = useState('');
  const [fullRunTitle, setFullRunTitle] = useState('');
  const [fullRunSetup, setFullRunSetup] = useState<ProductionSetup | null>(null);
  const [fullRunState, setFullRunState] = useState<AutomatedFirstClipState | null>(null);
  const [fullRunCapability, setFullRunCapability] = useState<Capability | null>(null);
  const [fullRunLoading, setFullRunLoading] = useState(false);
  const [fullRunBusy, setFullRunBusy] = useState(false);
  const [fullRunError, setFullRunError] = useState('');
  const fullRunLoadRef = useRef(0);
  const fullRunStatusRequest = useRef<{ epoch: number; promise: Promise<void> } | null>(null);
  const [fullRunRefreshing, setFullRunRefreshing] = useState(false);
  const [fullRunCheckedAt, setFullRunCheckedAt] = useState('');
  const hasPendingAttempt = Boolean(draft.pendingKey || draft.pendingRequest);
  const activeUnresolved = Boolean(active && !isTerminalStatus(active.job.status));

  const setDraft = useCallback((update: (prev: Draft) => Draft) => setDraftState(prev => { let next = update(prev);
    const beforeKey = shotDraftKey(prev), afterKey = shotDraftKey(next);
    if (beforeKey) localStorage.setItem(beforeKey, JSON.stringify(shotEdits(prev)));
    if (afterKey && afterKey !== beforeKey) {
      try { const saved = JSON.parse(localStorage.getItem(afterKey) || 'null'); if (saved) next = {...next,...saved}; } catch { /* Keep the current valid draft if its saved copy is unreadable. */ }
    }
    if (afterKey) localStorage.setItem(afterKey, JSON.stringify(shotEdits(next)));
    localStorage.setItem(DRAFT_KEY, JSON.stringify(next)); localStorage.setItem(`${DRAFT_KEY}:${next.workspaceId}`, JSON.stringify(next)); return next; }), []);
  useEffect(() => {
    if (!visible) return;
    let alive = true;
    void (async () => {
      const rows: StoryWorkspace[] = [];
      let page;
      do {
        page = await listStoryWorkspaces(rows.length, 50);
        rows.push(...page.items);
      } while (page.items.length && rows.length < page.total);
      if (alive) { setWorkspaces(rows); setWorkspaceError(''); }
    })().catch(error => { if (alive) setWorkspaceError((error as Error).message); });
    return () => { alive = false; };
  }, [visible]);
  useEffect(() => {
    localStorage.setItem(`${DRAFT_KEY}:${draft.workspaceId}`, JSON.stringify(draft));
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [draft]);
  const refreshFullRun = useCallback(async () => {
    const loadId = ++fullRunLoadRef.current;
    if (!visible) return;
    const requestedWorkspace = managedProjectId() || new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || '';
    const selectedId = requestedWorkspace || workspaceId;
    setFullRunCheckedAt(''); setFullRunRefreshing(false);
    setFullRunSetup(null); setFullRunWorkspace(''); setFullRunRevision(''); setFullRunState(null); setFullRunCapability(null); setFullRunError(''); setFullRunLoading(false);
    if (!selectedId.startsWith('story-')) return;
    setFullRunLoading(true);
    try {
      const workspace = await getStoryWorkspace(selectedId);
      if (loadId !== fullRunLoadRef.current) return;
      const sourceId = workspace.current_revision_id || workspace.current_revision?.revision_id;
      if (!sourceId) return;
      const screenplay = await getStoryScreenplay(selectedId, sourceId);
      if (!screenplay.accepted) return;
      const [revisions, setupState] = await Promise.all([
        listStoryScreenplays(selectedId), getProductionSetup(selectedId, screenplay.screenplay_revision_id),
      ]);
      if (loadId !== fullRunLoadRef.current) return;
      const currentAccepted = revisions.items.some(item => item.screenplay_revision_id === screenplay.screenplay_revision_id
        && item.source_revision_id === sourceId && item.accepted && !item.stale);
      if (!currentAccepted || setupState.setup?.mode !== 'fully_automated') return;
      setFullRunSetup(setupState.setup); setFullRunWorkspace(selectedId); setFullRunRevision(screenplay.screenplay_revision_id); setFullRunTitle(workspace.title);
      const firstWorkflow = WORKFLOW_ID;
      const run = await getAutomatedFirstClip(selectedId, screenplay.screenplay_revision_id).catch(() => null);
      if (loadId !== fullRunLoadRef.current) return;
      setFullRunState(run);
      if (!run) { setFullRunError('Could not recover run state. Refresh before starting; no Start action is offered.'); return; }
      if (run.run_state === 'not_started') {
        try { const capability = await getCapability(firstWorkflow); if (loadId === fullRunLoadRef.current) setFullRunCapability(capability); } catch { if (loadId === fullRunLoadRef.current) setFullRunCapability(null); }
      }
    } catch (error) { if (loadId === fullRunLoadRef.current) setFullRunError((error as Error).message); }
    finally { if (loadId === fullRunLoadRef.current) setFullRunLoading(false); }
  }, [visible, workspaceId]);
  useEffect(() => {
    void refreshFullRun();
    const onStorage = (event: StorageEvent) => { if (event.key === 'vibe-story-selected-v1') void refreshFullRun(); };
    const onHashChange = () => { void refreshFullRun(); };
    window.addEventListener('storage', onStorage);
    window.addEventListener('hashchange', onHashChange);
    return () => { fullRunLoadRef.current += 1; window.removeEventListener('storage', onStorage); window.removeEventListener('hashchange', onHashChange); };
  }, [refreshFullRun]);
  // Read the pinned run directly. A status check must not rediscover/reset its context.
  const refreshFullRunStatus = useCallback(async () => {
    if (!fullRunWorkspace || !fullRunRevision || fullRunBusy) return;
    const epoch = fullRunLoadRef.current;
    if (fullRunStatusRequest.current?.epoch === epoch) return fullRunStatusRequest.current.promise;
    setFullRunRefreshing(true);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12000);
    const promise = (async () => {
      try {
        const run = await getAutomatedFirstClip(fullRunWorkspace, fullRunRevision, controller.signal);
        if (epoch !== fullRunLoadRef.current) return;
        setFullRunState(run);
        setFullRunCheckedAt(new Date().toLocaleTimeString());
        setFullRunError('');
        if (run.run_state === 'not_started') {
          const workflow = WORKFLOW_ID;
          const capability = await getCapability(workflow, controller.signal);
          if (epoch === fullRunLoadRef.current) setFullRunCapability(capability);
        }
      } catch (error) {
        if (epoch === fullRunLoadRef.current) {
          setFullRunError(`Status check failed: ${controller.signal.aborted ? 'Request timed out.' : (error as Error).message} Showing the last known run. Refresh to retry; no new job was submitted.`);
          // Do not offer Start using an old readiness result after a failed check.
          setFullRunCapability(null);
        }
      } finally {
        window.clearTimeout(timeout);
        if (fullRunStatusRequest.current?.epoch === epoch) fullRunStatusRequest.current = null;
        if (epoch === fullRunLoadRef.current) setFullRunRefreshing(false);
      }
    })();
    fullRunStatusRequest.current = { epoch, promise };
    return promise;
  }, [fullRunWorkspace, fullRunRevision, fullRunBusy, fullRunSetup]);
  useEffect(() => {
    const identityReviewPending = fullRunState?.clips?.some(clip =>
      clip.identity_review && ['queued', 'processing'].includes(clip.identity_review.state));
    if (!fullRunWorkspace || !fullRunState ||
        (!['first_clip_queued', 'waiting_for_readiness', 'owner_paused'].includes(fullRunState.run_state) && !identityReviewPending)) return;
    const timer = window.setInterval(() => void refreshFullRunStatus(), 3000);
    return () => window.clearInterval(timer);
  }, [refreshFullRunStatus, fullRunState?.run_state,
      fullRunState?.clips?.map(clip => clip.identity_review?.state || 'none').join(',')]);
  const startFullRun = async () => {
    if (!fullRunWorkspace || !fullRunRevision || !fullRunCapability?.available || fullRunBusy || fullRunRefreshing || fullRunState?.run_state !== 'not_started' || !fullRunState.prompt_plan_ready) return;
    setFullRunBusy(true); setFullRunError('');
    window.location.hash = `#/take?workspace_id=${encodeURIComponent(fullRunWorkspace)}`;
    try {
      setFullRunState(await startAutomatedFirstClip(fullRunWorkspace, fullRunRevision));
      window.location.hash = `#/take?workspace_id=${encodeURIComponent(fullRunWorkspace)}`;
    }
    catch (error) { setFullRunError((error as Error).message); }
    finally { setFullRunBusy(false); }
  };
  const retryFullRunShot = async (sceneNumber: number, shotNumber: number, clipNumber: number) => {
    if (!fullRunWorkspace || !fullRunRevision || fullRunBusy || fullRunRefreshing || fullRunState?.run_state !== 'paused') return;
    setFullRunBusy(true); setFullRunError('');
    try { setFullRunState((await retryAutomatedRunShot(fullRunWorkspace, fullRunRevision, sceneNumber, shotNumber, clipNumber)).run); }
    catch (error) { setFullRunError((error as Error).message); }
    finally { setFullRunBusy(false); }
  };
  const controlFullRun = async (action: 'pause'|'resume'|'stop') => {
    if (!fullRunWorkspace || !fullRunRevision || fullRunBusy) return;
    fullRunLoadRef.current += 1;
    setFullRunRefreshing(false);
    setFullRunBusy(true); setFullRunError('');
    try { setFullRunState(await controlAutomatedRun(fullRunWorkspace, fullRunRevision, action)); }
    catch (error) { setFullRunError((error as Error).message); }
    finally { setFullRunBusy(false); }
  };
  const resumeFullRun = async () => {
    if (!fullRunWorkspace || !fullRunRevision || fullRunBusy || fullRunRefreshing || fullRunState?.run_state !== 'paused' || !fullRunState.resume_available) return;
    setFullRunBusy(true); setFullRunError('');
    try { setFullRunState(await resumeAutomatedRun(fullRunWorkspace, fullRunRevision)); }
    catch (error) { setFullRunError((error as Error).message); }
    finally { setFullRunBusy(false); }
  };
  useEffect(() => {
    if (!visible) return;
    const raw = localStorage.getItem(STORY_HANDOFF_KEY);
    if (!raw) return;
    let handoff: StoryHandoff;
    try { handoff = JSON.parse(raw) as StoryHandoff; } catch { localStorage.removeItem(STORY_HANDOFF_KEY); setMessage('The saved screenplay handoff was invalid. Choose the shot again from an accepted-screenplay workflow; no video job was started.'); return; }
    if (hasPendingAttempt || activeUnresolved) { setMessage('A saved video attempt is still unresolved. It was kept; settle it before opening a screenplay shot.'); return; }
    if ((draft.prompt.trim() || draft.sourceLineage) && !window.confirm('Replace the current video draft with the selected saved screenplay shot?')) return;
    const workflowId = handoff.workflow_id;
    setDraft(prev => ({ ...prev, workspaceId: handoff.workspace_id, clipId: handoff.clip_id,
      prompt: handoff.prompt, workflowId, sourceLineage: {
        screenplay_revision_id: handoff.screenplay_revision_id, setup_hash: handoff.setup_hash, ...(handoff.board_revision ? {board_revision:handoff.board_revision}:{}),
        scene_number: handoff.scene_number, shot_number: handoff.shot_number,
        source_prompt_sha256: handoff.source_prompt_sha256, knowledge_ref: handoff.knowledge_ref, style_ref: handoff.style_ref,
      }, r2vMainPrompt: workflowId === R2V_WORKFLOW_ID ? handoff.prompt : undefined,
      r2vCollatedPrompt: undefined, r2vImages: handoff.r2v_images || [], r2vVideos: [], r2vAudios: [], duration:handoff.duration||prev.duration,directorPrepared:false, directorWarnings:[], referenceReviews:{},
      firstFrameAssetId: handoff.first_frame_id, lastFrameAssetId: handoff.last_frame_id, pendingKey: undefined,
      pendingRequest: undefined, retakeOf: undefined, keepOriginal: undefined }));
    setPreview(null); setCapability(null); setCapState('idle');
    setMessage(`Opened saved screenplay Scene ${handoff.scene_number}, Shot ${handoff.shot_number}. Confirm the workflow settings in Video; the job has not started.`);
    localStorage.removeItem(STORY_HANDOFF_KEY);
  // Handoff is consumed only when the Video workspace becomes visible.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);
  const promptLength = unicodeLength(draft.prompt);
  const isFl2va = draft.workflowId === FL2VA_WORKFLOW_ID;
  const isR2v = draft.workflowId === R2V_WORKFLOW_ID;
  const firstFrame = mediaWorkspaceId === draft.workspaceId ? mediaAssets.find(asset => asset.asset_id === draft.firstFrameAssetId) : undefined;
  const lastFrame = mediaWorkspaceId === draft.workspaceId ? mediaAssets.find(asset => asset.asset_id === draft.lastFrameAssetId) : undefined;
  const frameCandidates = (role: 'first_frame'|'last_frame') => mediaAssets
    .filter(asset => asset.kind === 'image' && asset.roles.includes(role))
    .sort((a,b) => Number(isStoryFrame(b, role)) - Number(isStoryFrame(a, role)) || a.filename.localeCompare(b.filename));
  function isStoryFrame(asset: MediaAsset, role: 'first_frame'|'last_frame') {
    const job = asset.metadata?.production_image_job;
    const lineage = job?.settings?.lineage;
    return !!draft.sourceLineage && job?.intended_role === role && lineage?.target_type === 'clip'
      && lineage.screenplay_revision_id === draft.sourceLineage.screenplay_revision_id
      && lineage.scene_number === draft.sourceLineage.scene_number
      && lineage.shot_number === draft.sourceLineage.shot_number
      && lineage.clip_id === draft.clipId;
  }
  const frameOption = (asset: MediaAsset, role: 'first_frame'|'last_frame') => {
    const lineage = asset.metadata?.production_image_job?.settings?.lineage;
    const shot = lineage?.target_type === 'clip' && Number.isInteger(lineage.scene_number) && Number.isInteger(lineage.shot_number)
      ? `Scene ${lineage.scene_number} · Shot ${lineage.shot_number} · ` : '';
    return `${isStoryFrame(asset, role) ? 'Recommended · ' : ''}${shot}${asset.filename}`;
  };
  const r2vRefs = { images: draft.r2vImages || [], videos: draft.r2vVideos || [], audios: draft.r2vAudios || [] };
  const r2vTotalRefs = r2vRefs.images.length + r2vRefs.videos.length + r2vRefs.audios.length;
  const r2vUniqueRefs = new Set([...r2vRefs.images, ...r2vRefs.videos, ...r2vRefs.audios].map(ref => ref.assetId)).size === r2vTotalRefs;
  const r2vAssets = mediaWorkspaceId === draft.workspaceId ? mediaAssets : [];
  const activeR2vSeoStyle = r2vSeoStyles.find(style => style.style_id === r2vSeoStyleId);
  const assetForRef = (ref: R2VReferenceDraft) => r2vAssets.find(asset => asset.asset_id === ref.assetId);
  const r2vMainPrompt = draft.r2vMainPrompt !== undefined ? draft.r2vMainPrompt : draft.prompt;
  const buildR2vPrompt = () => {
    const lines = [r2vMainPrompt.trim()];
    let audioIndex = 1;
    r2vRefs.images.forEach((ref, index) => lines.push(`<Picture ${index + 1}> is a ${ref.role} reference. Use it to ${ref.intent}`));
    r2vRefs.videos.forEach((ref, index) => {
      lines.push(`<Video ${index + 1}> is a ${ref.role} reference. Use it to ${ref.intent}`);
      if (ref.includePairedSoundtrack) { lines.push(`<Audio ${audioIndex}> is the soundtrack from <Video ${index + 1}>. Use it to ${ref.audioIntent || 'guide the sound'}`); audioIndex += 1; }
    });
    r2vRefs.audios.forEach(ref => { lines.push(`<Audio ${audioIndex}> is a ${ref.role} reference. Use it to ${ref.intent}`); audioIndex += 1; });
    return r2vMainPrompt.trim() ? lines.filter(Boolean).join('\n\n') : '';
  };
  const bindR2vSpeakers = (prompt: string) => {
    if (!prompt.trim()) return prompt;
    // Canonicalize pasted/Director-authored tag spelling, preserving reference indices.
    // Missing references must still fail backend validation.
    prompt = prompt.replace(/<(picture|video|audio)\s*(\d+)>/gi,
      (_tag, kind: string, number: string) => `<${kind[0].toUpperCase()}${kind.slice(1).toLowerCase()} ${Number(number)}>`);
    const bindings: string[] = [];
    let audioIndex = 1 + r2vRefs.videos.filter(ref => ref.includePairedSoundtrack).length;
    r2vRefs.audios.forEach(ref => {
      const tag = `<Audio ${audioIndex++}>`;
      for (const speaker of ref.speakerIds || []) {
        // Same statement boundary and range as the backend speaker-binding contract.
        const bound = prompt.split(/[.\n]/).some(statement => {
          const tagAt = statement.indexOf(tag);
          const speakerAt = statement.indexOf(`(${speaker})`, tagAt + tag.length);
          return tagAt >= 0 && speakerAt >= tagAt + tag.length && speakerAt - tagAt - tag.length <= 240;
        });
        if (!bound) bindings.push(`${tag} is the assigned voice for speaker (${speaker}).`);
      }
    });
    return [prompt, ...bindings].join('\n\n');
  };
  const r2vFinalPrompt = bindR2vSpeakers(draft.r2vCollatedPrompt ?? buildR2vPrompt());
  const effectivePrompt = isR2v ? (r2vFinalPrompt || r2vMainPrompt) : draft.prompt;
  const effectivePromptLength = unicodeLength(effectivePrompt);
  const takeClips: TakeClip[] = [...(active && isReviewable(active.job.status) ? [active] : []), ...history]
    .filter(item => item.job.workspace_id === draft.workspaceId)
    .filter((item, index, items) => items.findIndex(candidate => candidate.job.job_id === item.job.job_id) === index)
    .flatMap(item => {
      const output = item.job.outputs?.find(candidate => candidate.kind === 'video' && candidate.playback_url);
      if (!output?.playback_url) return [];
      const playbackUrl = /^https?:\/\//.test(output.playback_url) ? output.playback_url : `${window.location.origin}${output.playback_url}`;
      return [{...item, playbackUrl}];
    });
  const selectedTakeClip = takeClips.find(item => item.job.job_id === selectedTakeJobId) || takeClips[0];
  useEffect(() => {
    if (active && isReviewable(active.job.status) && active.job.outputs?.some(output => output.kind === 'video' && output.playback_url))
      setSelectedTakeJobId(previous => previous || active.job.job_id);
  }, [active?.job.job_id, active?.job.status]);
  const r2vInputError = isR2v && !hasPendingAttempt ? assetsLoading ? 'Wait for this workspace’s image, video and audio library to load.' : !r2vTotalRefs ? 'Add at least one image, video or audio reference.' : !r2vUniqueRefs ? 'The same asset cannot be selected more than once.' : r2vRefs.images.length > 9 || r2vRefs.videos.length > 3 || r2vRefs.audios.length > 3 ? 'R2V limits: up to 9 images, 3 videos and 3 standalone audio references.' : [...r2vRefs.images, ...r2vRefs.videos, ...r2vRefs.audios].some(ref => !assetForRef(ref)) ? 'One or more selected references are no longer available in this workspace.' : [...r2vRefs.images, ...r2vRefs.videos, ...r2vRefs.audios].some(ref => !ref.role.trim() || !ref.intent.trim()) ? 'Give every selected reference a role and a short instruction.' : r2vRefs.videos.some(ref => ref.includePairedSoundtrack && !ref.audioIntent?.trim()) ? 'Describe how the selected video soundtrack should guide the new clip.' : !r2vMainPrompt.trim() && !r2vFinalPrompt ? 'Add a final prompt or describe the shot before collating references.' : !r2vFinalPrompt ? 'Collate references to prepare the final prompt and required MiniMax labels.' : '' : '';
  const errors = useMemo(() => ({ prompt: isR2v ? (!effectivePrompt.trim() ? (r2vFinalPrompt ? 'Add a prompt to describe the shot.' : 'Collate the main prompt and reference instructions first.') : effectivePromptLength >= 7000 ? 'Prompt must be fewer than 7,000 characters.' : '') : !draft.prompt.trim() ? 'Add a prompt to describe the shot.' : promptLength >= 7000 ? 'Prompt must be fewer than 7,000 characters.' : '', duration: draft.duration < 5 || draft.duration > (draft.workflowId === FL2VA_WORKFLOW_ID || isR2v ? 15 : 30) ? `Choose 5 to ${draft.workflowId === FL2VA_WORKFLOW_ID || isR2v ? 15 : 30} seconds.` : '', frames: draft.workflowId === FL2VA_WORKFLOW_ID && !hasPendingAttempt && (assetsLoading || !!imageLoadError || !firstFrame || !lastFrame) ? assetsLoading ? 'Wait for this workspace’s image library to load.' : imageLoadError ? 'Frame images could not be loaded. Refresh the library and try again.' : 'Choose a first and last image from this workspace library.' : '', r2v: r2vInputError }), [draft.prompt, draft.duration, draft.workflowId, promptLength, effectivePrompt, effectivePromptLength, r2vFinalPrompt, r2vInputError, isR2v, hasPendingAttempt, assetsLoading, imageLoadError, firstFrame, lastFrame]);
  const draftIdentity = JSON.stringify(draft);
  const currentDraftIdentity = useRef(draftIdentity);
  currentDraftIdentity.current = draftIdentity;
  const formLocked = busy || uploadingRefs || uploadingFrameRole !== null || hasPendingAttempt || capState === 'loading' || preparingShotPrompt;

  useLayoutEffect(() => {
    if (!visible) { setAssetsLoading(false); setMediaWorkspaceId(''); return; }
    let alive = true; setAssetsLoading(true); setAssetsError(''); setImageLoadError(''); setMediaWorkspaceId(''); setCurrentImageIds(new Set()); setPreview(null);
    const kinds = ['image', 'video', 'audio'];
    const styleContextId = currentStyleSetupContext();
    Promise.all([Promise.allSettled(kinds.map(kind => listMediaAssets(draft.workspaceId, kind, false, styleContextId))),
      isR2v ? listMediaSeoStyles(draft.workspaceId).catch(() => ({styles: [] as MediaSeoStyle[]})) : Promise.resolve({styles: [] as MediaSeoStyle[]})])
      .then(async ([results, styles]) => {
        const failures = results.flatMap((result,index)=>result.status==='rejected'?[`${kinds[index]}: ${result.reason?.message||'Could not load library'}`]:[]);
        const assets = results.flatMap(result => result.status==='fulfilled'?result.value.assets:[]);
        if(alive){setAssetsError(failures.join('; '));setImageLoadError(results[0].status==='rejected'?'Image library could not be loaded.':'');}
        const selected = new Set<string>();
        const targets = new Map<string, {revision: string; type: string; id: string}>();
        for (const asset of assets) {
          const lineage = asset.metadata?.production_image_job?.settings?.lineage;
          const role = asset.roles.find(role => ['character_master','world_master','first_frame','last_frame'].includes(role));
          if (!role || !lineage?.screenplay_revision_id) { selected.add(asset.asset_id); continue; }
          if (draft.sourceLineage && lineage.screenplay_revision_id !== draft.sourceLineage.screenplay_revision_id) continue;
          const type = role === 'character_master' ? 'character' : role === 'world_master' ? 'location' : role;
          const id = ['first_frame','last_frame'].includes(role) ? lineage.clip_id : lineage.target_record_id;
          if (!id) continue;
          const target = {revision: lineage.screenplay_revision_id, type, id};
          targets.set(JSON.stringify(target), target);
        }
        await Promise.all([...targets.values()].map(async target => {
          const result = await getImageSelection(draft.workspaceId, target.revision, target.type, target.id);
          if (result.selection) selected.add(result.selection.asset_id);
        }));
        if (alive) { setCurrentImageIds(selected); setMediaAssets(assets); setMediaWorkspaceId(draft.workspaceId); setR2vSeoStyles(Array.isArray(styles?.styles) ? styles.styles : []); }
      })
      .catch(error => { if (alive) { setMediaAssets([]); setAssetsError((error as Error).message); setImageLoadError((error as Error).message); setMessage(`Could not load ${isR2v ? 'reference assets' : 'frame images'}: ${(error as Error).message}. Add assets in Media Prep for this workspace, then retry.`); } })
      .finally(() => { if (alive) setAssetsLoading(false); });
    return () => { alive = false; };
  }, [visible, draft.workflowId, draft.workspaceId, isFl2va, isR2v, draft.sourceLineage?.screenplay_revision_id, libraryRefresh]);

  const refreshCapability = async () => {
    const identity = currentDraftIdentity.current; const workflowId = draft.workflowId;
    setCapState('loading'); setMessage(`Checking ${isFl2va ? 'first/last frame' : isR2v ? 'reference to video' : 'text to video'} readiness…`);
    try { const value = await getCapability(workflowId); if (currentDraftIdentity.current !== identity) { setCapState('idle'); return; } setCapability(value); const safe = value.runtime_guard?.safe_to_submit === true; const dispatch = value.dispatch?.available === true; setCapState(value.available && safe && dispatch ? 'ready' : 'unavailable'); setMessage(value.available && safe && dispatch ? 'Video generation is ready.' : 'Video generation is not ready. See Local Engine for details.'); }
    catch (e) { if (currentDraftIdentity.current !== identity) { setCapState('idle'); return; } setCapability(null); setCapState('unavailable'); setMessage(`Backend unavailable: ${String((e as Error).message)}. Your draft is saved on this device.`); }
  };

  useEffect(() => {
    if (visible && view === 'create' && capState === 'idle' && !preparingShotPrompt) void refreshCapability();
  }, [visible, view, capState, preparingShotPrompt]);

  const prepareCurrentShotPrompt = async () => {
    const lineage = draft.sourceLineage;
    if (!lineage || preparingShotPrompt || formLocked) return;
    if (lineage.board_revision) { window.location.hash='#/shot-frames'; return; }
    if (lineage.planned_clip_id) {
      try {
        const plan = await getAssistedVideoClipPlan(draft.workspaceId, lineage.screenplay_revision_id);
        const clip = plan.clips.find(row => row.clip_id === lineage.planned_clip_id);
        if (!clip) throw new Error('The selected clip is no longer in the saved plan.');
        if ((draft.r2vMainPrompt || draft.prompt).trim() && !window.confirm('Restore this clip’s planned prompt? This replaces your current prompt edits.')) return;
        setDraft(previous=>({...previous,prompt:clip.prompt,r2vMainPrompt:clip.prompt,r2vCollatedPrompt:undefined}));
        setPreview(null);setMessage('Planned clip prompt restored. Reference overrides are preserved.');
      } catch (error) { setMessage(`Could not restore the planned prompt: ${(error as Error).message}`); }
      return;
    }
    const currentPrompt = isR2v ? (draft.r2vMainPrompt ?? draft.prompt) : draft.prompt;
    if (currentPrompt.trim() && !window.confirm('Replace the current shot prompt with a new draft prepared from the accepted screenplay?')) return;
    setPreparingShotPrompt(true);
    setMessage('');
    try {
      const setupState = await getProductionSetup(draft.workspaceId, lineage.screenplay_revision_id);
      if (!setupState.setup) throw new Error('Save Automation & Parameters before preparing a screenplay prompt.');
      const shotKey = `${lineage.scene_number}.${lineage.shot_number}`;
      const prepared = await prepareStoryPrompt(draft.workspaceId, lineage.screenplay_revision_id, shotKey, draft.workflowId);
      if (prepared.workflow_id !== draft.workflowId) throw new Error('The prepared prompt workflow changed. Nothing was applied; check the selected workflow and try again.');
      const saved = await saveStoryPromptShot(draft.workspaceId, lineage.screenplay_revision_id, setupState.setup, shotKey, {
        workflow_id: prepared.workflow_id,
        prompt: prepared.prompt,
        knowledge_ref: prepared.knowledge_ref,
        style_ref: prepared.style_ref,
      });
      const persisted = saved.drafts[shotKey];
      if (!persisted?.prompt?.trim()) throw new Error('The prompt was prepared but could not be confirmed in the saved shot drafts.');
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(persisted.prompt));
      const sourcePromptSha = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
      setDraft(previous => {
        if (previous.clipId !== draft.clipId || previous.sourceLineage?.screenplay_revision_id !== lineage.screenplay_revision_id) return previous;
        return {
          ...previous,
          prompt: persisted.prompt,
          r2vMainPrompt: persisted.workflow_id === R2V_WORKFLOW_ID ? persisted.prompt : undefined,
          r2vCollatedPrompt: undefined,
          sourceLineage: { ...lineage, source_prompt_sha256: sourcePromptSha, knowledge_ref: persisted.knowledge_ref, style_ref: persisted.style_ref },
        };
      });
      setPreview(null);
      setMessage(`Prepared and saved a prompt for Scene ${lineage.scene_number}, Shot ${lineage.shot_number} using ${prepared.workflow_id} guidance v${prepared.knowledge_ref.guidance_version}. Review and edit it before generation.`);
    } catch (error) {
      setMessage(`Could not prepare this shot prompt: ${(error as Error).message}`);
    } finally {
      setPreparingShotPrompt(false);
    }
  };
  const returnToEditing = async (pending: Draft = draft) => {
    if (!pending.pendingKey || !pending.pendingRequest) return;
    const identity = currentDraftIdentity.current;
    setBusy(true);
    try {
      const result = await releaseVideoAttempt(pending.workspaceId, pending.pendingKey);
      if (currentDraftIdentity.current !== identity) return;
      if (!result.released) {
        if (!result.job) throw new Error('The backend did not confirm the attempt state.');
        const job = result.job;
        const saved = { jobId:job.job_id, snapshot:pending.pendingRequest, retakeOf:pending.retakeOf, keepOriginal:pending.keepOriginal, r2vMainPrompt:pending.r2vMainPrompt };
        saveWorkspaceActive(pending.workspaceId, JSON.stringify(saved));
        setActive({job, snapshot:pending.pendingRequest, retakeOf:pending.retakeOf, keepOriginal:pending.keepOriginal, r2vMainPrompt:pending.r2vMainPrompt});
      }
      const editable = {...pending, pendingKey:undefined, pendingRequest:undefined};
      localStorage.setItem(DRAFT_KEY, JSON.stringify(editable)); setDraftState(editable);
      setMessage(result.released ? 'No render was submitted. Your prompt, references and workflow choices are editable again.' : 'Recovered your existing job without submitting another render. Your draft is editable.');
    } catch (error) { setMessage(`Could not confirm the saved attempt: ${(error as Error).message}. Your draft and references are preserved.`); }
    finally { setBusy(false); }
  };
  // Only a confirmed 404 releases recovery; transport errors keep the saved job.
  const forgetMissingJob = useCallback((jobId: string) => {
    if (readWorkspaceActive(draft.workspaceId)?.jobId === jobId) clearWorkspaceActive(draft.workspaceId);
    setActive(previous => previous?.job.job_id === jobId ? null : previous);
    setHistory(previous => {
      const remaining = previous.filter(item => item.job.job_id !== jobId);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(remaining));
      return remaining;
    });
    setMessage(`Saved job ${jobId} no longer exists. Recovery stopped; your draft prompt is kept. No new job was submitted.`);
  }, []);
  useEffect(() => { let alive = true; const resume = async () => { let savedActive = readWorkspaceActive(draft.workspaceId); const legacy = readActive(); if (!savedActive && legacy?.jobId) { try { const job = await getJob(legacy.jobId); if (!alive) return; if (job.workspace_id === draft.workspaceId) { savedActive = {...legacy, workspaceId: draft.workspaceId}; saveWorkspaceActive(draft.workspaceId, JSON.stringify(savedActive)); } } catch { /* Legacy pointer is retained until its workspace can be confirmed. */ } } if (savedActive?.jobId) { setActive({ job: { job_id: savedActive.jobId, status: 'recovery_required' }, snapshot: savedActive.snapshot, retakeOf: savedActive.retakeOf, keepOriginal: savedActive.keepOriginal, r2vMainPrompt: savedActive.r2vMainPrompt }); try { const job = await getJob(savedActive.jobId); if (alive) { setActive({ job, snapshot: savedActive.snapshot, retakeOf: savedActive.retakeOf, keepOriginal: savedActive.keepOriginal, r2vMainPrompt: savedActive.r2vMainPrompt });  } } catch (e) { if (alive) { if (e instanceof ApiError && e.status === 404) forgetMissingJob(savedActive.jobId); else setMessage(`Could not reconnect to saved job ${savedActive.jobId}. Its reference and frozen prompt are preserved; no replacement job can start until it is reconciled.`); } } return; } const pending = readDraft(draft.workspaceId); if (pending.pendingKey && pending.pendingRequest) { try { const job = await findJobByIdempotency(pending.workspaceId, pending.pendingKey); if (!alive) return; saveWorkspaceActive(draft.workspaceId, JSON.stringify({ jobId: job.job_id, snapshot: pending.pendingRequest, retakeOf: pending.retakeOf, keepOriginal: pending.keepOriginal, r2vMainPrompt: pending.r2vMainPrompt })); setActive({ job, snapshot: pending.pendingRequest, retakeOf: pending.retakeOf, keepOriginal: pending.keepOriginal, r2vMainPrompt: pending.r2vMainPrompt }); const cleared = { ...pending, pendingKey: undefined, pendingRequest: undefined }; localStorage.setItem(DRAFT_KEY, JSON.stringify(cleared)); setDraftState(cleared); setMessage('Recovered the saved job by its idempotency key. No new job was submitted.');  } catch (e) { if (alive && e instanceof ApiError && e.status === 404) { await returnToEditing(pending); } else if (alive) setMessage(`Saved attempt could not be reconciled: ${(e as Error).message}. The immutable request and key remain saved; no job was submitted during reload.`); } } }; void resume(); return () => { alive = false; }; }, [draft.workspaceId]);
  useEffect(() => {
    if (!visible || view !== 'take' || !draft.workspaceId) return;
    let alive = true;
    void listAllJobs(draft.workspaceId).then(({ jobs }) => {
      if (!alive) return;
      const saved = jobs.filter(job => job.candidate_disposition !== 'discard_requested'
        && ['accepted', 'needs_review'].includes(job.status)

        && (job.request || job.request_snapshot))
        .map(job => ({ job, snapshot: (job.request || job.request_snapshot)! }));
      const known = new Set(jobs.map(job => job.job_id));
      for (const item of saved) known.add(item.job.job_id);
      const local = readHistory().filter(item => item.job.workspace_id === draft.workspaceId && !known.has(item.job.job_id));
      const merged = [...saved, ...local];
      setHistory(merged);
      localStorage.setItem(HISTORY_KEY, JSON.stringify([...readHistory().filter(item => item.job.workspace_id !== draft.workspaceId), ...merged]));
      if (!readWorkspaceActive(draft.workspaceId)) {
        const latest = jobs.find(job => job.candidate_disposition !== 'discard_requested' && (job.request || job.request_snapshot));
        if (latest) setActive({job: latest, snapshot: (latest.request || latest.request_snapshot)!});
      }
    }).catch(() => undefined);
    return () => { alive = false; };
  }, [visible, view, draft.workspaceId]);
  useEffect(() => {
    if (!active || isTerminalStatus(active.job.status)) return;
    let alive = true;
    const jobId = active.job.job_id;
    const timer = window.setInterval(() => {
      getJob(jobId).then(job => {
        if (alive) setActive(previous => previous?.job.job_id === jobId ? { ...previous, job } : previous);
      }).catch(error => {
        if (!alive) return;
        if (error instanceof ApiError && error.status === 404) {
          alive = false;
          window.clearInterval(timer);
          forgetMissingJob(jobId);
        } else setMessage('Connection interrupted. The same saved job will be checked again; no new job was submitted.');
      });
    }, 2500);
    return () => { alive = false; window.clearInterval(timer); };
  }, [active?.job.job_id, active?.job.status, forgetMissingJob]);

  useEffect(() => {
    if (!isR2v || !visible) return;
    let alive = true;
    for (const [group, kind] of [['Images','image'],['Audio','audio'],['Videos','video']]) {
      const selection = r2vSource[group];
      const remote = selection.startsWith('global:') || selection.startsWith('workspace:');
      if (!remote && group !== 'Videos') continue;
      setR2vCatalogueBusy(current=>({...current,[group]:true}));
      setR2vCatalogueError(current=>({...current,[group]:''}));
      browseMediaCatalogue(draft.workspaceId, {kinds:kind, source:selection.startsWith('global:')?selection.slice(7):'all',
        owner:selection.startsWith('workspace:')?selection.slice(10):'', query:r2vSearch[group==='Images'?'characters':group==='Audio'?'voices':'video-clips']||'', offset:r2vCatalogueOffset[group]||0, order:r2vSort[group==='Images'?'characters':group==='Audio'?'voices':'video-clips']||'newest'})
        .then(page=>{if(alive){setR2vCatalogue(current=>({...current,[group]:page}));setR2vWorkspaceNames(current=>({...current,...page.workspace_names}));setR2vWorkspaceIds(current=>[...new Set([...current,...page.workspaces])]);}})
        .catch(error=>{if(alive)setR2vCatalogueError(current=>({...current,[group]:(error as Error).message}));})
        .finally(()=>{if(alive)setR2vCatalogueBusy(current=>({...current,[group]:false}));});
    }
    return ()=>{alive=false;};
  }, [isR2v, visible, draft.workspaceId, r2vSource, r2vCatalogueOffset, r2vSearch, r2vSort, libraryRefresh]);

  const makeRequest = (): VideoRequest => isR2v
    ? ({ workflow_id: R2V_WORKFLOW_ID, workflow_version: 2, workflow_sha256: R2V_WORKFLOW_SHA256,
        prompt: r2vFinalPrompt, duration_seconds: draft.duration, aspect_ratio: draft.aspectRatio || '16:9',
        resolution_preset: draft.resolution, steps: 4, seed: 1, ref_image_size: 'match',
        images: r2vRefs.images.map(ref => ({ asset_id: ref.assetId, sha256: assetForRef(ref)!.sha256, role: ref.role, intent: ref.intent })),
        videos: r2vRefs.videos.map(ref => ({ asset_id: ref.assetId, sha256: assetForRef(ref)!.sha256, role: ref.role, intent: ref.intent,
          start_sec: ref.startSec ?? null, end_sec: ref.endSec ?? null, include_paired_soundtrack: ref.includePairedSoundtrack === true, audio_intent: ref.includePairedSoundtrack ? (ref.audioIntent || '') : '' })),
        audios: r2vRefs.audios.map(ref => ({ asset_id: ref.assetId, sha256: assetForRef(ref)!.sha256, role: ref.role, intent: ref.intent, ...(ref.speakerIds?.length ? {speaker_ids:ref.speakerIds} : {speaker_id:null}) })) })
    : isFl2va
      ? ({ workflow_id: FL2VA_WORKFLOW_ID, workflow_version: 2, workflow_sha256: FL2VA_WORKFLOW_SHA256, prompt: draft.prompt, duration_seconds: draft.duration, aspect_ratio: draft.aspectRatio || '16:9', resolution_preset: draft.resolution, first_frame: firstFrame ? {asset_id: firstFrame.asset_id, sha256: firstFrame.sha256} : undefined, last_frame: lastFrame ? {asset_id: lastFrame.asset_id, sha256: lastFrame.sha256} : undefined })
      : ({ workflow_id: WORKFLOW_ID, workflow_version: 2, workflow_sha256: WORKFLOW_SHA256, prompt: draft.prompt, duration_seconds: draft.duration, aspect_ratio: draft.aspectRatio || '16:9', resolution_preset: draft.resolution, steps: 4, seed: 1, references: [] });
  const collateR2vPrompt = () => {
    setDraft(prev => ({ ...prev, r2vCollatedPrompt: r2vFinalPrompt }));
    setPreview(null);
    setMessage('Prompt collated with workflow reference labels. Review and edit the final prompt before previewing.');
  };
  const updateR2vRef = (kind: 'images'|'videos'|'audios', index: number, change: Partial<R2VReferenceDraft>) => {
    setDraft(prev => { const key = kind === 'images' ? 'r2vImages' : kind === 'videos' ? 'r2vVideos' : 'r2vAudios';
      const rows = [...(prev[key] || [])]; rows[index] = { ...rows[index], ...change };
      return { ...prev, [key]: rows, r2vCollatedPrompt: undefined } as Draft; }); setPreview(null);
  };
  const addR2vRef = (kind: 'images'|'videos'|'audios', assetId: string) => {
    if (!assetId) return;
    if (r2vRefs[kind].some(ref=>ref.assetId===assetId)) return;
    if (r2vRefs[kind].length + 1 > (kind==='images'?9:3)) {
      window.alert(`This workflow accepts at most ${kind==='images'?9:3} ${kind}. Remove a reference before adding another.`);
      return;
    }
    const key = kind === 'images' ? 'r2vImages' : kind === 'videos' ? 'r2vVideos' : 'r2vAudios';
    const defaults = kind === 'images' ? { role: 'visual identity or style', intent: 'preserve the relevant visual details' }
      : kind === 'videos' ? { role: 'motion or camera reference', intent: 'guide the movement and timing' }
      : { role: 'audio or voice reference', intent: 'guide the sound, tone or timing' };
    setDraft(prev => ({ ...prev, [key]: [...(prev[key] || []), { assetId, ...defaults }], r2vCollatedPrompt: undefined } as Draft)); setPreview(null);
  };
  const toggleR2vPickerAsset = (carouselKey: R2vCarouselKey, assetId: string, alreadyAdded: Set<string>) => {
    setR2vPickerSelection(current => {
      const selected = current[carouselKey] || [];
      if (selected.includes(assetId)) return {...current,[carouselKey]:selected.filter(id=>id!==assetId)};
      if (alreadyAdded.has(assetId) || Object.entries(current).some(([key, ids]) => key !== carouselKey && (ids || []).includes(assetId))) return current;
      return {...current,[carouselKey]:[...selected,assetId]};
    });
  };
  const addSelectedR2vRefs = async (carouselKey: R2vCarouselKey, kind: 'images'|'videos'|'audios') => {
    const selected = r2vPickerSelection[carouselKey] || [];
    if (!selected.length) return;
    const existingIds = new Set([...r2vRefs.images,...r2vRefs.videos,...r2vRefs.audios].map(ref=>ref.assetId));
    const count = r2vRefs[kind].length + selected.filter(id=>!existingIds.has(id)).length;
    const maximum = kind==='images'?9:3;
    if (count > maximum) {
      window.alert(`That would add ${count} ${kind}. This workflow accepts at most ${maximum}. Deselect ${count-maximum} before adding.`);
      return;
    }
    const key = kind === 'images' ? 'r2vImages' : kind === 'videos' ? 'r2vVideos' : 'r2vAudios';
    const defaults = kind === 'images' ? { role: 'visual identity or style', intent: 'preserve the relevant visual details' }
      : kind === 'videos' ? { role: 'motion or camera reference', intent: 'guide the movement and timing' }
      : { role: 'audio or voice reference', intent: 'guide the sound, tone or timing' };
    const contextWorkspace = draft.workspaceId;
    const contextClip = draft.clipId;
    let localIds: string[] = [];
    setUploadingRefs(true);
    try {
      for (const id of selected) {
        const asset = mediaAssets.find(row=>row.asset_id===id) || Object.values(r2vCatalogue).flatMap(page=>page.assets).find(row=>row.asset_id===id);
        if (!asset) throw new Error('Reference is no longer available. Choose it again.');
        const local = asset.workspace_id === contextWorkspace ? asset : await reuseCatalogueAsset(contextWorkspace, asset);
        localIds.push(local.asset_id);
        setMediaAssets(current=>[...current.filter(row=>row.asset_id!==local.asset_id),local]);
      }
    } catch(error) { setMessage(`Could not add references: ${(error as Error).message}. Your selections are kept for retry.`); return; }
    finally {setUploadingRefs(false);}
    setDraft(prev => {
      if(prev.workspaceId!==contextWorkspace || prev.clipId!==contextClip)return prev;
      const existing = [...(prev.r2vImages || []),...(prev.r2vVideos || []),...(prev.r2vAudios || [])];
      const ids = new Set(existing.map(ref=>ref.assetId));
      const additions = [...new Set(localIds)].filter(assetId=>!ids.has(assetId)).map(assetId=>({assetId,...defaults}));
      return additions.length ? {...prev,[key]:[...(prev[key] || []),...additions],r2vCollatedPrompt:undefined} as Draft : prev;
    });
    setR2vPickerSelection(current=>({...current,[carouselKey]:[]}));
    setPreview(null);
  };
  const removeR2vRef = (kind: 'images'|'videos'|'audios', index: number) => {
    const key = kind === 'images' ? 'r2vImages' : kind === 'videos' ? 'r2vVideos' : 'r2vAudios';
    setDraft(prev => ({ ...prev, [key]: (prev[key] || []).filter((_, rowIndex) => rowIndex !== index), r2vCollatedPrompt: undefined } as Draft)); setPreview(null);
  };
  const searchR2vSemantically = async (carouselKey: R2vCarouselKey, kind: 'images'|'videos'|'audios') => {
    const query = (r2vSearch[carouselKey] || '').trim();
    if (!query) return;
    const mediaKind = kind === 'images' ? 'image' : kind === 'videos' ? 'video' : 'audio';
    setR2vSemanticBusy(current => ({...current,[carouselKey]:true}));
    try {
      const result = await searchMediaSemantically(draft.workspaceId, mediaKind, query);
      const results = result.results.map(row => row.asset).filter(asset => asset.workspace_id === draft.workspaceId && asset.kind === mediaKind);
      setMediaAssets(current => {
        const byId = new Map(current.map(asset => [asset.asset_id, asset]));
        results.forEach(asset => byId.set(asset.asset_id, asset));
        return [...byId.values()];
      });
      setR2vSemanticIds(current => ({...current,[carouselKey]:results.map(asset=>asset.asset_id)}));
      setR2vSemanticQueries(current => ({...current,[carouselKey]:query}));
      setMessage(result.reason || `Found ${result.results.length} semantic ${kind} matches.`);
    } catch (error) {
      setR2vSemanticIds(current => ({...current,[carouselKey]:[]}));
      setR2vSemanticQueries(current => ({...current,[carouselKey]:query}));
      setMessage(`Semantic search unavailable: ${(error as Error).message}`);
    } finally { setR2vSemanticBusy(current => ({...current,[carouselKey]:false})); }
  };
  const uploadR2vFiles = async (files: File[], expectedKind?: 'images'|'videos'|'audios', sourceKey?: R2vCarouselKey) => {
    if (!files.length || !isR2v || formLocked) return;
    const detectKind = (file: File): 'images'|'videos'|'audios'|undefined => {
      if (file.type.startsWith('image/')) return 'images';
      if (file.type.startsWith('video/')) return 'videos';
      if (file.type.startsWith('audio/')) return 'audios';
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (['png','jpg','jpeg','webp'].includes(ext || '')) return 'images';
      if (['mp4','mov','mkv','webm'].includes(ext || '')) return 'videos';
      if (['wav','mp3','m4a','ogg','flac','aac'].includes(ext || '')) return 'audios';
    };
    const roleFor = (kind: 'images'|'videos'|'audios') => ({characters:'character_master',worlds:'world_master','first-frames':'first_frame','last-frames':'last_frame',voices:'voice_master'} as Partial<Record<R2vCarouselKey,string>>)[sourceKey || 'imported-images'] || (kind === 'images' ? 'project_image' : kind === 'videos' ? 'project_video' : 'project_audio');
    const accepted: Array<{file: File; kind: 'images'|'videos'|'audios'}> = [];
    for (const file of files) {
      const kind = detectKind(file);
      if (!kind || (expectedKind && kind !== expectedKind)) { setMessage(`Skipped ${file.name}: choose a supported ${expectedKind?.slice(0,-1) || 'image, video or audio'} file.`); continue; }
      accepted.push({ file, kind });
    }
    if (!accepted.length) return;
    setUploadingRefs(true); setMessage(`Adding ${accepted.length} reference${accepted.length === 1 ? '' : 's'} to this workspace…`);
    const uploaded: MediaAsset[] = [];
    try {
      for (const row of accepted) {
        const asset = await uploadMediaAsset(draft.workspaceId, row.file, roleFor(row.kind));
        uploaded.push(asset);
      }
      const library = await Promise.all(['image','video','audio'].map(kind => listMediaAssets(draft.workspaceId, kind)));
      setMediaAssets(library.flatMap(page => page.assets)); setMediaWorkspaceId(draft.workspaceId);
      const selectedIds = new Set([...r2vRefs.images,...r2vRefs.videos,...r2vRefs.audios].map(ref => ref.assetId));
      for (const asset of uploaded) {
        const kind = asset.kind === 'image' ? 'images' : asset.kind === 'video' ? 'videos' : 'audios';
        if (!selectedIds.has(asset.asset_id)) { addR2vRef(kind, asset.asset_id); selectedIds.add(asset.asset_id); }
      }
      setMessage(`${uploaded.length} reference${uploaded.length === 1 ? '' : 's'} saved to the workspace library and added to this prompt.`);
    } catch (error) { try { const library = await Promise.all(['image','video','audio'].map(kind => listMediaAssets(draft.workspaceId, kind))); setMediaAssets(library.flatMap(page => page.assets)); setMediaWorkspaceId(draft.workspaceId); } catch { /* preserve the original upload error */ } setMessage(`Reference upload failed: ${(error as Error).message}. Any completed uploads remain in the workspace library.`); }
    finally { setUploadingRefs(false); }
  };
  const uploadFrameFile = async (file: File | undefined, role: 'first_frame'|'last_frame') => {
    if (!file || formLocked) return;
    const isImage = file.type.startsWith('image/') || /\.(png|jpe?g|webp)$/i.test(file.name);
    if (!isImage) { setMessage(`Skipped ${file.name}: choose a PNG, JPEG, or WebP image for this frame.`); return; }
    const workspaceId = draft.workspaceId;
    const identity = currentDraftIdentity.current;
    setUploadingFrameRole(role); setMessage(`Adding ${role === 'first_frame' ? 'first' : 'last'} frame to this workspace…`);
    try {
      const asset = await uploadMediaAsset(workspaceId, file, role);
      if (currentDraftIdentity.current !== identity) {
        setMessage(`${file.name} was saved to its original workspace. The current draft changed, so it was not selected.`);
        return;
      }
      setMediaAssets(current => {
        const byId = new Map((mediaWorkspaceId === workspaceId ? current : []).map(item => [item.asset_id, item]));
        byId.set(asset.asset_id, asset);
        return [...byId.values()];
      });
      setMediaWorkspaceId(workspaceId);
      setDraft(current => current.workspaceId === workspaceId ? {
        ...current,
        [role === 'first_frame' ? 'firstFrameAssetId' : 'lastFrameAssetId']: asset.asset_id,
      } : current);
      setPreview(null);
      setMessage(`${file.name} was saved and assigned as the ${role === 'first_frame' ? 'first' : 'last'} frame. The other frame slot was left unchanged.`);
    } catch (error) {
      setMessage(`Frame upload failed: ${(error as Error).message}. Your other frame selection is unchanged.`);
    } finally { setUploadingFrameRole(null); }
  };
  const pasteFrameFile = (event: ClipboardEvent<HTMLDivElement>, role: 'first_frame'|'last_frame') => {
    const files = Array.from(event.clipboardData.files);
    const itemFiles = Array.from(event.clipboardData.items).filter(item => item.kind === 'file').map(item => item.getAsFile()).filter((file): file is File => !!file);
    const file = [...files, ...itemFiles].find(item => item.type.startsWith('image/'));
    if (file) { event.preventDefault(); void uploadFrameFile(file, role); }
  };
  const dropFrameFile = (event: DragEvent<HTMLDivElement>, role: 'first_frame'|'last_frame') => {
    event.preventDefault(); void uploadFrameFile(event.dataTransfer.files[0], role);
  };
  const pasteR2vFiles = (event: ClipboardEvent<HTMLDivElement>) => {
    if (!isR2v) return;
    const files = Array.from(event.clipboardData.files);
    if (files.length) { event.preventDefault(); void uploadR2vFiles(files); }
  };
  const dropR2vFiles = (event: DragEvent<HTMLElement>, kind: 'images'|'videos'|'audios', sourceKey?: R2vCarouselKey) => {
    event.preventDefault(); void uploadR2vFiles(Array.from(event.dataTransfer.files), kind, sourceKey);
  };
  const preparePreview = async () => {
    if (errors.prompt || errors.duration || errors.frames || errors.r2v) { setMessage(errors.prompt || errors.duration || errors.frames || errors.r2v); return; }
    const identity = currentDraftIdentity.current; const request = makeRequest(); setBusy(true); setMessage('');
    try { const result = await validateRequest(request); if (currentDraftIdentity.current !== identity) return; setPreview(result.compiled_preview); setMessage('Settings validated. This is a preview; no video job was submitted.'); }
    catch (error) { if (currentDraftIdentity.current !== identity) return; setPreview(null); setMessage(`Could not compile preview: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const generate = async () => {
    if (busy) return;
    if (errors.prompt || errors.duration || errors.frames || errors.r2v) { setMessage(errors.prompt || errors.duration || errors.frames || errors.r2v); return; }
    const identity = currentDraftIdentity.current; const workflowId = draft.workflowId; setBusy(true); setMessage('');
    try {
      // Every explicit Generate click rechecks workflow and GPU admission.
      const cap = await getCapability(workflowId); if (currentDraftIdentity.current !== identity) return; setCapability(cap);
      const safe = cap.runtime_guard?.safe_to_submit === true; const dispatch = cap.dispatch?.available === true;
      setCapState(cap.available && safe && dispatch ? 'ready' : 'unavailable');
      if (!cap.available || !safe || !dispatch) throw new Error(!cap.available ? cap.disabled_reason || 'Local workflow is not ready. The draft stays editable.' : !safe ? cap.runtime_guard?.reason || 'GPU safety admission is unavailable. Generation is blocked; the draft stays editable.' : cap.dispatch?.reason || 'The isolated video worker is disabled or unavailable.');
      if (active && !isTerminalStatus(active.job.status)) throw new Error(`Job ${active.job.job_id} is still ${active.job.status.replaceAll('_',' ')}. Its saved request is preserved; wait for it to settle before starting another job.`);

      let frozen = draft.pendingRequest;
      let attemptKey = draft.pendingKey;
      if (Boolean(frozen) !== Boolean(attemptKey)) throw new Error('Saved attempt data is incomplete. Its local record is preserved; no new job was submitted.');
      if (frozen && attemptKey) {
        try {
          const recovered = await findJobByIdempotency(draft.workspaceId, attemptKey);
          saveWorkspaceActive(draft.workspaceId, JSON.stringify({ jobId: recovered.job_id, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal, r2vMainPrompt: draft.r2vMainPrompt }));
          setActive({ job: recovered, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal, r2vMainPrompt: draft.r2vMainPrompt });
          const cleared = { ...draft, pendingKey: undefined, pendingRequest: undefined, retakeOf: undefined, keepOriginal: undefined };
          localStorage.setItem(DRAFT_KEY, JSON.stringify(cleared)); setDraftState(cleared);
          setMessage('Recovered the saved job by its idempotency key. No new job was submitted.');
          openTakeIfOnVideo();
          return;
        } catch (e) { if (!(e instanceof ApiError) || e.status !== 404) throw e; }
      } else {
        frozen = makeRequest();
        attemptKey = id();
      }
      if (!frozen || !attemptKey) throw new Error('Could not prepare a saved generation attempt.');
      const validation = await validateRequest(frozen);
      if (currentDraftIdentity.current !== identity) return;
      if (validation.valid === false) throw new Error(validation.issues?.map((i: any) => i.message).join(' ') || 'The backend rejected these settings.');
      // Persist the immutable payload and key before the only job-creating POST.
      const savedAttempt = { ...draft, pendingKey: attemptKey, pendingRequest: frozen };
      localStorage.setItem(DRAFT_KEY, JSON.stringify(savedAttempt)); setDraftState(savedAttempt);
      const retake = draft.retakeOf ? { retake_of_job_id: draft.retakeOf, keep_original: draft.keepOriginal !== false } : undefined;
      const job = await createJob(draft.workspaceId, draft.clipId, attemptKey, frozen, retake, draft.sourceLineage);
      if (active && isTerminalStatus(active.job.status) && active.job.job_id !== job.job_id) { const nextHistory = [{ job: active.job, snapshot: active.snapshot, r2vMainPrompt: active.r2vMainPrompt }, ...history.filter(h => h.job.job_id !== active.job.job_id)]; setHistory(nextHistory); localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory)); }
      const nextActive = { job, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal, r2vMainPrompt: isR2v ? r2vMainPrompt : undefined };
      saveWorkspaceActive(draft.workspaceId, JSON.stringify({ jobId: job.job_id, snapshot: frozen, retakeOf: draft.retakeOf, keepOriginal: draft.keepOriginal, r2vMainPrompt: isR2v ? r2vMainPrompt : undefined }));
      setActive(nextActive); setMessage('Job saved. Progress will resume from this job if you reload.');
      openTakeIfOnVideo();
      const cleared = { ...draft, pendingKey: undefined, pendingRequest: undefined, retakeOf: undefined, keepOriginal: undefined };
      localStorage.setItem(DRAFT_KEY, JSON.stringify(cleared)); setDraftState(cleared);
    } catch (e) {
      if (e instanceof ApiError && e.admissionState === 'not_created') {
        const rejected = readDraft();
        if (rejected.pendingKey && rejected.pendingRequest) {
          const retryable = { ...rejected, pendingKey: undefined, pendingRequest: undefined,
            ...(rejected.sourceLineage && !rejected.retakeOf ? { sourceLineage: undefined, clipId: id() } : {}) };
          localStorage.setItem(DRAFT_KEY, JSON.stringify(retryable)); setDraftState(retryable);
          setMessage(`${e.message} The backend confirmed no job was created. Your prompt, references and settings remain editable. You can generate directly without preparing a screenplay shot.`);
        } else setMessage(e.message);
      } else setMessage((e as Error).message || 'Could not create job. The same saved attempt will be reused if the response was lost.');
    }
    finally { setBusy(false); }
  };
  const startRetake = async () => { if (!active) return; const source = active; setBusy(true); try { const result = await prepareRetake(source.job.job_id, retakeKeep); if (result.submission_created !== false) throw new Error('Backend did not confirm that the retake is only a draft.'); const request = result.request as VideoRequest; setDraft(prev => ({ ...prev, workflowId: request.workflow_id, workspaceId: source.job.workspace_id || prev.workspaceId, clipId: source.job.clip_id || prev.clipId, sourceLineage: result.source_lineage ? { screenplay_revision_id: result.source_lineage.screenplay_revision_id, setup_hash: result.source_lineage.setup_hash, scene_number: result.source_lineage.scene_number, shot_number: result.source_lineage.shot_number, source_prompt_sha256: result.source_lineage.source_prompt_sha256, planned_clip_id: result.source_lineage.planned_clip_id, ...(result.source_lineage.board_revision ? {board_revision:result.source_lineage.board_revision}:{}), knowledge_ref: result.source_lineage.knowledge_ref, style_ref: result.source_lineage.style_ref } : undefined, prompt: request.workflow_id===R2V_WORKFLOW_ID?prev.prompt:request.prompt, r2vMainPrompt:request.workflow_id===R2V_WORKFLOW_ID?(source.r2vMainPrompt ?? prev.r2vMainPrompt ?? prev.prompt):prev.r2vMainPrompt, r2vCollatedPrompt:request.workflow_id===R2V_WORKFLOW_ID?request.prompt:undefined, r2vImages:request.images?.map(ref=>({assetId:ref.asset_id,role:ref.role,intent:ref.intent})), r2vVideos:request.videos?.map(ref=>({assetId:ref.asset_id,role:ref.role,intent:ref.intent,startSec:ref.start_sec??undefined,endSec:ref.end_sec??undefined,includePairedSoundtrack:ref.include_paired_soundtrack,audioIntent:ref.audio_intent})), r2vAudios:request.audios?.map(ref=>({assetId:ref.asset_id,role:ref.role,intent:ref.intent,speakerIds:'speaker_ids' in ref ? ref.speaker_ids : ref.speaker_id ? [ref.speaker_id] : undefined})), duration: request.duration_seconds, resolution: request.resolution_preset, aspectRatio: request.aspect_ratio, firstFrameAssetId: request.first_frame?.asset_id, lastFrameAssetId: request.last_frame?.asset_id, pendingKey: undefined, pendingRequest: undefined, retakeOf: source.job.job_id, keepOriginal: result.keep_original })); if (isReviewable(source.job.status)) { const nextHistory = result.keep_original ? [{ job: source.job, snapshot: source.snapshot, r2vMainPrompt: source.r2vMainPrompt }, ...history.filter(h => h.job.job_id !== source.job.job_id)] : history.filter(h => h.job.job_id !== source.job.job_id); setHistory(nextHistory); localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory)); } clearWorkspaceActive(draft.workspaceId); setActive(null); setRetakeDialog(false); const discardedStatus = result.asset_cleanup === 'archived_recoverable' ? 'The candidate is removed from take history and archived from normal library search; Show archived can restore it, and saved references still work.' : result.asset_cleanup === 'retained_shared' ? 'The candidate is removed from take history; its shared-library file stays visible because another video job uses the same asset.' : result.asset_cleanup === 'partially_archived' ? 'The candidate is removed from take history; unshared outputs are archived and shared outputs stay visible.' : 'The candidate is removed from take history; no generated library asset needed archiving.'; const keptStatus = result.asset_cleanup === 'restored' ? 'The current candidate is back in take history and its library output has been restored.' : 'The current candidate is kept in take history.'; setMessage(`Retake draft prepared. ${result.keep_original ? keptStatus : discardedStatus} Nothing has been generated yet.`); window.location.hash = '#/video'; } catch (e) { setMessage(`Could not prepare retake: ${(e as Error).message}`); } finally { setBusy(false); } };
  const advanceToNext = async () => {
    if (!active || !isReviewable(active.job.status)) return;
    setBusy(true);
    try {
      let nextDraft: Draft;
      if (active.job.source_lineage) {
        const lineage = active.job.source_lineage;
        if (draft.workspaceId !== active.job.workspace_id || draft.clipId !== active.job.clip_id) throw new Error('This take belongs to another draft. Reopen its saved draft before advancing.');
        if (lineage.board_revision) {
          const accepted = active.job.status === 'accepted' ? active.job : await acceptJob(active.job.job_id);
          setActive({...active,job:accepted});
          setMessage('Take accepted. Choose its finished clip in Frame per shot, then continue to the next shot.');
          window.location.hash='#/shot-frames'; return;
        }
        const [screenplay, promptState, setupState] = await Promise.all([
          getStoryScreenplayRevision(draft.workspaceId, lineage.screenplay_revision_id),
          getStoryPromptDrafts(draft.workspaceId, lineage.screenplay_revision_id),
          getProductionSetup(draft.workspaceId, lineage.screenplay_revision_id),
        ]);
        if (!screenplay.accepted || !promptState.setup_matches_current || promptState.setup_hash !== lineage.setup_hash || !setupState.setup) throw new Error('The accepted screenplay or production setup changed. Return to Automation & Parameters and review this run before advancing.');
        if (lineage.planned_clip_id) {
          const plan = await getAssistedVideoClipPlan(draft.workspaceId, lineage.screenplay_revision_id);
          const index = plan.clips.findIndex(clip => clip.clip_id === lineage.planned_clip_id);
          if (index < 0) throw new Error('The clip plan changed. Reload screenplay clips before advancing.');
          const accepted = active.job.status === 'accepted' ? active.job : await acceptJob(active.job.job_id);
          const nextHistory = [{job:accepted,snapshot:active.snapshot,r2vMainPrompt:active.r2vMainPrompt}, ...history.filter(item=>item.job.job_id!==accepted.job_id)];
          localStorage.setItem(HISTORY_KEY,JSON.stringify(nextHistory)); setHistory(nextHistory);
          const next = plan.clips[index+1];
          if (!next) { setActive({...active,job:accepted}); setMessage('Final clip accepted. All planned clips are complete.'); return; }
          setDraft(previous=>({...previous,clipId:next.clip_id,sourceLineage:{...lineage,scene_number:next.scene_number,shot_number:next.shot_number,planned_clip_id:next.clip_id},duration:next.duration_seconds,
            prompt:'',r2vMainPrompt:'',r2vCollatedPrompt:undefined,r2vImages:[],r2vAudios:[],r2vVideos:[],directorPrepared:false,retakeOf:undefined,keepOriginal:undefined,pendingKey:undefined,pendingRequest:undefined}));
          clearWorkspaceActive(draft.workspaceId);setActive(null);setPreview(null);setCapability(null);setCapState('idle');
          setLibraryRefresh(value=>value+1); setMessage('Take accepted. Preparing the next clip prompt. References are optional.'); window.location.hash='#/video'; return;
        }
        const shots = screenplay.screenplay.scenes.flatMap(scene => scene.shots.map(shot => ({scene: scene.scene_number, shot: shot.shot_number})))
          .sort((a,b) => a.scene - b.scene || a.shot - b.shot);
        const index = shots.findIndex(item => item.scene === lineage.scene_number && item.shot === lineage.shot_number);
        if (index < 0) throw new Error('This clip is not in the accepted screenplay. Review the current accepted screenplay and choose a valid shot before advancing; your current take is unchanged.');
        const next = shots[index + 1];
        if (!next) {
          const accepted = active.job.status === 'accepted' ? active.job : await acceptJob(active.job.job_id);
          const nextHistory = [{job: accepted, snapshot: active.snapshot, r2vMainPrompt: active.r2vMainPrompt}, ...history.filter(item => item.job.job_id !== accepted.job_id)];
          localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory)); setHistory(nextHistory);
          const completed = {...active, job: accepted};
          saveWorkspaceActive(draft.workspaceId, JSON.stringify({jobId: accepted.job_id, snapshot: active.snapshot,
            retakeOf: active.retakeOf, keepOriginal: active.keepOriginal, r2vMainPrompt: active.r2vMainPrompt})); setActive(completed);
          setMessage('Final take accepted. All screenplay shots have been reached.');
          return;
        }
        const key = `${next.scene}.${next.shot}`;
        let saved = promptState.drafts[key];
        if (!saved?.prompt?.trim()) {
          const config = setupState.setup;
          const workflow = config.mode === 'fully_automated'
            ? WORKFLOW_ID
            : config.automate_steps.video ? config.video_workflow_id : draft.workflowId;
          if (!workflow) throw new Error('Choose the video workflow in Automation & Parameters before preparing the next shot.');
          const prepared = await prepareStoryPrompt(draft.workspaceId, lineage.screenplay_revision_id, key, workflow);
          const persisted = await saveStoryPromptShot(draft.workspaceId, lineage.screenplay_revision_id, config, key, {
            workflow_id: prepared.workflow_id, prompt: prepared.prompt, knowledge_ref: prepared.knowledge_ref, style_ref: prepared.style_ref,
          });
          saved = persisted.drafts[key];
        }
        if (!saved?.prompt?.trim()) throw new Error(`Could not prepare a prompt for Scene ${next.scene}, Shot ${next.shot}. Your current take is unchanged.`);
        if (![WORKFLOW_ID, FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID].includes(saved.workflow_id as typeof WORKFLOW_ID)) throw new Error(`Scene ${next.scene}, Shot ${next.shot} has an unsupported video workflow.`);
        const clipId = await storyClipId(draft.workspaceId, lineage.screenplay_revision_id, next.scene, next.shot);
        const promptHash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(saved.prompt));
        const sourcePromptSha = Array.from(new Uint8Array(promptHash), value => value.toString(16).padStart(2, '0')).join('');
        nextDraft = { ...draft, prompt: saved.prompt, workflowId: saved.workflow_id as Draft['workflowId'], clipId,
          sourceLineage: {...lineage, scene_number: next.scene, shot_number: next.shot, source_prompt_sha256: sourcePromptSha, knowledge_ref: saved.knowledge_ref, style_ref: saved.style_ref},
          r2vMainPrompt: saved.workflow_id === R2V_WORKFLOW_ID ? saved.prompt : undefined,
          r2vCollatedPrompt: undefined, r2vImages: [], r2vVideos: [], r2vAudios: [], directorPrepared:false, directorWarnings:[], referenceReviews:{},
          firstFrameAssetId: undefined, lastFrameAssetId: undefined, pendingKey: undefined, pendingRequest: undefined,
          retakeOf: undefined, keepOriginal: undefined };
      } else {
        nextDraft = {...defaultDraft(), workspaceId: active.job.workspace_id || draft.workspaceId, duration: draft.duration, resolution: draft.resolution};
      }
      const accepted = active.job.status === 'accepted' ? active.job : await acceptJob(active.job.job_id);
      const nextHistory = [{job: accepted, snapshot: active.snapshot, r2vMainPrompt: active.r2vMainPrompt}, ...history.filter(item => item.job.job_id !== accepted.job_id)];
      localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory)); setHistory(nextHistory);
      localStorage.setItem(DRAFT_KEY, JSON.stringify(nextDraft)); setDraft(() => nextDraft);
      clearWorkspaceActive(draft.workspaceId); setActive(null); setPreview(null); setCapability(null); setCapState('idle');
      setMessage(nextDraft.sourceLineage ? `Take accepted. Loaded Scene ${nextDraft.sourceLineage.scene_number}, Shot ${nextDraft.sourceLineage.shot_number}; Director will prepare its references.` : 'Take accepted. A clean video draft is ready.');
      window.location.hash = '#/video';
    } catch (error) { setMessage(`Could not advance: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const isReviewableOutput = isReviewable(active?.job.status);
  const needsReview = active?.job.status === 'needs_review';
  const activeRequest = active?.job.request || active?.job.request_snapshot || active?.snapshot;
  const output = active?.job.outputs?.find(o => o.kind === 'video');
  const playback = output?.playback_url ? (/^https?:\/\//.test(output.playback_url) ? output.playback_url : `${window.location.origin}${output.playback_url}`) : '';
  const statusLabel = !active ? 'Draft' : active.job.status === 'refinement_pending' ? 'Waiting for LTX video refinement' : active.job.status.replaceAll('_', ' ');
  const markAccepted = async () => { if (!active) return; setBusy(true); try { const job = await acceptJob(active.job.job_id); setActive({ ...active, job }); setMessage('Take acceptance saved.'); } catch (e) { setMessage(`Could not save acceptance: ${(e as Error).message}`); } finally { setBusy(false); } };

  return <div className={`app-shell legacy-inner legacy-video-inner ${view==='take'?'take-inner':''}`} onPaste={pasteR2vFiles}>
    <main className="main-content">
      <div className={`content-wrap ${view==='take'?'take-workspace-wrap':'create-workspace-wrap'}`}><CreateWorkspace enabled={view==='create'} key={`create:${draft.workspaceId}:${draft.clipId}`} draft={draft} disabled={formLocked || activeUnresolved} onPrompt={value=>{setDraft(p=>isR2v?({...p,r2vMainPrompt:value,r2vCollatedPrompt:undefined}):({...p,prompt:value}));setPreview(null);}}>
      <TakeWorkspace enabled={view==='take'} workspaceId={draft.workspaceId}><div className="page-heading"><div><div className="eyebrow">STUDIO / VIDEO</div><h1>{view==='take'?'Current take':'Create video'}</h1><p>{view === 'take' && fullRunWorkspace ? `${fullRunTitle} · Fully automated` : view==='take'?'Review your take.':draft.sourceLineage ? `Screenplay · Scene ${draft.sourceLineage.scene_number}, Shot ${draft.sourceLineage.shot_number}` : 'Isolated video · no story linked'}</p></div><button className="quiet-button" onClick={() => { const next = {...defaultDraft(), workspaceId: draft.workspaceId}; setDraftState(next); localStorage.setItem(DRAFT_KEY, JSON.stringify(next)); setMessage(activeUnresolved ? `New draft created. Existing job ${active?.job.job_id} remains active and must settle before another job can start.` : 'New local draft created. Current take and history are preserved.'); }} disabled={formLocked || (view === 'take' && Boolean(fullRunWorkspace))}><span>＋</span> New draft</button></div>
      {view === 'take' && message && <div className={`notice ${message.toLowerCase().includes('unavailable') || message.toLowerCase().includes('error') || message.toLowerCase().includes('could not') ? 'notice-warn' : ''}`} role="status"><span>{message}</span><button onClick={() => setMessage('')} aria-label="Dismiss"><X size={15}/></button></div>}
      {view === 'create' && <OutputDestination tool="video-generation" workspaceId={draft.workspaceId} disabled={busy||fullRunBusy||formLocked}/>}
      {view === 'take' && <T2VBatchPanel key={`batch-take:${draft.workspaceId}`} workspaceId={draft.workspaceId} showVideos={false} />}
      {view === 'take' && fullRunLoading && <section className="card" aria-label="Fully automated run">Checking selected story and saved setup…</section>}
      {view === 'take' && !fullRunLoading && fullRunWorkspace && fullRunState && <section className="card full-run-panel" aria-label="Fully automated run">
        <div>{fullRunState.run_state === 'not_started' && <button type="button" className="generate-button" onClick={() => void startFullRun()} disabled={fullRunBusy || fullRunRefreshing || !fullRunCapability?.available || !fullRunState.prompt_plan_ready}>{fullRunBusy ? 'Starting…' : 'Start run'}</button>}
          {['first_clip_queued','waiting_for_readiness'].includes(fullRunState.run_state) && <button type="button" className="quiet-button" disabled={fullRunBusy} onClick={() => void controlFullRun('pause')}>Pause run</button>}
          {fullRunState.run_state === 'owner_paused' && <button type="button" className="quiet-button" disabled={fullRunBusy} onClick={() => void controlFullRun('resume')}>Resume run</button>}
          {!['not_started','completed','stopped'].includes(fullRunState.run_state) && <button type="button" className="quiet-button" disabled={fullRunBusy} onClick={() => void controlFullRun('stop')}>Stop run</button>}
          <button type="button" className="quiet-button" onClick={() => void refreshFullRunStatus()} disabled={fullRunBusy || fullRunRefreshing}><RefreshCw size={15}/> {fullRunRefreshing ? 'Refreshing…' : 'Refresh run'}</button></div>
        <div><b>Fully automated · {fullRunState.run_state === 'completed' ? 'complete' : ['paused','owner_paused'].includes(fullRunState.run_state) ? 'paused' : fullRunState.run_state === 'stopped' ? 'stopped' : fullRunState.run_state === 'not_started' ? fullRunCapability?.available && fullRunState.prompt_plan_ready ? 'ready' : 'not ready' : 'run'}</b>
          <span>{fullRunTitle} · accepted screenplay {fullRunRevision}</span>
          <span>{fullRunState.clips?.length ? `${fullRunState.completed_count || 0} of ${fullRunState.planned_count ?? '—'} clips complete · latest ${fullRunState.clips[fullRunState.clips.length - 1].job.status}` : fullRunState.job ? `Scene ${fullRunState.scene_number}, Shot ${fullRunState.shot_number} · ${fullRunState.job.status} · ${fullRunState.job.job_id}` : fullRunBusy ? 'Loading the saved clip prompts and checking admission.' : 'No job starts until you choose Start run.'}</span>
          <span>The Director uses the saved story settings and continues after each completed clip. No per-clip acceptance is required.</span>
          {fullRunSetup && <span>Duration: {fullRunSetup.duration_policy.kind === 'fixed' ? `${fullRunSetup.duration_policy.seconds}s` : `Director decides · ${fullRunSetup.duration_policy.min_seconds}–${fullRunSetup.duration_policy.max_seconds}s`} · {ALL_VIDEO_QUALITIES.find(item => item.key === fullRunSetup.video_quality)?.label} · {qualityDimensions(ALL_VIDEO_QUALITIES.find(item => item.key === fullRunSetup.video_quality)?.preset || 0.98, fullRunSetup.aspect_ratio || '16:9')} · <a href={`#/setup?workspace_id=${encodeURIComponent(fullRunWorkspace)}`}>Edit saved settings</a></span>}
          {fullRunState.run_state === 'not_started' && !fullRunState.prompt_plan_ready && <a href={`#/prompts?workspace_id=${encodeURIComponent(fullRunWorkspace)}`}>Prepare and save clip prompts before starting</a>}
          {fullRunState.run_state === 'not_started' && fullRunCapability?.available && !fullRunCapability.render_verified && <span>The first clip will verify this workflow’s live output. Valid clips continue automatically; generation or safety failures stop the run.</span>}
          {fullRunBusy && <span role="status">Loading reviewed prompts and queuing the run…</span>}
          {fullRunState.clips?.map((clip, index, clips) => <div key={clip.job.job_id}><span>Scene {clip.scene_number}, Shot {clip.shot_number}, Clip {clip.clip_number ?? 1} · {clip.state} · {clip.job.job_id}{clip.duration_seconds != null ? ` · ${clip.duration_seconds}s${clip.duration_reason ? ` · ${clip.duration_reason}` : ''}` : ''}</span>
            {view === 'take' && <RunClipLiveView job={clip.job} workspaceId={fullRunWorkspace}/>}
            {view === 'take' && clip.job.outputs?.filter(output => output.kind === 'video' && output.playback_url).map(output => <DockedVideo key={output.playback_url} src={output.playback_url!} label={`Scene ${clip.scene_number} Shot ${clip.shot_number} Clip ${clip.clip_number ?? 1}`}/>)}
            {clip.job.error && <span role="alert">{typeof clip.job.error === 'string' ? clip.job.error : clip.job.error.message}</span>}
            {clip.identity_review && <span role="status">Character visibility review · {clip.identity_review.state === 'complete' ? 'candidate observations ready' : clip.identity_review.state.replaceAll('_', ' ')}{clip.identity_review.error ? ` · ${clip.identity_review.error}` : ''}</span>}
            {clip.identity_review?.frames.map(frame => <span key={frame.sample_index}>Frame at {frame.timestamp_seconds.toFixed(1)}s · {frame.observations.length ? frame.observations.map(item => `${item.status.replaceAll('_', ' ')}${item.character_name ? `: ${item.character_name}` : ''}${item.visual_evidence ? ` — ${item.visual_evidence}` : ''}`).join(' · ') : 'No character observations'}</span>)}
            {clip.attempts && clip.attempts.length > 1 && <span>Attempts: {clip.attempts.map(attempt => `#${attempt.attempt_number} ${attempt.job.status}`).join(' · ')}</span>}
            {fullRunState.run_state === 'paused' && ['failed', 'cancelled', 'stale', 'recovery_required'].includes(clip.state) && index === clips.length - 1 && <button type="button" className="quiet-button" disabled={fullRunBusy || fullRunRefreshing} onClick={() => void retryFullRunShot(clip.scene_number, clip.shot_number, clip.clip_number ?? 1)}>{fullRunBusy ? 'Retrying…' : `Retry Scene ${clip.scene_number}, Shot ${clip.shot_number}, Clip ${clip.clip_number ?? 1}`}</button>}
          </div>)}
          {fullRunState.error && <span role="status">{fullRunState.error}</span>}
          {fullRunState.run_state === 'paused' && fullRunState.resume_available && <button type="button" className="quiet-button" disabled={fullRunBusy || fullRunRefreshing} onClick={() => void resumeFullRun()}>{fullRunBusy ? 'Resuming…' : 'Resume next-scene planning'}</button>}
          {fullRunCapability && !fullRunCapability.available && <div role="status"><span>{capabilityBlocker(fullRunCapability)}</span> <a className="text-button" href="#/status">Open Status</a>{capabilityDetails(fullRunCapability).length > 0 && <details><summary>Technical details</summary><small>{capabilityDetails(fullRunCapability).join(' ')}</small></details>}</div>}
          {fullRunCheckedAt && <span role="status">Status checked at {fullRunCheckedAt}. Refresh checks progress; it does not start another job.</span>}
          {fullRunError && <span role="alert">{fullRunError}</span>}
        </div>

      </section>}
      {view === 'take' && fullRunWorkspace && !fullRunState && fullRunError && <section className="card" aria-label="Fully automated run" role="alert">{fullRunError} <button type="button" className="quiet-button" onClick={() => void refreshFullRun()}>Refresh status</button></section>}
      {fullRunError && !fullRunWorkspace && <section className="card" role="alert">Fully automated run status could not be loaded: {fullRunError}</section>}
      {view === 'create' && fullRunWorkspace && <section className="card story-run-context" aria-label="Story automation">
        <b>{fullRunTitle} · Fully automated</b>
        <p>Open Current Take to start or manage this story’s run. The form below creates a separate video draft.</p>
        <a className="quiet-button" href={`#/take?workspace_id=${encodeURIComponent(fullRunWorkspace)}`}>Open Current Take</a>
      </section>}
      {(view === 'create' || (!fullRunWorkspace && !fullRunLoading)) && <>
      <ShotReferenceDirector refreshKey={`${libraryRefresh}:${active?.job.status || "none"}`} visible={visible && view === 'create' && !fullRunWorkspace} draft={draft} assets={r2vAssets} assetsReady={mediaWorkspaceId === draft.workspaceId && !assetsLoading && !assetsError} locked={formLocked || activeUnresolved} onChange={change=>{setDraft(change);setPreview(null);setCapability(null);setCapState('idle');}} onBusy={setPreparingShotPrompt} onAssetsChanged={()=>setLibraryRefresh(value=>value+1)}/>
      <AssistedClipPlanPanel visible={visible && view === 'create'} />
      <div className="layout-grid"><section className="composer-column"><div className="section-title"><div><h2>Create a video</h2></div><span className="mode-pill"><Sparkles size={13}/> {isFl2va ? 'First + last frame' : isR2v ? 'Reference to video' : 'Text to video'}</span></div>
        <div className="mode-switch"><button className={`mode-option ${!isFl2va&&!isR2v?'selected':''}`} onClick={() => { setDraft(p => ({...p, workflowId: WORKFLOW_ID})); setCapability(null); setCapState('idle'); setPreview(null); }} disabled={formLocked} aria-pressed={!isFl2va&&!isR2v}><Film size={16}/><span><b>Text to video</b><small>Prompt only</small></span>{!isFl2va&&!isR2v && <Check size={15} className="mode-check"/>}</button><button className={`mode-option ${isFl2va?'selected':''}`} onClick={() => { setDraft(p => ({...p, workflowId: FL2VA_WORKFLOW_ID})); setCapability(null); setCapState('idle'); setPreview(null); }} disabled={formLocked} aria-pressed={isFl2va}><Image size={16}/><span><b>First + last frame</b><small>Pick or upload both</small></span>{isFl2va && <Check size={15} className="mode-check"/>}</button><button className={`mode-option ${isR2v?'selected':''}`} onClick={() => { setDraft(p => ({...p, workflowId: R2V_WORKFLOW_ID, r2vMainPrompt: p.r2vMainPrompt ?? p.prompt, r2vCollatedPrompt: undefined})); setCapability(null); setCapState('idle'); setPreview(null); }} disabled={formLocked} aria-pressed={isR2v}><FolderOpen size={16}/><span><b>Reference to video</b><small>Combine image, video and audio</small></span>{isR2v && <Check size={15} className="mode-check"/>}</button></div>
        {view === 'create' && !isFl2va && !isR2v && <><div className="generation-footer" role="group" aria-label="Text to video mode"><button type="button" className="quiet-button" aria-pressed={!batchMode} onClick={()=>setBatchMode(false)}>Single prompt</button><button type="button" className="quiet-button" aria-pressed={batchMode} onClick={()=>setBatchMode(true)}>Batch prompts</button></div><T2VBatchPanel key={`batch-create:${draft.workspaceId}`} workspaceId={draft.workspaceId} showVideos={view === 'create'} editor={batchMode} disabled={busy || activeUnresolved || preparingShotPrompt} onActive={setBatchActive} onStarted={()=>{window.location.hash=`#/take?workspace_id=${encodeURIComponent(draft.workspaceId)}`;}}/></>}
        {(!batchMode || isFl2va || isR2v) && <>
        {isFl2va && <div className="card settings-card fl2va-frame-card"><div className="card-header"><div><h3>Frame images</h3><p>Choose a saved frame or add a PNG, JPEG, or WebP for either slot. Each upload keeps its assigned role in this workspace.</p></div><a className="text-button" href="#/media-prep?tool=search">Open Media Prep</a></div>
          {assetsLoading ? <p role="status">Loading workspace images…</p> : <>{assetsError&&<p role="alert">{imageLoadError?'Could not load frame images.':'Some library items could not load:'} {assetsError} <button onClick={()=>setLibraryRefresh(value=>value+1)}>Retry library load</button></p>}
            <div className="setting-grid">{([{role:'first_frame',label:'First frame',asset:firstFrame},{role:'last_frame',label:'Last frame',asset:lastFrame}] as const).map(({role,label,asset})=><div className="field fl2va-frame-slot" key={role}>
              <label htmlFor={role === 'first_frame' ? 'first-frame' : 'last-frame'}>{label}</label>
              <div className="select-wrap"><select id={role === 'first_frame' ? 'first-frame' : 'last-frame'} value={role === 'first_frame' ? draft.firstFrameAssetId || '' : draft.lastFrameAssetId || ''} disabled={formLocked} onChange={event => { setDraft(p=>({...p,[role === 'first_frame' ? 'firstFrameAssetId' : 'lastFrameAssetId']:event.target.value || undefined})); setPreview(null); }}><option value="">Choose {role === 'first_frame' ? 'first' : 'last'} frame…</option>{frameCandidates(role).map(candidate=><option value={candidate.asset_id} key={candidate.asset_id}>{frameOption(candidate, role)}</option>)}</select><ChevronDown size={15}/></div>
              {asset && <button type="button" className="quiet-button" disabled={formLocked} onClick={()=>{setDraft(p=>({...p,[role==='first_frame'?'firstFrameAssetId':'lastFrameAssetId']:undefined}));setPreview(null);}}>Clear {label.toLowerCase()}</button>}{asset && <div className="fl2va-frame-preview"><img src={asset.content_url} alt={`${label}: ${asset.filename}`}/><span>{asset.filename} · {label}</span></div>}
              <div className="fl2va-frame-upload" tabIndex={0} aria-label={`Drop or paste ${label.toLowerCase()} image`} onDragOver={event=>event.preventDefault()} onDrop={event=>dropFrameFile(event,role)} onPaste={event=>pasteFrameFile(event,role)}>
                <span>Drop or paste an image here</span>
                <label className="quiet-button r2v-upload-button">{uploadingFrameRole === role ? 'Adding…' : `Upload ${label.toLowerCase()}`}<input type="file" accept="image/png,image/jpeg,image/webp" aria-label={`Choose ${label.toLowerCase()} image`} disabled={formLocked} onChange={event=>{void uploadFrameFile(event.target.files?.[0],role);event.target.value='';}}/></label>
              </div>
            </div>)}</div>
            {errors.frames && <small className="error-text" role="alert">{errors.frames}</small>}{(!frameCandidates('first_frame').length || !frameCandidates('last_frame').length) && <p className="error-text">Choose each frame from this workspace or upload it directly into its matching slot.</p>}
          </>}
        </div>}
        {isFl2va && <MediaSourcePicker workspaceId={draft.workspaceId} kinds={['image']} disabled={formLocked} onAdded={items=>{setMediaAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items]);setLibraryRefresh(value=>value+1);}}/>}
        {isR2v && <div className="card settings-card r2v-reference-card"><div className="card-header"><div><h3>Reference assets</h3><p>Select library media and say how each should guide this clip. Files stay in the workspace library.</p></div><a className="text-button" href="#/media-prep?tool=search">Open Media Prep</a></div>
          <ReferenceReview key={`${draft.workspaceId}:${draft.clipId}`} draft={draft} assets={r2vAssets} locked={formLocked} onChange={change=>{setDraft(change);setPreview(null);}}/>
          {assetsLoading ? <p role="status">Loading workspace references…</p> : <>{assetsError&&<div role="alert"><p>Some project references could not load: {assetsError}</p><button type="button" className="quiet-button" onClick={()=>setLibraryRefresh(value=>value+1)}>Retry library load</button></div>}
            {([
              {title:'Images', items:[
                {key:'characters' as const,title:'Characters',kind:'images' as const,singular:'character image',accept:'image/png,image/jpeg,image/webp',matches:(a:MediaAsset)=>(a.roles.includes('character_master')&&(!a.metadata?.production_image_job?.settings?.lineage?.screenplay_revision_id||currentImageIds.has(a.asset_id)))||a.roles.includes('character_view')},
                {key:'worlds' as const,title:'Worlds',kind:'images' as const,singular:'world image',accept:'image/png,image/jpeg,image/webp',matches:(a:MediaAsset)=>(a.roles.includes('world_master')&&(!a.metadata?.production_image_job?.settings?.lineage?.screenplay_revision_id||currentImageIds.has(a.asset_id)))||a.roles.includes('world_view')},
                {key:'first-frames' as const,title:'First Frames',kind:'images' as const,singular:'first-frame image',accept:'image/png,image/jpeg,image/webp',matches:(a:MediaAsset)=>(a.roles.includes('first_frame')&&(!a.metadata?.production_image_job?.settings?.lineage?.screenplay_revision_id||currentImageIds.has(a.asset_id)))},
                {key:'last-frames' as const,title:'Last Frames',kind:'images' as const,singular:'last-frame image',accept:'image/png,image/jpeg,image/webp',matches:(a:MediaAsset)=>(a.roles.includes('last_frame')&&(!a.metadata?.production_image_job?.settings?.lineage?.screenplay_revision_id||currentImageIds.has(a.asset_id)))},
                {key:'image-assets' as const,title:'Image Assets',kind:'images' as const,singular:'extracted image',accept:'image/png,image/jpeg,image/webp',matches:isAnalyzedReference},
                {key:'imported-images' as const,title:'Downloaded / imported images',kind:'images' as const,singular:'image',accept:'image/png,image/jpeg,image/webp',matches:(a:MediaAsset)=>a.origin==='imported'&&!isAnalyzedReference(a)},
              ]},
              {title:'Audio', items:[
                {key:'voices' as const,title:'Voice Files',kind:'audios' as const,singular:'voice',accept:'audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/flac,audio/aac',matches:(a:MediaAsset)=>a.roles.includes('voice_master')||a.audio_category==='voice'||!!a.metadata?.comfyui_voice_catalog},
                {key:'audio-clips' as const,title:'Audio Assets',kind:'audios' as const,singular:'audio clip',accept:'audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/flac,audio/aac',matches:(a:MediaAsset)=>isAnalyzedReference(a)||a.origin==='generated'},
                {key:'imported-audio' as const,title:'Downloaded / imported audio',kind:'audios' as const,singular:'audio file',accept:'audio/*',matches:(a:MediaAsset)=>a.origin==='imported'&&!isAnalyzedReference(a)},
              ]},
              {title:'Videos', items:[
                {key:'video-clips' as const,title:'Video Assets',kind:'videos' as const,singular:'video clip',accept:'video/mp4,video/quicktime,video/x-matroska,video/webm',matches:(a:MediaAsset)=>isAnalyzedReference(a)||a.origin==='generated'},
                {key:'source-videos' as const,title:'Downloaded / imported videos',kind:'videos' as const,singular:'video',accept:'video/*',matches:(a:MediaAsset)=>a.origin==='imported'&&!isAnalyzedReference(a)},
              ]},
            ]).map(group => <details className="r2v-kind" key={group.title} open>
              <summary className="r2v-kind-summary">{group.title}</summary>
              <label className="field">Reference source<select aria-label={group.title+' reference source'} value={r2vSource[group.title]} onChange={event=>{setR2vSource(current=>({...current,[group.title]:event.target.value}));setR2vCatalogueOffset(current=>({...current,[group.title]:0}));setR2vPickerSelection({});}}><optgroup label="Current project"><option value={'workspace:'+draft.workspaceId}>All media in this project</option>{group.items.map(item=><option key={item.key} value={item.key}>{item.title}</option>)}</optgroup><optgroup label="Shared library"><option value="global:all">All projects and shared media</option><option value="global:downloaded">YouTube downloads</option><option value="global:repertoire">Video repertoire</option><option value="global:generated">Generated media</option>{group.title==='Audio'&&<option value="global:ace_generated">ACE-Step generated audio</option>}<option value="global:imported">Imported files</option></optgroup><optgroup label="Workspaces">{[...new Set([...workspaceChoices.map(row=>row.id),...r2vWorkspaceIds])].map(id=><option key={id} value={'workspace:'+id}>{r2vWorkspaceNames[id]||workspaceChoices.find(row=>row.id===id)?.label||id}</option>)}</optgroup></select></label>
              {group.items.filter((item,index)=>item.key===r2vSource[group.title] || (index===0 && /^(global|workspace):/.test(r2vSource[group.title]))).map(item => {
                const {key,title,kind,singular,accept,matches}=item;
                const remote=/^(global|workspace):/.test(r2vSource[group.title]);
                const query=r2vSearch[key]||''; const mode=remote?'keyword':r2vSearchMode[key]||'keyword'; const sort=r2vSort[key]||'newest';
                const picked=r2vPickerSelection[key]||[]; const rows=r2vRefs[kind]; const max=kind==='images'?9:3; const used=rows.length;
                const selectedIds=new Set([...r2vRefs.images,...r2vRefs.videos,...r2vRefs.audios].map(ref=>ref.assetId));
                const sourceAssets=remote?(r2vCatalogue[group.title]?.assets||[]):r2vAssets;
                const pool=sourceAssets.filter(asset=>asset.kind===(kind==='images'?'image':kind==='videos'?'video':'audio')&&(remote||matches(asset)||(asset.recommendation_source==='production_style'&&['characters','worlds','first-frames','last-frames','audio-clips','video-clips'].includes(key)))&&!selectedIds.has(asset.asset_id));
                const pinned=pool.filter(asset=>asset.recommendation_source==='production_style').sort((a,b)=>b.created_at.localeCompare(a.created_at));
                const matching=[...pinned,...rankMediaAssets(pool.filter(asset=>asset.recommendation_source!=='production_style'),remote||mode==='keyword'?query:'',sort,activeR2vSeoStyle)];
                const available=!remote&&mode==='semantic'?(r2vSemanticQueries[key]===query.trim()?[...pinned,...(r2vSemanticIds[key]||[]).map(id=>r2vAssets.find(asset=>asset.asset_id===id)).filter((asset):asset is MediaAsset=>!!asset&&matches(asset)&&asset.kind===(kind==='images'?'image':kind==='videos'?'video':'audio')&&!selectedIds.has(asset.asset_id)&&asset.recommendation_source!=='production_style')]:[]):matching;
                const sameKindKeys: R2vCarouselKey[]=kind==='images'?['characters','worlds','first-frames','last-frames','image-assets','imported-images']:kind==='audios'?['voices','audio-clips','imported-audio']:['video-clips','source-videos'];
                const pending=sameKindKeys.reduce((total,pickerKey)=>total+(r2vPickerSelection[pickerKey]||[]).length,0);
                return <section className="r2v-subcarousel" key={key} onDragOver={event=>event.preventDefault()} onDrop={event=>dropR2vFiles(event,kind,key)}>
                  <h4>{remote?group.title:title}<small>{used}/{max} {kind==='images'?'images':kind==='videos'?'videos':'audio references'} in request</small></h4>
                  <div className="r2v-kind-head"><div className="r2v-add">
                    <input className="r2v-search" aria-label={'Search '+title.toLowerCase()} placeholder={mode==='semantic'?'Describe '+title.toLowerCase()+' to find':'Search '+title.toLowerCase()+' by name or tags'} value={query} onChange={event=>{setR2vSearch(current=>({...current,[key]:event.target.value}));setR2vCatalogueOffset(current=>({...current,[group.title]:0}));}}/>
                    <select disabled={remote} aria-label={'Search '+title.toLowerCase()+' by'} value={mode} onChange={event=>setR2vSearchMode(current=>({...current,[key]:event.target.value as 'keyword'|'semantic'}))}><option value="keyword">Name and tags</option><option value="semantic">Semantic</option></select>
                    {mode==='semantic'&&<button type="button" className="quiet-button" disabled={!!r2vSemanticBusy[key]||!query.trim()} onClick={()=>void searchR2vSemantically(key,kind)}>{r2vSemanticBusy[key]?'Searching…':'Search'}</button>}
                    <select aria-label={'Rank '+title.toLowerCase()+' by SEO style'} value={r2vSeoStyleId} onChange={event=>setR2vSeoStyleId(event.target.value)}><option value="">Default ranking</option>{r2vSeoStyles.map(style=><option key={style.style_id} value={style.style_id}>{style.name}</option>)}</select>
                    <button type="button" className="quiet-button media-sort" onClick={()=>setR2vSort(current=>({...current,[key]:sort==='newest'?'oldest':'newest'}))} aria-label={'Sort '+title.toLowerCase()+' '+(sort==='newest'?'oldest first':'newest first')} title={sort==='newest'?'Oldest first':'Newest first'}>{sort==='newest'?'↓':'↑'}</button>
                    <label className="quiet-button r2v-upload-button">{uploadingRefs?'Adding…':'Upload '+singular}<input type="file" accept={accept} multiple disabled={formLocked} onChange={event=>{void uploadR2vFiles(Array.from(event.target.files||[]),kind,key);event.target.value='';}}/></label>
                  </div>{mode==='semantic'&&<small>Semantic search uses saved annotations and indexed media content. Content search requires completed indexing.</small>}</div>
                  {remote&&r2vCatalogueBusy[group.title]&&<p role="status">Loading source…</p>}
                  {remote&&r2vCatalogueError[group.title]&&<p role="alert">{r2vCatalogueError[group.title]} <button type="button" onClick={()=>setLibraryRefresh(value=>value+1)}>Retry</button></p>}
                  <SelectionToggle selected={picked} shown={available.map(asset=>asset.asset_id)} disabled={formLocked||(remote&&(!!r2vCatalogueBusy[group.title]||!!r2vCatalogueError[group.title]))} capacity={max} occupied={used+pending-picked.length} onChange={ids=>setR2vPickerSelection(current=>({...current,[key]:ids}))}/>
                  <div className="r2v-asset-carousel" aria-label={title+' reference carousel'}>
                    {(!remote||!r2vCatalogueBusy[group.title]&&!r2vCatalogueError[group.title])&&available.map(asset=><article className={'r2v-asset-card'+(picked.includes(asset.asset_id)?' selected':'')} key={asset.asset_id}>
                      <button type="button" className="r2v-asset-pick" aria-pressed={picked.includes(asset.asset_id)} disabled={formLocked} onClick={()=>toggleR2vPickerAsset(key,asset.asset_id,selectedIds)}>
                        <span className="r2v-asset-selection" aria-hidden="true">{picked.includes(asset.asset_id)?'☑':'☐'}</span><span className="r2v-asset-preview">{asset.kind==='image'?<img src={asset.content_url} alt="" loading="lazy"/>:asset.kind==='video'?<video src={asset.content_url} muted loop playsInline preload="metadata" onMouseEnter={event=>void event.currentTarget.play().catch(()=>{})} onMouseLeave={event=>{event.currentTarget.pause();event.currentTarget.currentTime=0;}}/>:<AudioLines/>}</span>
                        <span className="r2v-asset-name" title={asset.filename}>{asset.recommendation_source==='production_style'?'Recommended · ':''}{asset.filename}</span>
                        <small>{asset.audio_category||asset.roles.slice(0,2).join(' · ')||asset.description||'Reference media'}</small>
                      </button>{asset.kind==='video'&&<video className="r2v-asset-video" src={asset.content_url} controls playsInline preload="metadata" aria-label={'Play '+asset.filename}/>} {asset.kind==='audio'&&<audio className="r2v-asset-audio" src={asset.content_url} controls preload="metadata" aria-label={'Play '+asset.filename}/>}
                    </article>)}
                    {!available.length&&<p className="r2v-empty">{query?'No matching media.':'No media in this carousel yet.'}</p>}
                  </div>
                  {remote&&<div className="r2v-carousel-footer"><button type="button" className="quiet-button" disabled={r2vCatalogueBusy[group.title]||!(r2vCatalogueOffset[group.title]||0)} onClick={()=>setR2vCatalogueOffset(current=>({...current,[group.title]:Math.max(0,(current[group.title]||0)-24)}))}>Previous</button><span>{r2vCatalogue[group.title]?.total||0} items</span><button type="button" className="quiet-button" disabled={r2vCatalogueBusy[group.title]||(r2vCatalogueOffset[group.title]||0)+24>=(r2vCatalogue[group.title]?.total||0)} onClick={()=>setR2vCatalogueOffset(current=>({...current,[group.title]:(current[group.title]||0)+24}))}>Next</button></div>}
                  <div className="r2v-carousel-footer"><span>{picked.length} selected · {Math.max(0,max-used-pending)} slots remaining{used+pending>max?' · deselect extras before adding':''}</span><button type="button" className="generate-button" disabled={formLocked||!picked.length||(remote&&(!!r2vCatalogueBusy[group.title]||!!r2vCatalogueError[group.title]))} onClick={()=>addSelectedR2vRefs(key,kind)}>Add selected {singular}{picked.length===1?'':'s'}</button></div>
                </section>;
              })}
              {group.title==='Images'&&r2vRefs.images.length>0&&<div className="r2v-reference-tray" aria-label="Image references for this clip">{r2vRefs.images.map((ref,index)=>{const asset=assetForRef(ref);const label='image reference '+(index+1);return <article className="r2v-ref-row" key={ref.assetId}><div className="r2v-ref-media">{asset&&<img src={asset.content_url} alt={asset.filename}/>}</div><div className="r2v-ref-fields"><b>{asset?.filename||'Missing image asset'}</b><label>Role<input aria-label={label+' role'} value={ref.role} disabled={formLocked} onChange={event=>updateR2vRef('images',index,{role:event.target.value})}/></label><SelectionMicroEdit label={label+' instruction'} value={ref.intent} surface="prompt" workspaceId={draft.workspaceId} revisionId={draft.sourceLineage?.screenplay_revision_id||draft.clipId} fieldKey={'video.'+draft.clipId+'.reference.images.'+ref.assetId+'.intent'} disabled={formLocked} onChange={value=>updateR2vRef('images',index,{intent:value})}/></div><button type="button" className="quiet-button" disabled={formLocked} onClick={()=>removeR2vRef('images',index)}>Remove</button></article>})}</div>}
              {group.title==='Audio'&&r2vRefs.audios.length>0&&<div className="r2v-reference-tray" aria-label="Audio references for this clip">{r2vRefs.audios.map((ref,index)=>{const asset=assetForRef(ref);const label='audio reference '+(index+1);return <article className="r2v-ref-row" key={ref.assetId}><div className="r2v-ref-media">{asset&&<audio src={asset.content_url} controls preload="metadata" aria-label={asset.filename}/>}</div><div className="r2v-ref-fields"><b>{asset?.filename||'Missing audio asset'}</b><label>Role<input aria-label={label+' role'} value={ref.role} disabled={formLocked} onChange={event=>updateR2vRef('audios',index,{role:event.target.value})}/></label><SelectionMicroEdit label={label+' instruction'} value={ref.intent} surface="prompt" workspaceId={draft.workspaceId} revisionId={draft.sourceLineage?.screenplay_revision_id||draft.clipId} fieldKey={'video.'+draft.clipId+'.reference.audios.'+ref.assetId+'.intent'} disabled={formLocked} onChange={value=>updateR2vRef('audios',index,{intent:value})}/></div><button type="button" className="quiet-button" disabled={formLocked} onClick={()=>removeR2vRef('audios',index)}>Remove</button></article>})}</div>}
              {group.title==='Videos'&&r2vRefs.videos.length>0&&<div className="r2v-reference-tray" aria-label="Video references for this clip">{r2vRefs.videos.map((ref,index)=>{const asset=assetForRef(ref);const label='video reference '+(index+1);return <article className="r2v-ref-row" key={ref.assetId}><div className="r2v-ref-media">{asset&&<video src={asset.content_url} controls preload="metadata" aria-label={asset.filename}/>}</div><div className="r2v-ref-fields"><b>{asset?.filename||'Missing video asset'}</b><label>Role<input aria-label={label+' role'} value={ref.role} disabled={formLocked} onChange={event=>updateR2vRef('videos',index,{role:event.target.value})}/></label><SelectionMicroEdit label={label+' instruction'} value={ref.intent} surface="prompt" workspaceId={draft.workspaceId} revisionId={draft.sourceLineage?.screenplay_revision_id||draft.clipId} fieldKey={'video.'+draft.clipId+'.reference.videos.'+ref.assetId+'.intent'} disabled={formLocked} onChange={value=>updateR2vRef('videos',index,{intent:value})}/><label>Start seconds (optional)<input type="number" min="0" step="0.1" aria-label={label+' start seconds'} value={ref.startSec??''} disabled={formLocked} onChange={event=>updateR2vRef('videos',index,{startSec:event.target.value===''?undefined:Number(event.target.value)})}/></label><label>End seconds (optional)<input type="number" min="0.1" max="15" step="0.1" aria-label={label+' end seconds'} value={ref.endSec??''} disabled={formLocked} onChange={event=>updateR2vRef('videos',index,{endSec:event.target.value===''?undefined:Number(event.target.value)})}/></label><label className="r2v-check"><input type="checkbox" checked={ref.includePairedSoundtrack===true} disabled={formLocked} onChange={event=>updateR2vRef('videos',index,{includePairedSoundtrack:event.target.checked})}/> Also use this video’s soundtrack</label>{ref.includePairedSoundtrack&&<SelectionMicroEdit label={label+' soundtrack direction'} value={ref.audioIntent||''} surface="prompt" workspaceId={draft.workspaceId} revisionId={draft.sourceLineage?.screenplay_revision_id||draft.clipId} fieldKey={'video.'+draft.clipId+'.reference.videos.'+ref.assetId+'.soundtrack'} disabled={formLocked} multiline={false} onChange={value=>updateR2vRef('videos',index,{audioIntent:value})}/>}</div><button type="button" className="quiet-button" disabled={formLocked} onClick={()=>removeR2vRef('videos',index)}>Remove</button></article>})}</div>}
            </details>)}
            <div className="r2v-limit-note">Drop files into the matching section or paste copied media anywhere on this page. The local MiniMax H3 R2V request allows up to 9 images, 3 videos and 3 audio references. Counts are shared across sources of the same media type. Each video excerpt can be up to 15 seconds; a video soundtrack is an additional audio reference.</div>
          </>}
          {errors.r2v && <small className="error-text" role="alert">{errors.r2v}</small>}
        </div>}
        {isR2v && <div className="generation-footer r2v-collate"><span>Tags and reference order are assigned from the selected assets.</span><button type="button" className="quiet-button" onClick={collateR2vPrompt} disabled={formLocked || !r2vMainPrompt.trim() || !r2vTotalRefs}>Collate prompt</button></div>}
        <div className="card prompt-card"><div className="card-header"><div><b>{isR2v ? 'Main shot prompt' : 'Shot prompt'}</b><p>{isR2v ? 'Describe the new clip; reference instructions are added when you collate.' : 'Describe the action and camera movement.'}</p></div><div className="prompt-meta">{draft.sourceLineage && <button type="button" className="quiet-button" onClick={() => void prepareCurrentShotPrompt()} disabled={formLocked || preparingShotPrompt}>{preparingShotPrompt ? 'Preparing…' : draft.sourceLineage?.board_revision ? 'Edit storyboard shot' : draft.sourceLineage?.planned_clip_id ? 'Restore planned prompt' : 'Prepare from screenplay'}</button>}<span className="saved"><span className="status-dot green"/> Auto-saved</span></div></div>
          {draft.sourceLineage && <small className="prompt-source-note">Shows the selected clip’s workflow-aware prompt. You can edit it here; restoring a planned prompt preserves its source coverage and your reference choices.</small>}
          <SelectionMicroEdit label={isR2v ? 'Main shot prompt' : 'Shot prompt'} value={isR2v ? (draft.r2vMainPrompt ?? draft.prompt) : draft.prompt} surface="prompt" workspaceId={draft.workspaceId} revisionId={draft.sourceLineage?.screenplay_revision_id || draft.clipId} fieldKey={`video.${draft.clipId}.${isR2v ? 'main-prompt' : 'prompt'}`} disabled={formLocked || preparingShotPrompt} onChange={value => { if (isR2v) setDraft(p => ({ ...p, r2vMainPrompt: value, r2vCollatedPrompt: undefined })); else setDraft(p => ({ ...p, prompt: value })); setPreview(null); }}/>
          <div className="prompt-footer"><div className="annotation-row"/><div className="prompt-meta"><span id="prompt-help" className="sr-only">Describe the video to generate.</span><span id="prompt-count" className={effectivePromptLength >= 7000 ? 'count error-text' : 'count'}>{(isR2v ? unicodeLength(draft.r2vMainPrompt ?? draft.prompt) : promptLength).toLocaleString()} / 6,999</span></div></div>
          {errors.prompt && draft.prompt && <div className="inline-error" role="alert">{errors.prompt}</div>}
        </div>
        {isR2v && r2vFinalPrompt && <div className="card prompt-card"><div className="card-header"><div><b>Final prompt</b><p>Review the generated tags and edit the exact text before previewing.</p></div><span className="prompt-meta">{effectivePromptLength.toLocaleString()} / 6,999</span></div><SelectionMicroEdit label="Final prompt" value={r2vFinalPrompt} surface="prompt" workspaceId={draft.workspaceId} revisionId={draft.sourceLineage?.screenplay_revision_id || draft.clipId} fieldKey={`video.${draft.clipId}.collated-prompt`} disabled={formLocked} onChange={value=>{setDraft(prev=>({...prev,r2vCollatedPrompt:value}));setPreview(null);}}/><small>Image, video and audio tags are numbered independently. Editing reference choices clears this collation.</small>{errors.prompt && <small className="error-text" role="alert">{errors.prompt}</small>}</div>}
        <div className="card settings-card"><div className="card-header"><div><h3>Output settings</h3></div><button className="collapse-button" onClick={() => setShowAdvanced(s => !s)} aria-expanded={showAdvanced}>Advanced <ChevronDown size={15} className={showAdvanced?'rotated':''}/></button></div>
          <div className="setting-grid"><div className="field"><label htmlFor="duration">Duration</label><div className="select-wrap"><select id="duration" value={draft.duration} disabled={formLocked} onChange={e => {setDraft(p => ({ ...p, duration: Number(e.target.value) }));setPreview(null);}}>{Array.from({length:isFl2va||isR2v?11:26}, (_,i) => i+5).map(n => <option value={n} key={n}>{n} seconds</option>)}</select><ChevronDown size={15}/></div>{draft.sourceLineage?.planned_clip_id && <small>Suggested by the screenplay plan; change it as needed.</small>}{errors.duration && <small className="error-text">{errors.duration}</small>}</div><div className="field"><label htmlFor="resolution">Final quality · Turbo + LTX</label><div className="select-wrap"><select id="resolution" value={draft.resolution} disabled={formLocked} onChange={e => {setDraft(p => ({ ...p, resolution: Number(e.target.value) as VideoResolution }));setPreview(null);}}>{!T2V_QUALITIES.some(item => item.preset === draft.resolution) && <option value={draft.resolution}>Legacy · {qualityDimensions(draft.resolution, draft.aspectRatio)}</option>}{T2V_QUALITIES.map(item => <option key={item.key} value={item.preset}>{item.label} · {qualityDimensions(item.preset, draft.aspectRatio)}</option>)}</select><ChevronDown size={15}/></div></div><div className="field"><label htmlFor="aspect-ratio">Aspect ratio</label><div className="select-wrap"><select id="aspect-ratio" value={draft.aspectRatio || '16:9'} disabled={formLocked} onChange={e => {setDraft(p => ({...p, aspectRatio: e.target.value as VideoAspectRatio}));setPreview(null);}}>{VIDEO_ASPECT_RATIOS.map(item => <option key={item.value} value={item.value}>{item.value} · {item.label}</option>)}</select><ChevronDown size={15}/></div><small>Dimensions align to the model’s 32-pixel grid.</small></div></div>
          {showAdvanced && <div className="advanced-row"><span>Steps <b>{'Turbo 4 → LTX 3'}</b></span><span>Seed <b>1</b></span><span>References <b>{isR2v?`${r2vRefs.images.length} pictures · ${r2vRefs.videos.length} videos · ${r2vRefs.audios.length} audio`:isFl2va?'First + last frame':'None'}</b></span><small>{isR2v?'Pinned workflow defaults':'Fixed settings'}</small></div>}
        </div>
        <div className="video-readiness card"><div className="small-heading">LOCAL ENGINE <span className={`status-dot ${capState==='ready'?'green':capState==='unavailable'?'red':''}`}/></div><p>{capState==='ready' ? 'Ready to generate' : capState==='loading' ? 'Checking readiness…' : capState==='unavailable' ? capability ? capabilityBlocker(capability) : 'Video generation is not ready. Check Status for setup details.' : 'Not checked yet'}</p>{capState==='ready' && capability?.workflow_id===R2V_WORKFLOW_ID && capability.render_verified===false && <p>Ready for your first R2V test. A successful video with audio must be recorded before automated R2V is enabled.</p>}{capState==='unavailable' && <a className="text-button" href="#/status">Open Status</a>}{capState==='unavailable' && capability && capabilityDetails(capability).length > 0 && <details><summary>Technical details</summary><small>{capabilityDetails(capability).join(' ')}</small></details>}<button className="text-button" onClick={refreshCapability} disabled={capState==='loading' || busy}><Activity size={14}/> Check readiness</button></div>
        {preview && <div className="card snapshot"><div className="snapshot-head"><div><span className="eyebrow">PREVIEW ONLY</span><b>Validated request</b></div><span>{preview.workflow_id}</span></div><div className="snapshot-tags"><span>{preview.compiled?.predicted_duration_seconds ?? preview.request?.duration_seconds ?? draft.duration}s</span><span>{preview.compiled?.final_width ?? preview.compiled?.width ?? ALL_VIDEO_QUALITIES.find(item => item.preset === draft.resolution)!.width} × {preview.compiled?.final_height ?? preview.compiled?.height ?? ALL_VIDEO_QUALITIES.find(item => item.preset === draft.resolution)!.height}</span><span>{preview.compiled?.frame_count ? `${preview.compiled.frame_count} frames` : isR2v?`${r2vTotalRefs} references`:'Prompt compiled'}</span></div>{isR2v && <pre className="r2v-preview-map">{JSON.stringify(preview.reference_map,null,2)}</pre>}<small>No job submitted.</small></div>}
        {view === 'create' && message && <div className="notice notice-warn" role="status" aria-label="Generation feedback"><span>{message}</span><button type="button" onClick={() => setMessage('')} aria-label="Dismiss"><X size={15}/></button></div>}
        <div className="generation-footer"><button className="quiet-button" onClick={preparePreview} disabled={busy || !!errors.prompt || !!errors.duration || !!errors.frames || !!errors.r2v || hasPendingAttempt}>Preview settings</button><button className="generate-button" onClick={generate} disabled={busy || !!errors.prompt || !!errors.duration || !!errors.frames || !!errors.r2v || capState!=='ready' || activeUnresolved || (batchActive && !isFl2va && !isR2v)}>{busy ? <><LoaderCircle size={16} className="spin"/> Preparing…</> : hasPendingAttempt ? <><RefreshCw size={16}/> Recover saved attempt</> : <><Sparkles size={16}/> Generate video <ArrowRight size={16}/></>}</button></div>
        {hasPendingAttempt && <div className="notice notice-warn" role="status"><span>A previous submission needs checking. Return to editing will recover an existing job or safely release the unsubmitted attempt, keeping your prompt and references.</span><button type="button" disabled={busy} onClick={() => void returnToEditing()}>Return to editing</button></div>}
        </>}
      </section>
      <aside className="result-column"><div className="section-title result-title"><div><h2>Current take</h2><p>Job status and output for this draft.</p></div><button className="icon-button" aria-label="Refresh job" disabled={!active} onClick={() => active && getJob(active.job.job_id).then(job => setActive({ ...active, job })).catch(() => setMessage('Could not refresh job status.'))}><RefreshCw size={16}/></button></div>
        {view !== 'take' && <div className={`preview card ${isReviewableOutput && playback ? 'has-video' : ''}`}>{isReviewableOutput && playback ? <video controls playsInline src={playback} aria-label="Generated video"/> : <div className="preview-empty"><div className="preview-icon">{active ? ['recovery_required','submission_unknown'].includes(active.job.status) ? <Activity size={24}/> : <LoaderCircle size={24} className={['queued','running','submitting','reconciling','refinement_pending'].includes(active.job.status)?'spin':''}/> : <Play size={23}/>}</div><b>{active ? active.job.status === 'needs_review' ? 'Ready to review' : active.job.status === 'accepted' ? 'Take accepted' : active.job.status === 'failed' ? 'Generation failed' : active.job.status === 'stale' ? 'Job is stale' : active.job.status === 'cancelled' ? 'Job was cancelled' : active.job.status === 'rejected' ? 'Job was rejected' : ['recovery_required','submission_unknown','reconciling'].includes(active.job.status) ? 'Recovery required' : ['queued','running','submitting'].includes(active.job.status) ? 'Rendering your shot' : `Status: ${active.job.status}` : 'Your video preview'}</b><span>{active ? (active.job.error && typeof active.job.error==='object' ? active.job.error.message : '') || (isReviewableOutput ? 'This job is reviewable, but the backend did not return a playable output URL.' : ['recovery_required','submission_unknown','reconciling'].includes(active.job.status) ? 'The backend is reconciling this saved job. No new job will be submitted.' : active.job.status === 'stale' ? 'The backend marked this job stale. Its request is preserved; no completed output is confirmed.' : active.job.status === 'cancelled' ? 'The backend confirmed cancellation. No completed output is confirmed.' : active.job.status === 'rejected' ? 'The backend rejected this job. Its request remains available in history.' : `Job ${active.job.job_id}`) : 'Your generated video will appear here.'}</span>{active && !isTerminalStatus(active.job.status) && <div className="progress-track"><span className={typeof active.job.progress?.fraction === 'number' ? '' : 'indeterminate'} style={typeof active.job.progress?.fraction === 'number' ? { width: `${Math.max(0,Math.min(100,active.job.progress.fraction*100))}%` } : undefined}/></div>}</div>}<div className="preview-controls"><span><span className={`status-dot ${isReviewableOutput?'green':''}`}/>{statusLabel}</span>{active?.job.attempt && <span>Take {active.job.attempt}</span>}</div></div>}
        {view === 'take' && active && <div className="take-job-status" role="status" aria-label="Current job status">
            <div><b>{active.job.outputs?.some(output => output.kind === 'video' && output.available === false) ? 'Video file missing' : active.job.status === 'refinement_pending' ? 'Waiting for LTX video refinement' : active.job.pipeline?.stage === 'ltx_refinement' && !isTerminalStatus(active.job.status) ? 'Refining final video with LTX' : active.job.status === 'queued' ? 'Queued for generation' : ['running','submitting'].includes(active.job.status) ? 'Rendering your shot' : active.job.status === 'needs_review' ? 'Ready to review' : active.job.status === 'accepted' ? 'Take accepted' : ['recovery_required','submission_unknown','reconciling'].includes(active.job.status) ? 'Recovering saved job' : active.job.status === 'failed' ? 'Generation failed' : `Job ${active.job.status.replaceAll('_',' ')}`}</b><span>Job {active.job.job_id} · {active.job.progress?.phase || (isTerminalStatus(active.job.status) ? 'Latest saved result' : 'Progress refreshes automatically')}</span></div>
            {active.job.error && <p role="alert">{typeof active.job.error === 'string' ? active.job.error : active.job.error.message || 'The render stopped without a completed video. Check Status before retrying.'}</p>}
            {!isTerminalStatus(active.job.status) && <div className="progress-track" aria-label="Generation progress"><span className={typeof active.job.progress?.fraction === 'number' ? '' : 'indeterminate'} style={typeof active.job.progress?.fraction === 'number' ? { width: `${Math.max(0,Math.min(100,active.job.progress.fraction*100))}%` } : undefined}/></div>}
          </div>}
        {view === 'take' && <TakeReviewSection><section className="take-gallery card" aria-label="Generated video clips">
          <h3>Generated clips</h3>
          {takeClips.length ? <>
            <div className="take-clip-carousel" role="list" aria-label="Generated video clips carousel">
              {takeClips.map(clip => <TakeClipCard key={clip.job.job_id} clip={clip} selected={selectedTakeClip?.job.job_id === clip.job.job_id} onSelect={() => setSelectedTakeJobId(clip.job.job_id)} />)}
            </div>
            {selectedTakeClip && <div className="take-selected-preview">
              <div className="take-player-frame">
                <button type="button" className="take-browse-arrow take-browse-previous" aria-label="View previous clip" disabled={takeClips.indexOf(selectedTakeClip)===0} onClick={()=>setSelectedTakeJobId(takeClips[takeClips.indexOf(selectedTakeClip)-1].job.job_id)}>‹</button>
                <DockedVideo src={selectedTakeClip.playbackUrl} label={`Play take ${selectedTakeClip.job.attempt || ''}`} />
                <button type="button" className="take-browse-arrow take-browse-next" aria-label="View next clip" disabled={takeClips.indexOf(selectedTakeClip)===takeClips.length-1} onClick={()=>setSelectedTakeJobId(takeClips[takeClips.indexOf(selectedTakeClip)+1].job.job_id)}>›</button>
              </div>
              <p className="take-player-caption">Clip {takeClips.indexOf(selectedTakeClip)+1} of {takeClips.length} · Take {selectedTakeClip.job.attempt || 1}</p>
            </div>}
          </> : <p>No generated clips are ready to play yet.</p>}
        {isReviewableOutput && <div className="review-actions">{needsReview && <button className="accept-button" onClick={markAccepted} disabled={busy}><Check size={16}/> Accept take</button>}<button className="retake-button" onClick={() => { setRetakeKeep(true); setRetakeDialog(true); }} disabled={busy}><RefreshCw size={15}/> Retake</button><button className="retake-button" onClick={() => void advanceToNext()} disabled={busy}>{busy ? 'Loading…' : draft.sourceLineage ? 'Next clip' : 'Next video'} <ArrowRight size={15}/></button><span>{needsReview ? 'Accept records this clip for later assembly. Next clip accepts it and loads the next saved screenplay prompt.' : 'Retake keeps this prompt; Next clears clip references and loads the next prompt.'}</span></div>}
        {active?.job.status === 'accepted' && <div className="accepted-status"><Check size={15}/> Accepted and saved</div>}
        </section></TakeReviewSection>}
        {view === 'take' && selectedTakeClip && <details className="card"><summary>Selected take prompt · Take {selectedTakeClip.job.attempt || '—'}</summary><p style={{whiteSpace:'pre-wrap'}}>{selectedTakeClip.snapshot.prompt}</p></details>}
        {view === 'take' && history.length > 0 && <details className="history-list card"><summary>Previous take details · {history.length}</summary>{history.map(item => <article className="history-item" key={item.job.job_id}><b>Take {item.job.attempt || '—'} · {item.snapshot.duration_seconds}s</b><p>{item.snapshot.prompt}</p></article>)}</details>}
        {view === 'take' && draft.sourceLineage && <TakeReviewSection><AssemblyPreviewPanel/></TakeReviewSection>}
        {active && activeRequest && <div className="snapshot card"><div className="snapshot-head"><div><span className="eyebrow">SAVED REQUEST</span><b>Submitted prompt</b></div><span className="snapshot-lock">Frozen</span></div><p>{activeRequest.prompt}</p><div className="snapshot-tags"><span>{activeRequest.duration_seconds}s</span><span>{qualityDimensions(activeRequest.resolution_preset, activeRequest.aspect_ratio)}</span><span>{activeRequest.aspect_ratio}</span><span>Seed 1</span></div>{active.job.source_lineage?.knowledge_ref && <small>Prompt guidance · {active.job.source_lineage.knowledge_ref.knowledge_id} · v{active.job.source_lineage.knowledge_ref.guidance_version}</small>}{active.retakeOf && <small>Retake of {active.retakeOf} · {active.keepOriginal ? 'original candidate kept' : 'deletion requested for this candidate only'}</small>}</div>}

        <div className="workflow-note"><Gauge size={16}/><div><b>Local workflow readiness</b><p>{!capability ? 'Readiness is not checked. Generation stays disabled until workflow, GPU safety and worker dispatch checks pass.' : capabilityBlocker(capability)}</p>{capability && <details><summary>Technical status</summary><p>{`${capabilityDetails(capability).join(' ')} Current: ${capability.runtime_guard?.operating_point ? `${capability.runtime_guard.operating_point.temperature_c}°C / ${capability.runtime_guard.operating_point.graphics_clock_mhz} MHz` : 'telemetry unavailable'}. Limits: ${capability.runtime_guard?.temperature_cutoff_c ?? '—'}°C / ${capability.runtime_guard?.graphics_clock_ceiling_mhz ?? '—'} MHz.`}</p></details>}<button className="text-button" onClick={refreshCapability} disabled={capState==='loading'}>Check status</button></div></div>
      </aside></div>
      </>}
      </TakeWorkspace></CreateWorkspace></div>
    </main>
    {retakeDialog && <div className="dialog-backdrop" role="presentation"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="retake-title"><button className="dialog-close" onClick={() => setRetakeDialog(false)} aria-label="Close"><X size={17}/></button><div className="dialog-icon"><RefreshCw size={20}/></div><h2 id="retake-title">Prepare a retake</h2><p>The prompt and settings return to the editor. This records your choice and does not start a job. Discard removes the clip from take history and archives its unshared output from normal library search. The file remains recoverable under Show archived, and saved references continue to work.</p><fieldset><legend>Current candidate</legend><label className="radio-option"><input type="radio" checked={retakeKeep} onChange={() => setRetakeKeep(true)}/> Keep this take in take history</label><label className="radio-option"><input type="radio" checked={!retakeKeep} onChange={() => setRetakeKeep(false)}/> Discard from take history</label><small className="dialog-footnote">No generated files are physically deleted. Outputs shared by another video job stay visible.</small></fieldset><div className="dialog-actions"><button className="quiet-button" onClick={() => setRetakeDialog(false)}>Cancel</button><button className="generate-button" onClick={startRetake} disabled={busy}>Return to editor <ArrowRight size={15}/></button></div></section></div>}
  </div>;
}

export default function App() {
  const parseRoute = (): StudioRoute => { const route = window.location.hash.split('?')[0].replace(/^#\/?/, '') || 'home'; return ['home','styles','story','screenplay','shot-frames','storyboard','setup','prompts','video','take','assets','characters','worlds','frames','text-to-image','image-to-3d-pixal3d','image-to-3d','media-prep','media','editor','status'].includes(route) ? route as StudioRoute : 'home'; };
  const [route, setRoute] = useState<StudioRoute>(parseRoute);
  const [videoWorkspace, setVideoWorkspace] = useState(() => readDraft().workspaceId);
  useEffect(() => {
    const onHashChange = () => {
      setRoute(parseRoute());
      if (['video','take'].includes(parseRoute())) setVideoWorkspace(managedProjectId() || requestedVideoWorkspace() || readDraft().workspaceId);
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  // Keep the video workspace mounted while Status is open so a running job,
  // pending recovery key, and editor state continue untouched in memory.
  const project=useProject();
  const context = project.workspace_id==='tool-library'?'Standalone video':project.title;
  return <StudioShell route={route} context={context}>
    {route==='home' && <div className="content-wrap home-content"><div className="page-heading"><div><div className="eyebrow">LOCAL STUDIO</div><h1>What would you like to make?</h1></div></div><div className="entry-cards"><a className="entry-card" href="#/story"><span className="entry-icon"><BookOpen size={20}/></span><b>Develop a story</b><p>Write, upload, or edit your story.</p><span className="entry-cta">Open Story <span>→</span></span></a><a className="entry-card" href="#/video"><span className="entry-icon"><Film size={20}/></span><b>Create a video</b><p>Generate a video from a prompt.</p><span className="entry-cta">Open Video <span>→</span></span></a></div></div>}
    {route==='story' && <><StoryPage/><div className="content-wrap story-video-entry"><section className="card"><div><b>Create a separate video</b><p>This story is not linked to video generation yet.</p></div><a className="generate-button" href="#/video">Open Video <ArrowRight size={15}/></a></section></div></>}
    {route==='screenplay' && <ScreenplayPage/>}
    {route==='shot-frames' && <StoryboardPage key="shot-frames" view="frames"/>}
    {route==='storyboard' && <StoryboardPage key="storyboard" view="storyboard"/>}
    {route==='setup' && <ProductionSetupPage/>}
    {route==='prompts' && <PromptPreparationPage/>}
    {route==='status' && <StatusPage/>}
    {route==='styles' && <ProductionStylesPage/>}
    {route==='media-prep' && <MediaPrepPage/>}
    {route==='editor' && <VibeEditorPage/>}
    {route==='text-to-image' && <TextToImagePage/>}
    {route==='image-to-3d' && <TrellisPage key="trellis"/>}
    {route==='image-to-3d-pixal3d' && <TrellisPage key="pixal" backend="pixal"/>}
    {route==='media' && <MediaLibraryPage/>}
    {['assets','characters','worlds','frames'].includes(route) && <ImageAssetsPage initialSection={route==='worlds'?'worlds':route==='frames'?'frames':'characters'} legacyRoute={route==='assets'}/>}
    <div className="video-workspace-mount" style={{display:route==='video'||route==='take'?'contents':'none'}} aria-hidden={route==='video'||route==='take'?undefined:true}><VideoWorkspace key={videoWorkspace} workspaceId={videoWorkspace} view={route==='take'?'take':'create'} visible={route==='video'||route==='take'}/></div>
  </StudioShell>;
}
