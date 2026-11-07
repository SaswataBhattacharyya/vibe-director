import {mockProject} from './fixtures/project.mjs';
import assert from 'node:assert/strict';
import { test, expect } from '@playwright/test';
const defaults={mode:'instrumental',tags:'',lyrics:'',duration:30,seed:1,steps:60,cfg:15,scheduler:'euler',adapter_id:'',max_steps:1000,learning_rate:0.0001,save_every:100,rank:16,task:'text',reference_id:'',reference_strength:.5,source_tags:'',source_lyrics:'',edit_min:.6,edit_max:1,style_name:'',style_description:''};
async function mockAce(page,projects=[]) {
  if(projects.length)await mockProject(page,projects[0].workspace_id);
  await page.route('**/api/studio-tools/output-destination',route=>route.fulfill({json:{mode:'workspace',path:'/test-owned/outputs/music',available:true}}));
  const state={projects,defaults,presets:{Jazz:'jazz, piano'},adapters:[],saved_presets:[],runtime:{ready:true,training_ready:true,reason:'Ready',dataset_format:'song.mp3\\nsong_prompt.txt\\nsong_lyrics.txt\\nUTF-8: [verse], [chorus], or [instrumental]',checks:{source:true},training_encoders_cached:true}};
  await page.route('**/api/media/*/assets**',route=>route.fulfill({json:{assets:[],total:0}}));
  await page.route('**/api/ace/state',route=>route.fulfill({json:state}));
  return state;
}
test('ACE chat drafts; only confirmation submits music',async({page})=>{
  const state=await mockAce(page);
  await mockProject(page,'ws-music');
  await page.route('**/api/story/workspaces**',route=>route.fulfill({json:{items:[{workspace_id:'ws-music',title:'Music test'}]}}));
  await page.route('**/api/ace/projects',route=>{
    const p={id:'music-test',name:'My song',workspace_id:'ws-music',revision:1,settings:{...defaults},intent:'generate',summary:'',questions:[],messages:[],dataset:null,assets:[],adapters:[],job_id:null};
    state.projects.push(p);return route.fulfill({json:p});
  });
  const actions=[];
  await page.route('**/api/ace/projects/music-test/command',route=>{
    const body=route.request().postDataJSON(),p=state.projects[0];actions.push(body.action);
    assert.equal(body.revision,p.revision);
    if(body.action==='chat'){
      p.messages.push({id:'reply',role:'assistant',content:'A soft instrumental piano piece.'});
      p.settings.tags='soft piano';p.summary='Soft piano, instrumental, 30 seconds';p.revision++;
    }else if(body.action==='settings'){p.settings=body.settings;p.intent=body.intent;p.revision++;}
    else if(body.action==='confirm'){p.confirmed_revision=p.revision;p.job_id='confirmed-job';p.job={job_id:p.job_id,status:'completed',stage:'completed',message:'Music saved.'};}
    return route.fulfill({json:p});
  });
  let messages=[];
  await page.route('**/api/agent/projects/ws-music/tasks',route=>route.fulfill({json:{tasks:[]}}));
  await page.route('**/api/agent/projects/ws-music/conversation',route=>{
    if(route.request().method()==='POST'){
      const body=route.request().postDataJSON(),p=state.projects[0];
      expect(body.surface).toBe('music');expect(body.target).toEqual({version:1,workspace_id:'ws-music',project_id:p.id,revision:p.revision});
      actions.push('chat');p.messages.push({id:'reply',role:'assistant',content:'A soft instrumental piano piece.'});p.settings.tags='soft piano';p.summary='Soft piano, instrumental, 30 seconds';p.revision++;
      messages.push({request_id:body.request_id,text:body.text,reply:'Review the session response.',status:'answered',task_id:null});
    }
    return route.fulfill({json:{messages}});
  });
  await page.goto('/#/media-prep?tool=music');
  await page.getByRole('heading',{name:'ACE-Step Music'}).waitFor();
  await expect(page.locator('#ace-chat')).toHaveCount(0);
  await expect(page.locator('.director-composer textarea')).toHaveCount(1);
  await page.getByLabel('Message the project Director',{exact:true}).fill('Make a soft piano instrumental');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await page.getByText('A soft instrumental piano piece.',{exact:true}).waitFor();
  assert.deepEqual(actions,['chat']);
  await page.getByRole('button',{name:'Run ACE-Step'}).click();
  await page.getByRole('button',{name:'Prepare another take'}).waitFor();
  assert.deepEqual(actions,['chat','confirm']);
  await page.getByRole('button',{name:'Fine-tune',exact:true}).click();
  await page.getByRole('heading',{name:'Fine-tune a music style'}).waitFor();
  assert.match(await page.locator('.ace-format').innerText(),/song_prompt.txt/);
  await page.reload();
  await page.getByLabel('Message the project Director',{exact:true}).waitFor();
  assert.deepEqual(actions,['chat','confirm']);
});

test('Control-Foley advanced controls reach the existing job API', async ({page}) => {
  await mockAce(page);
  const base = process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180';
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-foley',title:'Foley test'}],limit:50,offset:0,total:1})}));
  await page.route('**/api/audio/music/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
    ace_step:{comfyui_online:true,ace:{status:'blocked',checkpoint:'ace',checkpoint_size:1},finetune:{status:'blocked',smoke_ready:false,full_training_enabled:false,checks:[]}},
    control_foley:{status:'available',comfyui_online:true,model_ready:true,workflow_ready:true,missing_nodes:[],schema:{modes:[]}},
    workflow_files:{ace_step:false,control_foley:true},
  })}));
  await page.route('**/api/media/ws-foley/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.route('**/api/workflow-guidance?**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({workflow_id:'control_foley_text_audio_v1',model_id:'control_foley',knowledge_id:'foley-guidance-v1',guidance_version:1,workflow_sha256:'b'.repeat(64),retrieval_status:'matched',sources:[],nodes:[],edges:[]})}));
  await page.route('**/api/audio/ws-foley/control-foley/jobs', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  let submitted;
  await page.route('**/api/audio/ws-foley/control-foley/jobs', async route => {
    if (route.request().method() === 'GET') return route.fulfill({status:200,contentType:'application/json',body:'[]'});
    submitted = route.request().postDataJSON();
    await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({job_id:'foley-test',status:'queued',progress:0,stage:'queued',message:'Foley queued.'})});
  });

  await page.goto(`${base}/#/media-prep?tool=music`);
  await page.getByRole('heading',{name:'ACE-Step Music'}).waitFor();
  await page.getByRole('button',{name:'Control-Foley'}).click();
  await page.getByLabel('Music workspace').selectOption('ws-foley');
  await page.getByLabel('Sound description').fill('Rain on a metal roof');
  await page.getByText('Advanced settings').click();
  await page.getByLabel('Control-Foley negative prompt').fill('No voices');
  await page.getByLabel('Control-Foley inference steps').selectOption('30');
  await page.getByRole('button',{name:'Generate audio'}).click();
  await page.getByText('Foley queued.').waitFor();
  assert.equal(submitted.settings.negative_prompt,'No voices');
  assert.equal(submitted.settings.steps,30);
  assert.deepEqual(submitted.prompt_knowledge_ref,{knowledge_id:'foley-guidance-v1',guidance_version:1,workflow_sha256:'b'.repeat(64)});
});

test('Music & Sound shows source-linked guidance for the selected workflow without starting a job', async ({page}) => {
  await mockAce(page);
  const base = process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:5180';
  await page.route('**/api/story/workspaces**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{workspace_id:'ws-guidance',title:'Guidance test'}],limit:50,offset:0,total:1})}));
  await page.route('**/api/audio/music/capabilities', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
    ace_step:{comfyui_online:false,ace:{status:'blocked',checkpoint:'ace',checkpoint_size:1},finetune:{status:'blocked',smoke_ready:false,full_training_enabled:false,checks:[]}},
    control_foley:{status:'blocked',comfyui_online:false,model_ready:false,workflow_ready:false,missing_nodes:[],schema:{modes:[]}},
    workflow_files:{ace_step:true,control_foley:true},
  })}));
  await page.route('**/api/media/ws-guidance/assets**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({assets:[],total:0})}));
  await page.route('**/api/audio/ws-guidance/music/jobs', route => route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  const requested=[];
  await page.route('**/api/workflow-guidance?**', route => {
    const url=new URL(route.request().url());const workflowId=url.searchParams.get('workflow_id');requested.push(workflowId);
    const prompt=workflowId==='ace_step_music_v1'?'Tags are required; song mode needs lyrics.':workflowId==='control_foley_text_audio_v1'?'Describe a sound; this mode uses no media references.':'Video reference is required for this mode.';
    const sourceId='adapter_source';
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({workflow_id:workflowId,model_id:url.searchParams.get('model_id'),knowledge_id:`${workflowId}-knowledge-v2`,workflow_version:'local-v1',workflow_sha256:'c'.repeat(64),guidance_version:2,retrieval_status:'matched',sources:[{source_id:sourceId,uri:'music_sound.py',version:'sha256:adapter',section:'Local adapter contract'}],nodes:[{node_id:'prompt_contract',kind:'prompt_contract',text:prompt,source_ids:[sourceId]}],edges:[]})});
  });
  let jobPosts=0;
  page.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/api/audio/'))jobPosts++;});
  await page.goto(`${base}/#/media-prep?tool=music`);
  await page.getByRole('heading',{name:'ACE-Step Music'}).waitFor();
  await page.getByRole('button',{name:'Control-Foley'}).click();
  await page.getByText('Describe a sound; this mode uses no media references.').waitFor();
  await page.getByLabel('Control-Foley mode').selectOption('reference_video_audio');
  await page.getByText('Video reference is required for this mode.').waitFor();
  // React StrictMode replays mount effects in development, so compare the
  // workflow coverage/order while allowing a repeated initial read.
  assert.deepEqual([...new Set(requested)],['control_foley_text_audio_v1','control_foley_reference_video_audio_v1']);
  assert.equal(jobPosts,0);
});

test('ACE direct reference, lyrics, presets and dataset uploads share the saved draft',async({page})=>{
  const p={id:'music-direct',name:'Direct music',workspace_id:'ws-direct',revision:0,settings:{...defaults},intent:'generate',summary:'',questions:[],messages:[],dataset:null,assets:[],adapters:[],job_id:null};
  const state=await mockAce(page,[p]);
  state.adapters.push({id:'trained-style',name:'My trained style',tags:'trained, acoustic'});
  await page.addInitScript(()=>localStorage.setItem('vibe-ace-project:ws-direct','music-direct'));
  await page.route('**/api/story/workspaces**',r=>r.fulfill({json:{items:[]}}));
  let uploads=0;
  await page.route('**/api/media/ws-direct/assets**',route=>{
    if(route.request().method()==='GET')return route.fulfill({json:{assets:[],total:0}});
    uploads++;return route.fulfill({json:{asset_id:`audio-${uploads}`,filename:new URL(route.request().url()).searchParams.get('filename'),kind:'audio',content_url:'/mock-audio.wav'}});
  });
  const actions=[];let rows;
  await page.route('**/api/ace/projects/music-direct/command',route=>{
    const body=route.request().postDataJSON();actions.push(body.action);
    assert.equal(body.revision,p.revision);
    if(body.action==='settings'){p.settings=body.settings;p.intent=body.intent;p.revision++;}
    if(body.action==='confirm'){p.confirmed_revision=p.revision;p.job_id='job';p.job={job_id:'job',status:'running',stage:'generating',message:'Generating',step_progress:{done:2,total:10}};}
    return route.fulfill({json:p});
  });
  await page.route('**/api/ace/projects/music-direct/dataset',route=>{
    const body=route.request().postDataJSON();rows=body.rows;
    p.dataset={count:rows.length,songs:rows.map(r=>r.relative_path),entries:rows.map(r=>({...r,duration_seconds:10}))};p.revision++;
    return route.fulfill({json:p});
  });
  await page.goto('/#/media-prep?tool=music');
  await page.getByRole('textbox',{name:'Music prompt',exact:true}).fill('warm piano');
  await page.getByRole('textbox',{name:'Lyrics',exact:true}).fill('[verse]\nNew words here');
  await page.getByRole('combobox',{name:'Style',exact:true}).selectOption('base:Jazz');
  assert.equal(await page.getByRole('textbox',{name:'Music prompt',exact:true}).inputValue(),'jazz, piano');
  assert.equal(await page.getByRole('textbox',{name:'Lyrics',exact:true}).inputValue(),'[verse]\nNew words here');
  await page.getByLabel('Reference audio',{exact:true}).setInputFiles({name:'reference.wav',mimeType:'audio/wav',buffer:Buffer.from('mock audio')});
  await page.getByText('Attached reference.wav. Uploading does not start a job.',{exact:true}).waitFor();
  assert.equal(p.settings.reference_id,'audio-1');assert.equal(p.settings.task,'reference');
  assert.equal(p.settings.mode,'song');assert(!actions.includes('confirm'));assert(!actions.includes('chat'));
  await page.getByRole('textbox',{name:'Music prompt',exact:true}).fill('unsaved prompt retained');
  await page.reload();
  assert.equal(await page.getByRole('textbox',{name:'Music prompt',exact:true}).inputValue(),'unsaved prompt retained');
  await page.getByRole('button',{name:'Fine-tune',exact:true}).click();
  await page.getByLabel('Upload matching triplets').setInputFiles([{name:'song.mp3',mimeType:'audio/mpeg',buffer:Buffer.from('mock')},{name:'song_prompt.txt',mimeType:'text/plain',buffer:Buffer.from('jazz, piano')},{name:'song_lyrics.txt',mimeType:'text/plain',buffer:Buffer.from('[instrumental]')}]);
  await page.getByRole('heading',{name:'1 validated songs'}).waitFor();
  assert.equal(rows[0].relative_path,'song.mp3');
  await page.getByLabel('New style name').fill('My next style');
  await page.getByRole('button',{name:'Start fine-tuning',exact:true}).click();
  assert.equal(p.intent,'finetune');assert.equal(p.settings.style_name,'My next style');
  await expect.poll(()=>actions.filter(a=>a==='confirm').length).toBe(1);
  await page.getByRole('progressbar').waitFor();
});


test('ACE lists earlier tracks, confirms shared deletion and restores without generation',async({page})=>{
  const tracks=[1,2].map(n=>({asset_id:`pa-ace${n}`,workspace_id:'ws-audio',kind:'audio',roles:['project_audio'],filename:`take-${n}.wav`,created_at:'2026-10-27T00:00:00Z',content_url:`/fixture-${n}`}));
  const project={id:'music-library',name:'Shared song project',workspace_id:'ws-audio',revision:1,settings:{...defaults,reference_id:'pa-ace1'},intent:'generate',summary:'',questions:[],messages:[],dataset:null,assets:[...tracks],adapters:[],job_id:null};
  await mockAce(page,[project]);
  await page.addInitScript(()=>localStorage.setItem('vibe-ace-project:ws-audio','music-library'));
  await page.route('**/api/story/workspaces**',route=>route.fulfill({json:{items:[{workspace_id:'ws-audio',title:'Audio'}]}}));
  const archived=new Set(),writes=[];
  await page.route('**/api/media/ws-audio/assets/**',route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.pathname.endsWith('/catalogue')){
      expect(url.searchParams.get('source')).toBe('ace_generated');
      const assets=tracks.filter(a=>!archived.has(a.asset_id));
      return route.fulfill({json:{assets,total:assets.length,workspaces:['ws-audio'],offset:0,limit:24}});
    }
    writes.push(url.pathname);
    const id=url.pathname.split('/').at(-2);
    if(url.pathname.endsWith('/archive'))archived.add(id);else archived.delete(id);
    return route.fulfill({json:{asset:tracks.find(a=>a.asset_id===id)}});
  });
  await page.goto('/#/media-prep?tool=music');
  await page.getByRole('button',{name:'Audio & models',exact:true}).click();
  const list=page.getByRole('region',{name:'Generated ACE-Step audio'});
  await expect(list.getByLabel('take-1.wav')).toBeVisible();
  await expect(list.getByLabel('take-2.wav')).toBeVisible();
  await list.getByRole('button',{name:'Select all shown (2)',exact:true}).click();
  await expect(list.getByRole('button',{name:'Deselect all shown (2)',exact:true})).toBeVisible();
  await list.getByRole('button',{name:'Delete selected (2)',exact:true}).click();
  const dialog=list.getByRole('alertdialog');
  await expect(dialog).toContainText('Shared song project');
  await expect(dialog).toContainText('files are retained');
  expect(writes).toEqual([]);
  await dialog.getByRole('button',{name:'Cancel',exact:true}).click();
  expect(writes).toEqual([]);
  await list.getByRole('button',{name:'Delete selected (2)',exact:true}).click();
  await dialog.getByRole('button',{name:'Delete from library',exact:true}).click();
  await expect(list.getByText('No matching ACE-Step audio.',{exact:true})).toBeVisible();
  await list.getByRole('button',{name:'Undo deletion',exact:true}).click();
  await expect(list.getByLabel('take-1.wav')).toBeVisible();
  expect(writes).toHaveLength(4);
});
