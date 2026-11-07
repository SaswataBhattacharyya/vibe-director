import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';

test('visual edits share the plan, block old approval, save and reload without rendering',async({page},info)=>{
 const clips=[{asset_id:'v1',filename:'first.mp4',start:0,end:3,mime:'video/mp4'},{asset_id:'v2',filename:'second.mp4',start:0,end:3,mime:'video/mp4'}];
 const plan={summary:'Two clips',tools:['HyperFrames','FFmpeg'],width:320,height:180,fps:24,clips,audio:null};
 let project={id:'visual',name:'Visual edit',workspace_id:'w',style_id:null,revision:1,messages:[],revisions:[],selection:clips,overrides:{},view:{tab:'visual'},brief:{summary:'Edit clips',questions:[]},pending:{kind:'plan',revision:1,value:plan}};
 let posted,previewed,commands=0;
 await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:w','visual'));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{ready:true,checks:{}}}});
  if(path==='/api/editor/projects/visual/plan'){posted=route.request().postDataJSON();project={...project,revision:2,pending:{kind:'plan',revision:2,value:posted.plan}};return route.fulfill({json:project});}
  if(path==='/api/editor/projects/visual/preview'){previewed=route.request().postDataJSON();return route.fulfill({json:{revision:project.revision,duration:6,document:'<p>Trusted preview</p>'}});}
  if(path==='/api/editor/projects/visual/command'){commands++;return route.fulfill({json:project});}
  if(path==='/api/editor/projects/visual')return route.fulfill({json:project});
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
  return route.fulfill({status:404,json:{error:{message:'Unused mock endpoint'}}});
 });
 await mockProject(page,'w');await page.goto('/#/editor');
 await expect(page.getByRole('button',{name:'Return to AI Editor',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Load HyperFrames preview',exact:true}).click();
 await expect.poll(()=>previewed?.plan?.clips?.length).toBe(2);
 await expect(page.getByTitle('HyperFrames plan preview')).toHaveAttribute('sandbox','allow-scripts');
 await page.getByLabel('Visual caption',{exact:true}).fill('Edited visually');
 await expect(page.getByTitle('HyperFrames plan preview')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Approve this revision',exact:true})).toBeDisabled();
 await page.getByLabel('Source out (seconds)',{exact:true}).fill('2');
 await page.getByRole('button',{name:'Move selected clip later',exact:true}).click();
 await page.getByRole('button',{name:'Expand visual editor',exact:true}).click();
 await expect(page.locator('.editor-visual-expanded')).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.locator('.editor-visual-expanded')).toHaveCount(0);
 await page.getByText('Filters, speed & transition', {exact:true}).click();
 await page.getByLabel('Video filter',{exact:true}).selectOption('cinematic');
 await page.getByLabel('Starting speed (×)',{exact:true}).fill('1.5');
 await expect(page.getByRole('button',{name:'Load HyperFrames preview',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Save visual timeline proposal',exact:true}).click();
 await expect.poll(()=>posted?.plan?.clips?.[1]?.caption).toBe('Edited visually');
 expect(posted.plan.clips.map(c=>c.asset_id)).toEqual(['v2','v1']);expect(posted.plan.clips[1].end).toBe(2);
 expect(posted.plan.clips[1].effect.preset).toBe('cinematic');expect(posted.plan.clips[1].speed.start).toBe(1.5);
 expect(commands).toBe(0);
 await expect(page.getByRole('button',{name:'Approve this revision',exact:true})).toBeEnabled();
 // Simulate a previously approved plan on reload; the editable timeline must restore it.
 project={...project,pending:undefined,revisions:[{kind:'plan',revision:2,value:posted.plan}]};
 await page.reload();await expect(page.getByLabel('Source out (seconds)',{exact:true})).toHaveValue('3');
 await page.getByRole('button',{name:/2\. first.mp4/}).click();
 await expect(page.getByLabel('Visual caption',{exact:true})).toHaveValue('Edited visually');
 await expect(page.getByLabel('Source out (seconds)',{exact:true})).toHaveValue('2');
 expect(commands).toBe(0);
 await page.getByLabel('Visual caption',{exact:true}).fill('Keep my local draft');
 const remotePlan={...posted.plan,summary:'Another saved proposal'};
 project={...project,revision:3,pending:{kind:'plan',revision:3,value:remotePlan}};
 await page.getByRole('button',{name:'Refresh saved state',exact:true}).click();
 await expect(page.getByLabel('Visual caption',{exact:true})).toHaveValue('Keep my local draft');
 await expect(page.getByRole('button',{name:'Save visual timeline proposal',exact:true})).toBeDisabled();
 await expect(page.getByRole('button',{name:'Approve this revision',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Reload saved timeline',exact:true}).click();
 await expect(page.getByLabel('Visual caption',{exact:true})).toHaveValue('Edited visually');
 await page.screenshot({path:info.outputPath('visual-desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Expand visual editor',exact:true}).click();
 const bounds=await page.locator('.editor-visual-expanded').boundingBox();expect(bounds.y).toBeLessThan(6);expect(bounds.height).toBeGreaterThan(800);
 await page.screenshot({path:info.outputPath('visual-mobile.png')});
 await page.getByRole('button',{name:'Collapse visual editor',exact:true}).click();
 await page.getByRole('button',{name:'Return to AI Editor',exact:true}).click();
 await expect(page.getByRole('button',{name:'Open Visual Editor',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Open Visual Editor',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Visual Editor',exact:true})).toBeVisible();
});
