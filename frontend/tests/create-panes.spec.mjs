import {test,expect} from '@playwright/test';

test('Create keeps full-width controls and a collapsible prompt assistant without generating',async({page})=>{
  let requests=0;const submitted=[];
  await page.addInitScript(()=>{
    localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId:'workspace-a',clipId:'clip-a',workflowId:'minimax_h3_t2v_local_v1',prompt:'A boat at dawn.',duration:6,resolution:0.98,aspectRatio:'16:9'}));
  });
  await page.route('**/api/**',async route=>{
    const request=route.request();const path=new URL(request.url()).pathname;
    if(request.method()!=='GET') submitted.push(path);
    if(path==='/api/projects/current')return route.fulfill({json:{workspace_id:'workspace-a',title:'Test film',browser_state:{}}});
    if(path==='/api/projects/memory')return route.fulfill({json:{saved:true}});
    if(path==='/api/studio-tools/output-destination')return route.fulfill({json:{mode:'folder',path:'/test-owned/output',available:true}});
    if(path.endsWith('/field-edit-proposals')){requests++;return route.fulfill({json:{replacement:'A boat at dawn, filmed with a slow dolly.',explanation:'Added the camera movement.'}});}
    return route.fulfill({status:404,json:{detail:'Not used by this mocked layout test'}});
  });
  await page.goto('/#/video');
  const workspace=page.locator('.create-workspace-wrap');
  const assistant=workspace.locator('.create-prompt-assistant');
  const chat=assistant.locator('.create-chat'),form=workspace;
  await expect(form.getByLabel('Shot prompt',{exact:true})).toBeVisible();
  await expect(chat).toBeHidden();
  await assistant.locator('summary').click();
  await expect(chat.getByRole('heading',{name:'Refine this shot',exact:true})).toBeVisible();
  await chat.getByLabel('Message the Director').fill('Use a slow dolly.');
  await chat.getByRole('button',{name:'Send',exact:true}).click();
  await expect(chat.getByRole('button',{name:'Apply prompt',exact:true})).toBeEnabled();
  await form.getByLabel('Shot prompt',{exact:true}).fill('Changed while reviewing.');
  await expect(chat.getByRole('button',{name:'Apply prompt',exact:true})).toBeDisabled();
  await form.getByLabel('Shot prompt',{exact:true}).fill('A boat at dawn.');
  await chat.getByRole('button',{name:'Apply prompt',exact:true}).click();
  await expect(form.getByLabel('Shot prompt',{exact:true})).toHaveValue('A boat at dawn, filmed with a slow dolly.');
  await expect(form.getByLabel('Duration',{exact:true})).toHaveValue('6');
  await assistant.locator('summary').click();
  await expect(chat).toBeHidden();
  await page.reload();
  await expect(chat).toBeHidden();
  await assistant.locator('summary').click();
  await expect(chat.getByRole('button',{name:'Applied',exact:true})).toBeVisible();
  expect(requests).toBe(1);
  expect(submitted.filter(path=>!['/api/projects/memory','/api/studio-tools/output-destination'].includes(path))).toEqual(['/api/story/workspaces/workspace-a/field-edit-proposals']);
});
