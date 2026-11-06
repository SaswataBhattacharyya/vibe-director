import {test, expect} from '@playwright/test';
const A = 'story-aaaaaaaaaaaa', B = 'story-bbbbbbbbbbbb';
async function fixture(page, initial = 'tool-library') {
  let owner = initial;
  const calls = [], writes = [];
  const project = () => ({workspace_id: owner, title: owner === A ? 'Project A' : owner === B ? 'Project B' : 'Standalone tools', browser_state: {}});
  let release;
  const held = new Promise(resolve => {release = resolve;});
  let hold = false;
  await page.route('**/api/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    if (req.method() !== 'GET') writes.push(path);
    if (path === '/api/studio-tools/output-destination') return route.fulfill({json: {mode: 'folder', path: '/test-owned/output', available: true}});
    if (path === '/api/projects/current') return route.fulfill({json: project()});
    if (path === '/api/projects/memory') return route.fulfill({json: {saved: true}});
    if (path === '/api/projects/open') {owner = B; return route.fulfill({json: project()});}
    if (path.endsWith('/conversation')) return route.fulfill({json: {workspace_id: owner, messages: []}});
    if (path.endsWith('/tasks')) return route.fulfill({json: {tasks: []}});
    if (path.startsWith('/api/agent/')) {
      calls.push(req.method() + ' ' + url.pathname + url.search);
      const requested = url.searchParams.get('workspace_id') || path.split('/')[4];
      if (hold && requested === A) await held;
      const json = path.endsWith('/tools') ? {tools: [{id: 'audio.extract_mp3', effect: 'submit', status: 'available', execution_enabled: false, input_schema: {}}]} :
        path.endsWith('/skills') ? {skills: [{ref: 'application/vibe/craft', scope: 'application', provider: 'vibe', id: 'craft', available: true, description: 'Craft guide', sha256: 'a'.repeat(64)}], truncated: false} :
        {workspace_id: requested, nodes: [{id: 'workspace:' + requested, kind: 'workspace', source_id: requested, owner: requested, provenance: 'project registry', label: requested === A ? 'Context A' : requested === B ? 'Context B' : 'Standalone context'}], relations: [], truncated: []};
      return route.fulfill({json}).catch(() => {});
    }
    if (path === '/api/director/settings') return route.fulfill({json: {settings: {provider: 'codex', model: 'test', lessons: []}, models: []}});
    if (path === '/api/story/workspaces') return route.fulfill({json: {items: []}});
    if (path === '/api/editor/state') return route.fulfill({json: {projects: [], styles: [], runtime: {ready: false, checks: {}}}});
    if (path.endsWith('/assets')) return route.fulfill({json: {assets: [], total: 0}});
    return route.fulfill({status: 404, json: {error: {message: 'Unused mock ' + path}}});
  });
  return {calls, writes, hold: () => {hold = true;}, release};
}
for (const route of ['video', 'editor']) {
  test(`shared discovery on ${route} is collapsed, keyboard accessible and read only`, async ({page}) => {
    const mock = await fixture(page);
    await page.goto('/#/' + route);
    const inspector = page.getByRole('region', {name: 'Agent discovery'});
    const toggle = inspector.getByRole('button', {name: 'Show agent capabilities'});
    await expect(toggle).toBeVisible();
    expect(mock.calls).toEqual([]);
    if (route === 'video') {
      await expect(page.locator('.create-workspace-wrap').getByLabel('Shot prompt', {exact: true})).toBeVisible();
      await page.locator('.create-workspace-wrap').getByLabel('Shot prompt', {exact: true}).fill('Unsaved independent shot');
    }
    await toggle.focus(); await page.keyboard.press('Enter');
    await expect(inspector).toContainText('audio.extract_mp3');
    await expect(inspector).toContainText('Craft guide');
    await expect(inspector).toContainText('Standalone context');
    expect(mock.calls).toHaveLength(3);
    expect(mock.calls.every(call => call.startsWith('GET '))).toBe(true);
    // Existing output-destination reads use POST; discovery itself must only GET.
    expect(mock.writes.filter(path => !['/api/projects/memory', '/api/studio-tools/output-destination'].includes(path))).toEqual([]);
    await page.setViewportSize({width: 390, height: 844});
    await expect(inspector.getByRole('button', {name: 'Hide agent capabilities'})).toBeVisible();
    expect(await inspector.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
    await inspector.getByRole('button').click();
    if (route === 'video') await expect(page.getByLabel('Shot prompt', {exact: true})).toHaveValue('Unsaved independent shot');
  });
}
test('late discovery cannot cross an open-project change', async ({page}) => {
  const mock = await fixture(page, A); mock.hold();
  await page.goto('/#/editor');
  await page.getByRole('button', {name: 'Show agent capabilities'}).click();
  await expect.poll(() => mock.calls.length).toBe(3);
  await page.getByRole('button', {name: 'Load project', exact: true}).click();
  await page.getByLabel('Project folder path', {exact: true}).fill('/test-owned/B');
  await page.getByRole('button', {name: 'Open project', exact: true}).click();
  await expect(page.getByLabel('Project controls')).toContainText('Project B');
  mock.release();
  await page.getByRole('button', {name: 'Show agent capabilities'}).click();
  const inspector = page.getByRole('region', {name: 'Agent discovery'});
  await expect(inspector).toContainText('Context B');
  await expect(inspector).not.toContainText('Context A');
});

test('the existing sidebar still opens Media Prep and Editor without a story', async ({page}) => {
  const mock = await fixture(page);
  await page.goto('/#/video');
  const navigation = page.getByRole('navigation', {name: 'Studio navigation'});
  await navigation.getByRole('link', {name: 'Media Prep', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Media tools', exact: true})).toBeVisible();
  await navigation.getByRole('link', {name: 'Vibe Editor', exact: true}).click();
  await expect(page.getByRole('navigation', {name: 'Editor panels'})).toBeVisible();
  expect(mock.calls).toEqual([]);
});
