"""LastGood core: durable JSON storage, tested-state history, ledger, report.

Knows nothing about Hermes; the Hermes-facing wiring is in tools.py and
__init__.py. Stdlib only.

Storage rules:
  * every write is atomic (temp file in the same folder + os.replace)
  * every read-modify-write holds a lock (fcntl.flock where available,
    otherwise an O_EXCL lock file) plus an in-process lock
  * a history file that is not valid JSON is moved aside to
    "<name>.corrupt-<timestamp>" and reported, never silently overwritten
"""

from __future__ import annotations

from . import changeview as CV

import contextlib
import html
import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
CURRENT, STALE = "current", "stale"

_THREAD_LOCK = threading.RLock()
LOCK_TIMEOUT = 5.0


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- storage

@contextlib.contextmanager
def locked(path: Path, timeout: float = LOCK_TIMEOUT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    deadline = time.monotonic() + timeout
    if not _THREAD_LOCK.acquire(timeout=max(0.0, timeout)):
        raise TimeoutError("LastGood storage is busy")
    try:
        if fcntl is not None:
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
            try:
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except (BlockingIOError, PermissionError):
                        if time.monotonic() > deadline:
                            raise TimeoutError("LastGood storage is busy")
                        time.sleep(0.02)
                try:
                    yield
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
        else:
            while True:
                try:
                    os.close(os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
                    break
                except FileExistsError:
                    if time.monotonic() > deadline:
                        raise TimeoutError("LastGood storage is busy")
                    time.sleep(0.02)
            try:
                yield
            finally:
                with contextlib.suppress(OSError):
                    os.unlink(lock_path)
    finally:
        _THREAD_LOCK.release()


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def atomic_write_json(path: Path, data) -> None:
    atomic_write_text(path, CV.serialize_json(data))


def read_list(path: Path) -> tuple[list, str | None]:
    """Read-only load. Returns (items, error). Never moves or rewrites files."""
    path = Path(path)
    if not path.exists():
        return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [], f"{path.name} is unreadable ({type(exc).__name__})"
    if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
        return [], f"{path.name} has an unexpected shape"
    return data, None


def _load_for_update(path: Path) -> tuple[list, str | None]:
    """Caller holds the lock. Corrupt files are moved aside, not overwritten."""
    items, err = read_list(path)
    if err is None:
        return items, None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.corrupt-{stamp}")
    os.replace(path, backup)
    return [], f"{err}; preserved as {backup.name} and started a new history"


def update_list(path: Path, mutate, timeout: float = LOCK_TIMEOUT) -> tuple[object, str | None]:
    """Locked read-modify-write. ``mutate(items)`` changes the list in place
    and returns a value, which is passed back with any recovery note.
    Raises TimeoutError if the lock is not obtained within ``timeout``."""
    with locked(path, timeout):
        items, note = _load_for_update(Path(path))
        value = mutate(items)
        atomic_write_json(path, items)
    return value, note


# ---------------------------------------------------------------- history

def next_id(items: list) -> int:
    return max((int(i.get("id", 0)) for i in items), default=0) + 1


UNVERIFIED = "files current; web page not rechecked"


def freshness(record: dict, current_fingerprint: str, current_config_hash: str) -> str:
    same = (record.get("fingerprint") == current_fingerprint
            and record.get("config_hash") == current_config_hash)
    if not same:
        return STALE
    if any(c.get("type") == "url_loads" for c in record.get("checks", [])):
        return UNVERIFIED  # remote content is never fingerprinted
    return CURRENT


def last_pass(records: list) -> dict | None:
    for r in reversed(records):
        if r.get("result") == PASS:
            return r
    return None


def first_failure(records: list) -> dict | None:
    """First FAIL after a PASS (UNKNOWN is ignored); else the first FAIL.
    This is where failure was first OBSERVED, not proof of cause."""
    seen_pass, first = False, None
    for r in records:
        if r.get("result") == PASS:
            seen_pass = True
        elif r.get("result") == FAIL:
            if first is None:
                first = r
            if seen_pass:
                return r
    return first


# ---------------------------------------------------------------- ledger

_SAFE_TOOL = re.compile(r"[^A-Za-z0-9_.:-]")

# (category, level, pattern on normalised tool name, reason)
_TOOL_PATTERNS = [
    ("message", "irreversible", r"\b(send|reply|forward)\b.*\b(mail|email|message|messages|dm|chat|sms|text)\b|\bsend\b",
     "a sent message cannot be un-sent"),
    ("post", "irreversible", r"\b(post|publish|tweet|share|upload)\b", "a post may be seen before it is removed"),
    ("payment", "irreversible", r"\b(pay|payment|charge|purchase|transfer|wire|refund)\b", "a payment cannot be un-paid, only refunded"),
    ("remote_delete", "irreversible", r"\b(delete|remove|drop|destroy)\b.*\b(remote|api|cloud|account|repo|bucket|record)\b",
     "deleting something remote may leave no copy to restore"),
    ("create_remote", "compensable", r"\bcreate\b.*\b(calendar|event|issue|ticket|draft|pr|pull request)\b",
     "creates something that can usually be deleted again"),
    ("booking", "compensable", r"\b(schedule|book|reserve)\b", "a booking can usually be cancelled (fees may apply)"),
]
_COMMAND_PATTERNS = [
    ("git_push", "irreversible", r"\bgit\s+push\b", "a git push cannot be un-pushed, only reverted publicly"),
    ("network_send", "irreversible", r"\b(curl|wget|http)\b[^|;&]*\s-(X\s*(POST|PUT|DELETE|PATCH)|d|-data)\b",
     "a network request may have changed something remotely"),
]
_COMMAND_KEYS = ("command", "cmd", "script")
_RECIPIENT_KEYS = ("to", "recipient", "recipients", "email", "cc", "bcc")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
_SAFE_REMOTE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _recipient_domains(args: dict) -> list[str]:
    domains = []
    for key in _RECIPIENT_KEYS:
        val = args.get(key)
        vals = val if isinstance(val, list) else [val]
        for v in vals:
            if isinstance(v, str):
                domains.extend(m.group(1).lower() for m in _EMAIL.finditer(v))
    return sorted(set(domains))[:3]


def _push_remote(command: str) -> str | None:
    tokens = command.split()
    try:
        i = tokens.index("push")
    except ValueError:
        return None
    for tok in tokens[i + 1:]:
        if tok.startswith("-"):
            continue
        return tok if _SAFE_REMOTE.match(tok) and "://" not in tok and "@" not in tok else None
    return None


def classify_action(tool_name: str, args) -> dict | None:
    """Classify a tool call by whether a FILE rollback could undo it.

    Returns None for ordinary work, else {"category", "level", "reason",
    "target"}. Raw arguments are only inspected, NEVER returned: the target
    is at most recipient domains or a plain git remote name.
    """
    args = args if isinstance(args, dict) else {}
    name = _norm(tool_name)
    if re.search(r"\bdrafts?\b", name):
        return None  # draft-only tools do not send anything
    for category, level, pattern, reason in _TOOL_PATTERNS:
        if re.search(pattern, name):
            target = None
            if category == "message":
                doms = _recipient_domains(args)
                target = ("recipient domain(s): " + ", ".join(doms)) if doms else None
            return {"category": category, "level": level, "reason": reason, "target": target}
    for key in _COMMAND_KEYS:
        cmd = args.get(key)
        if not isinstance(cmd, str):
            continue
        for category, level, pattern, reason in _COMMAND_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                target = None
                if category == "git_push":
                    remote = _push_remote(cmd)
                    target = f"remote: {remote}" if remote else None
                return {"category": category, "level": level, "reason": reason, "target": target}
    return None


def map_post_status(status, error_type=None) -> str:
    s = str(status or "").lower()
    e = str(error_type or "").lower()
    if any(w in s or w in e for w in ("block", "denied", "deny", "veto", "reject", "cancel")):
        return "blocked"
    if s in ("ok", "success", "succeeded", "completed", "done"):
        return "succeeded"
    if s in ("error", "failed", "failure", "exception", "timeout"):
        return "failed"
    return "uncertain"


def safe_tool_name(tool_name) -> str:
    return _SAFE_TOOL.sub("_", str(tool_name or "?"))[:80]


# ---------------------------------------------------------------- report

_COLOURS = {PASS: "#2da44e", FAIL: "#cf222e", UNKNOWN: "#9a6700"}


def generate_report(project_label: str, records: list, ledger: list,
                    current_fp: str, current_cfg: str, notes: list | None = None, health_line="") -> str:
    e = html.escape
    rows, dots = [], []
    for r in records:
        result = r.get("result", UNKNOWN)
        colour = _COLOURS.get(result, "#8b949e")
        fresh = freshness(r, current_fp, current_cfg)
        details = "; ".join(f"{c.get('type')}: {c.get('result')} — {c.get('detail')}" for c in r.get("checks", []))
        if r.get("config_error"):
            details = f"setup problem: {r['config_error']}"
        dots.append(f'<span class="dot" style="background:{colour}" title="#{e(str(r.get("id")))} {e(str(r.get("label", "")))}"></span>')
        rows.append(
            f"<tr><td>#{e(str(r.get('id')))}</td><td>{e(str(r.get('label', '')))}</td>"
            f'<td style="color:{colour}"><b>{e(result)}</b></td><td>{e(fresh)}</td>'
            f"<td>{e(str(r.get('trigger', '')))}</td><td>{e(details)}</td><td>{e(str(r.get('created_at', '')))}</td></tr>")
    blame = first_failure(records)
    good = last_pass(records)
    if blame:
        verdict = f"Checks first failed at tested step #{e(str(blame['id']))} — “{e(str(blame.get('label', '')))}”. "
        verdict += (f"The last tested step that passed is #{e(str(good['id']))}." if good else "No tested step passed.")
        verdict += " This is where failure was first observed in retained history, not proof of what caused it."
        verdict += "<pre>" + e(CV.describe(blame.get("change_evidence"))) + "</pre>"
    elif records:
        verdict = "No check has failed in the recorded history."
    else:
        verdict = "No tested steps recorded yet."
    latest = records[-1] if records else None
    if latest:
        state = (f"Latest tested step #{e(str(latest['id']))}: {e(latest.get('result', UNKNOWN))}, "
                 f"{e(freshness(latest, current_fp, current_cfg))}.")
    else:
        state = "Nothing tested yet."
    ledger_rows = "".join(
        f"<tr><td>{e(str(x.get('category', '')))} ({e(str(x.get('level', '')))})</td>"
        f"<td>{e(str(x.get('tool_name', '')))}</td><td>{e(str(x.get('status', '')))}</td>"
        f"<td>{e(str(x.get('target') or '(not recorded)'))}</td><td>{e(str(x.get('reason', '')))}</td>"
        f"<td>{e(str(x.get('updated_at', x.get('attempted_at', ''))))}</td></tr>"
        for x in ledger
    ) or '<tr><td colspan="6">LastGood recognised no such tool calls. That does not prove none happened.</td></tr>'
    note_html = "".join(f"<li>{e(str(n))}</li>" for n in (notes or []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>LastGood Proof Report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}}
.dot{{display:inline-block;width:18px;height:18px;border-radius:50%;margin-right:6px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}}
.box{{background:#f6f8fa;border:1px solid #ddd;border-radius:8px;padding:1rem;margin:.5rem 0}}</style></head>
<body><h1>LastGood Proof Report</h1>
<p>Project: {e(project_label)}</p>
<p><small>{e(health_line)}</small></p>
<p>{''.join(dots)}</p>
<div class="box"><b>Now:</b> {state}</div>
<div class="box"><b>Verdict:</b> {verdict}</div>
<p><small>“current” means the checked files and the check setup are byte-for-byte what was tested.
“stale” means they changed since; rerun the checks. Web-page checks cannot be fingerprinted.
LastGood numbers are its own tested-step numbers, not Hermes checkpoint numbers.</small></p>
{('<ul>' + note_html + '</ul>') if note_html else ''}
<h2>Tested steps</h2>
<table><tr><th>#</th><th>Step</th><th>Result</th><th>Freshness</th><th>Trigger</th><th>Detail</th><th>When (UTC)</th></tr>{''.join(rows)}</table>
<h2>Recognised tool calls a file rollback won't undo</h2>
<p><small>Status comes from Hermes' tool-call hooks: “succeeded” means the tool reported success, not that LastGood verified the real-world effect. Raw arguments are never stored.</small></p>
<table><tr><th>Kind</th><th>Tool</th><th>Status</th><th>Target</th><th>Why</th><th>When (UTC)</th></tr>{ledger_rows}</table>
</body></html>"""
