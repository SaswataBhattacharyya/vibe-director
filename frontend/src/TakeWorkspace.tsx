import {createContext, ReactNode, useContext, useState} from 'react';
import {createPortal} from 'react-dom';
import EditorWorkspace from './EditorWorkspace';

const ReviewDock=createContext<{target:HTMLDivElement|null;workspaceId:string}|null>(null);
const InsideReview=createContext(false);

// Keep the existing review handlers in their owner while displaying their UI in the right pane.
export function TakeReviewSection({children}:{children:ReactNode}) {
  const dock=useContext(ReviewDock);
  if(!dock)return <>{children}</>;
  return dock.target?createPortal(<InsideReview.Provider value={true}>{children}</InsideReview.Provider>,dock.target):null;
}

export function DockedVideo({src,label}:{src:string;label:string}) {
  const dock=useContext(ReviewDock),inside=useContext(InsideReview);
  const key=`vibe-take-position:${dock?.workspaceId||''}:${src}`;
  const player=<video key={src} controls playsInline preload="metadata" src={src} aria-label={label} className="docked-video"
    onLoadedMetadata={e=>{try{e.currentTarget.currentTime=Math.min(Number(localStorage.getItem(key)||0),e.currentTarget.duration||0);}catch{/* Start at zero when the saved position is unavailable. */}}}
    onPause={e=>{try{localStorage.setItem(key,String(e.currentTarget.currentTime));}catch{/* Playback remains usable. */}}}/>;
  if(!dock||inside)return player;
  return <TakeReviewSection><article className="take-docked-clip"><h3>{label}</h3>{player}</article></TakeReviewSection>;
}

export default function TakeWorkspace({enabled,workspaceId,children}:{enabled:boolean;workspaceId:string;children:ReactNode}) {
  const [target,setTarget]=useState<HTMLDivElement|null>(null);
  if(!enabled)return <>{children}</>;
  return <ReviewDock.Provider value={{target,workspaceId}}><EditorWorkspace name="take" preview={<>
    <h2>Generated clips &amp; take review</h2>
    <div className="take-review-dock" ref={setTarget}/>
  </>}>{children}</EditorWorkspace></ReviewDock.Provider>;
}
