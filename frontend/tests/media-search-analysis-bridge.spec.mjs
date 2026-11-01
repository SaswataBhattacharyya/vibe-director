import { test, expect } from '@playwright/test';

test('Search opens Video Summariser with the selected workspace video preselected', async ({ page }) => {
  const video = {
    asset_id: 'video-one', workspace_id: 'workspace-a', kind: 'video', roles: ['project_video'],
    filename: 'rainy-courtroom.mp4', media_type: 'video/mp4', sha256: 'a'.repeat(64), size_bytes: 1024,
    content_url: '/video.mp4', created_at: '2026-10-11T00:00:00Z',
  };
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: {
    items: [{ workspace_id: 'workspace-a', title: 'Short film' }], limit: 50, offset: 0, total: 1,
  } }));
  await page.route('**/api/media/workspace-a/assets/seo-styles', route => route.fulfill({ json: { styles: [] } }));
  await page.route('**/api/video-summariser/capabilities', route => route.fulfill({ json: {
    can_analyze: true, reason: 'Ready', checks: {},
  } }));
  await page.route('**/api/video-summariser/workspace-a/analysis/jobs', route => route.fulfill({ json: [] }));
  await page.route('**/api/media/workspace-a/assets**', route => {
    const url = new URL(route.request().url());
    return route.fulfill({ json: { assets: url.searchParams.get('kind') === 'video' ? [video] : [], total: 1, limit: 50, offset: 0 } });
  });

  await page.goto('/#/media-prep?tool=search');
  await page.getByRole('tab', { name: 'Videos' }).click();
  await expect(page).toHaveURL(/tool=search.*kind=video/);
  await page.getByRole('link', { name: 'Analyze video for semantic search' }).click();

  await expect(page).toHaveURL(/tool=video.*videoPage=analyze.*workspace_id=workspace-a.*asset_id=video-one/);
  await expect(page.getByRole('heading', { name: 'Analyze videos' })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: /rainy-courtroom\.mp4/ })).toBeChecked();
  await expect(page.getByRole('button', { name: 'Analyze selected videos' })).toBeEnabled();
  await page.goBack();
  await expect(page).toHaveURL(/tool=search.*kind=video/);
  await expect(page.getByRole('tab', { name: 'Videos' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText('rainy-courtroom.mp4')).toBeVisible();
});

test('Search opens Image Detailer with the selected workspace image selected', async ({ page }) => {
  const image = {
    asset_id: 'image-one', workspace_id: 'workspace-a', kind: 'image', roles: ['project_image'],
    filename: 'rainy-courtroom.png', media_type: 'image/png', sha256: 'b'.repeat(64), size_bytes: 1024,
    content_url: '/image.png', created_at: '2026-10-11T00:00:00Z',
  };
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: {
    items: [{ workspace_id: 'workspace-a', title: 'Short film' }], limit: 50, offset: 0, total: 1,
  } }));
  await page.route('**/api/media/workspace-a/assets/seo-styles', route => route.fulfill({ json: { styles: [] } }));
  await page.route('**/api/image-detailer/workspace-a/jobs', route => route.fulfill({ json: [] }));
  await page.route('**/api/media/workspace-a/assets**', route => route.fulfill({ json: {
    assets: new URL(route.request().url()).searchParams.get('kind') === 'image' ? [image] : [], total: 1, limit: 50, offset: 0,
  } }));

  await page.goto('/#/media-prep?tool=search');
  await page.getByRole('link', { name: 'Open in Image Detailer' }).click();

  await expect(page).toHaveURL(/tool=image.*workspace_id=workspace-a.*asset_id=image-one/);
  await expect(page.getByRole('heading', { name: 'Image Detailer' })).toBeVisible();
  await expect(page.getByRole('button', { name: /rainy-courtroom\.png/ })).toHaveAttribute('aria-pressed', 'true');
});

test('Image Detailer indexes filename and role metadata without requiring notes', async ({ page }) => {
  const calls = [];
  const asset = {
    asset_id: 'image-one', workspace_id: 'workspace-a', kind: 'image', roles: ['project_image'],
    filename: 'rainy-courtroom.png', media_type: 'image/png', sha256: 'b'.repeat(64), size_bytes: 1024,
    content_url: '/image.png', created_at: '2026-10-11T00:00:00Z',
  };
  const job = {
    job_id: 'image-job-12345678', status: 'completed', progress: 100, stage: 'complete', message: 'Image analysis complete.',
    created_at: '2026-10-11T00:00:00Z', updated_at: '2026-10-11T00:00:00Z',
    request: {workspace_id:'workspace-a',asset_id:'image-one',sha256:asset.sha256,mode:'balanced'}, events: [],
    result: {asset_id:'image-one',filename:asset.filename,sha256:asset.sha256,mode:'balanced',analysis:{analysis:{summary:'Rainy courtroom',subjects:['witness']},frame_card:{summary:'Rainy courtroom'}}},
  };
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Short film'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/image-detailer/workspace-a/jobs', route => route.fulfill({json:[job]}));
  await page.route('**/api/media/workspace-a/assets**', async route => {
    const request=route.request(), url=new URL(request.url());
    if(url.pathname.endsWith('/semantic-index')&&request.method()==='POST'){
      calls.push(request.method());
      return route.fulfill({json:{asset:{...asset,semantic_annotation_index:{source:'saved_annotations',source_sha256:asset.sha256,annotation_sha256:'c'.repeat(64),model:'facebook/pe-av-base',dimension:1024}},indexed:true,source:'saved filename, description, tags and roles'}});
    }
    return route.fulfill({json:{assets:[asset],total:1,limit:50,offset:0}});
  });

  await page.goto('/#/media-prep?tool=image&workspace_id=workspace-a&asset_id=image-one');
  const indexButton=page.getByRole('button',{name:'Index saved details for semantic search'});
  await expect(indexButton).toBeEnabled();
  await indexButton.click();
  await expect.poll(()=>calls).toEqual(['POST']);
  await expect(page.getByText('Saved image details indexed for semantic search. Image pixels are not embedded.')).toBeVisible();
});


test('Image Detailer ignores a delayed library response after workspace changes', async ({ page }) => {
  let releaseA, startedA;
  const waitingA=new Promise(resolve=>{releaseA=resolve;});
  const requestedA=new Promise(resolve=>{startedA=resolve;});
  const asset=id=>({asset_id:`image-${id}`,workspace_id:`workspace-${id}`,kind:'image',roles:['project_image'],filename:`${id}.png`,media_type:'image/png',sha256:'b'.repeat(64),size_bytes:10,content_url:`/${id}.png`,created_at:'2026-10-11T00:00:00Z'});
  await page.route('**/api/story/workspaces?**',route=>route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'A'},{workspace_id:'workspace-b',title:'B'}],total:2,limit:50,offset:0}}));
  await page.route('**/api/image-detailer/*/jobs',route=>route.fulfill({json:[]}));
  await page.route('**/api/media/*/assets**',async route=>{
    const id=new URL(route.request().url()).pathname.includes('/workspace-a/')?'a':'b';
    if(id==='a'){startedA();await waitingA;}
    await route.fulfill({json:{assets:[asset(id)],total:1,limit:50,offset:0}});
  });
  await page.goto('/#/media-prep?tool=image&workspace_id=workspace-a');
  await requestedA;
  await page.getByLabel('Image Detailer workspace').selectOption('workspace-b');
  await expect(page.getByRole('button',{name:/b\.png/})).toBeVisible();
  const responseA=page.waitForResponse(response=>response.url().includes('/workspace-a/assets'));
  releaseA();
  await responseA;
  await expect(page.getByRole('button',{name:/b\.png/})).toBeVisible();
  await expect(page.getByRole('button',{name:/a\.png/})).toHaveCount(0);
});
