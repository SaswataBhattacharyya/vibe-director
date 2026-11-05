import {test,expect} from '@playwright/test';
const w='story-aaaaaaaaaaaa',r='screenplay-prompts';
const workflow='minimax_h3_t2v_local_v1';
const script={workspace_id:w,screenplay_revision_id:r,source_revision_id:'source-1',accepted:true,stale:false,screenplay:{title:'The key',scenes:[{scene_number:1,slugline:'INT. ROOM - DAY',summary:'Mira finds a key.',shots:[{shot_number:1,action:'Mira holds a key.',dialogue:'MIRA: Here it is.',direction:{camera:'Static',lighting:'Day',mood:'Quiet',sfx:'',music:''}}]}]}};
async function fixture(page,mode='assisted_manual'){
 const requests=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 let guidance={revision:0,lessons:[],assets:{},targets:{mira:{scope:'character',name:'Mira',detail:'An established character.'},room:{scope:'world',name:'Room',detail:'A small room.'}},items:[]};
 let drafts={'1.1':{workflow_id:workflow,prompt:'Mira holds a key.'}};
 await page.route('**/api/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname,body=req.method()==='GET'?null:req.postDataJSON();requests.push({path,method:req.method(),body});let json={};
  if(path==='/api/projects/current')json={workspace_id:w,title:'The key',folder:'/projects/key',browser_state:{}};
  else if(path==='/api/projects/memory')json={saved:true};
  else if(path==='/api/story/workspaces/'+w)json={workspace_id:w,current_revision_id:'source-1'};
  else if(path.endsWith('/screenplay'))json=script;
  else if(path.endsWith('/screenplay/revisions'))json={items:[script]};
  else if(path.endsWith('/production-setup'))json={setup:{mode,automate_steps:{video:false},video_workflow_id:workflow}};
  else if(path.endsWith('/assisted-video-clip-plan'))json={clips:[],references:{},setup_matches_current:true};
  else if(path.endsWith('/assets'))json={assets:[],total:0};
  else if(path.endsWith('/prompt-drafts')){if(body)drafts=body.drafts;json={drafts,setup_hash:'hash',setup_matches_current:true};}
  else if(path.endsWith('/prompt-director/'+r)){
   if(body)guidance={...guidance,revision:guidance.revision+1,lessons:body.lessons,assets:body.assets};json=guidance;
  }else if(path.includes('/prompt-director/'+r+'/')){
   const mode=path.split('/').pop();
   if(mode==='skill')json={filename:'SKILL.md',text:'---\nname: project-prompting\ndescription: Reusable prompting rules.\n---\n'+guidance.lessons.map(l=>l.rule).join('\n')};
   else{await new Promise(resolve=>setTimeout(resolve,300));json={key:body.idempotency_key,revision_id:r,instruction:body.instruction,mode,status:'complete',reply:mode==='chat'?'I understand. Keep camera direction concise.':'Review the proposal.',proposal:mode==='learn'?{lessons:[{scope:'video',rule:'Use one concrete camera move per shot.'}]}:mode==='propose'?{changes:[{key:'shot:1.1',before:body.prompts['shot:1.1'],value:'Mira holds a key. One slow push-in.'}]}:null};guidance.items.push(json);}
  }else if(path==='/api/director/settings')json={settings:{provider:'codex',model:'test',lessons:[]},models:[]};
  else return route.fulfill({status:404,json:{error:{message:'Unused fixture '+path}}});
  return route.fulfill({json});
 });
 return {requests,errors,getGuidance:()=>guidance,getDrafts:()=>drafts};
}
test('prompt chat discusses, animates, remembers history and applies only reviewed edits',async({page})=>{
 const fx=await fixture(page);await page.goto('/#/prompts');
 const input=page.getByRole('textbox',{name:'Prompt instruction',exact:true});await expect(input).toBeVisible();
 await input.fill('Can we simplify the camera?');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.getByText('Director is thinking…',{exact:true})).toBeVisible();
 expect(await page.locator('.screenplay-thinking .spin').evaluate(el=>getComputedStyle(el).animationName)).not.toBe('none');
 await expect(page.getByText('I understand. Keep camera direction concise.')).toBeVisible();
 expect(fx.requests.filter(q=>q.method==='PUT')).toHaveLength(0);
 await page.reload();await expect(page.getByText('Can we simplify the camera?',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Prepare agreed changes',exact:true}).click();
 await expect(page.getByRole('button',{name:'Apply selected prompt changes',exact:true})).toBeVisible();
 const shot=page.getByRole('textbox',{name:'Prompt for scene 1 shot 1',exact:true});await expect(shot).toHaveValue('Mira holds a key.');
 await page.getByRole('button',{name:'Apply selected prompt changes',exact:true}).click();await expect(shot).toHaveValue('Mira holds a key. One slow push-in.');
 expect(fx.getDrafts()['1.1'].prompt).toBe('Mira holds a key.');
 await page.getByRole('button',{name:'Save prompt drafts',exact:true}).click();await expect(page.getByRole('button',{name:'Prompt drafts saved',exact:true})).toBeVisible();
 expect(fx.getDrafts()['1.1'].prompt).toContain('push-in');expect(fx.errors).toEqual([]);
});
test('image briefs and explicitly approved learning rules persist and export, with responsive layout',async({page})=>{
 const fx=await fixture(page);await page.setViewportSize({width:1440,height:1000});await page.goto('/#/prompts');
 await expect(page.getByRole('textbox',{name:'Prompt instruction',exact:true})).toBeEnabled();
 await page.getByText('Characters (1)',{exact:true}).click();await page.getByRole('textbox',{name:'Mira',exact:true}).fill('Mira, established appearance, plain white background.');
 await page.getByRole('button',{name:'Save character & background briefs',exact:true}).click();await expect.poll(()=>fx.getGuidance().assets.mira).toContain('plain white');
 await page.getByRole('textbox',{name:'Mira',exact:true}).fill('Unsaved character adjustment.');
 await page.getByRole('textbox',{name:'Prompt instruction',exact:true}).fill('Remember: use one concrete camera move per shot.');
 await page.getByRole('button',{name:'Draft learning rules',exact:true}).click();await expect(page.getByText('Use one concrete camera move per shot.',{exact:true})).toBeVisible();
 expect(fx.getGuidance().lessons).toHaveLength(0);
 await page.getByRole('button',{name:'Save selected rules',exact:true}).click();await expect.poll(()=>fx.getGuidance().lessons.length).toBe(1);
 expect(fx.getGuidance().assets.mira).toBe('Mira, established appearance, plain white background.');
 await expect(page.getByRole('textbox',{name:'Mira',exact:true})).toHaveValue('Unsaved character adjustment.');
 await page.getByText('Saved prompting rules (1) · this project',{exact:true}).click();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export SKILL.md',exact:true}).click();expect((await download).suggestedFilename()).toBe('SKILL.md');
 await page.getByText('Worlds / backgrounds (1)',{exact:true}).click();await expect(page.getByRole('textbox',{name:'Room',exact:true})).toHaveValue(/Empty environment/);
 await page.getByRole('heading',{name:'Direct the prompts',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:'/tmp/vibe-prompt-director-desktop.png'});
 await page.getByRole('button',{name:'Hide navigation',exact:true}).click();
 await page.setViewportSize({width:390,height:844});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'/tmp/vibe-prompt-director-mobile.png'});
 await page.reload();await expect(page.getByText('Saved prompting rules (1) · this project',{exact:true})).toBeVisible();
 expect(fx.requests.filter(q=>q.path==='/api/images/jobs'||q.path.startsWith('/api/video/jobs'))).toHaveLength(0);expect(fx.errors).toEqual([]);
});

test('Continue opens character preparation without a clip plan, protecting unsaved prompts',async({page})=>{
 const fx=await fixture(page);await page.goto('/#/prompts');
 const next=page.getByRole('link',{name:'Continue to Characters & Voices',exact:true});
 await expect(next).toHaveAttribute('aria-disabled','false');
 const shot=page.getByRole('textbox',{name:'Prompt for scene 1 shot 1',exact:true});
 await shot.fill('Mira slowly lifts the key.');
 await expect(next).toHaveAttribute('aria-disabled','true');
 await expect(page.getByText('Save your prompt and reference edits before continuing.',{exact:true})).toBeVisible();
 await next.click({force:true});await expect(page).toHaveURL(/#\/prompts$/);
 await page.getByRole('button',{name:'Save prompt drafts',exact:true}).click();
 await expect(next).toHaveAttribute('aria-disabled','false');
 await next.click();await expect(page).toHaveURL(new RegExp(`#/characters\\?step=character_images&workspace_id=${w}$`));
 expect(fx.getDrafts()['1.1'].prompt).toBe('Mira slowly lifts the key.');
 expect(fx.requests.filter(q=>q.path.endsWith('/assisted-video-clip-plan')&&q.method==='POST')).toHaveLength(0);
});
test('Continue to Current Take still requires a current production clip plan',async({page})=>{
 await fixture(page,'fully_automated');await page.goto('/#/prompts');
 const next=page.getByRole('link',{name:'Continue to Current Take',exact:true});
 await expect(next).toHaveAttribute('aria-disabled','true');
 await expect(page.getByText('Prepare and review the per-clip prompts before continuing to Current Take.',{exact:true})).toBeVisible();
 await next.click({force:true});await expect(page).toHaveURL(/#\/prompts$/);
});
test('image drafts are cached per approved project guidance version',async({page})=>{
 let version=1,prepares=0,jobs=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname;let json={};
  if(path==='/api/projects/current')json={workspace_id:w,title:'The key',folder:'/projects/key',browser_state:{}};
  else if(path==='/api/projects/memory')json={saved:true};
  else if(path==='/api/studio-tools/output-destination')json={path:'/projects/key/output',available:true,mode:'project'};
  else if(path==='/api/story/workspaces')json={items:[{workspace_id:w,title:'The key'}],total:1};
  else if(path.endsWith('/screenplay/revisions'))json={items:[script],total:1};
  else if(path.endsWith('/screenplay/revisions/'+r))json={...script,graph_snapshot_id:'graph-1'};
  else if(path.endsWith('/graph'))json={snapshot_id:'graph-1',records:[{record_id:'mira',kind:'entity',type:'character',name:'Mira',detail:'Established appearance.'}]};
  else if(path.endsWith('/production-setup'))json={setup:{mode:'assisted_manual',automate_steps:{character_images:false,world_images:false,frame_images:false,video:false}}};
  else if(path.endsWith('/assisted-stage-skips'))json={skipped:[]};
  else if(path.endsWith('/prompt-director/'+r))json={revision:version,lessons:[],assets:{},targets:{},items:[]};
  else if(path==='/api/images/workflows')json={workflows:[{workflow_id:'z_image_turbo',label:'Z-Image',available:true,prompt_knowledge_ref:{knowledge_id:'k',guidance_version:1,workflow_sha256:'hash'},defaults:{width:1280,height:720,steps:8,cfg:1}}],gpu_admission:{available:true}};
  else if(path==='/api/video/runtime')json={safe_to_submit:true};
  else if(path==='/api/video/batches')json={batches:[]};
  else if(path==='/api/images/worker')json={available:true};
  else if(path.includes('/loras'))json={items:[],loras:[],checkpoints:[]};
  else if(path==='/api/images/prompts/prepare'){prepares++;json={workflow_id:'z_image_turbo',prompt:`Mira with approved guidance ${version}.`,knowledge_ref:{knowledge_id:'k',guidance_version:1,workflow_sha256:'hash'},sources:[]};}
  else if(path==='/api/images/jobs'){jobs++;return route.fulfill({status:500,json:{}});}
  else if(path.endsWith('/assets'))json={assets:[],total:0};
  else if(path==='/api/director/settings')json={settings:{provider:'codex',model:'test',lessons:[]},models:[]};
  return route.fulfill({json});
 });
 await page.goto(`/#/characters?step=character_images&workspace_id=${w}`);
 const prompt=page.getByRole('textbox',{name:'Image prompt',exact:true});
 await expect(prompt).toHaveValue('Mira with approved guidance 1.');
 await prompt.fill('Owner-reviewed image draft.');
 const before=prepares;await page.reload();await expect(prompt).toHaveValue('Owner-reviewed image draft.');expect(prepares).toBe(before);
 version=2;await page.reload();await expect(prompt).toHaveValue('Mira with approved guidance 2.');expect(prepares).toBeGreaterThan(before);
 expect(jobs).toBe(0);expect(errors).toEqual([]);
});
