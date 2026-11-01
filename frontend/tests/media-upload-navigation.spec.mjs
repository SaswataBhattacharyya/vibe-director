import { test, expect } from '@playwright/test';

for (const operation of ['upload', 'voice']) for (const changeWorkspace of [false, true]) test(`${operation} completion ${changeWorkspace ? 'does not replace a different workspace' : 'appears in its own library'}`, async ({page}) => {
  let releaseUpload;
  const delayed = new Promise(resolve => { releaseUpload = resolve; });
  let markRequested;
  const requested = new Promise(resolve => { markRequested = resolve; });
  const asset = (workspace, filename) => ({asset_id:`asset-${workspace}`,workspace_id:workspace,kind:'image',roles:['style_reference'],filename,media_type:'image/png',sha256:'a'.repeat(64),size_bytes:8,content_url:'/fixture.png',created_at:'2026-10-13T00:00:00Z'});
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/audio/voices') return route.fulfill({json:[{id:'guide',name:'Guide',source:'comfyui',relative_path:'voices/guide.wav',content_url:'/guide.wav',created_at:'2026-10-13T00:00:00Z',size_bytes:8}]});
    if (url.pathname.endsWith('/voice-library/import')) {
      markRequested(); await delayed;
      return route.fulfill({json:{asset:{...asset('workspace-a','Uploaded A.png'),kind:'audio',roles:['voice_master'],audio_category:'voice'}}});
    }
    if (url.pathname === '/api/story/workspaces') return route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Story A'},{workspace_id:'workspace-b',title:'Story B'}]}});
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if (url.pathname.endsWith('/assets')) {
      if (route.request().method() === 'POST') {
        markRequested(); await delayed;
        return route.fulfill({json:{...asset('workspace-a','Uploaded A.png'),deduplicated:false}});
      }
      const rows = url.pathname.includes('/workspace-b/') ? [{...asset('workspace-b','Existing B.png'),...(operation === 'voice' ? {kind:'audio',roles:['voice_master'],audio_category:'voice'} : {})}] : [];
      return route.fulfill({json:{assets:rows,total:rows.length}});
    }
    return route.fulfill({json:[]});
  });
  await page.goto(`/#/media-prep?tool=search&workspace_id=workspace-a&kind=${operation === 'voice' ? 'audio' : 'image'}`);
  await expect(page.getByRole('button',{name:'Refresh',exact:true})).toBeEnabled();
  if (operation === 'voice') await page.getByRole('button',{name:'Add to workspace',exact:true}).click();
  else {
    await page.getByLabel('Choose media file').setInputFiles({name:'Uploaded A.png',mimeType:'image/png',buffer:Buffer.from('fixture')});
    await page.getByRole('button',{name:'Add asset',exact:true}).click();
  }
  await requested;
  if (changeWorkspace) {
    await page.getByLabel('Workspace',{exact:true}).selectOption('workspace-b');
    await expect(page.locator('.media-asset').filter({hasText:'Existing B.png'})).toBeVisible();
  }
  const settled = page.waitForResponse(response => response.request().method()==='POST' && response.url().includes(operation === 'voice' ? '/workspace-a/voice-library/import' : '/workspace-a/assets'));
  releaseUpload(); await settled;
  // Allow the upload's async continuation to run before inspecting visible state.
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  if (changeWorkspace) {
    await expect(page.getByLabel('Workspace',{exact:true})).toHaveValue('workspace-b');
    await expect(page.locator('.media-asset').filter({hasText:'Existing B.png'})).toBeVisible();
    await expect(page.locator('.media-asset').filter({hasText:'Uploaded A.png'})).toHaveCount(0);
  } else {
    await expect(page.locator('.media-asset').filter({hasText:'Uploaded A.png'})).toBeVisible();
  }
});
