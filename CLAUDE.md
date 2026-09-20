# Project Conventions — prime-agent (the LOCI layer)

<!-- High-signal only. Every rule here costs token budget on every call.
     Bootstrapped 2026-09-19 via /superpowers-init. HARNESS.md is the source of
     truth for constraints; this file is how to WORK here. -->

## What this repo is

A fork of `PrimeIntellect-ai/prime-agent` — a TypeScript/Node CLI coding agent with
a Python REPL tool. In the standing chain it is the **locus of control**:

```
Claude (judge/driver) → prime-agent (HERE: locus/executor) → agent-ops (arbiter)
                                                           → conductor → DB receipt
```

Read `HARNESS.md` before proposing anything about dispatch, gates, or autonomy —
its constraints exist because of this position, not because of generic TS hygiene.

**Upstream discipline:** local changes are merge-churn candidates. Prefer additive,
local-only files over edits to upstream paths. `AGENTS.md` is upstream's — do not
rewrite it.

## The one property worth protecting

**prime-agent must not be able to declare itself finished.** The autonomous runtime
already enforces this — it injects *"Do not end the session yourself; the
verifier/evaluator decides completion when configured gates pass."* Every change
touching autonomy must preserve that. If a change would let a session mark its own
work complete, it is wrong regardless of how convenient it is.

## Build and Test

    # Build (compiles to packages/coding-agent/dist/)
    npm run build

    # Test (per-workspace)
    npm run test --workspaces --if-present

    # Lint + format + typecheck (biome + tsgo, one command)
    npm run check

`npm run check` writes fixes and errors on warnings. Run it before any commit; it is
the only constraint in `HARNESS.md` with real deterministic enforcement today.

## Verified CLI surface

Every item below was confirmed by real invocation on 2026-09-19. Re-verify after any
upstream merge rather than trusting this list.

| need | how |
|---|---|
| headless run | `prime-agent -p` (`--print`) — prints a response and exits |
| working directory | `--cwd <dir>` — genuinely works; prefer it over `cd` |
| autonomy | `--autonomous` + `--autonomous-gate <cmd>` (repeatable) |
| bounds | `--autonomous-max-tokens` / `-max-turns` / `-max-continuations` / `-timeout-ms` |
| model | `--model <id>`, `--provider <name>`; `prime-agent model list` enumerates |
| session output | the session transcript under `~/.prime/agent/sessions/<id>.jsonl` |

**Token accounting:** `--autonomous-max-tokens` counts `input + output + cacheWrite`
and **excludes `cacheRead`** — replayed cached context would otherwise exhaust a
verifier loop's budget before real work landed.

## Gotchas (each cost real time to find)

1. **`daemon` is NOT a public verb.** It was removed upstream. `prime-agent daemon
   stats` / `daemon list` do not exist, so **there is no CLI path to per-session
   cost**. Do not build tooling that assumes one. Reading the TypeScript
   `SessionUsageSummary` interface proves the type exists, not that the CLI exposes
   it — that exact inference was made and was wrong.
2. **Cost readback only works from the transcripts.** `prime-agent list --all --json`
   returns sessions with no `usage` block. `~/.prime/agent/sessions/*.jsonl` does
   carry `usage` / `cost` / `totalTokens`. That file is the only honest source.
3. **Creating a session programmatically needs top-level await.** The only path in is
   `handleDaemonCommand(["daemon","create",name])` imported from
   `./packages/coding-agent/dist/cli/daemon-command.js`, which requires a module with
   top-level await — hence `create-session.mts` (`.mts`, not `.js`). The importable
   package is `@earendil-works/pi-coding-agent`, NOT `@earendil-works/pi-agent-core`
   (that path does not exist).
4. **`dist/` must be built before `create-session.mts` works** — it imports from
   `packages/coding-agent/dist/`, so a fresh clone needs `npm run build` first.
5. **Paid inference fails with a hard `402`.** OpenRouter returns
   `would exceed your available credits` with no local pre-check. The
   `--autonomous-max-*` flags bound tokens and turns, never dollars. Budget in
   tokens and expect the balance to be the real ceiling.
6. **A gate inside the worker's writable tree is not a gate.** Point
   `--autonomous-gate` at a command outside `--cwd`, or the session can weaken its
   own judge and the completion check silently degrades to a self-report.

## Workflow

### Dispatch discipline

A dispatched prompt states a **goal**, never a shell command. Passing `grep ...` or
`python3 -m ...` turns this layer into a relay and throws away the judgment that
justifies it.

| wrong | right |
|---|---|
| `"grep -r TODO src/"` | `"Find every unresolved TODO under src/. Report file, line, one-line summary."` |
| `"npm run check"` | `"Get this branch passing lint and typecheck; report what you changed."` |

### Verify before trusting

A session's own report is a claim. Re-run the gate, test, or build yourself before
accepting "done" / "green" / "passes". This is not distrust of a model — it is the
same rule that catches a human's mistaken claim, applied uniformly.

### Branch discipline

Never commit directly to `main`. Branch with a short hyphenated name. On a fork,
keep habitat/local files in their own commits so upstream rebases stay clean.

### Commit messages

Concise: what changed and why. No postamble, no attribution lines.

## Learnings

`REFLECTION_LOG.md` is a **generated aggregate** of per-entry fragments under
`reflections/active/<YYYY-MM-DD>-<slug>.md`. Read it before starting work; never edit
it by hand — add a fragment and regenerate. One file per reflection means two
concurrent reflections can never silently clobber each other at merge time (the
`.gitattributes` union-merge rule backs this up).
