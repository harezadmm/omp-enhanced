# MCP Guide

T3MP3ST includes a Model Context Protocol stdio server in `src/mcp-server.ts`.

## Start The Server

From a development checkout:

```bash
npm run mcp
```

From a built package:

```bash
npm run build
npm run mcp:prod
```

## Exposed Tool

| Tool | Purpose |
|---|---|
| `security_recon` | Runs quick DNS and nmap reconnaissance against a hostname or IP |

Input schema:

```json
{
  "target": "example.com",
  "scan_type": "quick"
}
```

`scan_type` may be `quick`, `standard`, `full`, or `stealth`.

## Safety And Validation

The MCP server validates the target before it reaches a subprocess:

- Target must be a hostname or IP-like value matching `[A-Za-z0-9._:-]`
- Shell metacharacters, spaces, pipes, and command separators are rejected
- Subprocesses use `execFile`, not a shell
- Executable names are restricted to an allowlist

The current `security_recon` implementation calls:

- `dig +short <target> ANY`
- `nmap` with scan arguments selected by `scan_type`

Only use this tool against systems inside your authorized scope.

## Example MCP Tool Call

```json
{
  "name": "security_recon",
  "arguments": {
    "target": "scanme.nmap.org",
    "scan_type": "quick"
  }
}
```

The response is JSON text containing DNS records, nmap output, command summaries, and suggested next steps.
