import {useRef,useState} from 'react';
export type ViewInput={id:string;name:string;url?:string;views?:Record<string,string>};
type ImageInput={id:string;url:string;name:string};
type Group={key:string;name:string;views:Record<string,ImageInput>};
type Crop={view:string;x:number;y:number;w:number;h:number};
const directions={two:['front','back'],four:['front','left','back','right']};
export async function upload3D(file:File):Promise<ImageInput>{
 const response=await fetch('/api/trellis/upload',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});
 const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Image upload failed');
 return {...data,name:file.name};
}
export default function MultiViewInputs({batch,profile,setProfile,disabled,onChange,confirmed,setConfirmed,onBusy}:{batch:boolean;profile:'two'|'four';setProfile:(p:'two'|'four')=>void;disabled:boolean;onChange:(items:ViewInput[])=>void;confirmed:boolean;setConfirmed:(v:boolean)=>void;onBusy:(v:boolean)=>void}){
 const [source,setSource]=useState<'images'|'sheet'>('images'),[groups,setGroups]=useState<Group[]>([{key:crypto.randomUUID(),name:'Object 1',views:{}}]),[error,setError]=useState(''),[working,setWorking]=useState(false);
 const [sheet,setSheet]=useState<{image:HTMLImageElement;key:string;sourceId:string}|null>(null),[columns,setColumns]=useState(2),[rows,setRows]=useState(1),[crops,setCrops]=useState<Crop[]>([]),[previews,setPreviews]=useState<string[]>([]);
 const folder=useRef<HTMLInputElement>(null);const views=directions[profile];
 const commit=(next:Group[])=>{setGroups(next);setConfirmed(false);onChange(next.map(g=>({id:g.views.front?.id||g.key,name:g.name,views:Object.fromEntries(Object.entries(g.views).filter(([v])=>views.includes(v)).map(([v,image])=>[v,image.id]))})));};
 const perform=async(fn:()=>Promise<void>)=>{setWorking(true);onBusy(true);setConfirmed(false);setError('');try{await fn();}catch(e){setError((e as Error).message);}finally{setWorking(false);onBusy(false);}};
 const pick=async(key:string,view:string,file:File)=>perform(async()=>{const image=await upload3D(file);commit(groups.map(g=>g.key===key?{...g,views:{...g.views,[view]:image}}:g));});
 const setGrid=(cols:number,rowCount:number)=>{
  setCrops(views.map((view,i)=>({view,x:Math.round((i%cols)*100/cols*100)/100,y:Math.round(Math.floor(i/cols)*100/rowCount*100)/100,w:Math.floor(100/cols*100)/100,h:Math.floor(100/rowCount*100)/100})));
  setPreviews([]);setConfirmed(false);
 };
 const openSheet=(key:string,file:File)=>perform(async()=>{
  const original=await upload3D(file);const image=new Image();image.src=original.url;await image.decode();
  if(image.naturalWidth*image.naturalHeight>40000000)throw new Error('Sheet exceeds 40 megapixels.');
  setSheet({image,key,sourceId:original.id});const r=profile==='four'?2:1;setRows(r);setColumns(2);setGrid(2,r);
 });
 const cropCanvases=()=>{
  if(!sheet)throw new Error('Choose a sheet first.');
  if(new Set(crops.map(c=>c.view)).size!==views.length||crops.some(c=>!views.includes(c.view)))throw new Error('Assign each direction exactly once.');
  return crops.map(c=>{
   if([c.x,c.y,c.w,c.h].some(v=>!Number.isFinite(v))||c.x<0||c.y<0||c.w<=0||c.h<=0||c.x+c.w>100.01||c.y+c.h>100.01)throw new Error('Crop rectangles must fit inside the sheet.');
   const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(sheet.image.naturalWidth*c.w/100));canvas.height=Math.max(1,Math.round(sheet.image.naturalHeight*c.h/100));
   canvas.getContext('2d')!.drawImage(sheet.image,sheet.image.naturalWidth*c.x/100,sheet.image.naturalHeight*c.y/100,sheet.image.naturalWidth*c.w/100,sheet.image.naturalHeight*c.h/100,0,0,canvas.width,canvas.height);return canvas;
  });
 };
 const preview=()=>perform(async()=>{setPreviews(cropCanvases().map(c=>c.toDataURL('image/png')));});
 const applyCrops=()=>perform(async()=>{
  const canvases=cropCanvases();const side=Math.max(...canvases.map(c=>Math.max(c.width,c.height)));if(side*side>40000000)throw new Error('Padded crops exceed 40 megapixels.');
  const mapped:Record<string,ImageInput>={};
  for(let i=0;i<canvases.length;i++){
   const canvas=document.createElement('canvas');canvas.width=side;canvas.height=side;canvas.getContext('2d')!.drawImage(canvases[i],Math.floor((side-canvases[i].width)/2),Math.floor((side-canvases[i].height)/2));
   const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('Could not crop sheet.')),'image/png'));
   mapped[crops[i].view]=await upload3D(new File([blob],`${crops[i].view}.png`,{type:'image/png'}));
  }
  commit(groups.map(g=>g.key===sheet!.key?{...g,views:mapped}:g));setSheet(null);setPreviews([]);
 });
 const importFolder=(files:File[])=>perform(async()=>{
  const eligible=files.filter(f=>/\.(png|jpe?g|webp)$/i.test(f.name));if(eligible.length>2000)throw new Error('Maximum 500 objects / 2000 view files.');
  const mapped=new Map<string,Record<string,File>>();
  for(const file of eligible){const view=file.name.replace(/\.[^.]+$/,'').toLowerCase();if(!views.includes(view))continue;const path=file.webkitRelativePath||file.name;const key=path.includes('/')?path.slice(0,path.lastIndexOf('/')):'Object';const row=mapped.get(key)||{};if(row[view])throw new Error(`Duplicate ${view} in ${key}. Rename/map images before importing.`);row[view]=file;mapped.set(key,row);}
  if(!mapped.size)throw new Error('Name images front, back, left and right. Batch: use one subject subfolder per object.');
  if(!batch&&mapped.size>1)throw new Error('Choose a folder containing views of only one object, or switch to Batch.');
  if(mapped.size>500)throw new Error('Batch limit is 500 objects.');
  const next:Group[]=[];
  for(const [name,files] of mapped){const images:Record<string,ImageInput>={};for(const [view,file] of Object.entries(files))images[view]=await upload3D(file);next.push({key:crypto.randomUUID(),name,views:images});}
  commit(next);
 });
 const valid=groups.length>0&&groups.every(g=>views.every(v=>g.views[v])&&new Set(views.map(v=>g.views[v].id)).size===views.length);
 const locked=disabled||working;
 return <section className="card multiview-inputs"><h2>Multi-view inputs</h2><p>Use the <strong>same subject and pose</strong> from different angles. Keep scale and canvas dimensions consistent, with a simple background. Two views: front/back. Four views: front/left/back/right. Three-quarter views are not side views.</p>
  <div className="studio-action-row"><label>Input method<select aria-label="Multi-view input method" value={source} disabled={locked} onChange={e=>{setSource(e.target.value as 'images'|'sheet');setSheet(null);setConfirmed(false);}}><option value="images">Separate view images</option><option value="sheet">Single image with multiple views</option></select></label><label>Views per object<select value={profile} disabled={locked} onChange={e=>{setProfile(e.target.value as 'two'|'four');setSheet(null);commit([{key:crypto.randomUUID(),name:'Object 1',views:{}}]);}}><option value="two">2 · Front + Back</option><option value="four">4 · Front + Left + Back + Right</option></select></label></div>
  {source==='images'&&<div className="studio-action-row"><input type="file" hidden ref={folder} {...{webkitdirectory:''}} multiple onChange={e=>{void importFolder(Array.from(e.target.files||[]));e.target.value='';}}/><button disabled={locked} onClick={()=>folder.current?.click()}>Choose view folder</button><span>Folders fill labelled slots; review assignments below.</span></div>}
  {groups.map((group,index)=><article className="multiview-object" key={group.key}><div className="studio-action-row"><label>Object name<input value={group.name} disabled={locked} onChange={e=>commit(groups.map(g=>g.key===group.key?{...g,name:e.target.value}:g))}/></label>{batch&&<button disabled={locked} onClick={()=>commit(groups.filter(g=>g.key!==group.key))}>Remove object {index+1}</button>}</div>
   {source==='sheet'&&<label className="multiview-drop" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f&&!locked)void openSheet(group.key,f);}}>Upload or drop a multi-view sheet<input type="file" accept="image/png,image/jpeg,image/webp" disabled={locked} onChange={e=>{if(e.target.files?.[0])void openSheet(group.key,e.target.files[0]);e.target.value='';}}/></label>}
   <div className="multiview-slots">{views.map(view=><div className="multiview-slot" key={view} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f&&!locked)void pick(group.key,view,f);}}><strong>{view[0].toUpperCase()+view.slice(1)}</strong>{group.views[view]?<><img src={group.views[view].url} alt={`${group.name} ${view}`}/><button disabled={locked} onClick={()=>{const next={...group.views};delete next[view];commit(groups.map(g=>g.key===group.key?{...g,views:next}:g));}}>Remove {view}</button></>:<p>Choose or drop this view</p>}<label>Choose / replace {view}<input aria-label={`Upload ${view} for object ${index+1}`} type="file" accept="image/png,image/jpeg,image/webp" disabled={locked} onChange={e=>{if(e.target.files?.[0])void pick(group.key,view,e.target.files[0]);e.target.value='';}}/></label></div>)}</div>
  </article>)}
  {batch&&<button disabled={locked||groups.length>=500} onClick={()=>commit([...groups,{key:crypto.randomUUID(),name:`Object ${groups.length+1}`,views:{}}])}>Add object</button>}
  {sheet&&<section className="multiview-sheet"><h3>Split and review sheet</h3><p>Choose a grid, adjust crop percentages and assign directions. The model receives separate crops, never the whole sheet. Keep each full subject inside its crop.</p><img className="multiview-sheet-source" src={sheet.image.src} alt="Original multi-view sheet"/><div className="studio-action-row"><label>Columns<select value={columns} disabled={locked} onChange={e=>{const n=Number(e.target.value);setColumns(n);setGrid(n,Math.ceil(views.length/n));setRows(Math.ceil(views.length/n));}}>{[1,2,4].map(n=><option key={n}>{n}</option>)}</select></label><span>{rows} row(s)</span></div>
   <div className="multiview-crops">{crops.map((crop,i)=><div key={i}><label>Crop {i+1} direction<select value={crop.view} disabled={locked} onChange={e=>{setCrops(crops.map((c,j)=>j===i?{...c,view:e.target.value}:c));setPreviews([]);}}>{views.map(v=><option key={v}>{v}</option>)}</select></label>{(['x','y','w','h'] as const).map(key=><label key={key}>{({x:'Left',y:'Top',w:'Width',h:'Height'})[key]} %<input type="number" min={0} max={100} step={.1} value={crop[key]} disabled={locked} onChange={e=>{setCrops(crops.map((c,j)=>j===i?{...c,[key]:Number(e.target.value)}:c));setPreviews([]);}}/></label>)}{previews[i]&&<img src={previews[i]} alt={`Preview ${crop.view}`}/>}</div>)}</div><div className="studio-action-row"><button disabled={locked} onClick={()=>void preview()}>Preview crops</button><button disabled={locked||previews.length!==views.length} onClick={()=>void applyCrops()}>Use reviewed crops</button><button disabled={locked} onClick={()=>setSheet(null)}>Cancel splitting</button></div></section>}
  {working&&<p role="status">Preparing images…</p>}{error&&<p role="alert">{error}</p>}<label className="multiview-confirm"><input type="checkbox" checked={confirmed} disabled={locked||!valid||!!sheet} onChange={e=>setConfirmed(e.target.checked)}/>I reviewed every direction and confirm these are aligned views of the same subject per object.</label>
 </section>;
}
