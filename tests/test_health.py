import importlib
import json
import shutil
import threading
import time
from pathlib import Path
from unittest.mock import patch
from test_lastgood import Base, C, core, tools, lastgood
from lastgood import health as H


class TestRuntimeHealth(Base):
    def setUp(self):
        super().setUp()
        self.states=patch.object(H,'_SCOPES',{});self.states.start();self.addCleanup(self.states.stop)
        self.reg=patch.object(H,'_REGISTRATION',{'state':'UNOBSERVED','time':None});self.reg.start();self.addCleanup(self.reg.stop)

    def test_zero_hooks_after_load_and_no_status_writes(self):
        self.assertFalse(self.data.exists())
        s=tools.status(self.project,{'session_id':'s'})
        self.assertEqual(s['health']['hook_activity'],'UNOBSERVED')
        self.assertEqual(s['health']['pre'],0);self.assertFalse(self.data.exists())
        self.assertEqual(s['health']['config'],'VALID')

    def test_registration_not_hook_delivery(self):
        H.registered();s=H.read(self.project)
        self.assertEqual(s['registration']['state'],'REGISTERED_IN_THIS_RUNTIME')
        self.assertEqual(s['hook_activity'],'UNOBSERVED')

    def test_self_test_does_not_dispatch_hooks_or_record_history(self):
        d=tools.doctor(self.project,{'session_id':'s'})
        self.assertEqual(d['source'],'SELF-TEST');self.assertEqual(d['diagnostic_result'],'PASS')
        self.assertEqual(d['health']['hook_activity'],'UNOBSERVED')
        self.assertEqual(d['health']['pre'],0);self.assertEqual(d['health']['post'],0)
        self.assertIsNotNone(d['health']['self_test']['last_completed'])
        self.assertIsNone(d['health']['check']['last_completed'])
        self.assertFalse((tools.project_store(self.project)/'index.json').exists())
        self.assertEqual(list(self.data.rglob('.lastgood-doctor-*')),[])

    def test_simulated_callbacks_count_invocations_not_host_proof(self):
        lastgood._on_pre_tool_call(tool_name='read_file',args={'secret':'NEVER_CAPTURE_ME'},session_id='s')
        lastgood._on_post_tool_call(tool_name='read_file',args={'secret':'NEVER_CAPTURE_ME'},status='ok',session_id='s')
        h=H.read(self.project,{'session_id':'s'})
        self.assertEqual((h['pre'],h['post']),(1,1));self.assertEqual(h['hook_activity'],'CALLBACKS_OBSERVED')
        self.assertEqual(h['last_tool'],'read_file');self.assertIsNotNone(h['last_hook'])
        self.assertNotIn('NEVER_CAPTURE_ME',json.dumps(h))
        self.assertIn('no guarantee',h['provenance'])

    def test_project_session_isolation_and_unspecified_scope(self):
        H.observe(self.project,{'session_id':'one'},'pre','x')
        self.assertEqual(H.read(self.project,{'session_id':'two'})['pre'],0)
        self.assertEqual(H.read(self.tmp/'other',{'session_id':'one'})['pre'],0)
        self.assertEqual(H.read(self.project)['session_scope'],'UNSPECIFIED')
        self.assertEqual(H.read(self.project)['pre'],0)

    def test_new_runtime_memory_has_no_prior_counters(self):
        H.observe(self.project,{},'pre','x')
        with patch.object(H,'_SCOPES',{}),patch.object(H,'RUNTIME_ID','new-process'):
            s=H.read(self.project);self.assertEqual(s['runtime_id'],'new-process');self.assertEqual(s['pre'],0)
            self.assertEqual(s['hook_activity'],'UNOBSERVED')

    def test_blocked_error_and_uncertain_post_status_distinct(self):
        for status in ('blocked','error','mystery','ok'):
            lastgood._on_post_tool_call(tool_name='read_file',status=status,session_id='s')
        h=H.read(self.project,{'session_id':'s'})
        self.assertEqual(h['post_status'],dict(succeeded=1,failed=1,blocked=1,uncertain=1))

    def test_callback_error_not_real_tool_error_and_no_exception_payload(self):
        with patch.object(tools,'ledger_attempt',side_effect=PermissionError('SECRET_RAW_ERROR')):
            lastgood._on_pre_tool_call(tool_name='send_email',args={},session_id='s')
        h=H.read(self.project,{'session_id':'s'})
        self.assertEqual(h['callback_error']['type'],'PermissionError')
        self.assertNotIn('SECRET_RAW_ERROR',json.dumps(h))

    def test_missing_and_invalid_config_explicit(self):
        (self.project/'lastgood-config.json').unlink()
        self.assertEqual(tools.status(self.project)['health']['config'],'MISSING')
        d=tools.doctor(self.project);self.assertEqual(d['config'],'MISSING');self.assertEqual(d['checks']['result'],'UNKNOWN')
        (self.project/'lastgood-config.json').write_text('{bad', encoding="utf-8", newline="")
        self.assertEqual(tools.status(self.project)['health']['config'],'INVALID')
        self.assertEqual(tools.doctor(self.project)['config'],'INVALID')

    def test_storage_permission_failure_and_no_probe_leaks(self):
        with patch.object(tools.tempfile,'mkstemp',side_effect=PermissionError('private-path')):
            d=tools.doctor(self.project)
        self.assertEqual(d['storage']['result'],'UNKNOWN');self.assertEqual(d['diagnostic_result'],'UNKNOWN')
        self.assertNotIn('private-path',json.dumps(d))

    def test_storage_timeout_bounded(self):
        store=tools.project_store(self.project);held=threading.Event();release=threading.Event()
        def hold():
            with core.locked(store/'doctor-probe'):
                held.set();release.wait(2)
        t=threading.Thread(target=hold);t.start();held.wait(2)
        start=time.monotonic()
        try:d=tools.doctor(self.project,budget=.08)
        finally:release.set();t.join()
        self.assertLess(time.monotonic()-start,.65);self.assertEqual(d['storage']['result'],'UNKNOWN')

    def test_diagnostic_cannot_hide_history_failure_or_make_green(self):
        tools.run_and_record(self.project,'baseline','test')
        self.page().write_text(self.page().read_text(encoding="utf-8").replace('555-0100',''), newline="")
        tools.run_and_record(self.project,'bad','test')
        path=tools.project_store(self.project)/'index.json';before=path.read_bytes()
        d=tools.doctor(self.project)
        self.assertEqual(d['checks']['result'],'FAIL');self.assertEqual(d['diagnostic_result'],'FAIL')
        self.assertEqual(path.read_bytes(),before)
        self.assertIn('FAIL',tools.status(self.project)['now']);self.assertIn('bad',tools.blame(self.project)['verdict'])

    def test_normal_attempt_completed_and_failed_attempt_distinguished(self):
        tools.run_and_record(self.project,'baseline','test',{'session_id':'s'})
        before=H.read(self.project,{'session_id':'s'})['check']['last_completed']
        with patch.object(tools,'_evaluate',side_effect=OSError('RAW_SECRET')):
            tools.run_and_record(self.project,'failed attempt','test',{'session_id':'s'})
        h=H.read(self.project,{'session_id':'s'})
        self.assertEqual(h['check']['last_completed'],before);self.assertIsNotNone(h['check']['last_error'])
        self.assertNotIn('RAW_SECRET',json.dumps(h))

    def test_corrupt_history_and_health_memory_lock_unknown(self):
        store=tools.project_store(self.project);(store/'index.json').write_text('{bad', encoding="utf-8", newline="")
        self.assertEqual(tools.status(self.project)['health']['history'],'UNKNOWN')
        self.assertEqual(tools.doctor(self.project)['diagnostic_result'],'UNKNOWN')
        with H._LOCK:
            self.assertEqual(H.read(self.project)['hook_activity'],'UNKNOWN')

    def test_doctor_skips_remote_calls_and_is_bounded(self):
        tools.save_setup(self.project,{'checks':[{'type':'url_loads','url':'http://127.0.0.1:1/'}]})
        with patch.object(C,'_check_url_loads',side_effect=AssertionError('must not call remote')):
            d=tools.doctor(self.project,budget=.15)
        self.assertEqual(d['checks']['result'],'UNKNOWN')
        self.assertIn('skips remote',d['checks']['details'][0]['detail'])

    def test_doctor_slash_and_no_new_tool_registration(self):
        text=lastgood._lastgood_command('doctor',session_id='s');d=json.loads(text)
        self.assertEqual(d['source'],'SELF-TEST')
        s=lastgood._lastgood_command('status',session_id='s')
        self.assertIn('Runtime callbacks: UNOBSERVED',s)
