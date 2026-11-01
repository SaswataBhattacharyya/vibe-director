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
export type StyleSourceBlock = { locator:string; text:string };
export type StyleSource = { source_id:string; sha256:string; filename:string; source_type:'pdf'|'markdown'|'text'; byte_length:number; text_character_count:number; evidence_blocks?:StyleSourceBlock[]; deduplicated?:boolean };
export type DocumentStyleEvidence = {kind:'document';source_id:string;source_sha256:string;filename:string;locator:string;quote:string;intent:string};
export type StyleProposal = {status:'proposal';persisted:false;published:false;provider:string;display_name:string;guidance:string;evidence:DocumentStyleEvidence[]};
export type ImageStyleProposal = {status:'proposal';persisted:false;published:false;provider:string;display_name:string;guidance:string;evidence:{kind:'image'|'audio'|'video';asset_id:string;sha256:string;intent:string;quote?:string;locator?:string;analyzer_run_id?:string}[]};
export type DirectingStyle = { style_id:string; display_name:string; version:number; style_version_id?:string; guidance:string; style_hash:string; custom?:boolean; evidence?:Record<string,unknown>[]; scope_type?:'cross_type'|'production_type'; production_type_scope?:string|null };
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
  directing_style?: DirectingStyle;
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
export const getStyleCatalog = () => json<StyleCatalog & { directing_styles:DirectingStyle[] }>('/api/styles/catalog');
export const getStyleSelections = (context: string, workspace_id?: string) => json<{ selections: StyleSelection[] }>(`/api/styles/selections?${workspace_id ? `workspace_id=${encodeURIComponent(workspace_id)}` : `isolated_context_id=${encodeURIComponent(context)}`}`);
export const saveStyleSelection = (isolated_context_id: string, production_type: string, style_version_id: string, directing_style_id:string, directing_style_version_id?:string, workspace_id?: string) => json<StyleSelection>('/api/styles/selections', post({ ...(workspace_id ? { workspace_id } : { isolated_context_id }), production_type, style_version_id, directing_style_id, directing_style_version_id }));
export const publishProductionType = async (production_type: string, narrative_guidance: Record<string, string>, director_profile: DirectorProfile): Promise<ProductionStyle> => {
  const record = await json<Omit<ProductionStyle, 'display_name' | 'custom'> & { display_name?: string; custom?: boolean }>('/api/styles/types', post({ production_type, narrative_guidance, director_profile }));
  return { ...record, display_name: record.display_name || record.director_profile.display_name, custom: true };
};
export type DirectingStyleEvidence = {asset_id:string;kind:'image'|'audio'|'video';sha256:string;intent:string;locator?:string;quote?:string;analyzer_run_id?:string} | DocumentStyleEvidence;
export const publishDirectingStyle = (isolated_context_id:string, style_id:string, display_name:string, guidance:string, evidence:DirectingStyleEvidence[], scope_type:'cross_type'|'production_type'='cross_type', production_type_scope?:string) => json<DirectingStyle>('/api/styles/directing-styles', post({isolated_context_id, style_id, display_name, guidance, evidence, scope_type, production_type_scope}));
export const listStyleSources = (context:string) => json<{sources:StyleSource[]}>(`/api/styles/sources?isolated_context_id=${encodeURIComponent(context)}`);
export const getStyleSource = (context:string, sourceId:string) => json<StyleSource>(`/api/styles/sources/${encodeURIComponent(sourceId)}?isolated_context_id=${encodeURIComponent(context)}`);
export const analyzeStyleSources = (context:string, source_ids:string[], user_intent:string) => json<StyleProposal>('/api/styles/sources/analyze',post({isolated_context_id:context,source_ids,user_intent}));
export const analyzeStyleImages = (context:string, asset_ids:string[], user_intent:string) => json<ImageStyleProposal>('/api/styles/media/analyze',post({isolated_context_id:context,asset_ids,user_intent}));
export async function uploadStyleSource(context:string, file:File):Promise<StyleSource> {
  const response = await fetch(`/api/styles/sources?isolated_context_id=${encodeURIComponent(context)}`, {
    method:'POST', headers:{'Content-Type':'application/octet-stream','X-File-Name':encodeURIComponent(file.name),Accept:'application/json'}, body:file,
  });
  if (!response.ok) { let message=`Request failed (${response.status}).`; try { const data=await response.json(); message=data.error?.message||message; } catch { /* retain status */ } throw new Error(String(message)); }
  return response.json();
}
