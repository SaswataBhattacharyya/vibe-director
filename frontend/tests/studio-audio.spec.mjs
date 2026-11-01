import {test,expect} from '@playwright/test';
test('Audio Studio keeps microphone permission explicit and exposes trained voice controls',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:1600,height:1000});
 await page.addInitScript(()=>{Object.defineProperty(navigator,'mediaDevices',{value:{enumerateDevices:async()=>[],getUserMedia:async()=>{throw new Error('Microphone permission denied');}}});});
 await page.route('**/api/**',route=>{
  const path=new URL(route.request().url()).pathname;
  let json;
  if(path==='/api/director/settings')json={settings:{provider:'codex',model:'test',reasoning_effort:'default',lessons:[]},models:[]};
  else if(path==='/api/story/workspaces')json={items:[{workspace_id:'ws-test',title:'Test workspace'}]};
  else if(path.includes('/assets'))json={assets:[]};
  else if(path==='/api/audio/effects/capabilities')json={operations:[],rvc_models:[]};
  else if(path==='/api/studio-tools/voice/capabilities')json={speech:true,design:false,training:true,errors:{design:'Local Qwen3 model unavailable'}};
  else if(path==='/api/studio-tools/voice/jobs')json={jobs:[]};
  return json===undefined?route.fulfill({status:404,json:{error:'Not configured in this isolated test'}}):route.fulfill({json});
 });
 await page.goto('/#/media-prep?tool=audio-studio&workspace_id=ws-test');
 await page.getByRole('button',{name:'Record',exact:true}).click();
 await expect(page.getByRole('alert').filter({hasText:'Microphone permission denied'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Record',exact:true})).toBeEnabled();
 await page.getByLabel('Activity').selectOption('training');
 await expect(page.getByRole('button',{name:'Review and start training'})).toBeDisabled();
 await page.getByLabel('Activity').selectOption('design');
 await expect(page.getByText('Local Qwen3 model unavailable')).toBeVisible();
 await expect(page.getByRole('button',{name:'Generate voice preview'})).toBeDisabled();
 expect(errors).toEqual([]);
 await page.screenshot({path:'/tmp/vibe-audio-studio.png',fullPage:true});
});
