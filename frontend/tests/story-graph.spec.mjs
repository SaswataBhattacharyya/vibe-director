import { test, expect } from '@playwright/test';

const pageOf = items => ({ items, limit: 50, offset: 0, total: items.length });

test('builds, reviews and reloads a revision-linked source graph without live provider calls', async ({ page }) => {
  let graph = null;
  const source = 'Mira keeps the key.';
  const revision = { revision_id: 'story-canon-abcdef123456', source_text: source, source_sha256: 'source-hash' };
  const calls = [];
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'story-graph'));
  await page.route('**/api/story/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    if (path === '/api/story/workspaces' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ workspace_id: 'story-graph', title: 'Graph me', current_revision_id: revision.revision_id, initialized: true, status: 'ready' }]) });
    if (path === '/api/story/workspaces/story-graph' && req.method() === 'GET') return route.fulfill({ json: { workspace_id: 'story-graph', title: 'Graph me', current_revision: revision, current_revision_id: revision.revision_id, initialized: true, status: 'ready' } });
    if (path === '/api/story/workspaces/story-graph/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ revision_id: revision.revision_id, source_sha256: 'source-hash', revision_number: 1 }]) });
    if (path === '/api/story/workspaces/story-graph/graph' && req.method() === 'GET') return graph ? route.fulfill({ json: graph }) : route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'No graph' } } });
    if (path === '/api/story/workspaces/story-graph/graph' && req.method() === 'POST') {
      const body = req.postDataJSON(); calls.push(body);
      graph = { snapshot_id: 'graph-1', idempotency_key: body.idempotency_key, workspace_id: 'story-graph', source_revision_id: revision.revision_id, source_sha256: 'source-hash', status: 'complete', coverage_state: 'all_chunks_processed_semantic_coverage_unverified', contradiction_state: 'not_assessed', chunk_total: 1, chunk_complete: 1, provider: 'codex', model: 'fake', semantic_coverage_claim: false, chunks: [{ chunk_id: 'story_chunk_0001', chunk_index: 1, state: 'complete' }], records: [{ record_id: 'record-1', kind: 'entity', type: 'character', name: 'Mira', detail: '', status: 'source_supported', confidence: 1, user_modified: false, properties: {}, evidence: [{ source_revision_id: revision.revision_id, source_sha256: 'source-hash', chunk_id: 'story_chunk_0001', start_codepoint: 0, end_codepoint: source.length, quote: source }] }] };
      return route.fulfill({ json: graph });
    }
    if (path === '/api/story/workspaces/story-graph/graph/records/record-1' && req.method() === 'PATCH') {
      const body = req.postDataJSON(); graph.records[0] = { ...graph.records[0], ...body, user_modified: true };
      return route.fulfill({ json: { record_id: 'record-1', ...body, user_modified: true } });
    }
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: `Unexpected ${req.method()} ${path}` } } });
  });
  await page.goto('/#/story');
  await page.getByRole('button', { name: 'Generate graph' }).click();
  await expect(page.getByText('story_chunk_0001: complete')).toBeVisible();
  await expect(page.getByLabel('Source-linked story graph').getByText(source)).toBeVisible();
  await page.getByLabel('Record').fill('Mira, the keeper');
  await page.getByLabel('Notes').fill('Reviewed by the writer.');
  await page.getByLabel('Review status').selectOption('user_authored');
  await page.getByRole('button', { name: 'Save review' }).click();
  await page.reload();
  await expect(page.getByLabel('Record')).toHaveValue('Mira, the keeper');
  await expect(page.getByLabel('Notes')).toHaveValue('Reviewed by the writer.');
  expect(calls).toHaveLength(1);
});
