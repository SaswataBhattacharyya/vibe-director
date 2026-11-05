import {useEffect, useRef, useState} from 'react';
import {MessageSquare, Sparkles, Check, Send, LoaderCircle} from 'lucide-react';
import {getConversation, chatScreenplay, proposeScreenplay, applyScreenplay, Conversation} from './lib/storyboard-api';
import type {ScreenplayRevision} from './lib/story-api';
import './storyboard.css';

export default function ScreenplayDirector({workspace, revision, disabled, onApplied}: {
  workspace: string; revision: string; disabled: boolean;
  onApplied: (value: ScreenplayRevision) => Promise<void>;
}) {
  const [items, setItems] = useState<Conversation[]>([]);
  const [instruction, setInstruction] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<'chat' | 'propose' | 'apply' | ''>('');
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Record<string, number[]>>({});
  const [sending, setSending] = useState('');
  const pending = useRef<{text: string; mode: string; key: string} | null>(null);
  const applyKey = useRef<{signature: string; key: string} | null>(null);
  const log = useRef<HTMLDivElement>(null);
  const locked = disabled || !!busy || loading;

  useEffect(() => {
    let live = true;
    setItems([]); setSelected({}); setError(''); setLoading(true); pending.current = null;
    void getConversation(workspace, revision).then(data => {
      if (live) setItems(data.items);
    }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [workspace, revision]);

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [items, busy]);

  const send = async (mode: 'chat' | 'propose') => {
    const message = instruction.trim() || 'Prepare the changes we agreed in this conversation. Leave unrelated content unchanged.';
    if (locked || (mode === 'chat' && !instruction.trim())) return;
    setBusy(mode); setSending(message); setError('');
    try {
      const key = pending.current?.text === message && pending.current.mode === mode ? pending.current.key : crypto.randomUUID();
      pending.current = {text: message, mode, key};
      let item: Conversation;
      if (mode === 'chat') item = await chatScreenplay(workspace, revision, message, key);
      else {
        const proposal = await proposeScreenplay(workspace, revision, message, key);
        item = {key, revision_id: revision, instruction: message, status: 'complete', proposal};
        setSelected(old => ({...old, [key]: proposal?.changes.map((_, i) => i) || []}));
      }
      setItems(old => [...old.filter(i => i.key !== key), item]);
      setInstruction(''); pending.current = null;
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(''); setSending(''); }
  };

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

  return <section className="card screenplay-director board-stack" aria-label="Whole screenplay Director">
    <div className="board-heading"><div>
      <h2><MessageSquare size={18}/> Direct the whole screenplay</h2>
      <p>Discuss ideas with the Director first. When you agree, prepare the changes, review them and apply them to a new revision.</p>
    </div></div>
    {disabled && <p className="muted">Save local edits and open the latest screenplay revision to use the Director.</p>}
    {error && <p className="error-banner" role="alert">{error}</p>}
    <div className="screenplay-chat-log" role="log" aria-label="Screenplay conversation" aria-live="polite" ref={log}>
      {!items.length && !busy && !loading && <p className="muted screenplay-chat-empty">Talk through dialogue, pacing, image shots or camera direction. Sending a message keeps the screenplay unchanged.</p>}
      {items.map(item => <article key={item.key} className="screenplay-chat-turn">
        <div className="screenplay-chat-message screenplay-chat-user"><strong>You</strong><p>{item.instruction}</p></div>
        <div className="screenplay-chat-message screenplay-chat-director"><strong>Director</strong>
          {item.reply ? <p>{item.reply}</p> : item.proposal ? <>
            <p>{item.proposal.explanation}</p>
            {item.revision_id && item.revision_id !== revision ? <small className="muted">Proposal from an earlier screenplay revision.</small> : <details className="screenplay-chat-review" open>
              <summary>Review proposed changes ({item.proposal.changes.length})</summary>
              <div className="board-changes">{item.proposal.changes.map((change, index) => <label key={index}>
                <input type="checkbox" checked={(selected[item.key] || []).includes(index)} disabled={locked}
                  onChange={e => setSelected(old => ({...old, [item.key]: e.target.checked ? [...(old[item.key] || []), index] : (old[item.key] || []).filter(i => i !== index)}))}/>
                <span><b>Scene {change.scene_number} · Shot {change.shot_number} · {change.field}</b>
                  <small>Before: {String(change.before ?? 'Not set')}</small><span>After: {String(change.value)}</span></span>
              </label>)}</div>
              <button className="quiet-button" disabled={locked || !selected[item.key]?.length} onClick={() => void apply(item)}><Check size={15}/> Apply selected changes</button>
            </details>}
          </> : <p>{item.status === 'in_progress' ? 'This request may still be processing. Reload the conversation to check its saved result.' : 'This request did not return a confirmed reply. Check its status before starting another request.'}</p>}
        </div>
      </article>)}
      {sending && <div className="screenplay-chat-message screenplay-chat-user"><strong>You</strong><p>{sending}</p></div>}
      {(busy || loading) && <div className="screenplay-thinking" role="status"><LoaderCircle size={16} className="spin" aria-hidden="true"/>
        {loading ? 'Loading conversation…' : busy === 'apply' ? 'Saving screenplay revision…' : busy === 'propose' ? 'Director is preparing changes…' : 'Director is thinking…'}
      </div>}
    </div>
    <form className="board-stack" onSubmit={e => {e.preventDefault(); void send('chat');}}>
      <label className="board-field">Screenplay instruction
        <textarea value={instruction} maxLength={4000} disabled={locked} onChange={e => setInstruction(e.target.value)}
          onKeyDown={e => {if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {e.preventDefault(); void send('chat');}}}
          placeholder="Talk to the Director — for example: where would character dialogue work better than narration?" rows={3}/>
      </label>
      <div className="board-actions screenplay-chat-actions">
        <button type="submit" className="generate-button" disabled={locked || !instruction.trim()}><Send size={15}/> Send message</button>
        <button type="button" className="quiet-button" disabled={locked || (!items.some(i => i.status === 'complete') && !instruction.trim())} onClick={() => void send('propose')}><Sparkles size={15}/> Prepare agreed changes</button>
        <small className="muted">Ctrl / ⌘ + Enter to send · Changes are saved only when you apply them.</small>
      </div>
    </form>
  </section>;
}
