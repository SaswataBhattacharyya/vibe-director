import * as Tone from 'tone';
import { Midi } from '@tonejs/midi';
export type Source = {
    id: string;
    workspace_id: string;
    asset_id: string;
    name: string;
    url: string;
    duration: number;
};
export type Clip = {
    id: string;
    source: string;
    at: number;
    start: number;
    end: number;
    reverse?: boolean;
};
export type Note = {
    id: string;
    beat: number;
    length: number;
    midi: number;
    velocity: number;
};
export type Track = {
    id: string;
    name: string;
    kind: 'audio' | 'synth' | 'bass' | 'kick' | 'snare' | 'hat' | 'sample';
    sample?: string;
    gain: number;
    pan: number;
    mute: boolean;
    solo: boolean;
    low: number;
    mid: number;
    high: number;
    echo: number;
    reverb: number;
    compress: boolean;
    fadeIn: number;
    fadeOut: number;
    rate: number;
    pitch: number;
    clips: Clip[];
    notes: Note[];
    automation: {
        time: number;
        gain: number;
        pan: number;
    }[];
};
export type DeckEvent = {
    time: number;
    type: 'cross' | 'play' | 'stop' | 'gain' | 'low' | 'mid' | 'high' | 'rate';
    deck?: 'A' | 'B';
    value?: number;
    source?: string;
    offset?: number;
    rate?: number;
    loop?: number;
};
export type MusicProject = {
    version: 1;
    id: string;
    workspace_id: string;
    name: string;
    revision: number;
    bpm: number;
    bars: number;
    master: number;
    limiter: boolean;
    swing: number;
    sources: Source[];
    tracks: Track[];
    dj: {
        cross: number;
        events: DeckEvent[];
    };
    mode: 'arrange' | 'dj';
    video?: {
        url: string;
        offset: number;
    };
};
export const uid = () => crypto.randomUUID();
export const fresh = (): MusicProject => ({ version: 1, id: '', workspace_id: '', name: 'Untitled jukebox', revision: 0, bpm: 120, bars: 4, master: -3, limiter: true, swing: 0, sources: [], tracks: [], dj: { cross: 0, events: [] }, mode: 'arrange' });
export const track = (kind: Track['kind'], name: string): Track => ({ id: uid(), kind, name, gain: -6, pan: 0, mute: false, solo: false, low: 0, mid: 0, high: 0, echo: 0, reverb: 0, compress: false, fadeIn: 0, fadeOut: 0, rate: 1, pitch: 0, clips: [], notes: [], automation: [] });
export const length = (p: MusicProject) => Math.max(p.bars * 4 * 60 / p.bpm, ...p.tracks.flatMap(t => [...t.clips.map(c => c.at + (c.end - c.start) / t.rate), ...t.notes.map(n => (n.beat + n.length) * 60 / p.bpm)]), ...p.dj.events.map(e => e.time + .05));
export const db = (value: number) => Math.pow(10, value / 20);
export function splitClip(c: Clip, at: number, rate = 1): Clip[] { const input = c.start + (at - c.at) * rate; if (at <= c.at || input >= c.end)
    return [c]; if (c.reverse)
    return [{ ...c, start: c.end - (input - c.start) }, { ...c, id: uid(), at, start: c.start, end: c.end - (input - c.start) }]; return [{ ...c, end: input }, { ...c, id: uid(), at, start: input }]; }
export function ripple(clips: Clip[], removed: Clip, rate = 1) { const span = (removed.end - removed.start) / rate; return clips.filter(c => c.id !== removed.id).map(c => ({ ...c, at: c.at >= removed.at + span ? c.at - span : c.at })); }
const buffers = new Map<string, AudioBuffer>();
let decoding: AudioContext | undefined;
export async function loadSource(s: Source) {
    if (buffers.has(s.url))
        return buffers.get(s.url)!;
    decoding ??= new AudioContext({ sampleRate: 44100 });
    const r = await fetch(s.url);
    if (!r.ok)
        throw Error(`Missing source: ${s.name}. Restore the file or relink it.`);
    const bytes = await r.arrayBuffer();
    if (bytes.byteLength > 64 * 1024 * 1024)
        throw Error('Use audio files smaller than 64 MiB.');
    const b = await decoding.decodeAudioData(bytes);
    if (b.duration > 600)
        throw Error('Split recordings longer than 10 minutes before import.');
    const memory = [...buffers.values()].reduce((n, b) => n + b.length * b.numberOfChannels * 4, 0) + b.length * b.numberOfChannels * 4;
    if (memory > 192 * 1024 * 1024)
        throw Error('Decoded audio cache reached 192 MiB. Remove unused sources or use shorter recordings.');
    buffers.set(s.url, b);
    return b;
}
export function clearUnused(sources: Source[]) { const urls = new Set(sources.map(s => s.url)); for (const url of buffers.keys())
    if (!urls.has(url))
        buffers.delete(url); }
export function forgetBuffers() { buffers.clear(); void decoding?.close(); decoding = undefined; }
export function peaks(buffer: AudioBuffer, count = 1200) { const data = buffer.getChannelData(0), result = new Float32Array(count); for (let i = 0; i < count; i++) {
    let v = 0;
    for (let j = Math.floor(i * data.length / count); j < Math.floor((i + 1) * data.length / count); j++)
        v = Math.max(v, Math.abs(data[j]));
    result[i] = v;
} return result; }
function noise(ctx: Tone.OfflineContext, seconds: number) { const b = ctx.createBuffer(1, Math.ceil(seconds * 44100), 44100), data = b.getChannelData(0); let seed = 1492; for (let i = 0; i < data.length; i++) {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    data[i] = (seed / 2147483648 - 1) * (1 - i / data.length);
} return b; }
function channel(ctx: Tone.OfflineContext, t: Track, output: AudioNode, duration: number) {
    const input = ctx.createGain(), gain = ctx.createGain(), pan = ctx.createStereoPanner();
    gain.gain.value = db(t.gain);
    pan.pan.value = t.pan;
    let tail: AudioNode = input;
    for (const [type, hz, val] of [['lowshelf', 200, t.low], ['peaking', 1000, t.mid], ['highshelf', 4000, t.high]] as const) {
        const f = ctx.createBiquadFilter();
        f.type = type;
        f.frequency.value = hz;
        f.gain.value = val;
        tail.connect(f);
        tail = f;
    }
    if (t.compress) {
        const c = ctx.createDynamicsCompressor();
        c.threshold.value = -18;
        c.ratio.value = 4;
        tail.connect(c);
        tail = c;
    }
    if (t.echo) {
        const d = ctx.createDelay(2), wet = ctx.createGain(), fb = ctx.createGain();
        d.delayTime.value = .25;
        wet.gain.value = t.echo;
        fb.gain.value = .3;
        tail.connect(d);
        d.connect(fb);
        fb.connect(d);
        d.connect(wet);
        wet.connect(gain);
    }
    if (t.reverb) {
        const c = ctx.createConvolver(), wet = ctx.createGain();
        c.buffer = noise(ctx, 1.2);
        wet.gain.value = t.reverb * .25;
        tail.connect(c);
        c.connect(wet);
        wet.connect(gain);
    }
    tail.connect(gain);
    gain.connect(pan);
    pan.connect(output);
    for (const p of [...t.automation].sort((a, b) => a.time - b.time)) {
        gain.gain.linearRampToValueAtTime(db(p.gain), p.time);
        pan.pan.linearRampToValueAtTime(p.pan, p.time);
    }
    const fade = ctx.createGain();
    fade.gain.value = t.fadeIn > 0 ? 0 : 1;
    fade.gain.setValueAtTime(t.fadeIn > 0 ? 0 : 1, 0);
    if (t.fadeIn)
        fade.gain.linearRampToValueAtTime(1, Math.min(duration, t.fadeIn));
    if (t.fadeOut) {
        fade.gain.setValueAtTime(1, Math.max(0, duration - t.fadeOut));
        fade.gain.linearRampToValueAtTime(0, duration);
    }
    fade.connect(input);
    return fade;
}
export async function renderMusic(p: MusicProject, only?: string, metronome = false): Promise<AudioBuffer> {
    const duration = length(p) + Math.max(0, ...p.tracks.map(t => t.echo || t.reverb ? 2 : 0));
    if (duration > 600)
        throw Error('Export limit is 10 minutes; shorten the arrangement.');
    for (const source of p.sources)
        await loadSource(source);
    const ctx = new Tone.OfflineContext(2, duration, 44100), master = ctx.createGain();
    master.gain.value = db(p.master);
    if (p.limiter) {
        const l = ctx.createDynamicsCompressor();
        l.threshold.value = -1;
        l.knee.value = 0;
        l.ratio.value = 20;
        l.attack.value = .001;
        l.release.value = .08;
        master.connect(l);
        l.connect(ctx.rawContext.destination);
    }
    else
        master.connect(ctx.rawContext.destination);
    const nodes: {
        dispose: () => unknown;
    }[] = [];
    const play = (id: string, input: AudioNode, at: number, start: number, end: number, rate = 1, reverse = false, pitch = 0, stretch = true) => {
        let b = buffers.get(p.sources.find(s => s.id === id)!.url)!;
        if (reverse) {
            const copy = ctx.createBuffer(b.numberOfChannels, b.length, b.sampleRate);
            for (let c = 0; c < b.numberOfChannels; c++)
                copy.copyToChannel(b.getChannelData(c).slice().reverse(), c);
            const old = start;
            start = b.duration - end;
            end = b.duration - old;
            b = copy;
        }
        if (pitch || stretch && rate !== 1) {
            const grain = new Tone.GrainPlayer({ context: ctx, url: b, playbackRate: rate, detune: pitch * 100, grainSize: .1, overlap: .05 });
            grain.connect(input);
            grain.start(at, start, (end - start) / rate);
            nodes.push(grain);
        }
        else {
            const s = ctx.createBufferSource();
            s.buffer = b;
            s.playbackRate.value = rate;
            s.connect(input);
            s.start(at, start, end - start);
        }
    };
    try {
        if (p.mode === 'dj') {
            const events = [...p.dj.events].sort((a, b) => a.time - b.time), cross = events.filter(e => e.type === 'cross');
            for (const deck of ['A', 'B'] as const) {
                const out = ctx.createGain(), g = ctx.createGain();
                g.gain.value = 1;
                g.connect(out);
                out.connect(master);
                const level = (x: number) => deck === 'A' ? Math.cos((x + 1) * Math.PI / 4) : Math.sin((x + 1) * Math.PI / 4);
                out.gain.setValueAtTime(level(p.dj.cross), 0);
                for (const e of cross)
                    out.gain.setTargetAtTime(level(e.value!), e.time, .015);
                const eqs = new Map<string, BiquadFilterNode>();
                let head: AudioNode = g;
                for (const [key, type, hz] of [['high', 'highshelf', 4000], ['mid', 'peaking', 1000], ['low', 'lowshelf', 200]] as const) {
                    const f = ctx.createBiquadFilter();
                    f.type = type;
                    f.frequency.value = hz;
                    f.connect(head);
                    head = f;
                    eqs.set(key, f);
                }
                const de = events.filter(e => e.deck === deck);
                for (let i = 0; i < de.length; i++) {
                    const e = de[i];
                    if (e.type === 'gain')
                        g.gain.setValueAtTime(db(e.value!), e.time);
                    else if (eqs.has(e.type))
                        eqs.get(e.type)!.gain.setValueAtTime(e.value!, e.time);
                    else if (e.type === 'play') {
                        const b = buffers.get(p.sources.find(s => s.id === e.source)!.url)!;
                        const stop = de.slice(i + 1).find(v => v.type === 'play' || v.type === 'stop')?.time ?? duration;
                        if (e.loop) {
                            const s = ctx.createBufferSource();
                            s.buffer = b;
                            s.playbackRate.value = e.rate!;
                            s.loop = true;
                            s.loopStart = e.offset!;
                            s.loopEnd = Math.min(b.duration, e.offset! + e.loop * 60 / p.bpm);
                            s.connect(head);
                            s.start(e.time, e.offset);
                            s.stop(stop);
                        }
                        else
                            play(e.source!, head, e.time, e.offset!, Math.min(b.duration, e.offset! + (stop - e.time) * e.rate!), e.rate, false, 0, false);
                    }
                }
            }
        }
        else {
            const solos = p.tracks.some(t => t.solo);
            for (const t of p.tracks) {
                if (t.mute || solos && !t.solo || only && only !== t.id)
                    continue;
                const input = channel(ctx, t, master, duration);
                for (const c of t.clips)
                    play(c.source, input, c.at, c.start, c.end, t.rate, c.reverse, t.pitch);
                if (['synth', 'bass'].includes(t.kind)) {
                    const synth = new Tone.PolySynth({ context: ctx, voice: Tone.Synth, options: { oscillator: { type: t.kind === 'bass' ? 'triangle' : 'sine' }, envelope: { attack: .005, decay: .1, sustain: .5, release: .08 } } });
                    synth.connect(input);
                    nodes.push(synth);
                    for (const n of t.notes)
                        synth.triggerAttackRelease(Tone.Frequency(n.midi, 'midi').toFrequency(), n.length * 60 / p.bpm, n.beat * 60 / p.bpm, n.velocity);
                }
                else
                    for (const n of t.notes) {
                        const at = (n.beat + (Math.round(n.beat * 4) % 2 ? p.swing * .25 : 0)) * 60 / p.bpm;
                        if (t.kind === 'sample') {
                            const b = buffers.get(p.sources.find(s => s.id === t.sample)!.url)!;
                            const s = ctx.createBufferSource(), g = ctx.createGain();
                            s.buffer = b;
                            g.gain.value = n.velocity;
                            s.connect(g);
                            g.connect(input);
                            s.start(at, 0, Math.min(b.duration, n.length * 60 / p.bpm));
                        }
                        else if (t.kind !== 'audio') {
                            const g = ctx.createGain();
                            g.connect(input);
                            g.gain.setValueAtTime(n.velocity, at);
                            g.gain.exponentialRampToValueAtTime(.001, at + (t.kind === 'kick' ? .25 : .12));
                            if (t.kind === 'kick') {
                                const o = ctx.createOscillator();
                                o.frequency.setValueAtTime(140, at);
                                o.frequency.exponentialRampToValueAtTime(40, at + .2);
                                o.connect(g);
                                o.start(at);
                                o.stop(at + .3);
                            }
                            else {
                                const s = ctx.createBufferSource(), f = ctx.createBiquadFilter();
                                s.buffer = noise(ctx, .15);
                                f.type = 'highpass';
                                f.frequency.value = t.kind === 'hat' ? 7000 : 1200;
                                s.connect(f);
                                f.connect(g);
                                s.start(at);
                            }
                        }
                    }
            }
        }
        if (metronome)
            for (let beat = 0; beat * 60 / p.bpm < duration; beat++) {
                const o = ctx.createOscillator(), g = ctx.createGain(), at = beat * 60 / p.bpm;
                o.frequency.value = beat % 4 ? 900 : 1400;
                g.gain.setValueAtTime(.1, at);
                g.gain.exponentialRampToValueAtTime(.001, at + .03);
                o.connect(g);
                g.connect(master);
                o.start(at);
                o.stop(at + .04);
            }
        const rendered = await ctx.render();
        return rendered.get()! as AudioBuffer;
    }
    finally {
        nodes.forEach(n => n.dispose());
        await ctx.close();
    }
}
export function wav(b: AudioBuffer) { const data = new ArrayBuffer(44 + b.length * 4), v = new DataView(data); const str = (at: number, s: string) => [...s].forEach((c, i) => v.setUint8(at + i, c.charCodeAt(0))); str(0, 'RIFF'); v.setUint32(4, data.byteLength - 8, true); str(8, 'WAVEfmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 2, true); v.setUint32(24, 44100, true); v.setUint32(28, 176400, true); v.setUint16(32, 4, true); v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, b.length * 4, true); for (let c = 0; c < 2; c++) {
    const d = b.getChannelData(Math.min(c, b.numberOfChannels - 1));
    for (let i = 0; i < b.length; i++)
        v.setInt16(44 + i * 4 + c * 2, Math.max(-32768, Math.min(32767, Math.round(d[i] * 32767))), true);
} return new Blob([data], { type: 'audio/wav' }); }
export function midiExport(p: MusicProject) { const m = new Midi(); m.header.setTempo(p.bpm); for (const t of p.tracks.filter(t => t.notes.length)) {
    const r = m.addTrack();
    r.name = t.name;
    for (const n of t.notes)
        r.addNote({ midi: n.midi, ticks: Math.round(n.beat * m.header.ppq), durationTicks: Math.round(n.length * m.header.ppq), velocity: n.velocity });
} return new Blob([new Uint8Array(m.toArray())], { type: 'audio/midi' }); }
export function midiImport(data: ArrayBuffer) { const m = new Midi(data); if (m.header.tempos.length > 1 || m.header.timeSignatures.some(t => t.timeSignature[0] !== 4 || t.timeSignature[1] !== 4))
    throw Error('This version supports one tempo and 4/4. Convert the MIDI tempo map/time signature before import.'); return { bpm: m.header.tempos[0]?.bpm ?? 120, tracks: m.tracks.filter(t => t.notes.length).map(t => ({ ...track('synth', t.name || 'MIDI instrument'), notes: t.notes.map(n => ({ id: uid(), beat: n.ticks / m.header.ppq, length: n.durationTicks / m.header.ppq, midi: n.midi, velocity: n.velocity })) })) }; }
export function houseBeat(p: MusicProject) { return (['kick', 'snare', 'hat'] as const).map(kind => ({ ...track(kind, kind[0].toUpperCase() + kind.slice(1)), notes: Array.from({ length: p.bars * 16 }, (_, i) => i).filter(i => kind === 'kick' ? i % 4 === 0 : kind === 'snare' ? i % 8 === 4 : i % 2 === 0).map(i => ({ id: uid(), beat: i / 4, length: .25, midi: kind === 'kick' ? 36 : kind === 'snare' ? 38 : 42, velocity: .7 })) })); }
