import {previewMediaDeletion, permanentlyDeleteMedia} from './media-api';
export async function deleteSelectedMedia(workspaceId:string, ids:string[]) {
  const plans=await Promise.all(ids.map(id=>previewMediaDeletion(workspaceId,id)));
  const blocked=plans.filter(p=>!p.can_delete);
  if(blocked.length)throw new Error('Files are still used. Remove these saved references first: '+blocked.map(p=>`${p.path}: ${p.references.join(', ')}`).join('; '));
  if(!window.confirm(`Permanently delete ${plans.length} file(s) from this PC? This cannot be undone.\n\n${plans.map(p=>p.path).join('\n')}`))return 'Deletion cancelled.';
  let deleted=0;
  try{for(const plan of plans){await permanentlyDeleteMedia(workspaceId,plan);deleted++;}}
  catch(error){throw new Error(`${deleted} of ${plans.length} files deleted. ${(error as Error).message}`);}
  return `${deleted} file(s) permanently deleted.`;
}
