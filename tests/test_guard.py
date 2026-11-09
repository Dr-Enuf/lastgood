"""v0.4.1 regressions: too-broad project roots and config guidance.

Reproduces the Nov 9 2026 field failure: Hermes ran in C:\\Users\\alex, the
model hand-wrote lastgood-config.json with invented fields, and nine UNKNOWN
records said only "unknown check type None".
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import lastgood
from lastgood import schemas
from test_lastgood import Base, C, tools

KENNY_CONFIG = {"checks": [
    {"name": "File exists", "description": "calculator.py exists", "verify": "exists", "target": ["calculator.py"]},
    {"name": "Syntax check", "description": "compiles", "verify": "syntax", "target": ["calculator.py"]},
]}


def records(base):
    idx = list((base.data / "projects").glob("*/index.json"))
    return [r for f in idx for r in json.loads(f.read_text(encoding="utf-8"))]


class TestBroadRoots(Base):
    def test_windows_and_posix_broad_roots_refused(self):
        homes = [r"C:\Users\alex", "/home/alex"]
        for p in (r"C:\Users\alex", "c:/users/ALEX/", "C:\\", "D:/", r"C:\Users", r"C:\Windows",
                  r"C:\Users\alex\OneDrive\Desktop", r"C:\Users\alex\Documents", r"C:\Users\other",
                  r"\\server\share", "/", "/home", "/home/alex", "/home/alex/Desktop", "/Users/kenny",
                  "/root", "/usr", "/etc", "/mnt/c", "/mnt/c/Users/alex", "/mnt/c/Users/alex/Downloads"):
            self.assertIsNotNone(C.broad_root_reason(p, homes=homes), p)

    def test_dedicated_folders_allowed(self):
        homes = [r"C:\Users\alex", "/home/alex"]
        for p in (r"C:\Users\alex\projects\calculator", r"C:\Users\alex\OneDrive\Desktop\Hermes Plugin",
                  r"D:\work\site", r"\\server\share\site", "/home/alex/projects/calc",
                  "/home/alex/Desktop/site", "/tmp/lastgood-x/project", "/mnt/c/Users/alex/proj",
                  "/srv/www/site"):
            self.assertIsNone(C.broad_root_reason(p, homes=homes), p)


class TestHomeFolderGuard(Base):
    """The session folder IS the user's home: refuse honestly, never PASS."""

    def setUp(self):
        super().setUp()
        self._home = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(self.project)
        self.addCleanup(self._restore_home)
        self._p = patch.object(Path, "home", classmethod(lambda cls: Path(str(self.project))))
        self._p.start(); self.addCleanup(self._p.stop)

    def _restore_home(self):
        for k, v in self._home.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_explicit_check_unknown_with_plain_message_one_record(self):
        # Even a valid config and passing files must not certify a home folder.
        (self.project / "lastgood-config.json").write_text(
            json.dumps({"checks": [{"type": "file_opens", "path": "index.html"}]}), encoding="utf-8", newline="")
        out = self.check("baseline")
        self.assertEqual(out["result"], "UNKNOWN")
        self.assertEqual(out["checks"], [])
        self.assertIn("is your home folder", out["setup_error"])
        self.assertIn("too broad to be one project", out["setup_error"])
        self.assertIn("dedicated project folder", out["setup_error"])
        self.assertEqual(len(records(self)), 1)  # one honest record, nothing else

    def test_auto_check_hook_writes_no_history(self):
        (self.project / "lastgood-config.json").write_text(
            json.dumps({"checks": [{"type": "file_opens", "path": "index.html"}]}), encoding="utf-8", newline="")
        for _ in range(3):
            self.post_hook()
        self.assertEqual(records(self), [])

    def test_status_and_command_explain(self):
        s = self.status()
        self.assertIn("too broad", s["setup"]["error"])
        self.assertEqual(s["health"]["config"], "TOO_BROAD")
        text = lastgood._lastgood_command("check")
        self.assertIn("Tested step #1: UNKNOWN", text)
        self.assertIn("Setup problem: LastGood refused to check here", text)

    def test_setup_refused_nothing_written(self):
        cfg = self.project / "lastgood-config.json"
        before = cfg.read_bytes() if cfg.exists() else None
        out = json.loads(tools.lastgood_setup({"checks": [{"type": "file_opens", "path": "index.html"}]}))
        self.assertIn("too broad", out["error"])
        self.assertEqual(cfg.read_bytes() if cfg.exists() else None, before)

    def test_doctor_not_pass(self):
        (self.project / "lastgood-config.json").write_text(
            json.dumps({"checks": [{"type": "file_opens", "path": "index.html"}]}), encoding="utf-8", newline="")
        d = tools.doctor(self.project)
        self.assertEqual(d["config"], "TOO_BROAD")
        self.assertNotEqual(d["diagnostic_result"], "PASS")

    def test_dedicated_subfolder_of_home_still_works(self):
        sub = self.project / "calc"; sub.mkdir()
        (sub / "calculator.py").write_text("print(1+1)\n", encoding="utf-8", newline="")
        tools.save_setup(sub, json.loads(C.CONFIG_EXAMPLE))
        self.assertEqual(self.check("baseline", sub)["result"], "PASS")


class TestConfigGuidance(Base):
    def assert_guidance(self, text):
        for t in C.CHECK_TYPES:
            self.assertIn(t, text)
        self.assertIn(C.CONFIG_EXAMPLE, text)
        self.assertIn("/lastgood setup", text)

    def write_cfg(self, cfg):
        (self.project / "lastgood-config.json").write_text(json.dumps(cfg), encoding="utf-8", newline="")

    def test_kenny_invented_fields_unknown_with_exact_guidance(self):
        self.write_cfg(KENNY_CONFIG)
        out = self.check("check")
        self.assertEqual(out["result"], "UNKNOWN")
        self.assertIn('check #1 has no "type" field', out["setup_error"])
        self.assert_guidance(out["setup_error"])
        s = self.status()
        self.assertEqual(s["health"]["config"], "INVALID")
        self.assert_guidance(s["setup"]["error"])
        self.assert_guidance(s["tested_steps"][-1]["config_error"])  # stored record keeps the help
        self.assert_guidance(lastgood._lastgood_command("check"))

    def test_unknown_type_and_unknown_field_rejected(self):
        with self.assertRaisesRegex(C.ConfigError, r"check #1 has unknown type 'syntax'"):
            C.validate_config({"checks": [{"type": "syntax", "path": "a.py"}]})
        with self.assertRaisesRegex(C.ConfigError, r"check #2 \(file_opens\) has unsupported field\(s\): description, name"):
            C.validate_config({"checks": [{"type": "file_opens", "path": "a.py"},
                                          {"type": "file_opens", "path": "a.py", "name": "x", "description": "y"}]})
        self.write_cfg({"checks": [{"type": "file_opens", "path": "index.html", "verify": "syntax"}]})
        out = self.check()
        self.assertEqual(out["result"], "UNKNOWN")  # never guesses what "verify" meant
        self.assert_guidance(out["setup_error"])

    def test_setup_tool_rejects_invented_fields_with_help_writes_nothing(self):
        cfg = self.project / "lastgood-config.json"
        before = cfg.read_bytes() if cfg.exists() else None
        out = json.loads(tools.lastgood_setup({"checks": KENNY_CONFIG["checks"]}))
        self.assertIn("Nothing was saved", out["error"])
        self.assert_guidance(out["error"])
        self.assertEqual(cfg.read_bytes() if cfg.exists() else None, before)

    def test_no_config_no_main_file_guidance(self):
        for f in self.project.iterdir():
            f.unlink() if f.is_file() else None
        out = self.check()
        self.assertEqual(out["result"], "UNKNOWN")
        self.assert_guidance(out["setup_error"])

    def test_example_config_is_valid_and_all_known_fields_accepted(self):
        self.assertEqual(C.validate_config(json.loads(C.CONFIG_EXAMPLE)), [{"type": "file_opens", "path": "calculator.py"}])
        C.validate_config({"checks": [
            {"type": "text_present", "path": "a", "text": "b", "case_insensitive": True},
            {"type": "files_exist", "paths": ["a"]},
            {"type": "url_loads", "url": "http://127.0.0.1/", "text": "x", "timeout": 2}]})

    def test_schema_matches_validator(self):
        items = schemas.LASTGOOD_SETUP["parameters"]["properties"]["checks"]["items"]
        self.assertEqual(items["properties"]["type"]["enum"], list(C.CHECK_TYPES))
        self.assertIs(items["additionalProperties"], False)
        self.assertEqual(set(items["properties"]), set().union(*C.CHECK_FIELDS.values()))
        self.assertIn("lastgood_setup", schemas.LASTGOOD_CHECK["description"])

    def test_windows_rooted_paths_rejected_even_if_isabs_says_no(self):
        # Python 3.13+ on Windows: os.path.isabs("/etc/hostname") is False.
        with patch.object(C.os.path, "isabs", lambda p: False):
            for bad in ("/etc/hostname", "\\x", "C:foo.txt", "C:\\x"):
                with self.assertRaises(C.ConfigError, msg=bad):
                    C.validate_config({"checks": [{"type": "file_opens", "path": bad}]})
