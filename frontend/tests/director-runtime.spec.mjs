import {test, expect} from '@playwright/test';

test('image prompt changes use one Director with Apply, stale protection and archived history', async ({page}) => {
  const writes = await fixture(page);
  await page.addInitScript(owner => localStorage.setItem(`vibe-image-director:${owner}:world_master`, JSON.stringify([
    {id: 'old-image', instruction: 'Previous image discussion', suggestion: {prompt: 'Historical room prompt'}}
  ])), owner);
  let saved = [];
  await page.route('**/api/agent/projects/*/conversation', async route => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      expect(body.surface).toBe('image');
      expect(body.target.request.workspace_id).toBe(owner);
      saved.push({request_id: body.request_id, text: body.text, reply: 'Review the image prompt.', status: 'answered', task_id: null,
        proposal: {surface: 'image', target: body.target, draft: {workflow_id: body.target.request.workflow_id, asset_role: 'world_master',
          prompt: 'A ruined room covered in slime.', knowledge_ref: {knowledge_id: 'image-guidance', guidance_version: 1, workflow_sha256: 'a'.repeat(64)}, sources: []}}});
    }
    return route.fulfill({json: {workspace_id: owner, messages: saved}});
  });
  await page.goto('/#/worlds');
  const prompt = page.getByRole('textbox', {name: 'Image prompt', exact: true});
  await prompt.fill('A ruined room.');
  await expect(page.locator('#image-director-message')).toHaveCount(0);
  await expect(page.getByLabel('Message the project Director', {exact: true})).toHaveCount(1);
  await page.getByText('Previous image conversation', {exact: true}).click();
  await expect(page.getByText('Historical room prompt', {exact: true})).toBeVisible();
  await page.getByLabel('Message the project Director', {exact: true}).fill('Cover the room in slime.');
  await page.getByRole('button', {name: 'Send to project Director', exact: true}).click();
  const apply = page.getByRole('button', {name: 'Apply prompt', exact: true});
  await expect(apply).toBeEnabled();
  await expect(prompt).toHaveValue('A ruined room.');
  await prompt.fill('A different room.');
  await expect(apply).toBeDisabled();
  await prompt.fill('A ruined room.');
  await page.reload();
  await expect(apply).toBeEnabled();
  await apply.click();
  await expect(prompt).toHaveValue('A ruined room covered in slime.');
  await expect(apply).toHaveCount(0);
  await page.reload();
  await expect(apply).toHaveCount(0);
  expect(writes.filter(path => path === '/api/images/jobs')).toEqual([]);
});
test('standalone Text to Image uses the shared Director, keeps references typed and leaves generation manual',async({page},info)=>{
  const writes=await fixture(page);let messages=[];
  await page.route('**/api/images/workflows*',route=>route.fulfill({json:{workflows:[{workflow_id:'z_image_turbo',label:'Z Image',available:true,version:'1',defaults:{width:1280,height:720,steps:8,cfg:1}}]}}));
  await page.route('**/api/agent/projects/*/conversation',async route=>{
    if(route.request().method()==='POST'){
      const body=route.request().postDataJSON();expect(body.surface).toBe('image');expect(body.target.request).toEqual({workspace_id:owner,workflow_id:'z_image_turbo',asset_role:'image_candidate',prompt:'A ruined room.'});
      messages.push({request_id:body.request_id,text:body.text,reply:'Review this prompt.',status:'answered',task_id:null,proposal:{surface:'image',target:body.target,draft:{workflow_id:'z_image_turbo',asset_role:'image_candidate',prompt:'A ruined room covered in slime.',knowledge_ref:{knowledge_id:'image-guidance',guidance_version:1,workflow_sha256:'a'.repeat(64)},sources:[]}}});
    }
    return route.fulfill({json:{workspace_id:owner,messages}});
  });
  await page.setViewportSize({width:1280,height:720});await page.goto('/#/text-to-image');
  const prompt=page.getByLabel('Image prompt',{exact:true});await prompt.fill('A ruined room.');
  await expect(page.locator('.director-composer textarea')).toHaveCount(1);await expect(page.locator('#t2i-chat-input')).toHaveCount(0);
  await page.getByLabel('Message the project Director',{exact:true}).fill('Cover the room in slime.');await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  const apply=page.getByRole('button',{name:'Apply prompt',exact:true});await expect(apply).toBeEnabled();await expect(prompt).toHaveValue('A ruined room.');
  await prompt.fill('Another room.');await expect(apply).toBeDisabled();await prompt.fill('A ruined room.');await apply.click();
  await expect(prompt).toHaveValue('A ruined room covered in slime.');await page.reload();await expect(apply).toHaveCount(0);
  for(const width of [1280,390]){await page.setViewportSize({width,height:width===390?844:720});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`text-to-image-${width}.png`)});}
  expect(writes.filter(path=>path.includes('/jobs'))).toEqual([]);
});
const owner = 'story-aaaaaaaaaaaa';
test('chat attachments support paste and drop, persist, and remove without deleting media', async ({page}) => {
  const writes = await fixture(page), uploads = [], bodies = [];
  const files = [];
  const pixel = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5ZkAAAAASUVORK5CYII=', 'base64');
  await page.route(`**/api/media/${owner}/assets?*`, async route => {
    if (route.request().method() === 'POST') {
      uploads.push(new URL(route.request().url()).searchParams.get('filename'));
      files.push({workspace_id:owner,asset_id:`pa-chat-${uploads.length}`,filename:uploads.at(-1),kind:'image',content_url:`/fixture/chat-${uploads.length}.png`,sha256:'d'.repeat(64),roles:['project_image']});
      return route.fulfill({json:files.at(-1)});
    }
    return route.fulfill({json:{assets:files,total:files.length}});
  });
  await page.route('**/fixture/chat-*.png', route => route.fulfill({contentType:'image/png',body:pixel}));
  await page.route('**/api/agent/projects/*/conversation', route => {
    if (route.request().method() === 'POST') bodies.push(route.request().postDataJSON());
    return route.fulfill({json:{workspace_id:owner,messages:[]}});
  });
  await page.goto('/#/home');
  const composer = page.getByLabel('Message the project Director', {exact:true});
  await composer.fill('Discuss this lighting.');
  await composer.evaluate((element, bytes) => {
    const data = new DataTransfer();
    data.items.add(new File([new Uint8Array(bytes)], 'pasted.png', {type:'image/png'}));
    element.dispatchEvent(new ClipboardEvent('paste', {clipboardData:data,bubbles:true,cancelable:true}));
  }, Array.from(pixel));
  await expect(page.getByRole('list', {name:'Chat attachments',exact:true})).toContainText('pasted.png');
  await expect(composer).toHaveValue('Discuss this lighting.');
  await composer.evaluate((element, bytes) => {
    const data = new DataTransfer();
    data.items.add(new File([new Uint8Array(bytes)], 'dropped.png', {type:'image/png'}));
    element.dispatchEvent(new DragEvent('drop', {dataTransfer:data,bubbles:true,cancelable:true}));
  }, Array.from(pixel));
  await expect(page.getByRole('list', {name:'Chat attachments',exact:true}).locator('img')).toHaveCount(2);
  await page.reload();
  await expect(page.getByRole('list', {name:'Chat attachments',exact:true})).toContainText('dropped.png');
  await expect(composer).toHaveValue('Discuss this lighting.');
  await page.getByRole('button',{name:'Remove chat attachment pasted.png',exact:true}).click();
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await expect.poll(()=>bodies.length).toBe(1);
  expect(bodies[0].asset_ids).toEqual(['pa-chat-2']);
  expect(uploads).toEqual(['pasted.png','dropped.png']);
  expect(files).toHaveLength(2);
  expect(writes.filter(path=>path.includes('/jobs'))).toEqual([]);
});
test('older backend chat error explains restart and preserves the creative draft', async ({page}) => {
  await fixture(page);
  await page.route('**/api/agent/projects/*/conversation',route=>route.fulfill(route.request().method()==='POST'
    ? {status:400,json:{error:{message:'Supply request_id, text, asset_ids, skill_refs and surface.'}}}
    : {json:{workspace_id:owner,messages:[]}}));
  await page.goto('/#/text-to-image');
  await page.getByLabel('Image prompt',{exact:true}).fill('A room.');
  const composer=page.getByLabel('Message the project Director',{exact:true});
  await composer.fill('Explain the reference mismatch.');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await expect(page.getByRole('alert').filter({hasText:'running backend is older'})).toBeVisible();
  await expect(composer).toHaveValue('Explain the reference mismatch.');
});
test('shared image references survive reload and removal never deletes library media',async({page})=>{
  const writes=await fixture(page);
  const source={workspace_id:'other',asset_id:'pa-foreign',kind:'image',filename:'saved-reference.png',roles:['project_image'],sha256:'d'.repeat(64),content_url:'/fixture/reference.png',created_at:'2026-11-06'};
  const owned={...source,workspace_id:owner,asset_id:'pa-owned-reference'};
  const reuse=[];
  await page.route('**/api/images/workflows*',route=>route.fulfill({json:{workflows:[{workflow_id:'qwen_image_edit_2511',label:'Qwen Image Edit',version:'1',available:true,defaults:{width:720,height:720,steps:8,cfg:1}}]}}));
  await page.route('**/assets/catalogue?*',route=>route.fulfill({json:{assets:[source],total:1,offset:0,limit:24,workspaces:[owner,'other'],workspace_names:{[owner]:'Film',other:'Other film'}}}));
  await page.route('**/assets/reuse',route=>{reuse.push(route.request().postDataJSON());return route.fulfill({json:owned});});
  await page.route(`**/api/media/${owner}/assets?*`,route=>route.fulfill({json:{assets:[owned],total:1}}));
  await page.goto('/#/text-to-image');
  await page.getByLabel('Image model',{exact:true}).selectOption('qwen_image_edit_2511');
  await page.getByRole('button',{name:'Browse media sources',exact:true}).click();
  const picker=page.locator('.media-source-picker');
  await picker.getByRole('checkbox',{name:source.filename,exact:true}).check();
  await picker.getByRole('button',{name:'Use as image references (1)',exact:true}).click();
  await expect(page.getByLabel('Selected workflow references')).toContainText(source.filename);
  expect(reuse).toEqual([{source_workspace_id:'other',asset_id:source.asset_id,role:'project_image',mode:'reference'}]);
  await page.reload();
  await expect(page.getByLabel('Selected workflow references')).toContainText(source.filename);
  await page.getByRole('button',{name:`Remove reference ${source.filename}`,exact:true}).click();
  await expect(page.getByLabel('Selected workflow references')).not.toContainText(source.filename);
  expect(writes.filter(path=>path.includes('/jobs')||path.includes('/temporary'))).toEqual([]);
});

test('shared catalogue sends audio, index, date and name filters without running analysis',async({page},info)=>{
  const writes=await fixture(page),queries=[];
  await page.route('**/assets/catalogue?*',route=>{
    queries.push(Object.fromEntries(new URL(route.request().url()).searchParams));
    return route.fulfill({json:{assets:[],total:0,offset:0,limit:24,workspaces:[owner],workspace_names:{[owner]:'Film'}}});
  });
  await page.goto('/#/media-prep?tool=utilities');
  const picker=page.locator('.media-source-picker');await picker.locator('summary').first().click();
  await picker.getByText('Filters',{exact:true}).click();
  await picker.getByRole('combobox',{name:'Audio category',exact:true}).selectOption('voice');
  await picker.getByRole('combobox',{name:'Content index',exact:true}).selectOption('indexed');
  await picker.getByLabel('Added from',{exact:true}).fill('2026-11-01');
  await picker.getByLabel('Added through',{exact:true}).fill('2026-11-06');
  await picker.getByLabel('Change sort order',{exact:true}).selectOption('name_asc');
  await expect.poll(()=>queries.at(-1)).toMatchObject({audio_category:'voice',content_index:'indexed',created_after:'2026-11-01',created_before:'2026-11-06',order:'name_asc',offset:'0'});
  for(const width of [1280,390]){
    await page.setViewportSize({width,height:900});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:info.outputPath(`media-filters-${width}.png`)});
  }
  await expect(picker.locator('.media-source-copy')).toHaveCSS('display','flex');
  await picker.getByRole('button',{name:'Clear filters',exact:true}).click();
  await expect.poll(()=>queries.at(-1)?.content_index||'').toBe('');
  expect(writes.filter(path=>path.includes('/jobs')||path.includes('/analysis'))).toEqual([]);
});
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
  const workflow = page.locator('.studio-workflow');
  await expect(workflow).not.toHaveAttribute('open', '');
  await workflow.locator('summary').click();
  await expect(page.getByRole('navigation', {name: 'Story to video stages'})).toBeVisible();
  await workflow.locator('summary').click();
  await expect(page.getByRole('navigation', {name: 'Story to video stages'})).toBeHidden();
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

test('global media attachment is explicit, project-owned and separate from generation', async ({page}) => {
  const writes = await fixture(page);
  const source={workspace_id:'other-project',asset_id:'pa-remote',kind:'audio',filename:'Rain.wav',roles:[],sha256:'a'.repeat(64),content_url:'/fixture.wav'};
  const reused=[];
  await page.route('**/assets/catalogue?**',r=>r.fulfill({json:{assets:[source],total:1,workspace_names:{[owner]:'Test film'},workspaces:[],folders:[]}}));
  await page.route('**/assets/reuse',r=>{reused.push(r.request().postDataJSON());return r.fulfill({json:{...source,workspace_id:owner,asset_id:'pa-local'}});});
  let sent;
  await page.route('**/conversation',r=>{if(r.request().method()==='POST')sent=r.request().postDataJSON();return r.fulfill({json:{messages:[]}});});
  await page.goto('/#/video');
  await page.getByRole('button',{name:'Context & skills',exact:true}).click();
  await page.getByRole('region',{name:'Project Director conversation'}).getByText('Browse media sources',{exact:true}).click();
  const picker=page.locator('.media-source-picker');
  await picker.getByRole('checkbox',{name:'Rain.wav',exact:true}).check();
  expect(reused).toEqual([]);
  await picker.getByRole('button',{name:'Attach to Director (1)',exact:true}).click();
  await expect(page.getByRole('button',{name:'Clear chat attachments (1)',exact:true})).toBeVisible();
  expect(reused).toEqual([{source_workspace_id:'other-project',asset_id:'pa-remote',mode:'reference'}]);
  await page.getByRole('region',{name:'Project Director conversation'}).getByText('Browse media sources',{exact:true}).click();
  await page.getByLabel('Message the project Director',{exact:true}).fill('Discuss this recording.');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await expect.poll(()=>sent?.asset_ids).toEqual(['pa-local']);
  expect(writes.filter(path=>path.includes('/jobs')||path.includes('/tasks'))).toEqual([]);
});

test('attachment capacity and reuse failures preserve the existing chat selection', async ({page}) => {
  await fixture(page);
  const existing=Array.from({length:99},(_,i)=>`existing-${i}`);
  await page.addInitScript(({owner,existing})=>localStorage.setItem(`vibe-project-settings:${owner}:DirectorRuntime:assets`,JSON.stringify(existing)),{owner,existing});
  const assets=['Rain.wav','Wind.wav'].map((filename,i)=>({workspace_id:'other',asset_id:`pa-${i}`,kind:'audio',filename,roles:[],sha256:'a'.repeat(64),content_url:'/fixture.wav'}));
  let calls=0;
  await page.route('**/assets/catalogue?**',r=>r.fulfill({json:{assets,total:2,workspace_names:{[owner]:'Test film'},workspaces:[],folders:[]}}));
  await page.route('**/assets/reuse',r=>{calls++;return r.fulfill({status:503,json:{error:{message:'Fixture unavailable'}}});});
  await page.goto('/#/video');
  await page.getByRole('button',{name:'Context & skills · 99 selected',exact:true}).click();
  await page.getByRole('region',{name:'Project Director conversation'}).getByText('Browse media sources',{exact:true}).click();
  const picker=page.locator('.media-source-picker');
  await picker.getByRole('checkbox',{name:'Rain.wav',exact:true}).check();
  await picker.getByRole('checkbox',{name:'Wind.wav',exact:true}).check();
  await picker.getByRole('button',{name:'Attach to Director (2)',exact:true}).click();
  await expect(picker.getByText('Choose at most 1 more file for this destination.',{exact:true})).toBeVisible();
  expect(calls).toBe(0);
  await picker.getByRole('checkbox',{name:'Wind.wav',exact:true}).uncheck();
  await picker.getByRole('button',{name:'Attach to Director (1)',exact:true}).click();
  await expect(picker.getByText(/destination selection unchanged/)).toBeVisible();
  await expect(picker.getByRole('checkbox',{name:'Rain.wav',exact:true})).toBeChecked();
  expect(await page.evaluate(owner=>JSON.parse(localStorage.getItem(`vibe-project-settings:${owner}:DirectorRuntime:assets`)),owner)).toEqual(existing);
  expect(calls).toBe(1);
});

for(const viewport of [{width:1440,height:900},{width:1280,height:720},{width:900,height:768},{width:390,height:844}]) {
  test(`image and take surfaces fit ${viewport.width}×${viewport.height} and retain drafts`, async ({page},info)=>{
    const writes=await fixture(page);
    await page.setViewportSize(viewport);
    await page.goto('/#/worlds');
    const prompt=page.getByRole('textbox',{name:'Image prompt',exact:true});
    await prompt.fill('Keep the broken room and slime.');
    await expect(page.locator('.image-assets-page .editor-workspace')).toHaveCount(0);
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    const form=await page.locator('.image-form').boundingBox();
    const canvas=await page.locator('.image-assets-page').boundingBox();
    expect(form.width/canvas.width).toBeGreaterThan(0.7);
    await page.getByRole('button',{name:'Hide Director conversation',exact:true}).click();
    await expect(prompt).toHaveValue('Keep the broken room and slime.');
    await page.getByRole('button',{name:'Show Director conversation',exact:true}).click();
    await expect(prompt).toHaveValue('Keep the broken room and slime.');
    await page.screenshot({path:info.outputPath(`image-${viewport.width}.png`),animations:'disabled'});
    await page.goto('/#/take');
    await expect(page.getByRole('heading',{name:'Current take',exact:true,level:1})).toBeVisible();
    await expect(page.locator('.take-review-workspace .editor-workspace')).toHaveCount(0);
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:info.outputPath(`take-${viewport.width}.png`),animations:'disabled'});
    expect(writes.filter(path=>path.includes('/jobs'))).toEqual([]);
  });
}

for(const backend of ['trellis','pixal']) test(`${backend} studio suggestions share the Director, preserve history and require fresh Apply`,async({page})=>{
 const writes=await fixture(page);let messages=[];
 await page.addInitScript(owner=>localStorage.setItem(`vibe-studio-chat-trellis:${owner}`,JSON.stringify([{text:'Earlier studio question',reply:'Preserved studio reply',settings:{seed:5}}])),owner);
 await page.route('**/api/trellis/state?**',route=>route.fulfill({json:{input:'/mock/input',output:'/mock/output',jobs:[]}}));
 await page.route('**/conversation',route=>{
   if(route.request().method()==='POST'){const body=route.request().postDataJSON();expect(body.surface).toBe('studio');expect(body.target.context.settings.backend).toBe(backend);
     messages.push({request_id:body.request_id,text:body.text,reply:'Seed suggestion.',status:'answered',task_id:null,proposal:{surface:'studio',target:body.target,settings:{seed:12}}});}
   return route.fulfill({json:{workspace_id:owner,messages}});
 });
 await page.goto(backend==='pixal'?'/#/image-to-3d-pixal3d':'/#/image-to-3d');
 await expect(page.locator('#chat-trellis')).toHaveCount(0);await expect(page.locator('.director-composer textarea')).toHaveCount(1);
 await page.getByText('Previous studio conversation',{exact:true}).click();await expect(page.getByText('Preserved studio reply',{exact:true})).toBeVisible();
 await page.getByLabel('Message the project Director',{exact:true}).fill('Set seed to 12.');await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
 const apply=page.getByRole('button',{name:'Apply suggested settings',exact:true});await expect(apply).toBeEnabled();
 await page.getByText('Parameters',{exact:true}).click();const seed=page.getByLabel('seed',{exact:true});const initial=await seed.inputValue();
 await seed.fill('2');await expect(apply).toBeDisabled();await seed.fill(initial);await expect(apply).toBeDisabled();
 await page.getByLabel('Message the project Director',{exact:true}).fill('Set seed to 12.');await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
 await expect(apply.last()).toBeEnabled();await apply.last().click();await expect(seed).toHaveValue('12');
 await page.reload();await expect(apply).toHaveCount(1);await expect(apply).toBeDisabled();expect(writes.filter(path=>path.includes('/jobs'))).toEqual([]);
});

test('shared media picker previews Editor ranges without attaching or resetting an unfinished range',async({page})=>{
  const writes=await fixture(page),updates=[];
  const asset={workspace_id:owner,asset_id:'pa-clip',kind:'video',filename:'clip.mp4',content_url:'/mock/clip.mp4',roles:[],media:{duration_seconds:20}};
  let edit={id:'edit-shared',workspace_id:owner,name:'Shared edit',revision:1,selection:[{asset_id:asset.asset_id,start:2,end:8}],messages:[],revisions:[],overrides:{},view:{tab:'media'}};
  await page.route('**/api/editor/projects/edit-shared',route=>{
    if(route.request().method()==='PUT'){const body=route.request().postDataJSON();updates.push(body);edit={...edit,...body};}
    return route.fulfill({json:edit});
  });
  await page.route('**/assets/catalogue?*',route=>route.fulfill({json:{assets:[asset],total:1,workspace_names:{[owner]:'Test film'},workspaces:[owner]}}));
  let reuses=0;
  await page.route('**/assets/reuse',route=>{reuses++;return route.fulfill({json:asset});});
  await page.goto('/#/editor');
  await page.getByRole('button',{name:'Asset selection',exact:true}).click();
  const picker=page.locator('.media-source-picker');
  await page.getByLabel('Editor work surface',{exact:true}).getByRole('button',{name:'Browse media sources',exact:true}).click();
  await picker.getByRole('checkbox',{name:'clip.mp4',exact:true}).check();
  await picker.getByRole('button',{name:'Preview in Editor (1)',exact:true}).click();
  await expect(page.getByLabel('In (seconds)',{exact:true})).toHaveValue('2');
  await expect(page.getByLabel('Out / image hold end (seconds)',{exact:true})).toHaveValue('8');
  expect(updates.filter(body=>body.selection)).toEqual([]);
  await page.getByRole('button',{name:'Close Browse media sources',exact:true}).click();
  await page.getByLabel('In (seconds)',{exact:true}).fill('3.25');
  await page.getByLabel('Out / image hold end (seconds)',{exact:true}).fill('7.75');
  await page.getByLabel('Editor work surface',{exact:true}).getByRole('button',{name:'Browse media sources',exact:true}).click();
  await picker.getByRole('checkbox',{name:'clip.mp4',exact:true}).check();
  await picker.getByRole('button',{name:'Preview in Editor (1)',exact:true}).click();
  await expect(page.getByLabel('In (seconds)',{exact:true})).toHaveValue('3.25');
  await expect(page.getByLabel('Out / image hold end (seconds)',{exact:true})).toHaveValue('7.75');
  expect(reuses).toBe(2);expect(updates.filter(body=>body.selection)).toEqual([]);
  await page.getByLabel('Editor work surface',{exact:true}).getByRole('button',{name:'Browse media sources',exact:true}).click();
  await page.getByRole('button',{name:'Add to edit selection',exact:true}).click();
  await expect.poll(()=>edit.selection).toEqual([{asset_id:'pa-clip',start:2,end:8},{asset_id:'pa-clip',start:3.25,end:7.75}]);
  expect(writes.filter(path=>path.includes('/jobs')||path.endsWith('/command'))).toEqual([]);
});

test('shared Editor preview rejects multiple files before registration',async({page})=>{
  await fixture(page);let reuses=0;
  const assets=['one','two'].map(id=>({workspace_id:owner,asset_id:id,kind:'video',filename:id+'.mp4',roles:[],content_url:'/mock/'+id}));
  await page.route('**/assets/catalogue?*',route=>route.fulfill({json:{assets,total:2,workspace_names:{[owner]:'Test film'},workspaces:[owner]}}));
  await page.route('**/assets/reuse',route=>{reuses++;return route.fulfill({json:assets[0]});});
  await page.goto('/#/editor');await page.getByRole('button',{name:'Asset selection',exact:true}).click();
  await page.getByLabel('Editor work surface',{exact:true}).getByRole('button',{name:'Browse media sources',exact:true}).click();
  const picker=page.locator('.media-source-picker');
  await picker.getByRole('checkbox',{name:'one.mp4',exact:true}).check();await picker.getByRole('checkbox',{name:'two.mp4',exact:true}).check();
  await picker.getByRole('button',{name:'Preview in Editor (2)',exact:true}).click();
  await expect(picker.getByRole('status')).toHaveText('Choose at most 1 more file for this destination.');expect(reuses).toBe(0);
});

test('shared media picker selects audio utility inputs without starting a job',async({page})=>{
  const writes=await fixture(page);let requests=0;
  const asset={workspace_id:owner,asset_id:'pa-source',kind:'video',filename:'source.mp4',roles:[],content_url:'/mock/source.mp4'};
  await page.route('**/api/story/workspaces',route=>route.fulfill({json:{items:[{workspace_id:owner,title:'Test film'}]}}));
  await page.route('**/api/audio/utilities/capabilities',route=>route.fulfill({json:{operations:[{id:'extract_mp3',status:'available'}]}}));
  await page.route('**/utilities/jobs',route=>{if(route.request().method()==='POST')requests++;return route.fulfill({json:[]});});
  await page.route('**/assets/catalogue?*',route=>{expect(new URL(route.request().url()).searchParams.get('kinds')).toBe('audio,video');return route.fulfill({json:{assets:[asset],total:1,workspace_names:{[owner]:'Test film'},workspaces:[owner]}});});
  await page.route('**/assets/reuse',route=>route.fulfill({json:asset}));
  await page.route('**/assets?kind=*',route=>route.fulfill({json:{assets:[],total:0}}));
  await page.goto('/#/media-prep?tool=utilities');
  const utility=page.getByRole('region',{name:'Audio Utilities'});
  await utility.getByText('Browse media sources',{exact:true}).click();
  const picker=utility.locator('.media-source-picker');
  await picker.getByRole('checkbox',{name:'source.mp4',exact:true}).check();await picker.getByRole('button',{name:'Use as MP3 extraction (1)',exact:true}).click();
  await expect(utility.getByText('1 selected',{exact:true})).toBeVisible();
  await expect(utility.getByRole('button',{name:'Run utility',exact:true})).toBeEnabled();
  expect(requests).toBe(0);expect(writes.filter(path=>path.includes('/jobs'))).toEqual([]);
  await utility.getByLabel('Audio utility operation').selectOption('noise_cleanup');
  await expect(utility.getByText('0 selected',{exact:true})).toBeVisible();
  await expect(utility.getByRole('button',{name:'Run utility',exact:true})).toBeDisabled();
});

test('sampled frames show images and exact approved settings in shared chat', async ({page}) => {
  const writes = await fixture(page);
  const task = {project_id: owner, task_id: 'task-sampled-frames', status: 'completed', current_revision: 1,
    plan_hash: 'f'.repeat(64), plan: {tool_id: 'video.sample_frames', scope: 'Explicit timestamps; preserve original media.',
      assets: [{asset_id: 'pa-video', filename: 'shot.mp4', sha256: 'b'.repeat(64)}], settings: {timestamps_seconds: [0, 0.8], snapshot: {}}},
    invocation: {invocation_id: 'call-samples', job_id: 'agent-workspace-samples', state: 'completed'}, events: [],
    outputs: [{workspace_id: owner, asset_id: 'pa-frame', filename: 'frame-0.png', kind: 'image', content_url: '/fixture/frame.png', sha256: 'c'.repeat(64)}],
    report: 'Sample at 0 seconds from approved source.'};
  await page.route('**/fixture/frame.png', route => route.fulfill({contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5ZkAAAAASUVORK5CYII=', 'base64')}));
  await page.route('**/api/agent/projects/*/tasks**', route => route.fulfill({json: new URL(route.request().url()).pathname.endsWith('/tasks') ? {tasks: [task]} : task}));
  await page.goto('/#/editor');
  const card = page.getByRole('article', {name: 'Task task-sampled-frames'});
  await expect(card).toContainText('Inspect video frames');
  await card.getByText('Exact tool settings', {exact: true}).click();
  await expect(card.locator('details pre')).toContainText('timestamps_seconds');
  await expect(card.locator('details pre')).toContainText('0.8');
  await expect(card.getByRole('img', {name: 'frame-0.png'})).toBeVisible();
  await expect(card.locator('audio')).toHaveCount(0);
  await expect(card.getByRole('button', {name: 'Offer audio to Editor'})).toHaveCount(0);
  await page.reload();
  await expect(card.getByRole('img', {name: 'frame-0.png'})).toBeVisible();
  expect(writes.filter(path => path.includes('/jobs') || path.endsWith('/run'))).toEqual([]);
});

test('speech and audio tasks keep truthful labels, settings and timed evidence after reload', async ({page}) => {
  const writes = await fixture(page);
  const rows = [
    ['audio.transcribe', 'Analyze complete-source speech', {}],
    ['audio.noise_cleanup', 'Denoise audio', {model: 'master64', dry: 0}],
    ['audio.demucs_stems', 'Separate audio stems', {stems: 2, device: 'cpu'}],
  ].map(([id, label, settings], index) => ({project_id: owner, task_id: `task-audio-${index}`, status: 'completed',
    current_revision: 1, plan_hash: 'f'.repeat(64), plan: {tool_id: id, scope: 'Complete source; preserve original media.',
      assets: [{asset_id: 'pa-owned', filename: 'speech.wav', sha256: 'b'.repeat(64)}], settings},
    invocation: {invocation_id: `call-${index}`, job_id: `job-${index}`, state: 'completed'}, events: [], outputs: [],
    report: index === 0 ? '6.500–8.000s: review this speech. No cuts or render have been approved.' : undefined, label}));
  await page.route('**/api/agent/projects/*/tasks**', route => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({json: path.endsWith('/tasks') ? {tasks: rows} : rows.find(row => path.endsWith(row.task_id))});
  });
  await page.goto('/#/editor');
  for (const row of rows) await expect(page.getByRole('article', {name: `Task ${row.task_id}`})).toContainText(row.label);
  const speech = page.getByRole('article', {name: 'Task task-audio-0'});
  await expect(speech).toContainText('6.500–8.000s');
  await expect(speech).toContainText('review against playback before cutting');
  await expect(speech.getByRole('button', {name: 'Offer audio to Editor'})).toHaveCount(0);
  await expect(page.getByRole('article', {name: 'Task task-audio-1'})).toContainText('Model master64 · dry mix 0');
  await expect(page.getByRole('article', {name: 'Task task-audio-2'})).toContainText('2 stems · cpu');
  await page.reload();
  await expect(speech).toContainText('6.500–8.000s');
  await expect(page.getByLabel('Message the project Director', {exact: true})).toHaveCount(1);
  expect(writes.filter(path => path.includes('/jobs') || path.endsWith('/run'))).toEqual([]);
});
