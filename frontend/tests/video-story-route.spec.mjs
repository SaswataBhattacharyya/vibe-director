import { test, expect } from '@playwright/test';

const screenplay = {
  workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', source_revision_id: 'source-current', graph_snapshot_id: 'graph-a', created_at: '2026-10-11T00:00:00Z', accepted: true,
  screenplay: { title: 'Current story', coverage_note: '', scenes: [{ scene_number: 1, slugline: 'EXT. ROAD - NIGHT', summary: 'Rain falls.', shots: [{ shot_number: 1, action: 'Mira crosses the road.', dialogue: '', direction: { camera: '', lighting: '', mood: '', sfx: '', music: '' }, evidence: [], character_record_ids: ['character-mira'] }] }] },
};
const run = { run_state: 'not_started', workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', setup_hash: 'setup-hash', prompt_sha256: '', scene_number: 1, shot_number: 1, clip_id: 'clip-a', idempotency_key: 'key-a', request: {}, source_lineage: {}, job: null, clips: [], completed_count: 0 };
const clip = { clip_id: 'clip-a', scene_number: 1, shot_number: 1, clip_number: 1, workflow_id: 'minimax_h3_r2v_dynamic_v1', duration_seconds: 6, duration_reason: 'fixed setup duration', prompt: 'Mira crosses the rainy road.', source_spans: [{ field: 'action', start: 0, end: 28, text: 'Mira crosses the road.' }] };
const setup = mode => ({ workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', updated_at: 'setup-v1', setup: mode === 'full'
  ? { mode: 'fully_automated', automate_steps: { character_images: false, character_voice: false, world_images: false, frame_images: false, video: false }, video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 } }
  : { mode: 'assisted_manual', automate_steps: { character_images: false, character_voice: false, world_images: false, frame_images: false, video: true }, video_workflow_id: 'minimax_h3_r2v_dynamic_v1', video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 } } });

async function mockStoryApi(page, mode, calls) {
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    calls.push(`${method} ${path}`);
    if (path === '/api/story/workspaces/workspace-a') return route.fulfill({ json: { workspace_id: 'workspace-a', title: 'Current story', current_revision_id: 'source-current' } });
    if (path.endsWith('/screenplay') && path.startsWith('/api/story/workspaces/')) return route.fulfill({ json: screenplay });
    if (path.endsWith('/screenplay/revisions')) return route.fulfill({ json: { items: [{ screenplay_revision_id: 'screenplay-current', source_revision_id: 'source-current', accepted: true, stale: false }] } });
    if (path.endsWith('/production-setup')) return route.fulfill({ json: setup(mode) });
    if (path.endsWith('/voice-bindings')) return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', graph_snapshot_id: 'graph-a', characters: [{ record_id: 'character-mira', name: 'Mira', kind: 'entity', type: 'character' }], bindings: [] } });
    if (path.endsWith('/automated-first-clip')) return route.fulfill({ json: run });
    if (path.endsWith('/assisted-video-run')) return route.fulfill({ json: { run_state: 'not_started', workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', clips: [], completed_count: 0, planned_count: 0 } });
    if (path.endsWith('/assisted-video-clip-plan')) return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', input_hash: 'plan-hash', clips: [clip], references: {} } });
    if (path.endsWith('/assisted-video-clip-references')) return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', input_hash: 'plan-hash', clips: [clip], references: {} } });
    if (path.includes('/api/media/')) return route.fulfill({ json: { assets: [], total: 0 } });
    if (path === '/api/video/capabilities') return route.fulfill({ json: { available: true, dispatch: { enabled: true, running: true, available: true }, runtime_guard: { safe_to_submit: true } } });
    return route.fulfill({ status: 404, json: { error: { message: `Unexpected mocked API: ${method} ${path}` } } });
  });
}

test('Assisted automated clip planning and reference mapping live in Video Create', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name: 'Assisted clip plan' });
  await expect(panel).toBeVisible();
  await expect(panel.getByText('Scene 1 · Shot 1 · Clip 1')).toBeVisible();
  await expect(panel.getByLabel('Prompt for planned clip clip-a')).toHaveValue('Mira crosses the rainy road.');
  expect(calls.some(call => call.includes('/assisted-video-clip-plan'))).toBe(true);
  expect(calls.some(call => call.includes('/automated-first-clip'))).toBe(false);
});

test('Assisted R2V recommends bound character voice and image references without selecting them', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  const voice = { asset_id: 'voice-mira', workspace_id: 'workspace-a', kind: 'audio', roles: ['voice_master'], filename: 'Mira-voice.wav', media_type: 'audio/wav', sha256: 'v'.repeat(64), size_bytes: 12, content_url: '/voice' };
  const image = { asset_id: 'image-mira', workspace_id: 'workspace-a', kind: 'image', roles: ['character_master'], filename: 'Mira.png', media_type: 'image/png', sha256: 'i'.repeat(64), size_bytes: 12, content_url: '/image', metadata: { production_image_job: { settings: { lineage: { target_record_id: 'character-mira' } } } } };
  await page.route('**/api/story/workspaces/workspace-a/voice-bindings?*', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', graph_snapshot_id: 'graph-a',
    characters: [{ record_id: 'character-mira', name: 'Mira', kind: 'entity', type: 'character' }],
    bindings: [{ character_id: 'character-mira', voice_asset_id: voice.asset_id }],
  } }));
  await page.route('**/api/media/workspace-a/assets?kind=audio*', route => route.fulfill({ json: { assets: [voice], total: 1 } }));
  await page.route('**/api/media/workspace-a/assets?kind=image*', route => route.fulfill({ json: { assets: [image], total: 1 } }));
  let payload;
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-clip-references', async route => {
    payload = route.request().postDataJSON();
    const refs = payload.clips[0].references;
    return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', input_hash: 'plan-hash', clips: [clip], references: { 'clip-a': refs } } });
  });
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name: 'Assisted clip plan' });
  const recommendation = panel.getByRole('group', { name: 'Recommended references for clip clip-a' });
  await expect(recommendation).toContainText('Mira');
  await expect(recommendation).toContainText('Bound voice: Mira-voice.wav');
  await expect(recommendation).toContainText('Mira.png');
  await expect(panel.getByLabel(/Reference asset for clip/)).not.toHaveValue(voice.asset_id);
  await recommendation.getByRole('button', { name: 'Add voice reference' }).click();
  await recommendation.getByRole('button', { name: 'Add image · Mira.png' }).click();
  await panel.getByRole('button', { name: 'Save per-clip choices' }).click();
  expect(payload.clips[0].references).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: 'audio', asset_id: voice.asset_id, speaker_ids: ['character-mira'] }),
    expect.objectContaining({ kind: 'image', asset_id: image.asset_id, role: 'character' }),
  ]));
});

test('Assisted planned clip prompt supports micro-edit and persists before run', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  const ref = { kind:'image', asset_id:'pa-1111111111111111', sha256:'a'.repeat(64), role:'character', intent:'Keep Mira consistent.' };
  await page.route('**/api/media/workspace-a/assets?kind=image*', route => route.fulfill({ json:{ assets:[{asset_id:ref.asset_id,workspace_id:'workspace-a',kind:'image',roles:[],filename:'Mira.png',media_type:'image/png',sha256:ref.sha256,size_bytes:1,content_url:'/image'}],total:1 } }));
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-clip-plan*', route => route.fulfill({ json:{workspace_id:'workspace-a',screenplay_revision_id:'screenplay-current',input_hash:'plan-hash',clips:[clip],references:{'clip-a':[ref]}} }));
  let savedPlan;
  let promptSaved = false;
  await page.route('**/api/story/workspaces/workspace-a/field-edit-proposals', async route => {
    const payload = route.request().postDataJSON();
    return route.fulfill({ json: { proposal_id:'proposal-a', revision_id:payload.revision_id, field_key:payload.field_key,
      field_sha256:'hash', start_codepoint:payload.start_codepoint, end_codepoint:payload.end_codepoint,
      expected_text:payload.expected_text, replacement:'storm-soaked', explanation:'Keeps the same action.', status:'pending' } });
  });
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-clip-prompt', async route => {
    promptSaved = true;
    const payload = route.request().postDataJSON();
    expect(payload).toMatchObject({ screenplay_revision_id:'screenplay-current', clip_id:'clip-a',
      expected_prompt:'Mira crosses the rainy road.', prompt:'Mira crosses the storm-soaked road.' });
    savedPlan = { workspace_id:'workspace-a', screenplay_revision_id:'screenplay-current', input_hash:'plan-hash',
      clips:[{...clip, prompt:payload.prompt}], references:{'clip-a':[ref]} };
    return route.fulfill({ json:savedPlan });
  });
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name:'Assisted clip plan' });
  const prompt = panel.getByLabel('Prompt for planned clip clip-a');
  await prompt.evaluate(element => {
    element.focus();
    element.setSelectionRange(17, 22);
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles:true }));
  });
  await panel.getByLabel('Instruction for Prompt for planned clip clip-a').fill('Make the weather stronger.');
  await panel.getByRole('button', { name:'Suggest edit' }).click();
  await panel.getByRole('button', { name:'Apply to draft' }).click();
  await expect(prompt).toHaveValue('Mira crosses the storm-soaked road.');
  await expect(panel.getByRole('button', { name:'Start video run' })).toBeDisabled();
  await panel.getByRole('button', { name:'Save clip prompt' }).click();
  await expect(prompt).toHaveValue(savedPlan.clips[0].prompt);
  expect(promptSaved).toBe(true);
  await expect(panel.getByRole('button', { name:'Start video run' })).toBeEnabled();
});

test('Assisted prompt limit counts Unicode code points like the backend', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  let savedPrompt = '';
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-clip-prompt', async route => {
    savedPrompt = route.request().postDataJSON().prompt;
    return route.fulfill({ json:{ workspace_id:'workspace-a', screenplay_revision_id:'screenplay-current',
      input_hash:'plan-hash', clips:[{ ...clip, prompt:savedPrompt }], references:{} } });
  });
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name:'Assisted clip plan' });
  const prompt = '😀'.repeat(6999);
  await panel.getByLabel('Prompt for planned clip clip-a').fill(prompt);
  await expect(panel.getByText('6,999/6,999 characters')).toBeVisible();
  const save = panel.getByRole('button', { name:'Save clip prompt' });
  await expect(save).toBeEnabled();
  await save.click();
  expect(Array.from(savedPrompt)).toHaveLength(6999);
});

test('paused Assisted run retries its latest failed clip from Video Create', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  const failedRun = { run_state: 'paused', workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current',
    planned_count: 1, completed_count: 0, error: 'The clip failed.', clips: [{ ...clip, state: 'failed',
      predecessor_job_id: null, job: { job_id: 'failed-job', status: 'failed', request: { workflow_id: clip.workflow_id } } }] };
  const resumedRun = { ...failedRun, run_state: 'running', error: null, clips: [{ ...failedRun.clips[0],
    state: 'queued', job: { ...failedRun.clips[0].job, job_id: 'retry-job', status: 'queued' } }] };
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-run?*', route => route.fulfill({ json: failedRun }));
  let submitted;
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-run-retry', async route => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ json: { status: 'queued', job: resumedRun.clips[0].job, run: resumedRun } });
  });
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name: 'Assisted video run status' });
  await expect(panel.getByRole('heading', { name: 'Run paused' })).toBeVisible();
  await panel.getByRole('button', { name: 'Retry latest clip' }).click();
  await expect(panel.getByRole('heading', { name: 'Run running' })).toBeVisible();
  expect(submitted).toEqual({ screenplay_revision_id: 'screenplay-current', clip_id: 'clip-a' });
});

test('Assisted R2V continuity is an explicit saved choice for later clips in the same scene', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  const later = { ...clip, clip_id: 'clip-b', clip_number: 2 };
  const refs = { 'clip-a': [{ kind: 'image', asset_id: 'pa-1111111111111111', sha256: 'a'.repeat(64), role: 'character', intent: 'Keep Mira consistent.' }], 'clip-b': [{ kind: 'image', asset_id: 'pa-2222222222222222', sha256: 'b'.repeat(64), role: 'character', intent: 'Keep Mira consistent.' }] };
  let savedPayload;
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-clip-plan*', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', input_hash: 'plan-hash', clips: [clip, later], references: refs,
  } }));
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-clip-references', async route => {
    savedPayload = route.request().postDataJSON().clips;
    return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-current', input_hash: 'plan-hash',
      clips: [clip, { ...later, continue_previous_clip: true }], references: refs } });
  });
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name: 'Assisted clip plan' });
  const continuity = panel.getByRole('checkbox', { name: 'Continue from previous clip for clip-b' });
  await expect(continuity).toBeVisible();
  await expect(panel.getByRole('checkbox', { name: 'Continue from previous clip for clip-a' })).toHaveCount(0);
  await continuity.check();
  await panel.getByRole('button', { name: 'Save per-clip choices' }).click();
  await expect(continuity).toBeChecked();
  expect(savedPayload.find(item => item.clip_id === 'clip-b').continue_previous_clip).toBe(true);
});


test('fresh Assisted plan prepares and saves missing prompts before planning, only after click', async ({ page }) => {
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  let saved = false;
  let planned = false;
  const flow = [];
  await page.route('**/api/story/workspaces/workspace-a/**', async route => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    if (path.endsWith('/prompt-drafts') && method === 'GET') return route.fulfill({ json: { drafts: {}, setup_matches_current: true } });
    if (path.endsWith('/prompt-drafts/prepare')) {
      flow.push('prepare');
      return route.fulfill({ json: { shot_key: '1.1', workflow_id: clip.workflow_id, prompt: clip.prompt } });
    }
    if (path.endsWith('/prompt-drafts/shot')) {
      flow.push('save'); saved = true;
      expect(route.request().postDataJSON().draft.prompt).toBe(clip.prompt);
      return route.fulfill({ json: { drafts: { '1.1': { workflow_id: clip.workflow_id, prompt: clip.prompt } }, setup_matches_current: true } });
    }
    if (path.endsWith('/assisted-video-clip-plan')) {
      if (method === 'POST') {
        expect(saved).toBe(true); flow.push('plan'); planned = true;
      }
      return route.fulfill({ json: { clips: planned ? [clip] : [], references: {} } });
    }
    return route.fallback();
  });
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name: 'Assisted clip plan' });
  await expect(panel.getByRole('button', { name: 'Plan clips', exact: true })).toBeEnabled();
  expect(flow).toEqual([]);
  await panel.getByRole('button', { name: 'Plan clips', exact: true }).click();
  await expect(panel.getByLabel('Prompt for planned clip clip-a')).toHaveValue(clip.prompt);
  expect(flow).toEqual(['prepare', 'save', 'plan']);
  expect(calls.some(call => call.startsWith('POST ') && call.includes('/api/video/'))).toBe(false);
});

test('same-page workspace switch clears the previous Assisted plan', async ({ page }) => {
  const calls = [];
  await mockStoryApi(page, 'assisted', calls);
  await page.route('**/api/story/workspaces/workspace-b**', async route => route.fulfill({ json: { workspace_id: 'workspace-b', title: 'New story', current_revision_id: null } }));
  await page.goto('/#/video?workspace_id=workspace-a');
  await expect(page.getByRole('region', { name: 'Assisted clip plan' })).toBeVisible();
  await page.evaluate(() => { window.location.hash = '#/video?workspace_id=workspace-b'; });
  await expect(page.getByRole('region', { name: 'Assisted clip plan' })).toHaveCount(0);
});

test('replanning warns before discarding unsaved reference choices', async ({ page }) => {
  await mockStoryApi(page, 'assisted', []);
  await page.route('**/api/media/workspace-a/assets?kind=image*', route => route.fulfill({ json: { assets: [{ asset_id: 'pa-1111111111111111', kind: 'image', filename: 'Mira.png', sha256: 'a'.repeat(64), roles: ['character_master'] }], total: 1 } }));
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name: 'Assisted clip plan' });
  await panel.getByLabel('Reference asset for clip clip-a').selectOption('pa-1111111111111111');
  await panel.getByRole('button', { name: 'Add reference' }).click();
  let warned = false;
  page.once('dialog', async dialog => { warned = true; await dialog.dismiss(); });
  await panel.getByRole('button', { name: 'Replan clips' }).click();
  expect(warned).toBe(true);
  await expect(panel.getByLabel('Reference intent for pa-1111111111111111')).toBeVisible();
});


test('removing a first frame preserves the same image mapped as the last frame', async ({ page }) => {
  await mockStoryApi(page, 'assisted', []);
  const frameId = 'pa-1111111111111111';
  const fflf = 'minimax_h3_fl2va_first_last_v1';
  await page.route('**/api/story/workspaces/workspace-a/production-setup*', route => route.fulfill({ json: { ...setup('assisted'), setup: { ...setup('assisted').setup, video_workflow_id: fflf } } }));
  await page.route('**/api/story/workspaces/workspace-a/assisted-video-clip-plan*', route => route.fulfill({ json: { clips: [{ ...clip, workflow_id: fflf }], references: { 'clip-a': ['first_frame', 'last_frame'].map(role => ({ kind: 'image', asset_id: frameId, sha256: 'a'.repeat(64), role, intent: role })) } } }));
  await page.route('**/api/media/workspace-a/assets?kind=image*', route => route.fulfill({ json: { assets: [{ asset_id: frameId, kind: 'image', filename: 'Static.png', roles: ['first_frame', 'last_frame'] }], total: 1 } }));
  await page.goto('/#/video?workspace_id=workspace-a');
  const panel = page.getByRole('region', { name: 'Assisted clip plan' });
  const first = panel.locator('p').filter({ hasText: 'First frame · Static.png' });
  await first.getByRole('button', { name: 'Remove' }).click();
  await expect(first).toHaveCount(0);
  await expect(panel.locator('p').filter({ hasText: 'Last frame · Static.png' })).toBeVisible();
});
