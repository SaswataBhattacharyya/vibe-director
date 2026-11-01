import {test,expect} from '@playwright/test';
test('shared images: selection follows filters, deletion requires confirmation and reports failure',async({page})=>{
 let deletes=0,previews=0;
 const assets=['one.png','two.png'].map((filename,i)=>({asset_id:`pa-${i}`,workspace_id:'tool-library',kind:'image',roles:['project_image'],filename,media_type:'image/png',sha256:'a'.repeat(64),size_bytes:100,content_url:'/image.png',created_at:'2026-11-01T00:00:00Z',metadata:{}}));
 await page.route('**/api/**',route=>{
  const p=new URL(route.request().url()).pathname;
  if(p==='/api/story/workspaces')return route.fulfill({json:{items:[],total:0}});
  if(p.endsWith('/deletion')){
   if(route.request().method()==='GET'){previews++;return route.fulfill({json:{asset_id:p.split('/').at(-2),path:'/chosen/folder/one.png',sha256:'a'.repeat(64),references:[],can_delete:true}});}
   deletes++;return route.fulfill({status:409,json:{error:{message:'File changed since confirmation.'}}});
  }
  if(p.endsWith('/assets'))return route.fulfill({json:{assets,total:2}});
  if(p.endsWith('/seo-styles'))return route.fulfill({json:{styles:[]}});
  if(p.endsWith('/jobs'))return route.fulfill({json:[]});
  if(p==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test'},models:[]}});
  return route.fulfill({status:404,json:{error:{message:'Unused mock route'}}});
 });
 await page.goto('/#/media-prep?tool=image-home');
 
 await expect(page.getByRole('heading',{name:'Search library'})).toBeVisible();
 
 await page.getByRole('button',{name:'Select all shown (2)',exact:true}).click();
 await expect(page.getByText('2 selected',{exact:true})).toBeVisible();
 await page.getByRole('searchbox',{name:'Search images',exact:true}).fill('one');
 await expect(page.getByText('0 selected',{exact:true})).toBeVisible();
 await page.getByRole('checkbox',{name:'Select one.png',exact:true}).check();
 page.once('dialog',d=>d.dismiss());
 await page.getByRole('button',{name:'Delete files permanently',exact:true}).click();
 await expect(page.getByText('Deletion cancelled.',{exact:true})).toBeVisible();
 expect(deletes).toBe(0);expect(previews).toBe(1);
 await page.getByRole('checkbox',{name:'Select one.png',exact:true}).check();
 page.once('dialog',d=>d.accept());
 await page.getByRole('button',{name:'Delete files permanently',exact:true}).click();
 await expect(page.getByText(/0 of 1 files deleted/)).toBeVisible();
 expect(deletes).toBe(1);
 await expect(page.getByRole('checkbox',{name:'Select one.png',exact:true})).toBeVisible();
});
