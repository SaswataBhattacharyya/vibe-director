import { useEffect, useState } from 'react';
import ModelSelector, { DirectorCatalog, DirectorSettingsValue, directorSettingsChanged, loadDirectorCatalog } from './ModelSelector';

type Settings = DirectorSettingsValue;
type Catalog = DirectorCatalog;
async function request(init?: RequestInit): Promise<Catalog> {
  if (!init) return loadDirectorCatalog(true);
  const response = await fetch('/api/director/settings', init);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error?.message || `Director settings unavailable (${response.status})`);
  return value;
}
export default function DirectorSettings() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [draft, setDraft] = useState<Settings | null>(null);
  const [lesson, setLesson] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const load = async () => { setBusy(true); try { const value = await request(); setCatalog(value); setDraft(value.settings); setMessage(''); } catch (e) { setMessage((e as Error).message); } finally { setBusy(false); } };
  useEffect(() => { void load(); const changed = () => { void loadDirectorCatalog().then(value => { setCatalog(value); setDraft(previous => previous ? { ...value.settings, lessons: previous.lessons } : value.settings); }).catch(e => setMessage(e.message)); }; window.addEventListener('director-model-changed', changed); return () => window.removeEventListener('director-model-changed', changed); }, []);
  const save = async () => {
    if (!draft || busy) return;
    setBusy(true);
    try {
      const lessons = lesson.trim() ? [...draft.lessons, lesson.trim()] : draft.lessons;
      const value = await request({ method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: draft.provider, model: draft.model, reasoning_effort: draft.reasoning_effort, lessons, revision: draft.revision }) });
      setCatalog(value); setDraft(value.settings); directorSettingsChanged(); setLesson(''); setMessage('Saved. Applies to subsequent Director requests.');
    } catch (e) { setMessage((e as Error).message); } finally { setBusy(false); }
  };
  const model = catalog?.models.find(item => item.id === draft?.model && (item.provider || 'codex') === draft?.provider);
  return <section className="director-settings"><h3>Director reasoning & lessons</h3>
    <p>Choose the Director model for new requests. Saved lessons guide future requests without changing existing drafts.</p>
    <ModelSelector/>
    {draft && catalog && <fieldset disabled={busy}>
    <p role="status">Saved Director: {draft.provider} / {draft.model} · {draft.reasoning_effort}</p>
    <h4>Saved lessons ({draft.lessons.length}/30)</h4>
    {draft.lessons.length === 0 && <p>No lessons saved yet. Record a useful correction after reviewing a result.</p>}
    <ul>{draft.lessons.map((text, index) => <li key={index}><span>{text}</span><button type="button" onClick={() => setDraft({ ...draft, lessons: draft.lessons.filter((_, i) => i !== index) })}>Remove lesson {index + 1}</button></li>)}</ul>
    <label>New lesson<textarea value={lesson} maxLength={1000} onChange={e => setLesson(e.target.value)} placeholder="For example: Keep dialogue brief in action scenes; preserve the source’s character motivations." /></label>
    <button type="button" disabled={!model || draft.lessons.length + (lesson.trim() ? 1 : 0) > 30} onClick={() => void save()}>{busy ? 'Saving…' : 'Save Director settings & lessons'}</button></fieldset>}
    <p role="status">{message}</p><button type="button" disabled={busy} onClick={() => void load()}>Reload Director settings</button>
  </section>;
}
