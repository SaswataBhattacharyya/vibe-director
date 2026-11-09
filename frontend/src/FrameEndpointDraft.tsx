import {useState} from 'react';

type Endpoints = {first_frame:{asset_id:string};last_frame:{asset_id:string}};

/** Explicit handoff; a reviewed take never mutates an existing frozen request. */
export default function FrameEndpointDraft({owner,disabled,onApply}:{owner:string;disabled:boolean;onApply:(value:Endpoints)=>void}) {
  const query=new URLSearchParams(window.location.hash.split('?')[1]||'');
  const take=query.get('frame_take'),revision=query.get('frame_revision');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  if(!take||!revision||query.get('workspace_id')!==owner)return null;
  const apply=async()=>{
    setBusy(true);setError('');
    try{
      const response=await fetch(`/api/frame-pipeline/${encodeURIComponent(owner)}/takes/${encodeURIComponent(take)}/endpoints?revision=${encodeURIComponent(revision)}`);
      const value=await response.json();
      if(!response.ok)throw new Error(value?.error?.message||'Could not load approved endpoints.');
      onApply(value);
      window.location.hash=`#/video?workspace_id=${encodeURIComponent(owner)}`;
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}
  };
  return <section className="card"><h3>Approved take endpoints</h3>
    <p>Create a new First + Last Frame draft using this take’s first and last approved keys. Your current draft is saved separately; no video starts here.</p>
    {error&&<p role="alert">{error}</p>}
    <button disabled={disabled||busy} onClick={()=>void apply()}>Create draft from approved endpoints</button>
    {disabled&&<p>Let the current attempt settle before creating this draft.</p>}
  </section>;
}
