import { test, expect } from '@playwright/test';

const capability = (ready) => ({
  available: ready,
  disabled_reason: ready ? null : 'Legacy T2V workflow is not verified.',
  runtime_guard: { monitor_available: true, safe_to_submit: ready, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100, operating_point: { temperature_c: 48, graphics_clock_mhz: 1900 }, reason: ready ? 'Runtime is inside the safety limits.' : 'GPU clock is over the safety limit.' },
  dispatch: { enabled: ready, running: ready, available: ready, worker_state: ready ? 'running' : 'disabled', reason: ready ? null : 'Worker is disabled.' },
});

test('mocked T2V flow gates readiness, reviews output, accepts, and prepares a non-submitting retake', async ({ page }) => {
  let readinessChecks = 0;
  let jobPosts = 0;
  let job = null;
  const calls = [];
  await page.route('**/api/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    calls.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/api/video/capabilities') return route.fulfill({ json: capability(++readinessChecks > 1) });
    if (url.pathname === '/api/video/validations') return route.fulfill({ json: { valid: true, request_hash: 'hash', normalized_request: request.postDataJSON().request, compiled_preview: {} } });
    if (url.pathname === '/api/video/jobs' && request.method() === 'POST') {
      jobPosts++;
      const body = request.postDataJSON();
      job = { job_id: 'job-1', workspace_id: body.workspace_id, clip_id: body.clip_id, status: 'needs_review', request: body.request, outputs: [{ asset_id: 'asset-1', kind: 'video', playback_url: '/api/video/assets/asset-1/playback' }], created_at: 'now', updated_at: 'now', attempt: 1 };
      return route.fulfill({ json: job });
    }
    if (url.pathname === '/api/video/jobs/job-1/accept') { job = { ...job, status: 'accepted' }; return route.fulfill({ json: job }); }
    if (url.pathname === '/api/video/retakes/job-1') return route.fulfill({ json: { source_job_id: 'job-1', request: job.request, keep_original: request.postDataJSON().keep_original, submission_created: false, referenced_assets_deletion: 'never_by_retake' } });
    if (url.pathname === '/api/video/assets/asset-1/playback') return route.fulfill({ status: 200, contentType: 'video/mp4', body: '' });
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });

  await page.goto('/#/video');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await expect(page.getByText('Legacy T2V workflow is not verified.', {exact: true})).toBeVisible();
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeDisabled();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByLabel('Shot prompt').fill('A slow dolly toward a rain-streaked window.');
  await expect(page.getByRole('button', { name: /Generate video/ })).toBeEnabled();
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByText('needs review', {exact:true})).toBeVisible();
  await expect(page.locator('video[aria-label="Generated video"]')).toHaveAttribute('src', /api\/video\/assets/);
  expect(jobPosts).toBe(1);
  await page.getByRole('button', { name: 'Accept take' }).click();
  await expect(page.getByText('accepted', {exact:true})).toBeVisible();
  await page.getByRole('button', { name: 'Retake' }).click();
  await expect(page.getByRole('heading', { name: 'Prepare a retake' })).toBeVisible();
  await expect(page.getByText(/does not start a job or delete anything/)).toBeVisible();
  await page.getByRole('button', { name: /Return to editor/ }).click();
  await expect(page.getByLabel('Shot prompt')).toHaveValue('A slow dolly toward a rain-streaked window.');
  expect(jobPosts).toBe(1);
  expect(calls.some(call => call === 'POST /api/video/retakes/job-1')).toBeTruthy();
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
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.goto('/#/video'); await page.evaluate(() => localStorage.clear()); await page.reload();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByLabel('Shot prompt').fill('Frozen original prompt.');
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByRole('button', { name: 'Recover saved attempt' })).toBeVisible();
  const keyBeforeReload = await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-draft-v1')).pendingKey);
  expect(keyBeforeReload).toBeTruthy();
  await page.reload();
  await expect(page.getByText('Recovered the saved job by its idempotency key. No new job was submitted.', { exact: true })).toBeVisible();
  await expect(page.getByText('Rendering your shot')).toBeVisible();
  expect(jobPosts).toBe(1);
  expect(calls.filter(call => call.startsWith('GET /api/video/jobs/by-idempotency/')).length).toBeGreaterThanOrEqual(1);
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
    return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked API request' } });
  });
  await page.goto('/#/video');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: 'Check readiness' }).click();
  await page.getByLabel('Shot prompt').fill('Keep this rendering job while I inspect status.');
  await page.getByRole('button', { name: /Generate video/ }).click();
  await expect(page.getByText('Rendering your shot')).toBeVisible();
  await page.goto('/#/status');
  await expect(page.getByRole('heading', { name: 'Connections & workflows' })).toBeVisible();
  await page.goto('/#/take');
  await expect(page.getByText('Rendering your shot')).toBeVisible();
  await expect(page.getByText('job-stays-mounted')).toBeVisible();
  expect(jobPosts).toBe(1);
});
