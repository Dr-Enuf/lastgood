#!/usr/bin/env python3
"""STANDALONE SIMULATION of the LastGood story. This is NOT a Hermes run.

It calls the plugin's own hook and handler functions directly, the way
Hermes would, on a temporary copy of sample-project/. Use it as a smoke
test and for rehearsing; it does not prove anything about real Hermes
(see PC_TEST_PLAN.md for that). Any video made from it must be labelled
"simulation, not live Hermes".

  1. baseline check                      -> PASS
  2. "agent" edits the slogan (write_file hook)       -> auto check PASS
  3. "agent" removes the phone number (patch hook)    -> auto check FAIL
  4. blame                               -> first failure = step 3
  5. a recognised irreversible attempt (git push) is recorded, then blocked
  6. simulated /rollback (files restored to step 2's bytes)
       -> step 3 now STALE, step 2 current again
  7. fresh check                         -> PASS (current)
  8. Proof Report copied to demo-output/report.html

Exit code 0 only if every expectation holds.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plugin"))

import lastgood  # noqa: E402
from lastgood import tools  # noqa: E402


def hook(tool, call_id, args=None, status="ok"):
    kw = dict(task_id="demo-task", session_id="demo-session", turn_id=f"turn-{call_id}",
              tool_call_id=call_id, duration_ms=1, status=status, error_type=None,
              error_message=None, middleware_trace=[])
    lastgood._on_pre_tool_call(tool_name=tool, args=args or {}, **{k: kw[k] for k in ("task_id", "session_id", "turn_id", "tool_call_id")})
    lastgood._on_post_tool_call(tool_name=tool, args=args or {}, result="{}", **kw)


def main() -> int:
    print("=== LastGood STANDALONE SIMULATION (not a Hermes run) ===")
    tmp = Path(tempfile.mkdtemp(prefix="lastgood-demo-"))
    project = tmp / "project"
    shutil.copytree(ROOT / "sample-project", project)
    os.environ["LASTGOOD_DATA_DIR"] = str(tmp / "data")
    os.environ["TERMINAL_CWD"] = str(project)
    page = project / "index.html"
    original = page.read_text()

    s1 = json.loads(tools.lastgood_check({"label": "baseline"}))
    slogan = original.replace("Fresh bread every morning.", "Fresh bread and cakes every morning.")
    page.write_text(slogan)
    hook("write_file", "c2", {"path": "index.html"})
    page.write_text(slogan.replace("555-0100", ""))
    hook("patch", "c3", {"path": "index.html"})
    blame = json.loads(tools.lastgood_blame({}))
    hook("terminal", "c4", {"command": "git push origin main"}, status="blocked")
    page.write_text(slogan)  # simulated /rollback to the checkpoint before step 3
    after_rb = json.loads(tools.lastgood_status({}))
    s5 = json.loads(tools.lastgood_check({"label": "after rollback"}))
    final = json.loads(tools.lastgood_status({}))
    report = json.loads(tools.lastgood_report({}))
    outdir = ROOT / "demo-output"
    outdir.mkdir(exist_ok=True)
    shutil.copyfile(report["report"], outdir / "report.html")

    steps = {r["label"]: r for r in final["tested_steps"]}
    for r in final["tested_steps"]:
        print(f"  #{r['id']} {r['result']:<7} {r['freshness']:<7} {r['label']}")
    print("blame        :", blame["verdict"])
    print("what changed :", blame.get("evidence_text", "no evidence"))
    print("after rollback, before re-check:", after_rb["now"])
    print("now          :", final["now"])
    print("report       :", outdir / "report.html")

    ok = (s1["result"] == "PASS"
          and steps["after write_file"]["result"] == "PASS"
          and steps["after patch"]["result"] == "FAIL"
          and "after patch" in blame["verdict"]
          and "removed configured text in index.html: 555-0100" in blame.get("evidence_text", "")
          and after_rb["now"].startswith("STALE")
          and steps["after patch"]["freshness"] == "stale"
          and steps["after write_file"]["freshness"] == "current"
          and s5["result"] == "PASS" and final["now"] == "PASS (current)")
    print("SIMULATION RESULT:", "PASS" if ok else "FAIL")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
