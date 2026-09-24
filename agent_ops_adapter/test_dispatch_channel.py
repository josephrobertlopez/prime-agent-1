"""Tests for the durable-output dispatch preflight.

The property under test: an answer-needing dispatch always has somewhere to put
its answer, or it fails loudly at dispatch time.
"""

import pytest

from agent_ops_adapter.dispatch_channel import (
    CHANNEL_DB_RECEIPT,
    CHANNEL_NONE,
    CHANNEL_SESSION_LOG,
    NoDurableChannelError,
    classify_channel,
    main,
    preflight,
)

BG_NOPERSIST = ["--bg", "--no-session-persistence", "-p", "what is the status"]


def test_bg_without_persistence_has_no_channel():
    assert classify_channel(BG_NOPERSIST) == CHANNEL_NONE
    assert classify_channel(["--bg", "--no-session", "-p", "x"]) == CHANNEL_NONE


def test_answer_needing_channelless_dispatch_is_refused():
    with pytest.raises(NoDurableChannelError) as exc:
        preflight(BG_NOPERSIST)
    msg = str(exc.value)
    assert "REFUSED" in msg
    assert CHANNEL_NONE in msg
    assert CHANNEL_DB_RECEIPT in msg and CHANNEL_SESSION_LOG in msg
    assert "--bg" in exc.value.offending_flags
    assert "--no-session-persistence" in exc.value.offending_flags


def test_refusal_names_the_phantom_flag():
    with pytest.raises(NoDurableChannelError) as exc:
        preflight(BG_NOPERSIST)
    assert "not a real prime-agent flag" in str(exc.value)
    assert "unknownFlags" in str(exc.value)


def test_fire_and_forget_is_allowed():
    """No answer needed -> the DB is the channel and no-channel is fine."""
    assert preflight(BG_NOPERSIST, answer_needed=False) == CHANNEL_NONE


def test_resolved_skill_gives_db_receipt_channel():
    assert preflight(BG_NOPERSIST, skill="queue-drain") == CHANNEL_DB_RECEIPT


def test_persisting_background_dispatch_keeps_its_session():
    assert preflight(["--bg", "-p", "synthesize an answer"]) == CHANNEL_SESSION_LOG


def test_foreground_dispatch_is_readable():
    assert preflight(["-p", "synthesize an answer"]) == CHANNEL_SESSION_LOG


def test_flag_equals_form_is_normalised():
    assert classify_channel(["--bg=true", "--no-session-persistence=1"]) == CHANNEL_NONE


def test_caller_forced_background_is_refused_without_persistence():
    with pytest.raises(NoDurableChannelError):
        preflight(["--no-session", "-p", "x"], background=True)


def test_cli_exit_codes(capsys):
    assert main(["--", *BG_NOPERSIST]) == 3
    err = capsys.readouterr().err
    assert "REFUSED" in err

    assert main(["--skill", "queue-drain", "--", *BG_NOPERSIST]) == 0
    assert capsys.readouterr().out.strip() == CHANNEL_DB_RECEIPT

    assert main(["--no-answer-needed", "--", *BG_NOPERSIST]) == 0
    assert capsys.readouterr().out.strip() == CHANNEL_NONE
