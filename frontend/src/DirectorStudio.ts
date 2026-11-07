import {createContext, type MutableRefObject} from 'react';
import type {AgentMessage} from './lib/agent-tasks';
export type StudioTarget = {version:1;workspace_id:string;name:'trellis'|'audio';context:Record<string,unknown>;history:Array<{text:string;reply:string}>};
export type StudioProposal = {surface:'studio';target:StudioTarget;settings:Record<string,number>};
export const DirectorStudio = createContext<{bridge:MutableRefObject<{prepareTarget:()=>StudioTarget}|null>;messages:AgentMessage[]}|null>(null);
