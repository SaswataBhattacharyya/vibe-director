import {createContext, type MutableRefObject} from 'react';
export type MusicTarget = {version:1;workspace_id:string;project_id:string;revision:number};
export const DirectorMusic = createContext<MutableRefObject<{prepareTarget:()=>Promise<MusicTarget>;refresh:()=>Promise<unknown>}|null>|null>(null);
