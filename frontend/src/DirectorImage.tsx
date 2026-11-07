import {createContext, useContext, useEffect, useRef, type MutableRefObject} from 'react';
import type {AgentMessage} from './lib/agent-tasks';
import type {ImagePromptDraft} from './lib/image-api';
import {useProjectState} from './lib/project-state';

export type ImageTarget = {version: 1; request: Record<string, unknown> & {workspace_id: string; prompt: string}};
export type ImageProposal = {surface: 'image'; target: ImageTarget; draft: ImagePromptDraft};
export type ImageBridge = {prepareTarget: () => ImageTarget};
export const DirectorImage = createContext<{bridge: MutableRefObject<ImageBridge | null>; messages: AgentMessage[]} | null>(null);
type LegacyExchange = {id: string; instruction: string; suggestion?: ImagePromptDraft};

export default function DirectorImageReview({request, disabled, onApply}: {
  request: ImageTarget['request']; disabled: boolean; onApply: (draft: ImagePromptDraft) => void;
}) {
  const director = useContext(DirectorImage);
  const latest = useRef({request, disabled});
  latest.current = {request, disabled};
  const [dismissed, setDismissed] = useProjectState<string[]>('DirectorImage:dismissed', []);
  useEffect(() => {
    if (!director) return;
    const bridge = {prepareTarget: (): ImageTarget => {
      if (latest.current.disabled) throw new Error('Wait for the image controls to finish loading.');
      return {version: 1, request: latest.current.request};
    }};
    director.bridge.current = bridge;
    return () => {if (director.bridge.current === bridge) director.bridge.current = null;};
  }, [director?.bridge]);
  let legacy: LegacyExchange[] = [];
  try {
    const saved = JSON.parse(localStorage.getItem(`vibe-image-director:${request.workspace_id}:${request.asset_role}`) || '[]');
    if (Array.isArray(saved)) legacy = saved.filter(item => item && typeof item === 'object' && typeof item.instruction === 'string'
      && (!item.suggestion || typeof item.suggestion.prompt === 'string'));
  } catch { /* Keep malformed legacy storage untouched. */ }
  const proposals = director?.messages.flatMap(message => message.proposal?.surface === 'image'
    && message.proposal.target.request.workspace_id === request.workspace_id
    && message.proposal.target.request.asset_role === request.asset_role && !dismissed.includes(message.request_id)
    ? [{...message, proposal: message.proposal}] : []) || [];
  const dismiss = (id: string) => setDismissed(items => [...items, id]);
  return <section className="image-director-review" aria-label="Image prompt review">
    {proposals.map(message => {
      const proposal = message.proposal!;
      const current = JSON.stringify(request) === JSON.stringify(proposal.target.request);
      return <article className="card" key={message.request_id}>
        <h3>Review Director prompt</h3><p>{proposal.draft.prompt}</p>
        {!current && <p role="status">The prompt, target or references changed. Ask the Director for a fresh suggestion.</p>}
        <div className="studio-action-row">
          <button type="button" disabled={disabled || !current} onClick={() => {onApply(proposal.draft); dismiss(message.request_id);}}>Apply prompt</button>
          <button type="button" onClick={() => dismiss(message.request_id)}>Discard suggestion</button>
        </div>
      </article>;
    })}
    {!!legacy.length && <details><summary>Previous image conversation</summary>{legacy.map((item, index) =>
      <article key={item.id || index}><p>{item.instruction}</p><p>{item.suggestion?.prompt || 'No saved suggestion.'}</p></article>)}</details>}
  </section>;
}
