import {mockProject} from './fixtures/project.mjs';
import { test, expect } from '@playwright/test';

const pageOf = items => ({ items, total: items.length, offset: 0, limit: 50 });
async function fixtures(page) {
  page.on('pageerror', error => console.error('Model picker page error:', error.message));
  let settings = {provider:'codex',model:'gpt-test',reasoning_effort:'medium',lessons:[],revision:1};
  const writes = [];
  await page.addInitScript(() => {
    localStorage.setItem('vibe-story-selected-v1','story-model');
    localStorage.setItem('vibe-ace-project','music-model');
    localStorage.setItem('vibe-editor-project','edit-model');
  });
  await page.route('**/api/**', async route => {
    const req=route.request(), path=new URL(req.url()).pathname;
    // Output-destination reads use POST; they do not send chat or change the model.
    if(req.method()!=='GET'&&path!=='/api/studio-tools/output-destination')writes.push(path);
    if(path==='/api/studio-tools/output-destination')return route.fulfill({json:{mode:'folder',path:'/test-owned/output',available:true}});
    if(path==='/api/director/status')return route.fulfill({json:{provider:settings.provider,model:settings.model,quota:'metered',quota_note:'Shared account allowance.',windows:[{bucket:'Codex',window:'primary',used_percent:23,remaining_percent:77,window_minutes:300,resets_at:null}],context_remaining_percent:null,context_note:'Each request is separate.',checked_at:Date.now()/1000,last_request:null}});
    if(path==='/api/director/settings') {
      if(req.method()==='PUT') settings={...req.postDataJSON(),revision:settings.revision+1};
      return route.fulfill({json:{settings,providers:[{id:'codex',label:'Codex',available:true},{id:'ollama',label:'Ollama local',available:true},{id:'opencode',label:'OpenCode API',available:true}],models:[
        {provider:'codex',id:'gpt-test',label:'GPT test',efforts:['medium','high'],default_effort:'medium',available:true},
        {provider:'ollama',id:'qwen-test',label:'Qwen local',efforts:['default'],default_effort:'default',available:true},
        {provider:'opencode',id:'vendor/test',label:'API test',efforts:['default'],default_effort:'default',available:true},
        {provider:'opencode',id:'ollama/missing',label:'Missing local alias',efforts:['default'],default_effort:'default',available:false},
      ]}});
    }
    const revision={revision_id:'rev-model',source_text:'A director walks into a studio.'};
    if(path==='/api/story/workspaces')return route.fulfill({json:pageOf([{workspace_id:'story-model',title:'Model story',current_revision_id:revision.revision_id,initialized:true,status:'ready'}])});
    if(path==='/api/story/workspaces/story-model')return route.fulfill({json:{workspace_id:'story-model',title:'Model story',current_revision:revision,initialized:true,status:'ready'}});
    if(path.endsWith('/draft'))return route.fulfill({json:{draft:null}});
    if(path.endsWith('/revisions'))return route.fulfill({json:pageOf([{revision_id:revision.revision_id,revision_number:1}])});
    if(path==='/api/ace/state')return route.fulfill({json:{projects:[{id:'music-model',name:'Model music',workspace_id:'story-model',revision:1,settings:{mode:'instrumental',tags:'',lyrics:'',duration:10,seed:1,steps:10,cfg:5,scheduler:'euler',adapter_id:'',max_steps:100,learning_rate:.0001,save_every:10,rank:8},intent:'generate',summary:'',questions:[],messages:[],dataset:null,assets:[],adapters:[],job_id:null}],defaults:{},runtime:{ready:false,training_ready:false,checks:{}}}});
    const project={id:'edit-model',name:'Model edit',workspace_id:'story-model',style_id:null,revision:1,messages:[],revisions:[],selection:[],overrides:{}};
    if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{ready:false,version:'test',checks:{},message:''}}});
    if(path==='/api/editor/projects/edit-model')return route.fulfill({json:project});
    if(path.startsWith('/api/media/'))return route.fulfill({json:{assets:[],items:[]}});
    return route.fulfill({status:404,json:{error:{code:'not_found',message:'Not part of the model picker fixture'}}});
  });
  await mockProject(page,'story-model');
  return writes;
}

test('header picker saves provider and synchronizes with the shared Director on Story',async({page})=>{
  const writes=await fixtures(page);
  await page.goto('/#/home');
  await page.getByRole('button',{name:'Model: codex / gpt-test ▾'}).first().click();
  const picker=page.getByRole('dialog',{name:'Choose Director model'});
  await expect(picker.getByRole('option',{name:'Missing local alias · offline'})).toHaveAttribute('disabled','');
  await picker.getByLabel('Available models').selectOption(JSON.stringify(['ollama','qwen-test']));
  await picker.getByRole('button',{name:'Use model',exact:true}).click();
  await expect(page.getByRole('button',{name:'Model: ollama / qwen-test ▾'}).first()).toBeVisible();
  await page.goto('/#/story');
  await expect(page.locator('#project-director-message')).toBeVisible();
  await expect(page.getByRole('button',{name:'Model: ollama / qwen-test ▾'})).toHaveCount(2);
  expect(writes).toEqual(['/api/director/settings']);
});

test('slash model in all three composers keeps drafts and does not send chat',async({page})=>{
  const writes=await fixtures(page);
  for(const [path,id] of [['/#/story','project-director-message'],['/#/editor','project-director-message'],['/#/media-prep?tool=music','project-director-message']]) {
    await page.goto(path);
    const composer=page.locator(`#${id}`);
    await expect(composer).toBeVisible();
    await composer.fill('Keep this draft /model');
    await expect(composer).toHaveValue('Keep this draft ');
    const picker=page.getByRole('dialog',{name:'Choose Director model'});
    await expect(picker).toBeVisible();
    await picker.getByLabel('Search models').fill('GPT');
    await picker.getByLabel('Search models').press('Enter');
    await expect(picker).toBeVisible();
    await picker.getByRole('button',{name:'Close',exact:true}).click();
    await expect(composer).toBeFocused();
  }
  expect(writes.filter(path=>path.includes('/command')||path.includes('edit-proposals'))).toEqual([]);
});


test('slash status in all four composers reads usage without sending chat',async({page})=>{
  const writes=await fixtures(page);
  await page.addInitScript(()=>localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId:'story-model',clipId:'clip-status',workflowId:'minimax_h3_t2v_local_v1',prompt:'A boat at dawn.',duration:6,resolution:0.98,aspectRatio:'16:9'})));
  for(const [path,id] of [['/#/story','project-director-message'],['/#/editor','project-director-message'],['/#/media-prep?tool=music','project-director-message'],['/#/video','project-director-message']]){
    await page.goto(path);
    const composer=page.locator(`#${id}`);
    await expect(composer).toBeVisible();
    await composer.fill('Keep my draft /status');
    await expect(composer).toHaveValue('Keep my draft ');
    const panel=page.getByRole('region',{name:'Model usage',exact:true});
    await expect(panel).toBeVisible();
    await expect(panel).toContainText('23% used · 77% remaining');
    await expect(panel).toContainText('Context remaining: Not reported');
    await panel.getByRole('button',{name:'Refresh usage'}).click();
    await panel.getByRole('button',{name:'Close status'}).click();
    await expect(composer).toBeFocused();
    await expect(composer).toHaveValue('Keep my draft ');
  }
  expect(writes).toEqual([]);
});


test('model picker controls use the studio palette in all themes', async ({page}) => {
  await fixtures(page);
  await page.goto('/#/home');
  await page.getByRole('button',{name:'Model: codex / gpt-test ▾'}).first().click();
  const picker=page.getByRole('dialog',{name:'Choose Director model'});
  for (const palette of ['studio','grit','mixtape']) {
    await page.evaluate(value=>document.documentElement.dataset.palette=value,palette);
    const refresh=picker.getByRole('button',{name:'Refresh',exact:true});
    const styles=await refresh.evaluate(element=>{
      const style=getComputedStyle(element);
      return {background:style.backgroundColor,color:style.color,border:style.borderStyle};
    });
    expect(styles.background).not.toBe('rgb(239, 239, 239)');
    expect(styles.background).not.toBe(styles.color);
    expect(styles.border).toBe('solid');
    await expect(picker.getByRole('button',{name:'Use model',exact:true})).toBeVisible();
    await expect(picker.getByLabel('Reasoning depth')).toHaveCSS('color-scheme','dark');
  }
});
