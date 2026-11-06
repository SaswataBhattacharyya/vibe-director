import type {AgentContext} from './agent-context';
export type AgentTool = {
  id: string; effect: 'read' | 'draft' | 'submit' | 'external' | 'destructive';
  input_schema: Record<string, unknown>; status: 'available' | 'blocked' | 'unknown' | 'navigation_only';
  execution_enabled: boolean; reason?: string;
};
export type AgentSkill = {
  ref: string; id: string; scope: 'global' | 'application' | 'project'; provider: string;
  description: string; sha256: string | null; version: string | null; available: boolean; reason?: string;
};
export type AgentDiscovery = {tools: AgentTool[]; skills: AgentSkill[]; context: AgentContext; skillsTruncated: boolean};
async function read<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`/api/agent/${path}`, {signal});
  const value = await response.json();
  if (!response.ok) throw new Error(value?.error?.message || 'Agent discovery failed.');
  return value;
}
export async function discoverAgent(workspace: string, signal: AbortSignal): Promise<AgentDiscovery> {
  const owner = encodeURIComponent(workspace);
  const [tools, skills, context] = await Promise.all([
    read<{tools: AgentTool[]}>(`tools?workspace_id=${owner}`, signal),
    read<{skills: AgentSkill[]; truncated: boolean}>(`skills?workspace_id=${owner}`, signal),
    read<AgentContext>(`projects/${owner}/context`, signal),
  ]);
  if (context.workspace_id !== workspace || context.nodes.some(node => node.owner !== workspace)) {
    throw new Error('Agent discovery returned a different project.');
  }
  return {tools: tools.tools, skills: skills.skills, context, skillsTruncated: skills.truncated};
}
