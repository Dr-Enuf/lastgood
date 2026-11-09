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

