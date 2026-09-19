# AI Literacy Assessment — prime-agent-fork (Joey's fork of PrimeIntellect-ai/prime-agent)

**Date**: 2026-09-18
**Assessed by**: Claude (assessor agent, single-context scan — see Scope Note)
**Assessed level**: Level 3 — Habitat Engineering (fork-specific work only; see Gaps for the honest caveat)

---

## Scope Note (read first)

This repo is **Joey's fork** of the upstream open-source project
`PrimeIntellect-ai/prime-agent` (`origin` confirmed via `git remote -v`).
The active branch is `feat/agent-ops-endorsed-loader`. Per the task brief,
this assessment explicitly separates:

- **Upstream engineering discipline** (PrimeIntellect-ai's own CI, AGENTS.md,
  `.cursor/BUGBOT.md`, release process) — real, present, but **not Joey's
  habitat engineering**. Included for completeness, excluded from the level
  determination.
- **Joey's fork-specific work** (3 commits: `4e133ef`, `723fe2f`, `23ee91c`,
  all dated 2026-09-15/16, all authored `Joseph Lopez`) — the actual subject
  of this assessment.

Repository has 1535 tracked files (`git ls-files | wc -l`), under the
300-file dynamic-workflow fan-out threshold only in the sense that no
`fan-out-threshold` override was found in this repo's HARNESS.md (there is
no HARNESS.md at all — see below); regardless, this scan proceeded as a
direct single-context scan since the file count that matters for *fork
provenance* (3 commits, ~6 fork-authored files) is small and fully
enumerable by hand — a full dynamic-workflow fan-out was not warranted for
that reason, not because of a hard threshold miss.

---

## Habitat document discovery

### HARNESS.md

- **Status**: not found
- **Path**: `—`
- **Markers matched**: none
- **Notes**: no constraint blocks, no Status section, anywhere in the repo.

### AGENTS.md

- **Status**: found at conventional path
- **Path**: `AGENTS.md` (repo root)
- **Markers matched**: `## Style`-shaped conventions ("Conversational Style",
  "Code Quality" sections); direct workflow rules (commit/PR/release
  process, "Daemon Protocol Changes", git-parallel-agent rules). No
  "gotchas"/"past learnings" section, no reference to a `REFLECTION_LOG.md`,
  no compound-learning vocabulary.
- **Notes**: **This file is 100% upstream.** `git log --format="%an" -- AGENTS.md`
  shows only `kt` (PrimeIntellect-ai contributor), last touched at commit
  `e9d68d9` ("make release manifest parsing forward-compatible (#2370)").
  Zero Joey-authored lines. It is real Level-3-shaped content (conventions +
  workflow rules) but it is **inherited habitat, not fork-built habitat** —
  see the Governance Dimension section below for why this matters to the
  level call.

### CLAUDE.md

- **Status**: not found
- **Path**: `—`
- **Markers matched**: none
- **Notes**: none anywhere in the repo (checked conventional + `.claude/`,
  `docs/`, `.ai/`).

### Ambiguities

None — no candidate confusion for any of the three documents.

### Paths checked but not matched

- `HARNESS.md`, `docs/HARNESS.md`, `.ai/HARNESS.md`, `.agents/HARNESS.md`,
  `conventions/HARNESS.md`, `governance/HARNESS.md`, `CONVENTIONS.md`,
  `STANDARDS.md`, `docs/conventions.md`, `docs/standards.md` — none exist
- `.agents/AGENTS.md`, `docs/AGENTS.md`, `.claude/AGENTS.md`,
  `.cursor/AGENTS.md` — none exist (only the conventional `AGENTS.md` exists)
- `CLAUDE.md`, `.claude/CLAUDE.md`, `docs/CLAUDE.md`, `.ai/CLAUDE.md` — none exist

## Tool-config evidence (parallel-tool surfaces)

- `.cursor/BUGBOT.md` **exists** but `git log --format="%an"` shows only
  `kt` — upstream review-rules content (no legacy scaffolding, comment
  discipline, test-quality rules), not a harness/constraint file, and not
  Joey's. Does not count as fork-side L3 evidence.
- `.github/copilot-instructions.md` — not found.
- `.windsurf/` — not found.
- No fork-specific parallel-tool config exists.

## The load-bearing evidence: AGENTOPS.md + agent_ops_adapter/

This is the real Joey-authored habitat evidence, confirmed via `git log`
(all three touching commits authored `Joseph Lopez`, 2026-09-15/16):

- **`AGENTOPS.md`** (repo root, 117 lines) — documents a genuine two-layer
  contract: Layer 1 = endorse-before-load trust gate (skills load only if
  agent-ops has execution-verified them), Layer 2 = max-local compute
  profile (routes inference to `gpu-fedora`, cost-motivated). Explicitly
  states honest boundaries ("Local 14B models were measured to FAIL
  manifest-contracted multi-file code edits... 7 receipted dispatch
  attempts") — this is real, falsifiable, non-aspirational language, not
  marketing copy.
- **`agent_ops_adapter/endorsed_loader.py`** (96 lines) — sophisticated
  per the hooks/scripts markers: defensive double-check logic (grade AND
  endorsed_version both required, guards against a named live agent-ops
  bug class — "endorsed_version can leak from bronze skills"), explicit
  error-path typing (`ImportError` vs generic `Exception`, each returning
  a structured `licensed=False` + named `reason`), environment-variable
  configurability (`AGENT_OPS_PATH`).
- **`agent_ops_adapter/test_endorsed_loader.py`** (171 lines, 6 tests) —
  tests against the **real** `agent_ops.db.schema` (imports
  `agent_ops.db.schema as db_schema`, calls `ensure_schema(conn)`), not a
  mock. This is a ground-truth-shaped test, the opposite of a hollow green.
- **`packages/coding-agent/src/core/agent-ops-endorsement.ts`** (58 lines) —
  the TypeScript side of the bridge: explicit fail-open/fail-closed
  semantics gated by `AGENT_OPS_ENFORCE`, subprocess bridge with a 5s
  timeout, single JSON-line stdout contract.
- **Wire point**: `packages/coding-agent/src/core/skills.ts` line 536,
  inside `loadSkillsFromDirInternal`'s `addSkills` — the single choke point
  every skill source passes through once. Confirmed by direct grep, not
  narrated.
- **`examples/models.gpu-fedora.json`** — real cost-routing config
  (`qwen2.5-coder:14b-8k`, `deepseek-r1:14b` on gpu-fedora, matches the
  global CLAUDE.md's documented model-routing table).

### Sophistication markers cited (per `sophistication-markers.md`)

**`agent_ops_adapter/endorsed_loader.py`** — sophisticated script/hook
shape, 2+ markers:
- State references: reads agent-ops's sqlite DB (`db_path`)
- Error recovery: distinct `ImportError` vs `Exception` handling, each
  returning a structured non-raising result (line 82–95)
- Configurability: `AGENT_OPS_PATH` env var changes import behaviour without
  editing the script (line 38–40)

**`agent-ops-endorsement.ts`** — sophisticated script shape, 2+ markers:
- Configurability: `AGENT_OPS_ENFORCE` env var flips fail-open/fail-closed
  behaviour (lines 30–32, 50–56)
- Error recovery: explicit try/catch with two distinct policy branches
  depending on enforcement mode (lines 48–57)

This raises the floor on **architectural constraints** (the endorsement
gate is a real enforced choke point, not aspirational prose) and on
**guardrail design** (fail-open/fail-closed is an explicit, tested design
decision) — but per the weakest-discipline-is-the-ceiling rule, this alone
does not push the level past what context engineering and the CI-integration
gap support (see Level Assessment).

## Real finding, Loop-2-verified live during this assessment

`python3 -m pytest agent_ops_adapter/test_endorsed_loader.py -q` was run
directly (not narrated from the adapter's own claims):

```
2 failed, 4 passed in 0.10s
FAILED test_silver_skill_with_endorsed_version_is_licensed
FAILED test_both_conditions_must_hold_for_license
```

Both failures are `assert result["version"] is not None` — the adapter's
own test fixtures are not correctly wired to `agent-ops`'s current schema/
`resolve()` contract (likely a drift between when the adapter was written
and the installed `agent-ops` package version, or a missing
`AGENT_OPS_PATH`/`sys.path` condition in this environment). **This suite is
not wired into any CI workflow** (`grep -rn "agent_ops_adapter\|AGENT_OPS"
.github/workflows/*.yml` returns nothing) — so this red state is currently
invisible to any automated gate. This is presented as observable ground
truth, not as a critique of the design; the adapter's *design* (defensive
double-check, fail-closed under enforcement) is sound even though its
*current test state* is red and unwatched.

## Observable Evidence — Repository Signals

| Signal | Found | Level indicator |
| --- | --- | --- |
| CI workflows | Yes — 8 workflows, all upstream (`ci.yml`, `benchmarks.yml`, etc.) | L2 (upstream, not Joey's) |
| Test coverage enforcement | No | L2 (absent) |
| Vulnerability scanning | No (`govulncheck`/`owasp`/`scout`/`codeql` all absent from workflows) | L2 (absent) |
| Mutation testing | No (only app-domain files named "mutation", unrelated to test infra) | L2 (absent) |
| CLAUDE.md | No | L3 (absent) |
| HARNESS.md | No | L3 (absent) |
| AGENTS.md | Yes, but 100% upstream (0 Joey-authored lines) | L3 (inherited, not built) |
| MODEL_ROUTING.md | No (but `examples/models.gpu-fedora.json` + `AGENTOPS.md` Layer 2 documents routing informally) | L3 (partial, non-canonical) |
| Custom skills (`.claude/skills/`) | No | L3 (absent) |
| Custom agents (`.claude/agents/`) | No | L3 (absent) |
| Custom commands (`.claude/commands/`) | No | L3 (absent) |
| Hooks configured | Yes (`.husky/pre-commit`) — upstream, simple (npm run check, ≤20 lines, no state/dispatch) | L2-shaped, not L3 sophistication |
| REFLECTION_LOG.md | No | L3 (absent) |
| Specifications directory (`specs/`) | No | L4 (absent) |
| Implementation plans | No | L4 (absent) |
| Orchestrator with safety gates | No orchestrator in this repo; the endorsement gate is a load-time trust check, not a plan-approval/review-cycle orchestrator | L4 (absent) |
| Plugin/platform tooling | No | L5 (absent) |
| OTel configuration | No (`grep -r "OTEL\|otel\|telemetry"` returns nothing fork-specific) | L5 (absent) |
| **Fork-specific: agent-ops endorsement gate** | Yes — `AGENTOPS.md`, `agent_ops_adapter/`, wired at `skills.ts:536` | L3 architectural constraint (real, sophisticated, but uncovered by CI and currently red) |

### Evidence Summary

Two very different pictures coexist in this repo. The **upstream base** —
PrimeIntellect-ai's own `AGENTS.md`, `.cursor/BUGBOT.md`, 8 CI workflows,
release process — is real engineering discipline, but it is not Joey's;
per the task brief it is excluded from the fork's own level determination.
The **fork-specific work** (3 commits, ~6 files) is small in surface area
but genuinely sophisticated in shape: a real trust gate wired at a single
choke point, defensive double-check logic against a named upstream bug
class, ground-truth-schema-based tests (not mocked), and explicit
fail-open/fail-closed semantics with honest, falsifiable claims in
`AGENTOPS.md` about what has and hasn't been verified. What's missing is
everything that would make this *durable habitat* rather than a
well-built one-off feature: no HARNESS.md/CLAUDE.md declaring the
constraint, no CI wiring to keep the adapter's own tests green, no
REFLECTION_LOG.md capturing what was learned, no internal documentation of
prime-agent's own verb surface (confirmed absent — see Gaps).

## Clarifying Responses

No interactive clarifying questions were asked (per task brief, answers
were supplied directly in the task context in lieu of interactive
questioning):

1. **Repo identity/role**: this is the executor layer in Joey's standing
   Claude → prime-agent → agent-ops → conductor chain (per global CLAUDE.md).
2. **Internal verb-surface documentation**: confirmed absent in this repo
   (no `docs/prime-agent-surface.md`-equivalent found; `grep` for
   "verb surface"/"10-verb"/"CLI verb" across all `.md` files returned
   nothing). The task brief flagged this as a possible gap — confirmed
   real: the knowledge exists only in `agent-ops`'s own `AGENTS.md`
   externally, not mirrored here.
3. **AGENTOPS.md + agent_ops_adapter/**: read in full, treated as the
   primary evidence (see above).
4. **Workflow habits/cost/team**: per task brief, assessed as Joey's
   personal fork customization, not upstream's practices. No cost-tracking
   artifact was found in the fork's own commits beyond the informal routing
   note in `AGENTOPS.md` Layer 2 (no dollar/token accounting file).
5. **Upstream vs fork-specific split**: called out throughout — see Scope
   Note and the "100% upstream" notes on `AGENTS.md`/`.cursor/BUGBOT.md`/CI.

## Level Assessment

### Primary Level: 3 — Habitat Engineering (fork-specific scope only)

The fork clears Level 2 comfortably in spirit (its adapter code is
verification-shaped — ground-truth schema tests, defensive double-checking)
but there is no CI enforcement making that verification *automatic and
current* — the adapter's own tests are red and unwatched, which is itself
a Level-2-discipline gap (verification exists but is not continuously
enforced).

The fork reaches **Level 3 (context engineering / architectural
constraints)** on the strength of `AGENTOPS.md` + the wired endorsement
gate: this is a real, sophisticated, falsifiable constraint enforced at a
genuine code choke point (`skills.ts:536`), with explicit fail-open/
fail-closed policy — not aspirational prose. That is squarely what the L3
"architectural constraints" discipline looks for, even though it doesn't
live in a canonically-named `HARNESS.md`.

The fork does **not** reach Level 4: there is no `specs/` directory
governing this work, no implementation plan, no orchestrator with a plan-
approval or review-cycle gate. The endorsement gate is a single load-time
check, not a multi-agent pipeline with safety gates.

### Discipline Maturity

| Discipline | Strength (1-5) | Evidence |
| --- | --- | --- |
| Context Engineering | 2 | No CLAUDE.md/HARNESS.md at all; `AGENTS.md` present but 100% upstream (0 Joey lines); the *only* fork-authored context artifact is `AGENTOPS.md` itself, which is real and good but is one file, not a maintained habitat surface (no cross-reference from AGENTS.md, no update since 2026-09-16). |
| Architectural Constraints | 3 | Real, wired, defensive constraint (`skills.ts:536` choke point, fail-open/fail-closed, `AGENT_OPS_ENFORCE` gate) — genuinely L3-shaped. Ceiling held down because it's not declared in a canonical harness file and has no enforcement-ratio tracking. |
| Guardrail Design | 2 | The endorsement gate itself is a real guardrail with sound failure-mode design. But its own test suite (the guardrail's guardrail) is red and has zero CI coverage — the feedback loop that would catch drift doesn't exist. |

### The Weakest Discipline

**Context Engineering** and **Guardrail Design** tie as the ceiling. There
is no habitat document declaring this constraint exists or how it's
enforced (context engineering gap), and the one piece of automated
verification that does exist (the pytest suite) is neither wired into CI
nor currently passing (guardrail design gap). Architectural Constraints is
ahead of both — the code-level enforcement is real and sophisticated — but
per the ALCI rule, the weakest discipline is the ceiling, which places the
overall level at 3 rather than higher, and flags that even L3 is fragile
here (one good file away from regressing to L2 if `AGENTOPS.md` goes stale).

## Operational Axes (ALCI Part D)

**Placement mode**: evidence-first (no survey administered, per task
scope — no interactive session with the team was available).

| Axis | Placement | Evidence |
| --- | --- | --- |
| Composition | L1 | Single-agent fork (no custom agents, no critic agents, no orchestrator layer added by Joey in this repo). The endorsement gate is a load-time filter, not agent composition. |
| Testing | L2 | Real unit tests exist (`test_endorsed_loader.py`, 6 tests, ground-truth-schema-based — a genuine strength for its shape) but are ad hoc: no coverage threshold, no mutation testing, not wired into CI, and currently 2/6 failing. This is "we have ad-hoc unit tests; coverage is uneven" (L1/L2 boundary) rather than "disciplined review" (solid L2) — placed at L2 for the schema-fidelity of the tests that do exist, capped there by the lack of CI enforcement. |
| Observability | L1 | No logging/metrics/dashboard for the endorsement gate's decisions beyond a documented gap in `AGENTOPS.md` itself ("Known gap: loaded skills log nothing (only refusals warn)"). No token/cost/latency tracking artifact in this repo (the `AGENTOPS.md` Layer 2 cost note is prose, not instrumentation). |
| Governance | L3 | See Governance Dimension below — a real, falsifiable, code-enforced constraint (not aspirational), consistent with the Governance Dimension's L3 placement. |

Operational axes mean: **L1.75**

## Habitat Build Gap

```text
Level placement (from cognitive assessment): L3
Operational axes mean (Part D):              L1.75
  Composition:    L1
  Testing:        L2
  Observability:  L1
  Governance:     L3
Habitat Build Gap:                           +1.25
Interpretation:                              Ambition outpaces enablement
```

The fork's cognitive/architectural ambition (a real, sophisticated,
enforced trust gate) is real, but the surrounding operational habitat
hasn't caught up: there's no agent composition beyond the single gate, no
observability into what the gate is doing in practice, and testing exists
but isn't continuously enforced. The gap says: **build the habitat the
fork's own architecture already implies** — wire the adapter's tests into
CI, add the missing "skill endorsed" info-level log line `AGENTOPS.md`
itself already names as a known gap, and write down the constraint in a
canonical file — rather than uplift literacy first. The one axis that
matches the cognitive level is Governance, because the endorsement gate
*is* the governance mechanism; the other three axes are honestly behind
what the gate's own sophistication would predict.

## Strengths

- **Falsifiable, non-aspirational design documentation.** `AGENTOPS.md`
  states measured limitations directly ("Local 14B models were measured to
  FAIL manifest-contracted multi-file code edits... 7 receipted dispatch
  attempts") rather than marketing the integration. This is the exact
  "reward = execution result, never self-report" discipline from Joey's own
  global CLAUDE.md, applied inside the fork's own docs.
- **Defensive, bug-aware code.** `endorsed_loader.py`'s double-check logic
  exists specifically to guard against a named live bug class in the
  upstream `agent-ops` project ("`endorsed_version` can leak from bronze
  skills") — this is architecture responding to a real, cited failure mode,
  not speculative hardening.
- **Ground-truth-shaped tests.** `test_endorsed_loader.py` builds its
  fixtures against the real `agent_ops.db.schema`, not a mock — the
  opposite of a hollow-green test.
- **A single, disciplined wire point.** The endorsement gate is wired at
  exactly one choke point (`addSkills` inside `loadSkillsFromDirInternal`)
  that every skill source passes through — a clean architectural decision,
  not a scattered patch.
- **Explicit fail-open/fail-closed policy**, correctly reasoned as
  environment-dependent (fail-open by default because this is "an optional
  overlay on someone else's runtime"; fail-closed only under
  `AGENT_OPS_ENFORCE=1`).

## Gaps

- **No internal documentation of prime-agent's own verb/capability
  surface.** Confirmed absent — the task brief's suspicion was correct.
  This knowledge lives only in `agent-ops`'s external `AGENTS.md`. Anyone
  working in this fork without that external context has no way to
  discover what "the executor layer" actually exposes from inside this
  repo.
- **The fork's own test suite is red and CI-uncovered.** 2 of 6 tests in
  `agent_ops_adapter/test_endorsed_loader.py` fail on direct execution, and
  no `.github/workflows/*.yml` references `agent_ops_adapter` or
  `AGENT_OPS` at all — this is exactly the "World-State Must Mirror
  Reality" failure named in Joey's own global CLAUDE.md (a claim of
  correctness that isn't backfilled/re-verified).
- **No canonical habitat document for the fork's own constraint.** The
  endorsement gate is real and enforced in code, but nothing declares it
  as a constraint the way `HARNESS.md`'s four-field blocks would — there is
  no `**Rule**:`/`**Enforcement**:`/`**Tool**:`/`**Scope**:` record anywhere.
- **No observability into the gate's actual runtime behaviour** beyond
  warn-level refusal logs — `AGENTOPS.md` names this gap itself
  ("loaded skills log nothing").
- **`AGENTS.md` is 100% inherited, not extended.** Joey's fork has not
  added a single line of compound-learning memory to it — no gotchas
  section, no reference back to `AGENTOPS.md`'s own known gaps.

## Recommendations

1. **Wire `agent_ops_adapter/test_endorsed_loader.py` into CI and fix the
   2 failing tests first.** (Testing axis, L2→L3.) This is the single
   highest-leverage fix — an unenforced, currently-red test suite for a
   trust gate is worse than no test suite, because it creates false
   confidence. Root-cause the `version is not None` assertion failures
   against the installed `agent-ops` schema/`resolve()` contract before
   doing anything else.
2. **Add the "skill endorsed" info-level log line `AGENTOPS.md` already
   names as a known gap.** (Observability axis, L1→L2.) Cheap, already
   scoped, closes the audit-parity gap the fork's own docs admit to.
3. **Write a minimal `HARNESS.md` (or extend `AGENTOPS.md` into one)
   declaring the endorsement gate as a formal constraint** — four-field
   shape (`Rule`/`Enforcement`/`Tool`/`Scope`), pointing at
   `skills.ts:536` and the `AGENT_OPS_ENFORCE` env var. (Context
   Engineering discipline, L2→L3, makes the L3 architectural-constraint
   evidence durable rather than a single well-written markdown file.)
4. **Cross-link `AGENTS.md` to `AGENTOPS.md`.** One line under a new
   "Fork-Specific Notes" section pointing future sessions (Joey's or
   otherwise) at the endorsement gate and its known gaps — turns the
   inherited `AGENTS.md` into a place fork-specific compound learning can
   accrete, rather than leaving `AGENTOPS.md` an orphaned root file.
5. **Document prime-agent's verb/capability surface internally**, even as
   a thin pointer file (`docs/prime-agent-surface.md` referencing
   `agent-ops`'s `AGENTS.md` as the canonical source) — closes the
   confirmed gap the task brief flagged, without duplicating content that
   lives correctly in agent-ops.

## Immediate Adjustments Applied

- **README badge added** — Level 3 / Habitat Engineering badge linked to
  this document, placed alongside the existing CI/Build/arXiv badges.
- **`AGENTS.md` cross-linked to `AGENTOPS.md`** — added a "Fork-Specific
  Notes" section pointing at `AGENTOPS.md` and its documented known gaps,
  per Recommendation 4 above. This turns the previously 100%-upstream
  `AGENTS.md` into a place fork-specific compound learning can now accrete.
- **Not applied as an "immediate" fix**: the 2 failing tests in
  `agent_ops_adapter/test_endorsed_loader.py` and CI-wiring for that suite
  (Recommendation 1) — this is a real code change requiring root-cause
  investigation against the installed `agent-ops` schema, not a
  no-code-change habitat-hygiene edit, so it is left in Recommendations
  for the user to schedule.

## Workflow Operation Changes

None accepted this cycle — no pre-existing operating rhythm (harness
audits, reflection reviews, mutation-score checks, cost-monitoring cadence)
existed to adjust, since this fork carries no HARNESS.md/REFLECTION_LOG.md/
MODEL_ROUTING.md to operate. The recommendation to write a minimal
HARNESS.md (Recommendation 3) is the prerequisite for any future operating-
rhythm recommendation to attach to.

## Reflection

- **Surprising**: the upstream/fork split was easy to establish
  mechanically (`git log --format=%an` on each candidate habitat file) and
  it mattered a lot — `AGENTS.md` looks L3-shaped by content alone, but is
  0% Joey's work; without the author-provenance check this would have
  been miscounted as fork-built habitat.
- **Where observable evidence diverged from self-report**: `AGENTOPS.md`
  itself is honest about its own gaps (audit-parity logging, no dry-run of
  a full session), but it does not mention that its own test suite is
  currently red — that was only caught by directly executing
  `pytest agent_ops_adapter/test_endorsed_loader.py` rather than trusting
  the document's "6/6 falsifier-tested" framing at face value ("Contract
  properties (all falsifier-tested, 6/6)" in `AGENTOPS.md` line 23 — read
  literally this claims passing tests; the 2 failures were a live
  Loop-2 catch, not something the docs disclosed).
- **What future assessments should watch**: whether the CI-wiring and
  HARNESS.md recommendations get adopted (would move Testing/Governance
  axes and close the Habitat Build Gap), and whether the fork accrues
  more Joey-authored constraints beyond the single endorsement gate
  (would move Composition off L1).

## Next Assessment

Suggested re-assessment date: **2026-12-18** (quarterly).

Previous assessment: first assessment for this repository.
