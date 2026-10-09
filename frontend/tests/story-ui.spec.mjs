import { test, expect } from '@playwright/test';

const pageOf = (items, offset = 0, total = items.length) => ({ items, limit: 50, offset, total });

test('import preview is editable, explicitly applied, saved as a revision, and reloads without a POST', async ({ page }) => {
  let workspace = null;
  const calls = [];
  await page.route('**/api/story/**', async route => {
    const req = route.request(), url = new URL(req.url()); calls.push(`${req.method()} ${url.pathname}`);
    if (url.pathname === '/api/story/workspaces' && req.method() === 'GET') return route.fulfill({ json: pageOf(workspace ? [{ workspace_id: workspace.workspace_id, title: workspace.title, current_revision_id: workspace.current_revision_id, initialized: true, status: 'ready' }] : []) });
    if (url.pathname === '/api/story/imports' && req.method() === 'POST') return route.fulfill({ json: { import_id: 'imp-1', filename: 'draft.txt', source_type: 'text/plain', source_sha256: 'abc123', text_sha256: 'def456', text: 'Extracted original\r\ntext', warnings: [], pages: [] } });
    if (url.pathname === '/api/story/imports/imp-1/apply') {
      workspace = { workspace_id: 'story-1', title: req.postDataJSON().title, initialized: true, status: 'ready', current_revision: { revision_id: 'rev-1', source_text: req.postDataJSON().source_text } };
      return route.fulfill({ json: workspace });
    }
    if (url.pathname === '/api/story/workspaces/story-1' && req.method() === 'GET') return route.fulfill({ json: workspace });
    if (url.pathname === '/api/story/workspaces/story-1/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf(workspace ? [{ revision_id: workspace.current_revision.revision_id, source_sha256: 'sha', revision_number: 1, created_at: 'now' }] : []) });
    if (url.pathname === '/api/story/workspaces/story-1/revisions' && req.method() === 'POST') {
      workspace = { ...workspace, current_revision_id: 'rev-2', current_revision: { revision_id: 'rev-2', source_text: req.postDataJSON().source_text } };
      return route.fulfill({ json: workspace.current_revision });
    }
    return route.fulfill({ status: 404, json: { detail: 'Unexpected story API request' } });
  });
  await page.goto('/#/story');
  await page.locator('input[type="file"]').setInputFiles({ name: 'draft.txt', mimeType: 'text/plain', buffer: Buffer.from('fixture') });
  await expect(page.getByLabel('Editable extracted text')).toHaveValue('Extracted original\ntext');
  await expect(page.getByText('abc123')).toBeVisible();
  await expect(page.getByText('def456')).toBeVisible();
  await expect(page.getByText(/Browser text editing normalizes line endings to LF/)).toBeVisible();
  expect(calls.some(call => call === 'POST /api/story/imports')).toBeTruthy();
  expect(calls.some(call => call.includes('/apply'))).toBe(false);
  await page.getByLabel('Editable extracted text').fill('Edited extracted text');
  await page.waitForFunction(() => JSON.parse(localStorage.getItem('vibe-story-ui-draft-v1') || '{}').importPreview?.text === 'Edited extracted text');
  await page.reload();
  await expect(page.getByLabel('Editable extracted text')).toHaveValue('Edited extracted text');
  expect(calls.some(call => call.includes('/apply'))).toBe(false);
  await page.getByRole('button', { name: 'Apply import as new workspace' }).click();
  await expect(page.getByLabel('Story source text')).toHaveValue('Edited extracted text');
  await page.getByLabel('Story source text').fill('Saved revision text');
  await page.getByRole('button', { name: 'Save revision' }).click();
  await expect(page.getByText('New story revision saved.')).toBeVisible();
  const postsBeforeReload = calls.filter(call => call.startsWith('POST ')).length;
  await page.reload();
  await expect(page.getByLabel('Story source text')).toHaveValue('Saved revision text');
  expect(calls.filter(call => call.startsWith('POST ')).length).toBe(postsBeforeReload);
});

test('stale revision conflict keeps the local draft and does not overwrite server state', async ({ page }) => {
  const workspace = { workspace_id: 'story-2', title: 'Concurrent story', current_revision_id: 'rev-server', initialized: true, status: 'ready', current_revision: { revision_id: 'rev-server', source_text: 'Server text' } };
  await page.addInitScript(() => {
    localStorage.setItem('vibe-story-selected-v1', 'story-2');
    localStorage.setItem('vibe-story-draft-v1', JSON.stringify({ 'story-2': { workspaceId: 'story-2', sourceText: 'My preserved local draft', baseRevisionId: 'rev-old' } }));
  });
  const posts = [];
  await page.route('**/api/story/**', async route => {
    const req = route.request(), url = new URL(req.url());
    if (url.pathname === '/api/story/workspaces' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ workspace_id: 'story-2', title: workspace.title, current_revision_id: 'rev-server', initialized: true, status: 'ready' }]) });
    if (url.pathname === '/api/story/workspaces/story-2' && req.method() === 'GET') return route.fulfill({ json: workspace });
    if (url.pathname === '/api/story/workspaces/story-2/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ revision_id: 'rev-server', source_sha256: 'sha', revision_number: 2, created_at: 'now' }]) });
    if (url.pathname === '/api/story/workspaces/story-2/revisions' && req.method() === 'POST') { posts.push(req.postDataJSON()); return route.fulfill({ status: 409, json: { error: { code: 'stale_revision', message: 'revision conflict' } } }); }
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto('/#/story');
  await expect(page.getByLabel('Story source text')).toHaveValue('My preserved local draft');
  await page.getByRole('button', { name: 'Save revision' }).click();
  await expect(page.getByRole('alert')).toContainText('Your draft is preserved and was not overwritten');
  await expect(page.getByLabel('Story source text')).toHaveValue('My preserved local draft');
  expect(posts).toEqual([{ source_text: 'My preserved local draft', expected_current_revision_id: 'rev-old' }]);
});


test('initializing workspace is unavailable and can be checked again', async ({ page }) => {
  let allowReady = false;
  const ready = { workspace_id: 'story-pending', title: 'Pending', current_revision_id: 'rev-1', initialized: true, status: 'ready', current_revision: { revision_id: 'rev-1', source_text: 'Ready text' } };
  await page.route('**/api/story/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/story/workspaces' && route.request().method() === 'GET') return route.fulfill({ json: pageOf([{ workspace_id: 'story-pending', title: 'Pending', current_revision_id: null, initialized: false, status: 'initializing' }]) });
    if (url.pathname === '/api/story/workspaces/story-pending' && route.request().method() === 'GET') {
      return route.fulfill({ json: allowReady ? ready : { workspace_id: 'story-pending', title: 'Pending', current_revision_id: null, initialized: false, status: 'initializing' } });
    }
    if (url.pathname === '/api/story/workspaces/story-pending/revisions') return route.fulfill({ json: pageOf([{ revision_id: 'rev-1', source_sha256: 'sha', revision_number: 1 }]) });
    return route.fulfill({ status: 404, json: {} });
  });
  await page.addInitScript(() => { localStorage.setItem('vibe-story-selected-v1', 'story-pending'); });
  await page.goto('/#/story');
  await expect(page.getByText('This workspace is still initializing.', { exact: false })).toBeVisible();
  await expect(page.getByLabel('Story source text')).toHaveCount(0);
  allowReady = true;
  await page.getByRole('button', { name: 'Refresh workspace' }).click();
  await expect(page.getByLabel('Story source text')).toHaveValue('Ready text');
});


test('storage failure keeps editing responsive and offers a downloadable draft', async ({ page }) => {
  const workspace = { workspace_id: 'story-storage', title: 'Storage failure', initialized: true, status: 'ready', current_revision: { revision_id: 'rev-1', source_text: 'Start' } };
  await page.addInitScript(() => {
    localStorage.setItem('vibe-story-selected-v1', 'story-storage');
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function(key, value) { if (key.startsWith('vibe-story-')) throw new DOMException('quota exceeded', 'QuotaExceededError'); return original.call(this, key, value); };
  });
  await page.route('**/api/story/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/story/workspaces' && route.request().method() === 'GET') return route.fulfill({ json: pageOf([{ workspace_id: workspace.workspace_id, title: workspace.title, current_revision_id: 'rev-1', initialized: true, status: 'ready' }]) });
    if (url.pathname === '/api/story/workspaces/story-storage' && route.request().method() === 'GET') return route.fulfill({ json: workspace });
    if (url.pathname === '/api/story/workspaces/story-storage/revisions') return route.fulfill({ json: pageOf([{ revision_id: 'rev-1', source_sha256: 'sha', revision_number: 1 }]) });
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto('/#/story');
  await page.getByLabel('Story source text').fill('Still editable without browser storage');
  await expect(page.getByRole('alert')).toContainText('Drafts may not survive reload');
  await expect(page.getByLabel('Story source text')).toHaveValue('Still editable without browser storage');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download draft text' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('Storage failure');
});
