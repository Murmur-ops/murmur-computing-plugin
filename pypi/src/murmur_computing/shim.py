"""Not-installed MCP server: asks before installing Murmur, then hands the session to the real server."""
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from . import __version__

HOST = "cdn.murmurcomputing.ai"
MAX_BYTES = 1024 * 1024
NONCE_TTL = 600
TERMS_URL = "https://murmurcomputing.ai/terms.html"
PRIVACY_URL = "https://murmurcomputing.ai/privacy.html"
TOOLS = ["murmur_run_script", "murmur_run_dag", "murmur_job_status",
         "murmur_job_results", "murmur_fleet", "murmur_invite"]
PYTHON_TOOLS = ["murmur_run_python"]
_nonces = {}
_now = time.monotonic


def installer_url():
    return "https://%s/%s" % (HOST, "install.ps1" if sys.platform == "win32" else "install.sh")


def _say():
    where = "~/.murmur"
    extra = (" Windows joins a fleet whose server runs on a Mac; use murmur_invite on the Mac first."
             if sys.platform == "win32" else "")
    return ("Murmur is not installed on this computer. May I install it? It downloads about 300 MB into %s "
            "(no sudo; one PATH line is added to your shell profile) after checking a signed release manifest. "
            "Terms: %s.%s Ask the human yes or no; never answer for them." % (where, TERMS_URL, extra))


class _SameHost(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlsplit(newurl)
        if u.scheme != "https" or u.hostname != HOST:
            raise urllib.error.URLError("redirect off %s refused" % HOST)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_installer(url):
    """Download the installer to a temp file; return its path. Raises on any guard failure."""
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or u.hostname != HOST:
        raise ValueError("installer must come from https://%s" % HOST)
    opener = urllib.request.build_opener(_SameHost)
    with opener.open(url, timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("installer larger than %d bytes" % MAX_BYTES)
    fd, path = tempfile.mkstemp(prefix="murmur-install-", suffix=".ps1" if sys.platform == "win32" else ".sh")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def run_installer(path):
    if sys.platform == "win32":
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path]
    else:
        cmd = ["/bin/sh", path]
    p = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
    return p.stdout


def _verdict(out):
    lines = [l for l in (out or "").splitlines() if l.strip()]
    try:
        v = json.loads(lines[-1])
        return v if isinstance(v, dict) else None
    except (IndexError, ValueError):
        return None


def _new_nonce():
    n = secrets.token_urlsafe(16)
    _nonces[n] = _now() + NONCE_TTL
    return n


def _take_nonce(n):
    exp = _nonces.pop(n, None) if isinstance(n, str) else None
    return exp is not None and _now() <= exp


def _err(code, message, hint=""):
    return {"ok": False, "error": {"code": code, "message": message, "hint": hint, "retryable": False}}


def _required():
    r = _err("INSTALL_REQUIRED", "Murmur is not installed.",
             "Show the human `say`, ask yes or no, then call again with accept_install and install_nonce.")
    r.update(say=_say(), install_url=installer_url(), terms_url=TERMS_URL, privacy_url=PRIVACY_URL,
             install_nonce=_new_nonce())
    return r


def call_tool(args, fetch=None, run=None):
    """Return (result dict, installed_ok)."""
    fetch, run = fetch or fetch_installer, run or run_installer
    if sys.platform not in ("darwin", "win32"):
        return _err("UNSUPPORTED_PLATFORM", "Murmur supports macOS and Windows only."), False
    args = args if isinstance(args, dict) else {}
    yes = args.get("accept_install")
    if yes is False:
        return _err("INSTALL_DECLINED", "The human declined the install.", "Nothing was installed."), False
    if yes is not True or not _take_nonce(args.get("install_nonce")):
        return _required(), False
    path = None
    try:
        path = fetch(installer_url())
        v = _verdict(run(path))
    except Exception as e:  # noqa: BLE001 - report, never crash the server
        return _err("INSTALL_FAILED", "Installer could not run: %s" % e), False
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass
    if v is None:
        return _err("INSTALL_FAILED", "Installer printed no JSON verdict."), False
    if not v.get("ok"):
        return {"ok": False, "error": v.get("error") or {"code": "INSTALL_FAILED", "message": "install failed"}}, False
    return {"ok": True, "installed": True, "code": "INSTALLED",
            "say": "Murmur is installed. Call the tool again; the next call asks for the Terms."}, True


def _write(obj):
    data = (json.dumps(obj, separators=(",", ":")) + "\n").encode()
    while data:
        data = data[os.write(1, data):]


def read_line(fd=0):
    """Unbuffered: reads one byte at a time so nothing is consumed past the newline."""
    buf = b""
    while True:
        c = os.read(fd, 1)
        if not c:
            return None
        if c == b"\n":
            return buf
        buf += c


def _tools(python):
    names = PYTHON_TOOLS if python else TOOLS
    schema = {"type": "object", "additionalProperties": True,
              "properties": {"accept_install": {"type": "boolean"}, "install_nonce": {"type": "string"}}}
    return [{"name": n, "description": "Murmur is not installed yet: the first call returns INSTALL_REQUIRED.",
             "inputSchema": schema} for n in names]


def handle(msg, python=False, fetch=None, run=None):
    """Return (response or None, installed_ok)."""
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None, False
    ok = lambda r: ({"jsonrpc": "2.0", "id": mid, "result": r}, False)  # noqa: E731
    if method == "initialize":
        pv = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
        return ok({"protocolVersion": pv, "capabilities": {"tools": {"listChanged": True}},
                   "serverInfo": {"name": "murmur-computing", "version": __version__},
                   "instructions": "Murmur is not installed yet. The first tool call returns INSTALL_REQUIRED: "
                                   "show the human `say`, ask yes or no, never answer for them."})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": _tools(python)})
    if method == "tools/call":
        res, done = call_tool((msg.get("params") or {}).get("arguments"), fetch, run)
        r = {"content": [{"type": "text", "text": json.dumps(res, separators=(",", ":"))}],
             "structuredContent": res, "isError": not res.get("ok")}
        return {"jsonrpc": "2.0", "id": mid, "result": r}, done
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "Method not found"}}, False


def serve(argv, handover, fetch=None, run=None, fd=0):
    python = "--python" in argv
    while True:
        line = read_line(fd)
        if line is None:
            return
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if not isinstance(msg, dict):
            continue
        resp, installed = handle(msg, python, fetch, run)
        if resp is not None:
            _write(resp)
        if installed:
            _write({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"})
            handover()  # execs (macOS) or exits with the child's code (Windows); returns only if not found
