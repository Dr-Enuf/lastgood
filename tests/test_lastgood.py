"""Standalone tests for LastGood (stdlib unittest, no Hermes needed).

Run from the hermes-lastgood folder:
    python3 -m unittest discover -s tests -v

Each "regression" test reproduces a defect found in the v0.1 review.
Real-Hermes behaviour is checked separately by scripts/hermes_harness.py.
"""

import inspect
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plugin"))

import lastgood  # noqa: E402
from lastgood import checks as C, core, tools  # noqa: E402

MARKER = "SYNTHETIC_PRIVATE_PAYLOAD_7f3a"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lastgood-test-"))
        self.project = self.tmp / "project"
        shutil.copytree(ROOT / "sample-project", self.project)
        self.data = self.tmp / "data"
        self._env = {k: os.environ.get(k) for k in ("LASTGOOD_DATA_DIR", "TERMINAL_CWD")}
        os.environ["LASTGOOD_DATA_DIR"] = str(self.data)
        os.environ["TERMINAL_CWD"] = str(self.project)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, label="step", path=None):
        return json.loads(tools.lastgood_check({"label": label, "path": str(path or self.project)}))

    def status(self, path=None):
        return json.loads(tools.lastgood_status({"path": str(path or self.project)}))

    def page(self):
        return self.project / "index.html"

    def symlink_or_skip(self, link, target):
        """Create a symlink, or skip cleanly where the OS/user cannot (e.g. Windows
        without Developer Mode/admin). POSIX runs keep full symlink coverage."""
        try:
            Path(link).symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable here ({type(exc).__name__})")

    def post_hook(self, tool="write_file", status="ok", **kw):
        lastgood._on_post_tool_call(tool_name=tool, args={"path": "index.html"}, result="{}",
                                    task_id="t1", session_id="s1", turn_id="u1",
                                    tool_call_id=kw.pop("tool_call_id", "c1"), duration_ms=3,
                                    status=status, error_type=None, error_message=None,
                                    middleware_trace=[], **kw)


class TestChecks(Base):
    def test_sample_project_passes(self):
        out = self.check()
        self.assertEqual(out["result"], "PASS", out)
        self.assertEqual(out["setup_source"], "project")

    def test_regression_project_config_is_used(self):
        # v0.1 ignored <project>/lastgood-config.json and fell back to a default PASS.
        (self.project / "lastgood-config.json").write_text(json.dumps(
            {"checks": [{"type": "text_present", "path": "index.html", "text": "NOT THERE"}]}), encoding="utf-8", newline="")
        self.assertEqual(self.check()["result"], "FAIL")

    def test_removing_phone_number_fails(self):
        self.page().write_text(self.page().read_text(encoding="utf-8").replace("555-0100", ""), newline="")
        out = self.check()
        self.assertEqual(out["result"], "FAIL")
        self.assertTrue(any("555-0100" in c["detail"] for c in out["checks"] if c["result"] == "FAIL"))

    def test_broken_json_fails_file_opens(self):
        (self.project / "data.json").write_text("{not json", encoding="utf-8", newline="")
        r = C.run_checks([{"type": "file_opens", "path": "data.json"}], self.project, time.monotonic() + 5)
        self.assertEqual(r[0].result, "FAIL")

    def test_files_exist(self):
        r = C.run_checks([{"type": "files_exist", "paths": ["index.html", "gone.txt"]}], self.project, time.monotonic() + 5)
        self.assertEqual(r[0].result, "FAIL")
        self.assertIn("gone.txt", r[0].detail)

    def test_command_check_type_rejected(self):
        with self.assertRaises(C.ConfigError):
            C.validate_config({"checks": [{"type": "command", "command": "true"}]})

    def test_default_setup_without_config(self):
        (self.project / "lastgood-config.json").unlink()
        out = self.check()
        self.assertEqual(out["setup_source"], "default")
        self.assertEqual(out["result"], "PASS")

    def test_no_subprocess_in_plugin(self):
        for f in (ROOT / "plugin" / "lastgood").glob("*.py"):
            found = re.search(r"^\s*(import|from)\s+subprocess\b|os\.system\(|os\.popen\(", f.read_text(encoding="utf-8"), re.M)
            self.assertIsNone(found, f.name)


class TestContainmentAndBounds(Base):
    def test_regression_parent_and_absolute_paths_rejected(self):
        for bad in ("../outside.txt", "/etc/hostname", "a/../../x"):
            with self.assertRaises(C.ConfigError, msg=bad):
                C.validate_config({"checks": [{"type": "file_opens", "path": bad}]})

    def test_regression_symlink_escape_is_unknown(self):
        outside = self.tmp / "outside.txt"
        outside.write_text("secret words", encoding="utf-8", newline="")
        self.symlink_or_skip(self.project / "link.txt", outside)
        r = C.run_checks([{"type": "text_present", "path": "link.txt", "text": "secret"}], self.project, time.monotonic() + 5)
        self.assertEqual(r[0].result, "UNKNOWN")
        self.assertIn("outside", r[0].detail)

    def test_large_file_is_unknown_not_read(self):
        big = self.project / "big.txt"
        with open(big, "wb") as fh:
            fh.truncate(C.MAX_FILE_BYTES + 1)
        r = C.run_checks([{"type": "file_opens", "path": "big.txt"}], self.project, time.monotonic() + 5)
        self.assertEqual(r[0].result, "UNKNOWN")

    def test_url_rules(self):
        for bad in ("file:///etc/passwd", "ftp://x/y", "http://user:pw@host/"):
            with self.assertRaises(C.ConfigError, msg=bad):
                C.validate_config({"checks": [{"type": "url_loads", "url": bad}]})
        cfg = C.validate_config({"checks": [{"type": "url_loads", "url": "http://127.0.0.1/", "timeout": 60}]})
        self.assertEqual(cfg[0]["timeout"], C.URL_TIMEOUT_CAP)


class _Slow(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(1.5)
        try:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"late")
        except OSError:
            pass

    def log_message(self, *a):
        pass


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class TestUrlAndUnknown(Base):
    def _serve(self, handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_loads_404_and_text(self):
        base = self._serve(lambda *a, **kw: _Quiet(*a, directory=str(self.project), **kw))
        dl = time.monotonic() + 10
        ok = C.run_checks([{"type": "url_loads", "url": base + "/index.html", "timeout": 2, "text": "Bakery"}], self.project, dl)
        self.assertEqual(ok[0].result, "PASS", ok[0].detail)
        missing = C.run_checks([{"type": "url_loads", "url": base + "/nope.html", "timeout": 2}], self.project, dl)
        self.assertEqual(missing[0].result, "FAIL")
        notext = C.run_checks([{"type": "url_loads", "url": base + "/index.html", "timeout": 2, "text": "Pizza"}], self.project, dl)
        self.assertEqual(notext[0].result, "FAIL")

    def test_unreachable_is_unknown_not_fail(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()  # nothing listens here now
        r = C.run_checks([{"type": "url_loads", "url": f"http://127.0.0.1:{port}/", "timeout": 1}], self.project, time.monotonic() + 5)
        self.assertEqual(r[0].result, "UNKNOWN", r[0].detail)

    def test_timeout_is_unknown_and_bounded(self):
        base = self._serve(_Slow)
        start = time.monotonic()
        r = C.run_checks([{"type": "url_loads", "url": base, "timeout": 0.3}], self.project, time.monotonic() + 5)
        self.assertEqual(r[0].result, "UNKNOWN")
        self.assertLess(time.monotonic() - start, 3)

    def test_total_budget_marks_rest_unknown(self):
        r = C.run_checks([{"type": "file_opens", "path": "index.html"}], self.project, time.monotonic() - 1)
        self.assertEqual(r[0].result, "UNKNOWN")

    def test_regression_malformed_config_is_unknown_and_unseats_green(self):
        self.assertEqual(self.check("good")["result"], "PASS")
        (self.project / "lastgood-config.json").write_text('{"checks": [{"type": "url_loads", "url": "http://x", "timeout": "soon"}]}', encoding="utf-8", newline="")
        out = self.check("after bad setup")
        self.assertEqual(out["result"], "UNKNOWN")
        self.assertTrue(out["setup_error"])
        st = self.status()
        self.assertNotIn("PASS", st["now"])
        self.assertEqual(st["tested_steps"][0]["freshness"], "stale")


class TestIdentityAndStale(Base):
    def test_regression_manual_edit_makes_result_stale(self):
        self.check("good")
        self.page().write_text(self.page().read_text(encoding="utf-8").replace("555-0100", ""), newline="")
        st = self.status()
        self.assertTrue(st["now"].startswith("STALE"))
        self.assertEqual(st["tested_steps"][0]["freshness"], "stale")

    def test_rollback_flow_old_results_stale_next_check_fresh(self):
        original = self.page().read_text(encoding="utf-8")
        self.check("good")
        self.page().write_text(original.replace("Fresh bread", "Fresh bread and cakes"), encoding="utf-8", newline="")
        self.check("slogan")
        self.page().write_text(original.replace("Fresh bread", "Fresh bread and cakes").replace("555-0100", ""), encoding="utf-8", newline="")
        self.assertEqual(self.check("tidy contact")["result"], "FAIL")
        self.page().write_text(original, encoding="utf-8", newline="")  # what a /rollback to before step 2 would do
        st = self.status()
        fresh = {r["label"]: r["freshness"] for r in st["tested_steps"]}
        self.assertEqual(fresh["tidy contact"], "stale")
        self.assertEqual(fresh["slogan"], "stale")
        self.assertEqual(fresh["good"], "current")  # same bytes as the restored files
        again = self.check("after rollback")
        self.assertEqual(again["result"], "PASS")
        self.assertEqual(self.status()["now"], "PASS (current)")

    def test_record_identity_fields(self):
        lastgood._on_post_tool_call(tool_name="write_file", args={}, result="{}", status="ok",
                                    session_id="s9", turn_id="u9", tool_call_id="c9", task_id="t9")
        rec = json.loads((next((self.data / "projects").iterdir()) / "index.json").read_text(encoding="utf-8"))[0]
        for key in ("fingerprint", "config_hash", "session_id", "turn_id", "tool_call_id"):
            self.assertTrue(rec.get(key), key)

    def test_no_checkpoint_terminology_in_results(self):
        out = self.check()
        self.assertNotIn("checkpoint", out)
        self.assertIn("tested_step", out)


class TestProjects(Base):
    def test_regression_projects_do_not_share_history(self):
        other = self.tmp / "other"
        other.mkdir()
        (other / "index.html").write_text("<html><body>other</body></html>", encoding="utf-8", newline="")
        self.check("A step")
        st_b = self.status(other)
        self.assertEqual(st_b["tested_steps"], [])

    def test_session_cwd_is_used_when_no_path(self):
        out = json.loads(tools.lastgood_check({"label": "cwd"}))
        self.assertEqual(out["result"], "PASS")
        self.assertEqual(self.status()["tested_steps"][0]["label"], "cwd")


class TestAutoCheckHook(Base):
    def _records(self):
        d = self.data / "projects"
        if not d.exists():
            return []
        out = []
        for p in d.iterdir():
            f = p / "index.json"
            if f.exists():
                out += json.loads(f.read_text(encoding="utf-8"))
        return out

    def test_successful_write_triggers_check(self):
        self.post_hook("write_file", "ok")
        recs = self._records()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["trigger"], "auto")
        self.assertEqual(recs[0]["result"], "PASS")

    def test_patch_after_breaking_edit_records_fail(self):
        self.page().write_text(self.page().read_text(encoding="utf-8").replace("555-0100", ""), newline="")
        self.post_hook("patch", "ok")
        self.assertEqual(self._records()[0]["result"], "FAIL")

    def test_failed_write_or_other_tools_do_not_check(self):
        self.post_hook("write_file", "error")
        self.post_hook("read_file", "ok")
        self.post_hook("terminal", "ok")
        self.assertEqual(self._records(), [])

    def test_no_auto_check_without_opt_in(self):
        (self.project / "lastgood-config.json").unlink()
        self.post_hook("write_file", "ok")
        self.assertEqual(self._records(), [])

    def test_hard_budget_does_not_wait_for_slow_worker_or_late_write(self):
        from unittest.mock import patch
        real = tools._evaluate
        def slow(project, deadline):
            time.sleep(0.25)
            return real(project, deadline)
        with patch.object(tools, "_evaluate", slow):
            start = time.monotonic()
            out = tools.run_and_record(self.project, "slow", "test", budget=0.03)
            self.assertLess(time.monotonic() - start, 0.20)
            self.assertEqual(out["record"]["result"], "UNKNOWN")
            again = tools.run_and_record(self.project, "busy", "test", budget=0.03)
            self.assertEqual(again["record"]["result"], "UNKNOWN")
            time.sleep(0.30)
        self.assertEqual(len(self._records()), 2)  # no late worker persistence

    def test_uncertain_write_does_not_autocheck(self):
        self.post_hook("write_file", None)
        self.assertEqual(self._records(), [])

    def test_hook_budget_under_hermes_limit(self):
        self.assertLess(tools.HOOK_BUDGET_SECONDS + core.LOCK_TIMEOUT, 30)

    def test_hooks_never_raise(self):
        os.environ["TERMINAL_CWD"] = str(self.tmp / "does-not-exist")
        lastgood._on_post_tool_call(tool_name="write_file", args=None, result=None, status="ok")
        lastgood._on_pre_tool_call(tool_name="send_email", args="not a dict")


class TestStorage(Base):
    def test_regression_concurrent_writes_keep_every_record(self):
        idx = self.tmp / "race.json"

        def add(n):
            for i in range(10):
                core.update_list(idx, lambda items: items.append({"id": core.next_id(items), "n": n, "i": i}))

        threads = [threading.Thread(target=add, args=(n,)) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        items = json.loads(idx.read_text(encoding="utf-8"))
        self.assertEqual(len(items), 80)
        self.assertEqual(len({i["id"] for i in items}), 80)

    def test_regression_corrupt_history_is_preserved(self):
        self.check("one")
        index = next((self.data / "projects").iterdir()) / "index.json"
        index.write_text("{broken json", encoding="utf-8", newline="")
        st = self.status()  # read-only: reports, does not move
        self.assertTrue(st["history_error"])
        self.assertEqual(index.read_text(encoding="utf-8"), "{broken json")
        out = self.check("two")
        self.assertIn("preserved", out["storage_note"])
        backups = list(index.parent.glob("index.json.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{broken json")

    def test_writes_are_atomic_no_temp_left(self):
        self.check()
        store = next((self.data / "projects").iterdir())
        self.assertEqual([p.name for p in store.iterdir() if p.name.endswith(".tmp")], [])

    def test_history_survives_reload(self):
        self.check("persisted")
        import importlib
        importlib.reload(tools)
        self.assertEqual(self.status()["tested_steps"][0]["label"], "persisted")


class TestLedger(Base):
    def _ledger(self):
        f = next((self.data / "projects").iterdir()) / "ledger.json"
        return json.loads(f.read_text(encoding="utf-8")), f

    def test_regression_raw_args_never_stored(self):
        args = {"to": "Pat <pat@example.com>", "subject": MARKER, "body": MARKER}
        lastgood._on_pre_tool_call(tool_name="send_email", args=args, tool_call_id="m1", session_id="s")
        lastgood._on_post_tool_call(tool_name="send_email", args=args, result=MARKER, tool_call_id="m1", status="ok")
        entries, f = self._ledger()
        self.assertNotIn(MARKER.lower(), f.read_text(encoding="utf-8").lower())
        self.assertNotIn("pat@", f.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "succeeded")
        self.assertEqual(entries[0]["target"], "recipient domain(s): example.com")
        report = Path(json.loads(tools.lastgood_report({"path": str(self.project)}))["report"]).read_text(encoding="utf-8")
        self.assertNotIn(MARKER.lower(), report.lower())

    def test_git_push_remote_only_and_blocked_status(self):
        cmd = f"git push https://token{MARKER}@github.com/x/y main"
        lastgood._on_pre_tool_call(tool_name="terminal", args={"command": cmd}, tool_call_id="g1")
        lastgood._on_post_tool_call(tool_name="terminal", args={"command": cmd}, result="", tool_call_id="g1",
                                    status="blocked")
        entries, f = self._ledger()
        self.assertIsNone(entries[0]["target"])
        self.assertEqual(entries[0]["status"], "blocked")
        self.assertNotIn(MARKER.lower(), f.read_text(encoding="utf-8").lower())
        lastgood._on_pre_tool_call(tool_name="terminal", args={"command": "git push origin main"}, tool_call_id="g2")
        lastgood._on_post_tool_call(tool_name="terminal", args={"command": "git push origin main"}, result="",
                                    tool_call_id="g2", status="error")
        entries, _ = self._ledger()
        self.assertEqual(entries[1]["target"], "remote: origin")
        self.assertEqual(entries[1]["status"], "failed")

    def test_unknown_status_is_uncertain_and_ledger_outside_project(self):
        lastgood._on_pre_tool_call(tool_name="make_payment", args={}, tool_call_id="p1")
        lastgood._on_post_tool_call(tool_name="make_payment", args={}, result="", tool_call_id="p1")
        entries, f = self._ledger()
        self.assertEqual(entries[0]["status"], "uncertain")
        self.assertNotIn(str(self.project), str(f))

    def test_ordinary_tools_not_recorded(self):
        self.assertIsNone(core.classify_action("write_file", {"path": "x"}))
        self.assertIsNone(core.classify_action("terminal", {"command": "git checkout main"}))


class TestBlameReportRegistration(Base):
    def test_blame_first_failure_ignores_unknown(self):
        recs = [{"id": 1, "result": "PASS"}, {"id": 2, "result": "UNKNOWN"}, {"id": 3, "result": "FAIL"},
                {"id": 4, "result": "PASS"}, {"id": 5, "result": "FAIL"}]
        self.assertEqual(core.first_failure(recs)["id"], 3)
        self.assertEqual(core.last_pass(recs)["id"], 4)

    def test_report_escapes_html(self):
        self.check("<script>alert(1)</script>")
        report = Path(json.loads(tools.lastgood_report({"path": str(self.project)}))["report"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", report)
        self.assertIn("&lt;script&gt;", report)

    def test_handlers_return_json_and_never_raise(self):
        for h in (tools.lastgood_check, tools.lastgood_status, tools.lastgood_blame,
                  tools.lastgood_report, tools.lastgood_setup):
            for bad in ({"path": "/nonexistent-dir-xyz"}, None, "junk", {"checks": "x"}):
                self.assertIsInstance(json.loads(h(bad, task_id="t")), dict)

    def test_setup_tool_and_command(self):
        (self.project / "lastgood-config.json").unlink()
        out = json.loads(tools.lastgood_setup({"path": str(self.project), "checks": [{"type": "file_opens", "path": "index.html"}]}))
        self.assertIn("saved", out)
        bad = json.loads(tools.lastgood_setup({"path": str(self.project), "checks": [{"type": "file_opens", "path": "../x"}]}))
        self.assertIn("error", bad)
        text = lastgood._lastgood_command('setup words index.html Sunny Day Bakery', session_id="s")
        self.assertIn("Saved 2 check", text)
        cfg = json.loads((self.project / "lastgood-config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["checks"][1]["text"], "Sunny Day Bakery")

    def test_command_subcommands(self):
        self.assertIn("Tested step #1: PASS", lastgood._lastgood_command("check first"))
        self.assertIn("PASS", lastgood._lastgood_command(""))
        self.assertIn("No check has failed", lastgood._lastgood_command("blame"))
        self.assertIn("report.html", lastgood._lastgood_command("report"))
        self.assertIn("LastGood commands", lastgood._lastgood_command("nonsense"))
        self.assertIn("LastGood blame", lastgood._blame_command(""))

    def test_register_matches_manifest_and_kwargs(self):
        class FakeCtx:
            def __init__(self):
                self.tools, self.hooks, self.commands = {}, {}, {}

            def register_tool(self, name, toolset, schema, handler, **kw):
                self.tools[name] = handler

            def register_hook(self, name, fn, *, hold_stream=False):
                self.hooks[name] = fn

            def register_command(self, name, handler, description="", args_hint="", argument_mode=None):
                self.commands[name] = handler

        ctx = FakeCtx()
        lastgood.register(ctx)
        manifest = (ROOT / "plugin" / "lastgood" / "plugin.yaml").read_text(encoding="utf-8")
        declared_tools = re.findall(r"^\s+- (lastgood_\w+)$", manifest, re.M)
        self.assertEqual(sorted(ctx.tools), sorted(declared_tools))
        self.assertEqual(sorted(ctx.hooks), ["post_tool_call", "pre_tool_call"])
        self.assertEqual(sorted(ctx.commands), ["blame", "lastgood"])
        for fn in list(ctx.hooks.values()) + list(ctx.commands.values()) + list(ctx.tools.values()):
            kinds = {p.kind for p in inspect.signature(fn).parameters.values()}
            self.assertIn(inspect.Parameter.VAR_KEYWORD, kinds, fn.__name__)
        self.assertIn('requires_hermes: ">=0.22.7"', manifest)


class TestIndependentAuditRegressions(Base):
    """Findings 1-7 from lastgood-independent-review.md (Nov 7, 2026)."""

    def _serve_body(self, body_ref):
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                data = body_ref[0]
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_f1_deleted_setup_is_unknown_not_weaker_default(self):
        self.assertEqual(self.check("base")["result"], "PASS")
        self.page().write_text(self.page().read_text(encoding="utf-8").replace("555-0100", ""), newline="")
        self.assertEqual(self.check("broken")["result"], "FAIL")
        (self.project / "lastgood-config.json").unlink()
        out = self.check("setup gone")
        self.assertEqual(out["result"], "UNKNOWN")
        self.assertIn("missing", out["setup_error"])
        self.post_hook("write_file", "ok")  # auto check still records UNKNOWN
        self.assertEqual(self.status()["tested_steps"][-1]["result"], "UNKNOWN")

    def test_f2_url_result_never_current(self):
        body = [b"<p>Bakery</p>"]
        base = self._serve_body(body)
        (self.project / "lastgood-config.json").write_text(json.dumps(
            {"checks": [{"type": "url_loads", "url": base + "/", "timeout": 2, "text": "Bakery"}]}), encoding="utf-8", newline="")
        self.assertEqual(self.check("url")["result"], "PASS")
        body[0] = b"<p>gone</p>"
        st = self.status()
        self.assertNotIn("current", st["now"])
        self.assertTrue(st["now"].startswith("UNVERIFIED"))
        self.assertNotEqual(st["tested_steps"][-1]["freshness"], "current")

    def test_f3_truncated_page_is_unknown(self):
        body = [b"x" * C.MAX_URL_BODY_BYTES + b"wanted"]
        base = self._serve_body(body)
        r = C.run_checks([{"type": "url_loads", "url": base + "/", "timeout": 3, "text": "wanted"}],
                         self.project, time.monotonic() + 5)
        self.assertEqual(r[0].result, "UNKNOWN", r[0].detail)

    def test_f4_storage_lock_is_inside_budget(self):
        store = tools.project_store(Path(os.path.realpath(self.project))) / "index.json"
        held = threading.Event()
        release = threading.Event()

        def hold():
            with core.locked(store):
                held.set()
                release.wait(2)
        t = threading.Thread(target=hold)
        t.start()
        held.wait(2)
        start = time.monotonic()
        out = tools.run_and_record(Path(os.path.realpath(self.project)), "busy", "test", budget=0.2)
        elapsed = time.monotonic() - start
        release.set()
        t.join()
        self.assertLess(elapsed, 0.6)
        self.assertEqual(out["record"]["result"], "UNKNOWN")
        self.assertIsNone(out["record"]["id"])

    def test_f5_url_query_and_fragment_redacted(self):
        secret = "SYNTHETIC_SECRET_AUDIT"
        base = self._serve_body([b"ok"])
        (self.project / "lastgood-config.json").write_text(json.dumps(
            {"checks": [{"type": "url_loads", "url": f"{base}/?token={secret}#frag{secret}", "timeout": 2}]}), encoding="utf-8", newline="")
        self.check("url")
        import socket
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        bad = C.run_checks([{"type": "url_loads", "url": f"http://127.0.0.1:{port}/?k={secret}", "timeout": 1}],
                           self.project, time.monotonic() + 3)
        self.assertNotIn(secret, bad[0].detail)
        report = Path(json.loads(tools.lastgood_report({"path": str(self.project)}))["report"]).read_text(encoding="utf-8")
        self.assertNotIn(secret, report)
        index = next((self.data / "projects").iterdir()) / "index.json"
        self.assertNotIn(secret, index.read_text(encoding="utf-8"))

    def test_f6_out_of_project_edit_not_certified(self):
        other = self.tmp / "other"
        shutil.copytree(ROOT / "sample-project", other)
        lastgood._on_post_tool_call(tool_name="write_file", args={"path": str(other / "index.html")},
                                    result="{}", status="ok", tool_call_id="x1")
        self.assertEqual(self.status()["tested_steps"], [])
        lastgood._on_post_tool_call(tool_name="write_file", args={"path": "../other/index.html"},
                                    result="{}", status="ok", tool_call_id="x2")
        self.assertEqual(self.status()["tested_steps"], [])
        self.post_hook("write_file", "ok")  # inside edit still checks
        self.assertEqual(len(self.status()["tested_steps"]), 1)

    def test_f7_draft_tools_not_logged_as_sends(self):
        for name in ("slack_send_message_draft", "gmail_create_draft", "save_email_draft"):
            self.assertIsNone(core.classify_action(name, {}), name)
        self.assertEqual(core.classify_action("send_email", {})["category"], "message")

    def test_unresolved_edit_target_is_skipped_unknown(self):
        self.assertEqual(self.check("base")["result"], "PASS")
        for args in ({}, {"path": ""}, {"patch": "*** Begin Patch\n*** Update File: x\n"}, None):
            lastgood._on_post_tool_call(tool_name="patch", args=args, result="{}", status="ok",
                                        tool_call_id="u1")
        steps = self.status()["tested_steps"]
        self.assertEqual(len(steps), 5)
        for st in steps[1:]:
            self.assertEqual(st["result"], "UNKNOWN")
            self.assertEqual(st["trigger"], "auto-skipped")
            self.assertIn("skipped", st["config_error"])
        index = next((self.data / "projects").iterdir()) / "index.json"
        self.assertNotIn("PASS", [r["result"] for r in json.loads(index.read_text(encoding="utf-8"))[1:]])


if __name__ == "__main__":
    unittest.main()
