import {test,expect} from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

test('native Studio opens, imports a proposal, closes and protects an unsaved Vibe draft',async({page})=>{
 const clip={asset_id:'v1',filename:'first.mp4',start:0,end:3,mime:'video/mp4'};
 const plan={width:320,height:180,fps:24,clips:[clip],audio:null};
 let project={id:'native',name:'Native edit',workspace_id:'w',style_id:null,revision:1,messages:[],revisions:[],selection:[clip],overrides:{},view:{tab:'visual'},brief:{summary:'Edit clips',questions:[]},pending:{kind:'plan',revision:1,value:plan}};
 const actions=[],opened=[];
 await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:w','native'));
 await page.route('**/native-frame',route=>route.fulfill({contentType:'text/html',body:'<p>Native test workspace</p>'}));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  let json;
  if(path==='/api/editor/state')json={projects:[project],styles:[],runtime:{ready:true,checks:{}}};
  else if(path==='/api/editor/projects/native')json=project;
  else if(path.endsWith('/native/studio')){opened.push(route.request().postDataJSON());json={token:'owned',url:new URL('/native-frame',route.request().url()).href,revision:project.revision};}
  else if(path.endsWith('/native/studio-action')){
   const body=route.request().postDataJSON();actions.push(body);
   if(body.action==='import')project={...project,revision:2,pending:{kind:'plan',revision:2,value:{...plan,clips:[{...clip,caption:'Native caption'}]}}};
   json=body.action==='import'?project:{closed:true};
  }
  else if(path==='/api/director/settings')json={settings:{provider:'codex',model:'test',lessons:[]},models:[]};
  else if(path==='/api/story/workspaces')json={items:[]};
  else return route.fulfill({status:404,json:{error:{message:'Unused mock endpoint'}}});
  return route.fulfill({json});
 });
 await mockProject(page,'w');await page.goto('/#/editor');
 const open=page.getByRole('button',{name:'Open HyperFrames Studio',exact:true});
 await open.click();await expect(page.getByTitle('HyperFrames Studio')).toBeVisible();
 expect(opened[0].revision).toBe(1);expect(opened[0].plan.clips[0].asset_id).toBe('v1');
 await page.getByRole('button',{name:'Import Studio edits as proposal',exact:true}).click();
 await expect(page.getByTitle('HyperFrames Studio')).toHaveCount(0);
 await expect(page.getByLabel('Visual caption',{exact:true})).toHaveValue('Native caption');
 expect(actions).toContainEqual({token:'owned',action:'import'});
 await open.click();await page.getByRole('button',{name:'Close HyperFrames Studio',exact:true}).click();
 await expect(page.getByTitle('HyperFrames Studio')).toHaveCount(0);
 expect(actions).toContainEqual({token:'owned',action:'close'});
 await page.getByLabel('Visual caption',{exact:true}).fill('Unsaved Vibe draft');await expect(open).toBeDisabled();
});
