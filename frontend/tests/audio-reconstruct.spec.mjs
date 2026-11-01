import { test, expect } from '@playwright/test';

test('Audio Reconstruct calibrates, prepares a dialogue part, and accepts a shared-library take', async ({ page }) => {
  const session = { version: 1, characters: [], parts: [], takes: [], updated_at: '2026-01-01T00:00:00Z' };
  const asset = { asset_id: 'pa-1234567890abcdef', workspace_id: 'ws-audio', kind: 'audio', roles: ['audio_clip'], filename: 'line.wav', media_type: 'audio/wav', sha256: 'abc', size_bytes: 20, content_url: '/line.wav', created_at: '2026-01-01T00:00:00Z' };
  await page.route('**/api/story/workspaces**', route => route.fulfill({ json: { items: [{ workspace_id: 'ws-audio', title: 'Audio test' }], total: 1 } }));
  await page.route('**/api/media/ws-audio/assets?kind=audio**', route => route.fulfill({ json: { assets: [asset], total: 1 } }));
  await page.route('**/api/audio/ws-audio/reconstruct**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (route.request().method() === 'GET') return route.fulfill({ json: session });
    const payload = route.request().postDataJSON();
    if (path.endsWith('/calibration')) {
      session.characters = [{ character_id: 'recon-char-1', name: payload.character_name, calibration_sentence: payload.sentence, status: 'calibrated' }];
      return route.fulfill({ json: session });
    }
    if (path.endsWith('/parts')) {
      session.parts = [{ ...payload, accepted_take_id: null }];
      return route.fulfill({ status: 201, json: session.parts[0] });
    }
    if (path.endsWith('/takes')) {
      session.takes = [{ take_id: 'scene_001_line_001_take_001', part_id: 'scene_001_line_001', sequence: 1, character_name: 'Mira', raw_path: 'audio/raw.wav', transcript: payload.transcript, status: 'raw', created_at: '2026-01-01T00:00:01Z' }];
      return route.fulfill({ status: 201, json: session.takes[0] });
    }
    if (path.endsWith('/accept/scene_001_line_001_take_001')) {
      session.parts[0].accepted_take_id = session.takes[0].take_id;
      session.takes[0].status = 'accepted';
      return route.fulfill({ json: { part: session.parts[0], take: session.takes[0], session, asset } });
    }
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected route' } } });
  });
  await page.goto('/#/media-prep');
  await page.getByRole('button', { name: 'Open Audio', exact: true }).click();
  await page.getByRole('article').filter({ has: page.getByRole('heading', { name: 'Audio Reconstruct' }) }).getByRole('button', { name: 'Open' }).click();
  await page.getByRole('heading', { name: 'Audio Reconstruct' }).waitFor();
  await page.getByLabel('Reconstruction workspace').selectOption('ws-audio');
  await page.getByRole('combobox', { name: 'Reconstruction character' }).fill('Mira');
  await page.getByRole('button', { name: 'Save calibration' }).click();
  await expect(page.getByText('Character calibration saved.')).toBeVisible();
  await page.getByLabel('Source audio asset').selectOption('pa-1234567890abcdef');
  await expect(page.getByRole('button', { name: 'Save take' })).toBeDisabled();
  await page.getByRole('textbox', { name: 'Expected dialogue' }).fill('We should leave now.');
  await page.getByRole('button', { name: 'Prepare dialogue part' }).click();
  await expect(page.getByText('Dialogue part prepared.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save take' })).toBeEnabled();
  await page.getByRole('button', { name: 'Save take' }).click();
  await expect(page.getByText('Take saved. Acceptance remains explicit.')).toBeVisible();
  await page.getByRole('button', { name: 'Accept take' }).click();
  await expect(page.getByText('Take accepted and added to the shared audio library.')).toBeVisible();
  await expect(page.getByText('Accepted', { exact: true })).toBeVisible();
});

test('Audio Reconstruct offers recording and simple/reference/RVC conversion without replacing dialogue tools',async({page})=>{
 const asset={asset_id:'source',workspace_id:'ws-audio',kind:'audio',roles:['audio_clip'],filename:'source.wav',content_url:'/source.wav',created_at:'2026-10-29'};
 const output={...asset,asset_id:'converted',filename:'changed.flac',content_url:'/changed.flac'};let posted=[];
 await page.route('**/api/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname;
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[{workspace_id:'ws-audio',title:'Audio test'}]}});
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
  if(path==='/api/media/ws-audio/assets')return route.fulfill({json:{assets:[asset],total:1}});
  if(path==='/api/audio/ws-audio/reconstruct')return route.fulfill({json:{version:1,characters:[],parts:[],takes:[]}});
  if(path==='/api/audio/effects/capabilities')return route.fulfill({json:{operations:['simple','voice_changer','rvc'].map(id=>({id,workflow_exists:true})),rvc_models:[{id:'voice.pth',name:'Trained voice',indexes:['voice.index']}]}});
  if(path==='/api/audio/voices')return route.fulfill({json:[{id:'target',name:'Target voice',discoverable:true,content_url:'/target.wav'}]});
  if(path==='/api/audio/ws-audio/effects/jobs'){
   if(req.method()==='GET')return route.fulfill({json:[]});
   posted.push(req.postDataJSON());return route.fulfill({json:{job_id:'job'+posted.length,status:'completed',progress:100,message:'Complete',result:{asset:output}}});
  }
  return route.fulfill({status:404,json:{error:{message:'Unused mock'}}});
 });
 await page.goto('/#/media-prep?tool=reconstruct&workspace_id=ws-audio');
 await expect(page.getByRole('heading',{name:'Audio Reconstruct',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Record',exact:true})).toBeVisible();
 await page.getByLabel('Voice conversion source').selectOption('');
 await expect(page.getByRole('button',{name:'Start voice change',exact:true})).toBeDisabled();
 await page.getByLabel('Voice conversion source').selectOption('source');
 await page.getByRole('combobox',{name:/^Voice effect/}).selectOption('telephone');
 await page.getByRole('button',{name:'Preview first 5 seconds'}).click();
 await expect.poll(()=>posted.length).toBe(1);expect(posted[0]).toMatchObject({operation:'simple',asset_id:'source',settings:{preset:'telephone',preview:true}});
 await page.getByRole('button',{name:'AI voice change',exact:true}).click();
 await expect(page.getByRole('button',{name:'Start voice change',exact:true})).toBeDisabled();
 await page.getByLabel('Target reference voice').selectOption('target');
 await page.getByRole('button',{name:'Start voice change',exact:true}).click();
 await expect.poll(()=>posted.length).toBe(2);expect(posted[1]).toMatchObject({operation:'voice_changer',settings:{target_voice_id:'target'}});
 await page.getByLabel('Conversion method').selectOption('rvc');
 await page.getByLabel('Trained RVC voice').selectOption('voice.pth');
 await page.getByRole('button',{name:'Start voice change',exact:true}).click();
 await expect.poll(()=>posted.length).toBe(3);expect(posted[2]).toMatchObject({operation:'rvc',settings:{model:'voice.pth'}});
 await page.getByRole('button',{name:'Use this result as source / dialogue take'}).click();
 await expect(page.getByLabel('Source audio asset')).toHaveValue('converted');
 await expect(page.getByRole('button',{name:'Save calibration'})).toBeVisible();
 await page.screenshot({path:'/tmp/vibe-audio-reconstruct-ui.png',fullPage:true});
});
