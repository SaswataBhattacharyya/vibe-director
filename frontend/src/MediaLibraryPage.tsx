import {deleteSelectedMedia} from './lib/media-deletion';
import MediaSourcePicker from './MediaSourcePicker';
import { ChangeEvent, ClipboardEvent, DragEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';
import { AudioLines, FileUp, GalleryHorizontal, Image as ImageIcon, LayoutGrid, List, RefreshCw, Search, Video, Trash2 } from 'lucide-react';
import { cancelMediaContentIndexJob, createMediaContentIndexJob, deleteMediaSeoStyle, getMediaContentIndexJob, importComfyVoiceToWorkspace, indexMediaAssetAnnotations, listAudioVoices, listMediaAssets, listMediaContentIndexJobs, listMediaSeoStyles, AudioVoice, MediaAsset, MediaSeoStyle, rankMediaAssets, retryMediaContentIndexJob, saveMediaSeoStyle, searchMediaSemantically, SemanticIndexJob, setMediaAssetArchived, updateMediaAnnotations, uploadMediaAsset } from './lib/media-api';
import { listStoryWorkspaces, StoryWorkspace } from './lib/story-api';
import { mediaWorkspaceOptions, preferredMediaWorkspaceId, rememberMediaWorkspaceId } from './lib/media-workspace';
import { getGpuAdmission } from './lib/status-api';
import './media-library.css';

type Kind = 'image'|'video'|'audio';
type AssetView = 'template'|'list'|'carousel';
type PanelControls = {search: string; order: 'newest'|'oldest'; view: AssetView; mode: 'keyword'|'semantic'};

function LibraryPreview({asset}:{asset:MediaAsset}) {
  const [previewing,setPreviewing]=useState(false);
  const video=useRef<HTMLVideoElement>(null);
  useEffect(()=>{const player=video.current;if(!player)return;if(previewing){player.muted=true;void player.play().catch(()=>{});}else{player.pause();player.currentTime=0;}},[previewing]);
  if(asset.kind==='image')return <img src={asset.content_url} alt={asset.description||asset.filename}/>;
  if(asset.kind==='video')return <video ref={video} src={asset.content_url} controls muted loop playsInline preload="metadata" onMouseEnter={()=>setPreviewing(true)} onMouseLeave={()=>setPreviewing(false)} onFocus={()=>setPreviewing(true)} onBlur={()=>setPreviewing(false)} aria-label={`${asset.filename}, muted hover preview`}/>;
  return <audio src={asset.content_url} controls preload="metadata" aria-label={`Play ${asset.filename}`}/>;
}

const readAssetView = (key: string): AssetView => {
  try { const value = localStorage.getItem(key); return value === 'list' || value === 'carousel' ? value : 'template'; }
  catch { return 'template'; }
};

export default function MediaLibraryPage() {
  const [workspaces, setWorkspaces] = useState<StoryWorkspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');
  const uploadInput = useRef<HTMLInputElement>(null);
  const assetLoadSequence = useRef(0);
  const [kind, setKind] = useState<Kind>(() => {
    const requested = new URLSearchParams(window.location.hash.split('?')[1] || '').get('kind');
    return requested === 'video' || requested === 'audio' ? requested : 'image';
  });
  const [panelControls, setPanelControls] = useState<Record<string, PanelControls>>(() => ({
    image: {search: '', order: 'newest', view: readAssetView('vibe-media-view-image-v1'), mode:'keyword'},
    video: {search: '', order: 'newest', view: readAssetView('vibe-media-view-video-v1'), mode:'keyword'},
    'voice-files': {search: '', order: 'newest', view: readAssetView('vibe-media-view-voice-files-v1'), mode:'keyword'},
    'audio-clips': {search: '', order: 'newest', view: readAssetView('vibe-media-view-audio-clips-v1'), mode:'keyword'},
  }));
  const [semanticIds, setSemanticIds] = useState<Record<string, string[]>>({});
  const [semanticQueries, setSemanticQueries] = useState<Record<string, string>>({});
  const [semanticSortTouched, setSemanticSortTouched] = useState<Record<string, boolean>>({});
  const [semanticBusy, setSemanticBusy] = useState<Record<string, boolean>>({});
  const semanticRequestIds = useRef<Record<string, number>>({});
  const currentWorkspaceId = useRef(workspaceId);
  const currentPanelControls = useRef(panelControls);
  currentWorkspaceId.current = workspaceId;
  currentPanelControls.current = panelControls;
  const [audioFilterForClips, setAudioFilterForClips] = useState('all');
  const [imageRoleFilter, setImageRoleFilter] = useState('all');
  const [role, setRole] = useState('style_reference');
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loadedAssetKey, setLoadedAssetKey] = useState('');
  const [assetLoadError, setAssetLoadError] = useState<{key: string; message: string} | null>(null);
  const [selectedVideoId, setSelectedVideoId] = useState('');
  const selectedVideoPlayer = useRef<HTMLElement>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [catalogVoices, setCatalogVoices] = useState<AudioVoice[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [annotationDrafts, setAnnotationDrafts] = useState<Record<string, {description: string; tags: string; audio_category: string}>>({});
  const [savingAssets, setSavingAssets] = useState<Set<string>>(new Set());
  const [archivingAssets, setArchivingAssets] = useState<Set<string>>(new Set());
  const [indexingAssets, setIndexingAssets] = useState<Set<string>>(new Set());
  const [importingVoiceIds, setImportingVoiceIds] = useState<Set<string>>(new Set());
  const [contentIndexJobs, setContentIndexJobs] = useState<Record<string, SemanticIndexJob>>({});
  const [seoStyles, setSeoStyles] = useState<MediaSeoStyle[]>([]);
  const [seoStyleId, setSeoStyleId] = useState('');
  const [seoName, setSeoName] = useState('');
  const [weightedTerms, setWeightedTerms] = useState('');
  const [avoidTerms, setAvoidTerms] = useState('');
  const [editingStyleId, setEditingStyleId] = useState('');
  const [savingStyle, setSavingStyle] = useState(false);
  const [checkedIds,setCheckedIds]=useState<string[]>([]);
  useEffect(()=>setCheckedIds([]),[workspaceId,kind,showArchived,panelControls,imageRoleFilter,audioFilterForClips]);
  const removeSelected=async()=>{setBusy(true);try{const message=await deleteSelectedMedia(workspaceId,checkedIds);await load();setMessage(message);}catch(e){await load();setMessage((e as Error).message);}finally{setCheckedIds([]);setBusy(false);}};
  const assetKey = `${workspaceId}|${kind}|${showArchived}`;

  useEffect(() => {
    if (selectedVideoId && kind === 'video') selectedVideoPlayer.current?.scrollIntoView({block: 'start'});
  }, [selectedVideoId, kind]);

  useEffect(() => {
    void listStoryWorkspaces().then(page => {
      setWorkspaces(page.items || []);
      const requestedWorkspace = new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || '';
      setWorkspaceId(preferredMediaWorkspaceId(page.items || [], requestedWorkspace));
    }).catch(error => setMessage(`Could not load workspaces: ${(error as Error).message}`));
  }, []);

  const load = async () => {
    if (!workspaceId) return;
    const requestId = ++assetLoadSequence.current;
    const requestKey = `${workspaceId}|${kind}|${showArchived}`;
    setAssetLoadError(null);
    setBusy(true);
    try {
      const [result, voices] = await Promise.all([listMediaAssets(workspaceId, kind, showArchived), kind === 'audio' ? listAudioVoices() : Promise.resolve([] as AudioVoice[])]);
      if (requestId !== assetLoadSequence.current) return;
      setAssets(result.assets); setCatalogVoices(voices); setMessage('');
    }
    catch (error) {
      if (requestId === assetLoadSequence.current) {
        const errorMessage = `Could not load assets: ${(error as Error).message}`;
        setAssets([]); setAssetLoadError({key: requestKey, message: errorMessage}); setMessage(errorMessage);
      }
    }
    finally { if (requestId === assetLoadSequence.current) { setLoadedAssetKey(requestKey); setBusy(false); } }
  };
  useEffect(() => {
    setSemanticIds({}); setSemanticQueries({}); void load();
    return () => { assetLoadSequence.current += 1; };
  }, [workspaceId, kind, showArchived]);
  useEffect(() => {
    if (!workspaceId) { setContentIndexJobs({}); return; }
    let active = true;
    void listMediaContentIndexJobs(workspaceId).then(jobs => {
      if (active) {
        const latestByAsset = new Map<string,SemanticIndexJob>();
        for (const job of jobs) if (!latestByAsset.has(job.request.asset_id)) latestByAsset.set(job.request.asset_id,job);
        setContentIndexJobs(Object.fromEntries(latestByAsset));
      }
    }).catch(error=>{if(active)setMessage(`Could not load semantic indexing jobs: ${(error as Error).message}`);});
    return ()=>{active=false;};
  }, [workspaceId]);
  useEffect(() => {
    if (!workspaceId) { setSeoStyles([]); return; }
    let active = true;
    void listMediaSeoStyles(workspaceId).then(result => { if (active) setSeoStyles(Array.isArray(result.styles) ? result.styles : []); })
      .catch(error => { if (active) setMessage(`Could not load SEO styles: ${(error as Error).message}`); });
    return () => { active = false; };
  }, [workspaceId]);

  useEffect(() => {
    const active = Object.entries(contentIndexJobs).filter(([,job]) => job.request.workspace_id === workspaceId && ['queued','running','cancel_requested'].includes(job.status));
    if (!active.length) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      await Promise.all(active.map(async ([assetId,job]) => {
        try {
          const latest = await getMediaContentIndexJob(workspaceId, job.job_id);
          if (cancelled) return;
          setContentIndexJobs(current => ({...current, [assetId]: latest}));
          if (latest.status === 'completed') {
            await load();
            if (!cancelled && currentWorkspaceId.current === workspaceId) setMessage(`Indexed ${latest.request.modality} content for semantic search.`);
          }
          else if (latest.status === 'failed') setMessage(`Content indexing failed: ${latest.message}`);
        } catch (error) { if (!cancelled) setMessage(`Could not read indexing status: ${(error as Error).message}`); }
      }));
    }, 1200);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [contentIndexJobs, workspaceId]);

  const workspaceOptions = useMemo(() => {
    return mediaWorkspaceOptions(workspaces, workspaceId);
  }, [workspaces, workspaceId]);

  const assetsForPanel = (panel: string) => {
    const control = panelControls[panel] || {search: '', order: 'newest' as const, view: 'template' as const, mode:'keyword' as const};
    const importedCatalogIds = new Set(assets.map(asset => asset.metadata?.comfyui_voice_catalog?.catalog_id).filter((id): id is string => typeof id === 'string'));
    const sharedAssets: MediaAsset[] = panel === 'voice-files' ? catalogVoices.filter(voice => !importedCatalogIds.has(voice.id)).map(voice => ({
      asset_id: `comfy-voice:${voice.id}`, workspace_id: workspaceId, kind: 'audio' as const,
      roles: ['voice_master'], filename: voice.relative_path, media_type: 'audio/*', sha256: '',
      size_bytes: voice.size_bytes, content_url: voice.content_url, created_at: voice.created_at,
      description: `${voice.source === 'bundled' ? 'Bundled' : 'ComfyUI'} voice${voice.has_transcript ? ' · transcript available' : ''}`,
      audio_category: 'voice' as const, catalog_only: true,
    })) : [];
    const rows = Array.from(new Map([...assets, ...sharedAssets].map(asset => [asset.asset_id, asset])).values()).filter(asset => {
    if (panel === 'voice-files' && !(asset.roles || []).includes('voice_master')) return false;
    if (panel === 'audio-clips' && (asset.roles || []).includes('voice_master')) return false;
    if (panel === 'image' && imageRoleFilter !== 'all') {
      const roles = asset.roles || [];
      const roleGroups: Record<string, string[]> = {
        character: ['character_master', 'character_image', 'character_view'],
        world: ['world_master', 'world_image', 'world_view'],
        first_frame: ['first_frame'],
        last_frame: ['last_frame'],
      };
      const isKnownRole = Object.values(roleGroups).flat().some(role => roles.includes(role));
      if (imageRoleFilter === 'other' ? isKnownRole : !roleGroups[imageRoleFilter]?.some(role => roles.includes(role))) return false;
    }
    const draft = annotationDrafts[asset.asset_id];
    const category = draft?.audio_category || asset.audio_category || '';
    const text = [asset.filename, ...(asset.roles || []), asset.description, ...(asset.tags || []), asset.provenance_notes,
      draft?.description, draft?.tags, category].filter(Boolean).join(' ').toLowerCase();
    return control.mode === 'semantic' || !control.search.trim() || text.includes(control.search.trim().toLowerCase());
    });
    if (control.mode === 'semantic') {
      if ((semanticQueries[panel] || '') !== control.search.trim()) return [];
      const ids = semanticIds[panel] || [];
      const matches = [...new Set(ids)].map(id => rows.find(asset => asset.asset_id === id)).filter((asset): asset is MediaAsset => !!asset);
      return semanticSortTouched[panel] ? rankMediaAssets(matches, '', control.order) : matches;
    }
    return rankMediaAssets(rows, '', control.order, seoStyles.find(style => style.style_id === seoStyleId));
  };

  const annotationFor = (asset: MediaAsset) => annotationDrafts[asset.asset_id] || {
    description: asset.description || '', tags: (asset.tags || []).join(', '), audio_category: asset.audio_category || '',
  };
  const patchAnnotation = (asset: MediaAsset, change: Partial<{description: string; tags: string; audio_category: string}>) => {
    setAnnotationDrafts(current => ({...current, [asset.asset_id]: {...annotationFor(asset), ...change}}));
  };
  const saveAnnotation = async (asset: MediaAsset) => {
    const value = annotationFor(asset); setSavingAssets(current => new Set(current).add(asset.asset_id)); setMessage('');
    try {
      const saved = await updateMediaAnnotations(workspaceId, asset.asset_id, {
        description: value.description, tags: value.tags.split(/[,;\n]+/).map(tag => tag.trim()).filter(Boolean),
        audio_category: asset.kind === 'audio' && value.audio_category ? value.audio_category as 'voice'|'sfx'|'music'|'dialogue' : null,
      });
      setAssets(current => current.map(row => row.asset_id === saved.asset_id ? saved : row));
      setAnnotationDrafts(current => { const next = {...current}; delete next[asset.asset_id]; return next; });
      setMessage('Search metadata saved.');
    } catch (error) { setMessage(`Could not save search metadata: ${(error as Error).message}`); }
    finally { setSavingAssets(current => { const next = new Set(current); next.delete(asset.asset_id); return next; }); }
  };

  const indexAnnotations = async (asset: MediaAsset) => {
    setIndexingAssets(current => new Set(current).add(asset.asset_id)); setMessage('');
    try {
      const result = await indexMediaAssetAnnotations(workspaceId, asset.asset_id);
      setAssets(current => current.map(row => row.asset_id === result.asset.asset_id ? result.asset : row));
      setMessage('Saved filename and search details are indexed with PE-AV text embeddings. Image pixels and raw audio/video were not embedded.');
    } catch (error) { setMessage(`Could not index saved search details: ${(error as Error).message}`); }
    finally { setIndexingAssets(current => { const next = new Set(current); next.delete(asset.asset_id); return next; }); }
  };
  const indexContent = async (asset: MediaAsset) => {
    if (!workspaceId) return;
    setIndexingAssets(current => new Set(current).add(asset.asset_id));
    try {
      const admission = await getGpuAdmission();
      if (!admission.available) {
        setMessage(`Content indexing is blocked: ${admission.reason || 'GPU admission is not ready.'}`);
        return;
      }
      const job = await createMediaContentIndexJob(workspaceId, asset.asset_id);
      setContentIndexJobs(current => ({...current, [asset.asset_id]: job}));
      setMessage(`Queued ${asset.kind} content indexing.`);
    } catch (error) { setMessage(`Could not queue content indexing: ${(error as Error).message}`); }
    finally { setIndexingAssets(current => { const next = new Set(current); next.delete(asset.asset_id); return next; }); }
  };
  const cancelContentIndex = async (assetId:string, jobId:string) => {
    try { const job = await cancelMediaContentIndexJob(workspaceId, jobId); setContentIndexJobs(current=>({...current,[assetId]:job})); }
    catch (error) { setMessage(`Could not cancel content indexing: ${(error as Error).message}`); }
  };
  const retryContentIndex = async (assetId:string, jobId:string) => {
    try { const job = await retryMediaContentIndexJob(workspaceId, jobId); setContentIndexJobs(current=>({...current,[assetId]:job})); }
    catch (error) { setMessage(`Could not retry content indexing: ${(error as Error).message}`); }
  };
  const importCatalogVoice = async (voiceId: string, voiceName: string) => {
    if (!workspaceId || importingVoiceIds.has(voiceId)) return;
    const requestSequence = assetLoadSequence.current;
    setImportingVoiceIds(current => new Set(current).add(voiceId)); setMessage('');
    try {
      const {asset} = await importComfyVoiceToWorkspace(workspaceId, voiceId);
      if (requestSequence !== assetLoadSequence.current || currentWorkspaceId.current !== workspaceId) return;
      setAssets(current => current.some(row => row.asset_id === asset.asset_id) ? current : [asset, ...current]);
      setMessage(`${voiceName} copied into this workspace. It is now available for audio-content indexing and semantic search.`);
    } catch (error) { if (requestSequence === assetLoadSequence.current) setMessage(`Could not copy voice into this workspace: ${(error as Error).message}`); }
    finally { setImportingVoiceIds(current => { const next = new Set(current); next.delete(voiceId); return next; }); }
  };

  const archiveAsset = async (asset: MediaAsset) => {
    if (!workspaceId || archivingAssets.has(asset.asset_id)) return;
    const archived = !asset.archived_at;
    setArchivingAssets(current => new Set(current).add(asset.asset_id)); setMessage('');
    try {
      const result = await setMediaAssetArchived(workspaceId, asset.asset_id, archived);
      setAssets(current => archived
        ? showArchived ? current.map(row => row.asset_id === asset.asset_id ? result.asset : row) : current.filter(row => row.asset_id !== asset.asset_id)
        : current.map(row => row.asset_id === asset.asset_id ? result.asset : row));
      setMessage(archived ? 'Asset archived. Its file and existing references are kept.' : 'Asset restored to the library.');
    } catch (error) { setMessage(`Could not ${archived ? 'archive' : 'restore'} asset: ${(error as Error).message}`); }
    finally { setArchivingAssets(current => { const next = new Set(current); next.delete(asset.asset_id); return next; }); }
  };

  const deleteClip = async (asset:MediaAsset) => {
    setArchivingAssets(current=>new Set(current).add(asset.asset_id));
    try {setMessage(await deleteSelectedMedia(workspaceId,[asset.asset_id]));await load();}
    catch(error) {setMessage((error as Error).message);await load();}
    finally {setArchivingAssets(current=>{const next=new Set(current);next.delete(asset.asset_id);return next;});}
  };

  const saveSeoStyle = async () => {
    const terms: Array<{term: string; weight: number}> = [];
    for (const line of weightedTerms.split(/\n+/).map(value => value.trim()).filter(Boolean)) {
      const match = /^(.*?)\s*=\s*(\d+(?:\.\d+)?)$/.exec(line);
      if (!match || Number(match[2]) < 0.1 || Number(match[2]) > 10) { setMessage(`Use one weighted term per line, from 0.1 to 10 (example: rain=2). Invalid: ${line}`); return; }
      terms.push({term: match[1].trim(), weight: Number(match[2])});
    }
    setSavingStyle(true); setMessage('');
    try {
      const saved = await saveMediaSeoStyle(workspaceId, {name: seoName, weighted_terms: terms,
        avoid_terms: avoidTerms.split(/[,;\n]+/).map(value => value.trim()).filter(Boolean)}, editingStyleId || undefined);
      setSeoStyles(current => editingStyleId ? current.map(style => style.style_id === saved.style_id ? saved : style) : [...current, saved]);
      setSeoStyleId(saved.style_id); setEditingStyleId(''); setSeoName(''); setWeightedTerms(''); setAvoidTerms(''); setMessage('SEO search style saved.');
    } catch (error) { setMessage(`Could not save SEO style: ${(error as Error).message}`); }
    finally { setSavingStyle(false); }
  };
  const editSeoStyle = (style: MediaSeoStyle) => {
    setSeoStyleId(style.style_id); setEditingStyleId(style.style_id); setSeoName(style.name);
    setWeightedTerms(style.weighted_terms.map(row => `${row.term}=${row.weight}`).join('\n')); setAvoidTerms(style.avoid_terms.join(', '));
  };
  const removeSeoStyle = async (style: MediaSeoStyle) => {
    try { await deleteMediaSeoStyle(workspaceId, style.style_id); setSeoStyles(current => current.filter(row => row.style_id !== style.style_id));
      if (seoStyleId === style.style_id) setSeoStyleId(''); setMessage('SEO search style deleted.'); }
    catch (error) { setMessage(`Could not delete SEO style: ${(error as Error).message}`); }
  };

  const onFile = (event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] || null);
  const chooseDroppedFile = (files: FileList | readonly File[]) => {
    if (!files.length) return;
    setFile(files[0]);
  };
  const onDropMedia = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    chooseDroppedFile(event.dataTransfer.files);
  };
  const onPasteMedia = (event: ClipboardEvent<HTMLDivElement>) => {
    const files = event.clipboardData.files;
    if (!files.length) return;
    event.preventDefault();
    chooseDroppedFile(files);
  };
  const onDropZoneKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      uploadInput.current?.click();
    }
  };
  const upload = async () => {
    if (!workspaceId || !file) return;
    const requestSequence = assetLoadSequence.current;
    setBusy(true); setMessage('');
    try {
      const saved = await uploadMediaAsset(workspaceId, file, role);
      // Navigation or a newer library load owns the visible state now.
      if (requestSequence !== assetLoadSequence.current || currentWorkspaceId.current !== workspaceId) return;
      setKind(saved.kind); setFile(null);
      const input = document.getElementById('media-upload') as HTMLInputElement | null;
      if (input) input.value = '';
      setMessage(saved.deduplicated ? 'This file was already in the library; its role was added.' : 'Added to the workspace library.');
      if (saved.kind === kind) setAssets(current => [
        ...(!saved.archived_at || showArchived ? [saved] : []),
        ...current.filter(asset => asset.asset_id !== saved.asset_id),
      ]);
    } catch (error) { if (requestSequence === assetLoadSequence.current) setMessage(`Upload failed: ${(error as Error).message}`); }
    finally { if (requestSequence === assetLoadSequence.current) setBusy(false); }
  };

  const icon = kind === 'image' ? <ImageIcon size={16}/> : kind === 'video' ? <Video size={16}/> : <AudioLines size={16}/>;
  const patchPanel = (panel: string, change: Partial<PanelControls>) => setPanelControls(current => ({
    ...current, [panel]: {...(current[panel] || {search: '', order: 'newest', view: 'template'}), ...change},
  }));
  const chooseView = (panel: string, view: AssetView) => {
    patchPanel(panel, {view});
    try { localStorage.setItem(`vibe-media-view-${panel}-v1`, view); } catch { /* Keep the selected view for this page session. */ }
  };
  const runSemanticSearch = async (panel: string, targetKind: Kind) => {
    const control = panelControls[panel];
    if (!workspaceId || !control?.search.trim()) return;
    const requestId = (semanticRequestIds.current[panel] || 0) + 1;
    const requestedWorkspace = workspaceId;
    const requestedQuery = control.search.trim();
    semanticRequestIds.current[panel] = requestId;
    setSemanticBusy(current => ({...current, [panel]: true})); setMessage('');
    try {
      const result = await searchMediaSemantically(requestedWorkspace, targetKind, requestedQuery);
      if (semanticRequestIds.current[panel] !== requestId || currentWorkspaceId.current !== requestedWorkspace ||
          currentPanelControls.current[panel]?.search.trim() !== requestedQuery || currentPanelControls.current[panel]?.mode !== 'semantic') return;
      setSemanticIds(current => ({...current, [panel]: result.results.map(row => row.asset.asset_id)}));
      setSemanticQueries(current => ({...current, [panel]: requestedQuery}));
      setMessage(result.reason ? result.reason : `Found ${result.results.length} semantic matches (${result.query_backend || 'model'} embeddings).`);
    } catch (error) {
      if (semanticRequestIds.current[panel] === requestId && currentWorkspaceId.current === requestedWorkspace &&
          currentPanelControls.current[panel]?.search.trim() === requestedQuery) {
        setSemanticIds(current => ({...current, [panel]: []}));
        setMessage(`Semantic search unavailable: ${(error as Error).message}`);
      }
    } finally {
      if (semanticRequestIds.current[panel] === requestId) setSemanticBusy(current => ({...current, [panel]: false}));
    }
  };
  const assetGrid = (panel: string, rows: MediaAsset[], emptyText: string) => {
    const view = panelControls[panel]?.view || 'template';
    const controls = panelControls[panel];
    const renderKey = `${panel}:${view}:${controls?.mode || 'keyword'}:${controls?.search || ''}:${semanticQueries[panel] || ''}`;
    if (workspaceId && loadedAssetKey !== assetKey) {
      return <div key={`${renderKey}:loading`} className="card media-empty" role="status">Loading {kind}s…</div>;
    }
    if (!rows.length) {
      if (assetLoadError?.key === assetKey) {
        return <div key={`${renderKey}:error`} className="card media-empty" role="status">{assetLoadError.message}. Refresh to try again.</div>;
      }
      const query = controls?.search.trim() || '';
      const previousQuery = semanticQueries[panel] || '';
      const workspaceLabel = workspaceOptions.find(option => option.id === workspaceId)?.label;
      const noSavedVideos = panel === 'video' && !query && controls?.mode !== 'semantic' && !!workspaceId;
      const empty = controls?.mode !== 'semantic' ? query ? `No results for “${query}” in ${workspaceLabel || 'this workspace'}.` : noSavedVideos ? `No active videos in “${workspaceLabel}”. Add a file above, download from YouTube, or import copied videos from Video Summariser. Archived videos are available when “Show archived” is enabled.` : emptyText
        : !query ? 'Enter a description, then run semantic search.'
        : previousQuery !== query ? 'The query changed. Run semantic search to refresh results.'
        : 'No semantic matches found.';
      return <div key={renderKey} className="card media-empty" role="status">{icon}<div><p>{empty}</p>{query && controls?.mode !== 'semantic' && <button className="text-button" type="button" onClick={()=>{patchPanel(panel,{search:''});setSemanticIds(current=>({...current,[panel]:[]}));setSemanticQueries(current=>({...current,[panel]:''}));}}>Clear search and show all</button>}{noSavedVideos && <div className="media-empty-actions"><a className="quiet-button" href={`#/media-prep?tool=video&workspace_id=${encodeURIComponent(workspaceId)}`}>Open Video Summariser</a><a className="quiet-button" href={`#/media-prep?tool=video&videoPage=youtube&workspace_id=${encodeURIComponent(workspaceId)}`}>Open YouTube Download</a></div>}</div></div>;
    }
    const selectedVideo = panel === 'video' ? rows.find(asset => asset.asset_id === selectedVideoId) : undefined;
    return <><div className="summariser-toolbar" aria-label={`${panel} selection controls`}><button className="quiet-button" disabled={busy} onClick={()=>setCheckedIds(rows.filter(a=>!a.recommended&&!a.catalog_only).map(a=>a.asset_id))}>Select all shown ({rows.filter(a=>!a.recommended&&!a.catalog_only).length})</button><button className="quiet-button" disabled={busy||!checkedIds.length} onClick={()=>setCheckedIds([])}>Deselect all</button><span>{checkedIds.length} selected</span><button className="quiet-button" disabled={busy||!checkedIds.length} onClick={()=>void removeSelected()}>Delete files permanently</button></div><div key={renderKey} className={`media-asset-grid media-view-${view}`} aria-label={`${panel} assets · ${view} view`}>{rows.map(asset => { const annotations = annotationFor(asset); const lineage = asset.metadata?.production_image_job?.settings?.lineage; const worldView = asset.metadata?.production_image_job?.world_view; const association = lineage ? [lineage.target_name, typeof lineage.scene_number === 'number' ? `Scene ${lineage.scene_number}` : '', typeof lineage.shot_number === 'number' ? `Shot ${lineage.shot_number}` : '', lineage.clip_id ? `Clip ${lineage.clip_id}` : ''].filter(Boolean).join(' · ') : ''; return <article className="card media-asset" key={asset.asset_id}>
      {!asset.recommended&&!asset.catalog_only&&<label className="media-select"><input type="checkbox" aria-label={`Select ${asset.filename}`} disabled={busy} checked={checkedIds.includes(asset.asset_id)} onChange={()=>setCheckedIds(ids=>ids.includes(asset.asset_id)?ids.filter(id=>id!==asset.asset_id):[...ids,asset.asset_id])}/> Select</label>}<div className="media-preview"><LibraryPreview asset={asset}/></div>
      {asset.kind === 'video' && <button className="quiet-button media-open-player" type="button" aria-pressed={selectedVideoId === asset.asset_id} onClick={()=>setSelectedVideoId(asset.asset_id)}>{selectedVideoId === asset.asset_id ? 'Selected for playback below' : 'Play video below'}</button>}
      <div className="media-asset-details"><b className="media-asset-name" title={asset.filename} tabIndex={0}>{asset.filename}</b>{asset.recommended && <span className="style-recommendation-badge">Recommended from production style</span>}{asset.archived_at && <span className="style-recommendation-badge">Archived</span>}<span>{asset.catalog_only ? 'ComfyUI voice · original stays in place' : asset.roles.join(' · ')}{asset.recommended && asset.source_workspace_id ? ` · source ${asset.source_workspace_id}` : ''}</span><small>{asset.kind === 'image' && asset.media?.width && asset.media?.height ? `${asset.media.width} × ${asset.media.height} · ` : ''}{asset.media?.duration_seconds ? `${asset.media.duration_seconds.toFixed(1)} sec · ` : ''}{Math.max(1, Math.round(asset.size_bytes / 1024))} KB</small>
        <small>{asset.description || ""}</small>{asset.kind === 'image' && (association || worldView?.label) && <small>Associated with: {[association, worldView?.label ? `${worldView.label} view` : ''].filter(Boolean).join(' · ')}</small>}{!!asset.provenance_notes && <small>Source notes: {asset.provenance_notes}</small>}{!!asset.tags?.length && <small>Search tags: {asset.tags.join(", ")}</small>}{asset.kind === 'audio' && <>
          <small>Audio type: {asset.audio_category || 'Not recorded'}</small>
          <small>Added: {asset.created_at ? asset.created_at.slice(0, 10) : 'Date not recorded'}</small>
          <small>Source: {asset.metadata?.source_asset_name || asset.metadata?.source_asset_id || 'Not recorded'}{typeof asset.metadata?.timestamp_start_seconds === 'number' && typeof asset.metadata?.timestamp_end_seconds === 'number' ? ` · ${asset.metadata.timestamp_start_seconds.toFixed(2)}–${asset.metadata.timestamp_end_seconds.toFixed(2)} sec` : ''}</small>
        </>}{asset.catalog_only && <button className="quiet-button" type="button" disabled={!workspaceId || importingVoiceIds.has(asset.asset_id.replace(/^comfy-voice:/, ''))} onClick={()=>{const voiceId=asset.asset_id.replace(/^comfy-voice:/, ''); void importCatalogVoice(voiceId,asset.filename);}}>{importingVoiceIds.has(asset.asset_id.replace(/^comfy-voice:/, '')) ? 'Copying…' : 'Add to workspace'}</button>}{!asset.recommended && !asset.catalog_only && <>
        <label>Description<input value={annotations.description} disabled={savingAssets.has(asset.asset_id)} maxLength={2000} onChange={event=>patchAnnotation(asset,{description:event.target.value})}/></label><label>Search tags<input value={annotations.tags} disabled={savingAssets.has(asset.asset_id)} placeholder="e.g. courtroom, rain, side tracking" onChange={event=>patchAnnotation(asset,{tags:event.target.value})}/></label>
        {asset.kind === 'audio' && <label>Audio type<select value={annotations.audio_category} disabled={savingAssets.has(asset.asset_id)} onChange={event=>patchAnnotation(asset,{audio_category:event.target.value})}><option value="">Choose type</option><option value="voice">Voice only</option><option value="sfx">SFX</option><option value="music">Music</option><option value="dialogue">Dialogue</option></select></label>}
        <button className="quiet-button" type="button" disabled={savingAssets.has(asset.asset_id)} onClick={()=>void saveAnnotation(asset)}>{savingAssets.has(asset.asset_id) ? 'Saving…' : 'Save search details'}</button>
        <button className="quiet-button" type="button" disabled={!!annotationDrafts[asset.asset_id] || indexingAssets.has(asset.asset_id)} onClick={()=>void indexAnnotations(asset)} title="Uses PE-AV text embeddings for saved filename, description, tags and roles; it does not embed media pixels or audio/video content">{indexingAssets.has(asset.asset_id) ? 'Indexing…' : asset.semantic_annotation_index ? 'Reindex saved text' : 'Index saved text for semantic search'}</button>
        <button className="quiet-button" type="button" disabled={indexingAssets.has(asset.asset_id) || ['queued','running','cancel_requested'].includes(contentIndexJobs[asset.asset_id]?.status || '')} onClick={()=>void indexContent(asset)} title={asset.kind === 'image' ? 'Checks GPU admission before embedding the image through PE-AV’s visual encoder; the original image is unchanged' : 'Checks GPU admission before embedding the actual audio/video content with the isolated PE-AV model'}>{indexingAssets.has(asset.asset_id) ? 'Checking GPU readiness…' : contentIndexJobs[asset.asset_id] && ['queued','running'].includes(contentIndexJobs[asset.asset_id].status) ? `Indexing… ${contentIndexJobs[asset.asset_id].progress}%` : asset.semantic_content_index ? 'Reindex visual/media content' : 'Index visual/media content for semantic search'}</button>
        {contentIndexJobs[asset.asset_id] && <><small role="status">{contentIndexJobs[asset.asset_id].message}{contentIndexJobs[asset.asset_id].status === 'failed' ? ` · ${contentIndexJobs[asset.asset_id].error || ''}` : ''}</small>{['queued','running','cancel_requested'].includes(contentIndexJobs[asset.asset_id].status) && <button className="quiet-button" type="button" onClick={()=>void cancelContentIndex(asset.asset_id,contentIndexJobs[asset.asset_id].job_id)}>Cancel indexing</button>}{['failed','interrupted','cancelled'].includes(contentIndexJobs[asset.asset_id].status) && <button className="quiet-button" type="button" onClick={()=>void retryContentIndex(asset.asset_id,contentIndexJobs[asset.asset_id].job_id)}>Retry indexing</button>}</>}
        {asset.kind === 'image' && workspaceId && <a className="quiet-button" href={`#/media-prep?tool=image&workspace_id=${encodeURIComponent(workspaceId)}&asset_id=${encodeURIComponent(asset.asset_id)}`}>Open in Image Detailer</a>}
        {asset.kind === 'video' && workspaceId && <a className="quiet-button" href={`#/media-prep?tool=video&videoPage=analyze&workspace_id=${encodeURIComponent(workspaceId)}&asset_id=${encodeURIComponent(asset.asset_id)}`} title="Open the existing Video Summariser analysis form with this video selected. Analysis starts only when you click Analyze selected videos.">Analyze video for semantic search</a>}
        </>}{!asset.recommended && !asset.catalog_only && <button className="quiet-button" type="button" disabled={archivingAssets.has(asset.asset_id)} onClick={()=>void archiveAsset(asset)}>{archivingAssets.has(asset.asset_id) ? 'Working…' : asset.archived_at ? 'Restore to library' : 'Archive asset'}</button>}{!asset.recommended&&!asset.catalog_only&&(asset.metadata?.analyzer_run_id||asset.metadata?.sam_audio?.run_id)&&<button type="button" className="quiet-button" aria-label={`Remove extracted ${asset.kind==='image'?'image':'clip'} ${asset.filename}`} disabled={archivingAssets.has(asset.asset_id)} onClick={()=>void deleteClip(asset)}><Trash2 size={16}/></button>}{asset.kind === 'image' && !!asset.metadata?.image_analyses?.length && <details className="image-analysis-records"><summary>Image analysis · {asset.metadata.image_analyses.length} saved</summary>{asset.metadata.image_analyses.map((record,index)=><section key={`${record.job_id}-${index}`}><small>{record.mode} · {new Date(record.saved_at).toLocaleString()} · source {record.source_sha256.slice(0,12)}</small><pre className="summariser-error">{JSON.stringify(record.analysis,null,2)}</pre></section>)}</details>}
      </div>
    </article>; })}</div>{selectedVideo && <section ref={selectedVideoPlayer} className="card media-selected-player" aria-label="Selected video player"><div className="media-selected-player-heading"><div><h2>{selectedVideo.filename}</h2><p>Use the player controls to review this video with sound.</p></div><button className="quiet-button" type="button" onClick={()=>setSelectedVideoId('')}>Close player</button></div><video controls playsInline preload="metadata" src={selectedVideo.content_url} aria-label={`Play ${selectedVideo.filename}`}/></section>}</>;
  };
  const panelToolbar = (panel: string, label: string) => {
    const control = panelControls[panel] || {search: '', order: 'newest' as const, view: 'template' as const, mode:'keyword' as const};
    const targetKind: Kind = panel === 'video' ? 'video' : panel === 'image' ? 'image' : 'audio';
    return <><div className="media-library-search">
      <label className="media-search-entry"><span>Search {label}</span><div className="media-search-field"><Search size={17} aria-hidden="true"/><input type="search" aria-label={`Search ${label}`} placeholder={`Type ${label.replace(/s$/, '')} title, filename, notes or tags`} value={control.search} onChange={event=>{semanticRequestIds.current[panel]=(semanticRequestIds.current[panel]||0)+1;setSemanticBusy(current=>({...current,[panel]:false}));patchPanel(panel,{search:event.target.value});setSemanticIds(current=>({...current,[panel]:[]}));setSemanticQueries(current=>({...current,[panel]:''}));}}/></div></label>
      <div className="media-search-options"><label className="media-search-mode"><span>Search by</span><select aria-label={`${label} search mode`} value={control.mode} onChange={event=>{semanticRequestIds.current[panel]=(semanticRequestIds.current[panel]||0)+1;setSemanticBusy(current=>({...current,[panel]:false}));patchPanel(panel,{mode:event.target.value as 'keyword'|'semantic'});setSemanticIds(current=>({...current,[panel]:[]}));setSemanticQueries(current=>({...current,[panel]:''}));}}><option value="keyword">Name and tags</option><option value="semantic">Semantic</option></select></label>
      {control.mode === 'semantic' && <button className="quiet-button media-search-submit" type="button" disabled={!!semanticBusy[panel] || !control.search.trim()} onClick={()=>void runSemanticSearch(panel,targetKind)}>{semanticBusy[panel]?'Searching…':'Search'}</button>}
      <label className="media-search-ranking"><span>Ranking</span><select aria-label={`Rank ${label} by SEO style`} value={seoStyleId} onChange={event=>setSeoStyleId(event.target.value)}><option value="">Default ranking</option>{seoStyles.map(style=><option key={style.style_id} value={style.style_id}>{style.name}</option>)}</select></label>
      <button className="quiet-button media-sort" type="button" onClick={() => {patchPanel(panel,{order: control.order === 'newest' ? 'oldest' : 'newest'});if(control.mode==='semantic')setSemanticSortTouched(current=>({...current,[panel]:true}));}} aria-label={`Sort ${label} ${control.order === 'newest' ? 'oldest first' : 'newest first'}`} title={control.order === 'newest' ? 'Newest first' : 'Oldest first'}>{control.order === 'newest' ? '↓' : '↑'}</button>
      <div className="asset-view-switch" role="group" aria-label={`${label} view`}>{([{id:'template', label:'Template view', icon:<LayoutGrid size={15}/>},{id:'list',label:'List view',icon:<List size={15}/>},{id:'carousel',label:'Carousel view',icon:<GalleryHorizontal size={15}/>} ] as const).map(option=><button type="button" key={option.id} className="quiet-button" aria-label={option.label} aria-pressed={control.view===option.id} onClick={()=>chooseView(panel,option.id)}>{option.icon}<span>{option.id === 'template' ? 'Cards' : option.id === 'list' ? 'List' : 'Carousel'}</span></button>)}</div>
      </div>
    </div><small className="media-search-hint">{control.mode === 'semantic'
      ? 'Semantic search checks completed Video Summariser analysis and indexed library assets. Downloaded video titles and notes match immediately with “Name and tags”; use “Index saved text” on a video card to find them by meaning, or “Index visual/media content” to search the actual video. Type a description above, then click Search. ComfyUI catalogue voices remain keyword-only.'
      : 'Type in the large search box above to filter names, descriptions, tags and source notes as you go. For meaning-based results, choose Semantic in “Search by”; indexed media or completed Video Summariser analysis is required.'}</small></>;
  };
  return <div className="content-wrap media-library-page">
    <div className="page-heading"><div><div className="eyebrow">MEDIA PREP / LIBRARY</div><h1>Search library</h1><p>Find saved images, videos, voices and audio clips.</p></div><button className="quiet-button" type="button" onClick={() => void load()} disabled={busy}><RefreshCw size={15}/> Refresh</button></div>
    {message && <div className="notice" role="status">{message}</div>}
    <section className="card media-upload-card">
    <MediaSourcePicker workspaceId={workspaceId} kinds={[kind]} onAdded={items=>setAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/>
    <div className="media-fields"><label>Collection<select value={workspaceId} onChange={event => { const nextWorkspaceId = event.target.value; for (const panel of Object.keys(semanticRequestIds.current)) semanticRequestIds.current[panel] += 1; setSemanticBusy({}); if (nextWorkspaceId !== workspaceId) { setAssets([]); setCatalogVoices([]); setContentIndexJobs({}); setSeoStyles([]); setMessage(''); } setWorkspaceId(nextWorkspaceId); rememberMediaWorkspaceId(nextWorkspaceId); }} aria-label="Workspace">{workspaceOptions.map(value => <option key={value.id} value={value.id}>{value.label}</option>)}{!workspaceOptions.length && <option value="">Create a story or video workspace first</option>}</select></label>
        <label>Use as<select value={role} onChange={event => setRole(event.target.value)}><option value="style_reference">Style reference</option><option value="character_master">Character image</option><option value="world_master">World image</option><option value="first_frame">First frame</option><option value="last_frame">Last frame</option><option value="action_reference_video">Video reference</option><option value="voice_master">Character voice</option><option value="project_image">Other image</option><option value="project_video">Other video</option><option value="project_audio">Other audio</option></select></label>
        <div className="media-drop-zone" role="button" tabIndex={0} aria-label="Choose, drop, or paste a media file" onClick={event=>{if(event.target!==uploadInput.current)uploadInput.current?.click();}} onKeyDown={onDropZoneKeyDown} onDragOver={event=>event.preventDefault()} onDrop={onDropMedia} onPaste={onPasteMedia}>
          <FileUp size={16}/><span>{file ? file.name : 'Choose, drop, or paste a media file'}</span>
          <input ref={uploadInput} id="media-upload" aria-label="Choose media file" type="file" accept="image/png,image/jpeg,image/webp,video/mp4,video/quicktime,video/x-matroska,video/webm,audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/flac,audio/aac" onChange={onFile}/>
        </div>
        <button className="generate-button" type="button" onClick={() => void upload()} disabled={busy || !workspaceId || !file}><FileUp size={15}/>{busy ? 'Working…' : 'Add asset'}</button>
      </div>
    </section>
    <div className="media-library-tabs" role="tablist" aria-label="Asset type">{(['image','video','audio'] as Kind[]).map(value => <button key={value} role="tab" aria-selected={kind === value} className={kind === value ? 'selected' : ''} onClick={() => { for (const panel of Object.keys(semanticRequestIds.current)) semanticRequestIds.current[panel] += 1; setSemanticBusy({}); setKind(value); const route = window.location.hash.split('?')[0]; const params = new URLSearchParams(window.location.hash.split('?')[1] || ''); params.set('kind', value); window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${route}?${params.toString()}`); }}>{value === 'image' ? <ImageIcon size={15}/> : value === 'video' ? <Video size={15}/> : <AudioLines size={15}/>} {value[0].toUpperCase() + value.slice(1)}s</button>)}</div>
    <label className="archived-media-toggle"><input type="checkbox" checked={showArchived} onChange={event=>setShowArchived(event.target.checked)}/> Show archived</label>
    {kind === 'audio' ? <div className="audio-repertoire-panels">
      <section className="card audio-repertoire-panel"><div className="section-title"><div><h2>Voice Files</h2><p>Workspace voices and configured ComfyUI voices appear here. ComfyUI originals stay in place.</p></div></div>{panelToolbar('voice-files','voice files')}{assetGrid('voice-files',assetsForPanel('voice-files'),'No voice files are available yet.')}</section>
      <section className="card audio-repertoire-panel"><div className="section-title"><div><h2>Audio Clips</h2><p>Dialogue, music, sound effects and other audio.</p></div></div>{panelToolbar('audio-clips','audio clips')}<label className="audio-kind-filter">Type<select aria-label="Filter audio clip type" value={audioFilterForClips} onChange={event=>setAudioFilterForClips(event.target.value)}><option value="all">All audio clips</option><option value="voice">Voice recordings</option><option value="sfx">SFX</option><option value="music">Music</option><option value="dialogue">Dialogue</option></select></label>{assetGrid('audio-clips',assetsForPanel('audio-clips').filter(asset=>audioFilterForClips==='all'||(asset.audio_category||'')===audioFilterForClips),'No audio clips saved in this workspace yet.')}</section>
    </div> : <>{panelToolbar(kind,`${kind}s`)}{kind === 'image' && <label className="image-role-filter">Image role<select aria-label="Filter images by role" value={imageRoleFilter} onChange={event=>setImageRoleFilter(event.target.value)}><option value="all">All images</option><option value="character">Characters</option><option value="world">Worlds</option><option value="first_frame">First frames</option><option value="last_frame">Last frames</option><option value="other">Other</option></select></label>}{assetGrid(kind,assetsForPanel(kind),workspaceId ? `No ${kind}s saved in this workspace yet.` : 'Choose or create a workspace to see its assets.')}</>}
    <section className="card seo-style-manager">
      <div className="section-title"><div><h2>Search ranking styles</h2><p>Optional: weight matching reference terms in search results.</p></div></div>
      <div className="seo-style-form"><label>Style name<input aria-label="SEO style name" value={seoName} maxLength={80} onChange={event=>setSeoName(event.target.value)}/></label>
        <label>Weighted terms<textarea aria-label="Weighted search terms" placeholder={'rain=2\ncourtroom=1.5'} value={weightedTerms} onChange={event=>setWeightedTerms(event.target.value)}/></label>
        <label>Downrank terms<textarea aria-label="Downrank terms" placeholder="cartoon, low resolution" value={avoidTerms} onChange={event=>setAvoidTerms(event.target.value)}/></label>
        <button className="quiet-button" type="button" disabled={savingStyle || !workspaceId} onClick={()=>void saveSeoStyle()}>{savingStyle ? 'Saving…' : editingStyleId ? 'Update style' : 'Save style'}</button>
      </div>
      {!!seoStyles.length && <ul className="seo-style-list">{seoStyles.map(style=><li key={style.style_id}><button type="button" className="text-button" onClick={()=>editSeoStyle(style)}>{style.name}</button><small>{style.weighted_terms.length} weighted terms</small><button className="quiet-button" type="button" onClick={()=>void removeSeoStyle(style)}>Delete</button></li>)}</ul>}
    </section>
  </div>;
}
