# Kenny — LastGood v0.4.1 tested review

Latest tested build. **Review only. Nothing to run or submit unless you choose to.**
Plugin source set: `f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282`.
Tests are the Windows-test-fix suite (every `write_text` uses `newline=""`). Plugin code did not change in that fix.

## What is new in v0.4.1

LastGood still records whether the checks you picked still hold after file edits (file opens, words present, files exist, page loads). v0.4.1 adds:

- It refuses to treat a home folder, drive/filesystem root, AppData, `/tmp`, Desktop/Documents/Downloads/OneDrive (including work/school `OneDrive - Org`) as one project. Result is UNKNOWN, never a false PASS, with a plain-English “start Hermes in a dedicated project folder” message.
- If `lastgood-config.json` is missing a `type` or uses invented fields, it stays UNKNOWN and tells you the accepted types (`file_opens`, `text_present`, `files_exist`, `url_loads`), gives a minimal example, and points to `/lastgood setup`.

## What passed — v0.4.1 (host-validated and live-tested)

- **114 unique tests** on the box (Python 3.13.5, ResourceWarning as error, 0 skipped) and on Hermes Python 3.14.9 in WSL (114, 0 skipped).
- Native Windows (`py -3`, Python 3.12.10): **114 ran, 0 failed, 4 skipped**. The four skips are symlink tests that cannot run without symlink privilege; that is intended. (An earlier native run failed one restore-freshness test because Windows `write_text` added CRLF; that was a test-only fix, plugin hash unchanged.)
- Hermes v0.22.7 doctor: **5 tools, 2 hooks**, manifest `lastgood 0.4.1`. Validate: **15/15 gates**, no warnings. Real PluginManager harness: PASS. Isolated-home freshness was true; no provisioning in these launches.
- Independent review of v0.4.1 passed (no false PASS, no guard bypass); four small follow-ups were fixed before host/live.
- **Live PTY sample** (isolated test home, local Ollama `gemma4-12b-64k:latest`, not Kenny’s real home):
  - (a) Session folder set to a stand-in home folder → `/lastgood check` UNKNOWN, “too broad… dedicated project folder”.
  - (b) Invented-field `lastgood-config.json` → UNKNOWN plus the accepted-types / `/lastgood setup` guidance.
  - (c) `/lastgood setup opens calculator.py` then `/lastgood check` → PASS (`file_opens`).
  - (d) One short model `patch` added `subtract` to `calculator.py`. Hook auto-check recorded **#3 PASS current after patch**. Status heartbeat: CALLBACKS_OBSERVED (pre=4, post=4), config=VALID, last_hook tool=patch.
- The helper queued `/lastgood status` a bit early because it mistook the on-screen footer for a ready prompt while the model was still working. That was a **test-driver** matcher issue, not a plugin defect. No second model request was sent; the hook result above is from the completed turn.
- **Owner-restart of the plugin-owning Hermes runtime remains host-untested** (same limit as v0.4.0). Health memory belongs to that runtime, not each terminal window.

This is verification history, not saved-state recovery, automatic rollback, or a security guarantee. LastGood step numbers are not Hermes checkpoint numbers.

Evidence: `integration-evidence/v041-box-only`, `v041-review-fixes`, `v041-windows-test-fix`, `v041-live`, plus the Desktop host-evidence and live-evidence folders packed with this review.

Open [the actual health/removal report](REPORT-ACTUAL-v0.4.0.html).

## What passed earlier — v0.4.0 (historical; not this code)

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

## Truth and privacy limits

This is runtime callback/check **observation**, not universal health, full tool
coverage, unforgeable delivery, recovery or a security guarantee. Registration
and a successful doctor are not proof of callback delivery. A tool failure is
separate from an internal callback exception. Health retains no raw args or
exception messages; safe tool/type/time fields only. Memory is bounded to
256 scopes; dropped updates make collection UNKNOWN. Absent session IDs are
explicitly UNSPECIFIED. Health persists across terminal reconnect while its
owner survives; it resets when that owner is actually replaced.

Doctor uses bounded local reads and a bounded explicit tempfile probe/cleanup,
skips remote URL checks, appends no history and simulates no hooks. Incomplete
cleanup is UNKNOWN; a hung OS worker can outlive the caller, with best-effort
cleanup, but cannot append late check history. Status does not probe/write.

Configured-string evidence stores no raw source lines, snippets, snapshots or
arbitrary diffs. Only adjacent stable same-config/session observations compare;
lost storage disables deltas until explicit baseline. No causal inference,
saved-state/checkpoint mapping or automatic recovery. Pattern redaction is not
universal: never configure secrets as invariants. Index retention is 200 records /
1 MiB; this does not cap the ledger. Only Hermes v0.22.7 was host-tested.

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
