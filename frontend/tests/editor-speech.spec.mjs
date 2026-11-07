import {test,expect} from '@playwright/test';
import {mockProject} from './fixtures/project.mjs';

test('reviewed transcript cuts retain one Director and become a persisted render proposal',async({page})=>{
  const selection=[{asset_id:'video',filename:'speech.mp4',mime:'video/mp4',start:0,end:12}];
  let project={id:'speech-edit',name:'Speech edit',workspace_id:'w',style_id:null,revision:4,
    selection,messages:[],revisions:[],overrides:{},view:{tab:'timeline'},brief:{summary:'Review speech',questions:[]}};
  let posted;
  await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:w','speech-edit'));
  await page.route('**/api/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{checks:{}}}});
    if(path==='/api/editor/projects/speech-edit/speech')return route.fulfill({json:{revision:project.revision,sources:[{
      task_id:'task-speech',job_id:'job-speech',asset_id:'video',sha256:'a'.repeat(64),filename:'speech.mp4',
      transcript:{duration_seconds:12,segments:[{start:6.5,end:8,text:'Review these words.',avg_logprob:-.4,no_speech_prob:.1}]},
    }]}});
    if(path==='/api/editor/projects/speech-edit/speech-cuts'){
      posted=req.postDataJSON();project={...project,revision:5,pending:{kind:'plan',revision:5,value:{
        summary:'Reviewed speech cuts',width:1280,height:720,fps:24,tools:['HyperFrames','FFmpeg'],audio:null,
        clips:[{...selection[0],end:6.5},{...selection[0],start:8}],
      }}};return route.fulfill({json:project});
    }
    if(path==='/api/editor/projects/speech-edit')return route.fulfill({json:project});
    if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
    if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
    if(path.endsWith('/tasks'))return route.fulfill({json:{tasks:[]}});
    if(path.endsWith('/conversation'))return route.fulfill({json:{messages:[]}});
    return route.fulfill({status:404,json:{error:{message:'Unused mock endpoint'}}});
  });
  await mockProject(page,'w');await page.goto('/#/editor');
  await page.getByText('Review speech and propose cuts',{exact:true}).click();
  await page.getByRole('button',{name:'Load completed speech evidence'}).click();
  await expect(page.getByText('6.500–8.000s · Review these words.')).toBeVisible();
  await expect(page.getByLabel('Speech source playback')).toHaveAttribute('src','/api/media/w/assets/video/content');
  await page.getByLabel('Remove speech segment 1').check();
  await page.getByRole('button',{name:'Save reviewed cuts as proposal'}).click();
  await expect.poll(()=>posted).toEqual({revision:4,task_id:'task-speech',segment_indices:[0]});
  await expect(page.locator('.editor-clearance')).toContainText('Reviewed speech cuts');
  await expect(page.getByRole('button',{name:'Approve this revision',exact:true})).toBeVisible();
  expect(project.selection).toEqual(selection);
  await page.reload();
  await expect(page.getByLabel('Editable timeline JSON')).toContainText('6.5');
  await expect(page.locator('#project-director-message')).toHaveCount(1);
});
