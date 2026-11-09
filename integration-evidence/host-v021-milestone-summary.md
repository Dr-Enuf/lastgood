
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
