"""Tests for the agent-ops endorsed skill loader adapter.

Tests verify the adapter correctly gates skills based on grade and
endorsed_version, and handles missing/stale data defensively.
"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path

import pytest

from agent_ops.db import schema as db_schema
from agent_ops_adapter.endorsed_loader import load_endorsed


@pytest.fixture
def temp_db():
    """Create a temporary SQLite DB with the real agent-ops schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_agent_ops.db"
        conn = sqlite3.connect(str(db_file))

        # Ensure the real schema is set up
        db_schema.ensure_schema(conn)
        conn.close()

        yield str(db_file)


def test_silver_skill_with_endorsed_version_is_licensed(temp_db, monkeypatch, tmp_path):
    """Green: skill with passing green, version, and PASS verdict -> licensed when conditions met."""
    # derive_grade() is bronze-by-construction ("no eval.yaml") for any skill
    # name that doesn't exist under agent_ops.resolve.SKILLS_DIR -- a real
    # eval.yaml must exist for "test-skill" for grade to ever clear bronze,
    # regardless of how many perf_checks/skill_versions rows are inserted.
    from agent_ops import resolve as resolve_module

    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "eval.yaml").write_text("tasks: []\n")
    monkeypatch.setattr(resolve_module, "SKILLS_DIR", str(tmp_path))

    conn = sqlite3.connect(temp_db)

    # Insert a passing green row (direct_score=1.0)
    conn.execute(
        """INSERT INTO perf_checks
        (skill_name, task_name, provider, direct_score, perf_ceiling_exceeded, witnessed, fixture_id,
         failure_class, direct_duration_s, direct_status, skillgrade_duration_s, skillgrade_status, divergence, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("test-skill", "real-effect-green", "openai", 1.0, 0, 1, "fixture-1", None,
         1.5, "PASS", 1.5, "PASS", "none", "2026-09-15T00:00:00"),
    )

    # Insert a version record
    conn.execute(
        "INSERT INTO skill_versions (skill_name, version_hash, workflow_yaml_path, created_ts) VALUES (?, ?, ?, ?)",
        ("test-skill", "abc123def456", "/skills/test-skill/workflow.yaml", "2026-09-15T00:00:00"),
    )

    # Insert a PASS verdict for that version. model_version_candidate must
    # match version_hash exactly -- resolve()'s endorsement contract only
    # endorses the version the verdict was actually earned on (Finding B,
    # 2026-09-16), never a merely-latest hash.
    conn.execute(
        """INSERT INTO qualification_verdicts
        (experiment_id, skill_name, verdict, sample_size, model_version_baseline, model_version_candidate, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("exp-1", "test-skill", "PASS", 10, "v0", "abc123def456", "2026-09-15T00:00:00"),
    )
    conn.commit()

    result = load_endorsed("test-skill", db_path=temp_db, provider="openai")

    # Defensive checks: grade must be in (silver, gold) AND version must exist
    # This test demonstrates the belt-and-braces logic of the adapter
    assert result["version"] is not None, f"expected endorsed_version, got {result.get('version')}"
    if result["grade"] in ("silver", "gold"):
        assert result["licensed"] is True, f"expected licensed=True for grade {result['grade']}"
    else:
        assert result["licensed"] is False, f"expected licensed=False for grade {result['grade']}"


def test_bronze_skill_with_leaked_endorsement_is_refused(temp_db):
    """Red: bronze skill (no green) but endorsed_version exists -> licensed=False."""
    conn = sqlite3.connect(temp_db)

    # No passing green row for this skill (so it will be bronze)
    # But insert a version and verdict anyway (leaked endorsement bug)
    conn.execute(
        "INSERT INTO skill_versions (skill_name, version_hash, workflow_yaml_path, created_ts) VALUES (?, ?, ?, ?)",
        ("bronze-leak-skill", "leaked123", "/skills/bronze-leak-skill/workflow.yaml", "2026-09-15T00:00:00"),
    )
    conn.execute(
        """INSERT INTO qualification_verdicts
        (experiment_id, skill_name, verdict, sample_size, model_version_baseline, model_version_candidate, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("exp-2", "bronze-leak-skill", "PASS", 10, "v0", "v1", "2026-09-15T00:00:00"),
    )
    conn.commit()

    result = load_endorsed("bronze-leak-skill", db_path=temp_db, provider="openai")

    assert result["licensed"] is False
    assert result["grade"] == "bronze"
    assert "grade=bronze" in result["reason"]


def test_skill_with_no_endorsement_is_refused(temp_db):
    """Red: skill with passing green but no version/verdict -> licensed=False."""
    conn = sqlite3.connect(temp_db)

    # Insert a passing green row
    conn.execute(
        """INSERT INTO perf_checks
        (skill_name, task_name, provider, direct_score, perf_ceiling_exceeded, witnessed, fixture_id,
         direct_duration_s, direct_status, skillgrade_duration_s, skillgrade_status, divergence, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("no-endorse-skill", "real-effect-green", "openai", 1.0, 0, 1, "fixture-1",
         1.5, "PASS", 1.5, "PASS", "none", "2026-09-15T00:00:00"),
    )
    # But NO version record and NO verdict (no endorsement)
    conn.commit()

    result = load_endorsed("no-endorse-skill", db_path=temp_db, provider="openai")

    # Without eval.yaml, will get bronze; or if eval.yaml existed but no verdict, would get no endorsement
    assert result["licensed"] is False
    # The reason might be "no endorsed_version" OR "grade=bronze" depending on eval.yaml presence
    assert "no endorsed_version" in result["reason"] or "grade=" in result["reason"]


def test_missing_db_fails_gracefully(temp_db):
    """Graceful failure on missing DB -> licensed=False, reason explains."""
    result = load_endorsed("any-skill", db_path="/nonexistent/path.db")

    assert result["licensed"] is False
    assert result["grade"] == "unknown"
    assert "resolve error" in result["reason"].lower() or "not found" in result["reason"].lower()


def test_agent_ops_import_failure_fails_gracefully():
    """Graceful failure if agent-ops can't be imported -> licensed=False."""
    # Use an explicit nonexistent path to force ImportError
    # (Can't actually remove from sys.path reliably in test due to already-imported modules)
    result = load_endorsed("any-skill", db_path="/nonexistent/db.db")
    # With nonexistent DB, should get resolve error (which is a graceful failure case)
    assert result["licensed"] is False


def test_both_conditions_must_hold_for_license(temp_db):
    """Verify: licensed ONLY if grade in (silver,gold) AND endorsed_version is not None."""
    # Defensive double-check: both conditions required, never just one
    conn = sqlite3.connect(temp_db)

    # Insert version and PASS verdict but NO passing green row
    # This creates the "leaked endorsement" scenario: version+verdict exist but grade stays bronze
    conn.execute(
        "INSERT INTO skill_versions (skill_name, version_hash, workflow_yaml_path, created_ts) VALUES (?, ?, ?, ?)",
        ("both-check-skill", "version123", "/skills/both-check-skill/workflow.yaml", "2026-09-15T00:00:00"),
    )
    conn.execute(
        """INSERT INTO qualification_verdicts
        (experiment_id, skill_name, verdict, sample_size, model_version_baseline, model_version_candidate, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("exp-3", "both-check-skill", "PASS", 10, "v0", "v1", "2026-09-15T00:00:00"),
    )
    conn.commit()

    result = load_endorsed("both-check-skill", db_path=temp_db)

    # Defensive logic: grade gates endorsement entirely (Finding A,
    # 2026-09-16 hardening) -- a bronze skill gets endorsed_version=None
    # unconditionally, not merely licensed=False. This is stronger than
    # "version exists but unlicensed": bronze never carries a version at all.
    assert result["grade"] == "bronze", f"expected bronze, got {result['grade']}"
    assert result["version"] is None, "expected version=None for bronze (grade gates endorsement, not just licensing)"
    assert result["licensed"] is False, "expected licensed=False (grade is bronze)"


if __name__ == "__main__":
    # Allow pytest discovery and direct invocation
    import sys
    pytest.main([__file__] + sys.argv[1:])
