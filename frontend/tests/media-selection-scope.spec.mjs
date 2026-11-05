import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';
test('selection toggle retains hidden items and can deselect a filtered collection',async({page})=>{
  await page.route('**/api/**',route=>{
    const url=new URL(route.request().url());
    let value=null;
    if(url.pathname==='/api/director/settings')return route.fulfill({status:503,json:{error:{message:'Models mocked offline'}}});
    if(url.pathname==='/api/story/workspaces')value={items:[{workspace_id:'ws-test',title:'Test'}],total:1};
    else if(url.pathname==='/api/audio/utilities/capabilities')value={operations:[{id:'extract_mp3',status:'available'}]};
    else if(url.pathname.endsWith('/utilities/jobs'))value=[];
    else if(url.pathname==='/api/media/ws-test/assets'){
      const assets=['alpha','beta'].map((name,i)=>({asset_id:`pa-${i}`,workspace_id:'ws-test',kind:'audio',roles:['project_audio'],filename:name+'.wav',content_url:'/fixture',created_at:'2026-10-27'}));
      value={assets:url.searchParams.get('kind')==='audio'?assets:[],total:url.searchParams.get('kind')==='audio'?2:0};
    }
    return route.fulfill(value===null?{status:503,json:{error:{message:'Not used in this test'}}}:{json:value});
  });
  await mockProject(page,'ws-test'); await page.goto('/#/media-prep?tool=utilities');
  await expect(page.getByRole('heading',{name:'Audio Utilities',exact:true})).toBeVisible();

  await page.getByRole('button',{name:'Select all shown (2)',exact:true}).click();
  await expect(page.getByRole('button',{name:'Deselect all shown (2)',exact:true})).toBeVisible();
  const search=page.getByRole('searchbox',{name:'Search filenames, descriptions or tags'});
  await search.fill('alpha');
  await page.getByRole('button',{name:'Deselect all shown (1)',exact:true}).click();
  await search.fill('');
  await expect(page.getByText('1 selected',{exact:true})).toBeVisible();
  await expect(page.getByRole('checkbox',{name:/^Select (alpha|beta)\.wav$/}).nth(0)).not.toBeChecked();
  await expect(page.getByRole('checkbox',{name:/^Select (alpha|beta)\.wav$/}).nth(1)).toBeChecked();
});
