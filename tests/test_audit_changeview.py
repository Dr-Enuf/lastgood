import copy
import json
import threading
from pathlib import Path
from unittest.mock import patch
import test_changeview as feature
from test_lastgood import Base, C, core, tools
from lastgood import changeview as V


# Reuse fixtures/helpers without inheriting the other test methods.
class TestChangeviewAudit(Base):
    configure = feature.TestChangeEvidence.configure
    run_record = feature.TestChangeEvidence.run_record

    def test_sensitive_symlink_target_read_and_fingerprint_excluded(self):
        self.configure();self.page().unlink();secret=self.project/'.env'
        secret.write_text('CONTACT=555-0100', encoding="utf-8", newline="");self.symlink_or_skip(self.page(), secret)
        first=self.run_record();fp=first['fingerprint']
        secret.write_text('CONTACT=gone', encoding="utf-8", newline="");second=self.run_record()
        self.assertEqual([first['result'],second['result']],['UNKNOWN','UNKNOWN'])
        self.assertEqual(second['fingerprint'],fp)
        self.assertEqual(second['presence_observations'],[None])
        self.assertEqual(second['change_evidence']['changes'],[])

    def test_ordinary_in_project_symlink_remains_supported(self):
        self.configure();self.page().unlink();target=self.project/'page.html';target.write_text('555-0100', encoding="utf-8", newline="")
        self.symlink_or_skip(self.page(), target);self.assertEqual(self.run_record()['result'],'PASS')

    def test_lost_unknown_blocks_until_explicit_successful_baseline(self):
        self.configure();self.run_record();held=threading.Event();release=threading.Event()
        path=tools.project_store(self.project)/'index.json'
        def hold():
            with core.locked(path):held.set();release.wait(2)
        t=threading.Thread(target=hold);t.start();held.wait(2)
        try:lost=tools.run_and_record(self.project,'not recorded','test',budget=.02)['record']
        finally:release.set();t.join()
        self.assertEqual(lost['result'],'UNKNOWN');self.assertIsNone(lost['id'])
        self.page().write_text('gone', encoding="utf-8", newline="");r=self.run_record()
        self.assertTrue(r['continuity_blocked']);self.assertEqual(r['change_evidence']['changes'],[])
        self.page().write_text('555-0100', encoding="utf-8", newline="");r=self.run_record()
        self.assertTrue(r['continuity_blocked']);self.assertEqual(r['change_evidence']['changes'],[])
        tools.run_and_record(self.project,'baseline','command')
        self.page().write_text('gone', encoding="utf-8", newline="");r=self.run_record()
        self.assertFalse(r['continuity_blocked']);self.assertEqual(r['change_evidence']['changes'][0]['change'],'removed')

    def test_general_storage_write_error_blocks_comparisons(self):
        self.configure();self.run_record()
        with patch.object(core,'atomic_write_json',side_effect=OSError('synthetic write failure')):
            lost=self.run_record()
        self.assertEqual(lost['result'],'UNKNOWN');self.assertIsNone(lost['id'])
        self.page().write_text('gone', encoding="utf-8", newline="");r=self.run_record()
        self.assertTrue(r['continuity_blocked']);self.assertEqual(r['change_evidence']['changes'],[])

    def test_epoch_change_does_not_bridge_a_process_restart(self):
        self.configure();self.run_record()
        with patch.object(V,'_STATES',{}):
            self.page().write_text('gone', encoding="utf-8", newline="");r=self.run_record()
        self.assertIn('epoch changed',r['change_evidence']['note']);self.assertEqual(r['change_evidence']['changes'],[])

    def test_retention_actual_indented_file_size(self):
        text='界'*400
        tools.save_setup(self.project,{'checks':[{'type':'text_present','path':'index.html','text':text} for _ in range(5)]})
        self.page().write_text(text, encoding="utf-8", newline="");r=self.run_record()
        items=[{**copy.deepcopy(r),'id':i+1} for i in range(200)]
        V.retain(items);p=self.tmp/'saved.json';core.atomic_write_json(p,items)
        self.assertLessEqual(p.stat().st_size,V.MAX_INDEX_BYTES);self.assertLessEqual(len(items),V.MAX_RECORDS)
        self.assertEqual(p.read_bytes(),V.serialize_json(items).encode('utf-8'))  # exact bytes: no newline/codepage translation

    def test_single_oversized_record_rejected_not_written(self):
        items=[{'oversized':'a'*V.MAX_INDEX_BYTES}]
        with self.assertRaises(ValueError):V.retain(items)

    def test_quoted_json_credential_redacted_before_disk_and_html(self):
        for name in ('api_key','password','token'):
            marker='SYNTHETIC_SECRET_'+name+'_123456'
            needle=json.dumps({name:marker})
            self.configure(needle);self.page().write_text(needle, encoding="utf-8", newline="");r=self.run_record()
            self.assertIsNone(r['presence_observations'][0])
            report=Path(tools.write_report(self.project)['report']).read_text(encoding="utf-8")
            disk=''.join(p.read_text(encoding="utf-8") for p in self.data.rglob('*.json'))
            self.assertNotIn(marker,disk+report)
