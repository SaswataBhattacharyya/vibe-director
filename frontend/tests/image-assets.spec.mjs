import {mockProject} from './fixtures/project.mjs';
import { test, expect } from '@playwright/test';

test.beforeEach(async ({page}) => {
  page.on('pageerror',error=>{throw error;});
  await page.route('**/api/images/prompts/prepare', async r=>r.fulfill({json:{workflow_id:'z_image_turbo',prompt:r.request().postDataJSON().prompt||'A rainy station platform',knowledge_ref:{knowledge_id:'fixture',guidance_version:1,workflow_sha256:'a'.repeat(64)},sources:[]}}));
  await page.route('**/api/story/workspaces/*/assisted-stage-skips**', r => r.fulfill({json:{skipped:[]}}));
});

test('image generation stays available with low reported memory when runtime checks pass', async ({ page }) => {
  let jobs = 0;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'workspace-image', role: 'character_master', workflowId: 'z_image_turbo',
    prompt: 'A lighthouse in fog.', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => {
    return route.fulfill({ json: { workflows: [{ workflow_id: 'z_image_turbo', label: 'Z-Image Turbo',
      version: '1', available: true, defaults: { width: 1280, height: 720, steps: 8, cfg: 1 } }],
      generation_policy: {}, gpu_admission: { available: true, checked: true, free_gib: 5.1, checked_at: 'now', reason: null },
    } });
  });
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true, running: true } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [{ workspace_id: 'workspace-image', title: 'Standalone' }], total: 1 } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await page.route('**/api/images/prompts/prepare', route => route.fulfill({ json: { workflow_id: 'z_image_turbo',
    prompt: 'A lighthouse in fog.', knowledge_ref: { knowledge_id: 'k', guidance_version: 1, workflow_sha256: 'a' }, sources: [] } }));
  await page.route('**/api/images/jobs', async route => { jobs += 1; return route.fulfill({ status: 202, json: { batch_id: 'unexpected', jobs: [] } }); });

  await imageProject(page); await page.goto('/#/assets');
  await expect(page.getByText(/GPU ready · 5\.1 GiB reported free \(informational\)/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Generate four' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Prepare prompt' })).toBeEnabled();
  expect(jobs).toBe(0);
});

test('image production routes select the correct page and constrain the image role', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({ workspaceId: '', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42 })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: false } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: false } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.route('**/api/media/**/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await imageProject(page); await page.goto('/#/characters');
  await expect(page.getByRole('heading', { name: 'Characters & voices', exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Image generation workspace' })).toHaveCount(0);
  await expect(page.getByRole('textbox', { name: 'Image prompt' })).toBeVisible();
  await imageProject(page); await page.goto('/#/worlds');
  await expect(page.getByRole('heading', { name: 'Scene Backgrounds', exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Image generation workspace' })).toHaveCount(0);
  await expect(page.getByText('Current project · change with New project or Load project above')).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Asset role' })).toHaveCount(0);
  await imageProject(page); await page.goto('/#/frames');
  await expect(page.getByRole('heading', { name: 'First & last frames' })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Frame role' })).toBeVisible();
  await expect(page.getByRole('option', { name: 'Character image' })).toHaveCount(0);
});

test('standalone image prompts support reviewed selection micro-edits', async ({ page }) => {
  let editRequest;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'workspace-image', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: false } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: false } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [{ workspace_id: 'workspace-image', title: 'Standalone workspace' }], total: 1 } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await page.route('**/api/story/workspaces/workspace-image/field-edit-proposals', async route => {
    editRequest = route.request().postDataJSON();
    return route.fulfill({ json: {
      proposal_id: 'proposal-1', revision_id: editRequest.revision_id, field_key: editRequest.field_key,
      expected_text: editRequest.expected_text, start_codepoint: editRequest.start_codepoint,
      end_codepoint: editRequest.end_codepoint, replacement: 'misty', explanation: 'Adjusted the mood.',
    } });
  });

  await imageProject(page); await page.goto('/#/assets');
  await expect(page.getByRole('combobox', { name: 'Image generation workspace' })).toHaveCount(0);
  const prompt = page.getByRole('textbox', { name: 'Image prompt' });
  await prompt.fill('A foggy house at dawn.');
  await prompt.evaluate(element => {
    element.focus();
    element.setSelectionRange(2, 7);
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
  });
  await expect(page.getByRole('region', { name: 'Edit selected text in Image prompt' })).toBeVisible();
  await page.getByRole('textbox', { name: 'Instruction for Image prompt' }).fill('Make the atmosphere misty.');
  await page.getByRole('button', { name: 'Suggest edit' }).click();
  await expect(page.getByText('Adjusted the mood.')).toBeVisible();
  await page.getByRole('button', { name: 'Apply to draft' }).click();
  await expect(prompt).toHaveValue('A misty house at dawn.');
  expect(editRequest).toMatchObject({ surface: 'prompt', expected_text: 'foggy', instruction: 'Make the atmosphere misty.' });
  expect(editRequest.revision_id).toContain('image-draft-character_master-standalone');
});

test('image screen previews a four-candidate request and queues it through guarded API', async ({ page }) => {
  let submitted = null;
  let polls = 0;
  let runningCandidate = 1;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'workspace-image', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'z_image_turbo', label: 'Z-Image Turbo · text to image', version: '1', available: true,
    disabled_reason: null, defaults: { width: 1280, height: 720, steps: 8, cfg: 1 },
  }], generation_policy: { assisted_manual: { initial_candidates: 4 } },
    gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: {
    monitor_available: true, safe_to_submit: true, temperature_cutoff_c: 83, graphics_clock_ceiling_mhz: 2100,
    operating_point: { temperature_c: 48, graphics_clock_mhz: 1800 },
  } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: {
    enabled: true, running: true, available: true, worker_state: 'running', reason: null,
  } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [{ workspace_id: 'workspace-image', title: 'Lighthouse story' }], total: 1 } }));
  await page.route('**/api/images/validations', route => route.fulfill({ json: {
    workflow_id: 'z_image_turbo', workflow_version: '1', prompt: 'A lighthouse in fog.',
    settings: { width: 1280, height: 720, steps: 8, cfg: 1 }, initial_candidate_count: 4,
    generation_policy: { initial_candidates: 4 }, candidates: [1, 2, 3, 4].map(seed => ({ seed, graph: {} })),
  } }));
  await page.route('**/api/images/jobs', async route => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ status: 202, json: { batch_id: 'batch-1', reused: false,
      jobs: [1, 2, 3, 4].map(candidate_index => ({ job_id: `job-${candidate_index}`, asset_role: 'character_master', candidate_index, status: 'queued' })) } });
  });
  await page.route('**/api/images/batches/batch-1?**', route => {
    polls += 1;
    return route.fulfill({ json: { batch_id: 'batch-1', jobs: [1, 2, 3, 4].map(candidate_index => ({
      job_id: `job-${candidate_index}`, asset_role: 'character_master', candidate_index, status: candidate_index < runningCandidate ? 'completed' : candidate_index === runningCandidate ? 'running' : 'queued', output_asset_id: null,
    })), generation_policy: {} } });
  });
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));

  await imageProject(page); await page.goto('/#/assets');
  await expect(page.getByRole('heading', { name: 'Characters, scene backgrounds & frames' })).toBeVisible();
  await expect(page.getByText('Current project · change with New project or Load project above')).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Image generation workspace' })).toHaveCount(0);
  await expect(page.getByText('workspace-image', { exact: true })).toHaveCount(0);
  await page.locator('.image-assets-page .image-prompt-label textarea').fill('A lighthouse in fog.');
  await page.getByRole('button', { name: 'Check generation request' }).click();
  await expect(page.getByText('4 candidates · no generation submitted')).toBeVisible();
  await page.getByRole('button', { name: 'Generate four' }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  await expect(page.getByText('Candidate 4')).toBeVisible();
  expect(submitted).toMatchObject({ workspace_id: 'workspace-image', asset_role: 'character_master', prompt: 'A lighthouse in fog.', control_mode: 'assisted_manual' });
  expect(polls).toBeGreaterThan(0);
  for (const index of [1, 2, 3, 4]) {
    runningCandidate = index;
    await page.getByRole('button', { name: 'Refresh', exact: true }).click();
    const cards = page.locator('.image-candidate-section .image-candidate');
    await expect(cards.nth(index - 1).getByRole('img', { name: 'Generating image', exact: true })).toBeVisible();
    await expect(page.getByRole('img', { name: 'Generating image', exact: true })).toHaveCount(1);
    await expect(page.getByRole('img', { name: 'Waiting to generate', exact: true })).toHaveCount(4 - index);
  }
});

test('image prompt preparation is explicit, editable and carries workflow provenance into the queued request', async ({ page }) => {
  let preparedRequest;
  let submittedRequest;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'workspace-image', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true,
    defaults: { width: 1280, height: 720, steps: 8, cfg: 1 },
  }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [{ workspace_id: 'workspace-image', title: 'Test story' }], total: 1 } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await page.route('**/api/images/prompts/prepare', async route => {
    preparedRequest = route.request().postDataJSON();
    return route.fulfill({ json: { workflow_id: 'z_image_turbo', asset_role: 'character_master',
      prompt: 'A source-grounded portrait of Mira.', knowledge_ref: { knowledge_id: 'knowledge-1',
        guidance_version: 3, workflow_sha256: 'a'.repeat(64) },
      sources: [{ uri: 'z_image_api.json', version: 'b'.repeat(64), section: 'prompt input' }] } });
  });
  await page.route('**/api/images/validations', route => route.fulfill({ json: {
    workflow_id: 'z_image_turbo', workflow_version: '1', initial_candidate_count: 4,
    settings: {}, generation_policy: {}, candidates: [],
  } }));
  await page.route('**/api/images/jobs', async route => {
    submittedRequest = route.request().postDataJSON();
    return route.fulfill({ status: 202, json: { batch_id: 'prepared-image', jobs: [], reused: false } });
  });
  await page.route('**/api/images/batches/prepared-image?**', route => route.fulfill({ json: {
    batch_id: 'prepared-image', jobs: [], generation_policy: {},
  } }));

  await imageProject(page); await page.goto('/#/assets');
  await page.locator('.image-assets-page .image-prompt-label textarea').fill('Mira, natural light.');
  await page.getByRole('button', { name: 'Prepare prompt' }).click();
  await expect(page.locator('.image-assets-page .image-prompt-label textarea')).toHaveValue('A source-grounded portrait of Mira.');
  await expect(page.getByText('Prompt sources · guidance v3')).toBeVisible();
  await page.locator('.image-assets-page .image-prompt-label textarea').fill('A source-grounded portrait of Mira, softer light.');
  await page.getByRole('button', { name: 'Generate four' }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  expect(preparedRequest).toMatchObject({ workflow_id: 'z_image_turbo', asset_role: 'character_master', prompt: 'Mira, natural light.' });
  expect(submittedRequest).toMatchObject({ prompt: 'A source-grounded portrait of Mira, softer light.',
    prompt_knowledge_ref: { knowledge_id: 'knowledge-1', guidance_version: 3, workflow_sha256: 'a'.repeat(64) } });
});

test('image screen retries the exact saved request after an uncertain response', async ({ page }) => {
  const submissions = [];
  let validationCalls = 0;
  let calls = 0;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'workspace-image', role: 'character_master', workflowId: 'z_image_turbo', prompt: 'Original prompt', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true,
    defaults: { width: 1280, height: 720, steps: 8, cfg: 1 },
  }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/images/validations', route => { validationCalls += 1; return route.fulfill({ json: {
    workflow_id: 'z_image_turbo', workflow_version: '1', prompt: 'Original prompt',
    settings: {}, initial_candidate_count: 4, generation_policy: { initial_candidates: 4 }, candidates: [],
  } }); });
  await page.route('**/api/images/jobs', async route => {
    submissions.push(route.request().postDataJSON());
    calls += 1;
    if (calls === 1) return route.fulfill({ status: 503, json: { error: { message: 'response uncertain' } } });
    return route.fulfill({ status: 200, json: { batch_id: 'batch-recovered', reused: true,
      jobs: [1, 2, 3, 4].map(candidate_index => ({ job_id: `job-${candidate_index}`, asset_role: 'character_master', candidate_index, status: 'queued' })) } });
  });
  await page.route('**/api/images/batches/batch-recovered?**', route => route.fulfill({ json: {
    batch_id: 'batch-recovered', jobs: [1, 2, 3, 4].map(candidate_index => ({
      job_id: `job-${candidate_index}`, asset_role: 'character_master', candidate_index, status: 'queued', output_asset_id: null,
    })), generation_policy: {},
  } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await imageProject(page); await page.goto('/#/assets');
  await page.getByRole('button', { name: 'Generate four' }).click();
  await expect(page.getByText('Retry sends its saved prompt and settings unchanged.')).toBeVisible();
  await expect(page.locator('.image-assets-page .image-prompt-label textarea')).toBeDisabled();
  await expect(page.locator('.image-assets-page .image-prompt-label textarea')).toHaveValue('Original prompt');
  await page.getByRole('button', { name: 'Resume saved request' }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  expect(submissions).toHaveLength(2);
  expect(submissions[1]).toEqual(submissions[0]);
  expect(submissions[1].prompt).toBe('Original prompt');
  expect(validationCalls).toBe(1);
});

test('Qwen Edit resumes its frozen request when the live reference list is unavailable', async ({ page }) => {
  const reference = { asset_id: 'image-1234567890abcdef', sha256: 'a'.repeat(64) };
  const frozen = { workflow_id: 'qwen_image_edit_2511', prompt: 'Keep the face; change the coat.',
    control_mode: 'assisted_manual', seed: 42, output_prefix: 'workspace-image/character_master',
    workspace_id: 'workspace-image', idempotency_key: 'saved-edit', asset_role: 'character_master',
    source_references: [reference] };
  let submitted;
  await page.addInitScript(value => {
    localStorage.setItem('vibe-image-draft-v1', JSON.stringify({ workspaceId: 'workspace-image',
      role: 'character_master', workflowId: 'qwen_image_edit_2511', prompt: value.prompt, seed: 42 }));
    localStorage.setItem('vibe-image-pending-request-v1', JSON.stringify(value));
  }, frozen);
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'qwen_image_edit_2511', label: 'Qwen Image Edit', version: '1', available: true,
    defaults: { width: 1024, height: 1024, steps: 4, cfg: 1 },
  }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ status: 503, json: {} }));
  await page.route('**/api/images/validations', () => { throw new Error('a frozen retry must not be revalidated'); });
  await page.route('**/api/images/jobs', async route => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ status: 200, json: { batch_id: 'batch-recovered', reused: true, jobs: [] } });
  });
  await page.route('**/api/images/batches/batch-recovered?**', route => route.fulfill({ json: {
    batch_id: 'batch-recovered', jobs: [], generation_policy: {},
  } }));
  await imageProject(page); await page.goto('/#/assets');
  await expect(page.getByRole('button', { name: 'Resume saved request' })).toBeEnabled();
  await page.getByRole('button', { name: 'Resume saved request' }).click();
  await expect.poll(()=>submitted).toEqual(frozen);
  expect(submitted).toEqual(frozen);
});

test('completed candidate can be selected for the active image role', async ({ page }) => {
  let selected = null;
  await page.addInitScript(() => {
    localStorage.setItem('vibe-image-draft-v1', JSON.stringify({ workspaceId: 'workspace-image', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42 }));
    localStorage.setItem('vibe-image-active-v1', JSON.stringify({ workspaceId: 'workspace-image', batchId: 'batch-done' }));
  });
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: false } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: false } }));
  await page.route('**/api/images/batches/batch-done?**', route => route.fulfill({ json: {
    batch_id: 'batch-done', generation_policy: {}, jobs: [{ job_id: 'job-done', asset_role: 'character_master', candidate_index: 1, status: 'completed', output_asset_id: 'pa-0123456789abcdef' }],
  } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { total: 1, assets: [{
    asset_id: 'pa-0123456789abcdef', workspace_id: 'workspace-image', kind: 'image', roles: ['image_candidate'],
    filename: 'portrait.png', media_type: 'image/png', sha256: 'abc', size_bytes: 123, content_url: '/portrait.png',
  }] } }));
  await page.route('**/api/images/jobs/job-done/accept', async route => {
    selected = route.request().postDataJSON();
    return route.fulfill({ json: { job_id: 'job-done', selected: true, asset: {
      asset_id: 'pa-0123456789abcdef', workspace_id: 'workspace-image', kind: 'image',
      roles: ['image_candidate', 'character_master'], filename: 'portrait.png', media_type: 'image/png',
      sha256: 'abc', size_bytes: 123, content_url: '/portrait.png',
    } } });
  });
  await imageProject(page); await page.goto('/#/assets');
  await page.getByRole('button', { name: 'Use as Character image' }).click();
  await expect(page.getByText('Selected as Character image')).toBeVisible();
  expect(selected).toEqual({ workspace_id: 'workspace-image', asset_role: 'character_master' });
});

test('generated image candidates open a keyboard-dismissible full-size preview', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('vibe-image-draft-v1', JSON.stringify({ workspaceId: 'workspace-image', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42 }));
    localStorage.setItem('vibe-image-active-v1', JSON.stringify({ workspaceId: 'workspace-image', batchId: 'batch-done' }));
  });
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: false } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: false } }));
  await page.route('**/api/images/batches/batch-done?**', route => route.fulfill({ json: {
    batch_id: 'batch-done', generation_policy: {}, jobs: [1,2].map(n=>({job_id:`job-${n}`,asset_role:'character_master',candidate_index:n,status:'completed',output_asset_id:`pa-${n}`})),
  } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { total: 2, assets: [
    ...[1,2].map(n=>({asset_id:`pa-${n}`,workspace_id:'workspace-image',kind:'image',roles:['image_candidate'],filename:n===1?'portrait.png':'portrait-2.png',media_type:'image/png',sha256:'abc',size_bytes:123,content_url:n===1?'/portrait.png':'/portrait-2.png'}))
  ] } }));
  await imageProject(page); await page.goto('/#/assets');
  const openPreview = page.getByRole('button', { name: 'View full-size Character image candidate 1' });
  await openPreview.click();
  const dialog = page.getByRole('dialog', { name: 'portrait.png' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Close image preview' })).toBeFocused();
  await expect(dialog.locator('img')).toHaveAttribute('src', '/portrait.png');
  await dialog.getByRole('button',{name:'Next candidate image'}).click();
  await expect(page.getByRole('dialog').locator('img')).toHaveAttribute('src','/portrait-2.png');
  await page.keyboard.press('ArrowLeft');
  await expect(dialog.locator('img')).toHaveAttribute('src','/portrait.png');
  await dialog.getByRole('button',{name:'Previous candidate image'}).click();
  await expect(page.getByRole('dialog').locator('img')).toHaveAttribute('src','/portrait-2.png');
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(openPreview).toBeFocused();
});

test('Qwen Edit attaches workspace image IDs and hashes to the saved request', async ({ page }) => {
  let submitted;
  const reference = { asset_id: 'image-1234567890abcdef', workspace_id: 'workspace-image', kind: 'image',
    roles: ['style_reference'], filename: 'rainy-street.png', media_type: 'image/png', sha256: 'a'.repeat(64),
    size_bytes: 100, content_url: '/rainy-street.png', recommended: true };
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'workspace-image', role: 'character_master', workflowId: 'qwen_image_edit_2511',
    prompt: 'Keep the person; make the coat red.', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'qwen_image_edit_2511', label: 'Qwen Image Edit', version: '1', available: true,
    defaults: { width: 1024, height: 1024, steps: 4, cfg: 1 },
  }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  const localReference = { ...reference, asset_id: 'local-image-12345678', roles: ['style_reference'], filename: 'local-street.png', recommended: false };
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { assets: [localReference, reference], total: 2 } }));
  await page.route('**/api/images/validations', async route => {
    const request = route.request().postDataJSON();
    expect(request.source_references).toEqual([{ asset_id: reference.asset_id, sha256: reference.sha256 }]);
    return route.fulfill({ json: { initial_candidate_count: 4, workflow_id: request.workflow_id,
      workflow_version: '1', candidates: [] } });
  });
  await page.route('**/api/images/jobs', async route => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ status: 202, json: { batch_id: 'batch-edit', jobs: [], reused: false } });
  });
  await page.route('**/api/images/batches/batch-edit?**', route => route.fulfill({ json: {
    batch_id: 'batch-edit', jobs: [], generation_policy: {},
  } }));
  await imageProject(page); await page.goto('/#/assets');
  await expect(page.getByText('rainy-street.png')).toBeVisible();
  const referenceCards = page.locator('.image-reference-grid label');
  await expect(referenceCards).toHaveCount(2);
  await expect(referenceCards.nth(0)).toContainText('rainy-street.png');
  await expect(referenceCards.nth(1)).toContainText('local-street.png');
  await expect(referenceCards.nth(0).getByRole('checkbox')).not.toBeChecked();
  await page.getByLabel('rainy-street.png').check();
  await page.getByRole('button', { name: 'Check generation request' }).click();
  await page.getByRole('button', { name: 'Generate four' }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  expect(submitted.source_references).toEqual([{ asset_id: reference.asset_id, sha256: reference.sha256 }]);
  expect(submitted).not.toHaveProperty('source_images');
});

for (const viewCount of [2, 3, 8]) test(`Worlds submits one selected base image and labels ${viewCount} directional views`, async ({ page }) => {
  const labels = viewCount === 2 ? ['Left','Right'] : viewCount === 3 ? ['Left','Right','Back'] : ['Front','Front-right','Right','Back-right','Back','Back-left','Left','Front-left'];
  let submitted;
  const base = { asset_id: 'image-world-12345678', workspace_id: 'workspace-image', kind: 'image',
    roles: ['world_master'], filename: 'station-base.png', media_type: 'image/png', sha256: 'b'.repeat(64),
    size_bytes: 100, content_url: '/station-base.png' };
  await page.addInitScript(count => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'workspace-image', role: 'world_master', workflowId: 'qwen_image_multi_angle_2511',
    prompt: 'An old station, same architecture from every direction.', seed: 42, worldViewCount: count,
  })), viewCount);
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'qwen_image_multi_angle_2511', label: 'Qwen Image Edit · world views', version: '2', available: true,
    defaults: { width: 1024, height: 1024, steps: 20, cfg: 4 },
  }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/media/workspace-image/assets?kind=image', route => route.fulfill({ json: { assets: [base], total: 1 } }));
  await page.route('**/api/images/validations', async route => {
    const request = route.request().postDataJSON();
    expect(request).toMatchObject({ workflow_id: 'qwen_image_multi_angle_2511', world_view_count: viewCount,
      source_references: [{ asset_id: base.asset_id, sha256: base.sha256 }] });
    return route.fulfill({ json: { workflow_id: request.workflow_id, workflow_version: '2',
      prompt: request.prompt, settings: { world_views: labels.map(label => ({ label })) },
      initial_candidate_count: viewCount, candidates: [] } });
  });
  await page.route('**/api/images/jobs', async route => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ status: 202, json: { batch_id: 'batch-world-views', reused: false, jobs: [] } });
  });
  await page.route('**/api/images/batches/batch-world-views?**', route => route.fulfill({ json: {
    batch_id: 'batch-world-views', jobs: Array.from({length:viewCount},(_,i)=>({job_id:`view-${i}`,candidate_index:i+1,status:'running',asset_role:'world_view',settings:{multi_angle_batch:true,world_views:labels.map(label=>({label}))}})), generation_policy: {},
  } }));
  await imageProject(page); await page.goto('/#/worlds');
  await expect(page.getByRole('combobox', { name: 'Image workflow' })).toContainText('world views');
  await expect(page.getByLabel('station-base.png', {exact:true})).toBeVisible();
  await page.getByRole('checkbox',{name:'station-base.png',exact:true}).check();
  await page.getByRole('button', { name: 'Check generation request' }).click();
  await expect(page.getByText(`${viewCount} candidates · no generation submitted`)).toBeVisible();
  await page.getByRole('button', { name: `Generate ${viewCount} views` }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  await expect(page.getByText(/One multi-angle workflow is running/)).toBeVisible();
  await expect(page.getByRole('img',{name:'Generating image',exact:true})).toHaveCount(viewCount);
  expect(submitted).toMatchObject({ asset_role: 'world_view', world_view_count: viewCount,
    source_references: [{ asset_id: base.asset_id, sha256: base.sha256 }] });
});

test('character image generation binds to a character in the accepted screenplay graph', async ({ page }) => {
  let submitted;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'story-1', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true,
    defaults: { width: 1280, height: 720, steps: 8, cfg: 1 },
  }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions?**', route => route.fulfill({ json: { items: [{
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1',
  }], total: 1, limit: 100, offset: 0 } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions/screenplay-1', route => route.fulfill({ json: {
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1', screenplay: { scenes: [] },
  } }));
  await page.route('**/api/story/workspaces/story-1/graph?snapshot_id=graph-1', route => route.fulfill({ json: {
    snapshot_id: 'graph-1', status: 'complete', records: [{ record_id: 'character-mira', kind: 'entity', type: 'character', name: 'Mira', detail: 'A detective' }],
  } }));
  await page.route('**/api/images/validations', route => route.fulfill({ json: { initial_candidate_count: 4, workflow_id: 'z_image_turbo', workflow_version: '1', candidates: [] } }));
  await page.route('**/api/images/jobs', async route => {
    submitted = route.request().postDataJSON();
    return route.fulfill({ status: 202, json: { batch_id: 'batch-story', jobs: [], reused: false } });
  });
  await page.route('**/api/images/batches/batch-story?**', route => route.fulfill({ json: { batch_id: 'batch-story', jobs: [], generation_policy: {} } }));
  await page.route('**/api/media/story-1/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await page.route('**/api/story/workspaces/story-1/production-setup?**', route => route.fulfill({ json: {
    setup: { mode: 'assisted_manual', automate_steps: { character_images: false, world_images: false, frame_images: false } },
  } }));
  await page.route('**/api/story/workspaces/story-1/assisted-stage-skips**', route => route.fulfill({ json: { skipped: [] } }));
  await page.route('**/api/images/prompts/prepare', route => route.fulfill({ json: {
    prompt: 'Mira, a detective, alone against a plain white background.',
    knowledge_ref: { knowledge_id: 'z-image', guidance_version: 2 }, sources: [],
  } }));
  await imageProject(page); await page.goto('/#/assets');
  await page.getByRole('combobox', { name: 'Character target' }).selectOption('character-mira');
  await expect(page.locator('.image-assets-page .image-prompt-label textarea')).toHaveValue('Mira, a detective, alone against a plain white background.');
  await page.locator('.image-assets-page .image-prompt-label textarea').fill('Portrait of Mira');
  await page.getByRole('button', { name: 'Generate four' }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  expect(submitted).toMatchObject({
    workspace_id: 'story-1', asset_role: 'character_master', screenplay_revision_id: 'screenplay-1',
    target_record_id: 'character-mira',
  });
});

test('story-linked image prompt supports selection-based Codex micro-edit', async ({ page }) => {
  await page.route('**/api/story/workspaces/story-1/production-setup?**',r=>r.fulfill({json:{setup:{mode:'assisted_manual',automate_steps:{character_images:false}}}}));
  await page.route('**/api/images/prompts/prepare',r=>r.fulfill({json:{workflow_id:'z_image_turbo',prompt:'Character reference portrait: Mira. A detective',knowledge_ref:{knowledge_id:'fixture',guidance_version:1,workflow_sha256:'a'.repeat(64)},sources:[]}}));
  let proposalRequest;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'story-1', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{workflow_id:'z_image_turbo',label:'Z-Image Turbo',available:false,defaults:{}}] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: false } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: false } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [{ workspace_id: 'story-1', title: 'Pilot story' }], total: 1 } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions?**', route => route.fulfill({ json: { items: [{
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1',
  }], total: 1, limit: 100, offset: 0 } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions/screenplay-1', route => route.fulfill({ json: {
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1', screenplay: { scenes: [] },
  } }));
  await page.route('**/api/story/workspaces/story-1/production-setup?**', route => route.fulfill({ json: {
    workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', setup: { mode: 'assisted_manual',
      automate_steps: { character_images: false, character_voice: false, world_images: false, frame_images: false, video: false },
      video_quality: 'standard', duration_policy: { kind: 'fixed', seconds: 5 } }, updated_at: null,
  } }));
  await page.route('**/api/story/workspaces/story-1/graph?snapshot_id=graph-1', route => route.fulfill({ json: {
    snapshot_id: 'graph-1', status: 'complete', records: [{ record_id: 'character-mira', kind: 'entity', type: 'character', name: 'Mira', detail: 'A detective' }],
  } }));
  await page.route('**/api/media/story-1/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await page.route('**/api/story/workspaces/story-1/field-edit-proposals', async route => {
    proposalRequest = route.request().postDataJSON();
    return route.fulfill({ json: { proposal_id: 'proposal-1', replacement: 'An observant detective',
      expected_text: proposalRequest.expected_text, start_codepoint: proposalRequest.start_codepoint,
      end_codepoint: proposalRequest.end_codepoint, field_sha256: 'a'.repeat(64),
      revision_id: proposalRequest.revision_id, field_key: proposalRequest.field_key,
      explanation: 'Adjusted the selected character description.' } });
  });

  await imageProject(page); await page.goto('/#/characters?step=character_images');
  await page.getByRole('combobox', { name: 'Character target' }).selectOption('character-mira');
  const prompt = page.getByRole('textbox', { name: 'Image prompt' });
  await expect(prompt).toHaveValue('Character reference portrait: Mira. A detective');
  await prompt.click();
  await page.keyboard.press('Control+A');
  await page.getByRole('textbox', { name: 'Instruction for Image prompt' }).fill('Make this a concise, visual description');
  await page.getByRole('button', { name: 'Suggest edit' }).click();
  await expect(page.getByText('An observant detective', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Apply to draft' }).click();
  await expect(prompt).toHaveValue('An observant detective');
  expect(proposalRequest).toMatchObject({ surface: 'prompt', revision_id: 'screenplay-1',
    field_key: 'character_images.character_master.character-mira', expected_text: 'Character reference portrait: Mira. A detective' });
});

test('saved character selection survives reload and is omitted for non-character image roles', async ({ page }) => {
  let submitted;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'story-1', role: 'character_master', workflowId: 'z_image_turbo', prompt: 'A portrait', seed: 42,
    targetRecordId: 'character-mira', acceptedScreenplayId: 'screenplay-1',
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{ workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true, live_smoke: { status: 'passed' }, defaults: { width: 1280, height: 720, steps: 8, cfg: 1 } }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions?**', route => route.fulfill({ json: { items: [{ screenplay_revision_id: 'screenplay-1', accepted: true }] } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions/screenplay-1', route => route.fulfill({ json: { screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1' } }));
  await page.route('**/api/story/workspaces/story-1/graph?snapshot_id=graph-1', route => route.fulfill({ json: { snapshot_id: 'graph-1', status: 'complete', records: [{ record_id: 'character-mira', kind: 'entity', type: 'character', name: 'Mira', detail: '' }] } }));
  await page.route('**/api/images/validations', route => route.fulfill({ json: { initial_candidate_count: 4, workflow_id: 'z_image_turbo', workflow_version: '1', candidates: [] } }));
  await page.route('**/api/images/jobs', async route => { submitted = route.request().postDataJSON(); return route.fulfill({ status: 202, json: { batch_id: 'batch-world', jobs: [], reused: false } }); });
  await page.route('**/api/images/batches/batch-world?**', route => route.fulfill({ json: { batch_id: 'batch-world', jobs: [], generation_policy: {} } }));
  await page.route('**/api/media/story-1/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await page.route('**/api/story/workspaces/story-1/production-setup?**', route => route.fulfill({ json: {
    setup: { mode: 'assisted_manual', automate_steps: { character_images: false, world_images: false, frame_images: false } },
  } }));
  await page.route('**/api/story/workspaces/story-1/assisted-stage-skips**', route => route.fulfill({ json: { skipped: [] } }));
  await page.route('**/api/images/prompts/prepare', route => route.fulfill({ json: {
    prompt: 'Mira, a detective, alone against a plain white background.',
    knowledge_ref: { knowledge_id: 'z-image', guidance_version: 2 }, sources: [],
  } }));
  await imageProject(page); await page.goto('/#/assets');
  await expect(page.getByText(/GPU ready · 22\.0 GiB reported free \(informational\)/)).toBeVisible();
  await expect(page.getByText('Image worker ready', { exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Character target' })).toHaveValue('character-mira');
  await page.getByLabel('Asset role').selectOption('world_master');
  await page.getByRole('button', { name: 'Generate four' }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  expect(submitted).toMatchObject({ workspace_id: 'story-1', asset_role: 'world_master' });
  expect(submitted).not.toHaveProperty('screenplay_revision_id');
  expect(submitted).not.toHaveProperty('target_record_id');
});

test('world master offers only canonical locations and preserves standalone generation for older graphs', async ({ page }) => {
  let submitted;
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'story-1', role: 'world_master', workflowId: 'z_image_turbo', prompt: 'A rain-soaked street', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{ workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true, defaults: { width: 1280, height: 720, steps: 8, cfg: 1 } }], gpu_admission: { available: true, checked: true, free_gib: 22, required_gib: 20, checked_at: 'now', reason: null } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions?**', route => route.fulfill({ json: { items: [{ screenplay_revision_id: 'screenplay-1', accepted: true }] } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions/screenplay-1', route => route.fulfill({ json: { screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1' } }));
  await page.route('**/api/story/workspaces/story-1/graph?snapshot_id=graph-1', route => route.fulfill({ json: { snapshot_id: 'graph-1', status: 'complete', records: [
    { record_id: 'legacy-place', kind: 'entity', type: 'background', name: 'Old Town', detail: '' },
    { record_id: 'character-mira', kind: 'entity', type: 'character', name: 'Mira', detail: '' },
  ] } }));
  await page.route('**/api/images/validations', route => route.fulfill({ json: { initial_candidate_count: 4, workflow_id: 'z_image_turbo', workflow_version: '1', candidates: [] } }));
  await page.route('**/api/images/jobs', async route => { submitted = route.request().postDataJSON(); return route.fulfill({ status: 202, json: { batch_id: 'batch-older-graph', jobs: [], reused: false } }); });
  await page.route('**/api/images/batches/batch-older-graph?**', route => route.fulfill({ json: { batch_id: 'batch-older-graph', jobs: [], generation_policy: {} } }));
  await page.route('**/api/media/story-1/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await imageProject(page); await page.goto('/#/assets');
  const target = page.getByRole('combobox', { name: 'Location target' });
  await expect(target).toBeVisible();
  await expect(target.locator('option')).toHaveCount(1);
  await expect(page.getByText(/no canonical location target is available/i)).toBeVisible();
  await page.getByRole('button', { name: 'Generate four' }).click();
  await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
  expect(submitted).toMatchObject({ workspace_id: 'story-1', asset_role: 'world_master' });
  expect(submitted).not.toHaveProperty('screenplay_revision_id');
  expect(submitted).not.toHaveProperty('target_record_id');
});

test('story character-image stage starts the checked automation and shows its progress', async ({ page }) => {
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true,
    defaults: { width: 1280, height: 720, steps: 8, cfg: 1 },
  }] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions?**', route => route.fulfill({ json: { items: [{
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1',
  }], total: 1, limit: 100, offset: 0 } }));
  await page.route('**/api/story/workspaces/story-1/production-setup?**', route => route.fulfill({ json: {
    workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', updated_at: 'setup-1', setup: {
      mode: 'assisted_manual', automate_steps: { character_images: true, character_voice: false, world_images: false, frame_images: false, video: false },
      video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 },
      image_stage_settings: { character_images: { workflow_id: 'z_image_turbo', width: 1280, height: 720, steps: 8, cfg: 1 } },
    },
  } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions/screenplay-1', route => route.fulfill({ json: {
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1', screenplay: { scenes: [] },
  } }));
  await page.route('**/api/story/workspaces/story-1/graph?snapshot_id=graph-1', route => route.fulfill({ json: {
    snapshot_id: 'graph-1', status: 'complete', records: [{ record_id: 'character-mira', kind: 'entity', type: 'character', name: 'Mira', detail: 'A detective' }],
  } }));
  await page.route('**/api/media/story-1/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  let stageRequest;
  await page.route('**/api/images/automated-stage', async route => { stageRequest = route.request().postDataJSON(); return route.fulfill({ status: 202, json: {
    run_id: 'run-image-stage', step: 'character_images', target_count: 1, batches: [{ batch_id: 'batch-auto-image', reused: false,
      jobs: [{ job_id: 'job-auto-image', candidate_index: 1, status: 'queued', settings: { lineage: { target_name: 'Mira' } } }] }],
  } }); });
  await page.route('**/api/images/batches/batch-auto-image?**', route => route.fulfill({ json: { batch_id: 'batch-auto-image', generation_policy: {},
    jobs: [{ job_id: 'job-auto-image', candidate_index: 1, status: 'queued', settings: { lineage: { target_name: 'Mira' } } }] } }));
  let submitted = false;
  await page.route('**/api/images/jobs', route => { submitted = true; return route.fulfill({ status: 202, json: { batch_id: 'must-not-queue', jobs: [] } }); });

  await imageProject(page); await page.goto('/#/assets?step=character_images&workspace_id=story-1');
  await expect(page.getByRole('heading', { name: 'Character image step' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'automated from the saved setup' }).first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Automated targets' })).toBeVisible();
  await expect(page.getByText('Mira · candidate 1')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Generate four' })).toBeDisabled();
  expect(stageRequest).toEqual({ workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', step: 'character_images' });
  expect(submitted).toBe(false);
});

async function mockWorldImageStage(page, { automated = false } = {}) {
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'story-1', role: 'world_master', workflowId: 'z_image_turbo', prompt: '', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true,
    defaults: { width: 1280, height: 720, steps: 8, cfg: 1 },
  }] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions?**', route => route.fulfill({ json: { items: [{
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1',
  }] } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions/screenplay-1', route => route.fulfill({ json: {
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1',
  } }));
  await page.route('**/api/story/workspaces/story-1/production-setup?screenplay_revision_id=screenplay-1', route => route.fulfill({ json: {
    workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', updated_at: 'setup-1', setup: {
      mode: 'assisted_manual', automate_steps: { character_images: false, character_voice: false, world_images: automated, frame_images: false, video: false },
      video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 },
      ...(automated ? { image_stage_settings: { world_images: { workflow_id: 'z_image_turbo', width: 1280, height: 720, steps: 8, cfg: 1 } } } : {}),
    },
  } }));
  await page.route('**/api/story/workspaces/story-1/graph?snapshot_id=graph-1', route => route.fulfill({ json: {
    snapshot_id: 'graph-1', status: 'complete', records: [
      { record_id: 'location-station', kind: 'entity', type: 'location', name: 'Old station', detail: 'Rain-dark stone platform' },
      { record_id: 'character-mira', kind: 'entity', type: 'character', name: 'Mira', detail: 'A detective' },
      { record_id: 'legacy-background', kind: 'entity', type: 'background', name: 'Legacy background', detail: '' },
    ],
  } }));
  await page.route('**/api/media/story-1/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
}

test('Assisted manual world-image step previews only against an accepted canonical location', async ({ page }) => {
  let previewRequest;
  let submitted = false;
  await mockWorldImageStage(page);
  await page.route('**/api/images/validations', async route => {
    previewRequest = route.request().postDataJSON();
    return route.fulfill({ json: { workflow_id: 'z_image_turbo', workflow_version: '1', prompt: previewRequest.prompt,
      settings: { width: 1280, height: 720, steps: 8, cfg: 1 }, initial_candidate_count: 4,
      generation_policy: {}, candidates: [] } });
  });
  await page.route('**/api/images/jobs', route => { submitted = true; return route.fulfill({ status: 202, json: { batch_id: 'unexpected', jobs: [] } }); });

  await imageProject(page); await page.goto('/#/assets?step=world_images&workspace_id=story-1');
  await expect(page.getByRole('heading', { name: 'Scene background step' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'world image generation is unchecked' })).toBeVisible();
  const target = page.getByRole('combobox', { name: 'Location target' });
  await expect(target.locator('option')).toHaveCount(2);
  await expect(target.locator('option').nth(1)).toHaveText('Old station');
  await target.selectOption('location-station');
  await page.getByRole('button', { name: 'Check generation request' }).click();
  await expect(page.getByRole('heading', { name: 'Compiled preview' })).toBeVisible();
  expect(previewRequest).toMatchObject({ workspace_id: 'story-1', asset_role: 'world_master',
    screenplay_revision_id: 'screenplay-1', target_record_id: 'location-station' });
  expect(submitted).toBe(false);
});

test('Assisted manual world-image step starts checked automation instead of manual generation', async ({ page }) => {
  let submitted = false;
  let stageRequest;
  await mockWorldImageStage(page, { automated: true });
  await page.route('**/api/images/jobs', route => { submitted = true; return route.fulfill({ status: 202, json: { batch_id: 'unexpected', jobs: [] } }); });
  await page.route('**/api/images/automated-stage', async route => { stageRequest = route.request().postDataJSON(); return route.fulfill({ status: 202, json: {
    run_id: 'run-world-stage', step: 'world_images', target_count: 1, batches: [{ batch_id: 'batch-world-auto', reused: false,
      jobs: [{ job_id: 'job-world-auto', candidate_index: 1, status: 'queued', settings: { lineage: { target_name: 'Old station' } } }] }],
  } }); });
  await page.route('**/api/images/batches/batch-world-auto?**', route => route.fulfill({ json: { batch_id: 'batch-world-auto', generation_policy: {}, jobs: [
    { job_id: 'job-world-auto', candidate_index: 1, status: 'completed', output_asset_id: null,
      settings: { lineage: { target_name: 'Old station' } }, director_review: { resolution_status: 'blocked',
        decision: { action: 'blocked', reason: 'Codex could not verify the generated location.' },
        error: { code: 'director_review_failed', message: 'Reviewer temporarily unavailable.' } } },
  ] } }));

  await imageProject(page); await page.goto('/#/assets?step=world_images&workspace_id=story-1');
  await expect(page.getByRole('heading', { name: 'Scene background step' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'World image generation is automated' }).first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Automated targets' })).toBeVisible();
  await expect(page.getByText('Old station · candidate 1')).toBeVisible();
  await expect(page.getByText('completed · Director blocked')).toBeVisible();
  await expect(page.getByText('Reviewer temporarily unavailable.')).toBeVisible();
  await expect(page.getByText('This candidate was kept in the library but not selected.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Check generation request' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Generate four' })).toBeDisabled();
  expect(stageRequest).toEqual({ workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', step: 'world_images' });
  expect(submitted).toBe(false);
});

async function mockFrameImageStage(page, { automated = false, prompt = 'A rainy station platform', multiWorkspace = false } = {}) {
  const skipped = new Set();
  const skipped2 = new Set(multiWorkspace ? ['1.1'] : []);
  await page.addInitScript((draftPrompt) => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'story-1', role: 'first_frame', workflowId: 'z_image_turbo', prompt: draftPrompt, seed: 42,
  })), prompt);
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [{
    workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', version: '1', available: true,
    defaults: { width: 1280, height: 720, steps: 8, cfg: 1 },
  }] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [
    { workspace_id: 'story-1', title: 'First story' }, ...(multiWorkspace ? [{ workspace_id: 'story-2', title: 'Second story' }] : []),
  ], total: multiWorkspace ? 2 : 1 } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions?**', route => route.fulfill({ json: { items: [{
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1',
  }] } }));
  await page.route('**/api/story/workspaces/story-1/screenplay/revisions/screenplay-1', route => route.fulfill({ json: {
    screenplay_revision_id: 'screenplay-1', accepted: true, source_revision_id: 'source-1', graph_snapshot_id: 'graph-1',
    screenplay: { scenes: [{ scene_number: 1, slugline: 'INT. STATION - NIGHT', summary: 'Mira arrives.', shots: [
      { direction:{}, shot_number: 1, action: 'Mira enters the platform.' }, { direction:{}, shot_number: 2, action: 'A train emerges from the fog.' },
    ] }] },
  } }));
  await page.route('**/api/story/workspaces/story-1/production-setup?screenplay_revision_id=screenplay-1', route => route.fulfill({ json: {
    workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', updated_at: 'setup-1', setup: {
      mode: 'assisted_manual', automate_steps: { character_images: false, character_voice: false,
        world_images: false, frame_images: automated, video: false },
      video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 },
    },
  } }));
  await page.route('**/api/story/workspaces/story-1/frame-preparation-skips**', async route => {
    if (route.request().method() === 'GET') return route.fulfill({ json: { workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', skipped: [...skipped].map(key => { const [scene_number, shot_number] = key.split('.').map(Number); return { scene_number, shot_number }; }) } });
    const body = route.request().postDataJSON();
    const key = `${body.scene_number}.${body.shot_number}`;
    if (body.skipped) skipped.add(key); else skipped.delete(key);
    return route.fulfill({ json: { workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', skipped: [...skipped].map(value => { const [scene_number, shot_number] = value.split('.').map(Number); return { scene_number, shot_number }; }) } });
  });
  if (multiWorkspace) {
    await page.route('**/api/story/workspaces/story-2/screenplay/revisions?**', route => route.fulfill({ json: { items: [{
      screenplay_revision_id: 'screenplay-2', accepted: true, source_revision_id: 'source-2', graph_snapshot_id: 'graph-2',
    }] } }));
    await page.route('**/api/story/workspaces/story-2/screenplay/revisions/screenplay-2', route => route.fulfill({ json: {
      screenplay_revision_id: 'screenplay-2', accepted: true, source_revision_id: 'source-2', graph_snapshot_id: 'graph-2',
      screenplay: { scenes: [{ scene_number: 1, slugline: 'EXT. HARBOR - DAY', summary: 'A boat arrives.', shots: [
        { direction:{}, shot_number: 1, action: 'A boat enters the harbor.' }, { direction:{}, shot_number: 2, action: 'The crew steps ashore.' },
      ] }] },
    } }));
    await page.route('**/api/story/workspaces/story-2/production-setup?screenplay_revision_id=screenplay-2', route => route.fulfill({ json: {
      workspace_id: 'story-2', screenplay_revision_id: 'screenplay-2', updated_at: 'setup-2', setup: {
        mode: 'assisted_manual', automate_steps: { character_images: false, character_voice: false,
          world_images: false, frame_images: false, video: false },
        video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 },
      },
    } }));
    await page.route('**/api/story/workspaces/story-2/frame-preparation-skips**', async route => {
      if (route.request().method() === 'GET') return route.fulfill({ json: { workspace_id: 'story-2', screenplay_revision_id: 'screenplay-2', skipped: [...skipped2].map(key => { const [scene_number, shot_number] = key.split('.').map(Number); return { scene_number, shot_number }; }) } });
      const body = route.request().postDataJSON();
      const key = `${body.scene_number}.${body.shot_number}`;
      if (body.skipped) skipped2.add(key); else skipped2.delete(key);
      return route.fulfill({ json: { workspace_id: 'story-2', screenplay_revision_id: 'screenplay-2', skipped: [...skipped2].map(value => { const [scene_number, shot_number] = value.split('.').map(Number); return { scene_number, shot_number }; }) } });
    });
    await page.route('**/api/story/workspaces/story-2/graph?snapshot_id=graph-2', route => route.fulfill({ json: { snapshot_id: 'graph-2', status: 'complete', records: [] } }));
    await page.route('**/api/media/story-2/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  }
  await page.route('**/api/story/workspaces/story-1/graph?snapshot_id=graph-1', route => route.fulfill({ json: {
    snapshot_id: 'graph-1', status: 'complete', records: [],
  } }));
  await page.route('**/api/media/story-1/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
}

test('fresh screenplay frame step can prepare an empty prompt without submitting image generation', async ({ page }) => {
  let prepareRequest;
  let generationSubmitted = false;
  await mockFrameImageStage(page, { prompt: '' });
  await page.route('**/api/images/prompts/prepare', async route => {
    prepareRequest ??= route.request().postDataJSON();
    return route.fulfill({ json: { workflow_id: 'z_image_turbo', asset_role: 'first_frame',
      prompt: 'A rainy station platform, Mira entering from frame left.',
      knowledge_ref: { knowledge_id: 'image-guide', guidance_version: 1, workflow_sha256: 'a'.repeat(64) },
      sources: [{ uri: 'z_image_api.json', version: 'b'.repeat(64), section: 'prompt input' }] } });
  });
  await page.route('**/api/images/jobs', route => { generationSubmitted = true; return route.fulfill({ status: 202, json: {} }); });

  await imageProject(page); await page.goto('/#/assets?step=frame_images&workspace_id=story-1');
  await expect(page.getByRole('button', { name: 'Prepare prompt' })).toBeEnabled();
  await page.getByRole('button', { name: 'Prepare prompt' }).click();
  await expect(page.getByRole('textbox', { name: 'Image prompt' })).toHaveValue('A rainy station platform, Mira entering from frame left.');
  expect(prepareRequest).toMatchObject({ workspace_id: 'story-1', workflow_id: 'z_image_turbo', asset_role: 'first_frame', prompt: '', screenplay_revision_id: 'screenplay-1', scene_number: 1, shot_number: 1 });
  expect(generationSubmitted).toBe(false);
});

test('Assisted manual frame step binds role to accepted shot and skip creates no asset', async ({ page }) => {
  let previewRequest;
  let submitted = false;
  await mockFrameImageStage(page);
  await page.route('**/api/images/validations', async route => {
    previewRequest = route.request().postDataJSON();
    return route.fulfill({ json: { workflow_id: 'z_image_turbo', workflow_version: '1', prompt: previewRequest.prompt,
      settings: { width: 1280, height: 720, steps: 8, cfg: 1 }, initial_candidate_count: 4, candidates: [] } });
  });
  await page.route('**/api/images/jobs', route => { submitted = true; return route.fulfill({ status: 202, json: { batch_id: 'unexpected', jobs: [] } }); });

  await imageProject(page); await page.goto('/#/assets?step=frame_images&workspace_id=story-1');
  await expect(page.getByRole('heading', { name: 'Clip frame step' })).toBeVisible();
  const clip = page.getByRole('combobox', { name: 'Planned clip' });
  await expect(clip.locator('option')).toHaveCount(3);
  await clip.selectOption('1.2');
  await expect(clip.locator('option').nth(2)).toContainText('Shot 2');
  await page.getByLabel('Frame role').selectOption('last_frame');
  await page.getByRole('button', { name: 'Check generation request' }).click();
  await expect(page.getByRole('heading', { name: 'Compiled preview' })).toBeVisible();
  expect(previewRequest).toMatchObject({ workspace_id: 'story-1', asset_role: 'last_frame', screenplay_revision_id: 'screenplay-1', scene_number: 1, shot_number: 2 });
  expect(previewRequest.clip_id).toMatch(/^story-[a-f0-9]{40}$/);
  expect(submitted).toBe(false);

  await page.getByRole('button', { name: 'Skip this clip’s frames' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'No image asset was created' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Check generation request' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Generate four' })).toBeDisabled();
  expect(submitted).toBe(false);
  await page.reload();
  await page.getByRole('combobox', { name: 'Planned clip' }).selectOption('1.2');
  await expect(page.getByRole('button', { name: 'Undo skip for this clip' })).toBeVisible();
  await page.getByRole('button', { name: 'Undo skip for this clip' }).click();
  await expect(page.getByRole('button', { name: 'Check generation request' })).toBeEnabled();
});

test('late frame skip responses cannot overwrite a newer workspace context or its pending state', async ({ page }) => {
  await mockFrameImageStage(page, { multiWorkspace: true });
  const pending = new Map();
  await page.route('**/api/story/workspaces/*/frame-preparation-skips', async route => {
    if (route.request().method() !== 'PUT') return route.fallback();
    const workspace = new URL(route.request().url()).pathname.split('/')[4];
    await new Promise(resolve => pending.set(workspace, resolve));
    const skipped = workspace === 'story-1'
      ? [{ scene_number: 1, shot_number: 1 }]
      : [];
    return route.fulfill({ json: { workspace_id: workspace, screenplay_revision_id: `screenplay-${workspace.slice(-1)}`, skipped } });
  });

  await imageProject(page); await page.goto('/#/assets?step=frame_images&workspace_id=story-1');
  await expect(page.getByRole('heading', { name: 'Clip frame step' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Skip this clip’s frames' })).toBeEnabled();
  await page.getByRole('button', { name: 'Skip this clip’s frames' }).click();
  await expect.poll(() => pending.has('story-1')).toBe(true);

  await page.evaluate(() => window.dispatchEvent(new CustomEvent('vibe-project-select',{detail:'story-2'})));
  await expect.poll(()=>page.evaluate(()=>localStorage.getItem('vibe-project-installed'))).toBe('story-2');
  await expect(page.getByRole('button', { name: 'Undo skip for this clip' })).toBeEnabled();
  await page.getByRole('button', { name: 'Undo skip for this clip' }).click();
  await expect.poll(() => pending.has('story-2')).toBe(true);

  pending.get('story-1')();
  const currentSave = page.getByRole('button', { name: 'Saving…' });
  await expect(currentSave).toBeDisabled();
  pending.get('story-2')();
  await expect(page.getByRole('button', { name: 'Skip this clip’s frames' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Undo skip for this clip' })).toHaveCount(0);
});

test('checked frame automation calls the stage admission endpoint and never submits a manual batch', async ({ page }) => {
  let stageRequest;
  await mockFrameImageStage(page, { automated: true });
  let submitted = false;
  await page.route('**/api/images/automated-stage', async route => {
    stageRequest = route.request().postDataJSON();
    return route.fulfill({ status: 202, json: { run_id: 'image-run', step: 'frame_images', target_count: 2,
      batches: [{ batch_id: 'image-batch', reused: false, jobs: [{ job_id: 'frame-job', candidate_index: 1,
        asset_role: 'last_frame', status: 'queued', output_asset_id: null, settings: { lineage: { target_name: 'Station · shot 1.1 · ending frame' } } }] }] } });
  });
  await page.route('**/api/images/batches/image-batch?**', route => route.fulfill({ json: {
    batch_id: 'image-batch', generation_policy: {}, jobs: [{ job_id: 'frame-job', candidate_index: 1,
      asset_role: 'last_frame', status: 'queued', output_asset_id: null, settings: { lineage: { target_name: 'Station · shot 1.1 · ending frame' } } }],
  } }));
  await page.route('**/api/images/jobs', route => { submitted = true; return route.fulfill({ status: 202, json: { batch_id: 'unexpected', jobs: [] } }); });
  await imageProject(page); await page.goto('/#/assets?step=frame_images&workspace_id=story-1');
  await expect(page.getByRole('heading', { name: 'Clip frame step' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'Clip frame generation is automated from the saved setup' }).first()).toBeVisible();
  await expect.poll(() => stageRequest).toEqual({ workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', step: 'frame_images' });
  await expect(page.getByText('Director review selects at most one first frame and one last frame per clip.')).toBeVisible();
  await expect(page.getByText('Station · shot 1.1 · ending frame · candidate 1')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Check generation request' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Generate four' })).toBeDisabled();
  expect(submitted).toBe(false);
});

test('same-page image-stage and workspace handoff reloads context before automated admission', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('vibe-image-draft-v1', JSON.stringify({
    workspaceId: 'story-1', role: 'character_master', workflowId: 'z_image_turbo', prompt: '', seed: 42,
  })));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: false } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: false } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [
    { workspace_id: 'story-1', title: 'First story' }, { workspace_id: 'story-2', title: 'Second story' },
  ], total: 2 } }));
  await page.route('**/api/story/workspaces/*/screenplay/revisions?**', route => {
    const workspace = new URL(route.request().url()).pathname.split('/')[4];
    const screenplay = workspace === 'story-1' ? 'screenplay-1' : 'screenplay-2';
    return route.fulfill({ json: { items: [{ screenplay_revision_id: screenplay, accepted: true,
      source_revision_id: `source-${workspace}`, graph_snapshot_id: `graph-${workspace}` }], total: 1 } });
  });
  await page.route('**/api/story/workspaces/*/screenplay/revisions/*', route => {
    const parts = new URL(route.request().url()).pathname.split('/');
    const workspace = parts[4];
    const screenplay = parts[7];
    return route.fulfill({ json: { screenplay_revision_id: screenplay, accepted: true,
      source_revision_id: `source-${workspace}`, graph_snapshot_id: `graph-${workspace}`,
      screenplay: { scenes: [] } } });
  });
  await page.route('**/api/story/workspaces/*/production-setup?**', route => {
    const workspace = new URL(route.request().url()).pathname.split('/')[4];
    const automatedStep = workspace === 'story-1' ? 'character_images' : 'world_images';
    return route.fulfill({ json: { workspace_id: workspace, screenplay_revision_id: `screenplay-${workspace.slice(-1)}`,
      setup: { mode: 'assisted_manual', automate_steps: {
        character_images: automatedStep === 'character_images', character_voice: false,
        world_images: automatedStep === 'world_images', frame_images: false, video: false,
      }, video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 6 } } } });
  });
  const graphRequests = [];
  await page.route('**/api/story/workspaces/*/graph?snapshot_id=*', route => {
    const workspace = new URL(route.request().url()).pathname.split('/')[4];
    const snapshot = new URL(route.request().url()).searchParams.get('snapshot_id');
    graphRequests.push({ workspace, snapshot });
    return route.fulfill({ json: { snapshot_id: `graph-${workspace}`, status: 'complete', records: [
      { record_id: `character-${workspace}`, kind: 'entity', type: 'character', name: `Character ${workspace}` },
      { record_id: `location-${workspace}`, kind: 'entity', type: 'location', name: `Location ${workspace}` },
    ] } });
  });
  await page.route('**/api/media/*/assets?kind=image', route => route.fulfill({ json: { assets: [], total: 0 } }));
  const admissions = [];
  await page.route('**/api/images/automated-stage', async route => {
    const body = route.request().postDataJSON(); admissions.push(body);
    return route.fulfill({ status: 202, json: { run_id: `${body.workspace_id}-${body.step}`, step: body.step,
      target_count: 0, batches: [] } });
  });

  await imageProject(page); await page.goto('/#/assets?step=character_images&workspace_id=story-1');
  await expect(page.getByRole('heading', { name: 'Character image step' })).toBeVisible();
  await expect.poll(() => admissions).toEqual([{ workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', step: 'character_images' }]);

  await page.evaluate(() => window.dispatchEvent(new CustomEvent('vibe-project-select',{detail:'story-2'})));
  await expect(page).toHaveURL(/step=character_images/);
  await expect(page.getByRole('combobox', { name: 'Character target' })).toContainText('Character story-2');
  await expect.poll(() => admissions).toEqual([
    { workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', step: 'character_images' },
  ]);

  await page.evaluate(() => { window.location.hash = '#/assets?step=world_images&workspace_id=story-2'; });
  await expect(page.getByRole('heading', { name: 'Scene background step' })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Image generation workspace' })).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: 'Location target' })).toContainText('Location story-2');
  await expect.poll(() => admissions).toEqual([
    { workspace_id: 'story-1', screenplay_revision_id: 'screenplay-1', step: 'character_images' },
    { workspace_id: 'story-2', screenplay_revision_id: 'screenplay-2', step: 'world_images' },
  ]);
  expect(graphRequests).toContainEqual({ workspace: 'story-1', snapshot: 'graph-story-1' });
  expect(graphRequests).toContainEqual({ workspace: 'story-2', snapshot: 'graph-story-2' });
});

test('story character prompts follow target and workflow and preserve director edits', async ({ page }) => {
  const drafts = [];
  let guidanceId = 'k';
  let jobs = 0;
  let savedSetup;
  const setup = { mode: 'assisted_manual', automate_steps: { character_images: true, character_voice: true, world_images: true, frame_images: true, video: true },
    video_quality: 'high', duration_policy: { kind: 'fixed', seconds: 5 },
    image_stage_settings: Object.fromEntries(['character_images', 'world_images', 'frame_images'].map(step => [step, { workflow_id: 'z_image_turbo', width: 1280, height: 720, steps: 8, cfg: 1 }])) };
  await page.route('**/api/**', route => route.fulfill({ status:404,json:{error:{message:'Unused fixture route'}} }));
  await page.route('**/api/images/workflows**', route => route.fulfill({ json: { workflows: ['z_image_turbo','qwen_image_2512'].map(workflow_id => ({ workflow_id, prompt_knowledge_ref: { knowledge_id: guidanceId, guidance_version: 1, workflow_sha256: 'a' }, label: workflow_id, available: true, automation_available: false, defaults: { width: 1280, height: 720, steps: 8, cfg: 1 } })), gpu_admission: { available: true } } }));
  await page.route('**/api/video/runtime', route => route.fulfill({ json: { safe_to_submit: true } }));
  await page.route('**/api/images/worker', route => route.fulfill({ json: { available: true } }));
  await page.route('**/api/story/workspaces?**', route => route.fulfill({ json: { items: [{ workspace_id: 'story-test', title: 'Harbor Light' }], total: 1 } }));
  await page.route('**/api/media/story-test/assets**', route => route.fulfill({ json: { assets: [], total: 0 } }));
  await page.route('**/api/story/workspaces/story-test/screenplay/revisions?**', route => route.fulfill({ json: { items: [{ screenplay_revision_id: 'screenplay-1', accepted: true, stale: false }], total: 1 } }));
  await page.route('**/api/story/workspaces/story-test/screenplay/revisions/screenplay-1', route => route.fulfill({ json: { screenplay_revision_id: 'screenplay-1', graph_snapshot_id: 'graph-1', screenplay: { scenes: [] } } }));
  await page.route('**/api/story/workspaces/story-test/graph?snapshot_id=graph-1', route => route.fulfill({ json: { snapshot_id: 'graph-1', records: ['Ivo','Mara'].map(name => ({ record_id: name, kind: 'entity', type: 'character', name, detail: `${name} in the harbor` })) } }));
  await page.route('**/api/story/workspaces/story-test/production-setup**', async route => {
    if (route.request().method() === 'PUT') {
      const incoming = route.request().postDataJSON().setup;
      if (Object.keys(incoming.image_stage_settings || {}).some(step => !incoming.automate_steps[step]))
        return route.fulfill({ status: 400, json: { error: { message: 'Image settings may only be provided for automated image steps.' } } });
      savedSetup = incoming;
    }
    return route.fulfill({ json: { setup: savedSetup || setup } });
  });
  await page.route('**/api/story/workspaces/story-test/assisted-stage-skips**', route => route.fulfill({ json: { skipped: [] } }));
  await page.route('**/api/images/automated-stage', route => route.fulfill({ status: 503, json: { error: 'Run this workflow manually once' } }));
  await page.route('**/api/images/prompts/prepare', async route => {
    const body = route.request().postDataJSON(); drafts.push(body);
    if (body.target_record_id === 'Mara' && drafts.filter(x => x.target_record_id === 'Mara').length === 1)
      return route.fulfill({ status: 503, json: { error: { message: 'temporary provider failure' } } });
    return route.fulfill({ json: { workflow_id: body.workflow_id, prompt: `${body.target_record_id} for ${body.workflow_id}`, knowledge_ref: { knowledge_id: guidanceId, guidance_version: 1, workflow_sha256: 'a' }, sources: [] } });
  });
  await page.route('**/api/images/jobs', route => { jobs++; return route.fulfill({ status: 500, json: {} }); });
  await imageProject(page); await page.goto('/#/assets?step=character_images&workspace_id=story-test');
  const prompt = page.getByRole('textbox', { name: 'Image prompt', exact: true });
  await expect(page.getByRole('combobox', { name: 'Frame role' })).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: 'Character target', exact: true })).toHaveValue('Ivo');
  await expect(prompt).toHaveValue('Ivo for z_image_turbo');
  await prompt.fill('Director edited Ivo');
  await page.getByRole('combobox', { name: 'Character target', exact: true }).selectOption('Mara');
  await expect(page.getByText(/Prompt was not prepared:.*temporary provider failure/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Prepare prompt', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Prepare prompt', exact: true }).click();
  await expect(prompt).toHaveValue('Mara for z_image_turbo');
  await page.getByRole('combobox', { name: 'Character target', exact: true }).selectOption('Ivo');
  await expect(prompt).toHaveValue('Director edited Ivo');
  await page.getByRole('combobox', { name: 'Image workflow', exact: true }).selectOption('qwen_image_2512');
  await expect(prompt).toHaveValue('Ivo for qwen_image_2512');
  await page.getByRole('combobox', { name: 'Image workflow', exact: true }).selectOption('z_image_turbo');
  await expect(prompt).toHaveValue('Director edited Ivo');
  await page.getByRole('button', { name: 'Use manual generation for this stage' }).click();
  await expect(page.getByRole('button', { name: 'Generate four', exact: true })).toBeEnabled();
  expect(savedSetup).toEqual({ ...setup, automate_steps: { ...setup.automate_steps, character_images: false }, image_stage_settings: { world_images: setup.image_stage_settings.world_images, frame_images: setup.image_stage_settings.frame_images } });
  expect(drafts[0]).toMatchObject({ screenplay_revision_id: 'screenplay-1', target_record_id: 'Ivo', asset_role: 'character_master', prompt: '' });
  expect(jobs).toBe(0);
  await page.reload();
  await expect(prompt).toHaveValue('Director edited Ivo');
  await expect(page.getByRole('button', { name: 'Use manual generation for this stage' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Generate four', exact: true })).toBeEnabled();
  const beforeUpdate = drafts.length;
  guidanceId = 'updated-guidance';
  await page.reload();
  await expect(prompt).toHaveValue('Ivo for z_image_turbo');
  await expect.poll(() => drafts.length).toBeGreaterThan(beforeUpdate);
  expect(jobs).toBe(0);
});

for (const targetKind of ['character','location']) test(`${targetKind} master replacement, candidate counts and optional views use frozen targets`, async ({ page }) => {
  const role = targetKind === 'character' ? 'character_master' : 'world_master';
  const routeName = targetKind === 'character' ? 'characters' : 'worlds';
  const targetLabel = targetKind === 'character' ? 'Character target' : 'Location target';
  const viewRole = targetKind === 'character' ? 'character_view' : 'world_view';
  const lineage = {screenplay_revision_id:'screenplay-1',target_type:targetKind,target_record_id:'first',target_name:'First'};
  const assets = [1,2].map(n=>({asset_id:`pa-${n}`,filename:`candidate-${n}.png`,sha256:'a'.repeat(64),kind:'image',roles:[role],content_url:`/candidate-${n}.png`,metadata:{production_image_job:{intended_role:role,settings:{lineage}}}}));
  const batch = {batch_id:'batch-1',jobs:assets.map((asset,index)=>({job_id:`job-${index+1}`,asset_role:role,candidate_index:index+1,status:'completed',output_asset_id:asset.asset_id,settings:{lineage}}))};
  let selected='pa-2'; let failSideViews=true; const drafts=[]; const validations=[]; const submissions=[];
  await page.addInitScript(({role})=>{if(!localStorage.getItem('seeded')) {localStorage.setItem('seeded','yes');localStorage.setItem('vibe-story-selected-v1','story-test');localStorage.setItem('vibe-image-draft-v1',JSON.stringify({workspaceId:'story-test',role,workflowId:'z_image_turbo',targetRecordId:'first',seed:42}));localStorage.setItem('vibe-image-active-v1',JSON.stringify({workspaceId:'story-test',batchId:'batch-1'}));}}, {role});
  await page.route('**/api/**',r=>r.fulfill({status:404,json:{error:{message:'Unused fixture route'}}}));
  await page.route('**/api/images/workflows**',r=>r.fulfill({json:{workflows:['z_image_turbo','qwen_image_multi_angle_2511'].map(workflow_id=>({workflow_id,label:workflow_id,available:true,defaults:{width:1280,height:720,steps:8,cfg:1}})),gpu_admission:{available:true}}}));
  await page.route('**/api/video/runtime',r=>r.fulfill({json:{safe_to_submit:true}}));
  await page.route('**/api/images/worker',r=>r.fulfill({json:{available:true}}));
  await page.route('**/api/story/workspaces?**',r=>r.fulfill({json:{items:[{workspace_id:'story-test',title:'Test'}]}}));
  await page.route('**/api/media/story-test/assets**',r=>r.fulfill({json:{assets,total:2}}));
  await page.route('**/api/story/workspaces/story-test/screenplay/revisions?**',r=>r.fulfill({json:{items:[{screenplay_revision_id:'screenplay-1',accepted:true,stale:false}]}}));
  await page.route('**/api/story/workspaces/story-test/screenplay/revisions/screenplay-1',r=>r.fulfill({json:{screenplay_revision_id:'screenplay-1',graph_snapshot_id:'graph-1',screenplay:{scenes:[]}}}));
  await page.route('**/api/story/workspaces/story-test/graph?**',r=>r.fulfill({json:{snapshot_id:'graph-1',records:['first','second'].map(record_id=>({record_id,name:record_id,kind:'entity',type:targetKind,detail:'Saved facts'}))}}));
  await page.route('**/api/story/workspaces/story-test/production-setup**',r=>r.fulfill({json:{setup:{mode:'assisted_manual',automate_steps:{character_images:false,world_images:false,frame_images:false}}}}));
  await page.route('**/api/story/workspaces/story-test/assisted-stage-skips**',r=>r.fulfill({json:{skipped:[]}}));
  await page.route('**/api/story/workspaces/story-test/voice-bindings?**',r=>r.fulfill({json:{screenplay_revision_id:'screenplay-1',characters:[{record_id:'first',name:'First',type:'character'}],bindings:[]}}));
  await page.route('**/api/audio/voices',r=>r.fulfill({json:[]}));
  await page.route('**/api/images/selections?**',r=>r.fulfill({json:{selection:{asset_id:new URL(r.request().url()).searchParams.get('target_record_id')==='first'?selected:''}}}));
  await page.route('**/api/images/batches/**',r=>r.fulfill({json:batch}));
  await page.route('**/api/images/jobs/*/accept',r=>{const n=r.request().url().includes('job-1')?1:2;selected=`pa-${n}`;return r.fulfill({json:{asset:assets[n-1],target_selection:{asset_id:selected}}});});
  await page.route('**/api/images/prompts/prepare',async r=>{const body=r.request().postDataJSON();drafts.push(body);if(body.asset_role===viewRole&&failSideViews){await new Promise(resolve=>setTimeout(resolve,400));return r.fulfill({status:503,json:{error:{message:'side view draft failed'}}});}if(body.target_record_id==='second'&&drafts.filter(x=>x.target_record_id==='second').length===1)return r.fulfill({status:503,json:{error:{message:'temporary draft failure'}}});return r.fulfill({json:{workflow_id:body.workflow_id,prompt:`${body.target_record_id} ${body.asset_role} draft`,knowledge_ref:{knowledge_id:'k',guidance_version:1,workflow_sha256:'a'},sources:[]}});});
  await page.route('**/api/images/validations',r=>{validations.push(r.request().postDataJSON());return r.fulfill({json:{candidates:[]}});});
  await page.route('**/api/images/jobs',r=>{submissions.push(r.request().postDataJSON());return r.fulfill({status:202,json:batch});});
  await imageProject(page); await page.goto(`/#/${routeName}`);
  const prompt=page.getByRole('textbox',{name:'Image prompt',exact:true});
  await expect(prompt).toHaveValue(`first ${role} draft`);
  await expect(page.getByRole('button',{name:'Selected',exact:true})).toHaveCount(1);
  if(targetKind==='character') await expect(page.getByRole('img',{name:'First reference',exact:true})).toHaveAttribute('src','/candidate-2.png');
  await page.getByRole('button',{name:targetKind==='character'?'Use as Character image':'Use as Scene background / base location',exact:true}).click();
  await expect(page.getByRole('button',{name:'Selected',exact:true})).toHaveCount(1);
  expect(selected).toBe('pa-1');
  if(targetKind==='character') await expect(page.getByRole('img',{name:'First reference',exact:true})).toHaveAttribute('src','/candidate-1.png');
  await page.getByRole('combobox',{name:targetLabel,exact:true}).selectOption('second');
  await expect(page.getByText(/Prompt was not prepared:.*temporary draft failure/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Prepare prompt',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Prepare prompt',exact:true}).click();
  await expect(prompt).toHaveValue(`second ${role} draft`);
  // Selecting a candidate from the previous batch still uses its original first target.
  await page.getByRole('button',{name:targetKind==='character'?'Use as Character image':'Use as Scene background / base location',exact:true}).click();
  expect(selected).toBe('pa-2');
  await page.getByRole('combobox',{name:targetLabel,exact:true}).selectOption('first');
  await page.getByRole('combobox',{name:'Number of candidates'}).selectOption('1');
  await page.getByRole('button',{name:'Check generation request',exact:true}).click();
  expect(validations.at(-1).initial_candidate_count).toBe(1);
  await page.getByRole('combobox',{name:'Number of candidates'}).selectOption('8');
  await page.getByRole('button',{name:'Generate 8 images',exact:true}).click();
  await expect.poll(()=>submissions.length).toBe(1);
  expect(submissions[0]).toMatchObject({initial_candidate_count:8,asset_role:role,target_record_id:'first'});
  await page.reload();
  await expect(page.getByRole('combobox',{name:'Number of candidates'})).toHaveValue('8');
  await expect(page.getByRole('button',{name:'Selected',exact:true})).toHaveCount(1);
  await page.getByRole('button',{name:'Prepare side views from selected master'}).click();
  const sideViews=page.getByRole('region',{name:'Optional side views'});
  await expect(sideViews.getByRole('button',{name:'Preparing side views…'})).toBeDisabled();
  await expect(sideViews.getByText(/Prompt was not prepared:.*side view draft failed/)).toBeVisible();
  failSideViews=false;
  await sideViews.getByRole('button',{name:'Prepare side views from selected master'}).click();
  await expect(prompt).toHaveValue(`first ${viewRole} draft`);
  expect(drafts.at(-1)).toMatchObject({asset_role:viewRole,target_record_id:'first',source_references:[{asset_id:'pa-2',sha256:'a'.repeat(64)}]});
  await expect(page.getByRole('button',{name:'Generate 4 views',exact:true})).toBeEnabled();
});

for (const savedRetry of [false, true]) {
  test(`stale image guidance unlocks preparation without another saved retry (${savedRetry ? 'saved' : 'fresh'})`, async ({ page }) => {
    const oldRef = { knowledge_id: 'old', guidance_version: 5, workflow_sha256: 'a'.repeat(64) };
    const newRef = { ...oldRef, knowledge_id: 'current', guidance_version: 6 };
    const frozen = { workflow_id: 'z_image_turbo', workspace_id: 'workspace-image', prompt: 'Existing portrait',
      asset_role: 'character_master', seed: 42, control_mode: 'assisted_manual', idempotency_key: 'old-retry',
      output_prefix: 'workspace-image/character_master', prompt_knowledge_ref: oldRef };
    await page.addInitScript(({ frozen, savedRetry }) => {
      localStorage.setItem('vibe-image-draft-v1', JSON.stringify({ workspaceId: frozen.workspace_id,
        role: frozen.asset_role, workflowId: frozen.workflow_id, prompt: frozen.prompt, seed: 42,
        promptKnowledge: { workflow_id: frozen.workflow_id, knowledge_ref: frozen.prompt_knowledge_ref, sources: [] } }));
      if (savedRetry) localStorage.setItem('vibe-image-pending-request-v1', JSON.stringify(frozen));
    }, { frozen, savedRetry });
    await page.route('**/api/images/workflows**', r => r.fulfill({ json: { workflows: [{
      workflow_id: 'z_image_turbo', label: 'Z-Image Turbo', available: true, version: '1',
      prompt_knowledge_ref: newRef, defaults: { width: 1280, height: 720, steps: 8, cfg: 1 } }],
      gpu_admission: { available: true, checked: true } } }));
    await page.route('**/api/video/runtime', r => r.fulfill({ json: { safe_to_submit: true } }));
    await page.route('**/api/images/worker', r => r.fulfill({ json: { available: true } }));
    await page.route('**/api/story/workspaces?**', r => r.fulfill({ json: { items: [], total: 0 } }));
    await page.route('**/api/media/workspace-image/assets?kind=image', r => r.fulfill({ json: { assets: [] } }));
    await page.route('**/api/images/validations', r => r.fulfill({ json: { candidates: [], generation_policy: {} } }));
    await page.route('**/api/images/prompts/prepare', r => r.fulfill({ json: {
      workflow_id: 'z_image_turbo', prompt: 'Reviewed current portrait', knowledge_ref: newRef, sources: [] } }));
    const submissions = [];
    await page.route('**/api/images/jobs', r => {
      const body = r.request().postDataJSON(); submissions.push(body);
      return body.prompt_knowledge_ref.knowledge_id === 'old'
        ? r.fulfill({ status: 409, json: { error: { code: 'image_prompt_guidance_changed', message: 'Workflow guidance changed' }, admission_state: 'not_created' } })
        : r.fulfill({ status: 202, json: { batch_id: 'new-guidance', jobs: [] } });
    });
    await page.route('**/api/images/batches/new-guidance?**', r => r.fulfill({ json: { batch_id: 'new-guidance', jobs: [] } }));
    await imageProject(page); await page.goto('/#/assets');
    await page.getByRole('button', { name: savedRetry ? 'Resume saved request' : 'Generate four' }).click();
    await expect(page.getByText(/No job was queued/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Discard saved retry' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Generate four' })).toBeDisabled();
    expect(await page.evaluate(() => localStorage.getItem('vibe-image-pending-request-v1'))).toBeNull();
    await page.getByRole('button', { name: 'Prepare prompt' }).click();
    await expect(page.locator('.image-prompt-label textarea')).toHaveValue('Reviewed current portrait');
    await page.getByRole('button', { name: 'Generate four' }).click();
    await expect(page.getByRole('status').filter({hasText:'Candidate batch queued'})).toBeVisible();
    expect(submissions).toHaveLength(2);
    expect(submissions[1].prompt_knowledge_ref).toEqual(newRef);
    expect(submissions[1].idempotency_key).not.toBe(submissions[0].idempotency_key);
  });
}

async function imageProject(page) {
  await mockProject(page,undefined,'vibe-image-draft-v1');
  await page.route('**/api/director/settings',r=>r.fulfill({json:{settings:{provider:'codex',model:'fixture',lessons:[]},models:[]}}));
  await page.route('**/api/studio-tools/loras',r=>r.fulfill({json:{loras:[]}}));
  await page.route('**/api/studio-tools/loras/checkpoints',r=>r.fulfill({json:{checkpoints:[]}}));
  await page.route('**/api/studio-tools/output-destination',route=>route.fulfill({json:{mode:'default',path:'/fixture/images',available:true}}));
}
