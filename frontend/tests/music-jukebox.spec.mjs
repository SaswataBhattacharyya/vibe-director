import {mockProject} from './fixtures/project.mjs';
import {test,expect} from '@playwright/test';
test('offline music graph renders instruments, preserves split ranges and roundtrips MIDI',async({page})=>{
 await mockProject(page); await page.goto('/');
 const result=await page.evaluate(async()=>{
  const e=await import('/src/lib/jukebox-engine.ts');
  const p=e.fresh();p.bars=1;p.master=-6;p.tracks=e.houseBeat(p);
  const synth=e.track('synth','Melody');synth.notes=[{id:'n',beat:0,length:1,midi:60,velocity:.5}];p.tracks.push(synth);
  const b=await e.renderMusic(p),bytes=await e.wav(b).arrayBuffer();
  const again=await e.renderMusic(p);let peak=0,diff=0;const d=b.getChannelData(0),d2=again.getChannelData(0);for(let i=0;i<d.length;i++){peak=Math.max(peak,Math.abs(d[i]));diff=Math.max(diff,Math.abs(d[i]-d2[i]));}
  const clip={id:'clip',source:'a',at:2,start:1,end:5,reverse:true};const split=e.splitClip(clip,3,1);
  const imported=e.midiImport(await e.midiExport(p).arrayBuffer());
  return {duration:b.duration,peak,diff,wav:bytes.byteLength,split,notes:imported.tracks.reduce((v,t)=>v+t.notes.length,0)};
 });
 expect(result.duration).toBeCloseTo(2,2);expect(result.peak).toBeGreaterThan(.02);expect(result.peak).toBeLessThan(1);expect(result.diff).toBeLessThan(.001);expect(result.wav).toBe(44+88200*4);
 expect(result.split.map(c=>[c.at,c.start,c.end])).toEqual([[2,4,5],[3,1,4]]);expect(result.notes).toBe(15);
});
test('music project UI composes, saves, recovers and previews without generation',async({page})=>{
 let saved;let saves=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async r=>{const path=new URL(r.request().url()).pathname;
  if(path==='/api/studio-tools/output-destination')return r.fulfill({json:{mode:'default',path:'/tmp/music',available:true}});
  if(path==='/api/jukebox/state')return r.fulfill({json:{projects:saved?[saved]:[],output:'/tmp/music'}});
  if(path==='/api/jukebox/projects'){saved={...r.request().postDataJSON().project,id:'jukebox-123456789abc',revision:1};return r.fulfill({json:saved});}
  if(path.endsWith('/save')&&path.includes('/jukebox/')){saved={...r.request().postDataJSON().project,revision:++saves+1};return r.fulfill({json:saved});}
  if(path.endsWith('/jobs')&&path.includes('/jukebox/'))return r.fulfill({json:{jobs:[]}});
  if(path==='/api/jukebox/projects/jukebox-123456789abc')return r.fulfill({json:saved});
  if(path==='/api/story/workspaces')return r.fulfill({json:{items:[]}});
  if(path==='/api/director/settings')return r.fulfill({json:{settings:{provider:'codex',model:'test',lessons:[]},models:[]}});
  if(path.includes('/workspace'))return r.fulfill({json:{}});
  return r.fulfill({status:404,json:{error:'Not mocked'}});
 });
 await mockProject(page); await page.goto('/#/media-prep?tool=music');await page.getByRole('button',{name:'Music Jukebox',exact:true}).click();
 await page.getByLabel('Session name',{exact:true}).fill('First beat');await page.getByRole('button',{name:'New music session',exact:true}).click();
 await page.getByRole('button',{name:'Compose & Beats',exact:true}).click();await page.getByRole('button',{name:'Add house drum pattern',exact:true}).click();
 await page.getByRole('button',{name:'Save music session',exact:true}).click();await expect.poll(()=>saved?.tracks.length).toBe(3);
 await page.getByRole('button',{name:'Prepare rendered preview',exact:true}).click();await expect(page.locator('audio[src^="blob:"]')).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);
 await page.getByRole('button',{name:'DJ Mix',exact:true}).click();await expect(page.getByRole('combobox',{name:'Track A',exact:true})).toBeVisible();
 await page.screenshot({path:'/tmp/music-jukebox-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'Compose & Beats',exact:true}).click();await page.getByRole('button',{name:'Add synth',exact:true}).click();
 await expect(page.getByRole('group',{name:'Piano roll grid'})).toBeVisible();
 await page.getByRole('button',{name:'Note 60 step 1',exact:true}).click();
 await page.reload();await page.getByRole('button',{name:'Music Jukebox',exact:true}).click();await expect(page.getByText('Recovered an unsaved browser draft. Save to keep it.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Save music session',exact:true}).click();await expect.poll(()=>saved?.tracks.length).toBe(4);expect(saved.tracks[3].notes).toHaveLength(1);
 await page.setViewportSize({width:760,height:1000});await page.screenshot({path:'/tmp/music-jukebox-narrow.png',fullPage:true});expect(errors).toEqual([]);
});
test('audio edits, stretch and captured DJ loops render with bounded timing',async({page})=>{
 await mockProject(page); await page.goto('/');
 const result=await page.evaluate(async()=>{
  const e=await import('/src/lib/jukebox-engine.ts');
  const ctx=new AudioContext({sampleRate:44100}),src=ctx.createBuffer(2,44100*3,44100);
  for(let c=0;c<2;c++)for(let i=0;i<src.length;i++)src.getChannelData(c)[i]=.2*Math.sin(i/44100*2*Math.PI*440);
  const url=URL.createObjectURL(e.wav(src));const source={id:'s',workspace_id:'test',asset_id:'test',url,name:'sine',duration:3};
  const p=e.fresh();p.bars=1;p.master=0;p.limiter=false;p.sources=[source];
  const t=e.track('audio','Sine');t.gain=0;t.clips=[{id:'c',source:'s',at:.25,start:.5,end:1.5}];p.tracks=[t];
  const original=await e.renderMusic(p);
  const split=await e.renderMusic({...p,tracks:[{...t,clips:e.splitClip(t.clips[0],.75)}]});
  let splitDiff=0;for(let i=0;i<original.length;i++)splitDiff=Math.max(splitDiff,Math.abs(original.getChannelData(0)[i]-split.getChannelData(0)[i]));
  const rms=(b,a,z)=>{const d=b.getChannelData(0);let sum=0;for(let i=Math.ceil(a*44100);i<Math.floor(z*44100);i++)sum+=d[i]*d[i];return Math.sqrt(sum/((z-a)*44100));};
  const raised=await e.renderMusic({...p,tracks:[{...t,gain:6}]});
  const stretched=await e.renderMusic({...p,tracks:[{...t,rate:2}]});
  const dj=await e.renderMusic({...p,mode:'dj',dj:{cross:-1,events:[{type:'play',deck:'A',time:0,source:'s',offset:0,rate:1,loop:1},{type:'stop',deck:'A',time:1.5}]}});
  URL.revokeObjectURL(url);e.forgetBuffers();await ctx.close();
  return {splitDiff,ratio:rms(raised,.3,1)/rms(original,.3,1),before:rms(original,0,.2),after:rms(original,1.3,1.9),stretch:rms(stretched,.35,.55),stretchEnd:rms(stretched,1,1.5),djLoop:rms(dj,.7,1.4),djEnd:rms(dj,1.6,1.9)};
 });
 expect(result.splitDiff).toBeLessThan(.0001);expect(result.ratio).toBeCloseTo(1.995,2);expect(result.before).toBeLessThan(.0001);expect(result.after).toBeLessThan(.0001);
 expect(result.stretch).toBeGreaterThan(.02);expect(result.stretchEnd).toBeLessThan(.001);expect(result.djLoop).toBeGreaterThan(.02);expect(result.djEnd).toBeLessThan(.001);
});
