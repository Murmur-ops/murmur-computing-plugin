#!/bin/sh
# Starts Murmur's local MCP server (stdio): `murmur planner mcp`, or `murmur planner mcp --python`.
#
# Why an absolute path: Claude Desktop and Cowork are GUI apps on macOS. They start with the
# launchd PATH (/usr/bin:/bin:/usr/sbin:/sbin) and never read ~/.zprofile, so a bare `murmur`
# is not found there even after install.sh added ~/.murmur/bin to the shell profile.
#
# This script runs nothing else and downloads nothing. If Murmur is not installed it exits with
# a message on stderr; the plugin's skill tells Claude to ask the human before installing.
MURMUR="$HOME/.murmur/bin/murmur"
if [ ! -x "$MURMUR" ]; then
  echo "murmur-computing: Murmur is not installed on this machine ($MURMUR not found)." >&2
  echo "Install (macOS, after the human says yes): curl -fsSL https://cdn.murmurcomputing.ai/install.sh | sh" >&2
  echo "Then reconnect this MCP server (/mcp in Claude Code) or start a new session." >&2
  exit 127
fi
exec "$MURMUR" planner mcp "$@"
