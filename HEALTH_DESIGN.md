# v0.4.0 runtime health / explicit doctor

Memory only, no health files: random process epoch, canonical project path and
session_id (conversation_id fallback; absent explicitly UNSPECIFIED) key a bounded
256-scope map. Separate pre/post callback counts; last callback UTC time and safe
tool name; post succeeded/failed/blocked/uncertain counts; callback errors by type
only. Registration completion is separate runtime evidence, never delivery proof.
After import/restart activity is UNOBSERVED until callbacks actually enter these
functions. Test-dispatched callbacks prove invocation only, not host provenance,
universal coverage or unforgeability. No args/results/messages are retained.

Normal checker attempts/completions/errors and SELF-TEST diagnostic attempts are
separate lanes. Last completed normal check is not overwritten by a diagnostic.
UNKNOWN/timeouts remain unknown, not green. Memory lock acquisition <=0.1s;
capacity/lock failure reports UNKNOWN rather than resurrecting prior runtime data.

/lastgood status reads setup/history/health without creating directories, metadata
or probe files. Explicit missing config is MISSING even if legacy defaults exist;
malformed config INVALID. Corrupt history reports UNKNOWN health/history detail.

/lastgood doctor is slash-only: no new tool or hooks. It runs the normal bounded
checker worker in SELF-TEST mode, local configured checks only (URL checks UNKNOWN
and deliberately not fetched), no history record, no synthetic hook dispatch.
Separate config, storage, check result and hook activity, never 'awake/connected'
from doctor. Storage only on explicit doctor: bounded daemon worker, bounded core
lock, tempfile write/read/cleanup inside project store, no config/real-file edits.
An OS-hung worker can outlive caller; it never writes history and cleanup is best
 effort. Nonmutating status cannot certify writability. Diagnostic overall PASS
means local self-test/config/storage pass, NEVER project recovery or hook delivery.

### Targeted diagnostic truthfulness corrections
Storage PASS is published only after write/read, cleanup and worker bookkeeping
finish within deadline; incomplete/late cleanup returns UNKNOWN, never provisional
PASS. The bounded caller's result is an independent snapshot; late cleanup cannot
rewrite it or history. Status/report distinguish check_error from callback_error
(safe type/time only), show last callback/tool and dropped-collection uncertainty.
