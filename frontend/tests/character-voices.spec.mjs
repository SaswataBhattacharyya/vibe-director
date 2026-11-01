import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/audio/voices', route => route.fulfill({json:[]}));
});

test('embedded voice panel reloads and saves against a changed route workspace', async ({ page }) => {
  const writes = [];
  await page.route('**/api/**', route => route.fulfill({ status: 404, json: { detail: 'Not used by this workspace-switch check.' } }));
  await page.route('**/api/audio/voices', route => route.fulfill({ json: [] }));
  await page.route('**/api/story/workspaces/workspace-*/screenplay/revisions?**', route => {
    const workspace = new URL(route.request().url()).pathname.split('/')[4];
    return route.fulfill({ json: { items: [{ screenplay_revision_id: `screenplay-${workspace}`, accepted: true, stale: false }] } });
  });
  await page.route('**/api/story/workspaces/workspace-*/production-setup?**', route => {
    const workspace = new URL(route.request().url()).pathname.split('/')[4];
    return route.fulfill({ json: { workspace_id: workspace, screenplay_revision_id: `screenplay-${workspace}`, setup: {
      mode: 'assisted_manual', automate_steps: { character_images: false, character_voice: false, world_images: false, frame_images: false, video: false },
      video_quality: 'standard', duration_policy: { kind: 'fixed', seconds: 5 },
    } } });
  });
  await page.route('**/api/story/workspaces/workspace-*/voice-bindings**', async route => {
    const workspace = new URL(route.request().url()).pathname.split('/')[4];
    if (route.request().method() === 'POST') writes.push({ workspace, body: route.request().postDataJSON() });
    const character = workspace === 'workspace-a'
      ? { record_id: 'character-a', kind: 'entity', type: 'character', name: 'Asha', detail: 'Detective.' }
      : { record_id: 'character-b', kind: 'entity', type: 'character', name: 'Mira', detail: 'Pilot.' };
    return route.fulfill({ json: { workspace_id: workspace, screenplay_revision_id: `screenplay-${workspace}`,
      graph_snapshot_id: `graph-${workspace}`, characters: [character], bindings: [] } });
  });
  await page.route('**/api/media/workspace-*/assets**', route => {
    const workspace = new URL(route.request().url()).pathname.split('/')[3];
    const kind = new URL(route.request().url()).searchParams.get('kind');
    const assets = kind === 'audio' ? [{ workspace_id: workspace, asset_id: 'pa-aaaaaaaaaaaaaaaa', kind: 'audio', roles: ['voice_master'],
      filename: 'Shared voice.wav', media_type: 'audio/wav', sha256: 'a'.repeat(64), size_bytes: 10, content_url: '/voice.wav', created_at: 'now' }] : [];
    return route.fulfill({ json: { assets, total: assets.length } });
  });

  await page.goto('/#/assets?step=character_images&workspace_id=workspace-a');
  await expect(page.getByLabel('Voice for Asha')).toBeVisible();
  await page.evaluate(() => { window.location.hash = '#/assets?step=character_images&workspace_id=workspace-b'; });
  await expect(page.getByLabel('Voice for Mira')).toBeVisible();
  await expect(page.getByLabel('Voice for Asha')).toHaveCount(0);
  await page.getByLabel('Voice for Mira').selectOption('pa-aaaaaaaaaaaaaaaa');
  await expect.poll(() => writes.length).toBe(1);
  expect(writes[0]).toMatchObject({ workspace: 'workspace-b', body: { character_id: 'character-b', voice_asset_id: 'pa-aaaaaaaaaaaaaaaa' } });
});

test('voice references are searchable, previewable, reusable and saved per canonical character', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  let bindings = [];
  await page.route('**/api/story/workspaces/workspace-a/screenplay/revisions?**', route => route.fulfill({ json: {
    items: [{ screenplay_revision_id: 'screenplay-a', accepted: true, stale: false }], limit: 100, offset: 0, total: 1,
  } }));
  await page.route('**/api/story/workspaces/workspace-a/production-setup?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', updated_at: 'now', setup: {
      mode: 'assisted_manual', automate_steps: { character_images: false, character_voice: false, world_images: false, frame_images: false, video: false },
      video_quality: 'standard', duration_policy: { kind: 'fixed', seconds: 5 },
    },
  } }));
  await page.route('**/api/story/workspaces/workspace-a/voice-bindings**', async route => {
    const req = route.request();
    if (req.method() === 'POST') {
      const body = req.postDataJSON();
      bindings = bindings.filter(item => item.character_id !== body.character_id);
      if (body.voice_asset_id) bindings.push({ character_id: body.character_id, voice_asset_id: body.voice_asset_id, updated_at: 'now' });
    }
    return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', graph_snapshot_id: 'graph-a',
      speech_statuses: [
        { character_id: 'char-asha', status: 'speaking', reason: 'Labeled dialogue is present.' },
        { character_id: 'char-ravi', status: 'not_speaking', reason: 'This character has no labeled dialogue.' },
      ],
      characters: [
        { record_id: 'char-asha', kind: 'entity', type: 'character', name: 'Asha', detail: 'Asha, a detective.', properties: {}, evidence: [] },
        { record_id: 'char-ravi', kind: 'entity', type: 'character', name: 'Ravi', detail: 'Asha’s colleague.', properties: {}, evidence: [] },
      ], bindings } });
  });
  await page.route('**/api/media/workspace-a/assets**', route => {
    const kind = new URL(route.request().url()).searchParams.get('kind');
    const common = { workspace_id: 'workspace-a', sha256: 'a'.repeat(64), size_bytes: 10, created_at: 'now' };
    const assets = kind === 'audio' ? [
      { ...common, asset_id: 'pa-aaaaaaaaaaaaaaaa', kind: 'audio', roles: ['voice_master'], filename: 'Warm narrator.wav', media_type: 'audio/wav', content_url: '/voice.wav', description: 'English narration in a low register', tags: ['warm', 'narration'] },
      { ...common, asset_id: 'pa-bbbbbbbbbbbbbbbb', kind: 'audio', roles: ['project_audio'], filename: 'Room tone.wav', media_type: 'audio/wav', content_url: '/room.wav' },
    ] : [{ ...common, asset_id: 'pa-cccccccccccccccc', kind: 'image', roles: ['character_master'], filename: 'asha.png', media_type: 'image/png', content_url: '/asha.png', metadata: { production_image_job: { settings: { lineage: { target_record_id: 'char-asha', target_type: 'character' } } } } }];
    return route.fulfill({ json: { assets, total: assets.length, limit: 50, offset: 0 } });
  });
  const catalog = ['Studio Narrator', 'David Attenborough', 'Morgan Freeman'].map(name=>({
    id:`user:${name}.wav`, name, source:'user', relative_path:`${name}.wav`,
    has_transcript:true, discoverable:true, user_managed:true, content_url:'/voice-preview.wav',created_at:'now',size_bytes:10,
  }));
  await page.route('**/api/audio/voices', route => route.fulfill({json:catalog}));
  const importIds = [];
  let failDavid = true;
  await page.route('**/api/audio/workspace-a/voice-library/import', async route => {
    const id = route.request().postDataJSON().voice_id;
    importIds.push(id);
    if (id.includes('David') && failDavid) { failDavid=false; return route.fulfill({status:500,json:{error:{message:'Temporary copy failure'}}}); }
    const voice=catalog.find(item=>item.id===id);
    return route.fulfill({json:{asset:{
      workspace_id:'workspace-a',asset_id:id.includes('Studio')?'pa-dddddddddddddddd':id.includes('David')?'pa-eeeeeeeeeeeeeeee':'pa-ffffffffffffffff',kind:'audio',roles:['voice_master'],filename:`${voice.name}.wav`,
      media_type:'audio/wav',sha256:'d'.repeat(64),size_bytes:10,content_url:'/studio-narrator.wav',created_at:'now',
      metadata:{comfyui_voice_catalog:{catalog_id:id,name:voice.name}},
    }}});
  });

  await page.goto('/#/assets');
  await expect(page.getByRole('heading', { name: 'Characters, worlds & frames' })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Asha reference' })).toBeVisible();
  await expect(page.getByText('Speaks in the accepted screenplay · voice not assigned')).toBeVisible();
  await expect(page.getByText('No labeled dialogue · voice optional')).toBeVisible();
  await expect(page.getByText('character · char-asha', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('checkbox', {name:'Select voice Studio Narrator',exact:true})).not.toBeVisible();
  await page.locator('.voice-catalog-dropdown summary').click();
  await page.getByRole('checkbox', {name:'Select voice Studio Narrator',exact:true}).check();
  await page.getByRole('button', {name:'Add selected (1)',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'added to this workspace'})).toBeVisible();
  await page.getByRole('button',{name:'Select all',exact:true}).click();
  await expect(page.getByRole('button',{name:'Add selected (2)',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Add selected (2)',exact:true}).click();
  await expect(page.getByRole('alert').filter({hasText:'Temporary copy failure'})).toBeVisible();
  await expect(page.getByRole('checkbox',{name:'Select voice David Attenborough',exact:true})).toBeChecked();
  await expect(page.getByLabel('Voice for Asha').locator('option',{hasText:'Morgan Freeman.wav'})).toHaveCount(1);
  await page.getByRole('button',{name:'Add selected (1)',exact:true}).click();
  await expect(page.getByLabel('Voice for Asha').locator('option',{hasText:'David Attenborough.wav'})).toHaveCount(1);
  await expect(page.getByLabel('Voice for Ravi').locator('option',{hasText:'David Attenborough.wav'})).toHaveCount(1);
  await expect(page.getByRole('region',{name:'Add ComfyUI voices'})).toHaveCount(0);
  expect(importIds).toEqual(['user:Studio Narrator.wav','user:David Attenborough.wav','user:Morgan Freeman.wav','user:David Attenborough.wav']);
  await page.getByLabel('Preview a voice before assigning').selectOption('pa-aaaaaaaaaaaaaaaa');
  const audition = page.locator('[aria-label="Preview voice sample Warm narrator.wav"]');
  await expect(audition).toBeVisible();
  await expect(audition).toHaveAttribute('src', '/voice.wav');
  expect(bindings).toHaveLength(0);
  await page.getByRole('searchbox', { name: 'Search voice previews' }).fill('warm');
  await page.getByLabel('Voice for Asha').selectOption('pa-aaaaaaaaaaaaaaaa');
  await expect(page.locator('[aria-label="Preview Warm narrator.wav"]')).toBeVisible();
  await expect(page.getByText('English narration in a low register', { exact: true })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Search voice previews' }).fill('no match');
  await expect(page.getByLabel('Voice for Asha')).toHaveValue('pa-aaaaaaaaaaaaaaaa');
  await page.getByRole('searchbox', { name: 'Search voice previews' }).fill('English');
  await expect(page.getByLabel('Voice for Asha').locator('option', { hasText: 'Warm narrator.wav' })).toHaveCount(1);
  await page.getByRole('searchbox', { name: 'Search voice previews' }).fill('warm');
  await page.getByLabel('Voice for Ravi').selectOption('pa-aaaaaaaaaaaaaaaa');
  await expect(page.getByText('Voice assignment saved.', { exact: true })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Search voice previews' }).fill('studio');
  await page.getByLabel('Voice for Asha').selectOption('pa-dddddddddddddddd');
  await expect(page.getByText('Voice assignment saved.', { exact: true })).toBeVisible();
  expect(bindings.map(item => item.voice_asset_id)).toEqual(['pa-aaaaaaaaaaaaaaaa', 'pa-dddddddddddddddd']);
  await page.getByRole('button', { name: 'Clear voice', exact: true }).first().click();
  await expect.poll(()=>bindings.length).toBe(1);
  expect(bindings[0].character_id).toBe('char-ravi');
  await page.getByRole('link', { name: 'Worlds' }).click();
  await expect(page.getByRole('heading', { name: 'Worlds', exact: true })).toBeVisible();
});

test('automatic voice matching binds clear matches and lets the director resolve an unmatched character', async ({ page }) => {
  let manualWrites = 0;
  let automatedRuns = 0;
  let assignedVoice = 'pa-aaaaaaaaaaaaaaaa';
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  await page.route('**/api/story/workspaces/workspace-a/screenplay/revisions?**', route => route.fulfill({ json: {
    items: [{ screenplay_revision_id: 'screenplay-a', accepted: true, stale: false }], limit: 100, offset: 0, total: 1,
  } }));
  await page.route('**/api/story/workspaces/workspace-a/production-setup?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', updated_at: 'now', setup: {
      mode: 'assisted_manual', automate_steps: { character_images: false, character_voice: true, world_images: false, frame_images: false, video: false },
      video_quality: 'standard', duration_policy: { kind: 'fixed', seconds: 5 },
    },
  } }));
  await page.route('**/api/story/workspaces/workspace-a/voice-bindings**', async route => {
    const url = route.request().url();
    if (route.request().method() === 'POST' && url.endsWith('/auto-match')) {
      automatedRuns += 1;
      return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', graph_snapshot_id: 'graph-a',
        characters: [{ record_id: 'char-asha', kind: 'entity', type: 'character', name: 'Asha', detail: 'Detective.', properties: {}, evidence: [] }],
        bindings: [], automation_decisions: [{ character_id: 'char-asha', status: 'unmatched', voice_asset_id: null, candidate_asset_ids: [], reason: 'No direct match.' }],
        automation_result: [{ character_id: 'char-asha', status: 'unmatched', voice_asset_id: null, candidate_asset_ids: [], reason: 'No direct match.' }],
      } });
    }
    if (route.request().method() === 'POST') { manualWrites += 1; assignedVoice = route.request().postDataJSON().voice_asset_id; }
    return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', graph_snapshot_id: 'graph-a',
      characters: [{ record_id: 'char-asha', kind: 'entity', type: 'character', name: 'Asha', detail: 'Detective.', properties: {}, evidence: [] }],
      bindings: assignedVoice ? [{ character_id: 'char-asha', voice_asset_id: assignedVoice, updated_at: 'now' }] : [],
      automation_decisions: [{ character_id: 'char-asha', status: 'resolved_manually', voice_asset_id: 'pa-aaaaaaaaaaaaaaaa', candidate_asset_ids: [], reason: 'Director resolved.' }],
    } });
  });
  await page.route('**/api/media/workspace-a/assets**', route => {
    const kind = new URL(route.request().url()).searchParams.get('kind');
    return route.fulfill({ json: { total: 1, assets: kind === 'audio' ? [{
      workspace_id: 'workspace-a', asset_id: 'pa-aaaaaaaaaaaaaaaa', kind: 'audio', roles: ['voice_master'], filename: 'Asha voice.wav',
      media_type: 'audio/wav', sha256: 'a'.repeat(64), size_bytes: 10, created_at: 'now', content_url: '/asha.wav',
    }] : [] } });
  });
  await page.goto('/#/assets');
  await expect(page.getByText('Automatic matching uses explicit character names')).toBeVisible();
  await expect(page.getByText(/No direct match · choose a voice/)).toBeVisible();
  await expect(page.getByLabel('Voice for Asha')).toBeEnabled();
  await page.getByLabel('Voice for Asha').selectOption('pa-aaaaaaaaaaaaaaaa');
  await expect(page.getByText(/Match resolved by you/)).toBeVisible();
  await expect(page.getByLabel('Voice for Asha')).toBeEnabled();
  await page.getByRole('button', {name:'Clear voice',exact:true}).click();
  await expect(page.getByLabel('Voice for Asha')).toHaveValue('');
  await page.getByLabel('Voice for Asha').selectOption('pa-aaaaaaaaaaaaaaaa');
  await expect(page.getByLabel('Voice for Asha')).toHaveValue('pa-aaaaaaaaaaaaaaaa');
  expect(manualWrites).toBe(3);
  expect(automatedRuns).toBe(1);
});

test('Assisted character image stage includes voice assignment for the route workspace and current accepted screenplay', async ({ page }) => {
  const requests = [];
  let autoMatches = 0;
  let setupMode = 'assisted_manual';
  await page.route('**/api/**', route => route.fulfill({ status: 404, json: { detail: 'Not used in this focused character and voice check.' } }));
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-other'));
  await page.route('**/api/story/workspaces/workspace-target/screenplay/revisions?**', route => route.fulfill({ json: {
    items: [
      { screenplay_revision_id: 'screenplay-stale', accepted: true, stale: true },
      { screenplay_revision_id: 'screenplay-current', accepted: true, stale: false },
    ], limit: 100, offset: 0, total: 2,
  } }));
  await page.route('**/api/story/workspaces/workspace-target/screenplay/revisions/screenplay-current', route => route.fulfill({ json: {
    workspace_id: 'workspace-target', screenplay_revision_id: 'screenplay-current', graph_snapshot_id: 'graph-current',
    screenplay: { scenes: [] },
  } }));
  await page.route('**/api/story/workspaces/workspace-target/graph?snapshot_id=graph-current', route => route.fulfill({ json: {
    snapshot_id: 'graph-current', records: [{ record_id: 'char-asha', kind: 'entity', type: 'character', name: 'Asha', detail: 'Detective.', properties: {}, evidence: [] }],
  } }));
  await page.route('**/api/story/workspaces/workspace-target/production-setup?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-target', screenplay_revision_id: 'screenplay-current', setup: {
      mode: setupMode, automate_steps: { character_images: false, character_voice: false, world_images: false, frame_images: false, video: false },
      video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 },
    },
  } }));
  await page.route('**/api/story/workspaces/workspace-target/voice-bindings**', async route => {
    const request = route.request();
    requests.push({ method: request.method(), url: request.url() });
    if (request.url().endsWith('/auto-match')) autoMatches += 1;
    return route.fulfill({ json: { workspace_id: 'workspace-target', screenplay_revision_id: 'screenplay-current', graph_snapshot_id: 'graph-current',
      characters: [{ record_id: 'char-asha', kind: 'entity', type: 'character', name: 'Asha', detail: 'Detective.', properties: {}, evidence: [] }], bindings: [],
    } });
  });
  await page.route('**/api/media/workspace-target/assets**', route => route.fulfill({ json: { assets: [], total: 0, limit: 50, offset: 0 } }));
  await page.route('**/api/audio/voices', route => route.fulfill({json:[]}));

  await page.goto('/#/assets?step=character_images&workspace_id=workspace-target');
  await expect(page.getByRole('heading', { name: 'Character image step' })).toBeVisible();
  await expect(page.getByLabel('Character voice assignments')).toBeVisible();
  await expect(page.getByLabel('Voice for Asha')).toBeEnabled();
  expect(requests.some(item => item.url.includes('screenplay_revision_id=screenplay-current'))).toBe(true);
  expect(requests.some(item => item.url.includes('workspace-target'))).toBe(true);
  expect(requests.some(item => item.url.includes('workspace-other'))).toBe(false);
  expect(autoMatches).toBe(0);

  const worldNext = page.getByRole('link', { name: 'Continue to World images' });
  await expect(worldNext).toHaveAttribute('href', '#/assets?step=world_images&workspace_id=workspace-target');
  await worldNext.click();
  await expect(page.getByRole('heading', { name: 'World image step' })).toBeVisible();
  await expect(page.getByLabel('Character voice assignments')).toHaveCount(0);
  const framesNext = page.getByRole('link', { name: 'Continue to First & last frames' });
  await expect(framesNext).toHaveAttribute('href', '#/assets?step=frame_images&workspace_id=workspace-target');
  await framesNext.click();
  await expect(page.getByRole('heading', { name: 'Clip frame step' })).toBeVisible();
  await expect(page.getByRole('link', { name: /Continue to (World images|First & last frames)/ })).toHaveCount(0);

  setupMode = 'fully_automated';
  await page.goto('/#/assets?step=character_images&workspace_id=workspace-target');
  await page.reload();
  await expect(page.getByText('Manual voice assignment is skipped in Fully automated mode.')).toBeVisible();
  await expect(page.getByLabel('Voice for Asha')).toBeDisabled();
  await expect(page.getByRole('link', { name: /Continue to (World images|First & last frames)/ })).toHaveCount(0);
  expect(autoMatches).toBe(0);
});


test('Assisted frame stage prepares only the selected accepted screenplay shot for Video Create', async ({ page }) => {
  let setupMode = 'assisted_manual';
  let automateVideo = false;
  let preparedRequest;
  let savedRequest;
  await page.route('**/api/**', route => route.fulfill({ status: 404, json: { detail: 'Not used by this first-shot handoff check.' } }));
  await page.route('**/api/story/workspaces/workspace-video/screenplay/revisions?**', route => route.fulfill({ json: {
    items: [{ screenplay_revision_id: 'screenplay-video', accepted: true, stale: false }], limit: 100, offset: 0, total: 1,
  } }));
  await page.route('**/api/story/workspaces/workspace-video/screenplay/revisions/screenplay-video', route => route.fulfill({ json: {
    workspace_id: 'workspace-video', screenplay_revision_id: 'screenplay-video', accepted: true, graph_snapshot_id: 'graph-video',
    screenplay: { title: 'Two-shot story', scenes: [
      { scene_number: 1, slugline: 'INT. STATION - NIGHT', summary: 'Asha arrives.', shots: [
        { shot_number: 1, action: 'The station doors open.', dialogue: '', direction: { camera: '', lighting: '', mood: '', sfx: '', music: '' }, evidence: [] },
        { shot_number: 2, action: 'Asha studies the case board.', dialogue: '', direction: { camera: '', lighting: '', mood: '', sfx: '', music: '' }, evidence: [] },
      ] },
      { scene_number: 2, slugline: 'EXT. STREET - NIGHT', summary: 'Ravi waits outside.', shots: [
        { shot_number: 1, action: 'Ravi checks the street.', dialogue: '', direction: { camera: '', lighting: '', mood: '', sfx: '', music: '' }, evidence: [] },
      ] },
    ] },
  } }));
  await page.route('**/api/story/workspaces/workspace-video/production-setup?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-video', screenplay_revision_id: 'screenplay-video', setup: {
      mode: setupMode, automate_steps: { character_images: false, character_voice: false, world_images: false, frame_images: false, video: automateVideo },
      video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 },
    },
  } }));
  await page.route('**/api/story/workspaces/workspace-video/graph?snapshot_id=graph-video', route => route.fulfill({ json: { snapshot_id: 'graph-video', records: [] } }));
  await page.route('**/api/story/workspaces/workspace-video/frame-preparation-skips?**', route => route.fulfill({ json: { workspace_id: 'workspace-video', screenplay_revision_id: 'screenplay-video', skipped: [] } }));
  await page.route('**/api/story/workspaces/workspace-video/prompt-drafts/prepare', async route => {
    preparedRequest = route.request().postDataJSON();
    return route.fulfill({ json: { shot_key: '1.2', workflow_id: 'minimax_h3_r2v_dynamic_v1', prompt: 'Asha studies the board in a measured close shot.', knowledge_ref: { knowledge_id: 'knowledge-video', guidance_version: 3, workflow_sha256: 'b'.repeat(64) }, sources: [] } });
  });
  await page.route('**/api/story/workspaces/workspace-video/prompt-drafts/shot', async route => {
    savedRequest = route.request().postDataJSON();
    return route.fulfill({ json: { workspace_id: 'workspace-video', screenplay_revision_id: 'screenplay-video', setup_hash: 'setup-hash-video', setup_matches_current: true,
      drafts: { '1.2': { workflow_id: 'minimax_h3_r2v_dynamic_v1', prompt: 'Asha studies the board in a measured close shot.', knowledge_ref: { knowledge_id: 'knowledge-video', guidance_version: 3, workflow_sha256: 'b'.repeat(64) } } }, updated_at: 'now',
    } });
  });
  await page.route('**/api/story/workspaces?limit=*', route => route.fulfill({ json: { items: [], limit: 50, offset: 0, total: 0 } }));
  await page.route('**/api/media/**', route => route.fulfill({ json: { assets: [], total: 0, limit: 50, offset: 0 } }));
  await page.goto('/#/assets?step=frame_images&workspace_id=workspace-video');
  await expect(page.getByRole('heading', { name: 'Clip frame step' })).toBeVisible();
  await expect(page.getByText(/Assisted manual · frame images are unchecked/)).toBeVisible();
  await expect(page.getByRole('region', { name: 'Open a screenplay shot in Video Create' })).toBeVisible();
  await page.getByLabel('Planned clip').selectOption('1.2');
  await page.getByLabel('Video workflow for selected shot').selectOption('minimax_h3_r2v_dynamic_v1');
  await page.getByRole('button', { name: 'Prepare this shot and open Video Create' }).click();
  await expect(page.getByRole('heading', { name: 'Create video' })).toBeVisible();
  const videoDraft = await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-draft-v1')));
  expect(preparedRequest).toMatchObject({ screenplay_revision_id: 'screenplay-video', shot_key: '1.2', workflow_id: 'minimax_h3_r2v_dynamic_v1' });
  expect(savedRequest).toMatchObject({ screenplay_revision_id: 'screenplay-video', shot_key: '1.2', setup: { mode: 'assisted_manual' }, draft: { workflow_id: 'minimax_h3_r2v_dynamic_v1' } });
  expect(videoDraft).toMatchObject({ workspaceId: 'workspace-video', clipId: expect.stringMatching(/^story-/), workflowId: 'minimax_h3_r2v_dynamic_v1', prompt: 'Asha studies the board in a measured close shot.', sourceLineage: { screenplay_revision_id: 'screenplay-video', setup_hash: 'setup-hash-video', scene_number: 1, shot_number: 2 } });
  expect(videoDraft.sourceLineage.source_prompt_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(videoDraft.sourceLineage.knowledge_ref.knowledge_id).toBe('knowledge-video');

  automateVideo = true;
  await page.goto('/#/assets?step=frame_images&workspace_id=workspace-video');
  await page.reload();
  await expect(page.getByRole('region', { name: 'Open a screenplay shot in Video Create' })).toHaveCount(0);
  setupMode = 'fully_automated';
  automateVideo = false;
  await page.goto('/#/assets?step=frame_images&workspace_id=workspace-video');
  await page.reload();
  await expect(page.getByRole('region', { name: 'Open a screenplay shot in Video Create' })).toHaveCount(0);
});


test('choosing a ComfyUI voice in a character dropdown imports and assigns in one step',async({page})=>{
  const writes=[];
  const asset={workspace_id:'voice-project',asset_id:'voice-imported',kind:'audio',roles:['voice_master'],filename:'My voice.wav',content_url:'/voice.wav',metadata:{comfyui_voice_catalog:{catalog_id:'user:my.wav'}}};
  let bindings=[], imported=false, mode='assisted_manual';
  await page.addInitScript(()=>localStorage.setItem('vibe-story-selected-v1','voice-project'));
  await page.route('**/api/**',route=>{
    const req=route.request(),url=new URL(req.url());
    let data;
    if(url.pathname==='/api/images/selections')data={selection:null};
    else if(url.pathname==='/api/audio/voices')data=[{id:'user:my.wav',name:'My voice',source:'user'}];
    else if(url.pathname.endsWith('/screenplay/revisions'))data={items:[{screenplay_revision_id:'rev',accepted:true,stale:false}]};
    else if(url.pathname.endsWith('/production-setup'))data={setup:{mode,automate_steps:{character_voice:false}}};
    else if(url.pathname.includes('/voice-bindings')){
      if(req.method()==='POST'){writes.push(req.postDataJSON());const body=req.postDataJSON();bindings=[...bindings.filter(row=>row.character_id!==body.character_id),{character_id:body.character_id,voice_asset_id:body.voice_asset_id}];}
      data={screenplay_revision_id:'rev',characters:[{record_id:'char',name:'Mira'},{record_id:'char-two',name:'Asha'}],bindings};
    }else if(url.pathname.endsWith('/voice-library/import')){imported=true;writes.push(req.postDataJSON());data={asset};}
    else if(url.pathname.endsWith('/assets'))data={assets:imported?[asset]:[],total:imported?1:0};
    return route.fulfill(data?{json:data}:{status:404,json:{error:{message:'Not used'}}});
  });
  await page.goto('/#/characters?workspace_id=voice-project');
  await expect(page.getByLabel('Voice for Mira')).toBeEnabled();
  await page.getByLabel('Voice for Mira').click();
  await expect.poll(() => page.getByLabel('Voice for Mira').evaluate(select => select.matches(':open'))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByLabel('Voice for Mira')).toHaveValue('');
  expect(writes).toHaveLength(0); // Opening the dropdown never imports or assigns a voice.
  await page.getByLabel('Voice for Mira').selectOption('comfy:user:my.wav');
  await expect(page.getByLabel('Voice for Mira')).toHaveValue('voice-imported');
  await expect(page.getByLabel('Voice for Mira').locator('option',{hasText:'My voice.wav'})).toHaveCount(1);
  expect(writes).toHaveLength(2);
  expect(writes[1]).toMatchObject({character_id:'char',voice_asset_id:'voice-imported'});
  await page.getByLabel('Voice for Asha').selectOption('voice-imported');
  await expect(page.getByLabel('Voice for Asha')).toHaveValue('voice-imported');
  expect(writes).toHaveLength(3); // Reuse does not import a duplicate voice.
  await page.getByRole('searchbox', {name:'Search voice previews'}).fill('no matching preview');
  await expect(page.getByLabel('Voice for Mira').locator('option',{hasText:'My voice.wav'})).toHaveCount(1);
  await expect(page.getByLabel('Voice for Asha').locator('option',{hasText:'My voice.wav'})).toHaveCount(1);
  mode='fully_automated';
  await page.reload();
  await expect(page.getByLabel('Voice for Mira')).toBeDisabled();
  await expect(page.getByText('Manual voice assignment is skipped in Fully automated mode.')).toBeVisible();
  await expect(page.getByRole('main').getByRole('link',{name:'Automation & Parameters'})).toHaveAttribute('href','#/setup?workspace_id=voice-project');
  await expect(page.getByLabel('Voice for Mira').locator('option',{hasText:'My voice.wav'})).toHaveCount(1);
});
