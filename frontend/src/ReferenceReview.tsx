import { useState } from 'react';
import type { Draft, R2VReferenceDraft } from './App';
import type { MediaAsset } from './lib/media-api';

type Kind = 'r2vImages'|'r2vVideos'|'r2vAudios';
const kinds: Kind[] = ['r2vImages','r2vVideos','r2vAudios'];
const reviewKey = (kind: Kind, ref: R2VReferenceDraft) => JSON.stringify([kind,ref.assetId,ref.role,ref.intent,ref.includePairedSoundtrack,ref.audioIntent]);
const counts = (draft: Draft) => [draft.r2vImages?.length || 0, draft.r2vVideos?.length || 0, (draft.r2vAudios?.length || 0) + (draft.r2vVideos || []).filter(ref=>ref.includePairedSoundtrack).length];
const exceeds = (draft: Draft) => counts(draft).some((count,index)=>count>[9,3,3][index]);

export default function ReferenceReview({draft,assets,locked,onChange}: {draft:Draft;assets:MediaAsset[];locked:boolean;onChange:(change:(draft:Draft)=>Draft)=>void}) {
  const [excluded,setExcluded] = useState<string[]>([]);
  const [choosing,setChoosing] = useState(false);
  const rows = kinds.flatMap(kind=>(draft[kind] || []).map(ref=>({kind,ref,key:`${kind}:${ref.assetId}`})));
  const retained = {...draft,...Object.fromEntries(kinds.map(kind=>[kind,(draft[kind] || []).filter(ref=>!excluded.includes(`${kind}:${ref.assetId}`))]))};
  const continuity = rows.some(({ref})=>/character|world|identity|location/i.test(ref.role));
  // Scope checks inspect written instructions, not the media's visual or audio content.
  const conflicts = rows.filter(({kind,ref})=>continuity && /style|motion|camera|appearance|sound|audio or voice/i.test(ref.role) && (!/only|do not change|preserve.*identity/i.test(ref.intent) || !!draft.referenceReviews?.[reviewKey(kind,ref)]));
  const name = (ref:R2VReferenceDraft) => assets.find(asset=>asset.asset_id===ref.assetId)?.filename || ref.assetId;
  return <div className="reference-review">
    {(exceeds(draft)||choosing) && <section className="notice warning" aria-label="Choose references to retain">
      <h4>Director needs your choice: reference capacity</h4>
      <p>Automatic and extra references share 9 image, 3 video and 3 audio slots. Video soundtracks also use audio slots. Choose which references to retain; generation stays blocked while the limits are exceeded.</p>
      {!choosing ? <button className="quiet-button" disabled={locked} onClick={()=>{setExcluded([]);setChoosing(true);}}>Choose references to retain</button> : <>
        {rows.map(({ref,key})=><label className="r2v-check" key={key}><input type="checkbox" checked={!excluded.includes(key)} disabled={locked} onChange={event=>setExcluded(previous=>event.target.checked?previous.filter(value=>value!==key):[...previous,key])}/>Keep {name(ref)} · {ref.role}{ref.includePairedSoundtrack?' + soundtrack':''}</label>)}
        <p>Retained: {counts(retained)[0]} images / {counts(retained)[1]} videos / {counts(retained)[2]} audio</p>
        <button className="quiet-button" disabled={locked||exceeds(retained)} onClick={()=>{onChange(previous=>({...previous,...Object.fromEntries(kinds.map(kind=>[kind,(previous[kind] || []).filter(ref=>!excluded.includes(`${kind}:${ref.assetId}`))])),r2vCollatedPrompt:undefined}));setChoosing(false);}}>Use retained references</button>
        <button className="quiet-button" disabled={locked} onClick={()=>setChoosing(false)}>Cancel</button>
      </>}
    </section>}
    {conflicts.map(({kind,ref,key})=>{
      const fingerprint=reviewKey(kind,ref), decision=draft.referenceReviews?.[fingerprint];
      const scope=kind==='r2vAudios'?'Use only its sound style and timing; preserve assigned speaker voices and dialogue.':'Use only its style, camera or motion guidance; preserve selected character identity, clothing and location appearance.';
      return <section className="notice" key={key} aria-label="Reference instruction review"><b>Director reference review · {name(ref)}</b><p>This {ref.role} instruction may compete with identity or location references. {scope}</p>
        {decision ? <p>Saved for this shot: {decision}</p> : <><p>Instruction-scope check only; media content has not been compared.</p><button className="quiet-button" disabled={locked} onClick={()=>onChange(previous=>{const updated={...ref,intent:`${ref.intent} ${scope}`};return {...previous,[kind]:(previous[kind] || []).map(row=>row.assetId===ref.assetId?updated:row),referenceReviews:{...previous.referenceReviews,[reviewKey(kind,updated)]:'Director scope applied'},r2vCollatedPrompt:undefined};})}>Apply suggested scope</button><button className="quiet-button" disabled={locked} onClick={()=>onChange(previous=>({...previous,referenceReviews:{...previous.referenceReviews,[fingerprint]:'User kept the original instruction override'}}))}>Keep my instruction</button></>}
      </section>;
    })}
  </div>;
}
