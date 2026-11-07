import type {CatalogueFilters} from './lib/media-api';

export default function MediaCatalogueFilters({value,onChange,audio,disabled}: {
  value:CatalogueFilters;onChange:(value:CatalogueFilters)=>void;audio:boolean;disabled:boolean;
}) {
  const change=(key:keyof CatalogueFilters,next:string)=>onChange({...value,[key]:next});
  const count=Object.values(value).filter(Boolean).length;
  return <details className="media-catalogue-filters"><summary>Filters{count?` · ${count}`:''}</summary>
    <fieldset disabled={disabled}>
      {audio&&<label>Audio category<select value={value.audio_category||''} onChange={e=>change('audio_category',e.target.value)}>
        <option value="">All audio</option><option value="voice">Voice</option><option value="dialogue">Dialogue</option><option value="sfx">Sound effects</option><option value="music">Music</option>
      </select></label>}
      <label>Content index<select value={value.content_index||''} onChange={e=>change('content_index',e.target.value)}>
        <option value="">All media</option><option value="indexed">Content indexed</option><option value="unindexed">No current content index</option>
      </select></label>
      <label>Added from<input type="date" value={value.created_after||''} onChange={e=>change('created_after',e.target.value)}/></label>
      <label>Added through<input type="date" value={value.created_before||''} onChange={e=>change('created_before',e.target.value)}/></label>
      <button type="button" className="quiet-button" disabled={!count} onClick={()=>onChange({})}>Clear filters</button>
    </fieldset>
    <small>Content indexed means a saved embedding matches this file’s hash. It does not certify analysis quality or search across projects by meaning.</small>
  </details>;
}
