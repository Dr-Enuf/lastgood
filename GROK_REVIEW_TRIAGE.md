# Grok review triage — 2026-11-07

Grok's verdict: ship a smaller LastGood, don't pivot; not a first-place
contender today because reliability claims are ahead of the evidence.
Muse checked each load-bearing claim against the official Hermes
docs, the public plugin API list, and the competitor PRs on
2026-11-07. Verdicts below.

## AGREE — verified true, changes our plan

1. **Checkpoints are NOT one per agent step.** Official docs: a
   checkpoint is a snapshot taken BEFORE file tools (`write_file`,
   `patch`) and destructive terminal commands; "at most one checkpoint
   per directory per turn"; no-change snapshots are skipped;
   checkpointing is opt-in (default off).
   → Consequence: a check that passes on the post-edit state cannot be
   attached as "green" to the pre-edit checkpoint. Multiple edits in
   one turn can share a single checkpoint, so "the exact step" may not
   be independently recoverable. Our SPEC wording ("labels each save
   point", "/lastgood returns to the last green one") overpromises and
   must change: LastGood labels TESTED STATES (its own step records);
   it identifies the restore target, Hermes' `/rollback` does the
   restoring, and the mapping must be proven tomorrow or stated as a
   limitation.
   Source: hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback

2. **No supported checkpoint interface for plugins.** The public plugin
   API list (the same list `hermes plugins validate` checks against)
   contains no checkpoint module or checkpoint-created event.
   → Importing internals is not stable integration. Tomorrow's test
   must pin the actual Hermes version and treat checkpoint linkage as
   a hard gate, not an assumption.
   Source: hermes-agent.nousresearch.com/docs/developer-guide/plugins/public-api

3. **Chronos is a real, strong competitor.** PR #149151
   (NousResearch/hermes-agent): pre-change snapshots into a shadow git
   repo, rollback path, Desktop timeline, `/chronos` command; validated
   16/16, doctor OK, 29/29 tests, real acceptance runs, maintainer
   review completed. Overlap is real (snapshots/timeline/rollback);
   Chronos does NOT do checks-per-state evidence or a can't-undo
   ledger — that remains our differentiation.
   Also real: git-autosave (pre-edit state preservation) and
   Afterforge (failures/corrections → evidence-backed regression
   checks), both in the catalog.

4. **Hooks have a hard time budget.** A Hermes maintainer's review of
   Chronos confirms core gives `pre_tool_call` a 30s budget and told
   them to move heavy git work out of the hook path.
   → Our checks must stay fast and must never certify a newer state
   with an older result (see STALE below).

5. **Integration gate before more features.** Grok's 5-step proof
   (baseline passes → real edit passes → real edit fails → report
   names the tested states AND the actual recoverable checkpoint →
   user-approved restore + fresh checks pass) becomes tomorrow's test
   plan, plus: multiple edits in one turn, a check timeout, and a
   manual user edit.

## AGREE — wording/honesty fixes

6. **Blame wording:** "The check first failed after this change" —
   never "this action definitely caused the bug."
7. **Ledger renamed in wording:** "observed actions not reverted by
   file rollback"; distinguish attempted vs confirmed vs uncertain
   (a pre_tool_call hook sees attempts that may be blocked or fail).
8. **Check results need PASS / FAIL / UNKNOWN / STALE.** After a
   restore, old results are stale — re-run checks instead of trusting
   the old green.
9. **Test-command preset executes real code** with user permissions:
   keep it explicit-config only and disclose that in setup/README.
   Passing doctor/validate proves loading, not safety.

## ALREADY TRUE in our build (Grok couldn't see this from the pitch)

10. **Shipped `/blame` does NOT do retrospective bisection.** It reads
    recorded pass/fail labels and returns the first red after a green
    (`core.CheckpointIndex.first_bad`). `bisect_first_bad` exists only
    as a tested pure helper on the non-shipping path. Grok's "single
    best change" is mostly a SPEC/pitch/demo-wording cut for us, not
    an engineering rebuild — remove the bisect claim from SPEC/demo,
    and drop or quarantine the helper so nobody wires it up later.
11. **Report content is already escaped** (`html.escape` on labels,
    details, ledger fields in `core.generate_report`).
12. **UNKNOWN already exists** as `passed=None` → "NOT CHECKED" in the
    report. STALE is the missing state (item 8).

## Where Muse pushes back (mildly)

- "Not a first-place contender today" is fair — nothing has run inside
  real Hermes yet, which we've said from the start. It is not evidence
  the finished entry can't compete; it means tomorrow's gate decides.
- Originality "moderate" is fair for snapshots/timeline (Chronos), but
  no competitor found attaches check evidence to states or tracks what
  rollback won't undo. Grok's own closing pitch is our pitch, tightened:
  "Know which checks passed on which saved state — and what restoring
  it won't undo."

## Actions (pending user go-ahead on the scope cuts)

- [x] SPEC.md + DEMO_SCRIPT.md + SUBMISSION.md: cut bisect/"exact
      step" claims; new blame + ledger wording; new pitch line above.
- [x] Add PASS/FAIL/UNKNOWN/STALE semantics + post-restore re-check to
      the plan for tomorrow's build session.
- [x] Tomorrow's computer test = Grok's 5-step gate + multi-edit turn
      + timeout + manual edit (add to TOMORROW_CHECKLIST.md).
- [x] If checkpoint identity can't be made reliable promptly tomorrow:
      drop automatic-recovery claims, state the limitation plainly.
      Do NOT build a second snapshot engine (Chronos already is one).
