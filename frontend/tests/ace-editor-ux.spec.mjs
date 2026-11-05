import {test,expect} from '@playwright/test';
import {mkdtempSync,mkdirSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const defaults={mode:'instrumental',tags:'warm',lyrics:'',duration:30,seed:42,steps:20,cfg:4,scheduler:'euler',adapter_id:'',max_steps:1000,learning_rate:.0001,save_every:100,rank:16};

test('ACE fresh Create, restored fine-tune and new session keep panels and settings consistent',async({page})=>{
 const training={id:'training',name:'Saved training',workspace_id:'tool-library',revision:2,settings:{...defaults,rank:32},intent:'finetune',summary:'',questions:[],messages:[],dataset:{count:1,songs:['song']},assets:[],adapters:[],job_id:null};
 const writes=[];
 await page.route('**/api/**',route=>{
  if(new URL(route.request().url()).pathname.startsWith('/api/projects/'))return route.fulfill({json:route.request().url().endsWith('/current')?{workspace_id:'tool-library',title:'Standalone tools',browser_state:{}}:{saved:true}});
  const path=new URL(route.request().url()).pathname;
  if(route.request().method()==='POST')writes.push(path);
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test'},models:[]}});
  if(path.endsWith('/assets/catalogue'))return route.fulfill({json:{assets:[],total:0,workspaces:[]}});
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
  if(path==='/api/ace/state')return route.fulfill({json:{projects:[training],defaults,adapters:[],runtime:{ready:false,training_ready:false,checks:{}}}});
  if(path==='/api/studio-tools/output-destination')return route.fulfill({json:{mode:'default',path:'/default/music'}});
  if(path.endsWith('/assets'))return route.fulfill({json:{assets:[],total:0}});
  return route.fulfill({status:404,json:{error:{message:'Unexpected mock endpoint'}}});
 });
 await page.goto('/#/media-prep?tool=music');
 const nav=page.getByRole('navigation',{name:'Music panels'});
 await expect(nav.getByRole('button',{name:'Create',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByRole('heading',{name:'Create music',exact:true})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Task',exact:true})).toHaveValue('generate');
 await page.locator('.editor-composer').getByRole('button',{name:'Browse media sources',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Browse media sources',exact:true})).toHaveCSS('position','fixed');
 await page.keyboard.press('Escape');
 await expect(page.getByRole('dialog',{name:'Browse media sources',exact:true})).toHaveCount(0);
 const before=await page.locator('.editor-composer').evaluate(el=>el.getBoundingClientRect().top+window.scrollY);
 await page.getByRole('button',{name:'Open session',exact:true}).click();
 const after=await page.locator('.editor-composer').evaluate(el=>el.getBoundingClientRect().top+window.scrollY);
 expect(Math.abs(after-before)).toBeLessThan(8);
 await expect(page.getByRole('dialog',{name:'Open session',exact:true})).toHaveCSS('position','fixed');
 await page.getByLabel('Music project').selectOption('training');
 await page.getByRole('button',{name:'Close Open session'}).click();
 await expect(nav.getByRole('button',{name:'Fine-tune',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByRole('heading',{name:'Create music',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Start fine-tuning',exact:true})).toBeVisible();
 await page.reload();
 await expect(nav.getByRole('button',{name:'Fine-tune',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'New session',exact:true}).click();
 await expect(nav.getByRole('button',{name:'Create',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByRole('heading',{name:'Create music',exact:true})).toBeVisible();
 await page.screenshot({path:'/tmp/vibe-ace-create.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Open session',exact:true}).click();
 const popup=await page.getByRole('dialog',{name:'Open session',exact:true}).boundingBox();
 expect(popup.x).toBeGreaterThanOrEqual(0);expect(popup.x+popup.width).toBeLessThanOrEqual(390);
 await page.keyboard.press('Escape');
 expect(training.settings.rank).toBe(32);
 expect(training.dataset.count).toBe(1);
 expect(writes.filter(path=>path.startsWith('/api/ace/'))).toEqual([]);
});

test('nested folder imports filter by kind, attach/drop/remove persist and deletion stays confirmed',async({page})=>{
 const root=mkdtempSync(join(tmpdir(),'vibe-editor-folder-'));
 mkdirSync(join(root,'nested','deeper'),{recursive:true});
 writeFileSync(join(root,'one.png'),'image');writeFileSync(join(root,'nested','deeper','two.png'),'image');writeFileSync(join(root,'nested','skip.wav'),'audio');writeFileSync(join(root,'skip.txt'),'text');
 let assets=[],uploads=[],deletes=0,project={id:'edit-folder',name:'Folder edit',workspace_id:'tool-library',revision:0,style_id:null,messages:[],revisions:[],selection:[],overrides:{},view:{tab:'media'}};
 await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:tool-library','edit-folder'));
 await page.route('**/api/**',route=>{
  if(new URL(route.request().url()).pathname.startsWith('/api/projects/'))return route.fulfill({json:route.request().url().endsWith('/current')?{workspace_id:'tool-library',title:'Standalone tools',browser_state:{}}:{saved:true}});
  const req=route.request(),url=new URL(req.url()),path=url.pathname;
  if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{checks:{}}}});
  if(path==='/api/editor/projects/edit-folder'){
   if(req.method()==='PUT'){const body=req.postDataJSON();project={...project,...body,revision:project.revision+1,view:{...project.view,...body.view}};}
   return route.fulfill({json:project});
  }
  if(path==='/api/media/tool-library/assets'){
   if(req.method()==='POST'){const name=url.searchParams.get('filename');uploads.push(name);const asset={asset_id:'asset-'+uploads.length,workspace_id:'tool-library',kind:'image',filename:name,content_url:'/mock/'+name,created_at:'2026-11-03',media:{},roles:[]};assets.push(asset);return route.fulfill({json:asset});}
   return route.fulfill({json:{assets:assets.filter(a=>a.kind===url.searchParams.get('kind')),total:assets.length}});
  }
  if(path.endsWith('/deletion')){const id=path.split('/').at(-2);if(req.method()==='POST'){deletes++;assets=assets.filter(a=>a.asset_id!==id);return route.fulfill({json:{deleted:true}});}return route.fulfill({json:{asset_id:id,path:'/managed/'+id,sha256:'a'.repeat(64),can_delete:!project.selection.some(r=>r.asset_id===id),references:project.selection.some(r=>r.asset_id===id)?['editor selection']:[]}});}
  if(path==='/api/studio-tools/output-folder')return route.fulfill({json:{path:'/chosen/editor',grant:'grant'}});
  if(path.endsWith('/assets/catalogue'))return route.fulfill({json:{assets:[],total:0,workspaces:[]}});
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
  return route.fulfill({status:404,json:{error:{message:'Unexpected mock endpoint'}}});
 });
 try{
  await page.goto('/#/editor');
  await page.getByRole('combobox',{name:'Kind',exact:true}).selectOption('image');
  await page.getByLabel('Choose asset folder',{exact:true}).setInputFiles(root);
  await expect.poll(()=>uploads.length).toBe(2);
  expect(uploads.sort()).toEqual(['one.png','two.png']);
  await expect(page.getByRole('button',{name:'Attach selected',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Select all shown (2)',exact:true}).click();
  await page.getByRole('button',{name:'Attach selected',exact:true}).click();
  await expect(page.getByLabel('Chat attachments')).toContainText('one.png');
  await expect.poll(()=>project.selection.length).toBe(2);
  await page.getByRole('button',{name:'Delete selected permanently'}).click();
  await expect(page.getByRole('alert').filter({hasText:'Files are still used'})).toBeVisible();
  expect(deletes).toBe(0);
  await page.getByRole('combobox',{name:'Asset view',exact:true}).selectOption('list');
  await page.getByRole('combobox',{name:'Sort assets',exact:true}).selectOption('name');
  await expect(page.locator('.editor-asset-list .editor-asset-card')).toHaveCount(2);
  await page.screenshot({path:'/tmp/vibe-editor-assets.png',fullPage:true});
  await page.getByLabel('Chat attachments').locator('.editor-attachment-chip').first().getByTitle('View attachment').focus();
  await expect(page.getByRole('button',{name:'Remove attachment 1',exact:true})).toHaveCSS('opacity','1');
  await page.getByLabel('Chat attachments').locator('.editor-attachment-chip').first().hover();
  await page.getByRole('button',{name:'Remove attachment 1',exact:true}).click();
  await expect.poll(()=>project.selection.length).toBe(1);
  await expect(page.locator('#edit-chat')).toBeEnabled();
  expect(deletes).toBe(0);
  await page.locator('.editor-composer').evaluate(el=>{const data=new DataTransfer();data.setData('application/x-vibe-editor-assets',JSON.stringify(['asset-1','asset-2']));el.dispatchEvent(new DragEvent('drop',{dataTransfer:data,bubbles:true,cancelable:true}));});
  await expect.poll(()=>project.selection.length).toBe(2);
  await page.locator('.editor-composer').evaluate(el=>{const data=new DataTransfer();data.setData('application/x-vibe-editor-assets',JSON.stringify(['asset-1']));el.dispatchEvent(new DragEvent('drop',{dataTransfer:data,bubbles:true,cancelable:true}));});
  await expect(page.locator('#edit-chat')).toBeEnabled();
  expect(project.selection.length).toBe(2);
  await page.reload();
  await expect(page.getByLabel('Chat attachments').locator('.editor-attachment-chip')).toHaveCount(2);
  for(let i=0;i<2;i++){await page.getByLabel('Chat attachments').locator('.editor-attachment-chip').first().hover();await page.getByRole('button',{name:'Remove attachment 1',exact:true}).click();await expect.poll(()=>project.selection.length).toBe(1-i);}
  await page.getByRole('combobox',{name:'Kind',exact:true}).selectOption('image');
  await page.getByRole('button',{name:'Select all shown (2)',exact:true}).click();
  page.once('dialog',dialog=>dialog.dismiss());
  await page.getByRole('button',{name:'Delete selected permanently'}).click();
  await expect(page.getByText('Deletion cancelled.',{exact:true})).toBeVisible();
  expect(deletes).toBe(0);
  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Delete selected permanently'}).click();
  await expect.poll(()=>deletes).toBe(2);
  await expect(page.getByRole('button',{name:'Preview one.png'})).toHaveCount(0);
  await page.getByRole('button',{name:'export',exact:true}).click();
  await page.getByRole('button',{name:'Choose folder',exact:true}).click();
  await expect(page.getByLabel('Output folder',{exact:true})).toHaveValue('/chosen/editor');
 }finally{rmSync(root,{recursive:true,force:true});}
});

test('first Editor import keeps successful files visible after a partial failure',async({page})=>{
 let project=null,uploads=0;
 const asset={asset_id:'first',workspace_id:'tool-library',kind:'video',filename:'first.mp4',created_at:'2026-11-03',content_url:'/mock/video',roles:[]};
 await page.route('**/api/**',route=>{
  if(new URL(route.request().url()).pathname.startsWith('/api/projects/'))return route.fulfill({json:route.request().url().endsWith('/current')?{workspace_id:'tool-library',title:'Standalone tools',browser_state:{}}:{saved:true}});
  const req=route.request(),path=new URL(req.url()).pathname;
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test'},models:[]}});
  if(path==='/api/editor/state')return route.fulfill({json:{projects:project?[project]:[],styles:[],runtime:{checks:{}}}});
  if(path==='/api/editor/projects'){project={id:'first-import',name:'Fresh edit',workspace_id:'tool-library',revision:0,messages:[],revisions:[],selection:[],overrides:{},view:{}};return route.fulfill({json:project});}
  if(path==='/api/editor/projects/first-import'){if(req.method()==='PUT')project={...project,...req.postDataJSON()};return route.fulfill({json:project});}
  if(path==='/api/media/tool-library/assets'){
   if(req.method()==='POST'){uploads++;return route.fulfill(uploads===1?{json:asset}:{status:503,json:{error:{message:'Second upload failed'}}});}
   return route.fulfill({json:{assets:uploads?[asset]:[],total:uploads?1:0}});
  }
  return route.fulfill({status:404,json:{error:{message:'Unexpected endpoint'}}});
 });
 await page.goto('/#/editor');
 await page.getByRole('button',{name:'Asset selection',exact:true}).click();
 await page.getByLabel('Choose asset files',{exact:true}).setInputFiles([{name:'first.mp4',mimeType:'video/mp4',buffer:Buffer.from('one')},{name:'second.mp4',mimeType:'video/mp4',buffer:Buffer.from('two')}]);
 await expect(page.getByRole('alert').filter({hasText:'Second upload failed'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Preview first.mp4',exact:true})).toBeVisible();
 expect(project.selection).toEqual([]);
 await page.getByRole('checkbox',{name:'Select first.mp4',exact:true}).check();
 await page.getByRole('button',{name:'Attach selected',exact:true}).click();
 await expect.poll(()=>project.selection.length).toBe(1);
});

test('Audio Studio recordings can be reused after removing the workspace selector',async({page})=>{
 const recording={asset_id:'recording',workspace_id:'story-other',kind:'audio',filename:'recording.wav',created_at:'2026-11-03',content_url:'/mock/recording',roles:[],media:{duration_seconds:4}};
 let project={id:'record-edit',name:'Recording edit',workspace_id:'tool-library',revision:0,messages:[],revisions:[],selection:[],overrides:{},view:{}};
 const reused=[];
 await page.addInitScript(recording=>{localStorage.setItem('vibe-editor-project:tool-library','record-edit');sessionStorage.setItem('vibe-editor-pending-audio',JSON.stringify({workspace_id:recording.workspace_id,asset:recording}));},recording);
 await page.route('**/api/**',route=>{
  if(new URL(route.request().url()).pathname.startsWith('/api/projects/'))return route.fulfill({json:route.request().url().endsWith('/current')?{workspace_id:'tool-library',title:'Standalone tools',browser_state:{}}:{saved:true}});
  const req=route.request(),path=new URL(req.url()).pathname;
  if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{checks:{}}}});
  if(path==='/api/editor/projects/record-edit'){if(req.method()==='PUT')project={...project,...req.postDataJSON()};return route.fulfill({json:project});}
  if(path==='/api/media/tool-library/assets/reuse'){reused.push(req.postDataJSON());return route.fulfill({json:{...recording,workspace_id:'tool-library',asset_id:'local-recording'}});}
  if(path.endsWith('/assets'))return route.fulfill({json:{assets:[],total:0}});
  return route.fulfill({status:404,json:{error:{message:'Unexpected endpoint'}}});
 });
 await page.goto('/#/editor');
 await page.getByRole('button',{name:'Preview for this project',exact:true}).click();
 await page.getByRole('button',{name:'Add to chat selection',exact:true}).click();
 await expect.poll(()=>project.selection.length).toBe(1);
 expect(project.selection[0]).toMatchObject({asset_id:'local-recording',start:0,end:4});
 expect(reused).toEqual([{source_workspace_id:'story-other',asset_id:'recording',role:'project_audio',mode:'reference'}]);
 expect(await page.evaluate(()=>sessionStorage.getItem('vibe-editor-pending-audio'))).toBeNull();
});
