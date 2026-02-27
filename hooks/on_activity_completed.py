"""
Hook: on_activity_completed — detects new running/strength activities and queues
a post-workout check-in message for Discord delivery.

Called from agent/runner.py inside the hash_changed block each heartbeat cycle.

Logic:
  1. Query activities table for running + strength activities from last 48 hours.
  2. For each, call upsert_checkin (INSERT OR IGNORE — idempotent).
  3. Call get_unsent_checkins — find any not yet delivered.
  4. If any exist AND no pending_checkin key in state:
       → pick the most recent unsent one
       → write JSON payload to state as 'pending_checkin'
  5. Return {"new_activities": N, "pending_written": bool, "activity_name": str|None}

Idempotency is guaranteed by INSERT OR IGNORE on activity_id.
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent

_STATE_PENDING_KEY = "pending_checkin"

# Activity types that trigger a check-in
_RUNNING_TYPES  = {"running", "trail_running", "treadmill_running"}
_STRENGTH_TYPES = {"strength_training", "cardio"}
_CHECKIN_TYPES  = _RUNNING_TYPES | _STRENGTH_TYPES

log = logging.getLogger("hooks.on_activity_completed")


def run(db_path=None) -> Dict[str, Any]:
    """
    Detect completed workouts and queue a check-in for Discord delivery.
    Returns: {"new_activities": int, "pending_written": bool, "activity_name": str|None}
    """
    from memory.db import (
        get_activities, upsert_checkin, get_unsent_checkins,
        get_state, set_state, DB_PATH as _DEFAULT_DB,
    )

    db = db_path or _DEFAULT_DB
    result: Dict[str, Any] = {
        "new_activities": 0,
        "pending_written": False,
        "activity_name": None,
    }

    # ── 1. Fetch recent activities (last 48 hours) ─────────────────────────
    today = date.today()
    two_days_ago = today - timedelta(days=2)

    try:
        recent = get_activities(start=two_days_ago, end=today, db_path=db)
    except Exception as exc:
        log.warning("on_activity_completed: could not query activities: %s", exc)
        return result

    # Filter to running + strength types
    relevant = [a for a in recent if a.get("activity_type", "").lower() in _CHECKIN_TYPES]

    # ── 2. Upsert checkin rows (INSERT OR IGNORE) ──────────────────────────
    for act in relevant:
        activity_date_raw = act.get("activity_date", today.isoformat())
        if isinstance(activity_date_raw, str):
            try:
                activity_date_val = date.fromisoformat(activity_date_raw)
            except ValueError:
                activity_date_val = today
        else:
            activity_date_val = activity_date_raw

        distance_mi: Optional[float] = None
        if act.get("distance_m"):
            distance_mi = round(act["distance_m"] / 1609.344, 2)

        duration_min: Optional[float] = None
        if act.get("duration_s"):
            duration_min = round(act["duration_s"] / 60, 1)

        try:
            upsert_checkin(
                activity_id=str(act["activity_id"]),
                activity_date=activity_date_val,
                activity_type=act.get("activity_type", "unknown"),
                activity_name=act.get("name"),
                distance_mi=distance_mi,
                duration_min=duration_min,
                avg_hr=act.get("avg_hr"),
                db_path=db,
            )
        except Exception as exc:
            log.warning("upsert_checkin failed for %s: %s", act.get("activity_id"), exc)

    result["new_activities"] = len(relevant)

    # ── 3. Find unsent checkins ────────────────────────────────────────────
    try:
        unsent = get_unsent_checkins(db_path=db)
    except Exception as exc:
        log.warning("on_activity_completed: get_unsent_checkins failed: %s", exc)
        return result

    if not unsent:
        return result

    # ── 4. Write pending_checkin if not already set ────────────────────────
    existing = get_state(_STATE_PENDING_KEY, db_path=db)
    if existing:
        result["reason"] = "pending_already_set"
        return result

    # Pick the most recent unsent (list is already ordered newest first)
    pick = unsent[0]
    payload = {
        "activity_id":   pick["activity_id"],
        "activity_date": pick["activity_date"],
        "activity_type": pick["activity_type"],
        "activity_name": pick["activity_name"],
        "distance_mi":   pick["distance_mi"],
        "duration_min":  pick["duration_min"],
        "avg_hr":        pick["avg_hr"],
    }

    try:
        set_state(_STATE_PENDING_KEY, json.dumps(payload), db_path=db)
        result["pending_written"] = True
        result["activity_name"] = pick["activity_name"]
        log.info(
            "on_activity_completed: checkin queued for '%s' (%s, %s)",
            pick["activity_name"],
            pick["activity_type"],
            pick["activity_date"],
        )
    except Exception as exc:
        log.warning("on_activity_completed: set_state failed: %s", exc)

    return result
