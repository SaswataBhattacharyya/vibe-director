import {test,expect} from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

test('Editor keyframes preserve drafts, branch and propose shared tasks without generation',async({page})=>{
 const project={id:'edit',name:'Frame test',workspace_id:'w',revision:1,messages:[],revisions:[],selection:[],overrides:{},view:{},style_id:null};
 let take={take_id:'take-a',revision:2,keys:[{key_id:'key-a',review:'approved',image:{asset_id:'image-a',width:1248,height:832}}]},task=null,proposal,review,ran=0;
 await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:w','edit'));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname,method=route.request().method();
  if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{ready:true,checks:{}},kdenlive:{ready:false}}});
  if(path==='/api/editor/projects/edit')return route.fulfill({json:project});
  if(path==='/api/frame-pipeline/w')return route.fulfill({json:{workspace_id:'w',takes:[take],interpolation:{models:['rife','film']}}});
  if(path==='/api/frame-pipeline/w/takes/take-a'){
   review=route.request().postDataJSON();expect(review).toEqual({revision:2,operation:'branch',key_id:'key-a'});
   take={...take,take_id:'take-branch',revision:1,parent:{take_id:'take-a',key_id:'key-a'}};return route.fulfill({json:take});
  }
  if(path==='/api/frame-pipeline/w/propose'){
   proposal=route.request().postDataJSON();task={project_id:'w',task_id:'task-frame',status:'draft',current_revision:1,plan_hash:'frozen',plan:{tool_id:proposal.tool_id,settings:proposal.settings,assets:[{asset_id:'image-a',filename:'key.png',sha256:'hash'}],scope:'Generate a review candidate.'},invocation:null,events:[]};return route.fulfill({json:task});
  }
  if(path==='/api/agent/projects/w/tasks'&&method==='GET')return route.fulfill({json:{tasks:task?[task]:[]}});
  if(path==='/api/agent/projects/w/tasks/task-frame/approve'){
   expect(route.request().postDataJSON()).toEqual({revision:1,plan_hash:'frozen'});task={...task,status:'approved'};return route.fulfill({json:task});
  }
  if(path.includes('/tasks/')&&path.endsWith('/run'))ran++;
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
  return route.fulfill({status:404,json:{error:{message:'Unused test endpoint'}}});
 });
 await mockProject(page,'w');await page.goto('/#/editor');
 const panel=page.locator('.frame-pipeline');await panel.locator('summary').click();
 await expect(panel.getByText('Key 1 · approved')).toBeVisible();
 await panel.getByLabel('Next-frame edit').fill('Move the camera left; preserve the rider.');
 await panel.locator('summary').click();await panel.locator('summary').click();
 await expect(panel.getByLabel('Next-frame edit')).toHaveValue('Move the camera left; preserve the rider.');
 await panel.getByRole('button',{name:'Prepare Kontext candidate task'}).click();
 expect(proposal).toEqual({tool_id:'image.generate_next_keyframe',settings:{take_id:'take-a',revision:2,prompt:'Move the camera left; preserve the rider.',seed:1}});
 await panel.getByRole('button',{name:'Approve this plan',exact:true}).click();expect(ran).toBe(0);
 await panel.getByRole('button',{name:'Branch here'}).click();expect(review.operation).toBe('branch');
 await expect(panel.getByRole('combobox').first()).toHaveValue('take-branch');
});

test('approved endpoints create a separate FFLF draft without starting generation',async({page})=>{
 const before={workspaceId:'w',clipId:'original-clip',workflowId:'minimax_h3_t2v_local_v1',prompt:'Keep this draft.',duration:6,resolution:.98,aspectRatio:'16:9'};
 let endpointReads=0;const writes=[];
 await page.addInitScript(value=>localStorage.setItem('vibe-video-draft-v1',JSON.stringify(value)),before);
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname;
  if(request.method()!=='GET')writes.push(path);
  if(path==='/api/frame-pipeline/w/takes/take-a/endpoints'){
   endpointReads++;expect(url.searchParams.get('revision')).toBe('4');
   return route.fulfill({json:{first_frame:{asset_id:'first-approved'},last_frame:{asset_id:'last-approved'}}});
  }
  if(path==='/api/video/jobs')return route.fulfill({json:{jobs:[]}});
  if(path==='/api/media/w/assets'){
   const assets=url.searchParams.get('kind')==='image'?['first-approved','last-approved'].map(asset_id=>({asset_id,workspace_id:'w',kind:'image',roles:['image_candidate'],filename:`${asset_id}.png`,media_type:'image/png',sha256:'a'.repeat(64),size_bytes:100,content_url:'/mock.png',media:{width:1024,height:1024},metadata:{}})):[];
   return route.fulfill({json:{assets,total:assets.length}});
  }
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[],total:0}});
  if(path==='/api/studio-tools/output-destination')return route.fulfill({json:{mode:'default',path:'/test/output',available:true}});
  return route.fulfill({status:404,json:{error:{message:'Unused mocked endpoint'}}});
 });
 await mockProject(page,'w');await page.goto('/#/video?workspace_id=w&frame_take=take-a&frame_revision=4');
 const button=page.getByRole('button',{name:'Create draft from approved endpoints'});
 await expect(button).toBeVisible();expect(endpointReads).toBe(0);
 await button.click();
 await expect.poll(()=>page.evaluate(()=>JSON.parse(localStorage.getItem('vibe-video-draft-v1')).firstFrameAssetId)).toBe('first-approved');
 const stored=await page.evaluate(()=>({draft:JSON.parse(localStorage.getItem('vibe-video-draft-v1')),backup:JSON.parse(localStorage.getItem('vibe-video-draft-v1:before-frame-handoff:original-clip'))}));
 expect(stored.draft.lastFrameAssetId).toBe('last-approved');expect(stored.draft.clipId).not.toBe('original-clip');
 expect(stored.backup.prompt).toBe(before.prompt);expect(stored.draft.pendingRequest).toBeUndefined();
 await expect(page.locator('#first-frame')).toHaveValue('first-approved');
 await expect(page.locator('#last-frame')).toHaveValue('last-approved');
 expect(writes.filter(path=>path.includes('/jobs'))).toEqual([]);
});
