# v0.3.0 design — configured-string presence deltas only

Deliberately NO raw-context opt-in in this first version: no file lines, snippets,
full diffs or snapshots are captured. The only displayed removed/added text is a
bounded, sanitized configured invariant, not the actual source line. Thus the
sample can show `removed configured text: 555-0100`, not a fabricated contact-line
diff. This is a privacy/expressiveness tradeoff; context storage is not supported.

For each local text_present check, during its existing bounded read record
schema=1, check index, sanitized path/text label and present=true/false. Only a
complete valid UTF-8 non-binary read is eligible. Known sensitive lexical AND resolved filenames, private-key markers in
file data, or recognizable credentials in the configured invariant suppress
evidence. Unrelated credential assignments in file data are not captured
(no raw context is stored), rather than universally scanned or erased. No additional file is read.

At locked persistence compare ONLY adjacent checked observations, same config
hash, same session (or both standalone), stable PASS/FAIL overall, nonoverlapping
observation intervals. No bridging UNKNOWN, skipped, missing, config mismatch or
legacy records. Baseline has no delta. Both record IDs are shown, along with
historical freshness and an explicit unobserved-edits/cause disclaimer. A missing
file is not proof its configured text was removed, so evidence unavailable.

Redact recognizable credential assignments/tokens/private-key markers before
persistence, not just rendering. This is NOT universal redaction: never configure
secrets as invariants/labels. Paths/text are bounded in UTF-8 bytes. HTML escaped.
Max five observations/deltas per record, 200 records / 1 MiB retained JSON index;
older records expire and blame means first failure in retained history. No restore
mapping, snapshot engine, dependency or host validation claim.

## Audit corrections (same v0.3.0, before host gate)
- Canonical-target sensitive check is shared by fingerprint/read containment.
- A per-process/project/session epoch prevents comparison across restart or
  storage failures. A lost index write sets a sticky in-memory blocked state.
  Future deltas remain disabled until a successful explicit
  `/lastgood check baseline` in that same session (label exactly baseline).
  Baseline itself has no delta. Failed baseline writes cannot clear the state;
  concurrent newer loss cannot be cleared by an older baseline. Epochs are
  random per process; first observation after restart does not compare with
  a prior process. This is NOT proof that no write failed across restarts.
  State map is capped at 256 keys; excess keys disable deltas fail-closed.
- Retention and atomic_write_json use one indent=2 UTF-8 serializer. Text
  writing disables newline translation; cap measures actual emitted bytes.
  A single oversize record is rejected rather than written over the cap.
- Quoted JSON credential keys are recognized before persistence. The user's
  own project config necessarily still contains their configured input; do
  not configure secrets. No universal scanner or source-file erasure claim.
