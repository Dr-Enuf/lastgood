#!/usr/bin/env python3
"""Drive the REAL Hermes plugin runtime against LastGood, with no model calls.

Run on the PC inside WSL, with Hermes' own Python and an ISOLATED
HERMES_HOME (never ~/.hermes). See PC_TEST_PLAN.md, step 5.

    HERMES_HOME=$T/home $HERMES_PY scripts/hermes_harness.py \
        --hermes-src ~/.hermes/hermes-agent --project $T/project

What it does (each step prints OK / FAIL / INFO):
  1. refuses to run unless HERMES_HOME is a test folder
  2. blocks outbound network except loopback
  3. imports Hermes from --hermes-src and loads plugins through Hermes'
     own plugin manager (function names are probed, and printed, because
     only the v0.22.7 source was read, not run)
  4. checks the LastGood tools, hooks and /lastgood command registered
  5. shows which built-in file tools exist and what post_tool_call
     "status" values Hermes derives (to confirm AUTO_CHECK_TOOLS)
  6. shows what resolve_agent_cwd() returns for this process
  7. fires pre/post_tool_call through hermes_cli.lifecycle.invoke_hook
     with v0.22.7-shaped keyword payloads and checks LastGood's records
It never edits anything outside HERMES_HOME and --project.
"""
import argparse
import hashlib
import json
import os
import socket
import sys
from pathlib import Path

RESULTS = []


def report(ok, step, detail=""):
    tag = {True: "OK  ", False: "FAIL", None: "INFO"}[ok]
    RESULTS.append(ok)
    print(f"[{tag}] {step}{': ' + str(detail) if detail != '' else ''}", flush=True)


def block_network():
    real_connect = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise OSError(f"harness blocked outbound connection to {host}")
        return real_connect(self, address)

    socket.socket.connect = guarded
    socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(OSError("harness blocked create_connection"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hermes-src", required=True)
    ap.add_argument("--project", required=True)
    a = ap.parse_args()

    home = Path(os.environ.get("HERMES_HOME", "")).expanduser()
    real_home = (Path.home() / ".hermes").resolve()
    if not os.environ.get("HERMES_HOME") or home.resolve() == real_home or real_home in home.resolve().parents:
        print("Refusing: set HERMES_HOME to an isolated test folder (not ~/.hermes).")
        return 2
    project = Path(a.project).resolve()
    if not (project / "lastgood-config.json").is_file():
        print("Refusing: --project must be the throwaway copy of sample-project with lastgood-config.json.")
        return 2
    report(None, "HERMES_HOME", home)
    report(None, "project", project)
    block_network()

    sys.path.insert(0, str(Path(a.hermes_src).expanduser().resolve()))
    os.chdir(project)
    os.environ["TERMINAL_CWD"] = str(project)

    try:
        import hermes_cli.plugins as hp
        report(True, "import hermes_cli.plugins")
    except Exception as exc:
        report(False, "import hermes_cli.plugins", repr(exc))
        return 1

    # ---- 3. load plugins through Hermes' own manager (probe names) -------
    loaded = False
    for fname in ("discover_plugins", "load_plugins", "ensure_plugins_loaded", "get_plugin_manager"):
        fn = getattr(hp, fname, None)
        if callable(fn):
            try:
                fn()
                report(True, f"called hermes_cli.plugins.{fname}()")
                loaded = True
                break
            except Exception as exc:
                report(False, f"hermes_cli.plugins.{fname}()", repr(exc))
    if not loaded:
        names = sorted(n for n in dir(hp) if not n.startswith("_") and callable(getattr(hp, n)))
        report(False, "no known loader function; public callables are", ", ".join(names)[:2000])

    manager = None
    for fname in ("get_plugin_manager", "plugin_manager", "get_manager"):
        obj = getattr(hp, fname, None)
        try:
            manager = obj() if callable(obj) else obj
        except Exception:
            manager = None
        if manager is not None:
            report(None, f"manager via {fname}", type(manager).__name__)
            break

    # ---- 4. registrations ---------------------------------------------------
    try:
        import tools.file_tools  # import registers the real built-in file tools
        from tools.registry import registry
        scope = getattr(manager, "scope_key", None)

        def entry(name):
            for kwargs in ({"scope": scope} if scope is not None else {}, {}):
                try:
                    e = registry.get_entry(name, **kwargs)
                    if e is not None:
                        return e
                except TypeError:
                    continue
            return None

        for t in ("lastgood_check", "lastgood_status", "lastgood_blame", "lastgood_report", "lastgood_setup"):
            report(entry(t) is not None, f"tool registered: {t}")
        for t in ("write_file", "patch", "edit_file", "terminal"):
            report(None, f"built-in tool {t} present", entry(t) is not None)
    except Exception as exc:
        report(False, "tool registry probe", repr(exc))

    try:
        from hermes_cli.lifecycle import has_hook, invoke_hook
        for h in ("pre_tool_call", "post_tool_call"):
            report(bool(has_hook(h)), f"hook registered: {h}")
    except Exception as exc:
        report(False, "import hermes_cli.lifecycle", repr(exc))
        return 1

    cmds = getattr(manager, "_plugin_commands", None) if manager is not None else None
    if isinstance(cmds, dict):
        report("lastgood" in cmds, "slash command /lastgood registered")
        report(None, "slash command /blame registered", "blame" in cmds)
    else:
        report(None, "could not read plugin command table; check /lastgood in the live chat step")

    # ---- 5. status values Hermes derives for post_tool_call ------------------
    try:
        import model_tools
        f = getattr(model_tools, "_tool_result_observer_fields")
        for sample in ('{"success": true}', '{"error": "boom"}', "plain text"):
            report(None, f"observer status for write_file result {sample!r}", f("write_file", sample))
    except Exception as exc:
        report(None, "observer status probe unavailable", repr(exc))

    # ---- 6. cwd resolution ------------------------------------------------
    try:
        from agent.runtime_cwd import resolve_agent_cwd
        got = Path(resolve_agent_cwd()).resolve()
        report(got == project, "resolve_agent_cwd() is the project", got)
    except Exception as exc:
        report(False, "resolve_agent_cwd()", repr(exc))

    # ---- 7. fire hooks with v0.22.7-shaped payloads ------------------------
    base = dict(task_id="harness-task", session_id="harness-session", turn_id="harness-turn",
                api_request_id="harness-req", middleware_trace=[])
    page = project / "index.html"
    original = page.read_text()

    def post(tool, call_id, args, status, result="{}"):
        invoke_hook("post_tool_call", tool_name=tool, args=args, result=result, tool_call_id=call_id,
                    duration_ms=5, status=status, error_type=None, error_message=None, **base)

    def pre(tool, call_id, args):
        return invoke_hook("pre_tool_call", tool_name=tool, args=args, tool_call_id=call_id, **base)

    try:
        from plugins.plugin_storage import plugin_data_dir
        data = Path(plugin_data_dir("lastgood"))
        report(home.resolve() in data.resolve().parents, "plugin data dir is inside test HERMES_HOME", data)
    except Exception as exc:
        report(False, "plugins.plugin_storage.plugin_data_dir", repr(exc))
        data = home / "plugin-data" / "lastgood"

    store = data / "projects" / hashlib.sha256(str(project).encode()).hexdigest()[:16]
    def read_items(name):
        path = store / name
        return json.loads(path.read_text()) if path.exists() else []
    before_records = len(read_items("index.json"))
    before_ledger = len(read_items("ledger.json"))
    def records():
        return read_items("index.json")[before_records:]
    def ledger():
        return read_items("ledger.json")[before_ledger:]

    page.write_text(original.replace("Fresh bread every morning.", "Fresh bread and cakes every morning."))
    pre("write_file", "h1", {"path": "index.html"})
    post("write_file", "h1", {"path": "index.html"}, "ok")
    recs = records()
    report(len(recs) == 1 and recs[-1]["result"] == "PASS", "good edit -> auto check PASS",
           [r.get("result") for r in recs])
    page.write_text(page.read_text().replace("555-0100", ""))
    pre("patch", "h2", {"path": "index.html"})
    post("patch", "h2", {"path": "index.html"}, "ok")
    recs = records()
    report(recs and recs[-1]["result"] == "FAIL", "breaking edit -> auto check FAIL", [r.get("result") for r in recs])
    report(recs and recs[-1].get("session_id") == "harness-session" and recs[-1].get("tool_call_id") == "h2",
           "record carries session/tool_call ids")
    marker = "HARNESS_PRIVATE_MARKER"
    pre("send_email", "h3", {"to": "x@example.com", "body": marker})
    post("send_email", "h3", {"to": "x@example.com", "body": marker}, "blocked")
    led = ledger()
    raw = json.dumps(led)
    report(len(led) == 1 and led[0].get("status") == "blocked", "ledger correlates pre/post by tool_call_id", led)
    report(marker not in raw, "ledger stores no raw arguments")
    page.write_text(original)
    print("\nSUMMARY:", "ALL REQUIRED STEPS OK" if False not in RESULTS else "SOME STEPS FAILED (see FAIL lines)")
    return 0 if False not in RESULTS else 1


if __name__ == "__main__":
    raise SystemExit(main())
