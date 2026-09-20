# Model Routing — prime-agent

<!-- Which model tier handles which kind of work, and why. Bootstrapped
     2026-09-19 via /superpowers-init. Routing here is unusually consequential:
     this repo IS the executor layer, so a routing mistake does not merely cost
     tokens, it can silently produce zero work (see the capability note below). -->

## The capability floor — measured, not assumed

**Local 14B models cannot drive an agentic tool loop in this harness.** Measured:
`qwen2.5-coder:14b` fired twice as a scheduled driver and produced **0 receipts both
times** — it answered in prose without invoking any tool. This is the single most
important routing fact in this file, because the failure is *silent*: the session
exits 0, the output looks plausible, and nothing happened.

The same models **do** reason perfectly well when they only have to emit text or
structured output and invoke nothing. So:

| the model must... | local 14B viable? |
|---|---|
| invoke tools, edit files, drive a multi-turn loop | **NO** — measured 0/2 |
| emit prose, a judgment, or structured output | **yes** — free and fine |

Never route a tool-driving dispatch to a local model to save money. The saving is
zero because the work does not happen.

## Agent Routing Table

| Work | Tier | Concrete model | Why |
|---|---|---|---|
| Autonomous file-editing dispatch | cheap-capable | `~anthropic/claude-haiku-latest` | cheapest tier measured to reliably drive a tool loop here |
| Multi-file refactor, architecture change | capable | `~anthropic/claude-sonnet-latest` | needs to hold cross-package context |
| Adversarial verify / refute a claim | capable | `~anthropic/claude-sonnet-latest` | a weak refuter rubber-stamps; cheapness here is false economy |
| Panel / critique / judgment, no tools | local (free) | `gpu-fedora qwen2.5:14b-instruct` | emits text only — the tool-loop floor does not apply |
| Discrimination: "is this claim real or fabricated" | local (free) | `gpu-fedora deepseek-r1:14b` | the coder/instruct variants invert the final verdict on this task class |
| Bulk mechanical edit, known pattern | cheap | `~deepseek/deepseek-v4-flash-latest` | high volume, low reasoning depth |
| Final judgment on whether work is DONE | **none — a gate** | n/a | this layer must never judge its own completion |

`prime-agent model list` enumerates what is actually available. Providers seen here:
`gpu-fedora` (free, local), `cloud-pinned`, `openrouter` (paid).

## Token Budget Guidance

Budget in **tokens**, because dollars are not measurable from this CLI (see
`CLAUDE.md` gotcha 1). `--autonomous-max-tokens` counts `input + output + cacheWrite`
and excludes `cacheRead`.

| Task shape | max-tokens | max-turns | timeout-ms | worst-case $ at ~$5/1M |
|---|---|---|---|---|
| Single-file authoring, clear spec | 90,000 | 10 | 480,000 | ~$0.45 |
| Audit / classify across a repo | 120,000 | 10 | 840,000 | ~$0.60 |
| Author a new parameterized capability | 180,000 | 12 | 840,000 | ~$0.90 |
| Adversarial verify one claim | 60,000 | 6 | 300,000 | ~$0.30 |

The dollar column is an **upper bound**, computed as if every token billed at the
output rate. Real spend lands well under because input costs ~5× less. Treat it as a
ceiling, never as an estimate of actual spend.

### The cage is the balance, not the flags

Verified 2026-09-19: paid inference returns a hard
`402 — would exceed your available credits`, discovered only on failure. The
`--autonomous-max-*` flags bound tokens and turns; **nothing bounds dollars locally.**
Check the provider balance before a multi-worker fan-out, or expect a mid-run 402 that
looks like a task failure but is not.

## Escalate by boosting the cheap tier first

Before buying a more expensive model, try:

1. **Schematize-then-interpret** — have the model emit the ALGORITHM as typed
   operations and let trusted code execute it. The model should emit STRUCTURE, never
   RESULTS: structure is what it knows, results are what it fabricates.
2. **Reflexion** — draft, critique, revise.
3. **Sharding** — for input past the context window, shard rather than reaching for a
   bigger window. Measured lift comes from the sharding, not the window size.

A paid escalation should name which of these was tried first.
