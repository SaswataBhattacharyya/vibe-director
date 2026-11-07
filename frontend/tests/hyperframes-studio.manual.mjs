import {mkdtemp,writeFile,readFile,rm,cp,mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn,spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createServer} from 'node:net';
import {chromium} from '@playwright/test';

// Optional local compatibility probe, not an application Studio integration.
// Run from the repository: node frontend/tests/hyperframes-studio.manual.mjs
const repository=fileURLToPath(new URL('../../',import.meta.url)).replace(/\/$/,'');
const reservation=createServer();
await new Promise(resolve=>reservation.listen(0,'127.0.0.1',resolve));
const port=reservation.address().port;
await new Promise(resolve=>reservation.close(resolve));
const root=await mkdtemp(join(tmpdir(),'vibe-hf-spike-'));
let server,browser;
try {
 const video=join(root,'clip.mp4');
 const ff=spawnSync('ffmpeg',['-v','error','-f','lavfi','-i','color=c=blue:s=320x180:d=2','-c:v','libx264','-pix_fmt','yuv420p',video],{timeout:30000});
 if(ff.status!==0)throw Error(ff.stderr.toString());
 const wav=join(root,'tone.wav');
 const tone=spawnSync('ffmpeg',['-v','error','-f','lavfi','-i','sine=frequency=440:duration=2',wav],{timeout:30000});
 if(tone.status!==0)throw Error(tone.stderr.toString());
 const registration=spawnSync('conda',['run','-n','react','python','-c',`from pathlib import Path; import json; from story_builder.isolated_server import create_app; from story_builder.services import media_library; root=Path(${JSON.stringify(root+'/runtime')}); create_app(data_root=root); a=media_library.register_upload(root,'tool-library',filename='clip.mp4',content=Path(${JSON.stringify(video)}).read_bytes(),role='project_video'); b=media_library.register_upload(root,'tool-library',filename='tone.wav',content=Path(${JSON.stringify(wav)}).read_bytes(),role='project_audio'); print(json.dumps({'asset_id':a['asset_id'],'sha256':a['sha256'],'path':str(media_library.asset_path(root,'tool-library',a['asset_id'])[0]),'audio_id':b['asset_id'],'audio_path':str(media_library.asset_path(root,'tool-library',b['asset_id'])[0])}))`],{cwd:repository+'/backend',timeout:60000});
 if(registration.status!==0)throw Error(registration.stderr.toString());
 console.log('Registered disposable source:',registration.stdout.toString().trim());
 const registered=JSON.parse(registration.stdout.toString().trim());
 await mkdir(join(root,'assets'));await cp(registered.path,join(root,'assets','owned.mp4'));await cp(registered.audio_path,join(root,'assets','owned.wav'));
 await cp(repository+'/local_data/runtimes/editor/node_modules/hyperframes/dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js',join(root,'gsap.js'));
 const html=`<!doctype html><html><body style="margin:0;width:100%;height:100%;overflow:hidden"><div id="main" data-composition-id="main" data-width="320" data-height="180" data-duration="2" data-start="0" style="position:absolute;inset:0"><video id="test-clip" class="clip" data-start="0" data-duration="2" data-track-index="0" data-media-start="0" src="assets/owned.mp4" muted playsinline style="position:absolute;inset:0;width:100%;height:100%"></video><audio id="test-audio" class="clip" data-start="0" data-duration="2" data-track-index="2" src="assets/owned.wav"></audio><div id="test-title" class="clip" data-start="0" data-duration="2" data-track-index="1" style="position:absolute;top:20px;color:white">Compatibility test</div></div><script src="gsap.js"></script><script>window.__timelines={main:gsap.timeline({paused:true}).to({}, {duration:2})};</script></body></html>`;
 await writeFile(join(root,'index.html'),html);
 server=spawn('node',[repository+'/local_data/runtimes/editor/node_modules/hyperframes/bin/hyperframes.mjs','preview',root,'--port',String(port),'--foreground','--no-open'],{env:{...process.env,DO_NOT_TRACK:'1'},stdio:['ignore','pipe','pipe']});
 let logs=''; server.stdout.on('data',s=>logs+=s);server.stderr.on('data',s=>logs+=s);
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium-browser'});
 const page=await browser.newPage();
 for(let i=0;i<40;i++){try{await page.goto(`http://127.0.0.1:${port}`);break;}catch{await new Promise(r=>setTimeout(r,250));}}
 await page.waitForTimeout(2500);
 console.log('SERVER',logs.slice(-1400));
 if(!(await page.locator('body').innerText()).includes(root.split('/').pop()))throw Error('Unexpected Studio project; refusing to edit');
 await page.getByRole('button',{name:/Test Title/}).click();
 await page.waitForTimeout(600);
 await page.locator('textarea').fill('Compatibility saved');
 await page.locator('textarea').blur();
 for(let i=0;i<30;i++){if((await readFile(join(root,'index.html'),'utf8')).includes('Compatibility saved'))break;await new Promise(r=>setTimeout(r,200));}
 if(!(await readFile(join(root,'index.html'),'utf8')).includes('Compatibility saved'))throw Error('Studio edit not saved');
 await page.reload();await page.getByRole('button',{name:/Test Title/}).click();
 if(await page.locator('textarea').inputValue()!=='Compatibility saved')throw Error('Studio edit not restored');
 console.log('STUDIO EDIT AND RELOAD VERIFIED');
 await page.getByRole('button',{name:/Test Clip/}).click();
 const clip=page.getByRole('button',{name:'Test Clip, 0.0 to 2.0 seconds',exact:true});
 const bounds=await clip.boundingBox();
 if(!bounds)throw Error('Timeline clip unavailable');
 await page.mouse.move(bounds.x+bounds.width-2,bounds.y+bounds.height/2);
 await page.mouse.down();await page.mouse.move(bounds.x+bounds.width*.7,bounds.y+bounds.height/2,{steps:12});await page.mouse.up();
 const savedDuration=async()=>Number((await readFile(join(root,'index.html'),'utf8')).match(/id="test-clip"[^>]*data-duration="([^"]+)"/)?.[1]);
 for(let i=0;i<30;i++){if(await savedDuration()<1.99)break;await new Promise(r=>setTimeout(r,200));}
 const trimmed=await savedDuration();
 if(!(trimmed>.1&&trimmed<1.99))throw Error('Timeline trim did not persist');
 await page.reload();await page.getByRole('button',{name:new RegExp(`Test Clip, 0.0 to ${trimmed.toFixed(1)} seconds`)}).waitFor();
 console.log('TIMELINE TRIM AND RELOAD VERIFIED',trimmed);
 for(let i=0;i<10;i++)await page.getByLabel('Seek preview',{exact:true}).press('ArrowRight');
 await page.waitForTimeout(700);
 await page.getByRole('button',{name:'Play',exact:true}).click();
 await page.waitForTimeout(500);
 await page.getByRole('button',{name:'Pause',exact:true}).click();
 const positions=await Promise.all(page.frames().map(f=>f.locator('video').evaluateAll(els=>els.map(e=>e.currentTime))));
 if(!positions.flat().some(time=>time>.3))throw Error('Preview playback did not advance');
 console.log('PLAYBACK VERIFIED');
 console.log('FRAMES',JSON.stringify(await Promise.all(page.frames().map(async frame=>({url:frame.url(),videos:await frame.locator('video').evaluateAll(els=>els.map(e=>({source:e.currentSrc,time:e.currentTime,ready:e.readyState,width:e.videoWidth,error:e.error?.message})))}))),null,2));
 const clips=await Promise.all(page.frames().map(f=>f.locator('video').evaluateAll(els=>els.map(e=>({ready:e.readyState,width:e.videoWidth,error:e.error?.message})))));if(!clips.flat().some(v=>v.ready>=2&&v.width===320&&!v.error))throw Error('Owned H264 preview did not decode');console.log('OWNED H264 PREVIEW VERIFIED');
 const audio=await Promise.all(page.frames().map(f=>f.locator('audio').evaluateAll(els=>els.map(e=>({ready:e.readyState,duration:e.duration,error:e.error?.message})))));
 if(!audio.flat().some(a=>a.ready>=2&&Math.abs(a.duration-2)<.1&&!a.error))throw Error('Owned WAV preview did not decode');
 console.log('OWNED WAV PREVIEW VERIFIED');
 } finally {
 try {
  await browser?.close();
 } finally {
  try {
   if(server&&server.exitCode===null&&server.signalCode===null){
    const stopped=new Promise(resolve=>server.once('exit',resolve));
    server.kill('SIGTERM');
    await Promise.race([stopped,new Promise(resolve=>setTimeout(resolve,2000))]);
    if(server.exitCode===null&&server.signalCode===null){server.kill('SIGKILL');await stopped;}
   }
  } finally {
   await rm(root,{recursive:true,force:true});
   try{await readFile(join(root,'index.html'));throw Error('Cleanup failed');}catch(e){if(e.code!=='ENOENT')throw e;}
   console.log('CLEANUP VERIFIED',root);
  }
 }
}
