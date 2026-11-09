import {useEffect, useRef, useState, type Dispatch, type ReactNode, type SetStateAction} from 'react';
import {Paperclip, X} from 'lucide-react';
import MediaSourcePicker from './MediaSourcePicker';
import {editorAssetMime} from './MediaPickerManagement';
import {listMediaAssets, uploadMediaAsset, type MediaAsset} from './lib/media-api';

const supported = /\.(png|jpe?g|webp|gif|mp4|mov|mkv|webm|avi|wav|mp3|flac|ogg|aac|m4a)$/i;
const image = /\.(png|jpe?g|webp|gif)$/i;

/** Shared chat imports use the library; removing an attachment only deselects it. */
export default function DirectorAttachments({owner, selected, setSelected, disabled, onBusy, children}: {
  owner:string; selected:string[]; setSelected:Dispatch<SetStateAction<string[]>>;
  disabled:boolean; onBusy:(busy:boolean)=>void; children:ReactNode;
}) {
  const input = useRef<HTMLInputElement>(null), active = useRef(true), uploading = useRef(false);
  const [assets, setAssets] = useState<Record<string,MediaAsset>>({}), [error, setError] = useState('');
  useEffect(() => {active.current = true; return () => {active.current = false;};}, []);
  useEffect(() => {
    if (!selected.length) return;
    let current = true;
    void listMediaAssets(owner, '').then(result => {
      if (current) setAssets(Object.fromEntries(result.assets.map(asset => [asset.asset_id, asset])));
    }).catch(() => {if (current) setError('Could not load attachment names. Refresh or remove unavailable attachments before sending.');});
    return () => {current = false;};
  }, [owner, selected]);
  async function attach(files:File[]) {
    if (disabled || uploading.current || !files.length) return;
    setError('');
    if (files.some(file => !supported.test(file.name))) {setError('Choose PNG, JPEG, WebP, GIF, or supported audio/video files.'); return;}
    if (selected.length + files.length > 100) {setError('Attach at most 100 media files per message.'); return;}
    const count = selected.filter(id => image.test(assets[id]?.filename || '')).length;
    if (count + files.filter(file => image.test(file.name)).length > 6) {setError('Attach up to six images per message.'); return;}
    if (files.some(file => image.test(file.name) && file.size > 20 * 1024 * 1024)) {setError('Chat images must each be 20 MiB or smaller.'); return;}
    uploading.current = true; onBusy(true);
    try {
      for (const file of files) {
        if (!active.current) break;
        const kind = image.test(file.name) ? 'image' : /\.(mp4|mov|mkv|webm|avi)$/i.test(file.name) ? 'video' : 'audio';
        const asset = await uploadMediaAsset(owner, file, `project_${kind}`);
        if (!active.current) break;
        setAssets(old => ({...old, [asset.asset_id]: asset}));
        setSelected(old => Array.from(new Set([...old, asset.asset_id])));
      }
    } catch (error) {if (active.current) setError((error as Error).message);}
    finally {uploading.current = false; if (active.current) onBusy(false);}
  }
  return <div className="director-attachment-zone" onPaste={event => {
    const files = Array.from(event.clipboardData.files);
    if (files.length) {event.preventDefault(); event.stopPropagation(); void attach(files);}
  }} onDragOver={event => {event.preventDefault(); event.stopPropagation();}} onDrop={event => {
    event.preventDefault(); event.stopPropagation();
    if (disabled || uploading.current) return;
    if (event.dataTransfer.files.length) {void attach(Array.from(event.dataTransfer.files)); return;}
    const data = event.dataTransfer.getData(editorAssetMime);
    if (data) {
      try {
        const ids:unknown = JSON.parse(data);
        if (!Array.isArray(ids) || ids.some(id => typeof id !== 'string') || selected.length + ids.length > 100) throw Error();
        setSelected(old => Array.from(new Set([...old, ...ids])));
      } catch {setError('Could not attach these items. Choose them from Browse media sources.');}
    }
  }}>
    {!!selected.length && <ul className="director-attachments" aria-label="Chat attachments">{selected.map(id => {
      const asset = assets[id];
      return <li key={id}>{asset?.kind === 'image' && <img src={asset.content_url} alt={asset.filename}/>}
        <span>{asset?.filename || id}</span><button type="button" aria-label={`Remove chat attachment ${asset?.filename || id}`} disabled={disabled || uploading.current} onClick={() => setSelected(old => old.filter(value => value !== id))}><X size={14}/></button></li>;
    })}</ul>}
    {children}
    <div className="director-attachment-actions">
      <button type="button" disabled={disabled || uploading.current} onClick={() => input.current?.click()}><Paperclip size={14}/> Attach files</button>
      <input ref={input} hidden type="file" multiple accept=".png,.jpg,.jpeg,.webp,.gif,.mp4,.mov,.mkv,.webm,.avi,.wav,.mp3,.flac,.ogg,.aac,.m4a" aria-label="Attach files to Director chat" onChange={event => {void attach(Array.from(event.target.files || [])); event.target.value = '';}}/>
      <MediaSourcePicker compact buttonLabel="Browse chat media" workspaceId={owner} kinds={['image','audio','video']} disabled={disabled || uploading.current} destination={{kind:'chat_attachment',capacity:100-selected.length,onSelect:rows=>setSelected(old=>Array.from(new Set([...old,...rows.map(row=>row.asset_id)])))}}/>
    </div>
    <small className="director-hint">{uploading.current ? 'Adding attachments…' : 'Paste or drop images, audio or video. Up to six images; audio/video analysis uses application tools. Generation references stay separate.'}</small>
    {error && <p role="alert" className="director-error">{error}</p>}
  </div>;
}
