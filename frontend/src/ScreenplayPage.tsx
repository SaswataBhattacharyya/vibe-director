import { useEffect, useState } from 'react';
import { RefreshCw, Save, Sparkles } from 'lucide-react';
import { draftStoryScreenplay, getStoryGraph, getStoryScreenplay, getStoryScreenplayRevision, getStoryWorkspace, listStoryScreenplays, saveStoryScreenplay, ScreenplayDraftTask, ScreenplayRevision, ScreenplayRevisionSummary } from './lib/story-api';

const directionKeys = ['camera', 'lighting', 'mood', 'sfx', 'music'] as const;
const pendingKey = (workspace: string, source: string) => `vibe-screenplay-task:${workspace}:${source}`;
export default function ScreenplayPage() {
  const [revision, setRevision] = useState<ScreenplayRevision | null>(null);
  const [history, setHistory] = useState<ScreenplayRevisionSummary[]>([]);
  const [graph, setGraph] = useState<Awaited<ReturnType<typeof getStoryGraph>> | null>(null);
  const [draft, setDraft] = useState<ScreenplayRevision['screenplay'] | null>(null);
  const [sourceId, setSourceId] = useState(''); const [workspaceId, setWorkspaceId] = useState('');
  const [busy, setBusy] = useState(false); const [task, setTask] = useState<ScreenplayDraftTask | null>(null); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const refresh = async () => {
    const id = localStorage.getItem('vibe-story-selected-v1') || '';
    if (!id) { setError('Open a story first to work on its screenplay.'); return; }
    setWorkspaceId(id); setBusy(true); setError('');
    try {
      const workspace = await getStoryWorkspace(id); const source = workspace.current_revision_id || workspace.current_revision?.revision_id;
      if (!source) throw new Error('The story has no saved source revision.'); setSourceId(source);
      const revisions = await listStoryScreenplays(id); setHistory(revisions.items || []);
      try { const value = await getStoryScreenplay(id, source); setRevision(value); setDraft(value.screenplay); }
      catch (e) {
        if ((e as Error & { status?: number }).status !== 404) throw e;
        const latest = revisions.items?.[0];
        if (latest) { const value = await getStoryScreenplayRevision(id, latest.screenplay_revision_id); setRevision(value); setDraft(value.screenplay); }
        else { setRevision(null); setDraft(null); }
      }
      try { setGraph(await getStoryGraph(id, source)); } catch (e) { if ((e as Error & { status?: number }).status === 404) setGraph(null); else throw e; }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  useEffect(() => { void refresh(); }, []);
  const generate = async () => {
    if (!graph || !sourceId) return; setBusy(true); setError('');
    try { const keyName = pendingKey(workspaceId, sourceId); const key = localStorage.getItem(keyName) || crypto.randomUUID(); localStorage.setItem(keyName, key); const result = await draftStoryScreenplay(workspaceId, sourceId, graph.snapshot_id, key); if ('screenplay' in result) { setRevision(result); setDraft(result.screenplay); setHistory((await listStoryScreenplays(workspaceId)).items); setTask(null); localStorage.removeItem(keyName); setNotice(`Draft saved. ${result.chunk_complete}/${result.chunk_total} source chunks planned; semantic coverage still needs review.`); } else { setTask(result); setNotice(`${result.chunk_complete}/${result.chunk_total} chunks planned. Select Continue draft to resume this saved task.`); } }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const save = async () => {
    if (!revision || !draft) return; setBusy(true); setError('');
    try { const result = await saveStoryScreenplay(workspaceId, revision.screenplay_revision_id, draft, crypto.randomUUID()); setRevision(result); setDraft(result.screenplay); setHistory((await listStoryScreenplays(workspaceId)).items); setNotice('Edit saved as a new screenplay revision; the prior version remains available in history.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const selectHistory = async (id: string) => {
    setBusy(true); setError('');
    try { const value = await getStoryScreenplayRevision(workspaceId, id); setRevision(value); setDraft(value.screenplay); setNotice('Viewing saved screenplay revision.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const stale = !!revision && revision.source_revision_id !== sourceId;
  const latestForSource = !!revision && history.find(item => item.source_revision_id === revision.source_revision_id)?.screenplay_revision_id === revision.screenplay_revision_id;
  const update = (sceneIndex: number, shotIndex: number, field: string, value: string) => setDraft(current => current && ({ ...current, scenes: current.scenes.map((scene, si) => si !== sceneIndex ? scene : { ...scene, shots: scene.shots.map((shot, hi) => hi !== shotIndex ? shot : field.startsWith('direction.') ? { ...shot, direction: { ...shot.direction, [field.slice(10)]: value } } : { ...shot, [field]: value }) }) }));
  return <main className="content-wrap story-content"><div className="page-heading"><div><div className="eyebrow">SOURCE-LINKED DRAFT</div><h1>Screenplay</h1><p>{sourceId ? `Source revision ${sourceId}` : 'Open a saved story to begin.'}</p></div><button className="quiet-button" onClick={() => void refresh()} disabled={busy}><RefreshCw size={15}/> Reload</button></div>
    {error && <div className="error-banner" role="alert">{error}</div>}{notice && <p role="status">{notice}</p>}
    <section className="card story-graph"><div className="story-panel-title"><div><h2>Readable screenplay</h2><p>{revision ? `Screenplay revision ${revision.screenplay_revision_id} · graph ${revision.graph_snapshot_id}` : 'Draft scenes from the accepted source graph.'}</p></div><div className="story-editor-actions"><button className="generate-button" onClick={() => void generate()} disabled={busy || graph?.status !== 'complete'}><Sparkles size={15}/> {task ? 'Continue draft' : revision ? 'Generate new revision' : 'Generate draft'}</button>{revision && <button className="quiet-button" onClick={() => void save()} disabled={busy || stale || !latestForSource}><Save size={15}/> Save edits</button>}</div></div>
      {history.length > 0 && <label className="screenplay-history">Saved revisions <select aria-label="Saved screenplay revisions" value={revision?.screenplay_revision_id || ''} onChange={e => void selectHistory(e.target.value)} disabled={busy}>{history.map(item => <option key={item.screenplay_revision_id} value={item.screenplay_revision_id}>{item.screenplay_revision_id} · source {item.source_revision_id}{item.stale ? ' · stale source' : ''}</option>)}</select></label>}
      {stale && <p className="error-banner" role="status">This screenplay uses story sour