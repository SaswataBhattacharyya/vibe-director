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
  await expect(page.getByText('Selected type: Story / film · v1.')).toBeVisible();
  expect(posts).toHaveLength(0);
  await page.getByRole('button', { name: 'Save selection' }).click();
  await expect(page.getByText('Saved Story / film with Cinematic direction. Both choices are frozen in this setup context.')).toBeVisible();
  await expect(page.getByText('Saved type: story_film · story_film-v1.')).toBeVisible();
  expect(posts[0].body).toEqual({ isolated_context_id: context, production_type: 'story_film', style_version_id: 'story_film-v1', directing_style_id: 'cinematic' });

  await page.getByLabel('Type ID').fill('custom_doc_film');
  await page.getByRole('form', { name: 'Create production type' }).getByLabel('Display name').fill('Documentary film');
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
  await expect(page.getByText('Saved type: custom_doc_film · custom_doc_film-v1.')).toBeVisible();
  await page.getByLabel('Director purpose').fill('A revised grounded documentary direction.');
  await page.getByRole('button', { name: 'Publish custom type' }).click();
  await expect(page.getByText(/was published as version 2\. It was not selected automatically\./)).toBeVisible();
  expect(selection.style_version_id).toBe('custom_doc_film-v1');

  const beforeReload = posts.length;
  await page.reload();
  await expect(page.getByText('Saved type: custom_doc_film · custom_doc_film-v1.')).toBeVisible();
  await expect(page.getByRole('option', { name: 'Documentary film · v1 · custom' })).toHaveCount(1);
  await page.locator('.style-type-card-selected').locator('details summary').click();
  await expect(page.locator('.style-type-card-selected').getByText('Story guidance text', {exact:true})).toBeVisible();
  await expect(page.getByRole('option', { name: 'Documentary film · v2 · custom' })).toHaveCount(1);
  await page.getByLabel('Production type and version').selectOption('custom_doc_film-v2');
  expect(selection.style_version_id).toBe('custom_doc_film-v1');
  expect(posts.filter(item => item.path.endsWith('/selections'))).toHaveLength(2);
  expect(posts).toHaveLength(beforeReload);
});

test('story style editor saves to the workspace and explains derived-work staleness', async ({ page }) => {
  const workspaceId = 'story-workspace-123';
  const styles = [makeStyle('story_film', 'Story / film')];
  let saved = null;
  const posts = [];
  await page.route('**/api/styles/**', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.pathname === '/api/styles/catalog' && request.method() === 'GET') return route.fulfill({ json: { catalog_version: 'fixture-v1', production_types: styles, directing_styles: [{style_id:'cinematic',display_name:'Cinematic',version:1,guidance:'Clear visual language',style_hash:'cinematic-hash'}] } });
    if (url.pathname === '/api/styles/selections' && request.method() === 'GET') {
      expect(url.searchParams.get('workspace_id')).toBe(workspaceId);
      return route.fulfill({ json: { selections: saved ? [saved] : [] } });
    }
    if (url.pathname === '/api/styles/selections' && request.method() === 'POST') {
      const body = request.postDataJSON(); posts.push(body);
      saved = { ...styles[0], snapshot_id:'workspace-style-snapshot', workspace_id:body.workspace_id, directing_style:{style_id:'cinematic',display_name:'Cinematic',version:1} };
      return route.fulfill({ status:201, json:saved });
    }
    return route.fulfill({status:404,json:{error:{message:'Unexpected style request'}}});
  });
  await page.goto(`/#/styles?workspace_id=${workspaceId}`);
  await expect(page.getByText(`Editing the pinned style for story ${workspaceId}.`)).toBeVisible();
  await page.getByLabel('Production type and version').selectOption('story_film-v1');
  await page.getByRole('button', {name:'Save selection'}).click();
  await expect(page.getByText(/New screenplay drafts will use this selection; earlier derived work is stale\./)).toBeVisible();
  expect(posts).toEqual([{workspace_id:workspaceId,production_type:'story_film',style_version_id:'story_film-v1',directing_style_id:'cinematic',directing_style_version_id:undefined}]);
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
  await expect(page.getByText('Selected type: Story / film · v1.')).toBeVisible();
  await page.getByRole('button', { name: 'Save selection' }).click();
  await expect(page.getByText(/server may have saved this version/i)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save selection' })).toBeDisabled();
  expect(posts).toHaveLength(1);
  await page.getByRole('button', { name: 'Refresh catalog' }).click();
  await expect(page.getByText('Saved type: story_film · story_film-v1.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save selection' })).toBeEnabled();
  expect(posts).toHaveLength(1);
});

test('style reference media is uploaded into the setup library and linked to the saved directing style', async ({ page }) => {
  const style = makeStyle('story_film', 'Story / film');
  const direction = { style_id: 'horror', display_name: 'Horror', version: 1, guidance: 'Controlled unease', style_hash: 'horror-hash' };
  const context = 'setup-12345678-1234-1234-1234-123456789abc';
  const media = [];
  await page.addInitScript(id => localStorage.setItem('vibe-style-setup-context-v1', id), context);
  await page.route('**/api/styles/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/styles/catalog') return route.fulfill({ json: { catalog_version: 'fixture-v1', production_types: [style], directing_styles: [direction] } });
    if (url.pathname === '/api/styles/selections') return route.fulfill({ json: { selections: [{ ...style, directing_style: direction, snapshot_id: 'snapshot-1', isolated_context_id: context }] } });
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected style request' } } });
  });
  await page.route('**/api/media/**', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.pathname === `/api/media/${context}/assets` && request.method() === 'GET') {
      const kind = url.searchParams.get('kind');
      return route.fulfill({ json: { assets: media.filter(asset => asset.kind === kind), total: media.filter(asset => asset.kind === kind).length } });
    }
    if (url.pathname === `/api/media/${context}/assets` && request.method() === 'POST') {
      const asset = { asset_id: 'pa-1234567890abcdef', workspace_id: context, kind: 'video', roles: ['style_reference'], filename: 'look.mp4', media_type: 'video/mp4', sha256: 'a'.repeat(64), size_bytes: 12, content_url: '/fixture/look.mp4', created_at: '2026-10-10T00:00:00Z', metadata: {}, media: {duration_seconds: 8} };
      media.push(asset);
      return route.fulfill({ status: 201, json: { ...asset, deduplicated: false } });
    }
    if (url.pathname.endsWith('/style-reference') && request.method() === 'POST') {
      const asset = media[0]; asset.metadata.directing_style_ids = [request.postDataJSON().directing_style_id];
      return route.fulfill({ json: asset });
    }
    if (url.pathname.endsWith('/style-frames') && request.method() === 'POST') {
      const body = request.postDataJSON();
      const frames = body.timestamps_seconds.map((timestamp, index) => ({ asset_id: `pa-frame-${index}`, workspace_id: context, kind: 'image', roles: ['style_reference'], filename: `look-${index}.jpg`, media_type: 'image/jpeg', sha256: String(index).padStart(64, '0'), size_bytes: 10, content_url: `/fixture/frame-${index}.jpg`, created_at: '2026-10-10T00:00:00Z', metadata: {directing_style_ids: [body.directing_style_id], style_frame_sources: [{parent_video_asset_id: 'pa-1234567890abcdef', parent_video_sha256: 'a'.repeat(64), source_width: 1920, source_height: 1080, timestamp_seconds: timestamp, directing_style_id: body.directing_style_id, extraction: {method:'ffmpeg-single-frame-jpeg-v1', max_width:1920, quality:2}}]} }));
      media.push(...frames);
      return route.fulfill({ status: 202, json: {job_id:'style-frames-fixture',status:'running',progress:1,stage:'starting',message:'Worker started.',request:{workspace_id:context,asset_id:'pa-1234567890abcdef',timestamps_seconds:body.timestamps_seconds}} });
    }
    if (url.pathname.endsWith('/style-frame-jobs/style-frames-fixture') && request.method() === 'GET') return route.fulfill({json:{job_id:'style-frames-fixture',status:'completed',progress:100,stage:'completed',message:'Job completed.',request:{workspace_id:context,asset_id:'pa-1234567890abcdef',timestamps_seconds:[2,6]},result:{frames:media.slice(1)}}});
    return route.fulfill({ status: 404, json: { error: { message: 'Unexpected media request' } } });
  });

  await page.goto('/#/styles');
  await expect(page.getByRole('heading', { name: 'Add reference media' })).toBeVisible();
  await page.getByLabel('Reference file').setInputFiles({ name: 'look.mp4', mimeType: 'video/mp4', buffer: Buffer.from('fixture') });
  await page.getByRole('button', { name: 'Add reference' }).click();
  await expect(page.getByText('look.mp4', { exact: true })).toBeVisible();
  await expect(page.locator('.style-reference-item video')).toHaveAttribute('src', '/fixture/look.mp4');
  expect(media[0].metadata.directing_style_ids).toEqual(['horror']);
  await expect(page.getByLabel('Style frame count')).toHaveValue('2');
  await expect(page.getByLabel('Frame 1 timestamp (seconds)')).toHaveValue('2');
  await page.getByLabel('Style frame count').fill('0');
  await expect(page.getByText('0 frames selected; the video remains available as a video reference.')).toBeVisible();
  await page.getByLabel('Style frame count').fill('2');
  await page.getByRole('button', {name:'Extract selected frames'}).click();
  await expect(page.getByRole('progressbar', {name:'Style frame extraction progress'})).toBeVisible();
  await expect(page.locator('.style-reference-item')).toHaveCount(3);
  expect(media.slice(1).map(asset=>asset.metadata.style_frame_sources[0].timestamp_seconds)).toHaveLength(2);
});

test('custom directing styles publish as versions and pin the exact version in a saved setup', async ({ page }) => {
  const production = makeStyle('story_film', 'Story / film');
  const otherProduction = makeStyle('social_profile', 'Social / short-form');
  const directions = [{style_id:'cinematic',display_name:'Cinematic',version:1,guidance:'Coherent direction',style_hash:'cinematic-hash'}];
  let frozen = null;
  const posts = [];
  const evidenceAsset={asset_id:'pa-0123456789abcdef',workspace_id:'setup-12345678-1234-1234-1234-123456789abc',kind:'image',roles:['style_reference'],filename:'rainy-alley.png',media_type:'image/png',sha256:'a'.repeat(64),size_bytes:12,content_url:'/fixture/rainy-alley.png',created_at:'2026-10-10T00:00:00Z',metadata:{}};
  const context=evidenceAsset.workspace_id;
  await page.addInitScript(id=>{localStorage.setItem('vibe-style-setup-context-v1',id);localStorage.removeItem('vibe-custom-direction-form-v1');},context);
  await page.route('**/api/styles/**', async route => {
    const request=route.request(), url=new URL(request.url()), body=request.postDataJSON?.() || {};
    if(url.pathname==='/api/styles/catalog'&&request.method()==='GET') return route.fulfill({json:{catalog_version:'fixture-v3',production_types:[production,otherProduction],directing_styles:directions}});
    if(url.pathname==='/api/styles/selections'&&request.method()==='GET') return route.fulfill({json:{selections:frozen?[frozen]:[]}});
    if(url.pathname==='/api/styles/directing-styles'&&request.method()==='POST'){
      posts.push({path:url.pathname,body});
      const direction={style_id:body.style_id,display_name:body.display_name,version:1,style_version_id:`custom-direction:${body.style_id}:v1:hash`,guidance:body.guidance,style_hash:'custom-hash',scope_type:body.scope_type,production_type_scope:body.production_type_scope||null,custom:true,evidence:body.evidence};
      directions.push(direction);
      return route.fulfill({status:201,json:direction});
    }
    if(url.pathname==='/api/styles/selections'&&request.method()==='POST'){
      posts.push({path:url.pathname,body});
      const direction=directions.find(item=>item.style_id===body.directing_style_id);
      frozen={...(body.production_type===otherProduction.production_type?otherProduction:production),directing_style:direction,snapshot_id:'snapshot-custom-direction',isolated_context_id:body.isolated_context_id};
      return route.fulfill({status:201,json:frozen});
    }
    return route.fulfill({status:404,json:{error:{message:'Unexpected style request'}}});
  });
  await page.route('**/api/media/**', async route=>{
    const request=route.request(),url=new URL(request.url());
    if(url.pathname===`/api/media/${context}/assets`&&request.method()==='GET')return route.fulfill({json:{assets:[evidenceAsset],total:1}});
    if(url.pathname===`/api/media/${context}/assets/${evidenceAsset.asset_id}/style-reference`&&request.method()==='POST'){
      posts.push({path:'/style-reference',body:request.postDataJSON()});return route.fulfill({json:evidenceAsset});
    }
    return route.fulfill({status:404,json:{error:{message:'Unexpected media request'}}});
  });
  await page.goto('/#/styles');
  await page.getByLabel('Production type and version').selectOption('story_film-v1');
  await page.getByLabel('Style ID').fill('neo_noir');
  await page.getByRole('form', {name:'Create directing style'}).getByLabel('Display name').fill('Neo-noir');
  await page.getByLabel('Directing guidance').fill('Use motivated shadows and restrained camera movement.');
  await page.getByLabel('Directing style scope').selectOption('production_type');
  await page.getByRole('group', { name: 'Reference media for this style (optional)' }).getByRole('checkbox').check();
  await page.getByRole('button',{name:'Publish directing style'}).click();
  await expect(page.getByRole('status').filter({hasText:'Each selected reference needs a short note'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Publish directing style'})).toBeEnabled();
  expect(posts.filter(item=>item.path==='/api/styles/directing-styles')).toHaveLength(0);
  await page.getByLabel('What to use from rainy-alley.png').fill('Use the wet pavement reflections and isolated framing.');
  await page.getByRole('button',{name:'Publish directing style'}).click();
  await expect(page.getByText(/published as directing-style version 1/)).toBeVisible();
  expect(posts.find(item=>item.path==='/api/styles/directing-styles').body).toMatchObject({isolated_context_id:context,scope_type:'production_type',production_type_scope:'story_film',evidence:[{asset_id:evidenceAsset.asset_id,kind:'image',sha256:evidenceAsset.sha256,intent:'Use the wet pavement reflections and isolated framing.'}]});
  await expect(page.getByLabel('Directing style', {exact:true})).toHaveValue('neo_noir');
  await expect(page.getByLabel('Directing style', {exact:true}).locator('option[value="neo_noir"]')).toHaveCount(1);
  await page.getByLabel('Production type and version').selectOption('social_profile-v1');
  await expect(page.getByLabel('Directing style', {exact:true})).toHaveValue('cinematic');
  await expect(page.getByLabel('Directing style', {exact:true}).locator('option[value="neo_noir"]')).toHaveCount(0);
  await page.getByLabel('Production type and version').selectOption('story_film-v1');
  await page.getByLabel('Directing style', {exact:true}).selectOption('neo_noir');
  await page.getByRole('button',{name:'Save selection'}).click();
  expect(posts.find(item=>item.path==='/api/styles/selections').body.directing_style_version_id).toBe('custom-direction:neo_noir:v1:hash');
  await expect.poll(()=>posts.some(item=>item.path==='/style-reference')).toBeTruthy();
  expect(posts.find(item=>item.path==='/style-reference').body).toEqual({directing_style_id:'neo_noir'});
  expect(frozen.directing_style.style_hash).toBe('custom-hash');
});

test('style documents produce cited editable rules that require review before publication', async ({ page }) => {
  const context='setup-12345678-1234-1234-1234-123456789abc';
  const source={source_id:'style-source-0123456789abcdef',sha256:'a'.repeat(64),filename:'look-guide.txt',source_type:'text',byte_length:42,text_character_count:25,evidence_blocks:[{locator:'line:1-1',text:'Use quiet dialogue.'}]};
  await page.addInitScript(id=>localStorage.setItem('vibe-style-setup-context-v1',id),context);
  const posts=[];
  await page.route('**/api/styles/**',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(url.pathname==='/api/styles/catalog')return route.fulfill({json:{catalog_version:'test',production_types:[makeStyle('story_film','Story / film')],directing_styles:[{style_id:'cinematic',display_name:'Cinematic',version:1,guidance:'Coherent',style_hash:'hash'}]}});
    if(url.pathname==='/api/styles/selections')return route.fulfill({json:{selections:[]}});
    if(url.pathname==='/api/styles/sources'&&request.method()==='GET')return route.fulfill({json:{sources:[]}});
    if(url.pathname==='/api/styles/sources/analyze'&&request.method()==='POST'){
      posts.push({path:url.pathname,body:request.postDataJSON()});
      return route.fulfill({json:{status:'proposal',persisted:false,published:false,provider:'test',display_name:'Quiet Film',guidance:'Use quiet dialogue.',evidence:[{kind:'document',source_id:source.source_id,source_sha256:source.sha256,filename:source.filename,locator:'line:1-1',quote:'Use quiet dialogue.',intent:'Keep dialogue restrained.'}]}});
    }
    if(url.pathname==='/api/styles/directing-styles'&&request.method()==='POST'){
      const body=request.postDataJSON();posts.push({path:url.pathname,body});
      return route.fulfill({status:201,json:{style_id:body.style_id,display_name:body.display_name,version:1,guidance:body.guidance,style_hash:'quiet-hash',evidence:body.evidence}});
    }
    if(url.pathname==='/api/styles/sources'&&request.method()==='POST'){
      expect(request.headers()['x-file-name']).toBe(encodeURIComponent('look-guide.txt'));
      expect(request.postDataBuffer().toString()).toBe('Use quiet dialogue.');
      return route.fulfill({status:201,json:source});
    }
    if(url.pathname===`/api/styles/sources/${source.source_id}`)return route.fulfill({json:source});
    return route.fulfill({status:404,json:{error:{message:'Unexpected style API request'}}});
  });
  await page.route('**/api/media/**',route=>route.fulfill({json:{assets:[],total:0}}));
  await page.goto('/#/styles');
  await page.getByLabel('Style document file').setInputFiles({name:'look-guide.txt',mimeType:'text/plain',buffer:Buffer.from('Use quiet dialogue.')});
  await page.getByRole('button',{name:'Add document'}).click();
  await expect(page.getByText('Extracted 25 characters from look-guide.txt. Review the cited text below before using it to draft style rules.')).toBeVisible();
  await page.locator('.style-source-item summary').click();
  await expect(page.getByText('line:1-1')).toBeVisible();
  await expect(page.getByText('Use quiet dialogue.',{exact:true})).toBeVisible();
  await page.getByLabel('Use look-guide.txt for style proposal').check();
  await page.getByLabel('What should the model learn from these documents?').fill('Adapt camera and dialogue style only.');
  await page.getByRole('button',{name:'Draft rules with Codex'}).click();
  await expect(page.getByLabel('Directing guidance')).toHaveValue('Use quiet dialogue.');
  await expect(page.getByText('Use quiet dialogue.',{exact:true})).toHaveCount(3);
  await expect(page.getByText(/nothing has been published yet/)).toBeVisible();
  await page.getByLabel('Style ID').fill('quiet_film');
  await page.getByRole('button',{name:'Publish directing style'}).click();
  await expect(page.getByText(/published as directing-style version 1/)).toBeVisible();
  expect(posts.find(item=>item.path==='/api/styles/sources/analyze').body).toEqual({isolated_context_id:context,source_ids:[source.source_id],user_intent:'Adapt camera and dialogue style only.'});
  expect(posts.find(item=>item.path==='/api/styles/directing-styles').body.evidence).toEqual([{kind:'document',source_id:source.source_id,source_sha256:source.sha256,filename:source.filename,locator:'line:1-1',quote:'Use quiet dialogue.',intent:'Keep dialogue restrained.'}]);
});

test('selected style images can draft editable visual rules without publishing', async ({ page }) => {
  const context='setup-12345678-1234-1234-1234-123456789abc';
  const image={asset_id:'pa-1234567890abcdef',workspace_id:context,kind:'image',roles:['style_reference'],filename:'rainy-alley.png',media_type:'image/png',sha256:'b'.repeat(64),size_bytes:12,content_url:'/fixture/rainy-alley.png',created_at:'2026-10-10T00:00:00Z',metadata:{}};
  const audio={asset_id:'pa-2234567890abcdef',workspace_id:context,kind:'audio',roles:['style_reference'],filename:'low-strings.wav',media_type:'audio/wav',sha256:'c'.repeat(64),size_bytes:12,content_url:'/fixture/low-strings.wav',created_at:'2026-10-10T00:00:00Z',description:'Low strings swell beneath distant dialogue.',tags:['restrained tension'],metadata:{analyzer_run_id:'analysis-1',timestamp_start_seconds:12,timestamp_end_seconds:18}};
  const posts=[];
  await page.addInitScript(id=>localStorage.setItem('vibe-style-setup-context-v1',id),context);
  await page.route('**/api/styles/**',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(url.pathname==='/api/styles/catalog')return route.fulfill({json:{catalog_version:'test',production_types:[makeStyle('story_film','Story / film')],directing_styles:[{style_id:'cinematic',display_name:'Cinematic',version:1,guidance:'Coherent',style_hash:'hash'}]}});
    if(url.pathname==='/api/styles/selections')return route.fulfill({json:{selections:[]}});
    if(url.pathname==='/api/styles/sources')return route.fulfill({json:{sources:[]}});
    if(url.pathname==='/api/styles/media/analyze'){
      const body=request.postDataJSON();posts.push(body);
      return route.fulfill({json:{status:'proposal',persisted:false,published:false,provider:'test',display_name:'Rainy Noir',guidance:'Use low-key light and wet-surface reflections.',evidence:[{kind:'image',asset_id:image.asset_id,sha256:image.sha256,intent:'Use the reflection and narrow framing.'},{kind:'audio',asset_id:audio.asset_id,sha256:audio.sha256,intent:'Keep the score restrained.',quote:audio.description,locator:'12-18s',analyzer_run_id:'analysis-1'}]}});
    }
    return route.fulfill({status:404,json:{error:{message:'Unexpected style request'}}});
  });
  await page.route('**/api/media/**',async route=>{
    const url=new URL(route.request().url());
    if(url.pathname===`/api/media/${context}/assets`){const assets=url.searchParams.get('kind')==='image'?[image]:url.searchParams.get('kind')==='audio'?[audio]:[];return route.fulfill({json:{assets,total:assets.length}});}
    return route.fulfill({status:404,json:{error:{message:'Unexpected media request'}}});
  });
  await page.goto('/#/styles');
  await expect(page.getByText('Images and selected video frames use vision. Audio and video proposals use source-linked analyzer notes; Codex does not inspect the original audio or video here.')).toBeVisible();
  await page.getByLabel('Analyze rainy-alley.png as style').check();
  await page.getByLabel('Analyze low-strings.wav as style').check();
  await page.getByLabel('What should Codex learn from these references?').fill('Focus on lighting.');
  await page.getByRole('button',{name:'Draft style rules with Codex'}).click();
  await expect(page.getByLabel('Directing guidance')).toHaveValue('Use low-key light and wet-surface reflections.');
  await expect(page.getByLabel('What to use from rainy-alley.png')).toHaveValue('Use the reflection and narrow framing.');
  await expect(page.getByLabel('What to use from low-strings.wav')).toHaveValue('Keep the score restrained.');
  await expect(page.getByText(/nothing has been published yet/)).toBeVisible();
  expect(posts).toEqual([{isolated_context_id:context,asset_ids:[image.asset_id,audio.asset_id],user_intent:'Focus on lighting.'}]);
});
