# v0.4.1 independent-review follow-ups — resolution (Mon Nov 9, 2026, box-only)

Review: independent-review.md (verdict PASS; 4 LOW/MEDIUM-LOW follow-ups). Previous source set b5924d76...; new source set f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282.
v0.4.0 (/workspace/lastgood-heartbeat) unchanged: 23cf5460d6c8e94c3b84a630e7e37e136bb81e1d5d4e96d98390b238fa68b1c2.

1. Work/school OneDrive: one case-insensitive child pattern `desktop|documents|downloads|appdata|onedrive( - <org>)?(/desktop|documents|downloads)?`
   is used for the home list, `users/<name>/...` (Windows) and `/home|/Users/<name>/...` (POSIX). Refused: `<WINDOWS_USER_HOME>\OneDrive - Contoso`, its Desktop/Documents.
   Still allowed: `...\OneDrive - Contoso\proj`, `...\OneDriveProjects`.
2. Refused narrowly: `C:\Users\<name>\AppData`, `/tmp` (itself only), `/home/<other>/Desktop|Documents|Downloads`.
   Still allowed: `/opt/myapp`, `/var/www/site`, `/tmp/x`, `AppData\Local\proj`, `/home/bob/Desktop/site`.
3. `_norm()` strips `\\?\` and `\\?\UNC\` (also `//?/` forms, case-insensitive UNC) before classification.
4. `lastgood_status` setup error and every handler `_err` (incl. lastgood_setup) pass through CV.redact, matching stored history.
Docs: README path note (`a:b.txt` rejected as drive-style; `notes:v2.txt` fine) and broad-folder list; SUBMISSION.md and
CATALOG_ENTRY_DRAFT.yaml describe 0.4.1 with host validation PENDING; CHANGELOG updated.

Results (isolated copy, Python 3.13.5): 114 tests OK with -W error::ResourceWarning, 0 skipped; simulation PASS;
forced symlink failure (os.symlink + Path.symlink_to raise WinError 1314): 114 ran, 4 skipped, 0 failures, 0 errors.
Mutation checks: removing each of the 7 fix points makes the suite fail (mutation-checks.txt).
New regressions: tests/test_guard_review.py (5 tests).

Still pending: Hermes host doctor/validate/harness for 0.4.1, native Windows run (8.3 short names, realpath of \\?\ paths), live test.
No PC actions, publishing, Git or other bots.
