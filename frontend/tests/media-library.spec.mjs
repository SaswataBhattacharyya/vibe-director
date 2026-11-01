import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';

test('workspace videos can be archived, restored, and remain playable', async ({ page }) => {
  let archived = false;
  const asset = {asset_id:'pa-0123456789abcdef',workspace_id:'workspace-a',kind:'video',roles:['project_video'],
    filename:'Mira scene.mp4',media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:128,
    content_url:'/mira.mp4',created_at:'2026-10-10T00:00:00Z',media:{duration_seconds:4}};
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Story'}],limit:50,offset:0,total:1}}));
  await page.route('**/mira.mp4', route => route.fulfill({
    path: fileURLToPath(new URL('./fixtures/archive-playback.mp4', import.meta.url)),
    contentType: 'video/mp4',
  }));
  await page.route('**/api/media/**', route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if (url.pathname.endsWith('/archive')) { archived = true; return route.fulfill({json:{asset:{...asset,archived_at:'2026-10-12T00:00:00Z'}}}); }
    if (url.pathname.endsWith('/restore')) { archived = false; return route.fulfill({json:{asset}}); }
    if (url.pathname.endsWith('/assets')) {
      const includeArchived = url.searchParams.get('include_archived') === 'true';
      return route.fulfill({json:{assets:!archived || includeArchived ? [{...asset,...(archived?{archived_at:'2026-10-12T00:00:00Z'}:{})}] : [],total:!archived || includeArchived ? 1 : 0,limit:50,offset:0}});
    }
    return route.fulfill({json:{assets:[],total:0,limit:50,offset:0}});
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a');
  await page.getByRole('tab', {name:'Videos'}).click();
  const card = page.locator('.media-asset').filter({hasText:'Mira scene.mp4'});
  await expect(card).toBeVisible();
  const preview = card.getByLabel('Mira scene.mp4, muted hover preview');
  await expect(preview).toBeVisible();
  await expect(preview).toHaveAttribute('src', '/mira.mp4');
  expect(await preview.evaluate(element => element.controls)).toBe(true);
  const openPlayer = card.getByRole('button', { name: 'Play video below' });
  await openPlayer.click();
  const selectedPlayer = page.locator('.media-selected-player video');
  await expect(selectedPlayer).toHaveAttribute('src', '/mira.mp4');
  await expect(selectedPlayer).toBeInViewport();
  expect(await selectedPlayer.evaluate(element => element.controls && !element.muted)).toBe(true);
  await page.getByRole('button', { name: 'Close player' }).click();
  await expect(page.locator('.media-selected-player')).toHaveCount(0);
  await card.getByRole('button',{name:'Archive asset'}).click();
  await expect(page.getByText('Asset archived. Its file and existing references are kept.')).toBeVisible();
  await expect(page.getByText('Mira scene.mp4')).toHaveCount(0);
  await expect(page.getByRole('status').filter({hasText:'No active videos in “Story”.'})).toContainText('Archived videos are available when “Show archived” is enabled.');
  await page.getByLabel('Show archived').check();
  const archivedCard = page.locator('.media-asset').filter({hasText:'Mira scene.mp4'});
  await expect(archivedCard.getByText('Archived')).toBeVisible();
  await archivedCard.getByRole('button',{name:'Restore to library'}).click();
  await expect(page.getByText('Asset restored to the library.')).toBeVisible();
  const restoredCard = page.locator('.media-asset').filter({hasText:'Mira scene.mp4'});
  await expect(restoredCard).toBeVisible();
  const restoredPreview = restoredCard.getByLabel('Mira scene.mp4, muted hover preview');
  await expect(restoredPreview).toHaveAttribute('src', '/mira.mp4');
  expect(await restoredPreview.evaluate(element => element.controls)).toBe(true);
  await restoredPreview.evaluate(element => { element.muted = true; return element.play(); });
  await expect.poll(() => restoredPreview.evaluate(element => element.currentTime)).toBeGreaterThan(0.1);
});

test('library keyword search stays visibly wide and clearly labelled in the desktop shell', async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 900 });
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Story'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/media/**', route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    return route.fulfill({json:{assets:[
      {asset_id:'video-youtube',workspace_id:'workspace-a',kind:'video',roles:['project_video'],filename:'YouTube street interview.mp4',media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:128,content_url:'/youtube.mp4',created_at:'2026-10-10T00:00:00Z',description:'Night market conversation',tags:['market','street']},
      {asset_id:'video-rain',workspace_id:'workspace-a',kind:'video',roles:['project_video'],filename:'Rainy courtyard.mp4',media_type:'video/mp4',sha256:'b'.repeat(64),size_bytes:128,content_url:'/rain.mp4',created_at:'2026-10-11T00:00:00Z',description:'Quiet evening scene',tags:['rain','courtroom']},
    ],total:2,limit:50,offset:0}});
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a&kind=video');
  const search = page.getByRole('searchbox', { name: 'Search videos' });
  await expect(search).toBeVisible();
  await expect(page.getByText('Search videos', { exact: true }).first()).toBeVisible();
  const bounds = await search.boundingBox();
  expect(bounds?.width || 0).toBeGreaterThan(250);
  await expect(search).toHaveAttribute('placeholder', 'Type video title, filename, notes or tags');
  await expect(page.getByText('Type in the large search box above to filter names, descriptions, tags and source notes as you go.', {exact:false})).toBeVisible();
  await search.fill('youtube');
  await expect(page.getByText('YouTube street interview.mp4')).toBeVisible();
  await expect(page.getByText('Rainy courtyard.mp4')).toHaveCount(0);
  await search.fill('courtroom');
  await expect(page.getByText('Rainy courtyard.mp4')).toBeVisible();
  await expect(page.getByText('YouTube street interview.mp4')).toHaveCount(0);
  await search.fill('nothing-by-that-name');
  await expect(page.getByRole('status').filter({hasText:'No results for “nothing-by-that-name” in Story.'})).toBeVisible();
  await page.getByRole('button',{name:'Clear search and show all'}).click();
  await expect(search).toHaveValue('');
  await expect(page.getByText('YouTube street interview.mp4')).toBeVisible();
});

test('empty video library explains the selected workspace and opens YouTube Download there', async ({ page }) => {
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Story'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/media/**', route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    return route.fulfill({json:{assets:[],total:0,limit:50,offset:0}});
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a&kind=video');
  const emptyState = page.getByRole('status').filter({hasText:'No active videos in “Story”.'});
  await expect(emptyState).toBeVisible();
  await expect(emptyState).toContainText('import copied videos from Video Summariser');
  await expect(emptyState.getByRole('link',{name:'Open Video Summariser'})).toHaveAttribute('href','#/media-prep?tool=video&workspace_id=workspace-a');
  await page.getByRole('link',{name:'Open YouTube Download'}).click();
  await expect(page).toHaveURL(/#\/media-prep\?tool=video&videoPage=youtube&workspace_id=workspace-a$/);
  await expect(page.getByRole('heading',{name:'YouTube Download'})).toBeVisible();
});

test('video search waits for the selected workspace assets before reporting an empty library', async ({ page }) => {
  let releaseAssets;
  let markAssetsRequested;
  const delayedAssets = new Promise(resolve => { releaseAssets = resolve; });
  const assetsRequested = new Promise(resolve => { markAssetsRequested = resolve; });
  const video = {asset_id:'video-delayed',workspace_id:'workspace-a',kind:'video',roles:['project_video'],filename:'Imported clip.mp4',media_type:'video/mp4',sha256:'c'.repeat(64),size_bytes:128,content_url:'/imported.mp4',created_at:'2026-10-12T00:00:00Z'};
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Story'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/media/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if (url.pathname.endsWith('/assets')) {
      markAssetsRequested();
      await delayedAssets;
      return route.fulfill({json:{assets:[video],total:1,limit:50,offset:0}});
    }
    return route.fulfill({json:{assets:[],total:0,limit:50,offset:0}});
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a&kind=video');
  await assetsRequested;
  await expect(page.getByRole('status').filter({hasText:'Loading videos…'})).toBeVisible();
  await expect(page.getByText('No active videos in “Story”.')).toHaveCount(0);
  releaseAssets();
  await expect(page.getByText('Imported clip.mp4')).toBeVisible();
});

test('nested Search honors and preserves the explicit workspace route', async ({ page }) => {
  const assetRequests = [];
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-b'));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: {
    items: [{ workspace_id: 'workspace-a', title: 'Route story' }, { workspace_id: 'workspace-b', title: 'Previously selected story' }], limit: 50, offset: 0, total: 2,
  } }));
  await page.route('**/api/media/**', route => {
    const url = new URL(route.request().url());
    const match = /\/api\/media\/([^/]+)\/assets/.exec(url.pathname);
    if (match) assetRequests.push(match[1]);
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({ json: { styles: [] } });
    return route.fulfill({ json: { assets: [], total: 0, limit: 50, offset: 0 } });
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a');
  await expect(page.getByRole('heading', { name: 'Search library' })).toBeVisible();
  await expect(page.getByLabel('Workspace', { exact: true })).toHaveValue('workspace-a');
  await expect.poll(() => assetRequests.includes('workspace-a')).toBe(true);
  expect(assetRequests).not.toContain('workspace-b');
  await page.getByRole('button', { name: '← Media Prep' }).click();
  await expect(page).toHaveURL(/#\/media-prep\?workspace_id=workspace-a$/);
  await page.getByRole('button', { name: 'Open Search' }).click();
  await expect(page).toHaveURL(/#\/media-prep\?tool=search&workspace_id=workspace-a$/);
  await expect(page.getByLabel('Workspace', { exact: true })).toHaveValue('workspace-a');
});

test('late media-list responses cannot replace the newly selected workspace', async ({ page }) => {
  let releaseWorkspaceA;
  const workspaceAResponse = new Promise(resolve => { releaseWorkspaceA = resolve; });
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: {
    items: [{ workspace_id: 'workspace-a', title: 'First story' }, { workspace_id: 'workspace-b', title: 'Second story' }], limit: 50, offset: 0, total: 2,
  } }));
  await page.route('**/api/media/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({ json: { styles: [] } });
    if (url.pathname.endsWith('/assets/search')) return route.fulfill({ json: { results: [] } });
    const workspaceId = /\/api\/media\/([^/]+)\/assets/.exec(url.pathname)?.[1];
    if (workspaceId === 'workspace-a') {
      await workspaceAResponse;
      return route.fulfill({ json: { assets: [{
        asset_id: 'asset-a', workspace_id: workspaceId, kind: 'image', roles: ['style_reference'], filename: 'First story image.png',
        media_type: 'image/png', sha256: 'a'.repeat(64), size_bytes: 16, content_url: '/a.png', created_at: '2026-10-10T00:00:00Z',
      }], total: 1, limit: 50, offset: 0 } });
    }
    return route.fulfill({ json: { assets: [{
      asset_id: 'asset-b', workspace_id: workspaceId, kind: 'image', roles: ['style_reference'], filename: 'Second story image.png',
      media_type: 'image/png', sha256: 'b'.repeat(64), size_bytes: 16, content_url: '/b.png', created_at: '2026-10-11T00:00:00Z',
    }], total: 1, limit: 50, offset: 0 } });
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a');
  await expect(page.getByLabel('Workspace', { exact: true })).toHaveValue('workspace-a');
  await page.getByLabel('Workspace', { exact: true }).selectOption('workspace-b');
  await expect(page.getByText('Second story image.png')).toBeVisible();
  releaseWorkspaceA();
  await expect(page.getByText('First story image.png')).toHaveCount(0);
  await expect(page.getByText('Second story image.png')).toBeVisible();
});

test('workspace change never polls a content-index job through the new workspace', async ({ page }) => {
  let releaseWorkspaceBJobs;
  const workspaceBJobs = new Promise(resolve => { releaseWorkspaceBJobs = resolve; });
  const wrongWorkspacePolls = [];
  const asset = {asset_id:'video-a',workspace_id:'workspace-a',kind:'video',roles:['project_video'],filename:'First story video.mp4',media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:32,content_url:'/a.mp4',created_at:'2026-10-10T00:00:00Z'};
  const job = {job_id:'job-a',kind:'semantic-index',status:'running',progress:25,stage:'embedding',message:'Embedding First story video.mp4.',request:{workspace_id:'workspace-a',asset_id:asset.asset_id,modality:'video'}};
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'First story'},{workspace_id:'workspace-b',title:'Second story'}],limit:50,offset:0,total:2}}));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[]}));
  await page.route('**/api/media/**', async route => {
    const url = new URL(route.request().url());
    const workspaceId = /\/api\/media\/([^/]+)/.exec(url.pathname)?.[1];
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if (url.pathname.endsWith('/semantic-index-jobs')) {
      if (workspaceId === 'workspace-a') return route.fulfill({json:[job]});
      await workspaceBJobs;
      return route.fulfill({json:[]});
    }
    if (url.pathname.endsWith('/semantic-index-jobs/job-a')) {
      if (workspaceId !== 'workspace-a') wrongWorkspacePolls.push(workspaceId);
      return route.fulfill({json:job});
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:workspaceId === 'workspace-a' ? [asset] : [],total:workspaceId === 'workspace-a' ? 1 : 0,limit:50,offset:0}});
    return route.fulfill({json:{}});
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a&kind=video');
  await expect(page.getByText('Embedding First story video.mp4.')).toBeVisible();
  await page.getByLabel('Workspace', {exact:true}).selectOption('workspace-b');
  await expect(page.getByLabel('Workspace', {exact:true})).toHaveValue('workspace-b');
  await expect(page.getByText('First story video.mp4')).toHaveCount(0);
  await page.waitForTimeout(1500);
  releaseWorkspaceBJobs();
  expect(wrongWorkspacePolls).toEqual([]);
});

test('semantic searches keep independent panel state and discard stale replies', async ({ page }) => {
  let releaseVoiceSearch;
  let releaseAudioSearch;
  const voiceSearchResponse = new Promise(resolve => { releaseVoiceSearch = resolve; });
  const audioSearchResponse = new Promise(resolve => { releaseAudioSearch = resolve; });
  const assets = [
    {asset_id:'voice-a',workspace_id:'workspace-a',kind:'audio',roles:['voice_master'],filename:'Warm voice.wav',media_type:'audio/wav',sha256:'a'.repeat(64),size_bytes:20,content_url:'/voice.wav',created_at:'2026-10-10T00:00:00Z',audio_category:'voice'},
    {asset_id:'clip-a',workspace_id:'workspace-a',kind:'audio',roles:['project_audio'],filename:'Rain ambience.wav',media_type:'audio/wav',sha256:'b'.repeat(64),size_bytes:20,content_url:'/rain.wav',created_at:'2026-10-11T00:00:00Z',audio_category:'sfx'},
  ];
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Short film'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[]}));
  await page.route('**/api/media/workspace-a/**', async route => {
    const request=route.request(),url=new URL(request.url());
    if(url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if(url.pathname.endsWith('/semantic-index-jobs')) return route.fulfill({json:[]});
    if(url.pathname.endsWith('/assets/search')) {
      if(url.searchParams.get('q')==='old voice query') {
        await voiceSearchResponse;
        return route.fulfill({json:{results:[{asset:assets[0],score:1,text:'old voice result'}],query_backend:'test'}});
      }
      if(url.searchParams.get('q')==='rain query') {
        await audioSearchResponse;
        return route.fulfill({json:{results:[{asset:assets[1],score:1,text:'rain result'}],query_backend:'test'}});
      }
      return route.fulfill({json:{results:[{asset:assets[1],score:1,text:'rain result'}],query_backend:'test'}});
    }
    if(url.pathname.endsWith('/assets')) return route.fulfill({json:{assets,total:assets.length,limit:50,offset:0}});
    return route.fulfill({json:{}});
  });

  await page.goto('/#/media-prep?tool=search&kind=audio&workspace_id=workspace-a');
  await page.getByLabel('voice files search mode').selectOption('semantic');
  await page.getByLabel('Search voice files').fill('old voice query');
  await page.getByRole('button',{name:'Search',exact:true}).first().click();
  await expect(page.getByRole('button',{name:'Searching…'}).first()).toBeDisabled();
  await page.getByLabel('audio clips search mode').selectOption('semantic');
  await page.getByLabel('Search audio clips').fill('rain query');
  await page.getByRole('button',{name:'Search',exact:true}).last().click();
  await expect(page.locator('.audio-repertoire-panel').last().getByRole('button',{name:'Searching…'})).toBeDisabled();
  await expect(page.locator('.audio-repertoire-panel').first().getByRole('button',{name:'Searching…'})).toBeDisabled();
  releaseAudioSearch();
  await expect(page.getByText('Found 1 semantic matches (test embeddings).')).toBeVisible();
  await expect(page.locator('.audio-repertoire-panel').last().getByText('Rain ambience.wav').first()).toBeVisible();
  await expect(page.locator('.audio-repertoire-panel').first().getByRole('button',{name:'Searching…'})).toBeDisabled();

  await page.getByLabel('Search voice files').fill('new voice query');
  await expect(page.getByText('The query changed. Run semantic search to refresh results.')).toBeVisible();
  releaseVoiceSearch();
  await expect(page.locator('.audio-repertoire-panel').first().getByRole('button',{name:'Search',exact:true})).toBeEnabled();
  await expect(page.locator('.audio-repertoire-panel').first().getByText('Warm voice.wav')).toHaveCount(0);
  await expect(page.locator('.audio-repertoire-panel').last().getByText('Rain ambience.wav').first()).toBeVisible();
});

test('semantic content indexing is explicit and reports the durable job result', async ({ page }) => {
  const calls = [];
  const asset = {asset_id:'pa-video-index-01',workspace_id:'workspace-a',kind:'video',roles:['project_video'],filename:'Rainy street.mp4',media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:128,content_url:'/video.mp4',created_at:'2026-10-11T00:00:00Z'};
  const job = {job_id:'semantic-job-1',kind:'semantic-index',status:'running',progress:25,stage:'embedding',message:'Embedding media content.',request:{workspace_id:'workspace-a',asset_id:asset.asset_id,modality:'video'}};
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Short film'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[]}));
  await page.route('**/api/video-summariser/capabilities?check_gpu_admission=1', route => route.fulfill({json:{gpu_admission:{available:true,checked:true,free_gib:22,required_gib:20}}}));
  await page.route('**/api/media/workspace-a/**', route => {
    const request = route.request(), url = new URL(request.url());
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if (url.pathname.endsWith('/semantic-index-jobs')) return route.fulfill({json:[job]});
    if (url.pathname.endsWith('/semantic-index-jobs/semantic-job-1')) return route.fulfill({json:{...job,status:'completed',progress:100,message:'Media content indexed.',result:{model:'facebook/pe-av-base',dimension:1024}}});
    if (url.pathname.endsWith('/semantic-content-index') && request.method()==='POST') {
      calls.push(request.method());
      return route.fulfill({status:202,json:job});
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[asset],total:1,limit:50,offset:0}});
    return route.fulfill({json:{}});
  });

  await page.goto('/#/media');
  await page.getByRole('tab',{name:'Videos'}).click();
  const card = page.locator('.media-asset').filter({hasText:asset.filename});
  await expect(card.getByRole('button',{name:'Index visual/media content for semantic search'})).toBeVisible();
  await card.getByRole('button',{name:'Index visual/media content for semantic search'}).click();
  await expect.poll(() => calls).toEqual(['POST']);
  await expect(page.getByText(/Media content indexed/)).toBeVisible();
});

test('image semantic indexing is available as an explicit action', async ({ page }) => {
  const image = {asset_id:'pa-image-index-01',workspace_id:'workspace-a',kind:'image',roles:['project_image'],filename:'Red jacket.png',media_type:'image/png',sha256:'b'.repeat(64),size_bytes:128,content_url:'/image.png',created_at:'2026-10-11T00:00:00Z'};
  const calls = [];
  const job = {job_id:'image-semantic-job',kind:'semantic-index',status:'queued',progress:0,stage:'queued',message:'Queued image indexing.',request:{workspace_id:'workspace-a',asset_id:image.asset_id,modality:'image'}};
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Short film'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[]}));
  await page.route('**/api/video-summariser/capabilities?check_gpu_admission=1', route => route.fulfill({json:{gpu_admission:{available:true,checked:true,free_gib:22,required_gib:20}}}));
  await page.route('**/api/media/workspace-a/**', route => {
    const request=route.request(),url=new URL(request.url());
    if(url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if(url.pathname.endsWith('/semantic-index-jobs')) return route.fulfill({json:[]});
    if(url.pathname.endsWith('/semantic-content-index') && request.method()==='POST') { calls.push(request.method()); return route.fulfill({status:202,json:job}); }
    if(url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[image],total:1,limit:50,offset:0}});
    return route.fulfill({json:{}});
  });
  await page.goto('/#/media');
  await page.getByRole('tab',{name:'Images'}).click();
  const card=page.locator('.media-asset').filter({hasText:image.filename});
  await expect(card.getByRole('button',{name:'Index visual/media content for semantic search'})).toBeVisible();
  await card.getByRole('button',{name:'Index visual/media content for semantic search'}).click();
  await expect.poll(()=>calls).toEqual(['POST']);
  await expect(page.getByText('Queued image indexing.')).toBeVisible();
});

test('semantic content indexing stops before job creation when runtime readiness is unavailable', async ({ page }) => {
  let jobsCreated = 0;
  const asset = {asset_id:'pa-video-blocked-01',workspace_id:'workspace-a',kind:'video',roles:['project_video'],filename:'Rainy street.mp4',media_type:'video/mp4',sha256:'c'.repeat(64),size_bytes:128,content_url:'/video.mp4',created_at:'2026-10-11T00:00:00Z'};
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Short film'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[]}));
  await page.route('**/api/video-summariser/capabilities?check_gpu_admission=1', route => route.fulfill({json:{gpu_admission:{available:false,checked:true,free_gib:2.1,reason:'GPU operating limit reached.'}}}));
  await page.route('**/api/media/workspace-a/**', route => {
    const request=route.request(),url=new URL(request.url());
    if(url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if(url.pathname.endsWith('/semantic-index-jobs')) return route.fulfill({json:[]});
    if(url.pathname.endsWith('/semantic-content-index') && request.method()==='POST') { jobsCreated++; return route.fulfill({status:202,json:{}}); }
    if(url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[asset],total:1,limit:50,offset:0}});
    return route.fulfill({json:{}});
  });

  await page.goto('/#/media-prep?tool=search&workspace_id=workspace-a&kind=video');
  const card=page.locator('.media-asset').filter({hasText:asset.filename});
  await card.getByRole('button',{name:'Index visual/media content for semantic search'}).click();
  await expect(page.getByText('Content indexing is blocked: GPU operating limit reached.')).toBeVisible();
  expect(jobsCreated).toBe(0);
});

test('workspace media library uploads an image and shows it in its type tab', async ({ page }) => {
  const assets = [];
  const seoStyles = [];
  let releaseSave;
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: {
    items: [{ workspace_id: 'workspace-a', title: 'Short film' }], limit: 50, offset: 0, total: 1,
  } }));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[{
    id:'user:Narrator.wav',name:'Narrator',source:'user',relative_path:'Narrator.wav',has_transcript:true,
    discoverable:true,user_managed:true,content_url:'/api/audio/voices/content?id=user%3ANarrator.wav',
    created_at:'2026-10-11T00:00:00Z',size_bytes:2048,
  }]}));
  await page.route('**/api/audio/voices/content**', route => route.fulfill({status:200,contentType:'audio/wav',body:Buffer.alloc(32)}));
  await page.route('**/api/media/workspace-a/assets**', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.pathname.endsWith('/assets/search')) {
      return route.fulfill({ json: { results: ['voice-asset','older-voice'].map(id => ({asset: assets.find(asset => asset.asset_id === id), score: 0.9, text: 'warm spoken voice'})), query_backend: 'test' } });
    }
    if (url.pathname.endsWith('/semantic-index')) {
      assets[0].semantic_annotation_index = {source:'saved_filename_description_tags_roles', source_sha256:'a'.repeat(64), annotation_sha256:'b'.repeat(64), model:'facebook/pe-av-base', dimension:1024};
      return route.fulfill({json:{asset:assets[0],indexed:true,source:'Saved text; pixels and raw audio/video are not embedded.'}});
    }
    if (url.pathname.endsWith('/seo-styles')) {
      if (request.method() === 'POST') {
        const payload = request.postDataJSON();
        const style = { style_id: 'seo-rain', name: payload.name, weighted_terms: Object.entries(payload.weighted_terms).map(([term, weight]) => ({term, weight})), avoid_terms: payload.avoid_terms, created_at: '2026-10-10T00:00:00Z' };
        seoStyles.push(style);
        return route.fulfill({status: 201, json: style});
      }
      return route.fulfill({json: {styles: seoStyles}});
    }
    if (request.method() === 'PATCH') {
      const annotations = request.postDataJSON();
      await new Promise(resolve => { releaseSave = resolve; });
      Object.assign(assets[0], annotations);
      return route.fulfill({ json: assets[0] });
    }
    if (request.method() === 'POST') {
      const role = url.searchParams.get('role');
      const asset = { asset_id: 'pa-0123456789abcdef', workspace_id: 'workspace-a', kind: 'image',
        roles: [role], filename: 'reference.png', media_type: 'image/png', sha256: 'a'.repeat(64),
        size_bytes: 128, content_url: '/api/media/workspace-a/assets/pa-0123456789abcdef/content',
        created_at: '2026-10-10T00:00:00Z', deduplicated: false,
        metadata: { production_image_job: { settings: { lineage: { target_name: 'Mira', target_type: 'character', target_record_id: 'character-mira', scene_number: 1, shot_number: 2, clip_id: 'clip-mira-01' } } }, image_analyses: [{job_id:'detail-job-1',source_sha256:'a'.repeat(64),mode:'balanced',saved_at:'2026-10-11T00:00:00Z',analysis:{setting:'Rainy courtroom',subjects:['Inspector Arjun'],mood:'tense'}}] } };
      assets.push(asset);
      return route.fulfill({ status: 201, json: asset });
    }
    return route.fulfill({ json: { assets: assets.filter(asset => asset.kind === (url.searchParams.get('kind') || 'image')), total: assets.length, limit: 50, offset: 0 } });
  });

  await page.goto('/#/media');
  await expect(page.getByRole('heading', { name: 'Search library' })).toBeVisible();
  await expect(page.getByLabel('Workspace', { exact: true })).toHaveValue('workspace-a');
  await page.getByLabel('Use as').selectOption('character_master');
  await page.locator('#media-upload').setInputFiles({ name: 'reference.png', mimeType: 'image/png', buffer: Buffer.from('test image bytes') });
  await page.getByRole('button', { name: 'Add asset' }).click();
  await expect(page.getByText('Added to the workspace library.')).toBeVisible();
  await expect(page.getByText('reference.png')).toBeVisible();
  await expect(page.getByText('Associated with: Mira · Scene 1 · Shot 2 · Clip clip-mira-01')).toBeVisible();
  const assetName = page.locator('.media-asset-name').filter({hasText:'reference.png'});
  await expect(assetName).toHaveCSS('text-overflow', 'ellipsis');
  await assetName.focus();
  await expect.poll(() => assetName.evaluate(element => getComputedStyle(element, '::after').content)).toBe('"reference.png"');
  const mediaCard = page.locator('.media-asset').filter({has: assetName});
  await mediaCard.hover();
  const preview = mediaCard.locator('.media-preview');
  await expect(preview).toHaveCSS('overflow', 'visible');
  await expect.poll(() => preview.locator('img').evaluate(image => new DOMMatrixReadOnly(getComputedStyle(image).transform).a)).toBeGreaterThan(1);
  await page.getByText('Image analysis · 1 saved').click();
  await expect(page.getByText(/"setting": "Rainy courtroom"/)).toBeVisible();
  await expect(mediaCard.getByRole('button', {name:'Index saved text for semantic search'})).toBeEnabled();
  await page.getByLabel('Description').fill('Rainy courtroom at blue hour');
  await page.getByLabel('Search tags').fill('courtroom, rain, blue hour');
  await page.getByRole('button', { name: 'Save search details' }).click();
  await expect(page.getByLabel('Description', {exact: true})).toBeDisabled();
  await expect(page.getByLabel('Search tags', {exact: true})).toBeDisabled();
  await expect.poll(() => typeof releaseSave).toBe('function');
  releaseSave();
  await expect(page.getByText('Search metadata saved.')).toBeVisible();
  await mediaCard.getByRole('button', {name:'Index saved text for semantic search'}).click();
  await expect(page.getByText(/Saved filename and search details are indexed with PE-AV text embeddings/)).toBeVisible();
  await expect(mediaCard.getByRole('button', {name:'Reindex saved text'})).toBeVisible();
  const librarySearch = page.getByLabel('Search images');
  await expect(librarySearch).toBeVisible();
  await expect(page.getByText('Search images', { exact: true })).toBeVisible();
  await expect.poll(() => librarySearch.evaluate(input => input.getBoundingClientRect().width)).toBeGreaterThan(350);
  await expect.poll(() => page.locator('.media-library-search').first().evaluate(search =>
    search.getBoundingClientRect().top < document.querySelector('.seo-style-manager').getBoundingClientRect().top)).toBe(true);
  await librarySearch.fill('blue hour');
  await expect(page.getByText('reference.png')).toBeVisible();
  await page.getByLabel('Filter images by role').selectOption('character');
  await expect(page.getByText('reference.png')).toBeVisible();
  await page.getByLabel('Filter images by role').selectOption('world');
  await expect(page.locator('.media-asset')).toHaveCount(0);
  await page.getByLabel('Filter images by role').selectOption('all');
  await expect(page.getByText('reference.png')).toBeVisible();
  await page.getByLabel('Search images').fill('');
  await page.getByLabel('Filter images by role').selectOption('all');
  await page.getByRole('button', { name: 'List view' }).click();
  await expect(page.getByRole('button', { name: 'List view' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.media-asset-grid')).toHaveClass(/media-view-list/);
  await page.getByRole('button', { name: 'Carousel view' }).click();
  await expect(page.locator('.media-asset-grid')).toHaveClass(/media-view-carousel/);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Carousel view' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Template view' }).click();
  await page.getByLabel('Search images').fill('unmatched phrase');
  await expect(page.getByText('No assets match this search.')).toBeVisible();
  await page.getByLabel('Search images').fill('');
  await page.getByLabel('SEO style name').fill('Rain noir');
  await page.getByLabel('Weighted search terms').fill('rain=2');
  await page.getByRole('button', {name: 'Save style'}).click();
  await expect(page.getByText('SEO search style saved.')).toBeVisible();
  await expect(page.getByLabel('Rank images by SEO style')).toHaveValue('seo-rain');
  assets.push(
    { asset_id: 'voice-asset', workspace_id: 'workspace-a', kind: 'audio', roles: ['voice_master'], filename: 'Arjun voice.wav', media_type: 'audio/wav', sha256: 'b'.repeat(64), size_bytes: 128, content_url: '/voice.wav', created_at: '2026-10-10T00:00:00Z', audio_category: 'voice', metadata:{analyzer_run_id:'run-a',occurrence_id:'voice-asset'} },
    { asset_id: 'older-voice', workspace_id: 'workspace-a', kind: 'audio', roles: ['voice_master'], filename: 'Older voice.wav', media_type: 'audio/wav', sha256: 'd'.repeat(64), size_bytes: 128, content_url: '/older.wav', created_at: '2026-10-08T00:00:00Z', audio_category: 'voice', metadata:{analyzer_run_id:'run-a',occurrence_id:'older-voice'} },
    { asset_id: 'clip-asset', workspace_id: 'workspace-a', kind: 'audio', roles: ['project_audio'], filename: 'Rain ambience.wav', media_type: 'audio/wav', sha256: 'c'.repeat(64), size_bytes: 128, content_url: '/rain.wav', created_at: '2026-10-09T00:00:00Z', audio_category: 'sfx', description: 'Rain ambience', provenance_notes: 'Collected from analyzed reference', metadata: {source_asset_id: 'source-video-1', source_asset_name: 'Courtroom reference.mp4', timestamp_start_seconds: 2, timestamp_end_seconds: 5.5} },
  );
  await page.getByRole('tab', { name: 'Audios' }).click();
  await expect(page.getByRole('heading', { name: 'Voice Files' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Audio Clips' })).toBeVisible();
  await expect(page.getByText('ComfyUI voice · original stays in place')).toBeVisible();
  await expect(page.getByText('Narrator.wav')).toBeVisible();
  await expect(page.getByText('Arjun voice.wav').first()).toBeVisible();
  await expect(page.getByText('Rain ambience.wav').first()).toBeVisible();
  const rainCard = page.locator('.audio-repertoire-panel').last().locator('.media-asset');
  await expect(rainCard.getByText('Audio type: sfx')).toBeVisible();
  await expect(rainCard.getByText('Added: 2026-10-09')).toBeVisible();
  await expect(rainCard.getByText('Source: Courtroom reference.mp4 · 2.00–5.50 sec')).toBeVisible();
  await expect(rainCard.getByText('Collected from analyzed reference')).toBeVisible();
  await rainCard.getByLabel('Audio type').selectOption('');
  await expect(rainCard.getByRole('button', { name: 'Save search details' })).toBeEnabled();
  await expect(page.locator('.audio-repertoire-panel').first().locator('.media-asset')).toHaveCount(3);
  await expect(page.locator('.audio-repertoire-panel').last().locator('.media-asset')).toHaveCount(1);
  await page.getByLabel('Search voice files').fill('Arjun');
  await expect(page.getByText('Arjun voice.wav').first()).toBeVisible();
  await expect(page.getByText('Rain ambience.wav').first()).toBeVisible();
  await page.getByLabel('voice files search mode').selectOption('semantic');
  await expect(page.getByText(/Search completed Video Summariser analysis and indexed library assets/)).toBeVisible();
  await page.getByLabel('Search voice files').fill('warm spoken voice');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByText('Found 2 semantic matches (test embeddings).')).toBeVisible();
  await expect(page.getByText('Arjun voice.wav').first()).toBeVisible();
  await expect(page.getByText('Narrator.wav')).toHaveCount(0);
  await page.getByRole('button', {name:'Sort voice files oldest first'}).click();
  await expect(page.locator('.audio-repertoire-panel').first().locator('.media-asset-name').first()).toHaveText('Older voice.wav');
  await page.getByLabel('Search voice files').fill('different query');
  await expect(page.getByText('The query changed. Run semantic search to refresh results.')).toBeVisible();
  await expect(page.locator('.audio-repertoire-panel').first().locator('.media-asset')).toHaveCount(0);
  await page.getByLabel('voice files search mode').selectOption('keyword');
  await page.getByLabel('Search voice files').fill('');
  await expect(page.getByText('Arjun voice.wav').first()).toBeVisible();
  await page.getByRole('button', { name: 'List view' }).first().click();
  await expect(page.getByRole('button', { name: 'List view' }).first()).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.audio-repertoire-panel').first().locator('.media-asset-grid')).toHaveClass(/media-view-list/);
  await expect(page.locator('.audio-repertoire-panel').last().locator('.media-asset-grid')).not.toHaveClass(/media-view-list/);
  await page.getByRole('tab', { name: 'Videos' }).click();
  await expect(page.getByText('No videos saved in this workspace yet.')).toBeVisible();
});

test('shared library accepts media files pasted or dropped into its upload target', async ({ page }) => {
  const uploads = [];
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Short film'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/media/workspace-a/assets**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if (request.method() === 'POST') {
      uploads.push(url.searchParams.get('filename'));
      return route.fulfill({status:201,json:{asset_id:`pa-${uploads.length}`,workspace_id:'workspace-a',kind:'image',roles:['style_reference'],filename:url.searchParams.get('filename'),media_type:'image/png',sha256:'a'.repeat(64),size_bytes:12,content_url:'/asset.png',created_at:'2026-10-11T00:00:00Z',deduplicated:false}});
    }
    return route.fulfill({json:{assets:[],total:0,limit:50,offset:0}});
  });
  await page.goto('/#/media');
  const target = page.getByRole('button', {name:'Choose, drop, or paste a media file'});
  await expect(target).toBeVisible();
  await target.evaluate(element => {
    element.focus();
    const clipboard = new DataTransfer();
    clipboard.items.add(new File(['clipboard image'], 'clipboard.png', {type:'image/png'}));
    element.dispatchEvent(new ClipboardEvent('paste', {clipboardData:clipboard,bubbles:true,cancelable:true}));
  });
  await expect(target).toContainText('clipboard.png');
  await page.getByRole('button', {name:'Add asset'}).click();
  await expect.poll(() => uploads).toEqual(['clipboard.png']);
  await target.evaluate(element => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['dropped image'], 'dropped.png', {type:'image/png'}));
    element.dispatchEvent(new DragEvent('drop', {dataTransfer:transfer,bubbles:true,cancelable:true}));
  });
  await expect(target).toContainText('dropped.png');
  await page.getByRole('button', {name:'Add asset'}).click();
  await expect.poll(() => uploads).toEqual(['clipboard.png','dropped.png']);
});

test('ComfyUI voice can be explicitly copied into the workspace and indexed without a duplicate catalog card', async ({ page }) => {
  const catalogVoice = {id:'comfy:voices/guide.wav',name:'Guide',source:'comfyui',relative_path:'voices/guide.wav',has_transcript:false,discoverable:true,user_managed:false,content_url:'/api/audio/voices/content?id=comfy%3Avoices%2Fguide.wav',created_at:'2026-10-11T00:00:00Z',size_bytes:2048};
  let imported;
  const importCalls = [];
  await page.route('**/api/story/workspaces?**', route => route.fulfill({json:{items:[{workspace_id:'workspace-a',title:'Short film'}],limit:50,offset:0,total:1}}));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[catalogVoice]}));
  await page.route('**/api/media/workspace-a/**', async route => {
    const request=route.request(),url=new URL(request.url());
    if(url.pathname.endsWith('/seo-styles')) return route.fulfill({json:{styles:[]}});
    if(url.pathname.endsWith('/semantic-index-jobs')) return route.fulfill({json:[]});
    if(url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:imported?[imported]:[],total:imported?1:0,limit:50,offset:0}});
    return route.fulfill({json:{}});
  });
  await page.route('**/api/audio/workspace-a/voice-library/import', async route => {
    importCalls.push(route.request().postDataJSON());
    imported={asset_id:'imported-guide',workspace_id:'workspace-a',kind:'audio',roles:['voice_master'],filename:'guide.wav',media_type:'audio/wav',sha256:'a'.repeat(64),size_bytes:2048,content_url:'/workspace/guide.wav',created_at:'2026-10-12T00:00:00Z',audio_category:'voice',metadata:{comfyui_voice_catalog:{catalog_id:catalogVoice.id,name:catalogVoice.name}}};
    return route.fulfill({status:201,json:{asset:imported}});
  });
  await page.goto('/#/media?kind=audio');
  await page.getByRole('tab',{name:'Audios'}).click();
  const catalogCard=page.locator('.audio-repertoire-panel').first().locator('.media-asset').filter({hasText:'voices/guide.wav'});
  await expect(catalogCard.getByRole('button',{name:'Add to workspace'})).toBeVisible();
  await expect(catalogCard.getByRole('button',{name:'Index visual/media content for semantic search'})).toHaveCount(0);
  await catalogCard.getByRole('button',{name:'Add to workspace'}).click();
  await expect.poll(()=>importCalls).toEqual([{voice_id:catalogVoice.id}]);
  await expect(page.getByText('guide.wav').first()).toBeVisible();
  await expect(page.getByText('ComfyUI voice · original stays in place')).toHaveCount(0);
  const copiedCard=page.locator('.audio-repertoire-panel').first().locator('.media-asset').filter({hasText:'guide.wav'});
  await expect(copiedCard.getByRole('button',{name:'Index visual/media content for semantic search'})).toBeVisible();
  await expect(page.locator('.audio-repertoire-panel').first().locator('.media-asset').filter({hasText:'voices/guide.wav'})).toHaveCount(0);
});
