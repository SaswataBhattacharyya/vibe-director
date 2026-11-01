import {test,expect} from '@playwright/test';
test('compatible sources are explicitly added without starting a job',async({page})=>{
  const reused=[];
  const catalogueRequests=[];
  const writes=[];
  const source={asset_id:'pa-source',workspace_id:'other',kind:'video',roles:['project_video'],filename:'Reference clip.mp4',content_url:'/fixture',created_at:'2026-10-27',sha256:'a'.repeat(64)};
  await page.route('**/api/**',route=>{
    const request=route.request(),url=new URL(request.url());
    if(request.method()!=='GET'&&!url.pathname.startsWith('/api/studio-tools/output-'))writes.push(url.pathname);
    let value;
    if(url.pathname==='/api/story/workspaces')value={items:[{workspace_id:'ws-test',title:'Test'},{workspace_id:'other',title:'Other project'}],total:2};
    else if(url.pathname==='/api/audio/utilities/capabilities')value={operations:[{id:'extract_mp3',status:'available'}]};
    else if(url.pathname.endsWith('/utilities/jobs'))value=[];
    else if(url.pathname.endsWith('/assets/catalogue')){
      expect(url.searchParams.get('kinds').split(',').sort()).toEqual(['audio','video']);
      catalogueRequests.push(Object.fromEntries(url.searchParams));
      value={assets:[source],total:1,offset:0,limit:24,workspaces:['ws-test','other'],workspace_names:{'ws-test':'Test',other:'Other project'},folders:[]};
    }else if(url.pathname.endsWith('/assets/catalogue-refresh'))value={added:0,errors:[]};
    else if(url.pathname.endsWith('/assets/reuse')){
      reused.push(request.postDataJSON());value={...source,workspace_id:'ws-test',asset_id:'pa-copy'};
    }else if(url.pathname==='/api/media/ws-test/assets')value={assets:[],total:0};
    return route.fulfill(value===undefined?{status:503,json:{error:{message:'Not used in this test'}}}:{json:value});
  });
  await page.goto('/#/media-prep?tool=utilities');
  await page.getByLabel('Audio utility workspace').selectOption('ws-test');
  const picker=page.locator('.media-source-picker');
  await picker.locator('summary').click();
  await expect(picker.getByText('Reference clip.mp4',{exact:true})).toBeVisible();
  await picker.getByRole('button',{name:'Source: All media'}).click();
  await picker.getByRole('button',{name:'Workspaces →',exact:true}).click();
  await picker.getByRole('button',{name:'Other project →',exact:true}).click();
  await expect.poll(()=>catalogueRequests.at(-1)?.owner).toBe('other');
  await picker.getByRole('button',{name:'Source: Workspaces'}).click();
  await picker.getByRole('button',{name:'YouTube downloads',exact:true}).click();
  await expect.poll(()=>catalogueRequests.at(-1)?.source).toBe('downloaded');
  expect(catalogueRequests.at(-1)?.owner).toBe('');
  await expect(picker.getByRole('checkbox',{name:'Reference clip.mp4',exact:true})).toBeVisible();
  await picker.getByRole('checkbox',{name:'Reference clip.mp4',exact:true}).check();
  await picker.getByRole('button',{name:/Deselect all/}).click();
  await expect(picker.getByRole('checkbox',{name:'Reference clip.mp4',exact:true})).not.toBeChecked();
  await picker.getByRole('button',{name:/Select all/}).click();
  expect(reused).toHaveLength(0);
  await picker.getByRole('button',{name:'Add selected (1)',exact:true}).click();
  await expect(picker.getByText('1 added. Choose them in the tool below.')).toBeVisible();
  expect(reused).toHaveLength(1);
  expect(reused[0]).toMatchObject({source_workspace_id:'other',asset_id:'pa-source'});
  expect(writes).toEqual(['/api/media/ws-test/assets/catalogue-refresh','/api/media/ws-test/assets/reuse']);
  await expect(page.getByRole('checkbox',{name:/Select Reference clip/})).not.toBeChecked();
});

test('an unnamed destination requires a durable name without losing selected media',async({page})=>{
  const writes=[];
  let named=false;
  const asset={asset_id:'pa-source',workspace_id:'other',kind:'audio',roles:['project_audio'],filename:'song.wav',content_url:'/fixture',created_at:'2026-10-27',sha256:'a'.repeat(64)};
  await page.addInitScript(()=>{localStorage.setItem('vibe-media-active-workspace-v1','media-unnamed');});
  await page.route('**/api/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname;
    let value;
    if(path==='/api/story/workspaces')value={items:[],total:0};
    else if(path==='/api/audio/utilities/capabilities')value={operations:[{id:'extract_mp3',status:'available'}]};
    else if(path.endsWith('/utilities/jobs'))value=[];
    else if(path.endsWith('/assets/catalogue'))value={assets:[asset],total:1,offset:0,limit:24,workspaces:['other'],workspace_names:{other:'Songs'}};
    else if(path.endsWith('/assets/workspace-name')){expect(request.postDataJSON()).toEqual({name:'My film'});named=true;value={workspace_id:'media-unnamed',name:'My film'};}
    else if(path.endsWith('/assets/reuse')){expect(named).toBe(true);writes.push(path);value={...asset,workspace_id:'media-unnamed'};}
    else if(path.endsWith('/assets'))value={assets:[],total:0};
    return route.fulfill(value===undefined?{status:503,json:{error:{message:'Not used'}}}:{json:value});
  });
  await page.goto('/#/media-prep?tool=utilities');
  const picker=page.locator('.media-source-picker');
  await picker.locator('summary').click();
  await picker.getByRole('checkbox',{name:'song.wav',exact:true}).check();
  await picker.getByRole('button',{name:'Add selected (1)',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Name workspace'});
  await expect(dialog).toBeVisible();
  expect(writes).toEqual([]);
  await dialog.getByLabel('Workspace name').fill('My film');
  await dialog.getByRole('button',{name:'Save name',exact:true}).click();
  await expect(dialog).toHaveCount(0);
  await expect(picker.getByRole('checkbox',{name:'song.wav',exact:true})).toBeChecked();
  await picker.getByRole('button',{name:'Add selected (1)',exact:true}).click();
  await expect.poll(()=>writes.length).toBe(1);
});

test('R2V warns before overfilling a reference group and keeps the draft',async({page})=>{
  const workspaceId='limit-check';
  const assets=Array.from({length:10},(_,i)=>({asset_id:'img-'+i,workspace_id:workspaceId,kind:'image',roles:['character_master'],filename:'Character '+i+'.png',content_url:'/fixture.png',sha256:'a'.repeat(64),created_at:'2026-10-27'}));
  await page.addInitScript(({workspaceId,assets})=>localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId,clipId:'clip-check',workflowId:'minimax_h3_r2v_dynamic_v1',prompt:'Keep this prompt',duration:6,resolution:0.98,r2vImages:assets.slice(0,9).map(a=>({assetId:a.asset_id,role:'character',intent:'Keep identity'}))})),{workspaceId,assets});
  const submissions=[];
  await page.route('**/api/**',route=>{
    const req=route.request(),url=new URL(req.url());
    if(req.method()==='POST'&&!url.pathname.startsWith('/api/studio-tools/output-'))submissions.push(url.pathname);
    if(url.pathname===`/api/media/${workspaceId}/assets`)return route.fulfill({json:{assets:url.searchParams.get('kind')==='image'?assets:[],total:url.searchParams.get('kind')==='image'?10:0}});
    if(url.pathname.endsWith('/seo-styles'))return route.fulfill({json:{styles:[]}});
    return route.fulfill({status:404,json:{error:{message:'Not used'}}});
  });
  await page.goto('/#/video');
  await page.getByRole('button',{name:'Reference to video',exact:false}).first().click();
  const card=page.locator('.r2v-asset-card').filter({hasText:'Character 9.png'});
  await card.getByRole('button').click();
  let warning='';
  page.once('dialog',async dialog=>{warning=dialog.message();await dialog.dismiss();});
  await page.getByRole('button',{name:'Add selected character image',exact:true}).click();
  expect(warning).toContain('at most 9');
  await expect(card.getByRole('button')).toHaveAttribute('aria-pressed','true');
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-draft-v1')).r2vImages.length)).toBe(9);
  expect(submissions).toEqual([]);
});


test('R2V uses its carousel source dropdown for global downloads and copies only on Add',async({page})=>{
  const writes=[],requests=[];
  const asset={asset_id:'remote-video',workspace_id:'downloads',kind:'video',roles:['project_video'],origin:'imported',filename:'Downloaded reference.mp4',content_url:'/fixture.mp4',created_at:'2026-10-27',sha256:'a'.repeat(64)};
  await page.addInitScript(()=>localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId:'target',clipId:'clip',workflowId:'minimax_h3_r2v_dynamic_v1',prompt:'Keep the shot',duration:6,resolution:0.98})));
  await page.route('**/api/**',route=>{
    const req=route.request(),url=new URL(req.url());
    if(req.method()==='POST'&&!url.pathname.startsWith('/api/studio-tools/output-'))writes.push({path:url.pathname,body:req.postDataJSON()});
    if(url.pathname.endsWith('/assets/catalogue')){
      requests.push(Object.fromEntries(url.searchParams));
      return route.fulfill({json:{assets:url.searchParams.get('source')==='downloaded'?[asset]:[],total:1,workspaces:['downloads','target'],workspace_names:{downloads:'Downloads',target:'Film'}}});
    }
    if(url.pathname.endsWith('/assets/reuse'))return route.fulfill({json:{...asset,workspace_id:'target',asset_id:'local-video'}});
    if(url.pathname.endsWith('/assets'))return route.fulfill({json:{assets:[],total:0}});
    if(url.pathname.endsWith('/seo-styles'))return route.fulfill({json:{styles:[]}});
    return route.fulfill({status:404,json:{error:{message:'Not used'}}});
  });
  await page.goto('/#/video');
  await page.getByRole('button',{name:'Reference to video',exact:false}).first().click();
  await expect(page.locator('.media-source-picker')).toHaveCount(0);
  await page.getByLabel('Videos reference source').selectOption('global:downloaded');
  const card=page.locator('.r2v-asset-card').filter({hasText:'Downloaded reference.mp4'});
  await expect(card).toBeVisible();
  expect(requests.at(-1)).toMatchObject({source:'downloaded',owner:'',kinds:'video'});
  expect(writes).toHaveLength(0);
  await card.getByRole('button').click();
  await page.getByRole('button',{name:'Add selected video clip',exact:true}).click();
  await expect(page.getByLabel('Video references for this clip').getByText('Downloaded reference.mp4')).toBeVisible();
  expect(writes).toEqual([{path:'/api/media/target/assets/reuse',body:{source_workspace_id:'downloads',asset_id:'remote-video',mode:'reference'}}]);
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-draft-v1')).r2vVideos[0].assetId)).toBe('local-video');
});
