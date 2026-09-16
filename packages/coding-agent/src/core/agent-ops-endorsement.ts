/**
 * Optional agent-ops endorsement gate for skill loading.
 *
 * Only active when AGENT_OPS_ENFORCE=1. Bridges to the Python adapter
 * (agent_ops_adapter.endorsed_loader.load_endorsed) via a python3 subprocess
 * that prints exactly one JSON line on stdout.
 *
 * Failure policy: by default any bridge failure (python3 missing, timeout,
 * bad JSON) FAILS OPEN — this gate is an overlay on someone else's runtime,
 * and refusing every skill when python is absent would brick the agent.
 * When AGENT_OPS_ENFORCE=1 is set, bridge failures fail CLOSED instead.
 */

import { execFileSyncHidden } from "../utils/child-process.js";

export interface EndorsementResult {
	licensed: boolean;
	reason: string;
}

const BRIDGE_TIMEOUT_MS = 5000;

const BRIDGE_SCRIPT = [
	"import json, os, sys",
	"from agent_ops_adapter.endorsed_loader import load_endorsed",
	"r = load_endorsed(sys.argv[1], db_path=os.environ.get('AGENT_OPS_DB'))",
	"print(json.dumps({'licensed': bool(r.get('licensed')), 'reason': str(r.get('reason', ''))}))",
].join("\n");

export function isEndorsementEnforced(): boolean {
	return process.env.AGENT_OPS_ENFORCE === "1";
}

export function checkEndorsement(skillName: string): EndorsementResult {
	try {
		const stdout = execFileSyncHidden("python3", ["-c", BRIDGE_SCRIPT, skillName], {
			encoding: "utf-8",
			timeout: BRIDGE_TIMEOUT_MS,
			env: process.env,
			stdio: ["ignore", "pipe", "pipe"],
		});
		const lastLine = stdout.trim().split("\n").at(-1) ?? "";
		const parsed = JSON.parse(lastLine) as { licensed?: unknown; reason?: unknown };
		if (typeof parsed.licensed !== "boolean") {
			throw new Error("bridge output missing boolean 'licensed'");
		}
		return { licensed: parsed.licensed, reason: typeof parsed.reason === "string" ? parsed.reason : "" };
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		if (isEndorsementEnforced()) {
			return {
				licensed: false,
				reason: `endorsement-check-unavailable: ${message} (fail-closed, AGENT_OPS_ENFORCE=1)`,
			};
		}
		return { licensed: true, reason: `endorsement-check-unavailable: ${message} (fail-open by default)` };
	}
}
