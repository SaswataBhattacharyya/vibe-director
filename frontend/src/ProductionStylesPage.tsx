import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ArrowRight, Check, LoaderCircle, Palette, RefreshCw, Save, Sparkles } from 'lucide-react';
import { DirectorProfile, getStyleCatalog, getStyleSelections, ProductionStyle, publishProductionType, saveStyleSelection, StyleSelection } from './lib/styles-api';

const CONTEXT_KEY = 'vibe-style-setup-context-v1';
const FORM_KEY = 'vibe-style-custom-form-v1';
const guidanceStages = [
  ['story', 'Story guidance'], ['scene_direction', 'Scene direction'], ['image', 'Image guidance'],
  ['audio', 'Audio guidance'], ['video', 'Video guidance'], ['review', 'Review guidance'],
] as const;
type CustomForm = { production_type: string; display_name: string; purpose: string; stages: Record<string,string>; behavior: string; review_priorities: string };
const emptyForm = (): CustomForm => ({ production_type: '', display_name: '', purpose: '', stages: Object.fromEntries(guidanceStages.map(([key]) => [key, ''])), behavior: '', review_priorities: '' });
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

export default function ProductionStylesPage() {
  const [contextId, setContextId] = useState(initialContext);
  const [storageWarning, setStorageWarning] = useState('');
  const [catalog, setCatalog] = useState<ProductionStyle[]>([]);
  const [catalogVersion, setCatalogVersion] = useState('');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [saved, setSaved] = useState<StyleSelection | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [selectionOutcomeUnknown, setSelectionOutcomeUnknown] = useState(false);
  const [publishOutcomeUnknown, setPublishOutcomeUnknown] = useState(false);
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState<CustomForm>(readForm);
  const [formDurable, setFormDurable] = useState(true);
  const [published, setPublished] = useState<ProductionStyle | null>(null);

  const selected = useMemo(() => catalog.find(item => item.style_version_id === selectedVersion) || null, [catalog, selectedVersion]);
  const load = async (context: string) => {
    setLoading(true); setNotice('');
    try {
      const [styles, selections] = await Promise.all([getStyleCatalog(), getStyleSelections(context)]);
      const latest = selections.selections?.at(-1) || null;
      let listed = styles.production_types || [];
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
      setSelectionOutcomeUnknown(false); setPublishOutcomeUnknown(false);
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
  useEffect(() => { try { localStorage.setItem(FORM_KEY, JSON.stringify(form)); setFormDurable(true); } catch { setFormDurable(false); } }, [form]);

  const refresh = () => contextId ? void load(contextId) : setNotice('Setup context is not saved. This browser cannot safely recover a selection.');
  const save = async () => {
    if (!contextId || !selected) return;
    setSaving(true); setNotice('');
    try { const frozen = await saveStyleSelection(contextId, selected.production_type, selected.style_version_id); setSaved(frozen); setSelectedVersion(frozen.style_version_id); setNotice(`Saved ${selected.display_name} · version ${selected.style_version}. Its guidance is frozen in this setup context.`); }
    catch (error) { setSelectionOutcomeUnknown(true); setNotice(`The save response was not confirmed: ${(error as Error).message}. The server may have saved this version. Refresh the catalog and selection before trying another save.`); }
    finally { setSaving(false); }
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

  return <div className="content-wrap styles-content">
    <div className="page-heading styles-heading"><div><div className="eyebrow">STORY WORKFLOW · SETUP</div><h1>Production Type &amp; Style</h1><p>Choose how you want to tell your story.</p></div><button className="quiet-button styles-refresh" type="button" onClick={refresh} disabled={loading}><RefreshCw size={15}/> Refresh catalog</button></div>
    {storageWarning && <div className="notice notice-warn" role="alert">{storageWarning}</div>}
    {notice && <div className="notice styles-notice" role="status">{notice}</div>}
    <section className="card style-context-card"><div><span className="styles-kicker"><Palette size={15}/> PRODUCTION SETUP</span><small>Choose a saved style when creating a story.</small><details><summary>Setup details</summary><code>{contextId || 'not persisted'}</code></details></div>{saved && <div className="pinned-style"><Check size={15}/><span>Saved style<strong>{saved.production_type} · {saved.style_version_id}</strong></span></div>}</section>

    <section className="styles-section" aria-labelledby="catalog-title"><div className="styles-section-heading"><div><span className="styles-kicker">VERSIONED CATALOG {catalogVersion && `· ${catalogVersion}`}</span><h2 id="catalog-title">Choose a production type</h2><p>Choose a type, then save.</p></div></div>
      {loading ? <div className="card styles-loading"><LoaderCircle className="spin" size={18}/> Loading catalog and saved selection…</div> : catalog.length === 0 ? <div className="card styles-empty">Types could not load. Refresh to try again.</div> : <>
        <label className="style-select-label" htmlFor="production-type-select">Production type and version</label>
        <select id="production-type-select" className="style-type-select" value={selectedVersion} onChange={event => setSelectedVersion(event.target.value)} aria-describedby="selection-status"><option value="">Choose a type…</option>{catalog.map(item => <option key={item.style_version_id} value={item.style_version_id}>{item.display_name} · v{item.style_version}{item.custom ? ' · custom' : ''}</option>)}</select>
        <p className="style-selection-note" id="selection-status">{saved ? `Saved selection: ${saved.production_type} · ${saved.style_version_id}. Unsaved changes remain a draft.` : 'No type saved.'}</p>
        <div className="style-catalog-grid">{catalog.map(item => <article key={item.style_version_id} className={`card style-type-card ${selectedVersion===item.style_version_id?'style-type-card-selected':''}`}>
          <div className="style-card-top"><div><span className="styles-kicker">{item.custom?'CUSTOM TYPE':'PRODUCTION TYPE'}</span><h3>{item.display_name}</h3></div><span className="style-version">v{item.style_version}</span></div>
          <p className="style-purpose">{item.director_profile?.purpose || 'Purpose guidance is not present in this catalog version.'}</p>
          <details className="style-guidance"><summary>Direction details</summary><dl>{guidanceStages.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{valueText(item.narrative_guidance?.[key]) || 'No guidance supplied.'}</dd></div>)}</dl><div className="style-profile-block"><h4>Director behavior</h4><ul>{(item.director_profile?.behavior || []).map((entry,index)=><li key={index}>{entry}</li>)}</ul><h4>Review priorities</h4><ul>{(item.director_profile?.review_priorities || []).map((entry,index)=><li key={index}>{entry}</li>)}</ul></div><small className="style-hashes">Style {item.narrative_hash} · Director {item.director_profile_hash}</small></details>
          <button className="quiet-button style-card-select" type="button" onClick={()=>setSelectedVersion(item.style_version_id)} aria-pressed={selectedVersion===item.style_version_id}>{selectedVersion===item.style_version_id?'Selected draft':'Select this version'}</button>
        </article>)}</div>
        {selectionOutcomeUnknown && <p className="styles-outcome-lock" role="alert">Save outcome is unknown. Refresh to confirm before another selection can be saved.</p>}
        <div className="style-save-row"><button className="generate-button" type="button" onClick={save} disabled={!selected || saving || loading || !contextId || Boolean(storageWarning) || selectionOutcomeUnknown}><Save size={15}/>{saving?'Saving selection…':'Save selection'}</button><span>{saved ? `Saved: ${saved.production_type}` : ''}</span></div>
      </>}
    </section>

    <section className="styles-section custom-type-section" aria-labelledby="custom-title"><div className="styles-section-heading"><div><span className="styles-kicker"><Sparkles size={14}/> CUSTOM TYPE</span><h2 id="custom-title">Create a production type</h2><p>Add your own direction. Publish it, then select it to use.</p></div></div>
      {!formDurable && <div className="notice notice-warn" role="alert">Browser storage is unavailable. Your edits remain visible in this tab but are not durable; copy them before leaving.</div>}
      <form className="card custom-type-form" onSubmit={publish}>
        <div className="style-form-grid"><label>Type ID<input value={form.production_type} onChange={event=>update('production_type',event.target.value)} placeholder="e.g. documentary_series" autoComplete="off"/></label><label>Display name<input value={form.display_name} onChange={event=>update('display_name',event.target.value)} placeholder="e.g. Documentary series"/></label></div>
        <label>Director purpose<textarea rows={3} value={form.purpose} onChange={event=>update('purpose',event.target.value)} placeholder="What should this type help the Director produce?"/></label>
        <div className="style-guidance-form"><h3>Stage guidance</h3><div className="style-form-grid">{guidanceStages.map(([key,label])=><label key={key}>{label}<textarea rows={4} value={form.stages[key]} onChange={event=>updateStage(key,event.target.value)} placeholder={`Guidance for ${label.toLowerCase()}…`}/></label>)}</div></div>
        <div className="style-form-grid"><label>Director behavior <small>One behavior per line</small><textarea rows={5} value={form.behavior} onChange={event=>update('behavior',event.target.value)} placeholder={'Preserve the requested point of view\nFavor clear transitions'}/></label><label>Review priorities <small>One priority per line</small><textarea rows={5} value={form.review_priorities} onChange={event=>update('review_priorities',event.target.value)} placeholder={'Check tonal consistency\nReview scene clarity'}/></label></div>
        {publishOutcomeUnknown && <p className="styles-outcome-lock" role="alert">Could not confirm publication. Refresh before trying again.</p>}
        <div className="style-publish-row"><button className="generate-button" type="submit" disabled={publishing || !formDurable || publishOutcomeUnknown}><Sparkles size={15}/>{publishing?'Publishing…':'Publish custom type'}</button><span>{published ? `Last published: ${published.display_name} · v${published.style_version}` : ''}</span></div>
      </form>
    </section>
    <section className="styles-boundary"><p>Media style references and video styling are coming soon.</p><a className="generate-button" href="#/story">Continue to Story <ArrowRight size={15}/></a></section>
  </div>;
}
