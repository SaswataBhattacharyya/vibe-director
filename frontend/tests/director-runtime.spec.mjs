import {test, expect} from '@playwright/test';
const owner = 'story-aaaaaaaaaaaa';
const taskId = 'task-' + 'a'.repeat(32);
async function fixture(page, continuity = false) {
  const writes = [];
  const edit = {id: 'edit-shared', workspace_id: owner, name: 'Shared edit', revision: 1, selection: [], messages: [], revisions: [], overrides: {}, view: {}};
  await page.addInitScript(owner => localStorage.setItem(`vibe-editor-project:${owner}`, 'edit-shared'), owner);
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
    else if (path === '/api/editor/projects/edit-shared') json = edit;
    else if (path === '/api/editor/state') json = {projects: [edit], styles: [], runtime: {ready: false, checks: {}}};
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

test('all eight desktop pane combinations retain the same mounted prompt and restore after reload', async ({page}) => {
  await fixture(page);
  await page.setViewportSize({width: 1440, height: 1000});
  await page.goto('/#/video');
  const shot = page.getByLabel('Shot prompt', {exact: true});
  await shot.fill('An unsaved shot in a ruined room');
  await page.getByLabel('Message the project Director', {exact: true}).fill('Keep this conversation draft');
  for (const left of [true, false]) for (const chat of [true, false]) for (const work of [true, false]) {
    for (const [name, open] of [['navigation', left], ['Director conversation', chat], ['workspace', work]]) {
      const hide = page.getByRole('button', {name: 'Hide '+name, exact: true});
      const current = await hide.count() > 0;
      if (current !== open) await page.getByRole('button', {name: (current ? 'Hide ' : 'Show ')+name, exact: true}).click();
    }
    await expect(page.locator('.director-slot')).toBeVisible({visible: chat});
    await expect(page.locator('.director-workspace>.studio-page-content')).toBeVisible({visible: work});
    expect(await shot.inputValue()).toBe('An unsaved shot in a ruined room');
    expect(await page.locator('#project-director-message').inputValue()).toBe('Keep this conversation draft');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.reload();
  await expect(page.getByRole('button', {name: 'Show navigation', exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Show workspace', exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Show Director conversation', exact: true}).click();
  await expect(page.locator('#project-director-message')).toHaveValue('Keep this conversation draft');
  await page.setViewportSize({width: 390, height: 844});
  await expect(page.locator('#project-director-message')).toBeVisible();
});

test('one Editor composer freezes the session and ranges, preserves history and uses both existing clearances', async ({page}, info) => {
  const writes = await fixture(page);
  let edit = {id: 'edit-shared', workspace_id: owner, name: 'Shared edit', revision: 4,
    selection: [{asset_id: 'pa-image', filename: 'frame.png', start: 1, end: 2}],
    messages: [{id: 'old-message', role: 'assistant', content: 'Preserved earlier session history'}], revisions: [], overrides: {}, view: {}};
  const other = {...edit, id: 'edit-other', name: 'Other saved edit', revision: 8};
  let messages = [], task, sent;
  const commands = [];
  await page.route('**/api/editor/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/state')) return route.fulfill({json: {projects: [edit, other], styles: [], runtime: {ready: false, checks: {}}}});
    if (path.endsWith('/command')) {
      const body = route.request().postDataJSON(); commands.push(body);
      expect(body.action).toBe('approve'); expect(body.revision).toBe(edit.revision);
      edit = {...edit, revision: edit.revision + 1, pending: {kind: 'plan', revision: edit.revision + 1,
        value: {summary: 'Review exact media and tools', tools: ['FFmpeg'], width: 320, height: 180, fps: 24, clips: edit.selection}}};
    }
    return route.fulfill({json: path.endsWith('/edit-other') ? other : edit});
  });
  await page.route('**/api/agent/projects/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (path.endsWith('/conversation')) {
      if (request.method() === 'POST') {
        sent = request.postDataJSON();
        messages = [{request_id: sent.request_id, text: sent.text, reply: 'Review brief preparation.', status: 'answered'}];
        task = {project_id: owner, task_id: taskId, status: 'draft', current_revision: 1, plan_hash: 'f'.repeat(64),
          plan: {tool_id: 'editor.prepare_brief', scope: 'Prepare brief; rendering requires both Editor clearances.',
            assets: [{asset_id: 'pa-image', filename: 'frame.png'}], settings: {instruction: sent.text, target: sent.target}}, invocation: null, events: []};
      }
      return route.fulfill({json: {messages}});
    }
    if (path.endsWith('/tasks')) return route.fulfill({json: {tasks: task ? [task] : []}});
    if (path.includes('/tasks/')) {
      if (path.endsWith('/approve')) task.status = 'approved';
      if (path.endsWith('/run')) {
        task.status = 'completed'; task.report = 'Creative brief ready for clearance 1.';
        edit = {...edit, revision: 5, pending: {kind: 'brief', revision: 5, value: {summary: 'A calm edit', questions: []}}};
      }
      return route.fulfill({json: task});
    }
    return route.fallback();
  });
  await page.goto('/#/editor');
  await expect(page.locator('#edit-chat,.editor-composer,.editor-workspace')).toHaveCount(0);
  await expect(page.locator('#project-director-message')).toBeVisible();
  await page.getByText('Previous Editor session history', {exact: true}).click();
  await expect(page.getByText('Preserved earlier session history', {exact: true})).toBeVisible();
  await page.locator('#project-director-message').fill('Make a calm one-second edit');
  await page.getByRole('button', {name: 'Send to project Director', exact: true}).click();
  const card = page.getByRole('article', {name: `Task ${taskId}`});
  await expect(card).toContainText('Prepare Editor brief');
  expect(sent.target).toEqual({version: 1, editor_session_id: 'edit-shared', expected_revision: 4, selected_ranges: [{asset_id: 'pa-image', start: 1, end: 2}]});
  expect(commands).toEqual([]);
  await card.getByRole('button', {name: 'Approve this plan', exact: true}).click();
  await card.getByRole('button', {name: 'Run approved task', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Clearance 1 · creative brief'})).toBeVisible();
  await page.getByRole('button', {name: 'Approve this revision', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Clearance 2 · media and tools'})).toBeVisible();
  expect(commands).toHaveLength(1); // Never approve clearance 2 or render in this regression.
  await page.getByRole('button', {name: 'Edit timeline', exact: true}).click();
  const timeline = page.getByLabel('Editable timeline JSON', {exact: true});
  const unsaved = (await timeline.inputValue()).replace('Review exact media and tools', 'Unsaved timeline proposal');
  await timeline.fill(unsaved);
  await page.getByRole('button', {name: 'Hide workspace', exact: true}).click();
  await expect(timeline).toBeHidden();
  await page.getByRole('button', {name: 'Show workspace', exact: true}).click();
  await expect(timeline).toHaveValue(unsaved);
  await page.getByRole('button', {name: 'Open session', exact: true}).click();
  await page.getByLabel('Editing project', {exact: true}).selectOption('edit-other');
  await expect(page.getByText('Other saved edit · revision 8', {exact: true})).toBeVisible();
  await expect(card).toContainText('Editor session edit-shared · revision 4');
  expect(writes.filter(path => path.includes('/command'))).toEqual([]);
  await page.getByRole('button', {name: 'Close Open session'}).click();
  await page.getByText('Previous Editor session history', {exact: true}).click();
  await page.evaluate(() => scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => {
    const send = document.querySelector('[aria-label="Send to project Director"]').getBoundingClientRect();
    const footer = document.querySelector('.studio-taskbar').getBoundingClientRect();
    const access = document.querySelector('[aria-label="Director access mode"]').getBoundingClientRect();
    const controls = document.querySelector('.director-composer-context').getBoundingClientRect();
    return send.bottom <= footer.top && send.top >= 0 && access.top >= controls.top && access.bottom <= controls.bottom;
  })).toBe(true);
  await expect(page.getByRole('button', {name:'Context & skills', exact:true})).toBeInViewport();
  await expect(page.getByLabel('Director access mode')).toBeInViewport();
  await page.screenshot({path: info.outputPath('unified-editor-desktop.png'), animations: 'disabled'});
});


test('pane preferences and conversation drafts remain isolated across project A → B → A', async ({page}) => {
  await fixture(page);
  let ownerNow = owner;
  const memories = {};
  await page.route('**/api/projects/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/memory')) {const body = route.request().postDataJSON(); memories[body.workspace_id] = body.browser_state; return route.fulfill({json: {saved: true}});}
    if (path.endsWith('/open')) ownerNow = route.request().postDataJSON().folder === '/test-owned/A' ? owner : 'story-bbbbbbbbbbbb';
    return route.fulfill({json: {workspace_id: ownerNow, title: ownerNow === owner ? 'Project A' : 'Project B', folder: '/test-owned/' + (ownerNow === owner ? 'A' : 'B'), browser_state: memories[ownerNow] || {}}});
  });
  const open = async (folder) => {
    await page.getByRole('button', {name: 'Load project', exact: true}).click();
    await page.getByLabel('Project folder path', {exact: true}).fill(folder);
    await page.getByRole('button', {name: 'Open project', exact: true}).click();
    await page.keyboard.press('Escape');
  };
  await page.goto('/#/video');
  await page.locator('#project-director-message').fill('Only project A');
  await page.getByRole('button', {name: 'Hide workspace', exact: true}).click();
  await open('/test-owned/B');
  await expect(page.getByLabel('Project controls')).toContainText('Project B');
  await expect(page.locator('#project-director-message')).toHaveValue('');
  await expect(page.getByRole('button', {name: 'Hide workspace', exact: true})).toBeVisible();
  await page.locator('#project-director-message').fill('Only project B');
  await open('/test-owned/A');
  await expect(page.getByLabel('Project controls')).toContainText('Project A');
  await expect(page.locator('#project-director-message')).toHaveValue('Only project A');
  await expect(page.getByRole('button', {name: 'Show workspace', exact: true})).toBeVisible();
});
