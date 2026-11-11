# Changelog

## 0.4.2 — 2026-11-11 (catalog-review fixes)
Linux standalone suite: 134 tests, 0 failures (was 114 before this change).
Windows was not re-run. `hermes plugins validate` was not run: the Hermes
build available here (PyPI hermes-agent 0.19.0) has no `validate` subcommand.
- `url_loads` resolves every A/AAAA address and refuses link-local, cloud-metadata
  (`169.254.0.0/16` including `169.254.169.254`, `fe80::/10`, `fd00:ec2::254`), and
  unspecified (`0.0.0.0`, `::`) addresses, including IPv4-mapped IPv6, on the first
  request and every redirect hop. It connects to the address it validated.
- Private ranges (`10/8`, `172.16/12`, `192.168/16`, `fc00::/7`) stay refused unless
  the user turns on the `allow_private_urls` plugin setting. `lastgood_setup` refuses
  `url_loads`; `/lastgood setup` and a hand-edited `lastgood-config.json` can still add one.
- The Hermes home folder, and anything inside it, cannot be a project.
- `text_present` also refuses `auth.json`, `auth.lock`, `webhook_subscriptions.json`,
  and `mcp-tokens` (file or directory).

## 0.4.1 — 2026-11-09 (host-validated and live-tested; owner-restart still host-untested)
- Test-only Windows newline fix: every test `Path.write_text` now uses `newline=""` so a restore
  writes the same bytes as on POSIX (no CRLF translation). Plugin code unchanged.
  `test_rollback_flow_old_results_stale_next_check_fresh` was the native Windows failure.
- Refuse too-broad project folders (home folder, drive/filesystem root, C:\Users, /home, Desktop/Documents/Downloads/OneDrive
  directly in a home, system folders): UNKNOWN with a plain-English "start Hermes in a dedicated project folder" message;
  no auto-check history; setup refused.
- Invalid lastgood-config.json now explains exactly what is wrong (check number, missing/unknown type, unsupported fields)
  and lists the accepted types with a minimal valid example and /lastgood setup. Unknown per-check fields are now rejected.
- Model-facing tool descriptions/schema describe the config format and point to lastgood_setup.
- Config paths starting with "/" or a drive prefix are rejected on every OS (Windows Python 3.13+ isabs change).
- Tests: symlink tests skip cleanly without symlink privilege; test I/O is explicit UTF-8.
- Independent-review follow-ups: also refuse work/school "OneDrive - <Org>" (and its Desktop/Documents/
  Downloads), AppData, /tmp itself and other users' Desktop/Documents/Downloads; strip \\?\ and \\?\UNC\
  prefixes before the guard; redact echoed errors in lastgood_status setup and lastgood_setup. 114 tests.

## 0.4.0 — 2026-11-07
Runtime health (memory-only callback/check observations) and /lastgood doctor self-test. Host gates + partial real interactive test.

## 0.3.0 — 2026-11-07
"What changed" evidence for configured text checks (presence deltas only, redacted, bounded).

## 0.2.1 — 2026-11-07
Audit fixes (URL redaction/freshness, bounded locks, fail-closed setup, draft tools, unresolved edits). Real interactive sample workflow verified.
