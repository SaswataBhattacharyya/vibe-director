export type StoryRevision = { revision_id: string; source_text: string; source_sha256?: string; created_at?: string; parent_revision_id?: string | null; revision_number?: number };
export type StoryRevisionSummary = { revision_id: string; source_sha256: string; created_at?: string; parent_revision_id?: string | null; revision_number?: number; metadata?: Record<string, unknown> };
export type StoryWorkspace = { workspace_id: string; title: string; current_revision_id?: string | null; current_revision?: StoryRevision; created_revision?: StoryRevision; style_selection_snapshot_id?: string | null; style_selection?: import('./styles-api').StyleSelection | null; initialized?: boolean; status?: 'ready' | 'initializing' | string; updated_at?: string };
export type Page<T> = { items: T[]; limit: number; offset: number; total: number };
export type StoryImportPage = { number: number; start_codepoint: number; end_codepoint: number; line_start?: number; line_end?: number };
export type StoryImport = { import_id: string; filename: string; source_type: string; source_sha256: string; text_sha256?: string; text: string; warnings: string[]; pages?: StoryImportPage[] | null };
export type StoryCreation = { status: 'initializing' | 'ready'; idempotency_key: string; request_hash: string; workspace: StoryWorkspace & { created_revision?: StoryRevision } };
export type StoryEditProposal = { proposal_id: string; workspace_id: string; base_revision_id: string; start_codepoint: number; end_codepoint: number; expected_text: string; replacement: string; instruction: string; status: string; provider?: string; model?: string; ai_generated?: boolean; resulting_revision_id?: string | null };
export type StoryGraphEvidence = { source_revision_id: string; source_sha256: string; chunk_id: string; start_codepoint: number; end_codepoint: number; quote: string };
export type StoryGraphRecord = { record_id: string; kind: string; type: string; name: string; detail: string; subject_id?: string | null; object_id?: string | null; predicate?: string | null; status: 'source_supported'|'inferred'|'user_authored'|'unresolved'; confidence?: number | null; user_modified: boolean; properties: Record<string, unknown>; evidence: StoryGraphEvidence[] };
export type StoryGraph = { snapshot_id: string; idempotency_key: string; workspace_id: string; source_revision_id: string; source_sha256: string; status: string; coverage_state: string; contradiction_state: string; chunk_total: number; chunk_complete: number; provider: string; model?: string; semantic_coverage_claim: false; chunks: Array<{ chunk_id: string; chunk_index: number; state: string; error_message?: string | null }>; records: StoryGraphRecord[] };

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    let code: string | undefined;
    try { const payload = await response.json(); detail = payload.error?.message || payload.detail?.message || payload.detail || payload.message || detail; code = payload.error?.code; } catch { /* retain status message */ }
    const error = new Error(String(detail)) as Error & { status?: number; code?: string };
    error.status = response.status; error.code = code;
    throw error;
  }
  return response.json();
}
const body = (value: unknown, method = 'POST') => ({ method, headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(value) });
export const listStoryWorkspaces = (offset = 0, limit = 50) => json<Page<StoryWorkspace>>(`/api/story/workspaces?limit=${limit}&offset=${offset}`);
export const createStoryWorkspace = (title: string, source_text: string, idempotency_key: string, style_selection_snapshot_id?: string) => json<StoryCreation>('/api/story/workspaces', body({ title, source_text, idempotency_key, ...(style_selection_snapshot_id ? { style_selection_snapshot_id } : {}) }));
export const getStoryCreation = (key: string) => json<StoryCreation>(`/api/story/creations/by-idempotency/${encodeURIComponent(key)}`);
export const getStoryWorkspace = (id: string) => json<StoryWorkspace>(`/api/story/workspaces/${encodeURIComponent(id)}`);
export const saveStoryRevision = (id: string, source_text: string, expected_current_revision_id: string) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/revisions`, body({ source_text, expected_current_revision_id }));
export const listStoryRevisions = (id: string, offset = 0, limit = 50) => json<Page<StoryRevisionSummary>>(`/api/story/workspaces/${encodeURIComponent(id)}/revisions?limit=${limit}&offset=${offset}`);
export const restoreStoryRevision = (id: string, revision_id: string, expected_current_revision_id: string) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/restore`, body({ revision_id, expected_current_revision_id }));
export const uploadStoryFile = (file: File) => json<StoryImport>(`/api/story/imports?filename=${encodeURIComponent(file.name)}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', Accept: 'application/json' }, body: file });
export const applyStoryImport = (id: string, title: string, source_text: string, idempotency_key: string, style_selection_snapshot_id?: string) => json<StoryCreation>(`/api/story/imports/${encodeURIComponent(id)}/apply`, body({ title, source_text, idempotency_key, ...(style_selection_snapshot_id ? { style_selection_snapshot_id } : {}) }));
export const proposeStoryEdit = (id: string, input: { base_revision_id: string; start_codepoint: number; end_codepoint: number; expected_text: string; instruction: string; idempotency_key: string }) => json<StoryEditProposal>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals`, body(input));
export const getStoryEditRequest = (key: string) => json<{ status: string; workspace_id: string; proposal?: StoryEditProposal; recovery_message?: string }>(`/api/story/edit-requests/by-key/${encodeURIComponent(key)}`);
export const getStoryEditProposal = (id: string, proposalId: string) => json<StoryEditProposal>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals?id=${encodeURIComponent(proposalId)}`);
export const acceptStoryEdit = (id: string, proposal_id: string, expected_current_revision_id: string) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals/accept`, body({ proposal_id, expected_current_revision_id }));
export const discardStoryEdit = (id: string, proposal_id: string) => json<StoryEditProposal>(`/api/story/workspaces/${encodeURIComponent(id)}/edit-proposals/discard`, body({ proposal_id }));
export const buildStoryGraph = (id: string, source_revision_id: string, idempotency_key: string) => json<StoryGraph>(`/api/story/workspaces/${encodeURIComponent(id)}/graph`, body({ source_revision_id, idempotency_key }));
export const getStoryGraph = (id: string, source_revision_id: string) => json<StoryGraph>(`/api/story/workspaces/${encodeURIComponent(id)}/graph?revision_id=${encodeURIComponent(source_revision_id)}`);
export const updateStoryGraphRecord = (id: string, record_id: string, input: { name: string; detail: string; status: StoryGraphRecord['status'] }) => json<Pick<StoryGraphRecord, 'record_id'|'name'|'detail'|'status'|'user_modified'>>(`/api/story/workspaces/${encodeURIComponent(id)}/graph/records/${encodeURIComponent(record_id)}`, body(input, 'PATCH'));
