import { test, expect } from '@playwright/test';

const makeStyle = (type, name, version = 1, custom = false) => ({
  production_type: type, display_name: name, style_version: version, style_version_id: `${type}-v${version}`,
  narrative_guidance: { story: 'Story focus', scene_direction: 'Scene focus', image: 'Image focus', audio: 'Audio focus', video: 'Video focus', review: 'Review focus' },
  narrative_hash: `${type}-narrative-hash`, director_profile: { display_name: name, purpose: `${name} purpose`, behavior: ['Keep direction consistent'], review_priorities: ['Review clarity'] },
  director_profile_hash: `${type}-profile-hash`, director_profile_version: 'director-v1', custom,
});

test('style selection is explicitly frozen and recovered without a reload POST; custom publication does not select it', async ({ page }) => {
  const styles = [makeStyle('story_film', 'Story / film'), makeStyle('social_profile', 'Social / short-form'), makeStyle('corporate_pitch', 'Corporate pitch'), makeStyle('informative', 'Informative / educational'), makeStyle('news_report', 'News report'), makeStyle('advertisement', 'Advertisement')];
  let selection = null;
  let customVersion = 0;
  const posts = [];
  await page.route('**/api/styles/**', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.pathname === '/api/styles/catalog' && request.method() === 'GET') return route.fulfill({ json: { catalog_version: 'fixture-catalog-v1', production_types: styles } });
    if (url.pathname === '/api/styles/selections' && request.method() === 'GET') return route.fulfill({ json: { selections: selection ? [selection] : [] } });
    if (url.pathname === '/api/styles/selections' && request.method() === 'POST') {
      posts.push({ path: url.pathname, body: request.postDataJSON() });
      const body = request.postDataJSON(), item = styles.find(style => style.style_version_id === body.style_version_id);
      selection = { ...item, snapshot_id: 'snapshot-1', isolated_context_id: body.isolated_context_id };
      return route.fulfill({ status: 201, json: selection });
    }
    if (url.pathname === '/api/styles/types' && request.method() === 'POST') {
      const body = request.postDataJSON(); posts.push({ path: url.pathname, body });
      customVersion += 1;
      const item = { ...makeStyle(body.production_type, body.director_profile.display_name, customVersion, true), narrative_guidance: body.narrative_guidance, director_profile: body.director_profile };
      for (let index = styles.length - 1; index >= 0; index -= 1) if (styles[index].production_type === body.production_type) styles.splice(index, 1);
      styles.push(item);
      return route.fulfill({ status: 201, json: { ...item, display_name: undefined, custom: undefined } });
    }
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'Unexpected mocked style API request' } } });
  });

  await page.goto('/#/styles');
  await expect(page.getByRole('heading', { name: 'Production Type & Style' })).toBeVisible();
  await expect(page.locator('.style-type-card')).toHaveCount(6);
  const context = await page.locator('.style-context-card code').textContent();
  expect(context).toMatch(/^setup-/);
  await page.getByLabel('Production type and version').selectOption('story_film-v1');
  expect(posts).toHaveLength(0);
  await page.getByRole('button', { name: 'Save selection' }).click();
  await expect(page.getByText('Saved version pinned')).toBeVisible();
  expect(posts[0].body).toEqual({ isolated_context_id: context, production_type: 'story_film', style_version_id: 'story_film-v1' });

  await page.getByLabel('Type ID').fill('custom_doc_film');
  await page.getByLabel('Display name').fill('Documentary film');
  await page.getByLabel('Director purpose').fill('Tell grounded factual stories.');
  for (const label of ['Story guidance', 'Scene direction', 'Image guidance', 'Audio guidance', 'Video guidance', 'Review guidance']) await page.getByLabel(label).fill(`${label} text`);
  await page.getByLabel('Director behavior One behavior per line').fill('Preserve evidence');
  await page.getByLabel('Review priorities One priority per line').fill('Check source clarity');
  const pinnedBeforePublish = posts.filter(item => item.path.endsWith('/selections')).length;
  await page.getByRole('button', { name: 'Publish custom type' }).click();
  await expect(page.getByText(/was published as version 1\. It was not selected automatically\./)).toBeVisible();
  expect(posts.filter(item => item.path.endsWith('/selections'))).toHaveLength(pinnedBeforePublish);
  expect(selection.style_version_id).toBe('story_film-v1');
  expect(posts.find(item => item.path.endsWith('/types')).body.narrative_guidance).toEqual({ story: 'Story guidance text', scene_direction: 'Scene direction text', image: 'Image guidance text', audio: 'Audio guidance text', video: 'Video guidance text', review: 'Review guidance text' });

  await page.getByLabel('Production type and version').selectOption('custom_doc_film-v1');
  await page.getByRole('button', { name: 'Save selection' }).click();
  await expect(page.getByText('Saved selection: custom_doc_film · custom_doc_film-v1. Unsaved changes remain a draft.')).toBeVisible();
  await page.getByLabel('Director purpose').fill('A revised grounded documentary direction.');
  await page.getByRole('button', { name: 'Publish custom type' }).click();
  await expect(page.getByText(/was published as version 2\. It was not selected automatically\./)).toBeVisible();
  expect(selection.style_version_id).toBe('custom_doc_film-v1');

  const beforeReload = posts.length;
  await page.reload();
  await expect(page.getByText('Saved selection: custom_doc_film · custom_doc_film-v1. Unsaved changes remain a draft.')).toBeVisible();
  await expect(page.getByRole('option', { name: 'Documentary film · v1 · custom' })).toHaveCount(1);
  await page.locator('.style-type-card-selected').locator('details summary').click();
  await expect(page.locator('.style-type-card-selected').getByText('Story guidance text', {exact:true})).toBeVisible();
  await expect(page.getByRole('option', { name: 'Documentary film · v2 · custom' })).toHaveCount(1);
  await page.getByLabel('Production type and version').selectOption('custom_doc_film-v2');
  expect(selection.style_version_id).toBe('custom_doc_film-v1');
  expect(posts.filter(item => item.path.endsWith('/selections'))).toHaveLength(2);
  expect(posts).toHaveLength(beforeReload);
});

test('lost selection response blocks retries until a read-only refresh confirms the committed snapshot', async ({ page }) => {
  const styles = [makeStyle('story_film', 'Story / film')];
  let committed = null;
  const posts = [];
  await page.route('**/api/styles/**', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.pathname === '/api/styles/catalog' && request.method() === 'GET') return route.fulfill({ json: { catalog_version: 'fixture-v1', production_types: styles } });
    if (url.pathname === '/api/styles/selections' && request.method() === 'GET') return route.fulfill({ json: { selections: committed ? [committed] : [] } });
    if (url.pathname === '/api/styles/selections' && request.method() === 'POST') {
      posts.push(request.postDataJSON());
      const body = request.postDataJSON(); committed = { ...styles[0], snapshot_id: 'committed-but-response-lost', isolated_context_id: body.isolated_context_id };
      return route.abort('failed');
    }
    return route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'Unexpected mocked style API request' } } });
  });
  await page.goto('/#/styles');
  await page.getByLabel('Production type and version').selectOption('story_film-v1');
  await page.getByRole('button', { name: 'Save selection' }).click();
  await expect(page.getByText(/server may have saved this version/i)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save selection' })).toBeDisabled();
  expect(posts).toHaveLength(1);
  await page.getByRole('button', { name: 'Refresh catalog' }).click();
  await expect(page.getByText('Saved selection: story_film · story_film-v1. Unsaved changes remain a draft.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save selection' })).toBeEnabled();
  expect(posts).toHaveLength(1);
});
