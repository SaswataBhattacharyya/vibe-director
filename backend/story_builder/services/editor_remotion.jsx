// Trusted composition only. Model-authored JSX, CSS, paths and scripts are never executed.
import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, OffthreadVideo, Sequence, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import input from './composition.json';
const {plan,sources,processed} = input;
const frames = seconds => Math.round(seconds*plan.fps);
const source = id => staticFile(sources[id]);
function Layer({layer}) {
  const frame=useCurrentFrame(), time=frame/plan.fps;
  const values={x:0,y:0,rotation:0,scale:1,opacity:layer.opacity};
  for(const key of Object.keys(values)) {
    const points=[{time:0,value:values[key]},...(layer.motion||[]).filter(k=>key in k).map(k=>({time:k.time,value:k[key]}))];
    const unique=points.filter((p,i)=>i===points.length-1||points[i+1].time!==p.time);
    values[key]=unique.length===1?unique[0].value:interpolate(time,unique.map(p=>p.time),unique.map(p=>p.value),{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  }
  if(layer.kind==='audio')return <Audio src={source(layer.asset_id)} trimBefore={frames(layer.start)} volume={layer.volume}/>;
  const style={position:'absolute',left:layer.x,top:layer.y,width:layer.width,height:layer.height,zIndex:layer.z,opacity:values.opacity,
    transform:`translate(${values.x}px,${values.y}px) rotate(${layer.rotation+values.rotation}deg) scale(${values.scale})`,objectFit:layer.fit};
  if(layer.kind==='image')return <Img src={source(layer.asset_id)} style={style}/>;
  if(layer.kind==='video')return <OffthreadVideo src={source(layer.asset_id)} trimBefore={frames(layer.start)} volume={layer.volume} style={style}/>;
  if(layer.kind==='shape')return <div style={{...style,backgroundColor:layer.color,borderRadius:layer.shape==='ellipse'?'50%':0}}/>;
  return <div style={{...style,color:layer.color,fontSize:layer.font_size,fontFamily:'sans-serif',whiteSpace:'pre-wrap',overflow:'hidden'}}>{layer.text}</div>;
}
function Film() {
  let at=0;
  return <AbsoluteFill style={{backgroundColor:'black'}}>
    {plan.clips.map((clip,index)=>{
      const from=frames(at), length=frames(clip.render_duration);at+=clip.render_duration;
      const src=staticFile(processed[index]||sources[clip.asset_id]);
      const style={width:'100%',height:'100%',objectFit:clip.fit};
      return <Sequence key={index} from={from} durationInFrames={length}>
        {clip.mime.startsWith('video/')?<OffthreadVideo src={src} trimBefore={processed[index]?0:frames(clip.start)} muted={Boolean(plan.audio)} style={style}/>:<Img src={src} style={style}/>}
        {clip.caption&&<div style={{position:'absolute',bottom:'10%',left:'10%',right:'10%',textAlign:'center',color:'white',fontSize:32,fontFamily:'sans-serif'}}>{clip.caption}</div>}
      </Sequence>;
    })}
    {plan.audio&&<Sequence durationInFrames={Math.min(frames(plan.audio.end-plan.audio.start),frames(at))}><Audio src={source(plan.audio.asset_id)} trimBefore={frames(plan.audio.start)}/></Sequence>}
    {(plan.layers||[]).map(layer=><Sequence key={layer.id} from={frames(layer.at)} durationInFrames={frames(layer.duration)}><Layer layer={layer}/></Sequence>)}
  </AbsoluteFill>;
}
const duration=plan.clips.reduce((sum,c)=>sum+c.render_duration,0);
registerRoot(()=> <Composition id="VibeFilm" component={Film} width={plan.width} height={plan.height} fps={plan.fps} durationInFrames={frames(duration)}/>);
