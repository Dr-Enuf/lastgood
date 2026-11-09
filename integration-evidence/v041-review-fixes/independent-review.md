# LastGood v0.4.1 independent review (BOX only)

Monday, November 9, 2026, 9:58 AM EST. Snapshot `/tmp/lastgood-v41-audit-pknnsnor/source` of `/workspace/lastgood-guard/hermes-lastgood`. No source, PC, Git, other-bot or publishing actions. Isolated HOME, loopback only.

## Verdict: PASS. No high or blocking defects; four small follow-ups

- Source set verified: `b5924d7617b2d647b7c9cbe972774c70e4e0a4e63e52153a2bef01195bb788cb` (matches the reported b5924d76…; the live copy was unchanged at the end).
- v0.4.0 is still `23cf5460d6c8e94c3b84a630e7e37e136bb81e1d5d4e96d98390b238fa68b1c2`, so it is unchanged.
- **109 unique tests passed** with ResourceWarning treated as an error. **Simulation PASS.**
- **Windows-like run with symlinks unavailable:** os.symlink and Path.symlink_to were forced to raise WinError 1314. Result: 109 ran, 0 failures, 0 errors, 4 skipped.
- **The regressions really test the behaviour.** I removed each fix in turn and the suite failed: guard removed gave 4 failures and 2 errors; extra-field rejection removed gave 1 failure; leading-'/' and drive rejection removed gave 1 failure.
- **No false PASS found.** A home folder with a valid config and passing files returns UNKNOWN/TOO_BROAD. Auto-check hooks write nothing. Setup refuses and writes nothing. Doctor is never PASS.

## Bypass probes (real filesystem, through the tool handlers)

The home folder is refused in all of these forms: a symlink alias, a relative path (`<home-basename>`), a trailing separator (`<home-basename>/`), `./<home-basename>/.` and a doubled `//`. This holds because `resolve_project` resolves the real path before the guard runs.

String-level checks also refuse:
- uppercase or mixed separators (`C:/USERS/<HOME-BASENAME>`)
- trailing `\` and `\.`
- `C:`
- `\\?\C:\`
- `C:\Users\Public`
- `/mnt/C/Users/<home-basename>` and `/mnt/d`

Allowed, as intended:
- `<WINDOWS_USER_HOME>\projects\calc`
- `<USER_HOME>/proj`
- `<WINDOWS_USER_HOME>/projects/calc`
- `…\Documents\calc`
- `/opt/myapp`
- `/var/www/site`
- `/mnt/data/proj`

A dedicated subfolder of home sets up and checks PASS.

8.3 short names (`<HOME~1>`) and `\\?\` long paths depend on Windows `os.path.realpath` expanding or normalizing them before the guard runs. That cannot be shown on Linux, so add it to the host checklist.

## Findings, all LOW to MEDIUM-LOW, non-blocking (`checks.py` lines 393-462)

1. **MEDIUM-LOW: OneDrive for work or school folders are not refused.** `<WINDOWS_USER_HOME>\OneDrive - Contoso` and `…\OneDrive - Contoso\Desktop` are allowed. These are the default names on work or school Windows accounts. `_BROAD_CHILDREN` only matches an exact `onedrive`.
   - Minimal fix: match `onedrive( - .+)?` (and the same name with `/desktop` or `/documents`) in both the home-relative loop and the `users/<name>/…` regex.
   - This is not a false PASS. Checks only read the configured files. It is a guidance or history-noise gap.
2. **LOW: some broad folders are still allowed.** These are `C:\Users\<name>\AppData`, `/tmp` itself, and `/home/<other user>/Desktop`. The POSIX branch only applies the `_BROAD_CHILDREN` rule to the current user's homes; the Windows branch applies it to every `users/<name>`.
   - Optional fix: add `appdata` and `/tmp` to the lists, and a `/home/[^/]+/(desktop|documents|downloads)` regex for parity. Scope these narrowly.
3. **LOW: an unextended `\\?\<WINDOWS_USER_HOME>` or `\\?\UNC\server\share` string is allowed** by the string guard. This is only reachable if realpath leaves the prefix in place (see the host checklist). If you want belt-and-braces, strip a leading `\\?\` (and turn `UNC\` into `\\`) at the start of `_norm()`.
4. **LOW: invalid-config messages echo raw values in non-persisted output.** A `type` of `sk-SYNTHETIC…` (or a secret-looking field name) is redacted in stored history and in the lastgood_check result, but appears unredacted in `lastgood_status` setup errors and in `lastgood_setup` errors. A synthetic field *value* (`password` value) never appeared.
   - The echo only reflects what the user or model already wrote, so the risk is low.
   - Minimal fix: pass these errors through `CV.redact` (as `_persist` already does) in `status()` setup error and `lastgood_setup` `_err`.

Also note: the drive check now rejects a POSIX filename such as `a:b.txt` (`PureWindowsPath(...).drive`). That is acceptable and intentional for portability, but mention it in the README. `notes:v2.txt`, `src/app.py` and `.well-known/x` are still accepted. Absolute POSIX paths were already rejected in earlier versions, so the leading-'/' rule changes nothing for legitimate POSIX users.

**Compatibility:** a config with extra fields that loaded before now becomes INVALID/UNKNOWN. This is intentional and documented in RESOLUTION.md. The sample config contains only allowed fields and still passes.

## Not covered

Native Windows test run, the Windows realpath behaviour for 8.3 and `\\?\` paths, and the host doctor/validate/live checks for v0.4.1 are all still pending.

Evidence: `/workspace/lastgood-guard-independent-review-evidence/` (test/demo/no-symlink logs, guard/message probes, mutation results, hashes). Per-file hashes are in `hashes.json`.
