import EditorLayerMotion from './EditorLayerMotion';
import type {EditorLayer, EditorPlan, EditorProject} from './lib/editor-api';

export default function EditorLayers({plan, project, disabled, onChange}:{plan:EditorPlan;project:EditorProject;disabled:boolean;onChange:(value:EditorPlan)=>void}) {
  const layers=plan.layers||[];
  const duration=plan.clips.reduce((total,c)=>total+(c.render_duration??c.end-c.start)-(c.transition?.duration||0),0);
  const update=(id:string,patch:Partial<EditorLayer>)=>onChange({...plan,layers:layers.map(l=>l.id===id?{...l,...patch}:l)});
  const add=(kind:EditorLayer['kind'],source?:typeof project.selection[number])=>{
    const length=source&&kind!=='image'?Math.min(duration,source.end-source.start):duration;
    onChange({...plan,layers:[...layers,{...source,id:`item-${crypto.randomUUID().slice(0,8)}`,kind,at:0,duration:length,
      x:0,y:0,width:plan.width,height:plan.height,opacity:1,rotation:0,z:200+layers.length,volume:1,
      ...(kind==='text'?{text:'Your text',font_size:48,color:'#ffffff'}:{}),
      ...(kind==='shape'?{shape:'rectangle',color:'#ffffff'}:{})}]});
  };
  return <fieldset disabled={disabled||plan.backend==='kdenlive'} className="editor-layers"><legend>Layers & animation</legend>
    <p>Layer selected media, text and shapes over the edit. Set timing, placement and animation for each layer.</p>
    <div className="editor-visual-toolbar"><button type="button" onClick={()=>add('text')}>Add text layer</button><button type="button" onClick={()=>add('shape')}>Add shape layer</button>
      <label>Add selected media<select value="" onChange={event=>{const source=project.selection[Number(event.target.value)];if(source)add(source.mime?.split('/')[0] as EditorLayer['kind'],source);}}>
        <option value="">Choose an attached source…</option>{project.selection.filter(row=>row.mime?.match(/^(image|video|audio)\//)).map(row=><option key={`${row.asset_id}-${row.start}`} value={project.selection.indexOf(row)}>{row.filename||row.asset_id} · {row.start}–{row.end}s</option>)}</select></label>
    </div>
    {layers.map((layer,index)=><details key={layer.id} open className="editor-layer"><summary>{index+1}. {layer.kind} · {layer.filename||layer.text?.slice(0,40)||layer.id}</summary>
      <div className="editor-visual-fields">
        {(['at','duration',...(layer.kind==='audio'?['volume']:['x','y','width','height','rotation','opacity','z'])] as const).map(key=><label key={key}>{key}<input type="number" step=".01" value={Number(layer[key as keyof EditorLayer]??(key==='opacity'||key==='volume'?1:0))} onChange={event=>update(layer.id,{[key]:Number(event.target.value)})}/></label>)}
        {layer.kind==='text'&&<><label>Text<textarea aria-label={`Layer ${index+1} text`} value={layer.text||''} maxLength={4000} onChange={event=>update(layer.id,{text:event.target.value})}/></label><label>Font size<input type="number" min={8} max={512} value={layer.font_size??48} onChange={event=>update(layer.id,{font_size:Number(event.target.value)})}/></label></>}
        {['text','shape'].includes(layer.kind)&&<label>Color<input type="color" value={layer.color||'#ffffff'} onChange={event=>update(layer.id,{color:event.target.value})}/></label>}
        {layer.kind==='shape'&&<label>Shape<select value={layer.shape||'rectangle'} onChange={event=>update(layer.id,{shape:event.target.value as 'rectangle'|'ellipse'})}><option>rectangle</option><option>ellipse</option></select></label>}
      </div>
      {layer.kind!=='audio'&&<EditorLayerMotion layer={layer} index={index} onChange={motion=>update(layer.id,{motion})}/>}
      <button type="button" onClick={()=>onChange({...plan,layers:layers.filter(l=>l.id!==layer.id)})}>Remove layer {index+1}</button>
    </details>)}
    <small>Save the timeline proposal to validate all ranges and animation before approval. Kdenlive joins keep their existing two-clip workflow.</small>
  </fieldset>;
}
