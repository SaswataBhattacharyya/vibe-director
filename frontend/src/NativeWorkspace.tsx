import {useEffect,useRef,useState} from 'react';
import './native-workspace.css';
import type {NativeSession,NativeAction} from './lib/native-workspace';

type Props={title:string;open:()=>Promise<NativeSession>;action:(token:string,action:NativeAction)=>Promise<unknown>;onImported?:()=>Promise<unknown>;onProposal?:(value:unknown)=>void;disabled?:boolean;identity:string};

// Native interfaces have their own origin and capability; Vibe owns saving and execution.
export default function NativeWorkspace({title,open,action,onImported,onProposal,disabled,identity}:Props){
 const [session,setSession]=useState<NativeSession|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const live=useRef<NativeSession|null>(null),generation=useRef(0),actionRef=useRef(action);
 actionRef.current=action;
 useEffect(()=>{
  const act=actionRef.current;
  return()=>{generation.current++;const current=live.current;live.current=null;if(current)void act(current.token,'close').catch(()=>{});};
 },[identity]);
 useEffect(()=>{setSession(null);setError('');},[identity]);
 useEffect(()=>{
  if(!session)return;
  const timer=window.setInterval(()=>void actionRef.current(session.token,onImported?'keepalive':'sync').catch(e=>setError(String(e.message))),5000);
  return()=>window.clearInterval(timer);
 },[session,onImported]);
 const perform=async(work:()=>Promise<void>)=>{setBusy(true);setError('');try{await work();}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 const launch=async()=>{const current=generation.current,next=await open();if(current!==generation.current){await action(next.token,'close');return;}const url=new URL(next.url);if(window.location.hostname==='localhost')url.hostname='localhost';next.url=url.href;live.current=next;setSession(next);};
 const close=async()=>{if(session)await action(session.token,'close');live.current=null;setSession(null);};
 return <section className="native-workspace" aria-label={title}>
  <div className="native-workspace-toolbar"><button disabled={disabled||busy||Boolean(session)} onClick={()=>void perform(launch)}>Open {title}</button>
   {session&&<><span>Opened at revision {session.revision}</span>{onImported?<button disabled={disabled||busy} onClick={()=>void perform(async()=>{await action(session.token,'import');live.current=null;setSession(null);await onImported();})}>Import Studio edits as proposal</button>:<button disabled={busy} onClick={()=>void perform(async()=>{await action(session.token,'sync');})}>Sync saved storyboard</button>}{onProposal&&<button disabled={disabled||busy} onClick={()=>void perform(async()=>{onProposal(await action(session.token,'proposal'));})}>Review Backlot edits</button>}<button disabled={busy} onClick={()=>void perform(close)}>Close {title}</button></>}
  </div>
  <p>{onImported?'Native Studio supports source trims, sequential ordering, captions and contain/cover framing here. Import creates a new proposal requiring approval. Filters, speed, extra layers and soundtrack changes stay in Vibe’s visual editor. Closing discards unimported Studio edits.':onProposal?'Native Backlot displays saved media. The Vibe editing extension prepares shot prompt, duration and note changes for review here; save the reviewed draft in Vibe. Closing discards unimported edits.':'Read-only Backlot follows saved storyboard changes every five seconds. Media remains owned by Vibe. Backlot write-back is unsupported.'}</p>
  {error&&<p role="alert">{error}</p>}
  {session&&<iframe title={title} src={session.url} sandbox="allow-scripts allow-same-origin" allow="autoplay; fullscreen" referrerPolicy="no-referrer"/>}
 </section>;
}
