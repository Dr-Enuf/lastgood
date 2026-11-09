# Independent audit resolution (box only, Nov 7 2026 ~12:15 PM EST)
Each fix has a regression in tests/test_lastgood.py::TestIndependentAuditRegressions. All 7 fail on pre-fix code and pass on fixed code.
1 HIGH missing setup -> defaults: now UNKNOWN ("set up ... but is now missing") once a project was ever configured (project.json "configured" flag or any record with config_source=project). Auto-check still records UNKNOWN.
2 HIGH URL freshness: records with url_loads checks report freshness "files current; web page not rechecked"; status says UNVERIFIED, never "current".
3 MED truncation: reads MAX+1 bytes; text missing within the truncated 1 MB is UNKNOWN, not FAIL.
4 MED unbounded thread lock: _THREAD_LOCK acquired with timeout; run_and_record passes remaining budget; on timeout returns UNKNOWN with id None and "NOT recorded".
5 MED URL secrets: redact_url() drops userinfo/query/fragment in every url_loads detail/error, so in index/report too.
6 MED out-of-project edits: post hook skips auto-check when args.path resolves outside the session project (logged, no record). Edits with no path arg are still checked against the session project (limitation).
7 LOW drafts: tool names containing word "draft"/"drafts" are not classified as irreversible sends.
Not addressed: SUBMISSION.md lines 47-54 stale wording; DEMO_SCRIPT note that recheck is explicit; host doctor/validate/harness NOT rerun on this code.

## v0.2.1 follow-up (Nov 7 2026 ~12:20 PM EST)
- Remaining limitation from finding 6 FIXED: when a write_file/patch target cannot be resolved (no/empty/non-string path, e.g. multi-file patch), the auto-check is skipped fail-closed and an UNKNOWN record with trigger "auto-skipped", skipped=true and a reason is written. The session project is never certified for that edit. Regression: test_unresolved_edit_target_is_skipped_unknown.
- SUBMISSION.md stale wording and DEMO_SCRIPT explicit re-check fixed.
