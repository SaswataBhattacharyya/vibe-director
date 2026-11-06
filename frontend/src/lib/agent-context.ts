export type AgentNode = {
  id: string; kind: 'workspace' | 'asset' | 'story_revision' | 'editor_session' | 'job';
  source_id: string; owner: string; revision: string | number | null; sha256: string | null;
  provenance: string; label: string;
};
export type AgentContext = {
  workspace_id: string; nodes: AgentNode[];
  relations: Array<{from: string; to: string; kind: string}>; truncated: string[];
};
