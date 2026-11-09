import {useEffect,useRef,useState} from 'react';
import type {MediaAsset} from './lib/media-api';
import {createBoardSource,listBoardSources,openBoardSource,BoardSourceResult} from './lib/storyboard-api';

type Props={workspace:string;assets:MediaAsset[];onOpen:(result:BoardSourceResult)=>void;disabled:boolean;hasBoard:boolean};
export default function StoryboardStart({workspace,assets,onOpen,disabled,hasBoard}:Props){
 const [title,setTitle]=useState('Untitled storyboard'),[brief,setBrief]=useState(''),[selected,setSelected]=useState<string[]>([]);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[source,setSource]=useState('');
 const [saved,setSaved]=useState<{source_id:string;title:string}[]>([]);
 const attempt=useRef({payload:'',id:''});
 useEffect(()=>{let live=true;void listBoardSources(workspace).then(r=>{if(live)setSaved(r.sources);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[workspace,hasBoard]);
 const open=async(reopen=false)=>{
  if(disabled||busy)return;
  setBusy(true);setError('');
  try{
   const value={title,brief,asset_ids:selected},payload=JSON.stringify(value);
   if(attempt.current.payload!==payload)attempt.current={payload,id:crypto.randomUUID()};
   const result=reopen?await openBoardSource(workspace,source):await createBoardSource(workspace,{...value,request_id:attempt.current.id});
   localStorage.setItem(`vibe-board-source:${workspace}`,result.source.screenplay_revision_id);
   setSaved(items=>[{source_id:result.source.screenplay_revision_id,title:result.source.screenplay.title},...items.filter(item=>item.source_id!==result.source.screenplay_revision_id)]);
   onOpen(result);
   if(!reopen)attempt.current={payload:'',id:''};
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}
 };
 return <details className="card board-stack" open={!hasBoard}>
  <summary>Start from a brief or project media</summary>
  <p>Write one shot per line, choose images/videos in shot order, or combine both. A screenplay is optional. Save current changes before switching boards.</p>
  <fieldset disabled={busy||disabled}>
   <label className="board-field">Storyboard title<input value={title} onChange={e=>setTitle(e.target.value)} maxLength={200}/></label>
   <label className="board-field">Shot outline<textarea rows={4} value={brief} onChange={e=>setBrief(e.target.value)} maxLength={16000}/></label>
   <fieldset><legend>Project media · click in shot order</legend><div className="board-controls">{assets.map(a=><label key={a.asset_id}><input type="checkbox" checked={selected.includes(a.asset_id)} onChange={e=>setSelected(ids=>e.target.checked?[...ids,a.asset_id]:ids.filter(id=>id!==a.asset_id))}/>{selected.includes(a.asset_id)?`${selected.indexOf(a.asset_id)+1}. `:''}{a.filename}</label>)}</div></fieldset>
   <button className="generate-button" disabled={!workspace||(!brief.trim()&&!selected.length)} onClick={()=>void open()}>Create storyboard</button>
   <label className="board-field">Saved storyboards<select value={source} onChange={e=>setSource(e.target.value)}><option value="">Choose a storyboard</option>{saved.map(s=><option key={s.source_id} value={s.source_id}>{s.title}</option>)}</select></label>
   <button className="quiet-button" disabled={!workspace||!source} onClick={()=>void open(true)}>Open saved storyboard</button>
  </fieldset>
  {error&&<p role="alert" className="error-banner">{error}</p>}
 </details>;
}
