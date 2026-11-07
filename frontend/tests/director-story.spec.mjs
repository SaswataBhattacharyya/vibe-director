import {test,expect} from '@playwright/test';
const owner='story-aaaaaaaaaaaa';
const original='Before 😀. The old phrase. After Ω.';
async function fixture(page,loseReply=false) {
  let source=original,revision='rev-1',proposal,messages=[];
  const writes=[];
  await page.addInitScript(owner=>{
    localStorage.setItem('vibe-story-selected-v1',owner);
    if(!localStorage.getItem('vibe-story-ui-draft-v1'))localStorage.setItem('vibe-story-ui-draft-v1',JSON.stringify({importPreview:null,importTitle:'',newTitle:'',newText:'',sourceHadCrLf:false,chatInstruction:'Preserved unsent instruction',conversations:{[owner]:[{instruction:'Previous request',replacement:'Saved historical reply',revision:'rev-old'}]}}));
  },owner);
  await page.route('**/api/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname,post=req.method()==='POST';
    if(post)writes.push({path,body:req.postDataJSON()});
    let json;
    if(path==='/api/projects/current')json={workspace_id:owner,title:'Story fixture',browser_state:{}};
    else if(path==='/api/projects/memory')json={saved:true};
    else if(path.endsWith('/conversation')){
      if(post){
        const body=req.postDataJSON();
        expect(body.surface).toBe('story');
        proposal={...body.target,proposal_id:'proposal-test',instruction:body.text,replacement:'new phrase',status:'pending'};
        messages.push({request_id:body.request_id,text:body.text,reply:loseReply?'':'Review the story passage.',status:loseReply?'interrupted':'answered',task_id:null,story_target:body.target});
        if(loseReply)return route.fulfill({status:500,json:{error:{message:'Reply lost after proposal saved'}}});
      }
      json={workspace_id:owner,messages};
    }
    else if(path.endsWith('/tasks'))json={tasks:[]};
    else if(path==='/api/story/workspaces')json={items:[],total:0,offset:0,limit:50};
    else if(path===`/api/story/workspaces/${owner}`)json={workspace_id:owner,title:'Story fixture',initialized:true,current_revision_id:revision,current_revision:{revision_id:revision,source_text:source}};
    else if(path.endsWith('/revisions'))json={items:[{revision_id:revision,revision_number:1}],total:1,offset:0,limit:50};
    else if(path.endsWith('/draft'))json={draft:null};
    else if(path.includes('/edit-requests/by-key/'))json={workspace_id:owner,status:'complete',proposal};
    else if(path.endsWith('/edit-proposals/accept')){
      expect(req.postDataJSON()).toEqual({proposal_id:'proposal-test',expected_current_revision_id:'rev-1'});
      source=Array.from(source).slice(0,proposal.start_codepoint).join('')+proposal.replacement+Array.from(source).slice(proposal.end_codepoint).join('');
      revision='rev-2';proposal.status='accepted';json={revision_id:revision,source_text:source};
    }
    else if(path.endsWith('/edit-proposals/discard')){proposal.status='discarded';json=proposal;}
    else return route.fulfill({status:404,json:{error:{message:'Fixture: unavailable'}}});
    return route.fulfill({json});
  });
  return writes;
}
async function selectPassage(page){
  const source=page.getByLabel('Story source text');
  await expect(source).toHaveValue(original);
  await source.evaluate(node=>{const start=node.value.indexOf('old phrase');node.focus();node.setSelectionRange(start,start+'old phrase'.length);node.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));});
  await expect(page.getByRole('group',{name:'Edit selected passage'})).toBeVisible();
}
async function send(page){
  await page.getByLabel('Message the project Director',{exact:true}).fill('Prepare clearer wording.');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
}
test('Story uses one Director, keeps history and drafts, and recovers a Unicode proposal without replay',async({page},info)=>{
  const writes=await fixture(page);
  await page.goto('/#/story');
  await selectPassage(page);
  await expect(page.locator('#story-chat')).toHaveCount(0);
  await page.getByText('Previous instructions · saved on this browser',{exact:true}).click();
  await expect(page.getByText('Saved historical reply',{exact:true})).toBeVisible();
  await page.getByText('Previous unsent instruction',{exact:true}).click();
  await expect(page.getByText('Preserved unsent instruction',{exact:true})).toBeVisible();
  await send(page);
  await expect(page.getByLabel('AI edit proposal')).toContainText('new phrase');
  const sent=writes.find(row=>row.path.endsWith('/conversation')).body;
  expect(sent.target).toEqual({version:1,workspace_id:owner,base_revision_id:'rev-1',start_codepoint:14,end_codepoint:24,expected_text:'old phrase'});
  await expect(page.getByLabel('Story source text')).toHaveValue(original);
  await page.evaluate(()=>{const key='vibe-story-ui-draft-v1';const ui=JSON.parse(localStorage.getItem(key));delete ui.editProposal;localStorage.setItem(key,JSON.stringify(ui));});
  await page.reload();
  await expect(page.getByLabel('AI edit proposal')).toBeVisible();
  for(const width of [1280,900,390]){
    await page.setViewportSize({width,height:width===390?844:900});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:info.outputPath(`story-${width}.png`)});
  }
  await page.getByRole('button',{name:'Accept as revision',exact:true}).click();
  await expect(page.getByLabel('Story source text')).toHaveValue('Before 😀. The new phrase. After Ω.');
  await page.reload();
  await expect(page.getByLabel('AI edit proposal')).toHaveCount(0);
  expect(writes.filter(row=>row.path.endsWith('/conversation'))).toHaveLength(1);
  expect(writes.filter(row=>row.path.endsWith('/edit-proposals'))).toHaveLength(0);
});
test('Story rejects unsaved draft guidance and recovers an interrupted reply by read-only Refresh',async({page})=>{
  const writes=await fixture(page,true);
  await page.goto('/#/story');await selectPassage(page);
  await page.getByLabel('Story source text').fill(original+' unfinished');
  await send(page);
  await expect(page.locator('.director-error')).toContainText('Save progress');
  expect(writes.filter(row=>row.path.endsWith('/conversation'))).toHaveLength(0);
  await page.getByLabel('Story source text').fill(original);await selectPassage(page);await send(page);
  await expect(page.locator('.director-error')).toContainText('Reply lost');
  await page.getByRole('button',{name:'Refresh Director conversation',exact:true}).click();
  await expect(page.getByLabel('AI edit proposal')).toBeVisible();
  await page.getByRole('button',{name:'Discard',exact:true}).click();
  await expect(page.getByLabel('AI edit proposal')).toHaveCount(0);
  await page.reload();
  await expect(page.getByLabel('AI edit proposal')).toHaveCount(0);
  expect(writes.filter(row=>row.path.endsWith('/conversation'))).toHaveLength(1);
  await expect(page.getByLabel('Story source text')).toHaveValue(original);
});
