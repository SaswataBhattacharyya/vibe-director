// Real installed HyperFrames runtime + synthetic H264; no owner project or provider calls.
import {mkdtemp,rm,readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {chromium} from '@playwright/test';
import {createServer} from 'node:http';
const repository=fileURLToPath(new URL('../../',import.meta.url));
const root=await mkdtemp(join(tmpdir(),'vibe-editor-preview-'));
let browser,server;
try{
 const code=`from pathlib import Path
import json, subprocess
from story_builder.isolated_server import create_app
from story_builder.services import media_library,vibe_editor,editor_preview
root=Path(${JSON.stringify(root)})
create_app(data_root=root)
source=root/'clip.mp4'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x180:d=3','-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-threads','1','-c:a','aac','-pix_fmt','yuv420p','-shortest',str(source)],check=True)
a=media_library.register_upload(root,'tool-library',filename='clip.mp4',content=source.read_bytes(),role='project_video')
p=vibe_editor.add_project(root,{'workspace_id':'tool-library','name':'Disposable preview'})
p=vibe_editor.update_project(root,p['id'],{'selection':[{'asset_id':a['asset_id'],'start':0,'end':3}]})
plan={'width':320,'height':180,'fps':24,'clips':[{'asset_id':a['asset_id'],'start':.25,'end':1.25,'caption':'First'},{'asset_id':a['asset_id'],'start':1.5,'end':2.5,'caption':'Second'}],'audio':None}
r=editor_preview.prepare(root,p['id'],{'revision':p['revision'],'plan':plan})
print(json.dumps({'preview':r,'media_url':a['content_url'],'media_path':str(media_library.asset_path(root,'tool-library',a['asset_id'])[0]),'scripts':{name:str(editor_preview.runtime_file(name)) for name in ['gsap.js','runtime.js','shaders.js']}}))`;
 const fixture=spawnSync('conda',['run','-n','react','python','-c',code],{cwd:join(repository,'backend'),timeout:60000});
 if(fixture.status!==0)throw Error(fixture.stderr.toString());
 const {preview,media_url,media_path,scripts}=JSON.parse(fixture.stdout.toString().trim());
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium-browser'});
 const page=await browser.newPage();
 page.on('pageerror',e=>console.log('PREVIEW ERROR',e.message));
 page.on('console',m=>{if(m.type()==='error')console.log('PREVIEW CONSOLE',m.text().slice(0,300));});
 server=createServer(async(req,res)=>{
  try{
   const path=new URL(req.url,'http://localhost').pathname;
   let body,type;
   if(path==='/'){type='text/html';body='<iframe title="preview" sandbox="allow-scripts" style="width:640px;height:360px;border:0"></iframe>';}
   else if(path===media_url){type='video/mp4';body=await readFile(media_path);}
   else{const name=path.replace('/api/editor/runtime/','');if(!scripts[name]){res.writeHead(404);res.end();return;}
    type='application/javascript';body=await readFile(scripts[name]);}
   const headers={'Content-Type':type,'Content-Length':Buffer.byteLength(body),'Accept-Ranges':'bytes'};
   const range=req.headers.range?.match(/^bytes=(\d+)-(\d*)$/);
   if(range&&Buffer.isBuffer(body)){const start=Number(range[1]),end=range[2]?Math.min(Number(range[2]),body.length-1):body.length-1;
    headers['Content-Range']=`bytes ${start}-${end}/${body.length}`;body=body.subarray(start,end+1);headers['Content-Length']=body.length;
    res.writeHead(206,headers);
   }else res.writeHead(200,headers);
   res.end(body);
  }catch(e){res.writeHead(500);res.end(String(e));}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 await page.goto(`http://127.0.0.1:${server.address().port}/`);
 await page.locator('iframe').evaluate((frame,document)=>frame.srcdoc=document,preview.document);
 const frame=page.frameLocator('iframe');
 await frame.locator('body').waitFor();
 await page.waitForFunction(()=>window.frames[0]&&document.querySelector('iframe'));
 const child=page.frames().find(f=>f.parentFrame());
 await child.waitForFunction(()=>window.__playerReady,null,{timeout:20000});
 const send=async(action,time)=>page.locator('iframe').evaluate((f,d)=>f.contentWindow.postMessage(d,'*'),{type:'vibe-editor-transport',action,time});
 await send('seek',1.4);
 await child.waitForFunction(()=>document.querySelector('#clip-1').readyState>=2&&Math.abs(document.querySelector('#clip-1').currentTime-1.9)<.15,null,{timeout:10000});
 await child.waitForFunction(()=>getComputedStyle(document.querySelector('#caption-1')).visibility!=='hidden');
 await send('play');await page.waitForTimeout(250);await send('pause');await page.waitForTimeout(100);
 const result=await child.evaluate(()=>({time:window.__player.getTime(),playing:window.__player.isPlaying(),width:document.querySelector('#clip-1').videoWidth,caption:document.querySelector('#caption-1').textContent,sourceTime:document.querySelector('#clip-1').currentTime,mediaError:document.querySelector('#clip-1').error?.message}));
 if(result.time<=1.45||result.playing||result.width!==320||result.caption!=='Second'||Math.abs(result.sourceTime-(result.time+.5))>.2||result.mediaError)throw Error(JSON.stringify(result));
 console.log('REAL HYPERFRAMES PREVIEW: playback, pause, source-offset seek and H264 decode verified',result);
 await page.screenshot({path:join(root,'preview.png')});
}finally{
 try{await browser?.close();}finally{
  try{if(server)await new Promise(resolve=>server.close(resolve));}finally{
   await rm(root,{recursive:true,force:true});
   try{await readFile(join(root,'clip.mp4'));throw Error('Cleanup failed');}catch(e){if(e.code!=='ENOENT')throw e;}
   console.log('CLEANUP VERIFIED',root);
  }
 }
}
