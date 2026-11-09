# LastGood v0.4.0 heartbeat independent review

November 7, 2026, 2:21 PM EST. Read-only BOX review of separate `/workspace/lastgood-heartbeat/hermes-lastgood`. Snapshot before execution: `/tmp/lastgood-v4-audit-q4rm04d5/source`. No builder-source or PC modifications, Git operations, other bots or publishing. Isolated HOME/HERMES_HOME; only loopback HTTP in inspected tests. Working plugin hashes matched snapshot when review ended.

## Verdict

**90 unique tests and standalone simulation pass. No concrete high-severity issue found; two medium diagnostic-truthfulness defects should be corrected before the host gate.** Host validation pending is not itself a defect. Keep the narrow heartbeat/doctor feature and preserve tested versions.

Compared against independently tested v0.3.0: checks.py and changeview.py are unchanged. core.py only adds an escaped health line to the report. Most new behavior is in health.py, tool wrappers/status/doctor and callback instrumentation. No new tools or hook kinds were added.

## 1. MEDIUM — doctor can return PASS while its storage worker is still cleaning up, and miss cleanup failure

**Location:** `plugin/lastgood/tools.py:476-491`, especially returning `box.get('value', ...)` without requiring `done.is_set()`.

The storage worker publishes PASS before entering cleanup. If cleanup exceeds the caller deadline, the caller still returns that published PASS instead of UNKNOWN. A later cleanup error replaces the worker's box value but does not change the already returned result.

**Independent deterministic reproduction:** Delay only deletion of `.lastgood-doctor-*` behind an event; run `doctor(..., budget=.12)`; then release cleanup and raise a synthetic PermissionError. The probe's actual fixture is removed before raising, so the reproduction leaves no leaked probe behind.

Observed at return:

- elapsed 0.120 seconds;
- cleanup had entered but was still blocked;
- one active storage probe remained;
- both storage and overall diagnostic result were **PASS**;
- the returned storage result remained PASS after the worker's cleanup failure.

This violates the diagnostic's advertised write/read/cleanup completion criterion. It is not about demanding that Python kill an OS-hung thread; the bounded caller should simply report UNKNOWN when completion is unconfirmed.

**Minimal remediation:** Treat storage as completed only once its done event is set; otherwise return UNKNOWN regardless of a provisional box value. Publish the final value after cleanup, or otherwise snapshot only after cleanup is known complete. Add the timeout-during-cleanup and cleanup-failure regression. Keep best-effort late cleanup; do not add a new background service.

## 2. MEDIUM — slash status and report say `error=none` despite a recorded callback failure

**Location:** `plugin/lastgood/health.py:70-71,106-116`; callers `__init__.py:119-120` and `tools.py:318-320`.

`H.line()` only renders the normal-check lane's last_error. It does not render callback_error. Callback entry increments the callback count before ledger/check work, so this omission affects the important case where the callback arrived but its work failed.

**Independent reproduction:** Force `ledger_attempt` to raise PermissionError with a synthetic private payload, then invoke the real pre-hook function. The structured health state correctly contains `callback_error.type=PermissionError`, without retaining the payload. But the actual slash-status line says:

`Runtime callbacks: CALLBACKS_OBSERVED (pre=1, post=0); config=VALID; completed=UNOBSERVED at never; attempt=never; error=none; registration is not delivery proof`

The same rendering is used in the report. Structured `lastgood_status` JSON is truthful; the user-facing concise view is not sufficient to distinguish arrived-and-failed from arrived-and-working.

**Minimal remediation:** Label the existing field `check_error` and separately show `callback_error` by safe type/time. Include dropped-collection detail when UNKNOWN if concise space allows. Do not treat a tool's ordinary failure status as an internal callback exception. Add an assertion against actual slash/report output, not only H.read().

README lines 5-6 also say slash status shows last hook/tool, but H.line currently omits both. This is a smaller presentation mismatch: render those existing safe fields or narrow that sentence, rather than adding data collection.

## Positive checks / scope limits

- Registration and actual callback invocation are distinct. Loading, status and doctor do not increment pre/post counts. Synthetic/manual calls are explicitly described as invocation evidence, not proof of Hermes provenance or full coverage. Instrumentation observes entries before normal hook filtering, including LastGood tool callbacks; that is consistent with counting received callbacks.
- Pre/post totals and post succeeded/failed/blocked/uncertain categories are separate. Callback exception types are captured without raw exception messages; raw args/results are not retained in health. Tool names are sanitized and capped.
- Runtime/project/session isolation exists, conversation_id is a fallback, and absent identity is explicitly UNSPECIFIED. I additionally ran **two actual Python processes** against the same project/session: the second had a different runtime ID, pre=0 and UNOBSERVED, not an old alive signal. No durable health file exists.
- Scope state is capped at 256 keys; reads do not allocate new stored scopes; dropped updates produce UNKNOWN instead of silently reviving complete-count claims. Memory lock waits are bounded. Per-project evaluator/probe worker guards prevent repeated workers for that same project; the design does not claim a global thread cap across arbitrary projects.
- Status now uses create=False, current_identity defaults to mark=False, and read-only data-root resolution avoids the potentially creating storage helper. The absent-store test passes, and my independent existing-store byte comparison showed no file content or file-set changes after status. Config loading/check fingerprinting are reads; status does not probe writability. This is not an OS filesystem sandbox or hard deadline for arbitrary filesystem reads.
- Doctor uses the diagnostic lane, skips URL fetches, does not dispatch hooks, does not call history persistence and does not replace normal-check last_completed. Existing FAIL history/blame and index bytes survive doctor in the passing regression. SELF-TEST UNKNOWN remains unknown. Store metadata/lock creation occurs only during explicit doctor and is disclosed.
- Normal and diagnostic evaluator completion is recorded from the caller; a late evaluator cannot append a late history result or overwrite health completion by itself. Diagnostic evaluation does not call _mark_configured. The storage worker may outlive the caller, as disclosed; finding 1 concerns whether its incomplete result is incorrectly trusted.
- Permission/tempfile failures return safe exception type and UNKNOWN. A successful non-timeout probe cleans its temporary file. Corrupt history makes diagnostic UNKNOWN; missing/invalid configuration is explicit instead of a default false PASS.
- Report health text is HTML-escaped by core.py. Existing change evidence/secret redaction and checkpoint disclaimers remain. No automated recovery mapping, causal blame, universal redaction or host-validation claim was added.
- All 90 existing/new tests passed, including the 16 new health tests. This does not certify actual Hermes identity kwargs, callback delivery or slash rendering inside the host. Run a version-matched isolated host gate after fixes.

## Evidence

`/workspace/lastgood-heartbeat-independent-review-evidence/` contains independent `tests.txt`, `demo.txt`, deterministic `reproduce.py`/output, actual `restart_probe.py`/output, and exact plugin `hashes.json`.

## Reviewed SHA-256 set

- `plugin/lastgood/__init__.py`: `612edd08b9994d73313677f280052a5a0ecdd6a028bb4611a6ab8899728f4656`
- `plugin/lastgood/changeview.py`: `4a9b9b44e782389bf8395cf5f3d52506dd982e0bc87765f3cbda2340663a1bb2`
- `plugin/lastgood/checks.py`: `58d309f0505dad8b4ccdeaf1dda8a358df1c2214048a00bfa5a537bdfb0228bc`
- `plugin/lastgood/core.py`: `0839bf70e281ba80ba5e22d7d33111962273d73a5188d0765700639d2aa2a114`
- `plugin/lastgood/health.py`: `4a50345fb4eca70cc399497d08343c90b79c759749b7610e0066142fcba6d49f`
- `plugin/lastgood/plugin.yaml`: `555403a41a7d7a3c714df133f9a425ae09d95d3208cf28b04ea7298b58af2837`
- `plugin/lastgood/schemas.py`: `b7e17b79fb736c313e56f7f0abacbc2fb1a16f4b55c277cfcead8b6ec444b223`
- `plugin/lastgood/tools.py`: `6194149bd1b0f18d93b1611d6cd2f71119443d9c4a2692691706f88bb33b2ef6`

No remediation performed. Next: fix the two narrow truthfulness issues, add regressions, rerun the suite, then proceed to isolated Hermes validation.
