import {useProjectState} from './lib/project-state';
import OutputDestination from './OutputDestination';
import {managedProjectId} from './lib/media-workspace';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, FolderOpen, Image as ImageIcon, LoaderCircle, RefreshCw, Sparkles, X } from 'lucide-react';
import DirectorImageReview from './DirectorImage';
import ZImageLoraControls,{ZImageLora} from './ZImageLoraControls';
import LocalImageFolderBrowser from './LocalImageFolderBrowser';
import MediaSourcePicker from './MediaSourcePicker';
import { createImageBatch, deleteTemporaryImageAsset, getImageBatch, getImageWorker, getImageWorkflows, ImageBatch, ImagePromptDraft, ImageWorkflow, prepareImagePrompt, stageTemporaryImageReference, validateImageRequest } from './lib/image-api';
import { getRuntimeGuard } from './lib/status-api';
import { listMediaAssets, MediaAsset } from './lib/media-api';
import './text-to-image.css';

const MODELS = [
  { id: 'flux_kontext_dev', label: 'FLUX Kontext · reference edit' },
  { id: 'z_image_turbo', label: 'Z Image' },
  { id: 'qwen_image_2512', label: 'Qwen Image 2512' },
  { id: 'qwen_image_edit_2511', label: 'Qwen Image Edit 2511' },
] as const;
const ACTIVE_KEY = 'vibe-text-to-image-active-v1';
const WORKSPACE_KEY = 'vibe-text-to-image-temporary-workspace-v1';
const REFERENCES_KEY = 'vibe-text-to-image-temporary-references-v1';
type Active = { workspaceId: string; batchId: string; outputToken: string; staged?: Array<{assetId:string;token:string}> };
type Ref = { asset: MediaAsset; token?: string };
const temporaryReferences = (refs:Ref[]) => refs.flatMap(({asset,token})=>token?[{assetId:asset.asset_id,token}]:[]);
type DirectoryHandle = FileSystemDirectoryHandle & { values(): AsyncIterable<FileSystemHandle> };
const randomToken = () => crypto.randomUUID().replaceAll('-', '');
function temporaryWorkspaceId() {
  if(managedProjectId()) {
    try { const pending=JSON.parse(localStorage.getItem(ACTIVE_KEY)||'null') as Active|null; if(pending?.outputToken)return pending.workspaceId; } catch { /* Preserve legacy recovery below. */ }
    return managedProjectId()!;
  }
  try {
    const active = JSON.parse(localStorage.getItem(ACTIVE_KEY) || 'null') as Active | null;
    if (active?.workspaceId) return active.workspaceId;
    const saved = localStorage.getItem(WORKSPACE_KEY);
    if (saved && /^t2i-[a-f0-9-]{36}$/i.test(saved)) return saved;
    const next = `t2i-${crypto.randomUUID()}`;
    localStorage.setItem(WORKSPACE_KEY, next);
    return next;
  } catch { return `t2i-${crypto.randomUUID()}`; }
}
const digest = async (bytes: ArrayBuffer) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), value => value.toString(16).padStart(2, '0')).join('');

export default function TextToImagePage() {
  const restoreSettings=useRef(localStorage.getItem(`vibe-project-settings:${managedProjectId()||'tool-library'}:TextToImagePage:width`)!==null);
  const [workspaceId, setWorkspaceId] = useState(temporaryWorkspaceId);
  const referenceKey = `${REFERENCES_KEY}:${workspaceId}`;
  const [workflows, setWorkflows] = useState<ImageWorkflow[]>([]);
  const [workflowId, setWorkflowId] = useProjectState<string>('TextToImagePage:workflowId',MODELS[0].id);
  const [active, setActive] = useState<Active | null>(() => { try { return JSON.parse(localStorage.getItem(ACTIVE_KEY) || 'null'); } catch { return null; } });
  const [batch, setBatch] = useState<ImageBatch | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<MediaAsset | null>(null);
  const [references, setReferences] = useState<Ref[]>([]);
  const [chatAttachments, setChatAttachments] = useState<File[]>([]);
  const [lora,setLora]=useState<ZImageLora|null>(null);
  const [prompt, setPrompt] = useProjectState('TextToImagePage:prompt','');
  const [promptDraft, setPromptDraft] = useState<ImagePromptDraft | null>(null);
  const [previousChatDraft] = useProjectState('TextToImagePage:chat','');
  const [width, setWidth] = useProjectState('TextToImagePage:width',1280);
  const [height, setHeight] = useProjectState('TextToImagePage:height',720);
  const [steps, setSteps] = useProjectState('TextToImagePage:steps',8);
  const [cfg, setCfg] = useProjectState('TextToImagePage:cfg',1);
  const [seed, setSeed] = useProjectState('TextToImagePage:seed',1);
  const [destinationReady,setDestinationReady]=useState(false);
  const [outputHandle, setOutputHandle] = useState<DirectoryHandle | null>(null);
  const [outputName, setOutputName] = useState('');
  const [previewUrl, setPreviewUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const selectedWorkflow = workflows.find(item => item.workflow_id === workflowId);
  const editing = ['qwen_image_edit_2511', 'flux_kontext_dev'].includes(workflowId);
  const referenceLimit = workflowId === 'flux_kontext_dev' ? 1 : 3;
  const currentJob = batch?.jobs?.[0] || null;
  const readyAsset = selectedAsset || null;
  const chatPreviewUrls = useMemo(() => chatAttachments.map(file => URL.createObjectURL(file)), [chatAttachments]);
  useEffect(() => () => chatPreviewUrls.forEach(url => URL.revokeObjectURL(url)), [chatPreviewUrls]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    void getImageWorkflows(false).then(catalog => {
      if (!alive) return;
      setWorkflows(catalog.workflows.filter(item => MODELS.some(model => model.id === item.workflow_id)));
    }).catch(reason => { if (alive) setError((reason as Error).message); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    let alive = true;
    void listMediaAssets(workspaceId, 'image').then(result => {
      let staged: Array<{assetId:string;token?:string}> = [];
      try { staged = JSON.parse(localStorage.getItem(referenceKey) || localStorage.getItem(REFERENCES_KEY) || '[]'); } catch { /* No staged references to restore. */ }
      if (alive) setReferences(staged.flatMap(ref => {
        const asset = result.assets.find(item => item.asset_id === ref.assetId);
        return asset ? [{ asset, token: ref.token }] : [];
      }));
    }).catch(() => {});
    return () => { alive = false; };
  }, [workspaceId]);
  useEffect(() => {
    if (!selectedWorkflow) return;
    if(restoreSettings.current){restoreSettings.current=false;return;}
    setWidth(selectedWorkflow.defaults.width); setHeight(selectedWorkflow.defaults.height);
    setSteps(selectedWorkflow.defaults.steps); setCfg(selectedWorkflow.defaults.cfg);
    if (!editing && references.length) setMessage('This workflow is text-only. Select Qwen Image Edit 2511 to use references.');
  }, [selectedWorkflow?.workflow_id]);
  useEffect(() => {
    if (!active) return;
    let alive = true, polling = false;
    const poll = async () => {
      if (polling) return;
      polling = true;
      try {
        const updated = await getImageBatch(active.workspaceId, active.batchId);
        if (!alive) return;
        setBatch(updated);
        const job = updated.jobs?.[0];
        if (job?.status === 'completed' && job.output_asset_id && !selectedAsset) {
          const result = await listMediaAssets(active.workspaceId, 'image');
          if (!alive) return;
          const asset = result.assets.find(item => item.asset_id === job.output_asset_id);
          if (asset) { setSelectedAsset(asset); setOutputName(asset.filename); }
          else { setMessage('Image generated. Waiting for the temporary result to be indexed.'); return; }
        }
        // Keep the active job identity until the user saves the final bytes to the
        // chosen folder; the save action needs its token to remove the temp copy.
        if (job?.status === 'completed' && selectedAsset?.asset_id === job.output_asset_id) {
          if(!active.outputToken){localStorage.removeItem(ACTIVE_KEY);setActive(null);setMessage('Image saved in the output folder and project media library.');}
          return;
        }
        if (job && ['completed', 'failed', 'cancelled', 'recovery_required'].includes(job.status)) {
          if (job.status !== 'completed') {
            localStorage.removeItem(ACTIVE_KEY); setActive(null);
          }
          setMessage(job.status === 'completed' ? 'Image is ready. Choose an output folder and save it there; the temporary server copy is removed after the save is verified.' : `Image job ${job.status.replaceAll('_', ' ')}${job.error?.message ? `: ${job.error.message}` : '.'}`);
        }
      } catch (reason) { if (alive) setError(`Could not refresh image job: ${(reason as Error).message}`); }
      finally { polling = false; }
    };
    void poll(); const timer = window.setInterval(() => void poll(), 2500);
    return () => { alive = false; window.clearInterval(timer); };
  }, [active?.workspaceId, active?.batchId, selectedAsset]);

  const stageReferences = async (files: File[]) => {
    if (!editing) { setMessage('Select Qwen Image Edit 2511 to use reference images.'); return; }
    const remaining = Math.max(0, referenceLimit - references.length);
    const accepted = files.filter(file => file.type.startsWith('image/')).slice(0, remaining);
    if (!accepted.length) { setError(references.length >= referenceLimit ? 'Qwen Image Edit accepts up to three reference images.' : 'Choose image files.'); return; }
    setBusy(true); setError('');
    try {
      const staged: Ref[] = [];
      try {
        for (const file of accepted) {
          const token = randomToken();
          const asset = await stageTemporaryImageReference(workspaceId, file, token);
          staged.push({ asset, token });
        }
      } catch (reason) {
        await Promise.allSettled(temporaryReferences(staged).map(ref => deleteTemporaryImageAsset(workspaceId, ref.assetId, ref.token)));
        throw reason;
      }
      setReferences(old => {
        const next = [...old, ...staged].slice(0, referenceLimit);
        localStorage.setItem(referenceKey, JSON.stringify(next.map(ref => ({ assetId: ref.asset.asset_id, token: ref.token }))));
        return next;
      });
      setMessage(`${staged.length} image reference${staged.length === 1 ? '' : 's'} ready for Qwen Image Edit.`);
    } catch (reason) { setError(`Could not prepare reference image: ${(reason as Error).message}`); }
    finally { setBusy(false); }
  };
  const removeReference = async (index: number) => {
    const ref = references[index]; setReferences(old => old.filter((_, i) => i !== index));
    localStorage.setItem(referenceKey, JSON.stringify(references.filter((_, i) => i !== index).map(item => ({ assetId: item.asset.asset_id, token: item.token }))));
    if(ref.token) await deleteTemporaryImageAsset(workspaceId, ref.asset.asset_id, ref.token).catch(reason => setError(`Temporary reference cleanup failed: ${(reason as Error).message}`));
  };
  const prepare = async () => {
    if (!workflowId || (editing && (!references.length || references.length>referenceLimit))) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const source_references = editing ? references.map(item => ({ asset_id: item.asset.asset_id, sha256: item.asset.sha256 })) : [];
      const result = await prepareImagePrompt({ workspace_id: workspaceId, workflow_id: workflowId, asset_role: 'image_candidate', prompt: prompt.trim(), ...(source_references.length ? { source_references } : {}) });
      setPrompt(result.prompt); setPromptDraft(result);
      setMessage(`Prompt prepared from ${result.sources.length} workflow guidance source${result.sources.length === 1 ? '' : 's'}. Review and edit it before generating.`);
    } catch (reason) { setError(`Could not prepare prompt: ${(reason as Error).message}`); }
    finally { setBusy(false); }
  };
  const generate = async () => {
    if (!destinationReady || active || !selectedWorkflow?.available || !prompt.trim() || busy || (editing && (!references.length || references.length>referenceLimit))) return;
    setBusy(true); setError(''); setMessage('Checking workflow, GPU safety and worker readiness…');
    try {
      const [catalog, runtime, worker] = await Promise.all([getImageWorkflows(true), getRuntimeGuard(), getImageWorker()]);
      const exact = catalog.workflows.find(item => item.workflow_id === workflowId);
      if (!exact?.available || catalog.gpu_admission?.available !== true || runtime.safe_to_submit !== true || worker.available !== true) throw new Error(exact?.disabled_reason || catalog.gpu_admission?.reason || runtime.reason || worker.reason || 'Workflow, GPU safety and image worker must all be ready.');
      const source_references = editing ? references.map(item => ({ asset_id: item.asset.asset_id, sha256: item.asset.sha256 })) : [];
      const outputToken = '';
      const request = { zimage_lora:workflowId==='z_image_turbo'?lora:null, workflow_id: workflowId, initial_candidate_count: 1, prompt: prompt.trim(), control_mode: 'assisted_manual', seed, output_prefix: `standalone/image_candidate`, workspace_id: workspaceId, idempotency_key: crypto.randomUUID(), asset_role: 'image_candidate', width, height, steps, cfg,
        ...(promptDraft?.workflow_id === workflowId ? { prompt_knowledge_ref: promptDraft.knowledge_ref } : {}), ...(source_references.length ? { source_references } : {}) };
      await validateImageRequest(request);
      const result = await createImageBatch(request);
      const next: Active = { workspaceId, batchId: result.batch_id, outputToken, staged: temporaryReferences(references) };
      localStorage.setItem(ACTIVE_KEY, JSON.stringify(next)); setBatch({ batch_id: result.batch_id, jobs: result.jobs, generation_policy: {} }); setSelectedAsset(null); setActive(next);
      setMessage('Image request queued. This page will reconnect to the job after reload.');
    } catch (reason) { setError(`Generation was not started: ${(reason as Error).message}`); setMessage(''); }
    finally { setBusy(false); }
  };
  const chooseOutputFolder = async () => {
    setError('');
    try {
      const picker = (window as Window & { showDirectoryPicker?: (options?: { mode?: 'read'|'readwrite' }) => Promise<DirectoryHandle> }).showDirectoryPicker;
      if (!picker) throw new Error('This browser cannot choose a writable folder. Use a browser with local folder access on localhost.');
      setOutputHandle(await picker({ mode: 'readwrite' }));
    } catch (reason) { if ((reason as DOMException).name !== 'AbortError') setError((reason as Error).message); }
  };
  const saveOnlyToChosenFolder = async () => {
    if (!readyAsset || !outputHandle || !active || !outputName.trim() || /[\\/]/.test(outputName)) return;
    setBusy(true); setError('');
    try {
      let fileHandle: FileSystemFileHandle;
      try { fileHandle = await outputHandle.getFileHandle(outputName, { create: false });
        if (!window.confirm(`${outputName} already exists. Overwrite it?`)) { setOutputName(outputName.replace(/(\.[^.]+)?$/, '-2$1')); return; }
      } catch (reason) { if ((reason as DOMException).name !== 'NotFoundError') throw reason; fileHandle = await outputHandle.getFileHandle(outputName, { create: true }); }
      const response = await fetch(readyAsset.content_url);
      if (!response.ok) throw new Error('Could not retrieve the temporary generated image.');
      const blob = await response.blob();
      const stream = await fileHandle.createWritable(); await stream.write(blob); await stream.close();
      const written = await fileHandle.getFile();
      if (await digest(await written.arrayBuffer()) !== readyAsset.sha256) throw new Error('Saved image verification failed. The temporary server copy is being retained for recovery.');
      setPreviewUrl(URL.createObjectURL(written));
      await deleteTemporaryImageAsset(workspaceId, readyAsset.asset_id, active.outputToken);
      setSelectedAsset(null); setBatch(null); setActive(null); localStorage.removeItem(ACTIVE_KEY);
      await Promise.allSettled((active.staged || temporaryReferences(references)).map(ref => deleteTemporaryImageAsset(workspaceId, ref.assetId, ref.token)));
      setReferences([]); localStorage.removeItem(referenceKey); localStorage.removeItem(WORKSPACE_KEY); setWorkspaceId(temporaryWorkspaceId()); setMessage(`Saved and verified ${outputName} in ${outputHandle.name}. Temporary Vibe Director image copies were removed.`);
    } catch (reason) { setError(`Could not save and verify image: ${(reason as Error).message}`); }
    finally { setBusy(false); }
  };

  return <main className="content-wrap text-to-image-page">
    <header className="page-heading"><div><div className="eyebrow">GENERATION ASSETS</div><h1>Text to Image</h1><p>Generate an image in your project or use this tool on its own.</p></div><button type="button" className="quiet-button" onClick={() => { setError(''); setLoading(true); void getImageWorkflows(false).then(value => setWorkflows(value.workflows.filter(item => MODELS.some(model => model.id === item.workflow_id)))).catch(reason => setError((reason as Error).message)).finally(() => setLoading(false)); }} disabled={loading}><RefreshCw size={15}/> Refresh workflows</button></header>
    {error && <div className="error-banner" role="alert">{error}</div>}{message && <div className="notice" role="status">{message}</div>}
    {active?.outputToken?<div className="t2i-workspace card"><strong>Finish saving the previous image</strong><button type="button" className="quiet-button" onClick={()=>void chooseOutputFolder()}><FolderOpen size={15}/> Choose output folder</button><span>{outputHandle?.name || 'No output folder selected'}</span><small>The previous temporary result stays available until its saved bytes are verified.</small></div>:<OutputDestination tool="image-generation" workspaceId={workspaceId} disabled={busy||!!active} onReady={setDestinationReady}/>}

    <div className="t2i-layout">
      <section className="card t2i-controls" aria-label="Image creation controls">
        <label>Image model<select aria-label="Image model" value={workflowId} onChange={event => { setWorkflowId(event.target.value); setPromptDraft(null); }}>
          {MODELS.map(model => { const item = workflows.find(row => row.workflow_id === model.id); return <option key={model.id} value={model.id} disabled={!item?.available}>{model.label}{item?.available ? '' : ' · unavailable'}</option>; })}
        </select></label>
        {selectedWorkflow && <p className="t2i-model-state">{selectedWorkflow.available ? `${selectedWorkflow.label} · workflow ${selectedWorkflow.version} ready` : selectedWorkflow.disabled_reason || 'This workflow is not ready.'}</p>}
        {editing && <div className="t2i-reference-tray" aria-label="Selected workflow references">{references.length ? references.map((ref,index)=><span key={ref.asset.asset_id}><img src={ref.asset.content_url} alt=""/>{ref.asset.filename}<button type="button" aria-label={`Remove reference ${ref.asset.filename}`} onClick={()=>void removeReference(index)}><X size={13}/></button></span>) : <small>Select images below and choose “Use as reference”. Kontext accepts one reference; Qwen Edit accepts up to three.</small>}</div>}
        {editing&&<MediaSourcePicker workspaceId={workspaceId} kinds={['image']} compact role="project_image" disabled={busy||loading||!!active||references.length>=referenceLimit}
          destination={{kind:'model_reference',slot:'image references',capacity:Math.max(0,referenceLimit-references.length),onSelect:items=>{
            if(items.some(asset=>asset.workspace_id!==workspaceId||asset.kind!=='image'))throw new Error('Choose registered image references for this project.');
            const next:Ref[]=[...references,...items.filter(asset=>!references.some(ref=>ref.asset.asset_id===asset.asset_id)).map(asset=>({asset}))];
            if(next.length>referenceLimit)throw new Error('This workflow has too many references; Kontext accepts one, Qwen Edit up to three.');
            setReferences(next);setPromptDraft(null);
            localStorage.setItem(referenceKey,JSON.stringify(next.map(ref=>({assetId:ref.asset.asset_id,token:ref.token}))));
          }}}/>}
        <ZImageLoraControls enabled={workflowId==='z_image_turbo'} onChange={setLora} onTrigger={word=>setPrompt(old=>`${word} ${old}`)}/><label>Prompt<textarea aria-label="Image prompt" rows={7} maxLength={6999} value={prompt} onChange={event => { setPrompt(event.target.value); setPromptDraft(null); }} placeholder="Describe the image you want to create…"/></label>
        <div className="t2i-settings">{workflowId==='flux_kontext_dev'&&<p>Kontext follows the reference’s native aspect bucket. Width and height below are nominal; review the actual output before accepting.</p>}<label>Width<input type="number" disabled={workflowId==='flux_kontext_dev'} min="256" max="2048" step="8" value={width} onChange={event => setWidth(Number(event.target.value))}/></label><label>Height<input type="number" disabled={workflowId==='flux_kontext_dev'} min="256" max="2048" step="8" value={height} onChange={event => setHeight(Number(event.target.value))}/></label><label>Steps<input type="number" min={['qwen_image_2512','flux_kontext_dev'].includes(workflowId) ? 20 : 4} max={['qwen_image_2512','flux_kontext_dev'].includes(workflowId) ? 80 : 16} value={steps} onChange={event => setSteps(Number(event.target.value))}/></label><label>CFG<input type="number" min="0.1" max={workflowId === 'z_image_turbo' ? 2 : 8} step="0.1" value={cfg} onChange={event => setCfg(Number(event.target.value))}/></label><label>Seed<input type="number" min="0" max="4294967295" value={seed} onChange={event => setSeed(Number(event.target.value))}/></label></div>
        <div className="t2i-actions"><button type="button" className="quiet-button" onClick={() => void prepare()} disabled={busy||(editing&&(!references.length||references.length>referenceLimit))}><Sparkles size={15}/> Prepare prompt</button><button type="button" className="generate-button" onClick={() => void generate()} disabled={busy||loading||!selectedWorkflow?.available||!prompt.trim()||(editing&&(!references.length||references.length>referenceLimit))||!!active||!destinationReady}>{busy?<LoaderCircle size={15} className="spin"/>:<ImageIcon size={15}/>} {active?'Generating…':'Generate image'}</button></div>
      </section>
      <section className="card t2i-result" aria-label="Generated image preview"><h2>Image preview</h2>{active&&<div className="t2i-progress"><LoaderCircle size={17} className="spin"/><span>{currentJob?.status?`Image job ${currentJob.status.replaceAll('_',' ')}`:'Connecting to image job…'}</span>{currentJob?.error?.message&&<p role="alert">{currentJob.error.message}</p>}</div>}{readyAsset?<><figure><img src={readyAsset.content_url} alt={readyAsset.description||readyAsset.filename}/><figcaption>{readyAsset.filename} · {readyAsset.media?.width||'—'} × {readyAsset.media?.height||'—'} · {active?.outputToken?'temporary until saved':'saved in output folder'}</figcaption></figure>{active?.outputToken?<><label>Filename<input value={outputName} onChange={event=>setOutputName(event.target.value)} placeholder="image.png"/></label><button type="button" className="generate-button" disabled={busy||!outputHandle||!active||!outputName.trim()} onClick={()=>void saveOnlyToChosenFolder()}><Check size={15}/> Save to chosen folder</button></>:<a className="quiet-button" href={readyAsset.content_url} download={readyAsset.filename}>Download image</a>}</>:previewUrl?<figure><img src={previewUrl} alt="Saved generated image"/><figcaption>{outputName} · Saved to {outputHandle?.name || 'chosen folder'}</figcaption></figure>:<div className="t2i-empty"><ImageIcon size={40}/><p>Choose a model, write a prompt, select an output folder, and generate.</p></div>}</section>
    </div>
    <DirectorImageReview disabled={busy||loading||!!active||(editing&&(!references.length||references.length>referenceLimit))} request={{workspace_id:workspaceId,workflow_id:workflowId,asset_role:'image_candidate',
      prompt:[prompt.trim(),chatAttachments.length?`Attached local image filenames (metadata only): ${chatAttachments.map(file=>file.name).join(', ')}.`:''].filter(Boolean).join('\n\n'),
      ...(editing&&references.length?{source_references:references.map(item=>({asset_id:item.asset.asset_id,sha256:item.asset.sha256}))}:{})}}
      onApply={draft=>{setPrompt(draft.prompt);setPromptDraft(draft);}}/>
    {promptDraft&&<details><summary>Prompt guidance</summary><small>{promptDraft.knowledge_ref.knowledge_id} · v{promptDraft.knowledge_ref.guidance_version}</small></details>}
    {!!previousChatDraft&&<details><summary>Previous image chat draft</summary><p>{previousChatDraft}</p></details>}
    <details className="card t2i-folder-details"><summary>Reference image folder</summary>
      <p>Local attachments provide filenames to the Director. Choose Use as reference to send image bytes to a compatible generation workflow.</p>
      <div className="t2i-chat-attachments" onDragOver={event=>event.preventDefault()} onDrop={event=>{event.preventDefault();const files=Array.from(event.dataTransfer.files).filter(file=>file.type.startsWith('image/'));setChatAttachments(old=>[...old,...files.filter(file=>!old.some(item=>item.name===file.name&&item.size===file.size))]);}}>
        {chatAttachments.map((file,index)=><span key={`${file.name}:${file.size}:${index}`}><img src={chatPreviewUrls[index]} alt=""/>{file.name}<button type="button" aria-label={`Remove ${file.name}`} onClick={()=>setChatAttachments(old=>old.filter((_,i)=>i!==index))}><X size={13}/></button></span>)}
      </div>
      <LocalImageFolderBrowser maxReferences={referenceLimit} referencesEnabled={editing&&references.length<referenceLimit} onUseAsReference={files=>void stageReferences(files)} onAttachToChat={files=>setChatAttachments(old=>[...old,...files.filter(file=>!old.some(item=>item.name===file.name&&item.size===file.size))])}/>
    </details>
  </main>;
}
