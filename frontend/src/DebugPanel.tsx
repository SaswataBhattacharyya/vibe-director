import { useEffect, useState } from 'react';
import { DebugStatus, downloadDebugLog, getDebugStatus, saveDebugObservation, setDebugEnabled } from './lib/debug-recorder';

export default function DebugPanel() {
  const [status,setStatus]=useState<DebugStatus|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [note,setNote]=useState('');
  const [outcome,setOutcome]=useState('observation');
  const [message,setMessage]=useState('');
  useEffect(()=>{
    void getDebugStatus().then(setStatus).catch(error=>setError(String(error)));
    const listener=(event:Event)=>setError((event as CustomEvent<string>).detail);
    window.addEventListener('debug-recorder-error',listener);
    return ()=>window.removeEventListener('debug-recorder-error',listener);
  },[]);
  async function act(action:()=>Promise<unknown>) {
    setBusy(true);setError('');setMessage('');
    try {await action();} catch(error){setError(String(error));} finally{setBusy(false);}
  }
  return <section className="runtime-card card" aria-label="Debug recording" data-debug-panel>
    <h2>Debug</h2>
    <label><input type="checkbox" role="switch" aria-label="Debug" checked={status?.enabled || false} disabled={!status || busy} onChange={event=>void act(async()=>setStatus(await setDebugEnabled(event.target.checked)))}/> Record manual steps</label>
    <p>Records page changes, controls used, media playback, API results and browser errors to a local file. Successful requests do not prove that a result is correct; add your observations below.</p>
    <p>Text fields record character counts, not their contents. File contents and passwords are excluded. Each new recording session has an 8 MiB limit; previous files remain available locally.</p>
    {status?.log_path && <p>Local log: <code style={{overflowWrap:'anywhere'}}>{status.log_path}</code></p>}
    <div className="top-actions"><button className="quiet-button" disabled={!status?.session_id || busy} onClick={()=>void act(downloadDebugLog)}>Download debug log</button><button className="quiet-button" disabled={busy} onClick={()=>void act(async()=>setStatus(await getDebugStatus()))}>Refresh debug status</button></div>
    {status?.enabled && <><label>Manual result <select aria-label="Manual result" value={outcome} onChange={event=>setOutcome(event.target.value)}><option value="observation">Observation</option><option value="passed">Passed</option><option value="failed">Failed</option></select></label><label>Step and observation <textarea aria-label="Step and observation" placeholder="Example: Search → Videos, clicked Play on my imported video. Picture and sound worked." maxLength={1000} value={note} onChange={event=>setNote(event.target.value)}/></label><button className="quiet-button" disabled={busy || !note.trim()} onClick={()=>void act(async()=>{await saveDebugObservation(outcome,note.trim());setNote('');setMessage('Observation sent to the local journal.');})}>Save observation</button></>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">Debug recording: {error}</p>}
    {!status && <p>Recording is unavailable until the backend provides the Debug API. Refresh after restarting the backend.</p>}
  </section>;
}
