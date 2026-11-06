import {test,expect} from '@playwright/test';

test('Debug records steps and observations, excludes typed text, and stops when off',async({page})=>{
  let enabled=false; const events=[]; let sessions=0;
  const policy=()=>({enabled,session_id:sessions?'session':null,log_path:sessions?'/tmp/manual-debug.jsonl':null,bytes:0,max_bytes:8388608});
  await page.route('**/api/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    if(path==='/api/debug') {
      if(req.method()==='PUT'){enabled=req.postDataJSON().enabled;if(enabled)sessions++;}
      return route.fulfill({json:policy()});
    }
    if(path==='/api/debug/events'){if(enabled)events.push(...req.postDataJSON().events);return route.fulfill({json:{recorded:req.postDataJSON().events.length,enabled}});}
    return route.fulfill({status:503,json:{error:{message:'Mock backend unavailable'}}});
  });
  await page.goto('/#/status');
  await page.getByRole('switch',{name:'Debug',exact:true}).click();
  await expect(page.getByRole('switch',{name:'Debug',exact:true})).toBeChecked();
  await expect(page.getByText('Local log:',{exact:false})).toBeVisible();
  await page.getByRole('link',{name:'Create',exact:true}).first().click();
  await page.getByLabel('Shot prompt').pressSequentially('PRIVATE PROMPT DO NOT LOG');
  await page.getByLabel('Shot prompt').press('Tab');
  await page.getByRole('link',{name:'Status',exact:true}).click();
  await page.getByLabel('Manual result').selectOption('failed');
  await page.getByLabel('Step and observation').fill('Preview missing in mock scenario');
  await page.getByRole('button',{name:'Save observation'}).click();
  await expect(page.getByText('Observation sent to the local journal.')).toBeVisible();
  expect(events.some(event=>event.kind==='navigation' && event.route.includes('video'))).toBeTruthy();
  expect(events.some(event=>event.kind==='interaction' && event.action==='change' && event.value.includes('characters entered'))).toBeTruthy();
  expect(events.some(event=>event.kind==='api' && event.status===503)).toBeTruthy();
  expect(events.some(event=>event.kind==='owner_observation' && event.outcome==='failed')).toBeTruthy();
  expect(JSON.stringify(events)).not.toContain('PRIVATE PROMPT');
  await page.getByRole('switch',{name:'Debug',exact:true}).click();
  await expect(page.getByRole('switch',{name:'Debug',exact:true})).not.toBeChecked();
  const count=events.length;
  await page.getByRole('link',{name:'Create',exact:true}).first().click();
  await page.waitForTimeout(1300);
  expect(events).toHaveLength(count);
});

test('Debug displays a journal write failure and can stop a full recording',async({page})=>{
  let enabled=true, attempts=0;
  await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path==='/api/debug'){if(route.request().method()==='PUT')enabled=route.request().postDataJSON().enabled;return route.fulfill({json:{enabled,session_id:'test',log_path:'/tmp/debug.jsonl',bytes:0,max_bytes:8388608}});}
    if(path==='/api/debug/events'){attempts++;return route.fulfill({status:400,json:{error:{message:'Debug log is full'}}});}
    return route.fulfill({status:503,json:{}});
  });
  await page.goto('/#/status');
  await page.getByLabel('Step and observation').fill('Attempt to save');
  await page.getByRole('button',{name:'Save observation'}).click();
  await expect(page.getByText(/Debug recording:.*Debug log is full/)).toBeVisible();
  await expect(page.getByText('Observation sent to the local journal.')).toHaveCount(0);
  const rejected=attempts;
  await page.evaluate(async()=>{
    const recorder=await import('/src/lib/debug-recorder.ts');
    recorder.recordDebug({kind:'interaction',target:'Do not retry a rejected batch'});
    for(let i=0;i<3;i++)await recorder.flushDebug().catch(()=>{});
  });
  expect(attempts).toBe(rejected);
  await page.getByRole('switch',{name:'Debug',exact:true}).click();
  await expect(page.getByRole('switch',{name:'Debug',exact:true})).not.toBeChecked();
});

test('Debug enabled in one tab starts recording in tabs that were already open',async({context})=>{
  let enabled=false; const events=[];
  await context.route('**/api/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    if(path==='/api/debug') {
      if(req.method()==='PUT') enabled=req.postDataJSON().enabled;
      return route.fulfill({json:{enabled,session_id:enabled?'session':null,log_path:enabled?'/tmp/manual-debug.jsonl':null,bytes:0,max_bytes:8388608}});
    }
    if(path==='/api/debug/events') { if(enabled) events.push(...req.postDataJSON().events); return route.fulfill({json:{recorded:enabled?req.postDataJSON().events.length:0,enabled}}); }
    return route.fulfill({status:503,json:{error:{message:'Mock backend unavailable'}}});
  });
  const [workflow,status]=await Promise.all([context.newPage(),context.newPage()]);
  await Promise.all([workflow.goto('/'),status.goto('/#/status')]);
  await workflow.evaluate(()=>{const button=document.createElement('button');button.textContent='Create';document.body.append(button);});
  await status.getByRole('switch',{name:'Debug',exact:true}).click();
  await expect(status.getByRole('switch',{name:'Debug',exact:true})).toBeChecked();
  await workflow.getByRole('button',{name:'Create',exact:true}).click();
  await expect.poll(()=>events.some(event=>event.kind==='interaction' && event.target==='Create')).toBeTruthy();
  expect(events.some(event=>event.kind==='navigation' && event.action==='recording_started_in_another_tab')).toBeTruthy();
  await workflow.clock.install();
  await workflow.clock.pauseAt(new Date());
  await workflow.evaluate(async()=>{
    window.debugSyncState=null;
    window.addEventListener('storage',event=>{if(event.key==='vibe-director-debug-enabled')window.debugSyncState=event.newValue;});
    const recorder=await import('/src/lib/debug-recorder.ts');
    recorder.recordDebug({kind:'interaction',target:'UNSAVED OLD SESSION'});
  });
  await status.getByRole('switch',{name:'Debug',exact:true}).click();
  await expect.poll(()=>workflow.evaluate(()=>window.debugSyncState)).toBe('false');
  await workflow.evaluate(async()=>{const recorder=await import('/src/lib/debug-recorder.ts');await recorder.flushDebug();});
  await status.getByRole('switch',{name:'Debug',exact:true}).click();
  await expect.poll(()=>workflow.evaluate(()=>window.debugSyncState)).toBe('true');
  await workflow.evaluate(async()=>{
    const recorder=await import('/src/lib/debug-recorder.ts');
    recorder.recordDebug({kind:'interaction',target:'NEW SESSION'});await recorder.flushDebug();
  });
  expect(events.some(event=>event.target==='UNSAVED OLD SESSION')).toBeFalsy();
  expect(events.some(event=>event.target==='NEW SESSION')).toBeTruthy();
  await workflow.close(); await status.close();
});
