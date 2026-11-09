> **SUPERSEDED (Nov 7, 2026, v0.2.0).** This packet describes v0.1 and
> is out of date. Corrections: v0.1 had 15 tests, not 16. There were 4
> check presets, not 5, and the bisect helper had already been removed.
> v0.2.0 rewrote the plugin (see BUILD_LOG.md, README.md, PC_TEST_PLAN.md).
> Kept only as history.

# Review packet — for Grok / Cursor / any second agent

The user will show you this file (and the repo) to double-check the
work. Please review it adversarially: the goal is to catch mistakes
before hackathon judges do. Everything below is written so you can
verify each claim yourself from the files + public Hermes docs.

## What this is
LastGood, a plugin for Nous Research's Hermes Agent, built for the
Hermes Agent Plugin Hackathon (announced Nov 6, 2026; submissions due
Nov 11, 2026, 5:00 PM EST; $20k prizes; judges score usefulness,
reliability, polish, creativity, favouring plugins that do more than a
prompt/skill). The author does not code; Muse built this (~90% target).

## Claims to verify (and how)
1. "Hermes already has checkpoints//rollback, so plain undo is a
   duplicate." Verify: Hermes docs "Checkpoints and /rollback"
   (hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback).
2. "The plugin follows the official plugin shape." Verify against
   https://hermes-agent.nousresearch.com/docs/developer-guide/plugins —
   manifest fields (name/version/description/provides_tools/
   provides_hooks), handlers (args: dict, **kwargs) -> JSON string and
   never raise, register(ctx) wiring tools/hooks/commands, state via
   plugin data dir. Check plugin/lastgood/{plugin.yaml,__init__.py,
   schemas.py,tools.py} line up: every tool/hook in plugin.yaml is
   registered, and vice versa (there is a unit test for this too).
3. "16 tests pass with no Hermes install." Run:
   `python3 -m unittest discover -s tests -v` from this folder.
   Expected at time of writing: Ran 16 tests — OK.
4. "The demo story works." Run: `python3 scripts/demo_end_to_end.py`
   Expected: step 1 GOOD, step 2 BROKEN, blame names step 2,
   "DEMO RESULT: PASS", and demo-output/report.html written.
5. "Stdlib only / no keys." Grep imports across plugin/: only stdlib
   plus intra-package imports should appear.

## Known limitations — please confirm these are honestly stated
- NOT yet run inside real Hermes. Hook argument shapes, command
  registration, and data-dir location follow the published guide but
  are UNVERIFIED live. First real-Hermes session is scheduled Nov 8.
  `hermes plugins doctor` / `validate` results do not exist yet.
- LastGood keeps its own labelled-checkpoint index; it does not yet
  read Hermes' built-in checkpoint store. Whether a plugin can read
  that store is an open spike (see SPEC.md). /lastgood currently tells
  the user which labelled checkpoint was last green; the actual restore
  is done by the user with Hermes' /rollback.
- The bisect helper (core.bisect_first_bad) is implemented and tested
  as a pure function; the shipped /blame currently reads recorded
  pass/fail labels (first red after green) rather than re-testing
  restored checkpoints — re-testing needs the spike above.
- Can't-undo detection is regex-based and conservative; v0.1 records
  and warns only, never blocks. Expect both false positives and misses.
- URL preset follows the spec (retry once, 5s default) but is the only
  network-dependent check; everything else is local.

## Files map
- SPEC.md — one-page spec incl. timeline and the spike/fallback
- PLAN.md — criteria mapping, differentiation research, risks
- plugin/lastgood/ — plugin.yaml, __init__.py (register), schemas.py,
  tools.py (handlers + state), checks.py (5 preset checks), core.py
  (index, bisect, classify, report)
- tests/test_lastgood.py — 16 unittest tests (stdlib unittest)
- sample-project/ — deliberately breakable demo site + its check config
- scripts/demo_end_to_end.py — headless demo/smoke test
- DEMO_SCRIPT.md, SUBMISSION.md, TOMORROW_CHECKLIST.md

## Questions a reviewer can usefully answer
1. Does the plugin.yaml match the current Hermes manifest spec (incl.
   any v2 fields judges/validators may expect)?
2. Are hook signatures (pre_tool_call/post_tool_call) right, and should
   pre_tool_call return something to warn inside Hermes' UI rather
   than only logging?
3. Is there a supported way for a plugin to list built-in checkpoints
   (the spike)? Point at docs/code if yes.
4. Any security smell: the `command` preset runs a user-configured
   shell command (by design — it is the user's own test command, like
   CI). Is that acceptable for catalog review, and should the manifest
   declare a capability for it?
5. Would `hermes plugins validate` complain about anything visible
   statically (tool names vs schemas, provides_* lists, layout depth)?

Please report findings as: BLOCKER / SHOULD-FIX / NICE-TO-HAVE, each
with file:line. Do not rewrite the plugin silently; the build log in
BUILD_LOG.md should stay an accurate record.
