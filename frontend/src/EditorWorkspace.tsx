import { ReactNode, useEffect, useState } from 'react';
import './vibe-editor.css';

function useSaved<T>(key:string, fallback:T) {
  const [value,setValue]=useState<T>(()=>{try {return JSON.parse(localStorage.getItem(key)||'null')??fallback;}catch{return fallback;}});
  const save=(next:T)=>{setValue(next);try {localStorage.setItem(key,JSON.stringify(next));}catch{/* In-memory layout remains usable. */}};
  return [value,save] as const;
}
export default function EditorWorkspace({name,children,preview,reveal=0,leftLabel='conversation',rightLabel='preview',initialWidth=42}:{name:string;children:ReactNode;preview:ReactNode;reveal?:number;leftLabel?:string;rightLabel?:string;initialWidth?:number}) {
  const [center,setCenter]=useSaved(`vibe-${name}-center`,true);
  const [right,setRight]=useSaved(`vibe-${name}-preview`,true);
  const [width,setWidth]=useSaved(`vibe-${name}-preview-width`,initialWidth);
  const [mobile,setMobile]=useState<'conversation'|'preview'>('conversation');
  useEffect(()=>{if(reveal){setRight(true);setMobile('preview');}},[reveal]);
  return <div className={`editor-workspace mobile-${mobile}`}>
    <nav className="editor-mobile-tabs" aria-label="Workspace pane"><button onClick={()=>{setCenter(true);setMobile('conversation');}}>{leftLabel==='conversation'?'Written panel':`${leftLabel} panel`}</button><button onClick={()=>{setRight(true);setMobile('preview');}}>{rightLabel} panel</button></nav>
    <div className="editor-pane-controls"><button onClick={()=>setCenter(!center)} aria-expanded={center}>{center?'Hide':'Show'} {leftLabel}</button><button onClick={()=>setRight(!right)} aria-expanded={right}>{right?'Hide':'Show'} {rightLabel}</button>{right&&<label>{rightLabel} width <input aria-label={`${rightLabel} width`} type="range" min="25" max="65" value={width} onChange={e=>setWidth(Number(e.target.value))}/></label>}</div>
    <div className="editor-panes" style={{gridTemplateColumns:center&&right?`minmax(0,${100-width}fr) minmax(0,${width}fr)`:'minmax(0,1fr)'}}>
      <section className="editor-conversation" hidden={!center}>{children}</section><aside className="editor-preview" hidden={!right}>{preview}</aside>
    </div>
  </div>;
}
