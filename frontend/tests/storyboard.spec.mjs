import {test,expect} from '@playwright/test';
const w='story-aaaaaaaaaaaa',r='screenplay-test';
const shot=(n)=>({shot_number:n,presentation:'image',planned_duration_seconds:2,action:'Mira holds the key.',dialogue:'MIRA: Here it is.',direction:{camera:'Static',lighting:'Day',mood:'Quiet',sfx:'Keys',music:'Soft'},evidence:[]});
const script={workspace_id:w,screenplay_revision_id:r,source_revision_id:'source-1',accepted:true,created_at:'2026-11-04',screenplay:{title:'The key',scenes:[{scene_number:1,slugline:'INT. ROOM — DAY',summary:'Mira finds the key and opens the door.',shots:[shot(1),shot(2),shot(3),shot(4)]}]}};
const prep=()=>({presentation:'image',duration:2,route:'image',control:'manual',image_asset_id:'asset-image',media_asset_id:'',reference_ids:[],background_asset_id:'',first_frame_id:'',last_frame_id:'',prompt:'Mira holds the key.',video_prompt:'Mira holds the key.',batch_id:'',request_key:'',image_request:'',batch_target:'image',notes:''});
async function fixture(page,missing=false){
 let board={workspace_id:w,screenplay_revision_id:r,revision:1,body:{mode:'assisted_manual',deliverable:'storyboard',stages:Object.fromEntries(['worlds','shot_frames','storyboard','first_last'].map(k=>[k,{enabled:k==='shot_frames'||k==='storyboard',control:'manual'}])),scenes:{'1':{description:'Mira finds the key and opens the door.',dialogue:'MIRA: Here it is.'}},shots:Object.fromEntries([1,2,3,4].map(i=>['1.'+i,{...prep(),...(missing?{image_asset_id:'',control:'auto'}:{})}]))}};
 const requests=[];const errors=[];const conversation=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{const req=route.request(),path=new URL(req.url()).pathname;requests.push({path,method:req.method(),body:req.method()==='GET'?null:req.postDataJSON()});
  let json={};
  if(path==='/api/projects/current')json={workspace_id:w,title:'The key',folder:'/projects/key',browser_state:{}};
  else if(path==='/api/projects/memory')json={saved:true};
  else if(path==='/api/story/workspaces')json={items:[],total:0};
  else if(path==='/api/story/workspaces/'+w)json={workspace_id:w,title:'The key',current_revision_id:'source-1'};
  else if(path.endsWith('/screenplay')||path.endsWith('/screenplay/revisions/'+r))json=script;
  else if(path.endsWith('/screenplay/revisions'))json={items:[{...script,stale:false}],total:1};
  else if(path.endsWith('/screenplay-director/'+r+'/conversation'))json={items:conversation};
  else if(path.endsWith('/screenplay-director/'+r+'/chat')){await new Promise(resolve=>setTimeout(resolve,350));json={key:req.postDataJSON().idempotency_key,revision_id:r,instruction:req.postDataJSON().instruction,status:'complete',reply:'I understand. Keep narration for context and let Mira speak her lines.',proposal:null};conversation.push(json);}
  else if(path.endsWith('/screenplay-director/'+r+'/propose'))json={explanation:'Short still images.',changes:[{scene_number:1,shot_number:1,field:'planned_duration_seconds',value:2,before:6}]};
  else if(path.endsWith('/storyboard/'+r)){if(req.method()==='PUT'){board={...board,revision:board.revision+1,body:req.postDataJSON().body};}json=board;}
  else if(path.endsWith('/storyboard/'+r+'/editor'))json={id:'edit-storyboard'};
  else if(path.endsWith('/assets')&&new URL(req.url()).searchParams.get('kind')==='video')json={total:0,assets:[]};
  else if(path.endsWith('/assets'))json={total:1,assets:[{asset_id:'asset-image',filename:'key.svg',kind:'image',sha256:'a'.repeat(64),content_url:'data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#243347"/><circle cx="320" cy="170" r="55" fill="#f5cc67"/></svg>'),media:{width:640,height:360}}]};
  else if(path==='/api/images/jobs')json={batch_id:'batch-'+requests.length,jobs:[]};
  else if(path.startsWith('/api/images/batches/'))json={batch_id:path.split('/').pop(),jobs:[{job_id:'image-job',status:'completed',output_asset_id:'asset-image'}]};
  else if(path==='/api/images/workflows')json={workflows:[{workflow_id:'z_image_turbo',label:'Z Image',available:true,automation_available:true,defaults:{width:1280,height:720,steps:8,cfg:1}},{workflow_id:'qwen_image_edit_2511',label:'Qwen Edit',available:true,automation_available:true,defaults:{width:1024,height:1024,steps:4,cfg:1}}]};
  else if(path==='/api/director/settings')json={settings:{provider:'codex',model:'test',lessons:[]},models:[]};
  else if(path==='/api/editor/projects/edit-storyboard')json={id:'edit-storyboard',workspace_id:w,name:'Storyboard edit',revision:0,messages:[],revisions:[],selection:[{asset_id:'asset-image',start:0,end:2}],overrides:{},view:{tab:'media'}};
  else if(path==='/api/editor/state')json={projects:[{id:'edit-storyboard',workspace_id:w}],styles:[],runtime:{ready:false,checks:{},message:'Fixture'}};
  else return route.fulfill({status:404,json:{error:{message:'Unused fixture '+path}}});
  return route.fulfill({json});
 });return {requests,errors,getBoard:()=>board};
}
test('scene storyboard groups four ordered images right of editable text, retains project edits and fits narrow screens',async({page})=>{
 const fx=await fixture(page);await page.setViewportSize({width:1440,height:1000});await page.goto('/#/storyboard');
 await expect(page.getByRole('textbox',{name:'Scene description',exact:true})).toHaveValue('Mira finds the key and opens the door.');
 await expect(page.locator('.board-scene figure')).toHaveCount(4);
 const left=await page.getByRole('textbox',{name:'Scene description',exact:true}).boundingBox(),right=await page.locator('.board-images').boundingBox();expect(right.x).toBeGreaterThan(left.x+left.width);
 await page.getByRole('textbox',{name:'Scene description',exact:true}).fill('A new scene direction');
 await page.getByRole('button',{name:'Save storyboard',exact:true}).click();await expect(page.getByText(/Saved board revision 2/)).toBeVisible();
 await page.reload();await expect(page.getByRole('textbox',{name:'Scene description',exact:true})).toHaveValue('A new scene direction');
 await page.screenshot({path:'/tmp/vibe-storyboard-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await expect.poll(async()=>{const box=await page.locator('.studio-sidebar').boundingBox();return !box||box.x+box.width<=0;}).toBe(true);
 await page.screenshot({path:'/tmp/vibe-storyboard-mobile.png',fullPage:true,animations:'disabled'});expect(fx.errors).toEqual([]);
});
test('optional controls keep FFLF manual and classification editable with no automatic generation on visit',async({page})=>{
 const fx=await fixture(page);await page.goto('/#/shot-frames');await expect(page.getByRole('combobox',{name:'Presentation',exact:true})).toBeVisible();
 await page.getByText('Production choices & optional stages',{exact:true}).click();
 await page.getByLabel('First & last frames',{exact:true}).check();
 await expect(page.getByLabel('First & last frames control').locator('option[value=auto]')).toBeDisabled();
 await page.getByRole('combobox',{name:'Production mode',exact:true}).selectOption('fully_automated');
 await expect(page.getByLabel('First & last frames control')).toHaveValue('manual');
 await page.getByRole('combobox',{name:'Presentation',exact:true}).selectOption('video');await page.getByRole('combobox',{name:'Shot control',exact:true}).selectOption('manual');await page.getByRole('combobox',{name:'Production route',exact:true}).selectOption('fflf');
 await page.getByRole('button',{name:'Save storyboard',exact:true}).click();await expect(page.getByText(/Saved board revision 2/)).toBeVisible();
 expect(fx.getBoard().body.shots['1.1'].route).toBe('fflf');
 expect(fx.requests.filter(q=>q.path==='/api/images/jobs')).toEqual([]);
 await page.screenshot({path:'/tmp/vibe-shot-frames-desktop.png',fullPage:true});expect(fx.errors).toEqual([]);
});
test('unfinished local edits recover across navigation without silently saving',async({page})=>{
 const fx=await fixture(page);await page.goto('/#/storyboard');await page.getByRole('textbox',{name:'Dialogue',exact:true}).fill('MIRA: Keep this draft.');
 await page.reload();await expect(page.getByRole('textbox',{name:'Dialogue',exact:true})).toHaveValue('MIRA: Keep this draft.');
 await expect(page.getByText('Unsaved storyboard edits',{exact:true})).toBeVisible();expect(fx.getBoard().revision).toBe(1);
});
test('whole screenplay Director reveals reviewable changes and never applies on propose',async({page})=>{
 const fx=await fixture(page);await page.goto('/#/screenplay');await expect(page.getByRole('textbox',{name:'Screenplay instruction',exact:true})).toBeVisible();
 await page.getByRole('textbox',{name:'Screenplay instruction',exact:true}).fill('Make still images two seconds long');await page.getByRole('button',{name:'Prepare agreed changes',exact:true}).click();
 await expect(page.getByRole('button',{name:'Apply selected changes',exact:true})).toBeVisible();
 expect(fx.requests.filter(q=>q.path.endsWith('/apply'))).toEqual([]);expect(fx.errors).toEqual([]);
});

test('automatic frames save each request before submission and resume without rerendering completed shots',async({page})=>{
 const fx=await fixture(page,true);await page.goto('/#/shot-frames');await page.getByText('Production choices & optional stages',{exact:true}).click();
 await page.getByRole('combobox',{name:'Production mode',exact:true}).selectOption('fully_automated');
 await page.getByRole('button',{name:'Save storyboard',exact:true}).click();
 await page.getByRole('button',{name:'Start / continue frames',exact:true}).click();
 await expect(page.getByText('Selected automatic shot frames are prepared.',{exact:false})).toBeVisible();
 const calls=fx.requests.filter(q=>q.path==='/api/images/jobs');expect(calls).toHaveLength(4);
 for(const call of calls){const index=fx.requests.indexOf(call);expect(fx.requests.slice(0,index).some(q=>q.method==='PUT'&&Object.values(q.body?.body?.shots||{}).some(row=>row.request_key===call.body.idempotency_key))).toBe(true);}
 expect(Object.values(fx.getBoard().body.shots).every(s=>s.image_asset_id==='asset-image')).toBe(true);
 await page.getByRole('button',{name:'Start / continue frames',exact:true}).click();await expect(page.getByRole('button',{name:'Start / continue frames',exact:true})).toBeEnabled();
 expect(fx.requests.filter(q=>q.path==='/api/images/jobs')).toHaveLength(4);expect(fx.errors).toEqual([]);
});
test('Editor handoff selects the returned editing session',async({page})=>{
 const fx=await fixture(page);await page.goto('/#/storyboard');await page.getByRole('button',{name:'Assemble saved shots in Vibe Editor',exact:true}).click();
 await expect(page).toHaveURL(/#\/editor/);expect(await page.evaluate(w=>localStorage.getItem(`vibe-editor-project:${w}`),w)).toBe('edit-storyboard');
 expect(fx.requests.filter(q=>q.path.endsWith('/editor')&&q.method==='POST')).toHaveLength(1);
});

test('screenplay chat discusses over multiple turns, shows thinking and waits for an explicit change request',async({page})=>{
 const fx=await fixture(page);await page.goto('/#/screenplay');
 const input=page.getByRole('textbox',{name:'Screenplay instruction',exact:true});
 await input.fill('Can Mira speak instead of the narrator?');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'Director is thinking…'})).toBeVisible();
 await expect(page.locator('.screenplay-thinking .spin')).toHaveCSS('animation-name','styles-spin');
 await expect(page.getByRole('log',{name:'Screenplay conversation'})).toContainText('let Mira speak her lines.');
 expect(fx.requests.filter(q=>q.path.endsWith('/propose')||q.path.endsWith('/apply'))).toEqual([]);
 await input.fill('Keep some narration too.');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeDisabled();
 await expect(page.locator('.screenplay-chat-turn')).toHaveCount(2);
 await page.reload();await expect(page.locator('.screenplay-chat-turn')).toHaveCount(2);
 await page.getByRole('button',{name:'Prepare agreed changes',exact:true}).click();
 await expect(page.getByRole('button',{name:'Apply selected changes',exact:true})).toBeEnabled();
 expect(fx.requests.filter(q=>q.path.endsWith('/apply'))).toEqual([]);
 await page.screenshot({path:'/tmp/vibe-screenplay-conversation.png',fullPage:false});
 await page.setViewportSize({width:390,height:844});
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(fx.errors).toEqual([]);
});
