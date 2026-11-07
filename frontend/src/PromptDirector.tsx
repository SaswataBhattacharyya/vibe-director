import {useContext,useEffect,useRef,useState} from 'react';
import {Check,Download,LoaderCircle,MessageSquare,Trash2} from 'lucide-react';
import {exportPromptSkill,getPromptGuidance,savePromptGuidance,PromptChange,PromptGuidance,PromptTurn} from './lib/prompt-director-api';
import './storyboard.css';
import {DirectorPrompts, type PromptTarget} from './DirectorScreenplay';
import {useProjectState} from './lib/project-state';

export default function PromptDirector({workspace,revision,shotPrompts,shotWorkflows,disabled,onApplyShots,onBusy}:{
  workspace:string;revision:string;shotPrompts:Record<string,string>;shotWorkflows:Record<string,string>;disabled:boolean;
  onApplyShots:(changes:PromptChange[])=>void;onBusy:(busy:boolean)=>void;
}){
  const [state,setState]=useState<PromptGuidance|null>(null),[assets,setAssets]=useState<Record<string,string>>({});
  const [focus,setFocus]=useState('all'),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [busy,setBusy]=useState('Loading prompts and conversation…');
  const [selected,setSelected]=useState<Record<string,number[]>>({});
  const bridge=useContext(DirectorPrompts);
  const [dismissed,setDismissed]=useProjectState<string[]>('PromptDirector:dismissed',[]);
  const locked=disabled||!!busy||!state;
  const assetsDirty=!!state&&JSON.stringify(assets)!==JSON.stringify(state.assets);
  useEffect(()=>{
    let live=true;
    setState(null);setAssets({});setSelected({});setBusy('Loading prompts and conversation…');setError('');
    void getPromptGuidance(workspace,revision).then(value=>{if(live){setState(value);setAssets(value.assets);}})
      .catch(e=>{if(live)setError(e.message);}).finally(()=>{if(live)setBusy('');});
    return()=>{live=false;};
  },[workspace,revision]);
  useEffect(()=>{onBusy(!!busy);return()=>onBusy(false);},[busy,onBusy]);
  const prompts=()=>{
    const result:Record<string,string>={};
    for(const [key,value] of Object.entries(shotPrompts))if(focus==='all'||focus==='video'||focus===`shot:${key}`)result[`shot:${key}`]=value;
    for(const [id,target] of Object.entries(state?.targets||{}))if(focus==='all'||focus===target.scope||focus===`image:${id}`)
      result[`image:${id}`]=assets[id]??seed(target);
    return result;
  };
  const latest=useRef({workspace,revision,locked,prompts,shotWorkflows});
  latest.current={workspace,revision,locked,prompts,shotWorkflows};
  useEffect(()=>{
    if(!bridge)return;
    let active=true;
    const adapter={
      prepareTarget:():PromptTarget=>{
        const scope=latest.current;
        if(scope.locked)throw new Error('Wait for Prompt Preparation to load and save or finish active edits first.');
        const context=scope.prompts();
        if(!Object.keys(context).length)throw new Error('Choose a focus with available prompts.');
        const workflows=Object.fromEntries(Object.entries(scope.shotWorkflows).filter(([key])=>`shot:${key}` in context).map(([key,value])=>[`shot:${key}`,value]));
        return {version:1,workspace_id:scope.workspace,screenplay_revision_id:scope.revision,prompts:context,workflows};
      },
      refresh:async()=>{
        const scope=latest.current;
        const value=await getPromptGuidance(scope.workspace,scope.revision);
        if(active&&latest.current.workspace===scope.workspace&&latest.current.revision===scope.revision){
          setState(value);
          setSelected(old=>Object.fromEntries(value.items.map(item=>[item.key,old[item.key]??(item.proposal?.changes||item.proposal?.lessons||[]).map((_,index)=>index)])));
        }
      }
    };
    bridge.current=adapter;
    return()=>{active=false;if(bridge.current===adapter)bridge.current=null;};
  },[bridge]);
  const persist=async(nextAssets=assets,lessons=state!.lessons,keepLocalAssets=false)=>{
    const saved=await savePromptGuidance(workspace,revision,state!.revision,lessons,nextAssets);
    setState(saved);if(!keepLocalAssets)setAssets(saved.assets);
  };
  const apply=async(item:PromptTurn)=>{
    if(!state||locked)return;
    setError('');setBusy('Applying reviewed changes…');
    try{
      const indices=selected[item.key]||[];
      if(item.mode==='learn'){
        const lessons=(item.proposal?.lessons||[]).filter((_,i)=>indices.includes(i));
        const combined=[...state.lessons];
        for(const lesson of lessons)if(!combined.some(old=>old.scope===lesson.scope&&old.rule===lesson.rule))combined.push(lesson);
        await persist(state.assets,combined,true);setNotice('Approved rules saved for this project. Future prompt preparation will use them.');
      }else{
        const changes=(item.proposal?.changes||[]).filter((_,i)=>indices.includes(i));
        const current:Record<string,string>={...Object.fromEntries(Object.entries(shotPrompts).map(([k,v])=>[`shot:${k}`,v])),
          ...Object.fromEntries(Object.entries(state.targets).map(([k,v])=>[`image:${k}`,assets[k]??seed(v)]))};
        if(changes.some(c=>current[c.key]!==c.before))throw new Error('A prompt changed after this proposal. Prepare new changes; local edits have been retained.');
        const next={...assets};for(const change of changes)if(change.key.startsWith('image:'))next[change.key.slice(6)]=change.value;
        // Save image briefs first. A failed compare-and-swap must not partly apply shot edits.
        if(changes.some(c=>c.key.startsWith('image:'))){
          const savedAssets={...state.assets};for(const change of changes)if(change.key.startsWith('image:'))savedAssets[change.key.slice(6)]=change.value;
          await persist(savedAssets,state.lessons,true);setAssets(next);
        }
        onApplyShots(changes.filter(c=>c.key.startsWith('shot:')));
        setNotice('Reviewed changes applied. Save shot prompt drafts below to use edited shot briefs in production.');
      }
      setSelected(old=>({...old,[item.key]:[]}));
    }catch(e){setError((e as Error).message);}finally{setBusy('');}
  };
  const saveAssets=async()=>{setBusy('Saving image briefs…');setError('');try{await persist();setNotice('Character and background briefs saved. Image preparation will adapt them to its selected workflow and actual references.');}catch(e){setError((e as Error).message);}finally{setBusy('');}};
  const removeLesson=async(index:number)=>{setBusy('Updating rules…');setError('');try{await persist(state!.assets,state!.lessons.filter((_,i)=>i!==index),true);}catch(e){setError((e as Error).message);}finally{setBusy('');}};
  const download=async()=>{setBusy('Exporting skill…');setError('');try{
    const value=await exportPromptSkill(workspace,revision);const url=URL.createObjectURL(new Blob([value.text],{type:'text/markdown'}));
    const a=document.createElement('a');a.href=url;a.download=value.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){setError((e as Error).message);}finally{setBusy('');}};
  const label=(key:string)=>key.startsWith('shot:')?`Shot ${key.slice(5)}`:state?.targets[key.slice(6)]?.name||key;
  return <>
    <section className="card board-stack prompt-director" aria-label="Prompt Director">
      <div className="board-heading"><div><h2><MessageSquare size={18}/> Direct the prompts</h2>
        <p>Discuss prompts in the shared Director. Ask it to prepare agreed changes or draft reusable learning rules, then review them here.</p></div></div>
      {error&&<p role="alert" className="error-banner">{error}</p>}{notice&&<p role="status" className="prompt-notice">{notice}</p>}
      <label className="board-field">Conversation focus<select value={focus} disabled={locked} onChange={e=>setFocus(e.target.value)}>
        <option value="all">All prompts</option><option value="video">Video shot prompts</option><option value="character">Character prompts</option><option value="world">Scene background prompts</option>
        {Object.keys(shotPrompts).map(key=><option key={key} value={`shot:${key}`}>Shot {key}</option>)}
        {Object.entries(state?.targets||{}).map(([id,t])=><option key={id} value={`image:${id}`}>{t.name}</option>)}
      </select></label>
      {state?.items.filter(item=>item.proposal&&!dismissed.includes(item.key)).map(item=><article className="screenplay-chat-review" key={item.key}>
        <p>{item.reply}</p>
        {item.revision_id!==revision?<small>Proposal from an earlier screenplay revision.</small>:<>
          <h3>{item.mode==='learn'?'Review learning rules':'Review prompt changes'}</h3>
          <div className="board-changes">{(item.proposal!.changes||item.proposal!.lessons||[]).map((value,index)=><label key={index}>
            <input type="checkbox" disabled={locked} checked={(selected[item.key]||[]).includes(index)} onChange={e=>setSelected(old=>({...old,[item.key]:e.target.checked?[...(old[item.key]||[]),index]:(old[item.key]||[]).filter(i=>i!==index)}))}/>
            <span>{'key' in value?<><b>{label(value.key)}</b><small>Before: {value.before}</small><span>After: {value.value}</span></>:<><b>{value.scope}</b><span>{value.rule}</span></>}</span>
          </label>)}</div>
          <div className="board-actions">
            <button className="quiet-button" disabled={locked||!selected[item.key]?.length} onClick={()=>void apply(item)}><Check size={15}/>{item.mode==='learn'?'Save selected rules':'Apply selected prompt changes'}</button>
            <button className="quiet-button" disabled={locked} onClick={()=>setDismissed(old=>[...old,item.key])}>Discard suggestion</button>
          </div>
        </>}
      </article>)}
      {state?.items.some(item=>item.status!=='complete')&&<p role="status">A saved prompt request has no confirmed result. Reload its conversation before starting another request.</p>}
      {busy&&<p role="status"><LoaderCircle className="spin" size={16}/>{busy}</p>}
      {!!state?.items.length&&<details><summary>Previous prompt conversation</summary>{state.items.map(item=><article key={item.key}><p><strong>You</strong> {item.instruction}</p><p><strong>Director</strong> {item.reply||item.status}</p></article>)}</details>}
      <button className="quiet-button" disabled={locked} onClick={()=>void bridge?.current?.refresh().catch(e=>setError(e.message))}>Reload prompt conversation</button>
      <details className="prompt-rules"><summary>Saved prompting rules ({state?.lessons.length||0}) · this project</summary>
        <p className="muted">Approved rules guide future video and image prompt preparation with any configured Director model. Existing saved or frozen production requests stay as reviewed.</p>
        {state?.lessons.map((lesson,index)=><div className="prompt-rule" key={index}><p><b>{lesson.scope}</b> · {lesson.rule}</p><button className="quiet-button" disabled={locked} aria-label={`Remove prompting rule ${index+1}`} onClick={()=>void removeLesson(index)}><Trash2 size={14}/></button></div>)}
        <button className="quiet-button" disabled={locked||!state?.lessons.length} onClick={()=>void download()}><Download size={15}/> Export SKILL.md</button>
      </details>
    </section>
    <section className="card board-stack" aria-label="Character and world prompts"><div><h2>Character &amp; background prompts</h2><p>Reusable image briefs linked to the accepted screenplay’s characters and locations. Image preparation adapts these briefs to the chosen workflow and attached references before generation.</p></div>
      {state&&(['character','world'] as const).map(scope=><details className="prompt-assets-group" key={scope}><summary>{scope==='character'?'Characters':'Scene backgrounds'} ({Object.values(state.targets).filter(t=>t.scope===scope).length})</summary>
        {!Object.values(state.targets).some(t=>t.scope===scope)&&<p className="muted">No canonical {scope==='character'?'characters':'locations'} in this screenplay’s source graph. Nothing has been invented.</p>}
        {Object.entries(state.targets).filter(([,t])=>t.scope===scope).map(([id,t])=><label className="board-field" key={id}>{t.name}<textarea rows={4} maxLength={6999} disabled={locked} value={assets[id]??seed(t)} onChange={e=>setAssets(old=>({...old,[id]:e.target.value}))}/></label>)}
      </details>)}
      <div className="board-actions"><button className="quiet-button" disabled={locked||!assetsDirty} onClick={()=>void saveAssets()}>Save character &amp; background briefs</button>
        <a className="quiet-button" href={`#/assets?step=character_images&workspace_id=${encodeURIComponent(workspace)}`}>Characters &amp; Voices</a>
        <a className="quiet-button" href={`#/assets?step=world_images&workspace_id=${encodeURIComponent(workspace)}`}>Scene Backgrounds</a></div>
      {assetsDirty&&<small role="status">Unsaved image briefs. Save before leaving this page.</small>}
    </section>
  </>;
}
function seed(target:{scope:string;name:string;detail:string}){
  return target.scope==='character'?`${target.name}. ${target.detail}\nDescribe established visible appearance and clothing only. One character, plain white studio background.`
    :`${target.name}. ${target.detail}\nEmpty environment without characters. Preserve the established architecture and layout.`;
}
