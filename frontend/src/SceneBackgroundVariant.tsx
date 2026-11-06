import type {MediaAsset} from './lib/media-api';
import {useProjectState} from './lib/project-state';

export default function SceneBackgroundVariant({assets, disabled, onPrepare}: {
  assets: MediaAsset[]; disabled: boolean;
  onPrepare: (base: MediaAsset, prompt: string) => void;
}) {
  const [baseId, setBaseId] = useProjectState('SceneBackgroundVariant:base', '');
  const [scene, setScene] = useProjectState('SceneBackgroundVariant:scene', '');
  const [condition, setCondition] = useProjectState('SceneBackgroundVariant:condition', '');
  const base = assets.find(asset => asset.asset_id === baseId && asset.kind === 'image');
  return <section className="card scene-background-variant" aria-label="Scene background variation">
    <h2>Same place, a different scene</h2>
    <p>Keep a base location reference. Use image editing to show its condition in a particular scene—ruined, flooded, covered in slime, or lit differently.</p>
    <div className="image-fields">
      <label>Base location image<select value={baseId} onChange={event => setBaseId(event.target.value)} disabled={disabled}>
        <option value="">Choose an existing image</option>{assets.filter(asset => asset.kind === 'image' && !asset.archived_at).map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.filename}</option>)}
      </select></label>
      <label>Scene or shot label<input value={scene} onChange={event => setScene(event.target.value)} placeholder="Scene 5 · after the collapse" maxLength={200} disabled={disabled}/></label>
    </div>
    <label>What changes in this scene?<textarea value={condition} onChange={event => setCondition(event.target.value)} placeholder="The walls are cracked and covered in green slime. Keep the same doorway, camera angle and room layout." maxLength={3000} rows={3} disabled={disabled}/></label>
    <button disabled={disabled || !base || !scene.trim() || !condition.trim()} onClick={() => {
      if (base) onPrepare(base, `Scene background variation: ${scene.trim()}. Use the supplied base location image as the continuity reference. Preserve the location's recognizable layout and architecture. Scene-specific condition: ${condition.trim()}. Environment only, without characters.`);
    }}>Prepare scene variation</button>
    <small>Prepares an editable Qwen Image Edit request with the base image attached. Review it and click Generate; the original stays intact. No screenplay is required.</small>
  </section>;
}
