import { test, expect } from '@playwright/test';

const pageOf = items => ({ items, limit: 50, offset: 0, total: items.length });

test('builds, reviews and reloads a revision-linked source graph without live provider calls', async ({ page }) => {
  let graph = null;
  let screenplay = null;
  let screenplayHistory = [];
  const source = 'Mira keeps the key.\n' + '😀'.repeat(200);
  const revision = { revision_id: 'story-canon-abcdef123456', source_text: source, source_sha256: 'source-hash' };
  const calls = [];
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'story-graph'));
  await page.route('**/api/story/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    if (path === '/api/story/workspaces' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ workspace_id: 'story-graph', title: 'Graph me', current_revision_id: revision.revision_id, initialized: true, status: 'ready' }]) });
    if (path === '/api/story/workspaces/story-graph' && req.method() === 'GET') return route.fulfill({ json: { workspace_id: 'story-graph', title: 'Graph me', current_revision: revision, current_revision_id: revision.revision_id, initialized: true, status: 'ready' } });
    if (path === '/api/story/workspaces/story-graph/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ revision_id: revision.revision_id, source_sha256: 'source-hash', revision_number: 1 }]) });
    if (path === '/api/story/workspaces/story-graph/graph' && req.method() === 'GET') return graph && new URL(req.url()).searchParams.get('revision_id') === graph.source_revision_id ? route.fulfill({ json: graph }) : route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'No graph' } } });
    if (path === '/api/story/workspaces/story-graph/screenplay' && req.method() === 'GET') return screenplay && new URL(req.url()).searchParams.get('revision_id') === screenplay.source_revision_id ? route.fulfill({ json: screenplay }) : route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'No screenplay' } } });
    if (path === '/api/story/workspaces/story-graph/screenplay/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf(screenplayHistory.map(item => ({ ...item, stale: item.source_revision_id !== revision.revision_id, accepted: item.accepted === true && item.source_revision_id === revision.revision_id && screenplayHistory.find(candidate => candidate.source_revision_id === item.source_revision_id)?.screenplay_revision_id === item.screenplay_revision_id }))) });
    if (path.startsWith('/api/story/workspaces/story-graph/screenplay/revisions/') && req.method() === 'GET') return route.fulfill({ json: screenplayHistory.find(item => item.screenplay_revision_id === path.split('/').at(-1)) });
    if (path === '/api/story/workspaces/story-graph/graph' && req.method() === 'POST') {
      const body = req.postDataJSON(); calls.push(body);
      const quote = 'Mira keeps the key.';
      const evidence = { source_revision_id: revision.revision_id, source_sha256: 'source-hash', chunk_id: 'story_chunk_0001', start_codepoint: 0, end_codepoint: quote.length, quote };
      graph = { snapshot_id: 'graph-1', idempotency_key: body.idempotency_key, workspace_id: 'story-graph', source_revision_id: revision.revision_id, source_sha256: 'source-hash', status: 'complete', coverage_state: 'all_chunks_processed_semantic_coverage_unverified', contradiction_state: 'not_assessed', chunk_total: 1, chunk_complete: 1, provider: 'codex', model: 'fake', semantic_coverage_claim: false, source_span_coverage: { kind: 'cited_source_spans_only', source_chars: Array.from(source).length, cited_chars: quote.length, percent: Math.round(quote.length * 10000 / Array.from(source).length) / 100, uncovered_range_count: 1, uncovered_ranges_omitted: 0, uncovered_ranges: [{ start_codepoint: quote.length, end_codepoint: Array.from(source).length, preview: '\n' + '😀'.repeat(159) }] }, chunks: [{ chunk_id: 'story_chunk_0001', chunk_index: 1, state: 'complete' }], records: [{ record_id: 'record-1', kind: 'entity', type: 'character', name: 'Mira', detail: '', status: 'source_supported', confidence: 1, user_modified: false, properties: {}, evidence: [evidence] }, { record_id: 'event-1', kind: 'event', type: 'interior', name: 'Mira keeps the key', detail: 'Mira holds the key.', status: 'source_supported', confidence: 1, user_modified: false, properties: {}, evidence: [evidence] }] };
      return route.fulfill({ json: graph });
    }
    if (path === '/api/story/workspaces/story-graph/graph/records/record-1' && req.method() === 'PATCH') {
      const body = req.postDataJSON(); graph.records[0] = { ...graph.records[0], ...body, user_modified: true };
      return route.fulfill({ json: { record_id: 'record-1', ...body, user_modified: true } });
    }
    if (path === '/api/story/workspaces/story-graph/screenplay' && req.method() === 'POST') {
      const body = req.postDataJSON(); screenplay = { screenplay_revision_id: 'screenplay-1', workspace_id: 'story-graph', source_revision_id: revision.revision_id, graph_snapshot_id: body.graph_snapshot_id, screenplay: { title: 'Screenplay draft', coverage_note: 'Chunk processing does not establish semantic completeness.', scenes: [{ scene_number: 1, slugline: 'INTERIOR', summary: 'Mira keeps the key', shots: [{ shot_number: 1, action: 'Mira holds the key.', dialogue: '', direction: { camera: '', lighting: '', mood: '', sound: '', music: '' }, evidence: [graph.records[1].evidence[0]] }] }] } }; screenplayHistory = [screenplay]; return route.fulfill({ status: 201, json: screenplay });
    }
    if (path === '/api/story/workspaces/story-graph/screenplay/revisions/screenplay-1' && req.method() === 'PATCH') { const body = req.postDataJSON(); screenplay = { ...screenplay, screenplay_revision_id: 'screenplay-2', parent_screenplay_revision_id: 'screenplay-1', screenplay: body.screenplay }; screenplayHistory = [screenplay, ...screenplayHistory]; return route.fulfill({ status: 201, json: screenplay }); }
    if (path === '/api/story/workspaces/story-graph/screenplay/revisions/screenplay-2/accept' && req.method() === 'POST') { await new Promise(resolve => setTimeout(resolve, 150)); screenplay = { ...screenplay, accepted: true, accepted_at: '2026-10-09 12:00:00' }; screenplayHistory = screenplayHistory.map(item => item.screenplay_revision_id === 'screenplay-2' ? screenplay : item); return route.fulfill({ status: 200, json: screenplay }); }
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: `Unexpected ${req.method()} ${path}` } } });
  });
  await page.goto('/#/story');
  await page.getByRole('button', { name: 'Generate graph' }).click();
  await expect(page.getByText('story_chunk_0001: complete')).toBeVisible();
  await page.getByText('Review uncited passages').click();
  const uncitedPreview = page.locator('.story-graph details blockquote').first();
  await expect(uncitedPreview).toBeVisible();
  expect(await uncitedPreview.evaluate(node => Array.from(node.textContent || '').at(-1))).toBe('…');
  await page.getByLabel('Record').first().fill('Mira, the keeper');
  await page.getByLabel('Notes').first().fill('Reviewed by the writer.');
  await page.getByLabel('Review status').first().selectOption('user_authored');
  await page.getByRole('button', { name: 'Save review' }).first().click();
  await page.reload();
  await expect(page.getByLabel('Record').first()).toHaveValue('Mira, the keeper');
  await expect(page.getByLabel('Notes').first()).toHaveValue('Reviewed by the writer.');
  expect(calls).toHaveLength(1);
  await page.goto('/#/screenplay');
  await expect(page.locator('.stage-rail a[href="#/screenplay"]')).not.toContainText('Unavailable');
  await page.getByRole('button', { name: 'Generate draft' }).click();
  await expect(page.getByText('Shot 1')).toBeVisible();
  await expect(page.getByText('Mira keeps the key.')).toBeVisible();
  await page.getByLabel('Action').fill('Mira locks the key away.');
  await expect(page.getByRole('button', { name: 'Review & accept' })).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'Save your screenplay edits' })).toBeVisible();
  await expect(page.getByLabel('Saved screenplay revisions')).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'Save your edits before opening another revision' })).toBeVisible();
  await page.getByRole('button', { name: 'Save edits' }).click();
  await expect(page.getByRole('button', { name: 'Review & accept' })).toBeEnabled();
  await page.reload();
  await expect(page.getByLabel('Action')).toHaveValue('Mira locks the key away.');
  await expect(page.getByLabel('Saved screenplay revisions')).toContainText('screenplay-2');
  await page.getByRole('button', { name: 'Review & accept' }).click();
  await expect(page.getByLabel('Action')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Accepted' })).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'reviewed and accepted for Assisted manual' })).toBeVisible();
  await page.getByLabel('Saved screenplay revisions').selectOption('screenplay-1');
  await expect(page.getByLabel('Action')).toHaveValue('Mira holds the key.');
  await expect(page.getByRole('button', { name: 'Save edits' })).toBeDisabled();
  revision.revision_id = 'story-canon-fedcba654321';
  await page.reload();
  await expect(page.getByRole('status').filter({ hasText: 'This screenplay uses story source' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save edits' })).toBeDisabled();
  await expect(page.getByLabel('Saved screenplay revisions')).toContainText('stale source');
});
