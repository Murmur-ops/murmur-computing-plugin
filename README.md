# Murmur plugin for Claude

Murmur is an MCP server that lets Claude hand heavy compute to your own devices. Claude passes a NumPy script, or the Python functions to offload, plus a deadline. Murmur runs the work on this computer and, when it is faster, on your other Macs and Windows PCs. It returns the answer and whether the deadline was met. Free for up to 10 devices.

This plugin adds Murmur's two MCP servers (`murmur`, `murmur-python`) and one skill that tells Claude when to offload and how to read the results.

## Tools

| Tool | What it does |
|---|---|
| `murmur_run_script` | Runs a NumPy script on your devices with a deadline; returns outputs and a deadline verdict |
| `murmur_run_python` | Runs a Python file here and sends the functions you name to your devices |
| `murmur_run_dag` | Runs a Murmur DAG you built |
| `murmur_fleet` | Lists your online devices, their measured speed, and the licence state |
| `murmur_invite` | Makes a one-time line (or, for a Windows PC, a download and a code) that adds another of your computers, no account |
| `murmur_job_status`, `murmur_job_results` | Look up a job by id |

## Install

```bash
claude plugin marketplace add Murmur-ops/murmur-computing-plugin
claude plugin install murmur-computing@murmur-computing
```

## Example prompts

Each of these runs on a Mac or Windows PC (the first one also walks you through setup):

1. "Estimate pi with a 2,000,000-path Monte Carlo in NumPy on Murmur, deadline 2 minutes." Claude writes the script, calls `murmur_run_script`, and reports the estimate and whether the deadline was met.
2. "What compute do I have on Murmur?" Claude calls `murmur_fleet` and lists your devices, their measured speed and how many of your 10 free devices are in use.
3. "Multiply two random 2048 x 2048 float32 matrices on Murmur and give me the sum of all entries of the result, deadline 1 minute." Claude calls `murmur_run_script` and reports the sum and the deadline verdict.
4. "Add my other Mac to Murmur." Claude calls `murmur_invite` and gives you one line to paste in Terminal on that Mac.

## First run happens inside Claude

1. Ask for a heavy job, for example: "Estimate pi with a 2,000,000-path Monte Carlo in NumPy on Murmur, deadline 2 minutes."
2. Claude shows you Murmur's Terms and asks yes or no. Nothing installs without your yes.
3. Murmur sets up a local server on this computer in the background: about 5 minutes and 300 MB, once. Claude tells you when it is ready and runs the job.
4. To add another Mac or a Windows PC, ask Claude "add my other computer to Murmur". On a Mac you paste one line in Terminal; on a Windows PC you download the installer, double-click it and paste a code. No account for up to 10 devices; the 11th needs an account and payment, and Claude asks you first.

The MCP servers are hosted by the Murmur command-line tool. If it is not on this computer yet, Claude asks before it runs the signed installer (`curl -fsSL https://cdn.murmurcomputing.ai/install.sh | sh` on a Mac, `install.ps1` on Windows), then asks you to reconnect the server with `/mcp`.

## Requirements

- macOS on Apple silicon or Windows 10/11 (x64), with Murmur installed in `~/.murmur` by its installer.
- Claude Code (terminal, IDE or desktop app) or Cowork running on your computer. Murmur's MCP servers are local, so claude.ai chat on the web and the mobile apps load only the skill; there Claude tells you Murmur needs Claude Code or Cowork on your computer.
- Windows install: `Invoke-WebRequest -UseBasicParsing https://cdn.murmurcomputing.ai/install.ps1 -OutFile "$env:TEMP\install.ps1"`, then `powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\install.ps1"` as your normal user. Claude runs these for you after you say yes; setup then continues inside Claude as on a Mac.

## What this plugin runs, sends and fetches

- **Runs:** `murmur planner mcp` (or `murmur planner mcp --python`) from `~/.murmur/bin`. It runs nothing else. If Murmur is missing, the server fails to start and Claude asks before installing it.
- **Downloads:** nothing by itself. Claude runs Murmur's installer only after you say yes. The installer checks an Ed25519-signed release manifest from `cdn.murmurcomputing.ai`. Setup after your Terms answer downloads about 300 MB from the same host.
- **Sends:** your script text stays on this machine. Input arrays and results travel between your own devices over TLS with your own private CA (DTLS on direct links). They do not pass through Murmur. Murmur's servers receive only licence, device-link and update metadata ([privacy policy](https://murmurcomputing.ai/privacy.html)).
- **PATH:** Claude Desktop and Cowork on macOS do not read your shell profile, and a Windows terminal opened before the install does not see the new PATH entry. So `.mcp.json` puts `~/.murmur/bin` first on the server's PATH, followed by your own PATH. The value is written once for both systems: on macOS the `;` pieces are unused entries, on Windows the `:` pieces are. Your PATH appears twice so that no entry of it is lost on either system.
- **Two copies of the tools:** if you already registered Murmur with `claude mcp add`, you will see its tools twice. Remove the manual ones with `claude mcp remove murmur` and `claude mcp remove murmur-python`.

## Install from PyPI

Without the plugin, any MCP client that runs stdio servers can use the `murmur-computing` package, pinned to a version:

```bash
claude mcp add --scope user murmur -- uvx murmur-computing==0.1.0
```

If Murmur is installed it starts Murmur's MCP server; if not, it asks first and installs only after the human says yes. Source: [`pypi/`](pypi/).

## Support

- Bugs and questions: [GitHub issues](https://github.com/Murmur-ops/murmur-computing-plugin/issues)
- Email: support@murmuredgecomputing.com

## Licence

The files in this plugin are MIT licensed. Murmur itself is covered by its [Terms of Service](https://murmurcomputing.ai/terms.html).
