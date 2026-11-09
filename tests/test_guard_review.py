"""v0.4.1 independent-review follow-ups (Nov 9 2026): broad-folder gaps,
extended-length prefixes, and redaction of echoed config errors."""
import json
import os

import lastgood
from test_lastgood import Base, C, tools

HOMES = [r"C:\Users\alex", "/home/alex"]


class TestReviewGuardGaps(Base):
    def refused(self, p):
        self.assertIsNotNone(C.broad_root_reason(p, homes=HOMES), p)

    def allowed(self, p):
        self.assertIsNone(C.broad_root_reason(p, homes=HOMES), p)

    def test_work_school_onedrive_refused_home_list_and_users_pattern(self):
        for p in (r"C:\Users\alex\OneDrive - Contoso", r"C:\Users\alex\OneDrive - Contoso\Desktop",
                  r"C:\Users\alex\onedrive - contoso\documents", r"C:\Users\bob\OneDrive - Uni",
                  r"C:\Users\bob\OneDrive - Uni\Documents", "/home/alex/OneDrive - X",
                  "/home/alex/OneDrive - X/Desktop"):
            self.refused(p)
        # Called with only a home list (no users/<name> pattern) still refuses.
        self.assertIsNotNone(C.broad_root_reason("/srv/u/me/OneDrive - Org/Documents", homes=["/srv/u/me"]))
        for p in (r"C:\Users\alex\OneDrive - Contoso\proj", r"C:\Users\alex\OneDrive - Contoso\Desktop\site",
                  r"C:\Users\alex\OneDriveProjects"):
            self.allowed(p)

    def test_appdata_tmp_and_other_users_personal_folders_refused_narrowly(self):
        for p in (r"C:\Users\alex\AppData", r"C:\Users\bob\AppData", "/tmp", "/tmp/",
                  "/home/bob/Desktop", "/home/bob/documents", "/home/bob/Downloads", "/Users/bob/Desktop"):
            self.refused(p)
        for p in ("/opt/myapp", "/var/www/site", "/tmp/x", "/tmp/lastgood-test/project",
                  r"C:\Users\alex\AppData\Local\proj", "/home/bob/Desktop/site", "/home/bob/proj"):
            self.allowed(p)

    def test_extended_length_prefixes_stripped(self):
        for p in ("\\\\?\\C:\\Users\\alex", "\\\\?\\C:\\", "\\\\?\\UNC\\server\\share",
                  "\\\\?\\unc\\server\\share\\", "//?/C:/Users/alex", "\\\\?\\C:\\Users\\alex\\OneDrive - X"):
            self.refused(p)
        for p in ("\\\\?\\C:\\Users\\alex\\proj", "\\\\?\\UNC\\server\\share\\site"):
            self.allowed(p)

    def test_status_and_setup_errors_redacted(self):
        secret = "sk-SYNTHETICSECRET123456"
        cfg = self.project / "lastgood-config.json"
        cfg.write_text(json.dumps({"checks": [{"type": secret, "path": "index.html"}]}), encoding="utf-8", newline="")
        s = self.status()
        self.assertIn("unknown type", s["setup"]["error"])
        self.assertNotIn(secret, json.dumps(s))
        before = cfg.read_bytes()
        out = tools.lastgood_setup({"checks": [{"type": secret}],
                                    "path": str(self.project)})
        self.assertIn("[redacted]", out)
        self.assertNotIn(secret, out)
        out2 = tools.lastgood_setup({"checks": [{"type": "file_opens", "path": "a", "ghp_SYNTHETICFIELD99": 1}],
                                     "path": str(self.project)})
        self.assertIn("unsupported field", out2)
        self.assertNotIn("ghp_SYNTHETICFIELD99", out2)
        self.assertEqual(cfg.read_bytes(), before)

    def test_drive_style_relative_names_rejected_others_kept(self):
        with self.assertRaises(C.ConfigError):
            C.validate_config({"checks": [{"type": "file_opens", "path": "a:b.txt"}]})
        for ok in ("notes:v2.txt", "src/app.py", ".well-known/x"):
            C.validate_config({"checks": [{"type": "file_opens", "path": ok}]})
