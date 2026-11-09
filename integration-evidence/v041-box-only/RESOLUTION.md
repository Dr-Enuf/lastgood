# LastGood v0.4.1 — box-only resolution notes (Mon Nov 9, 2026)

Base: v0.4.0 exact tested source set 23cf5460d6c8e94c3b84a630e7e37e136bb81e1d5d4e96d98390b238fa68b1c2
(copied unchanged from /workspace/lastgood-heartbeat/hermes-lastgood; that copy and all earlier versions are untouched).
New source set: b5924d7617b2d647b7c9cbe972774c70e4e0a4e63e52153a2bef01195bb788cb
(sha256 of json.dumps({file: sha256}, sort_keys=True) over plugin/lastgood/*.py + plugin.yaml; per-file list in source-sha256.json).
Changed files: __init__.py, checks.py, schemas.py, tools.py, plugin.yaml.

## Why (field diagnosis, Nov 9 2026 ~9:21 AM EST, read-only)
Kenny's Windows Hermes ran LastGood v0.4.0 (hashes matched the tested build) with the session folder = <WINDOWS_USER_HOME>.
Record #1: "no lastgood-config.json and no main file to check". The model then hand-wrote lastgood-config.json with
invented fields (name, description, verify, target; no "type"). Records #2-#9: "unknown check type None". All UNKNOWN; no crash.

## Fixes
1. Project-root guard (checks.broad_root_reason, Windows + POSIX string-aware regardless of host OS).
   Refused: filesystem root, drive roots (C:\, D:/, \\server\share, /mnt/c), the user's home (Path.home/HOME/USERPROFILE),
   the folder holding user homes (C:\Users, /home), any C:\Users\<name> / /home/<name> / /Users/<name> / /mnt/<d>/Users/<name>,
   Desktop/Documents/Downloads/OneDrive(/Desktop|/Documents) directly in a home, and system folders (/usr, /etc, C:\Windows, ...).
   Allowed: any dedicated subfolder (<WINDOWS_USER_HOME>\projects\calculator, ...\OneDrive\Desktop\Hermes Plugin, /tmp/x, D:\work\site).
   Behaviour on a too-broad root: explicit check -> one honest UNKNOWN record with a plain-English message; post_tool_call
   auto-checks write NOTHING; lastgood_setup / /lastgood setup refuse and write nothing; status/health config=TOO_BROAD;
   doctor never PASS. Ledger of can't-undo actions is unchanged (not check history).
2. Config guidance (strictness kept: still UNKNOWN, never guessed). Errors now say which check and what is wrong
   (check #N has no "type" field / unknown type 'x' / (type) has unsupported field(s): ...), plus CONFIG_HELP listing
   file_opens {path}, text_present {path, text}, files_exist {paths}, url_loads {url, optional text}, a minimal valid
   example {"checks": [{"type": "file_opens", "path": "calculator.py"}]} and "/lastgood setup opens <file>" / lastgood_setup.
   Shown in the stored record, /lastgood check, /lastgood status ("Setup problem:"), the lastgood_check tool result
   (setup_error) and lastgood_setup errors ("Nothing was saved"). Unknown per-check fields are now REJECTED (previously
   silently ignored) — intentional: an ignored "verify": "syntax" would let a user believe something was checked.
   Model-facing schema: lastgood_check description says not to hand-write the config and gives the format; lastgood_setup
   items now declare enum types, allowed properties and additionalProperties:false.
3. Windows-native test portability. The four symlink tests use Base.symlink_or_skip (skip on OSError/NotImplementedError,
   e.g. WinError 1314); simulated with symlink_to forced to raise: 4 skipped, 0 failures (symlink-unavailable-sim.txt).
   On POSIX nothing is skipped. Path assertion: "/etc/hostname" relied on os.path.isabs, which is False on Windows
   Python 3.13+ — fixed in CODE (_validate_rel_path also rejects leading "/" and any drive prefix such as "C:foo"), with a
   regression that forces isabs False. Text assertions: all test file I/O is now explicit UTF-8, and the retention test
   compares exact bytes instead of read_text (no codepage/newline translation).
   Caveat: the exact Windows failure log was not available in this box stage; these are the identified causes, not a
   Windows re-run. test_missing_binary_and_escape_no_delta skips as a whole without symlinks (its non-symlink assertions
   are covered by other tests).

## Results (box only, isolated copy /tmp/lg041/src, Python 3.13.5)
- Full suite: 109 tests, OK, 0 skipped (was 94). New: tests/test_guard.py (15 tests).
- Simulation demo_end_to_end.py: SIMULATION RESULT: PASS.
- Behaviour examples (exact messages): behavior-examples-SIMULATION.txt.

## NOT done / not claimed
No PC actions, no Hermes host doctor/validate/harness, no live model run, no install on Kenny's machine, no publishing.
Host validation for v0.4.1 is NOT RUN; v0.4.0/v0.2.1 host passes do not cover it. Kenny's existing
<WINDOWS_USER_HOME>\lastgood-config.json is untouched.
