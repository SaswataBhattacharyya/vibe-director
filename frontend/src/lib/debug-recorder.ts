/** Opt-in manual investigation. HTTP success is evidence, never an acceptance verdict. */
export type DebugStatus = {enabled:boolean; session_id:string|null; log_path:string|null; bytes:number; max_bytes:number};
type Event = Record<string, string|number|boolean>;
const nativeFetch = window.fetch.bind(window);
let enabled = false;
let installed = false;
let queue: Event[] = [];
let pending: Promise<void>|null = null;
let blocked: Error|null = null;
let recordingVersion = 0;
const signatures = new Map<string,string>();
const debugStateKey = 'vibe-director-debug-enabled';
function publishError(message:string) { window.dispatchEvent(new CustomEvent('debug-recorder-error', {detail:message})); }
class DebugRequestError extends Error {
  constructor(readonly status:number, message:string) {super(message);}
}
async function request(path:string, init?:RequestInit) {
  const response = await nativeFetch(path,init);
  if (!response.ok) throw new DebugRequestError(response.status, `Debug API ${response.status}: ${await response.text()}`);
  return response.json();
}
export async function getDebugStatus():Promise<DebugStatus> {
  const status = await request('/api/debug'); enabled = status.enabled; return status;
}
export async function setDebugEnabled(value:boolean):Promise<DebugStatus> {
  if (!value) { try { await flushDebug(); } catch { queue=[]; } }
  const status = await request('/api/debug',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:value})});
  enabled = status.enabled; blocked = null; recordingVersion++; signatures.clear();
  try { localStorage.setItem(debugStateKey, String(status.enabled)); } catch { /* Storage may be unavailable in restricted browser contexts. */ }
  if (enabled) recordDebug({kind:'navigation',action:'recording_started'});
  return status;
}
export function recordDebug(event:Event) {
  if (!enabled || blocked) return;
  if (queue.length >= 100) { publishError('Debug events could not be saved fast enough. Some events were dropped.'); return; }
  queue.push({...event,route:location.hash,client_time:new Date().toISOString()});
}
export function flushDebug():Promise<void> {
  if (pending) return pending;
  if (blocked) return Promise.reject(blocked);
  pending = (async()=>{
    while (queue.length) {
      const batch = queue.splice(0,50);
      const version = recordingVersion;
      try { const result=await request('/api/debug/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({events:batch}),keepalive:true}); if(result.recorded!==batch.length)throw new Error('Debug recording was turned off in another tab. These events were not saved.'); }
      catch (error) {
        if(version!==recordingVersion || !enabled)return;
        queue.unshift(...batch); queue = queue.slice(0,100);
        // A rejected batch cannot succeed unchanged. Keep it for an explicit stop,
        // but do not send it every second or collect errors about its own failure.
        if(error instanceof DebugRequestError && error.status>=400 && error.status<500) blocked=error;
        publishError(String(error)); throw error;
      }
    }
  })().finally(()=>{pending=null;});
  return pending;
}
export async function saveDebugObservation(outcome:string, message:string) {
  if (!enabled) throw new Error('Turn Debug on before saving observations.');
  recordDebug({kind:'owner_observation',outcome,message}); await flushDebug();
}
export async function downloadDebugLog() {
  await flushDebug();
  const response = await nativeFetch('/api/debug/log');
  if (!response.ok) throw new Error(`Debug download failed (${response.status}).`);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a'); link.href=url; link.download='vibe-director-debug.jsonl'; link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function targetName(element:HTMLElement) {
  return (element.getAttribute('aria-label') || (element instanceof HTMLInputElement ? element.labels?.[0]?.textContent : '') || element.textContent || element.id || element.tagName).trim().slice(0,160);
}
export function installDebugRecorder() {
  if (installed) return;
  installed = true;
  void getDebugStatus().then(status=>{if(status.enabled)recordDebug({kind:'navigation',action:'page_loaded'});}).catch(()=>{}); // Older/offline servers remain usable, Status exposes errors.
  setInterval(()=>void flushDebug().catch(()=>{}),1000);
  document.addEventListener('click',event=>{
    const control = (event.target as Element)?.closest<HTMLElement>('button,a,input,select,summary,video,audio');
    if (!control || control.closest('[data-debug-panel]')) return;
    if (control instanceof HTMLInputElement && control.type==='password') return;
    recordDebug({kind:'interaction',action:'click',target:targetName(control)});
  },true);
  document.addEventListener('change',event=>{
    const control = event.target;
    if (!(control instanceof HTMLInputElement || control instanceof HTMLSelectElement || control instanceof HTMLTextAreaElement) || control.closest('[data-debug-panel]')) return;
    if (control instanceof HTMLInputElement && control.type==='password') return;
    const value = control instanceof HTMLSelectElement ? control.selectedOptions[0]?.textContent || '' : control instanceof HTMLInputElement && ['checkbox','radio'].includes(control.type) ? String(control.checked) : control instanceof HTMLInputElement && ['number','range'].includes(control.type) ? control.value : control instanceof HTMLInputElement && control.type==='file' ? `${control.files?.length || 0} files selected` : `${control.value.length} characters entered`;
    recordDebug({kind:'interaction',action:'change',target:targetName(control),value});
  },true);
  window.addEventListener('pagehide',()=>void flushDebug().catch(()=>{}));
  window.addEventListener('storage',event=>{
    if (event.key !== debugStateKey) return;
    enabled = event.newValue === 'true'; blocked = null; recordingVersion++; signatures.clear();
    // A stopped session's unsaved events must never spill into the next recording.
    if (!enabled) queue=[];
    if (enabled) recordDebug({kind:'navigation',action:'recording_started_in_another_tab'});
  });
  window.addEventListener('hashchange',()=>recordDebug({kind:'navigation',action:'page_changed'}));
  window.addEventListener('error',event=>recordDebug({kind:'error',message:event.message}));
  window.addEventListener('unhandledrejection',event=>recordDebug({kind:'error',message:String(event.reason)}));
  for (const action of ['play','pause','ended','error']) document.addEventListener(action,event=>{
    if (event.target instanceof HTMLMediaElement) recordDebug({kind:'media',action,target:targetName(event.target),value:event.target.currentTime});
  },true);
  const visibleMessages = new Set<string>();
  new MutationObserver(()=>{
    if (!enabled) return;
    for (const element of document.querySelectorAll<HTMLElement>('[role="alert"],[role="status"]')) {
      if (element.closest('[data-debug-panel]') || !element.getClientRects().length) continue;
      const message = element.textContent?.trim().slice(0,1000) || '';
      const key = `${location.hash}:${message}`;
      if (message && !visibleMessages.has(key)) { recordDebug({kind:'feedback',message}); if(visibleMessages.size>500)visibleMessages.clear(); visibleMessages.add(key); }
    }
  }).observe(document.body,{subtree:true,childList:true,characterData:true});
  window.fetch = async (input,init) => {
    const url = new URL(input instanceof Request ? input.url : String(input),location.href);
    const method = init?.method || (input instanceof Request ? input.method : 'GET');
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/') || url.pathname.startsWith('/api/debug')) return nativeFetch(input,init);
    try {
      const response = await nativeFetch(input,init);
      if (enabled) {
        const event:Event = {kind:'api',path:url.pathname,method,status:response.status};
        // Only small diagnostic fields, never full request/response bodies or file content.
        if (response.headers.get('content-type')?.includes('json')) {
          try {
            const data = await response.clone().json();
            for (const key of ['job_id','status','state']) if (typeof data[key]==='string') event[key==='status'?'state':key]=data[key].slice(0,200);
            const jobs = data.jobs || data.batch?.jobs || (data.job ? [data.job] : []);
            if (Array.isArray(jobs) && jobs.length) event.value=JSON.stringify(jobs.slice(0,10).map(job=>({job_id:job.job_id,status:job.status || job.state,error:job.error?.message}))).slice(0,1000);
            if (!response.ok) event.message=String(data.error?.message || data.error || data.message || 'Request failed').slice(0,1000);
          } catch { /* Non-JSON diagnostics are represented by HTTP status. */ }
        }
        const signature = JSON.stringify(event); const key = `${method} ${url.pathname}`;
        if (method !== 'GET' || signatures.get(key)!==signature) { recordDebug(event); if(signatures.size>500)signatures.clear(); signatures.set(key,signature); }
      }
      return response;
    } catch (error) { recordDebug({kind:'api_error',path:url.pathname,method,message:String(error)}); throw error; }
  };
}
