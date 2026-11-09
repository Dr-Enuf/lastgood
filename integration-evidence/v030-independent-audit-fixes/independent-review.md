# Independent LastGood v0.3.0 review — standalone safety gate

November 7, 2026, 1:34 PM EST. Reviewed separate `/workspace/lastgood-changeview/hermes-lastgood` only. No source edits, PC actions, Git operations, publishing, or external network requests. Snapshot before execution: `/tmp/lastgood-v3-audit-nqnxf_l7/source`. Tests used isolated HOME/HERMES_HOME and local HTTP only. Plugin source hashes were unchanged at end of review.

## Verdict

**The narrowed feature is real and useful; hold the initial safety gate for three targeted corrections below.** This is configured-string membership evidence, not captured source snippets or a full diff. That narrowing is honestly documented and is not itself a defect. No rewrite or scope expansion is warranted.

Independently reran **66 tests: PASS** (53 existing + 13 new); independently reran the **standalone simulation: PASS**, including `removed configured text in index.html: 555-0100`. These do not validate v0.3.0 inside Hermes. Historical v0.2.1 host/rollback evidence is correctly distinguished and cannot be inherited as a v0.3.0 pass.

## Ranked actionable findings

### 1. MEDIUM — known-sensitive files can be read and evidenced through an ordinary in-project symlink

**Location:** `plugin/lastgood/checks.py:142-150,175-188`; `changeview.py:38-46`.

Sensitive-name checks inspect the configured alias, not its resolved target. Reproduction in a disposable project:

1. Create `.env` containing `CONTACT=555-0100`.
2. Create `index.html` as a symlink to that same in-project `.env`.
3. Configure `text_present(index.html, 555-0100)` and check.
4. Replace `.env` content with `CONTACT=gone` and check again.

**Actual:** PASS then FAIL, with persisted removed-text evidence naming `index.html`. The `.env` was also included in content fingerprinting through the alias. This needs no race or filesystem attack; static symlinks suffice. Outside-project escape checks still work.

**Minimum fix:** Apply sensitive-path exclusion to the canonical in-project target as well as the configured name, consistently for reading, fingerprinting and observations. Return UNKNOWN/no evidence for the alias. Add this exact regression. Do not build an OS sandbox or prohibit all ordinary symlinks.

### 2. MEDIUM — a nonpersisted UNKNOWN observation is bridged by the next delta

**Location:** `tools.py:208-225` and `changeview.py:59-84`.

Comparison only sees the previous persisted record. A failed persistence returns UNKNOWN to the caller but leaves no gap indicator for the next successful write.

**Reproduced:** Baseline PASS; hold the index storage lock in another thread for 0.2 seconds; call `run_and_record(..., budget=0.02)`. It returns `UNKNOWN`, `id=None`, correctly reporting that it was not recorded. Release the lock, remove the phone number, and run another check. The new FAIL nevertheless compares to the baseline and produces a removed-text delta.

This does not fabricate source context and the two retained endpoint memberships are genuine, but it violates the explicit no-bridging-UNKNOWN/missing-observation guarantee in the design. The existing UNKNOWN-gap test only covers UNKNOWN records that successfully reached disk.

**Minimum fix:** Mark the next comparison unavailable after an unrecorded observation in the same process/project, or explicitly narrow the contract to successfully persisted observations and disclose this exception. If retaining the current no-gap promise, test storage-timeout/nonpersisted UNKNOWN separately. Do not claim that no failed persistence could have occurred across restarts without durable evidence.

### 3. MEDIUM — the advertised 1 MiB retained-index bound is not the actual on-disk bound

**Location:** `changeview.py:97-100`; `core.py:107-108`; retention caller `tools.py:210-219`.

`retain()` measures the unindented JSON encoding, but storage writes `indent=2`. The suite measures only the former and therefore misses the real artifact size.

**Reproduced using a real valid record:** Configure five text checks with a 400-character multibyte invariant. Copy that resulting sanitized record into a 200-record retention fixture, run the production `retain()` and production `atomic_write_json()` functions. Retention keeps 122 records, compact encoding **1,042,347 bytes**, but actual file is **1,160,201 bytes**, exceeding **1,048,576 bytes**.

**Minimum fix:** Measure the exact serialized encoding that will be written, and assert the saved file size in a regression. The existing 200-record count cap and per-label UTF-8 bounds do work. No need for a new storage engine or ledger retention feature.

## Redaction caveat: useful targeted improvement, not a universal-secrets blocker

`changeview.py:10-14,24-35` redacts bare assignments such as `api_key=...`, but **does not match ordinary quoted JSON assignments**. A configured invariant `"api_key": "SYNTHETIC_SECRET_123456"` persists unchanged in presence observations/history. Reproduced with no real credential. This is a recognizable credential format worth covering, but the docs explicitly say never configure secrets and that redaction is not universal, so this is not grounds to demand a comprehensive secret scanner. Add quoted-key coverage or document that common case explicitly. The invariant's project config necessarily also contains user-selected text; do not promise universal secret erasure.

The design statement that credential markers in the *file* suppress evidence (`CHANGE_EVIDENCE_DESIGN.md:11-12`) is broader than implementation: observation suppression checks private-key markers in data and redacted configured text, not ordinary credential assignments elsewhere in source. No raw context is stored, so those unrelated assignments do not themselves leak through evidence. Align that sentence rather than adding broad scanning scope.

## What I checked positively

- Observation creation reuses the existing bounded file read. No extra raw-context read, source snapshot, subprocess, shell check or dependency was added. Only configured text/path and presence metadata enter evidence.
- UTF-8 decode failure, binary controls, missing files, oversized reads, outside-project paths and direct sensitive names suppress eligible observations; UNKNOWN does not turn into green. Credential/private-key pattern handling happens before new index-record persistence, not just at rendering.
- Evidence is compared during locked persistence against the adjacent stored record. Config hashes must match; explicit session IDs must match; legacy/overlapping intervals and stored UNKNOWN/skipped records prevent a delta. Observation lists retain their check positions, including None, so zip alignment does not shift when an earlier check is ineligible.
- A busy evaluator yields UNKNOWN rather than a second concurrent read for that project. Separate per-project stores and atomic locked ID allocation remain. Concurrent-ID test passes. A delayed evaluator cannot append a late result directly.
- Interval timestamps use `time.time()`, so the order criterion assumes a normally progressing wall clock. This is not a process-independent causal clock; no need to expand the hackathon feature into one. Explicitly missing session IDs are treated alike as standalone, so host tests must verify real hook/command identity payloads rather than assuming absence proves standalone.
- Both before/after record IDs and the unobserved-edits/not-proof-of-cause caution are in the delta. Historical freshness appears in blame and the corresponding report table row. The report does not claim a tested state is a restorable checkpoint. Identical restored local bytes may match historical fingerprints, but fresh checks still require explicit invocation.
- Report evidence is escaped through `html.escape`, including configured text, paths and descriptions; the actual-report XSS regression passes. Credential-looking labels are sanitized before new persistence. No raw message arguments are newly captured by this feature.
- Existing records without change-evidence or interval fields remain readable; they produce unavailable/no-comparable evidence rather than fabricated deltas. The original standalone behavior tests pass. Retention deliberately expires history; do not imply first-ever lifetime failure or permanent immutable audit. A retained delta may reference a before-ID that has expired; it is historical evidence, not an independently available saved state.
- Inherited host evidence and release-ready v0.2.1 are explicitly labeled historical/untouched. v0.3.0 needs its own doctor/validate and real hook/command checks after the targeted fixes. No host failure is inferred from tests not yet run.

## Evidence / reproduction

Saved outside the source in `/workspace/lastgood-changeview-independent-review-evidence/`:

- `tests.txt`: 66 passing tests.
- `demo.txt`: passing simulation with observed phone-invariant removal.
- `reproduce.py`, `reproduce.txt`: deterministic sensitive-symlink, exact serializer size, quoted-assignment and unpersisted-UNKNOWN-gap probes. All fixtures are temporary; no PC state or external services are involved.
- `plugin-sha256.json`: precise reviewed Python source hashes.

**Next:** Correct the three narrow contract failures, rerun their regressions and the 66-test baseline, then run the separate v0.3.0 host gate. Keep the honest configured-text feature; do not revive full snippets, causal blame or automatic rollback mapping.
