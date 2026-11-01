import assert from 'node:assert/strict';
import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';

test('copied donor videos are imported only after explicit selection', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  const source = {asset_id:'video-donor-123456789abc',filename:'court.mp4',title:'Court scene',channel:'Archive',created_at:'2026-10-11T00:00:00Z',size_bytes:12_000_000,importable:true,sha256:'a'.repeat(64),source_mode:'youtube',source_url:'https://youtube.com/watch?v=demo'};
  const oversized = {...source,asset_id:'video-donor-too-large',filename:'oversized.mp4',title:'Oversized clip',size_bytes:512*1024*1024+1,importable:false};
  let library = [];
  await page.route('**/api/video-summariser/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:false,reason:'Unavailable.',checks:{}})}));
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/video-summariser/ws-test/library/donor', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([source,oversized])}));
  await page.route(`**/api/video-summariser/ws-test/library/donor/${source.asset_id}/content`, route => route.fulfill({path:fileURLToPath(new URL('./fixtures/archive-playback.mp4',import.meta.url)),contentType:'video/mp4'}));
  await page.route('**/api/video-summariser/ws-test/library/donor/import', async route => {
    assert.deepEqual(route.request().postDataJSON(),{asset_ids:[source.asset_id]});
    library=[{asset_id:'pa-donor-123456789abc',workspace_id:'ws-test',kind:'video',roles:['project_video'],filename:'court.mp4',media_type:'video/mp4',sha256:source.sha256,size_bytes:source.size_bytes,content_url:'/api/media/ws-test/assets/pa-donor-123456789abc/content',created_at:source.created_at,provenance_notes:`Imported from staged Story Builder Video Repertoire asset ${source.asset_id}`}];
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:library})});
  });
  await page.route('**/api/media/ws-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:library,total:library.length})}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Import copied Story Builder videos').click();
  assert.equal(await page.getByText('Court scene',{exact:true}).count(),0);
  await page.getByRole('button',{name:'Show copied videos'}).click();
  const videoPreview=page.getByLabel('Preview Court scene');
  await videoPreview.waitFor();
  assert.equal(await videoPreview.getAttribute('controls') !== null,true);
  assert.equal(await videoPreview.getAttribute('src'),`/api/video-summariser/ws-test/library/donor/${source.asset_id}/content`);
  // Headless Chromium in CI may lack an H.264 decoder. Verify the explicit
  // player is wired to the staged media endpoint; real playback is covered by
  // owner acceptance and the shared-library playback contract.
  assert.equal(await page.getByRole('checkbox',{name:/Oversized clip/}).isDisabled(),true);
  await page.getByText(/Over the 512 MiB per-file limit/).waitFor();
  const sourceCard=page.getByRole('article').filter({hasText:'Court scene'});
  await sourceCard.getByRole('button',{name:'Select for import'}).click();
  await expect(sourceCard.getByRole('checkbox',{name:/Court scene/})).toBeChecked();
  await sourceCard.getByRole('button',{name:'Remove from selection'}).click();
  await expect(sourceCard.getByRole('checkbox',{name:/Court scene/})).not.toBeChecked();
  await sourceCard.getByRole('button',{name:'Select for import'}).click();
  await page.getByRole('button',{name:'Import selected'}).click();
  await page.getByText('1 copied video added to this workspace library.').waitFor();
  assert.equal(await page.getByText('court.mp4').count(),1);
});

test('imports visible selections across bounded batches and keeps an unconfirmed batch selected for retry', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  const sources = Array.from({length:21},(_,index)=>({
    asset_id:`video-${(index+1).toString(16).padStart(12,'0')}`,filename:`clip-${index+1}.mp4`,title:`Clip ${index+1}`,
    channel:'Archive',created_at:'2026-10-11T00:00:00Z',size_bytes:1200,importable:true,sha256:String(index+1).padStart(64,'0'),source_mode:'youtube',source_url:'https://youtube.com/watch?v=demo',
  }));
  const batches=[];
  let imported=[];
  await page.route('**/api/video-summariser/capabilities',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:false,reason:'Unavailable.',checks:{}})}));
  await page.route('**/api/story/workspaces**',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/video-summariser/ws-test/library/donor',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(sources)}));
  await page.route('**/api/video-summariser/ws-test/library/donor/import',route=>{
    const ids=route.request().postDataJSON().asset_ids;
    batches.push(ids);
    if(batches.length===2) return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'temporary batch failure'})});
    const assets=ids.map((id,index)=>({asset_id:`pa-${id.slice(6)}`,workspace_id:'ws-test',kind:'video',roles:['project_video'],filename:`clip-${imported.length+index+1}.mp4`,media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:1200,content_url:'/video.mp4',created_at:'2026-10-11T00:00:00Z'}));
    imported=[...imported,...assets];
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets})});
  });
  await page.route('**/api/media/ws-test/assets**',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:imported,total:imported.length})}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Import copied Story Builder videos').click();
  await page.getByRole('button',{name:'Show copied videos'}).click();
  await page.getByRole('button',{name:'Select visible'}).click();
  await expect(page.getByText('21 selected · 21 available')).toBeVisible();
  await page.getByRole('button',{name:'Import selected'}).click();
  await expect(page.getByText(/20 of 21 selected videos were confirmed/)).toBeVisible();
  await expect(page.getByText('1 selected · 21 available')).toBeVisible();
  assert.deepEqual(batches.map(batch=>batch.length),[20,1]);
  await page.getByRole('button',{name:'Import selected'}).click();
  await page.getByText('1 copied video added to this workspace library.').waitFor();
  assert.deepEqual(batches.map(batch=>batch.length),[20,1,1]);
  assert.equal(batches[2][0],sources[20].asset_id);
  assert.equal(imported.length,21);
  await expect(page.getByText('0 selected · 21 available')).toBeVisible();
});

test('keeps the failed-batch retry guidance when the library refresh also fails', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  const sources = Array.from({length:21},(_,index)=>({
    asset_id:`video-${(index+1).toString(16).padStart(12,'0')}`,filename:`clip-${index+1}.mp4`,title:`Clip ${index+1}`,
    channel:'Archive',created_at:'2026-10-11T00:00:00Z',size_bytes:1200,importable:true,sha256:String(index+1).padStart(64,'0'),source_mode:'youtube',source_url:'https://youtube.com/watch?v=demo',
  }));
  let importCalls=0;
  await page.route('**/api/video-summariser/capabilities',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:false,reason:'Unavailable.',checks:{}})}));
  await page.route('**/api/story/workspaces**',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/video-summariser/ws-test/library/donor',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(sources)}));
  await page.route('**/api/video-summariser/ws-test/library/donor/import',route=>{
    importCalls+=1;
    if(importCalls===2) return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'temporary batch failure'})});
    const assets=route.request().postDataJSON().asset_ids.map((id,index)=>({asset_id:`pa-${id.slice(6)}`,workspace_id:'ws-test',kind:'video',roles:['project_video'],filename:`clip-${index+1}.mp4`,media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:1200,content_url:'/video.mp4',created_at:'2026-10-11T00:00:00Z'}));
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets})});
  });
  await page.route('**/api/media/ws-test/assets**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'library refresh failure'})}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Import copied Story Builder videos').click();
  await page.getByRole('button',{name:'Show copied videos'}).click();
  await page.getByRole('button',{name:'Select visible'}).click();
  await page.getByRole('button',{name:'Import selected'}).click();
  await expect(page.getByText(/20 of 21 selected videos were confirmed\. The failed batch and later videos remain selected; retry to continue\./)).toBeVisible();
  await expect(page.getByText(/The library could not refresh: Media request failed \(503\)/)).toBeVisible();
  await expect(page.getByText('1 selected · 21 available')).toBeVisible();
  await expect(page.getByRole('checkbox',{name:/Clip 21/})).toBeChecked();
  await expect(page.getByRole('button',{name:'Import selected'})).toBeEnabled();
  assert.equal(importCalls,2);
});

test('successful donor import is not reported as failed when the follow-up library refresh fails', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  const source = {asset_id:'video-donor-123456789abc',filename:'court.mp4',title:'Court scene',channel:'Archive',created_at:'2026-10-11T00:00:00Z',size_bytes:1200,importable:true,sha256:'a'.repeat(64),source_mode:'youtube',source_url:'https://youtube.com/watch?v=demo'};
  let importCompleted = false;
  await page.route('**/api/video-summariser/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:false,reason:'Unavailable.',checks:{}})}));
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/video-summariser/ws-test/library/donor', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([source])}));
  await page.route('**/api/video-summariser/ws-test/library/donor/import', route => { importCompleted=true; return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[{asset_id:'pa-imported-video',filename:'court.mp4'}]})}); });
  await page.route('**/api/media/ws-test/assets**', route => importCompleted
    ? route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Library temporarily unavailable.'})})
    : route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Import copied Story Builder videos').click();
  await page.getByRole('button',{name:'Show copied videos'}).click();
  await page.getByRole('checkbox',{name:/Court scene/}).check();
  await page.getByRole('button',{name:'Import selected'}).click();
  await page.getByText(/1 copied video added to this workspace library\. The library could not refresh:/).waitFor();
  assert.equal(await page.getByRole('button',{name:'Import selected'}).isDisabled(),true);
});

test('donor analysis audio is previewed and imported only after explicit selection', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  const source = {asset_id:'video-donor-123456789abc',filename:'court.mp4',title:'Court scene',channel:'Archive',created_at:'2026-10-11T00:00:00Z',size_bytes:12_000_000,sha256:'a'.repeat(64),source_mode:'youtube',source_url:'https://youtube.com/watch?v=demo'};
  const analysis = {video_asset_id:source.asset_id,analysis:{analysis_id:'analysis-demo',run_id:'run-demo',model:'summary-model',revision:'abc123',summary:'A tense courtroom argument.'},audio_assets:[{asset_id:'sfx_demo_01',category:'sfx',label:'Gavel strike',filename:'gavel.wav',start_time_sec:3.25,end_time_sec:4,size_bytes:3200,sha256:'b'.repeat(64)},{asset_id:'voice_demo_02',category:'voice',label:'Witness voice',filename:'voice.wav',start_time_sec:5,end_time_sec:6,size_bytes:3000,sha256:'c'.repeat(64)},{asset_id:'dialogue_demo_03',category:'dialogue',label:'Witness line',filename:'line.wav',start_time_sec:6,end_time_sec:7,size_bytes:3100,sha256:'d'.repeat(64)}]};
  let imported = false;
  await page.route('**/api/video-summariser/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:false,reason:'Unavailable.',checks:{}})}));
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/video-summariser/ws-test/library/donor', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([source])}));
  await page.route(`**/api/video-summariser/ws-test/library/donor/${source.asset_id}/analysis`, route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(analysis)}));
  await page.route(`**/api/video-summariser/ws-test/library/donor/${source.asset_id}/analysis/import`, async route => {
    assert.deepEqual(route.request().postDataJSON(),{asset_ids:['voice_demo_02','dialogue_demo_03']}); imported=true;
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[{asset_id:'pa-audio-voice-demo',kind:'audio',audio_category:'voice'},{asset_id:'pa-audio-dialogue-demo',kind:'audio',audio_category:'dialogue'}]})});
  });
  await page.route('**/api/media/ws-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Import copied Story Builder videos').click();
  await page.getByRole('button',{name:'Show copied videos'}).click();
  assert.equal(await page.getByText('A tense courtroom argument.').count(),0);
  await page.getByRole('button',{name:'Show analysis'}).click();
  await page.getByText('A tense courtroom argument.').waitFor();
  await page.getByRole('checkbox',{name:/Witness voice · voice/}).check();
  await page.getByRole('checkbox',{name:/Witness line · dialogue/}).check();
  assert.equal(imported,false);
  await page.getByRole('button',{name:'Import 2 selected audio clips'}).click();
  await page.getByText('2 analyzed audio clips added to this workspace library.').waitFor();
  assert.equal(imported,true);
});

test('late donor-video listing is discarded after a workspace switch', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  const source = {asset_id:'video-donor-late123456',filename:'old-workspace.mp4',title:'Old workspace clip',channel:'Archive',created_at:'2026-10-11T00:00:00Z',size_bytes:1200,sha256:'a'.repeat(64),source_mode:'youtube',source_url:'https://youtube.com/watch?v=demo'};
  let releaseDonorResponse;
  const donorResponse = new Promise(resolve => { releaseDonorResponse = resolve; });
  await page.route('**/api/video-summariser/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:false,reason:'Unavailable.',checks:{}})}));
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-one',title:'Workspace one'},{workspace_id:'ws-two',title:'Workspace two'}],total:2})}));
  await page.route('**/api/media/**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.route('**/api/video-summariser/ws-one/library/donor', async route => {
    await donorResponse;
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([source])});
  });
  await page.route('**/api/video-summariser/ws-two/library/donor', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL||'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Import copied Story Builder videos').click();
  await page.getByRole('button',{name:'Show copied videos'}).click();
  await page.getByLabel('Summariser workspace').selectOption('ws-two');
  releaseDonorResponse();
  await page.waitForTimeout(50);
  assert.equal(await page.getByText('Old workspace clip',{exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Show copied videos'}).isEnabled(),true);
});
