import sys,os,json,tempfile,threading,time,socket
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,"/tmp/lastgood-audit-fz583ewf/source/plugin")
import lastgood
from lastgood import tools,checks as C,core
root=Path(tempfile.mkdtemp(prefix="lastgood-audit-repro-")); os.environ["LASTGOOD_DATA_DIR"]=str(root/"data")
def project(name,checks):
 p=root/name;p.mkdir(); (p/"index.html").write_text("<html>phone 555-0100</html>"); tools.save_setup(p,{"checks":checks});return p
words=[{"type":"text_present","path":"index.html","text":"555-0100"}]
p=project("fallback",words)
print("CONFIG_DELETION",tools.run_and_record(p,"baseline","audit")["record"]["result"],end=" -> ")
(p/"index.html").write_text("<html>no phone</html>")
print(tools.run_and_record(p,"broken","audit")["record"]["result"],end=" -> ")
(p/"lastgood-config.json").unlink();r=tools.run_and_record(p,"config deleted","audit")["record"]
print(r["result"],"source="+r["config_source"])
state={"body":b"wanted","count":0}
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  state["count"]+=1;self.send_response(200);self.end_headers();self.wfile.write(state["body"])
 def log_message(self,*a):pass
s=ThreadingHTTPServer(("127.0.0.1",0),H);threading.Thread(target=s.serve_forever,daemon=True).start()
u=f"http://127.0.0.1:{s.server_port}/?token=SYNTHETIC_SECRET_AUDIT"
p=project("url",[{"type":"url_loads","url":u,"text":"wanted"}])
r=tools.run_and_record(p,"url good","audit")["record"];state["body"]=b"broken";count=state["count"]
print("URL_CHANGED",r["result"],"status="+tools.status(p)["now"],"requests_since_change="+str(state["count"]-count))
report=Path(tools.write_report(p)["report"]).read_text();print("URL_SECRET_IN_REPORT", "SYNTHETIC_SECRET_AUDIT" in report)
state["body"]=b"x"*C.MAX_URL_BODY_BYTES+b"wanted"
print("URL_TRUNCATION",tools.run_and_record(p,"large page","audit")["record"]["result"])
s.shutdown();s.server_close()
p=project("lock",words);store=tools.project_store(p);held=threading.Event()
def hold():
 with core.locked(store/"index.json"):
  held.set();time.sleep(.35)
t=threading.Thread(target=hold);t.start();held.wait();start=time.monotonic();r=tools.run_and_record(p,"blocked writer","audit",budget=.02);print("TOTAL_BUDGET", "budget=.02", "elapsed="+str(round(time.monotonic()-start,3)),r["record"]["result"]);t.join()
p=project("cwd-a",words);q=project("edited-b",words);os.environ["TERMINAL_CWD"]=str(p)
(q/"index.html").write_text("<html>no phone</html>")
lastgood._on_post_tool_call(tool_name="write_file",args={"path":str(q/"index.html")},result="{}",status="ok",tool_call_id="b-edit")
print("CROSS_PROJECT_EDIT", "A="+tools.status(p)["now"],"B_records="+str(len(tools.status(q)["tested_steps"])))
print("DRAFT_CLASSIFICATION", core.classify_action("slack_send_message_draft",{}))
print("ALL_FIXTURES",root)
