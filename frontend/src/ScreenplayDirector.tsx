import {useContext, useEffect, useRef, useState} from 'react';
import {Check, LoaderCircle} from 'lucide-react';
import {getConversation, applyScreenplay, Conversation} from './lib/storyboard-api';
import type {ScreenplayRevision} from './lib/story-api';
import './storyboard.css';
import {DirectorScreenplay, type ScreenplayTarget} from './DirectorScreenplay';
import {useProjectState} from './lib/project-state';

export default function ScreenplayDirector({workspace, revision, disabled, onApplied}: {
  workspace: string; revision: string; disabled: boolean;
  onApplied: (value: ScreenplayRevision) => Promise<void>;
}) {
  const [items, setItems] = useState<Conversation[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<'apply' | ''>('');
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Record<string, number[]>>({});
  const bridge = useContext(DirectorScreenplay);
  const [dismissed, setDismissed] = useProjectState<string[]>('ScreenplayDirector:dismissed', []);
  const applyKey = useRef<{signature: string; key: string} | null>(null);
  const locked = disabled || !!busy || loading;

  useEffect(() => {
    let live = true;
    setItems([]); setSelected({}); setError(''); setLoading(true);
    void getConversation(workspace, revision).then(data => {
      if (live) setItems(data.items);
    }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [workspace, revision]);

  const latest = useRef({workspace, revision, locked});
  latest.current = {workspace, revision, locked};
  useEffect(() => {
    if (!bridge) return;
    let active = true;
    const adapter = {
      prepareTarget: (): ScreenplayTarget => {
        if (latest.current.locked) throw new Error('Save local edits and open the latest screenplay revision before using its Director.');
        return {version: 1, workspace_id: latest.current.workspace, screenplay_revision_id: latest.current.revision};
      },
      refresh: async () => {
        const scope = latest.current;
        const result = await getConversation(scope.workspace, scope.revision);
        if (active && latest.current.workspace === scope.workspace && latest.current.revision === scope.revision) {
          setItems(result.items);
          setSelected(previous => Object.fromEntries(result.items.map(item =>
            [item.key, previous[item.key] ?? item.proposal?.changes.map((_, index) => index) ?? []])));
        }
      }
    };
    bridge.current = adapter;
    return () => {active = false; if (bridge.current === adapter) bridge.current = null;};
  }, [bridge]);

  const apply = async (item: Conversation) => {
    setBusy('apply'); setError('');
    try {
      const selection = selected[item.key] || [];
      const signature = JSON.stringify([item.key, selection]);
      const key = applyKey.current?.signature === signature ? applyKey.current.key : crypto.randomUUID();
      applyKey.current = {signature, key};
      await onApplied(await applyScreenplay(workspace, revision, item.key, selection, key));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(''); }
  };

  return <section className="card screenplay-director board-stack" aria-label="Screenplay change review">
    <h2>Screenplay changes</h2>
    <p>Discuss the screenplay in the shared Director. Ask it to prepare agreed changes, then review and apply them here.</p>
    {disabled && <p className="muted">Save local edits and open the latest screenplay revision to use the Director.</p>}
    {error && <p className="error-banner" role="alert">{error}</p>}
    {items.filter(item => item.proposal && !dismissed.includes(item.key)).map(item => <article key={item.key} className="screenplay-chat-review">
      <p>{item.proposal!.explanation}</p>
      {item.revision_id && item.revision_id !== revision ? <small className="muted">Proposal from an earlier screenplay revision.</small> : <>
        <div className="board-changes">{item.proposal!.changes.map((change, index) => <label key={index}>
          <input type="checkbox" checked={(selected[item.key] || []).includes(index)} disabled={locked}
            onChange={event => setSelected(old => ({...old, [item.key]: event.target.checked ? [...(old[item.key] || []), index] : (old[item.key] || []).filter(i => i !== index)}))}/>
          <span><b>Scene {change.scene_number} · Shot {change.shot_number} · {change.field}</b>
            <small>Before: {String(change.before ?? 'Not set')}</small><span>After: {String(change.value)}</span></span>
        </label>)}</div>
        <div className="board-actions">
          <button className="quiet-button" disabled={locked || !selected[item.key]?.length} onClick={() => void apply(item)}><Check size={15}/> Apply selected changes</button>
          <button className="quiet-button" disabled={!!busy} onClick={() => setDismissed(old => [...old, item.key])}>Discard suggestion</button>
        </div>
      </>}
    </article>)}
    {items.some(item => !['complete'].includes(item.status)) && <p role="status">A saved screenplay request has no confirmed result. Reload its conversation to check before starting another request.</p>}
    {(busy || loading) && <p role="status"><LoaderCircle size={16} className="spin"/> {loading ? 'Loading conversation…' : 'Saving screenplay revision…'}</p>}
    {!!items.length && <details><summary>Previous screenplay conversation</summary>
      {items.map(item => <article key={item.key}><p><strong>You</strong> {item.instruction}</p><p><strong>Director</strong> {item.reply || item.proposal?.explanation || item.status}</p></article>)}
    </details>}
    <button className="quiet-button" disabled={locked} onClick={() => void bridge?.current?.refresh().catch(e => setError(e.message))}>Reload screenplay conversation</button>
  </section>;
}
