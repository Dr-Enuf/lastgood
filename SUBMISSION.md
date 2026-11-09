# Draft only — LastGood v0.4.1

## v0.4.1 status (Nov 9, 2026) — host-validated and live-tested

v0.4.1 is v0.4.0 plus fixes from a real field failure (Hermes started in a
home folder; the model hand-wrote an invalid lastgood-config.json):
- refuses too-broad project folders (home folder, drive/filesystem root,
  C:\Users, /home, /tmp itself, AppData, Desktop/Documents/Downloads/OneDrive
  incl. work/school "OneDrive - Org" directly in a home, system folders) with
  UNKNOWN and a plain-English "use a dedicated project folder" message;
- explains invalid setups with the accepted check types, a minimal example
  and /lastgood setup; unknown per-check fields are now rejected (strict);
- echoed setup errors are redacted; Windows-portable tests (`newline=""`).

Plugin source set: `f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282`
(unchanged by the test-only Windows newline fix or this GitHub packaging). Tests set in this copy:
`9cede66135a08767577dbbc3522c90adeaab0954baeae15db5621fae4f88f683` (guard-test path fixtures generalized to `alex` / `<home-basename>`; the Windows-test-fix suite before that was `d99cada02265f0bdd675926b99453f0c3925b2ac79563b2889b705506dc6af45`).

What passed for 0.4.1:
- **114 tests** on the box and on Hermes Python 3.14.9 in WSL (0 skipped).
- Native Windows: 114 ran, 0 failed, **4 skipped** (symlink tests; intended).
- doctor --ci: 5 tools, 2 hooks, manifest 0.4.1. validate --json: 15/15, no warnings.
  PluginManager harness: PASS. Isolated freshness true; no provisioning in these launches.
- Independent review PASS; four small follow-ups fixed before host/live.
- Live PTY (isolated stand-in home + dedicated project, local gemma4-12b-64k): TOO_BROAD
  UNKNOWN; invalid-config guidance UNKNOWN; setup opens + check PASS; one model patch
  auto-check #3 PASS current; heartbeat CALLBACKS_OBSERVED pre=4/post=4 last_hook=patch.
- Test-driver note: the status helper queued `/lastgood status` during the model spinner
  (mistook the footer for a ready prompt). Not a plugin defect. No second model request.
- **Owner-restart of the plugin-owning runtime remains host-untested.**
- Native Windows 8.3 short names and `\\?\` realpath expansion were not re-proved on the host
  beyond the string-level guard and the 114-test suite.

License: MIT (Copyright (c) 2026 Kenneth Ausmus). Repo: https://github.com/Dr-Enuf/lastgood. Maintainer: Kenneth Ausmus (Dr-Enuf). Catalog `sha:` is still a placeholder until the commit exists after upload. Nothing has been posted, pushed or submitted from this package.
Everything below is the earlier v0.4.0 record and does not replace the 0.4.1 results above.


Verification history, bounded configured-string deltas, scoped callback/check
observations and an explicit SELF-TEST doctor. No saved-state engine, causal
blame, automatic recovery, universal liveness/coverage or security claim.
Nothing posted, pushed or submitted. This review does not require an action.

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
