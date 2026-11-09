import json
import threading
import time
from pathlib import Path
from unittest.mock import patch
from test_lastgood import Base, tools, lastgood
from lastgood import health as H


class TestHealthAuditTruth(Base):
    def setUp(self):
        super().setUp()
        state=patch.object(H,'_SCOPES',{});state.start();self.addCleanup(state.stop)

    def test_cleanup_timeout_and_late_failure_are_never_pass(self):
        entered=threading.Event();release=threading.Event();finished=threading.Event()
        real_unlink=tools.os.unlink
        def delay(path,*args,**kwargs):
            if Path(path).name.startswith('.lastgood-doctor-'):
                entered.set();release.wait(2)
                real_unlink(path,*args,**kwargs);finished.set()
                raise PermissionError('SYNTHETIC_PRIVATE_CLEANUP')
            return real_unlink(path,*args,**kwargs)
        with patch.object(tools.os,'unlink',delay):
            started=time.monotonic()
            try:
                result=tools.doctor(self.project,budget=.12)
                self.assertTrue(entered.is_set())
                self.assertFalse(finished.is_set())
                self.assertLess(time.monotonic()-started,.5)
                self.assertEqual(result['storage']['result'],'UNKNOWN')
                self.assertEqual(result['diagnostic_result'],'UNKNOWN')
                snapshot=json.dumps(result)
            finally:
                release.set();finished.wait(2)
                deadline=time.monotonic()+2
                while tools._PROBES and time.monotonic()<deadline:time.sleep(.01)
            self.assertEqual(json.dumps(result),snapshot)
        self.assertEqual(result['storage']['result'],'UNKNOWN')
        self.assertFalse((tools.project_store(self.project)/'index.json').exists())
        self.assertEqual(list(self.data.rglob('.lastgood-doctor-*')),[])

    def test_cleanup_failure_completed_before_deadline_is_unknown(self):
        real_unlink=tools.os.unlink
        def fail(path,*args,**kwargs):
            real_unlink(path,*args,**kwargs)
            if Path(path).name.startswith('.lastgood-doctor-'):
                raise PermissionError('SYNTHETIC_PRIVATE_CLEANUP')
        with patch.object(tools.os,'unlink',fail):
            result=tools.doctor(self.project,budget=1)
        self.assertEqual(result['storage']['result'],'UNKNOWN')
        self.assertEqual(result['storage']['error'],'Probe cleanup failed')
        self.assertEqual(result['diagnostic_result'],'UNKNOWN')
        self.assertNotIn('SYNTHETIC_PRIVATE_CLEANUP',json.dumps(result))

    def test_actual_slash_and_report_expose_safe_callback_error_separately(self):
        with patch.object(tools,'ledger_attempt',side_effect=PermissionError('SYNTHETIC_PRIVATE_CALLBACK')):
            lastgood._on_pre_tool_call(tool_name='send_email',args={'body':'RAW_PRIVATE_MARKER'},session_id='audit')
        line=lastgood._lastgood_command('status',session_id='audit')
        self.assertIn('check_error=none',line)
        self.assertIn('callback_error=PermissionError',line)
        self.assertIn('tool=send_email',line);self.assertIn('last_hook=',line)
        report=Path(tools.write_report(self.project,{'session_id':'audit'})['report']).read_text(encoding="utf-8")
        self.assertIn('callback_error=PermissionError',report)
        self.assertIn('check_error=none',report)
        for private in ('SYNTHETIC_PRIVATE_CALLBACK','RAW_PRIVATE_MARKER'):
            self.assertNotIn(private,line+report)

    def test_collection_uncertainty_visible_in_concise_output(self):
        with patch.object(H,'_UPDATES_DROPPED',True):
            text=lastgood._lastgood_command('status')
        self.assertIn('Runtime callbacks: UNKNOWN',text)
        self.assertIn('counts may be incomplete',text)
