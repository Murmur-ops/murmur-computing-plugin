# murmur-computing

<!-- mcp-name: ai.murmurcomputing/murmur -->

Murmur's MCP server for AI agents. The agent hands Murmur a NumPy script, or the Python functions to offload, plus a deadline. Murmur runs the work on your own Macs and Windows PCs and returns the answer and whether the deadline was met. Free for up to 10 devices.

## Add it to your agent

```bash
claude mcp add --scope user murmur -- uvx murmur-computing==0.1.0
claude mcp add --scope user murmur-python -- uvx murmur-computing==0.1.0 --python
```

Any MCP client that runs stdio servers works the same way: command `uvx`, arguments `murmur-computing==0.1.0`.

## First run happens inside the agent

1. On the first tool call, the agent shows you Murmur's Terms and asks yes or no.
2. If Murmur is not on this machine, the agent asks before it runs Murmur's signed installer.
3. Setup runs in the background: about 5 minutes and 300 MB, once.
4. To add another Mac, ask the agent; it calls `murmur_invite` and you paste one line on that Mac.

## What this package is

A small launcher, standard library only. If Murmur is installed (`~/.murmur/bin/murmur`), it starts `murmur planner mcp`. If not, it serves the same tool names and answers each call with `INSTALL_REQUIRED` until you say yes to the installer. It contains no Murmur engine code and sends nothing itself.

Your script text stays on your machine. Input arrays and results travel only between your own devices. Murmur's servers receive licence, device-link and update metadata ([privacy policy](https://murmurcomputing.ai/privacy.html)). Terms: https://murmurcomputing.ai/terms.html
