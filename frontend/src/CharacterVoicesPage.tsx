import {managedProjectId} from './lib/media-workspace';
import SelectionToggle from './SelectionToggle';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, Mic2, RefreshCw, X } from 'lucide-react';
import { AudioVoice, importComfyVoiceToWorkspace, listAudioVoices, listMediaAssets, MediaAsset } from './lib/media-api';
import { getCharacterVoiceState, getProductionSetup, listStoryScreenplays, runAutomaticCharacterVoiceMatching, setCharacterVoice, CharacterVoiceState, ProductionSetupState } from './lib/story-api';
import { getImageSelection } from './lib/image-api';
import './character-voices.css';

export default function CharacterVoicesPage({ onAssets, embedded = false, contextWorkspaceId }: { onAssets?: () => void; embedded?: boolean; contextWorkspaceId?:string }) {
  const [state, setState] = useState<CharacterVoiceState | null>(null);
  const [voices, setVoices] = useState<MediaAsset[]>([]);
  const [comfyVoices, setComfyVoices] = useState<AudioVoice[]>([]);
  const [selectedVoiceIds, setSelectedVoiceIds] = useState<string[]>([]);
  const importContext = useRef(0);
  const [images, setImages] = useState<MediaAsset[]>([]);
  const [search, setSearch] = useState('');
  const [previewVoiceId, setPreviewVoiceId] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState('');
  const [importingVoice, setImportingVoice] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [setupState, setSetupState] = useState<ProductionSetupState | null>(null);
  const [setupError, setSetupError] = useState('');
  const [setupLoading, setSetupLoading] = useState(true);
  const autoRunRevision = useRef('');
  const canEditBindings = !setupLoading && !setupError && setupState?.setup?.mode === 'assisted_manual'
    && setupState.setup.automate_steps.character_voice === false;
  const automaticMatching = !setupLoading && !setupError && setupState?.setup?.mode === 'assisted_manual'
    && setupState.setup.automate_steps.character_voice === true;
  useEffect(()=>{if(state)window.dispatchEvent(new Event('vibe-character-voices-changed'));},[state]);
  const bindingByCharacter = useMemo(() => new Map((state?.bindings || []).map(item => [item.character_id, item.voice_asset_id])), [state]);
  const speechByCharacter = useMemo(() => new Map((state?.speech_statuses || []).map(item => [item.character_id, item])), [state]);
  const decisionByCharacter = useMemo(() => new Map((state?.automation_decisions || []).map(item => [item.character_id, item])), [state]);
  const filteredVoices = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return voices;
    return voices.filter(asset => [
      asset.filename, asset.description || '', ...(asset.tags || []), asset.metadata?.comfyui_voice_catalog?.name || '',
    ].some(value => value.toLowerCase().includes(query)));
  }, [voices, search]);

  const refresh = async (force = false) => {
    importContext.current += 1; setSelectedVoiceIds([]);
    setLoading(true); setError(''); setMessage(''); setSetupLoading(true); setSetupError(''); setSetupState(null);
    try {
      const query = new URLSearchParams(window.location.hash.split('?')[1] || '');
      const routeWorkspace = query.get('workspace_id');
      const id = managedProjectId() || contextWorkspaceId || routeWorkspace || localStorage.getItem('vibe-story-selected-v1') || '';
      if (!id.startsWith('story-')) throw new Error('Open a story and accept its screenplay to assign character voices. Use Audio Studio for standalone voices.');
      const revisions = await listStoryScreenplays(id, 0, 100);
      const accepted = revisions.items.find(item => item.accepted && !item.stale);
      if (!accepted) throw new Error('This story has no current accepted screenplay. Review and accept one on the Screenplay page.');
      const [initialBindings, audio, visual, catalog] = await Promise.all([
        getCharacterVoiceState(id, accepted.screenplay_revision_id),
        listMediaAssets(id, 'audio'), listMediaAssets(id, 'image'), listAudioVoices(),
      ]);
      setWorkspaceId(id);
      setVoices(audio.assets.filter(asset => asset.roles.includes('voice_master')));
      setPreviewVoiceId(current => audio.assets.some(asset => asset.asset_id === current && asset.roles.includes('voice_master'))
        ? current
        : '');
      const savedCatalogIds = new Set(audio.assets.map(asset => asset.metadata?.comfyui_voice_catalog?.catalog_id).filter(Boolean));
      const availableComfyVoices = catalog.filter(voice => !savedCatalogIds.has(voice.id));
      setComfyVoices(availableComfyVoices);
      setSelectedVoiceIds([]);
      const selections = await Promise.all(initialBindings.characters.map(async character => {
        const result = await getImageSelection(id, accepted.screenplay_revision_id, 'character', character.record_id);
        return visual.assets.find(asset=>asset.asset_id===result.selection?.asset_id);
      }));
      setImages(selections.filter((asset):asset is MediaAsset=>!!asset));
      try {
        const setup = await getProductionSetup(id, accepted.screenplay_revision_id);
        setSetupState(setup);
        // Keep the canonical character list visible in every mode so the page can
        // explain why bindings are unavailable; the controls remain mode-gated.
        setState(initialBindings);
        if (!setup.setup) setSetupError('Save Automation & Parameters before assigning screenplay character voices.');
        else if (setup.setup.mode === 'fully_automated') setSetupError('Manual voice assignment is skipped in Fully automated mode.');
        else if (setup.setup.automate_steps.character_voice) {
          const runKey = `${id}:${accepted.screenplay_revision_id}`;
          if (!force && autoRunRevision.current === runKey) { setState(initialBindings); return; }
          autoRunRevision.current = runKey;
          let matched: CharacterVoiceState;
          try { matched = await runAutomaticCharacterVoiceMatching(id, accepted.screenplay_revision_id); }
          catch (e) { autoRunRevision.current = ''; throw e; }
          setState(matched);
          const result = matched.automation_result || [];
          const count = result.filter(item => item.status === 'matched').length;
          const unresolved = result.filter(item => item.status === 'ambiguous' || item.status === 'unmatched').length;
          setMessage(`Automatic voice matching assigned ${count} ${count === 1 ? 'voice' : 'voices'}; ${unresolved} need a choice.`);
        } else setState(initialBindings);
      } catch (e) { setState(initialBindings); setSetupError(`Could not verify or run the saved voice setup: ${(e as Error).message}`); }
    } catch (e) { setState(null); setVoices([]); setImages([]); setError((e as Error).message); }
    finally { setLoading(false); setSetupLoading(false); }
  };
  useEffect(() => { void refresh(); return () => { importContext.current += 1; }; }, []);

  useEffect(()=>{
    const updateMaster=(event:Event)=>{
      const detail=(event as CustomEvent).detail;
      if(detail.workspaceId!==workspaceId||detail.revisionId!==state?.screenplay_revision_id||detail.targetType!=='character')return;
      setImages(current=>[detail.asset,...current.filter(asset=>asset.metadata?.production_image_job?.settings?.lineage?.target_record_id!==detail.targetId)]);
    };
    window.addEventListener('vibe-image-master-selected',updateMaster);
    return()=>window.removeEventListener('vibe-image-master-selected',updateMaster);
  },[workspaceId,state?.screenplay_revision_id]);

  const save = async (characterId: string, voiceId: string | null) => {
    if (!state || saving || !(canEditBindings || automaticMatching)) return;
    setSaving(characterId); setError(''); setMessage('');
    try {
      setState(await setCharacterVoice(workspaceId, state.screenplay_revision_id, characterId, voiceId));
      setMessage(voiceId ? 'Voice assignment saved.' : 'Voice assignment cleared.');
    } catch (e) { setError((e as Error).message); }
    finally { setSaving(''); }
  };
  const importVoices = async () => {
    const pending = comfyVoices.filter(voice => selectedVoiceIds.includes(voice.id));
    if (!workspaceId || !pending.length || importingVoice) return;
    const context = importContext.current;
    setImportingVoice(true); setError(''); setMessage('');
    let addedCount = 0;
    const failures: string[] = [];
    try {
      for (const voice of pending) {
        if (context !== importContext.current) break;
        try {
          const { asset } = await importComfyVoiceToWorkspace(workspaceId, voice.id);
          if (context !== importContext.current) break;
          setVoices(current => current.some(item => item.asset_id === asset.asset_id) ? current : [...current, asset]);
          setComfyVoices(current => current.filter(item => item.id !== voice.id));
          setSelectedVoiceIds(current => current.filter(id => id !== voice.id));
          addedCount += 1;
          setMessage(`${addedCount} of ${pending.length} voices added to this workspace…`);
        } catch (e) {
          if (context !== importContext.current) break;
          failures.push(`${voice.name}: ${(e as Error).message}`);
        }
      }
      if (context === importContext.current) {
        if (addedCount) setSearch('');
        setMessage(`${addedCount} voice${addedCount === 1 ? '' : 's'} added to this workspace. Assign them to characters below.`);
        if (failures.length) setError(`Could not add ${failures.length} voice(s). They remain selected for retry. ${failures.join('; ')}`);
      }
    } finally { if (context === importContext.current) setImportingVoice(false); }
  };
  const chooseVoice = async (characterId: string, value: string) => {
    if (!value.startsWith('comfy:')) { await save(characterId, value || null); return; }
    if (!state || saving || importingVoice || !(canEditBindings || automaticMatching)) return;
    const context = importContext.current;
    const id = value.slice(6);
    setImportingVoice(true); setSaving(characterId); setError('');
    try {
      const {asset} = await importComfyVoiceToWorkspace(workspaceId, id);
      if (context !== importContext.current) return;
      setVoices(current=>[...current.filter(row=>row.asset_id!==asset.asset_id),asset]);
      setComfyVoices(current=>current.filter(row=>row.id!==id));
      setSelectedVoiceIds(current=>current.filter(row=>row!==id));
      setSearch('');
      const updated = await setCharacterVoice(workspaceId, state.screenplay_revision_id, characterId, asset.asset_id);
      if (context !== importContext.current) return;
      setState(updated); setMessage('Voice imported and assigned. It is also available for other characters.');
    } catch(error) { if(context===importContext.current)setError((error as Error).message); }
    finally {if(context===importContext.current){setImportingVoice(false);setSaving('');}}
  };
  const imageFor = (characterId: string) => images.find(asset => {
    const lineage = asset.metadata?.production_image_job?.settings?.lineage;
    return lineage?.target_record_id === characterId && lineage.target_type === 'character';
  });
  const previewVoice = voices.find(asset => asset.asset_id === previewVoiceId);

  return <section className={embedded ? 'character-voices-embedded' : 'content-wrap image-assets-page'} aria-label="Character voice assignments">
    {!embedded && <><div className="page-heading"><div><div className="eyebrow">CHARACTERS & ASSETS</div><h1>Character voices</h1><p>Assign saved voice references to characters in the accepted screenplay.</p></div><button className="quiet-button" onClick={() => void refresh(true)} disabled={loading || !!saving || importingVoice}><RefreshCw size={15}/> Reload</button></div>
    <div className="studio-subtabs" aria-label="Character asset sections"><button type="button" className="quiet-button" onClick={onAssets}>Images</button><button type="button" className="generate-button" aria-current="page"><Mic2 size={15}/> Voices</button></div></>}
    {error && <div className="error-banner" role="alert">{error} {!state && <a href="#/screenplay">Open Screenplay</a>}</div>}
    {message && <p role="status">{message}</p>}
    {state && <div className={canEditBindings || automaticMatching ? 'card' : 'error-banner'} role={canEditBindings || automaticMatching ? 'status' : 'alert'}>
      {setupLoading ? 'Checking saved Automation & Parameters…' : canEditBindings
        ? 'Manual character voice assignment is enabled for this Assisted manual setup.'
        : automaticMatching
          ? 'Automatic matching uses explicit character names or voice guidance in saved asset metadata. Only one clear match is assigned. You can change or clear any assignment.'
        : setupError || 'Manual character voice assignment is unavailable.'}
      {setupState?.setup?.mode==='fully_automated'&&<p>Your imported voices are saved below. To assign them, choose Assisted manual in <a href={'#/setup?workspace_id='+encodeURIComponent(workspaceId)}>Automation &amp; Parameters</a>. Fully automated runs skip character assets and voice assignments.</p>}
    </div>}
    {state && <div className="card voice-library-tools"><label>Search voice previews<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search names, descriptions and tags"/></label>{search && <button className="quiet-button" onClick={()=>setSearch('')}>Clear voice search</button>}<span>{search ? `${filteredVoices.length} matching · ` : ''}{voices.length} voice{voices.length === 1 ? '' : 's'} in this workspace</span></div>}
    {state && voices.length > 0 && <div className="card voice-audition-tools"><label>Preview a voice before assigning<select aria-label="Preview a voice before assigning" value={previewVoiceId} onChange={event => setPreviewVoiceId(event.target.value)}><option value="">Choose a voice to preview</option>{(previewVoice && !filteredVoices.some(asset=>asset.asset_id===previewVoice.asset_id) ? [previewVoice,...filteredVoices] : filteredVoices).map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}</select></label>{previewVoice ? <audio controls preload="none" src={previewVoice.content_url} aria-label={`Preview voice sample ${previewVoice.filename}`}/> : <small>Audition a workspace voice here; this does not change any character assignment.</small>}</div>}
    {state && comfyVoices.length > 0 && <section className="card voice-catalog-batch" aria-label="Add ComfyUI voices">
      <h2>ComfyUI voice files</h2><p>Add voice references to this workspace, then assign them to characters below.</p>
      <details className="voice-catalog-dropdown"><summary>Choose voices · {selectedVoiceIds.length} selected · {comfyVoices.length} available</summary><div className="voice-catalog-menu"><div className="voice-catalog-actions"><SelectionToggle selected={selectedVoiceIds} shown={comfyVoices.map(voice=>voice.id)} onChange={setSelectedVoiceIds} disabled={importingVoice}/><span>{selectedVoiceIds.length} selected · {comfyVoices.length} available</span><button type="button" className="generate-button" disabled={importingVoice || !selectedVoiceIds.length} onClick={()=>void importVoices()}>{importingVoice ? 'Adding voices…' : `Add selected (${selectedVoiceIds.length})`}</button></div>
      <div className="voice-catalog-options">{comfyVoices.map(voice=><label key={voice.id}><input type="checkbox" aria-label={`Select voice ${voice.name}`} checked={selectedVoiceIds.includes(voice.id)} disabled={importingVoice} onChange={event=>setSelectedVoiceIds(current=>event.target.checked ? [...current,voice.id] : current.filter(id=>id!==voice.id))}/><span>{voice.name}<small>{voice.source}</small></span></label>)}</div></div></details>
    </section>}
    {loading && <p role="status">Loading screenplay characters and voice library…</p>}
    {state && <section className="voice-character-list" aria-label="Character voice assignments">{state.characters.map(character => {
      const selected = bindingByCharacter.get(character.record_id) || '';
      const decision = decisionByCharacter.get(character.record_id);
      const speech = speechByCharacter.get(character.record_id);
      const canResolve = automaticMatching;
      const image = imageFor(character.record_id);
      const voice = voices.find(item => item.asset_id === selected);
      // Preview search must not hide imported choices from character assignments.
      const visibleVoices = voices;
      return <article className="card voice-character-card" key={character.record_id}>
        {image ? <img src={image.content_url} alt={`${character.name} reference`} /> : <div className="voice-character-placeholder"><Mic2 size={21}/></div>}
        <div className="voice-character-copy"><h2>{character.name}</h2><p>{character.detail || 'No character description in the accepted graph.'}</p></div>
        <div className="voice-character-control"><label>Voice reference<select aria-label={`Voice for ${character.name}`} value={selected} onChange={event => void chooseVoice(character.record_id, event.target.value)} disabled={!!saving || importingVoice || loading || !(canEditBindings || canResolve)}>
          <option value="">No voice assigned</option>{selected && !voices.some(item => item.asset_id === selected) && <option value={selected}>Previously assigned voice (unavailable)</option>}
          {visibleVoices.map(item => <option key={item.asset_id} value={item.asset_id}>{item.filename}{item.tags?.length ? ` · ${item.tags.join(', ')}` : ''}</option>)}
          {comfyVoices.length>0&&<optgroup label="ComfyUI voices · import and assign">{comfyVoices.map(voice=><option key={voice.id} value={'comfy:'+voice.id}>{voice.name}</option>)}</optgroup>}
        </select></label>
        {!(canEditBindings || canResolve)&&voices.length>0&&<small>{voices.length} imported voices available. Enable Assisted manual to assign one.</small>}
        {voice && <audio controls preload="none" src={voice.content_url} aria-label={`Preview ${voice.filename}`}/>}
        {!selected && speech && <small className={`voice-speaking-status voice-speaking-status-${speech.status}`} role="status">{speech.status === 'speaking' ? 'Speaks in the accepted screenplay · voice not assigned' : speech.status === 'narrator' ? 'Narrator · voice not assigned' : speech.status === 'not_speaking' ? 'No labeled dialogue · voice optional' : 'Speaker status unclear · review dialogue labels'} — {speech.reason}</small>}
        {voice?.description && <small>{voice.description}</small>}
        {decision && <small className="voice-match-status" role="status">{decision.status === 'matched' ? 'Automatically matched' : decision.status === 'resolved_manually' ? 'Match resolved by you' : decision.status === 'ambiguous' ? 'Several possible matches · choose one' : decision.status === 'unmatched' ? 'No direct match · choose a voice' : decision.status === 'not_speaking' ? 'No voice needed for this screenplay' : 'Existing voice kept'} — {decision.reason}</small>}
        {saving === character.record_id && <small role="status">Saving…</small>}{selected && <button type="button" className="text-button" onClick={() => void save(character.record_id, null)} disabled={!!saving || !(canEditBindings || canResolve)}><X size={14}/> Clear voice</button>}
        </div>
      </article>;
    })}{!state.characters.length && <div className="card media-empty"><p>No canonical characters are present in this accepted graph.</p></div>}</section>}
    <p className="graph-disclosure"><Check size={14}/> One voice can be assigned to several characters. Changing a binding affects future work only; existing generated audio stays unchanged.</p>
  </section>;
}
