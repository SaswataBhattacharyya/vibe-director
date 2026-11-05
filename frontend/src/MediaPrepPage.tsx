import {useProjectState} from './lib/project-state';
import {deleteSelectedMedia} from './lib/media-deletion';
import OutputDestination from './OutputDestination';
import VoiceConversion from './VoiceConversion';
import StudioCheckpoints from './StudioCheckpoints';
import EditorWorkspace from './EditorWorkspace';
import StudioChat from './StudioChat';
import VoiceRecorder from './VoiceRecorder';
import VoiceStudioTools from './VoiceStudioTools';
import SelectionToggle from './SelectionToggle';
import MediaSourcePicker from './MediaSourcePicker';
import { ChangeEvent, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, AudioLines, Check, Download, FileUp, GalleryHorizontal, Image, LayoutGrid, Library, List, ListVideo, Image as ImageIcon, Mic2, RefreshCw, Search, Video, Trash2, X } from 'lucide-react';
import { AudioCapabilities, AudioModel, AudioVoice, acceptReconstructionTake, addReconstructionTake, cancelImageDetailerJob, cancelVideoAnalysis, deleteVideoAnalysis, deleteExtractedMediaAsset, cancelYoutubeJob, createAudioEffectJob, createAudioUtilityJob, createF5PreparationJob, createReconstructionPart, createTimedTTSJob, discardSamAudioPreview, enrollAudioVoice, getAudioCapabilities, getAudioEffectCapabilities, getAudioEffectJob, getAudioUtilityCapabilities, getAudioUtilityJob, getF5PreparationJob, getImageDetailerJob, getReconstructionSession, getSamAudioCapability, getStagedDonorAnalysis, getTimedTTSJob, getVideoAnalysisJob, getYoutubeJob, ImageDetailerJob, importStagedDonorAnalysisAudio, importStagedDonorVideos, indexMediaAssetAnnotations, isolateVideoAudioEvent, listAudioEffectJobs, listAudioModels, listAudioUtilityJobs, listAudioVoices, listF5PreparationJobs, listImageDetailerJobs, listMediaAssets, listStagedDonorVideos, listTimedTTSJobs, listVideoAnalysisJobs, listYoutubeJobs, MediaAsset, ReconstructionSession, resolveYoutubeSources, retryImageDetailerJob, retryVideoAnalysis, saveSamAudioPreview, saveImageAnalysis, saveReconstructionCalibration, startImageDetailerJob, startVideoAnalysis, startYoutubeDownload, uploadMediaAsset, VideoAnalysisJob, YoutubeCandidate, StagedDonorAnalysis, StagedDonorVideo, TimedTTSJob, AudioEffectCapabilities, AudioEffectJob, AudioUtilityCapabilities, AudioUtilityJob, AudioUtilityOperation, F5PreparationJob, refreshAudioVoices, SamAudioCapability, SamAudioPreview } from './lib/media-api';
import { getCharacterVoiceState, listStoryScreenplays, listStoryWorkspaces, CharacterVoiceState, StoryWorkspace } from './lib/story-api';
import { defaultMediaWorkspaceId,  preferredMediaWorkspaceId } from './lib/media-workspace';
import MusicSoundPage from './MusicSoundPage';
import { AudioSceneSurgery } from './AudioSceneSurgery';
import MediaLibraryPage from './MediaLibraryPage';
import './media-prep.css';
import './video-summarizer.css';
import './image-detailer.css';

type GpuAdmission = { available: boolean; checked: boolean; free_gib?: number | null; required_gib?: number; checked_at?: string; reason?: string; host_memory?: { total_gib: number; available_gib: number; swap_total_gib: number; swap_free_gib: number } | null };
type Capability = { can_analyze: boolean; reason: string; gpu_admission?: GpuAdmission; checks: Record<string, {available: boolean; state: string; reason?: string; items?: Record<string, {available: boolean; state: string; reason?: string}>}> };
type SummariserPage = 'library'|'youtube'|'analyze'|'results'|'audio'|'video-assets'|'image-assets';
type AudioAnalysisSettings = {
  extract_source_audio: boolean; extract_preview_mp3: boolean; detect_speech: boolean;
  diarize_speakers: boolean; detect_music: boolean; detect_sfx: boolean;
  create_audio_embeddings: boolean; create_av_embeddings: boolean;
  run_demucs: 'AUTO'|'off'|'2-stem'|'4-stem'|'6-stem'; extract_fps: number; adaptive_sampling: boolean;
  frame_change_threshold: number; preserve_scene_anchors: boolean; keep_intermediate_samples: boolean;
  collect_voice_examples: boolean; collect_music_clips: boolean; collect_sfx_clips: boolean;
};
type VideoCutSettings = { extract_cut_clips: boolean; cut_boundary_threshold: number; min_cut_seconds: number };
const DONOR_VIDEO_IMPORT_BATCH_SIZE = 20;
const pages: Array<{id: SummariserPage; label: string; icon: typeof Video}> = [
  {id:'library',label:'Library',icon:Library},{id:'youtube',label:'YouTube Download',icon:Download},
  {id:'analyze',label:'Analyze',icon:Activity},{id:'results',label:'Results',icon:ListVideo},{id:'audio',label:'Audio Assets',icon:AudioLines},{id:'video-assets',label:'Video Assets',icon:Video},{id:'image-assets',label:'Image Assets',icon:ImageIcon},
];
const videoCapability = async (): Promise<Capability> => {
  const response = await fetch('/api/video-summariser/capabilities');
  if (!response.ok) throw new Error('Could not check analyzer readiness.');
  return response.json();
};
const checkVideoGpuAdmission = async (): Promise<GpuAdmission> => {
  const response = await fetch('/api/video-summariser/capabilities?check_gpu_admission=1');
  if (!response.ok) throw new Error('Could not check runtime readiness.');
  const value = await response.json() as Capability;
  if (!value.gpu_admission?.checked) throw new Error('The connected API does not yet provide runtime readiness checks. Restart the Vibe Director backend from this checkout, then recheck.');
  return value.gpu_admission;
};
const hostMemoryNote = (admission: GpuAdmission) => admission.host_memory
  ? `Host memory context (informational only): ${admission.host_memory.available_gib} GiB available of ${admission.host_memory.total_gib} GiB RAM; ${admission.host_memory.swap_free_gib} GiB swap free. Unified-memory systems share RAM between CPU and GPU.`
  : null;

function VideoSummariser() {
  const readPage = (): SummariserPage => {
    const value = new URLSearchParams(window.location.hash.split('?')[1] || '').get('videoPage');
    return value === 'youtube' || value === 'analyze' || value === 'results' || value === 'audio' || value === 'video-assets' || value === 'image-assets' ? value : 'library';
  };
  const [page, setPageState] = useState<SummariserPage>(readPage);
  const setPage = (next: SummariserPage) => {
    setPageState(next);
    if (window.location.hash.startsWith('#/media-prep')) {
      const params = new URLSearchParams(window.location.hash.split('?')[1] || '');
      params.set('tool', 'video');
      if (next === 'library') params.delete('videoPage'); else params.set('videoPage', next);
      window.location.hash = `/media-prep?${params.toString()}`;
    }
  };
  useEffect(() => {
    const syncPage = () => setPageState(readPage());
    window.addEventListener('hashchange', syncPage);
    return () => window.removeEventListener('hashchange', syncPage);
  }, []);
  const [capability, setCapability] = useState<Capability | null>(null);
  const [gpuAdmission, setGpuAdmission] = useState<GpuAdmission | null>(null);
  const [gpuAdmissionBusy, setGpuAdmissionBusy] = useState(false);
  const [, setWorkspaces] = useState<StoryWorkspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState(defaultMediaWorkspaceId);
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [selectedExtractedIds,setSelectedExtractedIds] = useState<string[]>([]);
  const [deletingExtracted,setDeletingExtracted] = useState(false);
  const extractedWorkspaceRef = useRef(workspaceId);
  extractedWorkspaceRef.current = workspaceId;
  useEffect(()=>setSelectedExtractedIds([]),[workspaceId,page]);
  const [donorVideos, setDonorVideos] = useState<StagedDonorVideo[]>([]);
  const [donorSelected, setDonorSelected] = useState<string[]>([]);
  const [donorAnalysis, setDonorAnalysis] = useState<StagedDonorAnalysis | null>(null);
  const [donorAudioSelected, setDonorAudioSelected] = useState<string[]>([]);
  const [showDonorVideos, setShowDonorVideos] = useState(false);
  const donorWorkspaceRef = useRef(workspaceId);
  const donorOperationRef = useRef(0);
  donorWorkspaceRef.current = workspaceId;
  const [query, setQuery] = useProjectState('VideoSummariser:query','');
  const visibleDonorVideos = useMemo(() => donorVideos.filter(row => [row.title,row.filename,row.channel].join(' ').toLowerCase().includes(query.trim().toLowerCase())), [donorVideos,query]);
  const [oldestFirst, setOldestFirst] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [analysisDestinationReady,setAnalysisDestinationReady]=useState(false);

  const [message, setMessage] = useState('');
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([]);
  const [pendingVideoId, setPendingVideoId] = useState(() => new URLSearchParams(window.location.hash.split('?')[1] || '').get('asset_id') || '');
  const [jobs, setJobs] = useState<VideoAnalysisJob[]>([]);
  const [activeJob, setActiveJob] = useState<VideoAnalysisJob | null>(null);
  const [existingAnalysis, setExistingAnalysis] = useState<VideoAnalysisJob | null>(null);
  const existingAnalysisDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (existingAnalysis && !existingAnalysisDialog.current?.open) existingAnalysisDialog.current?.showModal();
  }, [existingAnalysis]);
  useEffect(() => setExistingAnalysis(null), [workspaceId]);
  const [samSelection, setSamSelection] = useState('');
  const [samPrompt, setSamPrompt] = useProjectState('VideoSummariser:samPrompt','');
  const [samPreview, setSamPreview] = useState<SamAudioPreview|null>(null);
  const [samCapability, setSamCapability] = useState<SamAudioCapability|null>(null);
  const [samBusy, setSamBusy] = useState(false);
  const samWorkspaceRef = useRef(workspaceId);
  const samOperationRef = useRef(0);
  samWorkspaceRef.current = workspaceId;
  const [audioAnalysis, setAudioAnalysis] = useProjectState('VideoSummariser:audioAnalysis',true);
  const [audioSettings, setAudioSettings] = useProjectState<AudioAnalysisSettings>('VideoSummariser:audioSettings',{
    extract_source_audio:true, extract_preview_mp3:true, detect_speech:true, diarize_speakers:true,
    detect_music:true, detect_sfx:true, create_audio_embeddings:true, create_av_embeddings:true,
    run_demucs:'AUTO', extract_fps:4, adaptive_sampling:true, frame_change_threshold:0.08,
    preserve_scene_anchors:true, keep_intermediate_samples:false,
    collect_voice_examples:false, collect_music_clips:false, collect_sfx_clips:false,
  });
  const [videoCutSettings, setVideoCutSettings] = useProjectState<VideoCutSettings>('VideoSummariser:videoCutSettings',{
    extract_cut_clips:true, cut_boundary_threshold:0.18, min_cut_seconds:0.5,
  });
  const [youtubeMode, setYoutubeMode] = useProjectState<'search'|'paste'>('VideoSummariser:youtubeMode','search');
  const [youtubeQuery, setYoutubeQuery] = useProjectState('VideoSummariser:youtubeQuery','');
  const [youtubeUrls, setYoutubeUrls] = useProjectState('VideoSummariser:youtubeUrls','');
  const [youtubeCandidates, setYoutubeCandidates] = useState<YoutubeCandidate[]>([]);
  const [youtubeSelected, setYoutubeSelected] = useState<string[]>([]);
  const [youtubeJob, setYoutubeJob] = useState<VideoAnalysisJob|null>(null);

  useEffect(() => {
    void videoCapability().then(setCapability).catch(error => setMessage((error as Error).message));
    void listStoryWorkspaces().then(result => {
      setWorkspaces(result.items || []);
      const requestedWorkspace = new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || '';
      setWorkspaceId(preferredMediaWorkspaceId(result.items || [], requestedWorkspace));
    }).catch(error => setMessage(`Could not load workspaces: ${(error as Error).message}`));
  }, []);
  const refreshGpuAdmission = async () => {
    setGpuAdmissionBusy(true);
    setGpuAdmission(null);
    try { setGpuAdmission(await checkVideoGpuAdmission()); }
    catch (error) { setGpuAdmission({available:false,checked:true,reason:(error as Error).message}); }
    finally { setGpuAdmissionBusy(false); }
  };
  useEffect(() => {
    const retryableJob = page === 'results' && activeJob && ['failed','cancelled','interrupted'].includes(activeJob.status);
    if ((page === 'analyze' || retryableJob) && capability?.can_analyze && !gpuAdmission && !gpuAdmissionBusy) void refreshGpuAdmission();
  }, [page, activeJob?.job_id, activeJob?.status, capability?.can_analyze, gpuAdmission, gpuAdmissionBusy]);
  useEffect(() => {
    if (!workspaceId) { setAssets([]); return; }
    let active = true;
    void (page === 'results' ? Promise.all(['video','audio','image'].map(kind=>listMediaAssets(workspaceId,kind))).then(rows=>({assets:rows.flatMap(row=>row.assets)})) : listMediaAssets(workspaceId,page === 'audio' ? 'audio' : page === 'image-assets' ? 'image' : 'video')).then(result => { if (active) setAssets(result.assets); })
      .catch(error => { if (active) { setAssets([]); setMessage(`Could not load media: ${(error as Error).message}`); } });
    return () => { active = false; };
  }, [workspaceId, page]);

  useEffect(() => {
    if (!pendingVideoId || page !== 'analyze' || !assets.length) return;
    if (assets.some(asset => asset.asset_id === pendingVideoId && asset.kind === 'video' && !asset.metadata?.analyzer_run_id)) {
      setSelectedVideoIds(current => current.includes(pendingVideoId) ? current : [...current, pendingVideoId]);
      setPendingVideoId('');
    } else {
      setMessage('The selected video is not available in this workspace. Choose it from the Analyze list.');
      setPendingVideoId('');
    }
  }, [assets, page, pendingVideoId]);

  useEffect(() => {
    if (!workspaceId || page !== 'youtube') return;
    let active = true;
    void listYoutubeJobs(workspaceId).then(rows => {
      if (!active) return;
      setYoutubeJob(current => current ? rows.find(row => row.job_id === current.job_id) || current : rows.find(row => ['queued','running','cancel_requested'].includes(row.status)) || rows[0] || null);
    }).catch(error => { if (active) setMessage(`Could not load downloads: ${(error as Error).message}`); });
    return () => { active = false; };
  }, [workspaceId, page]);

  useEffect(() => {
    if (!workspaceId || !youtubeJob || !['queued','running','cancel_requested'].includes(youtubeJob.status)) return;
    let active = true;
    const timer = window.setInterval(() => void getYoutubeJob(workspaceId, youtubeJob.job_id).then(updated => {
      if (!active) return;
      setYoutubeJob(updated);
    }).catch(error => { if (active) setMessage(`Could not refresh download: ${(error as Error).message}`); }), 2500);
    return () => { active = false; window.clearInterval(timer); };
  }, [workspaceId, youtubeJob?.job_id, youtubeJob?.status]);
  useEffect(() => { samOperationRef.current += 1; setSelectedVideoIds([]); setActiveJob(null); setSamSelection(''); setSamPrompt(''); setSamPreview(null); setSamBusy(false); }, [workspaceId]);
  useEffect(() => {
    donorOperationRef.current += 1;
    setDonorVideos([]); setDonorSelected([]); setDonorAnalysis(null); setDonorAudioSelected([]);
    setShowDonorVideos(false); setBusy(false);
  }, [workspaceId]);

  useEffect(() => {
    if (!workspaceId) { setJobs([]); setActiveJob(null); return; }
    let active = true;
    void listVideoAnalysisJobs(workspaceId).then(rows => {
      if (!active) return;
      setJobs(rows);
      setActiveJob(current => current ? rows.find(row => row.job_id === current.job_id) || current : rows[0] || null);
    }).catch(error => { if (active && page === 'results') setMessage(`Could not load analyses: ${(error as Error).message}`); });
    return () => { active = false; };
  }, [workspaceId, page]);

  useEffect(() => {
    if (!workspaceId || !activeJob || !['queued','running','cancel_requested'].includes(activeJob.status)) return;
    let active = true;
    const timer = window.setInterval(() => {
      void getVideoAnalysisJob(workspaceId, activeJob.job_id).then(updated => {
        if (!active) return;
        setActiveJob(updated);
        setJobs(rows => [updated, ...rows.filter(row => row.job_id !== updated.job_id)]);
      }).catch(error => { if (active) setMessage(`Could not refresh analysis: ${(error as Error).message}`); });
    }, 2500);
    return () => { active = false; window.clearInterval(timer); };
  }, [workspaceId, activeJob?.job_id, activeJob?.status]);

  const isExtracted = (asset:MediaAsset) => !!(asset.metadata?.analyzer_run_id || asset.metadata?.sam_audio?.run_id);
  const sourceVideos = assets.filter(asset=>asset.kind==='video'&&!isExtracted(asset));
  const completedSources = new Set(jobs.filter(job=>job.status==='completed').flatMap(job=>job.request.source_asset_ids||[]));
  const analysisSources = sourceVideos.filter(asset=>!completedSources.has(asset.asset_id));
  useEffect(()=>{const completed=new Set(jobs.filter(job=>job.status==='completed').flatMap(job=>job.request.source_asset_ids||[]));setSelectedVideoIds(current=>current.filter(id=>!completed.has(id)));},[jobs]);
  const deleteClip = async (asset:MediaAsset) => {
    if(deletingExtracted)return;
    setDeletingExtracted(true);
    try {setMessage(await deleteSelectedMedia(workspaceId,[asset.asset_id]));setAssets((await listMediaAssets(workspaceId,extractedKind)).assets);}
    catch(error) {setMessage((error as Error).message);setAssets((await listMediaAssets(workspaceId,extractedKind)).assets);}
    finally {setDeletingExtracted(false);setSelectedExtractedIds([]);}
  };
  const extractedKind = page==='audio'?'audio':page==='image-assets'?'image':'video';
  const extractedAssets = assets.filter(asset=>asset.kind===extractedKind&&asset.workspace_id===workspaceId&&isExtracted(asset));
  const deleteExtractedBatch = async (all:boolean) => {
    if (deletingExtracted) return;
    const targets=extractedAssets.filter(asset=>all||selectedExtractedIds.includes(asset.asset_id));
    if (!targets.length || !window.confirm(`Permanently delete ${all?'all ':''}${targets.length} extracted ${extractedKind} asset(s) in this workspace? They will also disappear from Results. Original source files and analysis summaries are retained.${all&&query.trim()?' This includes items hidden by the search filter.':''}`)) return;
    const targetWorkspace=workspaceId;
    setDeletingExtracted(true);setMessage('');
    let deleted=0;const failures:string[]=[];
    try {
      for (const asset of targets) {
        try {
          await deleteExtractedMediaAsset(targetWorkspace,asset.asset_id);
          deleted++;
          if (extractedWorkspaceRef.current===targetWorkspace) {
            setAssets(current=>current.filter(row=>row.asset_id!==asset.asset_id));
            setSelectedExtractedIds(current=>current.filter(id=>id!==asset.asset_id));
          }
        } catch(error) {failures.push(`${asset.filename}: ${(error as Error).message}`);}
      }
      if (extractedWorkspaceRef.current===targetWorkspace) setMessage(`${deleted} extracted asset(s) deleted. Original source files retained.${failures.length?` ${failures.length} could not be deleted: ${failures.join('; ')}`:''}`);
    } finally {setDeletingExtracted(false);}
  };
  const visibleAssets = useMemo(() => assets.filter(asset => (page==='audio'||page==='video-assets'||page==='image-assets'?isExtracted(asset)&&asset.kind===extractedKind&&asset.workspace_id===workspaceId:!isExtracted(asset))).filter(asset => [asset.filename,asset.description,...(asset.tags || [])].filter(Boolean).join(' ').toLowerCase().includes(query.trim().toLowerCase()))
    .sort((a,b) => oldestFirst ? a.created_at.localeCompare(b.created_at) : b.created_at.localeCompare(a.created_at)), [assets, query, oldestFirst, page, extractedKind, workspaceId]);
  const addVideo = async () => {
    if (!workspaceId || !file) return;
    setBusy(true); setMessage('');
    try {
      const saved = await uploadMediaAsset(workspaceId,file,'project_video');
      setFile(null);
      const input = document.getElementById('summariser-video-upload') as HTMLInputElement | null;
      if (input) input.value = '';
      const result = await listMediaAssets(workspaceId,'video'); setAssets(result.assets);
      setMessage(saved.deduplicated ? 'This video is already in the library.' : 'Video added to the shared library.');
    } catch (error) { setMessage(`Upload failed: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const loadDonorVideos = async () => {
    if (!workspaceId) return;
    const requestedWorkspaceId = workspaceId;
    const operationId = ++donorOperationRef.current;
    setBusy(true); setMessage('');
    try {
      const rows = await listStagedDonorVideos(requestedWorkspaceId);
      if (donorWorkspaceRef.current !== requestedWorkspaceId || donorOperationRef.current !== operationId) return;
      setDonorVideos(rows); setShowDonorVideos(true);
    } catch (error) {
      if (donorWorkspaceRef.current === requestedWorkspaceId && donorOperationRef.current === operationId) setMessage(`Could not list copied Story Builder videos: ${(error as Error).message}`);
    } finally { if (donorOperationRef.current === operationId) setBusy(false); }
  };
  const importDonorVideos = async () => {
    if (!workspaceId || !donorSelected.length) return;
    const requestedWorkspaceId = workspaceId;
    const operationId = ++donorOperationRef.current;
    const selectedIds = [...donorSelected];
    setBusy(true); setMessage('');
    let confirmedCount = 0;
    let failedBatch = '';
    try {
      const batchCount = Math.ceil(selectedIds.length / DONOR_VIDEO_IMPORT_BATCH_SIZE);
      for (let offset = 0; offset < selectedIds.length; offset += DONOR_VIDEO_IMPORT_BATCH_SIZE) {
        const batch = selectedIds.slice(offset, offset + DONOR_VIDEO_IMPORT_BATCH_SIZE);
        setMessage(`Importing batch ${Math.floor(offset / DONOR_VIDEO_IMPORT_BATCH_SIZE) + 1} of ${batchCount}…`);
        try {
          const result = await importStagedDonorVideos(requestedWorkspaceId, batch);
          if (donorWorkspaceRef.current !== requestedWorkspaceId || donorOperationRef.current !== operationId) return;
          confirmedCount += result.assets.length;
          setDonorSelected(current => current.filter(id => !batch.includes(id)));
        } catch (error) {
          failedBatch = (error as Error).message;
          break;
        }
      }
      if (donorWorkspaceRef.current !== requestedWorkspaceId || donorOperationRef.current !== operationId) return;
      const importSummary = failedBatch
        ? `${confirmedCount} of ${selectedIds.length} selected videos were confirmed. The failed batch and later videos remain selected; retry to continue. If the request partially completed, matching files will be reused.`
        : `${confirmedCount} copied video${confirmedCount === 1 ? '' : 's'} added to this workspace library.`;
      if (!failedBatch) setDonorSelected([]);
      setMessage(importSummary);
      if (confirmedCount > 0) try {
        const library = await listMediaAssets(requestedWorkspaceId, 'video');
        if (donorWorkspaceRef.current !== requestedWorkspaceId || donorOperationRef.current !== operationId) return;
        setAssets(library.assets);
      } catch (error) {
        if (donorWorkspaceRef.current === requestedWorkspaceId && donorOperationRef.current === operationId) setMessage(`${importSummary} The library could not refresh: ${(error as Error).message}`);
      }
      if (failedBatch && confirmedCount === 0) setMessage(`Could not import copied videos: ${failedBatch}`);
    } finally { if (donorOperationRef.current === operationId) setBusy(false); }
  };
  const inspectDonorAnalysis = async (assetId: string) => {
    if (!workspaceId) return;
    const requestedWorkspaceId = workspaceId;
    const operationId = ++donorOperationRef.current;
    setBusy(true); setMessage(''); setDonorAudioSelected([]);
    try {
      const analysis = await getStagedDonorAnalysis(requestedWorkspaceId, assetId);
      if (donorWorkspaceRef.current !== requestedWorkspaceId || donorOperationRef.current !== operationId) return;
      setDonorAnalysis(analysis);
    } catch (error) {
      if (donorWorkspaceRef.current === requestedWorkspaceId && donorOperationRef.current === operationId) { setDonorAnalysis(null); setMessage(`Could not load copied analysis: ${(error as Error).message}`); }
    } finally { if (donorOperationRef.current === operationId) setBusy(false); }
  };
  const importDonorAudio = async () => {
    if (!workspaceId || !donorAnalysis || !donorAudioSelected.length) return;
    const requestedWorkspaceId = workspaceId;
    const operationId = ++donorOperationRef.current;
    const videoAssetId = donorAnalysis.video_asset_id;
    const selectedIds = [...donorAudioSelected];
    setBusy(true); setMessage('');
    try {
      const result = await importStagedDonorAnalysisAudio(requestedWorkspaceId, videoAssetId, selectedIds);
      if (donorWorkspaceRef.current !== requestedWorkspaceId || donorOperationRef.current !== operationId) return;
      setDonorAudioSelected([]);
      setMessage(`${result.assets.length} analyzed audio clip${result.assets.length === 1 ? '' : 's'} added to this workspace library.`);
    } catch (error) {
      if (donorWorkspaceRef.current === requestedWorkspaceId && donorOperationRef.current === operationId) setMessage(`Could not import analyzed audio: ${(error as Error).message}`);
    } finally { if (donorOperationRef.current === operationId) setBusy(false); }
  };
  const toggleVideo = (assetId: string) => {
    const existing = jobs.find(job => job.status === 'completed' && job.request.source_asset_ids?.includes(assetId));
    if (existing) { setExistingAnalysis(existing); return; }
    setSelectedVideoIds(current => current.includes(assetId) ? current.filter(id => id !== assetId) : [...current, assetId]);
  };
  const analyzeSelected = async () => {
    if (!workspaceId || !selectedVideoIds.length || !capability?.can_analyze || !gpuAdmission?.available) return;
    const existing = jobs.find(job => job.status === 'completed' && job.request.source_asset_ids?.some(id => selectedVideoIds.includes(id)));
    if (existing) { setExistingAnalysis(existing); return; }
    setBusy(true); setMessage('');
    try {
      const job = await startVideoAnalysis(workspaceId, selectedVideoIds, {
        ...videoCutSettings, audio_analyzer_enabled: audioAnalysis, audio_analyzer: audioSettings,
      });
      setActiveJob(job); setJobs(rows => [job, ...rows.filter(row => row.job_id !== job.job_id)]);
      setPage('results');
    } catch (error) { setMessage(`Could not start analysis: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const cancelActiveJob = async () => {
    if (!workspaceId || !activeJob) return;
    setBusy(true);
    try {
      const job = await cancelVideoAnalysis(workspaceId, activeJob.job_id);
      setActiveJob(job); setJobs(rows => [job, ...rows.filter(row => row.job_id !== job.job_id)]);
      setMessage(job.status === 'cancelled' ? 'Analysis cancelled.' : 'Cancellation requested. Waiting for the worker to stop.');
    } catch (error) { setMessage(`Could not cancel analysis: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const deleteActiveAnalysis = async () => {
    if (!workspaceId || !activeJob || busy) return;
    if (!window.confirm('Remove this analysis job? Shared repertoire files and their references are kept. Unpublished private job outputs are removed; the original video is retained.')) return;
    const jobId = activeJob.job_id;
    setBusy(true); setMessage('');
    try {
      await deleteVideoAnalysis(workspaceId, jobId);
      setJobs(rows => rows.filter(row => row.job_id !== jobId)); setActiveJob(null); setSamPreview(null);
      setMessage('Analysis and derived assets deleted. Original video retained.');
    } catch (error) { setMessage(`Could not delete analysis: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const retryActiveJob = async () => {
    if (!workspaceId || !activeJob) return;
    setBusy(true); setGpuAdmissionBusy(true); setMessage('');
    try {
      const admission = await checkVideoGpuAdmission();
      setGpuAdmission(admission);
      if (!admission.available) { setMessage(admission.reason || 'Runtime checks are not ready.'); return; }
      const job = await retryVideoAnalysis(workspaceId, activeJob.job_id);
      setActiveJob(job); setJobs(rows => [job, ...rows.filter(row => row.job_id !== job.job_id)]);
      setMessage('Analysis restarted with its saved settings.');
    } catch (error) { setMessage(`Could not retry analysis: ${(error as Error).message}`); }
    finally { setBusy(false); setGpuAdmissionBusy(false); }
  };
  const samEvents = (activeJob?.result?.audio_analysis || []).flatMap(run =>
    (run.run_id && Array.isArray(run.audio_events) ? run.audio_events : []).map(event => ({
      run_id: run.run_id as string, event, asset_id: run.asset_id,
    })));
  useEffect(() => {
    if (!samEvents.length) { setSamCapability(null); return; }
    let current = true;
    setSamCapability(null);
    void getSamAudioCapability().then(value => { if (current) setSamCapability(value); })
      .catch(() => { if (current) setSamCapability({available:false,status:'unavailable',checkpoint_present:false,worker_configured:false,authentication_configured:false,reason:'Could not check SAM Audio readiness.'}); });
    return () => { current = false; };
  }, [workspaceId, activeJob?.job_id, samEvents.length]);
  const selectedSamEvent = samEvents.find(row => `${row.run_id}|${row.event.event_id}` === samSelection) || samEvents[0];
  const isolateSamEvent = async () => {
    if (!workspaceId || !selectedSamEvent || !samPrompt.trim()) return;
    const requestedWorkspaceId = workspaceId;
    const operationId = ++samOperationRef.current;
    setSamBusy(true); setMessage('');
    try {
      const preview = await isolateVideoAudioEvent(requestedWorkspaceId, selectedSamEvent.run_id, selectedSamEvent.event.event_id, samPrompt.trim());
      if (samWorkspaceRef.current !== requestedWorkspaceId || samOperationRef.current !== operationId) {
        if (preview.temporary_id) await discardSamAudioPreview(requestedWorkspaceId, preview.temporary_id).catch(() => {});
        return;
      }
      setSamPreview(preview);
      if (preview.status !== 'preview_ready') setMessage(preview.reason || 'SAM Audio is not ready.');
    } catch (error) { if (samWorkspaceRef.current === requestedWorkspaceId && samOperationRef.current === operationId) setMessage(`Could not isolate this sound: ${(error as Error).message}`); }
    finally { if (samOperationRef.current === operationId) setSamBusy(false); }
  };
  const saveSamPreview = async () => {
    if (!workspaceId || !samPreview?.temporary_id) return;
    const requestedWorkspaceId = workspaceId;
    const temporaryId = samPreview.temporary_id;
    const operationId = ++samOperationRef.current;
    setSamBusy(true);
    try {
      const result = await saveSamAudioPreview(requestedWorkspaceId, temporaryId);
      if (samWorkspaceRef.current !== requestedWorkspaceId || samOperationRef.current !== operationId) return;
      if (result.asset) {
        try {
          const library = await listMediaAssets(requestedWorkspaceId, 'audio');
          if (samWorkspaceRef.current !== requestedWorkspaceId || samOperationRef.current !== operationId) return;
          setAssets(library.assets);
          setSamPreview(null);
          setMessage('Saved the isolated sound to Audio Assets.');
        } catch {
          // Keep the preview ID so the idempotent save endpoint can recover a lost library refresh.
          if (samWorkspaceRef.current === requestedWorkspaceId && samOperationRef.current === operationId) {
            setMessage('The sound is saved, but Audio Assets could not refresh. Retry Save to reload it.');
          }
        }
      } else setMessage('The sound preview was not saved.');
    } catch (error) { if (samWorkspaceRef.current === requestedWorkspaceId && samOperationRef.current === operationId) setMessage(`Could not save the sound: ${(error as Error).message}`); }
    finally { if (samOperationRef.current === operationId) setSamBusy(false); }
  };
  const discardSamPreview = async () => {
    if (!workspaceId || !samPreview?.temporary_id) return;
    const requestedWorkspaceId = workspaceId;
    const temporaryId = samPreview.temporary_id;
    const operationId = ++samOperationRef.current;
    setSamBusy(true);
    try {
      await discardSamAudioPreview(requestedWorkspaceId, temporaryId);
      if (samWorkspaceRef.current === requestedWorkspaceId && samOperationRef.current === operationId) { setSamPreview(null); setMessage('Temporary sound preview discarded.'); }
    }
    catch (error) { if (samWorkspaceRef.current === requestedWorkspaceId && samOperationRef.current === operationId) setMessage(`Could not discard preview: ${(error as Error).message}`); }
    finally { if (samOperationRef.current === operationId) setSamBusy(false); }
  };
  const refreshJobs = async () => {
    if (!workspaceId) return;
    try { const rows = await listVideoAnalysisJobs(workspaceId); setJobs(rows); setActiveJob(current => current ? rows.find(row => row.job_id === current.job_id) || current : rows[0] || null); }
    catch (error) { setMessage(`Could not load analyses: ${(error as Error).message}`); }
  };
  const findYoutubeSources = async () => {
    if (!workspaceId) return;
    setBusy(true); setMessage(''); setYoutubeCandidates([]); setYoutubeSelected([]);
    try {
      const result = await resolveYoutubeSources(workspaceId, youtubeMode === 'search'
        ? {mode:'search', query:youtubeQuery, count:10}
        : {mode:'paste', urls_text:youtubeUrls});
      setYoutubeCandidates(result.candidates);
      setYoutubeSelected(result.candidates.map(item=>item.url));
      if (!result.candidates.length) setMessage('No matching videos found.');
    } catch (error) { setMessage(`Could not find YouTube videos: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const downloadYoutube = async () => {
    if (!workspaceId || !youtubeSelected.length) return;
    const selected = youtubeCandidates.filter(item=>youtubeSelected.includes(item.url));
    setBusy(true); setMessage('');
    try {
      const job = await startYoutubeDownload(workspaceId, selected, youtubeMode);
      setYoutubeJob(job);
    } catch (error) { setMessage(`Could not start download: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const cancelYoutube = async () => {
    if (!workspaceId || !youtubeJob) return;
    setBusy(true);
    try { const job=await cancelYoutubeJob(workspaceId,youtubeJob.job_id); setYoutubeJob(job); }
    catch(error) { setMessage(`Could not cancel download: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };
  const readiness = capability?.checks || {};
  const analyzerHeaderState = !capability ? 'Checking' : !capability.can_analyze ? 'Unavailable'
    : gpuAdmissionBusy || (page === 'analyze' && !gpuAdmission) ? 'Checking runtime'
    : !gpuAdmission ? 'Setup ready' : gpuAdmission.available ? 'Ready' : 'Runtime blocked';
  const analyzerHeaderNote = !capability ? 'Checking analyzer setup…' : !capability.can_analyze
    ? 'Analyzer setup unavailable. Review the setup checks before analyzing a video.'
    : gpuAdmissionBusy || (page === 'analyze' && !gpuAdmission) ? 'Analyzer setup is ready; checking runtime readiness…'
    : !gpuAdmission ? 'Analyzer setup is ready. Runtime readiness will be checked before analysis.'
    : gpuAdmission.available ? 'Analyzer setup and runtime are ready. Select a video below to analyze it.'
    : `Analyzer setup is ready, but runtime checks are blocked: ${gpuAdmission.reason || 'the runtime is not ready.'}`;
  const legacyGpuAdmissionFailure = activeJob?.status === 'failed' && activeJob.message.includes('20 GiB is required');
  return <section className="card summariser-page" aria-label="Video Summariser">
    {existingAnalysis && <dialog ref={existingAnalysisDialog} className="card notice" style={{ maxWidth: '36rem' }} aria-labelledby="existing-analysis-title" onCancel={() => setExistingAnalysis(null)}>
      <h2 id="existing-analysis-title">Video has already been analysed</h2>
      <p>Do you want to go to its analysis?</p>
      <button type="button" className="generate-button" onClick={() => { setActiveJob(existingAnalysis); setExistingAnalysis(null); setPage('results'); }}>Yes</button>
      <button type="button" className="quiet-button" onClick={() => setExistingAnalysis(null)}>No</button>
    </dialog>}
    <header className="summariser-heading"><div><div className="eyebrow">MEDIA PREP / VIDEO SUMMARISER</div><h1>Video Summariser</h1><p>Add source videos, analyze them, then review the derived clips, frames and audio.</p><p className="summariser-readiness-note">{analyzerHeaderNote}</p></div><span className="media-prep-state">{analyzerHeaderState}</span></header>
    <nav className="summariser-tabs" aria-label="Video Summariser pages">{pages.map(({id,label,icon:Icon})=><button type="button" key={id} disabled={deletingExtracted} aria-current={page===id?'page':undefined} className={page===id?'selected':''} onClick={()=>{setPage(id);setMessage('');}}><Icon size={15}/>{label}</button>)}</nav>
    {message && <p className="notice" role="status">{message}</p>}
    {page === 'library' && <>
      <div className="summariser-toolbar"><p className="project-context-label">Current project · change with New project or Load project above</p><label className="summariser-upload">Add video<input id="summariser-video-upload" type="file" accept="video/*" onChange={(event:ChangeEvent<HTMLInputElement>)=>{const next=event.currentTarget.files?.[0]||null;event.currentTarget.value='';setFile(next);}}/></label><button className="generate-button" type="button" disabled={busy||!file||!workspaceId} onClick={()=>void addVideo()}><FileUp size={15}/>{busy?'Adding…':'Add to library'}</button></div>
      <div className="summariser-toolbar"><label className="summariser-search"><Search size={16}/><input aria-label="Search source videos" placeholder="Search video name or notes" value={query} onChange={event=>setQuery(event.target.value)}/></label><button type="button" className="quiet-button" aria-label={oldestFirst?'Sort newest first':'Sort oldest first'} title={oldestFirst?'Oldest first':'Newest first'} onClick={()=>setOldestFirst(value=>!value)}>{oldestFirst?'↑':'↓'}</button><span className="media-prep-state">{visibleAssets.length} videos</span></div>
      <details className="card donor-video-import"><summary>Import copied Story Builder videos</summary><p>Preview and select copied videos. You can select any number; Vibe imports them in sequential batches of up to 20 so each request stays bounded. Original donor files remain untouched; each file must be 512 MiB or smaller.</p><div className="summariser-toolbar"><button type="button" className="quiet-button" disabled={busy||!workspaceId} onClick={()=>void loadDonorVideos()}>{busy?'Loading…':'Show copied videos'}</button>{donorVideos.length>0&&<><span>{donorSelected.length} selected · {donorVideos.length} available</span><SelectionToggle selected={donorSelected} shown={visibleDonorVideos.filter(row=>row.importable).map(row=>row.asset_id)} onChange={setDonorSelected} disabled={busy}/><button className="generate-button" disabled={busy||!donorSelected.length} onClick={()=>void importDonorVideos()}>{busy?'Importing…':'Import selected'}</button></>}</div>{donorVideos.length>0&&<div className="summariser-analysis-picker donor-video-picker">{visibleDonorVideos.map(row=><article className="donor-video-card" key={row.asset_id}><video className="donor-video-preview" src={`/api/video-summariser/${encodeURIComponent(workspaceId)}/library/donor/${encodeURIComponent(row.asset_id)}/content`} controls preload="none" aria-label={`Preview ${row.title}`}/><div className="donor-video-card-details"><label><input type="checkbox" checked={donorSelected.includes(row.asset_id)} disabled={!row.importable||busy} onChange={()=>setDonorSelected(current=>current.includes(row.asset_id)?current.filter(id=>id!==row.asset_id):row.importable?[...current,row.asset_id]:current)}/><span title={`${row.title} · ${row.filename}`}>{row.title}<small>{row.channel||row.filename} · {(row.size_bytes/1024/1024).toFixed(1)} MB{!row.importable&&' · Over the 512 MiB per-file limit; cannot import.'}</small></span></label><button type="button" className="quiet-button" aria-pressed={donorSelected.includes(row.asset_id)} disabled={!row.importable||busy} onClick={()=>setDonorSelected(current=>current.includes(row.asset_id)?current.filter(id=>id!==row.asset_id):row.importable?[...current,row.asset_id]:current)}>{donorSelected.includes(row.asset_id)?'Remove from selection':'Select for import'}</button><button type="button" className="quiet-button" disabled={busy} onClick={()=>void inspectDonorAnalysis(row.asset_id)}>Show analysis</button></div></article>)}</div>}{showDonorVideos&&!donorVideos.length&&<p>No staged copied videos are available.</p>}
        {donorAnalysis&&<section className="donor-analysis-preview" aria-label="Copied video analysis"><h3>Analysis · {donorAnalysis.video_asset_id}</h3>{donorAnalysis.analysis?<><p>{donorAnalysis.analysis.model} · {donorAnalysis.analysis.revision}</p><p>{donorAnalysis.analysis.summary||'No saved video summary.'}</p><h4>Collected audio clips ({donorAnalysis.audio_assets.length})</h4><p>Choose the clips to add. Source video and time range will be saved with each clip.</p><div className="summariser-analysis-picker">{donorAnalysis.audio_assets.map(item=><label key={item.asset_id}><input type="checkbox" checked={donorAudioSelected.includes(item.asset_id)} disabled={!donorAudioSelected.includes(item.asset_id)&&donorAudioSelected.length>=20} onChange={()=>setDonorAudioSelected(current=>current.includes(item.asset_id)?current.filter(id=>id!==item.asset_id):current.length<20?[...current,item.asset_id]:current)}/><span>{item.label} · {item.category} · {item.start_time_sec ?? '?'}–{item.end_time_sec ?? '?'} sec · {(item.size_bytes/1024).toFixed(0)} KB</span></label>)}</div>{donorAnalysis.audio_assets.length>0&&<button type="button" className="generate-button" disabled={busy||!donorAudioSelected.length} onClick={()=>void importDonorAudio()}>{busy?'Importing…':`Import ${donorAudioSelected.length} selected audio clips`}</button>}</>:<p>No linked, readable summary or collected clips were found for this video.</p>}</section>}
      </details>
      <MediaSourcePicker workspaceId={workspaceId} kinds={['video']} disabled={busy} onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/><SelectionToggle selected={selectedVideoIds} shown={visibleAssets.filter(asset=>!completedSources.has(asset.asset_id)).map(asset=>asset.asset_id)} onChange={setSelectedVideoIds} disabled={busy}/><p className="summariser-selection-hint">Select videos here, then open Analyze. {selectedVideoIds.length} selected.</p>
      <MediaGrid assets={visibleAssets} empty={workspaceId?'No videos in this workspace yet.':'Create or select a workspace first.'} selectable analyzedIds={[...completedSources]} selectedIds={selectedVideoIds} onToggle={toggleVideo}/>
    </>}
    {page === 'youtube' && <div className="summariser-status youtube-download"><h2>YouTube Download</h2><p>Find or paste YouTube links, then download selected videos once into the shared downloads folder (720p maximum). This workspace links to the original; analysis never requires another source copy.</p>
      <p className="project-context-label">Current project · change with New project or Load project above</p>
      <div className="summariser-toolbar"><label><input type="radio" name="youtube-mode" checked={youtubeMode==='search'} onChange={()=>setYoutubeMode('search')}/> Search YouTube</label><label><input type="radio" name="youtube-mode" checked={youtubeMode==='paste'} onChange={()=>setYoutubeMode('paste')}/> Paste links</label></div>
      {youtubeMode==='search' ? <label>Search query<input aria-label="YouTube search query" value={youtubeQuery} onChange={event=>setYoutubeQuery(event.target.value)} placeholder="e.g. cinematic courtroom scene"/></label> : <label>YouTube URLs<textarea aria-label="YouTube URLs" value={youtubeUrls} onChange={event=>setYoutubeUrls(event.target.value)} placeholder="Paste one YouTube URL per line"/></label>}
      <button className="generate-button" type="button" disabled={busy||!workspaceId||(youtubeMode==='search'?!youtubeQuery.trim():!youtubeUrls.trim())} onClick={()=>void findYoutubeSources()}><Search size={15}/>{busy?'Searching…':'Find videos'}</button>
      {youtubeCandidates.length>0&&<><SelectionToggle selected={youtubeSelected} shown={youtubeCandidates.map(row=>row.url)} onChange={setYoutubeSelected} disabled={busy}/><p>{youtubeSelected.length} of {youtubeCandidates.length} selected</p><div className="summariser-analysis-picker">{youtubeCandidates.map(item=><label key={item.url}><input type="checkbox" checked={youtubeSelected.includes(item.url)} onChange={()=>setYoutubeSelected(rows=>rows.includes(item.url)?rows.filter(url=>url!==item.url):[...rows,item.url])}/><span title={item.title}>{item.title || item.url}{item.channel?` · ${item.channel}`:''}</span></label>)}</div><button className="generate-button" type="button" disabled={busy||!youtubeSelected.length} onClick={()=>void downloadYoutube()}><Download size={15}/>{busy?'Starting…':'Download selected'}</button></>}
      {youtubeJob&&<article className="card summariser-job-detail"><h3>{youtubeJob.message}</h3><p>{youtubeJob.status} · {youtubeJob.progress}%</p><progress max="100" value={youtubeJob.progress}/>{['queued','running','cancel_requested'].includes(youtubeJob.status)&&<button className="quiet-button" type="button" disabled={busy||youtubeJob.status==='cancel_requested'} onClick={()=>void cancelYoutube()}>Cancel</button>}{youtubeJob.error&&<pre className="summariser-error">{youtubeJob.error.slice(0,2000)}</pre>}{youtubeJob.result?.failures?.map((row,index)=><p className="summariser-error" key={`${row.url}-${index}`}>{row.url}: {row.error}</p>)}{youtubeJob.result?.published_assets&&<><h3>Added to this workspace</h3><MediaGrid assets={youtubeJob.result.published_assets} empty=""/></>}</article>}
    </div>}
    {page === 'analyze' && <div className="summariser-status"><h2>Analyze videos</h2><OutputDestination tool="analysis" workspaceId={workspaceId} disabled={busy} onReady={setAnalysisDestinationReady}/><p>{capability?.reason || 'Checking analyzer setup.'}</p><section className="card summariser-gpu-admission" aria-label="Runtime readiness"><div><strong>Runtime readiness</strong><p role="status">{gpuAdmissionBusy ? 'Checking GPU health and workload availability…' : !gpuAdmission ? 'Not checked yet.' : gpuAdmission.available ? `Ready · ${gpuAdmission.free_gib?.toFixed(1) ?? 'Free-memory reading unavailable'}${typeof gpuAdmission.free_gib === 'number' ? ' GiB reported free (informational).' : ' (diagnostic only).'}` : gpuAdmission.reason || 'Not ready.'}</p>{gpuAdmission&&hostMemoryNote(gpuAdmission)&&<small>{hostMemoryNote(gpuAdmission)}</small>}</div><button className="quiet-button" type="button" disabled={gpuAdmissionBusy} onClick={()=>void refreshGpuAdmission()}><RefreshCw size={15}/>{gpuAdmissionBusy?'Checking…':'Recheck runtime readiness'}</button></section><details><summary>Analyzer setup checks</summary><ul>{Object.entries(readiness).map(([name,check])=><li key={name}><b>{name}</b>: {check.state}{check.reason&&` — ${check.reason}`}{check.items&&<ul>{Object.entries(check.items).map(([item,value])=><li key={item}>{item}: {value.state}{value.reason&&` — ${value.reason}`}</li>)}</ul>}</li>)}</ul></details>
      <h3>Choose source videos</h3><SelectionToggle selected={selectedVideoIds} shown={analysisSources.map(asset=>asset.asset_id)} onChange={setSelectedVideoIds} disabled={busy}/><p>{selectedVideoIds.length} selected · {analysisSources.length} not yet analyzed in this workspace</p>
      <div className="summariser-analysis-picker">{sourceVideos.map(asset=><label key={asset.asset_id}><input type="checkbox" checked={selectedVideoIds.includes(asset.asset_id)} onChange={()=>toggleVideo(asset.asset_id)}/><span title={asset.filename}>{asset.filename}{completedSources.has(asset.asset_id) ? " · Analyzed — open analysis" : ""}</span></label>)}{!sourceVideos.length&&<small>No new source videos. Completed analyses are in Results; extracted clips are in Video Assets.</small>}</div>
      <label className="summariser-option"><input type="checkbox" checked={audioAnalysis} onChange={event=>setAudioAnalysis(event.target.checked)}/> Analyze audio and collect transcript, speech, music and sound cues</label>
      {audioAnalysis&&<div className="summariser-audio-options" aria-label="Audio analysis settings">
        <h3>Audio analysis</h3><p>Choose which audio results to analyze. Reusable clips are saved only when selected below.</p>
        <div className="summariser-analysis-picker">{([
          ['extract_source_audio','Preserve source audio'],['extract_preview_mp3','Create MP3 preview'],
          ['detect_speech','Speech and transcript'],['diarize_speakers','Speaker diarization'],
          ['detect_music','Music events'],['detect_sfx','Sound effects and ambience'],
          ['create_audio_embeddings','Audio semantic search data'],['create_av_embeddings','Audio and video search data'],
        ] as const).map(([key,label])=><label key={key}><input aria-label={label} type="checkbox" checked={audioSettings[key]} onChange={event=>setAudioSettings(current=>({...current,[key]:event.target.checked}))}/><span>{label}</span></label>)}</div>
        <div className="summariser-toolbar"><label>Source separation<select aria-label="Audio source separation" value={audioSettings.run_demucs} onChange={event=>setAudioSettings(current=>({...current,run_demucs:event.target.value as AudioAnalysisSettings['run_demucs']}))}><option value="AUTO">Automatic</option><option value="off">Off</option><option value="2-stem">2 stems</option><option value="4-stem">4 stems</option><option value="6-stem">6 stems</option></select></label><label>Scene/change sampling rate (FPS)<input aria-label="Scene change sampling rate" type="number" min="0.5" max="24" step="0.5" value={audioSettings.extract_fps} onChange={event=>setAudioSettings(current=>({...current,extract_fps:Number(event.target.value)}))}/><small>Sampling rate for scene/cut analysis; it is not the source video’s frame rate.</small></label><label>Frame change threshold<input aria-label="Frame change threshold" type="number" min="0" max="1" step="0.01" value={audioSettings.frame_change_threshold} onChange={event=>setAudioSettings(current=>({...current,frame_change_threshold:Number(event.target.value)}))}/></label><label className="summariser-option"><input type="checkbox" checked={audioSettings.adaptive_sampling} onChange={event=>setAudioSettings(current=>({...current,adaptive_sampling:event.target.checked}))}/>Reduce redundant frame samples</label><label className="summariser-option"><input type="checkbox" checked={audioSettings.preserve_scene_anchors} onChange={event=>setAudioSettings(current=>({...current,preserve_scene_anchors:event.target.checked}))}/>Keep scene start and end anchors</label><label className="summariser-option"><input aria-label="Keep temporary decode samples" type="checkbox" checked={audioSettings.keep_intermediate_samples} onChange={event=>setAudioSettings(current=>({...current,keep_intermediate_samples:event.target.checked}))}/>Keep temporary decode samples</label></div>
        <section className="summariser-audio-options" aria-label="Video cut subdivisions"><h3>Cut-to-cut subdivisions</h3><p>Attach timestamped intervals for cuts inside each detected scene. They are estimates from sampled frames, not frame-accurate edit metadata.</p><label className="summariser-option"><input aria-label="Attach cut-to-cut subdivisions" type="checkbox" checked={videoCutSettings.extract_cut_clips} onChange={event=>setVideoCutSettings(current=>({...current,extract_cut_clips:event.target.checked}))}/>Attach cut-to-cut subdivisions</label>{videoCutSettings.extract_cut_clips&&<div className="summariser-toolbar"><label>Change sensitivity<input aria-label="Cut change sensitivity" type="number" min="0.05" max="0.9" step="0.01" value={videoCutSettings.cut_boundary_threshold} onChange={event=>setVideoCutSettings(current=>({...current,cut_boundary_threshold:Number(event.target.value)}))}/></label><label>Minimum cut length (seconds)<input aria-label="Minimum cut length" type="number" min="0.25" max="20" step="0.25" value={videoCutSettings.min_cut_seconds} onChange={event=>setVideoCutSettings(current=>({...current,min_cut_seconds:Number(event.target.value)}))}/></label></div>}</section>
        <h3>Save reusable audio clips</h3><div className="summariser-analysis-picker">{([
          ['collect_voice_examples','Voice examples'],['collect_music_clips','Music clips'],['collect_sfx_clips','SFX and ambience clips'],
        ] as const).map(([key,label])=><label key={key}><input aria-label={`Save ${label}`} type="checkbox" checked={audioSettings[key]} onChange={event=>setAudioSettings(current=>({...current,[key]:event.target.checked}))}/><span>{label}</span></label>)}</div>
      </div>}
      <button className="generate-button" type="button" disabled={busy||!analysisDestinationReady||gpuAdmissionBusy||!capability?.can_analyze||!gpuAdmission?.available||!selectedVideoIds.length} onClick={()=>void analyzeSelected()}><Activity size={15}/>{busy?'Starting…':'Analyze selected videos'}</button>
      {!capability?.can_analyze&&<small>Analysis becomes available when analyzer files, models, container images and the Vibe adapter pass setup checks. Runtime health and operating limits are checked separately above; reported free memory is informational.</small>}
    </div>}
    {page === 'results' && <div className="summariser-results"><div className="summariser-results-heading"><div><h2>Analysis results</h2><p>Current project library</p><p>Completed analyses and their published media are retained in the current project library.</p></div><button className="quiet-button" type="button" onClick={()=>void refreshJobs()}>Refresh</button></div>
      {!jobs.length ? <div className="card summariser-empty">No analysis jobs yet. Select videos on Library, then start one from Analyze.</div> : <div className="summariser-job-layout"><nav aria-label="Analysis jobs" className="summariser-jobs">{jobs.map(job=><button type="button" key={job.job_id} className={activeJob?.job_id===job.job_id?'selected':''} onClick={()=>setActiveJob(job)}><strong>{job.request.source_asset_ids?.length || 0} video(s)</strong><span>{job.status} · {new Date(job.created_at).toLocaleString()}</span></button>)}</nav>{activeJob&&<div className="card summariser-job-detail"><div className="summariser-results-heading"><div><h3>{legacyGpuAdmissionFailure?'Earlier analysis stopped by the old memory check':activeJob.message}</h3><p>{activeJob.stage} · {activeJob.progress}% · {activeJob.status}</p></div><div className="summariser-toolbar">{['queued','running','cancel_requested'].includes(activeJob.status)&&<button className="quiet-button" type="button" disabled={busy||activeJob.status==='cancel_requested'} onClick={()=>void cancelActiveJob()}><X size={15}/>Cancel</button>}{['failed','cancelled','interrupted'].includes(activeJob.status)&&<button className="generate-button" type="button" disabled={busy||gpuAdmissionBusy||!capability?.can_analyze||!gpuAdmission?.available} onClick={()=>void retryActiveJob()}>{busy?'Retrying…':'Retry analysis'}</button>}{['completed','failed','cancelled','interrupted'].includes(activeJob.status)&&<button className="quiet-button" type="button" disabled={busy||samBusy} onClick={()=>void deleteActiveAnalysis()}>Delete analysis</button>}</div></div><progress max="100" value={activeJob.progress}/>
        {legacyGpuAdmissionFailure&&<details><summary>Saved failure message</summary><p>{activeJob.message}</p></details>}
        {['failed','cancelled','interrupted'].includes(activeJob.status)&&<><p className="notice notice-warn" role="note">{legacyGpuAdmissionFailure?'This saved failure came from the old 20 GiB free-memory rule. The current app has removed that limit; reported free memory is informational. Retry checks current runtime readiness before resubmitting.':'This message records why the saved attempt ended at that time. Current runtime readiness is shown below and is checked again before retry.'}</p><section className="card summariser-gpu-admission" aria-label="Runtime readiness before retry"><div><strong>Runtime readiness before retry</strong><p role="status">{gpuAdmissionBusy?'Checking GPU health and workload availability…':!gpuAdmission?'Not checked yet.':gpuAdmission.available?`Ready · ${gpuAdmission.free_gib?.toFixed(1)??'Free-memory reading unavailable'}${typeof gpuAdmission.free_gib==='number'?' GiB reported free (informational).':' (diagnostic only).'}`:gpuAdmission.reason||'Not ready.'}</p>{gpuAdmission&&hostMemoryNote(gpuAdmission)&&<small>{hostMemoryNote(gpuAdmission)}</small>}</div><button className="quiet-button" type="button" disabled={gpuAdmissionBusy||!capability?.can_analyze} onClick={()=>void refreshGpuAdmission()}><RefreshCw size={15}/>{gpuAdmissionBusy?'Checking…':'Recheck runtime readiness'}</button></section></>}
        {activeJob.events?.length>0&&<details><summary>Progress details ({activeJob.events.length})</summary><ol className="summariser-events">{activeJob.events.map((item,index)=><li key={`${item.timestamp}-${index}`}><time>{new Date(item.timestamp).toLocaleTimeString()}</time> {item.message}</li>)}</ol></details>}
        {activeJob.result&&<><details><summary>Extraction stages and limitations</summary>{activeJob.result.audio_analysis?.map(run=><div key={run.run_id}><strong>{run.run_id}</strong>{run.statuses&&<ul>{Object.entries(run.statuses).map(([stage,status])=><li key={stage}>{stage.replaceAll('_',' ')}: {status.replaceAll('_',' ')}</li>)}</ul>}{run.media_collection?.limitations&&<ul>{Object.entries(run.media_collection.limitations).map(([stage,reason])=><li key={stage}>{stage}: {reason}</li>)}</ul>}</div>)}</details><h3>Summaries</h3>{activeJob.result.videos?.map((video,index)=><article className="card summariser-summary" key={`${video.title}-${index}`}><strong>{video.title || `Video ${index+1}`}</strong><p>{video.summary?.detailed_video_summary || video.summary?.brief_video_summary || 'No summary text was returned.'}</p><small>{video.scenes?.length || 0} timestamped scenes</small></article>)}<h3>Added to the shared library</h3><p>Cut clips keep the full video composition. Demucs separates vocals from accompaniment, not overlapping speakers. Music stems may retain sound effects; clean SFX require reviewed sound isolation.</p>{activeJob.result.published_assets?.length ? <MediaGrid assets={assets.filter(asset=>activeJob.result?.published_assets?.some(row=>row.asset_id===asset.asset_id))} empty="All published assets were deleted or archived." onDelete={deleteClip}/> : <p>No derived clips or frames were published for this run.</p>}{samEvents.length>0&&<section className="card summariser-audio-options" aria-label="On-demand sound isolation"><h3>Isolate a detected sound</h3><p>Choose an analyzed event and describe the sound to separate, such as “bird chirping”. SAM Audio makes a temporary preview for you to listen to and explicitly save or discard. Separation quality needs listening review.</p><p role="status">SAM Audio: {samCapability ? samCapability.available ? 'Ready' : samCapability.reason || 'Unavailable' : 'Checking readiness…'}</p><div className="summariser-toolbar"><label>Detected event<select aria-label="Detected audio event" value={samSelection||`${samEvents[0].run_id}|${samEvents[0].event.event_id}`} onChange={event=>setSamSelection(event.target.value)}>{samEvents.map(row=><option key={`${row.run_id}|${row.event.event_id}`} value={`${row.run_id}|${row.event.event_id}`}>{row.event.label||row.event.event_type||'Audio event'} · {Number(row.event.start_time_sec).toFixed(1)}–{Number(row.event.end_time_sec).toFixed(1)}s · {row.asset_id}</option>)}</select></label><label>Sound to isolate<input aria-label="Sound isolation prompt" maxLength={500} value={samPrompt} onChange={event=>setSamPrompt(event.target.value)} placeholder="For example: the distant crowd cheering"/></label><button className="generate-button" type="button" disabled={samBusy||!samPrompt.trim()||!samCapability?.available} onClick={()=>void isolateSamEvent()}>{samBusy?'Working…':'Preview isolation'}</button></div>{samPreview?.status==='preview_ready'&&samPreview.temporary_id&&<div className="summariser-audio-options"><p>Temporary preview · {samPreview.model} · {samPreview.prompt}</p><audio controls preload="metadata" src={`/api/video-summariser/${encodeURIComponent(workspaceId)}/sam/previews/${encodeURIComponent(samPreview.temporary_id)}/audio`}/><div className="summariser-toolbar"><button className="generate-button" type="button" disabled={samBusy} onClick={()=>void saveSamPreview()}>{samBusy?'Saving…':'Save to Audio Assets'}</button><button className="quiet-button" type="button" disabled={samBusy} onClick={()=>void discardSamPreview()}>Discard preview</button></div></div>}</section>}{activeJob.result.gpu_usage?.available&&<small>Observed GPU allocation peak: {activeJob.result.gpu_usage.peak_mib} MiB (delta {activeJob.result.gpu_usage.peak_delta_mib} MiB).</small>}</>}
      </div>}</div>}
    </div>}
    {(page === 'audio'||page==='video-assets'||page==='image-assets') && <><div className="summariser-toolbar"><p className="project-context-label">Current project · change with New project or Load project above</p><label className="summariser-search"><Search size={16}/><input aria-label="Search extracted assets" placeholder="Search extracted name or notes" value={query} onChange={event=>setQuery(event.target.value)}/></label></div><p>Extracted {page==='audio'?'audio':page==='image-assets'?'images':'video'} only. Sources remain in Library. Semantic search is available in Search library.</p><div className="summariser-toolbar" aria-label="Bulk extracted asset controls"><SelectionToggle selected={selectedExtractedIds} shown={visibleAssets.map(asset=>asset.asset_id)} onChange={setSelectedExtractedIds} disabled={deletingExtracted}/><span>{selectedExtractedIds.length} selected</span><button type="button" className="quiet-button" disabled={deletingExtracted||!selectedExtractedIds.length} onClick={()=>void deleteExtractedBatch(false)}>Delete selected ({selectedExtractedIds.length})</button><button type="button" className="quiet-button" disabled={deletingExtracted||!extractedAssets.length} onClick={()=>void deleteExtractedBatch(true)}>Delete all {extractedKind} assets ({extractedAssets.length})</button>{deletingExtracted&&<span role="status">Deleting assets…</span>}</div>{page==='video-assets'?<>{[...new Set(visibleAssets.map(asset=>asset.metadata?.analyzer_run_id))].map(runId=><section key={runId} className="card"><h3>Video clip group · {runId}</h3><p>{visibleAssets.find(asset=>asset.metadata?.analyzer_run_id===runId)?.metadata?.analysis_summary || jobs.flatMap(job=>job.result?.audio_analysis||[]).find(run=>run.run_id===runId)?.summary || 'The source video summary is available in Results.'}</p><MediaGrid assets={visibleAssets.filter(asset=>asset.metadata?.analyzer_run_id===runId)} empty="" selectable selectedIds={selectedExtractedIds} onToggle={id=>setSelectedExtractedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id])} disabled={deletingExtracted} onDelete={deleteClip}/></section>)}{!visibleAssets.length&&<p>No extracted video clips in this workspace yet.</p>}</>:<MediaGrid assets={visibleAssets} empty={`No extracted ${page==='image-assets'?'images':'audio clips'} in this workspace yet.`} selectable selectedIds={selectedExtractedIds} onToggle={id=>setSelectedExtractedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id])} disabled={deletingExtracted} onDelete={deleteClip}/>}</>}
  </section>;
}

function ImageDetailer({onBack}:{onBack:()=>void}) {
  const [,setWorkspaces]=useState<StoryWorkspace[]>([]);
  const [workspaceId,setWorkspaceId]=useState(defaultMediaWorkspaceId);
  const [assets,setAssets]=useState<MediaAsset[]>([]);
  const [selectedId,setSelectedId]=useState('');
  const [checkedIds,setCheckedIds]=useState<string[]>([]);
  const removeSelected=async()=>{setBusy(true);let result='';try{result=await deleteSelectedMedia(workspaceId,checkedIds);}catch(e){result=(e as Error).message;}finally{await refresh(workspaceId);setCheckedIds([]);setMessage(result);setBusy(false);}};
  const [pendingImageId,setPendingImageId]=useState(()=>new URLSearchParams(window.location.hash.split('?')[1]||'').get('asset_id')||'');
  const [query,setQuery]=useProjectState('ImageDetailer:query','');
  const [oldestFirst,setOldestFirst]=useState(false);
  const [assetView,setAssetView]=useState<'template'|'list'|'carousel'>(()=>{
    try { const saved=localStorage.getItem('vibe-image-detailer-view-v1'); return saved==='list'||saved==='carousel'?saved:'template'; }
    catch { return 'template'; }
  });
  const [mode,setMode]=useProjectState<'quick'|'balanced'|'deep'>('ImageDetailer:mode','balanced');
  const [jobs,setJobs]=useState<ImageDetailerJob[]>([]);
  const [activeJob,setActiveJob]=useState<ImageDetailerJob|null>(null);
  const [file,setFile]=useState<File|null>(null);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const [gpuAdmission,setGpuAdmission]=useState<GpuAdmission|null>(null);
  const [gpuAdmissionBusy,setGpuAdmissionBusy]=useState(false);

  useEffect(()=>{void listStoryWorkspaces().then(result=>{
    const rows=result.items||[]; setWorkspaces(rows);
    const requestedWorkspace=new URLSearchParams(window.location.hash.split('?')[1]||'').get('workspace_id')||'';
    setWorkspaceId(current=>current||preferredMediaWorkspaceId(rows, requestedWorkspace));
  }).catch(error=>setMessage(`Could not load workspaces: ${(error as Error).message}`));},[]);
  const refresh=async(id:string,isCurrent:()=>boolean=()=>true)=>{
    if(!id){setAssets([]);setJobs([]);setActiveJob(null);return;}
    const [media,history]=await Promise.all([listMediaAssets(id,'image'),listImageDetailerJobs(id)]);
    if(!isCurrent())return;
    setAssets(media.assets);setJobs(history);
    setActiveJob(current=>current?history.find(row=>row.job_id===current.job_id)||null:null);
    setSelectedId(current=>media.assets.some(row=>row.asset_id===current)?current:'');
  };
  useEffect(()=>{
    let current=true;
    setAssets([]);setJobs([]);setActiveJob(null);setSelectedId('');setCheckedIds([]);setMessage('');
    void refresh(workspaceId,()=>current).catch(error=>{if(current)setMessage(`Could not load image library: ${(error as Error).message}`);});
    return()=>{current=false;};
  },[workspaceId]);
  useEffect(()=>{if(!pendingImageId||!assets.length)return;if(assets.some(asset=>asset.asset_id===pendingImageId)){setSelectedId(pendingImageId);setPendingImageId('');}else{setMessage('The selected image is not available in this workspace. Choose it from the image repository.');setPendingImageId('');}},[assets,pendingImageId]);
  useEffect(()=>{setGpuAdmission(null);if(workspaceId)void refreshGpuAdmission();},[workspaceId]);
  useEffect(()=>{if(!selectedId){setActiveJob(null);return;}setActiveJob(current=>jobs.find(job=>job.request.asset_id===selectedId&&(!current||job.job_id===current.job_id))||jobs.find(job=>job.request.asset_id===selectedId)||null);},[selectedId,jobs]);
  useEffect(()=>{
    if(!workspaceId||!activeJob||!['queued','running','cancel_requested'].includes(activeJob.status))return;
    let current=true;
    const timer=window.setInterval(()=>void getImageDetailerJob(workspaceId,activeJob.job_id).then(job=>{
      if(!current)return;setActiveJob(job);setJobs(rows=>[job,...rows.filter(row=>row.job_id!==job.job_id)]);
    }).catch(error=>{if(current)setMessage(`Could not refresh image analysis: ${(error as Error).message}`);}),2000);
    return()=>{current=false;window.clearInterval(timer);};
  },[workspaceId,activeJob?.job_id,activeJob?.status]);
  const visible=useMemo(()=>assets.filter(asset=>[asset.filename,asset.description,...(asset.tags||[])].filter(Boolean).join(' ').toLowerCase().includes(query.trim().toLowerCase())).sort((a,b)=>{
    const order=Date.parse(a.created_at)-Date.parse(b.created_at);return oldestFirst?order:-order;
  }),[assets,query,oldestFirst]);
  useEffect(()=>setCheckedIds([]),[query]);
  const chooseAssetView=(view:'template'|'list'|'carousel')=>{
    setAssetView(view);
    try { localStorage.setItem('vibe-image-detailer-view-v1',view); } catch { /* Keep this view for the current page. */ }
  };
  const selected=assets.find(asset=>asset.asset_id===selectedId&&asset.workspace_id===workspaceId);
  const refreshGpuAdmission=async()=>{
    setGpuAdmissionBusy(true);
    try{setGpuAdmission(await checkVideoGpuAdmission());}
    catch(error){setGpuAdmission({available:false,checked:true,reason:(error as Error).message});}
    finally{setGpuAdmissionBusy(false);}
  };
  const addImage=async()=>{
    if(!workspaceId||!file)return;setBusy(true);setMessage('');
    try{const result=await uploadMediaAsset(workspaceId,file,'project_image');await refresh(workspaceId);if(result.asset_id)setSelectedId(result.asset_id);setFile(null);setMessage('Image added to the shared library.');}
    catch(error){setMessage(`Could not add image: ${(error as Error).message}`);}finally{setBusy(false);}
  };
  const analyze=async()=>{
    if(!workspaceId||!selected)return;setBusy(true);setGpuAdmissionBusy(true);setMessage('');
    try{const admission=await checkVideoGpuAdmission();setGpuAdmission(admission);if(!admission.available){setMessage(admission.reason||'GPU is not ready for image analysis.');return;}const job=await startImageDetailerJob(workspaceId,selectedId,mode);setActiveJob(job);setJobs(rows=>[job,...rows.filter(row=>row.job_id!==job.job_id)]);}
    catch(error){setMessage(`Could not start image analysis: ${(error as Error).message}`);}finally{setBusy(false);setGpuAdmissionBusy(false);}
  };
  const cancel=async()=>{if(!workspaceId||!activeJob)return;setBusy(true);try{const job=await cancelImageDetailerJob(workspaceId,activeJob.job_id);setActiveJob(job);}catch(error){setMessage(`Could not cancel: ${(error as Error).message}`);}finally{setBusy(false);}};
  const retry=async()=>{if(!workspaceId||!activeJob)return;setBusy(true);setGpuAdmissionBusy(true);try{const admission=await checkVideoGpuAdmission();setGpuAdmission(admission);if(!admission.available){setMessage(admission.reason||'GPU is not ready for image analysis.');return;}const job=await retryImageDetailerJob(workspaceId,activeJob.job_id);setActiveJob(job);}catch(error){setMessage(`Could not retry: ${(error as Error).message}`);}finally{setBusy(false);setGpuAdmissionBusy(false);}};
  const saveAnalysis=async()=>{
    if(!workspaceId||!selected||!activeJob||!analysis)return;
    if((selected.description||selected.tags?.length)&&!window.confirm('Replace this image’s current search description and tags with the analysis?'))return;
    const terms=(value:unknown)=> (Array.isArray(value)?value:[value]).flatMap(item=>typeof item==='string'?[item]:item&&typeof item==='object'&&'name'in item?[String((item as {name:unknown}).name)]:[]);
    const tags=[...new Set([...terms(analysis.analysis?.subjects),...terms(analysis.analysis?.objects),...terms(analysis.analysis?.palette),...terms(analysis.analysis?.mood)])].filter(Boolean).slice(0,40);
    const description=[summary,frameCard.setting||analysis.analysis?.setting].filter(Boolean).join(' — ').slice(0,2000);
    setBusy(true);setMessage('');
    try{const saved=await saveImageAnalysis(workspaceId,selected.asset_id,{job_id:activeJob.job_id,source_sha256:activeJob.request.sha256,mode:activeJob.request.mode,analysis,description,tags});setAssets(rows=>rows.map(row=>row.asset_id===saved.asset_id?saved:row));setMessage('Image analysis and search details saved to the shared library.');}
    catch(error){setMessage(`Could not save search details: ${(error as Error).message}`);}finally{setBusy(false);}
  };
  const indexSavedDetails=async()=>{
    if(!workspaceId||!selected)return;setBusy(true);setMessage('');
    try{const result=await indexMediaAssetAnnotations(workspaceId,selected.asset_id);setAssets(rows=>rows.map(row=>row.asset_id===result.asset.asset_id?result.asset:row));setMessage('Saved image details indexed for semantic search. Image pixels are not embedded.');}
    catch(error){setMessage(`Could not index saved image details: ${(error as Error).message}`);}finally{setBusy(false);}
  };
  const analysis=activeJob?.result?.analysis;
  const imageJobError=activeJob?.error?.split(/\nTraceback \(most recent call last\):/)[0].trim();
  const frameCard=analysis?.frame_card||{};
  const summary=frameCard.summary||analysis?.analysis?.summary||analysis?.analysis?.description||'';
  const inputEvidence=analysis?.input;
  const specialistEvidence=analysis?.specialist_evidence;
  return <section className="card summariser-page" aria-label="Image Detailer">
    <button className="quiet-button summariser-back" type="button" onClick={onBack}>← Images</button>
    <header className="summariser-heading"><div><div className="eyebrow">MEDIA PREP / IMAGE DETAILER</div><h1>Image Detailer</h1><p>Analyze an image already in the selected collection.</p></div><span className="media-prep-state">Uses the copied local analyzer</span></header>
    {message&&<p className="notice" role="status">{message}</p>}
    <MediaSourcePicker workspaceId={workspaceId} kinds={['image']} disabled={busy} onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/>
    <div className="summariser-toolbar"><p className="project-context-label">Current project · change with New project or Load project above</p><label className="summariser-upload">Add image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={event=>{const next=event.currentTarget.files?.[0]||null;event.currentTarget.value='';setFile(next);}}/><small>PNG, JPEG or WebP</small></label><button className="quiet-button" type="button" disabled={busy||!file||!workspaceId} onClick={()=>void addImage()}><FileUp size={15}/>Add to library</button></div>
    <div className="summariser-toolbar image-detailer-search"><label className="summariser-search"><Search size={16}/><input aria-label="Search image repertoire" placeholder="Search images by name or notes" value={query} onChange={event=>setQuery(event.target.value)}/></label><span className="media-prep-state">{visible.length} images</span><button className="quiet-button media-sort" type="button" onClick={()=>setOldestFirst(value=>!value)} aria-label={oldestFirst?'Sort newest first':'Sort oldest first'} title={oldestFirst?'Oldest first':'Newest first'}>{oldestFirst?'↑':'↓'}</button><div className="asset-view-switch" role="group" aria-label="Image repository view">{([{id:'template',label:'Template view',icon:<LayoutGrid size={15}/>},{id:'list',label:'List view',icon:<List size={15}/>},{id:'carousel',label:'Carousel view',icon:<GalleryHorizontal size={15}/>} ] as const).map(option=><button type="button" key={option.id} className="quiet-button" aria-label={option.label} aria-pressed={assetView===option.id} onClick={()=>chooseAssetView(option.id)}>{option.icon}<span>{option.id === 'template' ? 'Cards' : option.id === 'list' ? 'List' : 'Carousel'}</span></button>)}</div></div>
    <section className="card summariser-gpu-admission" aria-label="Runtime readiness"><div><strong>Runtime readiness for Image Detailer</strong><p role="status">{gpuAdmissionBusy?'Checking GPU health and workload availability…':!gpuAdmission?'Not checked yet.':gpuAdmission.available?`Ready · ${gpuAdmission.free_gib?.toFixed(1)??'Free-memory reading unavailable'}${typeof gpuAdmission.free_gib==='number'?' GiB reported free (informational).':' (diagnostic only).'}`:gpuAdmission.reason||'Not ready.'}</p>{gpuAdmission&&hostMemoryNote(gpuAdmission)&&<small>{hostMemoryNote(gpuAdmission)}</small>}</div><button className="quiet-button" type="button" disabled={gpuAdmissionBusy||busy||!workspaceId} onClick={()=>void refreshGpuAdmission()}><RefreshCw size={15}/>{gpuAdmissionBusy?'Checking…':'Recheck runtime readiness'}</button></section>
    <div className="summariser-toolbar"><label>Analysis depth<select aria-label="Image analysis depth" value={mode} onChange={event=>setMode(event.target.value as typeof mode)}><option value="quick">Quick</option><option value="balanced">Balanced</option><option value="deep">Deep</option></select></label><button className="generate-button" type="button" disabled={busy||gpuAdmissionBusy||!gpuAdmission?.available||!selectedId} onClick={()=>void analyze()}><Activity size={15}/>{busy?'Working…':'Start analysis'}</button></div>
    <div className="summariser-toolbar" aria-label="Image management"><button className="quiet-button" disabled={busy} onClick={()=>setCheckedIds(visible.map(a=>a.asset_id))}>Select all shown ({visible.length})</button><button className="quiet-button" disabled={busy||!checkedIds.length} onClick={()=>setCheckedIds([])}>Deselect all</button><span>{checkedIds.length} selected for management</span><button className="quiet-button" disabled={busy||!checkedIds.length} onClick={()=>void removeSelected()}>Delete files permanently</button><button className="quiet-button" disabled={!selectedId||busy} onClick={()=>setSelectedId('')}>Deselect analysis image</button></div>
    <p role="status">{selected?`Analysis target: ${selected.filename}`:'Choose an image preview to analyze. Checkboxes select files for management.'}</p>
    <div className="image-detailer-layout"><div className={`summariser-assets image-detailer-gallery image-repository-${assetView}`} aria-label="Image repository">{visible.map(asset=><article className="card image-detailer-item" key={asset.asset_id}><label><input type="checkbox" aria-label={`Select ${asset.filename}`} disabled={busy} checked={checkedIds.includes(asset.asset_id)} onChange={()=>setCheckedIds(ids=>ids.includes(asset.asset_id)?ids.filter(id=>id!==asset.asset_id):[...ids,asset.asset_id])}/> Select</label><button type="button" className={`card summariser-asset image-detailer-choice ${selectedId===asset.asset_id?'selected':''}`} aria-pressed={selectedId===asset.asset_id} onClick={()=>setSelectedId(current=>current===asset.asset_id?'':asset.asset_id)}><div className="summariser-preview"><img src={asset.content_url} alt={asset.description||asset.filename} loading="lazy"/></div><strong title={asset.filename}>{asset.filename}</strong><small>{asset.description||asset.provenance_notes||asset.roles.join(' · ')}</small></button></article>)}{!visible.length&&<div className="card summariser-empty">{workspaceId?'No images in this workspace yet.':'Create or select a story workspace first.'}</div>}</div>
    <div className="image-detailer-report">{selected&&<img className="image-detailer-selected" src={selected.content_url} alt={selected.filename}/>}
    {activeJob&&<article className="card summariser-job-detail"><header className="summariser-results-heading"><div><h2>{activeJob.message}</h2><p>{activeJob.request.mode} · {activeJob.status} · {activeJob.progress}%</p></div>{['queued','running','cancel_requested'].includes(activeJob.status)?<button className="quiet-button" type="button" disabled={busy||activeJob.status==='cancel_requested'} onClick={()=>void cancel()}>Cancel</button>:['failed','cancelled','interrupted'].includes(activeJob.status)?<button className="generate-button" type="button" disabled={busy||gpuAdmissionBusy||!gpuAdmission?.available} onClick={()=>void retry()}>Retry</button>:null}</header><progress max="100" value={activeJob.progress}/>{imageJobError&&<pre className="summariser-error">{imageJobError.slice(0,500)}</pre>}{activeJob.events.length>0&&<details><summary>Progress</summary><ol className="summariser-events">{activeJob.events.map((event,index)=><li key={`${event.timestamp}-${index}`}>{event.message}</li>)}</ol></details>}{analysis&&<><h3>{summary||'Analysis complete'}</h3><p>{frameCard.setting||analysis.analysis?.setting||''}</p><section className="card image-detailer-evidence" aria-label="Input evidence"><h3>Input evidence</h3><p>{inputEvidence?.filename||activeJob.result?.filename}{inputEvidence?.width&&inputEvidence?.height?` · ${inputEvidence.width}×${inputEvidence.height}`:''}</p><p>Model: {analysis.model||'Not reported'} · Analysis mode: {analysis.mode||activeJob.request.mode} · Detected objects: {specialistEvidence?.detections?.length??0}</p>{analysis.warnings?.map((warning,index)=><p className="notice" key={`${index}-${warning}`}>{warning}</p>)}</section><dl className="image-detailer-facts">{[['Subjects',frameCard.subjects||analysis.analysis?.subjects],['Objects',frameCard.objects||analysis.analysis?.objects],['Actions',frameCard.action_state||analysis.analysis?.actions],['Camera',frameCard.camera||analysis.analysis?.camera],['Lighting',frameCard.lighting||analysis.analysis?.lighting],['Mood',analysis.analysis?.mood],['Continuity',analysis.analysis?.continuity_facts],['Uncertainties',frameCard.uncertainties||analysis.analysis?.uncertainties]].map(([label,value])=><div key={String(label)}><dt>{label}</dt><dd>{Array.isArray(value)?value.map(item=>typeof item==='string'?item:JSON.stringify(item)).join(' · '):String(value||'—')}</dd></div>)}</dl><div className="summariser-toolbar"><button className="quiet-button" type="button" disabled={busy||!selected||selected.asset_id!==activeJob.request.asset_id} onClick={()=>void saveAnalysis()}>Save analysis to image search</button><button className="quiet-button" type="button" disabled={busy||!selected} onClick={()=>void indexSavedDetails()} title="Uses PE-AV text embeddings for saved image details; it does not embed image pixels">{selected?.semantic_annotation_index?'Reindex saved details':'Index saved details for semantic search'}</button></div><details><summary>Full structured result</summary><pre className="summariser-error">{JSON.stringify(analysis,null,2)}</pre></details></>}</article>}{!activeJob&&<p>{selected?'Choose the analysis depth and click Start analysis.':'Select an image to preview and analyze.'}</p>}</div></div>
  </section>;
}

function AudioStudio({onBack}:{onBack:()=>void}) {
  const [ttsDestinationReady,setTtsDestinationReady]=useState(false),[effectDestinationReady,setEffectDestinationReady]=useState(false);
  const [,setWorkspaces]=useState<StoryWorkspace[]>([]);
  const [workspaceId,setWorkspaceId]=useState(defaultMediaWorkspaceId);
  const [voiceBindings,setVoiceBindings]=useState<CharacterVoiceState|null>(null);
  const [voiceBindingsLoaded,setVoiceBindingsLoaded]=useState(false);
  const [assets,setAssets]=useState<MediaAsset[]>([]);
  const [voices,setVoices]=useState<AudioVoice[]>([]);
  const [models,setModels]=useState<AudioModel[]>([]);
  const [capabilities,setCapabilities]=useState<AudioCapabilities|null>(null);
  const [selectedId,setSelectedId]=useState('');
  const [voiceQuery,setVoiceQuery]=useProjectState('AudioStudio:voiceQuery','');
  const [audioQuery,setAudioQuery]=useProjectState('AudioStudio:audioQuery','');
  const [name,setName]=useProjectState('AudioStudio:name','');
  const [transcript,setTranscript]=useProjectState('AudioStudio:transcript','');
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const [srt,setSrt]=useProjectState('AudioStudio:srt','');
  const [speakerVoices,setSpeakerVoices]=useProjectState<Record<string,{voiceId:string;language:string}>>('AudioStudio:speakerVoices',{});
  const [timingMode,setTimingMode]=useProjectState('AudioStudio:timingMode','smart_natural');
  const [ttsParameters,setTtsParameters]=useProjectState('AudioStudio:ttsParameters',{seed:1,exaggeration:.5,temperature:.8,cfg_weight:.5,enable_audio_cache:true,fade:.01,max_stretch_ratio:1,min_stretch_ratio:.5,timing_tolerance:2,batch_size:0});
  const [ttsJob,setTtsJob]=useState<TimedTTSJob|null>(null);
  const [f5Dataset,setF5Dataset]=useProjectState('AudioStudio:f5Dataset','voice_dataset');
  const [f5Model,setF5Model]=useProjectState('AudioStudio:f5Model','F5TTS_v1_Base');
  const [f5Samples,setF5Samples]=useProjectState<Record<string,string>>('AudioStudio:f5Samples',{});
  const [f5Job,setF5Job]=useState<F5PreparationJob|null>(null);
  const [effectCapabilities,setEffectCapabilities]=useState<AudioEffectCapabilities|null>(null);
  const [effectJob,setEffectJob]=useState<AudioEffectJob|null>(null);
  const [effectOperation,setEffectOperation]=useProjectState<'simple'|'noise_cleanup'|'voice_repair'|'voice_changer'|'rvc'|'emotion'|'style'>('AudioStudio:effectOperation','voice_repair');
  const [simplePreset,setSimplePreset]=useProjectState('AudioStudio:simplePreset','deep');
  const [simpleStrength,setSimpleStrength]=useProjectState('AudioStudio:simpleStrength',.5);
  const [effectVoice,setEffectVoice]=useProjectState('AudioStudio:effectVoice','');
  const [effectTranscript,setEffectTranscript]=useProjectState('AudioStudio:effectTranscript','');
  const [effectChoice,setEffectChoice]=useProjectState('AudioStudio:effectChoice','happy');
  const [effectRestoration,setEffectRestoration]=useProjectState('AudioStudio:effectRestoration',0);
  const [effectAggressiveness,setEffectAggressiveness]=useProjectState('AudioStudio:effectAggressiveness',10);
  const [effectPasses,setEffectPasses]=useProjectState('AudioStudio:effectPasses',1);
  const [effectPitch,setEffectPitch]=useProjectState('AudioStudio:effectPitch',0);
  const [rvcModel,setRvcModel]=useProjectState('AudioStudio:rvcModel','');
  const [rvcIndex,setRvcIndex]=useProjectState('AudioStudio:rvcIndex','');
  const refresh=async()=>{
    const [voiceRows,modelRows,ready]=await Promise.all([listAudioVoices(),listAudioModels(),getAudioCapabilities()]);
    setVoices(voiceRows);setModels(modelRows);setCapabilities(ready);
  };
  useEffect(()=>{void getAudioEffectCapabilities().then(setEffectCapabilities).catch(error=>setMessage(`Could not check audio effects: ${(error as Error).message}`));},[]);
  useEffect(()=>{void Promise.all([listStoryWorkspaces(),refresh()]).then(([result])=>{
    const rows=result.items||[];setWorkspaces(rows);
    const requestedWorkspace=new URLSearchParams(window.location.hash.split('?')[1]||'').get('workspace_id')||'';
    setWorkspaceId(current=>current||preferredMediaWorkspaceId(rows, requestedWorkspace));
  }).catch(error=>setMessage(`Could not load Audio Studio: ${(error as Error).message}`));},[]);
  useEffect(()=>{if(!workspaceId){setAssets([]);return;}let active=true;void listMediaAssets(workspaceId,'audio').then(result=>{if(active){setAssets(result.assets);setSelectedId(current=>result.assets.some(row=>row.asset_id===current)?current:result.assets[0]?.asset_id||'');}}).catch(error=>{if(active)setMessage(`Could not load audio clips: ${(error as Error).message}`);});return()=>{active=false;}},[workspaceId]);
  useEffect(()=>{if(!workspaceId.startsWith('story-')){setVoiceBindings(null);setVoiceBindingsLoaded(true);return;}let active=true;setVoiceBindings(null);setVoiceBindingsLoaded(false);void listStoryScreenplays(workspaceId,0,100).then(page=>{const accepted=page.items.find(row=>row.accepted&&!row.stale);return accepted?getCharacterVoiceState(workspaceId,accepted.screenplay_revision_id):null;}).then(state=>{if(active){setVoiceBindings(state);setVoiceBindingsLoaded(true);}}).catch(()=>{if(active){setVoiceBindings(null);setVoiceBindingsLoaded(true);}});return()=>{active=false;}},[workspaceId]);
  useEffect(()=>{if(!workspaceId)return;let active=true;void listTimedTTSJobs(workspaceId).then(rows=>{if(active)setTtsJob(rows.find(row=>['queued','running','submitting'].includes(row.status))||rows[0]||null);}).catch(error=>{if(active)setMessage(`Could not load timed-audio jobs: ${(error as Error).message}`);});return()=>{active=false;}},[workspaceId]);
  useEffect(()=>{if(!workspaceId)return;let active=true;void listF5PreparationJobs(workspaceId).then(rows=>{if(active)setF5Job(rows[0]||null);}).catch(error=>{if(active)setMessage(`Could not load F5 preparation jobs: ${(error as Error).message}`);});return()=>{active=false;}},[workspaceId]);
  useEffect(()=>{if(!workspaceId||!f5Job||!['queued','running'].includes(f5Job.status))return;let active=true;const timer=window.setInterval(()=>void getF5PreparationJob(workspaceId,f5Job.job_id).then(row=>{if(active)setF5Job(row);}).catch(error=>{if(active)setMessage(`Could not refresh F5 preparation: ${(error as Error).message}`);}),2000);return()=>{active=false;window.clearInterval(timer);};},[workspaceId,f5Job?.job_id,f5Job?.status]);
  useEffect(()=>{if(!workspaceId||!ttsJob||!['queued','running','submitting'].includes(ttsJob.status))return;let active=true;const timer=window.setInterval(()=>void getTimedTTSJob(workspaceId,ttsJob.job_id).then(row=>{if(active)setTtsJob(row);}).catch(error=>{if(active)setMessage(`Could not refresh timed audio: ${(error as Error).message}`);}),2000);return()=>{active=false;window.clearInterval(timer);};},[workspaceId,ttsJob?.job_id,ttsJob?.status]);
  useEffect(()=>{if(!workspaceId)return;let active=true;void listAudioEffectJobs(workspaceId).then(rows=>{if(active)setEffectJob(rows.find(row=>['queued','running','submitting'].includes(row.status))||rows[0]||null);}).catch(error=>{if(active)setMessage(`Could not load audio-effect jobs: ${(error as Error).message}`);});return()=>{active=false;}},[workspaceId]);
  useEffect(()=>{if(!workspaceId||!effectJob||!['queued','running','submitting'].includes(effectJob.status))return;let active=true;const timer=window.setInterval(()=>void getAudioEffectJob(workspaceId,effectJob.job_id).then(row=>{if(active)setEffectJob(row);}).catch(error=>{if(active)setMessage(`Could not refresh audio effect: ${(error as Error).message}`);}),2000);return()=>{active=false;window.clearInterval(timer);};},[workspaceId,effectJob?.job_id,effectJob?.status]);
  useEffect(()=>{if(!effectCapabilities?.rvc_models.length)return;setRvcModel(current=>effectCapabilities.rvc_models.some(row=>row.id===current)?current:effectCapabilities.rvc_models[0].id);},[effectCapabilities]);
  useEffect(()=>{if(!effectVoice&&voices.some(voice=>voice.discoverable))setEffectVoice(voices.find(voice=>voice.discoverable)!.id);},[effectVoice,voices]);
  useEffect(()=>{const indexes=effectCapabilities?.rvc_models.find(row=>row.id===rvcModel)?.indexes||[];setRvcIndex(current=>indexes.includes(current)?current:indexes[0]||'');},[effectCapabilities,rvcModel]);
  useEffect(()=>{if(effectJob?.status==='completed'&&effectJob.result?.asset)setAssets(current=>current.some(row=>row.asset_id===effectJob.result?.asset?.asset_id)?current:[effectJob.result!.asset!,...current]);},[effectJob?.status,effectJob?.result?.asset?.asset_id]);
  const visible=useMemo(()=>assets.filter(asset=>[asset.filename,asset.description,...(asset.tags||[])].filter(Boolean).join(' ').toLowerCase().includes(audioQuery.trim().toLowerCase())).sort((a,b)=>b.created_at.localeCompare(a.created_at)),[assets,audioQuery]);
  const speakers=useMemo(()=>{const found=new Set<string>();for(const match of srt.matchAll(/\[\s*(?!pause\s*:)(?:[^:\]\n]+\s*:\s*)?([^\]\n]+)\s*\]/gi)){const name=match[1].trim();if(name&&!/^\d/.test(name))found.add(name);}return [...found];},[srt]);
  const boundVoiceForSpeaker=(speaker:string)=>{const character=voiceBindings?.characters.find(row=>row.name.trim().toLocaleLowerCase()===speaker.trim().toLocaleLowerCase());if(!character)return null;const binding=voiceBindings?.bindings.find(row=>row.character_id===character.record_id);if(!binding)return null;const asset=assets.find(row=>row.asset_id===binding.voice_asset_id);if(!asset)return {asset:null,voice:null};const catalogId=asset.metadata?.comfyui_voice_catalog?.catalog_id;return {asset,voice:typeof catalogId==='string'?voices.find(row=>row.id===catalogId&&row.discoverable)||null:null};};
  const selected=assets.find(asset=>asset.asset_id===selectedId);
  useEffect(()=>{setSpeakerVoices(current=>{const next={...current};for(const speaker of speakers)next[speaker]??={voiceId:'',language:'en'};for(const name of Object.keys(next))if(!speakers.includes(name))delete next[name];return next;});},[speakers,voices]);
  const enroll=async()=>{if(!workspaceId||!selected||!name.trim()||!transcript.trim())return;setBusy(true);setMessage('');try{const result=await enrollAudioVoice(workspaceId,selected.asset_id,name,transcript);setAssets(rows=>rows.map(asset=>asset.asset_id===result.asset.asset_id?result.asset:asset));await refresh();setMessage(result.restart_required?'Voice file installed. It is now in Voice Files; ComfyUI did not expose it yet, so refresh its voice node before using it.':'Voice file installed, added to Voice Files, and discovered by ComfyUI.');}catch(error){setMessage(`Could not add voice: ${(error as Error).message}`);}finally{setBusy(false);}};
  const refreshLiveVoices=async()=>{setBusy(true);setMessage('');try{const result=await refreshAudioVoices();await refresh();setMessage(result.restart_required?'Voice list refreshed, but ComfyUI still needs a restart to discover some files.':`Voice list refreshed. ComfyUI sees ${result.live_count} reference voices.`);}catch(error){setMessage(`Could not refresh ComfyUI voices: ${(error as Error).message}`);}finally{setBusy(false);}};
  const generateTimedAudio=async()=>{if(!workspaceId||!srt.trim()||!speakers.length)return;setBusy(true);setMessage('');try{const rows=speakers.map(speaker=>({name:speaker,reference_voice_id:speakerVoices[speaker]?.voiceId||'',language:speakerVoices[speaker]?.language||'en'}));const job=await createTimedTTSJob(workspaceId,{srt_content:srt,characters:rows,settings:{language:'English',timing_mode:timingMode,...ttsParameters}});setTtsJob(job);setMessage('Timed dialogue audio queued.');}catch(error){setMessage(`Could not start timed audio: ${(error as Error).message}`);}finally{setBusy(false);}};
  const prepareF5Dataset=async()=>{if(!workspaceId)return;const samples=Object.entries(f5Samples).filter(([,text])=>text.trim()).map(([asset_id,text])=>({asset_id,text}));if(!samples.length)return;setBusy(true);setMessage('');try{const job=await createF5PreparationJob(workspaceId,{dataset_name:f5Dataset,base_model:f5Model,samples});setF5Job(job);setMessage('F5 dataset preparation queued. Training will not start.');}catch(error){setMessage(`Could not prepare F5 dataset: ${(error as Error).message}`);}finally{setBusy(false);}};
  const runEffect=async(preview=false)=>{if(!workspaceId||!selected)return;setBusy(true);setMessage('');try{const settings:Record<string,unknown>={};if(effectOperation==='simple')Object.assign(settings,{preset:simplePreset,strength:simpleStrength,preview});if(effectOperation==='noise_cleanup')Object.assign(settings,{model:'UVR/UVR-DeNoise.pth',aggressiveness:effectAggressiveness,use_cache:true});if(effectOperation==='voice_repair')Object.assign(settings,{restoration_mode:effectRestoration,use_cuda:true});if(effectOperation==='voice_changer')Object.assign(settings,{target_voice_id:effectVoice,language:'local:English',refinement_passes:effectPasses,max_chunk_duration:30,chunk_method:'smart'});if(effectOperation==='rvc')Object.assign(settings,{model:rvcModel,index_file:rvcIndex,pitch:effectPitch,pitch_detection:'rmvpe',index_ratio:.75,consonant_protection:.25,volume_envelope:.25,refinement_passes:effectPasses,max_chunk_duration:30,chunk_method:'smart'});if(effectOperation==='emotion'||effectOperation==='style'){settings.transcript=effectTranscript;settings[effectOperation]=effectChoice;settings.iterations=effectPasses;}const job=await createAudioEffectJob(workspaceId,effectOperation,selected.asset_id,settings);setEffectJob(job);setMessage(`${effectCapabilities?.operations.find(row=>row.id===effectOperation)?.label||'Audio effect'} queued.`);}catch(error){setMessage(`Could not start audio effect: ${(error as Error).message}`);}finally{setBusy(false);}};
  return <><button className="quiet-button summariser-back" type="button" onClick={onBack}>← Audio tools</button><EditorWorkspace name="audio-studio" rightLabel="audio controls" preview={<section className="card summariser-page" aria-label="Audio Studio">
    <header className="summariser-heading"><div><div className="eyebrow">MEDIA PREP / AUDIO STUDIO</div><h1>Audio Studio</h1><p>Browse ComfyUI voice references and explicitly enroll a library clip for voice workflows.</p></div><span className="media-prep-state">{capabilities?.comfyui_online?'ComfyUI online':capabilities?'ComfyUI offline':'Checking'}</span></header>
    {message&&<p className="notice" role="status">{message}</p>}
    <MediaSourcePicker workspaceId={workspaceId} kinds={['audio']} disabled={busy} onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/>
    <div className="summariser-toolbar"><p className="project-context-label">Current project · change with New project or Load project above</p><span className="media-prep-state">{voices.length} voices · {models.length} TTS models</span></div>
    {!capabilities?.comfyui_root_exists&&<p className="notice">ComfyUI model folder was not found. Set COMFYUI_ROOT to the configured ComfyUI installation.</p>}
    <VoiceRecorder workspaceId={workspaceId} onSaved={(asset,use)=>{setAssets(rows=>[asset,...rows.filter(r=>r.asset_id!==asset.asset_id)]);setSelectedId(asset.asset_id);if(use==='Use for conversion')setEffectOperation('simple');if(use==='Use in Vibe Editor'){sessionStorage.setItem('vibe-editor-pending-audio',JSON.stringify({workspace_id:workspaceId,asset}));window.location.hash='/editor';}setMessage(use==='Use in Vibe Editor'?'Recording saved. Open Vibe Editor and select it from this workspace’s audio library.':use==='Use as voice reference'?'Recording selected. Enter its exact transcript and voice name in Enroll a library clip below.':'Recording saved and selected.');}}/>
    <VoiceStudioTools key={workspaceId} workspaceId={workspaceId} voices={voices} assets={assets} onAudio={(asset,text)=>{setAssets(rows=>[asset,...rows.filter(r=>r.asset_id!==asset.asset_id)]);setSelectedId(asset.asset_id);setTranscript(text);setMessage('Audio selected. Enter a voice name and click Add to ComfyUI voices below to save it as a reference.');}}/>
    <section className="card timed-tts-panel"><h2>Timed dialogue to audio</h2><p>Paste SRT with timestamps. Add speaker tags such as <code>[Arjun]</code> and pauses such as <code>[pause:1s]</code>; assign each speaker a ComfyUI voice.</p>
      <label>Timed dialogue (SRT)<textarea aria-label="Timed dialogue SRT" value={srt} onChange={event=>setSrt(event.target.value)} rows={9} maxLength={500000} placeholder={'1\n00:00:00,000 --> 00:00:02,500\n[Arjun] We should leave now. [pause:500ms]'} /></label>
      {speakers.length>0&&<div className="timed-tts-speakers"><h3>Speaker voices</h3>{speakers.map(speaker=>{const bound=boundVoiceForSpeaker(speaker);return <div className="timed-tts-speaker" key={speaker}><strong>{speaker}</strong><label>Voice<select aria-label={`${speaker} voice`} value={speakerVoices[speaker]?.voiceId||''} onChange={event=>setSpeakerVoices(current=>({...current,[speaker]:{...current[speaker],voiceId:event.target.value}}))}><option value="">Choose a voice</option>{voices.filter(voice=>voice.discoverable).map(voice=><option key={voice.id} value={voice.id}>{voice.name}</option>)}</select></label>{bound?.asset&&<small className="voice-match-status">Character binding: {bound.asset.filename}{bound.voice?bound.voice.id===speakerVoices[speaker]?.voiceId?' · selected':'': ' · not available to this TTS workflow; choose a ComfyUI voice'}</small>}{bound?.voice&&bound.voice.id!==speakerVoices[speaker]?.voiceId&&<button type="button" className="text-button" onClick={()=>setSpeakerVoices(current=>({...current,[speaker]:{...current[speaker],voiceId:bound.voice!.id}}))}>Use bound voice</button>}<label>Language<select aria-label={`${speaker} language`} value={speakerVoices[speaker]?.language||'en'} onChange={event=>setSpeakerVoices(current=>({...current,[speaker]:{...current[speaker],language:event.target.value}}))}><option value="en">English</option><option value="de">German</option><option value="fr">French</option><option value="no">Norwegian</option><option value="ru">Russian</option><option value="hy">Armenian</option><option value="ka">Georgian</option><option value="ja">Japanese</option><option value="ko">Korean</option><option value="it">Italian</option></select></label></div>})}</div>}
      {speakers.length>0&&voiceBindingsLoaded&&<small className="graph-disclosure">Story voice assignments are offered when a matching SRT speaker is bound to a voice in the discoverable ComfyUI catalog. Your selection here remains editable.</small>}
      <label>Timing mode<select aria-label="Dialogue timing mode" value={timingMode} onChange={event=>setTimingMode(event.target.value)}><option value="smart_natural">Smart natural</option><option value="stretch_to_fit">Stretch to fit</option><option value="pad_with_silence">Pad with silence</option><option value="concatenate">Concatenate</option></select></label>
      <details className="audio-advanced-settings"><summary>Advanced ChatterBox and timing settings</summary><label className="audio-cache-setting"><input type="checkbox" checked={ttsParameters.enable_audio_cache} onChange={event=>setTtsParameters(current=>({...current,enable_audio_cache:event.target.checked}))}/> Cache generated audio chunks for reuse</label><div className="audio-parameter-grid">{([['seed','Seed',0,4294967295,1],['exaggeration','Exaggeration',.25,2,.05],['temperature','Temperature',.05,5,.05],['cfg_weight','CFG weight',0,1,.05],['fade','Crossfade seconds',0,.1,.001],['max_stretch_ratio','Maximum stretch ratio',.5,5,.1],['min_stretch_ratio','Minimum stretch ratio',.1,2,.1],['timing_tolerance','Timing tolerance',.5,10,.5],['batch_size','Batch size',0,32,1]] as const).map(([key,label,min,max,step])=><label key={key}>{label}<input aria-label={label} type="number" min={min} max={max} step={step} value={ttsParameters[key]} onChange={event=>setTtsParameters(current=>({...current,[key]:Number(event.target.value)}))}/></label>)}</div><p>Defaults match the workflow. Values outside the backend’s supported range are rejected before generation.</p></details>
      <OutputDestination tool="timed-tts" onReady={setTtsDestinationReady} workspaceId={workspaceId} disabled={busy||!!(ttsJob&&['queued','running'].includes(ttsJob.status))}/>
      {!capabilities?.timed_tts_workflow_exists&&<p className="summariser-error">Timed TTS workflow file is missing from this checkout.</p>}
      <button className="generate-button" type="button" disabled={busy||!ttsDestinationReady||!!(ttsJob&&['queued','running','submitting'].includes(ttsJob.status))||!workspaceId||!capabilities?.comfyui_online||!capabilities?.timed_tts_workflow_exists||!srt.trim()||!speakers.length||speakers.some(speaker=>!speakerVoices[speaker]?.voiceId)||!voices.some(voice=>voice.discoverable)} onClick={()=>void generateTimedAudio()}><AudioLines size={15}/>{busy?'Starting…':'Generate timed audio'}</button>
      {ttsJob&&<article className="card timed-tts-job"><h3>{ttsJob.message}</h3><p>{ttsJob.status} · {ttsJob.progress}%</p><progress max="100" value={ttsJob.progress}/>{ttsJob.error&&<p className="summariser-error">{ttsJob.error}</p>}{ttsJob.result?.asset&&<audio src={ttsJob.result.asset.content_url} controls preload="metadata"/>}{ttsJob.status==='recovery_required'&&<p className="notice">ComfyUI may still be processing this request. Check its queue before trying again.</p>}</article>}
    </section>
    <section className="card timed-tts-panel" aria-label="Audio effects"><h2>Change / Process audio</h2><OutputDestination tool="audio-effects" onReady={setEffectDestinationReady} workspaceId={workspaceId} disabled={busy}/><p>Reuse a workspace clip with the existing ComfyUI repair and voice workflows. Required nodes are checked when the job runs.</p>
      <label>Source audio<select aria-label="Audio effect source" value={selectedId} onChange={event=>setSelectedId(event.target.value)}><option value="">Choose an audio clip</option>{assets.map(asset=><option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}</select></label>
      {selected&&<div className="card"><audio controls src={selected.content_url}/><button onClick={()=>setSelectedId('')}>Remove source selection</button></div>}
      <div className="studio-action-row" role="group" aria-label="Voice change type"><button aria-pressed={effectOperation==='simple'} onClick={()=>setEffectOperation('simple')}>Simple effects</button><button aria-pressed={['voice_changer','rvc'].includes(effectOperation)} onClick={()=>setEffectOperation('voice_changer')}>AI conversion</button></div>
      {effectOperation==='simple'&&<><label>Preset<select value={simplePreset} onChange={e=>setSimplePreset(e.target.value)}>{['deep','cartoon','telephone','robot','echo','reverb'].map(p=><option key={p}>{p}</option>)}</select></label><label>Strength<input type="range" min={0} max={1} step={.05} value={simpleStrength} onChange={e=>setSimpleStrength(Number(e.target.value))}/></label><button onClick={()=>{setSimplePreset('deep');setSimpleStrength(.5);}}>Reset effect</button><button disabled={busy||!effectDestinationReady||!selected||!!(effectJob&&['queued','running','submitting'].includes(effectJob.status))} onClick={()=>void runEffect(true)}>Preview first 5 seconds</button></>}
      <label>Effect<select aria-label="Audio effect" value={effectOperation} onChange={event=>setEffectOperation(event.target.value as typeof effectOperation)}>{(effectCapabilities?.operations||[]).map(row=><option key={row.id} value={row.id} disabled={!row.workflow_exists}>{row.label}{row.workflow_exists?'':' · workflow file missing'}</option>)}</select></label>
      {effectOperation==='voice_repair'&&<label>Restoration mode<select aria-label="Voice restoration mode" value={effectRestoration} onChange={event=>setEffectRestoration(Number(event.target.value))}><option value={0}>Original</option><option value={1}>Remove high frequencies</option><option value={2}>Seriously degraded</option></select></label>}
      {effectOperation==='noise_cleanup'&&<label>Cleanup aggressiveness<input aria-label="Cleanup aggressiveness" type="number" min={0} max={20} value={effectAggressiveness} onChange={event=>setEffectAggressiveness(Math.max(0,Math.min(20,Number(event.target.value)||0)))}/></label>}
      {effectOperation==='voice_changer'&&<label>Target ComfyUI voice<select aria-label="Target ComfyUI voice" value={effectVoice} onChange={event=>setEffectVoice(event.target.value)}><option value="">Choose a reference voice</option>{voices.filter(voice=>voice.discoverable).map(voice=><option key={voice.id} value={voice.id}>{voice.name}</option>)}</select></label>}
      {(effectOperation==='voice_changer'||effectOperation==='rvc')&&<label>Refinement passes<input aria-label="Audio refinement passes" type="number" min={1} max={5} value={effectPasses} onChange={event=>setEffectPasses(Math.max(1,Math.min(5,Number(event.target.value)||1)))}/></label>}
      {effectOperation==='rvc'&&<><label>RVC model<select aria-label="RVC model" value={rvcModel} onChange={event=>setRvcModel(event.target.value)}><option value="">No local RVC model found</option>{(effectCapabilities?.rvc_models||[]).map(row=><option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label>Matching index<select aria-label="RVC matching index" value={rvcIndex} onChange={event=>setRvcIndex(event.target.value)}><option value="">No index</option>{(effectCapabilities?.rvc_models.find(row=>row.id===rvcModel)?.indexes||[]).map(item=><option key={item}>{item}</option>)}</select></label><label>Pitch semitones<input aria-label="RVC pitch" type="number" min={-14} max={14} value={effectPitch} onChange={event=>setEffectPitch(Math.max(-14,Math.min(14,Number(event.target.value)||0)))}/></label></>}
      {(effectOperation==='emotion'||effectOperation==='style')&&<><label>Exact transcript<textarea aria-label="Audio effect transcript" value={effectTranscript} onChange={event=>setEffectTranscript(event.target.value)} maxLength={10000} placeholder="Enter exactly what is spoken in the source clip."/></label><label>{effectOperation==='emotion'?'Emotion':'Delivery style'}<select aria-label="Audio effect choice" value={effectChoice} onChange={event=>setEffectChoice(event.target.value)}>{(effectOperation==='emotion'?['happy','sad','angry','excited','calm','fearful','surprised','disgusted','confusion','empathy','embarrass','depressed','coldness','admiration','remove']:['whisper','serious','child','older','girl','pure','sister','sweet','exaggerated','ethereal','generous','recite','act_coy','warm','shy','comfort','authority','chat','radio','soulful','gentle','story','vivid','program','news','advertising','roar','murmur','shout','deeply','loudly','arrogant','friendly','remove']).map(value=><option key={value}>{value}</option>)}</select></label></>}
      {!effectCapabilities&&<p>Checking copied workflow files…</p>}
      <button className="generate-button" type="button" disabled={busy||!effectDestinationReady||!selected||!effectCapabilities?.operations.find(row=>row.id===effectOperation)?.workflow_exists||!!(effectJob&&['queued','running','submitting'].includes(effectJob.status))||(effectOperation==='voice_changer'&&!effectVoice)||(effectOperation==='rvc'&&!rvcModel)||((effectOperation==='emotion'||effectOperation==='style')&&!effectTranscript.trim())} onClick={()=>void runEffect()}><AudioLines size={15}/>{busy?'Starting…':'Run audio effect'}</button>
      {effectJob&&<article className="card timed-tts-job"><h3>{effectJob.message}</h3><p>{effectJob.status} · {effectJob.progress}%</p><progress max="100" value={effectJob.progress}/>{effectJob.error&&<p className="summariser-error">{effectJob.error}</p>}{effectJob.result?.asset&&<audio src={effectJob.result.asset.content_url} controls preload="metadata"/>}</article>}
    </section>
    <AudioSceneSurgery workspaceId={workspaceId} assets={assets}/>
    <div className="audio-studio-columns">
      <section className="card"><div className="page-heading"><div><h2>Voice files</h2><p>Only clips with an exact transcript are usable as reference voices. Existing ComfyUI voice files are listed here.</p></div><button className="quiet-button" type="button" onClick={()=>void refreshLiveVoices()} disabled={busy||!capabilities?.comfyui_online}><RefreshCw size={14}/> Refresh voices</button></div><label className="summariser-search"><Search size={16}/><input aria-label="Search voice files" placeholder="Search voices" value={voiceQuery} onChange={event=>setVoiceQuery(event.target.value)}/></label><div className="audio-voice-list">{voices.filter(voice=>voice.name.toLowerCase().includes(voiceQuery.toLowerCase())).map(voice=><article className="audio-voice-row" key={voice.id}><strong>{voice.name}</strong><span>{voice.source} · {voice.has_transcript?'transcript ready':'transcript needed'}</span><small>{voice.discoverable?'Available to ComfyUI':'Not available to ComfyUI until transcript is added'}</small></article>)}{!voices.length&&<p>No voice files found in the configured ComfyUI voice folders.</p>}</div></section>
      <section className="card"><h2>Enroll a library clip</h2><p>Choose an audio clip and provide its exact spoken transcript. This copies the clip and transcript into ComfyUI’s user voice folder.</p><label className="summariser-search"><Search size={16}/><input aria-label="Search audio clips" placeholder="Search audio clips" value={audioQuery} onChange={event=>setAudioQuery(event.target.value)}/></label><div className="audio-voice-list">{visible.map(asset=><button type="button" className={`audio-clip-choice ${selectedId===asset.asset_id?'selected':''}`} aria-pressed={selectedId===asset.asset_id} key={asset.asset_id} onClick={()=>setSelectedId(asset.asset_id)}><strong title={asset.filename}>{asset.filename}</strong><small>{asset.description||asset.audio_category||asset.roles.join(' · ')}</small></button>)}{!visible.length&&<p>No audio clips in this workspace yet.</p>}</div><label>Voice name<input aria-label="New voice name" value={name} onChange={event=>setName(event.target.value)} maxLength={80} placeholder="e.g. Arjun warm"/></label><label>Exact transcript<textarea aria-label="Exact voice transcript" value={transcript} onChange={event=>setTranscript(event.target.value)} placeholder="Type exactly what is spoken in the selected clip."/></label><button className="generate-button" type="button" disabled={busy||!selected||!name.trim()||!transcript.trim()||voices.some(voice=>voice.name.toLowerCase()===name.trim().toLowerCase())} onClick={()=>void enroll()}>{busy?'Adding…':'Add to ComfyUI voices'}</button></section>
    </div>
    <StudioCheckpoints/><details className="card"><summary>F5 dataset preparation</summary>{capabilities?.f5_dataset_preparation?<><p>{capabilities.f5_dataset_preparation.message} Training is disabled.</p><p>Preparation {capabilities.f5_dataset_preparation.preparation_ready?'ready':'unavailable'} · Python: {capabilities.f5_dataset_preparation.python}</p><ul>{capabilities.f5_dataset_preparation.checks.map(check=><li key={check.name}>{check.ok?'Ready':'Missing'} · {check.name}: {check.detail}</li>)}</ul><label>Dataset name<input aria-label="F5 dataset name" value={f5Dataset} onChange={event=>setF5Dataset(event.target.value)} maxLength={80}/></label><label>Base model<select aria-label="F5 base model" value={f5Model} onChange={event=>setF5Model(event.target.value)}>{capabilities.f5_dataset_preparation.base_models.map(model=><option key={model.id} value={model.id} disabled={!model.available}>{model.id}{model.available?'':` · ${model.checkpoint} missing`}</option>)}</select></label><h3>Audio clips and exact transcripts</h3><SelectionToggle selected={Object.keys(f5Samples)} shown={assets.map(asset=>asset.asset_id)} onChange={ids=>setF5Samples(current=>Object.fromEntries(ids.map(id=>[id,current[id]||''])))} disabled={busy}/>{assets.map(asset=><div className="f5-sample-row" key={asset.asset_id}><label><input type="checkbox" checked={Object.hasOwn(f5Samples,asset.asset_id)} onChange={event=>setF5Samples(current=>{const next={...current};if(event.target.checked)next[asset.asset_id]='';else delete next[asset.asset_id];return next;})}/>{asset.filename}</label>{Object.hasOwn(f5Samples,asset.asset_id)&&<textarea aria-label={`Transcript for ${asset.filename}`} value={f5Samples[asset.asset_id]} maxLength={10000} onChange={event=>setF5Samples(current=>({...current,[asset.asset_id]:event.target.value}))} placeholder="Exact transcript"/>}</div>)}<button className="generate-button" type="button" disabled={busy||!capabilities.f5_dataset_preparation.preparation_ready||!capabilities.f5_dataset_preparation.base_models.find(model=>model.id===f5Model)?.available||!workspaceId||!f5Dataset.trim()||!Object.values(f5Samples).some(text=>text.trim())||!!(f5Job&&['queued','running'].includes(f5Job.status))} onClick={()=>void prepareF5Dataset()}>Prepare dataset</button>{f5Job&&<article className="card timed-tts-job"><h3>{f5Job.message}</h3><p>{f5Job.status} · {f5Job.progress}%</p><progress max="100" value={f5Job.progress}/>{f5Job.error&&<p className="summariser-error">{f5Job.error}</p>}{f5Job.result?.dataset_name&&<p>Prepared dataset: {f5Job.result.dataset_name}</p>}</article>}</>:<p>Checking local preparation requirements…</p>}</details>
    <details className="card"><summary>Detected TTS models</summary>{models.length?<ul>{models.map(model=><li key={model.id}>{model.family} · {model.name} · {model.artifact_count} files · {model.finetune_status}</li>)}</ul>:<p>No TTS model files found in the configured ComfyUI TTS folder.</p>}</details>
  </section>}><StudioChat name="audio" context={{workspaceId,activity:effectOperation,selectedAudio:selected?.filename}}/></EditorWorkspace></>;
}

function AudioReconstruct({onBack}:{onBack:()=>void}) {
  const [,setWorkspaces]=useState<StoryWorkspace[]>([]);
  const [workspaceId,setWorkspaceId]=useState(defaultMediaWorkspaceId);
  const [assets,setAssets]=useState<MediaAsset[]>([]);
  const [recording,setRecording]=useState<File|null>(null);
  const [session,setSession]=useState<ReconstructionSession|null>(null);
  const [character,setCharacter]=useProjectState('AudioReconstruct:character','');
  const [sentence,setSentence]=useProjectState('AudioReconstruct:sentence','This is my calibration sentence for the character voice.');
  const [partId,setPartId]=useProjectState('AudioReconstruct:partId','scene_001_line_001');
  const [sequence,setSequence]=useProjectState('AudioReconstruct:sequence',1);
  const [expected,setExpected]=useProjectState('AudioReconstruct:expected','');
  const [transcript,setTranscript]=useProjectState('AudioReconstruct:transcript','');
  const [selectedAsset,setSelectedAsset]=useState('');
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const refresh=async(id:string)=>{
    if(!id){setAssets([]);setSession(null);return;}
    const [media,reconstruction]=await Promise.all([listMediaAssets(id,'audio'),getReconstructionSession(id)]);
    setAssets(media.assets);setSession(reconstruction);
    setSelectedAsset(current=>media.assets.some(row=>row.asset_id===current)?current:media.assets[0]?.asset_id||'');
    setCharacter(current=>current||reconstruction.characters[0]?.name||'');
  };
  useEffect(()=>{void listStoryWorkspaces().then(result=>{const rows=result.items||[];setWorkspaces(rows);const requestedWorkspace=new URLSearchParams(window.location.hash.split('?')[1]||'').get('workspace_id')||'';setWorkspaceId(preferredMediaWorkspaceId(rows, requestedWorkspace));}).catch(error=>setMessage(`Could not load workspaces: ${(error as Error).message}`));},[]);
  useEffect(()=>{void refresh(workspaceId).catch(error=>setMessage(`Could not load reconstruction session: ${(error as Error).message}`));},[workspaceId]);
  const selected=assets.find(asset=>asset.asset_id===selectedAsset);
  const run=async(action:()=>Promise<unknown>,success:string)=>{setBusy(true);setMessage('');try{await action();await refresh(workspaceId);setMessage(success);}catch(error){setMessage((error as Error).message);}finally{setBusy(false);}};
  const calibrate=()=>run(()=>saveReconstructionCalibration(workspaceId,character,sentence),'Character calibration saved.');
  const prepare=()=>run(()=>createReconstructionPart(workspaceId,{part_id:partId,character_name:character,sequence,expected_text:expected}),'Dialogue part prepared.');
  const saveTake=()=>run(()=>addReconstructionTake(workspaceId,partId,selectedAsset,transcript||expected),'Take saved. Acceptance remains explicit.');
  const addRecording=async()=>{if(!workspaceId||!recording)return;setBusy(true);setMessage('');try{const saved=await uploadMediaAsset(workspaceId,recording,'audio_clip');await refresh(workspaceId);setSelectedAsset(saved.asset_id);setRecording(null);setMessage('Recording added to the shared audio library.');}catch(error){setMessage(`Could not add recording: ${(error as Error).message}`);}finally{setBusy(false);}};
  const accept=async(part:string,take:string)=>run(async()=>{const result=await acceptReconstructionTake(workspaceId,part,take);return result;},'Take accepted and added to the shared audio library.');
  return <section className="card summariser-page" aria-label="Audio Reconstruct">
    <button className="quiet-button summariser-back" type="button" onClick={onBack}>← Audio tools</button>
    <header className="summariser-heading"><div><div className="eyebrow">MEDIA PREP / AUDIO RECONSTRUCT</div><h1>Audio Reconstruct</h1><p>Calibrate a character, prepare dialogue parts, then review and accept recorded takes.</p></div><span className="media-prep-state">Story Builder tool reused</span></header>
    {message&&<p className="notice" role="status">{message}</p>}
    <MediaSourcePicker workspaceId={workspaceId} kinds={['audio']} disabled={busy} onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/>
    <div className="summariser-toolbar"><p className="project-context-label">Current project · change with New project or Load project above</p></div>
    <VoiceRecorder key={workspaceId} workspaceId={workspaceId} onSaved={(asset,use)=>{setAssets(rows=>[asset,...rows.filter(r=>r.asset_id!==asset.asset_id)]);setSelectedAsset(asset.asset_id);if(use==='Use in Vibe Editor'){sessionStorage.setItem('vibe-editor-pending-audio',JSON.stringify({workspace_id:workspaceId,asset}));window.location.hash='/editor';}else setMessage(use==='Use as voice reference'?'Recording saved. Enroll it with its exact transcript in Audio Studio to make a reusable TTS voice.':'Recording ready below for voice conversion or a dialogue take.');}}/>
    <label>Recording to change<select aria-label="Voice conversion source" value={selectedAsset} onChange={e=>setSelectedAsset(e.target.value)}><option value="">Choose a recording</option>{assets.map(a=><option key={a.asset_id} value={a.asset_id}>{a.filename}</option>)}</select></label>
    <VoiceConversion key={'conversion-'+workspaceId} workspaceId={workspaceId} source={selected} onSaved={asset=>{setAssets(rows=>[asset,...rows.filter(r=>r.asset_id!==asset.asset_id)]);setSelectedAsset(asset.asset_id);setMessage('Converted audio selected. Save it as a dialogue take below if needed.');}}/>
    <div className="audio-studio-columns">
      <section className="card"><h2><Mic2 size={17}/> Character calibration</h2><p>Save a calibration sentence and voice settings for each character before preparing their dialogue.</p><label>Character<input aria-label="Reconstruction character" value={character} maxLength={80} onChange={event=>setCharacter(event.target.value)} placeholder="Character name" list="reconstruction-characters"/><datalist id="reconstruction-characters">{session?.characters.map(row=><option key={row.character_id} value={row.name}/>)}</datalist></label><label>Calibration sentence<textarea aria-label="Calibration sentence" value={sentence} onChange={event=>setSentence(event.target.value)} maxLength={2000}/></label><button className="generate-button" type="button" disabled={busy||!workspaceId||!character.trim()||!sentence.trim()} onClick={()=>void calibrate()}>{busy?'Saving…':'Save calibration'}</button><div className="audio-voice-list">{session?.characters.map(row=><article className="audio-voice-row" key={row.character_id}><strong>{row.name}</strong><small>{row.status} · {row.calibration_sentence}</small></article>)}</div></section>
      <section className="card"><h2>Prepare a dialogue part</h2><p>Use a stable part ID to keep retakes together. Add a source recording from this workspace’s audio library.</p><div className="summariser-toolbar"><label>Part ID<input aria-label="Dialogue part ID" value={partId} maxLength={80} onChange={event=>setPartId(event.target.value)}/></label><label>Sequence<input aria-label="Dialogue sequence" type="number" min={1} value={sequence} onChange={event=>setSequence(Number(event.target.value))}/></label></div><label>Character<select aria-label="Dialogue character" value={character} onChange={event=>setCharacter(event.target.value)}><option value="">Choose calibrated character</option>{session?.characters.filter(row=>row.status==='calibrated').map(row=><option key={row.character_id} value={row.name}>{row.name}</option>)}</select></label><label>Expected dialogue<textarea aria-label="Expected dialogue" value={expected} onChange={event=>setExpected(event.target.value)} maxLength={5000}/></label><button className="quiet-button" type="button" disabled={busy||!workspaceId||!character||!expected.trim()} onClick={()=>void prepare()}>Prepare dialogue part</button>
        <div className="summariser-toolbar"><label className="summariser-upload">Add recording<input type="file" accept="audio/*" onChange={event=>{const next=event.currentTarget.files?.[0]||null;event.currentTarget.value='';setRecording(next);}}/></label><button className="quiet-button" type="button" disabled={busy||!recording||!workspaceId} onClick={()=>void addRecording()}>Add to audio library</button></div><label>Source audio<select aria-label="Source audio asset" value={selectedAsset} onChange={event=>setSelectedAsset(event.target.value)}><option value="">Choose an audio clip</option>{assets.map(asset=><option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}</select></label>{selected&&<div className="summariser-preview"><audio src={selected.content_url} controls preload="metadata"/></div>}<label>Transcript<textarea aria-label="Reconstruction transcript" value={transcript} onChange={event=>setTranscript(event.target.value)} placeholder="Defaults to expected dialogue" maxLength={5000}/></label><button className="generate-button" type="button" disabled={busy||!workspaceId||!selectedAsset||!partId.trim()||!session?.parts.some(part=>part.part_id===partId)} onClick={()=>void saveTake()}><FileUp size={15}/>{busy?'Saving…':'Save take'}</button>
      </section>
    </div>
    <section className="card summariser-status"><h2>Dialogue parts and takes</h2>{!session?.parts.length&&<p>No dialogue parts prepared yet.</p>}{session?.parts.slice().sort((a,b)=>a.sequence-b.sequence).map(part=><article className="card summariser-job-detail" key={part.part_id}><div className="summariser-results-heading"><div><h3>{part.character_name} · {part.sequence}</h3><p>{part.part_id} · {part.expected_text}</p></div><span className="media-prep-state">{part.accepted_take_id?'Accepted':'Needs review'}</span></div>{session.takes.filter(take=>take.part_id===part.part_id).map(take=><div className="audio-reconstruct-take" key={take.take_id}><div><strong>{take.take_id}</strong><small>{take.created_at} · {take.transcript||'No transcript'}</small></div>{take.status!=='accepted'&&<button className="quiet-button" type="button" disabled={busy} onClick={()=>void accept(part.part_id,take.take_id)}><Check size={15}/>Accept take</button>}</div>)}</article>)}</section>
  </section>;
}

function MediaGrid({assets,empty,selectable=false,selectedIds=[],analyzedIds=[],disabled=false,onToggle,onDelete}:{assets:MediaAsset[];empty:string;selectable?:boolean;selectedIds?:string[];analyzedIds?:string[];disabled?:boolean;onToggle?:(assetId:string)=>void;onDelete?:(asset:MediaAsset)=>void}) {
  if (!assets.length) return <div className="card summariser-empty">{empty}</div>;
  return <div className="summariser-assets">{assets.map(asset=><article className={`card summariser-asset ${selectable?'is-selectable':''}`} key={asset.asset_id}>
    {selectable&&<label className="summariser-select"><input type="checkbox" checked={selectedIds.includes(asset.asset_id)} aria-label={analyzedIds.includes(asset.asset_id)?"Analyzed — see Results":`Select ${asset.filename}`} disabled={disabled} onChange={()=>onToggle?.(asset.asset_id)}/><span>{analyzedIds.includes(asset.asset_id)?"Analyzed — see Results":"Select"}</span></label>}
    <div className="summariser-preview">{asset.kind==='video'?<video src={asset.content_url} controls preload="metadata"/>:asset.kind==='image'?<img src={asset.content_url} alt={asset.description || asset.filename} loading="lazy"/>:<audio src={asset.content_url} controls preload="metadata"/>}</div>
    {onDelete&&(asset.metadata?.analyzer_run_id||asset.metadata?.sam_audio?.run_id)&&<button type="button" className="quiet-button" aria-label={`Remove extracted ${asset.kind==='image'?'image':'clip'} ${asset.filename}`} title={asset.kind==='image'?'Delete extracted image':'Delete extracted clip'} disabled={disabled} onClick={()=>onDelete(asset)}><Trash2 size={16}/></button>}
    <strong title={asset.filename}>{asset.filename}</strong>{typeof asset.media?.duration_seconds==='number'&&<small>{asset.media.duration_seconds.toFixed(2)} seconds</small>}<small>{asset.description || asset.provenance_notes || asset.roles.join(' · ')}</small>
  </article>)}</div>;
}

function AudioUtilities({onBack}:{onBack:()=>void}) {
  const [utilityDestinationReady,setUtilityDestinationReady]=useState(false);
  const [,setWorkspaces]=useState<StoryWorkspace[]>([]);
  const [workspaceId,setWorkspaceId]=useState(defaultMediaWorkspaceId);
  const [capabilities,setCapabilities]=useState<AudioUtilityCapabilities|null>(null);
  const [assets,setAssets]=useState<MediaAsset[]>([]);
  const [query,setQuery]=useProjectState('AudioUtilities:query','');
  const [importFiles,setImportFiles]=useState<File[]>([]);
  const [selected,setSelected]=useState<string[]>([]);
  const [operation,setOperation]=useProjectState<AudioUtilityOperation['id']>('AudioUtilities:operation','extract_mp3');
  const [settings,setSettings]=useProjectState<Record<string,unknown>>('AudioUtilities:settings',{quality:2,model:'master64',dry:0,stems:2,device:'cuda'});
  const [jobs,setJobs]=useState<AudioUtilityJob[]>([]);
  const [message,setMessage]=useState('');
  const [busy,setBusy]=useState(false);
  useEffect(()=>{
    void getAudioUtilityCapabilities().then(setCapabilities).catch(error=>setMessage((error as Error).message));
    void listStoryWorkspaces().then(result=>{const rows=result.items||[];setWorkspaces(rows);const requestedWorkspace=new URLSearchParams(window.location.hash.split('?')[1]||'').get('workspace_id')||'';setWorkspaceId(preferredMediaWorkspaceId(rows, requestedWorkspace));}).catch(error=>setMessage((error as Error).message));
  },[]);
  useEffect(()=>{setSelected([]);if(!workspaceId){setAssets([]);setJobs([]);return;}let active=true;void Promise.all([listMediaAssets(workspaceId,'audio'),listMediaAssets(workspaceId,'video'),listAudioUtilityJobs(workspaceId)]).then(([audio,video,existing])=>{if(active){setAssets([...audio.assets,...video.assets]);setJobs(existing);}}).catch(error=>{if(active)setMessage((error as Error).message);});return()=>{active=false;}},[workspaceId]);
  const running=jobs.find(job=>['queued','running','cancel_requested'].includes(job.status));
  useEffect(()=>{if(!workspaceId||!running)return;let active=true;const timer=window.setInterval(()=>void getAudioUtilityJob(workspaceId,running.job_id).then(job=>{if(active)setJobs(rows=>[job,...rows.filter(row=>row.job_id!==job.job_id)]);}).catch(error=>{if(active)setMessage((error as Error).message);}),2000);return()=>{active=false;window.clearInterval(timer);};},[workspaceId,running?.job_id,running?.status]);
  const available=capabilities?.operations.find(item=>item.id===operation);
  const compatibleAssets=assets.filter(asset=>operation==='extract_mp3'||asset.kind==='audio');
  const visibleAssets=compatibleAssets.filter(asset=>[asset.filename,asset.description,...(asset.tags||[])].filter(Boolean).join(' ').toLowerCase().includes(query.trim().toLowerCase()));
  const toggle=(id:string)=>setSelected(rows=>rows.includes(id)?rows.filter(row=>row!==id):[...rows,id]);
  const importSelected=async()=>{if(!workspaceId||!importFiles.length)return;setBusy(true);setMessage('');let added=0;try{for(const file of importFiles){const ext=file.name.split('.').pop()?.toLowerCase()||'';const video=['mp4','mov','mkv','webm'].includes(ext);const audio=['wav','mp3','flac','ogg','m4a','aac'].includes(ext);if(!video&&!audio)throw new Error(`Unsupported file: ${file.name}. Convert it to a supported audio/video format first.`);await uploadMediaAsset(workspaceId,file,video?'project_video':'project_audio');added++;}const [audio,video]=await Promise.all([listMediaAssets(workspaceId,'audio'),listMediaAssets(workspaceId,'video')]);setAssets([...audio.assets,...video.assets]);setImportFiles([]);setMessage(added?`${added} media file${added===1?'':'s'} added to the shared library.`:'No supported audio or video files were found.');}catch(error){setImportFiles(files=>files.slice(added));try{const [audio,video]=await Promise.all([listMediaAssets(workspaceId,'audio'),listMediaAssets(workspaceId,'video')]);setAssets([...audio.assets,...video.assets]);}catch{/* Preserve the original import error if library refresh also fails. */}setMessage(`Import stopped after ${added} file${added===1?'':'s'}: ${(error as Error).message}`);}finally{setBusy(false);}};
  const submit=async()=>{if(!workspaceId||!selected.length)return;setBusy(true);setMessage('');try{const job=await createAudioUtilityJob(workspaceId,operation,selected,settings);setJobs(rows=>[job,...rows.filter(row=>row.job_id!==job.job_id)]);setMessage('Utility job queued. Outputs will appear in the shared audio library.');}catch(error){setMessage((error as Error).message);}finally{setBusy(false);}};
  return <section className="card summariser-page" aria-label="Audio Utilities">
    <button className="quiet-button summariser-back" type="button" onClick={onBack}>← Audio tools</button>
    <header className="summariser-heading"><div><div className="eyebrow">MEDIA PREP / AUDIO UTILITIES</div><h1>Audio Utilities</h1><p>Clean audio, extract MP3 tracks, or separate stems from shared-library media.</p></div><span className="media-prep-state">Story Builder operations reused</span></header>
    {message&&<p className="notice" role="status">{message}</p>}
    <OutputDestination tool="audio-utilities" onReady={setUtilityDestinationReady} workspaceId={workspaceId} disabled={busy}/>
    <div className="summariser-toolbar"><p className="project-context-label">Current project · change with New project or Load project above</p><label>Operation<select aria-label="Audio utility operation" value={operation} onChange={event=>{const next=event.target.value as AudioUtilityOperation['id'];setOperation(next);setSelected(ids=>ids.filter(id=>assets.some(asset=>asset.asset_id===id&&(next==='extract_mp3'||asset.kind==='audio'))));}}><option value="extract_mp3">Extract MP3</option><option value="noise_cleanup">Noise cleanup</option><option value="demucs_stems">Separate stems</option></select></label></div>
    {available?.status!=='available'&&<p className="notice">{available?.reason||'Checking operation availability…'}</p>}
    {operation==='extract_mp3'&&<label>MP3 quality (0 best, 9 smallest)<input type="number" min={0} max={9} value={String(settings.quality)} onChange={event=>setSettings({...settings,quality:Number(event.target.value)})}/></label>}
    {operation==='noise_cleanup'&&<div className="summariser-toolbar"><label>Model<select value={String(settings.model)} onChange={event=>setSettings({...settings,model:event.target.value})}><option value="master64">Master64</option><option value="dns64">DNS64</option></select></label><label>Dry mix<input type="number" min={0} max={1} step={0.05} value={String(settings.dry)} onChange={event=>setSettings({...settings,dry:Number(event.target.value)})}/></label></div>}
    {operation==='demucs_stems'&&<div className="summariser-toolbar"><label>Stem count<select value={String(settings.stems)} onChange={event=>setSettings({...settings,stems:Number(event.target.value)})}><option value="2">2 stems</option><option value="4">4 stems</option><option value="6">6 stems</option></select></label><label>Device<select value={String(settings.device)} onChange={event=>setSettings({...settings,device:event.target.value})}><option value="cuda">CUDA</option><option value="cpu">CPU</option></select></label></div>}
    <MediaSourcePicker workspaceId={workspaceId} kinds={operation==='extract_mp3'?['audio','video']:['audio']} disabled={busy} onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/><section className="card"><div className="summariser-results-heading"><div><h2>Shared media</h2><p>Import individual files or a folder. MP3 extraction accepts audio or video; other operations accept audio. Originals stay in the shared library.</p></div></div><div className="summariser-toolbar"><label className="summariser-upload media-file-button" title="Import individual audio or video files from your computer.">Import files…<input aria-label="Import individual media files" type="file" multiple accept="audio/*,video/*" onChange={event=>{const files=Array.from(event.currentTarget.files||[]);event.currentTarget.value='';setImportFiles(files);}}/></label><label className="summariser-upload media-file-button" title="Import compatible media from a folder on your computer.">Import folder…<input aria-label="Import a media folder" type="file" multiple {...({webkitdirectory:''} as React.InputHTMLAttributes<HTMLInputElement>)} accept="audio/*,video/*" onChange={event=>{const files=Array.from(event.currentTarget.files||[]);event.currentTarget.value='';setImportFiles(files);}}/></label><button className="quiet-button" type="button" disabled={busy||!importFiles.length||!workspaceId} onClick={()=>void importSelected()}>{busy?'Importing…':`Add ${importFiles.length||''} to library`}</button></div>{importFiles.length>0&&<ul aria-label="Files ready to import">{importFiles.map((file,index)=><li key={`${file.name}-${index}`}>{file.name}<button type="button" className="quiet-button" disabled={busy} onClick={()=>setImportFiles(rows=>rows.filter((_,i)=>i!==index))}>Remove {file.name}</button></li>)}<li><button type="button" className="quiet-button" disabled={busy} onClick={()=>setImportFiles([])}>Clear import list</button></li></ul>}<label>Search filenames, descriptions or tags<input type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Search shared audio and video"/></label><div className="summariser-results-heading"><div><h3>Select source media</h3><p>{selected.length} selected</p></div><SelectionToggle selected={selected} shown={visibleAssets.map(asset=>asset.asset_id)} onChange={setSelected} disabled={busy}/></div><MediaGrid assets={visibleAssets} empty="No compatible audio or video in this workspace library yet." selectable selectedIds={selected} onToggle={toggle}/><button className="generate-button" type="button" disabled={busy||!utilityDestinationReady||!selected.length||available?.status!=='available'||!!running} onClick={()=>void submit()}>{busy?'Submitting…':'Run utility'}</button></section>
    <section className="card summariser-status"><h2>Utility jobs</h2>{jobs.slice(0,12).map(job=><article className="card summariser-job-detail" key={job.job_id}><div className="summariser-results-heading"><div><h3>{job.stage} · {job.progress}%</h3><p>{job.message}</p></div><span className="media-prep-state">{job.status}</span></div>{job.error&&<p>{job.error}</p>}{job.result?.assets&&<MediaGrid assets={job.result.assets} empty="No outputs published."/>}</article>)}{!jobs.length&&<p>No audio utility jobs yet.</p>}</section>
  </section>;
}

export default function MediaPrepPage() {
  type Tool = 'overview'|'video'|'image-home'|'image'|'audio-home'|'audio-studio'|'reconstruct'|'music'|'utilities'|'search';
  const readTool = (): Tool => {
    const value = new URLSearchParams(window.location.hash.split('?')[1] || '').get('tool');
    return value === 'video' || value === 'image-home' || value === 'image' || value === 'audio-home' || value === 'audio-studio' || value === 'reconstruct' || value === 'music' || value === 'utilities' || value === 'search' ? value : 'overview';
  };
  const [tool,setToolState] = useState<Tool>(readTool);
  const setTool = (next: Tool) => {
    setToolState(next);
    if (window.location.hash.startsWith('#/media-prep')) {
      const current = new URLSearchParams(window.location.hash.split('?')[1] || '');
      const workspaceId = current.get('workspace_id');
      const query = new URLSearchParams();
      if (next !== 'overview') query.set('tool', next);
      if (workspaceId) query.set('workspace_id', workspaceId);
      const queryText = query.toString();
      window.location.hash = `/media-prep${queryText ? `?${queryText}` : ''}`;
    }
  };
  useEffect(() => {
    const syncTool = () => setToolState(readTool());
    window.addEventListener('hashchange', syncTool);
    return () => window.removeEventListener('hashchange', syncTool);
  }, []);
  if (tool === 'video') return <div className="content-wrap media-prep-page"><button className="quiet-button summariser-back" type="button" onClick={()=>setTool('overview')}>← Media Prep</button><VideoSummariser/></div>;
  if (tool === 'image-home') return <div className="content-wrap media-prep-page"><button className="quiet-button summariser-back" onClick={()=>setTool('overview')}>← Media Prep</button><MediaLibraryPage/></div>;
  if (tool === 'image') return <div className="content-wrap media-prep-page"><ImageDetailer onBack={()=>setTool('image-home')}/></div>;
  if (tool === 'audio-home') return <AudioHome onBack={()=>setTool('overview')} onOpen={setTool}/>;
  if (tool === 'audio-studio') return <div className="content-wrap media-prep-page"><AudioStudio onBack={()=>setTool('audio-home')}/></div>;
  if (tool === 'reconstruct') return <div className="content-wrap media-prep-page"><AudioReconstruct onBack={()=>setTool('audio-home')}/></div>;
  if (tool === 'music') return <div className="content-wrap media-prep-page"><MusicSoundPage onBack={()=>setTool('audio-home')}/></div>;
  if (tool === 'utilities') return <div className="content-wrap media-prep-page"><AudioUtilities onBack={()=>setTool('audio-home')}/></div>;
  if (tool === 'search') {
    const from = new URLSearchParams(window.location.hash.split('?')[1] || '').get('from');
    const backTool = from === 'audio' ? 'audio-home' : 'overview';
    const backLabel = from === 'audio' ? '← Audio' : '← Media Prep';
    return <div className="content-wrap media-prep-page"><button className="quiet-button summariser-back" type="button" onClick={()=>setTool(backTool)}>{backLabel}</button><MediaLibraryPage/></div>;
  }
  return <div className="content-wrap media-prep-page">
    <header className="page-heading"><div><div className="eyebrow">MEDIA PREP</div><h1>Media tools</h1><p>Prepare, review and find media in the shared library.</p></div><a className="generate-button" href="#/media-prep?tool=search"><Search size={16}/> Open Search</a></header>
    <section className="media-prep-tools" aria-label="Media tools">
      <article className="card media-prep-tool"><span className="media-prep-icon"><Video size={19}/></span><div><h2>Vibe Editor</h2><p>Describe an edit, review media and tools, then preview and export.</p></div><a className="generate-button" href="#/editor">Open Editor</a></article>
      <article className="card media-prep-tool"><span className="media-prep-icon"><Search size={19}/></span><div><h2>Search library</h2><p>Find saved images, videos, voice files and audio clips.</p></div><button className="generate-button" type="button" onClick={()=>setTool('search')}>Open Search</button></article>
      <article className="card media-prep-tool"><span className="media-prep-icon"><Video size={19}/></span><div><h2>Video Summariser</h2><p>Library · YouTube Download · Analyze · Results · Audio Assets</p></div><button className="generate-button" type="button" onClick={()=>setTool('video')}>Open</button></article>
      <article className="card media-prep-tool"><span className="media-prep-icon"><Image size={19}/></span><div><h2>Images</h2><p>Browse images · Image Detailer</p></div><button className="generate-button" type="button" onClick={()=>setTool('image-home')}>Open Images</button></article>
      <article className="card media-prep-tool"><span className="media-prep-icon"><AudioLines size={19}/></span><div><h2>Audio</h2><p>Studio · Reconstruct · Music &amp; Sound · Utilities</p></div><button className="generate-button" type="button" onClick={()=>setTool('audio-home')}>Open Audio</button></article>
    </section>
  </div>;
}

function AudioHome({onOpen,onBack}:{onOpen:(tool:'audio-studio'|'reconstruct'|'music'|'utilities')=>void;onBack:()=>void}) {
  const tools=[
    {id:'audio-studio' as const,title:'Audio Studio',description:'Manage reference voices, TTS models and timed dialogue generation.',icon:<AudioLines size={19}/>},
    {id:'reconstruct' as const,title:'Audio Reconstruct',description:'Calibrate characters, prepare dialogue parts and review takes.',icon:<Mic2 size={19}/>},
    {id:'music' as const,title:'Music & Sound',description:'Create music with ACE-Step and effects with Control-Foley.',icon:<AudioLines size={19}/>},
    {id:'utilities' as const,title:'Audio Utilities',description:'Clean audio, extract MP3 and separate Demucs stems.',icon:<AudioLines size={19}/>},
  ];
  return <div className="content-wrap media-prep-page"><button className="quiet-button summariser-back" type="button" onClick={onBack}>← Media Prep</button><header className="page-heading"><div><div className="eyebrow">MEDIA PREP / AUDIO</div><h1>Audio tools</h1><p>Choose a tool. Voice files and generated clips use the shared media library.</p></div><a className="quiet-button" href="#/media-prep?tool=search&kind=audio&from=audio">Open audio library</a></header><section className="media-prep-tools" aria-label="Audio tools">{tools.map(item=><article className="card media-prep-tool" key={item.id}><span className="media-prep-icon">{item.icon}</span><div><h2>{item.title}</h2><p>{item.description}</p></div><button className="generate-button" type="button" onClick={()=>onOpen(item.id)}>Open</button></article>)}</section></div>;
}
