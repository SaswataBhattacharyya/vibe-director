import {test,expect} from '@playwright/test';

const setup=mode=>({mode,automate_steps:{character_images:false,character_voice:false,world_images:false,frame_images:false,video:true},video_quality:'high',duration_policy:{kind:'fixed',seconds:6}});

async function openVideo(page,{mode='fully_automated',accepted=true,stale=false,runState='not_started',resumeAvailable=false,clips,statusReply,capability={available:true,dispatch:{available:true},runtime_guard:{safe_to_submit:true}}}={}){
  let starts=0,resumes=0;const controls=[];
  await page.addInitScript(()=>localStorage.setItem('vibe-story-selected-v1','story-full'));
  await page.route('**/api/story/**',route=>{
    const req=route.request(),url=new URL(req.url()),path=url.pathname;
    if(path==='/api/story/workspaces/story-full')return route.fulfill({json:{workspace_id:'story-full',title:'Full story',current_revision_id:'source-1'}});
    if(path.endsWith('/screenplay/revisions'))return route.fulfill({json:{items:[{screenplay_revision_id:'screen-1',source_revision_id:'source-1',accepted,stale}],total:1,offset:0,limit:50}});
    if(path.endsWith('/screenplay'))return route.fulfill({json:{workspace_id:'story-full',screenplay_revision_id:'screen-1',source_revision_id:'source-1',accepted,screenplay:{title:'Full story',scenes:[{scene_number:1,slugline:'INT. ROOM',summary:'A choice',shots:[{shot_number:1,action:'Mira opens the door.',dialogue:'',direction:{camera:'Wide',lighting:'Soft',mood:'Tense',sfx:'',music:''}}]}]}}});
    if(path.endsWith('/production-setup'))return route.fulfill({json:{workspace_id:'story-full',screenplay_revision_id:'screen-1',setup:setup(mode)}});
    if(path.endsWith('/prompt-drafts'))return route.fulfill({status:404,json:{error:{message:'No saved prompt drafts'}}});
    if(path.endsWith('/automated-first-clip')&&req.method()==='GET'&&statusReply)return statusReply(route);
    if(path.endsWith('/automated-first-clip')&&req.method()==='GET')return route.fulfill({json:{run_state:runState,resume_available:resumeAvailable,workspace_id:'story-full',screenplay_revision_id:'screen-1',job:starts?{job_id:'full-run-job',status:'queued'}:null,clips:typeof clips==='function'?clips():(clips??(runState==='paused'?[{scene_number:1,shot_number:1,clip_number:1,state:'needs_review',job:{job_id:'completed-first-clip',status:'needs_review'},attempts:[]}]:[]))}});
    if(path.endsWith('/automated-first-clip')&&req.method()==='POST'){starts++;runState='first_clip_queued';return route.fulfill({json:{run_state:'first_clip_queued',workspace_id:'story-full',screenplay_revision_id:'screen-1',job:{job_id:'full-run-job',status:'queued'},clips:[]}});}
    if(path.endsWith('/automated-run-control')&&req.method()==='POST'){
      const {action}=req.postDataJSON();controls.push(action);runState=action==='pause'?'owner_paused':action==='stop'?'stopped':'first_clip_queued';
      return route.fulfill({json:{run_state:runState,workspace_id:'story-full',screenplay_revision_id:'screen-1',clips:[]}});
    }
    if(path.endsWith('/automated-run-resume')&&req.method()==='POST'){resumes++;return route.fulfill({json:{run_state:'first_clip_queued',workspace_id:'story-full',screenplay_revision_id:'screen-1',resume_available:false,job:null,clips:[{scene_number:1,shot_number:1,clip_number:1,state:'needs_review',job:{job_id:'completed-first-clip',status:'needs_review'}}]}});}
    return route.fulfill({status:404,json:{error:{message:'Not mocked'}}});
  });
  await page.route('**/api/video/**',route=>route.fulfill({json:capability}));
  await page.goto('/#/video');
  return ()=>({starts,resumes,controls});
}

test('Full run panel requires current accepted screenplay and saved Fully automated setup',async({page})=>{
  await openVideo(page,{mode:'assisted_manual'});
  await expect(page.getByRole('region',{name:'Fully automated run'})).toHaveCount(0);
});

test('stale or unaccepted screenplay does not expose Full run controls',async({page})=>{
  await openVideo(page,{accepted:false});
  await expect(page.getByRole('region',{name:'Fully automated run'})).toHaveCount(0);
});

test('stale latest screenplay does not expose Full run controls',async({page})=>{
  await openVideo(page,{stale:true});
  await expect(page.getByRole('region',{name:'Fully automated run'})).toHaveCount(0);
});

test('Full run starts on explicit click without pre-saved prompts and refresh does not start twice',async({page})=>{
  const starts=await openVideo(page);
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(panel).toContainText('Full story · accepted screenplay screen-1');
  await expect(panel.getByRole('button',{name:'Start run'})).toBeEnabled();
  expect(starts().starts).toBe(0);
  await panel.getByRole('button',{name:'Start run'}).click();
  await expect(panel).toContainText('queued');
  expect(starts().starts).toBe(1);
  await panel.getByRole('button',{name:'Refresh run'}).click();
  expect(starts().starts).toBe(1);
});

test('paused Full run can explicitly resume next-scene planning after a completed clip',async({page})=>{
  const counts=await openVideo(page,{runState:'paused',resumeAvailable:true});
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(panel).toContainText('Scene 1, Shot 1, Clip 1 · needs_review');
  const resume=panel.getByRole('button',{name:'Resume next-scene planning'});
  await expect(resume).toBeVisible();
  expect(counts().starts).toBe(0);
  await resume.click();
  await expect(panel).toContainText('run');
  expect(counts().resumes).toBe(1);
  expect(counts().starts).toBe(0);
});

test('paused Full run hides planning resume when backend has not marked it safe',async({page})=>{
  await openVideo(page,{runState:'paused',resumeAvailable:false});
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(panel.getByRole('button',{name:'Resume next-scene planning'})).toHaveCount(0);
});

test('Full run status shows durable character visibility observations without claiming verified identity',async({page})=>{
  await openVideo(page,{runState:'paused',clips:[{
    scene_number:1,shot_number:1,clip_number:1,duration_seconds:7,duration_reason:'The dialogue needs time to land.',state:'needs_review',
    job:{job_id:'completed-first-clip',status:'needs_review'},attempts:[],
    identity_review:{state:'complete',updated_at:'2026-10-12T00:00:00Z',frames:[{
      sample_index:2,timestamp_seconds:3.25,observations:[{
        status:'candidate_match',character_id:'character-mira',character_name:'Mira',visual_evidence:'red coat and silver pendant',
      }],
    }]},
  }]});
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(panel.getByRole('status').filter({hasText:'Character visibility review'})).toContainText('Character visibility review · candidate observations ready');
  await expect(panel).toContainText('Scene 1, Shot 1, Clip 1 · needs_review · completed-first-clip · 7s · The dialogue needs time to land.');
  await expect(panel).toContainText('Frame at 3.3s · candidate match: Mira — red coat and silver pendant');
  await expect(panel).not.toContainText('verified identity');
  await expect(panel.getByRole('button',{name:'Start run'})).toHaveCount(0);
});

test('Full run polls a processing identity review and replaces it with completed observations',async({page})=>{
  let reads=0;
  await openVideo(page,{runState:'paused',clips:()=>{
    reads++;
    const processing=reads===1;
    return [{scene_number:1,shot_number:1,clip_number:1,state:'needs_review',job:{job_id:'completed-first-clip',status:'needs_review'},attempts:[],identity_review:{
      state:processing?'processing':'complete',updated_at:'2026-10-12T00:00:00Z',frames:processing?[]:[{sample_index:1,timestamp_seconds:1.75,observations:[]}],
    }}];
  }});
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(panel.getByRole('status').filter({hasText:'Character visibility review'})).toContainText('Character visibility review · processing');
  await expect(panel.getByRole('status').filter({hasText:'Character visibility review'})).toContainText('Character visibility review · candidate observations ready',{timeout:5000});
  await expect(panel).toContainText('Frame at 1.8s · No character observations');
  expect(reads).toBeGreaterThanOrEqual(2);
});

test('saving Fully automated setup continues to Video Create for the same workspace without loading prompt drafts',async({page})=>{
  await page.addInitScript(()=>localStorage.setItem('vibe-story-selected-v1','story-full'));
  let savedSetup=null, promptDraftReads=0;
  await page.route('**/api/images/workflows',route=>route.fulfill({json:{workflows:[]}}));
  await page.route('**/api/story/**',route=>{
    const req=route.request(),url=new URL(req.url()),path=url.pathname;
    if(path==='/api/story/workspaces/story-full')return route.fulfill({json:{workspace_id:'story-full',title:'Full story',current_revision_id:'source-1'}});
    if(path.endsWith('/screenplay/revisions'))return route.fulfill({json:{items:[{screenplay_revision_id:'screen-1',source_revision_id:'source-1',accepted:true,stale:false}],total:1,offset:0,limit:50}});
    if(path.endsWith('/screenplay'))return route.fulfill({json:{workspace_id:'story-full',screenplay_revision_id:'screen-1',source_revision_id:'source-1',accepted:true,screenplay:{title:'Full story',scenes:[]}}});
    if(path.endsWith('/assisted-stage-skips'))return route.fulfill({json:{skipped:[]}});
    if(path.endsWith('/production-setup')&&req.method()==='PUT'){
      const body=req.postDataJSON(); savedSetup={workspace_id:'story-full',screenplay_revision_id:body.screenplay_revision_id,setup:body.setup};
      return route.fulfill({json:savedSetup});
    }
    if(path.endsWith('/production-setup'))return route.fulfill({json:savedSetup||{workspace_id:'story-full',screenplay_revision_id:'screen-1',setup:null}});
    if(path.endsWith('/prompt-drafts')){promptDraftReads++;return route.fulfill({status:404,json:{error:{message:'No saved prompts'}}});}
    if(path.endsWith('/automated-first-clip'))return route.fulfill({json:{run_state:'not_started',workspace_id:'story-full',screenplay_revision_id:'screen-1',job:null,clips:[]}});
    return route.fulfill({status:404,json:{error:{message:'Not mocked'}}});
  });
  await page.route('**/api/video/**',route=>route.fulfill({json:{available:true,dispatch:{available:true},runtime_guard:{safe_to_submit:true}}}));

  await page.goto('/#/setup');
  await page.getByRole('radio',{name:'Fully automated'}).click();
  await page.getByRole('button',{name:'Save setup'}).click();
  await expect(page.getByRole('status')).toContainText('Setup saved for this accepted screenplay revision');
  const next=page.getByRole('link',{name:'Continue to Video Create'});
  await expect(next).toHaveAttribute('href','#/video?workspace_id=story-full');
  await next.click();
  await expect(page).toHaveURL(/#\/video\?workspace_id=story-full$/);
  await expect(page.getByRole('region',{name:'Fully automated run'})).toContainText('Full story · accepted screenplay screen-1');
  expect(promptDraftReads).toBe(0);
});

test('Assisted per-clip picker ranks pinned style references first without selecting them', async ({page})=>{
  const assistedSetup = { ...setup('assisted_manual'), video_workflow_id:'minimax_h3_r2v_dynamic_v1' };
  const asset = (asset_id, kind, filename, recommended=false) => ({
    asset_id, workspace_id:'story-full', kind, filename, sha256:'a'.repeat(64), size_bytes:1024,
    content_url:`/media/${asset_id}`, roles:[kind === 'audio' ? 'voice' : 'style'], tags:[], created_at:'2026-10-10T00:00:00Z',
    recommended, ...(recommended ? {recommendation_source:'production_style', source_workspace_id:'style-source'} : {}),
  });
  await page.addInitScript(()=>localStorage.setItem('vibe-story-selected-v1','story-full'));
  await page.route('**/api/story/**',route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    if(path==='/api/story/workspaces/story-full') return route.fulfill({json:{workspace_id:'story-full',title:'Full story',current_revision_id:'source-1'}});
    if(path.endsWith('/screenplay/revisions')) return route.fulfill({json:{items:[{screenplay_revision_id:'screen-1',source_revision_id:'source-1',accepted:true,stale:false}],total:1,offset:0,limit:50}});
    if(path.endsWith('/screenplay')) return route.fulfill({json:{workspace_id:'story-full',screenplay_revision_id:'screen-1',source_revision_id:'source-1',accepted:true,screenplay:{title:'Full story',scenes:[{scene_number:1,slugline:'INT. ROOM',summary:'A choice',shots:[{shot_number:1,action:'Mira opens the door.',dialogue:'',direction:{camera:'Wide',lighting:'Soft',mood:'Tense',sfx:'',music:''}}]}]}}});
    if(path.endsWith('/production-setup')) return route.fulfill({json:{workspace_id:'story-full',screenplay_revision_id:'screen-1',setup:assistedSetup}});
    if(path.endsWith('/assisted-video-clip-plan')) return route.fulfill({json:{workspace_id:'story-full',screenplay_revision_id:'screen-1',input_hash:'hash',clips:[{clip_id:'clip-1',scene_number:1,shot_number:1,clip_number:1,workflow_id:'minimax_h3_r2v_dynamic_v1',duration_seconds:6,duration_reason:'within range',prompt:'Mira opens the door.',source_spans:[]}],references:{}}});
    if(path.endsWith('/assisted-video-run')) return route.fulfill({json:{workspace_id:'story-full',screenplay_revision_id:'screen-1',run_state:'not_started',planned_count:1,completed_count:0,clips:[]}});
    return route.fulfill({status:404,json:{error:{message:'Not mocked'}}});
  });
  await page.route('**/api/media/story-full/assets?**',route=>{
    const kind=new URL(route.request().url()).searchParams.get('kind');
    const values={
      image:[asset('style-image','image','Style image',true),asset('local-image','image','Local image')],
      video:[asset('style-video','video','Style video',true),asset('local-video','video','Local video')],
      audio:[asset('style-audio','audio','Style audio',true),asset('local-audio','audio','Local audio')],
    };
    const assets=values[kind]||[];
    return route.fulfill({json:{assets,total:assets.length}});
  });
  await page.route('**/api/video/**',route=>route.fulfill({json:{available:false,dispatch:{available:false},runtime_guard:{safe_to_submit:false}}}));
  await page.goto('/#/video?workspace_id=story-full');
  const panel=page.getByRole('region',{name:'Assisted clip plan'});
  await expect(panel).toBeVisible();
  const picker=panel.getByLabel('Reference asset for clip clip-1');
  await expect(picker.locator('option')).toHaveCount(7);
  const options=await picker.locator('option').allTextContents();
  expect(options.slice(1,4)).toEqual(['Recommended style · image · Style image','Recommended style · video · Style video','Recommended style · audio · Style audio']);
  await expect(picker).toHaveValue('');
  await picker.selectOption('style-image');
  await panel.getByRole('button',{name:'Add reference'}).click();
  await expect(panel.getByLabel('Reference intent for style-image')).toHaveValue('Use this image for visual style; preserve the screenplay characters and action.');
  await picker.selectOption('style-audio');
  await panel.getByRole('button',{name:'Add reference'}).click();
  await expect(panel.getByLabel('Reference intent for style-audio')).toHaveValue('Use this audio for style; preserve the screenplay dialogue and action.');
});


const runningState={run_state:'first_clip_queued',workspace_id:'story-full',screenplay_revision_id:'screen-1',job:{job_id:'same-running-job',status:'running'},clips:[],scene_number:1,shot_number:1};
test('Refresh gives feedback, preserves last status on failure and recovers without submission',async({page})=>{
  let fail=false, complete=false;
  const counts=await openVideo(page,{statusReply:route=>route.fulfill(fail?{status:503,json:{detail:'Backend unavailable'}}:{json:{...runningState,run_state:complete?'completed':'first_clip_queued'}})});
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(panel).toContainText('same-running-job');
  await panel.getByRole('button',{name:'Refresh run',exact:true}).click();
  await expect(panel).toContainText('Status checked at');
  fail=true;
  await panel.getByRole('button',{name:'Refresh run',exact:true}).click();
  await expect(panel.getByRole('alert')).toContainText('Backend unavailable');
  await expect(panel).toContainText('same-running-job');
  fail=false;complete=true;
  await panel.getByRole('button',{name:'Refresh run',exact:true}).click();
  await expect(panel.getByRole('alert')).toHaveCount(0);
  await expect(panel).toContainText('Fully automated · complete');
  await expect(panel.getByRole('button',{name:'Refresh run',exact:true})).toBeEnabled();
  expect(counts().starts).toBe(0);
  await expect(page).toHaveURL(/#\/take\?workspace_id=story-full$/);
});
test('slow refresh retains card and prevents overlapping status requests',async({page})=>{
  let reads=0, release, hold=false;
  const counts=await openVideo(page,{statusReply:async route=>{
    reads++;
    if(hold)await new Promise(resolve=>{release=resolve;});
    return route.fulfill({json:runningState});
  }});
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(page).toHaveURL(/#\/take\?workspace_id=story-full$/);
  await expect(panel).toContainText('same-running-job');
  const initialReads=reads;hold=true;
  await panel.getByRole('button',{name:'Refresh run',exact:true}).click();
  await expect(panel.getByRole('button',{name:'Refreshing…',exact:true})).toBeDisabled();
  await expect(panel).toContainText('same-running-job');
  await page.waitForTimeout(3300);
  expect(reads).toBe(initialReads+1);hold=false;release();
  await expect(panel).toContainText('Status checked at');
  expect(counts().starts).toBe(0);
});
for(const runState of ['first_clip_queued','waiting_for_readiness']){
  test(`returning to ${runState} opens Current Take without starting a job`,async({page})=>{
    const counts=await openVideo(page,{runState});
    await expect(page).toHaveURL(/#\/take\?workspace_id=story-full$/);
    await expect(page.getByRole('region',{name:'Fully automated run'})).toBeVisible();
    expect(counts().starts).toBe(0);
    await page.goto('/#/video?workspace_id=story-full');
    await expect(page).toHaveURL(/#\/take\?workspace_id=story-full$/);
    expect(counts().starts).toBe(0);
  });
}
for(const reason of ['Required model is missing','GPU temperature exceeds limit','Worker is unavailable','Queue is busy']){
  test(`Start blocked with recovery route when ${reason}`,async({page})=>{
    const counts=await openVideo(page,{capability:{available:false,disabled_reason:reason}});
    const panel=page.getByRole('region',{name:'Fully automated run'});
    await expect(panel.getByRole('button',{name:'Start run',exact:true})).toBeDisabled();
    await expect(panel).toContainText(reason);
    await expect(panel.getByRole('link',{name:'Open Status'})).toHaveAttribute('href','#/status');
    await expect(panel.getByRole('button',{name:'Refresh run',exact:true})).toBeEnabled();
    expect(counts().starts).toBe(0);
  });
}


test('Current Take controls pause resume stop while Refresh only reads',async({page})=>{
  const counts=await openVideo(page,{runState:'first_clip_queued'});
  await page.getByRole('link',{name:'Current Take',exact:true}).first().click();
  const panel=page.getByRole('region',{name:'Fully automated run'});
  await expect(panel.getByRole('button',{name:'Pause run',exact:true})).toBeVisible();
  await panel.getByRole('button',{name:'Refresh run',exact:true}).click();
  expect(counts().controls).toEqual([]);
  await panel.getByRole('button',{name:'Pause run',exact:true}).click();
  await expect(panel.getByRole('button',{name:'Resume run',exact:true})).toBeVisible();
  await panel.getByRole('button',{name:'Resume run',exact:true}).click();
  await expect(panel.getByRole('button',{name:'Pause run',exact:true})).toBeVisible();
  await panel.getByRole('button',{name:'Stop run',exact:true}).click();
  await expect(panel).toContainText('stopped');
  expect(counts()).toEqual({starts:0,resumes:0,controls:['pause','resume','stop']});
});
