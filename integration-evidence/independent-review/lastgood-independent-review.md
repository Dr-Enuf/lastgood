# LastGood independent read-only review

Reviewed November 7, 2026, 11:56 AM EST. Artifact: `/workspace/lastgood-work/hermes-lastgood`, v0.2.0.

## Verdict

**Keep this implementation, but do not call it release-ready yet.** The basic file-only story works in the standalone suite. Three small but material correctness problems remain before making the current reliability promises. This is not a recommendation to expand scope or build checkpoint mapping.

I changed no project source, PC configuration, repository, or external service. All execution was against an independent snapshot at `/tmp/lastgood-audit-fz583ewf/source`, with isolated HOME/HERMES_HOME, no inherited credentials, and only loopback HTTP fixtures. No Git, PC, posting, push, submission, or other-bot actions occurred. Plugin hashes still matched the working source when the review ended. Evidence and reproducible probes are saved in `/workspace/lastgood-independent-review-evidence/`.

## Ranked new findings: fix before claiming the corresponding feature reliable

### 1. HIGH — deleting the selected setup silently substitutes weaker checks and returns green

**Files:** `plugin/lastgood/checks.py:357-363`; `tools.py:103-106`; automatic opt-in gate at `__init__.py:61-62`.

**Reproduced:** With a phone-number text check, baseline PASS; remove the phone, FAIL; delete `lastgood-config.json`, then run the same explicit check: **PASS, source=default**. The default checks only HTML markers. No explicit user selection of a weaker check occurred.

A config file can disappear during agent work or rollback. Automatic checks then stop entirely; a later manual check silently changes the meaning of green. Existing records do become stale, but this does not prevent the new misleading green. This is particularly relevant to a plugin intended to catch agent drift.

**Minimum outcome needed:** Once selected setup existed, missing setup must be surfaced as UNKNOWN / setup required, rather than silently certifying a weaker default. Alternatively remove fallback defaults and require explicit setup. Do not add an approval framework or snapshot engine.

### 2. HIGH for URL-enabled projects — unchanged local files certify a changed remote page as PASS (current)

**Files:** `checks.py:139-146,378-398`; `tools.py:90-94,168-182`; `core.py:146-149,306-333`.

**Reproduced:** Configure only a loopback URL with required text; check PASS; change the server response so the text is absent; request status without rechecking. Output remains **PASS (current)** and the server receives **zero** new requests. A URL-only project always fingerprints the empty local-file set. A mixed project has the same issue when only remote content changes.

README lines 113-114 and the report footnote acknowledge this limitation, but the primary status still certifies an unmeasured current result. A footnote does not neutralize the green headline.

**Minimum outcome needed:** URL-containing results must not be presented as freshly verified/current remote health. Use explicit unchecked/unknown freshness for the external part, or avoid a global current PASS for such results. No polling or new monitor is required.

### 3. MEDIUM — large valid pages receive a false FAIL because the text search silently truncates

**File:** `checks.py:273-279`.

**Reproduced:** Loopback HTTP 200 body = 1 MiB of `x` followed by the required `wanted` text. LastGood returns **FAIL**, saying the text is not on the page. It is on the page, outside the read prefix.

**Minimum outcome needed:** Keep the allocation cap, but detect truncation; absent text in a truncated body must be UNKNOWN, not an assertion of broken content. Reading one extra byte can distinguish a complete body from a capped one.

## Targeted improvements / conditional concerns (not reasons to rewrite)

### 4. MEDIUM — advertised hard budget does not bound the full call under storage contention

**Files:** `core.py:46-51` and `tools.py:124-145,164`.

The timed worker bounds evaluation, not subsequent storage. `_THREAD_LOCK` is acquired without any timeout, before the timed flock loop. It is also global across projects. A thread waiting for another thread's storage operation has no bounded wait.

**Reproduced:** Hold `core.locked(index)` in another thread for 0.35 s, then call `run_and_record(..., budget=0.02)`: returns PASS after **0.352 s**, not within the requested total budget. This finite probe demonstrates the unbounded lock-acquisition path without hanging a process. A normal uncontended hook is fine; a slow storage operation can defeat the claim that the whole hook is capped at 10 s. The existing budget test only delays evaluation, and the arithmetic test does not exercise lock acquisition.

**Needed before a strict whole-hook deadline claim:** Include lock acquisition/storage in the deadline, or narrow the claim to evaluation only and disclose storage waits. Do not claim an exact total hard bound from current tests.

### 5. MEDIUM privacy caveat — URL query secrets are copied into history and the shareable-looking report

**Files:** `checks.py:83-91,277-288`; `tools.py:114,155-164`; `core.py:288-295`.

**Reproduced:** A configured loopback URL ending `?token=SYNTHETIC_SECRET_AUDIT` passes validation and appears unredacted in generated report HTML. This is not a raw ledger-argument leak: ledger body/subject redaction works. It is check-detail persistence. Credentials in URL userinfo are rejected, but query credentials are not.

**Minimum outcome needed before sharing a report:** Redact query/fragment values in persisted/displayed URL details, or clearly disallow secret-bearing URLs and warn that check details are not scrubbed. Do not advertise reports as secret-free. Configured required text is also deliberately persisted; users must not put secrets there.

### 6. MEDIUM boundary caveat — automatic hooks check session cwd, not the edited file's project

**Files:** `__init__.py:53,63`; `tools.py:54-71`.

**Reproduced:** Cwd is opted-in project A. A successful write hook names an absolute file in opted-in project B, whose phone number was removed. A receives **PASS (current)**; B has **zero records**. Histories are correctly separated by canonical project path; this is not cross-project data mixing. It is missed coverage/misattribution when tools write outside cwd.

**Minimum outcome needed:** Clearly limit automatic coverage to the session project and avoid implying the out-of-project edit was tested. Reject/skip and disclose out-of-project edits, or require explicit `lastgood_check(path=B)`. No workspace discovery feature is necessary.

### 7. LOW — draft tools are labelled as sent messages

**File:** `core.py:179-186,238-244`.

`classify_action("slack_send_message_draft", {})` returns `message / irreversible / a sent message cannot be un-sent`, even though a draft is not a send. The create-draft compensable pattern is later and does not cover that spelling. “Succeeded means tool reported success” is honest about status, but does not fix a wrong action category. Special-case draft names or keep classification wording tentative. Other heuristic misses/false positives are already disclosed and are not a demand for exhaustive detection.

## What passed and what the evidence really establishes

- **Independently rerun: 45/45 standalone tests passed**, exit 0. Includes local URL timeout/404, automatic hook function calls, file containment for static symlinks, malformed setup, staleness after manual edits, concurrent thread writes, ledger redaction, HTML escaping, and registration shape.
- **Independently rerun: standalone simulation PASS**, exit 0. It explicitly identifies itself as simulation. I did not run the Hermes harness or touch the PC.
- Supplied `doctor-r2.txt` / `validate-r2.json` record successful real-host discovery/registration and all 15 validator checks. A validator's “safe” result is a static/capability check, not a security or recovery proof.
- Supplied `tests-r2.txt` records 45 tests passing under host Python; these remain standalone tests.
- Supplied `harness-r3.txt`, checked against `scripts/hermes_harness.py`, supports **real Hermes loader, real lifecycle dispatch, cwd resolution, data directory, and payload compatibility**. It edits files with Python and manually dispatches hooks with supplied `ok`/`blocked` values. It does **not** execute real model file edits or a real rollback. The observer probe separately shows JSON success -> ok and JSON error -> error. Current plugin code appropriately suppresses automatic checks for error/unknown status.
- `live.txt` records an earlier unsupported CLI-option error **before inference**. Builder is separately completing a live test. Absence of later results in my frozen snapshot is NOT evidence that the pending test failed. Update the final evidence once that test finishes.
- File-only fingerprints, setup hashes and canonical per-project stores substantially improve the prototype. An old identical-byte record may become current again after restore; this is intentionally tested. There is no restore event tracking or guarantee that remote state was restored. Fresh checking after rollback remains an explicit command.
- Atomic replace and read-modify-write locking are present. The suite proves thread contention (80 records), not crash/power-loss safety or all cross-process failure cases. Histories are loaded/re-written in full without size/retention limits; this is a future long-session scaling concern, not a four-day hackathon blocker.
- File reads have byte caps and static realpath containment. They are **not** an adversarial filesystem sandbox: symlink replacement between resolution/open remains possible, as the integration notes already admit. Configuration reads and status fingerprinting are synchronous outside the timed evaluator in status/report. Avoid unqualified “all operations hard bounded” or sandbox claims.
- A timed-out evaluator cannot directly persist a late PASS; persistence happens in the caller and only one read-only worker per project remains in flight. This is a meaningful safety improvement. An OS-blocked daemon thread can survive until its read returns; do not call it killed or cancelled. There are no spawned subprocesses in the plugin.
- Report text is escaped, colors are allowlisted, and ledger storage does not copy message bodies, subjects, full email addresses, or raw command strings. The URL-detail leak above is a separate path.
- Explicit setup validates supported types, path containment, counts and size limits, and refuses a config symlink overwrite. The model schema says to use setup only when the user has specified checks; this is an instruction, not an enforced human-approval boundary. Do not describe it as tamper-proof governance. An agent already able to edit project files can also alter setup.

## No-post scope and presentation

`SUBMISSION.md:1-4` and `CATALOG_ENTRY_DRAFT.yaml:1-4` clearly mark drafts and require exact approval before posting/pushing/submission. I found no publishing automation in the reviewed scripts. I posted/sent nothing.

Before use, fix stale draft wording: `SUBMISSION.md:47-54` still says “saved state,” “after each step,” and green/red only; current implementation is tested states, write_file/patch only, PASS/FAIL/UNKNOWN. Catalog repo/SHA/maintainer are TODOs, so it is deliberately not submission-ready. `DEMO_SCRIPT.md:21` should make clear the fresh recheck is explicitly requested, not triggered by rollback automatically. Keep the simulation label if using the fallback demo.

**Do not imply LastGood maps a green result to a recoverable Hermes checkpoint.** Source and README correctly deny that mapping. A judged demo must show the user choosing an actual available checkpoint and then explicitly running fresh checks. No placement guarantee can follow from this audit.

## Reproduction artifacts

- `lastgood-independent-review-evidence/reproduce.py` — deterministic probes for findings 1-7; touches only disposable temp projects and loopback HTTP.
- `reproduce.txt` — observed output.
- `tests.txt`, `demo.txt` — independent baseline outputs.
- `plugin-sha256.json` — exact plugin files reviewed.

No remediation was performed. Prioritize setup disappearance and URL truthfulness; cut the URL preset for this release if it cannot be made honest quickly. Preserve the narrow file-only demo and complete the separately running real-Hermes gate.
