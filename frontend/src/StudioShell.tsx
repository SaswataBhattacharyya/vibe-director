import {createPortal} from 'react-dom';
import { ReactNode, useEffect, useRef, useState } from 'react';
import { Activity, BookOpen, Clapperboard as BrandIcon, Film, FolderOpen, Home, Image, Palette, PenLine, Settings2, UserRound } from 'lucide-react';
import Clapper from './Clapper';
import DirectorSettings from './DirectorSettings';
import ModelSelector from './ModelSelector';
import DirectorWorkspace from './DirectorWorkspace';

export type StudioRoute = 'home'|'styles'|'story'|'screenplay'|'shot-frames'|'storyboard'|'setup'|'prompts'|'video'|'take'|'assets'|'characters'|'worlds'|'frames'|'image-to-3d-pixal3d'|'image-to-3d'|'text-to-image'|'media-prep'|'media'|'editor'|'status';
const paletteOptions = [
  { id: 'quiet', title: 'Quiet comic', colors: ['#b9c7bc','#1b1a27','#f4f0e5'] },
  { id: 'grit', title: 'Concrete & ink', colors: ['#f28e5d','#191a1d','#f8f2e7'] },
  { id: 'mixtape', title: 'Midnight mixtape', colors: ['#f5c65c','#211831','#73d0ff'] },
];
const validPalette = (value: string | null): string => paletteOptions.some(item => item.id === value) ? value! : 'quiet';
const titles: Record<StudioRoute,string> = { home:'Home',styles:'Production Type & Style',story:'Story',screenplay:'Screenplay','shot-frames':'Frame per shot',storyboard:'Storyboard',setup:'Automation & Parameters',prompts:'Prompt Preparation',video:'Video · Create',take:'Video · Current Take',assets:'Image assets',characters:'Characters & Voices',worlds:'Scene Backgrounds',frames:'First & Last Frames','image-to-3d':'Image to 3D · TRELLIS.2','image-to-3d-pixal3d':'Image to 3D · Pixal3D','text-to-image':'Text to Image','media-prep':'Media Prep',media:'Search',editor:'Vibe Editor',status:'Status' };
function PalettePicker() {
  const [palette,setPalette] = useState(() => { try { return validPalette(localStorage.getItem('vibe-studio-palette')); } catch { return 'quiet'; } });
  useEffect(() => { document.documentElement.dataset.palette = palette; try { localStorage.setItem('vibe-studio-palette',palette); } catch { /* Theme still applies in this tab. */ } },[palette]);
  return <fieldset className="palette-switcher"><legend><Palette size={14}/> Theme</legend><div className="palette-options">{paletteOptions.map(item=><button key={item.id} type="button" className="palette-option" data-palette={item.id} aria-pressed={palette===item.id} onClick={()=>setPalette(item.id)}><span className="palette-swatch" aria-hidden="true">{item.colors.map((color,index)=><i key={index} style={{'--swatch':color} as React.CSSProperties}/>)}</span><span>{item.title}</span></button>)}</div></fieldset>;
}
function ProfileSettings() {
  const [open,setOpen] = useState(false);
  const [position,setPosition] = useState({top:64,left:16});
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const place = () => {
      const anchor=trigger.current?.getBoundingClientRect();
      if(!anchor)return;
      const width=Math.min(540,window.innerWidth-32);
      setPosition({left:Math.max(16,Math.min(anchor.left,window.innerWidth-width-16)),top:Math.max(16,Math.min(anchor.bottom+12,window.innerHeight-160))});
    };
    place();
    window.addEventListener('resize',place);
    window.addEventListener('scroll',place,true);
    panel.current?.querySelector<HTMLButtonElement>('button')?.focus();
    const onPointer = (event: PointerEvent) => { if (!panel.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setOpen(false); };
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); trigger.current?.focus(); } };
    document.addEventListener('pointerdown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => { window.removeEventListener('resize',place); window.removeEventListener('scroll',place,true); document.removeEventListener('pointerdown', onPointer); document.removeEventListener('keydown', onKey); };
  }, [open]);
  return <div className="profile-settings">
    <button ref={trigger} className="profile-trigger" type="button" aria-label="Open Director and appearance settings" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(value => !value)}><UserRound size={17}/></button>
    {createPortal(<div className="studio-shell profile-settings-layer"><div ref={panel} className="profile-popover" style={{top:position.top,left:position.left,maxHeight:`calc(100dvh - ${position.top+16}px)`}} hidden={!open} role="dialog" aria-labelledby="profile-settings-title"><h2 id="profile-settings-title">Director & appearance</h2>{open && <DirectorSettings/>}<PalettePicker/></div></div>,document.body)}
  </div>;
}
function NavLink({ route, current, children, disabled=false, onNavigate }: { route:StudioRoute;current:StudioRoute;children:ReactNode;disabled?:boolean;onNavigate?:()=>void }) {
  return disabled ? <span className="studio-nav-disabled" aria-disabled="true">{children}<small>Not integrated</small></span> : <a className="studio-nav-link" href={`#/${route}`} aria-current={route===current?'page':undefined} onClick={onNavigate}>{children}</a>;
}
export default function StudioShell({ route, children, context='Direct creation' }: { route:StudioRoute;children:ReactNode;context?:string }) {
  const [mobileOpen,setMobileOpen] = useState(false);
  const [navClosed,setNavClosed] = useState(()=>{try{return localStorage.getItem('vibe-navigation-closed')==='true';}catch{return false;}});
  const toggleNav=()=>{setNavClosed(v=>{try{localStorage.setItem('vibe-navigation-closed',String(!v));}catch{}return !v;});};
  const activeStage: StudioRoute = route==='take'?'video':route;
  const stages: StudioRoute[] = ['styles','story','screenplay','setup','prompts','video'];
  return <div className={`studio-shell route-${route}${navClosed?' navigation-closed':''}`}>
    <aside className={`studio-sidebar ${mobileOpen?'mobile-open':''}`}><div className="studio-brand-row"><a className="studio-brand" href="#/home"><span className="studio-brand-mark"><BrandIcon size={18}/></span><span><b>Vibe Director</b><small>LOCAL STUDIO</small></span></a><ProfileSettings/></div>
      <nav aria-label="Studio navigation" className="studio-navigation">
        <div className="studio-nav-group"><b>HOME</b><NavLink route="home" current={route} onNavigate={()=>setMobileOpen(false)}><Home size={16}/>Home</NavLink></div>
        <div className="studio-nav-group"><b>STORY WORKFLOW</b><NavLink route="styles" current={route} onNavigate={()=>setMobileOpen(false)}><Palette size={16}/>Production Type & Style</NavLink><NavLink route="story" current={route} onNavigate={()=>setMobileOpen(false)}><BookOpen size={16}/>Story</NavLink><NavLink route="screenplay" current={route} onNavigate={()=>setMobileOpen(false)}><PenLine size={16}/>Screenplay</NavLink><NavLink route="shot-frames" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/>Frame per shot</NavLink><NavLink route="storyboard" current={route} onNavigate={()=>setMobileOpen(false)}><BookOpen size={16}/>Storyboard</NavLink><NavLink route="setup" current={route} onNavigate={()=>setMobileOpen(false)}><Settings2 size={16}/>Automation & Parameters</NavLink><NavLink route="prompts" current={route} onNavigate={()=>setMobileOpen(false)}><PenLine size={16}/>Prompt Preparation</NavLink></div>
        <div className="studio-nav-group"><b>VIDEO</b><NavLink route="video" current={route} onNavigate={()=>setMobileOpen(false)}><Film size={16}/>Create</NavLink><NavLink route="take" current={route} onNavigate={()=>setMobileOpen(false)}><Activity size={16}/>Current Take</NavLink></div>
        <div className="studio-nav-group"><b>GENERATION ASSETS</b><NavLink route="characters" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/>Characters & Voices</NavLink><NavLink route="worlds" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/>Scene Backgrounds</NavLink><NavLink route="frames" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/>First & Last Frames</NavLink><NavLink route="text-to-image" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/>Text to Image</NavLink><NavLink route="image-to-3d" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/> TRELLIS.2 · Image to 3D</NavLink><NavLink route="image-to-3d-pixal3d" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/> Pixal3D · Multi-view to 3D</NavLink></div>
        <div className="studio-nav-group"><b>MEDIA PREP</b><NavLink route="media-prep" current={route==='media'?'media-prep':route} onNavigate={()=>setMobileOpen(false)}><FolderOpen size={16}/>Media Prep</NavLink><NavLink route="editor" current={route} onNavigate={()=>setMobileOpen(false)}><Film size={16}/>Vibe Editor</NavLink></div>
        <div className="studio-nav-group studio-projects"><b>PROJECTS</b><NavLink route="story" current={route} onNavigate={()=>setMobileOpen(false)}><BookOpen size={16}/>Start a story</NavLink><small>New / Open / Save above</small></div>
        <div className="studio-nav-group"><b>SYSTEM</b><NavLink route="status" current={route} onNavigate={()=>setMobileOpen(false)}><Activity size={16}/>Status</NavLink></div>
      </nav><div className="studio-sidebar-foot"><span className="studio-local-dot"/> Local source text and drafts</div><div className="studio-mascot"><Clapper route={route}/></div>
    </aside>
    <main className={`studio-main ${route==='take'?'video-view-take':route==='video'?'video-view-create':''}`}>
      <header className="studio-topbar"><button className="studio-nav-toggle" type="button" aria-expanded={!navClosed} onClick={toggleNav}>{navClosed?'Show':'Hide'} navigation</button><button className="studio-menu-button" aria-expanded={mobileOpen} aria-label={mobileOpen?'Close navigation menu':'Open navigation menu'} onClick={()=>setMobileOpen(open=>!open)}>{mobileOpen?'Close':'Menu'}</button><div><div className="studio-crumb">Project <span>/</span> {titles[route]}</div><strong>{route==='video'||route==='take'?context:titles[route]}</strong></div><div className="studio-top-actions"><ModelSelector/><span className="local-pill"><span className="status-dot"/> Local mode</span></div></header>
      {['styles','story','screenplay','setup','prompts','video','take'].includes(route) && <details className="studio-workflow"><summary>Story workflow</summary><nav className="stage-rail" aria-label="Story to video stages">{stages.map((stage,index)=><a key={stage} href={`#/${stage}`} aria-current={stage===activeStage?'step':undefined}><span>{index+1}</span>{titles[stage]}</a>)}</nav></details>}
      {(route==='video'||route==='take') && <nav className="video-tabs" aria-label="Video views"><a href="#/video" aria-current={route==='video'?'page':undefined}><Film size={15}/> Create</a><a href="#/take" aria-current={route==='take'?'page':undefined}><Activity size={15}/> Current Take</a></nav>}
      <DirectorWorkspace>{children}</DirectorWorkspace>
    </main>
    <footer className="studio-taskbar" aria-label="Project navigation"><span className="taskbar-location"><small>OPEN</small><strong>{titles[route]}</strong>{(route==='video'||route==='take')&&<span>{context}</span>}</span><nav aria-label="Quick navigation"><a href="#/story" aria-current={route==='story'?'page':undefined}><BookOpen size={15}/>Story</a><a href="#/video" aria-current={route==='video'?'page':undefined}><Film size={15}/>Video Create</a></nav></footer>
  </div>;
}
