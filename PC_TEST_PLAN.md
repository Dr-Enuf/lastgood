# v0.4.0 current validation scope

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
