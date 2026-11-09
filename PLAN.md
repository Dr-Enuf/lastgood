> **Update (Nov 7, 2026, v0.2.0):** the build status below is historical.
> Current state: BUILD_LOG.md and README.md. Live gate: PC_TEST_PLAN.md.

# LastGood — detailed plan

Deadline: Wed Nov 11, 2026, 5:00 PM EST. Submit Wed morning.
Today: Sat Nov 7. User does not code; ~90% AI-built. User tests on their
computer with real Hermes starting Sun Nov 8 (see TOMORROW_CHECKLIST.md).

## Judging criteria → where LastGood answers them
Source for criteria: Nous Research announcement (LinkedIn, Nov 6):
judges score usefulness, reliability, polish, creativity, and favour
plugins that do more than a prompt or a skill could.
- Usefulness: every Hermes user fears an agent breaking work / doing
  something un-undoable. Preset checks make it usable by non-coders.
- Reliability: stdlib-only, no keys, no network required except the
  URL preset; checks fail closed (errors read as BROKEN with a reason,
  never as a crash — see tests test_unknown_check_type_fails_closed,
  test_handlers_return_json_and_never_raise).
- Polish: Proof Report HTML, plain-English messages everywhere
  (no git/jargon in user-facing strings), README with honest "is NOT".
- Creativity: first-observed-failure blame over tested agent states +
  an observed can't-undo ledger for real-world actions, packaged for
  non-coders. (Updated Nov 7 per Grok/Gemini merged plan: no bisect
  claims — blame reads recorded labels.)
- More than a prompt: real tools, pre/post tool-call hooks, slash
  commands, durable state on disk.

## Differentiation (verified by research Nov 7 — sources in chat)
- Hermes built-in checkpoints/`/rollback`: snapshots + restore, NO
  pass/fail labelling, NO blame search, NO side-effects account.
- memory-rewind plugin (marketplace): version history for Hermes' own
  memory/skills files only.
- Claude Code `/rewind`, Cursor checkpoints, mrq: undo for coding
  tools; none label last-known-good or search for the breaking step.
- git bisect: searches git commits by re-testing them; expert tool,
  code only. LastGood deliberately does NOT re-test restored states
  (not reproducible; replaying actions can repeat side effects) — it
  reads its own recorded results instead.
- Damocles: read-only observability timeline; no checks, no blame.
- VOID / agent-saga: developer libraries classifying reversible vs
  irreversible agent actions; not Hermes plugins, not non-coder facing,
  no last-known-good/blame.
- Chronos (catalog PR #149151, found Nov 7): snapshots + rollback +
  Desktop timeline, validated 16/16 with real acceptance runs. It does
  NOT attach check evidence to states or track can't-undo actions —
  that is LastGood's differentiation.
Claim for the pitch: the combination (check evidence on tested states +
first-observed-failure + observed can't-undo ledger, Hermes-native,
non-coder presets) was not found elsewhere.
Do NOT claim we invented undo, checkpoints, or bisect.

## Build status
DONE (Nov 7): spec, plugin v0.1, end-to-end demo script PASS, sample
project, README, review packet, this plan. Merged-plan revision (Nov 7,
after Grok + Gemini reviews): test-command preset REMOVED, bisect
helper REMOVED, blame/ledger wording made honest, 15 passing tests.
SPIKE RESOLVED from docs (Nov 7): the public plugin API exposes no
checkpoint interface, and checkpoints are pre-change/one-per-turn/
opt-in — so LastGood's own labelled step records ARE the design, and
the remaining unknown is the live INTEGRATION GATE (Sun Nov 8, see
TOMORROW_CHECKLIST.md): prove the loop in real Hermes, run
`hermes plugins doctor` + `hermes plugins validate --install-deps`,
confirm live hook argument shapes and the /rollback target mapping.
If checkpoint linkage proves unreliable, state the limitation plainly —
do NOT build a second snapshot engine.
BUILD ITEM for Sun/Mon (from merged plan): mark pre-restore results
STALE in status/report after a rollback is observed, and always re-run
checks after a restore before calling a state good again.

## Risks and mitigations
1. Hook signatures differ in real Hermes → handlers accept *flexible
   args/**kwargs per guide examples; verify in doctor/live run Sun.
2. Checkpoint list not exposed (now CONFIRMED via public API list) →
   own step records are the design; restore stays a manual /rollback
   guided by label/time. Limitation stated, not hidden.
3. URL preset flakiness → retry once, 5s timeout, failure says why.
4. Non-monotonic breakage (broke, fixed, broke) → blame reports the
   FIRST observed break and says so in the README.
5. Can't-undo classifier false positives/negatives → records and
   warns only, never blocks; entries marked attempted vs observed;
   patterns are conservative and unit-tested.
6. Scope creep → feature freeze Mon Nov 9 (per timeline in SPEC.md).

## Demo (75s) — full script in DEMO_SCRIPT.md
Setup presets (20s) → good change green → breaking change red →
/blame shows the step after which checks first failed → /lastgood +
/rollback returns to the last proven-good state, checks re-run green
on camera → Proof Report + can't-undo line.

## Submission pack (drafts in SUBMISSION.md)
- GitHub repo with plugin/ as the plugin root content, README, tests
- PR to Hermes plugin catalog: one plugin-catalog/<name>.yaml pinning
  the repo commit (exact format to confirm from catalog README at spike)
- X post with demo video tagging @NousResearch
- Hackathon form with both links
