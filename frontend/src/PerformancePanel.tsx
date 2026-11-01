import { useEffect, useState } from 'react';

type Timing = {take_id:string; phase:string; seconds:string; outcome:string; recorded_at:string; workflow_id:string};
type Status = {enabled:boolean; session_id:string|null; log_path:string|null; bytes:number; max_bytes:number; recent:Timing[]};
const phases:Record<string,string> = {
  prepare_and_stage:'Prepare and stage inputs', comfy_execution_inclusive:'ComfyUI execution (all nodes)',
  collect_and_validate:'Collect and validate output', post_submit_to_worker_result:'After submission → worker result (inclusive)',
  model_unload_observation:'Model unload → observed release (overlaps preparation at handoff)',
};
export default function PerformancePanel() {
  const [status,setStatus]=useState<Status|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  async function load(enabled?:boolean) {
    setBusy(true);setError('');
    try {
      const response=await fetch('/api/performance',enabled===undefined?undefined:{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled})});
      if(!response.ok)throw new Error(`Performance API ${response.status}: ${await response.text()}`);
      setStatus(await response.json());
    } catch(error){setError(String(error));} finally{setBusy(false);}
  }
  useEffect(()=>{void load();},[]);
  useEffect(()=>{
    if(!status?.enabled)return;
    const timer=window.setInterval(()=>{void load();},10000);
    return ()=>window.clearInterval(timer);
  },[status?.enabled]);
  return <section className="runtime-card card" aria-label="Generation timing" data-debug-panel>
    <h2>Generation timing</h2>
    <label><input type="checkbox" role="switch" aria-label="Record generation timing" checked={status?.enabled||false} disabled={!status||busy} onChange={event=>void load(event.target.checked)}/> Record generation timing</label>
    <p>Turn this on before generating to compare H3 timings. Independent of Debug; records job IDs, workflow settings and elapsed seconds locally, without prompts or media. Updates every 10 seconds while recording.</p>
    <p>ComfyUI execution includes model loading, text encoding, denoising, decoding and saving. Those internal stages are not measured separately. The inclusive worker time overlaps execution and collection: do not add these rows together. Timings are observations, not a promised render time.</p>
    <div className="top-actions"><button className="quiet-button" disabled={busy} onClick={()=>void load()}>Refresh timings</button>{status?.session_id&&<a className="quiet-button" href="/api/performance/log" download="vibe-director-performance.jsonl">Download timing log</a>}</div>
    {status?.log_path&&<p>Local log: <code style={{overflowWrap:'anywhere'}}>{status.log_path}</code></p>}
    {status&&status.bytes>=status.max_bytes&&<p role="alert">Timing log is full. Turn recording off and on to start a new file.</p>}
    {!!status?.recent.length&&<div style={{overflowX:'auto'}}><table><thead><tr><th>Clip / take</th><th>Stage</th><th>Seconds</th><th>Result</th></tr></thead><tbody>{status.recent.slice().reverse().map((row,index)=><tr key={`${row.recorded_at}-${index}`}><td title={row.take_id}>{row.take_id.slice(0,12)}</td><td>{phases[row.phase]||row.phase}</td><td>{Number(row.seconds).toFixed(2)}</td><td>{row.outcome}</td></tr>)}</tbody></table></div>}
    {status&&!status.recent.length&&<p>No timings recorded in this session. Completed stages appear here; an unfinished generation may still be running.</p>}
    <p>Each session has an 8 MiB limit. Turning off stops recording; turning on again starts a new file. Past files remain on disk.</p>
    {error&&<p role="alert">{error}</p>}
  </section>;
}
