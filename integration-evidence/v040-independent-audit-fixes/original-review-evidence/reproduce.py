import sys,os,tempfile,time,threading,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/tmp/lastgood-v4-audit-q4rm04d5/source/plugin')
import lastgood
from lastgood import tools,health as H,core
root=Path(tempfile.mkdtemp(prefix='lastgood-v4-probe-'));os.environ['LASTGOOD_DATA_DIR']=str(root/'data')
p=root/'project';p.mkdir();(p/'index.html').write_text('<html>555-0100</html>');tools.save_setup(p,{'checks':[{'type':'text_present','path':'index.html','text':'555-0100'}]});os.environ['TERMINAL_CWD']=str(p)
entered=threading.Event();release=threading.Event();real_unlink=os.unlink
# Simulate a slow cleanup followed by a permission failure, without leaving the fixture behind.
def delayed_unlink(path,*args,**kwargs):
 if str(Path(path).name).startswith('.lastgood-doctor-'):
  entered.set();release.wait(1);real_unlink(path,*args,**kwargs);raise PermissionError('synthetic cleanup denial')
 return real_unlink(path,*args,**kwargs)
with patch.object(tools.os,'unlink',delayed_unlink):
 start=time.monotonic();d=tools.doctor(p,budget=.12)
 print('INCOMPLETE_STORAGE_PROBE',json.dumps({'elapsed':round(time.monotonic()-start,3),'cleanup_entered':entered.is_set(),'cleanup_still_blocked':not release.is_set(),'diagnostic_result':d['diagnostic_result'],'storage':d['storage'],'active_probes':len(tools._PROBES)}))
 release.set()
 # Only wait for this worker's completion so monkeypatch is not removed during its operation.
 deadline=time.monotonic()+2
 while tools._PROBES and time.monotonic()<deadline:threading.Event().wait(.01)
 print('RETURNED_AFTER_CLEANUP_FAILURE',json.dumps(d['storage']))
with patch.object(tools,'ledger_attempt',side_effect=PermissionError('NOT_FOR_DISPLAY')):
 lastgood._on_pre_tool_call(tool_name='send_email',args={'body':'RAW_PRIVATE_MARKER'},session_id='s')
s=tools.status(p,{'session_id':'s'});line=lastgood._fmt_status(s)
print('CALLBACK_ERROR_STATUS',json.dumps({'recorded_callback_error':s['health']['callback_error'],'slash_line':line.splitlines()[1]}))
# Verify disk remains unchanged on normal status with existing and absent stores.
before={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()};tools.status(p,{'session_id':'s'});after={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()};print('STATUS_DISK_UNCHANGED',before==after)
print('FIXTURES',root)
