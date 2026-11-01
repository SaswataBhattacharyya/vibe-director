import json
import tempfile
import unittest
from pathlib import Path
from story_builder.services.debug_journal import DebugJournal


class DebugJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.journal = DebugJournal(self.root)

    def test_opt_in_persistence_events_and_new_session(self):
        self.assertFalse(self.journal.status()['enabled'])
        self.assertEqual(self.journal.record([{'kind':'click'}])['recorded'], 0)
        first = self.journal.set_enabled(True)
        self.journal.record([{'kind':'owner_observation','outcome':'passed','message':'Video plays','secret':'never log this'}])
        events = [json.loads(line) for line in self.journal.read_log().splitlines()]
        self.assertEqual(events[-1]['message'],'Video plays')
        self.assertNotIn('secret', events[-1])
        self.assertTrue(DebugJournal(self.root).status()['enabled'])
        self.journal.set_enabled(False)
        original = self.journal.read_log()
        self.journal.record([{'kind':'click'}])
        self.assertEqual(original,self.journal.read_log())
        second = self.journal.set_enabled(True)
        self.assertNotEqual(first['session_id'],second['session_id'])
        self.assertTrue(Path(first['log_path']).exists())

    def test_limits_and_invalid_inputs(self):
        for value in ['true',1,None]:
            with self.assertRaises(ValueError): self.journal.set_enabled(value)
        for events in [None,[{}],[{'kind':'click'}]*51]:
            with self.assertRaises(ValueError): self.journal.record(events)
        self.journal.set_enabled(True)
        self.journal.MAX_BYTES = 10
        with self.assertRaisesRegex(ValueError,'full'): self.journal.record([{'kind':'click'}])

    def test_invalid_session_cannot_escape_directory(self):
        self.journal.directory.mkdir(parents=True)
        self.journal.policy_path.write_text(json.dumps({'enabled':True,'session_id':'../../outside'}))
        with self.assertRaises(ValueError): self.journal.read_log()


class DebugAPITests(unittest.TestCase):
    def test_toggle_record_download_and_validation(self):
        import io
        from story_builder.isolated_server import create_app
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(data_root=Path(directory))
            def request(path, method='GET', payload=None):
                body = json.dumps(payload).encode() if payload is not None else b''
                environ = {'PATH_INFO':path,'REQUEST_METHOD':method,'QUERY_STRING':'',
                           'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body)}
                status=[]
                result=b''.join(app(environ,lambda value,headers:status.append(value)))
                return status[0],result
            self.assertFalse(json.loads(request('/api/debug')[1])['enabled'])
            self.assertTrue(request('/api/debug','PUT',{'enabled':'yes'})[0].startswith('400'))
            self.assertTrue(request('/api/debug','PUT',{'enabled':True})[0].startswith('200'))
            status,body=request('/api/debug/events','POST',{'events':[{'kind':'api','status':404,'message':'missing route'}]})
            self.assertTrue(status.startswith('200'), (status, body))
            self.assertEqual(json.loads(body)['recorded'],1)
            status,body=request('/api/debug/log')
            self.assertTrue(status.startswith('200'), (status, body))
            self.assertIn(b'missing route',body)
