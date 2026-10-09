export type DirectorProfile = {
  display_name: string;
  purpose: string;
  behavior: string[];
  review_priorities: string[];
};
export type ProductionStyle = {
  production_type: string;
  display_name: string;
  style_version: number | string;
  style_version_id: string;
  narrative_guidance: Record<string, unknown>;
  narrative_hash: string;
  director_profile: DirectorProfile;
  director_profile_hash: string;
  director_profile_version?: string;
  custom: boolean;
};
export type StyleCatalog = { catalog_version: string; production_types: ProductionStyle[] };
export type StyleSelection = {
  snapshot_id: string;
  isolated_context_id?: string;
  production_type: string;
  style_version_id: string;
  style_version?: string | number;
  narrative_guidance: Record<string, unknown>;
  narrative_hash: string;
  director_profile: DirectorProfile;
  director_profile_hash: string;
  custom?: boolean;
  created_at?: string;
};
async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try { const data = await response.json(); message = data.error?.message || data.message || message; } catch { /* keep status */ }
    throw new Error(String(message));
  }
  return response.json();
}
const post = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(body) });
export const getStyleCatalog = () => json<StyleCatalog>('/api/styles/catalog');
export const getStyleSelections = (context: string) => json<{ selections: StyleSelection[] }>(`/api/styles/selections?isolated_context_id=${encodeURIComponent(context)}`);
export const saveStyleSelection = (isolated_context_id: string, production_type: string, style_version_id: string) => json<StyleSelection>('/api/styles/selections', post({ isolated_context_id, production_type, style_version_id }));
export const publishProductionType = async (production_type: string, narrative_guidance: Record<string, string>, director_profile: DirectorProfile): Promise<ProductionStyle> => {
  const record = await json<Omit<ProductionStyle, 'display_name' | 'custom'> & { display_name?: string; custom?: boolean }>('/api/styles/types', post({ production_type, narrative_guidance, director_profile }));
  return { ...record, display_name: record.display_name || record.director_profile.display_name, custom: true };
};
