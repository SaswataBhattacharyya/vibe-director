import type { StoryWorkspace } from './story-api';

let activeProjectId: string | undefined;
export function setActiveProjectId(value:string){activeProjectId=value;}
export function managedProjectId(){return activeProjectId;}

const STORY_SELECTION_KEY = 'vibe-story-selected-v1';
const VIDEO_DRAFT_KEY = 'vibe-video-draft-v1';
const ACTIVE_MEDIA_WORKSPACE_KEY = 'vibe-media-active-workspace-v1';

function usable(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(value);
}

export function standaloneMediaWorkspaceId(): string {
  return 'tool-library';
}

export function rememberMediaWorkspaceId(workspaceId: string): void {
  if(activeProjectId!==undefined&&workspaceId!==activeProjectId)return;
  if (!usable(workspaceId)) return;
  try { localStorage.setItem(ACTIVE_MEDIA_WORKSPACE_KEY, workspaceId); } catch { /* Current page state remains usable without persistence. */ }
}

export function defaultMediaWorkspaceId(): string {
  if(activeProjectId!==undefined)return activeProjectId;
  try {
    const activeWorkspace = localStorage.getItem(ACTIVE_MEDIA_WORKSPACE_KEY) || '';
    if (usable(activeWorkspace) && (activeWorkspace==='tool-library'||activeWorkspace.startsWith('story-'))) return activeWorkspace;
    const selectedStory = localStorage.getItem(STORY_SELECTION_KEY) || '';
    if (usable(selectedStory) && selectedStory.startsWith('story-')) return selectedStory;
  } catch { /* Use the standalone workspace if browser storage is unavailable. */ }
  return standaloneMediaWorkspaceId();
}

export function preferredMediaWorkspaceId(workspaces: StoryWorkspace[], requested = ''): string {
  if(activeProjectId!==undefined)return activeProjectId;
  if (usable(requested)&&(requested==='tool-library'||workspaces.some(row=>row.workspace_id===requested))) return requested;
  let storySelection = '';
  let activeWorkspace = '';
  let videoWorkspace = '';
  try {
    storySelection = localStorage.getItem(STORY_SELECTION_KEY) || '';
    activeWorkspace = localStorage.getItem(ACTIVE_MEDIA_WORKSPACE_KEY) || '';
    const draft = JSON.parse(localStorage.getItem(VIDEO_DRAFT_KEY) || '{}');
    videoWorkspace = draft?.workspaceId || '';
  } catch { /* Fall back to a saved story or the standalone library. */ }
  const available = new Set(workspaces.map(row => row.workspace_id));
  if (usable(activeWorkspace) && (activeWorkspace === 'tool-library' || available.has(activeWorkspace))) return activeWorkspace;
  if (usable(storySelection) && available.has(storySelection)) return storySelection;
  if (usable(videoWorkspace) && available.has(videoWorkspace)) return videoWorkspace;
  return standaloneMediaWorkspaceId();
}

export function mediaWorkspaceOptions(workspaces: StoryWorkspace[], selectedId: string) {
  if(activeProjectId!==undefined)return [{id:activeProjectId,label:activeProjectId==='tool-library'?'Standalone media':'Current project'}];
  let names: Record<string,string> = {};
  try { names = JSON.parse(localStorage.getItem('vibe-workspace-names-v1') || '{}'); } catch { /* Use saved story titles. */ }
  const rows = workspaces.map(row => ({ id: row.workspace_id, label: row.title || names[row.workspace_id] || 'Unnamed workspace' }));
  if (!rows.some(row => row.id === 'tool-library')) rows.unshift({id:'tool-library',label:'Shared media'});
  if (selectedId && !rows.some(row => row.id === selectedId)) {
    rows.unshift({ id: selectedId, label: names[selectedId] || 'Unnamed workspace — choose a name' });
  }
  return rows;
}
