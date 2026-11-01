import assert from 'node:assert/strict';
import { expect, test } from '@playwright/test';

test('SAM save can recover when the library refresh fails after a successful save', async ({page}) => {
  const previewId = `sam-${'a'.repeat(32)}`;
  const savedAsset = {asset_id:'pa-1234567890abcdef',workspace_id:'ws-test',kind:'audio',roles:['project_audio'],filename:'isolated.wav',media_type:'audio/wav',sha256:'abc',size_bytes:100,content_url:'/isolated.wav',created_at:'2026-01-01T00:00:00Z'};
  let audioRefreshFailed = false;
  let audioRefreshes = 0;
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/video-summariser/sam/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({available:true,status:'ready',model:'facebook/sam-audio-large-tv',checkpoint_present:true,worker_configured:true,authentication_configured:true,reason:null})}));
  await page.route('**/api/media/ws-test/assets**', async route => {
    if (route.request().url().includes('kind=audio')) {
      audioRefreshes += 1;
      if (!audioRefreshFailed) {
        audioRefreshFailed = true;
        return route.fulfill({status:503,contentType:'application/json',body:'{"error":"temporary refresh failure"}'});
      }
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[savedAsset],total:1})});
    }
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})});
  });
  await page.route('**/api/video-summariser/ws-test/analysis/jobs', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([{
    job_id:'analysis-complete',status:'completed',request:{workspace_id:'ws-test'},result:{audio_analysis:[{
      run_id:'0123456789abcdef',asset_id:'pa-source12345678',audio_events:[{event_id:'rain-1',label:'Rain',event_type:'rain',start_time_sec:1,end_time_sec:3}]
    }]}
  }])}));
  await page.route('**/api/video-summariser/ws-test/analysis/runs/*/events/*/isolate', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({status:'preview_ready',temporary_id:previewId,model:'SAM Audio',prompt:'rain',audio_url:`/api/video-summariser/ws-test/sam/previews/${previewId}/audio`})}));
  let saves = 0;
  await page.route(`**/api/video-summariser/ws-test/sam/previews/${previewId}/save`, route => {
    saves += 1;
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({status:'saved',asset:savedAsset,idempotent:saves > 1})});
  });
  await page.route('**/api/video-summariser/ws-test/sam/previews/*/audio', route => route.fulfill({status:200,contentType:'audio/wav',body:Buffer.from('RIFF')}));

  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep?tool=video&videoPage=results`);
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByRole('heading',{name:'Isolate a detected sound'}).waitFor();
  await page.getByRole('textbox',{name:'Sound isolation prompt'}).fill('rain');
  await page.getByRole('button',{name:'Preview isolation'}).click();
  await page.getByText('Temporary preview · SAM Audio · rain').waitFor();
  await page.getByRole('button',{name:'Save to Audio Assets'}).click();
  await page.getByText('The sound is saved, but Audio Assets could not refresh. Retry Save to reload it.').waitFor();
  await page.getByText('Temporary preview · SAM Audio · rain').waitFor();
  await page.getByRole('button',{name:'Save to Audio Assets'}).click();
  await page.getByText('Saved the isolated sound to Audio Assets.').waitFor();
  assert.equal(saves,2);
  assert.ok(audioRefreshes >= 2, 'Save retry should reload Audio Assets after the first refresh fails');
});

test('late SAM isolation result is discarded when the director switches workspaces', async ({page}) => {
  const previewId = `sam-${'b'.repeat(32)}`;
  const workspaceBPreviewId = `sam-${'c'.repeat(32)}`;
  let releaseIsolation;
  let isolationStarted;
  let releaseWorkspaceBIsolation;
  let workspaceBIsolationStarted;
  let markDiscarded;
  const started = new Promise(resolve => { isolationStarted = resolve; });
  const release = new Promise(resolve => { releaseIsolation = resolve; });
  const workspaceBStarted = new Promise(resolve => { workspaceBIsolationStarted = resolve; });
  const workspaceBRelease = new Promise(resolve => { releaseWorkspaceBIsolation = resolve; });
  const discardFinished = new Promise(resolve => { markDiscarded = resolve; });
  let discardedWorkspace = '';
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[
    {workspace_id:'ws-a',title:'Workspace A'}, {workspace_id:'ws-b',title:'Workspace B'},
  ],total:2})}));
  await page.route('**/api/video-summariser/sam/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:'{"available":true,"status":"ready","model":"facebook/sam-audio-large-tv","checkpoint_present":true,"worker_configured":true,"authentication_configured":true,"reason":null}'}));
  await page.route('**/api/media/**/assets**', route => route.fulfill({status:200,contentType:'application/json',body:'{"assets":[],"total":0}'}));
  await page.route('**/api/video-summariser/ws-a/analysis/jobs', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([{
    job_id:'analysis-a',status:'completed',request:{workspace_id:'ws-a'},result:{audio_analysis:[{
      run_id:'0123456789abcdef',asset_id:'pa-source12345678',audio_events:[{event_id:'rain-a',label:'Rain',event_type:'rain',start_time_sec:1,end_time_sec:3}],
    }]},
  }])}));
  await page.route('**/api/video-summariser/ws-b/analysis/jobs', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([{
    job_id:'analysis-b',status:'completed',request:{workspace_id:'ws-b'},result:{audio_analysis:[{
      run_id:'fedcba9876543210',asset_id:'pa-source87654321',audio_events:[{event_id:'wind-b',label:'Wind',event_type:'wind',start_time_sec:4,end_time_sec:8}],
    }]},
  }])}));
  await page.route('**/api/video-summariser/ws-a/analysis/runs/*/events/*/isolate', async route => {
    isolationStarted();
    await release;
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({status:'preview_ready',temporary_id:previewId,model:'SAM Audio',prompt:'rain'})});
  });
  await page.route('**/api/video-summariser/ws-b/analysis/runs/*/events/*/isolate', async route => {
    workspaceBIsolationStarted();
    await workspaceBRelease;
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({status:'preview_ready',temporary_id:workspaceBPreviewId,model:'SAM Audio',prompt:'wind'})});
  });
  await page.route(`**/api/video-summariser/ws-a/sam/previews/${previewId}`, route => {
    assert.equal(route.request().method(),'DELETE');
    discardedWorkspace = 'ws-a';
    markDiscarded();
    return route.fulfill({status:200,contentType:'application/json',body:'{"status":"discarded"}'});
  });

  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep?tool=video&videoPage=results&workspace_id=ws-a`);
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByRole('heading',{name:'Isolate a detected sound'}).waitFor();
  await page.getByRole('textbox',{name:'Sound isolation prompt'}).fill('rain');
  await page.getByRole('button',{name:'Preview isolation'}).click();
  await started;
  await page.getByRole('button',{name:'Library'}).click();
  await page.getByLabel('Summariser workspace').selectOption('ws-b');
  await page.getByRole('button',{name:'Results'}).click();
  await expect(page.getByLabel('Detected audio event')).toHaveValue('fedcba9876543210|wind-b');
  await page.getByRole('textbox',{name:'Sound isolation prompt'}).fill('wind');
  await page.getByRole('button',{name:'Preview isolation'}).click();
  await workspaceBStarted;
  releaseIsolation();
  await discardFinished;
  assert.equal(discardedWorkspace,'ws-a');
  await expect(page.getByText('Temporary preview · SAM Audio · rain')).toHaveCount(0);
  releaseWorkspaceBIsolation();
  await page.getByText('Temporary preview · SAM Audio · wind').waitFor();
});
