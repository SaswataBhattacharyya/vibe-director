import assert from 'node:assert/strict';
import { test } from '@playwright/test';

test('Image Detailer repository sorts and switches views without losing selection', async ({page}) => {
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-images',title:'Image workspace'}],limit:50,offset:0,total:1})}));
  await page.route('**/api/media/ws-images/assets?kind=image', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({total:2,assets:[
    {asset_id:'pa-new-image',workspace_id:'ws-images',kind:'image',roles:['project_image'],filename:'new reference.png',media_type:'image/png',sha256:'new-hash',size_bytes:100,content_url:'/new.png',created_at:'2026-10-02T00:00:00Z'},
    {asset_id:'pa-old-image',workspace_id:'ws-images',kind:'image',roles:['project_image'],filename:'old reference.png',media_type:'image/png',sha256:'old-hash',size_bytes:100,content_url:'/old.png',created_at:'2026-09-01T00:00:00Z'}
  ]})}));
  await page.route('**/api/image-detailer/ws-images/jobs', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.goto('/#/media-prep?tool=image&workspace_id=ws-images');
  await page.getByRole('heading',{name:'Image Detailer'}).waitFor();
  assert.equal(await page.getByLabel('Add image').getAttribute('accept'),'image/png,image/jpeg,image/webp');
  const cards=page.locator('.image-detailer-choice');
  await cards.first().waitFor();
  assert.match(await cards.first().innerText(),/new reference\.png/);
  await page.getByRole('button',{name:'Sort oldest first'}).click();
  assert.match(await cards.first().innerText(),/old reference\.png/);
  await cards.first().click();
  await page.getByRole('button',{name:'List view'}).click();
  assert.equal(await page.getByRole('button',{name:'List view'}).getAttribute('aria-pressed'),'true');
  assert.equal(await cards.first().getAttribute('aria-pressed'),'true');
  await page.getByRole('button',{name:'Carousel view'}).click();
  assert.equal(await page.getByRole('button',{name:'Carousel view'}).getAttribute('aria-pressed'),'true');
  assert.equal(await cards.first().getAttribute('aria-pressed'),'true');
});

test('Image Detailer shows a concise failure reason without exposing the worker traceback', async ({page}) => {
  const stack = 'Could not verify ComfyUI queue.\nTraceback (most recent call last):\n  File "/private/path/worker.py", line 42, in run\nRuntimeError: internal detail';
  await page.route('**/api/story/workspaces**', route => route.fulfill({json:{items:[{workspace_id:'ws-images',title:'Image workspace'}],total:1}}));
  await page.route('**/api/media/ws-images/assets?kind=image', route => route.fulfill({json:{total:1,assets:[{
    asset_id:'pa-image',workspace_id:'ws-images',kind:'image',roles:['project_image'],filename:'reference.png',
    media_type:'image/png',sha256:'hash',size_bytes:100,content_url:'/reference.png',created_at:'2026-10-02T00:00:00Z'
  }]}}));
  await page.route('**/api/image-detailer/ws-images/jobs', route => route.fulfill({json:[{
    job_id:'detailer-failed',status:'failed',progress:35,stage:'analyzing',message:'Image analysis failed.',
    created_at:'2026-10-02T00:00:00Z',updated_at:'2026-10-02T00:00:00Z',
    request:{workspace_id:'ws-images',asset_id:'pa-image',sha256:'hash',mode:'balanced'},events:[],error:stack
  }]}));
  await page.route('**/api/video-summariser/capabilities?check_gpu_admission=1', route => route.fulfill({json:{can_analyze:true,reason:'Ready',checks:{},gpu_admission:{available:false,checked:true,reason:'Could not verify ComfyUI queue.'}}}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep?tool=image&workspace_id=ws-images`);
  await page.getByRole('heading',{name:'Image Detailer'}).waitFor();
  await page.getByLabel('Runtime readiness').getByText('Could not verify ComfyUI queue.',{exact:true}).waitFor();
  await page.locator('.image-detailer-choice').first().click();
  await page.getByRole('button',{name:'Retry'}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Retry'}).isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'Start analysis'}).isDisabled(),true);
  await page.getByLabel('Runtime readiness').getByText('Could not verify ComfyUI queue.',{exact:true}).waitFor();
  if (await page.getByText(/Traceback|\/private\/path\/worker\.py|RuntimeError: internal detail/).count()) {
    throw new Error('Image Detailer exposed worker traceback details in its UI.');
  }
});

test('Image Detailer rechecks GPU admission before sending an analysis request', async ({page}) => {
  let checks=0;
  let submissions=0;
  await page.route('**/api/story/workspaces**', route => route.fulfill({json:{items:[{workspace_id:'ws-images',title:'Image workspace'}],total:1}}));
  await page.route('**/api/media/ws-images/assets?kind=image', route => route.fulfill({json:{total:1,assets:[{
    asset_id:'pa-image',workspace_id:'ws-images',kind:'image',roles:['project_image'],filename:'reference.png',
    media_type:'image/png',sha256:'hash',size_bytes:100,content_url:'/reference.png',created_at:'2026-10-02T00:00:00Z'
  }]}}));
  await page.route('**/api/image-detailer/ws-images/jobs', async route => {
    if (route.request().method()==='POST') submissions++;
    await route.fulfill({json:[]});
  });
  await page.route('**/api/video-summariser/capabilities?check_gpu_admission=1', async route => {
    checks++;
    await route.fulfill({json:{can_analyze:true,reason:'Ready',checks:{},gpu_admission:checks===1
      ?{available:true,checked:true,free_gib:22,required_gib:20,reason:null}
      :{available:false,checked:true,free_gib:1.7,reason:'GPU operating limit reached.'}}});
  });
  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep?tool=image&workspace_id=ws-images`);
  await page.getByRole('heading',{name:'Image Detailer'}).waitFor();
  const analyze=page.getByRole('button',{name:'Start analysis'});
  await page.getByLabel('Runtime readiness').getByText(/Ready · 22\.0 GiB reported free \(informational\)\./).waitFor();
  await page.locator('.image-detailer-choice').first().click();
  await analyze.click();
  await page.locator('p.notice').filter({hasText:'GPU operating limit reached.'}).waitFor();
  assert.ok(checks>=2);
  assert.equal(submissions,0);
});
