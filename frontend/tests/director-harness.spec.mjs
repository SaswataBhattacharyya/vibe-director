import {test, expect} from '@playwright/test';

async function fixture(page, initial = 'running') {
  let status = initial, reads = 0, mayFinish = initial !== 'running';
  const actions = [];
  actions.finish = () => {mayFinish = true;};
  const message = () => ({request_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', text: 'Inspect media, then prepare an edit.',
    reply: status === 'waiting_for_approval' ? 'Measured 0.3 seconds. Review the saved draft.' : '', status: 'thinking', task_id: null,
    goal: {request_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', objective: 'Inspect media, then prepare an edit.', status,
      state: {phase: status === 'running' ? 'reading' : 'stopped', progress: 'Inspecting source audio', authorization: 'read-only-and-draft', dependencies: [], stop_reason: null},
      steps: [{tool: 'media_list', task_id: 'task-list', status: 'completed'}, {tool: 'media_inspect', task_id: 'task-inspect', status: status === 'running' ? 'started' : 'completed'}]}});
  await page.route('**/api/**', route => {
    const req = route.request(), path = new URL(req.url()).pathname;
    if (path === '/api/studio-tools/output-destination') return route.fulfill({json: {mode: 'folder', path: '/test-owned/output', available: true}});
    if (path.endsWith('/resume') || path.endsWith('/cancel')) {
      actions.push({path, body: req.postDataJSON()});
      status = path.endsWith('/cancel') ? 'cancelled' : 'running'; reads = 0;
      return route.fulfill({json: {workspace_id: 'tool-library', messages: [message()]}});
    }
    if (path.endsWith('/conversation')) {
      if (req.method() === 'POST') {actions.push({path, body: req.postDataJSON()}); status = 'running'; reads = 0;}
      if (status === 'running' && ++reads >= 2 && mayFinish) status = 'waiting_for_approval';
      return route.fulfill({json: {workspace_id: 'tool-library', messages: status === 'empty' ? [] : [message()], runtime: {harness_enabled: true, harness_model: 'gpt-6-luna'}}});
    }
    if (path.endsWith('/tasks')) return route.fulfill({json: {tasks: []}});
    if (path === '/api/projects/current') return route.fulfill({json: {workspace_id: 'tool-library', title: 'Test owned', browser_state: {}}});
    if (path === '/api/projects/memory') return route.fulfill({json: {saved: true}});
    if (path === '/api/director/settings') return route.fulfill({json: {settings: {provider: 'codex', model: 'test', lessons: []}, models: []}});
    if (path === '/api/editor/state') return route.fulfill({json: {projects: [], styles: [], runtime: {ready: false, checks: {}}}});
    if (path === '/api/story/workspaces') return route.fulfill({json: {items: []}});
    if (path.endsWith('/assets')) return route.fulfill({json: {assets: [], total: 0}});
    return route.fulfill({status: 404, json: {error: {message: 'Unused mock ' + path}}});
  });
  return actions;
}

for (const surface of ['video', 'editor']) {
  test(`shared ${surface} chat polls a saved goal and cancels without a new user message`, async ({page}) => {
    const actions = await fixture(page);
    await page.goto('/#/' + surface);
    const goal = page.getByRole('region', {name: 'Saved Director goal'});
    await expect(goal).toContainText('running');
    actions.finish();
    await expect(goal).toContainText('waiting for approval', {timeout: 10000});
    await expect(page.getByRole('log', {name: 'Director conversation history'})).toContainText('Measured 0.3 seconds.');
    await goal.getByRole('button', {name: 'Cancel goal', exact: true}).click();
    await expect(goal).toContainText('cancelled');
    expect(actions).toHaveLength(1);
    expect(actions[0].body).toEqual({});
    expect(actions[0].path).toMatch(/\/conversation\/[a-f-]+\/cancel$/);
  });
}

test('interrupted goal resumes through its saved identity and preserves the composer draft', async ({page}) => {
  const actions = await fixture(page, 'interrupted');
  await page.goto('/#/editor');
  const input = page.getByLabel('Message the project Director', {exact: true});
  await input.fill('Keep this unsent draft');
  await page.getByRole('button', {name: 'Resume saved goal', exact: true}).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('region', {name: 'Saved Director goal'})).toContainText('waiting for approval', {timeout: 10000});
  await expect(input).toHaveValue('Keep this unsent draft');
  expect(actions[0].path).toMatch(/\/conversation\/[a-f-]+\/resume$/);
});

for (const surface of ['video', 'editor']) {
  test(`opt-in ${surface} chat starts the harness without a creative prerequisite or session write`, async ({page}) => {
    const actions = await fixture(page, 'empty');
    const editorWrites = [];
    page.on('request', request => {if (request.method() !== 'GET' && new URL(request.url()).pathname.startsWith('/api/editor/')) editorWrites.push(request.url());});
    await page.goto('/#/' + surface);
    await expect(page.getByText('Codex harness · gpt-6-luna', {exact: true})).toBeVisible();
    const input = page.getByLabel('Message the project Director', {exact: true});
    await input.fill('Inspect my media, then prepare an edit.');
    await page.getByRole('button', {name: 'Send to project Director', exact: true}).click();
    await expect(page.getByRole('region', {name: 'Saved Director goal'})).toContainText('waiting for approval', {timeout: 10000});
    expect(actions).toHaveLength(1);
    expect(actions[0].body.surface).toBe('director');
    expect(actions[0].body.target).toBeUndefined();
    expect(editorWrites).toEqual([]);
  });
}

for (const surface of ['video', 'editor']) {
  test(`${surface} requires separate approval and run for a goal-linked proposal`, async ({page}) => {
    await fixture(page, 'empty');
    const id = 'task-' + '1'.repeat(32), request = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
    let status = 'draft', goalStatus = 'waiting_for_approval';
    const actions = [];
    const task = () => ({project_id: 'tool-library', task_id: id, status, current_revision: 1, plan_hash: 'a'.repeat(64),
      plan: {tool_id: 'editor.create_session', scope: 'Create an empty Editor session.', assets: [], settings: {name: 'Reviewed edit'}},
      invocation: status === 'completed' ? {invocation_id: 'call-test', job_id: 'job-test', state: 'completed'} : null,
      events: [], ...(status === 'completed' ? {report: '{"diagnostics":"saved result"}'} : {})});
    await page.route('**/api/agent/**', route => {
      const req = route.request(), path = new URL(req.url()).pathname;
      if (path === '/api/agent/computer-access') return route.fulfill({json: {available: true, session_token: 'test-owner-grant'}});
      if (path.endsWith('/conversation')) return route.fulfill({json: {runtime: {harness_enabled: true}, messages: [{request_id: request,
        text: 'Prepare a reviewed edit, then continue.', status: 'answered', reply: status === 'completed' ? 'Consumed verified result; continued original objective.' : 'Review the proposal.',
        goal: {request_id: request, status: goalStatus, objective: 'Prepare a reviewed edit, then continue.',
          state: {phase: goalStatus, progress: '', dependencies: [id], authorization: 'read-only-and-draft', stop_reason: 'approval_needed'},
          steps: [{tool: 'editor_propose_session', task_id: id, status: 'completed'}]}}]}});
      if (path.endsWith('/tasks')) return route.fulfill({json: {tasks: [task()]}});
      if (path.endsWith('/approve') || path.endsWith('/run')) {
        actions.push({action: path.split('/').at(-1), body: req.postDataJSON(), grant: req.headers()['x-vibe-computer-token']});
        status = path.endsWith('/approve') ? 'approved' : 'completed';
        goalStatus = status === 'approved' ? 'waiting_for_execution' : 'blocked';
        return route.fulfill({json: task()});
      }
      if (path.endsWith('/' + id)) return route.fulfill({json: task()});
      return route.fallback();
    });
    await page.goto('/#/' + surface);
    const card = page.getByRole('article', {name: `Task ${id}`});
    await expect(card).toContainText('Reviewed edit');
    await expect(card.getByRole('button', {name: 'Run approved task'})).toHaveCount(0);
    await card.getByRole('button', {name: 'Approve this plan'}).click();
    await expect(page.getByRole('region', {name: 'Saved Director goal'})).toContainText('waiting for execution');
    expect(actions).toHaveLength(1);
    await card.getByRole('button', {name: 'Run approved task'}).click();
    await expect(page.getByRole('log', {name: 'Director conversation history'})).toContainText('Consumed verified result');
    await expect(card.locator('details').filter({hasText: 'Tool result'})).not.toHaveAttribute('open', '');
    expect(actions).toEqual(['approve', 'run'].map(action => ({action, body: {revision: 1, plan_hash: 'a'.repeat(64)}, grant: 'test-owner-grant'})));
  });
}
