import {createContext, type MutableRefObject} from 'react';
import type {AgentMessage} from './lib/agent-tasks';

export type StoryTarget = {version:1; workspace_id:string; base_revision_id:string;
  start_codepoint:number; end_codepoint:number; expected_text:string};
export const DirectorStory = createContext<{bridge:MutableRefObject<{prepareTarget:()=>StoryTarget}|null>;
  messages:AgentMessage[]}|null>(null);
