import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from story_builder.services import media_library as library, media_semantic_search as search, video_repertoire as store

class ExtractedAssetControlsTests(unittest.TestCase):
    def test_delete_one_clip_preserves_source_and_sibling_and_rejects_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/'projects'/'ws'/'media';project.mkdir(parents=True)
            outputs=root/'projects'/'ws'/'media'/'generated';outputs.mkdir(parents=True)
            for name in ['clip.wav','other.wav']:(outputs/name).write_bytes(b'audio')
            source=root/'projects'/'ws'/'media'/'imports'/'source.mp4';source.parent.mkdir(parents=True);source.write_bytes(b'original')
            rows=[{'asset_id':'pa-'+str(i)*16,'source':'project_output','kind':'audio','relative_path':name,'media_type':'audio/wav','filename':name,'metadata':{'analyzer_run_id':'run-a','occurrence_id':f'audio_clip-{i}'}} for i,name in [(1,'clip.wav'),(2,'other.wav')]]
            rows.append({'asset_id':'pa-'+'3'*16,'source':'project_upload','kind':'video','relative_path':'imports/source.mp4','media_type':'video/mp4','filename':'source.mp4'})
            (project/'assets.json').write_text(json.dumps({'schema_version':1,'assets':rows}))
            run=root/'video_repertoire'/'runs'/'run-a';run.mkdir(parents=True)
            (run/'clip.wav').write_bytes(b'private audio')
            (run/'manifest.json').write_text(json.dumps({'run_id':'run-a','media_collection':{'assets':[{'asset_id':'clip-1','category':'music','relative_path':'clip.wav'}]}}))
            with self.assertRaises(library.ProductionAssetError):library.delete_extracted_asset(root,'ws','pa-'+'3'*16)
            library.delete_extracted_asset(root,'ws','pa-'+'1'*16)
            self.assertFalse((run/'clip.wav').exists());self.assertFalse((outputs/'clip.wav').exists());self.assertTrue((outputs/'other.wav').exists());self.assertTrue(source.exists())
            self.assertEqual(len(json.loads((project/'assets.json').read_text())['assets']),2)

    def test_delete_extracted_image_keeps_imported_image_and_private_frame_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/'projects'/'ws'/'media';project.mkdir(parents=True)
            outputs=root/'projects'/'ws'/'media'/'generated';outputs.mkdir(parents=True)
            (outputs/'frame.png').write_bytes(b'frame')
            imported=root/'projects'/'ws'/'media'/'imports'/'original.png';imported.parent.mkdir(parents=True);imported.write_bytes(b'original')
            rows=[{'asset_id':'pa-'+'1'*16,'source':'project_output','kind':'image','relative_path':'frame.png','media_type':'image/png','filename':'frame.png','metadata':{'analyzer_run_id':'run-a','occurrence_id':'scene_one_frame_1'}},
                  {'asset_id':'pa-'+'2'*16,'source':'project_upload','kind':'image','relative_path':'imports/original.png','media_type':'image/png','filename':'original.png'}]
            (project/'assets.json').write_text(json.dumps({'schema_version':1,'assets':rows}))
            run=root/'video_repertoire'/'runs'/'run-a';run.mkdir(parents=True)
            (run/'frame.png').write_bytes(b'private frame');(run/'other.png').write_bytes(b'sibling')
            (run/'manifest.json').write_text(json.dumps({'run_id':'run-a','scenes':[{'scene_id':'one','frames':[{'frame_id':1,'path':'frame.png'}]}]}))
            with self.assertRaises(library.ProductionAssetError):library.delete_extracted_asset(root,'ws','pa-'+'2'*16)
            library.delete_extracted_asset(root,'ws','pa-'+'1'*16)
            self.assertFalse((outputs/'frame.png').exists());self.assertFalse((run/'frame.png').exists())
            self.assertTrue((run/'other.png').exists());self.assertTrue(imported.exists())

    def test_imports_use_kind_folders_and_public_origin(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(library,'_probe',return_value={}):
            root=Path(tmp)
            for filename,content,role,folder in [('x.png',b'\x89PNG\r\n\x1a\nX','project_image','images'),('x.wav',b'RIFF0000WAVE','project_audio','audio'),('x.mp4',b'0000ftypisom','project_video','videos')]:
                asset=library.register_upload(root,'ws',filename=filename,content=content,role=role)
                self.assertEqual(asset['origin'],'imported')
                path,_,_=library.asset_path(root,'ws',asset['asset_id'])
                self.assertEqual(path.parent.name,folder)

    def test_summary_match_returns_all_surviving_cuts_audio_uses_own_text_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store.configure_roots(root)
            self.addCleanup(store.configure_roots,Path(tmp)/'reset')
            run=store.analyzer_runs_root()/'run-a';index=run/'index';index.mkdir(parents=True)
            (run/'manifest.json').write_text(json.dumps({'embeddings':{'pe_av':{'status':'completed'}}}))
            (index/'index_manifest.json').write_text(json.dumps({'record_schema_version':2,'model':{'backend':'pe_av'},'vector_fields':{'pe_av_text_vector':2}}))
            summary={'record_id':'full','kind':'video_summary','text':'reactor watches childhood clips','pe_av_text_embedding_backend':'pe_av','pe_av_text_vector':[1,0]}
            event={'record_id':'event','kind':'audio_event','text':'piano music','start_time_sec':0,'end_time_sec':3,'pe_av_text_embedding_backend':'pe_av','pe_av_text_vector':[1,0]}
            jobs=[{'status':'completed','request':{'workspace_id':'ws'},'result':{'audio_analysis':[{'run_id':'run-a'}]}}]
            fake=type('Retrieval',(),{'_load_records':staticmethod(lambda _: [summary,event]),'search_records':staticmethod(lambda rows,*a,**k:{'results':[{**r,'score':.9} for r in rows[:k['top_n']]]})})
            video=[{'asset_id':f'cut-{i}','kind':'video','metadata':{'analyzer_run_id':'run-a','scene_id':'scene-a'}} for i in [1,2]]
            with patch.object(search,'_retrieval_module',return_value=fake),patch.object(store,'list_jobs',return_value=jobs),patch.object(search,'list_assets',return_value={'assets':video,'total':2}):
                result=search.search_workspace(root,'ws','childhood',kind='video',limit=1)
                self.assertEqual([h['asset']['asset_id'] for h in result['results']],['cut-1','cut-2'])
                self.assertTrue(all(h['semantic_source']=='video_summary' and h['group_size']==2 for h in result['results']))
            audio=[{'asset_id':'own','kind':'audio','description':'piano music','metadata':{'analyzer_run_id':'run-a','timestamp_start_seconds':0,'timestamp_end_seconds':3}}, {'asset_id':'fallback','kind':'audio','metadata':{'analyzer_run_id':'run-a'}}]
            with patch.object(search,'_retrieval_module',return_value=fake),patch.object(store,'list_jobs',return_value=jobs),patch.object(search,'list_assets',return_value={'assets':audio,'total':2}):
                result=search.search_workspace(root,'ws','music',kind='audio')
                self.assertEqual({h['asset']['asset_id']:h['text'] for h in result['results']},{'own':'piano music','fallback':summary['text']})
