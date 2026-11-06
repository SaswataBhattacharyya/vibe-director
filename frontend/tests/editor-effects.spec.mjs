import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';
test('effects controls preserve chosen ranges and require a new media/tool clearance',async({page},info)=>{
 const clips=[{asset_id:'v1',filename:'first.mp4',mime:'video/mp4',start:0,end:3,fit:'contain'},{asset_id:'v2',filename:'second.mp4',mime:'video/mp4',start:0,end:3,fit:'contain'}];
 let project={id:'effects',name:'Effects edit',workspace_id:'w',style_id:null,revision:1,messages:[],revisions:[],selection:clips,overrides:{},view:{tab:'timeline'},brief:{summary:'Edit these clips',questions:[]}};
 const plan={summary:'Two clips',tools:['HyperFrames','FFmpeg'],width:320,height:180,fps:24,clips,audio:null};
 project.pending={kind:'plan',revision:1,value:plan};let posted;
 await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:w','effects'));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{ready:true,checks:{}}}});
  if(path==='/api/editor/projects/effects/plan'){posted=route.request().postDataJSON();project={...project,revision:2,pending:{kind:'plan',revision:2,value:posted.plan}};return route.fulfill({json:project});}
  if(path==='/api/editor/projects/effects')return route.fulfill({json:project});
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
  return route.fulfill({status:404,json:{error:{message:'Unused mock endpoint'}}});
 });
 await mockProject(page,'w'); await page.goto('/#/editor');
 await page.getByRole('button',{name:'Edit timeline',exact:true}).click();
 const first=page.getByRole('group',{name:'Clip 1: first.mp4',exact:true});
 await first.getByText('Filters, speed & transition',{exact:true}).click();
 await first.getByRole('combobox',{name:/^Video filter/}).selectOption('vhs');
 await first.getByLabel('Starting speed (×)').fill('.75');
 await first.getByLabel('Ending speed (×)').fill('1.5');
 await first.getByLabel('Transition to next clip').selectOption('cross-warp-morph');
 await first.getByLabel('Transition duration (seconds)').fill('.5');
 await expect(first.getByText('Warp / blend is a visual transition', {exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Save proposed timeline',exact:true}).click();
 await expect.poll(()=>posted?.plan?.clips?.[0]?.effect?.preset).toBe('vhs');
 expect(posted.plan.clips[0].speed).toEqual({start:.75,end:1.5});
 expect(posted.plan.clips[0].transition).toEqual({kind:'cross-warp-morph',duration:.5});
 expect(posted.plan.clips.map(c=>[c.asset_id,c.start,c.end])).toEqual([['v1',0,3],['v2',0,3]]);
 await expect(page.locator('.editor-clearance')).toContainText('Speed: 0.75× → 1.5×');
 await expect(page.getByRole('button',{name:'Approve this revision'})).toBeVisible();
 await page.screenshot({path:info.outputPath('editor-effects.png'),fullPage:true});
});
