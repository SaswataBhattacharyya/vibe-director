import assert from 'node:assert/strict';
import { test, expect } from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

test('Media Prep opens image and audio libraries with working return paths', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  await mockProject(page,'ws-test');
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],limit:50,offset:0,total:1})}));
  await page.route('**/api/media/ws-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.route('**/api/media/ws-test/assets/seo-styles', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({styles:[]})}));
  await page.route('**/api/media/ws-test/content-index/jobs**', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.route('**/api/image-detailer/ws-test/jobs', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.route('**/api/audio/voices', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('heading',{name:'Media tools'}).waitFor();
  await page.getByRole('button',{name:'Open Images'}).click();
  await page.getByRole('heading',{name:'Search library'}).waitFor();
  assert.match(page.url(), /tool=image-home/);
  await page.getByRole('button',{name:'← Media Prep'}).click();
  await page.getByRole('heading',{name:'Media tools'}).waitFor();
  await page.getByRole('button',{name:'Open Audio'}).click();
  await page.getByRole('heading',{name:'Audio tools'}).waitFor();
  await page.getByRole('link',{name:'Open audio library'}).click();
  await page.getByRole('heading',{name:'Search library'}).waitFor();
  assert.equal(await page.getByRole('tab',{name:'Audios'}).getAttribute('aria-selected'),'true');
  await page.getByRole('heading',{name:'Voice Files'}).waitFor();
  await page.getByRole('heading',{name:'Audio Clips'}).waitFor();
  assert.match(page.url(), /kind=audio&from=audio/);
  await page.getByRole('button',{name:'← Audio'}).click();
  await page.getByRole('heading',{name:'Audio tools'}).waitFor();
});

test('Media Prep voice refresh and nested pages stay connected', async ({page}) => {
  await page.setViewportSize({width:1280,height:850});
  await page.route('**/api/studio-tools/output-destination', route => route.fulfill({json:{mode:'workspace',path:'/test-owned/outputs/audio',available:true}}));
  await mockProject(page,'story-test');
  await page.route('**/api/video-summariser/capabilities', route => route.fulfill({status:200, contentType:'application/json', body:JSON.stringify({
    can_analyze:false, reason:'Analysis is unavailable until the required components are ready.', checked_without_starting_jobs:true,
    checks:{
      analyzer_source:{available:true,state:'ready'},
      container_images:{available:false,state:'incomplete',items:{
        analysis:{available:true,state:'ready'},
        video_summary:{available:false,state:'image_missing',reason:'Required analyzer image is not built.'}
      }},
      vibe_adapter:{available:true,state:'ready'}
    }
  })}));
  await page.route('**/api/story/workspaces**', route => {
    const url=route.request().url();
    if(url.includes('/screenplay/revisions?'))return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{screenplay_revision_id:'screenplay-story-test',accepted:true,stale:false}],limit:100,offset:0,total:1})});
    if(url.includes('/voice-bindings?'))return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({workspace_id:'story-test',screenplay_revision_id:'screenplay-story-test',graph_snapshot_id:'graph-story-test',characters:[{record_id:'character-arjun',kind:'character',type:'character',name:'Arjun',detail:'',status:'source_supported',user_modified:false,properties:{},evidence:[]}],bindings:[{character_id:'character-arjun',voice_asset_id:'pa-bound-voice-1234567890',updated_at:'2026-10-13T00:00:00Z'}]})});
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'story-test',title:'Test workspace'}],limit:50,offset:0,total:1})});
  });
  await page.route('**/api/media/story-test/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.route('**/api/media/story-test/assets/seo-styles', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({styles:[]})}));
  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('heading', { name: 'Media tools' }).waitFor();
  assert.equal(await page.getByRole('navigation', { name: 'Studio navigation' }).getByRole('link', { name: 'Media Prep', exact: true }).getAttribute('aria-current'), 'page');
  assert.equal(await page.getByRole('button',{name:'Open Audio'}).count(),1);
  assert.equal(await page.getByRole('button',{name:'Open',exact:true}).count(),1);
  await page.getByRole('button',{name:'Open Search'}).click();
  await page.getByRole('heading',{name:'Search library'}).waitFor();
  assert.match(page.url(), /#\/media-prep\?tool=search/);
  assert.equal(await page.getByRole('navigation', { name: 'Studio navigation' }).getByRole('link', { name: 'Media Prep', exact: true }).getAttribute('aria-current'), 'page');
  await page.getByRole('button',{name:'← Media Prep'}).click();
  await page.getByRole('heading',{name:'Media tools'}).waitFor();
  await page.route('**/api/audio/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({comfyui_url:'http://127.0.0.1:3008',comfyui_online:true,comfyui_root_exists:true,tts_suite_exists:true,timed_tts_workflow_exists:true,voice_enrollment:true,voice_catalog_is_read_only:true,f5_dataset_preparation:{preparation_ready:true,training_enabled:false,python:'/python',message:'Dataset preparation ready.',checks:[],base_models:[{id:'F5TTS_v1_Base',available:true,checkpoint:'model_1250000.safetensors'}]}})}));
  await page.route('**/api/audio/voices', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([{id:'user:Bob.wav',name:'Bob',source:'user',relative_path:'Bob.wav',has_transcript:true,discoverable:true,user_managed:true},{id:'user:Alice.wav',name:'Alice',source:'user',relative_path:'Alice.wav',has_transcript:true,discoverable:true,user_managed:true}])}));
  await page.route('**/api/audio/models', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([])}));
  await page.route('**/api/media/story-test/assets?kind=audio**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[{asset_id:'pa-1234567890abcdef',workspace_id:'story-test',kind:'audio',roles:['project_audio'],filename:'voice.wav',media_type:'audio/wav',sha256:'abc',size_bytes:100,content_url:'/voice.wav',created_at:'2026-01-01T00:00:00Z',metadata:{analyzer_run_id:'test-analysis'}},{asset_id:'pa-bound-voice-1234567890',workspace_id:'story-test',kind:'audio',roles:['voice_master'],filename:'Arjun reference.wav',media_type:'audio/wav',sha256:'def',size_bytes:100,content_url:'/arjun-reference.wav',created_at:'2026-01-02T00:00:00Z',metadata:{comfyui_voice_catalog:{catalog_id:'user:Alice.wav',name:'Alice'}}}],total:2})}));
  await page.route('**/api/video-summariser/story-test/analysis/jobs', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.route('**/api/audio/story-test/finetune/f5/jobs**', async route => {
    if(route.request().method()==='GET') return route.fulfill({status:200,contentType:'application/json',body:'[]'});
    assert.deepEqual(route.request().postDataJSON(),{dataset_name:'voice_dataset',base_model:'F5TTS_v1_Base',samples:[{asset_id:'pa-1234567890abcdef',text:'Exact spoken words'}]});
    await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({job_id:'f5-prepare-123456789abc',status:'running',progress:1,stage:'starting',message:'Worker started.'})});
  });
  let timedJob = null;
  await page.route('**/api/audio/story-test/timed-tts/jobs**', async route => {
    if (route.request().method() === 'GET') return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(route.request().url().includes('/jobs/timed-tts-')?timedJob:[])});
    assert.deepEqual(route.request().postDataJSON(),{srt_content:'1\n00:00:00,000 --> 00:00:02,000\n[Arjun] Hello. [pause:500ms]',characters:[{name:'Arjun',reference_voice_id:'user:Alice.wav',language:'en'}],settings:{language:'English',timing_mode:'smart_natural',seed:1,exaggeration:.75,temperature:.8,cfg_weight:.5,enable_audio_cache:false,fade:.01,max_stretch_ratio:1,min_stretch_ratio:.5,timing_tolerance:2,batch_size:0}});
    timedJob={job_id:'timed-tts-123456789abc',status:'running',progress:1,stage:'starting',message:'Worker started.',events:[]};
    await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify(timedJob)});
  });
  await page.getByRole('button',{name:'Open Audio'}).click();
  await page.getByRole('heading',{name:'Audio tools'}).waitFor();
  assert.equal(await page.getByRole('link',{name:'Open audio library'}).getAttribute('href'),'#/media-prep?tool=search&kind=audio&from=audio');
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Audio Studio'}).waitFor();
  await expect(page.locator('#chat-audio')).toHaveCount(0);
  await expect(page.locator('.director-composer textarea')).toHaveCount(1);
  await page.locator('.audio-voice-list strong').filter({hasText:/^Alice$/}).waitFor();
  const voiceSearch=page.getByLabel('Search voice files');
  const audioSearch=page.getByLabel('Search audio clips');
  await voiceSearch.fill('Alice');
  assert.equal(await audioSearch.inputValue(),'');
  await audioSearch.fill('rain');
  assert.equal(await voiceSearch.inputValue(),'Alice');
  await voiceSearch.fill('');
  await audioSearch.fill('');
  await page.getByRole('textbox',{name:'Timed dialogue SRT'}).fill('1\n00:00:00,000 --> 00:00:02,000\n[Arjun] Hello. [pause:500ms]');
  await page.getByText('Character binding: Arjun reference.wav').waitFor();
  assert.equal(await page.getByLabel('Arjun voice').inputValue(),'');
  assert.equal(await page.getByRole('button',{name:'Generate timed audio'}).isDisabled(),true);
  await page.getByRole('button',{name:'Use bound voice'}).click();
  assert.equal(await page.getByLabel('Arjun voice').inputValue(),'user:Alice.wav');
  assert.equal(await page.getByRole('button',{name:'Generate timed audio'}).isDisabled(),false);
  await page.getByText('Advanced ChatterBox and timing settings').click();
  await page.getByLabel('Exaggeration').fill('0.75');
  await page.getByLabel('Cache generated audio chunks for reuse').uncheck();
  await page.getByLabel('Arjun voice').selectOption('user:Alice.wav');
  await page.getByLabel('Arjun language').selectOption('en');
  await page.getByRole('button',{name:'Generate timed audio'}).click();
  await page.getByText('Timed dialogue audio queued.').waitFor();
  await page.getByText(/running · 1%/).waitFor();
  await page.getByRole('button',{name:/voice.wav/}).click();
  await page.getByRole('textbox',{name:'New voice name'}).fill('New Voice');
  await page.getByRole('textbox',{name:'Exact voice transcript'}).fill('Exact spoken words');
  await page.route('**/api/audio/story-test/voices', async route => {
    assert.deepEqual(route.request().postDataJSON(),{asset_id:'pa-1234567890abcdef',name:'New Voice',transcript:'Exact spoken words'});
    await route.fulfill({status:201,contentType:'application/json',body:JSON.stringify({voice:{id:'user:New Voice.wav',name:'New Voice',source:'user',relative_path:'New Voice.wav',has_transcript:true,discoverable:true,user_managed:true},asset:{asset_id:'pa-1234567890abcdef',workspace_id:'story-test',kind:'audio',roles:['project_audio','voice_master'],filename:'voice.wav',media_type:'audio/wav',sha256:'abc',size_bytes:100,content_url:'/voice.wav',created_at:'2026-01-01T00:00:00Z',metadata:{analyzer_run_id:'test-analysis'}},live_discovery:{refreshed:true,restart_required:false},restart_required:false})});
  });
  await page.getByRole('button',{name:'Add to ComfyUI voices'}).click();
  await page.getByText('Voice file installed, added to Voice Files, and discovered by ComfyUI.').waitFor();
  await page.route('**/api/audio/voices/refresh', async route => {
    assert.deepEqual(route.request().postDataJSON(),{expected_voice_id:null});
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({refreshed:true,live_count:2,catalog_count:2,discovered_voice_ids:['user:Alice.wav'],restart_required:false})});
  });
  await page.getByRole('button',{name:'Refresh voices'}).click();
  await page.getByText('Voice list refreshed. ComfyUI sees 2 reference voices.').waitFor();
  await page.getByText('F5 dataset preparation').click();
  await page.getByRole('checkbox',{name:'voice.wav'}).check();
  await page.getByRole('textbox',{name:'Transcript for voice.wav'}).fill('Exact spoken words');
  await page.getByRole('button',{name:'Prepare dataset'}).click();
  await page.getByText('F5 dataset preparation queued. Training will not start.').waitFor();
  await page.getByRole('button',{name:'← Audio tools'}).click();
  await page.getByRole('button',{name:'← Media Prep'}).click();
  await page.getByRole('button',{name:'Open',exact:true}).first().click();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Add source videos, analyze them, then review the derived clips, frames and audio.').waitFor();
  await page.getByRole('button',{name:/Analyze/}).click();
  await page.getByText('Analyze videos',{exact:true}).waitFor();
  assert.match(page.url(), /tool=video.*videoPage=analyze|videoPage=analyze.*tool=video/);
  await page.reload();
  await page.getByRole('heading',{name:'Video Summariser'}).waitFor();
  await page.getByText('Analyze videos',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Library'}).click();
  await page.getByText('Add source videos, analyze them, then review the derived clips, frames and audio.').waitFor();
  await page.getByText('Unavailable',{exact:true}).waitFor();
  assert.equal(await page.getByText(/when the analyzer adapter is connected/).count(),0);
  for (const name of ['Library','YouTube Download','Analyze','Results','Audio Assets']) await page.getByRole('button',{name:new RegExp(name)}).waitFor();
  await page.getByRole('button',{name:/Analyze/}).click();
  await page.getByText('Analyzer setup checks',{exact:true}).click();
  await page.getByText(/Required analyzer image is not built/).waitFor();
  assert.equal(await page.getByRole('button',{name:'Analyze selected videos'}).isDisabled(),true);
  await page.getByRole('button',{name:'Audio Assets'}).click();
  await page.getByText('voice.wav',{exact:true}).waitFor();
});
