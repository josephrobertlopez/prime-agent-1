"""Durable-output preflight for prime-agent dispatches.

WHY THIS EXISTS
---------------
A dispatch whose answer must be READ BACK needs somewhere durable to put that
answer. Exactly three channels exist, and two of them are conditional:

  1. ``db-receipt``  -- the goal resolved to a skill, so conductor writes a row
     into ``db/agent_ops.db`` (``runs`` for ``agent-ops run``, ``perf_checks``
     for ``agent-ops perf``). The DB is the channel; stdout is irrelevant.
  2. ``session-log`` -- session persistence is ON, so the transcript survives
     under ``~/.prime/agent/sessions/<id>.jsonl`` and is readable afterwards.
  3. ``none``        -- backgrounded AND persistence disabled. The session exits,
     the transcript was never written, and a NO_SKILL halt writes no DB row.
     The answer evaporates.

Measured behaviour this module encodes (re-verified 2026-09-21, prime-agent-fork):

  * ``--no-session`` is the real persistence-off flag. ``cli/args.ts:169-170``
    sets ``noSession``; ``main.ts:460-461`` turns that into
    ``SessionManager.inMemory()``; ``core/session-manager.ts:2380-2382``
    constructs it with ``persist=false``; ``core/session-manager.ts:1541``
    (``if (this.persist)``) is the only place a session file path is ever
    assigned, so ``getSessionFile()`` (``:1666``) stays ``undefined`` and
    NOTHING is written to disk. There is no other write path and no verdict file.
  * ``--bg`` and ``--no-session-persistence`` are NOT prime-agent flags at all.
    ``cli/args.ts:342-355`` sweeps any unrecognised ``--x`` into
    ``unknownFlags`` with ZERO parse diagnostics (confirmed by calling the built
    ``parseArgs``: ``diag: []``, ``unknown: [["bg",true],
    ["no-session-persistence",true]]``). They are only rejected much later, as
    unknown *extension* flags, in
    ``core/agent-session-services.ts:139-144``. They are treated here as
    background / persistence-off INTENT because that is what a caller writing
    them means, and because silently ignoring them is precisely the failure this
    module exists to make loud.

This module never writes to the DB. Refusal is a loud non-zero exit at dispatch
time, not a recorded row -- ``dispatch_refusals.cause`` is CHECK-constrained to
``'unknown_host'``, so a no-channel refusal has no legal row to write, and
inventing one would mean mutating the production schema.
"""

from __future__ import annotations

import sys
from typing import Optional, Sequence

__all__ = [
    "CHANNEL_DB_RECEIPT",
    "CHANNEL_SESSION_LOG",
    "CHANNEL_NONE",
    "NoDurableChannelError",
    "classify_channel",
    "preflight",
    "main",
]

CHANNEL_DB_RECEIPT = "db-receipt"
CHANNEL_SESSION_LOG = "session-log"
CHANNEL_NONE = "none"

#: Flags meaning "do not persist this session". ``--no-session`` is the real
#: one; the other two are unrecognised aliases callers actually write.
_PERSISTENCE_OFF_FLAGS = frozenset({"--no-session", "--no-session-persistence"})

#: Flags meaning "detach; nobody is reading stdout".
_BACKGROUND_FLAGS = frozenset({"--bg", "--background", "--detach"})

#: Flags that are swept into ``unknownFlags`` by ``cli/args.ts:342-355`` instead
#: of being parsed -- i.e. they do nothing, silently.
_NOT_REAL_PRIME_AGENT_FLAGS = frozenset({"--bg", "--background", "--detach", "--no-session-persistence"})


class NoDurableChannelError(RuntimeError):
    """Raised when an answer-needing dispatch has nowhere to put its answer."""

    def __init__(self, message: str, *, offending_flags: Sequence[str] = ()):
        super().__init__(message)
        self.offending_flags = list(offending_flags)


def _split_flags(argv: Sequence[str]) -> list[str]:
    """Normalise ``--flag=value`` to ``--flag`` and keep only long options."""
    out = []
    for raw in argv:
        if not isinstance(raw, str) or not raw.startswith("--"):
            continue
        out.append(raw.split("=", 1)[0])
    return out


def classify_channel(
    argv: Sequence[str],
    *,
    skill: Optional[str] = None,
    background: bool = False,
) -> str:
    """Return which durable channel this dispatch actually has.

    ``skill`` -- the skill the goal resolved to, if any. A resolved skill means
    conductor writes a receipt row, which is a channel regardless of session or
    stdout state.

    ``background`` -- force background even when no flag says so (e.g. an
    ``ssh ... &`` / ``--bg`` wrapper outside ``argv``).
    """
    flags = set(_split_flags(argv))

    if skill:
        return CHANNEL_DB_RECEIPT

    is_background = background or bool(flags & _BACKGROUND_FLAGS)
    persistence_off = bool(flags & _PERSISTENCE_OFF_FLAGS)

    if not is_background:
        # Foreground: stdout is attached and the caller reads it directly.
        return CHANNEL_SESSION_LOG
    if persistence_off:
        return CHANNEL_NONE
    return CHANNEL_SESSION_LOG


def preflight(
    argv: Sequence[str],
    *,
    answer_needed: bool = True,
    skill: Optional[str] = None,
    background: bool = False,
) -> str:
    """Validate a dispatch BEFORE it runs. Returns the channel, or refuses.

    Raises :class:`NoDurableChannelError` when ``answer_needed`` is true and the
    classified channel is :data:`CHANNEL_NONE`.
    """
    channel = classify_channel(argv, skill=skill, background=background)
    if channel != CHANNEL_NONE or not answer_needed:
        return channel

    flags = _split_flags(argv)
    offending = [f for f in flags if f in _BACKGROUND_FLAGS | _PERSISTENCE_OFF_FLAGS]
    phantom = sorted({f for f in offending if f in _NOT_REAL_PRIME_AGENT_FLAGS})

    lines = [
        "REFUSED: no durable output channel for an answer-needing dispatch.",
        "",
        f"  missing channel : {CHANNEL_NONE} "
        f"(neither {CHANNEL_DB_RECEIPT} nor {CHANNEL_SESSION_LOG} is available)",
        f"  offending flags : {' '.join(offending) or '(background forced by caller)'}",
        "",
        "  This combination is backgrounded AND non-persisting. The session exits",
        "  without writing a transcript (session-manager.ts:1541 only assigns a",
        "  session file when persist is true; --no-session builds the manager with",
        "  persist=false at session-manager.ts:2380-2382), no verdict file is ever",
        "  written, and a NO_SKILL halt writes no DB row. The answer evaporates.",
        "",
        "  Pick a channel:",
        f"    * {CHANNEL_DB_RECEIPT}  -- resolve the goal to a skill and dispatch it",
        "                     via conductor; read the row back with",
        "                     `agent-ops resolve <skill> --grade-only`.",
        f"    * {CHANNEL_SESSION_LOG} -- drop the persistence-off flag, keep the",
        "                     session, and read it back by session id.",
    ]
    if phantom:
        lines += [
            "",
            "  NOTE: " + ", ".join(phantom) + " is not a real prime-agent flag.",
            "  cli/args.ts:342-355 sweeps it into unknownFlags with no parse",
            "  diagnostic, so it silently does nothing here and is only rejected",
            "  later as an unknown extension flag",
            "  (core/agent-session-services.ts:139-144).",
        ]

    raise NoDurableChannelError("\n".join(lines), offending_flags=offending)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI: ``python -m agent_ops_adapter.dispatch_channel [opts] -- <dispatch...>``

    Exit 0 and print the channel when one exists; exit 3 and print the refusal
    on stderr when it does not.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    skill: Optional[str] = None
    answer_needed = True
    background = False
    rest: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            rest = args[i + 1 :]
            break
        if a == "--skill":
            i += 1
            skill = args[i] if i < len(args) else None
        elif a.startswith("--skill="):
            skill = a.split("=", 1)[1]
        elif a == "--no-answer-needed":
            answer_needed = False
        elif a == "--background":
            background = True
        else:
            rest.append(a)
        i += 1

    try:
        channel = preflight(
            rest, answer_needed=answer_needed, skill=skill, background=background
        )
    except NoDurableChannelError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(channel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
