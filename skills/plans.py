"""
Skills wrapper: read the active internal plan from SQLite.

Returns normalized session records from the authoritative internal plan.
FinalSurge/ICS is never read here.
"""

import logging
from datetime import date, timedelta
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
        workout_type   str  easy | tempo | interval | long | rest | cross
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


def get_active_sessions_safe(db_path=None) -> List[Dict[str, Any]]:
    """Call get_active_sessions(), returning [] on any error."""
    try:
        return get_active_sessions(db_path=db_path)
    except Exception:
        return []


def get_schedule(days: int = 7, start_date=None, db_path=None) -> Dict[str, Any]:
    """
    Return schedule rows for the next ``days`` days from ``start_date`` (today if None).

    Reads ONLY from the authoritative internal plan in SQLite.
    No Garmin API calls, no LLM calls.

    Returns a dict::

        {
            "plan_id":    str | None,
            "start_date": str,          # first date of range (ISO)
            "end_date":   str,          # last date of range (ISO)
            "created_at": str | None,   # plan creation timestamp
            "rows": [
                {
                    "date":           str,   # YYYY-MM-DD
                    "weekday":        str,   # "Mon", "Tue", …
                    "workout_type":   str,   # or "none"
                    "duration_min":   int | str,  # int, 0, or "" (blank for unknown)
                    "intent":         str,   # or "(no entry)"
                    "safety_flags":   list[str],
                    "structure_steps": list[dict],
                },
                …
            ],
        }

    If no active plan exists, ``plan_id`` is None and every row has type "none".
    """
    from memory.db import get_active_plan, DB_PATH as _DEFAULT_DB, init_db

    db = db_path or _DEFAULT_DB
    init_db(db)

    today: date = start_date if isinstance(start_date, date) else date.today()
    dates = [today + timedelta(days=i) for i in range(days)]

    active = get_active_plan(db_path=db)
    plan_id = None
    created_at = None
    plan_start = None
    plan_end = None

    # Index plan days by date string for O(1) lookup
    day_index: Dict[str, Dict] = {}
    if active is not None:
        plan_id = active["plan_id"]
        plan_start = active.get("start_date")
        plan_end = active.get("end_date")
        created_at = active.get("created_at")
        for day in active.get("days", []):
            wo = day.get("workout", {})
            # Derive duration_min estimate
            steps = wo.get("structure_steps", [])
            wtype = wo.get("workout_type", "rest")
            if steps:
                dur: Any = sum(s.get("duration_min", 0) for s in steps)
            elif wtype == "rest":
                dur = 0
            else:
                dur = wo.get("duration_min", "")

            day_index[day["day"]] = {
                "workout_type":    wtype,
                "duration_min":    dur,
                "intent":          day.get("intent") or wo.get("intent", ""),
                "safety_flags":    wo.get("safety_flags", []),
                "structure_steps": steps,
            }

    WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    rows = []
    for d in dates:
        ds = d.isoformat()
        wd = WEEKDAYS[d.weekday()]
        if ds in day_index:
            entry = day_index[ds]
            rows.append({
                "date":            ds,
                "weekday":         wd,
                "workout_type":    entry["workout_type"],
                "duration_min":    entry["duration_min"],
                "intent":          entry["intent"],
                "safety_flags":    entry["safety_flags"],
                "structure_steps": entry["structure_steps"],
            })
        else:
            rows.append({
                "date":            ds,
                "weekday":         wd,
                "workout_type":    "none",
                "duration_min":    "",
                "intent":          "(no entry)",
                "safety_flags":    [],
                "structure_steps": [],
            })

    return {
        "plan_id":    plan_id,
        "plan_start": plan_start,
        "plan_end":   plan_end,
        "created_at": created_at,
        "range_start": today.isoformat(),
        "range_end":   dates[-1].isoformat() if dates else today.isoformat(),
        "rows":       rows,
    }


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
