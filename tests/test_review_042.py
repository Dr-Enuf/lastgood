"""v0.4.2 catalog-review regressions.

Address checks use literal IPs and a local loopback server only. Non-loopback
dials are intercepted and never leave the machine. No metadata endpoint is contacted.
"""
import ipaddress
import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from test_lastgood import ROOT, Base, C, lastgood, tools
from lastgood import changeview as CV
from lastgood import schemas

PHRASE = "fetches the http(s) address you configure (link-local/metadata refused)"
SECRET = "synthetic-hermes-control-secret"


class _PolicyBase(Base):
    def setUp(self):
        super().setUp()
        self._saved_home = os.environ.get("HERMES_HOME")
        self._saved_getter = C._PRIVATE_GETTER
        self.addCleanup(self._restore_policy)
        self.hermes = self.tmp / "hermes-home"
        self.hermes.mkdir()
        os.environ["HERMES_HOME"] = str(self.hermes)
        C.set_private_url_config_getter(None)
        self.seen = []
        real = socket.create_connection

        def spy(address, *args, **kwargs):
            raw = str(address[0])
            try:
                ip = ipaddress.ip_address(raw.split("%", 1)[0])
            except ValueError as exc:
                raise AssertionError(f"dialed a hostname instead of a validated IP: {raw}") from exc
            self.seen.append(ip)
            if not ip.is_loopback:
                # Prove the dial was attempted, but do not send the packet.
                raise TimeoutError(f"test refused a non-loopback dial to {ip}")
            return real(address, *args, **kwargs)

        patcher = patch("lastgood.checks.socket.create_connection", spy)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _restore_policy(self):
        C.set_private_url_config_getter(self._saved_getter)
        if self._saved_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = self._saved_home

    def write_setting(self, enabled, flow=False):
        if flow:
            body = (
                "plugins:\n"
                "  entries:\n"
                "    lastgood:\n"
                f"      settings: {{allow_private_urls: {'true' if enabled else 'false'}}}\n"
            )
        else:
            body = (
                "plugins:\n"
                "  enabled:\n"
                "    - lastgood\n"
                "  entries:\n"
                "    other:\n"
                "      settings:\n"
                "        allow_private_urls: true\n"
                "    lastgood:\n"
                "      enabled: true\n"
                "      settings:\n"
                "        # comment must not count\n"
                f"        allow_private_urls: {'true' if enabled else 'false'}\n"
            )
        (self.hermes / "config.yaml").write_text(body, encoding="utf-8")

    def fetch(self, url, text=None):
        check = {"type": "url_loads", "url": url, "timeout": 2}
        if text is not None:
            check["text"] = text
        return C.run_checks([check], self.project, time.monotonic() + 8)[0]

    def assert_refused(self, url, reason):
        before = len(self.seen)
        result = self.fetch(url)
        self.assertEqual(result.result, "UNKNOWN", result.detail)
        self.assertIn("refused", result.detail)
        self.assertIn(reason, result.detail)
        self.assertEqual(self.seen[before:], [], result.detail)
        self.assertNotIn(SECRET, result.detail)
        return result

    def serve(self, handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        import threading
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        return f"http://127.0.0.1:{server.server_address[1]}"


class TestAddressPolicy(Base):
    """Classifier boundaries. These do not open sockets."""

    def reason(self, text, allow_private=False):
        return C._block_reason(ipaddress.ip_address(text), allow_private)

    def test_required_addresses_and_mapped_forms(self):
        meta = "link-local or cloud-metadata address"
        for text in ("169.254.169.254", "169.254.0.1", "169.254.255.255",
                     "fe80::1", "febf::1", "fd00:ec2::254",
                     "::ffff:169.254.169.254", "::ffff:169.254.1.1"):
            self.assertEqual(self.reason(text), meta, text)
            self.assertEqual(self.reason(text, allow_private=True), meta, text)
        for text in ("0.0.0.0", "::", "::ffff:0.0.0.0"):
            self.assertEqual(self.reason(text), "unspecified address", text)
            self.assertEqual(self.reason(text, allow_private=True), "unspecified address", text)
        for text in ("127.0.0.1", "127.0.0.2", "::1", "::ffff:127.0.0.1"):
            self.assertIsNone(self.reason(text), text)

    def test_private_ranges_need_opt_in_and_edges_stay_public(self):
        private = ("10.0.0.0", "10.255.255.255", "172.16.0.0", "172.31.255.255",
                   "192.168.0.0", "192.168.255.255", "fc00::", "fdff::1",
                   "::ffff:10.1.2.3", "::ffff:192.168.0.1")
        for text in private:
            self.assertEqual(self.reason(text), "private-network address", text)
            self.assertIsNone(self.reason(text, allow_private=True), text)
        # fd00:ec2::254 is inside fc00::/7 and stays refused when private is on.
        self.assertEqual(self.reason("fd00:ec2::254", allow_private=True),
                         "link-local or cloud-metadata address")
        for text in ("172.15.255.255", "172.32.0.0", "192.167.255.255", "192.169.0.0",
                     "11.0.0.1", "8.8.8.8", "fe00::1"):
            self.assertIsNone(self.reason(text), text)


class TestUrlFetchGuards(_PolicyBase):
    def test_metadata_link_local_unspecified_and_mapped_are_not_dialed(self):
        cases = (
            ("http://169.254.169.254/latest/meta-data/", "link-local or cloud-metadata address"),
            ("http://169.254.1.1/", "link-local or cloud-metadata address"),
            ("http://[fe80::1]/", "link-local or cloud-metadata address"),
            ("http://[fd00:ec2::254]/", "link-local or cloud-metadata address"),
            ("http://0.0.0.0/", "unspecified address"),
            ("http://[::]/", "unspecified address"),
            ("http://[::ffff:169.254.169.254]/", "link-local or cloud-metadata address"),
            ("http://[::ffff:0.0.0.0]/", "unspecified address"),
            ("http://[::ffff:169.254.1.1]/latest/", "link-local or cloud-metadata address"),
        )
        for url, reason in cases:
            self.assert_refused(url, reason)

    def test_private_literals_and_names_refused_until_user_opts_in(self):
        for url in ("http://10.1.2.3/", "http://172.16.5.5/", "http://192.168.1.20/",
                    "http://[fc00::1]/", "http://[fd12:3456::9]/", "http://[::ffff:10.9.8.7]/"):
            self.assert_refused(url, "private-network address")
        real = socket.getaddrinfo

        def fake(host, port, *args, **kwargs):
            if host == "lan.example":
                return real("192.168.1.20", port, *args, **kwargs)
            return real(host, port, *args, **kwargs)

        with patch("lastgood.checks.socket.getaddrinfo", fake):
            self.assert_refused("http://lan.example/secret", "private-network address")
        self.write_setting(True)
        self.assertTrue(C.private_urls_allowed())
        self.seen.clear()
        allowed = self.fetch("http://10.1.2.3/")
        self.assertNotIn("refused", allowed.detail)
        self.assertIn("could not be reached", allowed.detail)
        self.assertTrue(self.seen)
        self.assertTrue(all(ip == ipaddress.ip_address("10.1.2.3") for ip in self.seen))
        # Opt-in does not unlock metadata, link-local, or unspecified.
        self.assert_refused("http://169.254.169.254/", "link-local or cloud-metadata address")
        self.assert_refused("http://[fe80::1]/", "link-local or cloud-metadata address")
        self.assert_refused("http://[fd00:ec2::254]/", "link-local or cloud-metadata address")
        self.assert_refused("http://0.0.0.0/", "unspecified address")
        self.assert_refused("http://[::]/", "unspecified address")
        with patch("lastgood.checks.socket.getaddrinfo", fake):
            self.seen.clear()
            named = self.fetch("http://lan.example/")
            self.assertNotIn("refused", named.detail)
            self.assertIn(ipaddress.ip_address("192.168.1.20"), self.seen)

    def test_any_blocked_address_refuses_the_whole_name(self):
        real = socket.getaddrinfo

        def fake(host, port, *args, **kwargs):
            if host == "mixed.example":
                return (real("203.0.113.5", port, *args, **kwargs)
                        + real("169.254.169.254", port, *args, **kwargs)
                        + real("::ffff:169.254.169.254", port, *args, **kwargs))
            return real(host, port, *args, **kwargs)

        with patch("lastgood.checks.socket.getaddrinfo", fake):
            self.assert_refused("http://mixed.example/", "link-local or cloud-metadata address")

    def test_loopback_still_allowed_including_mapped_v4(self):
        class Page(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"Bakery loopback"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        base = self.serve(Page)
        port = base.rsplit(":", 1)[1]
        self.seen.clear()
        ok = self.fetch(base + "/", text="Bakery")
        self.assertEqual(ok.result, "PASS", ok.detail)
        self.assertEqual(self.seen, [ipaddress.ip_address("127.0.0.1")])
        mapped = self.fetch(f"http://[::ffff:127.0.0.1]:{port}/", text="Bakery")
        self.assertEqual(mapped.result, "PASS", mapped.detail)
        self.assertTrue(all(ip.is_loopback for ip in self.seen))

    def test_ipv6_loopback_still_allowed_when_the_stack_has_it(self):
        try:
            probe = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            probe.bind(("::1", 0))
        except OSError as exc:
            self.skipTest(f"::1 is not available ({exc})")
        port = probe.getsockname()[1]
        probe.close()

        class Page(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"Bakery v6"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        class V6Server(ThreadingHTTPServer):
            address_family = socket.AF_INET6

        server = V6Server(("::1", port), Page)
        import threading
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        self.seen.clear()
        result = self.fetch(f"http://[::1]:{port}/", text="Bakery")
        self.assertEqual(result.result, "PASS", result.detail)
        self.assertIn(ipaddress.ip_address("::1"), self.seen)

    def test_redirect_from_loopback_to_metadata_is_refused(self):
        class Jump(BaseHTTPRequestHandler):
            def do_GET(self):
                target = self.path.split("target=", 1)[-1]
                self.send_response(302)
                self.send_header("Location", target)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        base = self.serve(Jump)
        hops = (
            "http://169.254.169.254/latest/meta-data/",
            "http://[::ffff:169.254.169.254]/latest/meta-data/",
            "http://[fd00:ec2::254]/",
            "http://[fe80::1]/",
            "http://0.0.0.0/",
            "http://10.1.2.3/secret",
            "file:///etc/passwd",
        )
        for target in hops:
            self.seen.clear()
            result = self.fetch(base + "/jump?target=" + target)
            self.assertEqual(result.result, "UNKNOWN", result.detail)
            self.assertIn("refused", result.detail)
            self.assertTrue(all(ip.is_loopback for ip in self.seen), (target, self.seen, result.detail))
            self.assertNotIn("root:", result.detail)

    def test_redirect_staying_on_loopback_still_passes(self):
        class Jump(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/jump"):
                    self.send_response(302)
                    self.send_header("Location", "/done")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                body = b"Bakery after redirect"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        base = self.serve(Jump)
        self.seen.clear()
        result = self.fetch(base + "/jump", text="Bakery")
        self.assertEqual(result.result, "PASS", result.detail)
        self.assertGreaterEqual(len(self.seen), 2)
        self.assertTrue(all(ip.is_loopback for ip in self.seen))

    def test_dns_rebind_connects_to_the_address_that_was_checked(self):
        calls = {"n": 0}
        real = socket.getaddrinfo

        def fake(host, port, *args, **kwargs):
            if host == "rebind.example":
                calls["n"] += 1
                if calls["n"] == 1:
                    return real("127.0.0.1", port, *args, **kwargs)
                return real("169.254.169.254", port, *args, **kwargs)
            return real(host, port, *args, **kwargs)

        class Page(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"Bakery pinned"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        base = self.serve(Page)
        port = base.rsplit(":", 1)[1]
        with patch("lastgood.checks.socket.getaddrinfo", fake):
            self.seen.clear()
            result = self.fetch(f"http://rebind.example:{port}/", text="Bakery")
        self.assertEqual(result.result, "PASS", result.detail)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self.seen, [ipaddress.ip_address("127.0.0.1")])

    def test_https_loopback_uses_the_validated_ip(self):
        import shutil
        import ssl
        import subprocess
        import tempfile
        if shutil.which("openssl") is None:
            self.skipTest("openssl is not available to mint a local test certificate")
        work = tempfile.mkdtemp(dir=self.tmp)
        cert = str(Path(work) / "cert.pem")
        key = str(Path(work) / "key.pem")
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", key, "-out", cert,
             "-days", "1", "-nodes", "-subj", "/CN=127.0.0.1"],
            check=True, capture_output=True)

        class Page(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"Bakery https"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        import threading
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        port = server.server_address[1]
        self.seen.clear()
        result = self.fetch(f"https://127.0.0.1:{port}/", text="Bakery")
        # The certificate is not trusted, so this is not a PASS. It must still
        # be a TLS failure after dialing loopback, not a policy refusal or a crash.
        self.assertEqual(result.result, "UNKNOWN", result.detail)
        self.assertNotIn("refused", result.detail)
        self.assertNotIn("errored", result.detail)
        self.assertTrue(self.seen)
        self.assertTrue(all(ip == ipaddress.ip_address("127.0.0.1") for ip in self.seen))

    def test_proxy_env_cannot_steer_the_dial(self):
        class Page(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"Bakery direct"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        base = self.serve(Page)
        saved = {k: os.environ.get(k) for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY")}
        os.environ["http_proxy"] = os.environ["HTTP_PROXY"] = "http://169.254.169.254:80"
        os.environ["https_proxy"] = os.environ["HTTPS_PROXY"] = "http://169.254.169.254:80"
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
                                  for k, v in saved.items()])
        self.seen.clear()
        result = self.fetch(base + "/", text="Bakery")
        self.assertEqual(result.result, "PASS", result.detail)
        self.assertEqual(self.seen, [ipaddress.ip_address("127.0.0.1")])

    def test_project_file_cannot_opt_in_and_plugin_setting_can(self):
        (self.project / "lastgood-config.json").write_text(json.dumps({
            "allow_private_urls": True,
            "checks": [{"type": "url_loads", "url": "http://10.1.2.3/", "timeout": 2}],
        }), encoding="utf-8")
        self.assertFalse(C.private_urls_allowed())
        self.seen.clear()
        out = self.check("probe")
        self.assertEqual(out["result"], "UNKNOWN")
        self.assertIn("private-network", out["checks"][0]["detail"])
        self.assertEqual(self.seen, [])
        # A comment, another plugin, and a root key do not turn the setting on.
        (self.hermes / "config.yaml").write_text(
            "# allow_private_urls: true\n"
            "allow_private_urls: true\n"
            "plugins:\n"
            "  entries:\n"
            "    lastgood:\n"
            "      allow_private_urls: true\n",
            encoding="utf-8")
        self.assertFalse(C.private_urls_allowed())
        self.write_setting(True)
        self.assertTrue(C.private_urls_allowed())
        self.write_setting(True, flow=True)
        self.assertTrue(C.private_urls_allowed())
        self.write_setting(False)
        self.assertFalse(C.private_urls_allowed())
        self.write_setting(True)
        C.set_private_url_config_getter(lambda: False)
        self.assertFalse(C.private_urls_allowed())  # live plugin setting wins over a true file
        C.set_private_url_config_getter(lambda: True)
        self.assertTrue(C.private_urls_allowed())
        C.set_private_url_config_getter(lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        self.assertFalse(C.private_urls_allowed())  # a broken reader stays off; it does not fall through


class TestWhoMayAddUrlLoads(_PolicyBase):
    def test_tool_refuses_url_loads_and_writes_nothing(self):
        cfg = self.project / "lastgood-config.json"
        before = cfg.read_bytes()
        out = json.loads(tools.lastgood_setup({
            "path": str(self.project),
            "allow_private_urls": True,
            "checks": [
                {"type": "file_opens", "path": "index.html"},
                {"type": "url_loads", "url": "http://169.254.169.254/latest/meta-data/"},
            ],
        }))
        self.assertIn("url_loads", out["error"])
        self.assertIn("Nothing was saved", out["error"])
        self.assertNotIn("169.254.169.254", out["error"])
        self.assertEqual(cfg.read_bytes(), before)
        self.assertFalse(C.private_urls_allowed())
        self.assertNotIn("url_loads", schemas.LASTGOOD_SETUP["parameters"]["properties"]["checks"]["items"]["properties"]["type"]["enum"])
        self.assertIn("refuses", schemas.LASTGOOD_SETUP["description"])

    def test_slash_command_can_add_url_loads(self):
        class Page(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"Bakery from slash"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        base = self.serve(Page)
        payload = json.dumps({"checks": [{"type": "url_loads", "url": base + "/", "text": "Bakery", "timeout": 2}]})
        text = lastgood._lastgood_command("setup json " + payload)
        self.assertIn("Saved 1", text)
        saved = json.loads((self.project / "lastgood-config.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["checks"][0]["type"], "url_loads")
        self.seen.clear()
        out = self.check("slash url")
        self.assertEqual(out["result"], "PASS", out)
        self.assertTrue(all(ip.is_loopback for ip in self.seen))

    def test_hand_edited_file_can_add_url_loads(self):
        class Page(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"Bakery by hand"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        base = self.serve(Page)
        (self.project / "lastgood-config.json").write_text(json.dumps(
            {"checks": [{"type": "url_loads", "url": base + "/", "text": "Bakery", "timeout": 2}]}
        ), encoding="utf-8")
        loaded = C.load_project_config(self.project)
        self.assertIsNone(loaded["error"])
        self.assertEqual(loaded["checks"][0]["type"], "url_loads")
        self.seen.clear()
        out = self.check("hand")
        self.assertEqual(out["result"], "PASS", out)


class TestHermesHomeProject(Base):
    def setUp(self):
        super().setUp()
        self._saved_home = os.environ.get("HERMES_HOME")
        self.addCleanup(self._restore)
        self.home = self.tmp / "real-hermes"
        self.home.mkdir()
        os.environ["HERMES_HOME"] = str(self.home)

    def _restore(self):
        if self._saved_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = self._saved_home

    def assert_refused(self, path):
        with self.assertRaises(ValueError) as caught:
            tools.resolve_project(str(path))
        self.assertIn("Hermes home", str(caught.exception))

    def test_home_child_and_symlink_refused_sibling_allowed(self):
        child = self.home / "plugins" / "lastgood"
        child.mkdir(parents=True)
        self.assertEqual(tools.hermes_home(), self.home.resolve())
        self.assert_refused(self.home)
        self.assert_refused(child)
        os.environ["TERMINAL_CWD"] = str(child)
        self.assert_refused_session()
        sibling = self.project
        resolved = tools.resolve_project(str(sibling))
        self.assertEqual(resolved, Path(os.path.realpath(sibling)))
        link = self.tmp / "home-link"
        self.symlink_or_skip(link, self.home)
        os.environ["HERMES_HOME"] = str(link)
        self.assertEqual(tools.hermes_home(), self.home.resolve())
        self.assert_refused(link)
        self.assert_refused(self.home)
        self.assert_refused(child)
        outside = self.tmp / "via-link"
        self.symlink_or_skip(outside, child)
        self.assert_refused(outside)

    def assert_refused_session(self):
        with self.assertRaises(ValueError) as caught:
            tools.resolve_project()
        self.assertIn("Hermes home", str(caught.exception))

    def test_tool_error_names_the_hermes_home(self):
        os.environ["TERMINAL_CWD"] = str(self.home)
        out = json.loads(tools.lastgood_check({"label": "nope"}))
        self.assertIn("Hermes home", out["error"])
        self.assertFalse((self.home / "lastgood-config.json").exists())


class TestSensitiveHermesFiles(Base):
    def test_each_new_control_name_is_refused_by_text_present(self):
        for name in ("auth.json", "auth.lock", "webhook_subscriptions.json", "mcp-tokens",
                     "Auth.JSON", "config/auth.json", "config/webhook_subscriptions.json"):
            path = self.project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(SECRET + "\n", encoding="utf-8")
            self.assertTrue(CV.sensitive_path(name), name)
            result = C.run_checks(
                [{"type": "text_present", "path": name, "text": SECRET}],
                self.project, time.monotonic() + 5)[0]
            self.assertEqual(result.result, "UNKNOWN", name)
            blob = json.dumps(result.to_dict())
            self.assertNotIn(SECRET, blob, name)
            self.assertIsNone(result.observation, name)
        # mcp-tokens as a directory, and as a file already covered above.
        token_dir = self.project / "mcp-tokens"
        if token_dir.is_file():
            token_dir.unlink()
        token_dir.mkdir(exist_ok=True)
        (token_dir / "access.json").write_text(SECRET, encoding="utf-8")
        nested = "mcp-tokens/access.json"
        self.assertTrue(CV.sensitive_path(nested))
        self.assertTrue(CV.sensitive_path("subdir\\mcp-tokens\\token"))
        result = C.run_checks(
            [{"type": "text_present", "path": nested, "text": SECRET}],
            self.project, time.monotonic() + 5)[0]
        self.assertEqual(result.result, "UNKNOWN")
        self.assertNotIn(SECRET, json.dumps(result.to_dict()))


class TestDisclosureAndVersion(Base):
    def test_version_and_disclosure_wording(self):
        manifest = (ROOT / "plugin" / "lastgood" / "plugin.yaml").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        catalog = (ROOT / "CATALOG_ENTRY_DRAFT.yaml").read_text(encoding="utf-8")
        self.assertRegex(manifest, r"(?m)^version: 0\.4\.2$")
        self.assertIn('requires_hermes: ">=0.22.7"', manifest)
        self.assertIn(PHRASE, manifest)
        self.assertIn(PHRASE, readme)
        self.assertIn(PHRASE, catalog)
        self.assertIn('version: "0.4.2"', catalog)
        self.assertNotIn("provides_middleware", manifest)
        for tool in ("lastgood_check", "lastgood_status", "lastgood_blame",
                     "lastgood_report", "lastgood_setup"):
            self.assertIn(tool, manifest)
        self.assertIn("pre_tool_call", manifest)
        self.assertIn("post_tool_call", manifest)
