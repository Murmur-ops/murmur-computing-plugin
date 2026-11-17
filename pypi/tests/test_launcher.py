import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmur_computing import launcher, shim  # noqa: E402

REAL_TOOLS = ["murmur_run_script", "murmur_run_dag", "murmur_job_status",
              "murmur_job_results", "murmur_fleet", "murmur_invite"]


def call(args, python=False, **kw):
    return shim.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "murmur_fleet", "arguments": args}}, python, **kw)


def payload(resp):
    return resp["result"]["structuredContent"]


class Base(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        for p in (mock.patch.dict(os.environ, {"HOME": self.home.name, "USERPROFILE": self.home.name}),
                  mock.patch.object(sys, "platform", "darwin")):
            p.start()
            self.addCleanup(p.stop)
        shim._nonces.clear()

    def fake_murmur(self, name="murmur"):
        d = os.path.join(self.home.name, ".murmur", "bin")
        os.makedirs(d)
        p = os.path.join(d, name)
        open(p, "w").write("#!/bin/sh\n")
        os.chmod(p, 0o755)
        return p


class Installed(Base):
    def test_execv_absolute_path_with_argv(self):
        p = self.fake_murmur()
        with mock.patch("os.execv") as ex, self.assertRaises(SystemExit):  # mock returns; real execv never does
            launcher.main(["--python", "--x"])
        ex.assert_called_once_with(p, [p, "planner", "mcp", "--python", "--x"])

    def test_windows_subprocess_exit_code(self):
        p = self.fake_murmur("murmur.cmd")
        with mock.patch.object(sys, "platform", "win32"), \
                mock.patch("subprocess.call", return_value=7) as sc:
            with self.assertRaises(SystemExit) as e:
                launcher.main(["--python"])
        sc.assert_called_once_with([p, "planner", "mcp", "--python"])
        self.assertEqual(e.exception.code, 7)

    def test_not_found_means_shim(self):
        with mock.patch.object(shim, "serve") as sv:
            launcher.main(["a"])
        self.assertEqual(sv.call_args[0][0], ["a"])


class Shim(Base):
    def test_initialize_and_tools(self):
        r, _ = shim.handle({"id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "murmur-computing")
        self.assertTrue(r["result"]["capabilities"]["tools"]["listChanged"])
        r, _ = shim.handle({"id": 2, "method": "tools/list"})
        self.assertEqual([t["name"] for t in r["result"]["tools"]], REAL_TOOLS)
        r, _ = shim.handle({"id": 2, "method": "tools/list"}, python=True)
        self.assertEqual([t["name"] for t in r["result"]["tools"]], ["murmur_run_python"])

    def test_required_has_nonce(self):
        r, done = call({})
        p = payload(r)
        self.assertFalse(done)
        self.assertEqual(p["error"]["code"], "INSTALL_REQUIRED")
        self.assertTrue(p["install_nonce"])
        self.assertIn("terms.html", p["terms_url"])

    def test_declined(self):
        r, done = call({"accept_install": False})
        self.assertEqual(payload(r)["error"]["code"], "INSTALL_DECLINED")

    def _stubs(self, out='{"ok":true}'):
        ran = []
        fetch = lambda url: (ran.append(url), self._tmp())[1]  # noqa: E731
        return ran, fetch, (lambda path: out)

    def _tmp(self):
        p = os.path.join(self.home.name, "inst.sh")
        open(p, "w").write("x")
        return p

    def test_bad_nonce_refused(self):
        ran, f, r = self._stubs()
        res, done = call({"accept_install": True, "install_nonce": "nope"}, fetch=f, run=r)
        self.assertEqual(payload(res)["error"]["code"], "INSTALL_REQUIRED")
        self.assertEqual(ran, [])

    def test_expired_nonce_refused(self):
        n = payload(call({})[0])["install_nonce"]
        ran, f, r = self._stubs()
        with mock.patch.object(shim, "_now", return_value=shim._now() + shim.NONCE_TTL + 5):
            res, _ = call({"accept_install": True, "install_nonce": n}, fetch=f, run=r)
        self.assertEqual(payload(res)["error"]["code"], "INSTALL_REQUIRED")
        self.assertEqual(ran, [])

    def test_yes_path_and_single_use(self):
        n = payload(call({})[0])["install_nonce"]
        ran, f, r = self._stubs()
        res, done = call({"accept_install": True, "install_nonce": n}, fetch=f, run=r)
        self.assertTrue(done)
        self.assertEqual(payload(res)["code"], "INSTALLED")
        self.assertEqual(ran, ["https://cdn.murmurcomputing.ai/install.sh"])
        self.assertFalse(os.path.exists(os.path.join(self.home.name, "inst.sh")))
        res, done = call({"accept_install": True, "install_nonce": n}, fetch=f, run=r)  # reuse
        self.assertFalse(done)
        self.assertEqual(payload(res)["error"]["code"], "INSTALL_REQUIRED")
        self.assertEqual(len(ran), 1)

    def test_installer_failure_passthrough_and_garbage(self):
        n = payload(call({})[0])["install_nonce"]
        _, f, _ = self._stubs()
        res, done = call({"accept_install": True, "install_nonce": n}, fetch=f,
                         run=lambda p: 'log\n{"ok":false,"error":{"code":"X","message":"m"}}')
        self.assertEqual(payload(res)["error"]["code"], "X")
        n = payload(call({})[0])["install_nonce"]
        res, done = call({"accept_install": True, "install_nonce": n}, fetch=f, run=lambda p: "not json")
        self.assertEqual(payload(res)["error"]["code"], "INSTALL_FAILED")
        self.assertFalse(done)

    def test_linux_unsupported(self):
        with mock.patch.object(sys, "platform", "linux"):
            res, done = call({"accept_install": True, "install_nonce": "x"})
        self.assertEqual(payload(res)["error"]["code"], "UNSUPPORTED_PLATFORM")

    def test_windows_runs_file_with_powershell(self):
        with mock.patch.object(sys, "platform", "win32"), mock.patch("subprocess.run") as sr:
            sr.return_value.stdout = '{"ok":true}'
            shim.run_installer("C:\\t\\i.ps1")
        self.assertEqual(sr.call_args[0][0], ["powershell.exe", "-NoProfile", "-ExecutionPolicy",
                                               "Bypass", "-File", "C:\\t\\i.ps1"])


class Fetch(Base):
    def _resp(self, data):
        r = mock.MagicMock()
        r.__enter__.return_value = r
        r.read.side_effect = lambda n=-1: data[:n]
        return r

    def test_refuses_http_and_other_host(self):
        for u in ("http://cdn.murmurcomputing.ai/install.sh", "https://evil.example/install.sh"):
            with self.assertRaises(ValueError):
                shim.fetch_installer(u)

    def test_size_cap(self):
        op = mock.MagicMock()
        op.open.return_value = self._resp(b"x" * (shim.MAX_BYTES + 1))
        with mock.patch("urllib.request.build_opener", return_value=op):
            with self.assertRaises(ValueError):
                shim.fetch_installer(shim.installer_url())

    def test_downloads_to_file(self):
        op = mock.MagicMock()
        op.open.return_value = self._resp(b"echo hi")
        with mock.patch("urllib.request.build_opener", return_value=op):
            p = shim.fetch_installer(shim.installer_url())
        self.assertEqual(open(p, "rb").read(), b"echo hi")
        os.unlink(p)

    def test_off_host_redirect_refused(self):
        h = shim._SameHost()
        with self.assertRaises(urllib.error.URLError):
            h.redirect_request(mock.MagicMock(), None, 302, "", {}, "https://evil.example/x")
        with self.assertRaises(urllib.error.URLError):
            h.redirect_request(mock.MagicMock(), None, 302, "", {}, "http://cdn.murmurcomputing.ai/x")


class Handover(Base):
    def test_second_request_left_in_fd(self):
        r, w = os.pipe()
        n = payload(call({})[0])["install_nonce"]
        a = json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"arguments":
                        {"accept_install": True, "install_nonce": n}}})
        b = json.dumps({"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
        os.write(w, (a + "\n" + b + "\n").encode())
        out_r, out_w = os.pipe()
        saved = os.dup(1)
        os.dup2(out_w, 1)
        seen = []

        def handover():
            seen.append(shim.read_line(r))  # what the real server would read next
            raise SystemExit(0)

        try:
            with self.assertRaises(SystemExit):
                shim.serve([], handover, fetch=lambda u: self._f(), run=lambda p: '{"ok":true}', fd=r)
        finally:
            os.dup2(saved, 1)
            os.close(saved)
            os.close(out_w)
        out = os.read(out_r, 65536).decode().splitlines()
        self.assertEqual(json.loads(out[0])["id"], 5)
        self.assertEqual(json.loads(out[1])["method"], "notifications/tools/list_changed")
        self.assertEqual(json.loads(seen[0])["id"], 6)

    def _f(self):
        p = os.path.join(self.home.name, "i.sh")
        open(p, "w").write("x")
        return p


if __name__ == "__main__":
    unittest.main()
