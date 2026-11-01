import {test,expect} from '@playwright/test';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jwZkAAAAASUVORK5CYII=','base64');
async function mocks(page){let uploads=0,submitted;
 await page.route('**/api/**',async route=>{
 const path=new URL(route.request().url()).pathname;
 if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',reasoning_effort:'default',lessons:[]},models:[]}});
 if(path==='/api/trellis/state')return route.fulfill({json:{input:'/mock/input',output:'/mock/output',jobs:[],service:{ready:true}}});
 if(path==='/api/trellis/upload')return route.fulfill({json:{id:String(++uploads).padStart(32,'0'),url:'/mock/image.png'}});
 if(path==='/api/trellis/jobs'){submitted=route.request().postDataJSON();return route.fulfill({json:{job_id:'trellis-123456abcdef',status:'queued',progress:0,message:'Mock queued',items:[],request:submitted}});}
 return route.fulfill({status:404,json:{error:{message:'Unused mock'}}});
 });
 await page.route('**/mock/image.png',r=>r.fulfill({contentType:'image/png',body:png}));
 return ()=>submitted;
}
test('Pixal has only multiview, labelled uploads and explicit approval before start',async({page})=>{
 const submitted=await mocks(page);await page.goto('/#/image-to-3d-pixal3d');
 await expect(page.getByRole('heading',{name:'Image to 3D · Pixal3D'})).toBeVisible();
 await expect(page.getByLabel('Image input',{exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Generate 3D',exact:true})).toBeDisabled();
 for(const view of ['front','back'])await page.getByLabel(`Upload ${view} for object 1`,{exact:true}).setInputFiles({name:view+'.png',mimeType:'image/png',buffer:png});
 const confirm=page.getByLabel('I reviewed every direction',{exact:false});await expect(confirm).toBeEnabled();
 expect(submitted()).toBeUndefined();await confirm.check();await page.getByRole('button',{name:'Generate 3D',exact:true}).click();
 await expect.poll(()=>submitted()?.views_confirmed).toBe(true);expect(submitted().backend).toBe('pixal');expect(Object.keys(submitted().items[0].views)).toEqual(['front','back']);
});
test('TRELLIS sheet previews and approval, four view slots, padding and collapse',async({page})=>{
 await mocks(page);const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#/image-to-3d');
 await page.getByLabel('Image input',{exact:true}).selectOption('multiview');
 await page.getByLabel('Multi-view input method').selectOption('sheet');
 await page.locator('.multiview-drop input').setInputFiles({name:'sheet.png',mimeType:'image/png',buffer:png});
 await expect(page.getByRole('heading',{name:'Split and review sheet'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Use reviewed crops'})).toBeDisabled();
 await page.getByRole('button',{name:'Preview crops'}).click();
 await expect(page.locator('.multiview-crops img')).toHaveCount(2);
 await page.getByRole('button',{name:'Use reviewed crops'}).click();
 await expect(page.locator('.multiview-slot img')).toHaveCount(2);
 await expect(page.getByRole('button',{name:'Generate 3D',exact:true})).toBeDisabled();
 await page.getByLabel('I reviewed every direction',{exact:false}).check();
 await expect(page.getByRole('button',{name:'Generate 3D',exact:true})).toBeEnabled();
 await page.getByLabel('Views per object').selectOption('four');await expect(page.locator('.multiview-slot')).toHaveCount(4);
 await expect(page.getByRole('button',{name:'Generate 3D',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Hide conversation',exact:true}).click();await page.getByRole('button',{name:'Show conversation',exact:true}).click();
 await page.screenshot({path:'/tmp/vibe-multiview-desktop.png',fullPage:true});
 const overlap=await page.locator('.multiview-slot').evaluateAll(nodes=>nodes.some((n,i)=>nodes.slice(i+1).some(m=>{const a=n.getBoundingClientRect(),b=m.getBoundingClientRect();return a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;})));expect(overlap).toBe(false);
 await page.setViewportSize({width:480,height:900});await page.getByRole('button',{name:'creation controls panel',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'/tmp/vibe-multiview-mobile.png',fullPage:true});expect(errors).toEqual([]);
});
