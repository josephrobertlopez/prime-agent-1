import { join, resolve } from "path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock only the python-subprocess wrapper; everything else stays real so the
// endorsement gate's actual parse/fail-closed logic is under test.
vi.mock("../src/utils/child-process.js", async (importOriginal) => {
	const actual = await importOriginal<typeof import("../src/utils/child-process.js")>();
	return {
		...actual,
		execFileSyncHidden: vi.fn(),
	};
});

import { checkEndorsement } from "../src/core/agent-ops-endorsement.js";
import { loadSkills } from "../src/core/skills.js";
import { execFileSyncHidden } from "../src/utils/child-process.js";

// The wrapper's overloads default to a Buffer return; the endorsement bridge
// calls it with encoding "utf-8" and consumes a string, so type the mock as such.
const execMock = vi.mocked(execFileSyncHidden) as unknown as ReturnType<typeof vi.fn<(...args: unknown[]) => string>>;

const fixturesDir = resolve(__dirname, "fixtures/skills");
const emptyAgentDir = resolve(__dirname, "fixtures/empty-agent");
const emptyCwd = resolve(__dirname, "fixtures/empty-cwd");

function loadValidSkill() {
	return loadSkills({
		agentDir: emptyAgentDir,
		cwd: emptyCwd,
		skillPaths: [join(fixturesDir, "valid-skill")],
		includeDefaults: false,
	});
}

describe("agent-ops endorsement gate", () => {
	const originalEnforce = process.env.AGENT_OPS_ENFORCE;

	beforeEach(() => {
		execMock.mockReset();
	});

	afterEach(() => {
		if (originalEnforce === undefined) {
			delete process.env.AGENT_OPS_ENFORCE;
		} else {
			process.env.AGENT_OPS_ENFORCE = originalEnforce;
		}
	});

	it("does not invoke the endorsement bridge when enforcement is off (env unset)", () => {
		delete process.env.AGENT_OPS_ENFORCE;
		const { skills, diagnostics } = loadValidSkill();
		expect(execMock).not.toHaveBeenCalled();
		expect(skills).toHaveLength(1);
		expect(diagnostics).toHaveLength(0);
	});

	it("drops unlicensed skills and emits a warning diagnostic under AGENT_OPS_ENFORCE=1", () => {
		process.env.AGENT_OPS_ENFORCE = "1";
		execMock.mockReturnValue(JSON.stringify({ licensed: false, reason: "grade below silver" }));
		const { skills, diagnostics } = loadValidSkill();
		expect(execMock).toHaveBeenCalled();
		expect(skills).toHaveLength(0);
		const warning = diagnostics.find((d) => d.type === "warning" && d.message.includes("not endorsed by agent-ops"));
		expect(warning).toBeDefined();
		expect(warning?.message).toContain("grade below silver");
	});

	it("keeps licensed skills under AGENT_OPS_ENFORCE=1", () => {
		process.env.AGENT_OPS_ENFORCE = "1";
		execMock.mockReturnValue(JSON.stringify({ licensed: true, reason: "silver" }));
		const { skills, diagnostics } = loadValidSkill();
		expect(execMock).toHaveBeenCalled();
		expect(skills).toHaveLength(1);
		expect(diagnostics).toHaveLength(0);
	});

	it("fails closed (skill absent) when the bridge throws under enforcement", () => {
		process.env.AGENT_OPS_ENFORCE = "1";
		execMock.mockImplementation(() => {
			throw new Error("python3 not found");
		});
		const { skills, diagnostics } = loadValidSkill();
		expect(skills).toHaveLength(0);
		const warning = diagnostics.find((d) => d.message.includes("endorsement-check-unavailable"));
		expect(warning).toBeDefined();
		expect(warning?.message).toContain("fail-closed");
	});

	describe("checkEndorsement unit behavior", () => {
		it("fails open on bridge error when enforcement is off", () => {
			delete process.env.AGENT_OPS_ENFORCE;
			execMock.mockImplementation(() => {
				throw new Error("boom");
			});
			const result = checkEndorsement("any-skill");
			expect(result.licensed).toBe(true);
			expect(result.reason).toContain("fail-open");
		});

		it("fails closed on malformed bridge JSON under enforcement", () => {
			process.env.AGENT_OPS_ENFORCE = "1";
			execMock.mockReturnValue("not json at all");
			const result = checkEndorsement("any-skill");
			expect(result.licensed).toBe(false);
			expect(result.reason).toContain("fail-closed");
		});

		it("parses the last stdout line as the JSON payload", () => {
			process.env.AGENT_OPS_ENFORCE = "1";
			execMock.mockReturnValue(`some noise\n${JSON.stringify({ licensed: true, reason: "ok" })}\n`);
			const result = checkEndorsement("skill-x");
			expect(result).toEqual({ licensed: true, reason: "ok" });
		});
	});
});
