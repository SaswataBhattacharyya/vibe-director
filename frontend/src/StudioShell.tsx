import { ReactNode, useEffect, useState } from 'react';
import { Activity, BookOpen, Clapperboard, Film, FolderOpen, Home, Image, Layers3, Palette, PenLine, Settings2 } from 'lucide-react';

export type StudioRoute = 'home'|'styles'|'story'|'screenplay'|'setup'|'prompts'|'video'|'take'|'assets'|'media'|'status';
const paletteOptions = [
  { id: 'quiet', title: 'Quiet comic', colors: ['#b9c7bc','#1b1a27','#f4f0e5'] },
  { id: 'grit', title: 'Concrete & ink', colors: ['#f28e5d','#191a1d','#f8f2e7'] },
  { id: 'mixtape', title: 'Midnight mixtape', colors: ['#f5c65c','#211831','#73d0ff'] },
];
const validPalette = (value: string | null): string => paletteOptions.some(item => item.id === value) ? value! : 'quiet';
const titles: Record<StudioRoute,string> = { home:'Home',styles:'Production Type & Style',story:'Story',screenplay:'Screenplay',setup:'Automation & Parameters',prompts:'Prompts',video:'Video · Create',take:'Video · Current Take',assets:'Assets',media:'Media Prep & Library',status:'Status' };
function PalettePicker() {
  const [palette,setPalette] = useState(() => { try { return validPalette(localStorage.getItem('vibe-studio-palette')); } catch { return 'quiet'; } });
  useEffect(() => { document.documentElement.dataset.palette = palette; try { localStorage.setItem('vibe-studio-palette',palette); } catch { /* Theme still applies in this tab. */ } },[palette]);
  return <fieldset className="palette-switcher"><legend><Palette size={14}/> Theme</legend><div className="palette-options">{paletteOptions.map(item=><button key={item.id} type="button" className="palette-option" data-palette={item.id} aria-pressed={palette===item.id} onClick={()=>setPalette(item.id)}><span className="palette-swatch">{item.colors.map((color,index)=><i key={index} style={{'--swatch':color} as React.CSSProperties}/>)}</span>{item.title}</button>)}</div></fieldset>;
}
function NavLink({ route, current, children, disabled=false, onNavigate }: { route:StudioRoute;current:StudioRoute;children:ReactNode;disabled?:boolean;onNavigate?:()=>void }) {
  return disabled ? <span className="studio-nav-disabled" aria-disabled="true">{children}<small>Not integrated</small></span> : <a className="studio-nav-link" href={`#/${route}`} aria-current={route===current?'page':undefined} onClick={onNavigate}>{children}</a>;
}
export default function StudioShell({ route, children, context='Direct creation' }: { route:StudioRoute;children:ReactNode;context?:string }) {
  const [mobileOpen,setMobileOpen] = useState(false);
  const activeStage: StudioRoute = route==='take'?'video':route;
  const stages: StudioRoute[] = ['styles','story','screenplay','setup','prompts','video'];
  return <div className={`studio-shell route-${route}`}>
    <aside className={`studio-sidebar ${mobileOpen?'mobile-open':''}`}><a className="studio-brand" href="#/home"><span className="studio-brand-mark"><Clapperboard size={18}/></span><span><b>Vibe Director</b><small>LOCAL STUDIO</small></span></a>
      <nav aria-label="Studio navigation" className="studio-navigation">
        <div className="studio-nav-group"><b>HOME</b><NavLink route="home" current={route} onNavigate={()=>setMobileOpen(false)}><Home size={16}/>Home</NavLink></div>
        <div className="studio-nav-group"><b>STORY WORKFLOW</b><NavLink route="styles" current={route} onNavigate={()=>setMobileOpen(false)}><Palette size={16}/>Production Type & Style</NavLink><NavLink route="story" current={route} onNavigate={()=>setMobileOpen(false)}><BookOpen size={16}/>Story</NavLink><NavLink route="screenplay" current={route} onNavigate={()=>setMobileOpen(false)}><PenLine size={16}/>Screenplay</NavLink><NavLink route="setup" current={route} onNavigate={()=>setMobileOpen(false)}><Settings2 size={16}/>Automation & Parameters</NavLink><NavLink route="prompts" current={route} onNavigate={()=>setMobileOpen(false)}><Layers3 size={16}/>Prompts</NavLink></div>
        <div className="studio-nav-group"><b>VIDEO</b><NavLink route="video" current={route} onNavigate={()=>setMobileOpen(false)}><Film size={16}/>Create</NavLink><NavLink route="take" current={route} onNavigate={()=>setMobileOpen(false)}><Activity size={16}/>Current Take</NavLink></div>
        <div className="studio-nav-group"><b>LIBRARY</b><NavLink route="assets" current={route} onNavigate={()=>setMobileOpen(false)}><Image size={16}/>Assets</NavLink><NavLink route="media" current={route} onNavigate={()=>setMobileOpen(false)}><FolderOpen size={16}/>Media Prep & Library</NavLink></div>
        <div className="studio-nav-group"><b>SYSTEM</b><NavLink route="status" current={route} onNavigate={()=>setMobileOpen(false)}><Activity size={16}/>Status</NavLink></div>
      </nav><div className="studio-sidebar-foot"><span className="studio-local-dot"/> Local source text and drafts</div>
    </aside>
    <main className={`studio-main ${route==='take'?'video-view-take':route==='video'?'video-view-create':''}`}>
      <header className="studio-topbar"><button className="studio-menu-button" aria-expanded={mobileOpen} aria-label={mobileOpen?'Close navigation menu':'Open navigation menu'} onClick={()=>setMobileOpen(open=>!open)}>{mobileOpen?'Close':'Menu'}</button><div><div className="studio-crumb">Workspace <span>/</span> {titles[route]}</div><strong>{route==='video'||route==='take'?context:titles[route]}</strong></div><div className="studio-top-actions"><span className="local-pill"><span className="status-dot"/> Local mode</span><PalettePicker/></div></header>
      {['styles','story','screenplay','setup','prompts','video','take'].includes(route) && <nav className="stage-rail" aria-label="Story to video stages">{stages.map((stage,index)=><a key={stage} href={`#/${stage}`} aria-current={stage===activeStage?'step':undefined} className={stage==='screenplay'||stage==='setup'||stage==='prompts'?'stage-not-integrated':''}><span>{index+1}</span>{titles[stage]}{['screenplay','setup','prompts'].includes(stage)&&<small>Unavailable</small>}</a>)}</nav>}
      {(route==='video'||route==='take') && <nav className="video-tabs" aria-label="Video views"><a href="#/video" aria-current={route==='video'?'page':undefined}><Film size={15}/> Create</a><a href="#/take" aria-current={route==='take'?'page':undefined}><Activity size={15}/> Current Take</a></nav>}
      <div className="studio-page-content">{children}</div>
    </main>
  </div>;
}
