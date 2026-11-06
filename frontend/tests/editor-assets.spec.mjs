import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';
test('editor library selections and pasted/dropped attachments persist into chat',async({page})=>{
  page.on('pageerror',e=>console.log('PAGE ERROR',e.message));
  const asset=(id,kind,name)=>({asset_id:id,workspace_id:'w',kind,filename:name,created_at:'2026-10-26',media:{duration_seconds:3},content_url:'/mock/'+name,roles:[]});
  const video=asset('v','video','clip.mp4'), image=asset('i','image','portrait.png');
  let project={id:'edit-assets',name:'Asset edit',workspace_id:'w',style_id:null,revision:1,messages:[],revisions:[],selection:[],overrides:{},view:{}};
  let chatSelection,uploads=0;const known=new Map([[video.asset_id,video],[image.asset_id,image]]);
  await page.addInitScript(()=>localStorage.setItem('vibe-editor-project:w','edit-assets'));
  await page.route('**/api/**',async route=>{
    const req=route.request(),url=new URL(req.url()),path=url.pathname;
    if(path==='/api/director/settings')return route.fulfill({json:{settings:{provider:'codex',model:'test',reasoning_effort:'default',lessons:[]},models:[]}});
    if(path==='/api/story/workspaces')return route.fulfill({json:{items:[]}});
    if(path==='/api/editor/state')return route.fulfill({json:{projects:[project],styles:[],runtime:{ready:false,checks:{}}}});
    if(path.endsWith('/conversation')){if(req.method()==='POST')chatSelection=req.postDataJSON().target.selected_ranges;return route.fulfill({json:{messages:[]}});}
    if(path.endsWith('/tasks'))return route.fulfill({json:{tasks:[]}});
    if(path==='/api/editor/projects/edit-assets'){
      if(req.method()==='PUT'){const body=req.postDataJSON();if(body.selection)body.selection=body.selection.map(r=>({...r,filename:known.get(r.asset_id)?.filename}));project={...project,...body,view:{...project.view,...body.view},revision:project.revision+1};}
      return route.fulfill({json:project});
    }
    if(path==='/api/media/w/assets'){
      if(req.method()==='POST'){uploads++;const uploaded=asset('upload'+uploads,'image',url.searchParams.get('filename'));known.set(uploaded.asset_id,uploaded);return route.fulfill({json:uploaded});}
      return route.fulfill({json:{assets:url.searchParams.get('kind')==='video'?[video]:[image],total:1}});
    }
    return route.fulfill({status:404,json:{error:{message:'Unused mock endpoint'}}});
  });
  await mockProject(page,'w'); await page.goto('/#/editor');
  await page.getByRole('navigation',{name:'Editor panels'}).getByRole('button',{name:'Asset selection',exact:true}).click();
  await page.getByRole('button',{name:'Preview clip.mp4',exact:true}).click();
  await page.getByRole('button',{name:'Add to edit selection',exact:true}).click();
  await expect(page.getByLabel('Editing attachments')).toContainText('clip.mp4 · 0–3s');
  await page.locator('.editor-preview').getByLabel('Kind').selectOption('image');
  await page.getByRole('button',{name:'Preview portrait.png',exact:true}).click();
  await page.getByRole('button',{name:'Add to edit selection',exact:true}).click();
  await expect(page.locator('#project-director-message')).toBeEnabled();
  await page.locator('.editor-attachments').evaluate(el=>{const data=new DataTransfer();data.items.add(new File(['png'],'pasted.png',{type:'image/png'}));el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true}));});
  await expect(page.getByLabel('Editing attachments')).toContainText('pasted.png');
  await expect(page.locator('#project-director-message')).toBeEnabled();
  await page.locator('.editor-attachments').evaluate(el=>{const data=new DataTransfer();data.items.add(new File(['png'],'dropped.png',{type:'image/png'}));el.dispatchEvent(new DragEvent('drop',{dataTransfer:data,bubbles:true,cancelable:true}));});
  await expect(page.getByLabel('Editing attachments')).toContainText('dropped.png');
  await page.reload();
  await expect(page.getByLabel('Editing attachments')).toContainText('clip.mp4');
  await expect(page.getByLabel('Editing attachments')).toContainText('dropped.png');
  await page.locator('#project-director-message').fill('Use these clips and images for the edit.');
  await page.getByRole('button',{name:'Send to project Director',exact:true}).click();
  await expect.poll(()=>chatSelection?.length).toBe(4);
  expect(chatSelection.map(r=>r.asset_id)).toEqual(['v','i','upload1','upload2']);
});
