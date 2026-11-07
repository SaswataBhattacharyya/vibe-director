import {test,expect} from '@playwright/test';

async function fixture(page,{lost=false,legacy=false}={}){
  let requests=0,messages=[];const submitted=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(legacy=>{
    localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId:'workspace-a',clipId:'clip-a',workflowId:'minimax_h3_t2v_local_v1',prompt:'A boat at dawn.',duration:6,resolution:0.98,aspectRatio:'16:9'}));
    if(legacy&&!localStorage.getItem('vibe-create-chat:workspace-a:clip-a'))localStorage.setItem('vibe-create-chat:workspace-a:clip-a',JSON.stringify([{instruction:'A previous direction',base:'A boat at dawn.',context:'old',requestKey:'legacy-pending'}]));
  },legacy);
  await page.route('**/api/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname;
    if(request.method()!=='GET')submitted.push(path);
    if(path==='/api/projects/current')return route.fulfill({json:{workspace_id:'workspace-a',title:'Test film',browser_state:{}}});
    if(path==='/api/projects/memory')return route.fulfill({json:{saved:true}});
    if(path==='/api/studio-tools/output-destination')return route.fulfill({json:{mode:'folder',path:'/test-owned/output',available:true}});
    if(path==='/api/agent/projects/workspace-a/tasks')return route.fulfill({json:{tasks:[]}});
    if(path==='/api/agent/projects/workspace-a/conversation'){
      if(request.method()==='POST'){
        requests++;const body=request.postDataJSON();expect(body.surface).toBe('video');expect(body.target.prompt).toBe('A boat at dawn.');expect(body.target.settings.duration).toBe(6);
        const item={request_id:body.request_id,text:body.text,reply:lost?'':'Review before Apply.',status:lost?'interrupted':'answered',task_id:null,video_target:body.target,
          ...(!lost?{proposal:{surface:'video',target:body.target,suggestion:{replacement:'A boat at dawn, filmed with a slow dolly.',explanation:'Added the camera movement.'}}}:{})};
        messages.push(item);
      }
      return route.fulfill({json:{messages}});
    }
    if(path.startsWith('/api/story/field-edit-requests/by-key/'))return route.fulfill({json:{status:'complete',proposal:{replacement:'A recovered boat prompt.',explanation:'Saved direction.'}}});
    return route.fulfill({status:404,json:{error:{message:'Not used by this mocked layout test'}}});
  });
  return {submitted,errors,requests:()=>requests};
}

test('Create uses the shared Director and reviews a prompt without changing settings or generating',async({page})=>{
  const fx=await fixture(page);await page.goto('/#/video');
  const form=page.locator('.create-workspace-wrap'),assistant=form.locator('.create-prompt-assistant'),chat=assistant.locator('.create-chat');
  await expect(form.getByLabel('Shot prompt',{exact:true})).toBeVisible();await expect(chat).toBeHidden();
  await expect(page.locator('#create-chat-message')).toHaveCount(0);await expect(page.locator('.director-composer textarea')).toHaveCount(1);
  await page.getByLabel('Message the project Director',{exact:true}).fill('Use a slow dolly.');await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await assistant.locator('summary').click();const apply=chat.getByRole('button',{name:'Apply prompt',exact:true});await expect(apply).toBeEnabled();
  await form.getByLabel('Shot prompt',{exact:true}).fill('Changed while reviewing.');await expect(apply).toBeDisabled();
  await form.getByLabel('Shot prompt',{exact:true}).fill('A boat at dawn.');await form.getByLabel('Duration',{exact:true}).selectOption('8');await expect(apply).toBeDisabled();
  await form.getByLabel('Duration',{exact:true}).selectOption('6');await expect(apply).toBeEnabled();
  await page.reload();await assistant.locator('summary').click();await expect(apply).toBeEnabled();await apply.click();
  await expect(form.getByLabel('Shot prompt',{exact:true})).toHaveValue('A boat at dawn, filmed with a slow dolly.');await expect(form.getByLabel('Duration',{exact:true})).toHaveValue('6');
  await page.reload();await assistant.locator('summary').click();await expect(apply).toHaveCount(0);
  expect(fx.requests()).toBe(1);expect(fx.submitted.filter(path=>path.includes('/jobs')||path.includes('field-edit-proposals'))).toEqual([]);expect(fx.errors).toEqual([]);
});

for(const legacy of [false,true])test(`${legacy?'legacy':'shared interrupted'} shot prompt recovers by saved key without resubmitting`,async({page})=>{
  const fx=await fixture(page,{lost:true,legacy});await page.goto('/#/video');
  if(!legacy){await page.getByLabel('Message the project Director',{exact:true}).fill('Use a slow dolly.');await page.getByRole('button',{name:'Send to project Director',exact:true}).click();}
  await page.locator('.create-prompt-assistant summary').click();
  await page.getByRole('button',{name:'Check suggestion status',exact:true}).click();await expect(page.getByText('A recovered boat prompt.',{exact:true})).toBeVisible();
  await page.reload();await page.locator('.create-prompt-assistant summary').click();await expect(page.getByText('A recovered boat prompt.',{exact:true})).toBeVisible();
  expect(fx.requests()).toBe(legacy?0:1);expect(fx.submitted.filter(path=>path.includes('/jobs')||path.includes('field-edit-proposals'))).toEqual([]);expect(fx.errors).toEqual([]);
});
