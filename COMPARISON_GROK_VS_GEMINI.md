# Grok vs Gemini — comparison and merged plan (2026-11-07)

Both reviews were given the same share message. Grok's claims were
verified against Hermes' docs/PRs on 2026-11-07 (see
GROK_REVIEW_TRIAGE.md). Gemini's review cites no sources; where it
conflicts with verified facts, the verified facts win.

## Where they agree (high confidence — both said it independently)

1. **Ship, don't pivot.** 4 days out, pivoting = starting from zero.
2. **Don't pitch it as an undo button.** The winning frame is
   verification + diagnosis: knowing why you need to go back, and
   where it broke. (Gemini's phrase: fights "silent agent drift.")
3. **Biggest risk = integration illusion.** A plugin that passes
   standalone tests can still shatter on live Hermes hooks/state.
   Get it running inside real Hermes ASAP; harden the core loop
   (check → green/red → blame) before anything else.
4. **The test-command preset is a security concern.** Grok: explicit
   config + disclosure; it runs real code with user permissions.
   Gemini: catalog security review may flag `subprocess` outright —
   stick to safe deterministic checks. (Catalog reviewers demonstrably
   scrutinise safety: the Chronos PR got approval-gating demands and
   rule-13 disclosures from a maintainer.)

## Where they clash — and Muse's ruling

### Clash 1: /blame binary search
- Gemini praises "automatic binary search (/blame over agent steps)"
  as a winning feature.
- Grok: cut retrospective bisection; keep "first observed failure."
- **Ruling: Grok.** Gemini is praising the pitch version. The shipped
  `/blame` already does first-failure lookup over recorded labels;
  re-testing restored states is unsound (states aren't reproducible,
  external effects can't be replayed safely). Cut bisect from the
  pitch/spec/demo wording.

### Clash 2: the can't-undo ledger
- Gemini: CUT or heavily descope — will be "fake or fragile."
- Grok: keep, but rename honestly ("observed actions not reverted by
  file rollback") and split attempted / confirmed / uncertain.
- **Ruling: split, leaning Grok.** The ledger is already built, costs
  little to keep, and is half of the differentiation Grok identified
  ("what restoring it won't undo"). But Gemini's "fake" warning is
  partly fair: it's pattern-matching on tool calls, not verified
  external effects. Grok's honest wording + attempted/confirmed split
  fixes exactly that. Keep it, descoped and renamed — do not expand it.

### Clash 3: fallback snapshot engine
- Gemini: ADD our own lightweight snapshotting so the demo always
  works even if Hermes' checkpoint store is unreadable.
- Grok: do NOT build a second snapshot engine; if checkpoint identity
  can't be made reliable, drop automatic-recovery claims and state
  the limitation.
- **Ruling: Grok.** A snapshot engine duplicates Chronos (a validated
  competitor), burns the remaining days, and adds the exact fragility
  both reviewers warn about. Gemini's underlying fear (demo dies) is
  handled differently: the demo runs with checkpoints explicitly
  enabled (`hermes chat --checkpoints`), tomorrow's integration gate
  tests the restore path early, and if linkage fails we present the
  limitation honestly instead of faking recovery.

## What Gemini missed / got wrong

- Didn't know (or check) that Hermes checkpoints are pre-change
  snapshots, max one per directory per turn — the fact that breaks
  naive checkpoint labelling. Grok found it; it's verified.
- No mention of Chronos, git-autosave, or Afterforge (real catalog
  competition). His "unique enough to win" is asserted, not checked.
- "Top 3 contention, legitimate shot at 1st" is encouragement, not
  evidence. Grok's "weak first-place case today, could be competitive
  if narrowed and proven" matches the verified state: nothing has run
  inside real Hermes yet.

## What Gemini added that Grok didn't

- The catalog-security framing on the test-command preset (stronger
  than Grok's version) → merged plan drops the command preset from
  the v1 submission scope; presets 1–4 (page loads, file opens,
  words present, nothing disappeared) are the non-coder story anyway.
  Re-add post-hackathon behind explicit opt-in + disclosure if wanted.
- Pitch language worth stealing: "agent safety and governance
  harness"; "silent agent drift" as the named enemy.
- Sequencing discipline: stop adding features, harden the loop,
  Tuesday = demo, Wednesday morning = submit. Matches our timeline.

## Merged plan (pending user go-ahead)

Everything in GROK_REVIEW_TRIAGE.md, plus:
- [x] Drop the "run my test command" preset from v1 submission scope
      (security-review friction; coders aren't the pitch audience).
- [x] Pitch adopts Gemini's framing words with Grok's honest claim:
      "Know which checks passed on which saved state — and what
      restoring it won't undo." Enemy: silent agent drift.
- [x] No fallback snapshot engine. Demo insurance = checkpoints flag
      on, tomorrow's gate, honest limitation if linkage fails.
