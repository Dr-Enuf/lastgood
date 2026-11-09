# Independent heartbeat v0.4.0 targeted recheck

November 07, 2026, 2:22 PM EST. BOX only. Fresh snapshot: `/tmp/lastgood-v4-recheck-_3diz0t2/source`.

## Verdict: PASS for the two fixes / standalone gate

**94 unique tests passed; standalone simulation passed.** Independently reran the exact original cleanup-block/failure and callback-rendering probes against the snapshot. Both prior medium defects are fixed. No new concrete high/medium issue found within this targeted scope. Actual Hermes host validation remains pending; this is not a host, recovery or release guarantee.

No source, prior-version or PC changes, Git operations, other bots, external network requests or publishing. Tests ran with isolated HOME/HERMES_HOME and loopback HTTP only. Working plugin hashes matched the tested snapshot at completion.

## Verified outcomes

1. **Incomplete cleanup no longer yields PASS.** Original delayed-cleanup probe returns in 0.120 seconds with storage UNKNOWN, diagnostic UNKNOWN and `cleanup unconfirmed`. One worker still exists at that point, honestly reflected by UNKNOWN. After cleanup is released and a synthetic PermissionError occurs, the returned result remains UNKNOWN. `tools.py:462-497` publishes the storage value only after cleanup/bookkeeping, requires completion within the deadline, and returns a copied result.
2. **Completed cleanup failure is UNKNOWN.** The new independently rerun regression covers cleanup failure before the deadline and confirms safe generic error text rather than the exception payload.
3. **Callback errors are visible in the real concise outputs.** The original probe now shows `check_error=none; callback_error=PermissionError`, safe timestamp, last hook/tool and collection status. Additional independent assertions verify actual slash output and generated HTML, not just structured health. See `health.py:107-121`.
4. **No late mutation or history overwrite.** An additional independent probe created real PASS then FAIL records, delayed doctor cleanup and raised a late synthetic error. The entire returned diagnostic serialized identically before/after worker completion; existing FAIL index bytes and the normal-check lane were unchanged; no temporary probes remained. Its overall diagnostic correctly remained FAIL because the local check genuinely failed, while storage was separately UNKNOWN.
5. **No private payload leakage.** Synthetic cleanup exception, callback exception and raw message-body markers were absent from the returned diagnostic, actual slash output and generated report. Health still stores safe type/time, not raw args/messages.
6. **Status remains read-only.** The original byte/file-set comparison still reports unchanged disk state after status.

Reviewed `integration-evidence/v040-independent-audit-fixes/RESOLUTION.md`, fixed source manifest and new four-regression test module before execution. Builder's source-set hash matches independently calculated actual plugin files:

`23cf5460d6c8e94c3b84a630e7e37e136bb81e1d5d4e96d98390b238fa68b1c2`

Definition: SHA-256 of UTF-8 `json.dumps({plugin_basename: file_sha256}, sort_keys=True)` for the eight plugin source/manifest files. This independently matches the reported `23cf5460d6c8e94c3b84a630e7e37e136bb81e1d5d4e96d98390b238fa68b1c2`.

## Exact tested SHA-256 set

- `plugin/lastgood/__init__.py`: `612edd08b9994d73313677f280052a5a0ecdd6a028bb4611a6ab8899728f4656`
- `plugin/lastgood/changeview.py`: `4a9b9b44e782389bf8395cf5f3d52506dd982e0bc87765f3cbda2340663a1bb2`
- `plugin/lastgood/checks.py`: `58d309f0505dad8b4ccdeaf1dda8a358df1c2214048a00bfa5a537bdfb0228bc`
- `plugin/lastgood/core.py`: `0839bf70e281ba80ba5e22d7d33111962273d73a5188d0765700639d2aa2a114`
- `plugin/lastgood/health.py`: `b148f31ca90da0a3978b5b61b1768fd9ca69d56417e11218fe02151cfde20c96`
- `plugin/lastgood/plugin.yaml`: `555403a41a7d7a3c714df133f9a425ae09d95d3208cf28b04ea7298b58af2837`
- `plugin/lastgood/schemas.py`: `b7e17b79fb736c313e56f7f0abacbc2fb1a16f4b55c277cfcead8b6ec444b223`
- `plugin/lastgood/tools.py`: `a01d8ffb9c2f9736bf09243c32ab33dc9ef3b1fadbd7b58c4d08c38c6ad7645d`

## Evidence and next step

`/workspace/lastgood-heartbeat-independent-recheck-evidence/` contains independent 94-test output, simulation output, adapted original reproduction and its results, the additional late-history/privacy probe and output, and plugin hash manifest.

Proceed to the separately isolated v0.4.0 Hermes host gate for this exact hash set. No remediation was performed during this review.
