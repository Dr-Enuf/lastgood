# Targeted independent v0.3.0 recheck

November 7, 2026, 1:37 PM EST. Reviewed fixed separate `/workspace/lastgood-changeview/hermes-lastgood` against a fresh snapshot at `/tmp/lastgood-v3-recheck-rkj44glg/source`.

## Verdict: PASS — targeted standalone safety gate

All three prior blockers are fixed in the tested artifact. **74 unique tests passed**, and the standalone simulation passed. I reran the original independent reproduction probes against this snapshot, not just the builder's new tests. No new concrete high-severity issue found in this targeted recheck. Proceed to separate isolated Hermes host validation; this is not a host/recovery validation or release guarantee.

No source/PC changes, Git operations, posting, publishing or external network requests. Execution used isolated HOME/HERMES_HOME and only local HTTP tests. Prior v0.2.1 was not touched. Working plugin hashes still matched the tested snapshot when this recheck ended.

## Blocker results

| Prior finding | Result | Independent observed outcome |
|---|---|---|
| Sensitive `.env` reachable through `index.html` symlink | **PASS / fixed** | Same original probe now returns UNKNOWN then UNKNOWN, with no delta. Canonical and configured sensitive names are rejected through the shared path resolver (`checks.py:155-163`), which fingerprinting also uses. Ordinary in-project symlinks remain supported by the passing regression. |
| Nonpersisted storage-timeout UNKNOWN bridged by next delta | **PASS / fixed** | Original locked-index probe still returns UNKNOWN with id=None; the next FAIL now has **no changes**. Additional regressions verify subsequent results stay blocked until a successfully saved explicit baseline, and generic write errors also poison continuity. `tools.py:208-237`, `changeview.py:118-143`. |
| 1 MiB cap measured against the wrong serializer | **PASS / fixed** | Original real-record fixture now retains 108 records and writes **1,040,791 bytes**, below 1,048,576. Retention and disk writes share `serialize_json`; single oversize record is rejected. `changeview.py:105-115`, `core.py:107-108`. |
| Optional quoted-JSON credential redaction | **PASS / fixed for tested forms** | Original `"api_key": "SYNTHETIC_SECRET_123456"` probe now has observation=None and marker absent from history. Added regressions cover quoted api_key/password/token and actual HTML. This remains pattern-based, not universal secret removal. |

## Continuity / process follow-up

I launched **two actual separate Python processes** against one disposable project/store with the same explicit session ID. Process 1 saved PASS; the file changed before process 2 saved FAIL. Epochs differed, process 2 emitted **no delta**, and its note said `Process/storage epoch changed; no comparison across uncertain continuity.` This is stronger than the suite's mocked `_STATES` reset alone.

The implementation's baseline semantics are conservative and clearly disclosed: a failed write blocks future deltas within the current process/project/session until the `baseline`-labelled PASS/FAIL record is successfully saved. A changed epoch prevents the first post-restart result from comparing with pre-restart results; it does not prove no earlier persistence failure happened. The documentation explicitly acknowledges that limit. An older baseline cannot clear a newer loss because `accept_baseline()` checks the epoch. Excess state-map keys fail closed.

## Claims and limitations checked

The design now correctly distinguishes credential markers in configured invariant text from unrelated credential assignments elsewhere in the file. No raw context/snippets/full diff is captured. Docs still describe configured-string membership, not causal attribution or recoverable checkpoints, and identify v0.3.0 as not host-validated. Prior v0.2.1 evidence remains historical. No new universal-redaction claim found.

The original non-sandbox caveats (malicious concurrent filesystem mutation, OS-blocked read threads, wall-clock interval assumptions) are not expanded or newly certified by this targeted recheck. Nothing here promises first place, complete action detection, or automatic rollback mapping.

## Exact tested plugin SHA-256 set

- `plugin/lastgood/__init__.py`
  `4389bcfb686fe7f06b86f621631f7fa1254fef93f9f79de244f56fd3462153f1`
- `plugin/lastgood/changeview.py`
  `4a9b9b44e782389bf8395cf5f3d52506dd982e0bc87765f3cbda2340663a1bb2`
- `plugin/lastgood/checks.py`
  `58d309f0505dad8b4ccdeaf1dda8a358df1c2214048a00bfa5a537bdfb0228bc`
- `plugin/lastgood/core.py`
  `afc38510e07fe5d6ae5f41c4dd2e8470e39b41211e4adaf0d6b76728002c1097`
- `plugin/lastgood/plugin.yaml`
  `329e6e4f08b2186b8c450450ed8e7f070f8dc898d3962615a4cb7b3e920d5b95`
- `plugin/lastgood/schemas.py`
  `b7e17b79fb736c313e56f7f0abacbc2fb1a16f4b55c277cfcead8b6ec444b223`
- `plugin/lastgood/tools.py`
  `076bba68a0f7e276124e95a19080a73fd10bf4eb6012c4549f0f3409889d819d`

## Saved evidence

`/workspace/lastgood-changeview-independent-recheck-evidence/` contains `tests.txt`, `demo.txt`, original adapted `reproduce.py` and its results, `process_probe.py` and actual process-boundary output, and `hashes.json`.

No remediation was performed by the reviewer. **Next step: independently version-matched Hermes doctor/validate, real hook dispatch and interactive command checks for this exact hash set.**
