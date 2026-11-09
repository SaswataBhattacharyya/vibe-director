import {test,expect} from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

test('ordered compare uses exact shared approvals, evidence, preview and explicit final clearance',async({page})=>{
 const clips=[{asset_id:'a',filename:'first.mp4',mime:'video/mp4',start:0,end:3},{asset_id:'b',filename:'second.mp4',mime:'video/mp4',start:0,end:3}];
 let project={id:'join',name:'Join clips',workspace_id:'w',style_id:null,revision:1,messages:[],revisions:[],selection:clips,overrides:{},view:{},brief:{summary:'Join clips',questions:[]}};
 let task=null,proposal,join,finalCommands=0;
 const evidence={task_id:'task-join',comparison:{status:'match',score:.99,reason:'Moving sequence matches.',overlap_seconds:1,timing_uncertainty_seconds:1/30,limitations:'Review original playback.',evidence:[{a_seconds:2,b_seconds:0}],suggested_ranges:[{start:0,end:3},{start:1,end:3}]}};
 await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:w','join'));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname,method=route.request().method();
  if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{ready:true,checks:{}},kdenlive:{ready:true,message:'CPU MCP ready'}}});
  if(path==='/api/agent/projects/w/tasks'&&method==='GET')return route.fulfill({json:{tasks:task?[task]:[]}});
  if(path==='/api/agent/projects/w/tasks'&&method==='POST'){
   proposal=route.request().postDataJSON();task={project_id:'w',task_id:'task-join',status:'draft',current_revision:1,plan_hash:'frozen-hash',plan:{...proposal,scope:'Compare without rendering.',assets:clips.map(c=>({asset_id:c.asset_id,filename:c.filename,sha256:'hash'}))},invocation:null,events:[]};return route.fulfill({json:task});
  }
  if(path==='/api/agent/projects/w/tasks/task-join/approve'){
   expect(route.request().postDataJSON()).toEqual({revision:1,plan_hash:'frozen-hash'});task={...task,status:'approved'};return route.fulfill({json:task});
  }
  if(path==='/api/agent/projects/w/tasks/task-join/run'){task={...task,status:'completed',invocation:{invocation_id:'inv',job_id:'cpu-job',state:'completed'}};return route.fulfill({json:task});}
  if(path==='/api/agent/projects/w/tasks/task-join')return route.fulfill({json:task});
  if(path==='/api/editor/projects/join/overlap')return route.fulfill({json:{revision:project.revision,sources:[evidence]}});
  if(path==='/api/editor/projects/join/join'){
   join=route.request().postDataJSON();project={...project,revision:2,join_preview:{revision:2,asset:{asset_id:'preview',content_url:'/preview.mp4'}},pending:{kind:'plan',revision:2,value:{summary:'Kdenlive reviewed join',backend:'kdenlive',tools:['Kdenlive MCP','MLT'],clips:[clips[0],{...clips[1],start:1}],width:1920,height:1080,fps:30,audio:null}}};return route.fulfill({json:project});
  }
  if(path==='/api/editor/projects/join/command'){finalCommands++;return route.fulfill({json:project});}
  if(path==='/api/editor/projects/join')return route.fulfill({json:project});
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
  return route.fulfill({status:404,json:{error:{message:'Unused fixture endpoint'}}});
 });
 await mockProject(page,'w');await page.goto('/#/editor');
 await page.getByText('Compare and stitch two clips · Kdenlive',{exact:true}).click();
 await page.getByRole('button',{name:'Compare clip boundaries',exact:true}).click();
 expect(proposal.asset_ids).toEqual(['a','b']);expect(proposal.tool_id).toBe('video.compare_clip_overlap');
 const review=page.locator('.clip-join-review');
 await review.getByRole('button',{name:'Approve this plan',exact:true}).click();
 await review.getByRole('button',{name:'Run approved task',exact:true}).click();
 await expect(page.getByLabel('Clip overlap evidence')).toBeVisible();
 await expect(page.getByLabel('Overlap source A')).toBeVisible();
 await page.getByRole('button',{name:'Inspect A 2.000s / B 0.000s',exact:true}).click();
 await page.getByRole('button',{name:'Prepare Kdenlive join preview',exact:true}).click();
 expect(join).toEqual({revision:1,task_id:'task-join'});
 await expect(page.getByLabel('Kdenlive join preview')).toBeVisible();
 await expect(page.getByRole('button',{name:'Approve this revision',exact:true})).toBeEnabled();
 expect(finalCommands).toBe(0);
 await page.getByRole('button',{name:'Approve this revision',exact:true}).click();
 expect(finalCommands).toBe(1);
});
