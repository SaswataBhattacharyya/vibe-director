import { test, expect } from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

test('style-stale screenplay redraft gets a new request key and clears the stale state', async ({ page }) => {
  const oldRequestKey = 'interrupted-before-style-change';
  const source = { revision_id: 'source-1', source_text: 'Mira finds a key.', source_sha256: 'source-hash' };
  const graph = { snapshot_id: 'graph-1', source_revision_id: source.revision_id, status: 'complete', chunk_total: 1, chunk_complete: 1, chunks: [{ chunk_id: 'chunk-1', chunk_index: 1, state: 'complete' }], records: [] };
  const screenplayBody = { title: 'The Key', scenes: [{ scene_number: 1, slugline: 'INT. ROOM - DAY', summary: 'Mira finds a key.', shots: [{ shot_number: 1, action: 'Mira finds a key.', dialogue: '', direction: { camera: '', lighting: '', mood: '', sfx: '', music: '' }, evidence: [], evidence_record_ids: [], character_record_ids: [] }] }] };
  let revisions = [{ screenplay_revision_id: 'screenplay-old', workspace_id: 'story-style', source_revision_id: source.revision_id, graph_snapshot_id: graph.snapshot_id, style_selection_snapshot_id: 'style-old', screenplay: screenplayBody, created_at: '2026-10-12' }];
  let postedKey;
  let workspaceReads = 0;
  await page.addInitScript(key => {
    localStorage.setItem('vibe-story-selected-v1', 'story-style');
    localStorage.setItem('vibe-screenplay-task:story-style:source-1', key);
  }, oldRequestKey);
  await page.route('**/api/story/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    if (path === '/api/story/workspaces/story-style' && req.method() === 'GET') { workspaceReads += 1; return route.fulfill({ json: { workspace_id: 'story-style', title: 'Style recovery', current_revision_id: source.revision_id, style_selection_snapshot_id: workspaceReads === 1 ? 'style-old' : 'style-new' } }); }
    if (path === '/api/story/workspaces/story-style/screenplay/revisions' && req.method() === 'GET') return route.fulfill({ json: { items: revisions.map(item => ({ ...item, stale: item.style_selection_snapshot_id !== 'style-new', accepted: false })), limit: 50, offset: 0, total: revisions.length } });
    if (path === '/api/story/workspaces/story-style/screenplay' && req.method() === 'GET') return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'No screenplay for current style' } } });
    if (path === '/api/story/workspaces/story-style/screenplay/revisions/screenplay-old' && req.method() === 'GET') return route.fulfill({ json: revisions[0] });
    if (path === '/api/story/workspaces/story-style/graph' && req.method() === 'GET') return route.fulfill({ json: graph });
    if (path === '/api/story/workspaces/story-style/screenplay' && req.method() === 'POST') {
      const body = req.postDataJSON(); postedKey = body.idempotency_key;
      const fresh = { ...revisions[0], screenplay_revision_id: 'screenplay-new', style_selection_snapshot_id: 'style-new', screenplay: screenplayBody };
      revisions = [fresh, ...revisions];
      return route.fulfill({ status: 201, json: { ...fresh, chunk_total: 1, chunk_complete: 1 } });
    }
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: `Unexpected ${req.method()} ${path}` } } });
  });

  await mockProject(page,'story-style');
  await page.goto('/#/screenplay');
  await expect(page.getByRole('status').filter({ hasText: 'pinned production type or directing style changed' })).toBeVisible();
  expect(postedKey).toBeUndefined();
  await page.getByRole('button', { name: 'Generate new revision' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Draft saved.' })).toBeVisible();
  expect(postedKey).toBeTruthy();
  expect(postedKey).not.toBe(oldRequestKey);
  expect(workspaceReads).toBeGreaterThanOrEqual(2);
  await expect(page.getByText('Screenplay revision screenplay-new · style style-new')).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'pinned production type or directing style changed' })).toHaveCount(0);
});
