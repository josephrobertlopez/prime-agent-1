/**
 * Create a real prime-agent session programmatically — the ONE primitive that
 * makes prime the LOCUS rather than a daemon we talk about.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * `create` is NOT a public verb. `prime-agent --help` lists agents/attach/send/
 * schedule/stop/... but never `create`, and the public `daemon` verb was removed
 * upstream. The only path in is `handleDaemonCommand(["daemon","create",...])`,
 * and that must be called from a module with TOP-LEVEL AWAIT — hence `.mts`.
 *
 * Measured 2026-09-19: the prime daemon had been UP for 3 days with **0
 * sessions**. Every piece of automation built around it (the convergence panel,
 * the tick ladder, the hourly clock) routed AROUND prime instead of through it,
 * because nothing could spawn a session. That is the gap this closes.
 *
 * CORRECTION to a prior surface-map claim: the importable package is
 * `@earendil-works/pi-coding-agent` (see packages/coding-agent/package.json),
 * NOT `@earendil-works/pi-agent-core`. That path does not exist. Verified by
 * reading the real package.json and the built dist/.
 *
 * Usage (from this repo root, dist/ must be built — `npm run build` at ROOT):
 *   node --experimental-strip-types create-session.mts <name> [--json]
 *   node create-session.mts <name> --json          # on a node that strips types natively
 *
 * Deliberately does exactly one thing: create a named session and report it.
 * Sending work is `prime-agent send`, scheduling is `prime-agent schedule` —
 * both already public. This file is the missing constructor, nothing more.
 */
import { handleDaemonCommand } from "./packages/coding-agent/dist/cli/daemon-command.js";

const argv = process.argv.slice(2);
const wantJson = argv.includes("--json");
const name = argv.find((a) => !a.startsWith("-"));

if (!name) {
  console.error(
    "usage: node create-session.mts <session-name> [--json] [-- <extra daemon args>]\n" +
      "  creates ONE named prime-agent session via handleDaemonCommand.\n" +
      "  --json  emit the daemon's machine-readable summary (use this for headless loops).",
  );
  process.exit(2);
}

// Pass-through for any extra daemon flags after a bare `--` (e.g. --cwd, --model).
const dashDash = argv.indexOf("--");
const extra = dashDash === -1 ? [] : argv.slice(dashDash + 1);

const cmd = ["daemon", "create", name, ...extra];
if (wantJson) cmd.push("--json");

try {
  // Top-level await is the whole reason this is a .mts and not a .js require.
  await handleDaemonCommand(cmd);
} catch (err) {
  // Fail LOUD and non-zero. A headless caller must never read a failed create
  // as success — that is the false-green shape this repo exists to kill.
  console.error(
    `create-session: FAILED to create session "${name}": ` +
      (err instanceof Error ? err.message : String(err)),
  );
  process.exit(1);
}
