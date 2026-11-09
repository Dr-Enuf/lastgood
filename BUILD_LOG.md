# Build log

## Sat Nov 7, 2026 (night, from phone chat)
Researched the hackathon + Hermes plugin guide + existing market
(notes and sources in PLAN.md / chat). User approved the LastGood
concept, then the addition of preset checks for non-coders.

Built:
- SPEC.md, PLAN.md, README.md, DEMO_SCRIPT.md, SUBMISSION.md,
  TOMORROW_CHECKLIST.md, REVIEW_FOR_ANOTHER_AGENT.md
- plugin/lastgood/: plugin.yaml, __init__.py, schemas.py, tools.py,
  checks.py, core.py (stdlib only)
- sample-project/ (breakable bakery page + lastgood-config.json)
- tests/test_lastgood.py — 16 tests
- scripts/demo_end_to_end.py + demo-output/report.html

Verification run here (Python 3.12, no Hermes installed):
- `python3 -m unittest discover -s tests -v` → Ran 16 tests in 0.568s — OK
  (includes a local-HTTP-server test for the URL preset; it prints two
  expected 404 log lines for the missing-page case)
- `python3 scripts/demo_end_to_end.py` → DEMO RESULT: PASS
  (step 1 GOOD → breaking change BROKEN → blame names the breaking
  step → report written)

NOT yet verified (needs user's computer + real Hermes, Nov 8):
- hermes plugins doctor / validate output
- Live hook signatures and slash-command behaviour
- Plugin data-dir location under a real Hermes profile
- Whether a plugin can read the built-in checkpoint list (spike)

## 2026-11-07 (later) — Grok + Gemini reviews; merged plan APPLIED
- Grok review: ship smaller, don't pivot. Muse verified its core
  claims (checkpoints are pre-change, max 1/directory/turn, opt-in;
  public plugin API has no checkpoint interface; Chronos PR #149151
  is a real validated competitor). Triage: GROK_REVIEW_TRIAGE.md.
- Gemini review: ship, don't pivot; clashed on bisect (praised it),
  ledger (cut it), fallback snapshot engine (add it). Comparison and
  rulings: COMPARISON_GROK_VS_GEMINI.md. User approved the merged plan.
- Applied same day:
  - checks.py: "command" preset REMOVED (no subprocess anywhere now);
    a config using it fails closed as an unknown type (regression test).
  - core.py: unused bisect_first_bad REMOVED. Report wording: "Checks
    first failed after step #N", "last step whose checks passed",
    ledger heading "Observed actions a file rollback won't undo",
    ledger rows show attempted/observed status.
  - tools.py / __init__.py: blame verdict + advice reworded (re-run
    checks after restore; earlier results are stale); ledger entries
    now record status attempted (pre_tool_call) vs observed
    (post_tool_call).
  - schemas.py, plugin.yaml, CATALOG_ENTRY_DRAFT.yaml, SPEC.md,
    PLAN.md, README.md, DEMO_SCRIPT.md, SUBMISSION.md, INSTALL_PREP.md:
    pitch = "Know which checks passed on which saved state — and what
    restoring it won't undo"; no bisect/exact-step/test-command claims.
  - TOMORROW_CHECKLIST.md: Grok's integration gate (A1–A5 + stress
    B1–B4) is now the Sun Nov 8 test plan.
- Verification after changes: `python3 -m unittest discover -s tests`
  → Ran 15 tests — OK. `python3 scripts/demo_end_to_end.py` →
  DEMO RESULT: PASS (blame prints the new first-failed wording).
- Still NOT verified: everything inside a real Hermes install (the
  gate above). Spike question is now ANSWERED from docs (no public
  checkpoint API) — the live test is about hook behaviour, data dir,
  and the /rollback target mapping, not about finding an API.

## 2026-11-07 (late morning, EST): Grok Bot takeover, v0.2.0 (standalone only)
Kenny approved handing the build over to Grok Bot. Work was done in a
copy; the reviewed v0.1 baseline and the uploaded ZIP are unchanged.
Hermes interfaces were read (not run) from Kenny's install: v0.22.7,
commit b200f5bc. Nothing was installed, run, pushed or posted on the PC.

Defects found in the v0.1 review, each now fixed and covered by a test:
- Automatic checks: v0.1 never ran checks from hooks and ignored
  `<project>/lastgood-config.json`. Now the config is read from the
  project, `lastgood_setup` and `/lastgood setup` save it, and
  post_tool_call runs the checks after a successful write_file/patch in
  opted-in projects (10 s cap).
- Shared history: all projects shared one history. Now the history and
  ledger are kept per project, under plugin_data_dir("lastgood").
- Stale results: a result stayed "good" after the files changed. Now each
  record has a content fingerprint, a setup hash and session ids, and is
  marked current or stale.
- Bad setup could keep an old green result as current. A malformed setup
  is now UNKNOWN and marks older results stale. An unreachable page or a
  timeout is UNKNOWN, not FAIL.
- Concurrent writes lost records, and corrupt JSON was silently
  replaced. Writes are now locked and atomic, and corrupt files are kept
  as .corrupt-*.
- The ledger stored raw arguments. Now it stores only a category, the
  tool name, a redacted target and a status (attempted, then
  succeeded/failed/blocked/uncertain) matched by tool_call_id.
- `../`, absolute paths and symlink escapes were accepted. All are now
  rejected; reads are capped at 2 MB, URLs are http(s) only and timeouts
  capped at 5 s.
- Also: a lastgood_setup tool, /lastgood subcommands, and
  `requires_hermes: ">=0.22.7"` (read from 0.22.7 only; untested live).
  Version 0.2.0.

New: scripts/hermes_harness.py (drives the real plugin manager, no
model calls) and PC_TEST_PLAN.md (isolated test folder, doctor --ci,
validate --json, harness, bounded live chat). Docs updated; stale
handoff files are marked SUPERSEDED. The headless demo is now labelled
STANDALONE SIMULATION.

Verification (box, Python 3.13, isolated HOME/TMPDIR, loopback only):
`python3 -m unittest discover -s tests` → Ran 43 tests, OK.
`python3 scripts/demo_end_to_end.py` → SIMULATION RESULT: PASS.
The harness was smoke-tested against stub Hermes modules only.
Still NOT verified: anything inside real Hermes (PC_TEST_PLAN.md).

## Nov 7, 2026 (late morning EST): real host integration stage

## Actual PC results
- Plugin doctor --ci: exit 0; real discovery/import/registration passed,
  5 tools, 2 hooks. See integration-evidence/doctor-r2.txt.
- Catalog validate --json (no --install-deps): exit 0, all 15 checks
  passed, warnings [], security scan safe, declared tools/hooks match.
  See validate-r2.json.
- Standalone suite under installed Hermes' Python: 45 tests, OK.
  See tests-r2.txt. These are still standalone tests, not live chat.
- Real PluginManager harness: final exit 0; all required checks OK.
  See harness-r3.txt. Loaded through real discover_plugins(); tool and
  command registration, lifecycle hook dispatch, cwd, data directory,
  IDs, automatic PASS/FAIL and correlated redacted blocked ledger verified.
  It edits files with Python then fires real lifecycle hooks. It does
  NOT prove an actual model tool call triggered those hooks.
- File tools loaded from tools.file_tools: write_file and patch exist;
  edit_file absent. Real observer mapping: success -> ok, error -> error;
  plain text -> ok. /lastgood and /blame both registered.
- Hard-check deadline regression passed on installed Python: a slow
  read-only worker returns UNKNOWN to the caller within its budget;
  a second call while busy is UNKNOWN and a finished late worker cannot
  append a misleading PASS later. One worker per project maximum.
- Repeated real processes reloaded existing history/ledger. This supports
  persistence, not a full interactive session-resume verdict.

## Failures found and addressed
- First harness did not import built-in file tools; its registry probe
  incorrectly showed them absent. Fixed to import tools.file_tools.
- Repeated harness runs incorrectly aggregated every project's records
  and assumed empty histories. Two harness attempts exited 1 for those
  assertions. Fixed to select only the requested project and only new
  records. No evidence was deleted to make it pass. R3 passed.
- Python 3.14 exposed an unclosed HTTPError response in a URL test.
  Plugin now closes HTTPError responses; the rerun had no such warning.
- Check deadline was cooperative only. Fixed to wait a bounded time on
  a read-only daemon worker, cap per-project workers, and persist only
  from the caller. Unknown write status no longer triggers auto-checks.

## Live chat: BLOCKED, not passed
One bounded local-model attempt used custom provider at
http://127.0.0.1:11434/v1, model gemma4-12b-64k:latest (confirmed present),
--ignore-user-config, --ignore-rules, --checkpoints, --in the disposable
project, file/lastgood toolsets, 4 turns, 230-second run budget and an
outer 245-second timeout.
It exited 2 BEFORE inference:

    Error: Unsupported gateway CLI options: --run-budget.
    No local fallback or policy changes were made.
    --run-budget: use `agent.run_budget_seconds` in config.yaml

No fallback, policy changes or second model attempt were made. No test
model process remains. No model-driven edits, real checkpoint restore,
interactive slash-command rendering or end-to-end recovery passed.
The following remain UNRUN in live chat: baseline -> good/bad edits,
blame/report, multiple edits/turn, manual-edit stale, URL timeout,
rollback target/diff/restore and interactive restart persistence.
Also, --ignore-user-config may discard the isolated plugin enable list;
that must be resolved explicitly, without ever reading/copying the real
configuration. The supported next approach requires a small test-home
config with just plugin enable and run-budget settings, after review.

## Unexpected host behavior / scope note
The FIRST invocation of the installed Hermes wrapper with a new
HERMES_HOME automatically prepared an isolated runtime and printed
"Installing Python dependencies" twice (see doctor.txt). No dependency
installation flag was used. This was not expected or requested. Later
runs reused that prepared runtime. The known created files are beneath
<TEST_ROOT>/integration-20261107-1134/home, but shared
package-cache changes were not audited; do not claim absolutely no
filesystem writes outside the test folder. No explicit install, upgrade,
default-home config mutation or service operation was performed.

## Remaining technical limits for independent review
A timed-out read-only worker can continue until its OS operation returns;
Python cannot kill that thread safely. The hook caller returns UNKNOWN,
no late result is persisted, and no second worker starts for that project.
File safety is realpath containment with bounded reads, not an OS sandbox
against malicious concurrent symlink replacement. URL checks contact only
configured http(s) addresses but DNS/redirects deserve review.
A returned old content fingerprint can match again after restoration;
that historical record displays current-by-bytes, while the newest FAIL
is stale until an explicit fresh check. No checkpoint mapping is claimed.


## 2026-11-07 ~12:15 PM EST — independent-audit fixes (box only)
- Backup of pre-fix plugin: /workspace/lastgood-work/plugin-before-audit-fixes-*.
- Fixed audit findings 1-7 (see integration-evidence/independent-review/RESOLUTION.md). Added 7 regressions; they fail on pre-fix code (7/7) and pass now.
- Box suite: 52 tests OK (isolated env, -W error::ResourceWarning). Demo: SIMULATION RESULT: PASS (standalone only).
- Live retry recovery: read-only PC check was NOT approved on the PC; live-retry result is still unknown. No new model calls launched.
- Desktop FINAL-REVIEW package (SHA 2cd218a2...) is STALE: pre-audit code.

## 2026-11-07 ~12:20 PM EST — v0.2.1 (box only)
- Unresolvable write_file/patch target -> skipped, UNKNOWN record (no certification). Regression added.
- Version 0.2.1 in plugin.yaml, CATALOG_ENTRY_DRAFT.yaml, SPEC, README, SUBMISSION. README opening now says "verification history"; no saved-state recovery claims. DEMO re-check is explicit.
- Isolated box run (Python 3.13.5): 53 tests OK; demo SIMULATION RESULT: PASS. Saved: integration-evidence/tests-v0.2.1-box-isolated.txt, demo-v0.2.1-box-isolated-SIMULATION.txt.
- v0.2.1 host validation: NOT RUN. v0.2.0 host checks: historical. Live test: UNKNOWN (evidence read not approved).
- Pre-change copy: /workspace/lastgood-work/hermes-lastgood-before-0.2.1-*.

## 2026-11-07 12:24 PM EST — v0.2.1 authorized host milestone
- Machine <MACHINE> (a83d7698-34e9-4b87-9c63-c46fabfe257d). New test source/project: <TEST_ROOT>/v021-20261107-1220.
- Input ZIP SHA256 9ac45217f60823199818f75ec8737647059340091f3a06322c2eaecda0357543; source manifest 0.2.1.
- Recovered previous v0.2.0 live-retry: no test process left. Actual records baseline PASS 12:02:08 PM EST, model patch PASS 12:02:11 PM EST, breaking model patch FAIL 12:02:13 PM EST. Older-code evidence, not v0.2.1 proof.
- v0.2.1 doctor --ci exit 0 (5 tools, 2 hooks); validate --json exit 0, 15 checks OK, no warnings, no install-deps.
- 53 tests passed on installed Hermes Python 3.14.9 with ResourceWarning errors.
- Real PluginManager harness passed. Initial direct -I script failed missing ruamel; rerun through installed hermes_bootstrap passed without installation. Failed log retained.
- Reused ONLY prior isolated test HERMES_HOME <TEST_ROOT>/integration-20261107-1134/home; backed up isolated plugin/config. Replaced isolated plugin with v0.2.1, set isolated agent.run_budget_seconds=145. Default ~/.hermes config/backend untouched.
- ONE new model attempt: loopback Ollama gemma4-12b-64k:latest; --checkpoints --in disposable project; outer timeout 160s. Duration 54s, exit 1 due iteration limit (8). Actual persisted baseline PASS 12:22:35 PM EST; native model patch PASS 12:22:37 PM EST; breaking native model patch FAIL 12:22:39 PM EST. File and tool-call IDs inspected independently. Model reached status/blame but report did NOT run before limit. No retry.
- Operator independently ran status/blame/report against actual records. Blame correctly first observed FAIL #3, not proof of causation.
- Listed actual native checkpoints for exact disposable project; selected hash 9f9d6f3cf87c6e12bc7bd0bc74419fc3b9845516 (before breaking patch), NOT a LastGood sequence ID. Backed up sample then CheckpointManager.restore(..., safe=True) restored ONLY index.html; kept good slogan, returned phone number. Native API restore tested, interactive /rollback UI NOT tested.
- Status after restore STALE before recheck. Operator explicit fresh run_and_record at 12:23:27 PM EST returned PASS (#4); report generated with 4 steps. Model did not perform restore/recheck/report.
- Desktop evidence: <DESKTOP>\LastGood-v0.2.1-HOST-EVIDENCE-20261107 (doctor/validate/tests/harness incl failed log/live output/exit/checkpoint targets/native restore+recheck trace/records/report/old live-retry).
- LIMITS: interactive /rollback not tested, model-driven report/recovery not completed; exit 1 iteration cap. No full end-to-end model recovery claim. Old review ZIP kept unchanged for provenance; its README/START-HERE host status is now HISTORICAL/STALE; package refresh deferred.

## 2026-11-07 12:25 PM EST — validated review consolidation
No code changes or new model/restore runs. Current raw host evidence copied verbatim via sanctioned CopyToBox (archive SHA256 854231b6a42d91275dea10727ac768be2b1c18a5fb527e182c54e4fdb8ccb03f), included with original independent audit. Current docs distinguish operator native restore from model actions and untested interactive slash UI. Older review archives preserved.

## 2026-11-07 12:45 PM EST — interactive CLI milestone (incomplete)
- Source inspection: cli_commands_mixin.py::_handle_rollback_command lists current cwd checkpoints and supports /rollback diff N and /rollback N; restores through native command dispatch, safe by default, no separate confirmation in inspected handler. Gateway variant gateway_rollback.py dispatches rollback.list/diff/restore. No direct restore called this stage.
- Actual installed CLI launched in real terminal PTY via installed Python -I bootstrap run_module('hermes_cli.main') chat --provider custom --base-url http://127.0.0.1:11434/v1 --model gemma4-12b-64k:latest --checkpoints --in <TEST_ROOT>/interactive-v021-20261107-1239/project --max-turns 5. Same isolated test HERMES_HOME, no default config change.
- Interactive onboarding asked 'Help improve Hermes?' with default 'No thanks'. Queued slash input arrived while that menu owned the terminal. Transcript confirms Shared metrics off, then actual classic interactive Hermes welcome and prompt. Queued /lastgood check baseline, /rollback, /quit were NOT proven dispatched; likely consumed during onboarding. No model request was sent. No checkpoint restore attempted. Do not claim interactive rollback verified.
- Stopped ONLY exact dedicated CLI PID 2485 and driver PID 2484 after checking /proc command lines. Prior nohup launch did not persist. AwaitShell observer errored 'Deferred interaction response requested'; retained raw transcript is authoritative.
- Desktop evidence <DESKTOP>\LastGood-v0.2.1-INTERACTIVE-MILESTONE-20261107 includes driver, exact argv invocation.json, terminal.raw/readable, sent queue log, process metadata. Source code unchanged, prior VALIDATED-REVIEW archive not refreshed.
- Next stage: launch same PTY now that isolated onboarding is settled; wait for actual input prompt BEFORE sending one command at a time. First /lastgood check baseline must visibly succeed and plugin availability must be confirmed. Then at most two short model edit requests, wait for each actual completion, inspect checkpoint targets, /rollback listing and diff, exact native selection, explicit /lastgood check PASS. If lastgood missing in actual classic CLI, inspect supported loading path rather than modifying Hermes core or pretending handler harness is interactive.

## 2026-11-07 12:55 PM EST — real interactive run2 milestone
Actual PTY prompt synchronized before sending any input. Real /lastgood check baseline returned PASS at 12:50:08 PM EST. Separate model native patch good edit auto-PASS at 12:52:21 PM EST (call_q6db1ixp; completion footer 27.9s). Second short native model patch removed phone and auto-FAIL at 12:53:24 PM EST (call_t4mecdiy; completion footer 5.3s). No other model requests.
Observer predicate erroneously required a Hermes heading for second completion; transcript already showed completed footer and ready prompt, but observer waited 105s. PTY driver's 390s hard cap ended session. Do not treat this as model failure. No /rollback, blame/report or fresh recovery check sent this run. Source unchanged; exact interactive rollback gap still open. No restore attempted/default backend change.
Same disposable project <TEST_ROOT>/interactive-v021-20261107-1239/project remains broken deliberately. index.html SHA256 7e7dfc56a1a9dd82f5262b6882f0394f27a98203eb11e65ca6b3c4e0fb49dffb. Desktop evidence: <DESKTOP>\LastGood-v0.2.1-INTERACTIVE-MILESTONE-20261107\run2 (raw/readable transcript, invocation, driver, request log, actual records and sample state). Prior review archives unchanged.
Next stage requires NO more model calls: launch slash-only real interactive CLI same project/home, wait prompt, /lastgood blame then report, /rollback list, inspect exact checkpoint belonging to this project using diff, select native checkpoint, explicit /lastgood check. Use actual terminal completion footer+ready prompt, not heading predicate. Never equate LastGood IDs to checkpoint IDs.

## Current interactive workflow result — Nov 7, 2026, 12:58 PM EST

**The user-driven interactive recovery workflow passed on the disposable
sample, using unchanged LastGood v0.2.1.** Run2 used the real interactive
CLI for baseline PASS and two separate local-model native patch requests:
good edit PASS, breaking edit FAIL. Run3 used **no model calls**:
`/lastgood blame`, `/lastgood report`, `/rollback` listing,
`/rollback diff 1`, then actual `/rollback 1` selected inspected native
checkpoint **b2c02ee8…**, before the breaking patch. The real CLI reported
successful restoration and an automatic pre-rollback snapshot. Only
`index.html` changed: good slogan retained, phone number restored.
`/lastgood status` showed STALE, then explicit
`/lastgood check explicit fresh check after interactive rollback`
returned **tested step #4 PASS at 12:58:43 PM EST**. A fresh report was
written. `/quit` exited 0.

This is real terminal CLI dispatch, not a handler harness or direct
CheckpointManager.restore substitute. Native checkpoint IDs are NOT
LastGood tested-step numbers. There was no separate confirmation prompt:
the selected command performed the default safe restore. It proves this
**user-driven rollback + explicit verification** workflow for this sample,
not automatic/model-driven recovery or saved-state mapping. No plugin
code changed; prior 53-test/doctor/15-gate validate/harness passes remain
applicable to the same source.

Desktop raw evidence, command responses, records, actual HTML report and
before/after bytes:
`<DESKTOP>\LastGood-v0.2.1-INTERACTIVE-MILESTONE-20261107\run3`
(plus run2 for actual model edits). Current consolidated review archive
has not yet been refreshed. Nothing posted, pushed or submitted.


## 2026-11-07 1:02 PM EST — final interactive-tested review consolidation
No code changes/new models/restores. Run2+run3 raw evidence copied with sanctioned CopyToBox; SHA256 ef453c34aac69081d432653c6f1835e14601e698dad62dd7fdfe66d556e65512. Current docs rewritten to distinguish proven user-driven sample workflow from automatic recovery/mapping. Older documents and failed evidence retained. Dedicated process inspection returned no matches.

## 2026-11-07 — v0.3.0 change-evidence BOX ONLY development stage
Separate copy /workspace/lastgood-changeview/hermes-lastgood; original validated v0.2.1 source and Desktop untouched. Version 0.3.0 manifest/catalog. Design recorded before code in CHANGE_EVIDENCE_DESIGN.md. Deliberately restricted to configured-string presence deltas; NO raw file context/snippets and no opt-in context feature. Displays removed/added configured text, not full line diff. Redaction before persistence, known sensitive file exclusion, bounded labels, 200-record/1MiB index retention; first failure means retained history. Adjacent stable same-session/same-config observations only, no bridging UNKNOWN or overlapping reads.
Isolated standalone Python run: 66 tests PASS (original 53 + 13 focused new tests), ResourceWarning treated as error. Simulation PASS, visibly shows removed configured text index.html: 555-0100, historical blame and fresh check. Saved raw results and HTML under integration-evidence/v030-box-only.
v0.3.0 has NOT run Hermes doctor/validate/harness/live model/interactive commands. Every inherited host pass is historical v0.2.1 only. Independent audit pending. No Git, publishing, PC actions, installs, API calls or other bots.
Limits: not universal secret detection; configured text itself must not be secret. No actual source line captured. Bounded retention expires old history; ledger storage is not capped by the new index cap. Existing historical artifacts retained for provenance and their original statuses do not validate v0.3.0.

## v0.3.0 targeted independent audit corrections (box only)
# Targeted audit resolutions — v0.3.0 box-only
1. Sensitive lexical AND canonical target exclusions now live in resolve_in_project shared by reads and fingerprints. Exact .env symlink repro returns UNKNOWN/UNKNOWN with no delta and unchanged excluded fingerprint; ordinary safe symlink remains supported.
2. Any index timeout/OSError/ValueError poisons per-process/project/session continuity. Sticky epoch blocks every later delta until successfully saved label exactly baseline. Process restart generates a new epoch so no cross-process comparison. Bounded state (256 keys) disables excess-key deltas safely. No claim that missed writes can be globally recovered or universally detected across restarts.
3. Retention measures exact shared indent=2 ensure_ascii=False UTF-8 serializer; writer disables platform newline translation. Single oversized record rejected. Actual production on-disk size regression included.
4. Quoted JSON api_key/password/token and other recognized credential assignments redacted before persistence; no universal guarantee or erasure of user-owned project config. Design clarified that unrelated source assignments are not captured, not universally scanned.
74 unique tests PASS (66 preserved + 8 audit regressions), isolated ResourceWarning-as-error run. Simulation PASS. Original reviewer reproduction rerun against fixed source saved here. Initial duplicate test discovery caused an intermediate 87 count; final unique count is 74. No PC/host validation or transfer.

Pre-fix source backup /workspace/lastgood-changeview/before-audit-fixes; original v0.2.1 source remains untouched.

## 2026-11-07 1:47 PM EST — interrupted v0.3.0 host-stage recovery
Only box staging archive was built: /workspace/LastGood-v0.3.0-FEATURE-PREVIEW-HOST-STAGE-20261107.zip; SHA256 93b47f95fdac8cc5207501e88f2595937fc3be4ba29b38f2c350193aad245f99. Includes exact independently rechecked source and recheck evidence. No copy to PC was invoked. The initial PC folder/runtime inspection call was interrupted waiting for approval before results. Fresh read-only recovery confirmed Desktop Hermes Plugin/Feature Preview v0.3.0 does NOT exist, no v0.3.0 test folder, and no dedicated PTY/v0.3.0 test process candidates. No process stopped and no new model calls.
v0.3.0 host doctor NOT RUN; validate NOT RUN; 74 tests on Hermes Python NOT RUN; host harness NOT RUN; live/interactive model and rollback NOT RUN. Standalone 74 tests + simulation and independent recheck passed on box, not host. v0.2.1 Current Project untouched.
Next stage: create feature-only Desktop/test folder under native approval, sanctioned CopyFromBox archive transfer, new isolated WSL profile/project, inspect/bootstrap existing installed dependencies without wrapper or installation, then doctor/validate/74 tests/harness. Live workflow separately only after gates and time permit.

## 2026-11-07 1:52 PM EST — v0.3.0 host gates, unexpected provisioning side effect
Desktop staged archive SHA256 93b47f95fdac8cc5207501e88f2595937fc3be4ba29b38f2c350193aad245f99 extracted NEW Feature Preview v0.3.0; v0.2.1 Current Project not changed. Unique WSL <TEST_ROOT>/v030-host-20261107-1352, home/plugins/lastgood 0.3.0, minimal own config plugins.enabled=[lastgood]. Home installs symlink points to earlier disposable test home's installs.
ACTUAL GATES: doctor --ci exit0 (5 tools 2 hooks), validate --json exit0 (15 checks all OK, warnings=[]), all74 tests on installed Hermes Python3.14.9 PASS, real PluginManager harness exit0 required steps pass. No model/PTy/restore invoked.
IMPORTANT CONSTRAINT FAILURE: despite invoking installed interpreter/module directly with hermes_bootstrap and reusing existing isolated installs, doctor startup unexpectedly printed 'preparing dependencies for this data root' then 'Installing Python dependencies' / success. Thus no-install guarantee was NOT met. No install-deps flag or explicit installer was used. Do NOT hide this or describe stage as no installations. Exact raw output retained Desktop host-evidence/doctor.txt. Provisioning may have changed shared old isolated installs via symlink and shared caches; exact extent UNKNOWN. No default configuration or backend was intentionally changed; do not claim all filesystem effects isolated without audit. No further host commands were launched after seeing result.
Desktop evidence: <DESKTOP>\Hermes Plugin\Feature Preview v0.3.0\host-evidence (doctor/validate/tests/harness/tested-source-sha256). No live feature proof yet; harness edits are not model edits. Stop before live until safe existing-runtime invocation avoiding provisioning is established.

## 2026-11-07 1:57 PM EST — v0.3.0 freshness true; live startup blocked
Read-only installed pm.venv_is_current(project_root=Path('<USER_HOME>/.hermes/hermes-agent')) under SAME <TEST_ROOT>/v030-host-20261107-1352/home returned true, exit0, no bootstrap. Saved freshness-before-live.txt Desktop host-evidence. Normal supported existing venv interpreter + hermes_bootstrap/module launched in dedicated PTY with abort-on-provisioning detection. No provisioning text appeared in this launch.
Blocked before actual chat prompt by installed first-run guard: "no API keys or providers found. Run setup now? [Y/n]". Provider custom/base-url loopback/model arguments were present but minimal isolated config only had plugins.enabled. Answered n, actual CLI exit1, driver ended. No setup/config changes, baseline, model request or rollback. v0.3.0 live feature remains UNVERIFIED, host74tests/doctor/validate/harness passes still actual prior milestones.
Desktop evidence <DESKTOP>\Hermes Plugin\Feature Preview v0.3.0\host-evidence\live-startup-blocked contains raw/readable terminal, exact argv, driver and result; current v0.2.1 untouched. Next: approved normal local-Ollama configuration in isolated testhome (or documented normal launch argument accepted by first-run guard), no bypass flags; recheck freshness after config changes, then one model removal and real slash rollback/fresh check. No source changes or packaging performed.

## 2026-11-07 ~2:00 PM EST — v0.3.0 actual live feature PASS
Resolved normal local-provider startup by inspecting ONLY allowlisted nonsecret fields from our old disposable v0.2.1 config via installed YAML library (no bootstrap). Same v030 home received model.default gemma4-12b-64k:latest, provider custom, base_url http://127.0.0.1:11434/v1 and agent budget100/maxturns4; plugin enable retained, own previous config backed up. No key supplied, no default config access. Read-only pm.venv_is_current true before/after. Normal existing runtime bootstrap launched without provisioning output; telemetry default No thanks selected only in test home.
REAL interactive baseline /lastgood check baseline -> #1 PASS. ONE local-model native patch removed 555-0100, completed17.1s -> #2 FAIL. Same real session local-4b44fc89316492c9b08dc66d13c67a61a9813f3c85a1208109b7a97d631bd5e3 and continuity epoch across all records. /lastgood blame and actual report show observed #1 -> #2 removed configured text in index.html:555-0100, with non-causality caution. No missing/UNKNOWN/config gap.
ACTUAL /rollback listed native target f29d705; exact /rollback diff1 showed only phone removal in disposable index.html. After independently checking exact diff lines, actual /rollback1 restored checkpoint f29d7057; no direct internal restore call. Status STALE, explicit /lastgood check after interactive rollback -> #3 PASS. Persisted evidence #2 -> #3 added configured phone text; historical blame #1 -> #2 still removed/stale. Final report generated and bytes phone restored. /quit exit0; dedicated driver+CLI PIDs no longer exist. Live installed-plugin hashes match exact host-gate tested source.
All raw/readable transcript, command responses, before/after sample, original/final reports and JSON records are on Desktop Hermes Plugin/Feature Preview v0.3.0/host-evidence/live-feature-PASS. Freshness-local-config and tested source hashes saved there.
Earlier doctor-stage automatic dependency installation remains a real documented constraint failure; this live run showed NO provisioning output. Do not rewrite history to claim the overall host effort had no installation. No source changes, publishing, other bots, paid endpoint, default backend/config changes or v0.2.1 Current Project changes. This proves bounded user-driven rollback+explicit verification and configured-string delta workflow on the sample, not automatic recovery, full file diff, universal redaction or causal mapping. Packaging/docs consolidation and evidence copy back to box remain separate stage.

## Final tested v0.3.0 consolidation — no code changes
## Verified scope — v0.3.0, Nov 7, 2026

- **74 unique tests pass** in an isolated box copy and on installed Hermes
  Python 3.14.9. Includes 53 prior tests, 13 feature tests, 8 audit regressions.
- **Hermes v0.22.7:** doctor passes (5 tools, 2 hooks); validate passes
  all 15 gates with no warnings; real PluginManager harness passes.
- Independent audit found sensitive-symlink, lost-write continuity and
  serialized-size blockers. All were fixed, quoted-JSON credential
  redaction improved, and the independent targeted recheck **passed**.
- **Actual interactive feature test:** explicit baseline #1 PASS; ONE
  loopback Ollama `gemma4-12b-64k:latest` native patch removes the phone,
  completing in 17.1 seconds, giving #2 FAIL. Real `/lastgood blame` and
  report show **removed configured text in index.html: 555-0100**, IDs
  **#1 → #2**. All records share one real session and continuity epoch;
  there is no UNKNOWN/config/missing-record gap.
- Actual native `/rollback` list and `/rollback diff 1` were inspected for
  the dedicated disposable sample. Real `/rollback 1` restored checkpoint
  **f29d7057…** (NOT a LastGood record ID). Status became STALE. Explicit
  `/lastgood check after interactive rollback` gave **#3 PASS**, with
  **added** configured-text evidence **#2 → #3** in persisted records.
  Blame still preserves the historical removed-text evidence as stale.
  Final HTML report was regenerated. CLI exited 0; dedicated CLI/driver
  processes were confirmed absent.

This proves **configured-string presence evidence and the user-driven
native rollback + explicit fresh check workflow on the disposable sample**.
It does not prove edit causality, automatic/model-driven recovery, arbitrary
project recovery, full source diffs or a tested-state/checkpoint mapping.
The model edited; the user-driven real slash commands restored and checked.

## Important runtime side effect (not hidden)

During the initial v0.3.0 **doctor startup**, Hermes bootstrap automatically
provisioned Python dependencies despite direct interpreter invocation and
no `--install-deps`. Raw `doctor.txt` preserves the message. Runtime facts
and a new environment generation were observed in the earlier isolated
home's installs directory, shared through the new test home's symlink.
The full extent of shared-cache/filesystem effects was not established.
Do not claim "no installations overall".

Before the later live launch, the supported read-only PM freshness probe
returned true both before and after applying normal nonsecret local-Ollama
settings in the isolated home. That normal live launch showed **no
provisioning output**. No user default config was read/copied/changed; no
default backend changes or restarts were performed. No paid API/key was used.

Raw host/live evidence copied verbatim via sanctioned CopyToBox; archive SHA256 15be9ed10aa6abc8dfce28ce275bd0df47d2e38b07995595143e079b89d61e45. Older docs retained; all tested Python and manifest hashes unchanged.

## v0.4.0 health/doctor BOX ONLY initial stage
Separate /workspace/lastgood-heartbeat/hermes-lastgood copied from tested v0.3.0; old box source and Desktop untouched. HEALTH_DESIGN.md written before implementation. New memory-only health.py scoped process/project/session; independent registration evidence, actual callback invocation counters and safe tool name/time/post outcome, normal check attempts/completions/errors and separate SELF-TEST lane. No health files/prior-runtime counters. Dropped updates report UNKNOWN.
Status now avoids store metadata/directory creation and only reads; explicit config MISSING/INVALID/VALID, history corruption UNKNOWN, storage writability UNTESTED until doctor. Slash-only /lastgood doctor uses bounded normal local checker worker (remote URLs skipped), bounded tempfile storage probe and cleanup. No synthetic hooks, no diagnostic history entry or replacement of real failure; doctor does not certify host delivery. Five tools/two hooks unchanged; no new schema/tool.
90 tests PASS: all74 prior +16 focused health tests. Isolated ResourceWarning-as-error run. Standalone SIMULATION PASS, existing observed invariant/restore story retained; no real Hermes/model validation of v0.4.0. Evidence integration-evidence/v040-box-only.
Limits: callback observation proves only entry into callback functions, not authenticity/universal coverage. Missing session context explicitly UNSPECIFIED. Memory dropped-update uncertainty is runtime-wide conservative; per-scope data never merged. OS-hung diagnostic thread may outlive caller but does not append history; tempfile cleanup best effort. History corruption reports UNKNOWN; no persisted health-storage format exists. Bounded probes may create explicit-doctor store metadata and lock file. Independent audit and host tests remain pending. No PC/Git/posts/installs/model calls or other bots.

## v0.4.0 targeted audit corrections
# v0.4.0 targeted audit resolutions (box only)
1 MED fixed: storage worker computes a local provisional outcome, performs cleanup and unregisters probe, then publishes final value and sets done. Caller requires done within deadline; otherwise UNKNOWN with cleanup unconfirmed. Snapshot is copied, so late worker cleanup cannot turn returned UNKNOWN into PASS or mutate history. Added blocked-cleanup/late-error and completed-cleanup-error regressions.
2 MED fixed: concise slash/status and actual HTML distinguish check_error vs callback_error (safe type/time), show last_hook/tool and dropped-update uncertainty. Raw exception text/arguments never enter health; exception type label is sanitized/capped. Regression asserts actual slash/report output, not merely structured state.
94 unique tests PASS (90 preserved +4 audit regressions), isolated warnings-as-errors. Standalone simulation PASS. Original reviewer reproduction rerun against fixed source: incomplete storage UNKNOWN and returned state remains UNKNOWN after late failure; callback PermissionError visible while private payload absent.
Independent targeted recheck and v0.4.0 Hermes host gates remain pending. No PC actions/code outside separate v0.4.0 copy, new feature scope, other bots or publishing.

Pre-fix backup: /workspace/lastgood-heartbeat/before-audit-fixes.

## 2026-11-07 2:27 PM EST — v0.4.0 host-gates PASS (no live stage yet)
Exact independently rechecked source set 23cf5460d6c8e94c3b84a630e7e37e136bb81e1d5d4e96d98390b238fa68b1c2. Packaged /workspace/LastGood-v0.4.0-PREVIEW-HOST-STAGE-20261107.zip SHA256 083a0d23bfde33f3b2adeeac322bfdb9c2db0257fbb6c62692d73e9a7f54a933; sanctioned CopyFromBox to Desktop Hermes Plugin/Feature Preview v0.4.0 then extracted. Independent review/recheck and resolutions included.
Initial read-only freshness true on exact old v030 home/runtime. Preserved active v030 plugin by moving byte-for-byte to <TEST_ROOT>/v040-host-20261107-1425/backups/lastgood-v030-active-copy, selected exact v040 plugin normally in same isolated home's plugins/lastgood; plugins enable/local model config unchanged. Freshness after selection true. No new home or runtime symlink created.
ACTUAL: doctor --ci exit0 (manifest0.4.0, 5tools2hooks), validate --json exit0 (15checks allOK,warnings[]), 94tests PASS on existing Hermes Python3.14.9 (5.896s), real PluginManager harness exit0 all requiredsteps. All supported launches monitored for provisioning; NO provisioning output or installs observed in this stage. Earlier v030 doctor-stage install caveat remains historical and is not erased. Exact staged/active source+manifest hashes independently compared with recheck hashes and matched.
Desktop logs <DESKTOP>\Hermes Plugin\Feature Preview v0.4.0\host-evidence (doctor/validate/tests/harness/freshness/source hashes/gate-results/HOST-RESULTS). WSL test <TEST_ROOT>/v040-host-20261107-1425. Desktop testedv030 and v021 folders untouched. No models/PTy/rollback, publishing, defaultbackend/config changes, otherbots or source edits. Real live callback delivery/doctor/slash health validation pending separate stage; harness dispatches cannot prove live callback provenance. Preview docs predate hostgates; HOST-RESULTS gives actual newer state.

## 2026-11-07 ~2:38 PM EST — v0.4.0 real interactive health results (partial restart gate)
Freshness true, normal existing runtime, no provisioning output. Actual /lastgood status initial UNOBSERVED pre0/post0. Explicit /lastgood doctor SELF-TEST/checks/config/storage PASS with zero hooks and NO index history; separate diagnostic lane only. Explicit baseline #1 PASS. ONE actual local Ollama native patch removal completed ~27s -> #2 FAIL. Real hook counters pre1/post1, last_tool patch, succeeded1, timestamp2:36:46 PM EST, normal completed FAIL.
Doctor after genuine FAIL returned FAIL, history index bytes unchanged, hook counts unchanged. Actual status/report show CALLBACKS_OBSERVED and check/callback error distinctions; real blame/report preserve configured-string removed #1->#2 with non-causality caution. First CLI /quit exit0. Source unchanged; no second modelcall, backendchange, install or directrestore. Optional rollback/freshcheck NOT repeated; disposable project intentionally remains FAIL.
RESTART LIMITATION: a second real CLI resumed SAME SESSION. Actual status still showed pre1/post1 and prior completed FAIL/timestamps, not resetUNOBSERVED. Could be persistent plugin/runtime owner surviving terminal restart; NOT proved as a source defect or as expected reset. Follow-up doctor timed out and no new runtimeID was obtained; do NOT claim same runtimeID was confirmed. Plugin-process restart reset remains not host-proven (independent standalone process tests did pass). No sharedbackend restart/reset attempted. All exact dedicated CLI/driver PIDs absent at end.
Desktop raw/readable transcript, initial/doctor/model/status/report responses, actual HTML/history and model-after sample, restart timeout/observed status and sourcehashes under <DESKTOP>\Hermes Plugin\Feature Preview v0.4.0\host-evidence\real-health-RESULTS. Not a blanket PASS for restart. Box logs updated; no code edits or final consolidation.


# v0.4.0 read-only restart/timeout diagnosis — Nov 7 2026, ~2:43 PM EST

## Ownership confirmed; terminal restart is not plugin-runtime restart
Installed `hermes_cli/gateway_plugin_commands.py:217-228` sends plugin slash
commands via `connection.call_until("slash.exec", session_id=cli.session_id,...)`.
`gateway/session_commands.py:182-227` resolves/executes the plugin handler in the
owning profile; `gateway/run_inbound_hooks.py:281-299` supplies session_id under
session env scope. `hermes_cli/plugins.py:1629-1645` caches manager per home inside
that owning process. This is not a fresh local plugin instance per terminal.
The isolated test home's gateway_state.json explicitly identifies PID5810;
read-only ps confirms PID5810 is a still-running gateway process, started while
the first health client was active. It was not restarted or touched.

First CLI/driver PIDs5761/5760 exited. New CLI/driver PIDs6444/6443 resumed SAME
session local-7622363d592e101cf5a51971b6d27574532e7b6ab56a9816552a1615bafc66f8.
Its real /lastgood status returned pre1/post1 and original patch/check timestamp
2:36:46 PM EST. That matches persistent owner semantics, not restoration from a
health file (none exists). Initial actual doctor runtime UUID was
11c2f221dc4f47a580353e5e648c34d3. No second UUID was obtained: do not claim a direct
UUID equality comparison. Existing evidence plus installed routing confirms the
terminal restart did not establish that the plugin-owning process restarted.
No concrete LastGood memory-reset defect was demonstrated. Actual plugin-owner
restart/reset remains host-UNTESTED; independent standalone process-reset tests
passed. User-visible health can correctly survive terminal reconnect to the same
live owner/session. Counts are scoped to plugin runtime, not terminal lifetime.

## No observed plugin doctor timeout
Restart driver sent.jsonl contains ONLY /lastgood status, sent2:37:26 PM EST.
It did return valid status. The helper expected `Runtime callbacks: UNOBSERVED`,
so a valid CALLBACKS_OBSERVED response failed its matcher and generated a 15s
harness timeout at2:37:41 PM EST. This was a wrong test expectation, not a slow
status handler.
Follow-up /lastgood doctor and /quit exist only in queue.jsonl (mtime2:38:23 PM
EST), NOT sent.jsonl. The doctor timeout capture is zero bytes; no doctor was
proved delivered. Thus do not attribute its missing response to plugin budget,
cleanup or a Hermes handler timeout. The driver was no longer forwarding input.
Its configured cap245s had NOT elapsed: started2:37:23 PM EST, queue updated
~60s later. No normal driver-ended marker was produced. Its termination cause
was not recorded (parent-script exception/tool subprocess lifetime is possible,
not proven). The exact dedicated client/driver PIDs were absent at prior end.

## Preserved scope
All inspection read-only; no new CLI/model, backend restart/kill, config changes,
code changes or source-hash changes. Earlier raw logs and timeout files preserved.
Real initial UNOBSERVED + doctor no-hooks/no-history + actual model callback
counts + doctor preserving genuine FAIL/report remain proven independently of
this invalid terminal-restart expectation. Packaging should explain this
runtime ownership nuance, not promise reset on every CLI reconnect.

## Final v0.4.0 consolidation, no code/test/model/launch/reset changes
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

Raw host-health archive copied via sanctioned CopyToBox, SHA256 e5bcaa752c012c42bbed3ecedeb479a13f79bf3e21ce6460e8cea4e823e6fa9c.


## 2026-11-09 v0.4.1 box-only (Kenny pt56u)
Copied exact v0.4.0 source set 23cf5460... to /workspace/lastgood-guard/hermes-lastgood. Added project-root guard,
config guidance, schema format hints, rooted-path rejection, Windows-portable tests. 109 tests OK (0 skipped on POSIX),
symlink-unavailable simulation 4 skipped/0 failed, demo SIMULATION PASS. New source set b5924d7617b2d647b7c9cbe972774c70e4e0a4e63e52153a2bef01195bb788cb.
No PC/host/model actions. Evidence: integration-evidence/v041-box-only.

## 2026-11-09 v0.4.1 review follow-ups (box-only)
Fixed 4 independent-review gaps (OneDrive work/school, AppData//tmp/other users' folders, \\?\ prefixes, redacted echoed errors). 114 tests OK (ResourceWarning=error), simulation PASS, forced-no-symlink 4 skipped/0 failed, 7/7 mutations caught. Source set f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282. Evidence: integration-evidence/v041-review-fixes.

## 2026-11-09 v0.4.1 test-only Windows newline fix
51 write_text calls in tests now pass newline="". Plugin source set still f5454db8.... Box 114 OK.
