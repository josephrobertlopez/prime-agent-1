# Harness — prime-agent (the LOCI layer)

<!-- Source of truth for this project's harness: what conventions exist, how they
     are enforced, and what periodic checks fight entropy.

     Bootstrapped 2026-09-19 via /superpowers-init. Deliberate deviation from the
     template default: this file lives at the REPO ROOT, not .claude/, so that one
     audit gate can read HARNESS.md identically across the three repos in the
     standing chain (monorepo-v2, agent-ops, prime-agent). That consistency is the
     point, not an accident.

     Inspired by Birgitta Boeckeler's "Harness Engineering":
     https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html -->

## Context

### Role in the chain — this repo IS the locus of control

This is not a generic TypeScript project. It is one layer of a four-layer chain,
and nearly every constraint below exists because of that position:

```
Claude          →   prime-agent        →   agent-ops        →   conductor  →  DB receipt
(judge/driver)      (THIS REPO:            (arbiter/            (runner)      (ground truth)
                     locus/executor)        substrate)
```

Each layer's single job:

| layer | DOES | DOES NOT |
|---|---|---|
| Claude | judge exit codes and DB scalars; drive dispatch | execute; write the DB |
| **prime-agent (here)** | **receive a GOAL; resolve it to a skill; dispatch; carry the work** | **judge its own success; answer the goal itself with a bare tool loop** |
| agent-ops | run conductor; write receipt rows; expose resolve/audit scalars | decide which skill to run |
| conductor | execute workflow.yaml steps deterministically | know anything about grading |
| DB | be ground truth | trust anyone's self-report |

The single most important property of this layer: **prime-agent must not be able
to declare itself finished.** The autonomous runtime already encodes this — the
continuation prompt it injects into itself says *"Do not end the session yourself;
the verifier/evaluator decides completion when configured gates pass."* Every
constraint about gates below is protecting that property.

### Stack

- **Primary languages**: TypeScript (Node), with a Python REPL tool surface
- **Build system**: npm workspaces — `packages/{agent,ai,coding-agent,tui}`;
  `npm run build` compiles to `packages/coding-agent/dist/`
- **Test framework**: per-workspace, via `npm run test --workspaces --if-present`
- **Lint/format/typecheck**: `biome` + `tsgo --noEmit`, both wrapped by `npm run check`
- **Git hooks**: husky (`prepare` script)
- **Upstream**: fork of `PrimeIntellect-ai/prime-agent`. Local changes are candidates
  for upstream — prefer additive, local-only files over edits that create merge churn.
- **Container strategy**: none in this repo

### Conventions

- **Headless entry point**: `prime-agent -p` (alias `--print`) prints a response and
  exits. `--cwd <dir>` genuinely works here (unlike some sibling CLIs) — use it rather
  than `cd`-ing first.
- **Autonomous surface**: `--autonomous`, plus `--autonomous-gate <cmd>` (repeatable),
  `--autonomous-max-tokens`, `--autonomous-max-turns`, `--autonomous-max-continuations`,
  `--autonomous-timeout-ms`, `--autonomous-gate-retries`, `--autonomous-gate-timeout-ms`.
- **Token accounting**: `--autonomous-max-tokens` counts `input + output + cacheWrite`
  and deliberately **excludes `cacheRead`** — cached context replayed each turn would
  otherwise exhaust a verifier loop's budget before any real work landed.
- **Error handling**: a failed dispatch must fail LOUD and non-zero. A headless caller
  must never be able to read a failed run as success — that is the false-green shape
  this whole chain exists to eliminate.
- **Documentation**: file-level preamble explaining WHY the file exists and what it
  deliberately does not do (see `create-session.mts` as the worked example).

---

## Constraints

<!-- Each constraint is a verification slot. "unverified" is an honest declaration
     of intent with no tool yet -- it is NOT a failure, and is strictly better than
     claiming deterministic enforcement that does not exist. -->

### A worker is never its own judge

- **Rule**: Any `--autonomous-gate` command MUST live outside the file tree the
  session is permitted to modify. A gate inside the worker's own writable tree can
  be weakened by the worker, which silently converts the completion check into a
  self-report — the exact failure the autonomous design prevents.
- **Enforcement**: unverified
- **Tool**: none yet (proposed: a wrapper that rejects a gate path under `--cwd`)
- **Scope**: dispatch

### Gates must be falsifiable before they are trusted

- **Rule**: Before a gate is used to authorise real work, it must be observed to
  FAIL on current state. A gate that already passes ends its session instantly and
  proves nothing (the `test "" = ""` shape).
- **Enforcement**: unverified
- **Tool**: none yet (proposed: pre-dispatch gate-honesty check, exit non-zero if
  the gate already passes)
- **Scope**: dispatch

### A goal is a goal, not a command

- **Rule**: The prompt handed to a dispatched session states an OBJECTIVE and lets
  this layer resolve it. Passing a literal shell command (`grep ...`,
  `python3 -m ...`) reduces this layer to a relay and discards the judgment that
  justifies its existence.
- **Enforcement**: agent
- **Tool**: reviewer judgment at dispatch authoring time
- **Scope**: dispatch

### Session output must have a durable channel

- **Rule**: If a dispatch's synthesised answer needs to be read back, it must run
  through a channel that survives session exit — `-p/--print`, a persisted session
  transcript, or an effect recorded in an external store. A fire-and-forget
  background session with persistence disabled has NO output channel; its result
  evaporates.
- **Enforcement**: unverified
- **Tool**: none yet
- **Scope**: dispatch

### Consistent formatting and types

- **Rule**: All source must pass `biome` and `tsgo --noEmit` without changes.
- **Enforcement**: deterministic
- **Tool**: `npm run check`
- **Scope**: commit

### Tests must pass

- **Rule**: The workspace test suites must pass before merge.
- **Enforcement**: deterministic
- **Tool**: `npm run test --workspaces --if-present`
- **Scope**: pr

### No secrets in source

- **Rule**: No API keys, tokens, or private keys in committed source. This layer
  handles provider credentials (`--api-key`, `~/.prime/agent/auth.json`), so the
  blast radius is higher here than in a normal repo.
- **Enforcement**: unverified
- **Tool**: none yet — `gitleaks` is NOT installed on this machine (verified
  2026-09-19: absent from PATH). Declaring this `deterministic` would be a false
  claim; it is `unverified` until the scanner exists.
- **Scope**: commit

### Inference spend has no local cage

- **Rule**: A dispatch that reaches a paid provider should be bounded by something
  local before it is bounded by the provider's balance.
- **Enforcement**: unverified
- **Tool**: none. Verified 2026-09-19: OpenRouter inference returns a hard
  `402 — would exceed your available credits` with no local pre-check. The
  `--autonomous-max-*` flags bound TOKENS and TURNS, never DOLLARS. The effective
  spend cage today is the account balance, discovered on failure.
- **Scope**: dispatch
- **Note**: declared honestly as a real governance gap rather than dressed up as
  enforcement. This is the highest-value constraint here to promote.

---

## Garbage Collection

### Cost-readback path still works

- **What it checks**: Whether per-session usage remains recoverable. `daemon` is NOT
  a public verb (removed upstream) so `prime-agent daemon stats` does not exist;
  `prime-agent list --all --json` returns sessions with NO usage block. The only real
  readback is the session transcripts at `~/.prime/agent/sessions/*.jsonl`, which do
  carry `usage`, `cost`, and `totalTokens` keys.
- **Frequency**: monthly
- **Enforcement**: unverified
- **Tool**: none yet
- **Auto-fix**: false

### Secret scanner operational

- **What it checks**: Whether `gitleaks` has been installed, allowing the
  "No secrets in source" constraint to be promoted from unverified to deterministic.
- **Frequency**: weekly
- **Enforcement**: deterministic
- **Tool**: `gitleaks --version`
- **Auto-fix**: false

### Upstream drift

- **What it checks**: How far this fork has diverged from
  `PrimeIntellect-ai/prime-agent`, and whether local habitat files have started
  colliding with upstream paths.
- **Frequency**: monthly
- **Enforcement**: agent
- **Tool**: harness-gc agent
- **Auto-fix**: false

### Documentation freshness

- **What it checks**: Whether this file's claims about the CLI surface still hold.
  Every flag and gotcha here was verified by real invocation on 2026-09-19; upstream
  merges can silently invalidate any of them.
- **Frequency**: monthly
- **Enforcement**: agent
- **Tool**: harness-gc agent
- **Auto-fix**: false

---

## Observability

- Snapshot cadence: monthly

### Operating cadence

- Harness audit: quarterly (90 days)
- AI literacy assessment: quarterly (90 days)
- Reflection review and promotion: monthly (30 days)
- Cost capture: quarterly (90 days) — currently blocked, see the cost-readback GC rule

### Health thresholds

- Minimum enforcement ratio for Healthy: 70%
- Consecutive zero-finding GC snapshots before alert: 3
- Unpromoted reflection age before learning flow is stalled: 60 days

### Regression detection

- Cadence non-compliance threshold: 2 or more activities overdue
- Reflection drought threshold: 4 consecutive weeks with zero reflections

---

## Read-side filtering

Readers of `REFLECTION_LOG.md` bound default intake so per-read cost stays flat:

- **Bounded entry count**: 50
- **Bounded day window**: 90 days
- **Default policy**: read the more inclusive of the two

---

## Status

<!-- Auto-updated by a harness audit — do not edit manually -->

Last audit: never
Constraints enforced: 2/8
Garbage collection active: 1/4
Drift detected: not yet audited

<!-- The 2/8 above is a DECLARATION derived from the enforcement fields at
     authoring time (only `npm run check` and the workspace test run have a real
     tool today), not an independently re-derived measurement. It has never been
     audited, and saying so is the point: a habitat document asserting a
     governance fact it has never re-verified is the same failure class as a
     false test-green. The honest low number is the correct starting state. -->
