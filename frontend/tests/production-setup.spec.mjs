import { test, expect } from '@playwright/test';

test('setup follows the requested workspace and ignores a late previous-workspace response', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  const workspaceRequests = [];
  const screenplayRequests = [];
  await page.route('**/api/images/workflows', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/story/workspaces/**', async route => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/').filter(Boolean);
    const workspaceId = parts[3];
    const action = parts.slice(4).join('/');
    if (!action && route.request().method() === 'GET') {
      workspaceRequests.push(workspaceId);
      if (workspaceId === 'workspace-a') await new Promise(resolve => setTimeout(resolve, 350));
      return route.fulfill({ json: {
        workspace_id: workspaceId, title: `Story ${workspaceId}`, current_revision_id: `source-${workspaceId}`,
      } });
    }
    if (action === 'screenplay') {
      screenplayRequests.push(workspaceId);
      return route.fulfill({ json: {
        workspace_id: workspaceId, screenplay_revision_id: `screenplay-${workspaceId}`,
        source_revision_id: `source-${workspaceId}`, accepted: true, screenplay: { scenes: [] },
      } });
    }
    if (action === 'production-setup') return route.fulfill({ json: {
      workspace_id: workspaceId, screenplay_revision_id: `screenplay-${workspaceId}`, setup: null, updated_at: null,
    } });
    return route.fulfill({ status: 404, json: { error: { message: `Unexpected ${action}` } } });
  });

  await page.goto('/#/setup?workspace_id=workspace-a');
  await page.waitForRequest(request => request.url().includes('/api/story/workspaces/workspace-a'));
  await page.evaluate(() => { window.location.hash = '#/setup?workspace_id=workspace-b'; });
  await expect(page.getByText('Accepted screenplay · screenplay-workspace-b')).toBeVisible();
  await page.waitForTimeout(400);

  expect(workspaceRequests).toContain('workspace-a');
  expect(workspaceRequests.filter(id => id === 'workspace-b')).toHaveLength(1);
  expect(screenplayRequests).toEqual(['workspace-b']);
  await expect(page.getByText('Accepted screenplay · screenplay-workspace-b')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save setup' })).toBeEnabled();
});

test('a late save from the previous workspace cannot block or unlock the current workspace', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  let startASave;
  let releaseASave;
  let startBSave;
  let releaseBSave;
  let finishASave;
  let finishBSave;
  const aSaveStarted = new Promise(resolve => { startASave = resolve; });
  const aSaveFinished = new Promise(resolve => { finishASave = resolve; });
  const bSaveStarted = new Promise(resolve => { startBSave = resolve; });
  const bSaveFinished = new Promise(resolve => { finishBSave = resolve; });
  const aSaveGate = new Promise(resolve => { releaseASave = resolve; });
  const bSaveGate = new Promise(resolve => { releaseBSave = resolve; });
  await page.route('**/api/images/workflows', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/story/workspaces/**', async route => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/').filter(Boolean);
    const workspaceId = parts[3];
    const action = parts.slice(4).join('/');
    if (!action) return route.fulfill({ json: { workspace_id: workspaceId, title: `Story ${workspaceId}`, current_revision_id: `source-${workspaceId}` } });
    if (action === 'screenplay') return route.fulfill({ json: {
      workspace_id: workspaceId, screenplay_revision_id: `screenplay-${workspaceId}`,
      source_revision_id: `source-${workspaceId}`, accepted: true, screenplay: { scenes: [] },
    } });
    if (action === 'production-setup') {
      if (route.request().method() === 'PUT') {
        if (workspaceId === 'workspace-a') { startASave(); await aSaveGate; finishASave(); }
        else { startBSave(); await bSaveGate; finishBSave(); }
        return route.fulfill({ json: {
          workspace_id: workspaceId, screenplay_revision_id: `screenplay-${workspaceId}`,
          setup: route.request().postDataJSON().setup, updated_at: '2026-10-13T10:00:00Z',
        } });
      }
      return route.fulfill({ json: { workspace_id: workspaceId, screenplay_revision_id: `screenplay-${workspaceId}`, setup: null, updated_at: null } });
    }
    return route.fulfill({ status: 404, json: { error: { message: `Unexpected ${action}` } } });
  });

  await page.goto('/#/setup?workspace_id=workspace-a');
  const stepA = page.getByLabel('Character image generation');
  await stepA.check();
  await page.getByRole('button', { name: 'Save setup' }).click();
  await aSaveStarted;
  await page.evaluate(() => { window.location.hash = '#/setup?workspace_id=workspace-b'; });
  await expect(page.getByText('Accepted screenplay · screenplay-workspace-b')).toBeVisible();

  const stepB = page.getByLabel('Character image generation');
  await expect(stepB).toBeEnabled();
  await stepB.check();
  await page.getByRole('button', { name: 'Save setup' }).click();
  await bSaveStarted;
  releaseASave();
  await aSaveFinished;
  await expect(stepB).toBeDisabled();
  releaseBSave();
  await bSaveFinished;
  await expect(page.getByRole('status')).toContainText('Setup saved for this accepted screenplay revision');
  await expect(stepB).toBeEnabled();
});

test('setup modes, assisted-step selection, parameters and saved revision reload', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  let persisted = null;
  let writes = [];
  await page.route('**/api/images/workflows', route => route.fulfill({ json: { workflows: [
    { workflow_id: 'qwen_image_2512', label: 'Qwen Image 2512 · text to image', available: true, disabled_reason: null, defaults: { width: 1664, height: 928, steps: 50, cfg: 4 } },
    { workflow_id: 'z_image_turbo', label: 'Z-Image Turbo · text to image', available: true, disabled_reason: null, defaults: { width: 1280, height: 720, steps: 8, cfg: 1 } },
    { workflow_id: 'qwen_image_edit_2511', label: 'Qwen Image Edit 2511 · image edit (4-step Lightning)', available: true, disabled_reason: null, defaults: { width: 1024, height: 1024, steps: 4, cfg: 1 } },
  ] } }));
  await page.route('**/api/story/workspaces/workspace-a', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', title: 'Test story', current_revision_id: 'source-a',
    current_revision: { revision_id: 'source-a', source_text: 'A short story.' },
  } }));
  await page.route('**/api/story/workspaces/workspace-a/screenplay?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', source_revision_id: 'source-a',
    accepted: true, screenplay: { scenes: [] },
  } }));
  await page.route('**/api/story/workspaces/workspace-a/production-setup**', async route => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      writes.push(body);
      persisted = { workspace_id: 'workspace-a', screenplay_revision_id: body.screenplay_revision_id,
        setup: body.setup, updated_at: '2026-10-10T12:00:00Z' };
      return route.fulfill({ status: 200, json: persisted });
    }
    return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', setup: persisted?.setup ?? null, updated_at: persisted?.updated_at ?? null } });
  });

  await page.goto('/#/setup');
  await expect(page.getByRole('heading', { name: 'Automation & Parameters' })).toBeVisible();
  await expect(page.getByText('0 of 5 steps automated')).toBeVisible();
  const steps = ['Character image generation', 'Character-to-audio selection', 'World-building image generation', 'Frame image generation', 'Video generation'];
  for (const step of steps) await expect(page.getByLabel(step)).not.toBeChecked();
  await page.getByLabel(steps[0]).check();
  await expect(page.getByLabel('character_images workflow')).toHaveValue('z_image_turbo');
  await expect(page.getByLabel('character_images workflow').locator('option[value="qwen_image_edit_2511"]')).toHaveCount(0);
  await page.getByLabel('character_images width').fill('1024');
  await expect(page.getByText('1 of 5 steps automated')).toBeVisible();
  for (const step of steps.slice(1)) await page.getByLabel(step).check();
  await expect(page.getByText('5 of 5 steps automated')).toBeVisible();
  await expect(page.getByLabel('frame_images workflow').locator('option[value="qwen_image_edit_2511"]')).toHaveCount(1);
  await page.getByLabel('frame_images workflow').selectOption('qwen_image_edit_2511');
  await expect(page.getByLabel('world_images world directions')).toHaveValue('4');
  await page.getByLabel('world_images world directions').selectOption('8');
  await page.getByLabel('Automated video workflow').selectOption('minimax_h3_fl2va_first_last_v1');

  await page.getByLabel('Director chooses each clip within the shared 5–10 sec range').check();
  await page.getByLabel('Shortest duration').selectOption('6');
  await page.getByLabel('Longest duration').selectOption('9');
  await page.getByLabel('Video quality').selectOption('standard');
  await page.getByRole('radio', { name: 'Fully automated' }).click();
  await expect(page.getByText('Image-free route')).toBeVisible();
  await expect(page.getByLabel(steps[0])).toHaveCount(0);
  await expect(page.getByText('Skip image preparation.', { exact: false })).toBeVisible();
  await page.getByRole('radio', { name: 'Assisted manual' }).click();
  await expect(page.getByText('5 of 5 steps automated')).toBeVisible();
  await expect(page.getByLabel('world_images world directions')).toHaveValue('8');

  for (const step of steps) await page.getByLabel(step).check();
  await page.getByLabel('Automated video workflow').selectOption('minimax_h3_r2v_dynamic_v1');
  await page.getByLabel('character_images width').fill('1024');
  await page.getByLabel('Fixed length').check();
  await page.getByLabel('Fixed duration').selectOption('7');
  await page.getByLabel('Video quality').selectOption('high');
  await page.getByRole('button', { name: 'Save setup' }).click();
  await expect(page.getByRole('status')).toContainText('Setup saved for this accepted screenplay revision');
  expect(writes).toHaveLength(1);
  expect(writes[0]).toEqual({ screenplay_revision_id: 'screenplay-a', setup: {
    mode: 'assisted_manual', automate_steps: { character_images: true, character_voice: true, world_images: true, frame_images: true, video: true },
    video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 7 },
    video_workflow_id: 'minimax_h3_r2v_dynamic_v1',
    image_stage_settings: {
      character_images: { workflow_id: 'z_image_turbo', width: 1024, height: 720, steps: 8, cfg: 1 },
      world_images: { workflow_id: 'z_image_turbo', width: 1280, height: 720, steps: 8, cfg: 1, world_view_count: 8 },
      frame_images: { workflow_id: 'qwen_image_edit_2511', width: 1024, height: 1024, steps: 4, cfg: 1 },
    },
  } });

  await page.reload();
  await expect(page.getByLabel('Video quality')).toHaveValue('high');
  await expect(page.getByLabel('character_images width')).toHaveValue('1024');
  await expect(page.getByLabel('world_images world directions')).toHaveValue('8');
  await expect(page.getByLabel('frame_images workflow')).toHaveValue('qwen_image_edit_2511');
  await expect(page.getByLabel('Fixed duration')).toHaveValue('7');
  await expect(page.getByText('5 of 5 steps automated')).toBeVisible();
  for (const step of steps) await expect(page.getByLabel(step)).toBeChecked();
  await expect(page.getByLabel('Automated video workflow')).toHaveValue('minimax_h3_r2v_dynamic_v1');
  await expect(page.getByRole('button', { name: 'Setup saved' })).toBeDisabled();
});

test('saving locks edits and a failed save keeps the editable draft visible', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  await page.route('**/api/story/workspaces/workspace-a', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', title: 'Test story', current_revision_id: 'source-a',
  } }));
  await page.route('**/api/story/workspaces/workspace-a/screenplay?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', accepted: true,
  } }));
  await page.route('**/api/story/workspaces/workspace-a/production-setup**', async route => {
    if (route.request().method() === 'PUT') {
      await new Promise(resolve => setTimeout(resolve, 250));
      return route.fulfill({ status: 503, json: { error: { message: 'Save temporarily unavailable.' } } });
    }
    return route.fulfill({ json: { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', setup: null, updated_at: null } });
  });

  await page.goto('/#/setup');
  const characterImages = page.getByLabel('Character image generation');
  await characterImages.check();
  const save = page.getByRole('button', { name: 'Save setup' });
  await save.click();
  await expect(characterImages).toBeDisabled();
  await expect(page.getByLabel('Video quality')).toBeDisabled();
  await expect(page.getByRole('radio', { name: 'Fully automated' })).toBeDisabled();
  await expect(page.getByRole('alert')).toContainText('Save temporarily unavailable.');
  await expect(characterImages).toBeVisible();
  await expect(characterImages).toBeChecked();
  await expect(characterImages).toBeEnabled();
  await expect(page.getByText('1 of 5 steps automated')).toBeVisible();
});

test('assisted setup continues into stage-local character image preparation', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  let saved = null;
  await page.route('**/api/images/workflows', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/story/workspaces/workspace-a', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', title: 'Test story', current_revision_id: 'source-a',
  } }));
  await page.route('**/api/story/workspaces/workspace-a/screenplay?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', accepted: true,
  } }));
  await page.route('**/api/story/workspaces/workspace-a/production-setup**', async route => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      saved = { workspace_id: 'workspace-a', screenplay_revision_id: body.screenplay_revision_id, setup: body.setup, setup_hash: 'hash-a' };
      return route.fulfill({ json: saved });
    }
    return route.fulfill({ json: saved || { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', setup: null } });
  });

  await page.goto('/#/setup');
  const next = page.getByRole('link', { name: 'Continue to Characters & Voices' });
  await expect(next).toHaveAttribute('aria-disabled', 'true');
  await page.getByRole('button', { name: 'Save setup' }).click();
  await expect(page.getByRole('status')).toContainText('Setup saved for this accepted screenplay revision');
  await expect(next).toHaveAttribute('href', '#/assets?step=character_images&workspace_id=workspace-a');
  await expect(next).toHaveAttribute('aria-disabled', 'false');
});

test('Assisted automatic R2V inherits an explicitly selected run-level style video', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  let saved = null;
  let write = null;
  await page.route('**/api/images/workflows', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/story/workspaces/workspace-a', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', title: 'Test story', current_revision_id: 'source-a',
    style_selection: { directing_style_id: 'cinematic' },
  } }));
  await page.route('**/api/story/workspaces/workspace-a/screenplay?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', accepted: true,
  } }));
  await page.route('**/api/media/workspace-a/assets?kind=video**', route => route.fulfill({ json: { total: 1, assets: [{
    asset_id: 'pa-0123456789abcdef', workspace_id: 'workspace-a', kind: 'video', roles: ['style_reference'],
    filename: 'Rainy street.mp4', media_type: 'video/mp4', sha256: 'a'.repeat(64), size_bytes: 100,
    content_url: '/media/test.mp4', recommended: true, recommendation_source: 'production_style',
  }] } }));
  await page.route('**/api/story/workspaces/workspace-a/production-setup**', async route => {
    if (route.request().method() === 'PUT') {
      write = route.request().postDataJSON();
      saved = { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', setup: write.setup };
      return route.fulfill({ status: 200, json: saved });
    }
    return route.fulfill({ json: saved || { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', setup: null } });
  });

  await page.goto('/#/setup');
  await page.getByLabel('Video generation').check();
  await page.getByLabel('Automated video workflow').selectOption('minimax_h3_r2v_dynamic_v1');
  await expect(page.getByRole('heading', { name: /Optional run-level style videos/ })).toBeVisible();
  await page.getByText('Rainy street.mp4', { exact: true }).click();
  await expect(page.getByLabel('Automated video workflow').locator('option[value="minimax_h3_fl2va_first_last_v1"]')).toHaveAttribute('disabled', '');
  await expect(page.getByLabel('Intent for Rainy street.mp4')).toHaveValue('Use Rainy street.mp4 as a visual style reference.');
  await page.getByRole('button', { name: 'Save setup' }).click();
  await expect(page.getByRole('status')).toContainText('Setup saved for this accepted screenplay revision');
  expect(write.setup.video_workflow_id).toBe('minimax_h3_r2v_dynamic_v1');
  expect(write.setup.style_video_references).toEqual([{ asset_id: 'pa-0123456789abcdef', sha256: 'a'.repeat(64), intent: 'Use Rainy street.mp4 as a visual style reference.' }]);
});

test('Full mode saves and restores selected style videos before continuing to Video Create', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'workspace-a'));
  let saved = null;
  let write = null;
  await page.route('**/api/images/workflows', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/story/workspaces/workspace-a', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', title: 'Test story', current_revision_id: 'source-a',
    style_selection: { directing_style_id: 'cinematic' },
  } }));
  await page.route('**/api/story/workspaces/workspace-a/screenplay?**', route => route.fulfill({ json: {
    workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', accepted: true,
  } }));
  await page.route('**/api/media/workspace-a/assets?kind=video**', route => route.fulfill({ json: { total: 1, assets: [{
    asset_id: 'pa-0123456789abcdef', workspace_id: 'workspace-a', kind: 'video', roles: ['style_reference'],
    filename: 'Rainy street.mp4', media_type: 'video/mp4', sha256: 'a'.repeat(64), size_bytes: 100,
    content_url: '/media/test.mp4', recommended: true, recommendation_source: 'production_style',
  }] } }));
  await page.route('**/api/story/workspaces/workspace-a/production-setup**', async route => {
    if (route.request().method() === 'PUT') {
      write = route.request().postDataJSON();
      saved = { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', setup: write.setup };
      return route.fulfill({ status: 200, json: saved });
    }
    return route.fulfill({ json: saved || { workspace_id: 'workspace-a', screenplay_revision_id: 'screenplay-a', setup: null } });
  });

  await page.goto('/#/setup');
  await page.getByRole('radio', { name: 'Fully automated' }).click();
  await expect(page.getByRole('heading', { name: /Optional style videos/ })).toBeVisible();
  await page.getByText('Rainy street.mp4', { exact: true }).click();
  await page.getByRole('button', { name: 'Save setup' }).click();
  await expect(page.getByRole('status')).toContainText('Setup saved for this accepted screenplay revision');
  expect(write.setup.mode).toBe('fully_automated');
  expect(write.setup.style_video_references).toEqual([{ asset_id: 'pa-0123456789abcdef', sha256: 'a'.repeat(64), intent: 'Use Rainy street.mp4 as a visual style reference.' }]);
  await expect(page.getByRole('link', { name: 'Continue to Video Create' })).toHaveAttribute('aria-disabled', 'false');

  await page.reload();
  await expect(page.getByRole('checkbox', { name: /Rainy street\.mp4 Pinned production-style video/ })).toBeChecked();
  await expect(page.getByLabel('Intent for Rainy street.mp4')).toHaveValue('Use Rainy street.mp4 as a visual style reference.');
  await expect(page.getByRole('link', { name: 'Continue to Video Create' })).toHaveAttribute('href', '#/video?workspace_id=workspace-a');
});
