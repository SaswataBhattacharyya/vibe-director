/** Existing page tests declare their owning project through their original fixture drafts.
 * Register last so broad endpoint mocks cannot accidentally hide the shared controller.
 */
export async function mockProject(page, owner) {
  let memory={};
  await page.route('**/api/projects/**',async route=>{
    const workspace=owner||await page.evaluate(()=>{
      try {const draft=JSON.parse(localStorage.getItem('vibe-video-draft-v1')||'{}');if(draft.workspaceId)return draft.workspaceId;}catch{}
      return localStorage.getItem('vibe-story-selected-v1')||localStorage.getItem('vibe-media-active-workspace-v1')||'tool-library';
    });
    if(route.request().url().includes('/memory')){memory=route.request().postDataJSON().browser_state;return route.fulfill({json:{saved:true}});}
    return route.fulfill({json:{workspace_id:workspace,title:'Fixture project',browser_state:memory}});
  });
}
