import {Dispatch, SetStateAction, useEffect, useState} from 'react';
import {defaultMediaWorkspaceId} from './media-workspace';

/** Form settings join the project's browser checkpoint; jobs remain in their durable services. */
export function useProjectState<T>(name:string, initial:T|(()=>T)): [T, Dispatch<SetStateAction<T>>] {
 const key=`vibe-project-settings:${defaultMediaWorkspaceId()}:${name}`;
 const [value,setValue]=useState<T>(()=>{
  try{const saved=localStorage.getItem(key);if(saved!==null)return JSON.parse(saved) as T;}catch{/* Use the form default if a saved draft is malformed. */}
  return typeof initial==='function'?(initial as ()=>T)():initial;
 });
 useEffect(()=>{localStorage.setItem(key,JSON.stringify(value));},[key,value]);
 return [value,setValue];
}
