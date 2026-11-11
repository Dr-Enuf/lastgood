"""Preset checks for LastGood (stdlib only, no subprocess).

A project opts in by putting ``lastgood-config.json`` in its folder:

    {"checks": [
      {"type": "file_opens",   "path": "index.html"},
      {"type": "text_present", "path": "index.html", "text": "555-0100"},
      {"type": "files_exist",  "paths": ["index.html", "menu.pdf"]},
      {"type": "url_loads",    "url": "http://127.0.0.1:8000/", "text": "Bakery"}
    ]}

Each check accepts only the fields shown for its type; unknown fields or a
missing/unknown "type" make the whole setup invalid (UNKNOWN, never guessed).
LastGood also refuses to treat a home folder, drive/filesystem root or
system folder as a project (UNKNOWN with a plain-English setup message).

Every check returns PASS, FAIL or UNKNOWN:
  PASS     the check ran and its condition held
  FAIL     the check ran and its condition did not hold (file missing,
           words gone, page answered with an error status)
  UNKNOWN  LastGood could not decide (time budget used up, page
           unreachable, file too large or unreadable, bad setup)

Paths must stay inside the project folder (no absolute paths, no "..",
no symlink that resolves outside). There is deliberately NO shell-command
check type.

url_loads fetches only the http(s) address in the config. The host is resolved
once; every A/AAAA result is checked, including IPv4-mapped IPv6, and the
connection is opened to an address that passed that check. The same check runs
on every redirect hop. Link-local, cloud-metadata and unspecified addresses are
always refused. Other private ranges are refused unless the user turned on
allow_private_urls. Loopback stays allowed.
"""

from __future__ import annotations

from . import changeview as CV

import csv
import errno
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"

CONFIG_NAME = "lastgood-config.json"
MAX_CONFIG_BYTES = 64 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_URL_BODY_BYTES = 1024 * 1024
URL_TIMEOUT_CAP = 5.0
MAX_CHECKS = 5
MAX_PATHS = 50
MAX_TEXT = 500
CHECK_TYPES = ("file_opens", "text_present", "files_exist", "url_loads")
# Fields each check type accepts. Anything else is rejected (never guessed).
CHECK_FIELDS = {
    "file_opens": {"type", "path"},
    "text_present": {"type", "path", "text", "case_insensitive"},
    "files_exist": {"type", "paths"},
    "url_loads": {"type", "url", "text", "timeout"},
}
CONFIG_EXAMPLE = '{"checks": [{"type": "file_opens", "path": "calculator.py"}]}'
CONFIG_HELP = (
    "Accepted check types: file_opens {path}, text_present {path, text}, "
    "files_exist {paths}, url_loads {url, optional text}. "
    f"Minimal valid lastgood-config.json: {CONFIG_EXAMPLE}. "
    "Easiest fix: run /lastgood setup opens <file> (or /lastgood setup words <file> <words>), "
    "or call the lastgood_setup tool, instead of writing the file by hand."
)
BROAD_ROOT_HELP = (
    "Start Hermes in a dedicated project folder (for example a new folder that holds only "
    "this project), then run /lastgood setup opens <file> and /lastgood check baseline."
)


class ConfigError(ValueError):
    """The check setup is unusable; results must be UNKNOWN, never PASS."""


class PathRejected(ValueError):
    """A configured path points outside the project."""


@dataclass
class CheckResult:
    type: str
    result: str
    detail: str
    files: list = field(default_factory=list)
    observation: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------- validation

def _validate_rel_path(raw) -> str:
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw or len(raw) > 300:
        raise ConfigError(f"bad file path: {raw!r}")
    if (os.path.isabs(raw) or PureWindowsPath(raw).is_absolute()
            or raw.startswith(("~", "\\", "/")) or PureWindowsPath(raw).drive):
        raise ConfigError(f"path must be inside the project, not absolute: {raw!r}")
    parts = PurePosixPath(raw.replace("\\", "/")).parts
    if ".." in parts:
        raise ConfigError(f"path must not use '..': {raw!r}")
    return raw


def _validate_url(raw) -> str:
    if not isinstance(raw, str) or len(raw) > 2000:
        raise ConfigError("url must be a short text address")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ConfigError(f"url must start with http:// or https://: {raw!r}")
    if parsed.username or parsed.password:
        raise ConfigError("url must not contain a username or password")
    return raw


def _validate_text(raw) -> str:
    if not isinstance(raw, str) or not raw or len(raw) > MAX_TEXT:
        raise ConfigError(f"words to look for must be 1-{MAX_TEXT} characters")
    return raw


def validate_config(config) -> list[dict]:
    """Return a normalised check list or raise ConfigError."""
    if not isinstance(config, dict):
        raise ConfigError("config must be a JSON object with a 'checks' list")
    checks = config.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ConfigError("config needs a non-empty 'checks' list")
    if len(checks) > MAX_CHECKS:
        raise ConfigError(f"pick at most {MAX_CHECKS} checks")
    out = []
    for n, c in enumerate(checks, 1):
        if not isinstance(c, dict):
            raise ConfigError(f"check #{n} must be an object")
        kind = c.get("type")
        if "type" not in c:
            raise ConfigError(f"check #{n} has no \"type\" field")
        if kind not in CHECK_TYPES:
            raise ConfigError(f"check #{n} has unknown type {CV.bounded(repr(kind), 60)}")
        extra = sorted(str(k) for k in c if k not in CHECK_FIELDS[kind])
        if extra:
            raise ConfigError(f"check #{n} ({kind}) has unsupported field(s): "
                              + CV.bounded(", ".join(extra), 120))
        if kind in ("file_opens", "text_present"):
            item = {"type": kind, "path": _validate_rel_path(c.get("path"))}
            if kind == "text_present":
                item["text"] = _validate_text(c.get("text"))
                if c.get("case_insensitive"):
                    item["case_insensitive"] = True
        elif kind == "files_exist":
            paths = c.get("paths")
            if not isinstance(paths, list) or not paths or len(paths) > MAX_PATHS:
                raise ConfigError(f"files_exist needs 1-{MAX_PATHS} file paths")
            item = {"type": kind, "paths": [_validate_rel_path(p) for p in paths]}
        else:
            item = {"type": kind, "url": _validate_url(c.get("url"))}
            timeout = c.get("timeout", URL_TIMEOUT_CAP)
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
                raise ConfigError("url timeout must be a number of seconds between 0 and 60")
            item["timeout"] = min(float(timeout), URL_TIMEOUT_CAP)
            if c.get("text") is not None:
                item["text"] = _validate_text(c.get("text"))
        out.append(item)
    return out


def checked_paths(checks: list[dict]) -> list[str]:
    paths = []
    for c in checks:
        if c["type"] in ("file_opens", "text_present"):
            if not CV.sensitive_path(c["path"]):
                paths.append(c["path"])
        elif c["type"] == "files_exist":
            paths.extend(c["paths"])
    return sorted(p for p in set(paths) if not CV.sensitive_path(p))


# ------------------------------------------------------------- containment

def resolve_in_project(project: Path, raw: str) -> Path:
    """Resolve a validated relative path; reject symlink escapes."""
    root = os.path.realpath(project)
    target = os.path.realpath(os.path.join(root, raw))
    if os.path.commonpath([root, target]) != root:
        raise PathRejected(f"{raw} points outside the project folder")
    if CV.sensitive_path(raw) or CV.sensitive_path(os.path.relpath(target, root)):
        raise PathRejected("Sensitive configured or resolved file excluded")
    return Path(target)


def _read_bounded(p: Path, limit: int = MAX_FILE_BYTES) -> bytes:
    size = p.stat().st_size
    if size > limit:
        raise OverflowError(f"{size} bytes is over the {limit // 1024} KB check limit")
    with open(p, "rb") as fh:
        data = fh.read(limit + 1)
    if len(data) > limit:
        raise OverflowError("file grew past the check limit while reading")
    return data


def _load_file(project: Path, raw: str, kind: str):
    """Return (bytes, None) or (None, CheckResult)."""
    if CV.sensitive_path(raw):
        return None, CheckResult(kind, UNKNOWN, "Sensitive file excluded from checks/evidence.")
    try:
        p = resolve_in_project(project, raw)
    except PathRejected as exc:
        return None, CheckResult(kind, UNKNOWN, f"{exc}; fix the setup.", [raw])
    if not p.exists():
        return None, CheckResult(kind, FAIL, f"{raw} is missing.", [raw])
    if not p.is_file():
        return None, CheckResult(kind, FAIL, f"{raw} is not a file.", [raw])
    try:
        return _read_bounded(p), None
    except OverflowError as exc:
        return None, CheckResult(kind, UNKNOWN, f"{raw} is too large to check ({exc}).", [raw])
    except OSError as exc:
        return None, CheckResult(kind, UNKNOWN, f"{raw} could not be read: {exc.strerror or exc}.", [raw])


# ------------------------------------------------------------- the checks

def _check_file_opens(c: dict, project: Path, deadline: float) -> CheckResult:
    raw = c["path"]
    data, err = _load_file(project, raw, "file_opens")
    if err:
        return err
    if not data.strip():
        return CheckResult("file_opens", FAIL, f"{raw} is empty.", [raw])
    suffix = Path(raw).suffix.lower()
    try:
        if suffix == ".json":
            json.loads(data.decode("utf-8"))
            detail = f"{raw} parses as JSON."
        elif suffix == ".csv":
            rows = list(csv.reader(data.decode("utf-8").splitlines()))
            if not rows:
                return CheckResult("file_opens", FAIL, f"{raw} has no rows.", [raw])
            detail = f"{raw} parses as CSV with {len(rows)} row(s)."
        elif suffix == ".py":
            compile(data, raw, "exec", dont_inherit=True)
            detail = f"{raw} has no Python syntax errors."
        elif suffix in (".html", ".htm"):
            text = data.decode("utf-8", errors="replace").lower()
            if "<html" not in text and "<!doctype" not in text and "<body" not in text:
                return CheckResult("file_opens", FAIL, f"{raw} no longer has HTML page markers.", [raw])
            detail = f"{raw} still has HTML page markers (not a browser render)."
        else:
            data.decode("utf-8")
            detail = f"{raw} is non-empty UTF-8 text."
    except Exception as exc:  # broken content is a FAIL, not a crash
        return CheckResult("file_opens", FAIL, f"{raw} no longer parses: {type(exc).__name__}.", [raw])
    return CheckResult("file_opens", PASS, detail, [raw])


def _check_text_present(c: dict, project: Path, deadline: float) -> CheckResult:
    raw, needle = c["path"], c["text"]
    data, err = _load_file(project, raw, "text_present")
    if err:
        return err
    try:
        hay = data.decode("utf-8")
    except UnicodeDecodeError:
        return CheckResult("text_present", UNKNOWN, "Not complete UTF-8 text; no presence evidence.", [raw])
    if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in hay):
        return CheckResult("text_present", UNKNOWN, "Binary file; no presence evidence.", [raw])
    found = needle.lower() in hay.lower() if c.get("case_insensitive") else needle in hay
    obs = CV.observation(c, data, found)
    if found:
        return CheckResult("text_present", PASS, CV.redact(f"“{needle}” is in {raw} (anywhere in the file, including hidden markup)."), [raw], obs)
    return CheckResult("text_present", FAIL, CV.redact(f"“{needle}” is no longer in {raw}."), [raw], obs)


def _check_files_exist(c: dict, project: Path, deadline: float) -> CheckResult:
    missing, rejected = [], []
    for raw in c["paths"]:
        try:
            if not resolve_in_project(project, raw).is_file():
                missing.append(raw)
        except PathRejected:
            rejected.append(raw)
    if rejected:
        return CheckResult("files_exist", UNKNOWN, "Outside the project folder: " + ", ".join(rejected), list(c["paths"]))
    if missing:
        return CheckResult("files_exist", FAIL, "Missing: " + ", ".join(missing), list(c["paths"]))
    return CheckResult("files_exist", PASS, f"All {len(c['paths'])} important file(s) exist.", list(c["paths"]))


# Addresses that are never fetched, on the first request and every redirect hop.
# Loopback stays allowed: checking a server on this computer is the point.
# Other private ranges need the user-only allow_private_urls plugin setting.
_LINK_LOCAL_V4 = ipaddress.ip_network("169.254.0.0/16")
_PRIVATE_V4 = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
_ULA_V6 = ipaddress.ip_network("fc00::/7")
_METADATA_V4 = ipaddress.ip_address("169.254.169.254")
_METADATA_V6 = ipaddress.ip_address("fd00:ec2::254")
_PRIVATE_SETTING = "allow_private_urls"
_PRIVATE_GETTER = None


class _AddressRefused(urllib.error.URLError):
    """The address must not be fetched. reason is a short category, not page content."""


class _PolicyError(OSError):
    """Raised from a socket connect when the peer is not the validated address."""


def set_private_url_config_getter(getter) -> None:
    """Point url checks at Hermes' plugin settings. None uses the config file."""
    global _PRIVATE_GETTER
    _PRIVATE_GETTER = getter


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().strip("\"'").lower() in {"1", "true", "yes", "on"}
    if type(value) is int:
        return value == 1
    return False


def _yaml_plugin_bool(text: str, plugin: str, key: str) -> bool:
    """True only when plugins.entries.<plugin>.settings.<key> is a true scalar.

    Anything ambiguous (tabs, flow style, a different plugin) stays false.
    """
    wanted = ("plugins", "entries", plugin, "settings", key)
    stack: list[tuple[int, str]] = []
    found = False
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent_text = raw_line[:len(raw_line) - len(raw_line.lstrip(" \t"))]
        if "\t" in indent_text:
            return False
        indent = len(indent_text)
        line = raw_line.strip()
        if line.startswith("- "):
            continue
        if ":" not in line:
            continue
        name, _, rest = line.partition(":")
        name = name.strip().strip("\"'")
        if not name or any(ch in name for ch in " {}[],"):
            continue
        rest = rest.strip()
        if rest and not rest.startswith(("'", '"', "|", ">")):
            rest = rest.split(" #", 1)[0].strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        path = tuple(item for _, item in stack) + (name,)
        scalar = rest not in ("", "|", ">", "|-", ">-", "|+", ">+")
        if path == wanted and scalar:
            found = _as_bool(rest)
            continue
        # One-line form: settings: {allow_private_urls: true}
        if (path == wanted[:-1] and rest.startswith("{") and rest.endswith("}")):
            for part in rest[1:-1].split(","):
                if ":" not in part:
                    continue
                item_key, _, item_value = part.partition(":")
                if item_key.strip().strip("\"'") == key:
                    found = _as_bool(item_value.strip())
            continue
        if not scalar:
            stack.append((indent, name))
    return found


def private_urls_allowed() -> bool:
    """User opt-in for private-network page checks. Default off. Fail closed."""
    getter = _PRIVATE_GETTER
    if getter is not None:
        try:
            return _as_bool(getter())
        except Exception:
            return False
    try:
        from . import tools as plugin_tools
    except ImportError:
        import tools as plugin_tools  # type: ignore
    try:
        home = plugin_tools.hermes_home()
    except Exception:
        return False
    for name in ("config.yaml", "config.yml"):
        path = Path(home) / name
        try:
            if not path.is_file():
                continue
            if path.stat().st_size > 2 * 1024 * 1024:
                return False
            return _yaml_plugin_bool(path.read_text(encoding="utf-8-sig"), "lastgood", _PRIVATE_SETTING)
        except OSError:
            return False
    return False


def _canonical_ip(ip):
    """Unwrap IPv4-mapped IPv6 (::ffff:169.254.169.254 is the IPv4 metadata address)."""
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return mapped
    return ip


def _block_reason(ip, allow_private: bool) -> str | None:
    """Why this one address must not be fetched, or None when it may."""
    ip = _canonical_ip(ip)
    if ip.is_unspecified:
        return "unspecified address"
    if ip == _METADATA_V4 or ip == _METADATA_V6:
        return "link-local or cloud-metadata address"
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in _LINK_LOCAL_V4 or ip.is_link_local:
            return "link-local or cloud-metadata address"
    elif ip.is_link_local:
        return "link-local or cloud-metadata address"
    if ip.is_loopback:
        return None
    private = any(ip in net for net in _PRIVATE_V4) if isinstance(ip, ipaddress.IPv4Address) else ip in _ULA_V6
    if private and not allow_private:
        return "private-network address"
    return None


def _blocked_reason(ips, allow_private: bool) -> str | None:
    """Refuse the host when any A/AAAA result is blocked (not only the first)."""
    reasons = [reason for reason in (_block_reason(ip, allow_private) for ip in ips) if reason]
    if not reasons:
        return None
    for kind in ("unspecified address", "link-local or cloud-metadata address", "private-network address"):
        if kind in reasons:
            return kind
    return reasons[0]


def _addresses_for(host: str, port: int):
    """Every stream address for host, each looked up once and unwrapped."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise urllib.error.URLError(exc) from exc
    found = []
    seen = set()
    for info in infos:
        raw = str(info[4][0]).split("%", 1)[0]
        try:
            ip = _canonical_ip(ipaddress.ip_address(raw))
        except ValueError as exc:
            raise _AddressRefused("unrecognised address") from exc
        if ip in seen:
            continue
        seen.add(ip)
        found.append(ip)
    if not found:
        raise urllib.error.URLError("host did not resolve")
    return found


def _refusal_detail(shown: str, reason: str) -> str:
    if reason == "private-network address":
        return (f"{shown} was refused (private-network address). "
                "Private ranges stay off unless you turn on allow_private_urls "
                "in LastGood's plugin settings. Nothing was fetched.")
    return (f"{shown} was refused ({reason}). "
            "Link-local and cloud-metadata addresses are never fetched.")


def _policy_text(exc) -> str | None:
    reason = getattr(exc, "reason", None)
    if isinstance(exc, _AddressRefused):
        return str(exc.reason)
    if isinstance(reason, _AddressRefused):
        return str(reason.reason)
    if isinstance(reason, _PolicyError):
        return str(reason)
    return None


def _pinned_connection(pin: str, allow_private: bool, https: bool):
    """HTTP(S) connection that dials the IP already validated, not the name again."""
    base = http.client.HTTPSConnection if https else http.client.HTTPConnection

    class _Conn(base):
        def connect(self):
            if self._tunnel_host:
                raise _PolicyError("proxy tunnels are not used for url checks")
            self.sock = socket.create_connection((pin, self.port), self.timeout, self.source_address)
            try:
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError as exc:
                if exc.errno != errno.ENOPROTOOPT:
                    raise
            try:
                peer = _canonical_ip(ipaddress.ip_address(str(self.sock.getpeername()[0]).split("%", 1)[0]))
                pin_ip = _canonical_ip(ipaddress.ip_address(pin))
            except ValueError as exc:
                self.sock.close()
                self.sock = None
                raise _PolicyError("connected address was not an IP address") from exc
            if peer != pin_ip:
                self.sock.close()
                self.sock = None
                raise _PolicyError("connected address did not match the validated address")
            reason = _block_reason(peer, allow_private)
            if reason:
                self.sock.close()
                self.sock = None
                raise _PolicyError(reason)
            if https:
                # server_hostname is the name the user typed (or the IP literal).
                # None is rejected when certificate checking is on, including for
                # https://127.0.0.1/. The TCP peer is still the pinned address.
                self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)

    return _Conn


def _open_pinned(handler, req, https: bool):
    if req.has_proxy():
        raise _AddressRefused("proxies are not used for url checks")
    parts = urllib.parse.urlsplit(req.full_url)
    if parts.scheme not in ("http", "https"):
        raise _AddressRefused("only an http(s) address is fetched")
    if parts.username or parts.password:
        raise _AddressRefused("url must not contain a username or password")
    host = parts.hostname
    if not host:
        raise _AddressRefused("url has no host")
    port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
    allow_private = private_urls_allowed()
    ips = _addresses_for(host, port)
    blocked = _blocked_reason(ips, allow_private)
    if blocked:
        raise _AddressRefused(blocked)
    last = None
    for ip in ips:
        conn_cls = _pinned_connection(str(ip), allow_private, https)
        try:
            kwargs = {"context": handler._context} if https else {}
            return handler.do_open(conn_cls, req, **kwargs)
        except _AddressRefused:
            raise
        except urllib.error.URLError as exc:
            policy = _policy_text(exc)
            if policy:
                raise _AddressRefused(policy) from exc
            last = exc
    if last is not None:
        raise last
    raise urllib.error.URLError("host did not resolve")


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return _open_pinned(self, req, False)


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return _open_pinned(self, req, True)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urllib.parse.urlsplit(newurl)
        if parts.scheme not in ("http", "https"):
            raise _AddressRefused("redirect to a non-http(s) address was refused")
        if parts.username or parts.password:
            raise _AddressRefused("redirect containing a username or password was refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

    def http_error_302(self, req, fp, code, msg, headers):
        # Checked again when the next hop is opened. This stops file/ftp redirects
        # before urllib turns them into a fetch of a different scheme.
        newurl = headers.get("location") or headers.get("uri") or ""
        parts = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl))
        if newurl and parts.scheme not in ("http", "https"):
            try:
                fp.read()
                fp.close()
            except Exception:
                pass
            raise _AddressRefused("redirect to a non-http(s) address was refused")
        if parts.username or parts.password:
            try:
                fp.read()
                fp.close()
            except Exception:
                pass
            raise _AddressRefused("redirect containing a username or password was refused")
        return super().http_error_302(req, fp, code, msg, headers)


_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    _SafeRedirect(),
    _PinnedHTTPHandler(),
    _PinnedHTTPSHandler(),
)


def redact_url(url: str) -> str:
    """Drop userinfo, query and fragment values from any displayed/stored URL."""
    try:
        p = urllib.parse.urlsplit(url)
        host = p.hostname or ""
        if p.port:
            host = f"{host}:{p.port}"
        tail = "?[redacted]" if p.query else ""
        tail += "#[redacted]" if p.fragment else ""
        return f"{p.scheme}://{host}{p.path}{tail}"
    except Exception:
        return "[url redacted]"


def _check_url_loads(c: dict, project: Path, deadline: float) -> CheckResult:
    url, needle = c["url"], c.get("text")
    shown = redact_url(url)
    last = CheckResult("url_loads", UNKNOWN, f"{shown} was not tried (time budget used up).")
    for _attempt in range(2):
        remaining = deadline - time.monotonic()
        if remaining < 0.2:
            break
        timeout = max(0.1, min(c.get("timeout", URL_TIMEOUT_CAP), URL_TIMEOUT_CAP, remaining))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LastGood/0.4.2"})
            with _OPENER.open(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                body = resp.read(MAX_URL_BODY_BYTES + 1) if needle else b""
            if not 200 <= status < 400:
                return CheckResult("url_loads", FAIL, f"{shown} answered with status {status}.")
            truncated = len(body) > MAX_URL_BODY_BYTES
            body = body[:MAX_URL_BODY_BYTES]
            if needle and needle not in body.decode("utf-8", errors="replace"):
                if truncated:
                    return CheckResult("url_loads", UNKNOWN, f"{shown} page is larger than the 1 MB check limit; “{needle}” was not in the part read.")
                return CheckResult("url_loads", FAIL, f"{shown} loads but “{needle}” is not on the page.")
            extra = f" and contains “{needle}”" if needle else ""
            return CheckResult("url_loads", PASS, f"{shown} loads (status {status}){extra}.")
        except _AddressRefused as exc:
            return CheckResult("url_loads", UNKNOWN, _refusal_detail(shown, str(exc.reason)))
        except urllib.error.HTTPError as exc:  # the server answered: a real result
            code = exc.code
            exc.close()
            return CheckResult("url_loads", FAIL, f"{shown} answered with status {code}.")
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            policy = _policy_text(exc)
            if policy:
                return CheckResult("url_loads", UNKNOWN, _refusal_detail(shown, policy))
            reason = getattr(exc, "reason", exc)
            last = CheckResult("url_loads", UNKNOWN, f"{shown} could not be reached ({type(reason).__name__}); not counted as broken content.")
        except Exception as exc:
            last = CheckResult("url_loads", UNKNOWN, f"{shown} check errored ({type(exc).__name__}).")
    return last


_RUNNERS = {
    "file_opens": _check_file_opens,
    "text_present": _check_text_present,
    "files_exist": _check_files_exist,
    "url_loads": _check_url_loads,
}


def run_checks(checks: list[dict], project: Path, deadline: float) -> list[CheckResult]:
    """Run validated checks; never raises. Out-of-time checks are UNKNOWN."""
    results = []
    for c in checks:
        if time.monotonic() >= deadline:
            results.append(CheckResult(c.get("type", "?"), UNKNOWN, "Not run: time budget used up."))
            continue
        try:
            results.append(_RUNNERS[c["type"]](c, Path(project), deadline))
        except Exception as exc:
            results.append(CheckResult(str(c.get("type")), UNKNOWN, f"Check errored ({type(exc).__name__})."))
    return results


def overall(results: list[CheckResult]) -> str:
    if not results:
        return UNKNOWN
    if any(r.result == FAIL for r in results):
        return FAIL
    if any(r.result == UNKNOWN for r in results):
        return UNKNOWN
    return PASS


# ------------------------------------------------------------- project root guard

# Folders directly in a home that hold many unrelated things (case-insensitive).
# OneDrive covers personal "OneDrive" and work/school "OneDrive - <Org>".
_BROAD_CHILD = (r"(desktop|documents|downloads|appdata|"
                r"onedrive(?: - [^/]+)?(?:/(?:desktop|documents|downloads))?)")
_POSIX_SYSTEM = {"/", "/tmp", "/home", "/users", "/root", "/usr", "/etc", "/var", "/bin", "/sbin",
                 "/lib", "/opt", "/mnt", "/media", "/srv", "/proc", "/sys", "/dev", "/boot",
                 "/private", "/system", "/applications", "/library", "/volumes"}
_WINDOWS_SYSTEM = ("users", "windows", "program files", "program files (x86)", "programdata",
                   "users/public")


def _norm(path: str) -> tuple[str, str]:
    """('win'|'posix', normalised lowercase-for-win path without trailing slash)."""
    raw = str(path)
    # Windows extended-length prefixes: \\?\UNC\server\share -> \\server\share, \\?\C:\ -> C:\
    if raw[:8].upper() in ("\\\\?\\UNC\\", "//?/UNC/"):
        raw = "\\\\" + raw[8:]
    elif raw[:4] in ("\\\\?\\", "//?/"):
        raw = raw[4:]
    if re.match(r"^[A-Za-z]:([\\/]|$)", raw) or raw.startswith("\\\\"):
        w = PureWindowsPath(raw)
        anchor = w.anchor.replace("\\", "/").rstrip("/").lower()
        rest = "/".join(part.lower() for part in w.parts[1:])
        return "win", (anchor + "/" + rest) if rest else anchor + "/"
    p = "/" + "/".join(x for x in raw.replace("\\", "/").split("/") if x and x != ".")
    return "posix", p


def broad_root_reason(project, homes=None) -> str | None:
    """Plain-English reason why ``project`` is too broad to be one project, else None.

    Refuses filesystem/drive roots, the user's home folder (and its parent), the
    Desktop/Documents/Downloads/OneDrive folders directly in it, and system folders.
    Works on Windows-style and POSIX-style paths regardless of the host OS.
    """
    shown = str(project)
    flavour, target = _norm(shown)
    if homes is None:
        homes = [str(Path.home())] + [os.environ.get(k, "") for k in ("HOME", "USERPROFILE")]
        homes = [h for h in homes if h] + [os.path.realpath(h) for h in homes if h]
    for h in homes:
        hf, home = _norm(h)
        if hf != flavour or home in ("/", "") or re.fullmatch(r"[a-z]:/", home):
            continue
        if target == home:
            return f"{shown} is your home folder"
        if target == home.rsplit("/", 1)[0] or (hf == "win" and target == home.rsplit("/", 1)[0] + "/"):
            return f"{shown} is the folder that holds every user's home folder"
        if target.lower().startswith(home.lower() + "/"):
            m = re.fullmatch(_BROAD_CHILD, target[len(home) + 1:], re.I)
            if m:
                return f"{shown} is a shared personal folder ({m.group(1).split('/')[-1]}), not one project"
    if flavour == "win":
        if re.fullmatch(r"[a-z]:/", target) or target.startswith("//") and target.rstrip("/").count("/") <= 3:
            return f"{shown} is a drive root"
        rel = target.split("/", 1)[1] if "/" in target else ""
        if rel in _WINDOWS_SYSTEM:
            return f"{shown} is a system folder"
        if re.fullmatch(r"users/[^/]+", rel):
            return f"{shown} is a user's home folder"
        m = re.fullmatch(r"users/[^/]+/" + _BROAD_CHILD, rel, re.I)
        if m:
            return f"{shown} is a shared personal folder ({m.group(1).split('/')[-1]}), not one project"
        return None
    if target == "/":
        return f"{shown} is the filesystem root"
    if target.lower() in _POSIX_SYSTEM:
        return f"{shown} is a system folder"
    if re.fullmatch(r"/(home|Users)/[^/]+", target):
        return f"{shown} is a user's home folder"
    m = re.fullmatch(r"/(?:home|Users)/[^/]+/" + _BROAD_CHILD, target, re.I)
    if m:
        return f"{shown} is a shared personal folder ({m.group(1).split('/')[-1]}), not one project"
    # WSL view of Windows drives: /mnt/c, /mnt/c/Users, /mnt/c/Users/<name>[/Desktop...]
    m = re.fullmatch(r"/mnt/[a-zA-Z](/.*)?", target)
    if m:
        win = "c:" + (m.group(1) or "/")
        inner = broad_root_reason(PureWindowsPath(win.replace("/", "\\")), homes=[])
        if inner:
            return inner.replace(str(PureWindowsPath(win.replace("/", "\\"))), shown)
    return None


def broad_root_message(reason: str) -> str:
    return f"LastGood refused to check here: {reason}, which is too broad to be one project. {BROAD_ROOT_HELP}"


# ------------------------------------------------------------- config + identity

_MAIN_FILE_CANDIDATES = ("index.html", "README.md", "main.py", "app.py", "index.md")


def default_checks(project: Path) -> list[dict] | None:
    """Zero-setup default: the main file still opens."""
    for name in _MAIN_FILE_CANDIDATES:
        try:
            if resolve_in_project(project, name).is_file():
                return [{"type": "file_opens", "path": name}]
        except PathRejected:
            continue
    return None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_project_config(project: Path) -> dict:
    """Read <project>/lastgood-config.json.

    Returns {"checks": list|None, "source": "project"|"default"|"none",
             "config_hash": str, "error": str|None}
    """
    reason = broad_root_reason(project)
    if reason:
        return {"checks": None, "source": "too_broad", "config_hash": "too_broad",
                "error": broad_root_message(reason)}
    try:
        cfg_path = resolve_in_project(project, CONFIG_NAME)
    except PathRejected:
        return {"checks": None, "source": "project", "config_hash": "rejected",
                "error": f"{CONFIG_NAME} points outside the project folder"}
    if not cfg_path.exists():
        checks = default_checks(project)
        canon = json.dumps(checks, sort_keys=True).encode()
        if checks is None:
            return {"checks": None, "source": "none", "config_hash": _sha(canon),
                    "error": f"no {CONFIG_NAME} and no main file to check. {CONFIG_HELP}"}
        return {"checks": checks, "source": "default", "config_hash": _sha(canon), "error": None}
    try:
        raw = _read_bounded(cfg_path, MAX_CONFIG_BYTES)
    except (OverflowError, OSError) as exc:
        return {"checks": None, "source": "project", "config_hash": "unreadable",
                "error": f"{CONFIG_NAME} could not be read ({type(exc).__name__})"}
    h = _sha(raw)
    try:
        checks = validate_config(json.loads(raw.decode("utf-8")))
    except (ConfigError, ValueError) as exc:
        return {"checks": None, "source": "project", "config_hash": h,
                "error": f"{CONFIG_NAME} is not valid: {exc}. {CONFIG_HELP}"}
    return {"checks": checks, "source": "project", "config_hash": h, "error": None}


def fingerprint(project: Path, paths: list[str]) -> str:
    """Content fingerprint of the checked files (sha256 of each, in order)."""
    h = hashlib.sha256()
    for raw in sorted(set(paths)):
        h.update(raw.encode() + b"\0")
        try:
            p = resolve_in_project(project, raw)
            if not p.is_file():
                h.update(b"missing")
            else:
                st = p.stat()
                if st.st_size > MAX_FILE_BYTES:
                    h.update(f"large:{st.st_size}:{st.st_mtime_ns}".encode())
                else:
                    h.update(_sha(_read_bounded(p)).encode())
        except PathRejected:
            h.update(b"rejected")
        except (OSError, OverflowError):
            h.update(b"unreadable")
        h.update(b"\n")
    return h.hexdigest()
