# Murmur plugin for Claude

Murmur is an MCP server that lets Claude hand heavy compute to your own devices. Claude passes a NumPy script, or the Python functions to offload, plus a deadline. Murmur runs the work on this Mac and, when it is faster, on your other Macs and Windows PCs. It returns the answer and whether the deadline was met. Free for up to 10 devices.

This plugin adds Murmur's two MCP servers (`murmur`, `murmur-python`) and one skill that tells Claude when to offload and how to read the results.

## Tools

| Tool | What it does |
|---|---|
| `murmur_run_script` | Runs a NumPy script on your devices with a deadline; returns outputs and a deadline verdict |
| `murmur_run_python` | Runs a Python file here and sends the functions you name to your devices |
| `murmur_run_dag` | Runs a Murmur DAG you built |
| `murmur_fleet` | Lists your online devices, their measured speed, and the licence state |
| `murmur_invite` | Makes a one-time line that adds another Mac to your fleet, no account |
| `murmur_job_status`, `murmur_job_results` | Look up a job by id |

## Install

```bash
claude plugin marketplace add Murmur-ops/murmur-computing-plugin
claude plugin install murmur-computing@murmur-computing
```

## First run happens inside Claude

1. Ask for a heavy job, for example: "Estimate pi with a 2,000,000-path Monte Carlo in NumPy on Murmur, deadline 2 minutes."
2. Claude shows you Murmur's Terms and asks yes or no. Nothing installs without your yes.
3. Murmur sets up a local server on this Mac in the background: about 5 minutes and 300 MB, once. Claude tells you when it is ready and runs the job.
4. To add another Mac, ask Claude "add my other Mac to Murmur". You paste one line on that Mac.

The MCP servers are hosted by the Murmur command-line tool. If it is not on this Mac yet, Claude asks before it runs the signed installer (`curl -fsSL https://cdn.murmurcomputing.ai/install.sh | sh`), then asks you to reconnect the server with `/mcp`.

## Requirements

- macOS on Apple silicon, in Claude Code or in Cowork running on your computer. claude.ai chat loads the skill only; local MCP servers do not run there.
- Windows: Murmur runs on Windows, but this plugin's launcher does not yet. Use [START-HERE](https://cdn.murmurcomputing.ai/START-HERE.md).

## What this plugin runs, sends and fetches

- **Runs:** `scripts/murmur-mcp.sh`, which starts `~/.murmur/bin/murmur planner mcp` (or `... --python`). It runs nothing else. If Murmur is missing it prints a message and exits.
- **Downloads:** nothing by itself. Claude runs Murmur's installer only after you say yes. The installer checks an Ed25519-signed release manifest from `cdn.murmurcomputing.ai`. Setup after your Terms answer downloads about 300 MB from the same host.
- **Sends:** your script text stays on this machine. Input arrays and results travel between your own devices over TLS with your own private CA (DTLS on direct links). They do not pass through Murmur. Murmur's servers receive only licence, device-link and update metadata ([privacy policy](https://murmurcomputing.ai/privacy.html)).
- **macOS GUI apps and PATH:** Claude Desktop and Cowork do not read your shell profile, so a bare `murmur` is not found there. The launcher calls `~/.murmur/bin/murmur` by absolute path for that reason.
- **Two copies of the tools:** if you already registered Murmur with `claude mcp add`, you will see its tools twice. Remove the manual ones with `claude mcp remove murmur` and `claude mcp remove murmur-python`.

## Install from PyPI

Without the plugin, any MCP client that runs stdio servers can use the `murmur-computing` package, pinned to a version:

```bash
claude mcp add --scope user murmur -- uvx murmur-computing==0.1.0
```

If Murmur is installed it starts Murmur's MCP server; if not, it asks first and installs only after the human says yes. Source: [`pypi/`](pypi/).

## Licence

The files in this plugin are MIT licensed. Murmur itself is covered by its [Terms of Service](https://murmurcomputing.ai/terms.html).
