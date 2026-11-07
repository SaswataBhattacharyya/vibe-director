import {test,expect} from '@playwright/test';
const A='story-aaaaaaaaaaaa',B='story-bbbbbbbbbbbb';
async function fixture(page){
 let current='tool-library';const memories={},saves=[];let block=false;
 const project=id=>({workspace_id:id,title:id===A?'Project A':id===B?'Project B':'Standalone tools',projects_folder:'/projects',...(id==='tool-library'?{}:{folder:'/projects/'+(id===A?'A':'B')}),browser_state:memories[id]||{}});
 await page.route('**/api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname,body=req.method()==='POST'?req.postDataJSON():{};
  if(path==='/api/projects/current')return route.fulfill({json:project(current)});
  if(path==='/api/projects/memory'){memories[body.workspace_id]=body.browser_state;return route.fulfill({json:{saved:true}});}
  if(path==='/api/projects/save'){if(block)return route.fulfill({status:422,json:{error:{message:'This project has an active job. Wait or cancel it before saving or changing projects.'}}});saves.push(body);return route.fulfill({json:project(current)});}
  if(path==='/api/projects/new'||path==='/api/projects/open'||path==='/api/projects/select'){
   if(block)return route.fulfill({status:422,json:{error:{message:'This project has an active job. Wait or cancel it before saving or changing projects.'}}});
   current=body.workspace_id==='tool-library'&&path.endsWith('select')?'tool-library':(path.endsWith('new')?body.title==='Project B':body.folder==='/projects/B')?B:A;
   return route.fulfill({json:project(current)});
  }
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
  if(path==='/api/images/workflows')return route.fulfill({json:{workflows:[{workflow_id:'z_image_turbo',available:true,defaults:{width:1280,height:720,steps:8,cfg:1},label:'Z Image',version:'1'}]}});
  if(path==='/api/studio-tools/output-destination')return route.fulfill({json:{mode:'folder',path:'/projects/'+(current===B?'B':'A')+'/outputs/images',available:true}});
  if(path.endsWith('/assets'))return route.fulfill({json:{assets:[]}});
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
  if(path==='/api/studio-tools/loras')return route.fulfill({json:{loras:[]}});
  return route.fulfill({status:404,json:{error:{message:'Unused fixture '+path}}});
 });
 return {memories,saves,setBlock:value=>{block=value;}};
}
async function open(page,folder,name){
 await page.getByRole('button',{name:name?'New project':'Load project',exact:true}).click();
 if(name){
  await page.getByLabel('New project name',{exact:true}).fill(name);
  await page.getByRole('button',{name:'Create project',exact:true}).click();
 }else{
  await page.getByLabel('Project folder path',{exact:true}).fill(folder);
  await page.getByRole('button',{name:'Open project',exact:true}).click();
 }
 await page.keyboard.press('Escape');
}
test('New project uses the default parent and installs the returned child folder',async({page})=>{
 await fixture(page);let request,saved;
 const created={workspace_id:A,title:'Lion and Mouse',folder:'/projects/Lion and Mouse',projects_folder:'/projects',browser_state:{}};
 await page.route('**/api/projects/new',route=>{request=route.request().postDataJSON();return route.fulfill({json:created});});
 await page.route('**/api/projects/save',route=>{saved=route.request().postDataJSON();return route.fulfill({json:created});});
 await page.goto('/#/text-to-image');
 await page.getByRole('button',{name:'New project',exact:true}).click();
 await expect(page.getByLabel('New project parent folder',{exact:true})).toHaveValue('/projects');
 await page.getByLabel('New project name',{exact:true}).fill('Lion and Mouse');
 await page.screenshot({path:'/tmp/vibe-new-project-folder.png'});
 // No manually entered destination or existing child directory is required.
 await page.getByRole('button',{name:'Create project',exact:true}).click();
 await expect(page.getByLabel('Project controls')).toContainText('Lion and Mouse');
 await expect(page.getByLabel('Project controls')).toContainText('/projects/Lion and Mouse');
 await expect(page.getByLabel('Project folder path',{exact:true})).toHaveCount(0);
 await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Load project',exact:true}).click();
 await expect(page.getByLabel('New project name',{exact:true})).toHaveCount(0);
 await expect(page.getByLabel('Project folder path',{exact:true})).toHaveValue('/projects/Lion and Mouse');
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await expect(page.getByRole('button',{name:'Open project',exact:true})).toBeVisible();
 expect(request.parent_folder).toBe('/projects');expect(request.title).toBe('Lion and Mouse');
 await page.keyboard.press('Escape');await page.getByRole('button',{name:'Save project',exact:true}).click();
 await expect.poll(()=>saved?.folder).toBe('/projects/Lion and Mouse');
});
test('separate folder pickers send the New save location and Load project folder',async({page})=>{
 await fixture(page);let chosen='/custom/projects',created,opened;
 await page.route('**/api/projects/choose-folder',route=>route.fulfill({json:{path:chosen}}));
 await page.route('**/api/projects/new',route=>{created=route.request().postDataJSON();return route.fulfill({json:{workspace_id:A,title:'New film',folder:'/custom/projects/New film',projects_folder:'/projects',browser_state:{}}});});
 await page.route('**/api/projects/open',route=>{opened=route.request().postDataJSON();return route.fulfill({json:{workspace_id:B,title:'Existing film',folder:chosen,projects_folder:'/projects',browser_state:{}}});});
 await page.goto('/#/text-to-image');
 await page.getByRole('button',{name:'New project',exact:true}).click();
 await page.getByLabel('New project name',{exact:true}).fill('New film');
 await page.getByRole('button',{name:'Choose parent folder',exact:true}).click();
 await expect(page.getByLabel('New project parent folder',{exact:true})).toHaveValue(chosen);
 await page.getByRole('button',{name:'Create project',exact:true}).click();
 await expect.poll(()=>created?.parent_folder).toBe('/custom/projects');
 await expect(page.getByLabel('Project controls')).toContainText('/custom/projects/New film');
 await page.keyboard.press('Escape');
 chosen='/existing/film';
 await page.getByRole('button',{name:'Load project',exact:true}).click();
 await page.getByRole('dialog',{name:'Load project',exact:true}).getByRole('button',{name:'Choose folder',exact:true}).click();
 await expect(page.getByLabel('Project folder path',{exact:true})).toHaveValue(chosen);
 await page.screenshot({path:'/tmp/vibe-load-project-folder.png'});
 await page.getByRole('button',{name:'Open project',exact:true}).click();
 await expect.poll(()=>opened?.folder).toBe('/existing/film');
 await expect(page.getByLabel('Project controls')).toContainText('Existing film');
});
test('one folder restores isolated image settings and chat A → B → A, including cleared browser storage',async({page})=>{
 const state=await fixture(page);await page.goto('/#/text-to-image');
 await expect(page.getByLabel('Image prompt',{exact:true})).toBeVisible();
 await open(page,'/projects/A','Project A');await expect(page.getByLabel('Project controls')).toContainText('Project A');
 await page.getByLabel('Image prompt',{exact:true}).fill('A distinct project prompt');
 await page.getByLabel('Message the project Director',{exact:true}).fill('Remember A camera style');
 await page.getByLabel('Width',{exact:true}).fill('1024');
 await open(page,'/projects/B','Project B');await expect(page.getByLabel('Project controls')).toContainText('Project B');
 await expect(page.getByLabel('Image prompt',{exact:true})).toHaveValue('');
 await expect(page.getByLabel('Message the project Director',{exact:true})).toHaveValue('');
 await page.getByLabel('Image prompt',{exact:true}).fill('Only B');
 await open(page,'/projects/A');await expect(page.getByLabel('Image prompt',{exact:true})).toHaveValue('A distinct project prompt');
 await expect(page.getByLabel('Message the project Director',{exact:true})).toHaveValue('Remember A camera style');
 await expect(page.getByLabel('Width',{exact:true})).toHaveValue('1024');
 await page.getByRole('button',{name:'Save project',exact:true}).click();
 await expect.poll(()=>state.saves.length).toBeGreaterThan(2);
 await page.evaluate(()=>{localStorage.clear();sessionStorage.clear();});await page.reload();
 await expect(page.getByLabel('Image prompt',{exact:true})).toHaveValue('A distinct project prompt');
 await expect(page.getByLabel('Width',{exact:true})).toHaveValue('1024');
 expect(JSON.stringify(state.memories[B])).not.toContain('A distinct project prompt');
 await page.screenshot({path:'/tmp/vibe-project-controller.png',fullPage:true});
});
test('blocked project switch retains the active project and unsaved form',async({page})=>{
 const state=await fixture(page);await page.goto('/#/text-to-image');await open(page,'/projects/A','Project A');await expect(page.getByLabel('Project controls')).toContainText('Project A');
 await page.getByLabel('Image prompt',{exact:true}).fill('Keep this draft');state.setBlock(true);
 await open(page,'/projects/B','Project B');
 await expect(page.getByRole('alert').filter({hasText:'active job'})).toBeVisible();
 await expect(page.getByLabel('Project controls')).toContainText('Project A');
 await expect(page.getByLabel('Image prompt',{exact:true})).toHaveValue('Keep this draft');
});

test('story pages retain the active project when a link contains another project',async({page})=>{
 await fixture(page);await page.goto('/#/text-to-image');await open(page,'/projects/A','Project A');
 await expect(page.getByLabel('Project controls')).toContainText('Project A');
 const requests=[];
 await page.route('**/api/story/workspaces/**',async route=>{
  requests.push(new URL(route.request().url()).pathname);
  return route.fulfill({json:{workspace_id:A,title:'Project A',current_revision_id:null,items:[],total:0,offset:0}});
 });
 for(const route of ['screenplay','setup','prompts','characters']){
  requests.length=0;
  await page.evaluate(hash=>{location.hash=hash;},`#/${route}?workspace_id=${B}`);
  await expect.poll(()=>requests.length).toBeGreaterThan(0);
  expect(requests.every(path=>path.includes('/'+A))).toBe(true);
  await expect(page.getByLabel('Project controls')).toContainText('Project A');
 }
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Load project',exact:true}).click();
 await expect(page.getByLabel('Project folder path',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'/tmp/vibe-project-narrow.png',fullPage:true});
});

test('returned project memory wins over stale browser archive',async({page})=>{
 const state=await fixture(page);await page.goto('/#/text-to-image');
 await open(page,'/projects/A','Project A');await expect(page.getByLabel('Project controls')).toContainText('Project A');
 await page.getByLabel('Image prompt',{exact:true}).fill('Saved on the server');
 await open(page,'/projects/B','Project B');await expect(page.getByLabel('Project controls')).toContainText('Project B');
 await page.evaluate(id=>localStorage.setItem('vibe-project-browser:'+id,JSON.stringify({['vibe-project-settings:'+id+':TextToImagePage:prompt']:JSON.stringify('Stale browser copy')})),A);
 await open(page,'/projects/A');
 await expect(page.getByLabel('Image prompt',{exact:true})).toHaveValue('Saved on the server');
 expect(await page.evaluate(id=>localStorage.getItem('vibe-recovery:'+id+':browser'),A)).toContain('Stale browser copy');
 expect(JSON.stringify(state.memories[A])).toContain('Saved on the server');
});

test('opening a project restores its saved Editor session without browser selection; New stays new',async({page})=>{
 await fixture(page);
 const edit={id:'edit-a',name:'Project A edit',workspace_id:A,style_id:null,revision:3,messages:[{id:'m1',role:'assistant',content:'Saved project A editing instructions'}],revisions:[],selection:[],overrides:{},view:{tab:'preview'}};
 const foreign={...edit,id:'edit-b',name:'Project B edit',workspace_id:B};
 await page.route('**/api/editor/**',route=>route.fulfill({json:route.request().url().endsWith('/state')?{projects:[edit,foreign],styles:[],runtime:{checks:{}}}:edit}));
 await page.goto('/#/text-to-image');await open(page,'/projects/A','Project A');
 await expect(page.getByLabel('Project controls')).toContainText('Project A');
 await page.evaluate(()=>{location.hash='#/editor';});
 await expect(page.getByLabel('Session name')).toHaveValue('Project A edit');
 await page.getByText('Previous Editor session history',{exact:true}).click();
 await expect(page.locator('.editor-session-history')).toContainText('Saved project A editing instructions');
 await page.getByRole('button',{name:'Open session',exact:true}).click();
 await expect(page.getByLabel('Editing project')).toHaveValue('edit-a');
 await expect(page.getByLabel('Editing project').locator('option')).toHaveCount(2);
 await page.keyboard.press('Escape');await page.getByRole('button',{name:'New session',exact:true}).click();
 await expect(page.getByLabel('Session name')).toHaveValue('');
 await page.reload();await expect(page.getByLabel('Session name')).toHaveValue('');
});

test('project-owned ACE work restores without browser selection while explicit New remains blank',async({page})=>{
 await fixture(page);
 const defaults={mode:'instrumental',tags:'',lyrics:'',duration:30,seed:1,steps:20,cfg:4,scheduler:'euler',adapter_id:'',max_steps:1000,learning_rate:.0001,save_every:100,rank:16};
 const music={id:'music-a',name:'A saved music',workspace_id:A,revision:1,settings:{...defaults,tags:'Saved soundtrack'},intent:'generate',summary:'',questions:[],messages:[],dataset:null,assets:[],adapters:[],job_id:null};
 await page.route('**/api/ace/state',route=>route.fulfill({json:{projects:[{...music,id:'music-b',workspace_id:B},music],defaults,adapters:[],runtime:{ready:false,training_ready:false,checks:{}}}}));
 await page.goto('/#/text-to-image');await open(page,'/projects/A','Project A');
 await expect(page.getByLabel('Project controls')).toContainText('Project A');
 await page.evaluate(()=>{location.hash='#/media-prep?tool=music';});
 await page.getByRole('button',{name:'Open session',exact:true}).click();
 await expect(page.getByLabel('Music project')).toHaveValue('music-a');
 await expect(page.getByLabel('Music project').locator('option')).toHaveCount(2);
 await page.keyboard.press('Escape');await page.getByRole('button',{name:'New session',exact:true}).click();
 await page.reload();await page.getByRole('button',{name:'Open session',exact:true}).click();
 await expect(page.getByLabel('Music project')).toHaveValue('');
});
