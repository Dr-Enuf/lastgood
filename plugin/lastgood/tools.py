"""LastGood tool handlers and shared operations.

Handler contract (Hermes v0.22.7 plugin guide): ``handler(args, **kwargs)``
returns a JSON string and never raises.

Where things live
  * check setup:  <project>/lastgood-config.json  (the user's own file)
  * history:      <plugin data dir>/projects/<sha256(project path)[:16]>/
                  index.json, ledger.json, report.html, project.json
    The plugin data dir is Hermes' ``plugins.plugin_storage.plugin_data_dir
    ("lastgood")`` (= <HERMES_HOME>/plugin-data/lastgood). When that module is
    not importable (standalone tests) the same path is computed from
    HERMES_HOME (default ~/.hermes). LASTGOOD_DATA_DIR overrides both.
  * project:      the session's working folder from Hermes'
    ``agent.runtime_cwd.resolve_agent_cwd()``; falls back to TERMINAL_CWD,
    then os.getcwd(). A tool call may pass an explicit "path".
    The Hermes home folder, and anything inside it, is refused.
"""

from __future__ import annotations

from . import changeview as CV
from . import health as H
import tempfile

import hashlib
import json
import os
import sys
import time
import threading
from pathlib import Path

try:
    from . import checks as C
    from . import core
except ImportError:  # flat import fallback
    import checks as C  # type: ignore
    import core  # type: ignore

PLUGIN_NAME = "lastgood"
HOOK_BUDGET_SECONDS = 10.0   # Hermes bounds hooks at 30 s by default
TOOL_BUDGET_SECONDS = 20.0


# ---------------------------------------------------------------- locations

def _platform_default_hermes_home() -> str:
    """Same default Hermes uses when HERMES_HOME is unset and its helper is absent."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return str(base / "hermes")
    return str(Path.home() / ".hermes")


def _hermes_home_from_helper():
    """Hermes' own resolver when the agent is installed (profile override, env, default)."""
    for mod_name, attr in (("hermes_constants", "get_hermes_home"),
                           ("hermes_cli.config", "get_hermes_home")):
        try:
            module = __import__(mod_name, fromlist=[attr])
            value = getattr(module, attr)()
        except Exception:
            continue
        if value:
            return value
    return None


def hermes_home() -> Path:
    """Hermes home, realpath'd: helper, else HERMES_HOME, else the platform default.

    This is the folder that holds credentials and control files. It is never a
    LastGood project, and neither is anything inside it.
    """
    raw = _hermes_home_from_helper()
    if not raw:
        env = os.environ.get("HERMES_HOME", "").strip()
        raw = env or _platform_default_hermes_home()
    return Path(os.path.realpath(os.path.expanduser(str(raw))))


def data_root(read_only=False) -> Path:
    override = os.environ.get("LASTGOOD_DATA_DIR")
    if override:
        return Path(override)
    if read_only:
        return hermes_home() / "plugin-data" / PLUGIN_NAME
    try:
        from plugins.plugin_storage import plugin_data_dir  # Hermes public helper
        return Path(plugin_data_dir(PLUGIN_NAME))
    except Exception:
        return hermes_home() / "plugin-data" / PLUGIN_NAME


def _session_cwd() -> Path:
    try:
        from agent.runtime_cwd import resolve_agent_cwd  # documented for plugins
        return Path(resolve_agent_cwd())
    except Exception:
        pass
    env = os.environ.get("TERMINAL_CWD", "").strip()
    if env and os.path.isdir(env):
        return Path(env)
    return Path(os.getcwd())


def resolve_project(path=None) -> Path:
    raw = Path(str(path)).expanduser() if path else _session_cwd()
    real = Path(os.path.realpath(raw))
    if not real.is_dir():
        raise NotADirectoryError(f"project folder not found: {raw}")
    home = hermes_home()
    try:
        inside = os.path.commonpath([str(home), str(real)]) == str(home)
    except ValueError:
        inside = False
    if inside:
        raise ValueError(
            f"{real} is the Hermes home folder, or inside it ({home}). "
            "That folder holds credentials and control files, so it cannot be a LastGood project. "
            "Start Hermes in a dedicated project folder."
        )
    return real


def project_store(project: Path, create=True) -> Path:
    key = hashlib.sha256(str(project).encode("utf-8")).hexdigest()[:16]
    d = data_root(read_only=not create) / "projects" / key
    meta = d / "project.json"
    if create and not meta.exists():
        core.atomic_write_json(meta, {"path": str(project), "created_at": core.now()})
    return d


def _ids(kwargs: dict) -> dict:
    keep = ("session_id", "conversation_id", "task_id", "turn_id", "tool_call_id")
    return {k: str(kwargs[k])[:120] for k in keep if kwargs.get(k)}


# ---------------------------------------------------------------- operations

def previously_configured(project: Path) -> bool:
    """True once this project has had an explicit lastgood-config.json."""
    store = project_store(project, create=False)
    try:
        if json.loads((store / "project.json").read_text()).get("configured"):
            return True
    except (OSError, ValueError):
        pass
    records, _ = core.read_list(store / "index.json")
    return any(r.get("config_source") == "project" for r in records)


def _mark_configured(project: Path) -> None:
    meta = project_store(project) / "project.json"
    try:
        data = json.loads(meta.read_text())
    except (OSError, ValueError):
        data = {"path": str(project)}
    if not data.get("configured"):
        data["configured"] = True
        core.atomic_write_json(meta, data)


def current_identity(project: Path, mark=False) -> dict:
    cfg = C.load_project_config(project)
    if mark and cfg["source"] == "project" and not cfg["error"]:
        _mark_configured(project)
    elif cfg["source"] in ("default", "none") and previously_configured(project):
        # Fail closed: never silently swap a chosen setup for weaker defaults.
        cfg = {"checks": None, "source": "missing", "config_hash": "missing",
               "error": f"{C.CONFIG_NAME} was set up for this project but is now missing; "
                        "restore it or run setup again"}
    paths = C.checked_paths(cfg["checks"]) if cfg["checks"] else []
    cfg["fingerprint"] = C.fingerprint(project, paths)
    return cfg


def config_state_of(cfg: dict) -> str:
    if cfg["source"] == "too_broad":
        return "TOO_BROAD"
    return 'MISSING' if cfg["source"] != 'project' else 'INVALID' if cfg['error'] else 'VALID'


# A timed-out worker never writes history. Limit each project to one in-flight
# read-only worker, so a hung filesystem/DNS request cannot grow a thread queue.
_WORKERS_LOCK = threading.Lock()
_WORKERS = {}


def _evaluate(project, deadline, diagnostic=False):
    ident = current_identity(project, mark=not diagnostic)
    if diagnostic and ident["source"] != "project":
        ident["error"] = "SELF-TEST requires an explicit valid project config."
    if diagnostic and not ident["error"]:
        results = []
        for check in ident["checks"]:
            if check["type"] == "url_loads":
                results.append(C.CheckResult("url_loads", C.UNKNOWN, "SELF-TEST skips remote URL checks."))
            else:
                results.extend(C.run_checks([check], project, deadline))
    else:
        results = [] if ident["error"] else C.run_checks(ident["checks"], project, deadline)
    config_state = config_state_of(ident)
    result = C.UNKNOWN if ident["error"] else C.overall(results)
    after = current_identity(project)
    same = (after["fingerprint"] == ident["fingerprint"]
            and after["config_hash"] == ident["config_hash"])
    if not same:
        result = C.UNKNOWN
    return {
        "result": result,
        "checks": [r.to_dict() for r in results],
        "config_source": ident["source"],
        "config_state": config_state,
        "config_hash": ident["config_hash"],
        "config_error": ident["error"] if same else "Files or setup changed during the check; rerun.",
        "fingerprint": ident["fingerprint"] if same else "changed-during-check",
    }


def run_and_record(project: Path, label: str, trigger: str, ids: dict | None = None,
                   budget: float = TOOL_BUDGET_SECONDS, diagnostic=False) -> dict:
    H.attempt(project, ids, diagnostic)
    started = time.time()
    deadline = time.monotonic() + budget
    done = threading.Event()
    box = {}

    def evaluate():
        try:
            box["value"] = _evaluate(project, deadline, diagnostic=True) if diagnostic else _evaluate(project, deadline)
        except Exception as exc:
            box["error"] = type(exc).__name__
        finally:
            done.set()
            with _WORKERS_LOCK:
                if _WORKERS.get(str(project)) is done:
                    _WORKERS.pop(str(project), None)

    with _WORKERS_LOCK:
        busy = str(project) in _WORKERS
        if not busy:
            _WORKERS[str(project)] = done
            threading.Thread(target=evaluate, daemon=True, name="lastgood-check").start()
    if not busy:
        done.wait(max(0, deadline - time.monotonic()))
    if "value" in box and done.is_set():
        evidence = box["value"]
    else:
        reason = ("Previous check is still running; not started." if busy else
                  "Check time budget exceeded; result UNKNOWN." if not done.is_set() else
                  "Check could not run: " + box.get("error", "unknown error"))
        evidence = {"result": C.UNKNOWN, "checks": [], "config_source": "unknown",
                    "config_hash": "unknown", "config_error": reason, "fingerprint": "unknown"}
    record = {
        "label": str(label or "tested step")[:200], **evidence,
        "trigger": trigger, "created_at": core.now(), **(ids or {}),
        "observation_started": started, "observation_finished": time.time(),
        "presence_observations": [c.get("observation") for c in evidence.get("checks", [])][:5],
    }

    out = {"record": {**record, "id": None, "trigger": "SELF-TEST"}, "note": "Diagnostic only; not recorded in history."} if diagnostic else _persist(project, record, deadline)
    H.finish(project, ids, out["record"]["result"], "value" in box and done.is_set(),
             "UNKNOWN" if out["record"]["result"] == C.UNKNOWN else None, diagnostic)
    return out


def record_skipped(project: Path, label: str, reason: str, ids: dict | None = None,
                   budget: float = HOOK_BUDGET_SECONDS) -> dict:
    """Record an auto-check that was deliberately NOT run (fail closed):
    result UNKNOWN, no checks, never a PASS for the session project."""
    record = {"label": str(label or "skipped step")[:200], "result": C.UNKNOWN, "checks": [],
              "config_source": "skipped", "config_hash": "skipped", "fingerprint": "skipped",
              "config_error": reason, "skipped": True, "trigger": "auto-skipped",
              "created_at": core.now(), **(ids or {})}
    return _persist(project, record, time.monotonic() + budget)


def _persist(project: Path, record: dict, deadline: float) -> dict:
    record = CV.sanitize(record)  # redaction happens before disk, not only display
    key = (os.path.realpath(project), str(record.get("session_id") or "standalone"))
    explicit_baseline = (record.get("label", "").strip().lower() == "baseline"
                         and record.get("trigger") != "auto-skipped"
                         and record.get("result") in (C.PASS, C.FAIL))
    def _append(items):
        state = CV.continuity(key)
        record["continuity_epoch"] = state["epoch"]
        record["continuity_blocked"] = state["blocked"] and not explicit_baseline
        record["baseline_requested"] = explicit_baseline
        record["id"] = core.next_id(items)
        record["change_evidence"] = CV.compare(items[-1] if items else None, record)
        items.append(record)
        CV.retain(items)
        return record

    try:
        remaining = max(0.01, deadline - time.monotonic())
        _, note = core.update_list(project_store(project) / "index.json", _append, timeout=remaining)
        if explicit_baseline:
            CV.accept_baseline(key, record["continuity_epoch"])
    except (TimeoutError, OSError, ValueError):
        CV.lost_continuity(key)
        record["id"] = None
        record["result"] = C.UNKNOWN
        record["config_error"] = (record.get("config_error") or "") + " Storage failed; result NOT recorded."
        record["change_evidence"] = None
        note = "storage failed; nothing recorded; deltas disabled until /lastgood check baseline succeeds"
    return {"record": record, "note": note}


def status(project: Path, ids=None) -> dict:
    store = project_store(project, create=False)
    records, err = core.read_list(store / "index.json")
    ident = current_identity(project)
    fp, ch = ident["fingerprint"], ident["config_hash"]
    view = [{**{k: r.get(k) for k in ("id", "label", "result", "trigger", "created_at", "config_error")},
             "freshness": core.freshness(r, fp, ch)} for r in records]
    latest = view[-1] if view else None
    good = core.last_pass(records)
    if latest is None:
        now_text = "nothing tested yet"
    elif latest["freshness"] == core.CURRENT:
        now_text = f"{latest['result']} (current)"
    elif latest["freshness"] == core.UNVERIFIED:
        now_text = f"UNVERIFIED: last result {latest['result']}; files unchanged but the web page was not rechecked"
    else:
        now_text = "STALE: files or check setup changed since the last check; run a check"
    return {
        "project": str(project),
        "health": runtime_health(project, ids, err),
        "now": now_text,
        "tested_steps": view,
        "last_pass": ({"id": good["id"], "label": good.get("label"),
                       "freshness": core.freshness(good, fp, ch)} if good else None),
        "setup": {"source": ident["source"], "error": CV.redact(ident["error"]) if ident["error"] else None},
        "history_error": err,
        "note": "LastGood step numbers are not Hermes checkpoint numbers.",
    }


def blame(project: Path) -> dict:
    records, err = core.read_list(project_store(project, create=False) / "index.json")
    hit, good = core.first_failure(records), core.last_pass(records)
    if hit is None:
        verdict = "No check has failed in the recorded history." if records else "No tested steps recorded yet."
        return {"verdict": verdict, "history_error": err}
    return {
        "verdict": f"Checks first failed at tested step #{hit['id']} — “{hit.get('label', '')}”.",
        "failed_checks": [c for c in hit.get("checks", []) if c.get("result") == C.FAIL],
        "change_evidence": hit.get("change_evidence"),
        "evidence_text": CV.describe(hit.get("change_evidence")),
        "evidence_freshness": core.freshness(hit, current_identity(project)["fingerprint"], current_identity(project)["config_hash"]),
        "last_pass": good["id"] if good else None,
        "caution": "First observed failure in retained history, not proof of cause.",
        "advice": ("To go back, run Hermes' /rollback, pick the checkpoint taken before the "
                   "failing step (use /rollback diff N to preview), then run a LastGood check. "
                   "LastGood step numbers are not Hermes checkpoint numbers."),
        "history_error": err,
    }


def write_report(project: Path, ids=None) -> dict:
    store = project_store(project)
    records, err1 = core.read_list(store / "index.json")
    ledger, err2 = core.read_list(store / "ledger.json")
    ident = current_identity(project)
    notes = [n for n in (err1, err2) if n]
    out = store / "report.html"
    core.atomic_write_text(out, core.generate_report(str(project), records, ledger,
                                                     ident["fingerprint"], ident["config_hash"], notes,
                                                     H.line(runtime_health(project, ids, err1))))
    return {"report": str(out), "tested_steps": len(records), "ledger_entries": len(ledger)}


def save_setup(project: Path, config, *, from_user=False) -> dict:
    reason = C.broad_root_reason(project)
    if reason:
        raise C.ConfigError(C.broad_root_message(reason))
    try:
        checks = C.validate_config(config)
    except C.ConfigError as exc:
        raise C.ConfigError(f"{exc}. Nothing was saved. {C.CONFIG_HELP}") from None
    # The model reaches this through lastgood_setup (from_user stays false).
    # A page check is only saved from the slash command or a file the user edits.
    if not from_user and any(c.get("type") == "url_loads" for c in checks):
        raise C.ConfigError(
            "url_loads checks can only be added by you, with /lastgood setup "
            "or by editing lastgood-config.json. The lastgood_setup tool cannot add one. "
            "Nothing was saved."
        )
    target = Path(project) / C.CONFIG_NAME
    if target.is_symlink():
        raise C.ConfigError(f"{C.CONFIG_NAME} is a symlink; refusing to overwrite it")
    core.atomic_write_json(target, {"checks": checks})
    _mark_configured(project)
    return {"saved": str(target), "checks": checks}


# ---------------------------------------------------------------- ledger

def ledger_attempt(project: Path, tool_name, args, ids: dict) -> None:
    verdict = core.classify_action(tool_name, args)
    if not verdict:
        return
    entry = {**verdict, "tool_name": core.safe_tool_name(tool_name), "status": "attempted",
             "attempted_at": core.now(), **ids}

    def _add(items):
        entry["id"] = core.next_id(items)
        items.append(entry)

    core.update_list(project_store(project) / "ledger.json", _add)


def ledger_result(project: Path, tool_name, args, ids: dict, status_value, error_type=None) -> None:
    mapped = core.map_post_status(status_value, error_type)
    call_id = ids.get("tool_call_id")
    path = project_store(project) / "ledger.json"
    verdict = None

    def _update(items):
        if call_id:
            for item in reversed(items):
                if item.get("tool_call_id") == call_id and item.get("status") == "attempted":
                    item["status"] = mapped
                    item["updated_at"] = core.now()
                    return True
        if verdict:
            items.append({**verdict, "id": core.next_id(items), "tool_name": core.safe_tool_name(tool_name),
                          "status": mapped, "updated_at": core.now(), **ids})
            return True
        return False

    verdict = core.classify_action(tool_name, args)
    if not verdict:
        if not call_id:
            return
        items, _ = core.read_list(path)
        if not any(i.get("tool_call_id") == call_id and i.get("status") == "attempted" for i in items):
            return
    core.update_list(path, _update)


# ---------------------------------------------------------------- handlers

def _err(name: str, exc: Exception) -> str:
    # Error text can echo user/model-written config values: redact like stored history.
    return json.dumps({"error": CV.redact(f"{name} failed: {type(exc).__name__}: {exc}")})


def _args(args) -> dict:
    return args if isinstance(args, dict) else {}


def lastgood_check(args, **kwargs) -> str:
    try:
        a = _args(args)
        project = resolve_project(a.get("path"))
        out = run_and_record(project, a.get("label") or "manual check", "tool", _ids(kwargs))
        r = out["record"]
        return json.dumps({
            "tested_step": r["id"], "label": r["label"], "result": r["result"],
            "checks": r["checks"], "setup_source": r["config_source"],
            "setup_error": r["config_error"], "storage_note": out["note"],
            "note": "This labels the files as they are now; it is not a Hermes checkpoint.",
        }, ensure_ascii=False)
    except Exception as exc:
        return _err("lastgood_check", exc)


def lastgood_status(args, **kwargs) -> str:
    try:
        return json.dumps(status(resolve_project(_args(args).get("path")), _ids(kwargs)), ensure_ascii=False)
    except Exception as exc:
        return _err("lastgood_status", exc)


def lastgood_blame(args, **kwargs) -> str:
    try:
        return json.dumps(blame(resolve_project(_args(args).get("path"))), ensure_ascii=False)
    except Exception as exc:
        return _err("lastgood_blame", exc)


def lastgood_report(args, **kwargs) -> str:
    try:
        return json.dumps(write_report(resolve_project(_args(args).get("path")), _ids(kwargs)))
    except Exception as exc:
        return _err("lastgood_report", exc)


def lastgood_setup(args, **kwargs) -> str:
    try:
        a = _args(args)
        project = resolve_project(a.get("path"))
        return json.dumps(save_setup(project, {"checks": a.get("checks")}), ensure_ascii=False)
    except Exception as exc:
        return _err("lastgood_setup", exc)


# Runtime diagnostics never dispatch hooks and never append diagnostic history.
def runtime_health(project, ids=None, history_error=None):
    state = H.read(project, ids)
    cfg = C.load_project_config(project)
    state['config'] = config_state_of(cfg)
    state['history'] = 'UNKNOWN' if history_error else 'READABLE_OR_EMPTY'
    state['storage_writable'] = 'UNTESTED (explicit doctor only)'
    return state


_PROBES_LOCK = threading.Lock()
_PROBES = set()


def _storage_probe(project, deadline):
    done = threading.Event()
    box = {}
    key = os.path.realpath(project)
    if not _PROBES_LOCK.acquire(timeout=0.1):
        return {'result': C.UNKNOWN, 'error': 'Probe registry busy'}
    try:
        if key in _PROBES:
            return {'result': C.UNKNOWN, 'error': 'Previous storage probe still running'}
        _PROBES.add(key)
    finally:
        _PROBES_LOCK.release()

    def probe():
        temp = None
        outcome = {'result': C.UNKNOWN, 'error': 'Storage probe incomplete'}
        try:
            store = project_store(project)
            with core.locked(store / 'doctor-probe', timeout=max(0, deadline - time.monotonic())):
                if time.monotonic() >= deadline:
                    raise TimeoutError('probe budget')
                fd, temp = tempfile.mkstemp(prefix='.lastgood-doctor-', dir=store)
                with os.fdopen(fd, 'w+b') as fh:
                    fh.write(b'LastGood storage probe\n')
                    fh.flush()
                    fh.seek(0)
                    if fh.read() != b'LastGood storage probe\n':
                        raise OSError('probe mismatch')
                _, history_error = core.read_list(store / 'index.json')
                outcome = {'result': C.PASS, 'history': 'UNKNOWN' if history_error else 'READABLE_OR_EMPTY'}
        except Exception as exc:
            outcome = {'result': C.UNKNOWN, 'error': type(exc).__name__}
        finally:
            if temp:
                try:
                    os.unlink(temp)
                except OSError:
                    outcome = {'result': C.UNKNOWN, 'error': 'Probe cleanup failed'}
            with _PROBES_LOCK:
                _PROBES.discard(key)
            if time.monotonic() > deadline:
                outcome = {'result': C.UNKNOWN, 'error': 'Storage probe lifecycle exceeded time budget'}
            box['value'] = outcome  # publish ONLY after cleanup and worker bookkeeping
            done.set()
    threading.Thread(target=probe, name='lastgood-doctor-probe', daemon=True).start()
    completed = done.wait(max(0, deadline - time.monotonic()))
    if not completed or time.monotonic() > deadline:
        return {'result': C.UNKNOWN, 'error': 'Storage probe time budget exceeded; cleanup unconfirmed'}
    return dict(box.get('value', {'result': C.UNKNOWN, 'error': 'Storage probe completion unknown'}))


def doctor(project, ids=None, budget=3.0):
    deadline = time.monotonic() + min(max(float(budget), 0.05), 5.0)
    tested = run_and_record(project, 'SELF-TEST doctor', 'SELF-TEST', ids,
                            budget=max(.01, (deadline - time.monotonic()) / 2), diagnostic=True)
    r = tested['record']
    config = r.get('config_state', 'UNKNOWN')
    storage = _storage_probe(project, deadline)
    result = C.FAIL if r['result'] == C.FAIL else C.UNKNOWN
    if r['result'] == C.PASS and storage['result'] == C.PASS and config == 'VALID' and storage.get('history') != 'UNKNOWN':
        result = C.PASS
    return {'source': 'SELF-TEST', 'diagnostic_result': result, 'config': config,
            'checks': {'result': r['result'], 'details': r['checks']}, 'storage': storage,
            'health': H.read(project, ids),
            'note': 'No history/checkpoint written; no hooks simulated. Diagnostic PASS is not hook delivery or recovery proof.'}
