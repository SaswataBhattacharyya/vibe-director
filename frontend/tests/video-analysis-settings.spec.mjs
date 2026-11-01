import assert from 'node:assert/strict';
import { test } from '@playwright/test';

test('Video Summariser passes donor extraction and cut settings to its saved job', async ({page}) => {
  await page.route('**/api/video-summariser/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_analyze:true,reason:'Ready',checks:{}})}));
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-video',title:'Video workspace'}],limit:50,offset:0,total:1})}));
  await page.route('**/api/media/ws-video/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[{asset_id:'vid-1234567890abcdef',workspace_id:'ws-video',kind:'video',roles:['project_video'],filename:'source.mp4',media_type:'video/mp4',sha256:'abc',size_bytes:100,content_url:'/source.mp4',created_at:'2026-01-01T00:00:00Z'}],total:1})}));
  let createdJob;
  await page.route('**/api/video-summariser/ws-video/analysis/jobs**', async route => {
    if (route.request().method() === 'GET') return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(createdJob ? [createdJob] : [])});
    const payload = route.request().postDataJSON();
    assert.deepEqual(payload.settings, {
      extract_cut_clips:true, cut_boundary_threshold:0.27, min_cut_seconds:1.25,
      audio_analyzer_enabled:true,
      audio_analyzer:{extract_source_audio:true,extract_preview_mp3:true,detect_speech:true,diarize_speakers:true,detect_music:true,detect_sfx:true,create_audio_embeddings:true,create_av_embeddings:true,run_demucs:'AUTO',extract_fps:6,adaptive_sampling:true,frame_change_threshold:0.08,preserve_scene_anchors:true,keep_intermediate_samples:true,collect_voice_examples:false,collect_music_clips:false,collect_sfx_clips:false},
    });
    createdJob={job_id:'analysis-123456789abc',status:'queued',progress:0,stage:'queued',message:'Queued',events:[],request:{workspace_id:'ws-video',source_asset_ids:['vid-1234567890abcdef']}};
    await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify(createdJob)});
  });
  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep?tool=video&videoPage=analyze`);
  await page.getByRole('heading',{name:'Analyze videos'}).waitFor();
  await page.getByLabel('Scene change sampling rate').fill('6');
  await page.getByLabel('Cut change sensitivity').fill('0.27');
  await page.getByLabel('Minimum cut length').fill('1.25');
  await page.getByLabel('Keep temporary decode samples').check();
  await page.locator('.summariser-analysis-picker').first().getByRole('checkbox').first().check();
  await page.getByRole('button',{name:'Analyze selected videos'}).click();
  await page.getByText('Queued',{exact:true}).waitFor();
  assert.ok(createdJob);
});
