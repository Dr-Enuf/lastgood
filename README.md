# LastGood

**Verification history for Hermes Agent** — know which checks passed on which
tested files, and what restoring those files will not undo.

LastGood is a Hermes plugin. After you (or the agent) edit files, it re-runs a
small set of checks you chose — does this file still open, are these words still
there, do these files still exist, does this page still load? — and records
PASS, FAIL, or UNKNOWN against a fingerprint of the checked files. Old results
are marked stale when the files change. `/lastgood blame` shows where checks
first failed (not why). A ledger notes tool calls that a file rollback cannot
undo, without storing their arguments.

It is **not** a save/restore engine and it does not run shell commands.

- Version: **0.4.1**
- License: [MIT](LICENSE) — Copyright (c) 2026 Kenneth Ausmus
- Repository: https://github.com/Dr-Enuf/lastgood
- Maintainer: Kenneth Ausmus (Dr-Enuf)
- Immutable catalog SHA: fill in the 40-character commit hash after you upload
  (`sha: TODO` in `CATALOG_ENTRY_DRAFT.yaml`)

## Install in about 30 seconds

1. Copy the `plugin/lastgood` folder into your Hermes plugins directory as
   `lastgood` (for example `%LOCALAPPDATA%\hermes\plugins\lastgood` on
   Windows, or `~/.hermes/plugins/lastgood` on Linux/macOS).
2. Enable it in Hermes’ plugin settings (or add `lastgood` under
   `plugins.enabled` in that Hermes home’s `config.yaml`).
3. Restart Hermes if it is already running, so it loads the new files.
4. Open Hermes **in a dedicated project folder** — not your home folder or
   Desktop — and run `/lastgood setup opens <file>` then `/lastgood check`.

Requires Hermes Agent **0.22.7** or newer.

## The four check types

Put them in `lastgood-config.json` in the project folder, or let `/lastgood setup`
write that file:

| Type | What it checks |
| --- | --- |
| `file_opens` | The file exists, is readable, and still parses (JSON, CSV, Python, HTML markers, or non-empty UTF-8). |
| `text_present` | The given words still appear in the file. |
| `files_exist` | Each listed file is still there. |
| `url_loads` | An `http://` or `https://` address still loads (optional words on the page). |

Unknown fields or a missing `type` make the whole setup UNKNOWN — LastGood will
not guess. There is no command-running check.

Minimal example:

```json
{"checks": [{"type": "file_opens", "path": "calculator.py"}]}
```

## Quick demo

```text
/lastgood setup opens calculator.py
/lastgood check baseline          → PASS (if the file opens)
# edit the file (yourself or let the agent patch it)
/lastgood status                  → current PASS/FAIL, or STALE if files changed
/lastgood blame                   → first recorded failure (not proof of cause)
/lastgood report                  → one HTML proof report
```

If you start Hermes in your home folder, LastGood refuses with UNKNOWN and asks
you to use a dedicated project folder. If `lastgood-config.json` uses invented
fields, it stays UNKNOWN and lists the four types above.

## Honest limits

- Results are verification history, not saved-state recovery or automatic rollback.
  LastGood step numbers are **not** Hermes checkpoint numbers; restore with Hermes’
  `/rollback`, then run a fresh `/lastgood check`.
- UNKNOWN means “could not decide” (bad setup, timeout, unreachable page) — never
  a silent PASS.
- Health (`/lastgood status` / `/lastgood doctor`) observes callbacks in the
  current plugin process. It is not a security guarantee. Owner-restart of the
  plugin-owning Hermes runtime was not re-tested on the host for 0.4.1.
- Native Windows test suite: 114 ran, 0 failed, **4 skipped** (symlink tests that
  need symlink privilege). Those skips are intended.
- A live PTY helper once queued `/lastgood status` during a model spinner because
  it mistook the on-screen footer for a ready prompt. That was the test driver,
  not the plugin.

What was tested for 0.4.1 (isolated Hermes home, plugin source set
`f5454db89818c3f80e9ece7d788f816ca7ee059136abea85edb699dd9df94282`): 114
standalone tests; Hermes doctor (5 tools, 2 hooks); validate 15/15; plugin
harness; a live local-model run showing TOO_BROAD refusal, invalid-config
guidance, setup + PASS, and a real `patch` auto-check PASS.

## Layout

```text
plugin/lastgood/     the plugin (copy this folder into Hermes)
tests/               standalone unittest suite
sample-project/      small bakery demo files
scripts/             demo_end_to_end.py and a Hermes PluginManager harness
integration-evidence/ host and live notes (raw PTY dumps omitted; paths generalized)
```

Further reading: [START-HERE.md](START-HERE.md), [DEMO_SCRIPT.md](DEMO_SCRIPT.md),
[INTEGRATION_RESULTS.md](INTEGRATION_RESULTS.md), [CHANGELOG.md](CHANGELOG.md),
[CATALOG_ENTRY_DRAFT.yaml](CATALOG_ENTRY_DRAFT.yaml).
