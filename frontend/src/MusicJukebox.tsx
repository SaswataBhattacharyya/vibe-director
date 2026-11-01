import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import EditorWorkspace from './EditorWorkspace';
import ModelSelector, { consumeModelCommand } from './ModelSelector';
import MediaSourcePicker from './MediaSourcePicker';
import VoiceRecorder from './VoiceRecorder';
import JukeboxDJ from './JukeboxDJ';
import { MediaAsset, uploadMediaAsset, nameMediaWorkspace } from './lib/media-api';
import { Clip, MusicProject, Source, Track, fresh, track, uid, length, loadSource, peaks, renderMusic, wav, midiImport, midiExport, houseBeat, splitClip, ripple, clearUnused, forgetBuffers } from './lib/jukebox-engine';
import './music-jukebox.css';
async function api<T>(path: string, body?: unknown): Promise<T> { const r = await fetch('/api/jukebox/' + path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); const v = await r.json(); if (!r.ok)
    throw Error(v.error?.message || 'Music request failed.'); return v; }
type Job = {
    job_id: string;
    status: string;
    message: string;
    error?: string;
    request?: {name:string;format:string;folder?:string;track_id?:string};
    result?: {
        url: string;
        name: string;
        path: string;
    };
};
type Proposal = {
    reply: string;
    action: 'none' | 'tempo' | 'gain' | 'house_beat' | 'crossfade';
    value: number;
    track: string;
};
function download(blob: Blob, name: string) { const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function Wave({ source, clip, position, rate, onSeek }: {
    source: Source;
    clip: Clip;
    position: number;
    rate: number;
    onSeek: (v: number) => void;
}) {
    const el = useRef<HTMLDivElement>(null), wave = useRef<WaveSurfer>();
    useEffect(() => {
        let active = true;
        void loadSource(source).then(b => {
            if (!active || !el.current)
                return;
            const all = peaks(b, Math.min(10000, b.length)), first = Math.floor(clip.start / b.duration * all.length), last = Math.ceil(clip.end / b.duration * all.length);
            const data = all.slice(first, last);
            if (clip.reverse)
                data.reverse();
            wave.current = WaveSurfer.create({ container: el.current, height: 60, waveColor: '#81b5cb', progressColor: '#f1ca6c', interact: false, peaks: [data], duration: (clip.end - clip.start) / rate });
        }).catch(() => { });
        return () => { active = false; wave.current?.destroy(); wave.current = undefined; };
    }, [source.url, clip.start, clip.end, clip.reverse, rate]);
    useEffect(() => { wave.current?.setTime(Math.max(0, position - clip.at)); }, [position, clip.at]);
    return <div ref={el} className="jb-wave" onClick={e => onSeek(clip.at + (e.clientX - e.currentTarget.getBoundingClientRect().left) / e.currentTarget.clientWidth * (clip.end - clip.start) / rate)}/>;
}
export default function MusicJukebox({ onAce }: {
    onAce: () => void;
}) {
    const [p, setP] = useState<MusicProject>(fresh), [projects, setProjects] = useState<{
        id: string;
        name: string;
        revision: number;
    }[]>([]), [saved, setSaved] = useState('');
    const [view, setView] = useState<'edit' | 'compose' | 'dj'>('edit'), [selected, setSelected] = useState(''), [clipId, setClip] = useState(''), [noteId, setNote] = useState('');
    const [djActive, setDjActive] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [position, setPosition] = useState(0), [playing, setPlaying] = useState(false), [loop, setLoop] = useState(false), [loopIn, setLoopIn] = useState(0), [loopOut, setLoopOut] = useState(8), [metro, setMetro] = useState(false), [countIn, setCountIn] = useState(false), [snap, setSnap] = useState(true);
    const [past, setPast] = useState<MusicProject[]>([]), [future, setFuture] = useState<MusicProject[]>([]), [clipboard, setClipboard] = useState<Clip | null>(null), [rippleDelete, setRipple] = useState(false);
    const [output, setOutput] = useState(''), [grant, setGrant] = useState(''), [exportName, setExportName] = useState('mix'), [format, setFormat] = useState('wav'), [job, setJob] = useState<Job | null>(null), [previewUrl, setPreviewUrl] = useState(''), [peak, setPeak] = useState(0);
    const [chatSources,setChatSources]=useState<string[]>([]);
    const [message, setMessage] = useState(''), [model, setModel] = useState(false), [conversation, setConversation] = useState<{
        text: string;
        reply: string;
    }[]>([]), [proposal, setProposal] = useState<Proposal | null>(null), [approved, setApproved] = useState(false), [proposalBase, setProposalBase] = useState('');
    const [bar, setBar] = useState(0), [velocity, setVelocity] = useState(.75), [noteLength, setNoteLength] = useState(.25), [video, setVideo] = useState(''), [zoom, setZoom] = useState(50), [pendingAsset, setPendingAsset] = useState<MediaAsset | null>(() => { try {
        return JSON.parse(sessionStorage.getItem('vibe-jukebox-pending-audio') || 'null');
    }
    catch {
        return null;
    } });
    const context = useRef<AudioContext>(), node = useRef<AudioBufferSourceNode>(), started = useRef(0), offset = useRef(0), raf = useRef(0), videoEl = useRef<HTMLVideoElement>(null), latest = useRef(p);
    latest.current = p;
    const file = useRef<HTMLInputElement>(null), folder = useRef<HTMLInputElement>(null), midi = useRef<HTMLInputElement>(null), projectFile = useRef<HTMLInputElement>(null);
    const t = p.tracks.find(t => t.id === selected), c = t?.clips.find(c => c.id === clipId), n = t?.notes.find(n => n.id === noteId);
    const dirty = JSON.stringify(p) !== saved, seconds = length(p), locked = busy || playing || djActive;
    const run = async (fn: () => Promise<unknown>) => { setBusy(true); setError(''); try {
        await fn();
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } };
    const stop = () => { node.current?.stop(); node.current = undefined; cancelAnimationFrame(raf.current); setPlaying(false); videoEl.current?.pause(); };
    const change = (next: MusicProject) => { if(next.tracks.length>24||next.sources.length>32){setError('Project limit: 24 tracks and 32 sources. Remove unused items first.');return;} stop(); setPast(old => [...old.slice(-29), p]); setFuture([]); setP(next); setProposal(null); };
    const editTrack = (value: Partial<Track>) => { if (t)
        change({ ...p, tracks: p.tracks.map(row => row.id === t.id ? { ...t, ...value } : row) }); };
    const quant = (v: number) => snap ? Math.round(v * p.bpm / 60 * 4) / 4 * 60 / p.bpm : v;
    const refresh = async () => { const s = await api<{
        projects: typeof projects;
        output: string;
    }>('state'); setProjects(s.projects); return s; };
    const open = async (id: string) => { stop(); const next = await api<MusicProject>('projects/' + id); let recovered: MusicProject | null = null; try {
        const d = JSON.parse(localStorage.getItem('vibe-jukebox-draft-' + id) || 'null');
        if (d?.revision === next.revision)
            recovered = d;
    }
    catch { /* Use atomic server save. */ } setP(recovered || next); setSaved(JSON.stringify(next)); setPast([]); setFuture([]); setSelected(''); setClip(''); setConversation([]); setProposal(null);setPreviewUrl('');setPosition(0);setJob(null);void api<{jobs:Job[]}>('projects/'+id+'/jobs').then(r=>setJob(r.jobs[0]||null)).catch(e=>setError(e.message)); setNotice(recovered && JSON.stringify(recovered) !== JSON.stringify(next) ? 'Recovered an unsaved browser draft. Save to keep it.' : 'Opened saved project.'); localStorage.setItem('vibe-jukebox-project', id); };
    useEffect(() => { void refresh().then(state => { const id = localStorage.getItem('vibe-jukebox-project'); if (id && state.projects.some(row=>row.id===id))
        void open(id).catch(e => setError(e.message)); else if(id){localStorage.removeItem('vibe-jukebox-project');setNotice('The previous session was removed. Your browser recovery drafts have been kept.');} }).catch(e => setError(e.message)); return () => { node.current?.stop(); cancelAnimationFrame(raf.current); void context.current?.close(); forgetBuffers(); }; }, []);
    useEffect(() => { if (p.id)
        try {
            localStorage.setItem('vibe-jukebox-draft-' + p.id, JSON.stringify(p));
        }
        catch {
            setNotice('Browser draft storage is full. Save this project to the server.');
        } clearUnused(p.sources); }, [p]);
    useEffect(() => { const leave = (e: BeforeUnloadEvent) => { if (dirty && p.id) {
        e.preventDefault();
        e.returnValue = '';
    } }; window.addEventListener('beforeunload', leave); return () => window.removeEventListener('beforeunload', leave); }, [dirty, p.id]);
    useEffect(() => { if (!job || !['queued', 'running', 'cancel_requested'].includes(job.status))
        return; const timer = setInterval(() => void api<Job>('jobs/' + job.job_id).then(j => { setJob(j); if (j.status === 'completed' && j.result)
        setNotice('Validated export: ' + j.result.path); }).catch(e => setError(e.message)), 1000); return () => clearInterval(timer); }, [job?.job_id, job?.status]);
    useEffect(() => () => { if (video)
        URL.revokeObjectURL(video); }, [video]);
    useEffect(() => () => { if (previewUrl)
        URL.revokeObjectURL(previewUrl); }, [previewUrl]);
    const save = async () => { if (!p.id)
        throw Error('Create a named project first.'); const next = await api<MusicProject>('projects/' + p.id + '/save', { project: p, revision: p.revision }); setP(next); setSaved(JSON.stringify(next)); await refresh(); setNotice('Project saved. Source recordings are unchanged.'); return next; };
    const create = async () => { if (p.id && dirty && !confirm('Start a new project? Your browser draft will be retained.'))
        return; const next = await api<MusicProject>('projects', { project: { ...fresh(), name: p.name || 'Untitled jukebox' } }); await nameMediaWorkspace(next.workspace_id, next.name); setP(next); setSaved(JSON.stringify(next)); localStorage.setItem('vibe-jukebox-project', next.id);setPosition(0);setJob(null);setPreviewUrl(''); setPast([]); setFuture([]); await refresh(); };
    const addAssets = async (assets: MediaAsset[]) => { let next = { ...latest.current, sources: [...latest.current.sources], tracks: [...latest.current.tracks] }; for (const a of assets) {
        if (a.kind !== 'audio')
            continue;
        const s: Source = { id: a.asset_id, workspace_id: a.workspace_id, asset_id: a.asset_id, name: a.filename, url: a.content_url, duration: a.media?.duration_seconds || 1 };
        const b = await loadSource(s);
        s.duration = b.duration;
        if (!next.sources.some(row => row.id === s.id))
            next.sources.push(s);
        const row = track('audio', s.name);
        row.clips = [{ id: uid(), source: s.id, at: quant(position), start: 0, end: b.duration }];
        next.tracks.push(row);
        setSelected(row.id);
        setClip(row.clips[0].id);
    } change(next); };
    const importFiles = async (files: File[]) => { if (!p.id)
        throw Error('Create a project before importing.'); const assets = []; for (const f of files.filter(f => /\.(wav|mp3|flac|ogg|m4a|aac|webm)$/i.test(f.name))) {
        if (f.size > 64 * 1024 * 1024)
            throw Error('Each recording must be under 64 MiB.');
        assets.push(await uploadMediaAsset(p.workspace_id, f, 'project_audio'));
    } await addAssets(assets); };
    const buffer = async (only?: string, click = false) => { const b = await renderMusic(p, only, click); let pk = 0; for (let c = 0; c < b.numberOfChannels; c++) {
        const data = b.getChannelData(c);
        for (let i = 0; i < data.length; i++)
            pk = Math.max(pk, Math.abs(data[i]));
    } setPeak(pk); return b; };
    const play = async () => { if (playing) {
        const pos = offset.current + (context.current!.currentTime - started.current);
        stop();
        setPosition(Math.min(seconds, pos));
        return;
    } context.current ??= new AudioContext({ sampleRate: 44100 }); await context.current.resume(); const b = await buffer(undefined, metro); const source = context.current.createBufferSource(); source.buffer = b; source.connect(context.current.destination); if (loop) {
        source.loop = true;
        source.loopStart = loopIn;
        source.loopEnd = Math.min(b.duration, Math.max(loopIn + .05, loopOut));
    } const from = position >= b.duration ? 0 : position; node.current = source; offset.current = from; const delay = countIn ? 4 * 60 / p.bpm : 0; started.current = context.current.currentTime + delay; source.start(started.current, from); setPlaying(true); source.onended = () => { if (node.current === source) {
        videoEl.current?.pause();
        setPlaying(false);
        cancelAnimationFrame(raf.current);
    } }; const tick = () => { let pos = from + Math.max(0, context.current!.currentTime - started.current); if (loop && pos >= loopOut)
        pos = loopIn + (pos - loopIn) % (loopOut - loopIn); setPosition(pos); if (videoEl.current) {
        const target = pos + (p.video?.offset || 0);
        if (Math.abs(videoEl.current.currentTime - target) > .15)
            videoEl.current.currentTime = Math.max(0, target);
        if (videoEl.current.paused)
            void videoEl.current.play().catch(() => { });
    } raf.current = requestAnimationFrame(tick); }; tick(); };
    const exportAudio = async (only?: string) => { stop(); const snapshot = await save(); const b = await buffer(only), response = await fetch(`/api/jukebox/projects/${snapshot.id}/render`, { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav(b) }), staged = await response.json(); if (!response.ok)
        throw Error(staged.error?.message || 'Audio upload failed.'); setJob(await api<Job>('projects/' + snapshot.id + '/export', { token: staged.token, name: exportName + (only ? '_' + (t?.name || 'stem').replace(/[^A-Za-z0-9_-]/g, '_') : ''), format, folder: grant, track_id:only, overwrite: false })); };
    const newTrack = (kind: Track['kind']) => { const row = track(kind, kind === 'audio' ? 'Audio track' : kind); if (kind === 'sample')
        row.sample = p.sources[0]?.id; change({ ...p, tracks: [...p.tracks, row] }); setSelected(row.id); };
    const applyProposal = () => { if (!proposal || JSON.stringify(p) !== proposalBase)
        throw Error('Project changed; request a new proposal.'); let next = { ...p }; if (proposal.action === 'tempo')
        next.bpm = Math.max(30, Math.min(300, proposal.value)); if (proposal.action === 'gain') {
        if (!p.tracks.some(t => t.id === proposal.track))
            throw Error('Choose a valid track.');
        next.tracks = p.tracks.map(t => t.id === proposal.track ? { ...t, gain: Math.max(-60, Math.min(12, proposal.value)) } : t);
    } if (proposal.action === 'house_beat') {
        next.bpm = Math.max(30, Math.min(300, proposal.value));
        next.tracks = [...p.tracks, ...houseBeat(next)];
    } if (proposal.action === 'crossfade')
        next.dj = { ...p.dj, events: [...p.dj.events.filter(e => e.type !== 'cross'), ...Array.from({ length: 101 }, (_, i) => ({ type: 'cross' as const, value: -1 + i / 50, time: i / 100 * Math.max(.1, Math.min(600, proposal.value)) }))] }; change(next); setApproved(false); };
    const num = (label: string, value: number, onChange: (v: number) => void, min: number, max: number, step = 1) => <label key={label}>{label}<input aria-label={label} type="number" value={value} min={min} max={max} step={step} disabled={locked} onChange={e => { const n = Number(e.target.value); if (Number.isFinite(n) && n >= min && n <= max)
        onChange(n); }}/></label>;
    const left = <><section className="card"><h2>Music Director</h2><p>Describe your edit or beat. Review the brief and exact changes before applying.</p><ModelSelector open={model} onClose={() => setModel(false)} returnFocusId="jukebox-message"/><div role="log">{conversation.map((r, i) => <article key={i}><b>You</b><p>{r.text}</p><b>Director</b><p>{r.reply}</p></article>)}</div><div onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();const id=e.dataTransfer.getData('text/jukebox-source');if(p.sources.some(s=>s.id===id))setChatSources(r=>Array.from(new Set([...r,id])));}}>{chatSources.filter(id=>p.sources.some(s=>s.id===id)).map(id=><button key={id} onClick={()=>setChatSources(r=>r.filter(s=>s!==id))}>Remove attachment · {p.sources.find(s=>s.id===id)?.name}</button>)}<small>Attach a source or drag it here to discuss its name and settings. Chat does not listen to or transcribe the recording.</small><label>Message the music Director<textarea id="jukebox-message" value={message} onChange={e => setMessage(consumeModelCommand(e.target.value, () => setModel(true), 'jukebox-message'))}/></label></div><button disabled={busy || !p.id || !message.trim()} onClick={() => void run(async () => { const reply = await api<Proposal>('chat', { text: message, context: {...p,attached_sources:p.sources.filter(s=>chatSources.includes(s.id))} }); setConversation(r => [...r, { text: message, reply: reply.reply }]); setProposal(reply); setProposalBase(JSON.stringify(p)); setApproved(false); setMessage(''); })}>Send</button>{proposal && proposal.action !== 'none' && <section className="jb-proposal"><h3>{approved ? '2. Review exact changes' : '1. Confirm the brief'}</h3><p>{proposal.reply}</p>{approved && <pre>{JSON.stringify({ action: proposal.action, value: proposal.value, track: proposal.track }, null, 2)}</pre>}<button disabled={locked} onClick={() => approved ? void run(async () => applyProposal()) : setApproved(true)}>{approved ? 'Approve and apply changes' : 'Approve brief'}</button><button onClick={() => { setProposal(null); setApproved(false); }}>Cancel proposal</button></section>}</section><details className="card" open><summary>Media & samples</summary>{pendingAsset && <section><p>From ACE-Step: {pendingAsset.filename}</p><button disabled={!p.id || locked} onClick={() => void run(async () => { await addAssets([pendingAsset]); setPendingAsset(null); sessionStorage.removeItem('vibe-jukebox-pending-audio'); })}>Import ACE-Step result</button><button onClick={() => { setPendingAsset(null); sessionStorage.removeItem('vibe-jukebox-pending-audio'); }}>Dismiss</button></section>}<button disabled={!p.id || locked} onClick={() => file.current?.click()}>Import audio files</button><button disabled={!p.id || locked} onClick={() => folder.current?.click()}>Import audio folder</button><input ref={file} type="file" multiple accept="audio/*" hidden onChange={e => void run(() => importFiles(Array.from(e.target.files || [])))}/><input ref={folder} type="file" multiple hidden {...{ webkitdirectory: '' }} onChange={e => void run(() => importFiles(Array.from(e.target.files || [])))}/><MediaSourcePicker workspaceId={p.workspace_id} kinds={['audio']} disabled={!p.id || locked} onAdded={a => void run(() => addAssets(a))}/>{p.sources.map(s => <div className="jb-source" key={s.id} draggable onDragStart={e => e.dataTransfer.setData('text/jukebox-source', s.id)}><span>{s.name} · {s.duration.toFixed(1)}s</span><button onClick={()=>setChatSources(r=>Array.from(new Set([...r,s.id])))}>Attach to chat</button><button disabled={locked} onClick={() => { const row = track('audio', s.name); row.clips = [{ id: uid(), source: s.id, at: quant(position), start: 0, end: s.duration }]; change({ ...p, tracks: [...p.tracks, row] }); setSelected(row.id); }}>Add at playhead</button><button disabled={locked} onClick={() => { if (p.tracks.some(t => t.sample === s.id || t.clips.some(c => c.source === s.id)) || p.dj.events.some(e => e.source === s.id)) {
        setError('Remove clips and captured deck events using this source first.');
        return;
    } change({ ...p, sources: p.sources.filter(r => r.id !== s.id) }); }}>Remove unused source</button></div>)}</details>{p.id && <fieldset className="jb-edit-lock" disabled={locked}><VoiceRecorder purpose="music" workspaceId={p.workspace_id} onSaved={asset => void run(() => addAssets([asset]))}/></fieldset>}<button onClick={onAce}>Generate with ACE-Step</button></>;
    const controls = <div className="jb-controls"><header><h1>Music Jukebox</h1><p>Edit recordings, compose beats and melodies, or capture a DJ mix.</p></header><section className="card"><div className="jb-fields"><label>Music project<select disabled={locked} value={p.id} onChange={e => { if (!dirty || confirm('Discard unsaved changes and open another project?'))
        void run(() => open(e.target.value)); }}><option value="">New project</option>{projects.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label><label>Project name<input value={p.name} disabled={locked} onChange={e => change({ ...p, name: e.target.value })}/></label></div><div className="jb-toolbar"><button disabled={locked} onClick={() => void run(create)}>New named project</button><button disabled={!p.id || locked} onClick={() => void run(save)}>Save project</button><button disabled={!p.id || locked} onClick={() => void run(async () => { const copy = { ...p, id: '', revision: 0, name: p.name + ' copy' }; const next = await api<MusicProject>('projects', { project: copy }); await nameMediaWorkspace(next.workspace_id,next.name);setP(next);setJob(null);setPreviewUrl('');setSaved(JSON.stringify(next));localStorage.setItem('vibe-jukebox-project',next.id);await refresh(); })}>Save as new project</button><button disabled={locked || !past.length} onClick={() => { setFuture(r => [p, ...r]); setP({ ...past[past.length - 1], revision: p.revision }); setPast(r => r.slice(0, -1)); }}>Undo</button><button disabled={locked || !future.length} onClick={() => { setPast(r => [...r, p]); setP({ ...future[0], revision: p.revision }); setFuture(r => r.slice(1)); }}>Redo</button><span>{dirty ? 'Unsaved changes' : 'Saved'} · revision {p.revision}</span></div><details><summary>Project files and recovery</summary><p>Atomic server saves retain 30 checkpoints. Imported recordings are shared media assets. Browser drafts recover unsaved edits on this device.</p><button disabled={!p.id || locked} onClick={() => download(new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' }), `${p.name}.jukebox.json`)}>Download project JSON</button><button disabled={locked} onClick={() => projectFile.current?.click()}>Open project JSON</button><input ref={projectFile} hidden type="file" accept=".json" onChange={e => void run(async () => { const f = e.target.files?.[0]; if (!f || f.size > 2e6)
        throw Error('Choose a project JSON under 2 MB.'); const candidate = JSON.parse(await f.text()); const next = await api<MusicProject>('projects', { project: candidate }); setP(next);setJob(null);setSaved(JSON.stringify(next));localStorage.setItem('vibe-jukebox-project',next.id);await refresh(); })}/><button disabled={!p.id || locked} onClick={() => void run(async () => { await save(); const chosen = await api<{
        grant: string;
    }>('folder', {}); const result = await api<{
        path: string;
    }>('projects/' + p.id + '/copy', { folder: chosen.grant, overwrite: confirm('Allow replacing this project’s JSON if it already exists in the chosen folder?') }); setNotice('Project JSON saved: ' + result.path); })}>Save project JSON to folder</button></details></section>{error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
 <nav className="jb-tabs" aria-label="Jukebox views">{(['edit', 'compose', 'dj'] as const).map(v => <button disabled={busy || djActive} aria-pressed={view === v} key={v} onClick={() => { stop(); setView(v); }}>{v === 'edit' ? 'Edit & Arrange' : v === 'compose' ? 'Compose & Beats' : 'DJ Mix'}</button>)}</nav>
 <section className="card jb-transport"><div className="jb-toolbar"><button disabled={!p.id || busy || djActive} onClick={() => void run(play)}>{playing ? 'Pause' : 'Play'}</button><button onClick={() => { stop(); setPosition(0); }}>Stop</button><output aria-label="Play position">{position.toFixed(2)} s · bar {Math.floor(position * p.bpm / 240) + 1}</output>{num('BPM', p.bpm, v => change({ ...p, bpm: v }), 30, 300)}{num('Bars (4/4)', p.bars, v => change({ ...p, bars: v }), 1, 128)}<label>Playback source<select value={p.mode} disabled={locked} onChange={e => change({ ...p, mode: e.target.value as MusicProject['mode'] })}><option value="arrange">Arrangement</option><option value="dj">Captured DJ performance</option></select></label></div><input aria-label="Playhead" type="range" min={0} max={Math.max(seconds, 1)} step={.01} value={position} disabled={playing} onChange={e => setPosition(Number(e.target.value))}/><div className="jb-toolbar"><label><input type="checkbox" checked={loop} disabled={playing} onChange={e => setLoop(e.target.checked)}/>Loop</label>{num('Loop in', loopIn, setLoopIn, 0, Math.max(0, loopOut - .05), .01)}{num('Loop out', loopOut, setLoopOut, loopIn + .05, 600, .01)}<label><input type="checkbox" checked={metro} disabled={playing} onChange={e => setMetro(e.target.checked)}/>Metronome (preview only)</label><label><input type="checkbox" checked={countIn} onChange={e => setCountIn(e.target.checked)}/>4-beat pre-roll</label><label><input type="checkbox" checked={snap} onChange={e => setSnap(e.target.checked)}/>Snap to 1/16</label></div><small>Playback prepares the processed mix first, using the same rendering graph as export. Pre-roll waits one bar; start microphone recording separately. Formats are stereo 44.1 kHz, up to 10 minutes.</small></section>
 {view === 'dj' ? <fieldset className="jb-edit-lock" disabled={busy||playing||!p.id}><JukeboxDJ key={p.id} project={p} onChange={change} onActivity={setDjActive}/></fieldset> : <fieldset className="jb-edit-lock" disabled={locked}><section className="card"><div className="jb-toolbar"><button disabled={!p.id || locked} onClick={() => newTrack('audio')}>Add audio track</button>{view === 'compose' && <><button disabled={!p.id || locked} onClick={() => newTrack('synth')}>Add synth</button><button disabled={!p.id || locked} onClick={() => change({ ...p, tracks: [...p.tracks, ...houseBeat(p)] })}>Add house drum pattern</button><button disabled={!p.id || locked || !p.sources.length} onClick={() => newTrack('sample')}>Add sampler</button><button disabled={locked} onClick={() => midi.current?.click()}>Import MIDI</button><button disabled={!p.tracks.some(t => t.notes.length)} onClick={() => download(midiExport(p), p.name + '.mid')}>Export MIDI</button><input ref={midi} hidden type="file" accept=".mid,.midi" onChange={e => void run(async () => { const f = e.target.files?.[0]; if (!f || f.size > 2e6)
            throw Error('Choose MIDI under 2 MB.'); const imported = midiImport(await f.arrayBuffer()); change({ ...p, bpm: imported.bpm, tracks: [...p.tracks, ...imported.tracks] }); })}/></>}</div><label>Timeline zoom<input aria-label="Timeline zoom" type="range" min={10} max={150} value={zoom} onChange={e => setZoom(Number(e.target.value))}/></label><div className="jb-arrangement" aria-label="Audio arrangement" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault();if(locked)return; const s = p.sources.find(s => s.id === e.dataTransfer.getData('text/jukebox-source')); if (s) {
            const r = track('audio', s.name);
            r.clips = [{ id: uid(), source: s.id, at: quant(position), start: 0, end: s.duration }];
            change({ ...p, tracks: [...p.tracks, r] });
        }
        else if (e.dataTransfer.files.length)
            void run(() => importFiles(Array.from(e.dataTransfer.files))); }}>{!p.tracks.length && <p>Import or drop audio here, record a take, or add a drum pattern.</p>}{p.tracks.map(row => <section className={'jb-track ' + (t?.id === row.id ? 'selected' : '')} key={row.id}><div className="jb-track-header"><button onClick={() => { setSelected(row.id); setClip(row.clips[0]?.id || ''); }}>{row.name}</button><small>{row.kind}</small><button aria-pressed={row.mute} onClick={() => change({ ...p, tracks: p.tracks.map(t => t.id === row.id ? { ...t, mute: !t.mute } : t) })}>Mute</button><button aria-pressed={row.solo} onClick={() => change({ ...p, tracks: p.tracks.map(t => t.id === row.id ? { ...t, solo: !t.solo } : t) })}>Solo</button></div><div className="jb-timeline-scroll"><div className="jb-ruler" style={{ width: Math.max(600, seconds * zoom) }}>{Array.from({ length: Math.ceil(seconds / 5) }, (_, i) => <span key={i} style={{ left: i * 5 * zoom }}>{i * 5}s</span>)}</div><div className="jb-clips" style={{ width: Math.max(600, seconds * zoom) }} onDragOver={e => e.preventDefault()} onDrop={e => {if(locked)return; const raw = e.dataTransfer.getData('text/jukebox-clip'); if (!raw)
            return; e.preventDefault(); e.stopPropagation(); const moved = JSON.parse(raw) as {
            track: string;
            clip: Clip;
        }; const at = quant(Math.max(0, (e.clientX - e.currentTarget.getBoundingClientRect().left) / zoom)); change({ ...p, tracks: p.tracks.map(tr => ({ ...tr, clips: [...tr.clips.filter(c => !(tr.id === moved.track && c.id === moved.clip.id)), ...(tr.id === row.id ? [{ ...moved.clip, at }] : [])] })) }); }}>{row.clips.map(clip => <button className={'jb-clip ' + (clip.id === clipId ? 'selected' : '')} key={clip.id} style={{ left: clip.at * zoom, width: Math.max(24, (clip.end - clip.start) / row.rate * zoom) }} draggable onDragStart={e => e.dataTransfer.setData('text/jukebox-clip', JSON.stringify({ track: row.id, clip }))} onClick={() => { setSelected(row.id); setClip(clip.id); }}><span>{clip.at.toFixed(2)}s → {(clip.at + (clip.end - clip.start) / row.rate).toFixed(2)}s · {p.sources.find(s => s.id === clip.source)?.name}</span>{p.sources.find(s => s.id === clip.source) && <Wave source={p.sources.find(s => s.id === clip.source)!} clip={clip} rate={row.rate} position={position} onSeek={v => { if (!playing)
            setPosition(quant(v)); }}/>}</button>)}{row.notes.length > 0 && <button className="jb-pattern" onClick={() => setSelected(row.id)}>{row.notes.length} notes · {p.bars} bars</button>}<i className="jb-playhead" style={{ left: position * zoom }}/></div></div></section>)}</div></section>
 {view === 'compose' && t && t.kind !== 'audio' && <section className="card"><h2>{t.kind === 'kick' || t.kind === 'snare' || t.kind === 'hat' ? 'Step sequencer' : 'Piano roll'} · {t.name}</h2><div className="jb-fields">{num('Edit bar', bar + 1, v => setBar(v - 1), 1, p.bars)}{num('Note length (beats)', noteLength, setNoteLength, .0625, 16, .0625)}{num('Velocity', velocity, setVelocity, .01, 1, .05)}{num('Swing', p.swing, v => change({ ...p, swing: v }), 0, .75, .05)}<label>Instrument<select value={t.kind} onChange={e => editTrack({ kind: e.target.value as Track['kind'] })}>{['synth', 'bass', 'kick', 'snare', 'hat', 'sample'].map(k => <option key={k}>{k}</option>)}</select></label>{t.kind === 'sample' && <label>Sampler source<select value={t.sample || ''} onChange={e => editTrack({ sample: e.target.value })}>{p.sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>}</div><div className="jb-piano" role="group" aria-label="Piano roll grid">{(t.kind === 'synth' || t.kind === 'bass' || t.kind === 'sample' ? Array.from({ length: 25 }, (_, i) => 72 - i) : [t.kind === 'kick' ? 36 : t.kind === 'snare' ? 38 : 42]).map(m => <div className="jb-note-row" key={m}><span>{['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'][m % 12]}{Math.floor(m / 12) - 1}</span>{Array.from({ length: 16 }, (_, i) => { const beat = bar * 4 + i / 4, note = t.notes.find(n => n.midi === m && Math.abs(n.beat - beat) < .01); return <button key={i} aria-label={`Note ${m} step ${i + 1}`} aria-pressed={!!note} onClick={() => { if (note) {
            setNote(note.id);
        }
        else {
            const n = { id: uid(), beat, length: noteLength, midi: m, velocity };
            editTrack({ notes: [...t.notes, n] });
            setNote(n.id);
        } }} onContextMenu={e => { e.preventDefault(); if (note)
            editTrack({ notes: t.notes.filter(n => n.id !== note.id) }); }}>{note ? '●' : '·'}</button>; })}</div>)}</div><button onClick={() => editTrack({ notes: [...t.notes, ...t.notes.filter(n => n.beat >= bar * 4 && n.beat < (bar + 1) * 4).map(n => ({ ...n, id: uid(), beat: n.beat + 4 }))] })}>Duplicate bar</button><button onClick={() => editTrack({ notes: t.notes.map(n => ({ ...n, beat: Math.round(n.beat * 4) / 4 })) })}>Quantize to 1/16</button>{n && <div className="jb-fields">{(['beat', 'length', 'midi', 'velocity'] as const).map(key => num('Note ' + key, n[key], value => editTrack({ notes: t.notes.map(row => row.id === n.id ? { ...n, [key]: value } : row) }), key === 'velocity' ? .01 : key === 'length' ? .0625 : 0, key === 'velocity' ? 1 : key === 'midi' ? 127 : 512, key === 'midi' ? 1 : .0625))}<button onClick={() => editTrack({ notes: t.notes.filter(row => row.id !== n.id) })}>Delete note</button></div>}<small>Click an empty cell to add; click a note to resize/move/change velocity below. Right-click deletes. No external sample bank is downloaded.</small></section>}
 {t && <details className="card" open><summary>Selected track / clip</summary><label>Track name<input value={t.name} disabled={locked} onChange={e => editTrack({ name: e.target.value })}/></label>{c && <><div className="jb-fields">{num('Clip position (seconds)', c.at, v => editTrack({ clips: t.clips.map(r => r.id === c.id ? { ...c, at: quant(v) } : r) }), 0, 600, .001)}{num('Source in (seconds)', c.start, v => editTrack({ clips: t.clips.map(r => r.id === c.id ? { ...c, start: v } : r) }), 0, c.end - .001, .001)}{num('Source out (seconds)', c.end, v => editTrack({ clips: t.clips.map(r => r.id === c.id ? { ...c, end: v } : r) }), c.start + .001, p.sources.find(s => s.id === c.source)?.duration || 600, .001)}</div><div className="jb-toolbar"><button onClick={() => editTrack({ clips: t.clips.flatMap(r => r.id === c.id ? splitClip(c, position, t.rate) : [r]) })}>Split at playhead</button><button onClick={() => { setClipboard({ ...c }); setNotice('Clip copied. Seek, then paste.'); }}>Copy clip</button><button onClick={() => { setClipboard({ ...c }); editTrack({ clips: rippleDelete ? ripple(t.clips, c, t.rate) : t.clips.filter(r => r.id !== c.id) }); }}>Cut clip</button><button onClick={() => editTrack({ clips: [...t.clips, { ...c, id: uid(), at: c.at + (c.end - c.start) / t.rate }] })}>Duplicate clip</button><button onClick={() => editTrack({ clips: rippleDelete ? ripple(t.clips, c, t.rate) : t.clips.filter(r => r.id !== c.id) })}>Delete clip</button><button onClick={() => editTrack({ clips: t.clips.map(r => r.id === c.id ? { ...c, reverse: !c.reverse } : r) })}>{c.reverse ? 'Restore direction' : 'Reverse clip'}</button></div></>}<button disabled={!clipboard} onClick={() => clipboard && editTrack({ clips: [...t.clips, { ...clipboard, id: uid(), at: quant(position) }] })}>Paste at playhead</button><label><input type="checkbox" checked={rippleDelete} onChange={e => setRipple(e.target.checked)}/>Ripple cut/delete (close the gap)</label><button onClick={() => editTrack({ gain: -60 })}>Silence track</button><button onClick={() => { if (confirm('Remove this track from the arrangement? Source recordings will be kept.'))
            change({ ...p, tracks: p.tracks.filter(r => r.id !== t.id) }); }}>Remove track</button></details>}
 </fieldset>}
 <fieldset className="jb-edit-lock" disabled={locked}><details className="card" open><summary>Mixer & effects</summary><div className="jb-fields">{num('Master gain (dB)', p.master, v => change({ ...p, master: v }), -60, 6, .5)}<label><input type="checkbox" checked={p.limiter} onChange={e => change({ ...p, limiter: e.target.checked })}/>Master compressor / peak protection</label><output>Last render peak: {peak ? (20 * Math.log10(peak)).toFixed(1) + ' dBFS' : '—'} {peak > 1 ? '⚠ Clipping: reduce gain before export' : ''}</output></div>{t && <><div className="jb-fields">{(['gain', 'pan', 'low', 'mid', 'high', 'echo', 'reverb', 'fadeIn', 'fadeOut', 'rate', 'pitch'] as const).map(key => num(key === 'gain' ? 'Track gain (dB)' : key === 'rate' ? 'Speed (time stretch)' : key === 'pitch' ? 'Pitch (semitones)' : key, t[key], v => editTrack({ [key]: v }), key === 'gain' ? -60 : key === 'pan' ? -1 : ['low', 'mid', 'high'].includes(key) ? -24 : key === 'rate' ? .25 : key === 'pitch' ? -12 : 0, key === 'gain' ? 12 : key === 'pan' ? 1 : ['low', 'mid', 'high'].includes(key) ? 24 : key === 'rate' ? 4 : key === 'pitch' ? 12 : key === 'echo' ? .8 : key === 'reverb' ? 1 : 60, key === 'pitch' ? 1 : .05))}</div><label><input type="checkbox" checked={t.compress} onChange={e => editTrack({ compress: e.target.checked })}/>Channel compressor</label><div className="jb-toolbar"><button onClick={() => void run(async () => { if (!t.clips.length)
        throw Error('Normalize an audio track first.'); const rendered = await renderMusic({ ...p, master: 0, limiter: false, tracks: p.tracks.map(row => ({ ...row, mute: false, solo: false, gain: row.id === t.id ? 0 : row.gain })) }, t.id); let max = 0; for (let c = 0; c < rendered.numberOfChannels; c++)
        for (const v of rendered.getChannelData(c))
            max = Math.max(max, Math.abs(v)); if (!max)
        throw Error('This track is silent.'); editTrack({ gain: Math.max(-60, Math.min(12, -1 - 20 * Math.log10(max))) }); })}>Normalize track to −1 dBFS</button><button onClick={() => editTrack({ low: 0, mid: 0, high: 0, echo: 0, reverb: 0, compress: false, fadeIn: 0, fadeOut: 0, rate: 1, pitch: 0 })}>Reset track effects</button><button onClick={() => editTrack({ automation: [...t.automation, { time: position, gain: t.gain, pan: t.pan }].sort((a, b) => a.time - b.time) })}>Add gain/pan automation at playhead</button><button onClick={() => editTrack({ automation: [] })}>Clear automation</button></div>{t.automation.map((a, i) => <p key={i}>{a.time.toFixed(2)}s · {a.gain} dB · pan {a.pan}<button onClick={() => editTrack({ automation: t.automation.filter((_, n) => n !== i) })}>Remove point</button></p>)}<small>Fades apply across the arrangement duration. Pitch shifting uses granular processing; preview before exporting.</small></>}</details></fieldset>
 <details className="card"><summary>Linked video preview</summary><input type="file" accept="video/*" onChange={e => { const f = e.target.files?.[0]; if (f) {
        if (video)
            URL.revokeObjectURL(video);
        setVideo(URL.createObjectURL(f));
    } }}/><p>Local video is preview-only and must be chosen again after reopening. Export creates audio; attaching it in Vibe Editor requires your approval.</p>{video && <video ref={videoEl} src={video} muted controls/>}{num('Video offset seconds', p.video?.offset || 0, v => change({ ...p, video: { url: '', offset: v } }), -600, 600, .01)}</details>
 <details className="card" open><summary>Export audio</summary><div className="jb-fields"><label>Output filename<input value={exportName} onChange={e => setExportName(e.target.value)}/></label><label>Format<select value={format} onChange={e => setFormat(e.target.value)}>{['wav', 'mp3', 'flac'].map(f => <option key={f}>{f}</option>)}</select></label><label>Output folder<input value={output} placeholder="Default: local_data/music_jukebox/output/project" onChange={e => { setOutput(e.target.value); setGrant(''); }}/></label></div><button disabled={busy} onClick={() => void run(async () => { const f = await api<{
        path: string;
        grant: string;
    }>('folder', {}); setOutput(f.path); setGrant(f.grant); })}>Choose export folder</button><button disabled={busy || !output} onClick={() => void run(async () => { const f = await api<{
        path: string;
        grant: string;
    }>('folder', { path: output }); setOutput(f.path); setGrant(f.grant); })}>Confirm entered folder</button><button disabled={!p.id || locked || !!output && !grant || !!job && ['queued', 'running'].includes(job.status)} onClick={() => void run(() => exportAudio())}>Export mix</button><button disabled={!t || locked || !!output && !grant || p.mode === 'dj'} onClick={() => void run(() => exportAudio(t?.id))}>Export selected track stem</button><button disabled={!p.id || locked} onClick={() => void run(async () => { const b = await buffer(); setPreviewUrl(URL.createObjectURL(wav(b))); })}>Prepare rendered preview</button>{previewUrl && <audio controls src={previewUrl}/>}<p>Export uses the same processed arrangement as playback, without the metronome. Existing files are protected.</p>{job && <section><p role="status">{job.status} · {job.error || job.message}</p>{['queued', 'running'].includes(job.status) && <button onClick={() => void run(async () => setJob(await api<Job>('jobs/' + job.job_id + '/cancel', {})))}>Cancel export</button>}{job.status === 'failed' && <button onClick={() => void run(async () => { if (!confirm('Overwrite the named output file if it exists?'))
        return; const s = await save(), b = await buffer(job.request?.track_id); const response = await fetch(`/api/jukebox/projects/${s.id}/render`, { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav(b) }), stage = await response.json(); if (!response.ok)
        throw Error(stage.error?.message); setJob(await api<Job>('projects/' + s.id + '/export', { token: stage.token, name: job.request?.name || exportName, format:job.request?.format || format, folder:job.request?.folder || grant, track_id:job.request?.track_id, overwrite: true })); })}>Confirm overwrite and retry</button>}{job.result && <><audio controls src={job.result.url}/><a href={job.result.url} download={job.result.name}>Download {job.result.name}</a><button onClick={() => void run(async () => { const r = await fetch(job.result!.url); if (!r.ok)
        throw Error('Export is missing.'); const asset = await uploadMediaAsset(p.workspace_id, new File([await r.blob()], job.result!.name, { type: job.result!.name.endsWith('.mp3') ? 'audio/mpeg' : job.result!.name.endsWith('.flac') ? 'audio/flac' : 'audio/wav' }), 'project_audio'); sessionStorage.setItem('vibe-editor-pending-audio', JSON.stringify({ workspace_id: p.workspace_id, asset })); location.hash = '#/editor'; })}>Copy export to library and open Vibe Editor</button><small>This explicit handoff makes a library copy. The editor previews it before you choose soundtrack replacement.</small></>}</section>}</details></div>;
    return <div className="music-jukebox"><EditorWorkspace initialWidth={65} name="music-jukebox" rightLabel="music controls" preview={controls}>{left}</EditorWorkspace></div>;
}
