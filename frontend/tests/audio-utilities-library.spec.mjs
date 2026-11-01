import assert from 'node:assert/strict';
import { test } from '@playwright/test';

test('Audio Utilities imports shared media and filters operation-compatible sources', async ({page}) => {
  const assets = [];
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-test',title:'Test workspace'}],total:1})}));
  await page.route('**/api/audio/utilities/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({operations:[{id:'extract_mp3',status:'available',runtime:'ffmpeg'},{id:'noise_cleanup',status:'available',runtime:'audio tools'},{id:'demucs_stems',status:'available',runtime:'audio tools'}]})}));
  await page.route('**/api/audio/ws-test/utilities/jobs**', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.route('**/api/media/ws-test/assets**', async route => {
    const request = route.request();
    if (request.method() === 'POST') {
      const url = new URL(request.url());
      const filename = url.searchParams.get('filename');
      const role = url.searchParams.get('role');
      assert.equal(role, filename.endsWith('.mp4') ? 'project_video' : 'project_audio');
      const video = role === 'project_video';
      const asset = {asset_id:`asset-${assets.length+1}`,workspace_id:'ws-test',kind:video?'video':'audio',roles:[role],filename,media_type:video?'video/mp4':'audio/wav',sha256:'a'.repeat(64),size_bytes:10,content_url:'/media',created_at:new Date().toISOString(),description:'Imported test media',tags:[]};
      assets.push(asset);
      return route.fulfill({status:201,contentType:'application/json',body:JSON.stringify(asset)});
    }
    const kind = new URL(request.url()).searchParams.get('kind');
    const matching = assets.filter(asset=>asset.kind===kind);
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:matching,total:matching.length})});
  });
  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180'}/#/media-prep`);
  await page.getByRole('button',{name:'Open Audio'}).click();
  await page.getByRole('button',{name:'Open',exact:true}).last().click();
  await page.getByRole('heading',{name:'Audio Utilities'}).waitFor();
  await page.getByLabel('Audio utility workspace').selectOption('ws-test');
  const inputs = page.locator('input[type=file]');
  await inputs.nth(0).setInputFiles([
    {name:'voice.wav',mimeType:'audio/wav',buffer:Buffer.from('audio')},
    {name:'court.mp4',mimeType:'video/mp4',buffer:Buffer.from('video')},
  ]);
  await page.getByRole('button',{name:'Add 2 to library'}).click();
  await page.getByText('2 media files added to the shared library.').waitFor();
  await page.getByText('voice.wav',{exact:true}).waitFor();
  await page.getByText('court.mp4',{exact:true}).waitFor();
  await page.getByRole('searchbox',{name:'Search filenames, descriptions or tags'}).fill('court');
  await page.getByText('court.mp4',{exact:true}).waitFor();
  assert.equal(await page.getByText('voice.wav',{exact:true}).count(),0);
  await page.getByRole('checkbox',{name:'Select court.mp4',exact:true}).check();
  await page.getByLabel('Audio utility operation').selectOption('noise_cleanup');
  assert.equal(await page.getByRole('checkbox',{name:'Select court.mp4',exact:true}).count(),0);
  assert.equal(assets.find(asset=>asset.filename==='court.mp4').roles[0],'project_video');
  assert.equal(assets.find(asset=>asset.filename==='voice.wav').roles[0],'project_audio');

  await inputs.nth(0).setInputFiles({name:'voice.wav',mimeType:'audio/wav',buffer:Buffer.from('audio')});
  await page.getByRole('button',{name:'Add 1 to library'}).click();
  assert.equal(assets.filter(asset=>asset.filename==='voice.wav').length,2,'selecting the same file again should trigger a fresh import');
});
