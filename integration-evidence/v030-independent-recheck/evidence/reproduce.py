import os,sys,tempfile,json,copy,time
from pathlib import Path
sys.path.insert(0,"/tmp/lastgood-v3-recheck-rkj44glg/source/plugin")
from lastgood import tools,checks as C,changeview as V,core
root=Path(tempfile.mkdtemp(prefix="lastgood-v3-probe-"));os.environ["LASTGOOD_DATA_DIR"]=str(root/"data")
def setup(name,path="index.html",text="555-0100",count=1):
 p=root/name;p.mkdir();tools.save_setup(p,{"checks":[{"type":"text_present","path":path,"text":text} for _ in range(count)]});return p
p=setup("alias");(p/".env").write_text("CONTACT=555-0100");(p/"index.html").symlink_to(p/".env")
a=tools.run_and_record(p,"alias baseline","test")["record"]
(p/".env").write_text("CONTACT=gone");b=tools.run_and_record(p,"alias change","test")["record"]
print("SENSITIVE_SYMLINK",a["result"],b["result"],json.dumps(b["change_evidence"]["changes"]))
p=setup("retention",text="界"*400,count=5);(p/"index.html").write_text("界"*400)
r=tools.run_and_record(p,"long check","test")["record"]
items=[{**copy.deepcopy(r),"id":i+1} for i in range(200)];V.retain(items)
compact=len(json.dumps(items,ensure_ascii=False).encode());dest=root/"retained.json";core.atomic_write_json(dest,items)
print("RETENTION", "records="+str(len(items)),"compact="+str(compact),"disk="+str(dest.stat().st_size),"limit="+str(V.MAX_INDEX_BYTES))
# Redaction matching a bare credential assignment is present, but ordinary quoted JSON is not handled.
p=setup("quoted-secret",text='"api_key": "SYNTHETIC_SECRET_123456"');(p/"index.html").write_text('"api_key": "SYNTHETIC_SECRET_123456"')
a=tools.run_and_record(p,"json secret invariant","test")["record"]
print("QUOTED_ASSIGNMENT",a["presence_observations"],"stored="+str("SYNTHETIC_SECRET_123456" in (tools.project_store(p)/"index.json").read_text()))
# Sensitive target alias is also fingerprinted.
print("FIXTURES",root)

import threading
p=setup("unpersisted-gap");(p/"index.html").write_text("555-0100")
a=tools.run_and_record(p,"baseline","test")["record"];lockpath=tools.project_store(p)/"index.json";held=threading.Event()
def hold():
 with core.locked(lockpath):held.set();time.sleep(.2)
t=threading.Thread(target=hold);t.start();held.wait();gap=tools.run_and_record(p,"not recorded","test",budget=.02)["record"];t.join()
(p/"index.html").write_text("gone");b=tools.run_and_record(p,"failure after gap","test")["record"]
print("UNPERSISTED_UNKNOWN_GAP", "gap_result="+gap["result"],"gap_id="+str(gap["id"]),"next_changes="+json.dumps(b["change_evidence"]["changes"]))
