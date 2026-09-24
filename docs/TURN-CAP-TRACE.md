# Turn Cap Mechanism Trace

## Summary

The turn cap mechanism does **not bind mid-segment**. The `maxTurns` limit is checked only at specific decision points (continuation admission gates), not continuously. Within a single run segment (the interval between user input and the assistant reaching "done"), the session can consume many turns before the limit is evaluated.

## Turn Count Increment

**File: `packages/coding-agent/src/core/autonomous.ts:267`**

```typescript
export function addAutonomousUsage(state: AutonomousRuntimeState, usage: Usage | undefined): void {
	if (!state.enabled) {
		return;
	}
	state.turnsUsed++;        // ← Incremented here
	state.tokensUsed += autonomousTokenDelta(usage);
}
```

**File: `packages/coding-agent/src/core/agent-session.ts:4352`**

```typescript
if (assistantMsg.stopReason !== "error") {
	addAutonomousUsage(this._autonomousState, assistantMsg.usage);  // ← Called here
}
```

**Timing:** `addAutonomousUsage()` is called **immediately after each assistant message arrives**, in the event handler at line 4352.

## Turn Cap Enforcement Points

The cap is checked at three locations:

### 1. Pre-Continuation Admission (Main Gate)

**File: `packages/coding-agent/src/core/agent-session.ts:2660`**

```typescript
const decision = await shouldAutonomouslyContinue(this._autonomousState, lastAssistantMessage, {
	cwd: this._cwd,
	signal: this.agent.signal,
});
if (!decision.shouldContinue) {
	this._clearAutonomousContinuationAwait();
	return;  // ← Exits here if limit reached
}
```

**Timing:** This check is performed **only when the session is deciding whether to admit a continuation** — i.e., after all messages in the current segment have been processed and the session is about to queue the next user message (the autonomous continuation).

### 2. Pre-Owed Continuation Resume (RLM Work Completion)

**File: `packages/coding-agent/src/core/agent-session.ts:2590`**

```typescript
if (autonomousLimitReason(this._autonomousState)) {
	// The run is over: hold nothing so the hook can apply the limit.
	return false;
}
```

**Timing:** Checked when RLM work (subagent) completes and the session considers delivering a held continuation.

### 3. Pre-Keep-Alive Continuation (Subagent Still Active)

**File: `packages/coding-agent/src/core/agent-session.ts:2716`**

```typescript
if (autonomousLimitReason(this._autonomousState)) {
	// The run is over; no keep-alive is owed anymore.
	this._clearAutonomousContinuationAwait();
	return true;
}
```

**Timing:** Checked when delivering a keep-alive continuation while subagents are still active.

## The Gap: Why the Cap Cannot Bind Mid-Segment

The `shouldAutonomouslyContinue()` function and `autonomousLimitReason()` checks are **decision gates**, not continuous guards. They are consulted at specific moments:
- When a run segment ends (no more assistant messages pending)
- When the session is about to queue a user message (continuation)
- When RLM work or keep-alive windows trigger

**Within a single run segment** (e.g., the initial prompt call with multiple assistant turns before stabilizing):
1. User submits prompt with `maxTurns: 3`
2. Assistant responds (turn 1) → `turnsUsed = 1`
3. Session queues continuation automatically
4. Assistant responds (turn 2) → `turnsUsed = 2`
5. Session queues continuation automatically
6. Assistant responds (turn 3) → `turnsUsed = 3`
7. Session queues continuation automatically
8. Assistant responds (turn 4) → `turnsUsed = 4` **← CAP NOT CHECKED YET**
9. Assistant responds (turn 5) → `turnsUsed = 5`
10. ...continues until `shouldAutonomouslyContinue()` is called at segment end...

## The Second Bound: Wall-Clock Timeout

**File: `packages/coding-agent/src/core/autonomous.ts:430`**

```typescript
if (state.startedAt !== undefined && now - state.startedAt >= state.limits.timeoutMs) {
	return "timeoutMs";
}
```

The wall-clock timeout **also has the same issue**: it is checked only at the same three decision gates (continuation admission, RLM work completion, keep-alive delivery). There is **no independent timer that interrupts a run segment in flight**.

### Verification of `--autonomous-timeout-ms`

The timeout is set via CLI flag `--autonomous-timeout-ms` and stored in `state.limits.timeoutMs`. It is checked at:
- Line 430 of `autonomous.ts` (in `autonomousLimitReason()`)
- Called from lines 411, 421 in `shouldAutonomouslyContinue()` and related gates

There is **no `setTimeout()` or `AbortController` triggered by the timeout** to interrupt the current segment. The check is purely a comparison of elapsed time at decision points.

## Conclusion

Both bounds are **reactive**, not proactive:
- **Turn cap**: Checked only when deciding to admit a continuation; not checked between assistant messages within a segment
- **Wall-clock timeout**: Checked only at the same decision gates; no independent interrupt mechanism fires when the timeout elapses

A run segment can exceed both bounds by the time the next check occurs. This is the root cause of observed overruns (e.g., a cap of 18 permitting 37 turns).
