"""String-presence evidence tests; no raw context or host simulation claims."""
import json
import time
import threading
from pathlib import Path
from unittest.mock import patch
from test_lastgood import Base, C, tools, core, lastgood
from lastgood import changeview as V


class TestChangeEvidence(Base):
    def run_record(self, session=None):
        return tools.run_and_record(self.project, 'observed', 'test',
                                   {'session_id': session} if session else {})['record']

    def configure(self, text='555-0100', path='index.html'):
        tools.save_setup(self.project, {'checks': [{'type': 'text_present', 'path': path, 'text': text}]})

    def test_removed_and_added_with_record_ids(self):
        self.configure();a=self.run_record();self.page().write_text(self.page().read_text(encoding="utf-8").replace('555-0100',''), newline="")
        b=self.run_record();self.assertEqual(b['change_evidence']['before_id'],a['id'])
        self.assertEqual(b['change_evidence']['changes'][0]['change'],'removed')
        blame=tools.blame(self.project);self.assertIn('removed configured text',blame['evidence_text'])
        self.assertIn('555-0100',lastgood._blame_text(self.project))
        self.page().write_text(self.page().read_text(encoding="utf-8")+'555-0100', newline="");c=self.run_record()
        self.assertEqual(c['change_evidence']['changes'][0]['change'],'added')

    def test_first_and_unchanged(self):
        self.configure();a=self.run_record();self.assertEqual(a['change_evidence']['changes'],[])
        self.assertIsNone(a['change_evidence']['before_id']);b=self.run_record()
        self.assertEqual(b['change_evidence']['changes'],[])

    def test_config_mismatch_never_compares(self):
        self.configure();self.run_record();self.configure('not there');b=self.run_record()
        self.assertEqual(b['change_evidence']['changes'],[])
        self.assertIn('setup changed',b['change_evidence']['note'])

    def test_unknown_gap_and_truncation(self):
        self.configure();self.run_record()
        with patch.object(C,'_read_bounded',side_effect=OverflowError('truncated')):
            b=self.run_record()
        self.assertEqual(b['result'],'UNKNOWN');self.assertEqual(b['change_evidence']['changes'],[])
        self.page().write_text('not there', encoding="utf-8", newline="");c=self.run_record()
        self.assertIn('gap',c['change_evidence']['note']);self.assertEqual(c['change_evidence']['changes'],[])

    def test_missing_binary_and_escape_no_delta(self):
        self.configure();self.run_record();self.page().unlink();b=self.run_record()
        self.assertEqual(b['change_evidence']['changes'],[])
        self.page().write_bytes(b'555-0100\x00');c=self.run_record();self.assertEqual(c['result'],'UNKNOWN')
        self.page().unlink();outside=self.tmp/'outside';outside.write_text('555-0100', encoding="utf-8", newline="")
        self.symlink_or_skip(self.page(), outside);d=self.run_record();self.assertEqual(d['result'],'UNKNOWN')
        self.assertEqual(d['change_evidence']['changes'],[])

    def test_secret_context_never_captured_and_credentials_redacted(self):
        marker='SYNTHETIC_PRIVATE_CONTEXT_123'
        self.page().write_text(self.page().read_text(encoding="utf-8")+'\npassword='+marker, newline="")
        self.configure();self.run_record();self.page().write_text('password='+marker, encoding="utf-8", newline="")
        self.run_record();report=Path(tools.write_report(self.project)['report']).read_text(encoding="utf-8")
        disk=''.join(p.read_text(encoding="utf-8") for p in self.data.rglob('*.json'))
        self.assertNotIn(marker,disk+report)
        credential='sk-SYNTHETIC_SECRET_TOKEN_12345'
        self.configure(credential);self.page().write_text(credential, encoding="utf-8", newline="");self.run_record()
        self.page().write_text('gone', encoding="utf-8", newline="");r=self.run_record();report=Path(tools.write_report(self.project)['report']).read_text(encoding="utf-8")
        disk=''.join(p.read_text(encoding="utf-8") for p in self.data.rglob('*.json'))
        self.assertNotIn(credential,disk+report);self.assertEqual(r['change_evidence']['changes'],[])

    def test_sensitive_files_and_private_key_markers(self):
        for path in ('.env','.env.local','id_rsa','private.pem','secrets.json'):
            self.configure('TOKEN',path);(self.project/path).write_text('TOKEN', encoding="utf-8", newline="")
            r=self.run_record();self.assertEqual(r['result'],'UNKNOWN');self.assertEqual(r['presence_observations'],[None])
        self.configure();self.page().write_text('-----BEGIN PRIVATE KEY-----\n555-0100', encoding="utf-8", newline="")
        r=self.run_record();self.assertIsNone(r['presence_observations'][0])

    def test_xss_escaped_in_actual_report(self):
        needle='<script>alert(1)</script>';self.configure(needle);self.page().write_text(needle, encoding="utf-8", newline="")
        self.run_record();self.page().write_text('gone', encoding="utf-8", newline="");self.run_record()
        html=Path(tools.write_report(self.project)['report']).read_text(encoding="utf-8")
        self.assertNotIn(needle,html);self.assertIn('&lt;script&gt;',html)
        self.assertIn('removed configured text',html)

    def test_multibyte_bounds_and_retention(self):
        self.configure('界'*400);self.page().write_text('界'*400, encoding="utf-8", newline="");r=self.run_record()
        label=r['presence_observations'][0]['text'];self.assertLessEqual(len(label.encode()),V.MAX_LABEL_BYTES)
        self.assertIn('[truncated]',label);label.encode().decode('utf-8')
        items=[{'id':i,'label':'界'*300} for i in range(300)]
        V.retain(items);self.assertLessEqual(len(items),200)
        self.assertLessEqual(len(json.dumps(items,ensure_ascii=False).encode()),V.MAX_INDEX_BYTES)
        with patch.object(V,'MAX_INDEX_BYTES',2000):
            V.retain(items);self.assertLessEqual(len(json.dumps(items,ensure_ascii=False).encode()),2000)

    def test_session_and_project_isolation(self):
        self.configure();self.run_record('one');self.page().write_text('gone', encoding="utf-8", newline="");r=self.run_record('two')
        self.assertIn('Session boundary',r['change_evidence']['note']);self.assertEqual(r['change_evidence']['changes'],[])
        other=self.tmp/'other';other.mkdir();(other/'index.html').write_text('other', encoding="utf-8", newline="")
        tools.save_setup(other,{'checks':[{'type':'text_present','path':'index.html','text':'other'}]})
        fresh=tools.run_and_record(other,'other','test')['record'];self.assertIsNone(fresh['change_evidence']['before_id'])

    def test_stale_evidence_is_historical(self):
        self.configure();self.run_record();self.page().write_text('gone', encoding="utf-8", newline="");self.run_record()
        self.page().write_text('555-0100', encoding="utf-8", newline="");b=tools.blame(self.project)
        self.assertEqual(b['evidence_freshness'],'stale');self.assertIn('removed',b['evidence_text'])

    def test_overlapping_observations_do_not_invent_order(self):
        a={'id':1,'result':'PASS','config_hash':'x','observation_finished':20}
        b={'id':2,'result':'FAIL','config_hash':'x','observation_started':10}
        self.assertIn('overlapping',V.compare(a,b)['note'])

    def test_concurrent_record_ids_remain_distinct(self):
        self.configure();out=[]
        threads=[threading.Thread(target=lambda:out.append(self.run_record())) for _ in range(4)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len({r['id'] for r in out}),4)
        for r in out:
            self.assertLessEqual(len(r['change_evidence']['changes']),5)
