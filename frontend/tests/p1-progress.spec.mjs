import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';
const paged=items=>({items,total:items.length,offset:0,limit:50});

test('story outside first page resumes, collaborator previews and applies, history compares and restores',async({page})=>{
  let source='Mira holds a key.\nHer sister waits.', revision='rev-1', proposal;
  let messages=[];
  const posts=[];
  await page.addInitScript(()=>localStorage.setItem('vibe-story-selected-v1','story-resume'));
  await page.route('**/api/story/**',route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    if(path==='/api/story/workspaces') return route.fulfill({json:paged([])});
    if(path==='/api/story/workspaces/story-resume') return route.fulfill({json:{workspace_id:'story-resume',title:'Resumed',current_revision_id:revision,current_revision:{revision_id:revision,source_text:source},initialized:true}});
    if(path.endsWith('/draft'))return route.fulfill({json:{draft:null}});
    if(path.endsWith('/revisions')&&req.method()==='GET') return route.fulfill({json:paged([{revision_id:'rev-1',revision_number:1,source_sha256:'hash'}])});
    if(path.endsWith('/revisions/rev-1')) return route.fulfill({json:{revision_id:'rev-1',revision_number:1,source_text:'Mira holds a key.\nHer sister waits.'}});
    if(path.includes('/edit-requests/by-key/'))return route.fulfill({json:{workspace_id:'story-resume',status:'complete',proposal}});
    if(path.endsWith('/edit-proposals')) {const body=req.postDataJSON();posts.push(body);proposal={...body,workspace_id:'story-resume',proposal_id:'proposal-1',replacement:'Mira hides a key.\nHer sister waits.',status:'pending'};return route.fulfill({json:proposal});}
    if(path.endsWith('/edit-proposals/accept')) {revision='rev-2';source=proposal.replacement;proposal.status='accepted';return route.fulfill({json:{revision_id:revision,source_text:source}});}
    if(path.endsWith('/restore')) {revision='rev-3';source='Mira holds a key.\nHer sister waits.';posts.push(req.postDataJSON());return route.fulfill({json:{revision_id:revision,source_text:source}});}
    return route.fulfill({status:404,json:{error:{message:'No graph'}}});
  });
  await mockProject(page,'story-resume');
  await page.route('**/api/agent/projects/*/conversation',route=>{
    if(route.request().method()==='POST') {
      const body=route.request().postDataJSON(); posts.push(body);
      expect(body.surface).toBe('story');
      proposal={...body.target,instruction:body.text,workspace_id:'story-resume',proposal_id:'proposal-1',replacement:'Mira hides a key.\nHer sister waits.',status:'pending'};
      messages.push({request_id:body.request_id,text:body.text,reply:'Review the story proposal.',status:'answered',task_id:null,story_target:body.target});
    }
    return route.fulfill({json:{workspace_id:'story-resume',messages}});
  });
  await page.route('**/api/agent/projects/*/tasks',route=>route.fulfill({json:{tasks:[]}}));
  await page.goto('/#/story');
  await expect(page.getByLabel('Story source text')).toHaveValue(source);
  await expect(page.locator('textarea.story-source')).toHaveCount(1);
  await expect(page.locator('details.revision-panel')).not.toHaveAttribute('open');
  await page.getByLabel('Message the project Director',{exact:true}).fill('Let Mira hide the key; preserve her sister.');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await expect(page.getByLabel('AI edit proposal')).toContainText('Mira hides');
  expect(posts[0].target.expected_text).toBe(source);
  await expect(page.locator('#story-chat')).toHaveCount(0);
  await expect(page.getByLabel('Story source text')).toHaveValue(source);
  await page.getByRole('button',{name:'Accept as revision'}).click();
  await expect(page.getByLabel('Story source text')).toHaveValue('Mira hides a key.\nHer sister waits.');
  await page.locator('details.revision-panel>summary').click();
  await page.getByRole('button',{name:'Compare',exact:true}).last().click();
  await expect(page.getByLabel('Revision comparison')).toContainText('Mira holds a key.');
  await expect(page.getByLabel('Revision comparison')).toContainText('Mira hides a key.');
  await page.getByRole('button',{name:'Restore as new revision'}).click();
  await expect(page.getByLabel('Story source text')).toHaveValue('Mira holds a key.\nHer sister waits.');
  expect(posts.at(-1).expected_current_revision_id).toBe('rev-2');
});

for(const storageFailure of [false,true]) test(`screenplay recovery and server save with storage failure ${storageFailure}`,async({page})=>{
  let saved={workspace_id:'story-script',screenplay_revision_id:'script-1',source_revision_id:'rev-1',graph_snapshot_id:'graph-1',screenplay:{scenes:[{scene_number:1,slugline:'INT. ROOM',summary:'A choice',shots:[{shot_number:1,action:'Mira holds a key.',dialogue:'MIRA: I will wait.',direction:{camera:'Wide',lighting:'Soft',mood:'Quiet',sfx:'Clock',music:'Piano'},evidence:[]}]}]}};
  const saves=[];
  await page.addInitScript(storageFailure=>{
    localStorage.setItem('vibe-story-selected-v1','story-script');
    if(storageFailure){const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key.startsWith('vibe-screenplay-local:'))throw new DOMException('full','QuotaExceededError');return original.call(this,key,value);};}
  },storageFailure);
  await page.route('**/api/story/**',route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    if(path==='/api/story/workspaces/story-script')return route.fulfill({json:{workspace_id:'story-script',current_revision_id:'rev-1'}});
    if(path.endsWith('/screenplay/revisions'))return route.fulfill({json:paged([{screenplay_revision_id:saved.screenplay_revision_id,source_revision_id:'rev-1',accepted:false}])});
    if(path.endsWith('/screenplay'))return route.fulfill({json:saved});
    if(path.endsWith('/screenplay/revisions/script-1')&&req.method()==='PATCH'){const body=req.postDataJSON();saves.push(body);saved={...saved,screenplay_revision_id:'script-2',screenplay:body.screenplay};return route.fulfill({json:saved});}
    if(path.endsWith('/graph'))return route.fulfill({json:{status:'complete'}});
    return route.fulfill({status:404,json:{}});
  });
  await mockProject(page,'story-script');
  await page.goto('/#/screenplay');await page.getByLabel('Action',{exact:true}).fill('Mira hides the key.');
  await expect(page.getByRole('button',{name:'Generate new revision'})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Review & accept'})).toBeDisabled();
  if(!storageFailure){await page.goto('/#/story');await page.goto('/#/screenplay');await expect(page.getByLabel('Action',{exact:true})).toHaveValue('Mira hides the key.');await expect(page.getByText('Recovered screenplay edits from this browser.',{exact:false})).toBeVisible();}
  else await expect(page.getByRole('alert').filter({hasText:'Browser recovery storage is unavailable'})).toBeVisible();
  await page.getByRole('button',{name:'Save progress'}).click();
  await expect(page.getByText('Edit saved as a new screenplay revision',{exact:false})).toBeVisible();
  expect(saves).toHaveLength(1);expect(saves[0].screenplay.scenes[0].shots[0].action).toBe('Mira hides the key.');
  await page.reload();await expect(page.getByLabel('Action',{exact:true})).toHaveValue('Mira hides the key.');
});
