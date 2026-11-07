/** Existing page tests declare their owning project through their original fixture drafts.
 * Register last so broad endpoint mocks cannot accidentally hide the shared controller.
 */
export async function mockProject(page, owner, draftKey) {
  let memory={};
  let current=owner;
  await page.route('**/api/projects/**',async route=>{
    if(route.request().url().endsWith('/select'))current=route.request().postDataJSON().workspace_id;
    const workspace=current||await page.evaluate(preferredDraft=>{
      const linked=new URLSearchParams(location.hash.split('?')[1]||'').get('workspace_id');
      if(preferredDraft&&linked)return linked;
      try {const draft=JSON.parse(localStorage.getItem(preferredDraft||'vibe-video-draft-v1')||'{}');if(draft.workspaceId)return draft.workspaceId;}catch{}
      return localStorage.getItem('vibe-story-selected-v1')||localStorage.getItem('vibe-media-active-workspace-v1')||'tool-library';
    },draftKey);
    current=workspace;
    if(route.request().url().includes('/memory')){memory=route.request().postDataJSON().browser_state;return route.fulfill({json:{saved:true}});}
    return route.fulfill({json:{workspace_id:workspace,title:'Fixture project',browser_state:memory}});
  });
}
