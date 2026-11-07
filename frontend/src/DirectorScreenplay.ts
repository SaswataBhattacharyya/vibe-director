import {createContext, type MutableRefObject} from 'react';

export type ScreenplayTarget = {version:1; workspace_id:string; screenplay_revision_id:string};
export type ScreenplayBridge = {prepareTarget:()=>ScreenplayTarget; refresh:()=>Promise<void>};
export const DirectorScreenplay = createContext<MutableRefObject<ScreenplayBridge|null>|null>(null);

export type PromptTarget = ScreenplayTarget & {prompts:Record<string,string>; workflows:Record<string,string>};
export type PromptBridge = {prepareTarget:()=>PromptTarget; refresh:()=>Promise<void>};
export const DirectorPrompts = createContext<MutableRefObject<PromptBridge|null>|null>(null);
