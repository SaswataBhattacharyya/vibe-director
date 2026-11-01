import { test, expect } from '@playwright/test';

test('Status is read-only, shows catalog and runtime, and preserves the video draft', async ({ page }) => {
  const calls = [];
  const guard = { monitor_available: true, safe_to_submit: false, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100, operating_point: { temperature_c: 48, graphics_clock_mhz: 2431 }, reason: 'Graphics clock exceeds the configured ceiling.' };
  const worker = { enabled: false, running: false, available: false, worker_state: 'disabled', reason: 'Worker is disabled.' };
  const localQueue = { checked: true, pending: 1, active: 2, attention: 1, sources: [
    { id: 'video_production', checked: true, pending: 1, active: 0, attention: 0 },
    { id: 'image_production', checked: true, pending: 0, active: 1, attention: 1 },
    { id: 'video_exports', checked: true, pending: 0, active: 0, attention: 0 },
    { id: 'media_prep', checked: true, pending: 0, active: 1, attention: 0 },
  ] };
  const status = { schema_version: 1, backend: { connected: true }, comfyui: { reachable: true, reason: null }, comfyui_queue: { checked: true, running: 0, pending: 0 }, local_queue: localQueue, runtime_guard: guard, dispatch: worker, workflows: [
    { workflow_id: 'minimax_h3_t2v_local_v1', label: 'MiniMax H3 · Text to video', state: 'unavailable', available: false, workflow_available: true, workflow_reason: null, feature_enabled: true, automation_available: false, automation_reason: 'No successful verified T2V render yet.', graph_present: true, models: { present: 4, required: 4 }, nodes: { checked: true, missing_count: 0 }, input_roles: ['prompt'], duration_seconds: { min: 5, max: 10, unit: 'seconds' }, outputs: [{ preset: 0.98, width: 1344, height: 768 }, { preset: 0.4, width: 864, height: 480 }], fixed_parameters: { seed: 1, steps: 20, aspect_ratio: '16:9', reference_count: 0 }, prompt_limit: { max: 6999, unit: 'Unicode code points' } },
    { workflow_id: 'first_last_frame', label: 'First + last frame', category: 'video', state: 'not_integrated', available: false, reason: 'Not integrated in this application yet.', input_roles: ['first_frame', 'last_frame', 'prompt'], prompt_limit: { unit: 'unknown' } },
    { workflow_id: 'reference_to_video', label: 'Reference to video', category: 'video', state: 'not_integrated', available: false, reason: 'Not integrated in this application yet.', input_roles: ['image_references', 'video_references', 'audio_references', 'prompt'], prompt_limit: { unit: 'unknown' } },
    { workflow_id: 'z_image_turbo', label: 'Z-Image Turbo · text to image', category: 'image', state: 'not_integrated', available: false, reason: 'Not integrated in this application yet.', input_roles: ['prompt'], prompt_limit: { unit: 'unknown' } },
    { workflow_id: 'ace_step_music_api', label: 'ACE-Step music', category: 'audio', state: 'not_checked', available: false, reason: 'Model compatibility and runtime safety remain unchecked.', input_roles: ['prompt'], prompt_limit: { unit: 'not applicable', reason: 'Separate inputs.' }, input_limits: { tags: { max: 4000, unit: 'Unicode code points' }, lyrics: { max: 10000, unit: 'Unicode code points' } } },
    { workflow_id: 'noise_cleanup_api', label: 'Noise cleanup', category: 'audio', state: 'not_checked', available: false, reason: 'Runtime compatibility remains unchecked.', input_roles: ['audio'], prompt_limit: { unit: 'unknown' }, input_contract: 'Select a supported cleanup model; adjust aggressiveness.' },
    { workflow_id: 'emotion_edit_api', label: 'Emotion edit', category: 'audio', state: 'not_checked', available: false, reason: 'Runtime compatibility remains unchecked.', input_roles: ['audio', 'transcript', 'emotion'], prompt_limit: { unit: 'unknown' }, input_contract: 'Requires exact transcript text.' },
  ] };
  await page.route('**/api/**', async route => {
    const req = route.request(), url = new URL(req.url()); calls.push(`${req.method()} ${url.pathname}`);
    if (url.pathname === '/api/status') return route.fulfill({ json: status });
    if (url.pathname === '/api/video-summariser/capabilities') return route.fulfill({ json: { gpu_admission: { available: false, checked: true, reason: 'GPU operating limit reached: graphics clock exceeds the configured ceiling.', checked_at: '2026-10-12T12:00:00Z' } } });
    if (url.pathname === '/api/video/runtime') return route.fulfill({ json: guard });
    if (url.pathname === '/api/video/worker') return route.fulfill({ json: worker });
    if (url.pathname === '/api/comfyui/queue') return route.fulfill({ json: { checked: true, running: 0, pending: 0 } });
    if (url.pathname === '/api/jobs/queue') return route.fulfill({ json: localQueue });
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto('/#/video'); await page.evaluate(() => localStorage.clear()); await page.reload();
  await page.getByLabel('Shot prompt').fill('Keep this prompt while opening Status.');
  await page.getByRole('link', { name: 'Status', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Connections & workflows' })).toBeVisible();
  await expect(page.getByText('0 running · 0 pending')).toBeVisible();
  await expect(page.getByText('2 active · 1 pending')).toBeVisible();
  await expect(page.getByText('1 needs attention across 4 job stores.')).toBeVisible();
  await page.getByText('Queue breakdown').click();
  await expect(page.getByText('Video production')).toBeVisible();
  await expect(page.locator('.status-queue-details').getByText('Media Prep')).toBeVisible();
  await expect(page.getByText('Full automationNot ready')).toBeVisible();
  await expect(page.getByText('Full mode is still blocked: No successful verified T2V render yet.')).toBeVisible();
  await expect(page.getByText('tags limit≤ 4,000 Unicode code points')).toBeVisible();
  await expect(page.getByText('lyrics limit≤ 10,000 Unicode code points')).toBeVisible();
  const noiseCard = page.locator('.status-workflow').filter({ hasText: 'Noise cleanup' });
  await expect(noiseCard.getByText('Prompt limit')).toHaveCount(0);
  await expect(noiseCard.getByText(/Unknown/)).toHaveCount(0);
  await expect(page.getByText('Text input limit')).toBeVisible();
  await expect(page.getByText('2,431 MHz')).toHaveCount(0); // value is rendered in the runtime facts with units
  await expect(page.locator('.runtime-values').getByText('2431 MHz')).toBeVisible();
  const clockGuidance = page.getByRole('alert', { name: 'GPU clock limit guidance' });
  await expect(clockGuidance).toBeVisible();
  await expect(clockGuidance.getByText('sudo nvidia-smi -i 0 --lock-gpu-clocks=0,2100', { exact: true })).toBeVisible();
  await page.evaluate(() => { Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => { window.__copiedClock = text; } } }); });
  await clockGuidance.getByRole('button', { name: 'Copy GPU clock command' }).click();
  await expect(clockGuidance.getByRole('status')).toHaveText('Copied');
  expect(await page.evaluate(() => window.__copiedClock)).toBe('sudo nvidia-smi -i 0 --lock-gpu-clocks=0,2100');
  expect(await clockGuidance.evaluate(el => getComputedStyle(el).display)).toBe('grid');
  await clockGuidance.getByText('Command help and undo').click();
  await expect(clockGuidance.getByText(/This page does not run the command/)).toBeVisible();
  await clockGuidance.screenshot({ path: '/tmp/vibe-gpu-clock-message.png' });
  await page.evaluate(() => { navigator.clipboard.writeText = async () => { throw new Error('denied'); }; });
  await clockGuidance.getByRole('button', { name: 'Copy GPU clock command' }).click();
  await expect(clockGuidance.getByRole('status')).toHaveText('Copy failed. Select the command and copy it manually.');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await clockGuidance.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  await page.setViewportSize({ width: 1280, height: 720 });

  expect(calls.some(call => call.startsWith('GET /api/video-summariser/capabilities'))).toBe(false);
  await page.getByRole('button', { name: 'Check runtime readiness' }).click();
  await expect(page.getByRole('status').getByText('Runtime blocked')).toBeVisible();
  await expect(page.getByText('GPU operating limit reached: graphics clock exceeds the configured ceiling.')).toBeVisible();
  await expect(page.getByText('Not integrated in this application yet.').first()).toBeVisible();
  await expect(page.getByText('not integrated', {exact: true})).toHaveCount(3);
  await expect(page.locator('.evidence-facts span').filter({hasText: 'Your acceptance testNot recorded'})).toHaveCount(7);
  await expect(page.locator('.evidence-facts span').filter({hasText: 'Verified renderNot confirmed'})).toHaveCount(7);
  await page.getByRole('navigation', { name: 'Studio navigation' }).getByRole('link', { name: 'Create', exact:true }).click();
  await expect(page.getByLabel('Shot prompt')).toHaveValue('Keep this prompt while opening Status.');
  expect(calls.some(call => call.startsWith('POST '))).toBe(false);
  expect(calls.filter(call => call === 'GET /api/video-summariser/capabilities').length).toBe(1);
  expect(calls.filter(call => call === 'GET /api/status').length).toBeGreaterThanOrEqual(1);
});

test('Status readiness becomes unknown on backend loss and recovers after a successful refresh', async ({ page }) => {
  let online = true;
  const readyGuard = { monitor_available: true, safe_to_submit: true, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100, operating_point: { temperature_c: 48, graphics_clock_mhz: 1900 }, reason: null };
  const readyWorker = { enabled: true, running: true, available: true, worker_state: 'running', reason: null };
  const readyStatus = { schema_version: 1, backend: { connected: true }, comfyui: { reachable: true, reason: null }, comfyui_queue: { checked: true, running: 0, pending: 0 }, local_queue: { checked: true, pending: 0, active: 0, attention: 0, sources: [] }, runtime_guard: readyGuard, dispatch: readyWorker, workflows: [
    { workflow_id: 'minimax_h3_t2v_local_v1', label: 'MiniMax H3 · Text to video', state: 'usable', available: true, workflow_available: true, workflow_reason: null, feature_enabled: true, graph_present: true, models: { present: 4, required: 4 }, nodes: { checked: true, missing_count: 0 }, input_roles: ['prompt'], duration_seconds: { min: 5, max: 10, unit: 'seconds' }, outputs: [{ preset: 0.98, width: 1344, height: 768 }, { preset: 0.4, width: 864, height: 480 }], fixed_parameters: { seed: 1, steps: 20, aspect_ratio: '16:9', reference_count: 0 }, prompt_limit: { max: 6999, unit: 'Unicode code points' } },
  ] };
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/status') return online ? route.fulfill({ json: readyStatus }) : route.fulfill({ status: 503, json: { detail: 'offline' } });
    if (url.pathname === '/api/video/runtime') return route.fulfill({ json: readyGuard });
    if (url.pathname === '/api/video/worker') return route.fulfill({ json: readyWorker });
    if (url.pathname === '/api/comfyui/queue') return route.fulfill({ json: { checked: true, running: 0, pending: 0 } });
    if (url.pathname === '/api/jobs/queue') return route.fulfill({ json: readyStatus.local_queue });
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto('/#/status');
  await expect(page.getByText('usable', { exact: true })).toBeVisible();
  online = false;
  await page.getByRole('button', { name: 'Refresh status' }).click();
  await expect(page.getByText('Showing last successful values as stale. Workflow readiness and GPU safety are unknown until status refresh succeeds.')).toBeVisible();
  await expect(page.getByText('Status stale', { exact: true })).toBeVisible();
  await expect(page.getByText('unavailable', { exact: true })).toBeVisible();
  await expect(page.getByText('safe now', { exact: true })).toHaveCount(0);
  online = true;
  await page.getByRole('button', { name: 'Refresh status' }).click();
  await expect(page.getByText('Backend connected', { exact: true })).toBeVisible();
  await expect(page.getByText('usable', { exact: true })).toBeVisible();
});

test('Status warns when the connected API omits current queue and automation fields', async ({ page }) => {
  const legacyStatus = {
    schema_version: 1,
    backend: { connected: true },
    comfyui: { reachable: true },
    runtime_guard: { monitor_available: true, safe_to_submit: false, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100 },
    dispatch: { enabled: false, running: false, available: false, worker_state: 'disabled', reason: 'Worker is disabled.' },
    workflows: [{
      workflow_id: 'minimax_h3_t2v_local_v1', label: 'MiniMax H3 · Text to video', category: 'video',
      state: 'unavailable', available: false, workflow_available: true, feature_enabled: true,
      input_roles: ['prompt'], prompt_limit: { unit: 'Unicode code points' },
    }],
  };
  await page.route('**/api/**', async route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === '/api/status') return route.fulfill({ json: legacyStatus });
    if (pathname === '/api/video/runtime') return route.fulfill({ json: legacyStatus.runtime_guard });
    if (pathname === '/api/video/worker') return route.fulfill({ json: legacyStatus.dispatch });
    if (pathname === '/api/comfyui/queue') return route.fulfill({ json: { checked: true, running: 0, pending: 0 } });
    return route.fulfill({ status: 404, json: {} });
  });

  await page.goto('/#/status');
  await expect(page.getByRole('alert').getByText('The API response does not include the workflow and queue status fields this UI expects. Readiness may be incomplete; reconcile the API serving this page before relying on it.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Connections & workflows' })).toBeVisible();
  await page.waitForTimeout(5200); // an unavailable local-queue endpoint must not stale healthy GPU/runtime checks
  await expect(page.getByText('Backend connected', { exact: true })).toBeVisible();
  await expect(page.getByText('Showing last successful values as stale. Workflow readiness and GPU safety are unknown until status refresh succeeds.')).toHaveCount(0);
  await expect(page.getByText('Vibe Director jobs', { exact: true })).toBeVisible();
});

test('Status persists simultaneous runs and keeps the saved mode when a busy update is rejected', async ({ page }) => {
  let parallel = false, busy = false;
  const updates = [];
  const guard = { monitor_available:true, safe_to_submit:true, temperature_cutoff_c:83, graphics_clock_ceiling_mhz:2100 };
  const dispatch = { enabled:false, running:false, available:false, worker_state:'stopped' };
  const queue = { checked:true, running:0, pending:0 };
  const localQueue = { checked:true, active:0, pending:0, attention:0, sources:[] };
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/status') return route.fulfill({json:{schema_version:1, backend:{connected:true}, comfyui:{reachable:true}, comfyui_queue:queue, local_queue:localQueue, runtime_guard:guard, dispatch, workflows:[], workload_policy:{allow_simultaneous_runs:parallel}}});
    if (url.pathname === '/api/runtime/workload-policy') {
      updates.push(route.request().postDataJSON());
      if (busy) return route.fulfill({status:409,json:{error:{message:'Wait for active workloads to finish before changing simultaneous runs.'}}});
      parallel = route.request().postDataJSON().allow_simultaneous_runs;
      return route.fulfill({json:{allow_simultaneous_runs:parallel}});
    }
    if (url.pathname === '/api/video/runtime') return route.fulfill({json:guard});
    if (url.pathname === '/api/video/worker') return route.fulfill({json:dispatch});
    if (url.pathname === '/api/comfyui/queue') return route.fulfill({json:queue});
    if (url.pathname === '/api/jobs/queue') return route.fulfill({json:localQueue});
    return route.fulfill({status:404,json:{}});
  });
  await page.goto('/#/status');
  const toggle = page.getByRole('switch', {name:'Allow simultaneous Vibe Director workloads'});
  await expect(toggle).not.toBeChecked();
  await toggle.click();
  await expect(toggle).toBeChecked();
  await page.reload();
  await expect(toggle).toBeChecked();
  busy = true;
  await toggle.click();
  await expect(page.getByRole('alert').filter({hasText:'Wait for active workloads'})).toBeVisible();
  await expect(toggle).toBeChecked();
  busy = false;
  await toggle.click();
  await expect(toggle).not.toBeChecked();
  expect(updates.map(value => value.allow_simultaneous_runs)).toEqual([true,false,false]);
});

test('Status shows recoverable unknown GPU termination and clears it only after confirmation', async ({ page }) => {
  let held = true;
  const guard = { monitor_available:true, safe_to_submit:true, temperature_cutoff_c:83, graphics_clock_ceiling_mhz:2100 };
  const dispatch = { enabled:false, running:false, available:false, worker_state:'stopped' };
  const queue = { checked:true, running:0, pending:0 };
  const localQueue = { checked:true, active:0, pending:0, attention:0, sources:[] };
  await page.route('**/api/**', async route => {
    const req = route.request(), url = new URL(req.url());
    if (url.pathname === '/api/status') return route.fulfill({json:{schema_version:1, backend:{connected:true}, comfyui:{reachable:true}, comfyui_queue:queue, local_queue:localQueue, runtime_guard:guard, dispatch, workflows:[], workload_policy:{allow_simultaneous_runs:false}, gpu_safety_hold:held ? {termination_unknown:true, reason:'No adapter cancellation handler was registered.', recorded_at:'2026-10-13T08:00:00Z', workload_id:'pid:123'} : {termination_unknown:false}}});
    if (url.pathname === '/api/runtime/safety-hold' && req.method() === 'POST') {
      expect(req.postDataJSON()).toEqual({verified_idle:true});
      held = false;
      return route.fulfill({json:{cleared:true}});
    }
    if (url.pathname === '/api/video/runtime') return route.fulfill({json:guard});
    if (url.pathname === '/api/video/worker') return route.fulfill({json:dispatch});
    if (url.pathname === '/api/comfyui/queue') return route.fulfill({json:queue});
    if (url.pathname === '/api/jobs/queue') return route.fulfill({json:localQueue});
    return route.fulfill({status:404,json:{}});
  });
  page.on('dialog', dialog => dialog.accept());
  await page.goto('/#/status');
  await expect(page.getByRole('heading', {name:'GPU workload stopped with unknown termination'})).toBeVisible();
  await expect(page.getByText('No adapter cancellation handler was registered.')).toBeVisible();
  await expect(page.getByText(/New Vibe Director GPU work is held/)).toBeVisible();
  await page.getByRole('button', {name:'I verified services are idle — clear hold'}).click();
  await expect(page.getByRole('heading', {name:'GPU workload stopped with unknown termination'})).toHaveCount(0);
  expect(held).toBe(false);
});
