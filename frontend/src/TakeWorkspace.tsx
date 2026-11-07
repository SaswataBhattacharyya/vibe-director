import {createContext, ReactNode, useContext} from 'react';

const TakeProject = createContext('');

export function DockedVideo({src,label}:{src:string;label:string}) {
  const workspaceId=useContext(TakeProject);
  const key=`vibe-take-position:${workspaceId}:${src}`;
  return <video key={src} controls playsInline preload="metadata" src={src} aria-label={label} className="docked-video"
    onLoadedMetadata={e=>{try{e.currentTarget.currentTime=Math.min(Number(localStorage.getItem(key)||0),e.currentTarget.duration||0);}catch{/* Start at zero when the saved position is unavailable. */}}}
    onPause={e=>{try{localStorage.setItem(key,String(e.currentTarget.currentTime));}catch{/* Playback remains usable. */}}}/>;
}

export default function TakeWorkspace({enabled,workspaceId,children}:{enabled:boolean;workspaceId:string;children:ReactNode}) {
  if(!enabled)return <>{children}</>;
  return <TakeProject.Provider value={workspaceId}><div className="take-review-workspace">{children}</div></TakeProject.Provider>;
}
