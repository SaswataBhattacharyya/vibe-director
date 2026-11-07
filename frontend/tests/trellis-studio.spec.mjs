import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jwZkAAAAASUVORK5CYII=','base64');
test('3D batch has explicit start, recovery and collapsible panels',async({page})=>{
 let submitted,uploads=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',reasoning_effort:'default',lessons:[]},models:[]}});
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
  if(path==='/api/trellis/state')return route.fulfill({json:{input:'/mock/input',output:'/mock/output',jobs:[]}});
  if(path==='/api/trellis/upload')return route.fulfill({json:{id:String(++uploads).padStart(32,'0'),url:'/mock/image.png'}});
  if(path==='/api/trellis/output-folder')return route.fulfill({json:{path:'/mock/chosen',grant:'testgrant'}});
  if(path==='/api/trellis/jobs'){submitted=route.request().postDataJSON();return route.fulfill({json:{job_id:'trellis-123456abcdef',status:'recovery_required',progress:0,message:'Owned prompt awaits reconciliation',items:[],request:submitted}});}
  return route.fulfill({status:404,json:{error:{message:'Unused mock'}}});
 });
 await page.route('**/mock/image.png',r=>r.fulfill({contentType:'image/png',body:png}));
 await mockProject(page); await page.goto('/#/image-to-3d');
 await expect(page.getByRole('heading',{name:'Image to 3D · TRELLIS.2'})).toBeVisible();
 await page.getByRole('button',{name:'Hide Director conversation',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Director',exact:true})).toBeHidden();
 await page.getByRole('button',{name:'Show Director conversation',exact:true}).click();
 await page.getByRole('button',{name:'Hide workspace',exact:true}).click();
 await page.getByRole('button',{name:'Show workspace',exact:true}).click();
 await page.getByText('Studio attachment context',{exact:true}).click();
 await page.getByLabel('Chat images').setInputFiles({name:'context.png',mimeType:'image/png',buffer:png});
 await page.getByRole('button',{name:'Remove context.png'}).click();
 await expect(page.getByRole('button',{name:'Remove context.png'})).toHaveCount(0);
 await page.getByRole('tab',{name:'Batch',exact:true}).click();
 // Simulate the browser's recursive directory selection; native folder choosers are OS-specific.
 await page.locator('input[webkitdirectory]').evaluate((input,bytes)=>{
  const transfer=new DataTransfer();
  for(const path of ['chosen/one.png','chosen/nested/two.png']){
   const file=new File([new Uint8Array(bytes)],path.split('/').pop(),{type:'image/png'});
   Object.defineProperty(file,'webkitRelativePath',{value:path});transfer.items.add(file);
  }
  input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
 },Array.from(png));
 await expect(page.locator('.trellis-gallery label')).toHaveCount(2);
 await page.getByRole('button',{name:'Deselect all'}).click();
 await expect(page.getByRole('button',{name:'Start batch'})).toBeDisabled();
 await page.getByRole('button',{name:'Select all',exact:true}).click();
 await page.getByLabel('Output folder',{exact:true}).fill('/mock/chosen');
 await expect(page.getByRole('button',{name:'Start batch'})).toBeDisabled();
 await page.getByRole('button',{name:'Use entered folder'}).click();
 expect(submitted).toBeUndefined();await page.getByRole('button',{name:'Start batch'}).click();
 await expect(page.getByRole('button',{name:'Reconcile / resume pending'})).toBeVisible();
 expect(submitted.mode).toBe('batch');expect(submitted.items).toHaveLength(2);expect(submitted.output_grant).toBe('testgrant');
 await expect(page.getByRole('button',{name:'Open with Blender'})).toHaveCount(0);await page.screenshot({path:'/tmp/vibe-trellis-desktop.png',fullPage:true});
 await page.setViewportSize({width:480,height:900});
 await expect(page.getByRole('heading',{name:'Image to 3D · TRELLIS.2'})).toBeVisible();
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'/tmp/vibe-trellis-mobile.png',fullPage:true});expect(errors).toEqual([]);
});
