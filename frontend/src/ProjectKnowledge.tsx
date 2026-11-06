import {useEffect, useRef, useState} from 'react';
import {useProject} from './ProjectController';
import {useProjectState} from './lib/project-state';
import {agentRequest} from './lib/agent-tasks';

type Knowledge = {workspace_id: string; revision: number; content: string};
export default function ProjectKnowledge() {
  const {workspace_id} = useProject();
  const [draft, setDraft] = useProjectState<{revision: number; content: string} | null>('DirectorRuntime:knowledge', null);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [notice, setNotice] = useState('');
  const saving = useRef<AbortController | null>(null);
  useEffect(() => () => saving.current?.abort(), []);
  useEffect(() => {
    if (draft !== null) return;
    const controller = new AbortController();
    void agentRequest<Knowledge>(workspace_id, 'knowledge', controller.signal).then(value => {
      if (!controller.signal.aborted) setDraft(value);
    }).catch(e => {if (!controller.signal.aborted) setError(e.message);});
    return () => controller.abort();
  }, [workspace_id, draft, setDraft]);
  async function save() {
    if (!draft || busy) return;
    setBusy(true); setError(''); setNotice('');
    const controller = new AbortController();
    saving.current = controller;
    try {
      const value = await agentRequest<Knowledge>(workspace_id, 'knowledge', controller.signal, {revision: draft.revision, content: draft.content});
      if (!controller.signal.aborted) {setDraft(value); setNotice(`Saved project knowledge · revision ${value.revision}`);}
    } catch (e) {if (!controller.signal.aborted) setError((e as Error).message);} finally {if (!controller.signal.aborted) setBusy(false);}
  }
  return <details className="director-knowledge"><summary>Project knowledge</summary>
    <p>Save recurring creative decisions and continuity notes. Director and Editor use these notes in future messages.</p>
    <label htmlFor="director-project-notes">Project notes</label>
    <textarea id="director-project-notes" rows={5} maxLength={16000} value={draft?.content || ''} disabled={!draft || busy} onChange={event => {if (draft) setDraft({...draft, content: event.target.value}); setNotice('');}}/>
    <div className="director-task-actions"><button disabled={!draft || busy} onClick={() => void save()}>Save project notes</button><button disabled={busy} onClick={() => {setDraft(null); setError(''); setNotice('');}}>Reload saved notes</button></div>
    {notice && <p role="status">{notice}</p>}{error && <p role="alert">{error}</p>}
  </details>;
}
