import {useRef} from 'react';
import type {MediaAsset} from './lib/media-api';

export const editorAssetMime='application/x-vibe-editor-assets';
export type EditorMediaActions = {
  onImport:(files:File[])=>Promise<void>;
  onAttach:(assets:MediaAsset[])=>Promise<void>;
  onDelete:(ids:string[])=>Promise<boolean>;
  onPreview:(asset:MediaAsset)=>void;
  onDiscover:(assets:MediaAsset[])=>void;
};

/** File/folder consent and deletion belong to project management, never discovery. */
export default function MediaPickerManagement({kind,disabled,selected,onImport,onDelete}:{
  kind:string; disabled:boolean; selected:MediaAsset[];
  onImport:EditorMediaActions['onImport']; onDelete:EditorMediaActions['onDelete'];
}) {
  const files=useRef<HTMLInputElement>(null), folder=useRef<HTMLInputElement|null>(null);
  const receive=(input:HTMLInputElement)=>{const chosen=Array.from(input.files||[]);input.value='';void onImport(chosen);};
  return <div className="editor-asset-controls">
    <input ref={files} hidden type="file" multiple accept={`${kind}/*`} aria-label="Choose asset files" disabled={disabled} onChange={e=>receive(e.currentTarget)}/>
    <input ref={el=>{folder.current=el;el?.setAttribute('webkitdirectory','');}} hidden type="file" multiple aria-label="Choose asset folder" disabled={disabled} onChange={e=>receive(e.currentTarget)}/>
    <button type="button" disabled={disabled} onClick={()=>files.current?.click()}>Choose files</button>
    <button type="button" disabled={disabled} onClick={()=>folder.current?.click()}>Choose folder</button>
    <button type="button" disabled={disabled||!selected.length} onClick={()=>void onDelete(selected.map(row=>row.asset_id))}>Delete selected permanently</button>
    <small>Imports include matching {kind} files from every subfolder. Deletion is limited to selected current-project assets.</small>
  </div>;
}
