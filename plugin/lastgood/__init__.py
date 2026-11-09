"""LastGood — registration for Hermes Agent (interfaces read from v0.22.7).

* tools:    lastgood_check, lastgood_status, lastgood_blame,
            lastgood_report, lastgood_setup
* hooks:    pre_tool_call  -> records recognised can't-undo attempts
            post_tool_call -> settles those entries with the hook's status,
                              and after a successful file edit runs the
                              project's checks (only when the project has a
                              lastgood-config.json), bounded to 10 s
* commands: /lastgood [status|check [label]|blame|report|setup ...|help]
            /blame (shortcut for /lastgood blame)

Every callback swallows its own errors: a LastGood problem must never
break the agent's tool call.
"""

import json
import logging

try:
    from . import checks as C
    from . import tools
    from . import health as H
except ImportError:  # flat import fallback
    import checks as C  # type: ignore
    import tools  # type: ignore

logger = logging.getLogger(__name__)

# Hermes v0.22.7 file-editing tools (the ones its checkpoints guard).
# Terminal commands are NOT auto-checked: most are read-only and a URL
# check could cost seconds per command. Run /lastgood check after them.
AUTO_CHECK_TOOLS = frozenset({"write_file", "patch"})


def _hook_ids(kwargs) -> dict:
    return tools._ids(kwargs)


def _edit_target(project, args) -> str:
    """'inside', 'outside', or 'unresolved' for a write_file/patch target."""
    import os
    raw = args.get("path") if isinstance(args, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        return "unresolved"
    try:
        target = os.path.realpath(os.path.join(str(project), os.path.expanduser(raw)))
        root = os.path.realpath(str(project))
        return "inside" if os.path.commonpath([root, target]) == root else "outside"
    except (ValueError, OSError):
        return "unresolved"


def _on_pre_tool_call(tool_name=None, args=None, **kwargs):
    """Observe only. Returns None so Hermes' own approval flow decides."""
    project, ids = None, _hook_ids(kwargs)
    try:
        project = tools.resolve_project()
        H.observe(project, ids, "pre", tool_name)
        if tool_name and not str(tool_name).startswith("lastgood_"):
            tools.ledger_attempt(tools.resolve_project(), tool_name, args, _hook_ids(kwargs))
    except Exception as exc:
        if project is not None:
            H.callback_error(project, ids, type(exc).__name__)
        logger.debug("LastGood pre_tool_call failed", exc_info=True)
    return None


def _on_post_tool_call(tool_name=None, args=None, result=None, **kwargs):
    project, ids = None, _hook_ids(kwargs)
    try:
        project = tools.resolve_project()
        H.observe(project, ids, "post", tool_name, tools.core.map_post_status(kwargs.get("status"), kwargs.get("error_type")))
        if not tool_name or str(tool_name).startswith("lastgood_"):
            return
        project = tools.resolve_project()
        ids = _hook_ids(kwargs)
        status = kwargs.get("status")
        tools.ledger_result(project, tool_name, args, ids, status, kwargs.get("error_type"))
        if tool_name in AUTO_CHECK_TOOLS:
            mapped = tools.core.map_post_status(status, kwargs.get("error_type"))
            if mapped != "succeeded":
                return
            if C.broad_root_reason(project):
                # Too-broad session folder (home/drive root): never auto-check or
                # write history per edit; explicit checks/status explain the fix.
                return
            where = _edit_target(project, args)
            if where == "outside":
                logger.info("LastGood: %s edited a file outside %s; not auto-checked", tool_name, project)
                return
            if not (project / C.CONFIG_NAME).is_file() and not tools.previously_configured(project):
                return  # project has not opted in
            if where == "unresolved":
                tools.record_skipped(project, f"after {tool_name} (skipped)",
                                     f"Auto-check skipped: could not tell which file {tool_name} changed, "
                                     "so this project was not certified. Run lastgood_check to test it.", ids)
                return
            tools.run_and_record(project, f"after {tool_name}", "auto", ids,
                                 budget=tools.HOOK_BUDGET_SECONDS)
    except Exception as exc:
        if project is not None:
            H.callback_error(project, ids, type(exc).__name__)
        logger.debug("LastGood post_tool_call failed", exc_info=True)


# ---------------------------------------------------------------- commands

HELP = """LastGood commands:
  /lastgood                 show tested steps and whether they are current
  /lastgood check [label]   run the checks now and record the result
  /lastgood blame           where checks first failed (not proof of cause)
  /lastgood report          write the HTML Proof Report
  /lastgood doctor          explicit SELF-TEST (not hook delivery proof)
  /lastgood setup           show the current check setup
  /lastgood setup words <file> <words...>   check those words stay in the file
  /lastgood setup opens <file>              check the file still opens
  /lastgood setup json {"checks": [...]}    full setup (up to 5 checks)
Checks live in lastgood-config.json in the project folder (start Hermes in a
dedicated project folder, not your home folder or a drive root).
Accepted check types: file_opens, text_present, files_exist, url_loads.
LastGood step numbers are not Hermes checkpoint numbers; restore with /rollback."""


def _fmt_status(s: dict) -> str:
    lines = [f"LastGood — {s['project']}", H.line(s.get("health", {})), f"Now: {s['now']}"]
    if s.get("setup", {}).get("error"):
        lines.append(f"Setup problem: {s['setup']['error']}")
    for r in s["tested_steps"][-15:]:
        lines.append(f"  #{r['id']} {r['result']:<7} {r['freshness']:<7} {r['label']}")
    lp = s.get("last_pass")
    if lp:
        lines.append(f"Last passing tested step: #{lp['id']} ({lp['freshness']}). "
                     "To go back, use /rollback to pick a checkpoint from before the failure, "
                     "then /lastgood check.")
    if s.get("history_error"):
        lines.append(f"History problem: {s['history_error']}")
    lines.append(s["note"])
    return "\n".join(lines)


def _setup_cmd(project, rest: str) -> str:
    rest = rest.strip()
    if not rest:
        cfg = C.load_project_config(project)
        if cfg["error"]:
            return f"Setup problem: {cfg['error']}\n\n{HELP}"
        return f"Checks ({cfg['source']}):\n" + json.dumps(cfg["checks"], indent=2, ensure_ascii=False)
    kind, _, tail = rest.partition(" ")
    if kind == "json":
        config = json.loads(tail)
    elif kind == "words":
        file, _, words = tail.strip().partition(" ")
        config = {"checks": [{"type": "file_opens", "path": file},
                             {"type": "text_present", "path": file, "text": words.strip()}]}
    elif kind == "opens":
        config = {"checks": [{"type": "file_opens", "path": tail.strip()}]}
    else:
        return HELP
    out = tools.save_setup(project, config)
    return (f"Saved {len(out['checks'])} check(s) to {out['saved']}.\n"
            "Run /lastgood check to test the current files.")


def _lastgood_command(raw_args="", **kwargs) -> str:
    try:
        parts = (raw_args or "").strip().split(None, 1)
        sub = parts[0].lower() if parts else "status"
        rest = parts[1] if len(parts) > 1 else ""
        project = tools.resolve_project()
        if sub in ("status", "ls"):
            return _fmt_status(tools.status(project, tools._ids(kwargs)))
        if sub == "doctor":
            return json.dumps(tools.doctor(project, tools._ids(kwargs)), ensure_ascii=False)
        if sub == "check":
            out = tools.run_and_record(project, rest or "checked via /lastgood", "command", tools._ids(kwargs))
            r = out["record"]
            lines = [f"Tested step #{r['id']}: {r['result']}"]
            lines += [f"  {c['result']:<7} {c['type']}: {c['detail']}" for c in r["checks"]]
            if r["config_error"]:
                lines.append(f"  Setup problem: {r['config_error']}")
            if out["note"]:
                lines.append(f"  Storage: {out['note']}")
            return "\n".join(lines)
        if sub == "blame":
            return _blame_text(project)
        if sub == "report":
            return "Proof Report written: " + tools.write_report(project, tools._ids(kwargs))["report"]
        if sub == "setup":
            return _setup_cmd(project, rest)
        return HELP
    except Exception as exc:
        return f"LastGood: {type(exc).__name__}: {exc}"


def _blame_text(project) -> str:
    b = tools.blame(project)
    text = f"LastGood blame: {b['verdict']}"
    if b.get("evidence_text"):
        text += f"\nHistorical evidence ({b['evidence_freshness']}):\n{b['evidence_text']}"
    if b.get("caution"):
        text += f"\n{b['caution']}\n{b['advice']}"
    return text


def _blame_command(raw_args="", **kwargs) -> str:
    try:
        return _blame_text(tools.resolve_project())
    except Exception as exc:
        return f"LastGood: {type(exc).__name__}: {exc}"


def register(ctx):
    try:
        from . import schemas
    except ImportError:  # flat import fallback
        import schemas  # type: ignore
    for name, schema, handler in (
        ("lastgood_check", schemas.LASTGOOD_CHECK, tools.lastgood_check),
        ("lastgood_status", schemas.LASTGOOD_STATUS, tools.lastgood_status),
        ("lastgood_blame", schemas.LASTGOOD_BLAME, tools.lastgood_blame),
        ("lastgood_report", schemas.LASTGOOD_REPORT, tools.lastgood_report),
        ("lastgood_setup", schemas.LASTGOOD_SETUP, tools.lastgood_setup),
    ):
        ctx.register_tool(name=name, toolset="lastgood", schema=schema, handler=handler)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_command("lastgood", _lastgood_command,
                         description="LastGood: tested steps, checks, blame, report, setup",
                         args_hint="[status|check|blame|report|doctor|setup]")
    H.registered()
    ctx.register_command("blame", _blame_command,
                         description="LastGood: where checks first failed")
