import sys,os,subprocess,json,tempfile
p=tempfile.mkdtemp(prefix='lastgood-health-restart-')
base="""import sys,json
sys.path.insert(0,'/tmp/lastgood-v4-audit-q4rm04d5/source/plugin')
from lastgood import health as H
"""
a=json.loads(subprocess.check_output([sys.executable,'-c',base+f"H.observe({p!r},{{'session_id':'s'}},'pre','read_file');print(json.dumps(H.read({p!r},{{'session_id':'s'}})))"],text=True))
b=json.loads(subprocess.check_output([sys.executable,'-c',base+f"print(json.dumps(H.read({p!r},{{'session_id':'s'}})))"],text=True))
print(json.dumps({'different_runtime':a['runtime_id']!=b['runtime_id'],'previous_pre':a['pre'],'new_pre':b['pre'],'new_activity':b['hook_activity']}));assert a['runtime_id']!=b['runtime_id'] and b['pre']==0 and b['hook_activity']=='UNOBSERVED'
