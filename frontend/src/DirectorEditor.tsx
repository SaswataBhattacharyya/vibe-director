import {createContext, useContext, type MutableRefObject} from 'react';
import type {EditorRange} from './lib/editor-api';

export type EditorTarget = {version: 1; editor_session_id: string; expected_revision: number;
  selected_ranges: Array<Pick<EditorRange, 'asset_id' | 'start' | 'end'>>};
export type EditorBridge = {prepareTarget: () => Promise<EditorTarget>; currentTarget?: () => EditorTarget | undefined; refresh: () => Promise<void>};
export const DirectorEditor = createContext<MutableRefObject<EditorBridge | null> | null>(null);
export function useDirectorEditor() {
  const bridge = useContext(DirectorEditor);
  if (!bridge) throw new Error('Editor requires DirectorRuntime.');
  return bridge;
}
