import { useEffect, useMemo, useRef, useState } from 'react';
import { FolderOpen, RefreshCw, Trash2, Image as ImageIcon, Paperclip } from 'lucide-react';
import './local-image-folder-browser.css';

type DirectoryHandleLike = FileSystemDirectoryHandle & { values(): AsyncIterable<FileSystemHandle> };
type LocalImage = { key: string; file: File; relativePath: string };
type Props = { title?: string; maxReferences?: number; referencesEnabled?: boolean; onUseAsReference?: (files: File[]) => void; onAttachToChat?: (files: File[]) => void };
// These formats are accepted by the server-side temporary-reference validator.
const isImage = (file: File) => ['image/png','image/jpeg','image/webp'].includes(file.type.toLowerCase()) || /\.(png|jpe?g|webp)$/i.test(file.name);

function HintedControl({ id, hint, children }: { id: string; hint: string; children: React.ReactNode }) {
  const [visible, setVisible] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancel = () => { if (timer.current) clearTimeout(timer.current); timer.current = null; };
  useEffect(() => cancel, []);
  return <div className={`local-image-hint-control${visible ? ' is-visible' : ''}`} onMouseEnter={() => { cancel(); timer.current = setTimeout(() => setVisible(true), 2000); }} onMouseLeave={() => { cancel(); setVisible(false); }} onFocusCapture={() => { cancel(); setVisible(true); }} onBlurCapture={() => { cancel(); setVisible(false); }}>
    {children}
    <span className="local-image-hint-tooltip" id={`${id}-hint`} role="tooltip">{hint}</span>
  </div>;
}

async function scanDirectory(root: DirectoryHandleLike): Promise<LocalImage[]> {
  const found: LocalImage[] = [];
  const walk = async (dir: DirectoryHandleLike, prefix: string) => {
    for await (const entry of dir.values()) {
      if (entry.name.startsWith('.')) continue;
      if (entry.kind === 'directory') await walk(entry as DirectoryHandleLike, `${prefix}${entry.name}/`);
      else if (entry.kind === 'file') {
        const file = await (entry as FileSystemFileHandle).getFile();
        if (isImage(file)) found.push({ key: `${prefix}${entry.name}:${file.lastModified}:${file.size}`, file, relativePath: `${prefix}${entry.name}` });
      }
    }
  };
  await walk(root, '');
  return found;
}

export default function LocalImageFolderBrowser({ title = 'Reference images', maxReferences = 3, referencesEnabled = false, onUseAsReference, onAttachToChat }: Props) {
  const [folderName, setFolderName] = useState('');
  const [rootHandle, setRootHandle] = useState<DirectoryHandleLike|null>(null);
  const [images, setImages] = useState<LocalImage[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [order, setOrder] = useState<'newest'|'oldest'>('newest');
  const [view, setView] = useState<'cards'|'list'|'table'>('cards');
  const [filter, setFilter] = useState('');
  const [error, setError] = useState('');
  const shown = useMemo(() => images.filter(item => item.relativePath.toLocaleLowerCase().includes(filter.toLocaleLowerCase())).sort((a,b) => order === 'newest' ? b.file.lastModified-a.file.lastModified : a.file.lastModified-b.file.lastModified), [images, order, filter]);
  const previews = useMemo(() => new Map(images.map(item => [item.key, URL.createObjectURL(item.file)])), [images]);
  useEffect(() => () => previews.forEach(url => URL.revokeObjectURL(url)), [previews]);
  const chosen = shown.filter(item => selected.includes(item.key));
  const chooseFolder = async () => {
    setError('');
    try {
      const picker = (window as Window & { showDirectoryPicker?: (options?: { mode?: 'read'|'readwrite' }) => Promise<DirectoryHandleLike> }).showDirectoryPicker;
      if (!picker) throw new Error('This browser does not support folder access. Open Vibe Director in a browser with the File System Access API.');
      const handle = await picker({ mode: 'readwrite' }) as DirectoryHandleLike;
      setRootHandle(handle); setFolderName(handle.name); setSelected([]); setImages(await scanDirectory(handle));
    } catch (reason) { if ((reason as DOMException).name !== 'AbortError') setError((reason as Error).message || 'Could not read this folder.'); }
  };
  const refresh = async () => { if (rootHandle) { try { setImages(await scanDirectory(rootHandle)); setSelected([]); setError(''); } catch (reason) { setError((reason as Error).message); } } else await chooseFolder(); };
  const toggle = (key: string) => setSelected(old => old.includes(key) ? old.filter(item => item !== key) : [...old, key]);
  const deleteSelected = async () => {
    if (!selected.length) return;
    const targets = images.filter(item => selected.includes(item.key));
    const confirmation = targets.map(item => item.relativePath).join('\n');
    if (!window.confirm(`Permanently delete ${targets.length} image file${targets.length===1?'':'s'} from the selected folder?\n\n${confirmation}`)) return;
    if (!rootHandle) return;
    const failures: string[] = [];
    for (const item of targets) {
      try {
        const parts = item.relativePath.split('/').filter(Boolean);
        const filename = parts.pop();
        if (!filename) { failures.push(item.relativePath); continue; }
        let directory: DirectoryHandleLike = rootHandle;
        for (const part of parts) directory = await directory.getDirectoryHandle(part) as DirectoryHandleLike;
        await directory.removeEntry(filename);
      } catch { failures.push(item.relativePath); }
    }
    setImages(await scanDirectory(rootHandle));
    if (failures.length) {
      setSelected(targets.filter(item => failures.includes(item.relativePath)).map(item => item.key));
      setError(`Deleted ${targets.length - failures.length} of ${targets.length} selected images. Could not delete:\n${failures.join('\n')}`);
    } else { setSelected([]); setError(''); }
  };
  const drag = (event: React.DragEvent, item: LocalImage) => { event.dataTransfer.effectAllowed = 'copy'; event.dataTransfer.setData('application/x-vibe-local-image', item.key); event.dataTransfer.setData('text/plain', item.relativePath); event.dataTransfer.items.add(item.file); };
  const attach = () => { if (chosen.length) onAttachToChat?.(chosen.map(item => item.file)); };
  const useRefs = () => { if (chosen.length && referencesEnabled && chosen.length <= maxReferences) onUseAsReference?.(chosen.map(item => item.file)); };
  return <section className="local-image-browser" aria-label={title}>
    <div className="local-image-browser-heading"><div><h2>{title}</h2><small>{folderName ? `${folderName} · ${images.length} images including subfolders` : 'Choose a folder to browse image files, including subfolders.'}</small></div><button type="button" className="quiet-button" onClick={() => void chooseFolder()}><FolderOpen size={15}/> Choose folder</button>{folderName && <button type="button" className="quiet-button" onClick={() => void refresh()}><RefreshCw size={15}/> Refresh</button>}</div>
    {folderName && <><div className="local-image-browser-toolbar"><input aria-label="Filter reference images by filename" placeholder="Filter by filename…" value={filter} onChange={event=>setFilter(event.target.value)}/><HintedControl id="image-sort" hint="Choose whether the newest or oldest modified images appear first."><select id="image-sort" aria-label="Sort reference images" aria-describedby="image-sort-hint" value={order} onChange={event=>setOrder(event.target.value as 'newest'|'oldest')}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></HintedControl><HintedControl id="image-view" hint="Choose cards, a compact list, or a table-style view."><select id="image-view" aria-label="Reference image view" aria-describedby="image-view-hint" value={view} onChange={event=>setView(event.target.value as typeof view)}><option value="cards">Cards</option><option value="list">List</option><option value="table">Table</option></select></HintedControl><button type="button" onClick={()=>setSelected(shown.map(item=>item.key))}>Select all</button><button type="button" onClick={()=>setSelected([])}>Deselect all</button><span>{selected.length} selected</span><button type="button" className="quiet-button" disabled={!selected.length||!referencesEnabled||selected.length>maxReferences} title={!referencesEnabled?'Selected workflow does not accept image references':selected.length>maxReferences?`Choose up to ${maxReferences} images`:''} onClick={useRefs}><ImageIcon size={15}/> Use as reference</button><button type="button" className="quiet-button" disabled={!selected.length} onClick={attach}><Paperclip size={15}/> Attach to chat</button><button type="button" className="quiet-button" disabled={!selected.length} onClick={()=>void deleteSelected()}><Trash2 size={15}/> Delete selected</button></div>
    <div className={`local-image-grid local-image-grid-${view}`}>{shown.map(item=><button type="button" key={item.key} draggable onDragStart={event=>drag(event,item)} aria-pressed={selected.includes(item.key)} className={selected.includes(item.key)?'selected':''} onClick={()=>toggle(item.key)}><img src={previews.get(item.key)} alt="" loading="lazy"/><span>{item.relativePath}</span></button>)}</div></>}
    {error && <p className="error-banner" role="alert">{error}</p>}
  </section>;
}
