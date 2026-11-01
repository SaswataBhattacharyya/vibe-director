import {test,expect} from '@playwright/test';

test('Create keeps its form in the right pane and applies chat suggestions without generating',async({page})=>{
  let requests=0;const submitted=[];
  await page.addInitScript(()=>{
    localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId:'workspace-a',clipId:'clip-a',workflowId:'minimax_h3_t2v_local_v1',prompt:'A boat at dawn.',duration:6,resolution:0.98,aspectRatio:'16:9'}));
  });
  await page.route('**/api/**',async route=>{
    const request=route.request();const path=new URL(request.url()).pathname;
    if(request.method()!=='GET') submitted.push(path);
    if(path.endsWith('/field-edit-proposals')){requests++;return route.fulfill({json:{replacement:'A boat at dawn, filmed with a slow dolly.',explanation:'Added the camera movement.'}});}
    return route.fulfill({status:404,json:{detail:'Not used by this mocked layout test'}});
  });
  await page.goto('/#/video');
  const workspace=page.locator('.create-workspace-wrap');
  const chat=workspace.locator('.editor-conversation'),form=workspace.locator('.editor-preview');
  await expect(chat.getByRole('heading',{name:'Director',exact:true})).toBeVisible();
  await expect(form.getByRole('button',{name:/Text to video/})).toBeVisible();
  await workspace.getByRole('button',{name:'Hide creation controls',exact:true}).click();
  await expect(form).toBeHidden();
  await workspace.getByRole('button',{name:'Show creation controls',exact:true}).click();
  await chat.getByLabel('Message the Director').fill('Use a slow dolly.');
  await chat.getByRole('button',{name:'Send',exact:true}).click();
  await expect(chat.getByRole('button',{name:'Apply prompt',exact:true})).toBeEnabled();
  await form.getByLabel('Shot prompt',{exact:true}).fill('Changed while reviewing.');
  await expect(chat.getByRole('button',{name:'Apply prompt',exact:true})).toBeDisabled();
  await form.getByLabel('Shot prompt',{exact:true}).fill('A boat at dawn.');
  await chat.getByRole('button',{name:'Apply prompt',exact:true}).click();
  await expect(form.getByLabel('Shot prompt',{exact:true})).toHaveValue('A boat at dawn, filmed with a slow dolly.');
  await expect(form.getByLabel('Duration',{exact:true})).toHaveValue('6');
  await workspace.getByRole('button',{name:'Hide conversation',exact:true}).click();
  await page.reload();
  await expect(workspace.locator('.editor-conversation')).toBeHidden();
  await workspace.getByRole('button',{name:'Show conversation',exact:true}).click();
  await expect(chat.getByRole('button',{name:'Applied',exact:true})).toBeVisible();
  expect(requests).toBe(1);
  expect(submitted).toEqual(['/api/story/workspaces/workspace-a/field-edit-proposals']);
});
