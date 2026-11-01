// Chromium supplies directory entries on drop; chooser uses webkitRelativePath.
type Entry={name:string;isFile:boolean;file:(ok:(file:File)=>void,fail:(e:DOMException)=>void)=>void;createReader:()=>{readEntries:(ok:(entries:Entry[])=>void,fail:(e:DOMException)=>void)=>void}};
export async function aceDroppedFiles(items:DataTransferItem[],fallback:File[]):Promise<File[]> {
  const entries=items.map(item=>item.webkitGetAsEntry?.() as Entry|null);
  if(!entries.some(Boolean))return fallback;
  const walk=async(entry:Entry,parent=''):Promise<File[]>=>{
    const path=parent+entry.name;
    if(entry.isFile){const file=await new Promise<File>((ok,fail)=>entry.file(ok,fail));Object.defineProperty(file,'webkitRelativePath',{value:path});return [file];}
    const reader=entry.createReader(),children:Entry[]=[];
    for(;;){const batch=await new Promise<Entry[]>((ok,fail)=>reader.readEntries(ok,fail));if(!batch.length)break;children.push(...batch);}
    return (await Promise.all(children.map(child=>walk(child,path+'/')))).flat();
  };
  return (await Promise.all(entries.filter((entry):entry is Entry=>Boolean(entry)).map(entry=>walk(entry)))).flat();
}
