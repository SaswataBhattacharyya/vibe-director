import {managedProjectId} from './lib/media-workspace';
import MediaSourcePicker from './MediaSourcePicker';
import SelectionToggle from './SelectionToggle';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ArrowRight, Check, LoaderCircle, Palette, RefreshCw, Save, Sparkles } from 'lucide-react';
import { DirectorProfile, DirectingStyle, DirectingStyleEvidence, DocumentStyleEvidence, ImageStyleProposal, analyzeStyleImages, analyzeStyleSources, getStyleCatalog, getStyleSelections, ProductionStyle, publishProductionType, publishDirectingStyle, saveStyleSelection, StyleSelection, StyleSource, listStyleSources, getStyleSource, uploadStyleSource } from './lib/styles-api';
import { cancelStyleFrameJob, extractMediaStyleFrames, getStyleFrameJob, linkMediaAssetToStyle, listMediaAssets, MediaAsset, StyleFrameJob, uploadMediaAsset } from './lib/media-api';

const CONTEXT_KEY = 'vibe-style-setup-context-v1';
const FORM_KEY = 'vibe-style-custom-form-v1';
const DIRECTION_FORM_KEY = 'vibe-custom-direction-form-v1';
const guidanceStages = [
  ['story', 'Story guidance'], ['scene_direction', 'Scene direction'], ['image', 'Image guidance'],
  ['audio', 'Audio guidance'], ['video', 'Video guidance'], ['review', 'Review guidance'],
] as const;
type CustomForm = { production_type: string; display_name: string; purpose: string; stages: Record<string,string>; behavior: string; review_priorities: string };
type DirectionForm = { style_id:string; display_name:string; guidance:string; scope_type:'cross_type'|'production_type'; evidence:Record<string,string>; source_ids:string[]; source_intent:string; image_source_ids:string[]; image_intent:string; document_evidence:DocumentStyleEvidence[]; media_analysis_evidence:ImageStyleProposal['evidence'] };
const emptyForm = (): CustomForm => ({ production_type: '', display_name: '', purpose: '', stages: Object.fromEntries(guidanceStages.map(([key]) => [key, ''])), behavior: '', review_priorities: '' });
const emptyDirectionForm = (): DirectionForm => ({style_id:'',display_name:'',guidance:'',scope_type:'cross_type',evidence:{},source_ids:[],source_intent:'',image_source_ids:[],image_intent:'',document_evidence:[],media_analysis_evidence:[]});
function readForm(): CustomForm {
  try {
    const value = JSON.parse(localStorage.getItem(FORM_KEY) || 'null');
    if (!value || typeof value !== 'object' || Array.isArray(value)) return emptyForm();
    const defaults = emptyForm();
    const text = (item: unknown, fallback: string) => typeof item === 'string' ? item : fallback;
    const rawStages = value.stages && typeof value.stages === 'object' && !Array.isArray(value.stages) ? value.stages as Record<string, unknown> : {};
    return {
      production_type: text(value.production_type, defaults.production_type),
      display_name: text(value.display_name, defaults.display_name),
      purpose: text(value.purpose, defaults.purpose),
      behavior: text(value.behavior, defaults.behavior),
      review_priorities: text(value.review_priorities, defaults.review_priorities),
      stages: Object.fromEntries(guidanceStages.map(([key]) => [key, text(rawStages[key], defaults.stages[key])])),
    };
  }
  catch { return emptyForm(); }
}
function valueText(value: unknown): string {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(valueText).filter(Boolean).join('\n');
  if (value && typeof value === 'object') return Object.entries(value as Record<string, unknown>).map(([key, item]) => `${key.replaceAll('_', ' ')}: ${valueText(item)}`).filter(Boolean).join('\n');
  return value == null ? '' : String(value);
}
function lines(value: string) { return value.split(/\r?\n/).map(item => item.trim()).filter(Boolean); }
function initialContext(): string { try { const value = localStorage.getItem(CONTEXT_KEY) || ''; return /^setup-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value) ? value : ''; } catch { return ''; } }
function readDirectionForm(): DirectionForm { try { const value=JSON.parse(localStorage.getItem(DIRECTION_FORM_KEY)||'null'); return value&&typeof value==='object' ? {style_id:typeof value.style_id==='string'?value.style_id:'',display_name:typeof value.display_name==='string'?value.display_name:'',guidance:typeof value.guidance==='string'?value.guidance:'',scope_type:value.scope_type==='production_type'?'production_type':'cross_type',evidence:value.evidence&&typeof value.evidence==='object'&&!Array.isArray(value.evidence)?Object.fromEntries(Object.entries(value.evidence).filter((entry):entry is [string,string]=>typeof entry[1]==='string')):{},source_ids:Array.isArray(value.source_ids)?value.source_ids.filter((id:unknown):id is string=>typeof id==='string'):[],source_intent:typeof value.source_intent==='string'?value.source_intent:'',image_source_ids:Array.isArray(value.image_source_ids)?value.image_source_ids.filter((id:unknown):id is string=>typeof id==='string'):[],image_intent:typeof value.image_intent==='string'?value.image_intent:'',document_evidence:Array.isArray(value.document_evidence)?value.document_evidence.filter((item:unknown):item is DocumentStyleEvidence=>Boolean(item&&typeof item==='object'&&(item as DocumentStyleEvidence).kind==='document')):[],media_analysis_evidence:Array.isArray(value.media_analysis_evidence)?value.media_analysis_evidence.filter((item:unknown):item is ImageStyleProposal['evidence'][number]=>Boolean(item&&typeof item==='object'&&['image','audio','video'].includes(String((item as {kind?:unknown}).kind)))):[]} : emptyDirectionForm(); } catch { return emptyDirectionForm(); } }

export default function ProductionStylesPage() {
  const [contextId, setContextId] = useState(initialContext);
  const [selectionWorkspaceId] = useState(() => managedProjectId()==='tool-library'?'':managedProjectId()||new URLSearchParams(window.location.hash.split('?')[1] || '').get('workspace_id') || '');
  const [storageWarning, setStorageWarning] = useState('');
  const [catalog, setCatalog] = useState<ProductionStyle[]>([]);
  const [directingStyles, setDirectingStyles] = useState<DirectingStyle[]>([]);
  const [catalogVersion, setCatalogVersion] = useState('');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [selectedDirectionId, setSelectedDirectionId] = useState('cinematic');
  const [saved, setSaved] = useState<StyleSelection | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [selectionOutcomeUnknown, setSelectionOutcomeUnknown] = useState(false);
  const [publishOutcomeUnknown, setPublishOutcomeUnknown] = useState(false);
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState<CustomForm>(readForm);
  const [directionForm, setDirectionForm] = useState<DirectionForm>(readDirectionForm);
  const [directionFormDurable, setDirectionFormDurable] = useState(true);
  const [publishingDirection, setPublishingDirection] = useState(false);
  const [directionPublishUnknown, setDirectionPublishUnknown] = useState(false);
  const [formDurable, setFormDurable] = useState(true);
  const [published, setPublished] = useState<ProductionStyle | null>(null);
  const [styleAssets, setStyleAssets] = useState<MediaAsset[]>([]);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [referenceBusy, setReferenceBusy] = useState(false);
  const [pendingVideo, setPendingVideo] = useState<MediaAsset | null>(null);
  const [pendingVideoStyle, setPendingVideoStyle] = useState('');
  const [frameCount, setFrameCount] = useState(2);
  const [frameTimestamps, setFrameTimestamps] = useState<number[]>([]);
  const [frameJob, setFrameJob] = useState<StyleFrameJob | null>(null);
  const [styleSources, setStyleSources] = useState<StyleSource[]>([]);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [sourceBusy, setSourceBusy] = useState(false);
  const [analysisBusy, setAnalysisBusy] = useState(false);

  const selected = useMemo(() => catalog.find(item => item.style_version_id === selectedVersion) || null, [catalog, selectedVersion]);
  const compatibleDirectingStyles = useMemo(() => directingStyles.filter(style =>
    style.scope_type !== 'production_type' || style.production_type_scope === selected?.production_type),
    [directingStyles, selected?.production_type]);
  useEffect(() => {
    if (!selected || !compatibleDirectingStyles.length || compatibleDirectingStyles.some(style => style.style_id === selectedDirectionId)) return;
    setSelectedDirectionId(compatibleDirectingStyles.some(style => style.style_id === 'cinematic') ? 'cinematic' : compatibleDirectingStyles[0].style_id);
  }, [selected, selectedDirectionId, compatibleDirectingStyles]);
  const load = async (context: string) => {
    setLoading(true); setNotice('');
    try {
      const [styles, selections] = await Promise.all([getStyleCatalog(), getStyleSelections(context, selectionWorkspaceId || undefined)]);
      const latest = selections.selections?.at(-1) || null;
      let listed = styles.production_types || [];
      setDirectingStyles(styles.directing_styles || []);
      if (latest && !listed.some(item => item.style_version_id === latest.style_version_id)) {
        const retained: ProductionStyle = {
          production_type: latest.production_type,
          display_name: latest.director_profile?.display_name || latest.production_type,
          style_version: latest.style_version ?? latest.style_version_id,
          style_version_id: latest.style_version_id,
          narrative_guidance: latest.narrative_guidance,
          narrative_hash: latest.narrative_hash,
          director_profile: latest.director_profile,
          director_profile_hash: latest.director_profile_hash,
          custom: latest.custom ?? !latest.style_version_id.startsWith("base:"),
        };
        listed = [...listed, retained];
      }
      setCatalog(listed); setCatalogVersion(styles.catalog_version || '');
      setSaved(latest); setSelectedVersion(latest?.style_version_id || '');
      setSelectedDirectionId(latest?.directing_style?.style_id || 'cinematic');
      setSelectionOutcomeUnknown(false); setPublishOutcomeUnknown(false); setDirectionPublishUnknown(false);
    } catch (error) {
      setNotice(`Could not confirm the latest catalog or saved selection: ${(error as Error).message}. Any version shown is the last successful snapshot; refresh before acting on it.`);
    } finally { setLoading(false); }
  };
  useEffect(() => {
    let context = contextId || initialContext();
    if (!context) {
      try { if (!crypto?.randomUUID) throw new Error('Secure random IDs are unavailable'); context = `setup-${crypto.randomUUID()}`; }
      catch { setStorageWarning('This browser cannot create a safe setup context ID. Style selection cannot be saved safely here.'); setLoading(false); return; }
      try { localStorage.setItem(CONTEXT_KEY, context); setContextId(context); }
      catch { setStorageWarning('This browser cannot persist the setup context. Style selection cannot be saved safely here.'); setLoading(false); return; }
    }
    setContextId(context);
    void load(context);
  // Load once per setup context; a Refresh button is explicit.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!contextId) return;
    let alive = true;
    void Promise.all(['image', 'video', 'audio'].map(kind => listMediaAssets(contextId, kind)))
      .then(pages => { if (alive) setStyleAssets([...new Map(pages.flatMap(page => page.assets).map(asset=>[asset.asset_id,asset])).values()]); })
      .catch(error => { if (alive) setNotice(`Could not load style reference media: ${(error as Error).message}`); });
    return () => { alive = false; };
  }, [contextId]);
  useEffect(() => {
    if (!contextId || !frameJob || !['queued','running','cancel_requested'].includes(frameJob.status)) return;
    let alive = true;
    const timer = window.setTimeout(() => {
      void getStyleFrameJob(contextId, frameJob.job_id).then(async current => {
        if (!alive) return;
        if (current.status === 'completed') {
          const pages = await Promise.all(['image','video','audio'].map(kind=>listMediaAssets(contextId,kind)));
          if (!alive) return;
          setStyleAssets([...new Map(pages.flatMap(page=>page.assets).map(asset=>[asset.asset_id,asset])).values()]);
          setFrameJob(current);
          setPendingVideo(null); setReferenceBusy(false);
          setNotice(`Added ${current.result?.frames?.length || 0} selected frame${current.result?.frames?.length === 1 ? '' : 's'} from the style video.`);
        } else if (['failed','interrupted','cancelled'].includes(current.status)) {
          setFrameJob(current);
          setReferenceBusy(false);
          setNotice(current.status === 'cancelled' ? 'Frame extraction was cancelled. Your video and timestamp selections are still available.' : `Frame extraction ${current.status}: ${current.error || current.message}. Your video and timestamp selections are still available.`);
        } else setFrameJob(current);
      }).catch(error => { if (alive) { setNotice(`Could not check frame extraction progress: ${(error as Error).message}. Retrying automatically.`); setFrameJob(current=>current?{...current}:current); } });
    }, 700);
    return () => { alive = false; window.clearTimeout(timer); };
  }, [contextId, frameJob]);
  useEffect(() => {
    if (!contextId) return;
    let alive = true;
    void listStyleSources(contextId).then(result => { if (alive) setStyleSources(result.sources || []); })
      .catch(error => { if (alive) setNotice(`Could not load style documents: ${(error as Error).message}`); });
    return () => { alive = false; };
  }, [contextId]);
  useEffect(() => { try { localStorage.setItem(FORM_KEY, JSON.stringify(form)); setFormDurable(true); } catch { setFormDurable(false); } }, [form]);
  useEffect(() => { try { localStorage.setItem(DIRECTION_FORM_KEY, JSON.stringify(directionForm)); setDirectionFormDurable(true); } catch { setDirectionFormDurable(false); } }, [directionForm]);

  const refresh = () => contextId ? void load(contextId) : setNotice('Setup context is not saved. This browser cannot safely recover a selection.');
  const save = async () => {
    if (!contextId || !selected || !selectedDirectionId) return;
    setSaving(true); setNotice('');
    try {
      let frozen: StyleSelection;
      try { const chosenDirection = directingStyles.find(style=>style.style_id===selectedDirectionId); frozen = await saveStyleSelection(contextId, selected.production_type, selected.style_version_id, selectedDirectionId, chosenDirection?.style_version_id, selectionWorkspaceId || undefined); }
      catch (error) { setSelectionOutcomeUnknown(true); setNotice(`The save response was not confirmed: ${(error as Error).message}. The server may have saved this version. Refresh the catalog and selection before trying another save.`); return; }
      setSaved(frozen); setSelectedVersion(frozen.style_version_id); setSelectedDirectionId(frozen.directing_style?.style_id || 'cinematic');
      const direction = frozen.directing_style;
      const evidenceIds = (direction?.evidence || []).map(item=>item.asset_id).filter((id):id is string=>typeof id==='string');
      const linked = direction ? await Promise.allSettled(evidenceIds.map(assetId=>linkMediaAssetToStyle(contextId,assetId,direction.style_id))) : [];
      if (evidenceIds.length) {
        try { const pages=await Promise.all(['image','video','audio'].map(kind=>listMediaAssets(contextId,kind))); setStyleAssets([...new Map(pages.flatMap(page=>page.assets).map(asset=>[asset.asset_id,asset])).values()]); }
        catch { /* The saved selection remains authoritative; refresh can reload its references. */ }
      }
      const failedLinks = linked.filter(item=>item.status==='rejected').length;
      setNotice(failedLinks ? `Saved ${selected.display_name} and ${direction?.display_name || 'Cinematic'} direction. ${failedLinks} reference${failedLinks===1?'':'s'} is recorded in the style version but could not be added to recommendations.` : `Saved ${selected.display_name} with ${direction?.display_name || 'Cinematic'} direction. ${selectionWorkspaceId ? 'New screenplay drafts will use this selection; earlier derived work is stale.' : 'Both choices are frozen in this setup context.'}`);
    } finally { setSaving(false); }
  };
  const publishDirection = async (event:FormEvent) => {
    event.preventDefault();
    const {style_id,display_name,guidance}=directionForm;
    if(directionPublishUnknown){setNotice('A previous style publish has an unknown outcome. Refresh the catalog before trying again.');return;}
    if(!directionFormDurable){setNotice('The directing-style draft is not saved in this browser. Copy it somewhere safe before publishing.');return;}
    if(!style_id.trim()||!display_name.trim()||!guidance.trim()){setNotice('Enter a style ID, a display name and the directing guidance.');return;}
    if(directionForm.scope_type==='production_type'&&!selected){setNotice('Choose a production type above before publishing a type-specific directing style.');return;}
    const evidence: DirectingStyleEvidence[] = Object.entries(directionForm.evidence).flatMap(([assetId,intent])=>{
      const asset=styleAssets.find(item=>item.asset_id===assetId && item.roles.includes('style_reference'));
      const analyzed=directionForm.media_analysis_evidence.find(item=>item.asset_id===assetId);
      return asset && intent.trim() ? [{...(analyzed||{}),asset_id:asset.asset_id,kind:asset.kind,sha256:asset.sha256,intent:intent.trim()}] : [];
    });
    if(Object.keys(directionForm.evidence).length!==evidence.length){setNotice('Each selected reference needs a short note describing what it should teach this style.');return;}
    evidence.push(...directionForm.document_evidence);
    setPublishingDirection(true);setNotice('');
    try{const record=await publishDirectingStyle(contextId,style_id.trim(),display_name.trim(),guidance.trim(),evidence,directionForm.scope_type,directionForm.scope_type==='production_type'?selected?.production_type:undefined);setDirectingStyles(current=>[...current.filter(item=>item.style_id!==record.style_id),record]);setSelectedDirectionId(record.style_id);setDirectionForm(emptyDirectionForm());setNotice(`${record.display_name} was published as directing-style version ${record.version}${record.scope_type==='production_type'?` for ${selected?.display_name}`:' for reuse across production types'}. Select and save it to use it for a production.`);}
    catch(error){setDirectionPublishUnknown(true);setNotice(`The style publish response was not confirmed: ${(error as Error).message}. Refresh the catalog before another publish; your draft is preserved.`);}
    finally{setPublishingDirection(false);}
  };
  const update = (key: keyof CustomForm, value: string) => setForm(previous => ({ ...previous, [key]: value }));
  const updateStage = (key: string, value: string) => setForm(previous => ({ ...previous, stages: { ...previous.stages, [key]: value } }));
  const publish = async (event: FormEvent) => {
    event.preventDefault();
    const productionType = form.production_type.trim();
    const narrative = Object.fromEntries(guidanceStages.map(([key]) => [key, form.stages[key].trim()]));
    const profile: DirectorProfile = { display_name: form.display_name.trim(), purpose: form.purpose.trim(), behavior: lines(form.behavior), review_priorities: lines(form.review_priorities) };
    if (publishOutcomeUnknown) { setNotice('A previous publish has an unknown outcome. Refresh the catalog before publishing again.'); return; }
    if (!formDurable) { setNotice('Custom type draft is not saved in this browser. Copy it to a safe place before publishing.'); return; }
    if (!productionType || !profile.display_name || !profile.purpose || Object.values(narrative).some(value => !value) || !profile.behavior.length || !profile.review_priorities.length) { setNotice('Complete the type ID, display name, purpose, all six guidance stages, and at least one behavior and review priority.'); return; }
    setPublishing(true); setNotice('');
    try {
      const record = await publishProductionType(productionType, narrative, profile);
      setPublished(record); setCatalog(current => [...current.filter(item => item.style_version_id !== record.style_version_id), record]);
      setNotice(`${record.display_name} was published as version ${record.style_version}. It was not selected automatically.`);
    } catch (error) { setPublishOutcomeUnknown(true); setNotice(`The publish response was not confirmed: ${(error as Error).message}. The server may have published this version. Refresh the catalog before publishing again; your editable form is preserved.`); }
    finally { setPublishing(false); }
  };
  const uploadStyleReference = async () => {
    if (!contextId || !selectedDirectionId || !referenceFile || referenceBusy) return;
    setReferenceBusy(true); setNotice('');
    try {
      const asset = await uploadMediaAsset(contextId, referenceFile, 'style_reference');
      const canAssociate = saved?.directing_style?.style_id === selectedDirectionId;
      if (canAssociate) await linkMediaAssetToStyle(contextId, asset.asset_id, selectedDirectionId);
      const pages = await Promise.all(['image', 'video', 'audio'].map(kind => listMediaAssets(contextId, kind)));
      setStyleAssets([...new Map(pages.flatMap(page => page.assets).map(asset=>[asset.asset_id,asset])).values()]); setReferenceFile(null);
      if (asset.kind === 'video') {
        const duration = asset.media?.duration_seconds || 0;
        setPendingVideo(asset); setPendingVideoStyle(selectedDirectionId); setFrameCount(2);
        setFrameTimestamps(duration > 0 ? [duration / 4, duration * 3 / 4].map(value => Number(value.toFixed(3))) : []);
        setNotice(`Added ${asset.filename}${canAssociate ? ` to ${selectedDirectionId} references` : ' to the setup library'}. Choose up to 12 timestamps for image references, or keep 0 to use only the video.`);
      } else setNotice(canAssociate ? `Added ${asset.filename} to ${selectedDirectionId} style references.` : `Added ${asset.filename} to the setup library. Select it as evidence in the directing-style draft; saving a style links it for recommendations.`);
    } catch (error) { setNotice(`Could not add style reference: ${(error as Error).message}. Any completed upload remains in this setup library.`); }
    finally { setReferenceBusy(false); }
  };
  const extractStyleFrames = async () => {
    if (!contextId || !pendingVideo || !selectedDirectionId || pendingVideoStyle !== selectedDirectionId || frameCount < 1 || frameTimestamps.length !== frameCount) return;
    setReferenceBusy(true); setNotice('');
    try {
      const job = await extractMediaStyleFrames(contextId, pendingVideo.asset_id, pendingVideoStyle, frameTimestamps);
      setFrameJob(job); setNotice('Style-frame extraction is running. You can cancel it while it is processing.');
    } catch (error) { setReferenceBusy(false); setNotice(`Could not start style-frame extraction: ${(error as Error).message}. The original video remains available.`); }
  };
  const cancelFrameExtraction = async () => {
    if (!contextId || !frameJob || !['queued','running'].includes(frameJob.status)) return;
    try { setFrameJob(await cancelStyleFrameJob(contextId, frameJob.job_id)); }
    catch (error) { setNotice(`Could not cancel frame extraction: ${(error as Error).message}`); }
  };
  const changeFrameCount = (count: number) => {
    const bounded = Math.max(0, Math.min(12, Number.isFinite(count) ? Math.trunc(count) : 0));
    setFrameCount(bounded);
    const duration = pendingVideo?.media?.duration_seconds || 0;
    setFrameTimestamps(Array.from({length: bounded}, (_, index) => frameTimestamps[index] ?? (duration * (index + 1) / (bounded + 1))).map(value => Number(value.toFixed(3))));
  };
  const addStyleDocument = async () => {
    if (!contextId || !sourceFile || sourceBusy) return;
    setSourceBusy(true); setNotice('');
    try {
      const source = await uploadStyleSource(contextId, sourceFile);
      setStyleSources(items => [source, ...items.filter(item => item.source_id !== source.source_id)]);
      setSourceFile(null);
      setNotice(`Extracted ${source.text_character_count.toLocaleString()} characters from ${source.filename}. Review the cited text below before using it to draft style rules.`);
    } catch (error) { setNotice(`Could not extract style document: ${(error as Error).message}`); }
    finally { setSourceBusy(false); }
  };
  const loadStyleSourceEvidence = async (sourceId: string) => {
    if (styleSources.find(item => item.source_id === sourceId)?.evidence_blocks) return;
    try { const source = await getStyleSource(contextId, sourceId); setStyleSources(items => items.map(item => item.source_id === sourceId ? source : item)); }
    catch (error) { setNotice(`Could not read extracted evidence: ${(error as Error).message}`); }
  };
  const proposeStyleRules = async () => {
    if (!contextId || !directionForm.source_ids.length || analysisBusy) return;
    setAnalysisBusy(true); setNotice('');
    try {
      const proposal = await analyzeStyleSources(contextId, directionForm.source_ids, directionForm.source_intent);
      setDirectionForm(value=>({...value,display_name:value.display_name || proposal.display_name,guidance:proposal.guidance,document_evidence:proposal.evidence}));
      setNotice(`Drafted ${proposal.evidence.length} cited rule${proposal.evidence.length===1?'':'s'}. Review the guidance and source quotes before publishing; nothing has been published yet.`);
    } catch (error) { setNotice(`Could not draft style rules: ${(error as Error).message}. Your current draft is unchanged.`); }
    finally { setAnalysisBusy(false); }
  };
  const proposeImageStyleRules = async () => {
    if (!contextId || !directionForm.image_source_ids.length || analysisBusy) return;
    setAnalysisBusy(true); setNotice('');
    try {
      const proposal = await analyzeStyleImages(contextId, directionForm.image_source_ids, directionForm.image_intent);
      const suggested = Object.fromEntries(proposal.evidence.map(item=>[item.asset_id,item.intent]));
      setDirectionForm(value=>({...value,display_name:value.display_name || proposal.display_name,guidance:proposal.guidance,evidence:{...value.evidence,...suggested},media_analysis_evidence:proposal.evidence}));
      setNotice(`Drafted style guidance from ${proposal.evidence.length} media reference${proposal.evidence.length===1?'':'s'}. Edit the rules and each media note before publishing; nothing has been published yet.`);
    } catch (error) { setNotice(`Could not draft visual style rules: ${(error as Error).message}. Your current draft is unchanged.`); }
    finally { setAnalysisBusy(false); }
  };
  const selectedStyleAssets = styleAssets.filter(asset => asset.metadata?.directing_style_ids?.includes(selectedDirectionId));
  const eligibleStyleEvidence = styleAssets.filter(asset => asset.roles.includes('style_reference'));
  const analyzableStyleEvidence = eligibleStyleEvidence.filter(asset => asset.kind === 'image' ||
    ((asset.kind === 'audio' || asset.kind === 'video') && Boolean(asset.metadata?.analyzer_run_id) && Boolean(asset.description?.trim() || asset.tags?.length)));

  return <div className="content-wrap styles-content">
    {selectionWorkspaceId && <p className="graph-disclosure" role="status">Editing the pinned style for story {selectionWorkspaceId}. Changing it marks existing screenplay work stale; already submitted jobs keep their frozen inputs. <a href="#/story">Return to Story</a></p>}
    <div className="page-heading styles-heading"><div><div className="eyebrow">STORY WORKFLOW · SETUP</div><h1>Production Type &amp; Style</h1><p>Choose how you want to tell your story.</p></div><button className="quiet-button styles-refresh" type="button" onClick={refresh} disabled={loading}><RefreshCw size={15}/> Refresh catalog</button></div>
    {storageWarning && <div className="notice notice-warn" role="alert">{storageWarning}</div>}
    {notice && <div className="notice styles-notice" role="status">{notice}</div>}
    <section className="card style-context-card"><div><span className="styles-kicker"><Palette size={15}/> PRODUCTION SETUP</span><small>Choose what you are making and how it should feel.</small><details><summary>Setup details</summary><code>{contextId || 'not persisted'}</code></details></div>{saved && <div className="pinned-style"><Check size={15}/><span>Saved setup<strong>{saved.production_type} · {saved.directing_style?.display_name || 'Legacy direction'}</strong></span></div>}</section>

    <section className="styles-section" aria-labelledby="catalog-title"><div className="styles-section-heading"><div><span className="styles-kicker">VERSIONED CATALOG {catalogVersion && `· ${catalogVersion}`}</span><h2 id="catalog-title">Choose the kind of production</h2><p>This defines the deliverable. Choose its creative direction separately below.</p></div></div>
      {loading ? <div className="card styles-loading"><LoaderCircle className="spin" size={18}/> Loading catalog and saved selection…</div> : catalog.length === 0 ? <div className="card styles-empty">Types could not load. Refresh to try again.</div> : <>
        <label className="style-select-label" htmlFor="production-type-select">Production type and version</label>
        <select id="production-type-select" className="style-type-select" value={selectedVersion} onChange={event => setSelectedVersion(event.target.value)} aria-describedby="selection-status"><option value="">Choose a type…</option>{catalog.map(item => <option key={item.style_version_id} value={item.style_version_id}>{item.display_name} · v{item.style_version}{item.custom ? ' · custom' : ''}</option>)}</select>
        <p className="style-selection-note" id="selection-status">{selected && selected.style_version_id !== saved?.style_version_id ? `Selected type: ${selected.display_name} · v${selected.style_version}.` : saved ? `Saved type: ${saved.production_type} · ${saved.style_version_id}.` : 'Choose a production type to continue.'}</p>
        <div className="style-catalog-grid">{catalog.map(item => <article key={item.style_version_id} className={`card style-type-card ${selectedVersion===item.style_version_id?'style-type-card-selected':''}`}>
          <div className="style-card-top"><div><span className="styles-kicker">{item.custom?'CUSTOM TYPE':'PRODUCTION TYPE'}</span><h3>{item.display_name}</h3></div><span className="style-version">v{item.style_version}</span></div>
          <p className="style-purpose">{item.director_profile?.purpose || 'Purpose guidance is not present in this catalog version.'}</p>
          <details className="style-guidance"><summary>Direction details</summary><dl>{guidanceStages.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{valueText(item.narrative_guidance?.[key]) || 'No guidance supplied.'}</dd></div>)}</dl><div className="style-profile-block"><h4>Director behavior</h4><ul>{(item.director_profile?.behavior || []).map((entry,index)=><li key={index}>{entry}</li>)}</ul><h4>Review priorities</h4><ul>{(item.director_profile?.review_priorities || []).map((entry,index)=><li key={index}>{entry}</li>)}</ul></div><small className="style-hashes">Style {item.narrative_hash} · Director {item.director_profile_hash}</small></details>
          <button className="quiet-button style-card-select" type="button" onClick={()=>setSelectedVersion(item.style_version_id)} aria-pressed={selectedVersion===item.style_version_id}>{selectedVersion===item.style_version_id?'Selected draft':'Select this version'}</button>
        </article>)}</div>
        {selectionOutcomeUnknown && <p className="styles-outcome-lock" role="alert">Save outcome is unknown. Refresh to confirm before another selection can be saved.</p>}
        <div className="style-save-row"><button className="generate-button" type="button" onClick={save} disabled={!selected || !selectedDirectionId || saving || loading || !contextId || Boolean(storageWarning) || selectionOutcomeUnknown}><Save size={15}/>{saving?'Saving selection…':'Save selection'}</button><span>{saved ? `Saved: ${saved.production_type}` : ''}</span></div>
      </>}
    </section>

    <section className="styles-section" aria-labelledby="direction-title"><div className="styles-section-heading"><div><span className="styles-kicker">DIRECTING STYLE</span><h2 id="direction-title">Choose the creative treatment</h2><p>This guides tone and presentation without changing story events.</p></div></div>
      <label className="style-select-label" htmlFor="directing-style-select">Directing style</label>
      <select id="directing-style-select" className="style-type-select" value={selectedDirectionId} onChange={event=>setSelectedDirectionId(event.target.value)} disabled={!selected}><option value="">{selected?'Choose a directing style…':'Choose a production type above first'}</option>{compatibleDirectingStyles.map(style=><option key={style.style_id} value={style.style_id}>{style.display_name} · v{style.version}</option>)}</select>
      {compatibleDirectingStyles.filter(style=>style.style_id===selectedDirectionId).map(style=><p className="style-selection-note" key={style.style_id}>{style.guidance}</p>)}
      {selected && <small>Showing styles available for {selected.display_name}; cross-type styles remain available for every production type.</small>}
      <small>Saved selections pin this version. Document proposals keep exact quotes; media references remain selectable assets.</small>
      <section className="card style-source-panel" aria-label="Style documents">
        <h3>Document references</h3><p>Upload a PDF, Markdown or text guide. Vibe Director extracts reviewable text with page or line citations; scanned PDFs need readable text or OCR.</p>
        <label>Style document<input aria-label="Style document file" type="file" accept=".pdf,.md,.txt,application/pdf,text/markdown,text/plain" onChange={event=>setSourceFile(event.target.files?.[0] || null)}/></label>
        <button className="quiet-button" type="button" disabled={!sourceFile || !contextId || sourceBusy} onClick={()=>void addStyleDocument()}>{sourceBusy?'Extracting…':'Add document'}</button>
        <SelectionToggle selected={directionForm.source_ids} shown={styleSources.map(row=>row.source_id)} onChange={ids=>setDirectionForm(value=>({...value,source_ids:ids}))} disabled={publishing}/>{styleSources.length > 0 && <div className="style-source-list">{styleSources.map(source=><details className="style-source-item" key={source.source_id} onToggle={event=>{if((event.currentTarget as HTMLDetailsElement).open) void loadStyleSourceEvidence(source.source_id);}}><summary><label><input type="checkbox" aria-label={`Use ${source.filename} for style proposal`} checked={directionForm.source_ids.includes(source.source_id)} onClick={event=>event.stopPropagation()} onChange={event=>setDirectionForm(value=>({...value,source_ids:event.target.checked?[...new Set([...value.source_ids,source.source_id])]:value.source_ids.filter(id=>id!==source.source_id)}))}/> {source.filename} · {source.text_character_count.toLocaleString()} characters · {source.source_type}</label></summary>{source.evidence_blocks?.length ? source.evidence_blocks.map(block=><article key={`${block.locator}-${block.text}`}><small>{block.locator}</small><p>{block.text}</p></article>) : <p>Loading extracted evidence…</p>}</details>)}</div>}
        <label>What should the model learn from these documents?<textarea rows={2} maxLength={3000} value={directionForm.source_intent} onChange={event=>setDirectionForm(value=>({...value,source_intent:event.target.value}))} placeholder="For example: use the lighting and camera language, without copying plot or dialogue."/></label>
        <button className="quiet-button" type="button" disabled={!directionForm.source_ids.length||analysisBusy} onClick={()=>void proposeStyleRules()}>{analysisBusy?'Drafting rules…':'Draft rules with Codex'}</button>
        <h3>Reference media</h3><p>Codex inspects selected images and uses exact, source-linked analyzer notes for audio and video. It does not hear or watch those original files here.</p>
        <SelectionToggle selected={directionForm.image_source_ids} shown={analyzableStyleEvidence.map(row=>row.asset_id)} onChange={ids=>setDirectionForm(value=>({...value,image_source_ids:ids}))} disabled={publishing}/>{analyzableStyleEvidence.length ? <div className="style-source-list">{analyzableStyleEvidence.map(asset=><label className="style-evidence-row" key={asset.asset_id}><input type="checkbox" aria-label={`Analyze ${asset.filename} as style`} checked={directionForm.image_source_ids.includes(asset.asset_id)} onChange={event=>setDirectionForm(value=>({...value,image_source_ids:event.target.checked?[...new Set([...value.image_source_ids,asset.asset_id])]:value.image_source_ids.filter(id=>id!==asset.asset_id)}))}/>{asset.filename} <small>{asset.kind}{asset.kind!=='image'?' · analyzed notes':''}</small></label>)}</div> : <small>Add an image, or analyzed audio/video style reference, below to enable a proposal.</small>}
        <label>What should Codex learn from these references?<textarea rows={2} maxLength={3000} value={directionForm.image_intent} onChange={event=>setDirectionForm(value=>({...value,image_intent:event.target.value}))} placeholder="For example: use the framing and cool, low-key lighting; keep the audio mood restrained."/></label>
        <button className="quiet-button" type="button" disabled={!directionForm.image_source_ids.length||directionForm.image_source_ids.length>5||analysisBusy} onClick={()=>void proposeImageStyleRules()}>{analysisBusy?'Drafting…':'Draft style rules with Codex'}</button>
      </section>
      <form className="card custom-type-form" onSubmit={publishDirection} aria-label="Create directing style">
        <h3>Create a directing style</h3><p className="style-selection-note">Review or edit the rules, then publish a version. Document quotes are checked against the uploaded source before they can be saved.</p>
        {!directionFormDurable&&<div className="notice notice-warn" role="alert">Browser storage is unavailable. Copy this draft before leaving.</div>}
        <div className="style-form-grid"><label>Style ID<input value={directionForm.style_id} onChange={event=>setDirectionForm(value=>({...value,style_id:event.target.value}))} placeholder="e.g. neo_noir" autoComplete="off"/></label><label>Display name<input value={directionForm.display_name} onChange={event=>setDirectionForm(value=>({...value,display_name:event.target.value}))} placeholder="e.g. Neo-noir"/></label></div>
        <label>Style scope<select aria-label="Directing style scope" value={directionForm.scope_type} onChange={event=>setDirectionForm(value=>({...value,scope_type:event.target.value==='production_type'?'production_type':'cross_type'}))}><option value="cross_type">Reusable across production types</option><option value="production_type" disabled={!selected}>Only {selected?.display_name || 'the selected production type'}</option></select></label>
        <small>{directionForm.scope_type==='production_type'?(selected?`This version will be available only with ${selected.display_name}.`:'Choose a production type above to publish a type-specific style.'):'This version will be available with any production type.'}</small>
        <label>Directing guidance<textarea rows={5} maxLength={12000} value={directionForm.guidance} onChange={event=>setDirectionForm(value=>({...value,guidance:event.target.value}))} placeholder="Describe camera, lighting, mood, pacing and sound choices. Preserve the story's events."/></label>
        {directionForm.document_evidence.length>0&&<fieldset className="style-evidence-picker"><legend>Cited document evidence</legend><p>These exact quotes support the draft rules. Remove citations you do not want attached to the published version.</p>{directionForm.document_evidence.map((item,index)=><article className="style-evidence-row" key={`${item.source_id}-${item.locator}-${index}`}><div><strong>{item.filename}</strong><small>{item.locator} · {item.intent}</small><blockquote>{item.quote}</blockquote></div><button type="button" className="quiet-button" onClick={()=>setDirectionForm(value=>({...value,document_evidence:value.document_evidence.filter((_entry,row)=>row!==index)}))}>Remove citation</button></article>)}</fieldset>}
        <fieldset className="style-evidence-picker"><legend>Reference media for this style (optional)</legend><p>Select only media that informed these rules, then say what to take from each item. Publishing saves these links in this immutable style version.</p><SelectionToggle selected={Object.keys(directionForm.evidence)} shown={eligibleStyleEvidence.map(row=>row.asset_id)} onChange={ids=>setDirectionForm(value=>({...value,evidence:Object.fromEntries(ids.map(id=>[id,value.evidence[id]||'']))}))} disabled={publishing}/>{eligibleStyleEvidence.length ? eligibleStyleEvidence.map(asset=><div className="style-evidence-row" key={asset.asset_id}><label className="style-evidence-select"><input type="checkbox" checked={Object.hasOwn(directionForm.evidence,asset.asset_id)} onChange={event=>setDirectionForm(value=>{const evidence={...value.evidence};if(event.target.checked)evidence[asset.asset_id]=evidence[asset.asset_id]||'';else delete evidence[asset.asset_id];return {...value,evidence};})}/><span>{asset.filename} <small>{asset.kind}</small></span></label>{Object.hasOwn(directionForm.evidence,asset.asset_id)&&<input aria-label={`What to use from ${asset.filename}`} value={directionForm.evidence[asset.asset_id]} maxLength={1000} onChange={event=>setDirectionForm(value=>({...value,evidence:{...value.evidence,[asset.asset_id]:event.target.value}}))} placeholder="What should the model learn from this reference?"/>}</div>) : <small>Add an image, audio or video reference below first. Video frames stay separate from the original clip.</small>}</fieldset>
        {directionPublishUnknown&&<p className="styles-outcome-lock" role="alert">Publish outcome is unknown. Refresh the catalog before retrying.</p>}
        <div className="style-publish-row"><button className="generate-button" type="submit" disabled={publishingDirection||!directionFormDurable||directionPublishUnknown}><Sparkles size={15}/>{publishingDirection?'Publishing…':'Publish directing style'}</button></div>
      </form>
    </section>

    <section className="styles-section custom-type-section" aria-labelledby="custom-title"><div className="styles-section-heading"><div><span className="styles-kicker"><Sparkles size={14}/> CUSTOM TYPE</span><h2 id="custom-title">Create a production type</h2><p>Define the deliverable and its stage guidance, publish it, then select it above.</p></div></div>
      {!formDurable && <div className="notice notice-warn" role="alert">Browser storage is unavailable. Your edits remain visible in this tab but are not durable; copy them before leaving.</div>}
      <form className="card custom-type-form" onSubmit={publish} aria-label="Create production type">
        <div className="style-form-grid"><label>Type ID<input value={form.production_type} onChange={event=>update('production_type',event.target.value)} placeholder="e.g. documentary_series" autoComplete="off"/></label><label>Display name<input value={form.display_name} onChange={event=>update('display_name',event.target.value)} placeholder="e.g. Documentary series"/></label></div>
        <label>Director purpose<textarea rows={3} value={form.purpose} onChange={event=>update('purpose',event.target.value)} placeholder="What should this type help the Director produce?"/></label>
        <div className="style-guidance-form"><h3>Stage guidance</h3><div className="style-form-grid">{guidanceStages.map(([key,label])=><label key={key}>{label}<textarea rows={4} value={form.stages[key]} onChange={event=>updateStage(key,event.target.value)} placeholder={`Guidance for ${label.toLowerCase()}…`}/></label>)}</div></div>
        <div className="style-form-grid"><label>Director behavior <small>One behavior per line</small><textarea rows={5} value={form.behavior} onChange={event=>update('behavior',event.target.value)} placeholder={'Preserve the requested point of view\nFavor clear transitions'}/></label><label>Review priorities <small>One priority per line</small><textarea rows={5} value={form.review_priorities} onChange={event=>update('review_priorities',event.target.value)} placeholder={'Check tonal consistency\nReview scene clarity'}/></label></div>
        {publishOutcomeUnknown && <p className="styles-outcome-lock" role="alert">Could not confirm publication. Refresh before trying again.</p>}
        <div className="style-publish-row"><button className="generate-button" type="submit" disabled={publishing || !formDurable || publishOutcomeUnknown}><Sparkles size={15}/>{publishing?'Publishing…':'Publish custom type'}</button><span>{published ? `Last published: ${published.display_name} · v${published.style_version}` : ''}</span></div>
      </form>
    </section>
    <section className="styles-section style-media-section" aria-labelledby="style-media-title"><div className="styles-section-heading"><div><span className="styles-kicker">DIRECTING-STYLE REFERENCES</span><h2 id="style-media-title">Add reference media</h2><p>Images and selected video frames use vision. Audio and video proposals use source-linked analyzer notes; Codex does not inspect the original audio or video here.</p></div></div>
      <section className="card style-media-upload"><label>Directing style<select aria-label="Directing style for reference media" value={selectedDirectionId} onChange={event=>setSelectedDirectionId(event.target.value)}><option value="">Choose a directing style…</option>{directingStyles.map(style=><option key={style.style_id} value={style.style_id}>{style.display_name} · v{style.version}</option>)}</select></label><label>Reference file<input aria-label="Directing style reference file" type="file" accept="image/png,image/jpeg,image/webp,video/mp4,video/quicktime,video/x-matroska,video/webm,audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/flac,audio/aac" onChange={event=>setReferenceFile(event.target.files?.[0] || null)}/></label><button className="generate-button" type="button" disabled={!contextId || !selectedDirectionId || !referenceFile || referenceBusy} onClick={()=>void uploadStyleReference()}>{referenceBusy?'Adding…':'Add reference'}</button>{(!saved || saved.directing_style?.style_id !== selectedDirectionId) && <small>Upload now, then select it as evidence in a style draft. It becomes a recommendation after that style is saved.</small>}</section>
      <MediaSourcePicker workspaceId={contextId} kinds={['image','video','audio']} role="style_reference" disabled={referenceBusy||!contextId} onAdded={items=>{setStyleAssets(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items]);const video=items.find(item=>item.kind==='video');if(video){setPendingVideo(video);setPendingVideoStyle(selectedDirectionId);setFrameCount(2);const duration=video.media?.duration_seconds||0;setFrameTimestamps(duration?[duration/4,duration*3/4]:[]);}setNotice('References added. Select them as style evidence; extract video frames only if needed.');}}/>
      {pendingVideo && <section className="card style-frame-picker" aria-label="Style video frame selection"><div><strong>Image references from {pendingVideo.filename}</strong><span>{pendingVideo.media?.duration_seconds ? `${pendingVideo.media.duration_seconds.toFixed(1)} seconds` : 'Video duration unavailable'}</span></div><label>Frames to extract<input aria-label="Style frame count" type="number" min="0" max="12" step="1" value={frameCount} disabled={referenceBusy} onChange={event=>changeFrameCount(Number(event.target.value))}/></label>{frameCount > 0 && frameTimestamps.map((timestamp,index)=><label key={index}>Frame {index+1} timestamp (seconds)<input aria-label={`Frame ${index+1} timestamp (seconds)`} type="number" min="0" max={Math.max(0,(pendingVideo.media?.duration_seconds || 0)-0.001)} step="0.001" value={timestamp} disabled={referenceBusy} onChange={event=>setFrameTimestamps(values=>values.map((value,row)=>row===index?Number(event.target.value):value))}/></label>)}<p>Extract up to 12 selected stills, scaled to at most 1920px wide. Extraction runs in the background and can be cancelled. The original video remains unchanged.</p>{frameJob && ['queued','running','cancel_requested'].includes(frameJob.status) ? <div className="style-frame-job" role="status"><span>{frameJob.message}</span><progress aria-label="Style frame extraction progress" max="100" value={frameJob.progress}/>{frameJob.status==='cancel_requested' ? <span>Cancellation requested…</span> : <button type="button" className="quiet-button" onClick={()=>void cancelFrameExtraction()}>Cancel extraction</button>}</div> : frameCount > 0 ? <button className="generate-button" type="button" disabled={referenceBusy || pendingVideoStyle!==selectedDirectionId || frameTimestamps.length!==frameCount || frameTimestamps.some(value=>!Number.isFinite(value)||value<0||value>=(pendingVideo.media?.duration_seconds||0))} onClick={()=>void extractStyleFrames()}>{referenceBusy?'Extracting…':'Extract selected frames'}</button> : <span>0 frames selected; the video remains available as a video reference.</span>}{pendingVideoStyle!==selectedDirectionId && <small>Select the directing style this video was saved under to extract frames.</small>}</section>}
      {selectedStyleAssets.length > 0 && <div className="style-reference-list">{selectedStyleAssets.map(asset=><article className="card style-reference-item" key={asset.asset_id}><strong>{asset.filename}</strong><span>{asset.kind} · {asset.roles.join(' · ')}</span>{asset.kind==='image'?<img src={asset.content_url} alt={asset.filename}/>:asset.kind==='video'?<video src={asset.content_url} controls preload="metadata"/>:<audio src={asset.content_url} controls preload="metadata"/>}</article>)}</div>}
      <div className="style-save-row"><a className="generate-button" href="#/story">Continue to Story <ArrowRight size={15}/></a></div>
    </section>
  </div>;
}
