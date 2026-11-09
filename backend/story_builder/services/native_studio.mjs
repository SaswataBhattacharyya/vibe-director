// Installed Apache-2.0 Studio, behind a deny-by-default local capability gate.
import {createServer} from 'node:http';
import {pathToFileURL} from 'node:url';
import {readFileSync,writeFileSync} from 'node:fs';
import {Readable} from 'node:stream';
const [runtime,projectDir,port,token]=process.argv.slice(2);
const {createStudioServer}=await import(pathToFileURL(`${runtime}/dist/studioServer-HG3RFAOY.js`));
const studio=createStudioServer({projectDir,historyRoot:`${projectDir}/.history`,autoProxy:false});
const {parseSourceDocument,findTargetElement}=await import(pathToFileURL(`${runtime}/dist/studio-api-D76Q4Q2N.js`));
const cookie=`vibe-interface-${token.slice(0,12)}`;
const deny=()=>Response.json({error:'This Studio action is unavailable in Vibe. Save supported edits as a Vibe proposal; render and export in Vibe.'},{status:403});
const timing=['data-start','data-duration','data-media-start','data-track-index'];
const validNumber=value=>value!==null&&String(value).trim()!==''&&Number.isFinite(Number(value))&&Number(value)>=0&&Number(value)<=36000;
function safeRewrite(text,baseline=readFileSync(`${projectDir}/index.html`,'utf8')){
 const before=parseSourceDocument(baseline).document;
 const after=parseSourceDocument(text).document;
 for(const document of [before,after]){
  for(const el of document.querySelectorAll('[id]')){
   if(/^clip-\d+$/.test(el.id)){
    for(const key of timing){if(!validNumber(el.getAttribute(key)))return false;el.removeAttribute(key);}
    if(!['contain','cover'].includes(el.style.objectFit))return false;
    el.style.removeProperty('object-fit');
   }
   if(/^layer-[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(el.id)){
    for(const key of ['data-start','data-duration','data-media-start','data-track-index','data-volume']){
     if(el.hasAttribute(key)){if(!validNumber(el.getAttribute(key)))return false;el.removeAttribute(key);}
    }
    for(const key of ['left','top','width','height','opacity','z-index']){
     const value=el.style.getPropertyValue(key);if(value&&!Number.isFinite(Number(value.replace(/px$/, ''))))return false;
     el.style.removeProperty(key);
    }
    if(el.tagName.toLowerCase()==='div'){if(el.children.length||el.textContent.length>4000)return false;el.textContent='';}
   }
   if(/^caption-\d+$/.test(el.id)){
    if(el.children.length||el.textContent.length>500)return false;
    el.textContent='';
   }
  }
  for(const el of document.querySelectorAll('[data-hf-id]'))el.removeAttribute('data-hf-id');
 }
 // Whole-file writes are accepted only when their DOM differs in supported typed fields.
 return before.documentElement.outerHTML===after.documentElement.outerHTML;
}
function allowed(path,method,body){
 if(path.includes('..')||path.includes('\\'))return false;
 if(method==='POST'&&/^\/api\/projects\/[^/]+\/history\/(checkpoint|step|undo|restore|pin|claim)$/.test(path)){
  if(!body||typeof body!=='object'||Array.isArray(body))return false;
  const action=path.split('/').at(-1),fields={checkpoint:[],step:['direction'],undo:['entryId','mode'],restore:['point'],pin:['entryId','pinned'],claim:['paths','label','coalesceKey','idleMs','overwrote','targets']}[action];
  if(Object.keys(body).some(k=>!fields.includes(k)))return false;
  if(action==='step')return ['back','forward'].includes(body.direction);
  if(action==='claim'){
   if(!Array.isArray(body.paths)||body.paths.length!==1||body.paths[0]!=='index.html'||JSON.stringify(body).length>10000)return false;
   if(body.overwrote&&(typeof body.overwrote!=='object'||Array.isArray(body.overwrote)||Object.keys(body.overwrote).some(p=>p!=='index.html')||Object.values(body.overwrote).some(v=>typeof v!=='string'||v.length>200)))return false;
   if(body.targets&&(!Array.isArray(body.targets)||body.targets.length>100||body.targets.some(t=>!t||t.file!=='index.html')))return false;
   return true;
  }
  if(action==='checkpoint')return true;
  return /^[A-Za-z0-9_:-]{1,160}$/.test(body.entryId||body.point||'');
 }
 if(method==='GET'){
  if(['/', '/favicon.svg', '/__hyperframes_config', '/api/runtime.js', '/api/events', '/api/projects', '/api/environment/ffmpeg', '/api/open-in-desktop'].includes(path))return true;
  if(/^\/(assets|icons)\/[^?]+$/.test(path)||/^\/api\/vendor\/npm\/gsap@3\.15\.0\/dist\/[\w.]+\.js$/.test(path))return true;
  const project=path.match(/^\/api\/projects\/[^/]+(?:\/(.*))?$/);
  if(!project)return false;
  const resource=project[1]||'';
  return ['', 'signature', 'selection', 'files/index.html', 'media/metadata', 'gsap-animations/index.html', 'gsap-mutation-capabilities', 'history', 'renders', 'lint', 'thumbnail/index.html'].includes(resource)
   || /^history\/(peek\/[A-Za-z0-9_:-]{1,160}|blob\/[0-9a-f]{64})$/.test(resource)
   || /^preview(?:\/.*)?$/.test(resource)||/^(image-thumbnail|waveform|peaks)\/assets\/[^/]+$/.test(resource);
 }
 if(method==='PUT'&&/^\/api\/projects\/[^/]+\/selection$/.test(path))return true;
 if(method==='PUT'&&/^\/api\/projects\/[^/]+\/files\/index.html$/.test(path))return typeof body==='string'&&safeRewrite(body);
 if(method==='POST'&&/^\/api\/projects\/[^/]+\/file-mutations\/probe-elements?\/index.html$/.test(path))return true;
 if(method!=='POST'||!/^\/api\/projects\/[^/]+\/file-mutations\/(?:patch-element\/index.html|patch-elements-batch\/index.html|patch-element-batches)$/.test(path))return false;
 const patches=body?.batches?body.batches.flatMap(b=>b.sourceFile==='index.html'?b.patches:[null]):body?.patches||[body];
 if(body?.fontFaceCss!==undefined||patches.some(p=>p?.fontFaceCss!==undefined))return false;
 const document=parseSourceDocument(readFileSync(`${projectDir}/index.html`,'utf8')).document;
 return patches.length>0&&patches.length<=200&&patches.every(p=>{
 const element=p?.target&&findTargetElement(document,p.target),id=element?.getAttribute('id')||'';
 return (/^(clip|caption)-\d+$/.test(id)||/^layer-[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(id))&&Array.isArray(p.operations)&&p.operations.length<=30&&p.operations.every(op=>{
  if(Object.keys(op).some(k=>!['type','property','value'].includes(k)))return false;
  if(op.type==='text-content')return (id.startsWith('caption-')||id.startsWith('layer-')&&element.tagName.toLowerCase()==='div')&&typeof op.value==='string'&&op.value.length<=(id.startsWith('layer-')?4000:500);
  if(id.startsWith('layer-')){
   if(op.type==='inline-style')return ['left','top','width','height','opacity','z-index'].includes(op.property)&&/^-?[0-9]+(?:\.[0-9]+)?(?:px)?$/.test(String(op.value))&&Math.abs(parseFloat(op.value))<=7680;
   return op.type==='attribute'&&[...timing,'data-volume'].includes(op.property)&&validNumber(op.value);
  }
  if(op.type==='inline-style')return id.startsWith('clip-')&&op.property==='object-fit'&&['contain','cover'].includes(op.value);
  return id.startsWith('clip-')&&op.type==='attribute'&&['start','duration','media-start','track-index',...timing].includes(op.property)&&validNumber(op.value);
 });});
}
let mutationTail=Promise.resolve();
const server=createServer(async(req,res)=>{
 let release;
 try{
  if(!['GET','HEAD'].includes(req.method)){const previous=mutationTail;mutationTail=new Promise(resolve=>{release=resolve;});await previous;}
  if(![`127.0.0.1:${port}`,`localhost:${port}`].includes(req.headers.host)){res.writeHead(400).end();return;}
  const localOrigin=`http://${req.headers.host}`;
  const url=new URL(req.url,localOrigin), supplied=url.searchParams.get('vibe_token');
  if(supplied===token&&url.pathname==='/'){
   res.writeHead(303,{'Set-Cookie':`${cookie}=${token}; HttpOnly; SameSite=Strict; Path=/`,'Location':'/','Referrer-Policy':'no-referrer'}).end();return;
  }
  if(!req.headers.cookie?.split(';').some(c=>c.trim()===`${cookie}=${token}`)){res.writeHead(403).end();return;}
  if(!['GET','HEAD'].includes(req.method)&&req.headers.origin!==localOrigin){res.writeHead(403).end();return;}
  const chunks=[];let size=0;
  for await(const c of req){size+=c.length;if(size>131072)throw Error('Request too large');chunks.push(c);}
  const bytes=Buffer.concat(chunks),path=decodeURIComponent(url.pathname);
  let body=bytes.toString();try{body=JSON.parse(body);}catch{}
  const request=new Request(url,{method:req.method,headers:req.headers,...(bytes.length?{body:bytes,duplex:'half'}:{})});
  const accepted=allowed(path,req.method,body);
  const historyMutation=accepted&&req.method==='POST'&&/\/history\//.test(path);
  const baseline=historyMutation?readFileSync(`${projectDir}/index.html`,'utf8'):null;
  let reply=accepted?await studio.app.fetch(request):deny();
  if(historyMutation){
   const updated=readFileSync(`${projectDir}/index.html`,'utf8');
   if(!safeRewrite(updated,baseline)){writeFileSync(`${projectDir}/index.html`,baseline);reply=deny();}
  }
  if(path==='/'&&reply.ok){
   // Native Studio omits loopback credentials; retain our capability on same-origin API calls.
   const bootstrap=`<script>const nativeFetch=window.fetch.bind(window);window.fetch=(input,init)=>nativeFetch(input,{...init,...(new URL(input instanceof Request?input.url:input,location.href).origin===location.origin?{credentials:'same-origin'}:{})});</script>`;
   reply=new Response((await reply.text()).replace('<head>','<head>'+bootstrap),{status:reply.status,headers:reply.headers});
   reply.headers.delete('content-length');
  }
  const headers=Object.fromEntries(reply.headers);
  headers['Referrer-Policy']='no-referrer';headers['X-Content-Type-Options']='nosniff';
  headers['Content-Security-Policy']="default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' blob:; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'self' http://127.0.0.1:* http://localhost:*";
  res.writeHead(reply.status,headers);
  if(reply.body){const stream=Readable.fromWeb(reply.body);res.on('close',()=>stream.destroy());stream.on('error',()=>res.destroy());stream.pipe(res);}else res.end();
 }catch(e){res.writeHead(400,{'Content-Type':'application/json'}).end(JSON.stringify({error:String(e.message)}));}
 finally{release?.();}
});
server.listen(Number(port),'127.0.0.1');
async function stop(){server.close();await studio.shutdown();process.exit(0);}
process.on('SIGTERM',stop);process.on('SIGINT',stop);
