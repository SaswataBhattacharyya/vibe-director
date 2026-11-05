import {mockProject} from './fixtures/project.mjs';
import { test, expect } from '@playwright/test';

test('Current Take shows generated clips in a selectable preview carousel', async ({ page }) => {
  const makeTake = (jobId, attempt, duration, prompt, outputId) => ({
    job: { job_id: jobId, workspace_id:'workspace-a', attempt, status: 'accepted', outputs: [{ asset_id: outputId, kind: 'video', playback_url: `/media/${outputId}.mp4` }] },
    snapshot: { workflow_id: 'minimax_h3_t2v_local_v1', workflow_version: 1, workflow_sha256: 'hash', prompt, duration_seconds: duration, aspect_ratio: '16:9', resolution_preset: 0.98 },
  });
  await page.addInitScript(({ takes }) => {
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({ workspaceId:'workspace-a', prompt:'', duration:6, resolution:0.98, clipId:'clip-a', workflowId:'minimax_h3_t2v_local_v1' }));
    localStorage.setItem('vibe-video-history-v1', JSON.stringify(takes));
  }, {
    takes: [makeTake('take-1', 1, 6, 'First clip prompt.', 'clip-1'), makeTake('take-2', 2, 8, 'Second clip prompt.', 'clip-2')],
  });
  await page.route('**/api/**', route => route.fulfill({ status: 404, json: { detail: 'Not used in this history-only test' } }));
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/take');

  const carousel = page.getByRole('list', { name: 'Generated video clips carousel' });
  await expect(carousel.getByRole('button', { name: /Take 1 · 6s · First clip prompt\./ })).toBeVisible();
  await expect(carousel.getByRole('button', { name: /Take 2 · 8s · Second clip prompt\./ })).toBeVisible();
  await carousel.getByRole('button', { name: /Take 2 · 8s · Second clip prompt\./ }).click();
  await expect(page.locator('.take-selected-preview video')).toHaveAttribute('src', /\/media\/clip-2\.mp4$/);
  await page.getByText('Selected take prompt · Take 2',{exact:true}).click();
  await expect(page.locator('details').filter({hasText:'Selected take prompt · Take 2'})).toContainText('Second clip prompt.');
});

test('Current Take restores accepted clips and keeps discarded candidates out of history', async ({ page }) => {
  const request = { workflow_id:'minimax_h3_t2v_local_v1', workflow_version:1, workflow_sha256:'hash', prompt:'Ledger clip prompt.', duration_seconds:6, aspect_ratio:'16:9', resolution_preset:0.98 };
  const job = { job_id:'ledger-take-1', workspace_id:'workspace-a', clip_id:'clip-1', attempt:1, status:'accepted', request,
    outputs:[{ asset_id:'asset-1', kind:'video', playback_url:'/api/video/assets/asset-1/playback' }] };
  const discarded = { ...job, job_id:'discarded-take', attempt:2, request:{ ...request, prompt:'Discarded take prompt.' },
    candidate_disposition:'discard_requested', outputs:[{ asset_id:'asset-discarded', kind:'video', playback_url:'/api/video/assets/asset-discarded/playback' }] };
  await page.addInitScript(({ request, discarded }) => {
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({ prompt:'', duration:6, resolution:0.98,
      workspaceId:'workspace-a', clipId:'clip-1', workflowId:'minimax_h3_t2v_local_v1' }));
    localStorage.setItem('vibe-video-history-v1', JSON.stringify([{ job:discarded, snapshot:request }]));
  }, { request, discarded });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/video/jobs' && route.request().method() === 'GET') return route.fulfill({ json:{ jobs:[discarded, job] } });
    if (url.pathname === '/api/video/jobs/ledger-take-1') return route.fulfill({ json:job });
    return route.fulfill({ status:404, json:{ detail:'Unexpected request in ledger history test' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/take');
  await expect(page.getByRole('button', { name:/Take 1 · 6s · Ledger clip prompt\./ })).toBeVisible();
  await expect(page.getByRole('list', { name:'Generated video clips carousel' }).getByRole('button', { name:/Discarded take prompt/ })).toHaveCount(0);
  await expect(page.locator('.take-selected-preview video')).toHaveAttribute('src', /asset-1\/playback$/);
});

test('Current Take orders assembly choices by screenplay and requires one accepted take per clip', async ({ page }) => {
  let saved = {};
  let savedAudio = [];
  const snapshots = [];
  const exportManifests = [];
  const exportJobs = [];
  const audioAsset = { asset_id:'audio-1', workspace_id:'workspace-a', kind:'audio', roles:['project_audio'], filename:'score.wav',
    media_type:'audio/wav', sha256:'a'.repeat(64), size_bytes:1200, content_url:'/media/score.wav', created_at:'now',
    audio_category:'music', media:{duration_seconds:18} };
  await page.addInitScript(() => {
    localStorage.setItem('vibe-story-selected-v1', 'workspace-a');
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({ workspaceId: 'workspace-a',
      sourceLineage: { screenplay_revision_id: 'screenplay-a', scene_number: 1, shot_number: 1 } }));
  });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/media/workspace-a/assets/pa-0123456789abcdef/content') return route.fulfill({body:'mock mp4',contentType:'video/mp4'});
    if (url.pathname === '/api/video/jobs') return route.fulfill({ json: { jobs: [] } });
    if (url.pathname === '/api/story/workspaces/workspace-a/screenplay/revisions') return route.fulfill({ json: { items: [
      { screenplay_revision_id: 'screenplay-a', accepted: true, stale: false },
    ], total: 1, offset: 0, limit: 50 } });
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-preview') return route.fulfill({ json: {
      screenplay_revision_id: 'screenplay-a', planned_source: 'screenplay', missing_clip_count: 0,
      planning_incomplete: false, warnings: [], clips: [
        { scene_number: 1, shot_number: 1, clip_number: 1, accepted_takes: [{ job_id: 'take-first', outputs: [{ playback_url: '/video/first' }] }], review_takes: [], missing_accepted_take: false },
        { scene_number: 1, shot_number: 2, clip_number: 1, accepted_takes: [{ job_id: 'take-second', outputs: [{ playback_url: '/video/second' }] }], review_takes: [], missing_accepted_take: false },
      ],
    } });
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-selection' && route.request().method() === 'GET') return route.fulfill({ json: { selections: saved } });
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-selection' && route.request().method() === 'PUT') {
      saved = route.request().postDataJSON().selections;
      return route.fulfill({ json: { selections: saved } });
    }
    if (url.pathname === '/api/media/workspace-a/assets') return route.fulfill({ json:{assets:[audioAsset],total:1} });
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-audio' && route.request().method() === 'GET') return route.fulfill({ json:{audio_tracks:savedAudio} });
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-audio' && route.request().method() === 'PUT') {
      savedAudio = route.request().postDataJSON().audio_tracks;
      return route.fulfill({ json:{audio_tracks:savedAudio} });
    }
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-snapshots' && route.request().method() === 'GET') return route.fulfill({ json:{snapshots} });
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-snapshots' && route.request().method() === 'POST') {
      const snapshot = { snapshot_id:'assembly-1', snapshot_sha256:'c'.repeat(64), created_at:'2026-10-11T00:00:00Z', snapshot:{state:'awaiting_export_settings'} };
      snapshots.unshift(snapshot);
      return route.fulfill({ status:201, json:snapshot });
    }
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-exports' && route.request().method() === 'GET') return route.fulfill({ json:{manifests:exportManifests} });
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-exports' && route.request().method() === 'POST') {
      const payload = route.request().postDataJSON();
      expect(payload.snapshot_id).toBe('assembly-1');
      expect(payload.settings).toEqual({resolution:'1080p',frame_rate:24,quality:22,audio_policy:'preserve_and_mix'});
      const manifest = {manifest_id:'export-1',manifest_sha256:'d'.repeat(64),created_at:'2026-10-11T00:00:00Z',manifest:{state:'ready_for_render',export_settings:{}}};
      exportManifests.unshift(manifest);
      return route.fulfill({status:201,json:manifest});
    }
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-export-jobs' && route.request().method() === 'GET') return route.fulfill({json:{jobs:exportJobs}});
    if (url.pathname === '/api/story/workspaces/workspace-a/assembly-export-jobs' && route.request().method() === 'POST') {
      const job = {job_id:'export-job-1',manifest_id:'export-1',state:'queued',created_at:'2026-10-11T00:00:00Z'};
      exportJobs.unshift(job);
      return route.fulfill({status:202,json:job});
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Not used in assembly selection test' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/take');
  const panel = page.getByRole('region', { name: 'Assemble story clips' });
  await expect(panel.getByText('Scene 1 · Shot 1 · Clip 1')).toBeVisible();
  await expect(panel.getByText('Scene 1 · Shot 2 · Clip 1')).toBeVisible();
  await panel.locator('input[value="take-first"]').check();
  await panel.locator('input[value="take-second"]').check();
  await expect(panel.getByText('2 of 2 clips selected')).toBeVisible();
  await panel.getByRole('button', { name: 'Save choices' }).click();
  await expect(panel.getByText(/2 of 2 clips selected · Saved/)).toBeVisible();
  await panel.getByRole('button', { name: 'Refresh' }).click();
  await expect(panel.locator('input[value="take-first"]')).toBeChecked();
  await expect(panel.locator('input[value="take-second"]')).toBeChecked();
  await panel.getByRole('button', { name: 'Add an optional audio track' }).click();
  await panel.getByRole('button', { name:'Add', exact: true }).click();
  await expect(panel.locator('.assembly-audio-track')).toContainText('score.wav');
  await panel.getByLabel('Starts at (s)').fill('2.5');
  await panel.getByLabel('Trim in (s)').fill('1');
  await panel.getByLabel('Trim out (s)').fill('12');
  await panel.getByLabel('Level').fill('0.7');
  await panel.getByRole('button', { name:'Save audio choices' }).click();
  await expect(panel.getByRole('button', { name:'Audio saved' })).toBeDisabled();
  expect(savedAudio).toEqual([{asset_id:'audio-1',sha256:'a'.repeat(64),start_seconds:2.5,trim_start_seconds:1,trim_end_seconds:12,gain:0.7}]);
  await panel.getByRole('button', { name:'Freeze assembly choices' }).click();
  await expect(panel.getByText('assembly-1', { exact:true })).toBeVisible();
  await panel.getByRole('button', { name:/Prepare export from/ }).click();
  await expect(panel.getByText('export-1', { exact:true })).toBeVisible();
  await panel.getByRole('button', { name:'Render export' }).click();
  await expect(panel.getByText(/ready for render · queued/)).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Render export' })).toHaveCount(0);
  exportJobs[0] = { ...exportJobs[0], state:'completed', output_asset_id:'pa-0123456789abcdef' };
  await panel.getByRole('button', { name:'Refresh' }).click();
  const download = panel.getByRole('link', { name:'Download MP4' });
  await expect(download).toHaveAttribute('href', '/api/media/workspace-a/assets/pa-0123456789abcdef/content');
  await expect(download).toHaveAttribute('download', 'vibe-director-export.mp4');
  const downloadEvent = page.waitForEvent('download');
  await download.click();
  expect((await downloadEvent).suggestedFilename()).toBe('vibe-director-export.mp4');
});

const capability = (ready) => ({
  available: ready,
  disabled_reason: ready ? null : 'Legacy T2V workflow is not verified.',
  runtime_guard: { monitor_available: true, safe_to_submit: ready, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100, operating_point: { temperature_c: 48, graphics_clock_mhz: 1900 }, reason: ready ? 'Runtime is inside the safety limits.' : 'GPU clock is over the safety limit.' },
  dispatch: { enabled: ready, running: ready, available: ready, worker_state: ready ? 'running' : 'disabled', reason: ready ? null : 'Worker is disabled.' },
});

test('Video prompt supports selected-text edits and applies only the accepted suggestion', async ({ page }) => {
  let editRequest;
  await page.route('**/api/**', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.pathname.endsWith('/field-edit-proposals') && request.method() === 'POST') {
      editRequest = request.postDataJSON();
      return route.fulfill({ json: { proposal_id:'proposal-1', revision_id:editRequest.revision_id, field_key:editRequest.field_key,
        expected_text:editRequest.expected_text, start_codepoint:editRequest.start_codepoint, end_codepoint:editRequest.end_codepoint,
        replacement:'an amber-lit room', status:'pending' } });
    }
    return route.fulfill({ status:404, json:{detail:'Not used in selected-edit test'} });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  const prompt = page.getByLabel('Shot prompt');
  await prompt.fill('A room with soft light.');
  await prompt.evaluate(element => {
    const start = element.value.indexOf('soft light');
    element.focus();
    element.setSelectionRange(start, start + 'soft light'.length);
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles:true }));
  });
  await page.getByLabel('Instruction for Shot prompt').fill('Make the lighting warm.');
  await page.getByRole('button', { name:'Suggest edit' }).click();
  await expect(page.getByText('an amber-lit room')).toBeVisible();
  expect(editRequest.expected_text).toBe('soft light');
  await page.getByRole('button', { name:'Apply to draft' }).click();
  await expect(prompt).toHaveValue('A room with an amber-lit room.');
});

test('story-linked Video Create prepares and saves only its current shot prompt', async ({ page }) => {
  const calls = [];
  const knowledgeRef = { knowledge_id:'minimax-h3-t2v', guidance_version:2, workflow_id:'minimax_h3_t2v_local_v1', workflow_sha256:'graph-hash' };
  const styleRef = { snapshot_id:'style-snapshot-1', style_version_id:'base:drama:v1', narrative_hash:'a'.repeat(64), director_profile_hash:'b'.repeat(64), directing_style_hash:'c'.repeat(64) };
  await page.addInitScript(({knowledgeRef, styleRef}) => {
    localStorage.setItem('vibe-story-video-handoff-v1', JSON.stringify({
      workspace_id:'workspace-a', clip_id:'story-clip-1', screenplay_revision_id:'screenplay-1', setup_hash:'setup-hash',
      scene_number:1, shot_number:1, source_prompt_sha256:'', knowledge_ref:knowledgeRef, style_ref:styleRef,
      workflow_id:'minimax_h3_t2v_local_v1', prompt:'',
    }));
  }, {knowledgeRef, styleRef});
  await page.route('**/api/**', async route => {
    const request = route.request(), url = new URL(request.url());
    calls.push(`${request.method()} ${url.pathname}`);
    if (url.pathname==='/api/story/workspaces/workspace-a/production-setup') return route.fulfill({json:{
      workspace_id:'workspace-a', screenplay_revision_id:'screenplay-1', setup:{mode:'assisted_manual', automate_steps:{character_images:false,character_voice:false,world_images:false,frame_images:false,video:false}, video_quality:'high',duration_policy:{kind:'fixed',seconds:6}}, updated_at:'now',
    }});
    if (url.pathname==='/api/story/workspaces/workspace-a/prompt-drafts/prepare') {
      expect(request.postDataJSON()).toMatchObject({screenplay_revision_id:'screenplay-1',shot_key:'1.1',workflow_id:'minimax_h3_t2v_local_v1'});
      return route.fulfill({json:{shot_key:'1.1',workflow_id:'minimax_h3_t2v_local_v1',prompt:'A tense close-up, rain against the courtroom window.',knowledge_ref:knowledgeRef,style_ref:styleRef,sources:[]}});
    }
    if (url.pathname==='/api/story/workspaces/workspace-a/prompt-drafts/shot' && request.method()==='PUT') {
      const body=request.postDataJSON();
      expect(body).toMatchObject({screenplay_revision_id:'screenplay-1',shot_key:'1.1',draft:{prompt:'A tense close-up, rain against the courtroom window.',workflow_id:'minimax_h3_t2v_local_v1'}});
      expect(body.draft.style_ref).toEqual(styleRef);
      return route.fulfill({json:{setup_hash:'setup-hash',setup_matches_current:true,drafts:{'1.1':body.draft}}});
    }
    return route.fulfill({status:404,json:{detail:'Not used in stage-local prompt preparation test'}});
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.getByRole('heading',{name:'Create video'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Prepare from screenplay'})).toBeVisible();
  await page.getByRole('button',{name:'Prepare from screenplay'}).click();
  await expect(page.getByLabel('Shot prompt')).toHaveValue('A tense close-up, rain against the courtroom window.');
  await expect(page.getByText(/Prepared and saved a prompt for Scene 1, Shot 1/)).toBeVisible();
  expect(calls).toContain('POST /api/story/workspaces/workspace-a/prompt-drafts/prepare');
  expect(calls).toContain('PUT /api/story/workspaces/workspace-a/prompt-drafts/shot');
  expect(calls.some(call=>call.includes('/api/video/jobs'))).toBeFalsy();
});

test('mocked T2V flow gates readiness, reviews output, accepts, and prepares a non-submitting retake', async ({ page }) => {
  let workflowReady = false;
  let jobPosts = 0;
  let job = null;
  const calls = [];
  await page.route('**/api/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    calls.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/api/video/capabilities') {
      const result = capability(workflowReady);
      if (!workflowReady) result.disabled_reason += `; ${result.dispatch.reason}`;
      return route.fulfill({ json: result });
    }
    if (url.pathname === '/api/video/validations') return route.fulfill({ json: { valid: true, request_hash: 'hash', normalized_request: request.postDataJSON().request, compiled_preview: {} } });
    if (url.pathname === '/api/video/jobs' && request.method() === 'POST') {
      jobPosts++;
      const body = request.postDataJSON();
      job = { job_id: 'job-1', workspace_id: body.workspace_id, clip_id: body.clip_id, status: 'needs_review', request: body.request, outputs: [{ asset_id: 'asset-1', kind: 'video', playback_url: '/api/video/assets/asset-1/playback' }], created_at: 'now', updated_at: 'now', attempt: 1 };
      return route.fulfill({ json: job });
    }
    if (url.pathname === '/api/video/jobs/job-1/accept') { job = { ...job, status: 'accepted' }; return route.fulfill({ json: job }); }
    if (url.pathname === '/api/video/retakes/job-1') { const keepOriginal = request.postDataJSON().keep_original; return route.fulfill({ json: { source_job_id: 'job-1', request: job.request, keep_original: keepOriginal, candidate_disposition: keepOriginal ? 'keep' : 'discard_requested', asset_cleanup: keepOriginal ? 'kept' : 'archived_recoverable', submission_created: false } }); }
    if (url.pathname === '/api/video/assets/asset-1/playback') return route.fulfill({ status: 200, contentType: 'video/mp4', body: '' });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });

  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await expect(page.locator('.video-readiness')).toContainText('The selected video workflow is not ready. Check Status for setup details.');
  await expect(page.locator('.video-readiness').getByRole('link', { name: 'Open Status' })).toHaveAttribute('href', '#/status');
  await expect(page.locator('.video-readiness').getByText('Legacy T2V workflow is not verified.', {exact: true})).toBeHidden();
  await page.locator('.video-readiness').getByText('Technical details').click();
  await expect(page.locator('.video-readiness details small')).toContainText('Legacy T2V workflow is not verified.');
  await expect(page.locator('.video-readiness details small')).toHaveText('Legacy T2V workflow is not verified.; Worker is disabled. GPU clock is over the safety limit.');
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
  workflowReady = true;
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByLabel('Shot prompt').fill('A slow dolly toward a rain-streaked window.');
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeEnabled();
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByText('Ready to review', {exact:true})).toBeVisible();
  await expect(page.locator('.take-selected-preview video')).toHaveAttribute('src', /api\/video\/assets/);
  expect(jobPosts).toBe(1);
  await page.getByRole('button', { name: 'Accept take' }).click();
  await expect(page.getByText('Take accepted', {exact:true})).toBeVisible();
  await page.getByRole('button', { name: 'Retake' }).click();
  await expect(page.getByRole('heading', { name: 'Prepare a retake' })).toBeVisible();
  await expect(page.getByText(/records your choice and does not start a job/)).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('recoverable under Show archived');
  await page.getByLabel('Discard from take history').check();
  await page.getByRole('button', { name: /Return to editor/ }).click();
  await expect(page.getByLabel('Shot prompt')).toHaveValue('A slow dolly toward a rain-streaked window.');
  await expect(page.getByText(/archived from normal library search; Show archived can restore it/)).toBeVisible();
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-history-v1') || '[]'))).toHaveLength(0);
  expect(jobPosts).toBe(1);
  expect(calls.some(call => call === 'POST /api/video/retakes/job-1')).toBeTruthy();
});

for (const final of [false, true]) test(`Next accepts the ${final ? 'final' : 'current'} story take`, async ({ page }) => {
  const request = { workflow_id:'minimax_h3_t2v_local_v1', workflow_version:1, workflow_sha256:'hash', prompt:'Scene one prompt', duration_seconds:6, aspect_ratio:'16:9', resolution_preset:0.98 };
  const sourceLineage = { screenplay_revision_id:'screenplay-1', setup_hash:'setup-1', scene_number:1, shot_number:1, source_prompt_sha256:'source-1' };
  await page.addInitScript(({request, sourceLineage}) => {
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({prompt:request.prompt, duration:6, resolution:0.98, workspaceId:'workspace-a', clipId:'story-current', workflowId:request.workflow_id, sourceLineage,
      r2vImages:[{assetId:'old-image',role:'character',intent:'old intent'}], r2vVideos:[], r2vAudios:[], firstFrameAssetId:'old-first', lastFrameAssetId:'old-last'}));
    localStorage.setItem('vibe-video-active-job-v1', JSON.stringify({jobId:'job-current', snapshot:request}));
  }, {request, sourceLineage});
  const calls = [];
  const job = {job_id:'job-current',workspace_id:'workspace-a',clip_id:'story-current',status:'needs_review',request,source_lineage:{...sourceLineage,workflow_id:request.workflow_id},outputs:[{asset_id:'output-1',kind:'video',playback_url:'/api/video/assets/output-1/playback'}]};
  await page.route('**/api/**', async route => {
    const req=route.request(), url=new URL(req.url()); calls.push(`${req.method()} ${url.pathname}`);
    if(url.pathname==='/api/video/jobs/job-current') return route.fulfill({json:job});
    if(url.pathname==='/api/video/jobs/job-current/accept') return route.fulfill({json:{...job,status:'accepted'}});
    if(url.pathname==='/api/story/workspaces/workspace-a/screenplay/revisions/screenplay-1') return route.fulfill({json:{accepted:true,screenplay_revision_id:'screenplay-1',workspace_id:'workspace-a',screenplay:{scenes:[{scene_number:1,slugline:'INT. ROOM',summary:'',shots:final ? [{shot_number:1}] : [{shot_number:1},{shot_number:2},{shot_number:3}]}]}}});
    if(url.pathname==='/api/story/workspaces/workspace-a/prompt-drafts') return route.fulfill({json:{setup_hash:'setup-1',setup_matches_current:true,drafts:{'1.1':{workflow_id:request.workflow_id,prompt:'Scene one prompt'},'1.2':{workflow_id:request.workflow_id,prompt:'Scene two prompt'}}}});
    if(url.pathname==='/api/story/workspaces/workspace-a/production-setup') return route.fulfill({json:{workspace_id:'workspace-a',screenplay_revision_id:'screenplay-1',setup:{mode:'assisted_manual',automate_steps:{character_images:false,character_voice:false,world_images:false,frame_images:false,video:false},video_quality:'high',duration_policy:{kind:'fixed',seconds:6}},updated_at:'now'}});
    if(url.pathname==='/api/video/assets/output-1/playback') return route.fulfill({status:200,contentType:'video/mp4',body:''});
    return route.fulfill({status:404,json:{detail:'Unexpected API request'}});
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/take');
  await expect(page.getByRole('heading',{name:'Current take', exact:true}).first()).toBeVisible();
  await expect(page.getByRole('button',{name:'Next clip',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Next clip',exact:true}).click();
  if (final) {
    await expect(page.getByText('Final take accepted. All screenplay shots have been reached.')).toBeVisible();
    expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-active-job-v1')).jobId)).toBe('job-current');
    expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-history-v1'))[0].job.status)).toBe('accepted');
    expect(calls).toContain('POST /api/video/jobs/job-current/accept');
    expect(calls.some(call=>call.includes('/prepare'))).toBe(false);
    return;
  }
  await expect(page.getByRole('heading',{name:'Create video'})).toBeVisible();
  await expect(page.getByLabel('Shot prompt')).toHaveValue('Scene two prompt');
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-draft-v1')).r2vImages)).toEqual([]);
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-draft-v1')).firstFrameAssetId)).toBeUndefined();
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-history-v1'))[0].job.status)).toBe('accepted');
  expect(calls).toContain('POST /api/video/jobs/job-current/accept');
});

test('Next prepares and saves only the next screenplay prompt when it has not been drafted yet', async ({ page }) => {
  const request = { workflow_id:'minimax_h3_t2v_local_v1', workflow_version:1, workflow_sha256:'hash', prompt:'Scene one prompt', duration_seconds:6, aspect_ratio:'16:9', resolution_preset:0.98 };
  const sourceLineage = { screenplay_revision_id:'screenplay-1', setup_hash:'setup-hash', scene_number:1, shot_number:1, source_prompt_sha256:'source-1' };
  const setup = { mode:'assisted_manual', automate_steps:{character_images:false,character_voice:false,world_images:false,frame_images:false,video:false}, video_quality:'high', duration_policy:{kind:'fixed',seconds:6} };
  await page.addInitScript(({request, sourceLineage}) => {
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({prompt:request.prompt,duration:6,resolution:0.98,workspaceId:'workspace-a',clipId:'story-current',workflowId:request.workflow_id,sourceLineage}));
    localStorage.setItem('vibe-video-active-job-v1', JSON.stringify({jobId:'job-current',snapshot:request}));
  }, {request, sourceLineage});
  const job = {job_id:'job-current',workspace_id:'workspace-a',clip_id:'story-current',status:'needs_review',request,source_lineage:{...sourceLineage,workflow_id:request.workflow_id},outputs:[{asset_id:'output-1',kind:'video',playback_url:'/api/video/assets/output-1/playback'}]};
  const calls = [];
  await page.route('**/api/**', async route => {
    const req=route.request(), url=new URL(req.url()); calls.push(`${req.method()} ${url.pathname}`);
    if(url.pathname==='/api/video/jobs/job-current') return route.fulfill({json:job});
    if(url.pathname==='/api/video/jobs/job-current/accept') return route.fulfill({json:{...job,status:'accepted'}});
    if(url.pathname==='/api/story/workspaces/workspace-a/screenplay/revisions/screenplay-1') return route.fulfill({json:{accepted:true,screenplay_revision_id:'screenplay-1',workspace_id:'workspace-a',screenplay:{scenes:[{scene_number:1,slugline:'INT. ROOM',summary:'A quiet exchange.',shots:[{shot_number:1},{shot_number:2}]}]}}});
    if(url.pathname==='/api/story/workspaces/workspace-a/prompt-drafts') return route.fulfill({json:{setup_hash:'setup-hash',setup_matches_current:true,drafts:{'1.1':{workflow_id:request.workflow_id,prompt:'Scene one prompt'}}}});
    if(url.pathname==='/api/story/workspaces/workspace-a/production-setup') return route.fulfill({json:{workspace_id:'workspace-a',screenplay_revision_id:'screenplay-1',setup,updated_at:'now'}});
    if(url.pathname==='/api/story/workspaces/workspace-a/prompt-drafts/prepare') return route.fulfill({json:{shot_key:'1.2',workflow_id:request.workflow_id,prompt:'Prepared second shot prompt.',knowledge_ref:{knowledge_id:'knowledge',guidance_version:1,workflow_sha256:'a'.repeat(64)},sources:[]}});
    if(url.pathname==='/api/story/workspaces/workspace-a/prompt-drafts/shot' && req.method()==='PUT') {
      expect(req.postDataJSON().shot_key).toBe('1.2');
      return route.fulfill({json:{setup_hash:'setup-hash',setup_matches_current:true,drafts:{'1.1':{workflow_id:request.workflow_id,prompt:'Scene one prompt'},'1.2':{workflow_id:request.workflow_id,prompt:'Prepared second shot prompt.'}}}});
    }
    if(url.pathname==='/api/video/assets/output-1/playback') return route.fulfill({status:200,contentType:'video/mp4',body:''});
    return route.fulfill({status:404,json:{detail:'Unexpected API request'}});
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/take');
  await page.getByRole('button',{name:'Next clip',exact:true}).click();
  await expect(page.getByLabel('Shot prompt')).toHaveValue('Prepared second shot prompt.');
  expect(calls).toContain('POST /api/story/workspaces/workspace-a/prompt-drafts/prepare');
  expect(calls).toContain('PUT /api/story/workspaces/workspace-a/prompt-drafts/shot');
});

test('Next refuses to accept a story take missing from the current accepted screenplay', async ({ page }) => {
  const request = { workflow_id:'minimax_h3_t2v_local_v1', workflow_version:1, workflow_sha256:'hash', prompt:'Scene one prompt', duration_seconds:6, aspect_ratio:'16:9', resolution_preset:0.98 };
  const sourceLineage = { screenplay_revision_id:'screenplay-1', setup_hash:'setup-1', scene_number:9, shot_number:9, source_prompt_sha256:'source-1' };
  await page.addInitScript(({request, sourceLineage}) => {
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({prompt:request.prompt, duration:6, resolution:0.98, workspaceId:'workspace-a', clipId:'story-current', workflowId:request.workflow_id, sourceLineage}));
    localStorage.setItem('vibe-video-active-job-v1', JSON.stringify({jobId:'job-current', snapshot:request}));
  }, {request, sourceLineage});
  const calls = [];
  const job = {job_id:'job-current',workspace_id:'workspace-a',clip_id:'story-current',status:'needs_review',request,source_lineage:{...sourceLineage,workflow_id:request.workflow_id},outputs:[{asset_id:'output-1',kind:'video',playback_url:'/api/video/assets/output-1/playback'}]};
  await page.route('**/api/**', async route => {
    const req=route.request(), url=new URL(req.url()); calls.push(`${req.method()} ${url.pathname}`);
    if(url.pathname==='/api/video/jobs/job-current') return route.fulfill({json:job});
    if(url.pathname==='/api/story/workspaces/workspace-a/screenplay/revisions/screenplay-1') return route.fulfill({json:{accepted:true,screenplay_revision_id:'screenplay-1',workspace_id:'workspace-a',screenplay:{scenes:[{scene_number:1,slugline:'INT. ROOM',summary:'',shots:[{shot_number:1},{shot_number:2}]}]}}});
    if(url.pathname==='/api/story/workspaces/workspace-a/prompt-drafts') return route.fulfill({json:{setup_hash:'setup-1',setup_matches_current:true,drafts:{'1.1':{workflow_id:request.workflow_id,prompt:'Scene one prompt'},'1.2':{workflow_id:request.workflow_id,prompt:'Scene two prompt'}}}});
    if(url.pathname==='/api/story/workspaces/workspace-a/production-setup') return route.fulfill({json:{workspace_id:'workspace-a',screenplay_revision_id:'screenplay-1',setup:{mode:'assisted_manual',automate_steps:{character_images:false,character_voice:false,world_images:false,frame_images:false,video:false},video_quality:'high',duration_policy:{kind:'fixed',seconds:6}},updated_at:'now'}});
    if(url.pathname==='/api/video/assets/output-1/playback') return route.fulfill({status:200,contentType:'video/mp4',body:''});
    return route.fulfill({status:404,json:{detail:'Unexpected API request'}});
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/take');
  await page.getByRole('button',{name:'Next clip',exact:true}).click();
  await expect(page.getByText(/Review the current accepted screenplay and choose a valid shot before advancing; your current take is unchanged\./)).toBeVisible();
  await expect(page.getByText(/reopen the saved shot from Prompt Preparation/i)).toHaveCount(0);
  expect(calls.some(call => call.endsWith('/accept'))).toBeFalsy();
  await expect(page.getByRole('button',{name:'Next clip',exact:true})).toBeVisible();
});

test('lost create response preserves the frozen request and only reconciles on reload', async ({ page }) => {
  let savedJob;
  let jobPosts = 0;
  const calls = [];
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url()); calls.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: capability(true) });
    if (url.pathname === '/api/video/validations') return route.fulfill({ json: { valid: true, request_hash: 'hash', normalized_request: request.postDataJSON().request, compiled_preview: {} } });
    if (url.pathname === '/api/video/jobs' && request.method() === 'POST') {
      jobPosts++; const body = request.postDataJSON(); savedJob = { job_id: 'job-recovered', workspace_id: body.workspace_id, clip_id: body.clip_id, status: 'running', request: body.request, outputs: [], created_at: 'now', updated_at: 'now' };
      return route.abort('connectionreset');
    }
    if (url.pathname === '/api/video/jobs/by-idempotency/' + encodeURIComponent(request.url().split('/by-idempotency/')[1]?.split('?')[0] || '')) return route.fulfill({ json: savedJob });
    if (url.pathname === '/api/video/jobs/job-recovered') return route.fulfill({ json: savedJob });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video'); await page.evaluate(() => localStorage.clear()); await page.reload();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByLabel('Shot prompt').fill('Frozen original prompt.');
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByRole('button', { name: 'Recover saved attempt' })).toBeVisible();
  const keyBeforeReload = await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-draft-v1')).pendingKey);
  expect(keyBeforeReload).toBeTruthy();
  await page.reload();
  await expect(page.getByText('Recovered the saved job by its idempotency key. No new job was submitted.', { exact: true })).toBeVisible();
  await page.getByRole('link',{name:'Current Take',exact:true}).first().click();
  await expect(page.getByText('Rendering your shot')).toBeVisible();
  expect(jobPosts).toBe(1);
  expect(calls.filter(call => call.startsWith('GET /api/video/jobs/by-idempotency/')).length).toBeGreaterThanOrEqual(1);
});

test('definitive stale story handoff rejection clears pending attempt but keeps editable draft', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Saved shot prompt.', duration: 6, resolution: 0.98, workspaceId: 'workspace-story',
    clipId: 'story-clip-original', workflowId: 'minimax_h3_t2v_local_v1',
    sourceLineage: { screenplay_revision_id: 'screenplay-old', setup_hash: 'a'.repeat(64), scene_number: 1, shot_number: 1, source_prompt_sha256: 'b'.repeat(64) },
  })));
  let posts = 0;
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: capability(true) });
    if (url.pathname === '/api/video/validations') return route.fulfill({ json: { valid: true, normalized_request: request.postDataJSON().request, compiled_preview: {} } });
    if (url.pathname === '/api/video/jobs' && request.method() === 'POST') {
      posts++;
      return route.fulfill({ status: 409, json: { error: { code: 'story_handoff_rejected', message: 'Saved shot prompt changed after opening it in Video.' }, admission_state: 'not_created' } });
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: `Unexpected ${request.method()} ${url.pathname}` } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.getByText('Screenplay · Scene 1, Shot 1')).toBeVisible();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByText(/backend confirmed no job was created/)).toBeVisible();
  const state = await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-draft-v1')));
  expect(state.pendingKey).toBeFalsy();
  expect(state.pendingRequest).toBeFalsy();
  expect(state.sourceLineage).toBeFalsy();
  expect(state.clipId).not.toBe('story-clip-original');
  await expect(page.getByLabel('Shot prompt')).toHaveValue('Saved shot prompt.');
  await expect(page.getByLabel('Shot prompt')).toBeEnabled();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeEnabled();
  expect(posts).toBe(1);
});

test('an active Video job stays mounted while visiting Status and returning to Create', async ({ page }) => {
  let jobPosts = 0;
  let job;
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: capability(true) });
    if (url.pathname === '/api/video/validations') return route.fulfill({ json: { valid: true, request_hash: 'hash', normalized_request: request.postDataJSON().request, compiled_preview: {} } });
    if (url.pathname === '/api/video/jobs' && request.method() === 'POST') {
      jobPosts++;
      const body = request.postDataJSON();
      job = { job_id: 'job-stays-mounted', workspace_id: body.workspace_id, clip_id: body.clip_id, status: 'running', request: body.request, outputs: [], created_at: 'now', updated_at: 'now', attempt: 1 };
      return route.fulfill({ json: job });
    }
    if (url.pathname === '/api/video/jobs/job-stays-mounted') return route.fulfill({ json: job });
    if (url.pathname.startsWith('/api/status')) return route.fulfill({ status: 503, json: { error: { message: 'Status fixture offline' } } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByLabel('Shot prompt').fill('Keep this rendering job while I inspect status.');
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByText('Rendering your shot')).toBeVisible();
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/status');
  await expect(page.getByRole('heading', { name: 'Connections & workflows' })).toBeVisible();
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/take');
  await expect(page.getByText('Rendering your shot')).toBeVisible();
  await expect(page.getByText('job-stays-mounted')).toBeVisible();
  expect(jobPosts).toBe(1);
});

test('FFL2VA uses ordered workspace images, validated preview and durable job request', async ({ page }) => {
  const validations = [];
  const submissions = [];
  const checks = [];
  await page.addInitScript(() => {
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({ prompt: '', duration: 6,
      resolution: 0.98, workspaceId: 'video-workspace', clipId: 'clip-ffl',
      workflowId: 'minimax_h3_t2v_local_v1' }));
  });
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.pathname === '/api/video/capabilities') {
      checks.push(url.searchParams.get('workflow_id'));
      const isFl2va = url.searchParams.get('workflow_id') === 'minimax_h3_fl2va_first_last_v1';
      return route.fulfill({ json: { ...capability(true), workflow_id: isFl2va ? 'minimax_h3_fl2va_first_last_v1' : 'minimax_h3_t2v_local_v1' } });
    }
    if (url.pathname === '/api/images/selections') return route.fulfill({json:{selection:null}});
    if (url.pathname === '/api/media/video-workspace/assets') return route.fulfill({ json: { total: 2, assets: [
      { asset_id: 'frame-first', workspace_id: 'video-workspace', kind: 'image', roles: ['first_frame'], filename: 'opening.png', media_type: 'image/png', sha256: 'a'.repeat(64), size_bytes: 10, content_url: '/media/opening.png' },
      { asset_id: 'frame-last', workspace_id: 'video-workspace', kind: 'image', roles: ['last_frame'], filename: 'closing.png', media_type: 'image/png', sha256: 'b'.repeat(64), size_bytes: 10, content_url: '/media/closing.png' },
    ] } });
    if (url.pathname === '/api/video/validations') {
      const body = request.postDataJSON(); validations.push(body.request);
      return route.fulfill({ json: { valid: true, normalized_request: body.request,
        compiled_preview: { workflow_id: body.request.workflow_id, request: body.request,
          compiled: { frame_count: 158, predicted_duration_seconds: 158 / 24,
            width: 1344, height: 768 }, preview_only: true, submission_performed: false } } });
    }
    if (url.pathname === '/api/video/jobs' && request.method() === 'POST') {
      const body = request.postDataJSON(); submissions.push(body.request);
      return route.fulfill({ json: { job_id: 'fl2va-job', workspace_id: body.workspace_id,
        clip_id: body.clip_id, status: 'queued', request: body.request, outputs: [] } });
    }
    if (url.pathname === '/api/video/jobs/fl2va-job') return route.fulfill({ json: { job_id: 'fl2va-job', status: 'queued', request: submissions.at(-1), outputs: [] } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByRole('button', { name: /First \+ last frame/ }).click();
  await expect(page.getByLabel('First frame', {exact:true})).toContainText('opening.png');
  await page.getByLabel('First frame', {exact:true}).selectOption('frame-first');
  await page.getByLabel('Last frame', {exact:true}).selectOption('frame-last');
  await page.getByLabel('Shot prompt').fill('Move from the first image to the final image.');
  await page.getByLabel('Duration').selectOption('6');
  await page.getByRole('button', { name: 'Preview settings' }).click();
  await expect(page.getByText('PREVIEW ONLY')).toBeVisible();
  await expect(page.locator('.snapshot-tags')).toContainText('6.583333333333333s');
  await expect(page.locator('.snapshot-tags')).toContainText('158 frames');
  expect(validations[0]).toMatchObject({ workflow_id: 'minimax_h3_fl2va_first_last_v1',
    first_frame: { asset_id: 'frame-first', sha256: 'a'.repeat(64) },
    last_frame: { asset_id: 'frame-last', sha256: 'b'.repeat(64) } });
  expect(validations[0].first_frame).not.toHaveProperty('path');
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await expect.poll(() => checks.at(-1)).toBe('minimax_h3_fl2va_first_last_v1');
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByText('Queued for generation', { exact: true })).toBeVisible();
  expect(submissions[0]).toMatchObject({ workflow_id: 'minimax_h3_fl2va_first_last_v1',
    first_frame: { asset_id: 'frame-first' }, last_frame: { asset_id: 'frame-last' } });
  expect(validations).toHaveLength(2);
  expect(submissions).toHaveLength(1);
});

test('story-linked FFL2VA lists frame-role assets with the matching shot recommended', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'A continuous courtroom shot.', duration: 6, resolution: 0.98,
    workspaceId: 'video-workspace', clipId: 'clip-current', workflowId: 'minimax_h3_fl2va_first_last_v1',
    sourceLineage: { screenplay_revision_id: 'screenplay-current', setup_hash: 'setup-hash',
      scene_number: 2, shot_number: 3, source_prompt_sha256: 'c'.repeat(64) },
  })));
  const image = (assetId, role, scene, clipId, suffix) => ({
    asset_id: assetId, workspace_id: 'video-workspace', kind: 'image', roles: [role],
    filename: `${assetId}.png`, media_type: 'image/png', sha256: suffix.repeat(64),
    size_bytes: 10, content_url: `/media/${assetId}.png`,
    metadata: { production_image_job: { intended_role: role, settings: { lineage: {
      target_type: 'clip', screenplay_revision_id: 'screenplay-current', scene_number: scene,
      shot_number: scene === 2 ? 3 : 1, clip_id: clipId,
    } } } },
  });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/images/selections') return route.fulfill({json:{selection:null}});
    if (url.pathname === '/api/media/video-workspace/assets') return route.fulfill({ json: { total: 3, assets: url.searchParams.get('kind') === 'image' ? [
      image('other-first', 'first_frame', 1, 'clip-other', 'a'),
      image('current-first', 'first_frame', 2, 'clip-current', 'b'),
      image('current-last', 'last_frame', 2, 'clip-current', 'd'),
    ] : [] } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.getByLabel('First frame', {exact:true}).locator('option')).toHaveText([
    'Choose first frame…', 'Recommended · Scene 2 · Shot 3 · current-first.png',
    'Scene 1 · Shot 1 · other-first.png',
  ]);
  await expect(page.getByLabel('Last frame', {exact:true}).locator('option')).toHaveText([
    'Choose last frame…', 'Recommended · Scene 2 · Shot 3 · current-last.png',
  ]);
});

test('FFLF accepts slot-specific frame uploads by picker, drop, and image paste', async ({ page }) => {
  const uploaded = [];
  const assets = [];
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Move from the opening frame to the closing frame.', duration: 6, resolution: 0.98,
    workspaceId: 'video-workspace', clipId: 'clip-local-frames', workflowId: 'minimax_h3_fl2va_first_last_v1',
  })));
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.pathname === '/api/media/video-workspace/assets' && request.method() === 'GET') return route.fulfill({ json: { total: assets.length, assets } });
    if (url.pathname === '/api/media/video-workspace/assets' && request.method() === 'POST') {
      const role = url.searchParams.get('role'); const filename = url.searchParams.get('filename');
      const asset = { asset_id: `asset-${uploaded.length + 1}`, workspace_id: 'video-workspace', kind: 'image', roles: [role], filename,
        media_type: 'image/png', sha256: String.fromCharCode(97 + uploaded.length).repeat(64), size_bytes: 10, content_url: `/api/media/video-workspace/assets/asset-${uploaded.length + 1}/content` };
      uploaded.push({ role, filename }); assets.push(asset);
      return route.fulfill({ json: { ...asset, deduplicated: false } });
    }
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: { ...capability(false), workflow_id: 'minimax_h3_fl2va_first_last_v1' } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected request in local frame upload test' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByLabel('Choose first frame image').setInputFiles({ name: 'opening.png', mimeType: 'image/png', buffer: Buffer.from('first') });
  await expect(page.getByLabel('First frame', { exact: true })).toHaveValue('asset-1');
  await expect(page.getByAltText('First frame: opening.png')).toBeVisible();
  await page.locator('[aria-label="Drop or paste last frame image"]').evaluate(node => {
    const file = new File(['last'], 'closing.png', { type: 'image/png' });
    const transfer = new DataTransfer(); transfer.items.add(file);
    node.dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer: transfer }));
  });
  await expect(page.getByLabel('Last frame', { exact: true })).toHaveValue('asset-2');
  await expect(page.getByAltText('Last frame: closing.png')).toBeVisible();
  await page.locator('[aria-label="Drop or paste first frame image"]').evaluate(node => {
    const file = new File(['replacement'], 'opening-revised.png', { type: 'image/png' });
    const transfer = new DataTransfer(); transfer.items.add(file);
    node.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, clipboardData: transfer }));
  });
  await expect(page.getByLabel('First frame', { exact: true })).toHaveValue('asset-3');
  await expect(page.getByLabel('Last frame', { exact: true })).toHaveValue('asset-2');
  await expect(page.getByAltText('First frame: opening-revised.png')).toBeVisible();
  expect(uploaded).toEqual([
    { role: 'first_frame', filename: 'opening.png' },
    { role: 'last_frame', filename: 'closing.png' },
    { role: 'first_frame', filename: 'opening-revised.png' },
  ]);
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-draft-v1')))).toMatchObject({
    firstFrameAssetId: 'asset-3', lastFrameAssetId: 'asset-2',
  });
});

test('frame assets refresh after an upload in Media Prep', async ({ page }) => {
  let assets = [
    { asset_id: 'frame-first', workspace_id: 'video-workspace', kind: 'image', roles: ['first_frame'], filename: 'opening.png', media_type: 'image/png', sha256: 'a'.repeat(64), size_bytes: 10, content_url: '/media/opening.png' },
    { asset_id: 'frame-last', workspace_id: 'video-workspace', kind: 'image', roles: ['last_frame'], filename: 'closing.png', media_type: 'image/png', sha256: 'b'.repeat(64), size_bytes: 10, content_url: '/media/closing.png' },
  ];
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Transition between frames.', duration: 6, resolution: 0.98,
    workspaceId: 'video-workspace', clipId: 'clip-upload',
    workflowId: 'minimax_h3_fl2va_first_last_v1' })));
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.pathname === '/api/story/workspaces') return route.fulfill({ json: { items: [{ workspace_id: 'video-workspace', title: 'Video workspace' }], total: 1 } });
    if (url.pathname === '/api/media/video-workspace/assets' && request.method() === 'GET') return route.fulfill({ json: { total: assets.length, assets } });
    if (url.pathname === '/api/media/video-workspace/assets' && request.method() === 'POST') {
      const added = { asset_id: 'new-frame', workspace_id: 'video-workspace', kind: 'image', roles: ['first_frame'], filename: 'new-frame.png', media_type: 'image/png', sha256: 'c'.repeat(64), size_bytes: 10, content_url: '/media/new-frame.png' };
      assets = [...assets, added]; return route.fulfill({ json: { ...added, deduplicated: false } });
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByRole('link', { name: 'Open Media Prep' }).click();
  await page.getByLabel('Choose media file').setInputFiles({ name: 'new-frame.png', mimeType: 'image/png', buffer: Buffer.from('test-image') });
  await page.getByRole('button', { name: 'Add asset' }).click();
  await expect(page.getByText('Added to the workspace library.')).toBeVisible();
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.getByLabel('First frame', {exact:true})).toContainText('new-frame.png');
});

test('saved frame IDs cannot enable FL2VA while the library is unresolved or failed', async ({ page }) => {
  let releaseAssets;
  const delayedAssets = new Promise(resolve => { releaseAssets = resolve; });
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Use saved frame IDs.', duration: 6, resolution: 0.98, workspaceId: 'video-workspace',
    clipId: 'clip-unresolved', workflowId: 'minimax_h3_fl2va_first_last_v1',
    firstFrameAssetId: 'frame-first', lastFrameAssetId: 'frame-last' })));
  await page.route('**/api/media/video-workspace/assets?kind=image', async route => {
    await delayedAssets;
    return route.fulfill({ status: 503, json: { detail: 'Library unavailable.' } });
  });
  await page.route('**/api/video/capabilities**', route => route.fulfill({ json: {
    ...capability(true), workflow_id: 'minimax_h3_fl2va_first_last_v1' } }));
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.getByText('Loading workspace images…')).toBeVisible();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
  releaseAssets();
  await expect(page.locator('.fl2va-frame-card p[role="alert"]')).toContainText('Could not load frame images');
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
});

test('preview locks its inputs until the captured request finishes', async ({ page }) => {
  let releaseValidation;
  let releaseJob;
  const delayedValidation = new Promise(resolve => { releaseValidation = resolve; });
  const delayedJob = new Promise(resolve => { releaseJob = resolve; });
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Frozen for preview.', duration: 6, resolution: 0.98,
    workspaceId: 'video-workspace', clipId: 'clip-preview-lock',
    workflowId: 'minimax_h3_fl2va_first_last_v1', firstFrameAssetId: 'frame-first', lastFrameAssetId: 'frame-last' })));
  await page.route('**/api/media/video-workspace/assets**', route => route.fulfill({ json: { total: 2, assets: [
    { asset_id: 'frame-first', workspace_id: 'video-workspace', kind: 'image', roles: ['first_frame'], filename: 'opening.png', media_type: 'image/png', sha256: 'a'.repeat(64), size_bytes: 10, content_url: '/media/opening.png' },
    { asset_id: 'frame-last', workspace_id: 'video-workspace', kind: 'image', roles: ['last_frame'], filename: 'closing.png', media_type: 'image/png', sha256: 'b'.repeat(64), size_bytes: 10, content_url: '/media/closing.png' },
  ] } }));
  await page.route('**/api/video/validations', async route => {
    await delayedValidation;
    const request = route.request().postDataJSON().request;
    return route.fulfill({ json: { valid: true, normalized_request: request,
      compiled_preview: { preview_only: true, workflow_id: request.workflow_id, request,
        compiled: { frame_count: 158, predicted_duration_seconds: 158 / 24, width: 1344, height: 768 } } } });
  });
  await page.route('**/api/video/capabilities**', route => route.fulfill({ json: capability(true) }));
  await page.route('**/api/video/jobs', async route => {
    await delayedJob;
    const body = route.request().postDataJSON();
    return route.fulfill({ json: { job_id: 'locked-job', workspace_id: body.workspace_id,
      clip_id: body.clip_id, status: 'queued', request: body.request, outputs: [] } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.getByLabel('First frame', {exact:true})).toContainText('opening.png');
  await page.getByRole('button', { name: 'Preview settings' }).click();
  await expect(page.getByLabel('Shot prompt')).toBeDisabled();
  await expect(page.getByLabel('First frame', {exact:true})).toBeDisabled();
  await expect(page.getByRole('button', { name: /Text to video/ })).toBeDisabled();
  releaseValidation();
  await expect(page.getByText('PREVIEW ONLY')).toBeVisible();
  await expect(page.getByLabel('Shot prompt')).toBeEnabled();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByLabel('Shot prompt')).toBeDisabled();
  await expect(page.getByLabel('Last frame', {exact:true})).toBeDisabled();
  await expect(page.getByRole('button', { name: /Text to video/ })).toBeDisabled();
  releaseJob();
  await expect(page.getByText('Queued for generation')).toBeVisible();
});

test('FL2VA readiness reason is shown and generation stays disabled', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Frame to frame.', duration: 6, resolution: 0.98, workspaceId: 'video-workspace',
    clipId: 'clip-disabled', workflowId: 'minimax_h3_fl2va_first_last_v1',
    firstFrameAssetId: 'frame-first', lastFrameAssetId: 'frame-last' })));
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: {
      ...capability(false), workflow_id: 'minimax_h3_fl2va_first_last_v1',
      disabled_reason: 'FL2VA smoke manifest is missing.' } });
    if (url.pathname === '/api/images/selections') return route.fulfill({json:{selection:null}});
    if (url.pathname === '/api/media/video-workspace/assets') return route.fulfill({ json: { total: 2, assets: [
      { asset_id: 'frame-first', kind: 'image', roles: [], filename: 'opening.png', sha256: 'a'.repeat(64) },
      { asset_id: 'frame-last', kind: 'image', roles: [], filename: 'closing.png', sha256: 'b'.repeat(64) },
    ] } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await expect(page.locator('.video-readiness')).toContainText('The selected video workflow is not ready. Check Status for setup details.');
  await expect(page.locator('.video-readiness details small')).toBeHidden();
  await page.locator('.video-readiness').getByText('Technical details').click();
  await expect(page.locator('.video-readiness details small')).toContainText('FL2VA smoke manifest is missing.');
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
});

test('R2V gates on its own readiness, collates numbered refs, previews, and submits frozen library IDs', async ({ page }) => {
  const readiness = [];
  let workflowReady = false;
  const validations = [];
  const submissions = [];
  const workspaceId = 'r2v-workspace';
  const assets = {
    image: [
      { asset_id: 'other-image', workspace_id: workspaceId, kind: 'image', roles: ['character_master'], filename: 'neutral.png', description: 'plain daylight', media_type: 'image/png', sha256: '4'.repeat(64), size_bytes: 12, content_url: '/media/neutral.png', created_at: '2026-10-10T00:00:00Z' },
      { asset_id: 'look-image', workspace_id: workspaceId, kind: 'image', roles: ['character_master'], filename: 'look.png', description: 'rainy courtroom blue hour', media_type: 'image/png', sha256: '1'.repeat(64), size_bytes: 12, content_url: '/media/look.png', created_at: '2026-10-09T00:00:00Z' },
    ],
    video: [{ asset_id: 'motion-video', workspace_id: workspaceId, kind: 'video', roles: ['motion'], filename: 'motion.mp4', metadata: {analyzer_run_id:'run-a'}, media_type: 'video/mp4', sha256: '2'.repeat(64), size_bytes: 24, content_url: '/media/motion.mp4' }],
    audio: [{ asset_id: 'sound-audio', workspace_id: workspaceId, kind: 'audio', roles: ['music'], filename: 'sound.wav', metadata: {analyzer_run_id:'run-a'}, media_type: 'audio/wav', sha256: '3'.repeat(64), size_bytes: 18, content_url: '/media/sound.wav' }],
  };
  await page.addInitScript(({ workspaceId }) => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: '', duration: 6, resolution: 0.98, workspaceId, clipId: 'clip-r2v',
    workflowId: 'minimax_h3_t2v_local_v1' })), { workspaceId });
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.pathname === '/api/video/capabilities') {
      const workflowId = url.searchParams.get('workflow_id'); readiness.push(workflowId);
      const isReady = workflowReady;
      return route.fulfill({ json: { ...capability(isReady), workflow_id: workflowId,
        disabled_reason: isReady ? null : 'R2V smoke evidence is missing.' } });
    }
    if (url.pathname.startsWith(`/api/media/${workspaceId}/assets`)) {
      if (url.pathname.endsWith('/seo-styles')) return route.fulfill({ json: { styles: [{ style_id: 'seo-rain', name: 'Rain noir', weighted_terms: [{term:'rain',weight:3}], avoid_terms: [], created_at: '2026-10-10T00:00:00Z' }] } });
      if (url.pathname.endsWith('/catalogue')) return route.fulfill({json:{assets:[],total:0,workspaces:[],workspace_names:{}}});
      const kind = url.searchParams.get('kind');
      return route.fulfill({ json: { total: assets[kind].length, assets: assets[kind] } });
    }
    if (url.pathname === '/api/video/validations') {
      const body = request.postDataJSON(); validations.push(body.request);
      return route.fulfill({ json: { valid: true, normalized_request: body.request,
        compiled_preview: { workflow_id: body.request.workflow_id, request: body.request,
          reference_map: { images: ['<Picture 1>'], videos: ['<Video 1>'], audios: ['<Audio 1>', '<Audio 2>'] },
          compiled: { predicted_duration_seconds: 6, width: 1344, height: 768 }, preview_only: true, submission_performed: false } } });
    }
    if (url.pathname === '/api/video/jobs' && request.method() === 'POST') {
      const body = request.postDataJSON(); submissions.push(body);
      return route.fulfill({ json: { job_id: 'r2v-job', workspace_id: body.workspace_id,
        clip_id: body.clip_id, status: 'queued', request: body.request, outputs: [] } });
    }
    if (url.pathname === '/api/video/jobs/r2v-job') return route.fulfill({ json: { job_id: 'r2v-job', status: 'queued', request: submissions.at(-1)?.request, outputs: [] } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: `Unexpected mocked API request: ${request.method()} ${url.pathname}` } });
  });

  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByRole('button', { name: /Reference to video/ }).click();
  await expect(page.locator('.r2v-asset-carousel[aria-label="Characters reference carousel"]')).toBeVisible();
  await page.getByLabel('Rank characters by SEO style').selectOption('seo-rain');
  await expect(page.locator('.r2v-asset-card').filter({ hasText: 'look.png' })).toHaveCount(1);
  await page.locator('.r2v-asset-card').filter({ hasText: 'look.png' }).getByRole('button').click();
  await page.getByRole('button', { name: 'Add selected character image' }).click();
  await page.locator('.r2v-asset-card').filter({ hasText: 'motion.mp4' }).getByRole('button').click();
  await page.getByRole('button', { name: 'Add selected video clip' }).click();
  await page.getByLabel('Audio reference source', {exact:true}).selectOption('audio-clips');
  await page.locator('.r2v-asset-card').filter({ hasText: 'sound.wav' }).getByRole('button').click();
  await page.getByRole('button', { name: 'Add selected audio clip' }).click();
  await page.getByLabel('image reference 1 role').fill('character appearance');
  await page.getByLabel('image reference 1 instruction').fill('Keep the same face and coat.');
  await page.getByLabel('video reference 1 role').fill('camera movement');
  await page.getByLabel('video reference 1 instruction').fill('Follow the slow side-tracking move.');
  await page.getByLabel('Also use this video’s soundtrack').check();
  await page.getByLabel('video reference 1 soundtrack direction').fill('Keep its low rhythmic pulse.');
  await page.getByLabel('audio reference 1 role').fill('music');
  await page.getByLabel('audio reference 1 instruction').fill('Use only as a tonal guide.');
  await page.getByLabel('Main shot prompt').fill('A detective enters the station at dawn.');
  await page.getByRole('button', { name: 'Collate prompt' }).click();
  await expect(page.getByLabel('Final prompt')).toContainText('<Picture 1>');
  await expect(page.getByLabel('Final prompt')).toContainText('<Video 1>');
  await expect(page.getByLabel('Final prompt')).toContainText('<Audio 1>');
  await expect(page.getByLabel('Final prompt')).toContainText('<Audio 2>');

  await page.getByRole('button', { name: 'Check readiness' }).click();
  await expect(page.locator('.video-readiness')).toContainText('The selected video workflow is not ready. Check Status for setup details.');
  await expect(page.locator('.video-readiness details small')).toContainText('R2V smoke evidence is missing.');
  await page.locator('.video-readiness').getByText('Technical details').click();
  await expect(page.locator('.video-readiness details small')).toBeVisible();
  await expect(page.locator('.video-readiness details small')).toContainText('R2V smoke evidence is missing.');
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
  expect(submissions).toHaveLength(0);

  workflowReady = true;
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeEnabled();
  await page.getByRole('button', { name: 'Preview settings' }).click();
  await expect(page.getByText('PREVIEW ONLY')).toBeVisible();
  await expect(page.locator('.r2v-preview-map')).toContainText('<Picture 1>');
  expect(validations.at(-1)).toMatchObject({ workflow_id: 'minimax_h3_r2v_dynamic_v1',
    images: [{ asset_id: 'look-image', sha256: '1'.repeat(64), role: 'character appearance', intent: 'Keep the same face and coat.' }],
    videos: [{ asset_id: 'motion-video', sha256: '2'.repeat(64), role: 'camera movement', include_paired_soundtrack: true, audio_intent: 'Keep its low rhythmic pulse.' }],
    audios: [{ asset_id: 'sound-audio', sha256: '3'.repeat(64), role: 'music', intent: 'Use only as a tonal guide.' }] });
  expect(JSON.stringify(validations.at(-1))).not.toContain('content_url');
  expect(JSON.stringify(validations.at(-1))).not.toContain('/home/');

  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByText('Queued for generation', { exact: true })).toBeVisible();
  expect(submissions).toHaveLength(1);
  expect(submissions[0]).toMatchObject({ workspace_id: workspaceId, clip_id: 'clip-r2v', request: {
    workflow_id: 'minimax_h3_r2v_dynamic_v1', prompt: expect.stringContaining('<Picture 1>'),
    images: [{ asset_id: 'look-image' }], videos: [{ asset_id: 'motion-video' }], audios: [{ asset_id: 'sound-audio' }] } });
  // Mount/workflow changes also refresh readiness; preview and submit must use R2V.
  expect(readiness.slice(-3)).toEqual(['minimax_h3_r2v_dynamic_v1','minimax_h3_r2v_dynamic_v1','minimax_h3_r2v_dynamic_v1']);
});

test('R2V remains usable when the optional SEO-style response has no styles array', async ({ page }) => {
  const workspaceId = 'r2v-missing-seo-styles';
  await page.addInitScript(({ workspaceId }) => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'A quiet street at dusk.', duration: 6, resolution: 0.98, workspaceId, clipId: 'clip-missing-seo',
    workflowId: 'minimax_h3_r2v_dynamic_v1' })), { workspaceId });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: { ...capability(false), workflow_id: 'minimax_h3_r2v_dynamic_v1' } });
    if (url.pathname === `/api/media/${workspaceId}/assets/seo-styles`) return route.fulfill({ json: {} });
    if (url.pathname === `/api/media/${workspaceId}/assets`) return route.fulfill({ json: { assets: [], total: 0 } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: `Unexpected request ${url.pathname}` } });
  });

  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.getByRole('heading', { name: 'Create video' })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Rank characters by SEO style' })).toHaveValue('');
});

test('R2V requests pinned production-style media and keeps it first in each compatible carousel', async ({ page }) => {
  const workspaceId = 'r2v-style-recommendations';
  const styleContextId = 'setup-12345678-1234-1234-1234-123456789abc';
  const requested = [];
  const asset = (id, kind, filename, extra = {}) => ({ asset_id: id, workspace_id: workspaceId, kind, roles: ['style_reference'],
    filename, media_type: `${kind}/test`, sha256: 'a'.repeat(64), size_bytes: 10, content_url: `/media/${id}`, ...extra });
  const pinned = [asset('pinned-image', 'image', 'Pinned style image.png', { recommended: true, recommendation_source: 'production_style' }),
    asset('pinned-video', 'video', 'Pinned style video.mp4', { recommended: true, recommendation_source: 'production_style' }),
    asset('pinned-audio', 'audio', 'Pinned style sound.mp3', { recommended: true, recommendation_source: 'production_style' })];
  const ordinary = [asset('ordinary-image', 'image', 'Ordinary image.png', { roles: ['character_master'] }),
    asset('ordinary-video', 'video', 'Ordinary video.mp4', { roles: ['project_video'] }),
    asset('ordinary-audio', 'audio', 'Ordinary clip.mp3', { roles: ['project_audio'] }),
    asset('ordinary-voice', 'audio', 'Ordinary voice.wav', { roles: ['voice_master'], audio_category: 'voice' })];
  await page.addInitScript(({ workspaceId, styleContextId }) => {
    localStorage.setItem('vibe-style-setup-context-v1', styleContextId);
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({ prompt: 'A character walks through a rainy street.', r2vMainPrompt: 'A character walks through a rainy street.',
      duration: 6, resolution: 0.98, workspaceId, clipId: 'clip-style-pins', workflowId: 'minimax_h3_r2v_dynamic_v1' }));
  }, { workspaceId, styleContextId });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: { ...capability(false), workflow_id: 'minimax_h3_r2v_dynamic_v1' } });
    if (url.pathname === `/api/media/${workspaceId}/assets/seo-styles`) return route.fulfill({ json: { styles: [] } });
    if (url.pathname === `/api/media/${workspaceId}/assets`) {
      requested.push({ kind: url.searchParams.get('kind'), styleContextId: url.searchParams.get('style_context_id') });
      const kind = url.searchParams.get('kind');
      const matching = [...pinned, ...ordinary].filter(row => row.kind === kind);
      return route.fulfill({ json: { assets: matching, total: matching.length } });
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: `Unexpected request ${url.pathname}` } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.locator('.r2v-asset-card').filter({ hasText: 'Pinned style image.png' })).toHaveCount(1);
  await expect(page.locator('.r2v-asset-card').filter({ hasText: 'Pinned style video.mp4' })).toHaveCount(1);
  await page.getByLabel('Audio reference source', {exact:true}).selectOption('audio-clips');
  await expect(page.locator('.r2v-asset-card').filter({ hasText: 'Pinned style sound.mp3' })).toHaveCount(1);
  await page.getByLabel('Audio reference source', {exact:true}).selectOption('voices');
  await expect(page.locator('.r2v-subcarousel').filter({ hasText: 'Voice Files' }).locator('.r2v-asset-card')).toHaveCount(1);
  expect(new Set(requested.map(row => row.kind))).toEqual(new Set(['image', 'video', 'audio']));
  expect(requested.every(row => row.styleContextId === styleContextId)).toBe(true);
  for (const [source,carousel] of [['characters','Characters'], ['worlds','Worlds'], ['first-frames','First Frames'], ['last-frames','Last Frames']]) {
    await page.getByLabel('Images reference source', {exact:true}).selectOption(source);
    await expect(page.locator('.r2v-subcarousel').filter({ hasText: carousel }).locator('.r2v-asset-card').first()).toContainText('Pinned style image.png');
  }
  await expect(page.locator('.r2v-subcarousel').filter({ hasText: 'Video Assets' }).locator('.r2v-asset-card').first()).toContainText('Pinned style video.mp4');
  await page.getByLabel('Audio reference source', {exact:true}).selectOption('audio-clips');
  await expect(page.locator('.r2v-subcarousel').filter({ hasText: 'Audio Assets' }).locator('.r2v-asset-card').first()).toContainText('Pinned style sound.mp3');
});

test('R2V file picker and drop upload references into the same workspace library', async ({ page }) => {
  const workspaceId = 'r2v-direct-upload';
  const assets = { image: [], video: [], audio: [] };
  const roles = [];
  let nextId = 0;
  await page.addInitScript(({ workspaceId }) => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: '', duration: 6, resolution: 0.98, workspaceId, clipId: 'clip-direct-upload', workflowId: 'minimax_h3_t2v_local_v1' })), { workspaceId });
  await page.route('**/api/**', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.pathname.startsWith(`/api/media/${workspaceId}/assets`) && request.method() === 'POST') {
      const role = url.searchParams.get('role'); roles.push(role);
      const kind = ['style_reference','character_master','project_image'].includes(role) ? 'image' : ['action_reference_video','project_video'].includes(role) ? 'video' : 'audio';
      const asset = { asset_id: `uploaded-${++nextId}`, workspace_id: workspaceId, kind,
        roles: [role], filename: url.searchParams.get('filename'), media_type: `${kind}/test`,
        sha256: String(nextId).repeat(64), size_bytes: 12, content_url: `/media/uploaded-${nextId}` };
      assets[kind].unshift(asset);
      return route.fulfill({ json: { ...asset, deduplicated: false } });
    }
    if (url.pathname.startsWith(`/api/media/${workspaceId}/assets`)) {
      if (url.pathname.endsWith('/seo-styles')) return route.fulfill({ json: { styles: [] } });
      if (url.pathname.endsWith('/catalogue')) return route.fulfill({json:{assets:[],total:0,workspaces:[],workspace_names:{}}});
      const kind = url.searchParams.get('kind');
      return route.fulfill({ json: { assets: assets[kind], total: assets[kind].length } });
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: `Unexpected request ${request.method()} ${url.pathname}` } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByRole('button', { name: /Reference to video/ }).click();
  await page.locator('.r2v-upload-button input').first().setInputFiles({ name: 'look.png', mimeType: 'image/png', buffer: Buffer.from('image') });
  await expect(page.getByLabel('image reference 1 role')).toHaveValue('visual identity or style');
  await page.evaluate(() => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['pasted image'], 'clipboard.png', { type: 'image/png' }));
    document.querySelector('.app-shell').dispatchEvent(new ClipboardEvent('paste', { bubbles: true, clipboardData: transfer }));
  });
  await expect(page.getByLabel('image reference 2 role')).toHaveValue('visual identity or style');
  await page.locator('.r2v-subcarousel').filter({ hasText: 'Video Assets' }).dispatchEvent('drop', { dataTransfer: await page.evaluateHandle(() => {
    const transfer = new DataTransfer(); transfer.items.add(new File(['video'], 'motion.mp4', { type: 'video/mp4' })); return transfer;
  }) });
  await expect(page.getByLabel('video reference 1 role')).toHaveValue('motion or camera reference');
  expect(roles).toEqual(['character_master', 'project_image', 'project_video']);
});

test('R2V asset pickers load items beyond the default first 50', async ({ page }) => {
  const workspaceId = 'r2v-large-library';
  const imageAssets = Array.from({ length: 51 }, (_, index) => ({ asset_id: `image-${index + 1}`, workspace_id: workspaceId,
    kind: 'image', roles: ['character_master'], filename: index === 50 ? 'late-image.png' : `image-${index + 1}.png`, media_type: 'image/png',
    sha256: String(index + 1).padStart(64, '0'), size_bytes: 10, content_url: `/media/image-${index + 1}.png` }));
  await page.addInitScript(({ workspaceId }) => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Build a shot from the late reference.', r2vMainPrompt: 'Build a shot from the late reference.', duration: 6,
    resolution: 0.98, workspaceId, clipId: 'clip-r2v-large', workflowId: 'minimax_h3_r2v_dynamic_v1' })), { workspaceId });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === `/api/media/${workspaceId}/assets`) {
      const offset = Number(url.searchParams.get('offset') || 0);
      if (url.searchParams.get('kind') === 'image') return route.fulfill({ json: { total: imageAssets.length,
        assets: imageAssets.slice(offset, offset + (offset ? 100 : 50)) } });
      return route.fulfill({ json: { total: 0, assets: [] } });
    }
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await expect(page.locator('.r2v-asset-card').filter({ hasText: 'late-image.png' })).toHaveCount(1);
  await page.locator('.r2v-asset-card').filter({ hasText: 'late-image.png' }).getByRole('button').click();
  await page.getByRole('button', { name: 'Add selected character image' }).click();
  await expect(page.getByText('late-image.png',{exact:true}).last()).toBeVisible();
});

test('R2V semantic picker uses indexed saved-text search for the selected media type', async ({ page }) => {
  const workspaceId = 'r2v-semantic-workspace';
  let searchRequest;
  const resultAsset = { asset_id: 'semantic-image', workspace_id: workspaceId, kind: 'image', roles: ['character_master'],
    filename: 'rainy-courtroom.png', description: 'Rainy courtroom with warm practical lights', media_type: 'image/png',
    sha256: '6'.repeat(64), size_bytes: 10, content_url: '/media/semantic-image.png' };
  await page.addInitScript(({ workspaceId }) => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Rainy courtroom scene.', r2vMainPrompt: 'Rainy courtroom scene.', duration: 6,
    resolution: 0.98, workspaceId, clipId: 'clip-r2v-semantic', workflowId: 'minimax_h3_r2v_dynamic_v1' })), { workspaceId });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === `/api/media/${workspaceId}/assets/search`) {
      searchRequest = { q: url.searchParams.get('q'), kind: url.searchParams.get('kind') };
      return route.fulfill({ json: { results: [{ asset: resultAsset, score: 0.91, text: resultAsset.description }], query_backend: 'saved_text' } });
    }
    if (url.pathname === `/api/media/${workspaceId}/assets`) return route.fulfill({ json: { total: 0, assets: [] } });
    if (url.pathname.endsWith('/seo-styles')) return route.fulfill({ json: { styles: [] } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByRole('button', { name: /Reference to video/ }).click();
  await page.getByLabel('Search characters by').selectOption('semantic');
  await page.getByRole('textbox', { name: 'Search characters' }).fill('rainy courtroom');
  await page.locator('.r2v-kind').filter({ hasText: 'Images' }).getByRole('button', { name: 'Search' }).click();
  await expect(page.locator('.r2v-asset-card').filter({ hasText: 'rainy-courtroom.png' })).toHaveCount(1);
  expect(searchRequest).toEqual({ q: 'rainy courtroom', kind: 'image' });
  await expect(page.getByText('Semantic search uses saved annotations and indexed media content. Content search requires completed indexing.')).toBeVisible();
});

test('Create Video Retake restores the original main prompt and re-collates edited reference intent', async ({ page }) => {
  const request = { workflow_id: 'minimax_h3_r2v_dynamic_v1', workflow_version: 1,
    workflow_sha256: '5ebac422ff9dd1eb467265d36610f10fa8744ff8c8d31262cd9bf871b814332d',
    prompt: 'The courier crosses the station.\n\n<Picture 1> is a character reference. Use it to preserve the old face.',
    duration_seconds: 6, aspect_ratio: '16:9', resolution_preset: 0.98, steps: 20, seed: 1, ref_image_size: 'match',
    images: [{ asset_id: 'retake-look', sha256: '4'.repeat(64), role: 'character', intent: 'preserve the old face' }], videos: [], audios: [] };
  const workspaceId = 'r2v-retake-workspace';
  await page.addInitScript(({ request, workspaceId }) => {
    localStorage.setItem('vibe-video-draft-v1', JSON.stringify({ prompt: '', r2vMainPrompt: 'The courier crosses the station.',
      r2vCollatedPrompt: request.prompt, r2vImages: [{ assetId: 'retake-look', role: 'character', intent: 'preserve the old face' }],
      r2vVideos: [], r2vAudios: [], duration: 6, resolution: 0.98, workspaceId, clipId: 'clip-retake', workflowId: request.workflow_id }));
    localStorage.setItem('vibe-video-active-job-v1', JSON.stringify({ jobId: 'r2v-source', snapshot: request,
      workspaceId, r2vMainPrompt: 'The courier crosses the station.' }));
  }, { request, workspaceId });
  await page.route('**/api/**', async route => {
    const apiRequest = route.request(); const url = new URL(apiRequest.url());
    if (url.pathname === '/api/video/jobs/r2v-source') return route.fulfill({ json: { job_id: 'r2v-source', workspace_id: workspaceId,
      clip_id: 'clip-retake', status: 'needs_review', request, outputs: [{ asset_id: 'clip-output', kind: 'video', playback_url: '/api/video/assets/clip-output/playback' }] } });
    if (url.pathname === '/api/video/assets/clip-output/playback') return route.fulfill({ status: 200, contentType: 'video/mp4', body: '' });
    if (url.pathname === `/api/media/${workspaceId}/assets`) return route.fulfill({ json: { total: 1, assets: [{ asset_id: 'retake-look', workspace_id: workspaceId,
      kind: 'image', roles: [], filename: 'retake-look.png', media_type: 'image/png', sha256: '4'.repeat(64), size_bytes: 10, content_url: '/media/retake-look.png' }] } });
    if (url.pathname === '/api/video/retakes/r2v-source') return route.fulfill({ json: { source_job_id: 'r2v-source', request,
      keep_original: false, candidate_disposition: 'discard_requested', asset_cleanup: 'archived_recoverable', submission_created: false } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.getByRole('link',{name:'Current Take',exact:true}).first().click();
  await page.getByRole('button', { name: 'Retake' }).click();
  await page.getByLabel('Discard from take history').check();
  await page.getByRole('button', { name: /Return to editor/ }).click();
  await expect(page.getByText(/archived from normal library search; Show archived can restore it/)).toBeVisible();
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-history-v1') || '[]'))).toHaveLength(0);
  await expect(page.getByLabel('Main shot prompt')).toHaveValue('The courier crosses the station.');
  await expect(page.getByLabel('image reference 1 instruction')).toHaveValue('preserve the old face');
  await page.getByLabel('image reference 1 instruction').fill('keep the raincoat and change the face');
  await page.getByRole('button', { name: 'Collate prompt' }).click();
  const finalPrompt = page.getByLabel('Final prompt');
  await expect(finalPrompt).toContainText('The courier crosses the station.');
  await expect(finalPrompt).toContainText('keep the raincoat and change the face');
  await expect(finalPrompt).not.toContainText('preserve the old face');
  await expect(finalPrompt).toContainText('<Picture 1>');
});

test('an explicitly blank R2V main prompt is not replaced by the prior prompt', async ({ page }) => {
  const workspaceId = 'r2v-empty-prompt';
  await page.addInitScript(({ workspaceId }) => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt: 'Old T2V prompt must not leak.', r2vMainPrompt: '', duration: 6, resolution: 0.98,
    workspaceId, clipId: 'clip-empty-main', workflowId: 'minimax_h3_r2v_dynamic_v1' })), { workspaceId });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === `/api/media/${workspaceId}/assets`) return route.fulfill({ json: { total: url.searchParams.get('kind') === 'image' ? 1 : 0, assets: url.searchParams.get('kind') === 'image' ? [{
      asset_id: 'empty-ref', workspace_id: workspaceId, kind: 'image', roles: [], recommendation_source: 'production_style', filename: 'style.png',
      media_type: 'image/png', sha256: '5'.repeat(64), size_bytes: 10, content_url: '/media/style.png' }] : [] } });
    if (url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page); await page.goto('/#/video');
  await page.locator('.r2v-asset-card').filter({ hasText: 'style.png' }).first().getByRole('button').click();
  await page.getByRole('button', { name: 'Add selected character image' }).click();
  await expect(page.getByLabel('Main shot prompt')).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Collate prompt' })).toBeDisabled();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
  await expect(page.getByText('Old T2V prompt must not leak.')).toHaveCount(0);
});

test('a failed audio library preserves available R2V images and FFLF choices',async({page})=>{
  const workspace='partial-library';
  const frame={asset_id:'frame-one',workspace_id:workspace,kind:'image',roles:['first_frame','last_frame','character_master'],filename:'available.png',content_url:'/frame.png',sha256:'a'.repeat(64),media:{},created_at:'2026-11-03'};
  await page.route('**/api/**',route=>{
    const url=new URL(route.request().url());
    if(url.pathname.endsWith('/assets'))return url.searchParams.get('kind')==='audio'?route.fulfill({status:503,json:{error:{message:'Audio temporarily unavailable'}}}):route.fulfill({json:{assets:url.searchParams.get('kind')==='image'?[frame]:[],total:url.searchParams.get('kind')==='image'?1:0}});
    if(url.pathname.endsWith('/seo-styles'))return route.fulfill({json:{styles:[]}});
    if(url.pathname==='/api/video/capabilities')return route.fulfill({json:capability(true)});
    if(url.pathname==='/api/studio-tools/output-destination')return route.fulfill({json:{mode:'default',path:'/fixture',available:true}});
    return route.fulfill({status:404,json:{error:{message:'Unused fixture endpoint'}}});
  });
  await mockProject(page,workspace);await page.goto('/#/video');
  await page.getByRole('button',{name:/Reference to video/}).click();
  await expect(page.locator('.r2v-asset-card').filter({hasText:'available.png'})).toHaveCount(1);
  await expect(page.getByText(/Some project references could not load/)).toBeVisible();
  await page.getByRole('button',{name:/First \+ last frame/}).click();
  await page.getByLabel('First frame',{exact:true}).selectOption('frame-one');
  await page.getByLabel('Last frame',{exact:true}).selectOption('frame-one');
  await page.getByLabel('Shot prompt',{exact:true}).fill('A continuous shot');
  await expect(page.getByRole('button',{name:/Generate video/})).toBeEnabled();
});

for (const invalidReference of [false, true]) test(`R2V pasted tag spellings ${invalidReference ? 'preserve invalid indices and expose rejection beside Generate' : 'compile and submit canonical audio tags'}`, async ({page}) => {
  const workspaceId = 'r2v-workspace';
  const assets = ['image', 'audio'].map((kind, index) => ({asset_id:`ref-${kind}`,workspace_id:workspaceId,
    kind,roles:[`project_${kind}`],filename:`ref.${kind==='image'?'png':'wav'}`,media_type:`${kind}/${kind==='image'?'png':'wav'}`,
    sha256:String(index+1).repeat(64),size_bytes:12,content_url:`/media/ref-${kind}`}));
  const submitted=[];
  await page.addInitScript(({workspaceId,invalidReference})=>localStorage.setItem('vibe-video-draft-v1',JSON.stringify({
    workspaceId,clipId:'clip-tags',workflowId:'minimax_h3_r2v_dynamic_v1',duration:15,resolution:0.98,
    prompt:'',r2vMainPrompt:'',
    r2vCollatedPrompt:`Use <picture1> as identity. Use <audio${invalidReference?2:1}> for the lion's voice.`,
    r2vImages:[{assetId:'ref-image',role:'lion',intent:'Preserve identity'}],
    r2vAudios:[{assetId:'ref-audio',role:'lion voice',intent:'Preserve voice'}],
  })),{workspaceId,invalidReference});
  await page.route('**/api/**',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.pathname==='/api/video/capabilities')return route.fulfill({json:{available:true,workflow_id:url.searchParams.get('workflow_id'),runtime_guard:{safe_to_submit:true},dispatch:{available:true}}});
    if(url.pathname===`/api/media/${workspaceId}/assets`)return route.fulfill({json:{assets,total:assets.length}});
    if(url.pathname==='/api/video/jobs'&&req.method()==='GET')return route.fulfill({json:{jobs:[]}});
    if(url.pathname==='/api/video/validations'){
      const prompt=req.postDataJSON().request.prompt;
      expect(prompt).toContain('<Picture 1>');expect(prompt).toContain(`<Audio ${invalidReference?2:1}>`);
      expect(prompt).not.toContain('<audio');
      if(invalidReference)return route.fulfill({status:422,json:{error:{code:'prompt_reference_tags_mismatch',message:'Prompt reference tags must match every connected reference exactly.'}}});
      return route.fulfill({json:{valid:true,compiled_preview:{}}});
    }
    if(url.pathname==='/api/video/jobs'&&req.method()==='POST'){
      submitted.push(req.postDataJSON());return route.fulfill({json:{job_id:'canonical-job',workspace_id:workspaceId,status:'queued',request:req.postDataJSON().request,outputs:[]}});
    }
    return route.fulfill({status:404,json:{detail:'Unused in reference tag regression'}});
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));
  await mockProject(page);await page.goto('/#/video');
  const generate=page.getByRole('button',{name:'Generate video',exact:true});
  await expect(generate).toBeEnabled();await generate.click();
  if(invalidReference){
    const feedback=page.getByRole('status',{name:'Generation feedback'});
    await expect(feedback).toContainText('Prompt reference tags must match');
    await expect(generate).toBeEnabled();
    await expect(feedback).toBeInViewport();
    const feedbackBox=await feedback.boundingBox(),buttonBox=await generate.boundingBox();
    expect(Math.abs(feedbackBox.y-buttonBox.y)).toBeLessThan(180);
    expect(submitted).toHaveLength(0);
  }else{
    await expect.poll(()=>submitted.length).toBe(1);
    expect(submitted[0].request.prompt).toContain('<Audio 1>');
    expect(submitted[0].request.audios[0].asset_id).toBe('ref-audio');
  }
});

for (const rejection of [false, true]) test(`planned screenplay clip remains editable with a manual final prompt${rejection ? ' after definite rejection' : ''}`, async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-video-draft-v1', JSON.stringify({
    prompt:'Screenplay suggestion.', duration:6, resolution:0.98, workspaceId:'workspace-story',
    clipId:'planned-clip', workflowId:'minimax_h3_t2v_local_v1',
    sourceLineage:{screenplay_revision_id:'screenplay-old',setup_hash:'a'.repeat(64),scene_number:1,shot_number:1,
      source_prompt_sha256:'b'.repeat(64),planned_clip_id:'planned-clip'},
  })));
  let submitted;
  await page.route('**/api/**', async route => {
    const request=route.request(), url=new URL(request.url());
    if(url.pathname==='/api/video/capabilities') return route.fulfill({json:capability(true)});
    if(url.pathname==='/api/video/validations') return route.fulfill({json:{valid:true,normalized_request:request.postDataJSON().request,compiled_preview:{}}});
    if(url.pathname==='/api/video/jobs' && request.method()==='POST') {
      submitted=request.postDataJSON();
      if(rejection) return route.fulfill({status:422,json:{error:{message:'Reference bytes changed.'},admission_state:'not_created'}});
      return route.fulfill({status:202,json:{job_id:'manual-planned',workspace_id:'workspace-story',clip_id:'planned-clip',status:'queued',request:submitted.request}});
    }
    if(url.pathname==='/api/video/jobs/manual-planned') return route.fulfill({json:{job_id:'manual-planned',status:'queued'}});
    if(url.pathname.endsWith('/assets')) return route.fulfill({json:{assets:[]}});
    return route.fulfill({status:404,json:{detail:'Not used'}});
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));
  await mockProject(page); await page.goto('/#/video');
  await page.getByRole('button',{name:'Check readiness'}).click();
  await expect(page.getByLabel('Duration',{exact:true})).toBeEnabled();
  await page.getByLabel('Duration',{exact:true}).selectOption('9');
  await page.getByLabel('Shot prompt',{exact:true}).fill('Use exactly my own prompt.');
  await page.getByRole('button',{name:/Generate video/}).click();
  await expect.poll(()=>submitted?.request.prompt).toBe('Use exactly my own prompt.');
  expect(submitted.request.duration_seconds).toBe(9);
  if(rejection) {
    await expect(page.getByText(/backend confirmed no job was created/)).toBeVisible();
    await expect(page.getByLabel('Shot prompt',{exact:true})).toBeEnabled();
    await expect(page.getByLabel('Duration',{exact:true})).toBeEnabled();
    const draft=await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-draft-v1')));
    expect(draft.pendingKey).toBeFalsy();
    expect(draft.prompt).toBe('Use exactly my own prompt.');
  } else await expect(page).toHaveURL(/#\/take/);
});

for(const existing of [false,true]) test(`pending attempt returns to editing without rendering: ${existing?'recover existing job':'release unsubmitted draft'}`,async({page})=>{
  const request={workflow_id:'minimax_h3_t2v_local_v1',workflow_version:2,prompt:'Keep my prompt.',duration_seconds:6};
  await page.addInitScript(request=>localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId:'workspace-a',clipId:'clip-a',prompt:'Keep my prompt.',duration:6,resolution:0.98,workflowId:request.workflow_id,pendingKey:'old-attempt',pendingRequest:request})),request);
  let renders=0,releases=0;
  const job={job_id:'existing-render',workspace_id:'workspace-a',clip_id:'clip-a',status:'running',request};
  await page.route('**/api/**',async route=>{
    const req=route.request(), url=new URL(req.url());
    if(url.pathname==='/api/video/capabilities')return route.fulfill({json:capability(true)});
    if(url.pathname.includes('/by-idempotency/'))return route.fulfill({status:existing?503:404,json:{error:{message:'Lookup unavailable'}}});
    if(url.pathname==='/api/video/attempts/release'){
      releases++;return route.fulfill({json:existing?{released:false,job}:{released:true}});
    }
    if(url.pathname==='/api/video/jobs' && req.method()==='POST'){renders++;return route.abort();}
    if(url.pathname==='/api/video/jobs/existing-render')return route.fulfill({json:job});
    if(url.pathname.endsWith('/assets'))return route.fulfill({json:{assets:[]}});
    return route.fulfill({status:404,json:{detail:'Not used'}});
  });
  await page.route('**/api/studio-tools/output-destination',r=>r.fulfill({json:{mode:'default',path:'/fixture/output',available:true}}));await mockProject(page);await page.goto('/#/video');
  if(existing)await page.getByRole('button',{name:'Return to editing',exact:true}).click();
  await expect(page.getByLabel('Shot prompt',{exact:true})).toBeEnabled();
  await expect(page.getByLabel('Shot prompt',{exact:true})).toHaveValue('Keep my prompt.');
  await expect(page.getByRole('button',{name:'Text to video',exact:false})).toBeEnabled();
  await expect(page.getByRole('button',{name:'Reference to video',exact:false})).toBeEnabled();
  expect(releases).toBe(1);expect(renders).toBe(0);
  const draft=await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-draft-v1')));
  expect(draft.pendingKey).toBeFalsy();
});
