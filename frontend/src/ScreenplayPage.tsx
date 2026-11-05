import {managedProjectId} from './lib/media-workspace';
import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, RefreshCw, Save, Sparkles } from 'lucide-react';
import SelectionMicroEdit from './SelectionMicroEdit';
import DirectorSettings from './DirectorSettings';
import ScreenplayDirector from './ScreenplayDirector';
import { acceptStoryScreenplay, buildStoryGraph, draftStoryScreenplay, getStoryGraph, getStoryScreenplay, getStoryScreenplayRevision, getStoryWorkspace, listStoryScreenplays, saveStoryScreenplay, ScreenplayDraftTask, ScreenplayRevision, ScreenplayRevisionSummary } from './lib/story-api';

const directionKeys = ['camera', 'lighting', 'mood', 'sfx', 'music'] as const;
const pendingKey = (workspace: string, source: string, styleSnapshot: string | null) => `vibe-screenplay-task:${workspace}:${source}:${styleSnapshot || 'none'}`;
const draftKey = (workspace: string, revision: string) => `vibe-screenplay-local:${workspace}:${revision}`;
const graphKey = (workspace: string, source: string) => `vibe-screenplay-graph:${workspace}:${source}`;
export default function ScreenplayPage() {
  const [revision, setRevision] = useState<ScreenplayRevision | null>(null);
  const [history, setHistory] = useState<ScreenplayRevisionSummary[]>([]);
  const [graph, setGraph] = useState<Awaited<ReturnType<typeof getStoryGraph>> | null>(null);
  const [draft, setDraft] = useState<ScreenplayRevision['screenplay'] | null>(null);
  const [sourceId, setSourceId] = useState(''); const [workspaceId, setWorkspaceId] = useState('');
  const [busy, setBusy] = useState(false); const [task, setTask] = useState<ScreenplayDraftTask | null>(null); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [storageWarning, setStorageWarning] = useState(false);
  const [historyOffset, setHistoryOffset] = useState<number | null>(null);
  const saveKeys = useRef<Record<string, {key:string;draft:string}>>({});
  const installRevision = (value: ScreenplayRevision, recover = true) => {
    setRevision(value); setDraft(value.screenplay);
    if (recover) {
      try {
        const saved = JSON.parse(localStorage.getItem(draftKey(value.workspace_id || workspaceId, value.screenplay_revision_id)) || 'null');
        if (Array.isArray(saved?.scenes) && saved.scenes.length === value.screenplay.scenes.length) {
          const recovered = {...value.screenplay,scenes:value.screenplay.scenes.map((scene,si)=>{
            const localScene = saved.scenes[si];
            if (!Array.isArray(localScene?.shots) || localScene.shots.length !== scene.shots.length) throw new Error('Invalid recovery scene');
            return {...scene,shots:scene.shots.map((shot,hi)=>{
              const localShot=localScene.shots[hi];
              if (typeof localShot?.action !== 'string' || typeof localShot?.dialogue !== 'string' || !directionKeys.every(key=>typeof localShot?.direction?.[key] === 'string')) throw new Error('Invalid recovery shot');
              if (localShot.planned_duration_seconds != null && (typeof localShot.planned_duration_seconds !== 'number' || !Number.isFinite(localShot.planned_duration_seconds) || localShot.planned_duration_seconds <= 0)) throw new Error('Invalid recovered duration');
              return {...shot,presentation:localShot.presentation === 'image' ? 'image' : localShot.presentation === 'video' ? 'video' : shot.presentation,planned_duration_seconds:'planned_duration_seconds' in localShot ? localShot.planned_duration_seconds : shot.planned_duration_seconds ?? null,action:localShot.action,dialogue:localShot.dialogue,direction:{...shot.direction,...Object.fromEntries(directionKeys.map(key=>[key,localShot.direction[key]]))}};
            })};
          })};
          if (JSON.stringify(recovered) !== JSON.stringify(value.screenplay)) {setDraft(recovered);setNotice('Recovered screenplay edits from this browser. Save progress to save them to the server.');}
        }
      } catch { setStorageWarning(true); }
    }
  };
  const loadHistory = async (id: string) => {
    const page = await listStoryScreenplays(id); setHistory(page.items || []);
    setHistoryOffset(page.offset + page.items.length < page.total ? page.offset + page.items.length : null);
    return page;
  };
  const refresh = async () => {
    if (dirty && !window.confirm('Reload the server screenplay? Your edits remain in this browser recovery draft.')) return;
    const id = managedProjectId() || localStorage.getItem('vibe-story-selected-v1') || '';
    if (!id.startsWith('story-')) { if(id)localStorage.removeItem('vibe-story-selected-v1'); setError('Open a story first to work on its screenplay. Browser drafts are retained.'); return; }
    setWorkspaceId(id); setBusy(true); setError('');
    try {
      const workspace = await getStoryWorkspace(id); const source = workspace.current_revision_id || workspace.current_revision?.revision_id;
      if (!source) throw new Error('The story has no saved source revision.'); setSourceId(source);
      const revisions = await loadHistory(id);
      try { const value = await getStoryScreenplay(id, source); installRevision(value); }
      catch (e) {
        if ((e as Error & { status?: number }).status !== 404) throw e;
        const latest = revisions.items?.[0];
        if (latest) { const value = await getStoryScreenplayRevision(id, latest.screenplay_revision_id); installRevision(value); }
        else { setRevision(null); setDraft(null); }
      }
      try { setGraph(await getStoryGraph(id, source)); } catch (e) { if ((e as Error & { status?: number }).status === 404) setGraph(null); else throw e; }
    } catch (e) { if((e as Error & {status?:number}).status===404&&!revision){localStorage.removeItem('vibe-story-selected-v1');setWorkspaceId('');setSourceId('');setError('The previously selected story was removed. Open a saved story. Browser recovery drafts are retained.');}else setError((e as Error).message); } finally { setBusy(false); }
  };
  useEffect(() => { void refresh(); }, []);
  const generate = async () => {
    if (!workspaceId || !sourceId || dirty || busy) return; setBusy(true); setError('');
    try {
      const currentWorkspace = await getStoryWorkspace(workspaceId);
      const currentStyleSnapshotId = currentWorkspace.style_selection_snapshot_id || null;
      let currentGraph = graph;
      if (!currentGraph || currentGraph.source_revision_id !== sourceId || currentGraph.status !== 'complete') {
        const graphKeyName = graphKey(workspaceId, sourceId);
        const key = currentGraph?.source_revision_id === sourceId
          ? currentGraph.idempotency_key
          : localStorage.getItem(graphKeyName) || crypto.randomUUID();
        localStorage.setItem(graphKeyName, key);
        setNotice('Preparing story context…');
        currentGraph = await buildStoryGraph(workspaceId, sourceId, key);
        setGraph(currentGraph);
        if (currentGraph.status !== 'complete') {
          setNotice(`Story context is ${currentGraph.status}: ${currentGraph.chunk_complete}/${currentGraph.chunk_total} sections ready. Continue here to resume; your story is saved.`);
          return;
        }
        localStorage.removeItem(graphKeyName);
      }
      const keyName = pendingKey(workspaceId, sourceId, currentStyleSnapshotId); const key = localStorage.getItem(keyName) || crypto.randomUUID(); localStorage.setItem(keyName, key); const result = await draftStoryScreenplay(workspaceId, sourceId, currentGraph.snapshot_id, key); if ('screenplay' in result) { installRevision(result, false); await loadHistory(workspaceId); setTask(null); localStorage.removeItem(keyName); setNotice(`Draft saved. ${result.chunk_complete}/${result.chunk_total} source chunks planned; semantic coverage still needs review.`); } else { setTask(result); setNotice(`${result.chunk_complete}/${result.chunk_total} chunks planned. Select Continue draft to resume this saved task.`); }
    }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const save = async () => {
    if (!revision || !draft || !dirty || busy || stale || !latestForSource) return; setBusy(true); setError('');
    try {
      if (draft.scenes.some(scene=>scene.shots.some(shot=>shot.planned_duration_seconds != null && (!Number.isFinite(shot.planned_duration_seconds) || shot.planned_duration_seconds <= 0)))) throw new Error('Planned shot duration must be a positive number of seconds, or leave it blank.');
      const recoveryKey = `${draftKey(workspaceId, revision.screenplay_revision_id)}:save`;
      let pending = saveKeys.current[recoveryKey];
      try { pending = JSON.parse(localStorage.getItem(recoveryKey) || 'null') || pending; } catch { setStorageWarning(true); }
      const serialized = JSON.stringify(draft);
      const key = pending?.draft === serialized ? pending.key : crypto.randomUUID();
      saveKeys.current[recoveryKey] = {key,draft:serialized};
      try { localStorage.setItem(recoveryKey, JSON.stringify({key,draft:serialized})); } catch { setStorageWarning(true); }
      const result = await saveStoryScreenplay(workspaceId, revision.screenplay_revision_id, draft, key);
      try { localStorage.removeItem(draftKey(workspaceId, revision.screenplay_revision_id)); localStorage.removeItem(recoveryKey); } catch { setStorageWarning(true); }
      installRevision(result, false); await loadHistory(workspaceId); setNotice('Edit saved as a new screenplay revision; the prior version remains available in history.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const accept = async () => {
    if (!revision || stale || !latestForSource) return;
    setBusy(true); setError('');
    try { const result = await acceptStoryScreenplay(workspaceId, revision.screenplay_revision_id); installRevision(result, false); await loadHistory(workspaceId); setNotice('Screenplay accepted. Choose Assisted manual or Fully automated and confirm its settings next.'); }
    catch (e) { setError(`Could not accept this screenplay revision: ${(e as Error).message}`); } finally { setBusy(false); }
  };
  const selectHistory = async (id: string) => {
    setBusy(true); setError('');
    try { const value = await getStoryScreenplayRevision(workspaceId, id); installRevision(value); setNotice('Viewing saved screenplay revision.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const currentSummary = revision && history.find(item => item.screenplay_revision_id === revision.screenplay_revision_id);
  const staleSource = !!revision && revision.source_revision_id !== sourceId;
  const staleStyle = !!revision && currentSummary?.stale === true && !staleSource;
  const stale = staleSource || staleStyle;
  const latestForSource = !!revision && history.find(item => item.source_revision_id === revision.source_revision_id)?.screenplay_revision_id === revision.screenplay_revision_id;
  const accepted = !!revision && history.find(item => item.screenplay_revision_id === revision.screenplay_revision_id)?.accepted === true;
  const dirty = !!revision && !!draft && JSON.stringify(draft) !== JSON.stringify(revision.screenplay);
  const update = (sceneIndex: number, shotIndex: number, field: string, value: string | number | null) => setDraft(current => {
    if (!current || !revision) return current;
    const next = { ...current, scenes: current.scenes.map((scene, si) => si !== sceneIndex ? scene : { ...scene, shots: scene.shots.map((shot, hi) => hi !== shotIndex ? shot : field.startsWith('direction.') ? { ...shot, direction: { ...shot.direction, [field.slice(10)]: String(value) } } : { ...shot, [field]: value }) }) };
    try { localStorage.setItem(draftKey(workspaceId,revision.screenplay_revision_id),JSON.stringify(next)); }
    catch { setStorageWarning(true); }
    return next;
  });
  const downloadDraft = () => { const url = URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'})); const link=document.createElement('a'); link.href=url;link.download='screenplay-draft.json';link.click();URL.revokeObjectURL(url); };
  useEffect(()=>{
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);
  },[dirty]);
  return <main className="content-wrap story-content"><div className="page-heading"><div><div className="eyebrow">SOURCE-LINKED DRAFT</div><h1>Screenplay</h1><p>{sourceId ? `Source revision ${sourceId}` : 'Open a saved story to begin.'}</p></div><button className="quiet-button" onClick={() => void refresh()} disabled={busy}><RefreshCw size={15}/> Reload</button></div>
    {storageWarning && <div className="error-banner" role="alert">Browser recovery storage is unavailable. Save progress to the server or <button className="text-button" onClick={downloadDraft}>Download screenplay draft</button>.</div>}{error && <div className="error-banner" role="alert">{error}</div>}{notice && <p role="status">{notice}</p>}
    <details className="card screenplay-director-settings"><summary>Director model, reasoning & saved lessons</summary><DirectorSettings/></details>
    {revision && <ScreenplayDirector workspace={workspaceId} revision={revision.screenplay_revision_id} disabled={busy || dirty || stale || !latestForSource} onApplied={async value=>{installRevision(value,false);await loadHistory(workspaceId);setNotice('Director changes saved as a new revision. Review and accept when ready.');}}/>}
    <section className="card story-graph"><div className="story-panel-title"><div><h2>Readable screenplay</h2><p>{revision ? `Screenplay revision ${revision.screenplay_revision_id}${revision.style_selection_snapshot_id ? ` · style ${revision.style_selection_snapshot_id}` : ""}` : 'Generate a readable screenplay from your saved story.'}</p></div><div className="story-editor-actions"><button className="generate-button" onClick={() => void generate()} disabled={busy || !sourceId || dirty}><Sparkles size={15}/> {task ? 'Continue draft' : revision ? 'Generate new revision' : 'Generate screenplay'}</button>{revision && <button className="quiet-button" onClick={() => void save()} disabled={busy || stale || !latestForSource || !dirty}><Save size={15}/> Save progress</button>}{revision && <button className="quiet-button" onClick={() => void accept()} disabled={busy || stale || !latestForSource || accepted || dirty || graph?.status !== 'complete'}><Check size={15}/> {accepted ? 'Accepted' : 'Review & accept'}</button>}</div></div>
      <p className="graph-disclosure">Story context is prepared before screenplay generation. Review the numbered scenes, shots and direction before continuing.</p>
      {graph && graph.status !== 'complete' && graph.chunks.some(chunk => chunk.state === 'failed' || chunk.state === 'uncertain') && <div className="error-banner" role="alert"><strong>Story preparation needs attention; no screenplay was generated.</strong><ul>{graph.chunks.filter(chunk => chunk.state === 'failed' || chunk.state === 'uncertain').map(chunk => <li key={chunk.chunk_id}>{chunk.chunk_id}: {chunk.error_message || chunk.state}</li>)}</ul><p>{graph.chunks.some(chunk => chunk.state === 'failed') ? 'Generate screenplay retries failed sections and preserves completed work.' : 'The provider outcome is uncertain. Review the saved attempt before starting another request.'} Your saved story is unchanged.</p></div>}
      {task?.chunks.some(chunk => chunk.error_message?.includes('scenes array')) && <p className="error-banner" role="status">The Director returned an incorrectly formatted screenplay. Your saved story is unchanged. Choose a Director model and reasoning depth above, then Continue draft to retry the failed section; completed sections are kept.</p>}
      {dirty && <p className="graph-disclosure" role="status">Draft on this browser only. Save progress to the server before accepting or generating another screenplay.</p>}
      {history.length > 0 && <details><summary>Screenplay revision history</summary><label className="screenplay-history">Saved revisions <select aria-label="Saved screenplay revisions" value={revision?.screenplay_revision_id || ''} onChange={e => void selectHistory(e.target.value)} disabled={busy || dirty}>{history.map(item => <option key={item.screenplay_revision_id} value={item.screenplay_revision_id}>{item.screenplay_revision_id} · source {item.source_revision_id}{item.stale ? ' · stale inputs' : ''}</option>)}</select></label>{historyOffset != null && <button className="text-button" disabled={busy} onClick={()=>void listStoryScreenplays(workspaceId,historyOffset).then(page=>{setHistory(old=>[...old,...page.items]);setHistoryOffset(page.offset+page.items.length<page.total?page.offset+page.items.length:null);}).catch(e=>setError(e.message))}>Load more revisions</button>}</details>}
      {dirty && <p className="graph-disclosure" role="status">Save your edits before opening another revision.</p>}
      {stale && <p className="error-banner" role="status">{staleStyle ? 'The pinned production type or directing style changed after this screenplay was created.' : `This screenplay uses story source ${revision?.source_revision_id}, while the current story is ${sourceId}.`} You can review it, but edits are locked. Generate a screenplay from the current source, style and graph to continue.</p>}
      {!stale && revision && !latestForSource && <p className="graph-disclosure" role="status">This is an earlier screenplay revision. Select the latest revision to edit.</p>}
      <p className="graph-disclosure">{draft?.coverage_note || 'Generation requires a complete graph for this exact source revision. Processed chunks do not prove semantic completeness.'} Direction is editable with each shot.</p>
      {draft?.graph_record_coverage && <details><summary>Source coverage and implementation evidence</summary><section aria-label="Extracted event and fact links" className="screenplay-coverage">
        <h3>Extracted story records</h3>
        <p>{draft.graph_record_coverage.linked_count} of {draft.graph_record_coverage.record_count} extracted events and facts are linked to screenplay shots. This does not show whether the graph extracted every meaningful event from the story.</p>
        {draft.graph_record_coverage.unlinked_records.length > 0 && <ul>{draft.graph_record_coverage.unlinked_records.map(record => <li key={record.record_id}><strong>{record.kind}: {record.name}</strong>{record.detail && <span> — {record.detail}</span>}{record.evidence.map((item, index) => <blockquote key={`${record.record_id}-${index}`}><q>{item.quote}</q><small>{item.start_codepoint}:{item.end_codepoint} · {item.chunk_id}</small></blockquote>)}</li>)}</ul>}
        {draft.graph_record_coverage.unlinked_records.length === 0 && draft.graph_record_coverage.record_count > 0 && <p>Every extracted event/fact record is linked.</p>}
      </section></details>}
      {task && <p role="status">Draft task {task.task_status}: {task.chunk_complete}/{task.chunk_total} source chunks complete · {task.coverage_state}. {task.chunks.filter(c => c.state !== 'complete').map(c => `${c.chunk_id}: ${c.state}${c.error_message ? ` (${c.error_message})` : ''}`).join(' · ')}</p>}
      {draft?.scenes.map((scene, si) => <article className="card screenplay-scene" key={`${scene.scene_number}-${si}`}><h2>Scene {scene.scene_number} · {scene.slugline}</h2><p>{scene.summary}</p>{scene.shots.map((shot, hi) => <div className="screenplay-shot" key={`${shot.shot_number}-${hi}`}><h3>Shot {shot.shot_number}</h3><label>Presentation<select aria-label={`Scene ${scene.scene_number} Shot ${shot.shot_number} presentation`} value={shot.presentation || 'video'} disabled={busy||stale||!latestForSource} onChange={e=>update(si,hi,'presentation',e.target.value)}><option value="video">Video</option><option value="image">Image</option></select></label><label>Planned duration (seconds)<input aria-label={`Scene ${scene.scene_number} Shot ${shot.shot_number} planned duration (seconds)`} type="number" min="0.1" step="any" placeholder="Not set" value={shot.planned_duration_seconds ?? ''} onChange={event=>update(si,hi,'planned_duration_seconds',event.target.value === '' ? null : Number(event.target.value))} disabled={busy||stale||!latestForSource}/></label><p className="muted">Intended shot length. Clip planning uses this pacing target within the selected workflow’s limits.</p><SelectionMicroEdit label="Action" value={shot.action} surface="screenplay" workspaceId={workspaceId} revisionId={revision?.screenplay_revision_id || ''} fieldKey={`${scene.scene_number}.${shot.shot_number}.action`} onChange={value=>update(si,hi,'action',value)} disabled={busy||stale||!latestForSource}/><SelectionMicroEdit label="Dialogue" value={shot.dialogue} surface="screenplay" workspaceId={workspaceId} revisionId={revision?.screenplay_revision_id || ''} fieldKey={`${scene.scene_number}.${shot.shot_number}.dialogue`} onChange={value=>update(si,hi,'dialogue',value)} disabled={busy||stale||!latestForSource}/><div className="screenplay-directions">{directionKeys.map(key => <SelectionMicroEdit key={key} label={key} value={shot.direction[key]} multiline={false} surface="screenplay" workspaceId={workspaceId} revisionId={revision?.screenplay_revision_id || ''} fieldKey={`${scene.scene_number}.${shot.shot_number}.direction.${key}`} onChange={value=>update(si,hi,`direction.${key}`,value)} disabled={busy||stale||!latestForSource}/>)}</div><details><summary>Source evidence</summary>{shot.evidence.map((item, i) => <blockquote key={`${item.chunk_id}-${i}`}><q>{item.quote}</q><small>{item.source_revision_id} · {item.start_codepoint}:{item.end_codepoint} · {item.chunk_id}</small></blockquote>)}</details></div>)}</article>)}
      {accepted && latestForSource && !stale && !dirty && <section className="card screenplay-next-stage"><div><h2>Next: production setup</h2><p>Choose Assisted manual or Fully automated, then confirm its parameters.</p></div><a className="generate-button" href="#/setup">Choose production mode <ArrowRight size={15}/></a></section>}
    </section></main>;
}
