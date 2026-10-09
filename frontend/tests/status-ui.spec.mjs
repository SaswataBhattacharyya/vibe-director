import { test, expect } from '@playwright/test';

test('Status is read-only, shows catalog and runtime, and preserves the video draft', async ({ page }) => {
  const calls = [];
  const guard = { monitor_available: true, safe_to_submit: false, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100, operating_point: { temperature_c: 48, graphics_clock_mhz: 2431 }, reason: 'Graphics clock exceeds the configured ceiling.' };
  const worker = { enabled: false, running: false, available: false, worker_state: 'disabled', reason: 'Worker is disabled.' };
  const status = { schema_version: 1, backend: { connected: true }, comfyui: { reachable: true, reason: null }, runtime_guard: guard, dispatch: worker, workflows: [
    { workflow_id: 'minimax_h3_t2v_local_v1', label: 'MiniMax H3 · Text to video', state: 'unavailable', available: false, workflow_available: true, workflow_reason: null, feature_enabled: true, graph_present: true, models: { present: 4, required: 4 }, nodes: { checked: true, missing_count: 0 }, input_roles: ['prompt'], duration_seconds: { min: 5, max: 10, unit: 'seconds' }, outputs: [{ preset: 0.98, width: 1344, height: 768 }, { preset: 0.4, width: 864, height: 480 }], fixed_parameters: { seed: 1, steps: 20, aspect_ratio: '16:9', reference_count: 0 }, prompt_limit: { max: 6999, unit: 'Unicode code points' } },
    { workflow_id: 'first_last_frame', label: 'First + last frame', category: 'video', state: 'not_integrated', available: false, reason: 'Not integrated in this application yet.', input_roles: ['first_frame', 'last_frame', 'prompt'], prompt_limit: { unit: 'unknown' } },
    { workflow_id: 'reference_to_video', label: 'Reference to video', category: 'video', state: 'not_integrated', available: false, reason: 'Not integrated in this application yet.', input_roles: ['image_references', 'video_references', 'audio_references', 'prompt'], prompt_limit: { unit: 'unknown' } },
    { workflow_id: 'z_image_turbo', label: 'Z-Image Turbo · text to image', category: 'image', state: 'not_integrated', available: false, reason: 'Not integrated in this application yet.', input_roles: ['prompt'], prompt_limit: { unit: 'unknown' } },
  ] };
  await page.route('**/api/**', async route => {
    const req = route.request(), url = new URL(req.url()); calls.push(`${req.method()} ${url.pathname}`);
    if (url.pathname === '/api/status') return route.fulfill({ json: status });
    if (url.pathname === '/api/video/runtime') return route.fulfill({ json: guard });
    if (url.pathname === '/api/video/worker') return route.fulfill({ json: worker });
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto('/'); await page.evaluate(() => localStorage.clear()); await page.reload();
  await page.getByLabel('Shot prompt').fill('Keep this prompt while opening Status.');
  await page.getByRole('link', { name: 'Status' }).click();
  await expect(page.getByRole('heading', { name: 'Connections & workflows' })).toBeVisible();
  await expect(page.getByText('2,431 MHz')).toHaveCount(0); // value is rendered in the runtime facts with units
  await expect(page.getByText('2431 MHz')).toBeVisible();
  await expect(page.getByText('Not integrated in this application yet.').first()).toBeVisible();
  await page.getByRole('link', { name: 'Video' }).click();
  await expect(page.getByLabel('Shot prompt')).toHaveValue('Keep this prompt while opening Status.');
  expect(calls.some(call => call.startsWith('POST '))).toBe(false);
  expect(calls.filter(call => call === 'GET /api/status').length).toBeGreaterThanOrEqual(1);
});

test('Status readiness becomes unknown on backend loss and recovers after a successful refresh', async ({ page }) => {
  let online = true;
  const readyGuard = { monitor_available: true, safe_to_submit: true, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100, operating_point: { temperature_c: 48, graphics_clock_mhz: 1900 }, reason: null };
  const readyWorker = { enabled: true, running: true, available: true, worker_state: 'running', reason: null };
  const readyStatus = { schema_version: 1, backend: { connected: true }, comfyui: { reachable: true, reason: null }, runtime_guard: readyGuard, dispatch: readyWorker, workflows: [
    { workflow_id: 'minimax_h3_t2v_local_v1', label: 'MiniMax H3 · Text to video', state: 'usable', available: true, workflow_available: true, workflow_reason: null, feature_enabled: true, graph_present: true, models: { present: 4, required: 4 }, nodes: { checked: true, missing_count: 0 }, input_roles: ['prompt'], duration_seconds: { min: 5, max: 10, unit: 'seconds' }, outputs: [{ preset: 0.98, width: 1344, height: 768 }, { preset: 0.4, width: 864, height: 480 }], fixed_parameters: { seed: 1, steps: 20, aspect_ratio: '16:9', reference_count: 0 }, prompt_limit: { max: 6999, unit: 'Unicode code points' } },
  ] };
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/status') return online ? route.fulfill({ json: readyStatus }) : route.fulfill({ status: 503, json: { detail: 'offline' } });
    if (url.pathname === '/api/video/runtime') return route.fulfill({ json: readyGuard });
    if (url.pathname === '/api/video/worker') return route.fulfill({ json: readyWorker });
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
