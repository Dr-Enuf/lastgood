import os,sys,tempfile,json,subprocess
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='lastgood-real-process-')); p=root/'project';p.mkdir();(p/'index.html').write_text('555-0100');(p/'lastgood-config.json').write_text(json.dumps({'checks':[{'type':'text_present','path':'index.html','text':'555-0100'}]}))
env={**os.environ,'LASTGOOD_DATA_DIR':str(root/'data'),'PROBE_PROJECT':str(p)}
child="""import os,sys,json
from pathlib import Path
sys.path.insert(0,'/tmp/lastgood-v3-recheck-rkj44glg/source/plugin')
from lastgood import tools
p=Path(os.environ['PROBE_PROJECT'])
r=tools.run_and_record(p,'observe','test',{'session_id':'same-session'})['record']
print(json.dumps({'epoch':r['continuity_epoch'],'evidence':r['change_evidence']}))
"""
a=json.loads(subprocess.check_output([sys.executable,'-c',child],env=env,text=True));(p/'index.html').write_text('gone');b=json.loads(subprocess.check_output([sys.executable,'-c',child],env=env,text=True));print('REAL_PROCESS_RESTART',json.dumps({'different_epochs':a['epoch']!=b['epoch'],'next_changes':b['evidence']['changes'],'note':b['evidence']['note']}));assert a['epoch']!=b['epoch'] and not b['evidence']['changes'] and 'epoch changed' in b['evidence']['note']
