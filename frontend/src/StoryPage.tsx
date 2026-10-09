import { ChangeEvent, DragEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, BookOpen, FileUp, History, RefreshCw, RotateCcw, Save, Sparkles } from 'lucide-react';
import { acceptStoryEdit, applyStoryImport, buildStoryGraph, createStoryWorkspace, discardStoryEdit, getStoryCreation, getStoryEditRequest, getStoryGraph, getStoryWorkspace, listStoryRevisions, listStoryWorkspaces, proposeStoryEdit, restoreStoryRevision, saveStoryRevision, StoryCreation, StoryEditProposal, StoryGraph, StoryGraphRecord, StoryImport, StoryRevision, StoryRevisionSummary, StoryWorkspace, updateStoryGraphRecord, uploadStoryFile } from './lib/story-api';
import { getStyleSelections, StyleSelection } from './lib/styles-api';

const LOCAL_KEY = 'vibe-story-draft-v1';
const UI_KEY = 'vibe-story-ui-draft-v1';
const STYLE_CONTEXT_KEY = 'vibe-style-setup-context-v1';
type LocalDraft = { workspaceId: string; sourceText: string; baseRevisionId: string };
type PendingCreate = { action: 'create' | 'apply'; key: string; state: 'unresolved' | 'not_found' | 'initializing' | 'conflict'; importId?: string; title: string; sourceText: string; styleSelectionSnapshotId?: string };
type LocalUi = { importPreview: StoryImport | null; importTitle: string; newTitle: string; newText: string; sourceHadCrLf: boolean; newStyleSelectionSnapshotId?: string; importStyleSelectionSnapshotId?: string; pendingCreate?: PendingCreate; editProposal?: StoryEditProposal; editRequest?: { key: string; workspace_id: string; state: 'submitting' | 'uncertain' } };
const emptyUi: LocalUi = { importPreview: null, importTitle: '', newTitle: '', newText: '', sourceHadCrLf: false };
const idOf = (workspace: StoryWorkspace) => workspace.workspace_id;
const normalizeWorkspace = (workspace: StoryWorkspace): StoryWorkspace => ({ ...workspace, current_revision_id: workspace.current_revision_id || workspace.current_revision?.revision_id || null });
function readObject<T>(key: string, fallback: T): T { try { const value = localStorage.getItem(key); return value ? JSON.parse(value) as T : fallback; } catch { return fallback; } }
function readDrafts(): Record<string, LocalDraft> { return readObject(LOCAL_KEY, {}); }
function safeStore(key: string, value: string): boolean { try { localStorage.setItem(key, value); return true; } catch { return false; } }
const summaryOf = (revision: StoryRevision): StoryRevisionSummary => ({ revision_id: revision.revision_id, source_sha256: revision.source_sha256 || '', created_at: revision.created_at, parent_revision_id: revision.parent_revision_id, revision_number: revision.revision_number });
const styleLabel = (selection: StyleSelection) => `${selection.director_profile?.display_name || selection.production_type} · v${selection.style_version ?? selection.style_version_id}`;
const styleOptionLabel = (selection: StyleSelection) => `${styleLabel(selection)} · saved ${selection.created_at ? new Date(selection.created_at).toLocaleString() : 'snapshot'}`;
const stylePinLabel = (workspace: StoryWorkspace) => workspace.style_selection ? styleLabel(workspace.style_selection) : workspace.style_selection_snapshot_id ? `Snapshot ${workspace.style_selection_snapshot_id} (details unavailable)` : 'None';

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
  const [ui, setUi] = useState<LocalUi>(() => {
    const saved = readObject<LocalUi>(UI_KEY, emptyUi);
    if (saved.editRequest && !saved.editRequest.workspace_id) {
      const workspaceId = saved.editProposal?.workspace_id || (() => { try { return localStorage.getItem('vibe-story-selected-v1') || ''; } catch { return ''; } })();
      if (workspaceId) saved.editRequest.workspace_id = workspaceId;
    }
    return saved;
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [storageWarning, setStorageWarning] = useState(false);
  const [styleSelections, setStyleSelections] = useState<StyleSelection[]>([]);
  const [styleSelectionState, setStyleSelectionState] = useState<'loading'|'ready'|'missing_context'|'unavailable'>('loading');
  const [dragging, setDragging] = useState(false);
  const [selectedText, setSelectedText] = useState<{ start: number; end: number; quote: string }>({ start: 0, end: 0, quote: '' });
  const [editInstruction, setEditInstruction] = useState('');
  const [storyGraph, setStoryGraph] = useState<StoryGraph | null>(null);
  const [graphBusy, setGraphBusy] = useState(false);
  const [graphDrafts, setGraphDrafts] = useState<Record<string, { name: string; detail: string; status: StoryGraphRecord['status'] }>>({});
  const sourceRef = useRef<HTMLTextAreaElement>(null);
  const currentRevision = workspace?.current_revision;
  const dirty = useMemo(() => !!workspace && !!currentRevision && text !== currentRevision.source_text, [workspace, currentRevision, text]);
  const importPreview = ui.importPreview;
  const retainedStyleOption = (snapshotId?: string) => snapshotId && !styleSelections.some(selection => selection.snapshot_id === snapshotId) ? <option value={snapshotId}>Previously selected snapshot · {snapshotId} · currently unavailable</option> : null;
  const selectedStyleDescription = (snapshotId?: string) => {
    if (!snapshotId) return '';
    const choice = styleSelections.find(selection => selection.snapshot_id === snapshotId);
    return choice ? `${choice.director_profile?.purpose || choice.production_type}` : 'Selected style is unavailable. Refresh to check again.';
  };
  const styleChoiceStatus = styleSelectionState === 'loading' ? 'Loading saved style selections…' : styleSelectionState === 'missing_context' ? 'Save a style in Type & Style, or continue without one.' : styleSelectionState === 'unavailable' ? 'Styles could not load. Refresh to try again.' : styleSelections.length ? '' : 'No saved styles.';
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
  const loadGraph = useCallback(async () => {
    if (!workspace || !currentRevision) { setStoryGraph(null); return; }
    try {
      const graph = await getStoryGraph(idOf(workspace), currentRevision.revision_id);
      setStoryGraph(graph);
      setGraphDrafts(Object.fromEntries(graph.records.map(record => [record.record_id, { name: record.name, detail: record.detail, status: record.status }])));
    } catch (e) {
      if ((e as Error & { status?: number }).status === 404) setStoryGraph(null);
      else setError(`Could not load the source graph: ${(e as Error).message}`);
    }
  }, [workspace?.workspace_id, currentRevision?.revision_id]);
  useEffect(() => { void loadGraph(); }, [loadGraph]);
  const generateGraph = async () => {
    if (!workspace || !currentRevision || dirty || graphBusy) return;
    setGraphBusy(true); setError('');
    try {
      const key = storyGraph?.source_revision_id === currentRevision.revision_id
        ? storyGraph.idempotency_key : crypto.randomUUID();
      const graph = await buildStoryGraph(idOf(workspace), currentRevision.revision_id, key);
      setStoryGraph(graph);
      setGraphDrafts(Object.fromEntries(graph.records.map(record => [record.record_id, { name: record.name, detail: record.detail, status: record.status }])));
      setNotice(graph.status === 'complete' ? 'Every source chunk has a processed graph result. Semantic completeness and contradictions still need review.' : graph.status === 'processing' ? 'A graph request is still active. Check again later; an active provider call will not be replaced.' : 'Graph extraction is partial. Completed chunks are saved; uncertain provider calls will not be repeated with this key.');
    } catch (e) { setError(`Graph extraction could not be confirmed: ${(e as Error).message}. Refresh the graph to recover its durable state.`); }
    finally { setGraphBusy(false); }
  };
  const saveGraphRecord = async (recordId: string) => {
    if (!workspace || !storyGraph) return;
    const draft = graphDrafts[recordId]; if (!draft) return;
    setGraphBusy(true);
    try {
      const saved = await updateStoryGraphRecord(idOf(workspace), recordId, draft);
      setStoryGraph({ ...storyGraph, records: storyGraph.records.map(record => record.record_id === recordId ? { ...record, ...saved } : record) });
      setNotice('Graph record saved as user-authored review. Its original evidence remains attached.');
    } catch (e) { setError(`Could not save graph review: ${(e as Error).message}`); }
    finally { setGraphBusy(false); }
  };
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
      setNotice(sourceUnavailable ? 'Creation is confirmed. The live source could not be loaded; refresh the workspace to retrieve it.' : 'Story creation is confirmed.');
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
    const editWorkspaceId = ui.editRequest?.workspace_id || ui.editProposal?.workspace_id;
    if (editWorkspaceId) await loadWorkspace(editWorkspaceId);
    else if (selectedId && page.items?.some(item => idOf(item) === selectedId)) await loadWorkspace(selectedId);
  }, [loadWorkspace, ui.editRequest?.workspace_id, ui.editProposal?.workspace_id]);
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
  useEffect(() => {
    const pending = ui.editRequest;
    if (!pending || !workspace || pending.workspace_id !== workspace.workspace_id || !['submitting', 'uncertain'].includes(pending.state)) return;
    let active = true;
    void getStoryEditRequest(pending.key).then(result => {
      if (!active) return;
      if (result.proposal && result.workspace_id === pending.workspace_id && result.proposal.workspace_id === pending.workspace_id) persistUi({ ...ui, editRequest: undefined, editProposal: result.proposal });
      else if (result.status !== 'not_found') persistUi({ ...ui, editRequest: { ...pending, state: 'uncertain' } });
    }).catch(() => { if (active) persistUi({ ...ui, editRequest: { ...pending, state: 'uncertain' } }); });
    return () => { active = false; };
  }, [workspace?.workspace_id, ui.editRequest?.key]);

  const chooseWorkspace = async (target: StoryWorkspace) => {
    if (workspace && idOf(workspace) === idOf(target)) return;
    const editWorkspaceId = ui.editRequest?.workspace_id || ui.editProposal?.workspace_id;
    if (editWorkspaceId) { setNotice('Resolve or discard this edit before switching workspaces.'); return; }
    if (dirty && !window.confirm('This story has unsaved text. Switch workspaces and keep this draft on this device?')) return;
    setBusy(true); setError('');
    try { await loadWorkspace(idOf(target)); }
    catch (e) { setError(`Could not open workspace: ${(e as Error).message}`); }
    finally { setBusy(false); }
  };
  const onText = (value: string) => { setText(value); setSelectedText({ start: 0, end: 0, quote: '' }); if (workspace) rememberDraft(idOf(workspace), value, baseRevisionId); };
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
  const captureSelection = () => {
    const node = sourceRef.current;
    if (!node || node.selectionStart === node.selectionEnd) { setSelectedText({ start: 0, end: 0, quote: '' }); return; }
    const start = Array.from(text.slice(0, node.selectionStart)).length;
    const end = start + Array.from(text.slice(node.selectionStart, node.selectionEnd)).length;
    setSelectedText({ start, end, quote: text.slice(node.selectionStart, node.selectionEnd) });
  };
  const requestSelectedEdit = async () => {
    if (!workspace || !currentRevision || !selectedText.quote || !editInstruction.trim() || dirty || busy || ui.editRequest || ui.editProposal) return;
    const pending = { key: crypto.randomUUID(), workspace_id: idOf(workspace), state: 'submitting' as const };
    const nextUi = { ...ui, editRequest: pending, editProposal: undefined };
    if (!safeStore(UI_KEY, JSON.stringify(nextUi))) { setStorageWarning(true); setError('The recovery key could not be saved locally, so the edit was not sent.'); return; }
    setUi(nextUi); setBusy(true); setError(''); setNotice('Preparing an edit proposal. Only the selected passage and your instruction are sent to Codex.');
    try {
      const proposal = await proposeStoryEdit(idOf(workspace), { base_revision_id: currentRevision.revision_id,
        start_codepoint: selectedText.start, end_codepoint: selectedText.end, expected_text: selectedText.quote,
        instruction: editInstruction, idempotency_key: pending.key });
      if (proposal.workspace_id !== pending.workspace_id) throw new Error('Server returned a proposal for a different workspace.');
      persistUi({ ...nextUi, editRequest: undefined, editProposal: proposal });
      setNotice('Proposal ready. Review the exact passage change before accepting it.');
    } catch (e) {
      const pendingUi = { ...nextUi, editRequest: { ...pending, state: 'uncertain' as const } };
      persistUi(pendingUi);
      setError(`Proposal status is unconfirmed: ${(e as Error).message}. Check status before starting another request; this key will not submit twice.`);
    } finally { setBusy(false); }
  };
  const reviewEdit = async (accept: boolean) => {
    if (!workspace || !currentRevision || !ui.editProposal || ui.editProposal.workspace_id !== idOf(workspace) || busy) return;
    setBusy(true); setError('');
    try {
      if (accept) {
        const revision = await acceptStoryEdit(idOf(workspace), ui.editProposal.proposal_id, currentRevision.revision_id);
        const updated = { ...workspace, current_revision_id: revision.revision_id, current_revision: revision, initialized: true, status: 'ready' };
        setWorkspace(updated); setBaseRevisionId(revision.revision_id); setText(revision.source_text); rememberDraft(idOf(updated), revision.source_text, revision.revision_id);
        setRevisions(prev => [summaryOf(revision), ...prev]); setRevisionTotal(n => n + 1);
        setNotice('Accepted as a new story revision.');
      } else {
        await discardStoryEdit(idOf(workspace), ui.editProposal.proposal_id); setNotice('Proposal discarded.');
      }
      persistUi({ ...ui, editProposal: undefined, editRequest: undefined });
    } catch (e) { setError((e as Error & { status?: number }).status === 409 ? 'The story changed after this proposal was made. Reload the latest revision before accepting it.' : `Could not update proposal: ${(e as Error).message}`); }
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
    if (ui.editRequest || ui.editProposal) { setNotice('Resolve or discard this edit before creating or opening another workspace.'); return; }
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
      <div className="content-wrap story-content"><div className="page-heading"><div><div className="eyebrow">WORKSPACE / STORY</div><h1>Story</h1></div><button className="quiet-button" onClick={() => void loadInitial().catch(e => setError((e as Error).message))} disabled={busy}><RefreshCw size={15}/> Refresh list</button></div>
        <div className="story-pending card"><Sparkles size={17}/><div><b>Selected passage editing</b><p>Select text in the story, enter an instruction and review the proposed replacement. Codex receives only that passage and instruction.</p></div></div>
        <section className="card story-graph" aria-label="Source-linked story graph">
          <div className="story-panel-title"><div><h2>Story graph</h2><p>{storyGraph ? `Snapshot ${storyGraph.snapshot_id} · source ${storyGraph.source_revision_id} · ${storyGraph.chunk_complete}/${storyGraph.chunk_total} chunks processed` : 'Extract reviewable entities, facts, events, time and relationships from every source chunk.'}</p></div><div className="story-editor-actions"><button className="quiet-button" onClick={() => void loadGraph()} disabled={!workspace || graphBusy}>Refresh graph</button><button className="generate-button" onClick={() => void generateGraph()} disabled={!workspace || !currentRevision || dirty || graphBusy}>{graphBusy ? 'Processing…' : storyGraph?.status === 'processing' ? 'Check/recover graph' : storyGraph?.chunks.some(chunk => chunk.state === 'failed') ? 'Retry failed chunks' : storyGraph?.status === 'partial' ? 'Check partial graph' : storyGraph ? 'Recheck graph' : 'Generate graph'}</button></div></div>
          <p className="graph-disclosure">Graph records retain exact source quotes and revision-bound spans. Cited character coverage helps locate uncited passages; it does not prove semantic completeness. Cross-chunk contradictions still need review.</p>
          {storyGraph && <><div className="story-editor-foot"><span>{storyGraph.status} · {storyGraph.coverage_state}</span><small>Contradictions: {storyGraph.contradiction_state} · {storyGraph.provider}{storyGraph.model ? ` / ${storyGraph.model}` : ''}</small></div><div className="graph-disclosure">Source text with evidence: {storyGraph.source_span_coverage.cited_chars.toLocaleString()} / {storyGraph.source_span_coverage.source_chars.toLocaleString()} characters ({storyGraph.source_span_coverage.percent}%). {storyGraph.source_span_coverage.uncovered_range_count.toLocaleString()} uncited ranges.</div>{storyGraph.source_span_coverage.uncovered_ranges.length > 0 && <details><summary>Review uncited passages{storyGraph.source_span_coverage.uncovered_ranges_omitted ? ` · first ${storyGraph.source_span_coverage.uncovered_ranges.length} of ${storyGraph.source_span_coverage.uncovered_range_count}` : ''}</summary><ol>{storyGraph.source_span_coverage.uncovered_ranges.map(range => <li key={`${range.start_codepoint}-${range.end_codepoint}`}><small>{range.start_codepoint}:{range.end_codepoint}</small><blockquote>{range.preview}{range.end_codepoint - range.start_codepoint > Array.from(range.preview).length ? '…' : ''}</blockquote></li>)}</ol></details>}<div className="graph-chunks">{storyGraph.chunks.map(chunk => <span key={chunk.chunk_id} title={chunk.error_message || ''}>{chunk.chunk_id}: {chunk.state}</span>)}</div><div className="graph-records">{storyGraph.records.map(record => { const draft = graphDrafts[record.record_id] || { name: record.name, detail: record.detail, status: record.status }; const entityLabel = (id?: string | null) => storyGraph.records.find(candidate => candidate.record_id === id)?.name || id; return <article className="graph-record" key={record.record_id}><div className="graph-record-heading"><b>{record.kind} · {record.type}</b><small>{record.status}{record.confidence == null ? '' : ` · ${Math.round(record.confidence * 100)}%`}</small></div><label>Record<input value={draft.name} onChange={event => setGraphDrafts(prev => ({ ...prev, [record.record_id]: { ...draft, name: event.target.value } }))}/></label><label>Notes<input value={draft.detail} onChange={event => setGraphDrafts(prev => ({ ...prev, [record.record_id]: { ...draft, name: draft.name, detail: event.target.value } }))}/></label><label>Review status<select value={draft.status} onChange={event => setGraphDrafts(prev => ({ ...prev, [record.record_id]: { ...draft, status: event.target.value as StoryGraphRecord['status'] } }))}><option value="source_supported">Source supported</option><option value="inferred">Inferred</option><option value="user_authored">User authored</option><option value="unresolved">Unresolved</option></select></label>{record.predicate && <p>{entityLabel(record.subject_id)} —{record.predicate}→ {entityLabel(record.object_id)}</p>}{record.evidence.map((evidence, index) => <blockquote key={`${evidence.chunk_id}-${index}`}><q>{evidence.quote}</q><small>{evidence.source_revision_id} · {evidence.start_codepoint}:{evidence.end_codepoint} · {evidence.chunk_id}</small></blockquote>)}<button className="quiet-button" onClick={() => void saveGraphRecord(record.record_id)} disabled={graphBusy}>Save review</button></article>; })}{!storyGraph.records.length && storyGraph.status === 'complete' && <p>No graph records were returned for this revision.</p>}</div></>}
        </section>
        {storageWarning && <div className="notice notice-warn" role="alert">Browser storage is unavailable or full. Drafts may not survive reload; download a text copy now. <button className="text-button" onClick={downloadDraft}>Download draft text</button></div>}
        {error && <div className="notice notice-warn" role="alert"><AlertTriangle size={15}/>{error}</div>}{notice && <div className="notice" role="status">{notice}</div>}
        {ui.pendingCreate && <div className="notice notice-warn" role="status"><div><b>{ui.pendingCreate.state === 'conflict' ? 'Creation key conflict' : 'Creation outcome needs recovery'}</b><p>{ui.pendingCreate.state === 'conflict' ? 'The server rejected this key for a different request. The original title, text, and style snapshot remain frozen; changed content cannot be sent with this key.' : ui.pendingCreate.state === 'not_found' ? 'A read-only lookup found no creation for this key. You may retry the exact frozen request.' : ui.pendingCreate.state === 'initializing' ? 'The server recorded this creation and is still initializing. Retry resumes the same frozen request.' : 'The POST outcome is unknown. Check server status before retrying.'}</p><small>Key {ui.pendingCreate.key} · {ui.pendingCreate.action} · frozen title “{ui.pendingCreate.title}” · {ui.pendingCreate.styleSelectionSnapshotId ? `style snapshot ${ui.pendingCreate.styleSelectionSnapshotId}` : 'no style selected'}</small></div><div className="creation-recovery-actions"><button className="quiet-button" onClick={() => void checkCreation()} disabled={busy || ui.pendingCreate.state === 'conflict'}>Check status</button>{(ui.pendingCreate.state === 'not_found' || ui.pendingCreate.state === 'initializing') && <button className="quiet-button" onClick={() => void submitCreation(ui.pendingCreate!)} disabled={busy}>Retry exact request</button>}</div></div>}
        <div className="story-columns">
          <aside className="story-tools"><section className="card story-panel"><div className="story-panel-title"><div><h2>Workspaces</h2><p>{workspaceTotal} saved stories.</p></div></div>{workspaces.length ? <ul className="workspace-list">{workspaces.map(item => <li key={idOf(item)}><button className={workspace && idOf(workspace) === idOf(item) ? 'workspace-choice selected' : 'workspace-choice'} onClick={() => void chooseWorkspace(item)} disabled={busy}><span>{item.title || 'Untitled story'}</span><small>{item.status === 'initializing' || !item.initialized ? 'Initializing · source not available' : 'Saved'}</small></button></li>)}</ul> : <p className="muted-empty">No saved stories.</p>}{workspaceOffset != null && <button className="text-button" onClick={() => void loadMoreWorkspaces()} disabled={busy}>Load more workspaces</button>}</section>
            <section className="card story-panel"><h2>Create a story</h2><label htmlFor="new-story-title">Title</label><input id="new-story-title" value={ui.newTitle} onChange={e => persistUi({...ui,newTitle:e.target.value})} placeholder="Untitled story" disabled={busy}/><label htmlFor="new-story-text">Source text</label><textarea id="new-story-text" value={ui.newText} onChange={e => persistUi({...ui,newText:e.target.value})} placeholder="Paste or write your story." disabled={busy}/><div className="story-style-choice"><label htmlFor="new-story-style">Production type &amp; style <span>Optional</span></label><select id="new-story-style" value={ui.newStyleSelectionSnapshotId || ''} onChange={e => persistUi({...ui,newStyleSelectionSnapshotId:e.target.value || undefined})} disabled={busy || !!ui.pendingCreate}><option value="">No style</option>{retainedStyleOption(ui.newStyleSelectionSnapshotId)}{styleSelections.map(selection=><option key={selection.snapshot_id} value={selection.snapshot_id}>{styleOptionLabel(selection)}</option>)}</select><small>{styleChoiceStatus}</small>{ui.newStyleSelectionSnapshotId && <small>{selectedStyleDescription(ui.newStyleSelectionSnapshotId)}</small>}<button className="text-button" type="button" onClick={() => void refreshStyleSelections()} disabled={busy || styleSelectionState==='loading'}>Refresh saved styles</button></div><button className="generate-button" onClick={() => void createWorkspace()} disabled={busy || !!ui.pendingCreate || !ui.newTitle.trim()}><BookOpen size={15}/> Create workspace</button></section>
            <section className="card story-panel"><div className="story-panel-title"><div><h2>Import source</h2><p>TXT, Markdown, or PDF extraction</p></div><FileUp size={17}/></div><div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={e => {e.preventDefault();setDragging(true);}} onDragLeave={() => setDragging(false)} onDrop={onDrop}><FileUp size={19}/><span>Drop a file or choose one</span><label className="file-button">Choose file<input type="file" accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf" onChange={onFileChange} disabled={busy}/></label></div></section>
          </aside>
          <section className="story-editor-column">{importPreview && <section className="card import-preview"><div className="story-panel-title"><div><h2>Review extracted text</h2><p>Check the text, then apply it.</p></div><FileUp size={17}/></div><details><summary>File details</summary><dl className="import-facts"><div><dt>Original file</dt><dd>{importPreview.filename} · {importPreview.source_type}</dd></div><div><dt>Original file SHA-256</dt><dd className="hash-value">{importPreview.source_sha256}</dd></div>{importPreview.text_sha256 && <div><dt>Extracted text SHA-256</dt><dd className="hash-value">{importPreview.text_sha256}</dd></div>}{importPreview.source_type === 'pdf' && importPreview.pages?.length ? <div><dt>PDF pages</dt><dd>{importPreview.pages.length} · page spans shown in extracted text offsets</dd></div> : null}</dl></details>{importPreview.source_type === 'pdf' && importPreview.pages?.length ? <details className="page-spans"><summary>PDF page text spans</summary>{importPreview.pages.map(page => <span key={page.number}>Page {page.number}: {page.start_codepoint}–{page.end_codepoint}</span>)}</details> : null}{importPreview.warnings?.length > 0 && <div className="import-warnings"><b>Extraction notes</b><ul>{importPreview.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></div>}{ui.sourceHadCrLf && <div className="line-ending-note">This preview contains CRLF line endings. Browser text editing normalizes line endings to LF; editing and applying it may change text hashes.</div>}<label htmlFor="import-title">Workspace title</label><input id="import-title" value={ui.importTitle} onChange={e => persistUi({...ui,importTitle:e.target.value})} disabled={busy}/><label htmlFor="import-text">Editable extracted text</label><textarea id="import-text" value={importPreview.text} onChange={e => persistUi({...ui,importPreview:{...importPreview,text:e.target.value}})} disabled={busy}/><div className="story-style-choice"><label htmlFor="import-story-style">Production type &amp; style <span>Optional</span></label><select id="import-story-style" value={ui.importStyleSelectionSnapshotId || ''} onChange={e => persistUi({...ui,importStyleSelectionSnapshotId:e.target.value || undefined})} disabled={busy || !!ui.pendingCreate}><option value="">No style</option>{retainedStyleOption(ui.importStyleSelectionSnapshotId)}{styleSelections.map(selection=><option key={selection.snapshot_id} value={selection.snapshot_id}>{styleOptionLabel(selection)}</option>)}</select><small>{styleChoiceStatus}</small>{ui.importStyleSelectionSnapshotId && <small>{selectedStyleDescription(ui.importStyleSelectionSnapshotId)}</small>}<button className="text-button" type="button" onClick={() => void refreshStyleSelections()} disabled={busy || styleSelectionState==='loading'}>Refresh saved styles</button></div><button className="generate-button" onClick={() => void applyImport()} disabled={busy || !!ui.pendingCreate}><BookOpen size={15}/> Apply import</button></section>}
          <section className="card story-editor"><div className="story-panel-title"><div><h2>{workspace?.title || 'Choose or create a story'}</h2><p>{workspace ? workspace.status === 'initializing' || !currentRevision ? 'Initializing · source text is not available yet.' : baseRevisionId !== currentRevision.revision_id ? 'A newer revision exists. Refresh before saving.' : '' : 'Select a workspace or create one to begin.'}</p></div>{workspace && <small className="story-style-pin"><b>Style:</b> {stylePinLabel(workspace)}.</small>}<div className="story-editor-actions"><button className="quiet-button" onClick={() => void reloadServer()} disabled={!workspace || busy}><RefreshCw size={14}/> Refresh workspace</button><button className="generate-button" onClick={() => void save()} disabled={!workspace || !currentRevision || !dirty || busy}><Save size={14}/> Save revision</button></div></div>{workspace && !currentRevision ? <div className="initializing-note" role="status"><RefreshCw size={16}/> Story is loading. Refresh to check again.{text && <button className="text-button" onClick={downloadDraft}>Download retained local draft</button>}</div> : <><label className="sr-only" htmlFor="story-source">Story source text</label><textarea id="story-source" ref={sourceRef} className="story-source" value={text} onChange={e => onText(e.target.value)} onMouseUp={captureSelection} onKeyUp={captureSelection} placeholder="Write your story here." disabled={!workspace || busy}/><div className="story-editor-foot"><span>{dirty ? 'Unsaved local changes' : workspace ? 'Saved' : 'No workspace selected'}</span>{workspace && <small>Changes save as new revisions.</small>}</div><div className="selected-edit"><p>{selectedText.quote ? `Selected passage (${selectedText.quote.length} characters)` : 'Select a passage above to request a focused edit.'}</p><textarea aria-label="Edit instruction" value={editInstruction} onChange={e => setEditInstruction(e.target.value)} placeholder="What should change in this passage?" disabled={!workspace || busy}/><button className="generate-button" onClick={() => void requestSelectedEdit()} disabled={!selectedText.quote || !editInstruction.trim() || dirty || busy || !!ui.editRequest || !!ui.editProposal}><Sparkles size={14}/> Propose edit</button>{ui.editRequest && <p role="status">{ui.editRequest.state === 'submitting' ? 'Checking the saved request…' : 'Provider status is uncertain. It will not be resubmitted with this key.'}<button className="text-button" onClick={() => void getStoryEditRequest(ui.editRequest!.key).then(result => { if (result.proposal && result.workspace_id === ui.editRequest!.workspace_id && result.proposal.workspace_id === ui.editRequest!.workspace_id) persistUi({...ui,editRequest:undefined,editProposal:result.proposal}); }).catch(e => setError((e as Error).message))}>Check status</button></p>}</div>{ui.editProposal && ui.editProposal.workspace_id === workspace?.workspace_id && <div className="edit-proposal" aria-label="AI edit proposal"><b>Review proposal · {ui.editProposal.provider || 'Codex'}{ui.editProposal.model ? ` · ${ui.editProposal.model}` : ''}</b><p><strong>Before</strong><br/><span>{ui.editProposal.expected_text}</span></p><p><strong>After</strong><br/><span>{ui.editProposal.replacement}</span></p><p>{ui.editProposal.instruction}</p><button className="generate-button" onClick={() => void reviewEdit(true)} disabled={busy || dirty || currentRevision?.revision_id !== ui.editProposal.base_revision_id}>Accept as revision</button><button className="quiet-button" onClick={() => void reviewEdit(false)} disabled={busy}>Discard</button></div>}</>}</section>
            <section className="card revision-panel"><div className="story-panel-title"><div><h2><History size={15}/> Revision history</h2><p>{revisionTotal} revisions. Restoring keeps earlier versions.</p></div></div>{revisions.length ? <ol className="revision-list">{revisions.map((revision, index) => <li key={`${revision.revision_id}-${index}`}><div><b>{revision.revision_id} · revision {revision.revision_number ?? '—'}</b><small>{revision.created_at || 'Saved revision'}</small><p>SHA-256 {revision.source_sha256}{revision.parent_revision_id ? ` · parent ${revision.parent_revision_id}` : ' · initial revision'}</p></div><button className="quiet-button" onClick={() => void restore(revision)} disabled={!workspace || !currentRevision || busy}><RotateCcw size={14}/> Restore</button></li>)}</ol> : <p className="muted-empty">No saved revisions to show.</p>}{workspace && revisionOffset != null && <button className="text-button" onClick={() => void loadMoreHistory()} disabled={busy}>Load more revisions</button>}</section>
          </section>
        </div>
      </div>
    </main>
  </div>;
}
