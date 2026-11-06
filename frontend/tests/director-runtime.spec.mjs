import {test, expect} from '@playwright/test';
const owner = 'story-aaaaaaaaaaaa';
const taskId = 'task-' + 'a'.repeat(32);
async function fixture(page, continuity = false) {
  const writes = [];
  let messages = [], tasks = [], knowledge = {workspace_id: owner, revision: 0, content: ''};
  await page.route('**/api/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    const post = request.method() === 'POST';
    if (post) writes.push(path);
    const body = post ? request.postDataJSON() : null;
    let json;
    if (path === '/api/projects/current') json = {workspace_id: owner, title: 'Test film', browser_state: {}};
    else if (path === '/api/projects/memory') json = {saved: true};
    else if (path === '/api/studio-tools/output-destination') json = {mode: 'folder', path: '/test-owned/output', available: true};
    else if (path.endsWith('/knowledge')) {
      if (post) knowledge = {...knowledge, revision: knowledge.revision + 1, content: body.content};
      json = knowledge;
    }
    else if (path.startsWith('/api/images/workflows')) json = {workflows: [{workflow_id: 'qwen_image_edit_2511', label: 'Qwen Image Edit', version: '1', available: false, defaults: {}}]};
    else if (path === '/api/images/worker') json = {available: false};
    else if (path === '/api/video/runtime') json = {safe_to_submit: false};
    else if (path.endsWith('/conversation')) {
      if (post) {
        messages.push({request_id: body.request_id, text: body.text, reply: 'Review the selected whole-asset extraction.', status: 'answered', task_id: taskId});
        tasks = [{project_id: owner, task_id: taskId, status: 'draft', current_revision: 1, plan_hash: 'f'.repeat(64),
          plan: {tool_id: continuity ? 'video.continuity_last_frame' : 'audio.extract_mp3', scope: 'Extract whole assets to MP3; preserve original media.', assets: [{asset_id: 'pa-owned', filename: continuity ? 'shot.mp4' : 'shot.wav', sha256: 'b'.repeat(64)}], settings: continuity ? {} : {quality: 2}}, invocation: null, events: []}];
      }
      json = {workspace_id: owner, messages};
    } else if (path.endsWith('/tasks')) json = {tasks};
    else if (path.includes('/tasks/')) {
      if (post) {
        expect(body).toEqual({revision: 1, plan_hash: 'f'.repeat(64)});
        if (path.endsWith('/approve')) tasks[0].status = 'approved';
        if (path.endsWith('/run')) {
          tasks[0].status = 'completed'; tasks[0].invocation = {invocation_id: 'call-owned', job_id: 'audio-utilities-owned', state: 'completed'};
          tasks[0].outputs = [{workspace_id: owner, asset_id: 'pa-output', filename: continuity ? 'last.png' : 'extracted.mp3', kind: continuity ? 'image' : 'audio', content_url: continuity ? '/test-owned/last.png' : '/test-owned/extracted.mp3', sha256: 'c'.repeat(64)}];
        }
      }
      json = tasks[0];
    } else if (path === '/api/agent/tools') json = {tools: [{id: 'audio.extract_mp3', status: 'available', effect: 'submit', input_schema: {}, execution_enabled: false}]};
    else if (path === '/api/agent/skills') json = {skills: [{ref: 'application/vibe/vibe-director', id: 'vibe-director', scope: 'application', provider: 'vibe', description: 'Film direction', available: true}], truncated: false};
    else if (path.endsWith('/context')) json = {workspace_id: owner, nodes: [{id: 'asset:pa-owned', kind: 'asset', source_id: 'pa-owned', owner, label: continuity ? 'shot.mp4' : 'shot.wav', sha256: 'b'.repeat(64)}], relations: [], truncated: []};
    else if (path === '/api/director/settings') json = {settings: {provider: 'codex', model: 'test', lessons: []}, models: []};
    else if (path === '/api/story/workspaces') json = {items: []};
    else if (path === '/api/editor/state') json = {projects: [], styles: [], runtime: {ready: false, checks: {}}};
    else if (path.endsWith('/assets')) json = {assets: [{workspace_id: owner, asset_id: 'pa-room', kind: 'image', filename: 'base-room.png', roles: ['world_master'], metadata: {}, content_url: '/test-owned/base-room.png', sha256: 'e'.repeat(64)}], total: 1};
    else return route.fulfill({status: 404, json: {error: {message: 'Unused mock ' + path}}});
    return route.fulfill({json});
  });
  return writes;
}
test('conversation draft survives routes, hide/show and reload without generation', async ({page}) => {
  const writes = await fixture(page);
  await page.goto('/#/video');
  await page.getByLabel('Message the project Director', {exact: true}).fill('A scene in a ruined slime-covered room');
  await page.getByRole('button', {name: 'Hide Director conversation', exact: true}).click();
  await page.getByRole('button', {name: 'Show Director conversation', exact: true}).click();
  await expect(page.getByLabel('Message the project Director', {exact: true})).toHaveValue('A scene in a ruined slime-covered room');
  await page.getByRole('navigation', {name: 'Studio navigation'}).getByRole('link', {name: 'Vibe Editor', exact: true}).click();
  await expect(page.getByLabel('Message the project Director', {exact: true})).toHaveValue('A scene in a ruined slime-covered room');
  await page.reload();
  await expect(page.getByLabel('Message the project Director', {exact: true})).toHaveValue('A scene in a ruined slime-covered room');
  expect(writes.filter(path => path.startsWith('/api/agent/'))).toEqual([]);
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
test('project notes are explicitly saved and available after switching surfaces', async ({page}) => {
  await fixture(page);
  await page.goto('/#/video');
  await page.getByRole('button', {name: 'Context & skills'}).click();
  await page.getByText('Project knowledge', {exact: true}).click();
  await page.getByLabel('Project notes', {exact: true}).fill('Keep the base room layout in every scene.');
  await page.getByRole('button', {name: 'Save project notes', exact: true}).click();
  await expect(page.getByRole('status').filter({hasText: 'Saved project knowledge'})).toBeVisible();
  await page.goto('/#/editor');
  const context = page.getByRole('button', {name: 'Context & skills'});
  if (await context.getAttribute('aria-expanded') !== 'true') await context.click();
  const notes = page.locator('.director-knowledge');
  if (await notes.getAttribute('open') === null) await notes.locator('summary').click();
  await expect(page.getByLabel('Project notes', {exact: true})).toHaveValue('Keep the base room layout in every scene.');
});
test('scene condition prepares an image edit with a base reference without generation', async ({page}, info) => {
  const writes = await fixture(page);
  await page.goto('/#/worlds');
  await expect(page.getByRole('heading', {name: 'Scene Backgrounds', exact: true})).toBeVisible();
  await page.getByRole('combobox', {name: 'Base location image', exact: true}).selectOption('pa-room');
  await page.getByLabel('Scene or shot label', {exact: true}).fill('Scene 5');
  await page.getByLabel('What changes in this scene?', {exact: true}).fill('The room is covered in slime.');
  await page.getByRole('button', {name: 'Prepare scene variation', exact: true}).click();
  await expect(page.getByLabel('Image prompt', {exact: true})).toHaveValue(/Scene 5.*covered in slime/);
  expect(writes.filter(path => path.includes('/api/images/'))).toEqual([]);
  const draft = await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-image-draft-v1')));
  expect(draft.sourceReferenceIds).toEqual(['pa-room']);
  expect(draft.workflowId).toBe('qwen_image_edit_2511');
  await page.setViewportSize({width: 1440, height: 1000});
  await page.evaluate(() => scrollTo(0, 0));
  await expect.poll(() => page.getByLabel('Message the project Director', {exact: true}).evaluate(element => element.getBoundingClientRect().bottom <= document.querySelector('.studio-taskbar').getBoundingClientRect().top)).toBe(true);
  await page.screenshot({path: info.outputPath('director-desktop.png'), animations: 'disabled'});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: info.outputPath('director-mobile.png'), animations: 'disabled'});
});
for (const surface of ['video', 'editor']) test(`${surface} reviews exact plan, runs once and offers verified audio`, async ({page}) => {
  const writes = await fixture(page);
  await page.goto('/#/' + surface);
  await page.getByRole('button', {name: 'Context & skills'}).click();
  await page.getByLabel('shot.wav', {exact: true}).check();
  await page.getByLabel('Message the project Director', {exact: true}).fill('Extract the selected audio to MP3');
  await page.getByRole('button', {name: 'Send to project Director', exact: true}).click();
  const card = page.getByRole('article', {name: `Task ${taskId}`});
  await expect(card).toContainText('shot.wav');
  expect(writes.some(path => path.endsWith('/run'))).toBe(false);
  await card.getByRole('button', {name: 'Approve this plan', exact: true}).click();
  await card.getByRole('button', {name: 'Run approved task', exact: true}).click();
  await expect(card.getByRole('link', {name: 'extracted.mp3', exact: true})).toBeVisible();
  await card.getByRole('button', {name: 'Offer audio to Editor', exact: true}).click();
  expect(writes.filter(path => path.endsWith('/run'))).toHaveLength(1);
  expect(await page.evaluate(() => JSON.parse(sessionStorage.getItem('vibe-editor-pending-audio')).asset.asset_id)).toBe('pa-output');
  // Offering a result never adds it to a timeline or starts rendering.
  expect(writes.filter(path => path.includes('/api/editor/'))).toEqual([]);
  await page.reload();
  await expect(page.getByRole('article', {name: `Task ${taskId}`})).toContainText('completed');
});

test('pane resizing supports keyboard and mobile switching retains drafts', async ({page}) => {
  await fixture(page);
  await page.setViewportSize({width: 1440, height: 1000});
  await page.goto('/#/video');
  const divider = page.getByRole('separator', {name: 'Resize Director conversation'});
  await divider.focus();
  await divider.press('ArrowRight');
  await expect(divider).toHaveAttribute('aria-valuenow', '36');
  await page.getByLabel('Message the project Director', {exact: true}).fill('Preserve my idea');
  await page.setViewportSize({width: 390, height: 844});
  await page.getByRole('button', {name: 'Workspace', exact: true}).click();
  await expect(page.getByLabel('Message the project Director', {exact: true})).toBeHidden();
  await page.getByRole('button', {name: 'Director chat', exact: true}).click();
  await expect(page.getByLabel('Message the project Director', {exact: true})).toHaveValue('Preserve my idea');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.setViewportSize({width: 1440, height: 1000});
  await page.reload();
  await expect(divider).toHaveAttribute('aria-valuenow', '36');
});
for (const surface of ['video', 'editor']) test(`${surface} approves a continuity frame and previews an image`, async ({page}) => {
  const writes = await fixture(page, true);
  await page.goto('/#/' + surface);
  await page.getByRole('button', {name: 'Context & skills'}).click();
  await page.getByLabel('shot.mp4', {exact: true}).check();
  await page.getByLabel('Message the project Director', {exact: true}).fill('Extract the last frame of this video');
  await page.getByRole('button', {name: 'Send to project Director', exact: true}).click();
  const card = page.getByRole('article', {name: `Task ${taskId}`});
  await expect(card).toContainText('Extract continuity frame');
  await expect(card).not.toContainText('Quality');
  await card.getByRole('button', {name: 'Approve this plan', exact: true}).click();
  await card.getByRole('button', {name: 'Run approved task', exact: true}).click();
  await expect(card.getByRole('img', {name: 'Extracted last frame'})).toBeVisible();
  await expect(card.getByRole('button', {name: 'Offer audio to Editor', exact: true})).toHaveCount(0);
  expect(writes.filter(path => path.endsWith('/run'))).toHaveLength(1);
});

for (const surface of ['video', 'editor']) test(`${surface} freezes explicit computer access before execution`, async ({page}) => {
  const writes = await fixture(page);
  let task;
  const computerWrites = [];
  await page.route('**/api/agent/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (path === '/api/agent/computer-access') return route.fulfill({json: {available: true, session_token: 'test-owned-token', browser_control: false}});
    if (!path.includes('/tasks')) return route.fallback();
    const post = request.method() === 'POST', body = post ? request.postDataJSON() : null;
    if (post) {
      expect(request.headers()['x-vibe-computer-token']).toBe('test-owned-token');
      computerWrites.push(path);
      if (path.endsWith('/tasks')) task = {project_id: owner, task_id: taskId, status: 'draft', current_revision: 1,
        plan_hash: 'd'.repeat(64), plan: {tool_id: body.tool_id, assets: [], scope: 'Project folder access; unrelated personal files and network are blocked.',
          settings: {...body.settings, workspace_path: '/test-owned/project', model: 'test-codex'}}, invocation: null, events: []};
      else {
        expect(body).toEqual({revision: 1, plan_hash: 'd'.repeat(64)});
        if (path.endsWith('/approve')) task.status = 'approved';
        if (path.endsWith('/run')) {task.status = 'completed'; task.report = 'Prepared agent-work/shots.txt; inspect it.';}
      }
    }
    return route.fulfill({json: path.endsWith('/tasks') && !post ? {tasks: task ? [task] : []} : task});
  });
  await page.goto('/#/' + surface);
  const access = page.getByRole('combobox', {name: 'Director access mode', exact: true});
  await expect(access).toHaveValue('app');
  await access.selectOption('project');
  await page.getByLabel('Message the project Director', {exact: true}).fill('Write a shot list in agent-work/');
  await page.getByRole('button', {name: 'Send to project Director', exact: true}).click();
  const card = page.getByRole('article', {name: `Task ${taskId}`});
  await expect(card).toContainText('Project only');
  await expect(card).toContainText('/test-owned/project');
  expect(computerWrites).toHaveLength(1);
  await access.selectOption('full');
  await expect(page.getByText('Codex can access local files outside the project and the network.', {exact: false})).toBeVisible();
  await expect(card).toContainText('Project only');
  await card.getByRole('button', {name: 'Approve this plan', exact: true}).click();
  await card.getByRole('button', {name: 'Run approved task', exact: true}).click();
  await expect(card).toContainText('inspect it.');
  expect(computerWrites.filter(path => path.endsWith('/run'))).toHaveLength(1);
  expect(writes.filter(path => path.endsWith('/conversation'))).toEqual([]);
  expect(await card.locator('audio,img').count()).toBe(0);
});
