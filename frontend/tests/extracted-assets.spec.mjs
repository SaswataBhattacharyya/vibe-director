import assert from 'node:assert/strict';
import {test} from '@playwright/test';
test('extracted clips separated from completed sources and individually deleted',async({page})=>{
 const base={workspace_id:'ws-test',roles:[],media_type:'video/mp4',sha256:'a'.repeat(64),size_bytes:32,created_at:'2026-10-14T00:00:00Z',content_url:'/missing.mp4'};
 const source={...base,asset_id:'source',kind:'video',filename:'original.mp4'};
 const clip={...base,asset_id:'cut',kind:'video',filename:'cut.mp4',metadata:{analyzer_run_id:'run-a',analysis_summary:'A man reacts to childhood scenes.'}};
 const audio={...base,asset_id:'audio',kind:'audio',filename:'short.wav',content_url:'/missing.wav',media:{duration_seconds:.4},metadata:{analyzer_run_id:'run-a'}};
 const image={...base,asset_id:'frame',kind:'image',filename:'frame.png',content_url:'/missing.png',metadata:{analyzer_run_id:'run-a'}};
 const job={job_id:'analysis-a',status:'completed',progress:100,stage:'completed',message:'Complete',request:{workspace_id:'ws-test',source_asset_ids:['source']},events:[],result:{published_assets:[clip,audio,image],audio_analysis:[],videos:[]}};
 let deleted=false;let imageDeleted=false;
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url());let body={};
  if(url.pathname==='/api/story/workspaces')body={items:[{workspace_id:'ws-test',title:'Test'}]};
  else if(url.pathname.includes('/capabilities'))body={can_analyze:true,reason:'Ready',checks:{},gpu_admission:{checked:true,available:true}};
  else if(url.pathname.endsWith('/analysis/jobs'))body=[job];
  else if(url.pathname==='/api/media/ws-test/assets/audio'&&route.request().method()==='DELETE'){deleted=true;body={deleted:true};}
  else if(url.pathname==='/api/media/ws-test/assets/frame'&&route.request().method()==='DELETE'){imageDeleted=true;body={deleted:true};}
  else if(url.pathname==='/api/media/ws-test/assets') {const kind=url.searchParams.get('kind');const assets=kind==='video'?[source,clip]:kind==='audio'&&!deleted?[audio]:kind==='image'&&!imageDeleted?[image]:[];body={assets,total:assets.length};}
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto('/#/media-prep?tool=video');
 await page.getByText('original.mp4',{exact:true}).waitFor();
 assert.equal(await page.getByText('cut.mp4',{exact:true}).count(),0);
 assert.equal(await page.getByRole('checkbox',{name:'Analyzed — see Results'}).isDisabled(),true);
 await page.getByRole('button',{name:'Analyze',exact:true}).click();
 await page.getByText('No new source videos.',{exact:false}).waitFor();
 assert.equal(await page.getByRole('checkbox',{name:'original.mp4'}).count(),0);
 await page.getByRole('button',{name:'Video Assets',exact:true}).click();
 await page.getByText('A man reacts to childhood scenes.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Delete extracted clip cut.mp4'}).waitFor();
 await page.getByRole('button',{name:'Audio Assets',exact:true}).click();
 await page.getByText('0.40 seconds',{exact:true}).waitFor();
 page.once('dialog',dialog=>dialog.accept());
 await page.getByRole('button',{name:'Delete extracted clip short.wav'}).click();
 await page.getByText('Extracted clip deleted. Original video retained.',{exact:true}).waitFor();
 assert.equal(deleted,true);
 await page.getByRole('button',{name:'Image Assets',exact:true}).click();
 await page.getByText('frame.png',{exact:true}).waitFor();
 page.once('dialog',dialog=>dialog.accept());
 await page.getByRole('button',{name:'Delete extracted image frame.png'}).click();
 await page.getByText('Extracted image deleted. Original video retained.',{exact:true}).waitFor();
 assert.equal(imageDeleted,true);
 await page.getByRole('button',{name:'Results',exact:true}).click();
 await page.getByText('cut.mp4',{exact:true}).waitFor();
 assert.equal(await page.getByText('short.wav',{exact:true}).count(),0);
 await page.getByRole('button',{name:'Library',exact:true}).click();
 await page.getByText('original.mp4',{exact:true}).waitFor();
});

test('three reference sections filter extracted and imported sources',async({page})=>{
 const make=(id,kind,roles,extra={})=>({asset_id:id,workspace_id:'ws-test',kind,roles,filename:id,media_type:kind+'/test',sha256:'a'.repeat(64),size_bytes:1,created_at:'2026-10-14',content_url:'/missing',...extra});
 const assets=[make('character.png','image',['character_master']),make('world.png','image',['world_master']),make('first.png','image',['first_frame']),make('last.png','image',['last_frame']),make('extracted.png','image',[],{metadata:{analyzer_run_id:'run-a'}}),make('download.png','image',['project_image'],{origin:'imported'}),make('voice.wav','audio',['voice_master']),make('extracted.wav','audio',[],{metadata:{analyzer_run_id:'run-a'}}),make('download.wav','audio',['project_audio'],{origin:'imported'}),make('extracted.mp4','video',[],{metadata:{analyzer_run_id:'run-a'}}),make('download.mp4','video',['project_video'],{origin:'imported'})];
 await page.addInitScript(()=>localStorage.setItem('vibe-video-draft-v1',JSON.stringify({workspaceId:'ws-test',clipId:'test',prompt:'',duration:6,resolution:.98,workflowId:'minimax_h3_r2v_dynamic_v1'})));
 await page.route('**/api/**',async route=>{
 const url=new URL(route.request().url());let body={};
 if(url.pathname==='/api/media/ws-test/assets'){const rows=assets.filter(a=>a.kind===url.searchParams.get('kind'));body={assets:rows,total:rows.length};}
 if(url.pathname.endsWith('/seo-styles'))body={styles:[]};
 await route.fulfill({json:body});
 });
 await page.goto('/#/video');
 await page.getByLabel('Images reference source',{exact:true}).waitFor();
 assert.equal(await page.locator('.r2v-kind').count(),3);
 for(const [group,key,filename] of [['Images','characters','character.png'],['Images','worlds','world.png'],['Images','first-frames','first.png'],['Images','last-frames','last.png'],['Images','image-assets','extracted.png'],['Images','imported-images','download.png'],['Audio','voices','voice.wav'],['Audio','audio-clips','extracted.wav'],['Audio','imported-audio','download.wav'],['Videos','video-clips','extracted.mp4'],['Videos','source-videos','download.mp4']]){
 await page.getByLabel(group+' reference source',{exact:true}).selectOption(key);
 const section=page.locator('.r2v-kind').filter({has:page.getByLabel(group+' reference source',{exact:true})});
 await section.getByText(filename,{exact:true}).waitFor();
 assert.equal(await section.locator('.r2v-asset-card').count(),1);
 }
});

for(const [kind,tab] of [['video','Video Assets'],['audio','Audio Assets'],['image','Image Assets']]){
 test(`${tab} selects and deletes batches and removes them from Results`,async({page})=>{
  const base={workspace_id:'ws-test',roles:[],media_type:kind+'/test',sha256:'a'.repeat(64),size_bytes:1,created_at:'2026-10-14',content_url:'/missing',metadata:{analyzer_run_id:'run-a'}};
  const first={...base,asset_id:'first',kind,filename:'first.'+kind};
  const second={...base,asset_id:'second',kind,filename:'second.'+kind};
  const sibling={...base,asset_id:'sibling',kind:kind==='audio'?'image':'audio',filename:'keep-sibling'};
  const source={...base,asset_id:'source',kind:'video',filename:'original.mp4',metadata:{}};
  const initial=[first,second,sibling,source];const deleted=new Set();let rejectOnce=kind==='image';
  const job={job_id:'analysis-a',status:'completed',progress:100,stage:'completed',message:'Complete',request:{workspace_id:'ws-test',source_asset_ids:['source']},events:[],result:{published_assets:[first,second,sibling],audio_analysis:[],videos:[]}};
  await page.route('**/api/**',async route=>{
   const url=new URL(route.request().url());let body={};
   if(url.pathname==='/api/story/workspaces')body={items:[{workspace_id:'ws-test',title:'Test'}]};
   else if(url.pathname.endsWith('/analysis/jobs'))body=[job];
   else if(route.request().method()==='DELETE'){if(rejectOnce){rejectOnce=false;return route.fulfill({status:409,json:{error:{message:'Simulated file failure'}}});}deleted.add(url.pathname.split('/').pop());body={deleted:true};}
   else if(url.pathname==='/api/media/ws-test/assets'){const rows=initial.filter(a=>!deleted.has(a.asset_id)&&a.kind===url.searchParams.get('kind'));body={assets:rows,total:rows.length};}
   await route.fulfill({json:body});
  });
  await page.goto('/#/media-prep?tool=video');
  await page.getByRole('button',{name:tab,exact:true}).click();
  await page.getByRole('button',{name:'Select all shown (2)',exact:true}).click();
  assert.equal(await page.getByRole('checkbox',{checked:true}).count(),2);
  await page.getByRole('button',{name:'Clear selection',exact:true}).click();
  await page.getByRole('checkbox',{name:`Select ${first.filename}`,exact:true}).check();
  page.once('dialog',dialog=>dialog.dismiss());
  await page.getByRole('button',{name:'Delete selected (1)',exact:true}).click();
  assert.equal(deleted.size,0);
  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Delete selected (1)',exact:true}).click();
  if(kind==='image'){
   await page.getByText('0 extracted asset(s) deleted. Original source files retained. 1 could not be deleted:',{exact:false}).waitFor();
   assert.equal(await page.getByRole('checkbox',{name:`Select ${first.filename}`,exact:true}).isChecked(),true);
   assert.equal(deleted.size,0);
   page.once('dialog',dialog=>dialog.accept());
   await page.getByRole('button',{name:'Delete selected (1)',exact:true}).click();
  }
  await page.getByText('1 extracted asset(s) deleted. Original source files retained.',{exact:true}).waitFor();
  assert.equal(await page.getByText(first.filename,{exact:true}).count(),0);
  await page.getByLabel('Search extracted assets',{exact:true}).fill('nothing-matches');
  page.once('dialog',dialog=>{assert.match(dialog.message(),/includes items hidden by the search filter/);return dialog.accept();});
  await page.getByRole('button',{name:`Delete all ${kind} assets (1)`,exact:true}).click();
  await page.getByRole('button',{name:`Delete all ${kind} assets (0)`,exact:true}).waitFor();
  assert.deepEqual([...deleted],['first','second']);
  await page.getByRole('button',{name:'Results',exact:true}).click();
  await page.getByText('keep-sibling',{exact:true}).waitFor();
  assert.equal(await page.getByText(first.filename,{exact:true}).count(),0);
  assert.equal(await page.getByText(second.filename,{exact:true}).count(),0);
  await page.getByRole('button',{name:'Library',exact:true}).click();
  await page.getByLabel('Search source videos',{exact:true}).fill('');
  await page.getByText('original.mp4',{exact:true}).waitFor();
 });
}
