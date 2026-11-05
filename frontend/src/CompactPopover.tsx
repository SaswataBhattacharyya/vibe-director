import {ReactNode, useEffect, useId, useLayoutEffect, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import './compact-popover.css';

/** Anchored secondary controls; the panel never changes the surrounding layout. */
export default function CompactPopover({label,children,onOpenChange,disabled=false}:{label:string;children:ReactNode;onOpenChange?:(open:boolean)=>void;disabled?:boolean}) {
  const [open,setOpen]=useState(false),[position,setPosition]=useState({top:0,left:0});
  const trigger=useRef<HTMLButtonElement>(null),panel=useRef<HTMLDivElement>(null),id=useId();
  const change=(value:boolean)=>{setOpen(value);onOpenChange?.(value);};
  useLayoutEffect(()=>{
    if(!open)return;
    const place=()=>{const box=trigger.current?.getBoundingClientRect();if(box)setPosition({top:Math.max(8,Math.min(box.bottom+6,window.innerHeight-Math.min(480,window.innerHeight*.7)-8)),left:Math.max(8,Math.min(box.left,window.innerWidth-Math.min(640,window.innerWidth-16)-8))});};
    place();window.addEventListener('resize',place);window.addEventListener('scroll',place,true);
    return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);};
  },[open]);
  useEffect(()=>{
    if(!open)return;
    panel.current?.focus();
    const outside=(e:PointerEvent)=>{if(!panel.current?.contains(e.target as Node)&&!trigger.current?.contains(e.target as Node))change(false);};
    const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.preventDefault();change(false);trigger.current?.focus();}};
    document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key);
    return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key);};
  },[open]);
  useEffect(()=>{if(disabled&&open)change(false);},[disabled]);
  return <><button ref={trigger} type="button" disabled={disabled} aria-expanded={open} aria-controls={id} onClick={()=>change(!open)}>{label}</button>{open&&createPortal(<div id={id} ref={panel} role="dialog" aria-label={label} tabIndex={-1} className="compact-popover" style={position}><div className="compact-popover-heading"><strong>{label}</strong><button type="button" aria-label={`Close ${label}`} onClick={()=>{change(false);trigger.current?.focus();}}>×</button></div>{children}</div>,document.body)}</>;
}
