import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';
const defaults={mode:'instrumental',tags:'',lyrics:'',duration:30,seed:42,steps:20,cfg:4,scheduler:'euler',adapter_id:'',max_steps:1000,learning_rate:.0001,save_every:100,rank:16,style_name:'',style_description:''};
for(const tool of ['editor','ace'])test(`${tool}: visible composer, stale session recovery and lazy save preserve the first message`,async({page})=>{
  let project=null,creates=0,text='',fail=true;
  await page.addInitScript(tool=>{if(!sessionStorage.getItem('seeded')){localStorage.setItem(tool==='editor'?'vibe-editor-project:tool-library':'vibe-ace-project:tool-library','removed-project');sessionStorage.setItem('seeded','1');}},tool);
  await page.route('**/api/**',async route=>{
    const p=new URL(route.request().url()).pathname,method=route.request().method();
    if(p==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
    if(p==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test'},models:[]}});
    if(p===`/api/${tool}/state`)return route.fulfill({json:{projects:project?[project]:[],styles:[],adapters:[],defaults,runtime:{ready:false,training_ready:false,checks:{}}}});
    if(p===`/api/${tool}/projects`&&method==='POST'){
      creates++;
      if(fail){fail=false;return route.fulfill({status:503,json:{error:{message:'Temporary save failure'}}});}
      project={id:'fresh',name:'Fresh session',workspace_id:'tool-library',settings:defaults,revision:0,intent:'generate',summary:'',questions:[],messages:[],assets:[],adapters:[],dataset:null,job_id:null,selection:[],revisions:[],overrides:{},view:{}};
      return route.fulfill({json:project});
    }
    if(p===`/api/${tool}/projects/fresh/command`){const body=route.request().postDataJSON();if(body.action==='chat'){text=body.text;project={...project,revision:project.revision+1,messages:[{id:'message-1',role:'user',text:body.text,content:body.text}]};}return route.fulfill({json:project});}
    if(p===`/api/${tool}/projects/fresh`)return route.fulfill({json:project});
    if(p.endsWith('/tasks'))return route.fulfill({json:{tasks:[]}});
    if(p.endsWith('/conversation')){if(method==='POST'){const body=route.request().postDataJSON();text=body.text;if(tool==='ace'){expect(body.surface).toBe('music');expect(body.target.project_id).toBe('fresh');project={...project,revision:project.revision+1,messages:[{id:'message-1',role:'user',content:text}]};}}return route.fulfill({json:{messages:text?[{request_id:'m',text,reply:'Ready',status:'answered'}]:[]}});}
    if(p.startsWith('/api/media/'))return route.fulfill({json:{assets:[],total:0}});
    return route.fulfill({status:404,json:{error:{message:'Unexpected mock route '+p}}});
  });
  await mockProject(page); await page.goto(tool==='editor'?'/#/editor':'/#/media-prep?tool=music');
  const composer=page.locator('#project-director-message');
  await expect(composer).toBeVisible();
  await expect.poll(()=>page.evaluate(tool=>localStorage.getItem(tool==='editor'?'vibe-editor-project:tool-library':'vibe-ace-project:tool-library'),tool)).toBe('');
  expect(creates).toBe(0);
  if(tool==='editor')await expect(page.getByRole('link',{name:'← Media Prep'})).toBeVisible();
  else await expect(page.getByRole('button',{name:'Run ACE-Step',exact:true})).toBeVisible();
  await composer.fill('Keep my first message');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await expect(page.getByText('Temporary save failure',{exact:true})).toBeVisible();
  await expect(composer).toHaveValue('Keep my first message');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await expect.poll(()=>text).toBe('Keep my first message');
  expect(creates).toBe(2);
  await expect(composer).toHaveValue('');
  await expect(page.getByRole('button',{name:/Create (music )?project/,exact:true})).toHaveCount(0);
  await page.reload();
  await expect(composer).toBeVisible();
  await expect(page.getByLabel('Director conversation history',{exact:true}).getByText('Keep my first message',{exact:true})).toBeVisible();
  expect(creates).toBe(2);
});
