import type {EditorLayer} from './lib/editor-api';

type Motion = NonNullable<EditorLayer['motion']>;
const properties = ['x','y','scale','rotation','opacity'] as const;
const labels = {x:'Horizontal offset', y:'Vertical offset', scale:'Scale', rotation:'Rotation', opacity:'Opacity'};

export default function EditorLayerMotion({layer,index,onChange}:{layer:EditorLayer;index:number;onChange:(motion:Motion)=>void}) {
  const motion=layer.motion||[];
  const nextTime=motion.length?Math.min(layer.duration,motion[motion.length-1].time+.5):0;
  const update=(frameIndex:number,key:string,value:string)=>onChange(motion.map((frame,i)=>{
    if(i!==frameIndex)return frame;
    const changed={...frame};
    if(value==='')delete changed[key as keyof typeof changed];
    else Object.assign(changed,{[key]:Number(value)});
    return changed;
  }));
  return <details><summary>Animation keyframes</summary>
    <p>Times start at the beginning of this layer. Leave a property empty to keep its previous value.</p>
    {motion.map((frame,frameIndex)=><div className="editor-visual-fields" key={frameIndex}>
      <label>Time (seconds)<input aria-label={`Layer ${index+1} keyframe ${frameIndex+1} time`} type="number" min={0} max={layer.duration} step=".01" value={frame.time} onChange={e=>update(frameIndex,'time',e.target.value)}/></label>
      {properties.map(key=><label key={key}>{labels[key]}<input aria-label={`Layer ${index+1} keyframe ${frameIndex+1} ${key}`} type="number" step=".01" value={frame[key]??''} min={key==='opacity'?0:key==='scale'?.01:undefined} max={key==='opacity'?1:key==='scale'?20:undefined} onChange={e=>update(frameIndex,key,e.target.value)}/></label>)}
      <button type="button" onClick={()=>onChange(motion.filter((_,i)=>i!==frameIndex))}>Remove keyframe {frameIndex+1}</button>
    </div>)}
    <button type="button" disabled={motion.length>=100||motion.length>0&&nextTime<=motion[motion.length-1].time} onClick={()=>onChange([...motion,{time:nextTime,opacity:1}])}>Add keyframe to layer {index+1}</button>
  </details>;
}
