# Creating Prime Agent Sessions Programmatically

## Overview

The **only way to create a prime-agent session programmatically** is via `create-session.mts` in the repo root. This file imports `handleDaemonCommand` from the compiled daemon module and calls it with top-level await, which is required because the daemon client uses promises at the module level.

The daemon `create` command is NOT exposed as a public CLI verb. `prime-agent --help` does not list it, and calling it directly requires using the internal `handleDaemonCommand` function, which can only be imported and awaited from a module with top-level await support (`.mts` or `.mjs`).

## Why This Exists

Measured 2026-09-19: the prime daemon had been UP for 3 days with **zero sessions**. Every piece of automation built around it (convergence panels, tick ladders, hourly clocks) was routing AROUND prime instead of through it because there was no way to spawn a session.

This file closes that gap by providing a single, deterministic entry point for session creation.

## Usage

### Basic: Create a session with defaults

```bash
npm run build                              # Must build first for dist/ to exist
node --experimental-strip-types create-session.mts my-session
```

Output (success):
```
Created 1fe089915fe6 (my-session)
```

### Machine-readable (for headless loops)

```bash
node --experimental-strip-types create-session.mts my-session --json
```

Returns JSON with the full session summary:
```json
{
  "id": "1fe089915fe6",
  "lifecycle": "draft",
  "activeSessionId": "1fe089915fe6",
  "sessionName": "my-session",
  "sessionFile": "/home/jojo/.prime/agent/sessions/01a0c464-808c-75dd-9613-dcaa6d461da7.jsonl",
  ...
}
```

### With daemon arguments

Pass extra daemon arguments after a bare `--`:

```bash
node --experimental-strip-types create-session.mts my-session --json -- --cwd /tmp/mywork --model claude-opus
```

## Exit Codes and Invariants

**CRITICAL INVARIANT: `exit==0` if and only if a session file was created.**

| Exit Code | Meaning | Session File |
|-----------|---------|--------------|
| 0 | Success | **Always exists** |
| 1 | Creation failed | Does not exist |
| 2 | Usage error (missing name) | N/A |
| 124 | Timeout (daemon unreachable) | Does not exist |

The script explicitly checks `process.exitCode` after calling `handleDaemonCommand` because the daemon module sets exitCode on failure but continues to return true (a design pattern in the upstream library). This script enforces the invariant by exiting non-zero if any error was detected.

## Finding Your Session

After creation, find your session file at:

```bash
~/.prime/agent/sessions/
```

Each session is a single `.jsonl` file (newline-delimited JSON). The filename is a UUID and does NOT match the session name you gave it — the session name is a human-readable label, stored inside the JSON.

To find a session by name:

```bash
grep -l '"sessionName":"my-session"' ~/.prime/agent/sessions/*.jsonl
```

## Implementation Details

### Why .mts?

The daemon client uses top-level await in its module. Node.js requires `.mts` (or `.mjs`) for files that use top-level await. A `.js` or `.ts` file with top-level await will fail with:
```
SyntaxError: await is only valid in async functions and the top level of modules
```

### Why it's separate from the main CLI

The main CLI (`prime-agent` command) does not expose `daemon create` as a public verb. The public verbs are:
- `agents` — list agents
- `attach` — connect to a running session
- `send` — send work to a session
- `schedule` — set up a cron job
- `stop` — stop a session

Session creation is an internal operation. This script makes it accessible for headless automation while keeping it separate from the public CLI surface.

### Error Handling Contract

The script enforces:
1. **Throws on parse errors** — missing or invalid daemon args
2. **Exits with exitCode on daemon errors** — if the daemon can't create the session, the error message is printed and the script exits non-zero
3. **Verifies creation succeeded** — if handleDaemonCommand sets exitCode=1 but returns true (a quirk of the daemon module), this script catches it and exits 1 instead of proceeding

## Typical Workflow (Headless Loop)

```bash
#!/bin/bash
set -e

SESSION_JSON=$(node --experimental-strip-types create-session.mts "auto-$(date +%s)" --json)
SESSION_ID=$(echo "$SESSION_JSON" | jq -r '.activeSessionId')
SESSION_FILE=$(echo "$SESSION_JSON" | jq -r '.sessionFile')

echo "Created session $SESSION_ID at $SESSION_FILE"

# Now use prime-agent send to dispatch work:
prime-agent send "$SESSION_ID" "fix the build"

# Or wait for completion with a separate monitor...
```

The `--json` output ensures machine-readable parsing in scripts. The exit code ensures the script doesn't proceed if creation failed.

## Troubleshooting

### "Timed out after 30000ms waiting for the Prime Agent daemon response"

The daemon is not responding. Check:

```bash
ps aux | grep prime-agent | grep -v grep
```

If the daemon is not running, start it:

```bash
prime-agent start
```

If the daemon is running but not responding, check the log:

```bash
ls -la ~/.prime/agent/logs/
```

### "Agent name X is unavailable: an agent of that name already exists"

The session name is already in use. Use a unique name:

```bash
node --experimental-strip-types create-session.mts "unique-$(date +%s)"
```

### "Error: Could not find dist/ files"

Build the project first:

```bash
npm run build
```

The script imports from `packages/coding-agent/dist/`, which is only created by the build step.

## Future Work

Future versions may expose `daemon create` as a public CLI verb, making this script obsolete. Until then, `create-session.mts` is the canonical way to create sessions from headless automation.
