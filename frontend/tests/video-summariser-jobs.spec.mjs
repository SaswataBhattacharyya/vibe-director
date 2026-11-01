import assert from 'node:assert/strict';
import { test } from '@playwright/test';

test('Video Summariser submits a shared video and shows the returned analysis', async ({page}) => {
  await page.setViewportSize({width:1280,height:900});
  const source = {asset_id:'video-source-1',workspace_id:'ws-test',kind:'video',roles:['project_video'],filename:'sample.mp4',media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:32,content_url:'/sample.mp4',created_at:'2026-10-11T00:00:00Z',description:'Courtroom scene',tags:['courtroom']};
  let job = null;
  let deleted = false;
  await page.route('**/api/video-summariser/capabilities**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:true,reason:'Ready.',gpu_admission:{available:true,checked:true,free_gib:22.5,required_gib:20,checked_at:new Date().toISOString()},checks:{analyzer_source:{available:true,state:'ready'},models:{available:true,state:'ready'},container_images:{available:true,state:'ready'},vibe_adapter:{available:true,state:'ready'}}})}));
  await page.route('**/api/video-summariser/sam/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({available:false,status:'gated_or_unavailable',model:'facebook/sam-audio-large-tv',checkpoint_present:false,worker_configured:true,authentication_configured:true,reason:'SAM Audio worker or checkpoint is not ready.'})}));
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/media/ws-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[source],total:1})}));
  await page.route('**/api/video-summariser/ws-test/analysis/jobs', async route => {
    if (route.request().method()==='POST') {
      const payload=route.request().postDataJSON();
      assert.deepEqual(payload.asset_ids,['video-source-1']);
      assert.equal(payload.settings.audio_analyzer_enabled,true);
      assert.equal(payload.settings.audio_analyzer.detect_music,false);
      assert.equal(payload.settings.audio_analyzer.collect_music_clips,true);
      assert.equal(payload.settings.audio_analyzer.run_demucs,'2-stem');
      job={job_id:'analysis-test-1',status:'queued',progress:0,stage:'queued',message:'Job is queued.',created_at:new Date().toISOString(),updated_at:new Date().toISOString(),request:{workspace_id:'ws-test',source_asset_ids:payload.asset_ids,settings:payload.settings},events:[],result:null};
      await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify(job)});
      return;
    }
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(job?[job]:[])});
  });
  await page.route('**/api/video-summariser/ws-test/analysis/jobs/analysis-test-1', route => {
    if (route.request().method()==='DELETE') {
      deleted=true; job=null;
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({deleted:true})});
    }
    job={...job,status:'completed',progress:100,stage:'completed',message:'Job completed.',result:{videos:[{title:'sample.mp4',summary:{detailed_video_summary:'A witness enters the courtroom.'},scenes:[{scene_id:'scene-1',start_time_sec:2,end_time_sec:8,summary:'Witness enters'}]}],audio_analysis:[{run_id:'0123456789abcdef',asset_id:'video-source-1',audio_events:[{event_id:'event-1',label:'Crowd cheer',event_type:'sfx',start_time_sec:3,end_time_sec:5}]}],published_assets:[],gpu_usage:{available:true,peak_mib:4000,peak_delta_mib:1500}},events:[]};
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(job)});
  });
  await page.route('**/api/video-summariser/ws-test/analysis/jobs/analysis-test-1/cancel', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(job)}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('article').filter({hasText:'Video Summariser'}).getByRole('button',{name:'Open',exact:true}).click();
  await page.getByRole('button',{name:/Analyze/}).click();
  await page.getByRole('checkbox',{name:'sample.mp4'}).check();
  await page.getByRole('checkbox',{name:'Music events'}).uncheck();
  await page.getByRole('checkbox',{name:'Save Music clips'}).check();
  await page.getByLabel('Audio source separation').selectOption('2-stem');
  await page.getByRole('button',{name:'Analyze selected videos'}).click();
  await page.getByText('A witness enters the courtroom.').waitFor({timeout:8000});
  await page.getByText('100% · completed').waitFor();
  assert.equal(await page.getByText('A witness enters the courtroom.').count(),1);
  await page.getByText('SAM Audio: SAM Audio worker or checkpoint is not ready.').waitFor();
  assert.equal(await page.getByRole('button',{name:'Preview isolation'}).isDisabled(),true);
  page.once('dialog',dialog=>dialog.dismiss());
  await page.getByRole('button',{name:'Delete analysis',exact:true}).click();
  assert.equal(deleted,false);
  page.once('dialog',dialog=>{assert.match(dialog.message(),/original imported\/downloaded video is kept/i);return dialog.accept();});
  await page.getByRole('button',{name:'Delete analysis',exact:true}).click();
  await page.getByText('Analysis and derived assets deleted. Original video retained.',{exact:true}).waitFor();
  assert.equal(deleted,true);
  await page.getByRole('button',{name:'Library',exact:true}).click();
  await page.getByText('sample.mp4',{exact:true}).waitFor();
});

test('Video Summariser reports low free memory without treating it as an admission limit', async ({page}) => {
  await page.setViewportSize({width:1280,height:900});
  let gpuChecks = 0;
  let releaseGpuCheck;
  let resolveGpuCheckStarted;
  const gpuCheckStarted = new Promise(resolve => { resolveGpuCheckStarted = resolve; });
  const gpuCheckGate = new Promise(resolve => { releaseGpuCheck = resolve; });
  await page.route('**/api/video-summariser/capabilities**', async route => {
    const checked = new URL(route.request().url()).searchParams.has('check_gpu_admission');
    if (checked) { gpuChecks++; resolveGpuCheckStarted(); await gpuCheckGate; }
    const gpu_admission = checked
      ? {available:true,checked:true,free_gib:3.4,checked_at:new Date().toISOString()}
      : undefined;
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:true,reason:'Analyzer setup ready.',gpu_admission,checks:{}})});
  });
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/media/ws-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep?tool=video`);
  await page.getByText('Setup ready',{exact:true}).waitFor();
  await page.getByText('Analyzer setup is ready. Runtime readiness will be checked before analysis.',{exact:true}).waitFor();
  assert.equal(gpuChecks,0);
  await page.getByRole('button',{name:'Analyze',exact:true}).click();
  await gpuCheckStarted;
  await page.getByText('Checking GPU health and workload availability…',{exact:true}).waitFor();
  assert.equal(gpuChecks,1);
  releaseGpuCheck();
  await page.getByText('Ready',{exact:true}).waitFor();
  await page.getByText('Ready · 3.4 GiB reported free (informational).',{exact:true}).waitFor();
  assert.equal(gpuChecks,1);
});

test('Video Summariser keeps analysis available when runtime checks pass with low reported free memory', async ({page}) => {
  await page.setViewportSize({width:1280,height:900});
  let gpuChecks = 0;
  let analysisPosts = 0;
  const source = {asset_id:'video-source-1',workspace_id:'ws-test',kind:'video',roles:['project_video'],filename:'sample.mp4',media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:32,content_url:'/sample.mp4',created_at:'2026-10-11T00:00:00Z'};
  await page.route('**/api/video-summariser/capabilities**', route => {
    const checked = new URL(route.request().url()).searchParams.has('check_gpu_admission');
    const gpu_admission = checked ? (gpuChecks++, {available:true,checked:true,free_gib:3.4,checked_at:new Date().toISOString()})
      : undefined;
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:true,reason:'Analyzer setup ready.',gpu_admission,checks:{}})});
  });
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/media/ws-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[source],total:1})}));
  await page.route('**/api/video-summariser/ws-test/analysis/jobs', route => {
    if(route.request().method()==='POST') analysisPosts++;
    return route.fulfill({status:200,contentType:'application/json',body:'[]'});
  });
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('article').filter({hasText:'Video Summariser'}).getByRole('button',{name:'Open',exact:true}).click();
  await page.getByRole('button',{name:/Analyze/}).click();
  await page.getByRole('checkbox',{name:'sample.mp4'}).check();
  await page.getByText('Ready · 3.4 GiB reported free (informational).',{exact:true}).waitFor();
  const analyze = page.getByRole('button',{name:'Analyze selected videos'});
  assert.equal(await analyze.isDisabled(),false);
  assert.ok(gpuChecks>=1);
  assert.equal(analysisPosts,0);
});

test('Video Summariser preflights GPU admission before retrying a failed job', async ({page}) => {
  await page.setViewportSize({width:1280,height:900});
  let retryPosts = 0;
  let admissionChecks = 0;
  const failed = {job_id:'analysis-failed-1',status:'failed',progress:10,stage:'gpu_admission',message:'GPU admission failed closed: ComfyUI reports only 3.4 GiB free; 20 GiB is required.',created_at:'2026-10-11T00:00:00Z',updated_at:'2026-10-11T00:01:00Z',request:{workspace_id:'ws-test',source_asset_ids:['video-source-1'],settings:{}},events:[],result:null,error:'Traceback (most recent):\nRuntimeError: legacy 20 GiB threshold.'};
  await page.route('**/api/video-summariser/capabilities**', route => {
    const checked = new URL(route.request().url()).searchParams.has('check_gpu_admission');
    const gpu_admission = checked ? {available:true,checked:true,free_gib:admissionChecks++===0?null:4.2,checked_at:new Date().toISOString()} : undefined;
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:true,reason:'Ready.',gpu_admission,checks:{}})});
  });
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/media/ws-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.route('**/api/video-summariser/ws-test/analysis/jobs**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([failed])}));
  await page.route('**/api/video-summariser/ws-test/analysis/jobs/analysis-failed-1/retry', route => {
    if(route.request().method()==='POST') retryPosts++;
    return route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({...failed,status:'queued'})});
  });
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep?tool=video&videoPage=results&workspace_id=ws-test`);
  const retry = page.getByRole('button',{name:'Retry analysis'});
  await retry.waitFor();
  await page.getByRole('heading',{name:'Earlier analysis stopped by the old memory check'}).waitFor();
  await page.getByText('This saved failure came from the old 20 GiB free-memory rule.',{exact:false}).waitFor();
  await page.getByText('Saved failure message',{exact:true}).click();
  await page.getByText('GPU admission failed closed: ComfyUI reports only 3.4 GiB free; 20 GiB is required.',{exact:true}).waitFor();
  await page.getByText('Ready · Free-memory reading unavailable (diagnostic only).',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Recheck runtime readiness'}).click();
  await page.getByText('Ready · 4.2 GiB reported free (informational).',{exact:true}).waitFor();
  assert.equal(await retry.isDisabled(),false);
  assert.equal(await page.getByText(/private\/runtime\/path/).count(),0);
  await retry.click();
  await page.getByText('Analysis restarted with its saved settings.',{exact:true}).waitFor();
  assert.equal(retryPosts,1);
});
