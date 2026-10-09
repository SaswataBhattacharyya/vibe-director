import { useEffect, useState } from 'react';
import { RefreshCw, Save, Sparkles } from 'lucide-react';
import { draftStoryScreenplay, getStoryGraph, getStoryScreenplay, getStoryWorkspace, saveStoryScreenplay, ScreenplayDraftTask, ScreenplayRevision } from './lib/story-api';

const directionKeys = ['camera', 'lighting', 'mood', 'sfx', 'music'] as const;
const pendingKey = (workspace: string, source: string) => `vibe-screenplay-task:${workspace}:${source}`;
export default function ScreenplayPage() {
  const [revision, setRevision] = useState<ScreenplayRevision | null>(null);
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
      try { const value = await getStoryScreenplay(id, source); setRevision(value); setDraft(value.screenplay); }
      catch (e) { if ((e as Error & { status?: number }).status !== 404) throw e; setRevision(null); setDraft(null); }
      try { setGraph(await getStoryGraph(id, source)); } catch (e) { if ((e as Error & { status?: number }).status === 404) setGraph(null); else throw e; }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  useEffect(() => { void refresh(); }, []);
  const generate = async () => {
    if (!graph || !sourceId) return; setBusy(true); setError('');
    try { const keyName = pendingKey(workspaceId, sourceId); const key = localStorage.getItem(keyName) || crypto.randomUUID(); localStorage.setItem(keyName, key); const result = await draftStoryScreenplay(workspaceId, sourceId, graph.snapshot_id, key); if ('screenplay' in result) { setRevision(result); setDraft(result.screenplay); setTask(null); localStorage.removeItem(keyName); setNotice(`Draft saved. ${result.chunk_complete}/${result.chunk_total} source chunks planned; semantic coverage still needs review.`); } else { setTask(result); setNotice(`${result.chunk_complete}/${result.chunk_total} chunks planned. Select Continue draft to resume this saved task.`); } }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const save = async () => {
    if (!revision || !draft) return; setBusy(true); setError('');
    try { const result = await saveStoryScreenplay(workspaceId, revision.screenplay_revision_id, draft, crypto.randomUUID()); setRevision(result); setDraft(result.screenplay); setNotice('Edit saved as a new screenplay revision; the prior version remains available in history.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const update = (sceneIndex: number, shotIndex: number, field: string, value: string) => setDraft(current => current && ({ ...current, scenes: current.scenes.map((scene, si) => si !== sceneIndex ? scene : { ...scene, shots: scene.shots.map((shot, hi) => hi !== shotIndex ? shot : field.startsWith('direction.') ? { ...shot, direction: { ...shot.direction, [field.slice(10)]: value } } : { ...shot, [field]: value }) }) }));
  return <main className="content-wrap story-content"><div className="page-heading"><div><div className="eyebrow">SOURCE-LINKED DRAFT</div><h1>Screenplay</h1><p>{sourceId ? `Source revision ${sourceId}` : 'Open a saved story to begin.'}</p></div><button className="quiet-button" onClick={() => void refresh()} disabled={busy}><RefreshCw size={15}/> Reload</button></div>
    {error && <div className="error-banner" role="alert">{error}</div>}{notice && <p role="status">{notice}</p>}
    <section className="card story-graph"><div className="story-panel-title"><div><h2>Readable screenplay</h2><p>{revision ? `Screenplay revision ${revision.screenplay_revision_id} · graph ${revision.graph_snapshot_id}` : 'Draft scenes from the accepted source graph.'}</p></div><div className="story-editor-actions"><button className="generate-button" onClick={() => void generate()} disabled={busy || graph?.status !== 'complete'}><Sparkles size={15}/> {task ? 'Continue draft' : revision ? 'Generate new revision' : 'Generate draft'}</button>{revision && <button className="quiet-button" onClick={() => void save()} disabled={busy}><Save size={15}/> Save edits</button>}</div></div>
      <p className="graph-disclosure">{draft?.coverage_note || 'Generation requires a complete graph for this exact source revision. Processed chunks do not prove semantic completeness.'} Direction and evidence stay visible with each shot.</p>
      {task && <p role="status">Draft task {task.task_status}: {task.chunk_complete}/{task.chunk_total} source chunks complete · {task.coverage_state}. {task.chunks.filter(c => c.state !== 'complete').map(c => `${c.chunk_id}: ${c.state}${c.error_message ? ` (${c.error_message})` : ''}`).join(' · ')}</p>}
      {!graph && <p>Generate and review the source graph in the Story workspace first.</p>}{graph && graph.status !== 'complete' && <p>Graph status: {graph.status}. Complete or recover the graph before drafting.</p>}
      {draft?.scenes.map((scene, si) => <article className="card screenplay-scene" key={`${scene.scene_number}-${si}`}><h2>Scene {scene.scene_number} · {scene.slugline}</h2><p>{scene.summary}</p>{scene.shots.map((shot, hi) => <div className="screenplay-shot" key={`${shot.shot_number}-${hi}`}><h3>Shot {shot.shot_number}</h3><label>Action<textarea value={shot.action} onChange={e => update(si, hi, 'action', e.target.value)}/></label><label>Dialogue<textarea value={shot.dialogue} onChange={e => update(si, hi, 'dialogue', e.target.value)}/></label><div className="screenplay-directions">{directionKeys.map(key => <label key={key}>{key}<input value={shot.direction[key]} onChange={e => update(si, hi, `direction.${key}`, e.target.value)}/></label>)}</div>{shot.evidence.map((item, i) => <blockquote key={`${item.chunk_id}-${i}`}><q>{item.quote}</q><small>{item.source_revision_id} · {item.start_codepoint}:{item.end_codepoint} · {item.chunk_id}</small></blockquote>)}</div>)}</article>)}
    </section></main>;
}
