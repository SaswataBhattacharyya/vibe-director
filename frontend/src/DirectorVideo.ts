import {createContext, type MutableRefObject} from 'react';
import type {AgentMessage} from './lib/agent-tasks';

export type VideoPromptTarget = {version:1; workspace_id:string; clip_id:string; revision_id:string; prompt:string;
  settings:Record<string,unknown>; history:Array<{user:string; prompt?:string}>};
export type VideoPromptProposal = {surface:'video'; target:VideoPromptTarget; suggestion:{replacement:string; explanation?:string}};
export const DirectorVideo = createContext<{bridge:MutableRefObject<{prepareTarget:()=>VideoPromptTarget}|null>; messages:AgentMessage[]}|null>(null);
