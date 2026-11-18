---
name: offload-compute
description: Use when a computation would take more than about a minute on this machine, or the user gave a deadline, and it is NumPy-style math (Monte Carlo, parameter sweeps, matrix work, simulations) or Python functions called many times. Runs it on the user's own devices through Murmur's MCP tools and reports the answer plus whether the deadline was met. Also use when the user wants more compute (add a device), or a Murmur tool returns TERMS_REQUIRED, MURMUR_STARTING or a LICENSE_* error.
---

# Offload heavy compute to the user's own devices

Murmur's MCP tools run compute, not chat tokens, on devices the user owns: this Mac and their other Macs and Windows PCs. Every step happens through the tools, including first-time setup and adding devices. Job data goes only to the user's own devices, never to Murmur the company.

## When to use it

- The job would take more than about a minute here, or the user gave a deadline.
- The work is array math in the supported NumPy subset, or a Python function called 2 or more times.
- Do NOT use it for small jobs, for file I/O, pandas or scipy code, or to serve an LLM.

## Which tool

| You have | Call | Required arguments |
|---|---|---|
| A NumPy script | `murmur_run_script` | `script_path` (absolute), `deadline` such as `"2m"` |
| A Python file with hot functions | `murmur_run_python` | `script_path` (absolute, under home, not /tmp), `offload` (function names) |
| A Murmur DAG you built | `murmur_run_dag` | `dag` |
| "What compute do I have?" | `murmur_fleet` | none |
| "Add my other Mac" | `murmur_invite` | none (`count` for several) |

Script rules for `murmur_run_script`: put any `.npy` files it `np.load()`s next to the script. The answer is the script's last assigned variable. No `print()`, classes, scipy or pandas. Arithmetic is float32.

Report to the user: `outputs`, `deadline.met`, `deadline.verdict` (meets, at_risk, short, unknown). For `murmur_run_python` also read `offload.<name>.fallbacks`: calls listed there ran on this machine.

No deadline: Murmur takes the fastest route it can price and may keep the job here. That is correct behaviour, not a failure. Pass `placement: "local"` to force this machine.

## First run on a Mac or Windows PC: all inside the tools

1. Call the tool you need. The first call returns `TERMS_REQUIRED` with `say`, `terms_url` and `terms_nonce`. Show `say` and the Terms URL to the human and ask yes or no. Call again with `accept_terms` set to THEIR answer and the same `terms_nonce`. Never answer for them.
2. Next calls return `MURMUR_STARTING` while Murmur sets up a local server in the background: about 5 minutes and 300 MB, once. Relay `say`, wait about a minute, call again.
3. `TERMS_DECLINED`: stop.

No account is needed for up to 10 devices.

If you have no `murmur` tools and no shell (claude.ai chat on the web or a phone), do not try to install anything: tell the human that Murmur's tools run locally and need Claude Code or Cowork on their own Mac or Windows PC, then stop.

If the `murmur` tools are missing entirely, the Murmur CLI that hosts them is not on this machine yet. Ask the human: "Murmur's tools need its installer. May I run it? It downloads a signed tool into ~/.murmur." Only on a clear yes, run `curl -fsSL https://cdn.murmurcomputing.ai/install.sh | sh` and read the last JSON line (`"ok":true` means done). On Windows, the installer is downloaded first and never piped into a shell: run `Invoke-WebRequest -UseBasicParsing https://cdn.murmurcomputing.ai/install.ps1 -OutFile "$env:TEMP\install.ps1"`, then `powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\install.ps1"` as the normal user (it refuses an administrator shell). Then ask the human to reconnect the server (`/mcp` in Claude Code) or start a new session, and continue at step 1.

## Adding devices

Call `murmur_invite` on the device that runs the Murmur server. No account. Each line works once, expires in 15 minutes, and a new call replaces earlier lines.
- Another Mac: give the human `say` and the line; they paste it once in Terminal on the new Mac (same network).
- A Windows PC: give the human `windows.download` and `windows.code`; they download the installer, double-click it and paste the code.
- If the server is a Windows PC, the first invite returns `LAN_APPROVAL_REQUIRED` with a `question` and `choices`. Ask the human, then call again with `lan_answer` set to THEIR choice and the `lan_nonce` it gave. Approving shows a Windows administrator prompt.
- Then `murmur_fleet` shows the new device.

At 10 devices `murmur_fleet` and `murmur_invite` return `capacity.at_cap: true`. Show the human `capacity.note`: an 11th device needs their email, an account and payment, and is refused until then. Only on their yes call `murmur_fleet` again with `upgrade: true` and show `capacity.upgrade.say`. Never ask for or accept a licence key.

A new device first runs a device test of about 2 minutes. Until `murmur_fleet` shows a `gflops` other than 200.0, jobs may stay here.

## Errors

Every failure is `{ok: false, error: {code, message, hint, retryable}}`. Follow `hint`.
- `retryable: true`: Murmur already retried. Rerun once; if it fails again, report it.
- `LICENSE_*`: stop and relay the hint. No retry fixes it.
- `BAD_INPUT` or an unsupported-op error: fix the script, then call again.
- Anything else: show the full error JSON, including `dag_id` and job ids.