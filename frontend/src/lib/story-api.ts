export type StoryRevision = { revision_id: string; source_text: string; source_sha256?: string; created_at?: string; parent_revision_id?: string | null; revision_number?: number };
export type StoryRevisionSummary = { revision_id: string; source_sha256: string; created_at?: string; parent_revision_id?: string | null; revision_number?: number; metadata?: Record<string, unknown> };
export type StoryWorkspace = { workspace_id: string; title: string; current_revision_id?: string | null; current_revision?: StoryRevision; initialized?: boolean; status?: 'ready' | 'initializing' | string; updated_at?: string };
export type Page<T> = { items: T[]; limit: number; offset: number; total: number };
export type StoryImportPage = { number: number; start_codepoint: number; end_codepoint: number; line_start?: number; line_end?: number };
export type StoryImport = { import_id: string; filename: string; source_type: string; source_sha256: string; text_sha256?: string; text: string; warnings: string[]; pages?: StoryImportPage[] | null };

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
const body = (value: unknown) => ({ method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(value) });
export const listStoryWorkspaces = (offset = 0, limit = 50) => json<Page<StoryWorkspace>>(`/api/story/workspaces?limit=${limit}&offset=${offset}`);
export const createStoryWorkspace = (title: string, source_text: string) => json<StoryWorkspace>('/api/story/workspaces', body({ title, source_text }));
export const getStoryWorkspace = (id: string) => json<StoryWorkspace>(`/api/story/workspaces/${encodeURIComponent(id)}`);
export const saveStoryRevision = (id: string, source_text: string, expected_current_revision_id: string) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/revisions`, body({ source_text, expected_current_revision_id }));
export const listStoryRevisions = (id: string, offset = 0, limit = 50) => json<Page<StoryRevisionSummary>>(`/api/story/workspaces/${encodeURIComponent(id)}/revisions?limit=${limit}&offset=${offset}`);
export const restoreStoryRevision = (id: string, revision_id: string, expected_current_revision_id: string) => json<StoryRevision>(`/api/story/workspaces/${encodeURIComponent(id)}/restore`, body({ revision_id, expected_current_revision_id }));
export const uploadStoryFile = (file: File) => json<StoryImport>(`/api/story/imports?filename=${encodeURIComponent(file.name)}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', Accept: 'application/json' }, body: file });
export const applyStoryImport = (id: string, title: string, source_text: string) => json<StoryWorkspace>(`/api/story/imports/${encodeURIComponent(id)}/apply`, body({ title, source_text }));
