"""Prime Agent adapter for agent-ops endorsed skill loading.

Provides a thin gate making Prime Agent load only agent-ops-endorsed skill
versions. Defensive design: tolerates live bugs in agent-ops resolve() by
double-checking that endorsed_version exists AND grade is silver/gold.
"""

import os
import sys
from typing import Optional

__all__ = ["load_endorsed"]


def load_endorsed(
    skill_name: str,
    db_path: Optional[str] = None,
    green_task: str = "real-effect-green",
    red_task: str = "real-effect-red",
    provider: str = "openai",
) -> dict:
    """Load endorsement status for a skill via agent-ops resolve().

    Returns a dict with keys:
        version (str or None): endorsed version hash if licensed, else None
        grade (str): 'gold', 'silver', or 'bronze'
        licensed (bool): True iff grade in ('silver', 'gold') AND endorsed_version is not None
        reason (str): explanation of licensing decision

    This function is DEFENSIVE: it double-checks both grade and
    endorsed_version before granting a license, protecting against
    live bugs in resolve() where:
    - endorsed_version can leak from bronze skills
    - endorsed_version can point to never-graded latest versions
    """
    try:
        # Import agent-ops resolve; parameterized for easy testing/mocking
        agent_ops_path = os.environ.get("AGENT_OPS_PATH")
        if agent_ops_path:
            sys.path.insert(0, agent_ops_path)

        from agent_ops.resolve import resolve

        # Call resolve with all parameters explicit
        result = resolve(
            skill_name,
            db=db_path,
            green_task=green_task,
            red_task=red_task,
            provider=provider,
        )

        grade = result.get("grade", "bronze")
        endorsed_version = result.get("endorsed_version")
        endorsement_reason = result.get("endorsement_reason", "unknown")

        # Defensive double-check: both conditions must hold
        # (not just one) to grant a license.
        licensed = (
            grade in ("silver", "gold")
            and endorsed_version is not None
        )

        reason = ""
        if licensed:
            reason = f"licensed (grade={grade}, version={endorsed_version})"
        else:
            if grade not in ("silver", "gold"):
                reason = f"grade={grade} (not silver/gold)"
            elif endorsed_version is None:
                reason = f"no endorsed_version despite grade={grade}"
            else:
                reason = "license check failed (unknown reason)"

        return {
            "version": endorsed_version,
            "grade": grade,
            "licensed": licensed,
            "reason": reason,
        }

    except ImportError as e:
        return {
            "version": None,
            "grade": "unknown",
            "licensed": False,
            "reason": f"agent-ops not found: {e}",
        }
    except Exception as e:
        return {
            "version": None,
            "grade": "unknown",
            "licensed": False,
            "reason": f"resolve error: {e}",
        }
