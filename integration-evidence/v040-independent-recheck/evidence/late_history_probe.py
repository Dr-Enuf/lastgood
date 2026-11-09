import os,sys,json,tempfile,threading,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/tmp/lastgood-v4-recheck-_3diz0t2/source/plugin')
import lastgood
from lastgood import tools,health as H
root=Path(tempfile.mkdtemp(prefix='lastgood-heartbeat-recheck-'));p=root/'project';p.mkdir();os.environ['LASTGOOD_DATA_DIR']=str(root/'data');os.environ['TERMINAL_CWD']=str(p)
tools.save_setup(p,{'checks':[{'type':'text_present','path':'index.html','text':'555-0100'}]});page=p/'index.html';page.write_text('555-0100');tools.run_and_record(p,'baseline','test',{'session_id':'s'});page.write_text('gone');tools.run_and_record(p,'bad','test',{'session_id':'s'})
idx=tools.project_store(p)/'index.json';before=idx.read_bytes();normal=H.read(p,{'session_id':'s'})['check'];release=threading.Event();entered=threading.Event();real=os.unlink
def delay(path,*a,**kw):
 if Path(path).name.startswith('.lastgood-doctor-'):
  entered.set();release.wait(2);real(path,*a,**kw);raise PermissionError('PRIVATE_LATE_EXCEPTION_383')
 return real(path,*a,**kw)
with patch.object(tools.os,'unlink',delay):
 d=tools.doctor(p,{'session_id':'s'},budget=.12);saved=json.dumps(d,sort_keys=True);assert entered.is_set() and d['storage']['result']=='UNKNOWN';release.set();limit=time.monotonic()+2
 while tools._PROBES and time.monotonic()<limit:threading.Event().wait(.01)
 assert not tools._PROBES
 same=json.dumps(d,sort_keys=True)==saved;unchanged=idx.read_bytes()==before;normal_same=H.read(p,{'session_id':'s'})['check']==normal;assert same and unchanged and normal_same
with patch.object(tools,'ledger_attempt',side_effect=PermissionError('PRIVATE_CALLBACK_383')):
 lastgood._on_pre_tool_call(tool_name='send_email',args={'body':'PRIVATE_BODY_383'},session_id='s')
slash=lastgood._lastgood_command('status',session_id='s');report=Path(tools.write_report(p,{'session_id':'s'})['report']).read_text();assert 'callback_error=PermissionError' in slash and 'callback_error=PermissionError' in report
private_absent=all(x not in saved+slash+report for x in ['PRIVATE_LATE_EXCEPTION_383','PRIVATE_CALLBACK_383','PRIVATE_BODY_383']);assert private_absent
print(json.dumps({'diagnostic':d['diagnostic_result'],'storage':d['storage']['result'],'full_return_unchanged_after_worker':same,'existing_FAIL_index_byte_identical':unchanged,'normal_check_lane_unchanged':normal_same,'private_payload_absent':private_absent,'callback_error_in_actual_slash_and_HTML':True,'remaining_temp_probes':len(list(root.rglob('.lastgood-doctor-*')))}))
