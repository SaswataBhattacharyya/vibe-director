import {test,expect} from '@playwright/test';

test('output selection saves a folder and missing-folder recovery verifies before enabling work',async({page})=>{
 let missing=false;const changes=[];
 await page.route('**/api/**',route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  if(path==='/api/story/workspaces')return route.fulfill({json:{items:[],total:0}});
  if(path==='/api/audio/utilities/capabilities')return route.fulfill({json:{operations:[{id:'extract_mp3',status:'available'}]}});
  if(path.endsWith('/utilities/jobs'))return route.fulfill({json:[]});
  if(path.endsWith('/assets'))return route.fulfill({json:{assets:[],total:0}});
  if(path==='/api/studio-tools/output-destination'){
   const body=request.postDataJSON();
   if(body.choice)changes.push(body);
   return route.fulfill({json:body.choice?{...body.choice,path:'/chosen/output'}:missing?{mode:'folder',grant:'old',path:'/missing',available:false}:{mode:'default',path:'/data/audio_studio/output'}});
  }
  if(path==='/api/studio-tools/output-folder')return route.fulfill({json:{path:'/chosen/output',grant:'chosen'}});
  if(path==='/api/studio-tools/output-relink'){changes.push(request.postDataJSON());return route.fulfill({json:{mode:'folder',grant:'old',path:'/chosen/output'}});}
  return route.fulfill({status:503,json:{error:{message:'Not used'}}});
 });
 await page.goto('/#/media-prep?tool=utilities');
 const card=page.locator('.output-destination').filter({has:page.getByLabel('audio-utilities output destination')});
 await expect(card.getByText('/data/audio_studio/output',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Audio utility workspace')).toHaveValue('tool-library');
 await card.getByRole('button',{name:'Choose folder',exact:true}).click();
 await expect(card.getByText('/chosen/output',{exact:true})).toBeVisible();
 expect(changes[0]).toMatchObject({tool:'audio-utilities',workspace_id:'tool-library',choice:{mode:'folder',grant:'chosen'}});
 missing=true;await page.reload();
 await expect(card.getByText('Unavailable: /missing',{exact:true})).toBeVisible();
 await card.getByRole('button',{name:'Choose folder',exact:true}).click();
 await expect(card.getByText('/chosen/output',{exact:true})).toBeVisible();
 expect(changes.at(-1)).toMatchObject({tool:'audio-utilities',workspace_id:'tool-library',grant:'chosen'});
 await expect(card.getByText(/No fallback folder/)).toHaveCount(0);
});
