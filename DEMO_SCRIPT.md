# v0.4.0 demo guidance — recording not included

Opening line: “Callbacks remain UNOBSERVED until the plugin runtime receives
invocations; doctor is a self-test, not delivery proof.”

Actual tested story: initial status zero hooks; doctor PASS without history or
fake hooks; explicit baseline PASS; one local-model phone-removal patch yields
FAIL, pre/post1 and configured-string removal #1->#2; doctor still FAIL and
history unchanged; actual report shows evidence and scoped health.

A terminal reconnect can retain counters because the gateway owner survives.
Do NOT demonstrate terminal restart as a memory-reset proof. Do NOT present
v0.3.0 rollback/fresh PASS as a completed v0.4.0 run. Existing standalone demo
remains clearly labeled SIMULATION, not host proof. No automated recovery claim.

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
