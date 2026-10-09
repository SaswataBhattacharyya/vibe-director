import { ChangeEvent, DragEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BookOpen, FileUp, History, RefreshCw, RotateCcw, Save, Sparkles } from 'lucide-react';
import { applyStoryImport, createStoryWorkspace, getStoryCreation, getStoryWorkspace, listStoryRevisions, listStoryWorkspaces, restoreStoryRevision, saveStoryRevision, StoryCreation, StoryImport, StoryRevision, StoryRevisionSummary, StoryWorkspace, uploadStoryFile } from './lib/story-api';
import { getStyleSelections, StyleSelection } from './lib/styles-api';

const LOCAL_KEY = 'vibe-story-draft-v1';
const UI_KEY = 'vibe-story-ui-draft-v1';
const STYLE_CONTEXT_KEY = 'vibe-style-setup-context-v1';
type LocalDraft = { workspaceId: string; sourceText: string; baseRevisionId: string };
type PendingCreate = { action: 'create' | 'apply'; key: string; state: 'unresolved' | 'not_found' | 'initializing' | 'conflict'; importId?: string; title: string; sourceText: string; styleSelectionSnapshotId?: string };
type LocalUi = { importPreview: StoryImport | null; importTitle: string; newTitle: string; newText: string; sourceHadCrLf: boolean; newStyleSelectionSnapshotId?: string; importStyleSelectionSnapshotId?: string; pendingCreate?: PendingCreate };
const emptyUi: LocalUi = { importPreview: null, importTitle: '', newTitle: '', newText: '', sourceHadCrLf: false };
const idOf = (workspace: StoryWorkspace) => workspace.workspace_id;
const normalizeWorkspace = (workspace: StoryWorkspace): StoryWorkspace => ({ ...workspace, current_revision_id: workspace.current_revision_id || workspace.current_revision?.revision_id || null });
function readObject<T>(key: string, fallback: T): T { try { const value = localStorage.getItem(key); return value ? JSON.parse(value) as T : fallback; } catch { return fallback; } }
function readDrafts(): Record<string, LocalDraft> { return readObject(LOCAL_KEY, {}); }
function safeStore(key: string, value: string): boolean { try { localStorage.setItem(key, value); return true; } catch { return false; } }
const summaryOf = (revision: StoryRevision): StoryRevisionSummary => ({ revision_id: revision.revision_id, source_sha256: revision.source_sha256 || '', created_at: revision.created_at, parent_revision_id: revision.parent_revision_id, revision_number: revision.revision_number });
const styleLabel = (selection: StyleSelection) => `${selection.director_profile?.display_name || selection.production_type} · v${selection.style_version ?? selection.style_version_id}`;
const styleOptionLabel = (selection: StyleSelection) => `${styleLabel(selection)} · saved ${selection.created_at ? new Date(selection.created_at).toLocaleString() : 'snapshot'}`;
const stylePinLabel = (workspace: StoryWorkspace) => workspace.style_selection ? styleLabel(workspace.style_selection) : workspace.style_selection_snapshot_id ? `Snapshot ${workspace.style_selection_snapshot_id} (details unavailable)` : 'No production style pinned';

export default function StoryPage() {
  const [workspaces, setWorkspaces] = useState<StoryWorkspace[]>([]);
  const [workspaceOffset, setWorkspaceOffset] = useState<number | null>(null);
  const [workspaceTotal, setWorkspaceTotal] = useState(0);
  const [workspace, setWorkspace] = useState<StoryWorkspace | null>(null);
  const [text, setText] = useState('');
  const [baseRevisionId, setBaseRevisionId] = useState('');
  const [revisions, setRevisions] = useState<StoryRevisionSummary[]>([]);
  const [revisionOffset, setRevisionOffset] = useState<number | null>(null);
  const [revisionTotal, setRevisionTotal] = useState(0);
  const [ui, setUi] = useState<LocalUi>(() => readObject(UI_KEY, emptyUi));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [storageWarning, setStorageWarning] = useState(false);
  const [styleSelections, setStyleSelections] = useState<StyleSelection[]>([]);
  const [styleSelectionState, setStyleSelectionState] = useState<'loading'|'ready'|'missing_context'|'unavailable'>('loading');
  const [dragging, setDragging] = useState(false);
  const currentRevision = workspace?.current_revision;
  const dirty = useMemo(() => !!workspace && !!currentRevision && text !== currentRevision.source_text, [workspace, currentRevision, text]);
  const importPreview = ui.importPreview;
  const retainedStyleOption = (snapshotId?: string) => snapshotId && !styleSelections.some(selection => selection.snapshot_id === snapshotId) ? <option value={snapshotId}>Previously selected snapshot · {snapshotId} · currently unavailable</option> : null;
  const selectedStyleDescription = (snapshotId?: string) => {
    if (!snapshotId) return 'No production type or style version is pinned to this new workspace.';
    const choice = styleSelections.find(selection => selection.snapshot_id === snapshotId);
    return choice ? `${choice.director_profile?.purpose || choice.production_type} · snapshot ${choice.snapshot_id}` : `Saved style snapshot ${snapshotId} is not in the latest available list; its original ID remains in the frozen request.`;
  };
  const styleChoiceStatus = styleSelectionState === 'loading' ? 'Loading saved style selections…' : styleSelectionState === 'missing_context' ? 'No saved setup context is available in this browser. You can create a story without a style.' : styleSelectionState === 'unavailable' ? 'Saved style selections could not be read. Refresh to try again; no style is attached automatically.' : styleSelections.length ? 'Choose a saved immutable style snapshot, or leave this as no style.' : 'No style versions have been saved in the current setup context. You can continue without one.';
  const persistUi = useCallback((next: LocalUi) => { setUi(next); if (!safeStore(UI_KEY, JSON.stringify(next))) setStorageWarning(true); }, []);
  const rememberDraft = useCallback((workspaceId: string, sourceText: string, baseId: string) => {
    const all = readDrafts(); all[workspaceId] = { workspaceId, sourceText, baseRevisionId: baseId };
    if (!safeStore(LOCAL_KEY, JSON.stringify(all))) setStorageWarning(true);
  }, []);
  const setSelectedId = (id: string) => { try { localStorage.setItem('vibe-story-selected-v1', id); } catch { setStorageWarning(true); } };

  const refreshStyleSelections = useCallback(async () => {
    let context = '';
    try { context = localStorage.getItem(STYLE_CONTEXT_KEY) || ''; }
    catch { setStyleSelectionState('unavailable'); setStyleSelections([]); return; }
    if (!/^setup-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(context)) {
      setStyleSelectionState('missing_context'); setStyleSelections([]); return;
    }
    setStyleSelectionState('loading');
    try { const response = await getStyleSelections(context); setStyleSelections(response.selections || []); setStyleSelectionState('ready'); }
    catch { setStyleSelectionState('unavailable'); setStyleSelections([]); }
  }, []);
  useEffect(() => { void refreshStyleSelections(); }, [refreshStyleSelections]);

  const loadHistory = useCallback(async (id: string) => {
    const page = await listStoryRevisions(id, 0); setRevisions(page.items || []);
    const next = page.offset + page.items.length; setRevisionOffset(next < page.total ? next : null); setRevisionTotal(page.total);
  }, []);
  const installWorkspace = useCallback((value: StoryWorkspace, forceServer = false) => {
    value = normalizeWorkspace(value);
    setWorkspace(value); setSelectedId(value.workspace_id);
    const local = forceServer ? undefined : readDrafts()[value.workspace_id];
    if (!value.current_revision) {
      setBaseRevisionId(local?.baseRevisionId || ''); setText(local?.sourceText || ''); setRevisions([]); setRevisionOffset(null); setRevisionTotal(0);
      setNotice('Workspace initialization is incomplete. Source text is unavailable; use Refresh workspace after initialization finishes.');
      return;
    }
    const revId = value.current_revision.revision_id;
    const source = local ? local.sourceText : value.current_revision.source_text;
    const base = local ? local.baseRevisionId : revId;
    setBaseRevisionId(base); setText(source); rememberDraft(value.workspace_id, source, base);
    setNotice(local && local.baseRevisionId !== revId ? 'This local draft is based on an older revision. Save uses that base and will preserve your draft if the server reports a conflict.' : 'Workspace opened.');
  }, [rememberDraft]);
  const loadWorkspace = useCallback(async (id: string, forceServer = false) => {
    const value = await getStoryWorkspace(id); installWorkspace(value, forceServer);
    if (value.current_revision) await loadHistory(id);
  }, [installWorkspace, loadHistory]);
  const finishCreation = useCallback(async (result: StoryCreation, pendingHint?: PendingCreate) => {
    const created = normalizeWorkspace(result.workspace);
    let installed = created;
    let sourceUnavailable = false;
    if (result.status === 'ready') {
      const initial = created.created_revision;
      if (initial && initial.revision_id === created.current_revision_id) installed = { ...created, current_revision: initial };
      else {
        try { installed = normalizeWorkspace(await getStoryWorkspace(created.workspace_id)); }
        catch { sourceUnavailable = true; }
      }
    }
    setWorkspaces(prev => [installed, ...prev.filter(item => idOf(item) !== idOf(installed))]);
    installWorkspace(installed);
    if (result.status === 'ready') {
      const pending = pendingHint || ui.pendingCreate;
      const clearCreateInputs = pending?.action === 'create' && ui.newTitle.trim() === pending.title && ui.newText === pending.sourceText;
      const preview = ui.importPreview;
      const clearImportInputs = pending?.action === 'apply' && !!preview && preview.import_id === pending.importId && (ui.importTitle.trim() || preview.filename) === pending.title && preview.text === pending.sourceText;
      persistUi({ ...ui, pendingCreate: undefined, ...(clearCreateInputs ? { newTitle: '', newText: '' } : {}), ...(clearImportInputs ? { importPreview: null, importTitle: '', sourceHadCrLf: false } : {}) });
      if (installed.current_revision) void loadHistory(idOf(installed)).catch(() => setNotice('Creation is confirmed. Revision history could not load yet; refresh the workspace to retry.'));
      setNotice(sourceUnavailable ? 'Creation is confirmed. The live source could not be loaded; refresh the workspace to retrieve it.' : 'Story workspace creation is confirmed.');
    } else {
      const pending = pendingHint || ui.pendingCreate;
      if (pending) persistUi({ ...ui, pendingCreate: { ...pending, state: 'initializing' } });
      setNotice('The server recorded this creation and it is still initializing. The frozen request remains available to resume.');
    }
  }, [installWorkspace, loadHistory, persistUi, ui]);
  const loadInitial = useCallback(async () => {
    setError('');
    const page = await listStoryWorkspaces(0); setWorkspaces(page.items || []); setWorkspaceTotal(page.total);
    const next = page.offset + page.items.length; setWorkspaceOffset(next < page.total ? next : null);
    let selectedId = ''; try { selectedId = localStorage.getItem('vibe-story-selected-v1') || ''; } catch { setStorageWarning(true); }
    if (selectedId && page.items?.some(item => idOf(item) === selectedId)) await loadWorkspace(selectedId);
  }, [loadWorkspace]);
  useEffect(() => { void loadInitial().catch(e => setError(`Could not load story workspaces: ${(e as Error).message}`)); }, [loadInitial]);
  useEffect(() => { if (!safeStore(UI_KEY, JSON.stringify(ui))) setStorageWarning(true); }, [ui]);
  useEffect(() => {
    const pending = ui.pendingCreate;
    if (!pending || pending.state === 'conflict') return;
    let active = true;
    void getStoryCreation(pending.key).then(result => {
      if (active) return finishCreation(result, pending);
      return undefined;
    }).catch(e => {
      if (!active) return;
      const status = (e as Error & { status?: number }).status;
      persistUi({ ...ui, pendingCreate: { ...pending, state: status === 404 ? 'not_found' : status === 409 ? 'conflict' : 'unresolved' } });
      setNotice(status === 404 ? 'No creation is recorded for this key. Retry will use the same frozen request.' : status === 409 ? 'The creation key conflicts with a different request. The original snapshot is retained and retry is blocked.' : `Creation status could not be confirmed: ${(e as Error).message}. Check status before retrying.`);
    });
    return () => { active = false; };
  }, []); // Mount recovery is read-only; it never replays create/apply POSTs.

  const chooseWorkspace = async (target: StoryWorkspace) => {
    if (workspace && idOf(workspace) === idOf(target)) return;
    if (dirty && !window.confirm('This story has unsaved text. Switch workspaces and keep this draft on this device?')) return;
    setBusy(true); setError('');
    try { await loadWorkspace(idOf(target)); }
    catch (e) { setError(`Could not open workspace: ${(e as Error).message}`); }
    finally { setBusy(false); }
  };
  const onText = (value: string) => { setText(value); if (workspace) rememberDraft(idOf(workspace), value, baseRevisionId); };
  const save = async () => {
    if (!workspace || !currentRevision || !dirty || busy) return;
    const submitted = text; setBusy(true); setError(''); setNotice('');
    try {
      const revision = await saveStoryRevision(idOf(workspace), submitted, baseRevisionId);
      const updated: StoryWorkspace = { ...workspace, current_revision_id: revision.revision_id, current_revision: revision, initialized: true, status: 'ready' };
      setWorkspace(updated); setBaseRevisionId(revision.revision_id); setText(submitted); rememberDraft(idOf(updated), submitted, revision.revision_id);
      setRevisions(prev => [summaryOf(revision), ...prev.filter(x => x.revision_id !== revision.revision_id)]); setRevisionTotal(n => Math.max(n, revisions.length + 1));
      setNotice('New story revision saved.');
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      setError(status === 409 ? 'This story changed on the server. Your draft is preserved and was not overwritten. Reload the latest server revision before continuing.' : `Could not save revision: ${(e as Error).message}. Your draft remains on this device.`);
    } finally { setBusy(false); }
  };
  const reloadServer = async () => {
    if (!workspace) return;
    if (dirty && !window.confirm('Replace this editor text with the current server revision and discard this device draft? This is the explicit recovery step after the server changed.')) return;
    setBusy(true); setError('');
    try { await loadWorkspace(idOf(workspace), true); setNotice('Loaded the latest server revision.'); }
    catch (e) { setError(`Could not reload the server revision: ${(e as Error).message}`); }
    finally { setBusy(false); }
  };
  const restore = async (revision: StoryRevisionSummary) => {
    if (!workspace || !currentRevision || busy) return;
    if (dirty && !window.confirm('Restore this revision and replace the current editor text? Unsaved local text will be replaced.')) return;
    setBusy(true); setError('');
    try {
      const restored = await restoreStoryRevision(idOf(workspace), revision.revision_id, baseRevisionId);
      const updated: StoryWorkspace = { ...workspace, current_revision_id: restored.revision_id, current_revision: restored, initialized: true, status: 'ready' };
      setWorkspace(updated); setBaseRevisionId(restored.revision_id); setText(restored.source_text); rememberDraft(idOf(updated), restored.source_text, restored.revision_id);
      setRevisions(prev => [summaryOf(restored), ...prev]); setRevisionTotal(n => n + 1); setNotice('Previous text restored as a new revision.');
    } catch (e) { setError((e as Error & {status?:number}).status === 409 ? 'The story changed on the server. Your current draft is preserved; reload before attempting a restore.' : `Could not restore revision: ${(e as Error).message}`); }
    finally { setBusy(false); }
  };
  const handleFiles = async (files: FileList | File[]) => {
    if (busy) return;
    const file = Array.from(files)[0]; if (!file) return;
    if (!/\.(txt|md|markdown|pdf)$/i.test(file.name)) { setError('Choose a .txt, .md, or .pdf file.'); return; }
    setBusy(true); setError(''); setNotice('');
    try { const preview = await uploadStoryFile(file); persistUi({ ...ui, importPreview: preview, importTitle: file.name.replace(/\.(txt|md|markdown|pdf)$/i, ''), sourceHadCrLf: preview.text.includes('\r') }); setNotice('Text extracted for review. Edit it below, then explicitly apply it to create a workspace.'); }
    catch (e) { setError(`Could not extract file text: ${(e as Error).message}`); }
    finally { setBusy(false); }
  };
  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => { if (event.target.files) void handleFiles(event.target.files); event.target.value = ''; };
  const onDrop = (event: DragEvent<HTMLDivElement>) => { event.preventDefault(); setDragging(false); if (!busy) void handleFiles(event.dataTransfer.files); };
  const submitCreation = async (pending: PendingCreate) => {
    if (busy || pending.state === 'conflict') return;
    setBusy(true); setError(''); setNotice('');
    try {
      const result = pending.action === 'create'
        ? await createStoryWorkspace(pending.title, pending.sourceText, pending.key, pending.styleSelectionSnapshotId)
        : await applyStoryImport(pending.importId!, pending.title, pending.sourceText, pending.key, pending.styleSelectionSnapshotId);
      await finishCreation(result, pending);
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      const nextState = status === 409 ? 'conflict' : 'unresolved';
      const updated = { ...ui, pendingCreate: { ...pending, state: nextState } as PendingCreate };
      if (!safeStore(UI_KEY, JSON.stringify(updated))) setStorageWarning(true);
      setUi(updated);
      setError(status === 409 ? 'The server rejected this key for a different request. The original frozen request is retained and cannot be retried with changed content.' : `Creation response was not confirmed: ${(e as Error).message}. The frozen request and key are preserved; check server status before retrying.`);
    } finally { setBusy(false); }
  };
  const checkCreation = async () => {
    const pending = ui.pendingCreate; if (!pending || busy || pending.state === 'conflict') return;
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await getStoryCreation(pending.key);
      if (result.status === 'ready') await finishCreation(result, pending);
      else { persistUi({ ...ui, pendingCreate: { ...pending, state: 'initializing' } }); setNotice('The server recorded this request and it is still initializing. Retry resumes the same frozen request.'); }
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      const state = status === 404 ? 'not_found' : status === 409 ? 'conflict' : 'unresolved';
      persistUi({ ...ui, pendingCreate: { ...pending, state } });
      setNotice(status === 404 ? 'A read-only lookup found no saved creation. Retry will use the same exact request.' : status === 409 ? 'The key conflicts with a different server request. The original snapshot is retained and retry is blocked.' : `Creation status remains unconfirmed: ${(e as Error).message}.`);
    } finally { setBusy(false); }
  };
  const beginCreation = (action: 'create' | 'apply', title: string, sourceText: string, importId?: string, styleSelectionSnapshotId?: string) => {
    if (busy || ui.pendingCreate) return;
    const pending: PendingCreate = { action, key: crypto.randomUUID(), title, sourceText, importId, styleSelectionSnapshotId, state: 'unresolved' };
    const updated = { ...ui, pendingCreate: pending };
    if (!safeStore(UI_KEY, JSON.stringify(updated))) { setStorageWarning(true); setError('Creation was not started because its recovery key and frozen request could not be saved locally. Free browser storage or export your text, then retry.'); return; }
    setUi(updated);
    void submitCreation(pending);
  };
  const createWorkspace = async () => {
    if (!ui.newTitle.trim()) { setError('Enter a title for the new story.'); return; }
    if (!ui.newText.trim()) { setError('Enter source text for the new story.'); return; }
    if (dirty && !window.confirm('This story has unsaved text. Create and switch workspaces while keeping the draft on this device?')) return;
    beginCreation('create', ui.newTitle.trim(), ui.newText, undefined, ui.newStyleSelectionSnapshotId);
  };
  const applyImport = async () => {
    if (!importPreview || busy || ui.pendingCreate) return;
    if (dirty && !window.confirm('This story has unsaved text. Apply the import as a new workspace and keep the current draft on this device?')) return;
    beginCreation('apply', ui.importTitle.trim() || importPreview.filename, importPreview.text, importPreview.import_id, ui.importStyleSelectionSnapshotId);
  };
  const loadMoreWorkspaces = async () => { if (workspaceOffset == null) return; try { const page = await listStoryWorkspaces(workspaceOffset); setWorkspaces(prev => [...prev, ...(page.items || [])]); const next = page.offset + page.items.length; setWorkspaceOffset(next < page.total ? next : null); setWorkspaceTotal(page.total); } catch (e) { setError(`Could not load more workspaces: ${(e as Error).message}`); } };
  const loadMoreHistory = async () => { if (!workspace || revisionOffset == null) return; try { const page = await listStoryRevisions(idOf(workspace), revisionOffset); setRevisions(prev => [...prev, ...(page.items || [])]); const next = page.offset + page.items.length; setRevisionOffset(next < page.total ? next : null); setRevisionTotal(page.total); } catch (e) { setError(`Could not load revision history: ${(e as Error).message}`); } };
  const downloadDraft = () => { const value = text || importPreview?.text || ui.newText; const blob = new Blob([value], { type: 'text/plain;charset=utf-8' }); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `${workspace?.title || ui.importTitle || ui.newTitle || 'story-draft'}.txt`; link.click(); URL.revokeObjectURL(url); };

  return <div className="app-shell story-shell legacy-inner">
    <main className="main-content">
      <div className="content-wrap story-content"><div className="page-heading"><div><div className="eyebrow">WORKSPACE / STORY</div><h1>Story workspace</h1><p>Write and revise source text. Chat-assisted planning and production setup are still pending.</p></div><button className="quiet-button" onClick={() => void loadInitial().catch(e => setError((e as Error).message))} disabled={busy}><RefreshCw size={15}/> Refresh list</button></div>
        <div className="story-pending card"><Sparkles size={17}/><div><b>Planning setup is not connected</b><p>Production Type &amp; Style selection is available, but it is not linked to this story. Codex chat, story graph, and screenplay fields are not implemented in this slice. No annotations or setup values are inserted automatically. Production work requiring the connected screenplay and automation setup remains blocked.</p></div></div>
        {storageWarning && <div className="notice notice-warn" role="alert">Browser storage is unavailable or full. Drafts may not survive reload; download a text copy now. <button className="text-button" onClick={downloadDraft}>Download draft text</button></div>}
        {error && <div className="notice notice-warn" role="alert"><AlertTriangle size={15}/>{error}</div>}{notice && <div className="notice" role="status">{notice}</div>}
        {ui.pendingCreate && <div className="notice notice-warn" role="status"><div><b>{ui.pendingCreate.state === 'conflict' ? 'Creation key conflict' : 'Creation outcome needs recovery'}</b><p>{ui.pendingCreate.state === 'conflict' ? 'The server rejected this key for a different request. The original title, text, and style snapshot remain frozen; changed content cannot be sent with this key.' : ui.pendingCreate.state === 'not_found' ? 'A read-only lookup found no creation for this key. You may retry the exact frozen request.' : ui.pendingCreate.state === 'initializing' ? 'The server recorded this creation and is still initializing. Retry resumes the same frozen request.' : 'The POST outcome is unknown. Check server status before retrying.'}</p><small>Key {ui.pendingCreate.key} · {ui.pendingCreate.action} · frozen title “{ui.pendingCreate.title}” · {ui.pendingCreate.styleSelectionSnapshotId ? `style snapshot ${ui.pendingCreate.styleSelectionSnapshotId}` : 'no style selected'}</small></div><div className="creation-recovery-actions"><button className="quiet-button" onClick={() => void checkCreation()} disabled={busy || ui.pendingCreate.state === 'conflict'}>Check status</button>{(ui.pendingCreate.state === 'not_found' || ui.pendingCreate.state === 'initializing') && <button className="quiet-button" onClick={() => void submitCreation(ui.pendingCreate!)} disabled={busy}>Retry exact request</button>}</div></div>}
        <div className="story-columns">
          <aside className="story-tools"><section className="card story-panel"><div className="story-panel-title"><div><h2>Workspaces</h2><p>{workspaceTotal} saved stories.</p></div></div>{workspaces.length ? <ul className="workspace-list">{workspaces.map(item => <li key={idOf(item)}><button className={workspace && idOf(workspace) === idOf(item) ? 'workspace-choice selected' : 'workspace-choice'} onClick={() => void chooseWorkspace(item)} disabled={busy}><span>{item.title || 'Untitled story'}</span><small>{item.status === 'initializing' || !item.initialized ? 'Initializing · source not available' : `${item.current_revision_id || 'Revision unavailable'} · ${item.style_selection_snapshot_id ? `style ${item.style_selection_snapshot_id}` : 'no style pin'}`}</small></button></li>)}</ul> : <p className="muted-empty">No story workspaces loaded yet.</p>}{workspaceOffset != null && <button className="text-button" onClick={() => void loadMoreWorkspaces()} disabled={busy}>Load more workspaces</button>}</section>
            <section className="card story-panel"><h2>Create a story</h2><label htmlFor="new-story-title">Title</label><input id="new-story-title" value={ui.newTitle} onChange={e => persistUi({...ui,newTitle:e.target.value})} placeholder="Untitled story" disabled={busy}/><label htmlFor="new-story-text">Source text</label><textarea id="new-story-text" value={ui.newText} onChange={e => persistUi({...ui,newText:e.target.value})} placeholder="Start with any text you want to develop." disabled={busy}/><div className="story-style-choice"><label htmlFor="new-story-style">Production type &amp; style <span>Optional · pinned at creation</span></label><select id="new-story-style" value={ui.newStyleSelectionSnapshotId || ''} onChange={e => persistUi({...ui,newStyleSelectionSnapshotId:e.target.value || undefined})} disabled={busy || !!ui.pendingCreate}><option value="">No style pinned to this story</option>{retainedStyleOption(ui.newStyleSelectionSnapshotId)}{styleSelections.map(selection=><option key={selection.snapshot_id} value={selection.snapshot_id}>{styleOptionLabel(selection)}</option>)}</select><small>{styleChoiceStatus}</small><small>{selectedStyleDescription(ui.newStyleSelectionSnapshotId)}</small><button className="text-button" type="button" onClick={() => void refreshStyleSelections()} disabled={busy || styleSelectionState==='loading'}>Refresh saved styles</button></div><button className="generate-button" onClick={() => void createWorkspace()} disabled={busy || !!ui.pendingCreate || !ui.newTitle.trim()}><BookOpen size={15}/> Create workspace</button></section>
            <section className="card story-panel"><div className="story-panel-title"><div><h2>Import source</h2><p>TXT, Markdown, or PDF extraction</p></div><FileUp size={17}/></div><div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={e => {e.preventDefault();setDragging(true);}} onDragLeave={() => setDragging(false)} onDrop={onDrop}><FileUp size={19}/><span>Drop a file or choose one</span><label className="file-button">Choose file<input type="file" accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf" onChange={onFileChange} disabled={busy}/></label></div></section>
          </aside>
          <section className="story-editor-column">{importPreview && <section className="card import-preview"><div className="story-panel-title"><div><h2>Review extracted text</h2><p>Upload does not create a workspace. Confirm Apply import to save a new workspace.</p></div><FileUp size={17}/></div><dl className="import-facts"><div><dt>Original file</dt><dd>{importPreview.filename} · {importPreview.source_type}</dd></div><div><dt>Original file SHA-256</dt><dd className="hash-value">{importPreview.source_sha256}</dd></div>{importPreview.text_sha256 && <div><dt>Extracted text SHA-256</dt><dd className="hash-value">{importPreview.text_sha256}</dd></div>}{importPreview.source_type === 'pdf' && importPreview.pages?.length ? <div><dt>PDF pages</dt><dd>{importPreview.pages.length} · page spans shown in extracted text offsets</dd></div> : null}</dl>{importPreview.source_type === 'pdf' && importPreview.pages?.length ? <details className="page-spans"><summary>PDF page text spans</summary>{importPreview.pages.map(page => <span key={page.number}>Page {page.number}: {page.start_codepoint}–{page.end_codepoint}</span>)}</details> : null}{importPreview.warnings?.length > 0 && <div className="import-warnings"><b>Extraction notes</b><ul>{importPreview.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></div>}{ui.sourceHadCrLf && <div className="line-ending-note">This preview contains CRLF line endings. Browser text editing normalizes line endings to LF; editing and applying it may change text hashes.</div>}<label htmlFor="import-title">Workspace title</label><input id="import-title" value={ui.importTitle} onChange={e => persistUi({...ui,importTitle:e.target.value})} disabled={busy}/><label htmlFor="import-text">Editable extracted text</label><textarea id="import-text" value={importPreview.text} onChange={e => persistUi({...ui,importPreview:{...importPreview,text:e.target.value}})} disabled={busy}/><div className="story-style-choice"><label htmlFor="import-story-style">Production type &amp; style <span>Optional · pinned at creation</span></label><select id="import-story-style" value={ui.importStyleSelectionSnapshotId || ''} onChange={e => persistUi({...ui,importStyleSelectionSnapshotId:e.target.value || undefined})} disabled={busy || !!ui.pendingCreate}><option value="">No style pinned to this story</option>{retainedStyleOption(ui.importStyleSelectionSnapshotId)}{styleSelections.map(selection=><option key={selection.snapshot_id} value={selection.snapshot_id}>{styleOptionLabel(selection)}</option>)}</select><small>{styleChoiceStatus}</small><small>{selectedStyleDescription(ui.importStyleSelectionSnapshotId)}</small><button className="text-button" type="button" onClick={() => void refreshStyleSelections()} disabled={busy || styleSelectionState==='loading'}>Refresh saved styles</button></div><button className="generate-button" onClick={() => void applyImport()} disabled={busy || !!ui.pendingCreate}><BookOpen size={15}/> Apply import as new workspace</button></section>}
            <section className="card story-editor"><div className="story-panel-title"><div><h2>{workspace?.title || 'Choose or create a story'}</h2><p>{workspace ? workspace.status === 'initializing' || !currentRevision ? 'Initializing · source text is not available yet.' : `Draft base ${baseRevisionId}${baseRevisionId !== currentRevision.revision_id ? ` · server is at ${currentRevision.revision_id}` : ''}` : 'Select a workspace or create one to begin.'}</p></div>{workspace && <small className="story-style-pin"><b>Style pinned at original creation:</b> {stylePinLabel(workspace)}. This snapshot is metadata; it is not yet consumed by video generation.</small>}<div className="story-editor-actions"><button className="quiet-button" onClick={() => void reloadServer()} disabled={!workspace || busy}><RefreshCw size={14}/> Refresh workspace</button><button className="generate-button" onClick={() => void save()} disabled={!workspace || !currentRevision || !dirty || busy}><Save size={14}/> Save revision</button></div></div>{workspace && !currentRevision ? <div className="initializing-note" role="status"><RefreshCw size={16}/> This workspace is still initializing. Its source cannot be edited yet. Refresh workspace to check again.{text && <button className="text-button" onClick={downloadDraft}>Download retained local draft</button>}</div> : <><label className="sr-only" htmlFor="story-source">Story source text</label><textarea id="story-source" className="story-source" value={text} onChange={e => onText(e.target.value)} placeholder="Write or edit the source text here. It will not be transformed automatically." disabled={!workspace || busy}/><div className="story-editor-foot"><span>{dirty ? 'Unsaved local changes' : workspace ? 'Saved revision loaded' : 'No workspace selected'}</span>{workspace && <small>Local draft uses base revision {baseRevisionId}; saves create new revisions.</small>}</div></>}</section>
            <section className="card revision-panel"><div className="story-panel-title"><div><h2><History size={15}/> Revision history</h2><p>Restore creates a new child revision; it never rewrites history. {revisionTotal} revisions.</p></div></div>{revisions.length ? <ol className="revision-list">{revisions.map((revision, index) => <li key={`${revision.revision_id}-${index}`}><div><b>{revision.revision_id} · revision {revision.revision_number ?? '—'}</b><small>{revision.created_at || 'Saved revision'}</small><p>SHA-256 {revision.source_sha256}{revision.parent_revision_id ? ` · parent ${revision.parent_revision_id}` : ' · initial revision'}</p></div><button className="quiet-button" onClick={() => void restore(revision)} disabled={!workspace || !currentRevision || busy}><RotateCcw size={14}/> Restore</button></li>)}</ol> : <p className="muted-empty">No saved revisions to show.</p>}{workspace && revisionOffset != null && <button className="text-button" onClick={() => void loadMoreHistory()} disabled={busy}>Load more revisions</button>}</section>
          </section>
        </div>
      </div>
    </main>
  </div>;
}
