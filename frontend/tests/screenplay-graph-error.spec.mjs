import { test, expect } from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

test('failed story preparation shows its saved error and retry preserves the graph key', async ({ page }) => {
  let graphPosts = 0, screenplayPosts = 0;
  const graph = { snapshot_id: 'graph-test', idempotency_key: 'saved-graph-key', source_revision_id: 'source-1', status: 'partial', chunk_complete: 0, chunk_total: 1, chunks: [{ chunk_id: 'story_chunk_0001', state: 'failed', error_message: 'Graph evidence quote does not exactly match its chunk span.' }], records: [] };
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'story-test'));
  await page.route('**/api/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (path === '/api/story/workspaces/story-test') return route.fulfill({ json: { workspace_id: 'story-test', current_revision_id: 'source-1' } });
    if (path.endsWith('/screenplay/revisions')) return route.fulfill({ json: { items: [], offset: 0, total: 0 } });
    if (path.endsWith('/screenplay')) {
      if (request.method() === 'POST') screenplayPosts++;
      return route.fulfill({ status: 404, json: { error: { message: 'No screenplay yet' } } });
    }
    if (path.endsWith('/graph')) {
      if (request.method() === 'POST') { graphPosts++; expect(request.postDataJSON().idempotency_key).toBe(graph.idempotency_key); }
      return route.fulfill({ json: graph });
    }
    return route.fulfill({status:404,json:{error:{message:'Unused mock endpoint'}}});
  });
  await mockProject(page,'story-test');
  await page.goto('/#/screenplay');
  await expect(page.getByRole('alert').filter({ hasText: 'Story preparation needs attention' })).toContainText('Graph evidence quote does not exactly match');
  expect(graphPosts).toBe(0);
  await page.getByRole('button', { name: 'Generate screenplay', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: '0/1 sections ready' })).toBeVisible();
  expect(graphPosts).toBe(1);
  expect(screenplayPosts).toBe(0);
});
