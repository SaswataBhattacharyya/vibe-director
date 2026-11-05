import {useEffect,useRef,useState} from 'react';
import {browseMediaCatalogue,reuseCatalogueAsset,refreshDownloadCatalogue,nameMediaWorkspace,type MediaAsset,type CataloguePage} from './lib/media-api';
import SelectionToggle from './SelectionToggle';
import CompactPopover from './CompactPopover';
import {listStoryWorkspaces} from './lib/story-api';

const sources=[['all','All media'],['current','Current project'],['workspaces','All projects'],['downloaded','YouTube downloads'],['extracted','Analyzed clips'],['repertoire','Video repertoire'],['generated','Generated media'],['ace_generated','ACE-Step generated audio'],['style','Style references'],['imported','Imported files']];
/** Discovery is global. Explicit Add preserves the tool's existing destination and slot selection. */
export default function MediaSourcePicker({workspaceId,kinds,onAdded,disabled=false,role,compact=false}: {
  workspaceId:string;kinds:Array<MediaAsset['kind']>;onAdded:(assets:MediaAsset[])=>void;disabled?:boolean;role?:string;compact?:boolean;
}) {
  const [open,setOpen]=useState(false),[source,setSource]=useState('all'),[owner,setOwner]=useState(''),[folder,setFolder]=useState('');
  const [navigation,setNavigation]=useState(false),[query,setQuery]=useState(''),[order,setOrder]=useState('newest'),[offset,setOffset]=useState(0),[view,setView]=useState('cards');
  const [page,setPage]=useState<CataloguePage|null>(null),[chosen,setChosen]=useState<MediaAsset[]>([]);
  const [message,setMessage]=useState(''),[loading,setLoading]=useState(false),[adding,setAdding]=useState(false),[syncing,setSyncing]=useState(false),[refresh,setRefresh]=useState(0);
  const [copyFiles,setCopyFiles]=useState(false);
  const [workspaceNames,setWorkspaceNames]=useState<Record<string,string>>({});
  const nameDialog=useRef<HTMLDialogElement>(null);
  const [naming,setNaming]=useState(''),[name,setName]=useState(''),[savingName,setSavingName]=useState(false);
  useEffect(()=>{if(naming)nameDialog.current?.showModal();else nameDialog.current?.close();},[naming]);
  useEffect(()=>{if(!open)return;let active=true;void listStoryWorkspaces().then(result=>{if(active)setWorkspaceNames(Object.fromEntries(result.items.filter(row=>row.title?.trim()).map(row=>[row.workspace_id,row.title])));}).catch(()=>{});return()=>{active=false;};},[open]);
  const kindsKey=kinds.join(','),scope=workspaceId+'|'+kindsKey+'|'+(role||'');
  const currentWorkspace=useRef(scope);currentWorkspace.current=scope;
  useEffect(()=>{setChosen([]);setPage(null);setOwner('');setFolder('');setOffset(0);setMessage('');setNaming('');},[workspaceId,kindsKey,role]);
  useEffect(()=>{if(!open||syncing)return;let active=true;setLoading(true);setPage(null);
    const timer=window.setTimeout(()=>void browseMediaCatalogue(workspaceId,{kinds:kindsKey,source:source==='workspaces'?'projects':source,owner:source==='workspaces'?owner:'',folder,query,offset,order})
      .then(result=>{if(active){setPage(result);}}).catch(error=>{if(active)setMessage((error as Error).message);})
      .finally(()=>{if(active)setLoading(false);}),200);
    return()=>{active=false;window.clearTimeout(timer);};
  },[workspaceId,kindsKey,open,source,owner,folder,query,offset,order,refresh,syncing]);
  const names={...workspaceNames,...page?.workspace_names};
  const workspaceLabel=(id:string)=>names[id]||'Unnamed workspace — choose a name';
  const sync=async()=>{setSyncing(true);setMessage('Checking the shared downloads folder…');try{const result=await refreshDownloadCatalogue(workspaceId);setMessage(result.errors.length?`${result.added} downloads indexed. ${result.errors.length} files could not be indexed: ${result.errors.map(e=>e.filename+': '+e.message).join('; ')}`:'Downloads are up to date.');}catch(error){setMessage((error as Error).message);}finally{setSyncing(false);setRefresh(v=>v+1);}};
  const changeSource=(next:string)=>{setSource(next);setOwner('');setFolder('');setQuery('');setOffset(0);setMessage('');setNavigation(next==='workspaces');if(next==='downloaded'&&kinds.includes('video'))void sync();};
  const key=(asset:MediaAsset)=>`${asset.workspace_id}:${asset.asset_id}`;
  const ids=chosen.map(key),shown=(page?.assets||[]).map(key);
  const select=(next:string[])=>setChosen(previous=>[...previous,...(page?.assets||[]).filter(asset=>!previous.some(item=>key(item)===key(asset)))].filter(asset=>next.includes(key(asset))));
  const add=async()=>{if(workspaceId!=='tool-library'&&!names[workspaceId]){setNaming(workspaceId);setName('');return;}const target=workspaceId,requestScope=scope;setAdding(true);setMessage('');const added:MediaAsset[]=[],completed=new Set<string>();try{
    for(const asset of chosen){if(currentWorkspace.current!==requestScope)break;added.push(await reuseCatalogueAsset(target,asset,role,copyFiles?'copy':'reference'));completed.add(key(asset));}
    if(currentWorkspace.current===requestScope){onAdded(added);setChosen([]);setMessage(`${added.length} added. Choose them in the tool below.`);}
  }catch(error){if(currentWorkspace.current===requestScope){onAdded(added);setChosen(previous=>previous.filter(asset=>!completed.has(key(asset))));setMessage(`${added.length} added; ${(error as Error).message}`);}}
  finally{setAdding(false);}};
  const saveName=async()=>{setSavingName(true);try{const result=await nameMediaWorkspace(naming,name);setWorkspaceNames(previous=>({...previous,[result.workspace_id]:result.name}));setPage(previous=>previous?{...previous,workspace_names:{...previous.workspace_names,[result.workspace_id]:result.name}}:previous);try{const saved=JSON.parse(localStorage.getItem('vibe-workspace-names-v1')||'{}');localStorage.setItem('vibe-workspace-names-v1',JSON.stringify({...saved,[result.workspace_id]:result.name}));window.dispatchEvent(new Event('vibe-workspace-names'));}catch{/* Server retains the name. */}setNaming('');setMessage('Workspace named. Your selections are kept; click Add selected to continue.');}catch(error){setMessage((error as Error).message);}finally{setSavingName(false);}};
  const locked=adding||disabled||syncing;
  const content = open&&<>
      <div className="media-source-controls">
        <button type="button" className="quiet-button" aria-expanded={navigation} onClick={()=>setNavigation(v=>!v)} disabled={locked}>Source: {sources.find(s=>s[0]===source)?.[1]} ▾</button>
        <label className="media-source-search">Search names, descriptions and tags<input type="search" disabled={locked} value={query} onChange={event=>{setQuery(event.target.value);setOffset(0);}}/></label>
        <button type="button" className="quiet-button" disabled={locked} aria-label="Change sort order" title={order==='newest'?'Newest first. Switch to oldest first.':'Oldest first. Switch to newest first.'} onClick={()=>{setOrder(order==='newest'?'oldest':'newest');setOffset(0);}}>{order==='newest'?'↓ Newest':'↑ Oldest'}</button>
        <label>View<select value={view} onChange={e=>setView(e.target.value)}><option value="cards">Cards</option><option value="list">List</option><option value="carousel">Carousel</option></select></label>
        <button type="button" className="quiet-button" disabled={locked||loading} onClick={()=>source==='downloaded'&&kinds.includes('video')?void sync():setRefresh(v=>v+1)}>Refresh sources</button>
      </div>
      {navigation&&<nav className="media-source-navigation" aria-label="Media sources">
        <div className="media-source-options">{sources.filter(s=>s[0]!=='ace_generated'||kinds.includes('audio')).map(([id,label])=><button type="button" key={id} className="quiet-button" aria-current={source===id?'true':undefined} disabled={locked} onClick={()=>changeSource(id)}>{label}{id==='workspaces'?' →':''}</button>)}</div>
        {source==='workspaces'&&<div className="media-source-workspaces" aria-label="Choose a workspace"><h3>Workspaces</h3><button type="button" className="quiet-button" disabled={locked} onClick={()=>{setOwner('');setFolder('');setOffset(0);setNavigation(false);}}>All workspaces</button>{[...new Set([...(page?.workspaces||[]),...Object.keys(workspaceNames)])].map((id,index)=><div key={id}><button type="button" className="quiet-button" disabled={locked} onClick={()=>{setOwner(id);setFolder('');setOffset(0);setNavigation(false);}}>{names[id]||`Unnamed workspace ${index+1}`} →</button>{!names[id]&&<button type="button" className="quiet-button" onClick={()=>{setNaming(id);setName('');}}>Name workspace</button>}</div>)}</div>}
      </nav>}
      <div className="media-source-breadcrumb"><span>{sources.find(s=>s[0]===source)?.[1]}{owner?' / '+workspaceLabel(owner):''}{folder?' / '+folder:''}</span>{(folder||owner)&&<button type="button" className="quiet-button" disabled={locked} onClick={()=>{if(folder)setFolder(folder.split('/').slice(0,-1).join('/'));else{setOwner('');setNavigation(true);}setOffset(0);}}>← Back</button>}</div>
      {!!page?.folders?.length&&<div className="media-source-folders">{page.folders.map(path=><button type="button" className="quiet-button" key={path} disabled={locked} onClick={()=>{setFolder(path);setOffset(0);}}>{path.split('/').pop()} →</button>)}</div>}
      <p className="media-source-hint">Showing supported {kinds.join(', ')} files, including files added directly to source folders. Add makes them available to this tool; it does not generate or attach references. Shared downloads and repertoire are linked without copying. Separate copies are limited to 512 MiB per file.</p>
      {message&&<p role="status">{message}</p>}{(loading||syncing)&&<p role="status">{syncing?'Indexing downloads without copying files…':'Loading sources…'}</p>}
      <label className="media-source-copy"><input type="checkbox" checked={copyFiles} disabled={locked} onChange={e=>setCopyFiles(e.target.checked)}/> Make a separate copy</label>
      <SelectionToggle selected={ids} shown={shown} onChange={select} disabled={locked||loading}/>
      <div className={'media-source-results media-source-'+view}>{page?.assets.map(asset=><article className="card" key={key(asset)}>
        <label><input type="checkbox" disabled={locked} checked={ids.includes(key(asset))} onChange={()=>select(ids.includes(key(asset))?ids.filter(id=>id!==key(asset)):[...ids,key(asset)])}/><span title={asset.filename}>{asset.filename}</span></label>
        {asset.kind==='image'?<img src={asset.content_url} alt={asset.filename} loading="lazy"/>:asset.kind==='video'?<video src={asset.content_url} controls muted playsInline preload="metadata" onMouseEnter={event=>void event.currentTarget.play().catch(()=>{})} onMouseLeave={event=>{event.currentTarget.pause();event.currentTarget.currentTime=0;}}/>:<audio src={asset.content_url} controls preload="none"/>}
        <small>{sources.find(s=>s[0]===asset.catalogue_source)?.[1]||asset.catalogue_source} · {names[asset.workspace_id]||'Unnamed workspace'}</small>
      </article>)}</div>
      {page&&!page.assets.length&&!loading&&!syncing&&<p>No {kinds.join(' / ')} files {query?'match this search':'in this source'}. Choose another source or refresh.</p>}
      <div className="media-source-footer"><button type="button" className="quiet-button" disabled={!offset||locked||loading} onClick={()=>setOffset(value=>Math.max(0,value-24))}>Previous</button>
        <span>{page?`${page.total?offset+1:0}–${Math.min(offset+24,page.total)} of ${page.total}`:''}</span>
        <button type="button" className="quiet-button" disabled={!page||offset+24>=page.total||locked||loading} onClick={()=>setOffset(value=>value+24)}>Next</button>
        <button type="button" className="generate-button" disabled={!chosen.length||locked||!workspaceId} onClick={()=>void add()}>{adding?'Adding…':`Add selected (${chosen.length})`}</button>
      </div>
      {naming&&<dialog ref={nameDialog} className="media-source-modal" aria-label="Name workspace" onCancel={e=>{if(savingName)e.preventDefault();else setNaming('');}}><div className="card"><h3>Name this workspace</h3><p>A name helps you find this work later. Its files and identity stay unchanged.</p><label>Workspace name<input autoFocus maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></label><div className="media-source-footer"><button type="button" className="quiet-button" disabled={savingName} onClick={()=>setNaming('')}>Cancel</button><button type="button" className="generate-button" disabled={savingName||!name.trim()} onClick={()=>void saveName()}>{savingName?'Saving…':'Save name'}</button></div></div></dialog>}
    </>;
  return compact ? <CompactPopover label="Browse media sources" onOpenChange={setOpen} disabled={disabled}><div className="media-source-picker">{content}</div></CompactPopover> : <details className="card media-source-picker" onToggle={event=>setOpen(event.currentTarget.open)}><summary>Browse media sources</summary>{content}</details>;
}
