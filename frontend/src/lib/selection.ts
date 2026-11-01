/** Toggle only the displayed, eligible IDs; retain selections outside this view. */
export function allShownSelected(selected: string[], shown: string[]) {
  return shown.length > 0 && shown.every(id => selected.includes(id));
}
export function toggleShown(selected: string[], shown: string[]) {
  const eligible = new Set(shown);
  return allShownSelected(selected, shown)
    ? selected.filter(id => !eligible.has(id))
    : [...new Set([...selected, ...shown])];
}
