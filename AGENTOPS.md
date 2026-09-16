# agent-ops × prime-agent: the two-layer contract (fork notes)

This fork integrates [agent-ops](https://github.com/josephrobertlopez/agent-ops) as an
**external verification layer** for prime-agent, plus a max-local compute profile.
Two independent layers; either is useful alone.

## Layer 1 — endorse-before-load (trust)

Prime-agent should load only skill versions agent-ops has execution-verified.
The adapter is `agent_ops_adapter/endorsed_loader.py` (committed on
`feat/agent-ops-endorsed-loader`):

```python
from agent_ops_adapter.endorsed_loader import load_endorsed

res = load_endorsed("my-skill", db_path="/path/to/agent_ops.db")
# {'version': <graded hash>|None, 'grade': 'silver', 'licensed': bool, 'reason': str}
if not res["licensed"]:
    # refuse to load; reason names why (bronze / no endorsement / drift / error)
    ...
```

Contract properties (all falsifier-tested, 6/6):
- `licensed = grade in ('silver','gold') AND endorsed_version is not None` —
  belt-and-braces on both fields.
- Never raises; every error path returns `licensed=False` with a named reason.
- `AGENT_OPS_PATH` env points at agent-ops's `src/` (no hardcoded paths).
- Upstream, agent-ops's `resolve()` endorses only the exact hash a PASS record
  graded — bronze, version-drift, and empty-candidate all refuse (see
  agent-ops `tests/test_endorsement_contract.py`).

**Wire point (WIRED — see "Wire point: IMPLEMENTED" below):** `packages/coding-agent/src/core/skills.ts`
(`loadSkillsFromDirInternal`) — call `load_endorsed` for Python skills and skip
entries with `licensed=False`. Verified by probe: a bronze skill returns
`licensed=False` through `prime-agent-runtime/src/rlm/harness.py`'s own
`HarnessState` layer (probe script in the integrating session's scratchpad).

## Layer 2 — max-local compute (cost)

Prime-agent's inference client reads `base_url` from its auth/config store
(`packages/coding-agent/src/core/prime-inference-auth.ts:130`, default =
Prime's hosted API). For a local-first profile, point it at any
OpenAI-compatible endpoint; a homelab Ollama works:

```jsonc
// config field (see prime-inference-auth.ts writeAuthField)
{
  "base_url": "${GPU_FEDORA_BASE:-http://100.65.241.73:11434}/v1",  // your box
  // models served locally, e.g.:
  //   qwen2.5-coder:14b-8k  (mechanical/structured — measured strong)
  //   deepseek-r1:14b       (discrimination-shaped judgment)
}
```

Honest boundaries (verified, not aspirational):
- The endpoint value above is THIS homelab's; substitute your own. The env-style
  placeholder is documentation of intent — the TS config stores a literal URL.
- Local 14B models were measured to FAIL manifest-contracted multi-file code
  edits that a frontier model completes (7 receipted dispatch attempts in the
  integrating session). Route mechanical labor local, judgment up the ladder.
- No dry-run of a full prime-agent session against the local endpoint has been
  performed in this fork yet (would need the CLI's auth flow); the base_url
  field's existence and the adapter's refusal path are what's verified.

## Why both layers

Prime-agent self-produces skills (Continual Harness); agent-ops grades them by
real execution before they're trusted. The referee stays outside the player,
and the labor stays on hardware you own. Verification: reward = execution
result, never a self-report — in both layers.

## Wire point: IMPLEMENTED

The endorsement gate is now wired at the single accept-point choke in
`packages/coding-agent/src/core/skills.ts` (`addSkills` inside `loadSkills`) —
every skill from every source (defaults, explicit skillPaths, single .md files)
passes through it exactly once, just before `skillMap.set()`. Bridge module:
`packages/coding-agent/src/core/agent-ops-endorsement.ts`, which shells out
synchronously (`execFileSyncHidden`, 5s timeout) to
`python3 -c` → `agent_ops_adapter.endorsed_loader.load_endorsed(skill_name,
db_path)` and parses one JSON line from stdout.

Env vars:
- `AGENT_OPS_ENFORCE=1` — the gate is OFF unless this is set. When set,
  unlicensed skills are skipped with a warning diagnostic + `log.warn`, and
  bridge failures (python3 missing, timeout, bad JSON) fail CLOSED.
- `AGENT_OPS_DB` — path to the agent-ops sqlite DB, passed as `db_path`.
- `AGENT_OPS_PATH` — path to agent-ops `src/`, consumed by the Python adapter
  itself (it prepends it to `sys.path`). Ensure `PYTHONPATH` also reaches
  `agent_ops_adapter` (this repo root) when running from elsewhere.

Fail-open/fail-closed rule: `checkEndorsement()` defaults to FAIL-OPEN on any
bridge error (`licensed: true`, reason prefixed
`endorsement-check-unavailable:`) because this is an optional overlay on
someone else's runtime — refusing all skills when python is absent would brick
the agent. With `AGENT_OPS_ENFORCE=1` (the only mode in which the loader calls
it), the same errors fail CLOSED instead.

## Driver recipe: VERIFIED LIVE (2026-09-16)

A real prime-agent session ran locally with all three properties confirmed:
no Prime login (isolated dir self-created empty `auth.json`), endorsement
gate firing in-session (12 refusals logged with real DB reasons; licensed
skill loaded), completion served by the local GPU box.

- Config dir: `~/.prime/agent/` (override: `PRIME_AGENT_CODING_AGENT_DIR`).
- `models.json` (schema: `core/model-registry.ts` validateConfig): see
  `examples/models.gpu-fedora.json`. `apiKey` is an env-var NAME resolved at
  registry load; the local endpoint ignores the value.
- Skills dirs: `<agentDir>/skills` + `<cwd>/.prime/agent/skills`; symlinks work.
- One-shot: `dist/bundle/cli.js -p "prompt" --provider gpu-fedora --model <pattern>`.
- Enforced session env: `AGENT_OPS_ENFORCE=1 AGENT_OPS_DB=<agent_ops.db>
  PYTHONPATH=<this repo root>`.
- Build: `npm run build` at repo ROOT (per-package build needs sibling dists).
- Known gap: loaded skills log nothing (only refusals warn) — a positive
  `skill endorsed` info line in skills.ts would give audit parity.
