import ProviderStatus from './ProviderStatus';
import { useEffect, useId, useRef, useState } from 'react';

export type DirectorSettingsValue = { provider: string; model: string; reasoning_effort: string; lessons: string[]; revision: number };
export type DirectorCatalog = { settings: DirectorSettingsValue; models: Array<{ provider?: string; id: string; label: string; efforts: string[]; default_effort: string; available?: boolean }>; providers?: Array<{ id: string; label: string; available: boolean; note?: string }> };
let catalogRequest: Promise<DirectorCatalog> | undefined;
export function loadDirectorCatalog(refresh = false): Promise<DirectorCatalog> {
  if (!catalogRequest || refresh) catalogRequest = fetch('/api/director/settings').then(async response => {
    const value = await response.json();
    if (!response.ok) throw new Error(value.error?.message || 'Model settings unavailable.');
    return value;
  }).catch(error => { catalogRequest = undefined; throw error; });
  return catalogRequest;
}
export function directorSettingsChanged() {
  catalogRequest = undefined;
  window.dispatchEvent(new Event('director-model-changed'));
}
export function consumeModelCommand(value: string, open: () => void, inputId?: string): string {
  if (/(?:^|\s)\/status\s*$/.test(value)) { window.dispatchEvent(new CustomEvent("director-status", {detail: inputId})); return value.replace(/\/status\s*$/, ""); }
  if (/(?:^|\s)\/model\s*$/.test(value)) { open(); return value.replace(/\/model\s*$/, ''); }
  return value;
}
const key = (model: { provider?: string; id: string }) => JSON.stringify([model.provider || 'codex', model.id]);

export default function ModelSelector({ open: requestedOpen = false, onClose, disabled = false, returnFocusId }: { open?: boolean; onClose?: () => void; disabled?: boolean; returnFocusId?: string }) {
  const [catalog, setCatalog] = useState<DirectorCatalog | null>(null), [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(''), [effort, setEffort] = useState(''), [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const root = useRef<HTMLDivElement>(null), trigger = useRef<HTMLButtonElement>(null), search = useRef<HTMLInputElement>(null);
  const id = useId();
  const [statusOpen,setStatusOpen] = useState(false);
  useEffect(()=>{const show=(event:Event)=>{if(returnFocusId && (event as CustomEvent).detail===returnFocusId)setStatusOpen(true);};window.addEventListener('director-status',show);return()=>window.removeEventListener('director-status',show);},[returnFocusId]);
  const load = async (refresh = false) => { try { const value = await loadDirectorCatalog(refresh); setCatalog(value); setSelected(key({ provider: value.settings.provider, id: value.settings.model })); setEffort(value.settings.reasoning_effort); setError(''); } catch (e) { setError((e as Error).message); } };
  useEffect(() => { void load(); const changed = () => void load(); window.addEventListener('director-model-changed', changed); return () => window.removeEventListener('director-model-changed', changed); }, []);
  useEffect(() => { if (requestedOpen) setOpen(true); }, [requestedOpen]);
  const close = () => { setOpen(false); onClose?.(); if (returnFocusId) document.getElementById(returnFocusId)?.focus(); else trigger.current?.focus(); };
  useEffect(() => {
    if (!open) return;
    search.current?.focus();
    const pointer = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) { setOpen(false); onClose?.(); } };
    document.addEventListener('pointerdown', pointer); return () => document.removeEventListener('pointerdown', pointer);
  }, [open]);
  const model = catalog?.models.find(item => key(item) === selected);
  const save = async () => {
    if (!catalog || !model || busy) return;
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/director/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: model.provider || 'codex', model: model.id, reasoning_effort: effort, lessons: catalog.settings.lessons, revision: catalog.settings.revision }) });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error?.message || 'Could not save model. Refresh and retry.');
      directorSettingsChanged(); close();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const providers = catalog?.providers || [{ id: 'codex', label: 'Codex', available: true }];
  return <div className="model-selector" ref={root} onKeyDown={e => { if (e.key === 'Escape' && open) { e.stopPropagation(); close(); } }}>
    <button ref={trigger} type="button" className="quiet-button" aria-haspopup="dialog" aria-expanded={open} disabled={disabled || busy} onClick={() => { setQuery(''); setOpen(!open); if (!catalog) void load(true); }}>Model: {catalog ? `${catalog.settings.provider} / ${catalog.settings.model}` : 'Choose…'} ▾</button>
    {open && <section className="model-picker" role="dialog" aria-labelledby={id} onKeyDown={e => { if (e.key === 'Enter' && (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement)) { e.preventDefault(); e.stopPropagation(); } }}>
      <strong id={id}>Choose Director model</strong><button type="button" className="text-button" onClick={close}>Close</button>
      <label>Search models<input ref={search} value={query} onChange={e => setQuery(e.target.value)} placeholder="GPT, Qwen, provider…" /></label>
      <label>Available models<select size={8} value={selected} disabled={busy || disabled} onChange={e => { setSelected(e.target.value); const item = catalog?.models.find(m => key(m) === e.target.value); if (item) setEffort(item.efforts.includes(effort) ? effort : item.default_effort); }}>{providers.map(provider => <optgroup key={provider.id} label={provider.label}>{catalog?.models.filter(item => (item.provider || 'codex') === provider.id && `${item.label} ${item.id} ${provider.label}`.toLowerCase().includes(query.toLowerCase())).map(item => <option key={key(item)} value={key(item)} disabled={item.available === false}>{item.label}{item.available === false ? ' · offline' : ''}</option>)}</optgroup>)}</select></label>
      {model && model.efforts.length > 1 && <label>Reasoning depth<select value={effort} disabled={busy || disabled} onChange={e => setEffort(e.target.value)}>{model.efforts.map(level => <option key={level}>{level}</option>)}</select></label>}
      <small>Shared across pages. Applies to new requests; running work keeps its current request.</small>
      <details><summary>Provider connections</summary>{providers.map(provider => <p key={provider.id}><b>{provider.label}</b>: {provider.available ? 'Model catalog available' : 'Unavailable'}. {provider.note}</p>)}<p>OpenCode API keys stay in OpenCode’s own connection settings. Run <code>opencode auth login</code> to connect a provider, then refresh. No keys are stored in browser drafts.</p></details>
      <div className="model-picker-actions"><button type="button" className="generate-button" disabled={busy || disabled || !model || model.available === false} onClick={() => void save()}>{busy ? 'Saving…' : 'Use model'}</button><button type="button" className="quiet-button" disabled={busy} onClick={() => void load(true)}>Refresh</button></div>
      {error && <p role="alert">{error}</p>}
    </section>}
    {returnFocusId && <button type="button" className="text-button" onClick={()=>setStatusOpen(!statusOpen)} aria-expanded={statusOpen}>/status</button>}
    {statusOpen && <ProviderStatus onClose={()=>{setStatusOpen(false);if(returnFocusId)document.getElementById(returnFocusId)?.focus();}}/>}
    {!open && error && <small role="alert">{error}</small>}
  </div>;
}
