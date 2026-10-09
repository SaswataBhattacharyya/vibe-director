import { test, expect } from '@playwright/test';

const pageOf = items => ({ items, limit: 50, offset: 0, total: items.length });

test('selected Codex proposal reviews and accepts an exact Unicode span; reload performs no provider POST', async ({ page }) => {
  let source = 'Before 😀. The old phrase. After Ω.';
  const revision = () => ({ revision_id: source.includes('new phrase') ? 'rev-2' : 'rev-1', source_text: source });
  const posts = [];
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'story-edit'));
  await page.route('**/api/story/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    if (path === '/api/story/workspaces' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ workspace_id: 'story-edit', title: 'Edit me', current_revision_id: revision().revision_id, initialized: true, status: 'ready' }]) });
    if (path === '/api/story/workspaces/story-edit' && req.method() === 'GET') return route.fulfill({ json: { workspace_id: 'story-edit', title: 'Edit me', current_revision: revision(), current_revision_id: revision().revision_id, initialized: true, status: 'ready' } });
    if (path === '/api/story/workspaces/story-edit/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ revision_id: revision().revision_id, source_sha256: 'hash', revision_number: source.includes('new phrase') ? 2 : 1 }]) });
    if (path === '/api/story/workspaces/story-edit/edit-proposals' && req.method() === 'POST') {
      const body = req.postDataJSON(); posts.push(body);
      return route.fulfill({ status: 201, json: { proposal_id: 'proposal-1', workspace_id: 'story-edit', base_revision_id: 'rev-1', start_codepoint: body.start_codepoint, end_codepoint: body.end_codepoint, expected_text: body.expected_text, replacement: 'the new phrase', instruction: body.instruction, provider: 'codex', model: 'gpt-6-luna', status: 'pending', ai_generated: true } });
    }
    if (path === '/api/story/workspaces/story-edit/edit-proposals/accept' && req.method() === 'POST') {
      source = 'Before 😀. The the new phrase. After Ω.';
      return route.fulfill({ status: 201, json: { revision_id: 'rev-2', source_text: source, source_sha256: 'newhash', parent_revision_id: 'rev-1', revision_number: 2 } });
    }
    if (path === '/api/story/edit-requests/by-key/' + posts[0]?.idempotency_key && req.method() === 'GET') return route.fulfill({ json: { status: 'complete', proposal: { proposal_id: 'proposal-1', workspace_id: 'story-edit', base_revision_id: 'rev-1', expected_text: 'old phrase', replacement: 'the new phrase', instruction: 'Make it clearer.', provider: 'codex', status: 'pending' } } });
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: `Unexpected ${req.method()} ${path}` } } });
  });
  await page.goto('/#/story');
  const story = page.getByLabel('Story source text');
  await expect(story).toHaveValue(source);
  await story.evaluate(node => { node.focus(); node.setSelectionRange(15, 25); node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true })); });
  await expect(page.getByText('Selected passage (10 characters)')).toBeVisible();
  await page.getByLabel('Edit instruction').fill('Make it clearer.');
  await expect(page.getByText(/Codex receives only that passage and instruction/)).toBeVisible();
  await page.getByRole('button', { name: 'Propose edit' }).click();
  await expect(page.getByLabel('AI edit proposal')).toContainText('the new phrase');
  expect(posts).toHaveLength(1);
  expect(posts[0].expected_text).toBe('old phrase');
  expect(posts[0].start_codepoint).toBe(14);
  await page.getByRole('button', { name: 'Accept as revision' }).click();
  await expect(story).toHaveValue(source);
  expect(posts).toHaveLength(1);
  await page.reload();
  await expect(page.getByLabel('Story source text')).toHaveValue(source);
  expect(posts).toHaveLength(1);
});
