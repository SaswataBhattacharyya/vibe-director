import {useState} from 'react';
import {studioRequest} from './StudioChat';
type Checkpoint={id:string;name:string;path:string;kind:string;bytes:number;sha256:string};
export default function StudioCheckpoints(){
 const [rows,setRows]=useState<Checkpoint[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const refresh=async()=>{setBusy(true);setError('');try{setRows((await studioRequest('/api/studio-tools/checkpoints')).checkpoints);}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 const remove=async(row:Checkpoint)=>{if(!window.confirm(`Permanently delete ${row.kind}?\n${row.path}\n${(row.bytes/1024**2).toFixed(1)} MiB\nSource recordings, datasets and base models are preserved. A published copy is a separate entry.`))return;setBusy(true);setError('');try{setRows((await studioRequest('/api/studio-tools/checkpoints/delete',{id:row.id,sha256:row.sha256,confirmed:true})).checkpoints);}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 return <details className="card"><summary>Trained models &amp; checkpoints</summary><p>Trained artifacts and published copies have separate paths. Deletion is permanent and requires idle training and generation.</p><button disabled={busy} onClick={()=>void refresh()}>{busy?'Checking…':'Refresh checkpoints'}</button>{rows.map(row=><article key={row.id}><strong>{row.kind} · {row.name}</strong><p style={{overflowWrap:'anywhere'}}>{row.path}</p><span>{(row.bytes/1024**2).toFixed(1)} MiB</span> <button disabled={busy} onClick={()=>void remove(row)}>Delete checkpoint…</button></article>)}{error&&<p role="alert">{error}</p>}</details>;
}
