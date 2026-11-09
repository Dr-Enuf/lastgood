> **SUPERSEDED (Nov 7, 2026).** Hermes v0.22.7 is already installed in
> WSL on Kenny's PC. Do NOT reinstall or update it. Follow PC_TEST_PLAN.md,
> which uses an isolated test HERMES_HOME.

# Install prep — for tomorrow (Sun Nov 8) on your computer

Prepared Sat Nov 7, 2026, after re-verifying the v0.1 tests (16 passing)
and demo (PASS). Checked against the official Hermes plugin guide and
install guides — NOT yet run on your computer, so treat the commands
below as the starting point and tell Muse what each one prints.

## 1. Install Hermes Agent
Easiest official route (macOS / Linux / WSL2, Terminal):

```
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Then reload the shell if `hermes` is not found, and verify:

```
hermes --version
hermes doctor
```

Desktop installer (macOS / Windows) is the alternative if you prefer
an app over Terminal — download it from the official Hermes Agent site.
A model provider is NOT needed just to install, only to actually chat
with Hermes; `hermes setup` walks through choosing one.

## 2. Install + enable LastGood (from this folder)
Plugins live in `~/.hermes/plugins/` or via a pip entry point, per the
official plugin guide. Tomorrow Muse will copy/enable this build and
confirm the exact path with you — do not guess it tonight.

## 3. Hermes' own checks on LastGood (the real test)
```
hermes plugins doctor <path-to-lastgood>
hermes plugins validate <path-to-lastgood> --install-deps
```
`doctor` runs the same discovery, manifest parser, `register(ctx)` and
registries Hermes uses. `validate` runs the same check catalog CI runs.
Paste / read Muse whatever they print — Muse interprets the results.

## 4. Then the 4 guided tests (from TOMORROW_CHECKLIST.md)
1. Pick a preset check, confirm "test it now" passes.
2. Let Hermes change a sample file until it breaks — save point turns red.
3. Run `/blame` — it should show the step after which checks first failed.
4. Run `/lastgood` — it should name the last step whose checks passed;
   restore with Hermes' `/rollback` and re-run the checks to confirm green.

## If something fails tomorrow
- `hermes: command not found` → close and reopen Terminal (PATH reload),
  then run `hermes --version` again before reinstalling.
- `hermes doctor` errors about a provider / API key → that is a chat
  setup issue, not a plugin issue; the plugin doctor/validate checks
  above are the ones that matter for LastGood.
- Any other error → copy the exact message to Muse; do not reinstall
  or delete anything first.

## Sources checked Nov 7, 2026
- Official plugin guide: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
  (`hermes plugins validate … --install-deps`, `hermes plugins doctor`,
  `~/.hermes/plugins/`, `hermes plugins install / list / enable`)
- Install command above appears in the official install path and in
  Mac install guides tested Jul–Aug 2026 (Hermes v0.18.2 / v0.20.5).
  Version numbers may have moved since — `hermes --version` tomorrow
  is the authoritative check.
