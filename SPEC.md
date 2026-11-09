# LastGood for Hermes — one-page spec

Hackathon: Hermes Agent Plugin Hackathon (Nous Research)
Deadline: Wednesday, Nov 11, 2026 at 5:00 PM EST — target submission Wed morning
Builder note: User does not code. Build ~90% with AI (Muse / Cursor / Grok).
User's part: install Hermes on their computer, install/enable the plugin,
run guided tests, record the demo, submit PR + X post + form under their accounts.

## Pitch in one sentence
Know which checks passed on which tested state — and what restoring
files won't undo. (The enemy: silent agent drift — an agent quietly ruining
work over many steps while every checkpoint looks the same.)

Hermes already has built-in checkpoints / `/rollback`. LastGood does NOT
rebuild that. It builds on top of it. IMPORTANT (verified Nov 7, 2026):
Hermes checkpoints are pre-change snapshots, at most ONE per directory
per turn, and opt-in — so LastGood labels TESTED STATES (its own step
records), never the checkpoints themselves. A green label means "the
checks passed on the files as they were at that moment," nothing more.

## What it does (v0.2.1, Nov 7, 2026)
1. Checks the user picked are kept in `<project>/lastgood-config.json`
   (`/lastgood setup ...` or the `lastgood_setup` tool). After a successful
   `write_file`/`patch` in a project with that file, the `post_tool_call`
   hook runs them, capped at 10 s. Each run records a tested step:
   PASS / FAIL / UNKNOWN, a SHA-256 fingerprint of the checked files, a
   setup hash, and the session/turn/tool-call ids.
2. Status marks each tested step current or stale by comparing
   fingerprints. After a `/rollback`, steps whose bytes no longer match
   are stale, and the next check is a new record. LastGood step numbers
   are never presented as Hermes checkpoint numbers.
3. `/lastgood blame` gives the first observed FAIL after a PASS, read
   from recorded results. Nothing is re-tested and causation is not
   claimed.
4. The ledger records recognised send/post/push/pay/remote-delete tool
   calls. Entries are attempted in `pre_tool_call` and settled in
   `post_tool_call` by tool_call_id as succeeded/failed/blocked/uncertain.
   Raw arguments are never stored. The ledger lives outside the project.
5. A one-file HTML Proof Report.

## Preset checks (deterministic, no command execution)
file_opens, text_present, files_exist, url_loads (http/https, timeout
capped at 5 s, optional words-on-page). Up to 5 checks. Paths are
contained to the project. Unreachable or out-of-time is UNKNOWN; malformed
setup is UNKNOWN and makes earlier results stale. Default when no config
exists: "main file still opens", but automatic checks only run in
projects that have a config file.

## Plugin shape (Hermes v0.22.7 interfaces, read from source b200f5bc)
- plugin.yaml + `__init__.py` `register(ctx)`; `requires_hermes: ">=0.22.7"`
- `ctx.register_tool` x5, `ctx.register_hook` pre/post_tool_call
  (callbacks accept `**kwargs`), `ctx.register_command` /lastgood and /blame
- Data: `plugins.plugin_storage.plugin_data_dir("lastgood")`. Project:
  `agent.runtime_cwd.resolve_agent_cwd()` (falls back to TERMINAL_CWD,
  then getcwd).
- Atomic, locked JSON writes. Corrupt files are preserved as `.corrupt-*`.

## Settled decisions (unchanged)
No bisect. No command-running check and no subprocess. No snapshot engine
of our own: restoring stays with Hermes' `/rollback`. Stdlib only. If the
live test shows that tested steps can't be mapped to a restorable
checkpoint, say so plainly instead of claiming recovery.

## Demo script
See DEMO_SCRIPT.md. A live demo must come from real Hermes. The
standalone simulation may only be shown if it's labelled as a simulation.

## Timeline (estimate)
- Sat Nov 7: spike + v0.1 (install, setup presets, green/red labelling) + spec/docs prep (no user computer needed)
- Sun Nov 8: v0.2 (blame finder, can't-undo ledger, Proof Report); user tests on their computer with Hermes
- Mon Nov 9: fix from tests, doctor/validate, README/install steps; feature freeze after
- Tue Nov 10: demo recording, PR + submission text prepped
- Wed Nov 11 (morning): submit PR + X post + form; rest of day is buffer

## What only the user's computer can do
- Install Hermes and the plugin and run them for real
- GitHub PR submission, X demo post, hackathon form (user's accounts)
