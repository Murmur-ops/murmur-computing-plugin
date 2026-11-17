"""Entry point: run Murmur's planner MCP server if installed, else the install-on-consent shim."""
import os
import subprocess
import sys

from . import shim


def murmur_path():
    """Absolute path of the installed CLI, or None. Never searches PATH."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        home = os.environ.get("USERPROFILE") or home
        p = os.path.join(home, ".murmur", "bin", "murmur.cmd")
        return p if os.path.isfile(p) else None
    if sys.platform == "darwin":
        p = os.path.join(home, ".murmur", "bin", "murmur")
        return p if os.path.isfile(p) and os.access(p, os.X_OK) else None
    return None


def start_murmur(path, argv):
    """Become `murmur planner mcp <argv>`. Returns only on Windows (exit code)."""
    cmd = [path, "planner", "mcp", *argv]
    if sys.platform == "win32":
        return subprocess.call(cmd)
    os.execv(path, cmd)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    path = murmur_path()
    if path:
        code = start_murmur(path, argv)
        sys.exit(code)
    shim.serve(argv, handover=lambda: _handover(argv))


def _handover(argv):
    path = murmur_path()
    if path is None:
        return False
    sys.exit(start_murmur(path, argv))
