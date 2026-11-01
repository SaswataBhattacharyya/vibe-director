import {allShownSelected, toggleShown} from './lib/selection';
export default function SelectionToggle({selected, shown, onChange, disabled=false,capacity,occupied=0}: {
  selected:string[]; shown:string[]; onChange:(ids:string[])=>void; disabled?:boolean; capacity?:number; occupied?:number;
}) {
  const all=allShownSelected(selected,shown);
  const exceeds=capacity!==undefined && !all && occupied+new Set([...selected,...shown]).size>capacity;
  return <button type="button" className="quiet-button" disabled={disabled || !shown.length || exceeds}
    title={exceeds?`This selection would exceed the ${capacity} reference limit. Select fewer items.`:"Changes only items shown here. Selections in other pages or filters are kept."}
    onClick={()=>onChange(toggleShown(selected, shown))}>
    {allShownSelected(selected, shown)?'Deselect all shown':'Select all shown'} ({shown.length})
  </button>;
}
