// Real native GUIs + isolated storyboard -> Studio -> approved CPU render. No owner media/providers.
import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import {createInterface} from 'node:readline';
import {fileURLToPath} from 'node:url';
import {chromium,expect} from '@playwright/test';
const repository=fileURLToPath(new URL('../../',import.meta.url));
const code=`import json,sys,subprocess
from pathlib import Path
from unittest.mock import patch
from story_builder.tests.test_native_interfaces import NativeInterfacesTests
from story_builder.isolated_server import create_app
from story_builder.services import editor_studio,production_board,interface_sessions,media_library,vibe_editor,video_repertoire,vibe_editor_render
f=NativeInterfacesTests();f.setUp()
try:
 create_app(data_root=f.root)
 source=f.root/'native-source.mp4'
 subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x180:d=5','-f','lavfi','-i','sine=frequency=440:duration=5','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True)
 video=media_library.register_upload(f.root,f.w,filename='native-source.mp4',content=source.read_bytes(),role='project_video')
 body=f.saved['body'];body['shots']['1.1'].update(presentation='video',route='t2v',control='manual',duration=5,media_asset_id=video['asset_id'])
 saved=f.save(body)
 p=f.board.editor_handoff(f.w,f.r)
 with vibe_editor.state(f.root) as data: vibe_editor.project(data,p['id'])['brief']={'summary':'Synthetic native workflow','questions':[]}
 plan={'width':320,'height':180,'fps':24,'audio':None,'clips':[{**p['selection'][0],'caption':'Native original'}], 'layers':[{'id':'title','kind':'text','duration':3,'text':'Layer title','x':10,'y':10,'width':100,'height':30,'font_size':16,'motion':[{'time':0,'opacity':0},{'time':1,'opacity':1}]}]}
 studio=editor_studio.open_workspace(f.root,p['id'],{'revision':p['revision'],'plan':plan})
 board=production_board.open_workspace(f.board,f.w,f.r,{'expected_revision':saved['revision']})
 print(json.dumps({'studio':studio,'backlot':board,'root':str(f.root)}),flush=True)
 for line in sys.stdin:
  command=json.loads(line)
  if command['action']=='backlot_proposal':
   value=production_board.operate(f.board,f.w,f.r,{'token':board['token'],'action':'proposal'})
   assert value['body']['shots']['1.1']['notes']=='Reviewed native note'
   assert f.board.get(f.w,f.r)['body']['shots']['1.1']['notes']!='Reviewed native note'
   print(json.dumps({'proposal':True}),flush=True)
  elif command['action']=='import':
   p=editor_studio.operate(f.root,p['id'],{'token':studio['token'],'action':'import'})
   assert p['pending']['value']['clips'][0]['caption']=='Native synchronized caption'
   assert p['pending']['value']['clips'][0]['end']<4.9
   assert p['pending']['value']['layers'][0]['text']=='Reviewed layer title'
   assert p['pending']['value']['layers'][0]['motion'][1]['opacity']==1
   assert not p.get('job_id')
   print(json.dumps({'proposal':p['pending']}),flush=True)
  elif command['action']=='sync':
   body=f.board.get(f.w,f.r)['body'];body['shots']['1.1']['prompt']='Live synchronized scene'
   f.save(body);result=production_board.operate(f.board,f.w,f.r,{'token':board['token'],'action':'sync'})
   print(json.dumps(result),flush=True)
  elif command['action']=='render':
   with patch.object(video_repertoire,'start_job',side_effect=lambda kind,ident:video_repertoire.read_job(kind,ident)):
    vibe_editor.command(f.root,p['id'],{'action':'approve','revision':p['revision']})
   p=next(x for x in vibe_editor.snapshot(f.root)['projects'] if x['id']==p['id'])
   job=video_repertoire.read_job('vibe-editor',p['job_id'])
   result=vibe_editor_render.render(f.root,p['job_id'],job['request'],lambda *_:None)
   asset=result['asset'];assert asset['media']['streams']==['audio','video']
   assert abs(asset['media']['duration_seconds']-job['request']['plan']['clips'][0]['render_duration'])<.15
   output=media_library.asset_path(f.root,f.w,asset['asset_id'])[0]
   decode=subprocess.run(['ffmpeg','-v','error','-threads','1','-filter_threads','1','-ss','0.2','-i',str(output),'-frames:v','1','-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True)
   assert decode.returncode==0,decode.stderr.decode()
   decoded=decode.stdout
   assert len(decoded)==3 and decoded[2]>180
   published=production_board.operate(f.board,f.w,f.r,{'token':board['token'],'action':'sync'})
   assert published['final_film']['asset_id']==asset['asset_id']
   assert published['final_film']['storyboard_revision']<published['final_film']['current_storyboard_revision']
   print(json.dumps({'render':asset['media'],'published':published['final_film']}),flush=True)
  elif command['action']=='close': break
finally:
 interface_sessions._shutdown()
 f.doCleanups()
 assert not Path(f.temp.name).exists()
 print(json.dumps({'cleanup':True}),flush=True)
`;
const child=spawn('conda',['run','--no-capture-output','-n','react','python','-u','-c',code],{cwd:repository+'/backend',stdio:['pipe','pipe','pipe']});
let browser,host,stderr='',pending=[],lines=[];
child.stderr.on('data',chunk=>stderr+=chunk);
createInterface({input:child.stdout}).on('line',line=>{try{const value=JSON.parse(line);const resolve=pending.shift();if(resolve)resolve(value);else lines.push(value);}catch{console.log('FIXTURE',line);}});
const exited=new Promise(resolve=>child.on('exit',code=>resolve(code)));
const next=()=>Promise.race([lines.length?Promise.resolve(lines.shift()):new Promise(resolve=>pending.push(resolve)),exited.then(code=>{throw Error(`Fixture exited ${code}: ${stderr}`);}),new Promise((_,reject)=>{const timer=setTimeout(()=>reject(Error(`Fixture timed out: ${stderr}`)),120000);timer.unref();})]);
const command=async action=>{child.stdin.write(JSON.stringify({action})+'\n');return next();};
let cleanup;
try{
 const fixture=await next();if(!fixture.studio)throw Error(JSON.stringify(fixture));
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium-browser'});
 const context=await browser.newContext({viewport:{width:1500,height:1000}});
 const board=await context.newPage();await board.goto(fixture.backlot.url);
 await expect(board.frameLocator('iframe[title="Native OpenMontage Backlot"]').getByText('MIRA: Here it is.',{exact:false}).first()).toBeVisible({timeout:20000});
 const stateUrl=new URL('/api/project/production/state',fixture.backlot.url).href;
 const state=await board.evaluate(async url=>(await fetch(url)).json(),stateUrl);
 const visual=state.storyboard.scenes[0].visual;if(!visual?.exists||!visual?.renderable)throw Error('Backlot missing playable owned media');
 // Exercise actual media bytes in the native board's own browser origin.
 await board.evaluate(async path=>{const v=document.createElement('video');v.src='/media/production/'+path;v.muted=true;document.body.append(v);await v.play();await new Promise(r=>setTimeout(r,250));v.pause();if(v.videoWidth!==320||v.currentTime<=0)throw Error('Backlot video did not play');v.remove();},visual.path);
 console.log('BACKLOT: native board and owned H264 playback passed');
 await board.getByLabel('Notes',{exact:true}).fill('Reviewed native note');
 await board.getByRole('button',{name:'Send edits for review in Vibe'}).click();
 await expect(board.getByRole('status')).toContainText('Proposal ready');
 const backlotProposal=await command('backlot_proposal');if(!backlotProposal.proposal)throw Error(JSON.stringify(backlotProposal));
 console.log('BACKLOT: native edit -> reviewed Vibe proposal passed');
 const refresh=board.waitForResponse(async response=>response.url().endsWith('/api/project/production/state')&&response.status()===200&&(await response.json()).storyboard?.scenes?.[0]?.description==='Live synchronized scene',{timeout:20000});
 const synced=await command('sync');if(!synced.revision)throw Error(JSON.stringify(synced));
 await refresh;
 console.log('BACKLOT: saved revision live SSE refresh passed');
 const page=await context.newPage();page.on('pageerror',e=>console.log('STUDIO ERROR',e.message));page.on('response',r=>{if(r.status()>=400)console.log('STUDIO HTTP',r.status(),new URL(r.url()).pathname);});await page.goto(fixture.studio.url);
 await expect(page.getByRole('button',{name:/Caption 0/}).first()).toBeVisible({timeout:20000});
 await expect.poll(async()=>{
  for(const frame of page.frames()){
   try{if(await frame.locator('video').evaluateAll(videos=>videos.some(v=>v.videoWidth===320&&v.readyState>=2)))return true;}catch{}
  }
  return false;
 },{timeout:20000}).toBe(true);
 console.log('STUDIO: native preview decoded the owned H264 source');
 const denied=await page.evaluate(async()=>{
  const projects=await (await fetch('/api/projects')).json(),id=projects.projects[0].id;
  const path=`/api/projects/${id}/files/index.html`,source=await (await fetch(path)).json();
  return {render:(await fetch(`/api/projects/${id}/render`,{method:'POST'})).status,
   source:(await fetch(path,{method:'PUT',headers:{'If-Match':source.version},body:source.content.replace('</body>','<script>alert(1)</script></body>')})).status,
   target:(await fetch(`/api/projects/${id}/file-mutations/patch-element/index.html`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target:{selector:'script'},operations:[{type:'text-content',property:'text',value:'alert(1)'}]})})).status};
 });
 if(Object.values(denied).some(status=>status!==403))throw Error('Studio execution gate failed');
 console.log('STUDIO: executable source changes, script-target patches and direct render blocked');
 await page.getByRole('button',{name:/Caption 0/}).first().click();
 await page.locator('textarea').fill('Native synchronized caption');await page.locator('textarea').blur();
 await page.reload();await page.getByRole('button',{name:/Caption 0/}).first().click();
 await expect(page.locator('textarea')).toHaveValue('Native synchronized caption');
 // Embed both interfaces under localhost, as Vibe does; separate ports must retain authentication.
 host=createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(`<iframe title="Studio" sandbox="allow-scripts allow-same-origin" src="${fixture.studio.url.replace('127.0.0.1','localhost')}"></iframe><iframe title="Backlot" sandbox="allow-scripts allow-same-origin" src="${fixture.backlot.url.replace('127.0.0.1','localhost')}"></iframe>`);});
 await new Promise(resolve=>host.listen(0,'127.0.0.1',resolve));
 const embedded=await context.newPage();await embedded.goto(`http://localhost:${host.address().port}`);
 await expect(embedded.frameLocator('iframe[title="Studio"]').getByRole('button',{name:/Caption 0/}).first()).toBeVisible({timeout:20000});
 await expect(embedded.frameLocator('iframe[title="Backlot"]').frameLocator('iframe[title="Native OpenMontage Backlot"]').getByText('MIRA: Here it is.',{exact:false}).first()).toBeVisible();
 await embedded.close();
 console.log('EMBED: simultaneous localhost Studio and Backlot authentication passed');
 const history=await page.evaluate(async()=>{
  const projects=await (await fetch('/api/projects')).json(),id=projects.projects[0].id,base=`/api/projects/${id}`;
  const post=async(path,body)=>{const r=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw Error(path+': '+r.status);return r.json();};
  await post('/history/checkpoint',{});
  const path=base+'/files/index.html',before=await(await fetch(path)).json();
  const after=before.content.replace('>Layer title</div>','>Reviewed layer title</div>');
  const written=await fetch(path,{method:'PUT',headers:{'If-Match':before.version},body:after});if(!written.ok)throw Error('Layer write '+written.status);
  await post('/history/claim',{paths:['index.html'],label:'Review layer',overwrote:{'index.html':before.version}});
  await post('/history/step',{direction:'back'});
  const undone=await(await fetch(path)).json();if(!undone.content.includes('>Layer title</div>'))throw Error('Native undo lost layer title');
  await post('/history/step',{direction:'forward'});
  const redone=await(await fetch(path)).json();if(!redone.content.includes('>Reviewed layer title</div>'))throw Error('Native redo lost layer title');
  return true;
 });
 if(!history)throw Error('Native history not verified');
 console.log('STUDIO: typed layer edit and native undo/redo passed');
 await page.getByRole('button',{name:/Clip 0, 0.0 to 5.0 seconds/}).first().click();
 const clip=page.getByRole('button',{name:'Clip 0, 0.0 to 5.0 seconds',exact:true});
 const bounds=await clip.boundingBox();if(!bounds)throw Error('Studio timeline clip unavailable');
 await page.mouse.move(bounds.x+bounds.width-2,bounds.y+bounds.height/2);await page.mouse.down();
 await page.mouse.move(bounds.x+bounds.width*.7,bounds.y+bounds.height/2,{steps:12});await page.mouse.up();
 await page.waitForTimeout(700);
 const proposal=await command('import');if(proposal.proposal?.value?.clips?.[0]?.caption!=='Native synchronized caption')throw Error(JSON.stringify(proposal));
 console.log('STUDIO: native caption edit, reload, trim and Vibe proposal import passed',proposal.proposal.value.clips[0].end);
 const rendered=await command('render');if(!rendered.render)throw Error(JSON.stringify(rendered));
 const publishedState=await board.evaluate(async url=>(await fetch(url)).json(),stateUrl);
 if(!publishedState.media.renders.some(item=>item.path===rendered.published.path))throw Error('Published film absent from native Backlot');
 await board.evaluate(async path=>{const video=document.createElement('video');video.src='/media/production/'+path;video.muted=true;document.body.append(video);try{await video.play();await new Promise(r=>setTimeout(r,250));if(video.videoWidth!==320||video.currentTime<=0)throw Error('Published film did not play in Backlot');}finally{video.pause();video.remove();}},rendered.published.path);
 console.log('BACKLOT: verified final Editor film discovered and played');
 console.log('WORKFLOW: saved storyboard -> Backlot playback -> Studio edit -> Vibe proposal -> approved CPU render passed',rendered.render);
 cleanup=await command('close');if(!cleanup.cleanup)throw Error(JSON.stringify(cleanup));
}finally{
 try{await browser?.close();}finally{
  if(host)await new Promise(resolve=>host.close(resolve));
  if(!cleanup){child.stdin.end();const code=await exited;if(code!==0)console.error(stderr);}
  else await exited;
 }
}
console.log('CLEANUP VERIFIED: fixture projects, databases, staged media and native processes removed');
