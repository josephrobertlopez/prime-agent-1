import { describe, expect, it } from "vitest";
import {
	addAutonomousUsage,
	autonomousLimitReason,
	autonomousStatus,
	createAutonomousRuntimeState,
	formatAutonomousHalt,
	recordAutonomousHalt,
	setAutonomousEnabled,
} from "../src/core/autonomous.js";

function state(limits: { maxTurns?: number; maxTokens?: number; timeoutMs?: number } = {}) {
	return createAutonomousRuntimeState({
		enabled: true,
		maxContinuations: 1000,
		maxTurns: limits.maxTurns ?? 1000,
		maxTokens: limits.maxTokens ?? 1_000_000,
		timeoutMs: limits.timeoutMs ?? 1_800_000,
	});
}

const usage = (input: number) => ({
	input,
	output: 0,
	cacheRead: 0,
	cacheWrite: 0,
	totalTokens: input,
	cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
});

describe("autonomous halt records", () => {
	// These label strings are the durable readback contract: a supervising
	// process greps them out of the session transcript after the process is
	// gone. Renaming one silently breaks every consumer, so pin them here.
	it("maps each limit to its stable halt label", () => {
		const cases = [
			{ reason: "maxTurns", label: "turn_cap" },
			{ reason: "maxTokens", label: "token_cap" },
			{ reason: "timeoutMs", label: "timeout" },
			{ reason: "maxContinuations", label: "continuation_cap" },
		] as const;
		for (const { reason, label } of cases) {
			const record = recordAutonomousHalt(state(), reason);
			expect(record?.label).toBe(label);
			expect(formatAutonomousHalt(record!)).toContain(`[autonomous-halt: ${label}]`);
		}
	});

	it("keeps the first halt when a second bound is crossed during teardown", () => {
		const s = state();
		expect(recordAutonomousHalt(s, "maxTurns")?.label).toBe("turn_cap");
		// A later bound must not rewrite why the run actually stopped.
		expect(recordAutonomousHalt(s, "timeoutMs")).toBeUndefined();
		expect(s.halt?.label).toBe("turn_cap");
	});

	it("captures the counters as they stood at the halt", () => {
		const s = state({ maxTurns: 3 });
		for (let i = 0; i < 3; i++) addAutonomousUsage(s, usage(100));
		const record = recordAutonomousHalt(s, autonomousLimitReason(s)!);
		expect(record).toMatchObject({ label: "turn_cap", turnsUsed: 3, tokensUsed: 300 });
		expect(record?.limits.maxTurns).toBe(3);
	});

	it("surfaces the halt through autonomousStatus for host readback", () => {
		const s = state({ maxTurns: 1 });
		addAutonomousUsage(s, usage(10));
		recordAutonomousHalt(s, "maxTurns");
		expect(autonomousStatus(s).halt?.label).toBe("turn_cap");
	});

	it("clears a stale halt when autonomy is re-enabled for a fresh budget", () => {
		const s = state({ maxTurns: 1 });
		recordAutonomousHalt(s, "maxTurns");
		setAutonomousEnabled(s, true);
		expect(s.halt).toBeUndefined();
		expect(autonomousLimitReason(s)).toBeUndefined();
	});

	it("counts cache reads against the token budget, since the provider bills them", () => {
		const s = state({ maxTokens: 1000 });
		addAutonomousUsage(s, {
			input: 10,
			output: 10,
			cacheRead: 2000,
			cacheWrite: 0,
			totalTokens: 2020,
			cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
		});
		expect(autonomousLimitReason(s)).toBe("maxTokens");
	});
});
