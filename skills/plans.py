"""
Skills wrapper: read the active internal plan from SQLite.

Returns normalized session records from the authoritative internal plan.
FinalSurge/ICS is never read here.
"""

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("skills.plans")

# Running workout types that can be published to Garmin
RUNNING_TYPES = {"easy", "tempo", "interval", "long"}


def get_active_sessions(db_path=None) -> List[Dict[str, Any]]:
    """
    Return planned sessions from the active plan in SQLite.

    Each session dict contains:
        date           str  YYYY-MM-DD
        intent         str  human-readable one-liner
        workout_type   str  easy | tempo | interval | long | strength | rest | cross
        duration_min   int
        structure_steps list[dict]
        safety_flags   list[str]
        rationale      str
        plan_id        str

    Returns [] if no active plan exists.
    """
    from memory.db import get_active_plan, init_db, DB_PATH as _DEFAULT_DB

    db = db_path or _DEFAULT_DB
    init_db(db)
    active = get_active_plan(db_path=db)
    if active is None:
        log.warning("No active plan in SQLite — run 'coach plan --week' first")
        return []

    plan_id = active["plan_id"]
    # get_active_plan returns day rows with the full PlanDay in day["workout"]
    sessions = []
    for day in active.get("days", []):
        wo = day.get("workout", {})
        sessions.append(
            {
                "date":            day["day"],
                "intent":          day.get("intent") or wo.get("intent", ""),
                "workout_type":    wo.get("workout_type", "rest"),
                "duration_min":    wo.get("duration_min", 0),
                "structure_steps": wo.get("structure_steps", []),
                "safety_flags":    wo.get("safety_flags", []),
                "rationale":       wo.get("rationale", ""),
                "plan_id":         plan_id,
            }
        )

    log.info("Active plan %s: %d sessions", plan_id, len(sessions))
    return sessions


def get_active_plan_meta(db_path=None) -> Optional[Dict[str, Any]]:
    """Return plan metadata (id, dates, phase, volume) for the active plan."""
    from memory.db import get_active_plan, DB_PATH as _DEFAULT_DB

    active = get_active_plan(db_path=db_path or _DEFAULT_DB)
    if active is None:
        return None

    plan = active.get("plan", {})
    return {
        "plan_id":             active["plan_id"],
        "week_start":          active.get("start_date"),
        "week_end":            active.get("end_date"),
        "phase":               plan.get("phase"),
        "weekly_volume_miles": plan.get("weekly_volume_miles"),
        "safety_flags":        plan.get("safety_flags", []),
        "data_quality":        plan.get("data_quality"),
    }
