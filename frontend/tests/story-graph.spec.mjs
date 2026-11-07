import { test, expect } from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

const pageOf = items => ({ items, limit: 50, offset: 0, total: items.length });

test('builds, reviews and reloads a revision-linked source graph without live provider calls', async ({ page }) => {
  let graph = null;
  let screenplay = null;
  let screenplayHistory = [];
  let savedScreenplayPayload = null;
  let delayGraphRefresh = false;
  let delayGraphSearch = false;
  let delayIdentityUndo = false;
  const graphSearchRequests = [];
  let forceDecisionConflict = false;
  const source = 'Mira keeps the key.\n' + '😀'.repeat(200);
  const revision = { revision_id: 'story-canon-abcdef123456', source_text: source, source_sha256: 'source-hash' };
  const storyRevisionHistory = [{ ...revision, revision_number: 1 }];
  const calls = [];
  await page.addInitScript(() => localStorage.setItem('vibe-story-selected-v1', 'story-graph'));
  await page.route('**/api/images/workflows', route => route.fulfill({ json: { workflows: [] } }));
  await page.route('**/api/story/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    if (path === '/api/story/workspaces' && req.method() === 'GET') return route.fulfill({ json: pageOf([{ workspace_id: 'story-graph', title: 'Graph me', current_revision_id: revision.revision_id, initialized: true, status: 'ready' }]) });
    if (path === '/api/story/workspaces/story-graph' && req.method() === 'GET') return route.fulfill({ json: { workspace_id: 'story-graph', title: 'Graph me', current_revision: revision, current_revision_id: revision.revision_id, initialized: true, status: 'ready' } });
    if (path === '/api/story/workspaces/story-graph/draft' && req.method() === 'GET') return route.fulfill({ json: { draft: null } });
    if (path === '/api/story/workspaces/story-graph/draft' && req.method() === 'PUT') return route.fulfill({ json: { workspace_id: 'story-graph', base_revision_id: req.postDataJSON().base_revision_id, source_text: req.postDataJSON().source_text, stale: false } });
    if (path === '/api/story/workspaces/story-graph/draft' && req.method() === 'DELETE') return route.fulfill({ json: { discarded: true } });
    if (path === '/api/story/workspaces/story-graph/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf(storyRevisionHistory) });
    if (path === '/api/story/workspaces/story-graph/revisions' && req.method() === 'POST') {
      const body = req.postDataJSON();
      storyRevisionHistory.unshift({ revision_id: 'story-canon-fedcba654321', source_text: body.source_text, source_sha256: 'new-source-hash', revision_number: 2, parent_revision_id: revision.revision_id });
      Object.assign(revision, storyRevisionHistory[0]);
      graph = null;
      return route.fulfill({ status: 201, json: revision });
    }
    if (path === '/api/story/workspaces/story-graph/graph' && req.method() === 'GET') {
      if (!graph || new URL(req.url()).searchParams.get('revision_id') !== graph.source_revision_id) return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'No graph' } } });
      if (delayGraphRefresh) { delayGraphRefresh = false; await new Promise(resolve => setTimeout(resolve, 350)); }
      return route.fulfill({ json: graph });
    }
    if (path === '/api/story/workspaces/story-graph/graph/search' && req.method() === 'GET') {
      graphSearchRequests.push(url.searchParams.get('q'));
      const response = { snapshot_id: graph.snapshot_id, source_revision_id: revision.revision_id, query: url.searchParams.get('q'), kind: 'literal_keyword_search', match_count: 1, matches: [graph.records[0]], neighborhoods: [{ match_record_id: graph.records[0].record_id, records: [graph.records[1]], alias_member_ids: graph.alias_groups?.[0] || ['record-1'], alias_provenance: graph.identity_decisions?.filter(item=>item.active).map(item=>({decision_id:item.decision_id,left_record_id:item.left_record_id,right_record_id:item.right_record_id})) || [] }] };
      if (delayGraphSearch) { delayGraphSearch = false; await new Promise(resolve => setTimeout(resolve, 350)); }
      return route.fulfill({ json: response });
    }
    if (path === '/api/story/workspaces/story-graph/graph/identity-decisions' && req.method() === 'POST') {
      const body = req.postDataJSON();
      if (body.action === 'undo' && delayIdentityUndo) { delayIdentityUndo = false; await new Promise(resolve => setTimeout(resolve, 350)); }
      if (forceDecisionConflict) { forceDecisionConflict = false; graph.decision_head = (graph.decision_head || 0) + 1; return route.fulfill({ status: 409, json: { error: { code: 'conflict', message: 'Changed elsewhere' } } }); }
      graph.decision_head = (graph.decision_head || 0) + 1;
      if (body.action === 'undo') { graph.identity_candidates[0].review = null; graph.alias_groups = []; graph.identity_decisions = []; }
      else { const decision_id=`decision-${graph.decision_head}`; graph.identity_candidates[0].review = { action: body.action, decision_id }; graph.alias_groups = body.action === 'alias' ? [['record-1','record-other']] : []; graph.identity_decisions = [{decision_id,sequence:graph.decision_head,action:body.action,left_record_id:'record-1',right_record_id:'record-other',active:true}]; }
      return route.fulfill({ status: 201, json: { decision_id: `decision-${graph.decision_head}`, sequence: graph.decision_head, replayed: false } });
    }
    if (path === '/api/story/workspaces/story-graph/screenplay' && req.method() === 'GET') return screenplay && new URL(req.url()).searchParams.get('revision_id') === screenplay.source_revision_id ? route.fulfill({ json: screenplay }) : route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'No screenplay' } } });
    if (path === '/api/story/workspaces/story-graph/assisted-stage-skips') return route.fulfill({json:{workspace_id:'story-graph',screenplay_revision_id:screenplay?.screenplay_revision_id,skipped:[]}});
    if (path === '/api/story/workspaces/story-graph/production-setup' && req.method() === 'GET') return route.fulfill({ json: { workspace_id: 'story-graph', screenplay_revision_id: screenplay?.screenplay_revision_id || '', setup: null, updated_at: null } });
    if (path === '/api/story/workspaces/story-graph/screenplay/revisions' && req.method() === 'GET') return route.fulfill({ json: pageOf(screenplayHistory.map(item => ({ ...item, stale: item.source_revision_id !== revision.revision_id, accepted: item.accepted === true && item.source_revision_id === revision.revision_id && screenplayHistory.find(candidate => candidate.source_revision_id === item.source_revision_id)?.screenplay_revision_id === item.screenplay_revision_id }))) });
    if (path.startsWith('/api/story/workspaces/story-graph/screenplay/revisions/') && req.method() === 'GET') return route.fulfill({ json: screenplayHistory.find(item => item.screenplay_revision_id === path.split('/').at(-1)) });
    if (path === '/api/story/workspaces/story-graph/graph' && req.method() === 'POST') {
      const body = req.postDataJSON(); calls.push(body);
      const quote = 'Mira keeps the key.';
      const evidence = { source_revision_id: revision.revision_id, source_sha256: revision.source_sha256, chunk_id: 'story_chunk_0001', start_codepoint: 0, end_codepoint: quote.length, quote };
      const currentSource = revision.source_text;
      graph = { snapshot_id: `graph-${calls.length}`, idempotency_key: body.idempotency_key, workspace_id: 'story-graph', source_revision_id: revision.revision_id, source_sha256: revision.source_sha256, status: 'complete', coverage_state: 'all_chunks_processed_semantic_coverage_unverified', contradiction_state: 'not_assessed', chunk_total: 1, chunk_complete: 1, provider: 'codex', model: 'fake', semantic_coverage_claim: false, source_span_coverage: { kind: 'cited_source_spans_only', source_chars: Array.from(currentSource).length, cited_chars: quote.length, percent: Math.round(quote.length * 10000 / Array.from(currentSource).length) / 100, uncovered_range_count: 1, uncovered_ranges_omitted: 0, uncovered_ranges: [{ start_codepoint: quote.length, end_codepoint: Array.from(currentSource).length, preview: currentSource.slice(quote.length, quote.length + 320) }] }, chunks: [{ chunk_id: 'story_chunk_0001', chunk_index: 1, state: 'complete' }], records: [{ record_id: 'record-1', kind: 'entity', type: 'character', name: 'Mira', detail: '', status: 'source_supported', confidence: 1, user_modified: false, properties: {}, evidence: [evidence] }, { record_id: 'event-1', kind: 'event', type: 'interior', name: 'Mira keeps the key', detail: 'Mira holds the key.', status: 'source_supported', confidence: 1, user_modified: false, properties: {}, evidence: [evidence] }] };
      return route.fulfill({ json: graph });
    }
    if (path === '/api/story/workspaces/story-graph/graph/records/record-1' && req.method() === 'PATCH') {
      const body = req.postDataJSON(); graph.records[0] = { ...graph.records[0], ...body, user_modified: true };
      graph.identity_candidates = [];
      delayGraphRefresh = true;
      return route.fulfill({ json: { record_id: 'record-1', ...body, user_modified: true } });
    }
    if (path === '/api/story/workspaces/story-graph/screenplay' && req.method() === 'POST') {
      const body = req.postDataJSON(); screenplay = { screenplay_revision_id: 'screenplay-1', workspace_id: 'story-graph', source_revision_id: revision.revision_id, graph_snapshot_id: body.graph_snapshot_id, screenplay: { title: 'Screenplay draft', coverage_note: '1/2 extracted event/fact records are linked.', graph_record_coverage: { scope: 'extracted_events_and_facts', linked_count: 1, record_count: 2, unlinked_records: [{ record_id: 'fact-1', kind: 'fact', type: 'possession', name: 'Mira has the key', detail: 'She keeps it.', status: 'source_supported', evidence: [graph.records[1].evidence[0]] }] }, scenes: [{ scene_number: 1, slugline: 'INTERIOR', summary: 'Mira keeps the key', shots: [{ shot_number: 1, action: 'Mira holds the key.', dialogue: '', direction: { camera: '', lighting: '', mood: '', sfx: '', music: '' }, evidence: [graph.records[1].evidence[0]], evidence_record_ids: ['event-1'], character_record_ids: ['record-1'] }] }] } }; screenplayHistory = [screenplay]; return route.fulfill({ status: 201, json: screenplay });
    }
    if (path === '/api/story/workspaces/story-graph/screenplay/revisions/screenplay-1' && req.method() === 'PATCH') { const body = req.postDataJSON(); savedScreenplayPayload = body.screenplay; screenplay = { ...screenplay, screenplay_revision_id: 'screenplay-2', parent_screenplay_revision_id: 'screenplay-1', screenplay: body.screenplay }; screenplayHistory = [screenplay, ...screenplayHistory]; return route.fulfill({ status: 201, json: screenplay }); }
    if (path === '/api/story/workspaces/story-graph/screenplay/revisions/screenplay-2/accept' && req.method() === 'POST') { await new Promise(resolve => setTimeout(resolve, 150)); screenplay = { ...screenplay, accepted: true, accepted_at: '2026-10-09 12:00:00' }; screenplayHistory = screenplayHistory.map(item => item.screenplay_revision_id === 'screenplay-2' ? screenplay : item); return route.fulfill({ status: 200, json: screenplay }); }
    if (path === '/api/story/workspaces/story-graph/field-edit-proposals' && req.method() === 'POST') { const body=req.postDataJSON(); expect(body.surface).toBe('screenplay'); expect(body.expected_text).toBe('holds'); return route.fulfill({status:201,json:{proposal_id:'field-proposal-1',surface:'screenplay',revision_id:'screenplay-1',field_key:'1.1.action',field_sha256:'hash',start_codepoint:5,end_codepoint:10,expected_text:'holds',replacement:'keeps',status:'pending'}}); }
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: `Unexpected ${req.method()} ${path}` } } });
  });
  await mockProject(page, 'story-graph');
  await page.goto('/#/story');
  await page.locator('details.story-graph > summary').click();
  await page.getByRole('button', { name: 'Generate graph' }).click();
  await expect(page.getByText('story_chunk_0001: complete')).toBeVisible();
  const storySource = page.getByLabel('Story source text');
  const savedSourceText = await storySource.inputValue();
  await storySource.fill(`${savedSourceText}\nUnsaved draft change.`);
  await expect(page.getByRole('status').filter({ hasText: 'This graph does not match the current story text.' })).toBeVisible();
  await expect(page.getByLabel('Find a person, event or fact')).toBeDisabled();
  await expect(page.getByLabel('Record').first()).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Save review' }).first()).toBeDisabled();
  await storySource.fill(savedSourceText);
  await expect(page.getByLabel('Find a person, event or fact')).toBeEnabled();
  await expect(page.getByLabel('Record').first()).toBeEnabled();
  // Older graph API payloads have no identity_candidates field.
  expect(graph.identity_candidates).toBeUndefined();
  graph.decision_head = 0;
  graph.identity_candidates = [{ left_record_id: 'record-1', left_name: 'Mira', left_type: 'character', left_fingerprint: 'fp-left', left_evidence: [{ ...graph.records[0].evidence[0] }], right_record_id: 'record-other', right_name: 'Mira Sen', right_type: 'character', right_fingerprint: 'fp-right', right_evidence: [{ ...graph.records[0].evidence[0], chunk_id: 'story_chunk_0002' }], kind: 'possible_name_variant', review: null }];
  await page.getByRole('button', { name: 'Refresh graph' }).click();
  await expect(page.getByRole('region', { name: 'Possible cross-chunk name variants' })).toContainText('Mira ↔ Mira Sen');
  graph.status = 'partial'; graph.chunk_complete = 0; graph.chunks[0].state = 'pending';
  await page.getByRole('button', { name: 'Refresh graph' }).click();
  await expect(page.getByText('Complete every graph chunk before reviewing identity suggestions.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Same person' })).toBeDisabled();
  graph.status = 'complete'; graph.chunk_complete = graph.chunk_total; graph.chunks[0].state = 'complete';
  await page.getByRole('button', { name: 'Refresh graph' }).click();
  await expect(page.getByRole('button', { name: 'Same person' })).toBeEnabled();
  await page.getByRole('button', { name: 'Same person' }).click();
  await expect(page.getByText('Reviewed: alias')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Undo review' })).toBeVisible();
  await page.reload();
  await page.locator('details.story-graph > summary').click();
  await expect(page.getByText('Reviewed: alias')).toBeVisible();
  await page.getByLabel('Find a person, event or fact').fill('Mira');
  await page.getByRole('button', { name: 'Search graph' }).click();
  await expect(page.getByText(/Accepted aliases: Mira · record-other · evidence decision-1/)).toBeVisible();
  delayGraphSearch = true;
  await page.getByLabel('Find a person, event or fact').fill('Mira stale search');
  await page.getByRole('button', { name: 'Search graph' }).click();
  await page.getByRole('button', { name: 'Undo review' }).click();
  await expect(page.getByText('Suggested match')).toBeVisible();
  await page.waitForTimeout(400);
  await expect(page.getByText(/keyword matches/)).toHaveCount(0);
  await expect(page.getByText(/Accepted aliases:/)).toHaveCount(0);
  await page.reload();
  await page.locator('details.story-graph > summary').click();
  await expect(page.getByText('Suggested match')).toBeVisible();
  await page.getByRole('button', { name: 'Same person' }).click();
  await expect(page.getByText('Reviewed: alias')).toBeVisible();
  await page.getByLabel('Find a person, event or fact').fill('before undo');
  await page.getByRole('button', { name: 'Search graph' }).click();
  await expect(page.getByText(/Accepted aliases:/)).toBeVisible();
  const searchesBeforeUndo = graphSearchRequests.length;
  delayIdentityUndo = true;
  await page.getByRole('button', { name: 'Undo review' }).click();
  await expect(page.getByLabel('Find a person, event or fact')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Search graph' })).toBeDisabled();
  expect(graphSearchRequests).toHaveLength(searchesBeforeUndo);
  await expect(page.getByText('Suggested match')).toBeVisible();
  await expect(page.getByText(/Accepted aliases:/)).toHaveCount(0);
  await page.getByRole('button', { name: 'Different people' }).click();
  await expect(page.getByText('Reviewed: distinct')).toBeVisible();
  await page.getByLabel('Find a person, event or fact').fill('Mira');
  await page.getByRole('button', { name: 'Search graph' }).click();
  await expect(page.getByText('1 keyword matches')).toBeVisible();
  await expect(page.getByText('Connected: Mira keeps the key')).toBeVisible();
  await page.getByText('Review uncited passages').click();
  const uncitedPreview = page.locator('.story-graph details blockquote').first();
  await expect(uncitedPreview).toBeVisible();
  expect(await uncitedPreview.evaluate(node => Array.from(node.textContent || '').at(-1))).toBe('…');
  await page.getByLabel('Record').nth(1).fill('Unsaved event draft');
  await page.getByLabel('Record').first().fill('Mira, the keeper');
  await page.getByLabel('Notes').first().fill('Reviewed by the writer.');
  await page.getByLabel('Review status').first().selectOption('user_authored');
  forceDecisionConflict = true;
  await page.getByRole('button', { name: 'Undo review' }).click();
  await expect(page.getByRole('alert').filter({hasText:'Identity review changed'})).toBeVisible();
  await expect(page.getByLabel('Record').nth(1)).toHaveValue('Unsaved event draft');
  await expect(page.getByLabel('Record').first()).toHaveValue('Mira, the keeper');
  await expect(page.getByLabel('Notes').first()).toHaveValue('Reviewed by the writer.');
  await page.getByRole('button', { name: 'Save review' }).first().click();
  await expect(page.getByLabel('Record').first()).toBeDisabled();
  await expect(page.getByLabel('Notes').first()).toBeDisabled();
  await expect(page.getByLabel('Review status').first()).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'Graph record saved as user-authored review' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Possible cross-chunk name variants' })).toHaveCount(0);
  await expect(page.getByLabel('Record').nth(1)).toHaveValue('Unsaved event draft');
  await expect(page.getByLabel('Record').first()).toBeEnabled();
  await page.reload();
  await page.locator('details.story-graph > summary').click();
  await expect(page.getByLabel('Record').first()).toHaveValue('Mira, the keeper');
  await expect(page.getByLabel('Notes').first()).toHaveValue('Reviewed by the writer.');
  expect(calls).toHaveLength(1);
  graph = null; // Screenplay should prepare this internal dependency for the user.
  await page.goto('/#/screenplay');
  await expect(page.locator('.stage-rail a[href="#/screenplay"]')).not.toContainText('Unavailable');
  await page.getByRole('button', { name: 'Generate screenplay' }).click();
  await expect(page.getByText('Shot 1')).toBeVisible();
  const duration = page.getByRole('spinbutton', { name: 'Scene 1 Shot 1 planned duration (seconds)' });
  await expect(duration).toHaveValue('');
  await duration.fill('8.5');
  await page.reload();
  await expect(duration).toHaveValue('8.5');
  await page.getByText('Source coverage and implementation evidence',{exact:true}).click();
  await page.getByText('Screenplay revision history',{exact:true}).click();
  await page.locator('.screenplay-shot details > summary').click();
  await expect(page.getByRole('region', { name: 'Extracted event and fact links' })).toContainText('1 of 2 extracted events and facts are linked');
  await expect(page.getByRole('region', { name: 'Extracted event and fact links' })).toContainText('Mira has the key');
  await expect(page.getByRole('article').getByText('Mira keeps the key.')).toBeVisible();
  const action=page.getByRole('textbox',{name:'Action',exact:true});
  await action.focus(); await action.press('Home'); for(let i=0;i<5;i++) await action.press('ArrowRight'); for(let i=0;i<5;i++) await action.press('Shift+ArrowRight');
  await page.getByLabel('Instruction for Action').fill('Use a quieter verb.');
  await page.getByRole('button',{name:'Suggest edit'}).click();
  await page.getByRole('button',{name:'Apply to draft'}).click();
  await expect(action).toHaveValue('Mira keeps the key.');
  await page.getByLabel('Action').fill('Mira locks the key away.');
  await expect(page.getByRole('button', { name: 'Review & accept' })).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'Draft on this browser only.' })).toBeVisible();
  await expect(page.getByLabel('Saved screenplay revisions')).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'Save your edits before opening another revision' })).toBeVisible();
  await page.getByRole('button', { name: 'Save progress' }).click();
  await expect(page.getByRole('button', { name: 'Review & accept' })).toBeEnabled();
  expect(savedScreenplayPayload.scenes[0].shots[0].planned_duration_seconds).toBe(8.5);
  expect(savedScreenplayPayload.scenes[0].shots[0].character_record_ids).toEqual(['record-1']);
  await page.reload();
  await expect(duration).toHaveValue('8.5');
  await expect(page.getByLabel('Action')).toHaveValue('Mira locks the key away.');
  await expect(page.getByLabel('Saved screenplay revisions')).toContainText('screenplay-2');
  await page.getByRole('button', { name: 'Review & accept' }).click();
  await expect(page.getByLabel('Action')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Accepted' })).toBeDisabled();
  await expect(page.getByRole('status').filter({ hasText: 'Screenplay accepted. Choose Assisted manual or Fully automated' })).toBeVisible();
  const nextStage = page.getByRole('link', { name: 'Choose production mode' });
  await expect(nextStage).toHaveAttribute('href', '#/setup');
  await nextStage.click();
  await expect(page.getByRole('heading', { name: 'Automation & Parameters' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Choose a production mode' })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Screenplay', exact: true })).toBeVisible();
  await page.getByText('Screenplay revision history',{exact:true}).click();
  await page.getByLabel('Saved screenplay revisions').selectOption('screenplay-1');
  await expect(page.getByLabel('Action')).toHaveValue('Mira holds the key.');
  await expect(page.getByRole('button', { name: 'Save progress' })).toBeDisabled();
  revision.revision_id = 'story-canon-fedcba654321';
  await page.reload();
  await expect(page.getByRole('status').filter({ hasText: 'This screenplay uses story source' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save progress' })).toBeDisabled();
  await expect(page.getByLabel('Saved screenplay revisions')).toContainText('stale inputs');

  await page.goto('/#/story');
  const sourceEditor = page.getByLabel('Story source text');
  await sourceEditor.fill(`${revision.source_text}\nA new source event is added.`);
  await page.getByRole('button', { name: 'Save progress' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'New story revision saved.' })).toBeVisible();
  await page.reload();
  await page.locator('details.story-graph > summary').click();
  await expect(page.getByRole('button', { name: 'Generate graph' })).toBeVisible();
  await expect(page.getByText('story_chunk_0001: complete')).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate graph' }).click();
  await expect(page.getByText('story_chunk_0001: complete')).toBeVisible();
  expect(calls.at(-1).source_revision_id).toBe('story-canon-fedcba654321');
  expect(graph.source_revision_id).toBe(revision.revision_id);
  expect(graph.source_revision_id).toBe('story-canon-fedcba654321');
});
