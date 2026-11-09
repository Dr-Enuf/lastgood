# Current v0.4.0 results

## What passed — v0.4.0

- **94 unique tests** on the box and installed Hermes Python 3.14.9.
- Hermes v0.22.7 doctor: **5 tools, 2 hooks**. Validate: **15 gates**, no
  warnings. Real PluginManager harness: PASS. Exact source-set identity:
  `23cf5460d6c8e94c3b84a630e7e37e136bb81e1d5d4e96d98390b238fa68b1c2`.
- Independent audit and targeted recheck passed after two diagnostic
  truthfulness fixes: no storage PASS before cleanup completion; separate
  callback/check errors in concise status and actual HTML.
- **Real interactive sample:** initial status UNOBSERVED, pre=0/post=0.
  `/lastgood doctor` SELF-TEST/config/local checks/storage PASS with zero
  hooks and no appended check history. Explicit baseline #1 PASS.
- **One actual local Ollama native patch** removed configured `555-0100`
  (~27-second completed turn), automatically yielding #2 FAIL. Actual hooks:
  pre=1/post=1, last tool patch, succeeded=1, timestamp observed. Normal
  last completed check was FAIL, separate from diagnostic results.
- Doctor after genuine FAIL returned FAIL; persisted history bytes and hook
  counts stayed unchanged. Actual status/report show health; blame/report
  preserve configured-string removal **#1 → #2**, not edit causality.
- First CLI exited 0; dedicated terminal/driver processes subsequently ended.
  **No rollback/fresh-check repeat in v0.4.0:** the disposable sample remains
  deliberately FAIL. Real user-driven rollback/fresh PASS was tested on
  v0.3.0 and v0.2.1 only; do not attribute those runs to new code.

## Runtime-owner/reconnect nuance and corrected timeout record

Health memory belongs to the **plugin-owning runtime**, not each terminal.
Installed Hermes routes plugin slash commands through `slash.exec` to the
persistent gateway/profile owner. Read-only isolated runtime metadata and
process inspection identify gateway PID 5810 surviving the terminal clients.
A new CLI resumed the same session and returned prior counts/timestamps.
That did not restart the plugin owner; no memory-reset defect was demonstrated.
Actual plugin-owner restart is **host-untested**. Independent separate-Python-
process tests passed. No second runtime UUID was captured, so no direct UUID
equality claim is made.

The earlier “doctor timeout” was **not a proven plugin timeout**. Restart
status returned valid CALLBACKS_OBSERVED, but the test matcher wrongly expected
UNOBSERVED and waited 15 seconds. Doctor was only queued, never in the driver's
sent log; its response capture is empty. The 245-second driver cap had not
elapsed. Exact driver termination cause was unrecorded. Original failed captures
are retained, with this diagnosis superseding their earlier uncertain labels.
See `integration-evidence/v040-readonly-runtime-ownership-diagnosis.md`.

## Runtime provisioning disclosure

The earlier v0.3.0 doctor startup automatically installed runtime dependencies.
That incident and its unknown wider cache effects remain recorded. v0.4.0 host
and real-health launches reused the existing runtime after read-only freshness
checks and showed **no provisioning output**; this is not a claim that the whole
project effort involved no installations. No default Hermes config/backend was
changed. All local model settings were nonsecret and isolated, loopback only.

## Evidence map

- `integration-evidence/v040-actual-host-health/host-evidence/`: raw doctor,
  validate, 94-test suite, harness, freshness and tested source hashes.
- Its `real-health-RESULTS/`: exact invocation, raw/readable real terminal,
  individual status/doctor responses, actual history/report, sample after
  removal, original restart status/matcher failure/unsent doctor evidence.
- `integration-evidence/v040-independent-audit-fixes/`: original review,
  deterministic reproductions, resolutions and isolated regression results.
- `integration-evidence/v040-independent-recheck/`: targeted independent PASS.
- `HEALTH_DESIGN.md` and `CHANGE_EVIDENCE_DESIGN.md`: bounded schemas/semantics.
- Older code-version results and failures remain historical under evidence.
- `DELIVERY-FILES-SHA256.json`: delivered file hashes (excluding itself).


## v0.4.1 (2026-11-09) — box-only
Standalone: 109 tests OK; simulation PASS. Host doctor/validate/harness: NOT RUN. Live/interactive: NOT RUN.
Source set b5924d7617b2d647b7c9cbe972774c70e4e0a4e63e52153a2bef01195bb788cb.

## v0.4.1 review follow-ups (2026-11-09) — box-only
Standalone 114 tests OK; simulation PASS. Host/live NOT RUN. Source set f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282.

## v0.4.1 test-only Windows newline fix (2026-11-09, ~2:15 PM EST)
Plugin source set unchanged: f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282.
Only tests/*.py: Path.write_text(..., encoding="utf-8", newline="") so restores keep LF bytes on Windows.
Box suite: 114 tests OK (ResourceWarning as error). No plugin code change. Host recheck of the new Desktop sibling folder is recorded separately.

## v0.4.1 live PTY (2026-11-09, ~2:24-2:36 PM EST)
Isolated home freshness true; no provisioning. (a) TOO_BROAD UNKNOWN PASS; (b) invalid-config guidance UNKNOWN PASS; (c) setup opens + check PASS; (d) local gemma4-12b-64k patch auto-check #3 PASS current, heartbeat CALLBACKS_OBSERVED pre=4/post=4 last_hook=patch. Evidence: integration-evidence/v041-live/ and Desktop Feature Preview v0.4.1 (Windows test fix)/live-evidence. Driver queued status during the model spinner (premature ready); no second model request. Plugin set still f5454db8....

## v0.4.1 consolidated — host-validated and live-tested (2026-11-09)

Plugin source set unchanged: `f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282`.
Windows-test-fix tests set: `d99cada02265f0bdd675926b99453f0c3925b2ac79563b2889b705506dc6af45`.

Host gates (isolated WSL Hermes home, freshness true, no provisioning): doctor --ci PASS
(manifest 0.4.1, 5 tools, 2 hooks); validate --json PASS (15/15, warnings []); PluginManager
harness PASS; 114 tests on Hermes Python 3.14.9 PASS (0 skipped). Native Windows after the
test-only newline fix: 114 ran, 0 failed, 4 skipped (symlink privilege). The four skips are
intended. Owner-restart of the plugin-owning runtime is still host-untested.

Live PTY (isolated stand-in home, not Kenny’s real home; local gemma4-12b-64k): (a) TOO_BROAD
UNKNOWN; (b) invented-field config UNKNOWN with accepted-types guidance; (c) `/lastgood setup
opens calculator.py` + check PASS; (d) one model patch, hook `#3 PASS current after patch`,
heartbeat CALLBACKS_OBSERVED pre=4/post=4 last_hook=patch. The status helper queued `/lastgood
status` during the model spinner (test-driver matcher); not a plugin defect.

Packaged for review as Desktop `LastGood v0.4.1 Tested` and `LastGood-v0.4.1-TESTED-20261109.zip`.
Nothing posted, pushed or submitted.
