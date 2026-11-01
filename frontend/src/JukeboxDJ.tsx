import { useEffect, useRef, useState } from 'react';
import { db, DeckEvent, loadSource, MusicProject } from './lib/jukebox-engine';
type Deck = {
    source: string;
    offset: number;
    bpm: number;
    rate: number;
    gain: number;
    low: number;
    mid: number;
    high: number;
    loop: number;
    cue: number;
};
const empty = (): Deck => ({ source: '', offset: 0, bpm: 120, rate: 1, gain: 0, low: 0, mid: 0, high: 0, loop: 0, cue: 0 });
export default function JukeboxDJ({ project, onChange, onActivity }: {
    project: MusicProject;
    onChange: (p: MusicProject) => void;
    onActivity: (active: boolean) => void;
}) {
    const [decks, setDecks] = useState({ A: empty(), B: empty() }), [cross, setCross] = useState(0), [capturing, setCapturing] = useState(false), [playing, setPlaying] = useState({ A: false, B: false }), [error, setError] = useState('');
    const ctx = useRef<AudioContext>(), start = useRef(0), events = useRef<DeckEvent[]>([]), capture = useRef(false), taps = useRef<Record<'A' | 'B', number[]>>({ A: [], B: [] }), started = useRef({ A: 0, B: 0 });
    const nodes = useRef<Partial<Record<'A' | 'B', {
        source: AudioBufferSourceNode;
        gain: GainNode;
        out: GainNode;
        eq: BiquadFilterNode[];
    }>>>({});
    const master = useRef<GainNode>();
    const pending = useRef({A:0,B:0});
    const deckPosition = (id: 'A' | 'B') => { const d = decks[id]; const elapsed = (ctx.current!.currentTime-started.current[id])*d.rate; const duration = nodes.current[id]?.source.buffer?.duration || 600; const span = Math.min(duration-d.offset,d.loop*60/d.bpm); return Math.min(duration, d.offset + (span>0 ? elapsed%span : elapsed)); };
    useEffect(() => { if (!capture.current && !nodes.current.A && !nodes.current.B && ctx.current) { void ctx.current.close();ctx.current=undefined; } },[project.master,project.limiter]);
    const latest = useRef(project);
    latest.current = project;
    const audio = () => { if (!ctx.current) {
        ctx.current = new AudioContext();
        master.current = ctx.current.createGain();
        master.current.gain.value = db(project.master);
        if (project.limiter) {
            const l = ctx.current.createDynamicsCompressor();
            l.threshold.value = -1;
            l.knee.value = 0;
            l.ratio.value = 20;
            l.attack.value = .001;
            l.release.value = .08;
            master.current.connect(l);
            l.connect(ctx.current.destination);
        }
        else
            master.current.connect(ctx.current.destination);
    } return ctx.current; };
    useEffect(() => { onActivity(capturing || playing.A || playing.B); }, [capturing, playing.A, playing.B]);
    const now = () => ctx.current ? ctx.current.currentTime - start.current : 0;
    const event = (e: Omit<DeckEvent, 'time'>) => { if (capture.current)
        events.current.push({ ...e, time: now() }); };
    const halt = (id: 'A' | 'B') => { pending.current[id]++; nodes.current[id]?.source.stop(); delete nodes.current[id]; setPlaying(p => ({ ...p, [id]: false })); event({ type: 'stop', deck: id }); };
    useEffect(() => () => { if (capture.current) {
        const p = latest.current;
        const end = Math.min(600, now());
        try {
            localStorage.setItem('vibe-jukebox-draft-' + p.id, JSON.stringify({ ...p, mode: 'dj', dj: { cross: 0, events: [...events.current, { type: 'stop', deck: 'A', time: end }, { type: 'stop', deck: 'B', time: end }] } }));
        }
        catch { /* Browser draft full. */ }
    } onActivity(false); for (const d of Object.values(nodes.current))
        d?.source.stop(); void ctx.current?.close(); }, []);
    const play = async (id: 'A' | 'B', override?: Deck) => { const ticket=++pending.current[id]; try {
        setError('');
        const deck = override || decks[id], s = project.sources.find(s => s.id === deck.source);
        if (!s)
            throw Error('Choose an audio source for the deck.');
        const ready = audio();
        await ready.resume();
        const b = await loadSource(s);
        if(ticket!==pending.current[id])return;
        if (deck.offset >= b.duration)
            throw Error('Deck position must be before the end of the recording.');
        halt(id);
        const c = ready, source = c.createBufferSource(), gain = c.createGain(), out = c.createGain();
        source.buffer = b;
        source.playbackRate.value = deck.rate;
        source.loop = !!deck.loop;
        source.loopStart = deck.offset;
        source.loopEnd = Math.min(b.duration, deck.offset + deck.loop * 60 / deck.bpm);
        gain.gain.value = db(deck.gain);
        out.gain.value = id === 'A' ? Math.cos((cross + 1) * Math.PI / 4) : Math.sin((cross + 1) * Math.PI / 4);
        let tail: AudioNode = source;
        const eq = ([['lowshelf', 200, deck.low], ['peaking', 1000, deck.mid], ['highshelf', 4000, deck.high]] as const).map(([type, hz, val]) => { const f = c.createBiquadFilter(); f.type = type; f.frequency.value = hz; f.gain.value = val; tail.connect(f); tail = f; return f; });
        tail.connect(gain);
        gain.connect(out);
        out.connect(master.current!);
        nodes.current[id] = { source, gain, out, eq };
        source.start(0, deck.offset);
        started.current[id] = c.currentTime;
        source.onended = () => { if (nodes.current[id]?.source === source) {
            delete nodes.current[id];
            setPlaying(p => ({ ...p, [id]: false }));
        } };
        setPlaying(p => ({ ...p, [id]: true }));
        event({ type: 'play', deck: id, source: deck.source, offset: deck.offset, rate: deck.rate, loop: deck.loop ? deck.loop * project.bpm / deck.bpm : 0 });
    }
    catch (e) {
        setError((e as Error).message);
    } };
    const change = (id: 'A' | 'B', key: keyof Deck, value: number | string) => { if (typeof value === 'number' && (!Number.isFinite(value) || value < (key === 'rate' ? .5 : key === 'bpm' ? 30 : ['gain', 'low', 'mid', 'high'].includes(key) ? -24 : 0) || value > (key === 'rate' ? 2 : key === 'bpm' ? 300 : key === 'offset' || key === 'cue' ? 600 : key === 'loop' ? 64 : 24)))
        return; const next = { ...decks[id], [key]: value }; setDecks(p => ({ ...p, [id]: next })); const n = nodes.current[id]; if (n) {
        if (key === 'gain')
            n.gain.gain.value = db(Number(value));
        if (['low', 'mid', 'high'].includes(key))
            n.eq[['low', 'mid', 'high'].indexOf(key)].gain.value = Number(value);
        if (['rate', 'offset', 'loop'].includes(key)) {
            const offset = key === 'offset' ? Number(value) : deckPosition(id);
            setDecks(p => ({ ...p, [id]: { ...next, offset } }));
            void play(id, { ...next, offset });
        }
    } if (['gain', 'low', 'mid', 'high'].includes(key))
        event({ type: key as 'gain', deck: id, value: Number(value) }); };
    const moveCross = (v: number) => { setCross(v); for (const id of ['A', 'B'] as const) {
        const n = nodes.current[id];
        if (n)
            n.out.gain.setTargetAtTime(id === 'A' ? Math.cos((v + 1) * Math.PI / 4) : Math.sin((v + 1) * Math.PI / 4), ctx.current!.currentTime, .015);
    } event({ type: 'cross', value: v }); };
    useEffect(() => { if (!capturing)
        return; const timer = setTimeout(() => finish(), 599000); return () => clearTimeout(timer); }, [capturing]);
    const finish = () => { halt('A'); halt('B'); capture.current = false; setCapturing(false); onChange({ ...project, mode: 'dj', dj: { cross, events: [...events.current] } }); };
    return <section className="jb-dj"><h2>DJ Mix</h2><p>Load each deck, set its BPM, then play and crossfade. Capture stores a replayable performance. Finish capture before leaving; leaving mid-capture retains a browser recovery draft. Use the common transport after stopping the decks. Tempo currently changes pitch too; independent key-lock and separate headphone routing are unavailable.</p><div className="jb-decks">{(['A', 'B'] as const).map(id => <fieldset key={id}><legend>Deck {id}</legend><label>Track {id}<select value={decks[id].source} disabled={playing[id]} onChange={e => change(id, 'source', e.target.value)}><option value="">Choose audio</option>{project.sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>{(['offset', 'bpm', 'rate', 'gain', 'low', 'mid', 'high', 'loop'] as const).map(k => <label key={k}>{k === 'offset' ? 'Position / seconds' : k === 'rate' ? 'Speed (pitch linked)' : k === 'loop' ? 'Loop beats (0 = off)' : k === 'gain' ? 'Gain dB' : k.toUpperCase()}<input type="number" aria-label={`Deck ${id} ${k}`} min={k === 'rate' ? .5 : k === 'gain' || ['low', 'mid', 'high'].includes(k) ? -24 : 0} max={k === 'rate' ? 2 : k === 'bpm' ? 300 : k === 'offset' ? 600 : k === 'loop' ? 64 : 24} step={k === 'rate' ? .01 : .1} value={decks[id][k]} onChange={e => change(id, k, Number(e.target.value))}/></label>)}<div className="jb-toolbar"><button onClick={() => void play(id)}>Play {id}</button><button onClick={() => halt(id)}>Stop {id}</button><button onClick={() => { const offset = playing[id] ? deckPosition(id) : decks[id].offset; setDecks(p => ({ ...p, [id]: { ...p[id], cue: offset } })); }}>Set cue {id}</button><button onClick={() => { change(id, 'offset', decks[id].cue); if (!playing[id])
        void play(id, { ...decks[id], offset: decks[id].cue }); }}>Cue {id}</button><button onClick={() => { const other = id === 'A' ? 'B' : 'A'; change(id, 'rate', Math.max(.5, Math.min(2, decks[other].bpm * decks[other].rate / decks[id].bpm))); }}>Sync tempo to {id === 'A' ? 'B' : 'A'}</button><button onClick={() => { const t = performance.now(); taps.current[id] = [...taps.current[id].slice(-7), t]; if (taps.current[id].length > 1) {
        const bpm = 60000 * (taps.current[id].length - 1) / (t - taps.current[id][0]);
        if (bpm >= 30 && bpm <= 300)
            change(id, 'bpm', Math.round(bpm));
    } }}>Tap BPM {id}</button></div></fieldset>)}</div><label>Crossfader · A ↔ B<input aria-label="Crossfader" type="range" min={-1} max={1} step={.02} value={cross} onChange={e => moveCross(Number(e.target.value))}/></label><button disabled={capturing} onClick={async () => { halt('A'); halt('B'); const ready = audio(); await ready.resume(); start.current = ready.currentTime; events.current = [{ type: 'cross', time: 0, value: cross }]; capture.current = true; setCapturing(true); for (const id of ['A', 'B'] as const)
        for (const key of ['gain', 'low', 'mid', 'high'] as const)
            event({ type: key, deck: id, value: decks[id][key] }); }}>Capture mix performance</button><button disabled={!capturing} onClick={finish}>Finish capture</button><p role="status">{capturing ? 'Capturing controls — play decks now.' : `${project.dj.events.length} saved performance events. Use the common transport to replay; choose DJ performance for export.`}</p>{error && <p role="alert">{error}</p>}</section>;
}
