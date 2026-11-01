import OutputDestination from './OutputDestination';
import MediaSourcePicker from './MediaSourcePicker';
import AceGeneratedAudio from './AceGeneratedAudio';
import ModelSelector, { consumeModelCommand } from './ModelSelector';
import {useEffect, useRef, useState} from 'react';
import EditorWorkspace from './EditorWorkspace';
import {MediaAsset, listMediaAssets, uploadMediaAsset} from './lib/media-api';
import {listStoryWorkspaces, StoryWorkspace} from './lib/story-api';
import {mediaWorkspaceOptions} from './lib/media-workspace';
import './ace-studio.css';
import {aceDroppedFiles} from './ace-folder-upload';

type Settings = {mode:string;tags:string;lyrics:string;duration:number;seed:number;steps:number;cfg:number;scheduler:string;adapter_id:string;max_steps:number;learning_rate:number;save_every:number;rank:number;task:string;reference_id:string;reference_strength:number;source_tags:string;source_lyrics:string;edit_min:number;edit_max:number;style_name:string;style_description:string};
const extras={task:'text',reference_id:'',reference_strength:.5,source_tags:'',source_lyrics:'',edit_min:.6,edit_max:1,style_name:'',style_description:''};
type Job = {job_id:string;status:string;stage:string;message:string;error?:string;result?:unknown;step_progress?:{done:number;total:number}};
type Project = {id:string;name:string;workspace_id:string;revision:number;settings:Settings;intent:'generate'|'finetune';summary:string;questions:string[];messages:Array<{id:string;role:string;content:string}>;dataset:null|{count:number;songs:string[];entries?:Array<{relative_path:string;duration_seconds:number;prompt:string;lyrics:string}>};assets:MediaAsset[];adapters:Array<{id:string;name:string;tags?:string;description?:string}>;job_id:string|null;job?:Job;confirmed_revision?:number|null};
type State = {projects:Project[];defaults:Settings;presets?:Record<string,string>;saved_presets?:Array<{id:string;name:string;tags:string}>;adapters?:Array<{id:string;name:string;description?:string;tags?:string}>;runtime:{ready:boolean;training_ready:boolean;reason:string;dataset_format:string;checks:Record<string,boolean>;training_encoders_cached:boolean;source:string;python:string;checkpoints:string}};
const active = (job?:Job)=>Boolean(job&&['queued','running','cancel_requested'].includes(job.status));
async function api<T>(path:string,body?:unknown):Promise<T> {
  const response=await fetch(`/api/ace/${path}`,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const value=await response.json();
  if(!response.ok)throw new Error(value?.error?.message||'Music request failed.');
  return value;
}
export default function AceStudioPage() {
  const [destinationReady,setDestinationReady]=useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const [state,setState]=useState<State|null>(null),[projectId,setProjectId]=useState(()=>{try{return localStorage.getItem('vibe-ace-project')||'';}catch{return '';}});
  const [stories,setStories]=useState<StoryWorkspace[]>([]),[workspace,setWorkspace]=useState('tool-library'),[name,setName]=useState('Untitled music');
  const [draft,setDraft]=useState(''),[config,setConfig]=useState<Settings|null>(null),[intent,setIntent]=useState<'generate'|'finetune'>('generate');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[tab,setTab]=useState<'settings'|'dataset'|'styles'|'assets'|'runtime'>('settings'),[log,setLog]=useState('');
  const bottom=useRef<HTMLDivElement>(null),folderInput=useRef<HTMLInputElement>(null);
  const [references,setReferences]=useState<MediaAsset[]>([]),[presetName,setPresetName]=useState(''),[loadedKey,setLoadedKey]=useState('');
  const project:Project|undefined=state?.projects.find(p=>p.id===projectId)||(state?{id:'',name:name.trim()||'Untitled music',workspace_id:workspace||'tool-library',revision:0,settings:state.defaults,intent:'generate',summary:'',questions:[],messages:[],dataset:null,assets:[],adapters:[],job_id:null}:undefined),locked=busy||active(project?.job);
  const creating=useRef<Promise<Project>|null>(null);
  const ensureProject=async()=>{
    if(project?.id)return project;
    if(!project)throw new Error('Music settings are still loading.');
    if(!creating.current)creating.current=api<Project>('projects',{name:project.name,workspace_id:project.workspace_id}).then(p=>{
      try{localStorage.setItem(`vibe-ace-draft-${p.id}`,JSON.stringify({revision:p.revision,config,intent,draft}));}catch{/* Server session remains usable. */}
      setState(current=>current?{...current,projects:[...current.projects,p]}:current);setProjectId(p.id);return p;
    }).finally(()=>{creating.current=null;});
    return creating.current;
  };
  const refresh=async()=>{const next=await api<State>('state');setState(next);setProjectId(id=>{if(id&&!next.projects.some(p=>p.id===id)){try{const recovered=localStorage.getItem(`vibe-ace-draft-${id}`);if(recovered){const value=JSON.parse(recovered);localStorage.setItem('vibe-ace-draft-',JSON.stringify({...value,revision:0}));}}catch{/* Keep original recovery draft. */}return '';}return id;});return next;};
  const attempt=async(work:()=>Promise<unknown>)=>{setBusy(true);setError('');setNotice('');try{await work();await refresh();}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  useEffect(()=>{void refresh().catch(e=>setError(e.message));void listStoryWorkspaces().then(result=>{setStories(result.items);}).catch(e=>setError(e.message));},[]);
  useEffect(()=>{try{localStorage.setItem('vibe-ace-project',projectId);}catch{/* Current project remains usable. */}},[projectId]);
  useEffect(()=>{
    if(!project){setConfig(null);setLoadedKey('');return;}
    let saved:null|{revision:number;config:Settings;intent:typeof intent;draft:string}=null;
    try{saved=JSON.parse(localStorage.getItem(`vibe-ace-draft-${project.id}`)||'null');}catch{/* Use saved server state. */}
    const same=saved?.revision===project.revision;
    setConfig({...extras,...project.settings,...(same?saved!.config:{})});setIntent(same?saved!.intent:project.intent);setDraft(same?saved!.draft:'');setLoadedKey(`${project.id}:${project.revision}`);setLog('');
  },[project?.id,project?.revision]);
  useEffect(()=>{if(project&&config&&loadedKey===`${project.id}:${project.revision}`)try{localStorage.setItem(`vibe-ace-draft-${project.id}`,JSON.stringify({revision:project.revision,config,intent,draft}));}catch{/* Explicit save remains usable. */}},[loadedKey,project?.id,project?.revision,config,intent,draft]);
  useEffect(()=>{let cancelled=false;setReferences([]);if(project)void listMediaAssets(project.workspace_id,'audio').then(r=>{if(!cancelled)setReferences(r.assets);}).catch(e=>{if(!cancelled)setError(e.message);});return()=>{cancelled=true;};},[project?.workspace_id]);
  useEffect(()=>{bottom.current?.scrollIntoView({block:'nearest'});},[project?.messages.length]);
  useEffect(()=>{if(!active(project?.job))return;const timer=window.setInterval(()=>void refresh().catch(e=>setError(e.message)),2500);return()=>window.clearInterval(timer);},[project?.job?.job_id,project?.job?.status]);
  const save=async()=>{
    if(!config)throw new Error('Music settings are still loading.');
    const target=await ensureProject();
    if(JSON.stringify(config)===JSON.stringify({...extras,...target.settings})&&intent===target.intent)return target;
    const saved=await api<Project>(`projects/${target.id}/command`,{action:'settings',revision:target.revision,settings:config,intent});
    try{localStorage.setItem(`vibe-ace-draft-${saved.id}`,JSON.stringify({revision:saved.revision,config,intent,draft}));}catch{/* Current draft remains in memory. */}
    return saved;
  };
  const send=()=>attempt(async()=>{const saved=await save();const reply=await api<Project>(`projects/${saved.id}/command`,{action:'chat',revision:saved.revision,text:draft});setTab(reply.intent==='finetune'?'dataset':'settings');setDraft('');});
  const attach=async(files:File[])=>{
    if(!project||!config)throw new Error('Open a music project first.');
    if(files.length!==1||(!files[0].type.startsWith('audio/')&&!/\.(wav|mp3|flac|ogg|m4a)$/i.test(files[0].name)))throw new Error('Choose one audio recording.');
    const target=await save();
    const asset=await uploadMediaAsset(target.workspace_id,files[0],'project_audio');
    await api(`projects/${target.id}/command`,{action:'settings',revision:target.revision,intent,settings:{...config,reference_id:asset.asset_id,task:config.task==='text'?'reference':config.task}});
    setReferences(r=>[asset,...r.filter(a=>a.asset_id!==asset.asset_id)]);setNotice(`Attached ${asset.filename}. Uploading does not start a job.`);
  };
  const upload=async(files:File[])=>{
    if(!project)throw new Error('Create a music project before adding a dataset.');
    const byName=new Map<string,File>();
    const relative=(file:File)=>file.webkitRelativePath||file.name;
    for(const file of files){const path=relative(file);if(path.startsWith('/')||path.includes('\\')||path.split('/').some(p=>!p||p==='.'||p==='..')||byName.has(path))throw new Error(`Invalid or duplicate path: ${path}`);byName.set(path,file);}
    const mp3s=files.filter(f=>f.name.endsWith('.mp3'));
    if(!mp3s.length||mp3s.length>500)throw new Error('Select 1–500 MP3 recordings and their matching _prompt.txt and _lyrics.txt files together.');
    const expected=new Set(mp3s.flatMap(f=>[relative(f),relative(f).replace(/\.mp3$/,'_prompt.txt'),relative(f).replace(/\.mp3$/,'_lyrics.txt')]));
    if(files.some(f=>!expected.has(relative(f))))throw new Error('Some files do not belong to an MP3/prompt/lyrics triplet.');
    // Validate every triplet before uploading any recording.
    const triplets=await Promise.all(mp3s.map(async file=>{
      const stem=file.name.slice(0,-4),promptFile=byName.get(relative(file).replace(/\.mp3$/,'_prompt.txt')),lyricsFile=byName.get(relative(file).replace(/\.mp3$/,'_lyrics.txt'));
      if(!/^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(stem)||!promptFile||!lyricsFile)throw new Error(`Incomplete or invalid triplet: ${stem}`);
      const prompt=await promptFile.text(),lyrics=await lyricsFile.text();
      if(!prompt.trim()||!lyrics.trim()||prompt.length>4000||lyrics.length>10000)throw new Error(`Check prompt and lyrics lengths for ${stem}.`);
      return {file,stem,prompt,lyrics,relative_path:relative(file)};
    }));
    const saved=await save();
    const rows=[];
    for(const row of triplets){setNotice(`Importing ${row.relative_path}…`);const asset=await uploadMediaAsset(saved.workspace_id,row.file,'project_audio');rows.push({stem:row.stem,relative_path:row.relative_path,prompt:row.prompt,lyrics:row.lyrics,asset_id:asset.asset_id});}
    await api(`projects/${saved.id}/dataset`,{rows,revision:saved.revision});setNotice(`${rows.length} song triplets validated and saved.`);
  };
  const numeric=(key:keyof Settings,label:string,min:number,max:number,step=1)=><label>{label}<input type="number" min={min} max={max} step={step} disabled={locked} value={String(config?.[key]??'')} onChange={e=>setConfig(c=>c?{...c,[key]:Number(e.target.value)}:c)}/></label>;
  const adapters=state?.adapters??state?.projects.flatMap(p=>p.adapters)??[];
  const reference=references.find(a=>a.asset_id===config?.reference_id);
  const chooseStyle=(value:string)=>{
    if(!config)return;
    if(value.startsWith('base:'))setConfig({...config,adapter_id:'',tags:state?.presets?.[value.slice(5)]||''});
    else if(value.startsWith('preset:'))setConfig({...config,adapter_id:'',tags:state?.saved_presets?.find(p=>p.id===value.slice(7))?.tags||''});
    else {const adapter=adapters.find(a=>a.id===value);setConfig({...config,adapter_id:value,...(adapter?.tags?{tags:adapter.tags}:{})});}
  };
  const styleSelect=<label>Style<select disabled={locked||!config} value={config?.adapter_id||(state?.saved_presets?.find(p=>p.tags===config?.tags)?`preset:${state.saved_presets.find(p=>p.tags===config?.tags)!.id}`:Object.entries(state?.presets||{}).find(([,tags])=>tags===config?.tags)?`base:${Object.entries(state?.presets||{}).find(([,tags])=>tags===config?.tags)![0]}`:'')} onChange={e=>chooseStyle(e.target.value)}><option value="">Custom prompt / base model</option><optgroup label="Prompt presets">{Object.keys(state?.presets||{}).map(n=><option key={n} value={`base:${n}`}>{n}</option>)}{state?.saved_presets?.map(p=><option key={p.id} value={`preset:${p.id}`}>{p.name}</option>)}</optgroup><optgroup label="Trained LoRAs">{adapters.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</optgroup></select></label>;
  const runButton=project&&config&&<button className="ace-run" disabled={locked||(intent==='generate'&&!destinationReady)||(intent==='finetune'?(!state?.runtime.training_ready||!project.dataset||!config.style_name.trim()):!state?.runtime.ready)||project.confirmed_revision===project.revision&&JSON.stringify(config)===JSON.stringify({...extras,...project.settings})&&intent===project.intent} onClick={()=>void attempt(async()=>{const p=await save();await api(`projects/${p.id}/command`,{action:'confirm',revision:p.revision});})}>{busy&&<span className="ace-spinner" aria-hidden="true"/>}{intent==='finetune'?'Start fine-tuning':'Run ACE-Step'}</button>;
  const preview=<>
    <nav className="ace-tabs" aria-label="Music panels">{(['settings','dataset','styles','assets','runtime'] as const).map(t=><button type="button" key={t} aria-pressed={tab===t} onClick={()=>{setTab(t);if(!locked&&t==='settings')setIntent('generate');if(!locked&&t==='dataset')setIntent('finetune');}}>{t==='dataset'?'Fine-tune':t==='styles'?'Styles':t==='assets'?'Audio & models':t==='runtime'?'Connection':'Create'}</button>)}</nav>
    {tab==='settings'&&project&&config&&<>
      <h2>{intent==='finetune'?'Fine-tune music':'Create music'}</h2>
      <label>Task<select disabled={locked} value={intent} onChange={e=>{setIntent(e.target.value as typeof intent);if(e.target.value==='finetune')setTab('dataset');}}><option value="generate">Generate song / instrumental</option><option value="finetune">Train a music LoRA</option></select></label>
      {intent==='generate'?<>
        <label>Generation method<select disabled={locked} value={config.task} onChange={e=>setConfig({...config,task:e.target.value,...(e.target.value==='remix'?{edit_min:.2,edit_max:.4}:e.target.value==='lyrics'?{edit_min:.6,edit_max:1}:{})})}><option value="text">Text to music</option><option value="reference">Reference-guided music</option><option value="remix">Remix / change track</option><option value="lyrics">Replace lyrics</option></select></label>
        <p>Reference mode retains elements of a recording. Remix and lyric edits need its original description and lyrics. Exact melody or sound preservation is not guaranteed.</p>
        <MediaSourcePicker workspaceId={project.workspace_id} kinds={['audio']} disabled={locked} onAdded={items=>setReferences(rows=>[...rows.filter(row=>!items.some(item=>item.asset_id===row.asset_id)),...items])}/>
        <div className="ace-drop" tabIndex={0} aria-label="Reference audio drop area" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!locked)void attempt(()=>attach(Array.from(e.dataTransfer.files)));}} onPaste={e=>{const files=Array.from(e.clipboardData.files);if(files.length){e.preventDefault();if(!locked)void attempt(()=>attach(files));}}}>
          <label>Reference audio<input type="file" accept="audio/*" disabled={locked} onChange={e=>{const files=Array.from(e.target.files||[]);if(files.length)void attempt(()=>attach(files));e.target.value='';}}/></label><small>Choose, drop or paste one audio file, up to 240 seconds. Chat receives metadata, not the sound itself.</small>
          <label>Library audio<select disabled={locked} value={config.reference_id} onChange={e=>setConfig({...config,reference_id:e.target.value,...(e.target.value&&config.task==='text'?{task:'reference'}:{})})}><option value="">No reference</option>{references.map(a=><option key={a.asset_id} value={a.asset_id}>{a.filename}</option>)}</select></label>
          {reference&&<><p>{reference.filename}</p><audio controls src={reference.content_url}/><button disabled={locked} onClick={()=>setConfig({...config,reference_id:''})}>Remove reference</button></>}
        </div>
        {config.task==='text'&&config.reference_id&&<p>Text mode will not use the attachment. Select Reference-guided music to use it.</p>}
        {config.task==='reference'&&numeric('reference_strength','Reference strength',0,1,.05)}
        {styleSelect}<small>Presets fill editable tags. Trained styles select one LoRA; selecting a style keeps your lyrics.</small>
        <label>Type<select disabled={locked} value={config.mode} onChange={e=>setConfig({...config,mode:e.target.value})}><option value="instrumental">Instrumental</option><option value="song">Song with lyrics</option></select></label>
        <label>Music prompt<textarea rows={5} maxLength={4000} disabled={locked} value={config.tags} onChange={e=>setConfig({...config,tags:e.target.value})} placeholder="Genre, mood, instruments, tempo"/></label>
        <label>Lyrics<textarea rows={12} maxLength={10000} disabled={locked} value={config.lyrics} onChange={e=>setConfig({...config,lyrics:e.target.value,...(e.target.value.trim()?{mode:'song'}:{})})} placeholder={'[verse]\nYour words…\n[chorus]\nYour chorus…'}/></label>
        {config.mode==='instrumental'&&<small>Instrumental mode sends [instrumental]; pasted lyrics are retained but not used.</small>}
        {['remix','lyrics'].includes(config.task)&&<fieldset><legend>Original recording</legend><label>Original music description<textarea maxLength={4000} disabled={locked} value={config.source_tags} onChange={e=>setConfig({...config,source_tags:e.target.value})}/></label><label>Original lyrics<textarea maxLength={10000} disabled={locked} value={config.source_lyrics} onChange={e=>setConfig({...config,source_lyrics:e.target.value})} placeholder="Original words or [instrumental]"/></label>{numeric('edit_min','Edit interval start',0,1,.05)}{numeric('edit_max','Edit interval end',0,1,.05)}</fieldset>}
        {numeric('duration','Duration (seconds)',5,240)}{numeric('seed','Seed',0,2147483647)}{numeric('steps','Inference steps',1,200)}{numeric('cfg','Guidance',0,30,.5)}
        <label>Scheduler<select disabled={locked} value={config.scheduler} onChange={e=>setConfig({...config,scheduler:e.target.value})}>{['euler','heun','pingpong'].map(s=><option key={s}>{s}</option>)}</select></label>
      </>:<>
        <p>{project.dataset?`${project.dataset.count} validated songs ready.`:'Add training triplets in Training files first.'}</p>
        {numeric('max_steps','Training steps (total)',1,100000)}{numeric('learning_rate','Learning rate',.0000001,.01,.00001)}{numeric('save_every','Save checkpoint every N steps',1,10000)}{numeric('rank','LoRA rank',1,256)}
        <p>Single GPU, batch size 1, BF16. Saves a new LoRA; the base model is retained.</p>
      </>}
      <button disabled={locked} onClick={()=>void attempt(save)}>Save settings</button>
      {runButton}
    </>}
    {tab==='dataset'&&<><h2>Fine-tune a music style</h2><p>Train a separate LoRA from recordings, descriptive tags and exact lyrics. Each completed run adds a named style. The base model is retained.</p><details open><summary>Training file format</summary><pre className="ace-format">{state?.runtime.dataset_format}</pre></details>
      <div className="ace-drop" aria-label="Training folder drop area" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(locked)return;const items=Array.from(e.dataTransfer.items),files=Array.from(e.dataTransfer.files);void attempt(async()=>upload(await aceDroppedFiles(items,files)));}}>
        <p>Drop a folder or matching triplets. Nested folders are supported; every MP3 needs both text files.</p>
        <label>Upload matching triplets<input type="file" multiple accept=".mp3,.txt" disabled={locked||!project} onChange={e=>{const files=Array.from(e.target.files||[]);if(files.length)void attempt(()=>upload(files));e.target.value='';}}/></label>
        <input hidden ref={folderInput} type="file" multiple {...{webkitdirectory:''}} onChange={e=>{const files=Array.from(e.target.files||[]);if(files.length)void attempt(()=>upload(files));e.target.value='';}}/>
        <button disabled={locked||!project} onClick={()=>folderInput.current?.click()}>Choose training folder</button>
      </div>
      {project?.dataset&&<><h3>{project.dataset.count} validated songs</h3>{project.dataset.entries?project.dataset.entries.map(row=><details key={row.relative_path}><summary>{row.relative_path} · {row.duration_seconds.toFixed(1)} seconds</summary><p>{row.prompt}</p><pre className="ace-format">{row.lyrics}</pre></details>):<ul>{project.dataset.songs.map(s=><li key={s}>{s}</li>)}</ul>}</>}
      {project&&config&&<><label>New style name<input maxLength={100} disabled={locked} value={config.style_name} onChange={e=>setConfig({...config,style_name:e.target.value})} placeholder="My acoustic style"/></label><label>Style description<textarea maxLength={1000} disabled={locked} value={config.style_description} onChange={e=>setConfig({...config,style_description:e.target.value})}/></label><label>Suggested generation tags<textarea maxLength={4000} disabled={locked} value={config.tags} onChange={e=>setConfig({...config,tags:e.target.value})}/></label><details><summary>Training settings</summary>{numeric('max_steps','Training steps (total)',1,100000)}{numeric('learning_rate','Learning rate',.0000001,.01,.00001)}{numeric('save_every','Save checkpoint every N steps',1,10000)}{numeric('rank','LoRA rank',1,256)}<p>Single GPU, batch size 1, BF16. More steps do not guarantee a better style.</p></details>{runButton}</>}
    </>}
    {tab==='styles'&&<><h2>Music styles</h2><p>{Object.keys(state?.presets||{}).length} built-in prompt presets. Tags are open-ended; these are starting points, not a complete list of what the model can make.</p>{styleSelect}{Object.entries(state?.presets||{}).map(([name,tags])=><details key={name}><summary>{name} · prompt preset</summary><p>{tags}</p><button disabled={locked||!project} onClick={()=>{chooseStyle(`base:${name}`);setIntent('generate');setTab('settings');}}>Use preset</button></details>)}{state?.saved_presets?.map(p=><details key={p.id}><summary>{p.name} · saved prompt</summary><p>{p.tags}</p></details>)}<h3>Trained LoRAs</h3>{!adapters.length&&<p>No trained styles yet. Successful fine-tuning adds them automatically.</p>}{adapters.map(a=><article key={a.id}><h4>{a.name}</h4><p>{a.description}</p><button disabled={locked||!project} onClick={()=>{chooseStyle(a.id);setIntent('generate');setTab('settings');}}>Use trained style</button></article>)}<label>Save current prompt as preset<input maxLength={100} disabled={locked} value={presetName} onChange={e=>setPresetName(e.target.value)} placeholder="Preset name"/></label><button disabled={locked||!project||!config?.tags.trim()||!presetName.trim()} onClick={()=>void attempt(async()=>{const saved=await save();await api(`projects/${saved.id}/command`,{action:'save_preset',revision:saved.revision,name:presetName,tags:config!.tags});setPresetName('');})}>Save prompt preset</button></>}
    {tab==='settings'&&project&&intent==='generate'&&<OutputDestination tool="ace-studio" workspaceId={project.workspace_id} disabled={locked} onReady={setDestinationReady}/>}
    {tab==='assets'&&<><AceGeneratedAudio workspaceId={project?.workspace_id||workspace} projects={state?.projects||[]} refreshKey={project?.job?.status} disabled={busy} onChanged={()=>{if(project)void listMediaAssets(project.workspace_id,'audio').then(r=>setReferences(r.assets)).catch(e=>setError(e.message));}}/><h2>Trained music models</h2>{adapters.map(a=><p key={a.id}>{a.name}</p>)}{!adapters.length&&<p>No trained LoRA yet.</p>}</>}
    {tab==='runtime'&&<><h2>Standalone ACE-Step</h2><p>{state?.runtime.reason||'Connection has not loaded.'}</p><p>Training encoders: {state?.runtime.training_encoders_cached?'cached':'MERT / mHuBERT not cached'}</p>{Object.entries(state?.runtime.checks||{}).map(([k,v])=><p key={k}>{v?'✓':'–'} {k}</p>)}<details><summary>Runtime locations</summary><pre className="ace-format">{JSON.stringify({source:state?.runtime.source,python:state?.runtime.python,checkpoints:state?.runtime.checkpoints},null,2)}</pre></details><p>Setup instructions: plans/ace_step_studio.md</p><button disabled={busy} onClick={()=>void attempt(refresh)}>Check connection</button></>}
    {project?.job&&<details><summary>Job details · {project.job.status}</summary><p>{project.job.stage} · {project.job.message}</p>{project.job.error&&<pre className="ace-format">{project.job.error}</pre>}<button onClick={()=>void attempt(async()=>{const r=await api<{text:string}>(`projects/${project.id}/log`);setLog(r.text);})}>Read runtime log</button>{log&&<pre className="ace-format">{log}</pre>}</details>}
  </>;
  return <div className="vibe-editor-page ace-studio-page">
    <header className="editor-header"><div><h1>ACE-Step Music</h1><small>Describe → review → confirm → listen</small></div><button disabled={busy} onClick={()=>void attempt(refresh)}>Refresh</button></header>
    {error&&<p role="alert" className="notice notice-warn">{error}</p>}{notice&&<p role="status" className="notice">{notice}</p>}
    <div className="editor-projects session-toolbar"><button disabled={locked} onClick={()=>{setProjectId('');setName('Untitled music');setIntent('generate');localStorage.removeItem('vibe-ace-draft-');setConfig(state?{...extras,...state.defaults}:null);setDraft('');}}>New session</button><label>Session name<input maxLength={100} disabled={locked||Boolean(projectId)} value={projectId?project?.name||'':name} onChange={e=>setName(e.target.value)}/></label><details><summary>Open / session details</summary><label>Saved music session<select aria-label="Music project" disabled={locked} value={projectId} onChange={e=>setProjectId(e.target.value)}><option value="">New session</option>{state?.projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>Optional story context<select disabled={locked||Boolean(projectId)} value={workspace||'tool-library'} onChange={e=>setWorkspace(e.target.value)}>{mediaWorkspaceOptions(stories,workspace).map(w=><option key={w.id} value={w.id}>{w.label}</option>)}</select></label><small>Attach audio with Browse media sources. Empty sessions are saved on your first action.</small></details></div>
    <EditorWorkspace name="ace-music" preview={preview}>
      {project?<>
        <div className="editor-project-status"><strong>{project.name}</strong><small>Draft kept in this browser · Save settings to store on server</small></div>
        <div className="editor-messages" aria-label="Music conversation">{!project.messages.length&&<p>Describe the music you want, ask for lyrics, or say you want to train a music style.</p>}{project.messages.map(m=><article key={m.id} className={`editor-message ${m.role}`}><small>{m.role==='user'?'You':'Director'}</small><p>{m.content}</p></article>)}<div ref={bottom}/></div>
        {(project.summary||config?.tags||intent==='finetune')&&<section className="editor-clearance"><h2>Review before {intent==='finetune'?'training':'generation'}</h2><p>{project.summary||'Review the settings in the right pane.'}</p><ul>{project.questions.map(q=><li key={q}>{q}</li>)}</ul><p>{intent==='finetune'?`${config?.max_steps} training steps · ${project.dataset?.count||0} songs`:`${config?.mode} · ${config?.duration} seconds · ${config?.steps} steps`}</p>{!(intent==='finetune'?state?.runtime.training_ready:state?.runtime.ready)&&<p>Runtime setup is incomplete. Open Connection for the missing items; chat and dataset preparation remain available.</p>}</section>}
        {!locked&&project.confirmed_revision===project.revision&&<button onClick={()=>void attempt(()=>api(`projects/${project.id}/command`,{action:'new_take',revision:project.revision}))}>Prepare another take</button>}
        {active(project.job)&&<section className="editor-job" role="status"><p>{project.job?.stage} · {project.job?.message}</p>{project.job?.step_progress?<><progress max={project.job.step_progress.total} value={project.job.step_progress.done}/><small>{project.job.step_progress.done} / {project.job.step_progress.total} steps in the current stage</small></>:<progress aria-label="ACE-Step is working"/>}<button disabled={busy} onClick={()=>void attempt(()=>api(`projects/${project.id}/command`,{action:'stop'}))}>Stop job</button></section>}
        <form className="editor-composer" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!locked)void attempt(()=>attach(Array.from(e.dataTransfer.files)));}} onSubmit={e=>{e.preventDefault();void send();}}><ModelSelector open={modelOpen} onClose={()=>setModelOpen(false)} disabled={locked} returnFocusId="ace-chat"/><label htmlFor="ace-chat">Talk to the music Director</label><textarea id="ace-chat" onPaste={e=>{const files=Array.from(e.clipboardData.files);if(files.length){e.preventDefault();if(!locked)void attempt(()=>attach(files));}}} rows={4} disabled={locked} value={draft} onChange={e=>setDraft(consumeModelCommand(e.target.value,()=>setModelOpen(true),"ace-chat"))} placeholder="Type /model to choose a model. Make a warm acoustic song… or help me fine-tune on my recordings" onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(draft.trim()&&!locked)void send();}}}/><label>Attach audio to chat<input type="file" accept="audio/*" disabled={locked} onChange={e=>{const files=Array.from(e.target.files||[]);if(files.length)void attempt(()=>attach(files));e.target.value='';}}/></label>{reference&&<div className="editor-range"><span>Attached: {reference.filename}</span><button type="button" disabled={locked} onClick={()=>setConfig(c=>c?{...c,reference_id:''}:c)}>Remove attachment</button></div>}<details><summary>Browse media sources</summary><MediaSourcePicker workspaceId={project.workspace_id} kinds={['audio']} disabled={locked} onAdded={items=>{const asset=items[0];if(asset){setReferences(rows=>[asset,...rows.filter(row=>row.asset_id!==asset.asset_id)]);setConfig(c=>c?{...c,reference_id:asset.asset_id,task:c.task==='text'?'reference':c.task}:c);}}}/></details><div><small>Chat edits settings. Run / Start fine-tuning starts the job.</small><button disabled={locked||!draft.trim()}>Send</button></div></form>
      </>:<p>Create or open a music project to begin.</p>}
    </EditorWorkspace>
  </div>;
}
