"""
Hook: on_vdot_change — detects when the race-derived VDOT has drifted
significantly from the active macro plan's stored VDOT.

Called from agent/runner.py inside the hash_changed block, after
on_activity_completed.

Logic:
  1. Get vdot_race_derived from the current context packet.
  2. Get vdot_stored from the active macro plan.
  3. If abs(derived - stored) >= 0.5 AND no pending_vdot_update in state:
       → Write pending_vdot_update to state with source activity details.
  4. Return {changed: bool, derived: float|None, stored: float|None}

The Discord bot reads pending_vdot_update and notifies the athlete.
Applying the VDOT update requires explicit confirmation — it is NOT automatic.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent

_STATE_PENDING_KEY = "pending_vdot_update"
_DRIFT_THRESHOLD = 0.5

log = logging.getLogger("hooks.on_vdot_change")


def run(ctx: Optional[Dict] = None, db_path=None) -> Dict[str, Any]:
    """
    Detect VDOT drift and queue a notification for Discord delivery.
    ctx: the current context packet (from build_context_packet). If None,
         builds it internally — callers that already have ctx should pass it.

    Returns: {changed: bool, derived: float|None, stored: float|None}
    """
    from memory.db import (
        get_active_macro_plan, get_state, set_state, DB_PATH as _DEFAULT_DB,
    )

    db = db_path or _DEFAULT_DB
    result: Dict[str, Any] = {
        "changed": False,
        "derived": None,
        "stored": None,
    }

    # ── 1. Get stored VDOT from active macro plan ──────────────────────────
    try:
        macro = get_active_macro_plan(db_path=db)
    except Exception as exc:
        log.warning("on_vdot_change: could not read active macro plan: %s", exc)
        return result

    if not macro:
        log.debug("on_vdot_change: no active macro plan — skipping")
        return result

    stored_vdot: float = float(macro.get("vdot", 0))
    result["stored"] = stored_vdot

    # ── 2. Get derived VDOT from context packet ────────────────────────────
    if ctx is None:
        try:
            from memory.retrieval import build_context_packet
            ctx = build_context_packet(db_path=db)
        except Exception as exc:
            log.warning("on_vdot_change: could not build context packet: %s", exc)
            return result

    derived_vdot: Optional[float] = (
        ctx.get("athlete", {}).get("vdot_race_derived")
    )

    if derived_vdot is None:
        log.debug("on_vdot_change: no race-derived VDOT in context — skipping")
        return result

    derived_vdot = float(derived_vdot)
    result["derived"] = derived_vdot

    # ── 3. Check drift threshold ───────────────────────────────────────────
    drift = abs(derived_vdot - stored_vdot)
    if drift < _DRIFT_THRESHOLD:
        log.debug(
            "on_vdot_change: drift %.2f < %.2f threshold — no action",
            drift, _DRIFT_THRESHOLD,
        )
        return result

    result["changed"] = True

    # ── 4. Only queue once (avoid spamming) ───────────────────────────────
    existing = get_state(_STATE_PENDING_KEY, db_path=db)
    if existing:
        log.debug("on_vdot_change: pending_vdot_update already set — skipping")
        return result

    # Find the source activity name (most recent race/time-trial in context)
    source_name = _find_source_activity(ctx, derived_vdot)

    payload = {
        "derived": derived_vdot,
        "stored":  stored_vdot,
        "drift":   round(drift, 2),
        "source":  source_name,
    }

    try:
        set_state(_STATE_PENDING_KEY, json.dumps(payload), db_path=db)
        log.info(
            "on_vdot_change: VDOT drift %.2f detected (%.1f → %.1f), "
            "pending_vdot_update written",
            drift, stored_vdot, derived_vdot,
        )
    except Exception as exc:
        log.warning("on_vdot_change: set_state failed: %s", exc)

    return result


def _find_source_activity(ctx: Dict, derived_vdot: float) -> str:
    """Return the name of the most recent race/time-trial activity, or a fallback string."""
    _RACE_KEYWORDS = ["race", "5k", "10k", "half", "marathon", "time trial",
                      "tt ", "timed mile", "test effort", "race effort"]

    activities = ctx.get("athlete", {}).get("recent_activities", [])
    if not activities:
        # Fall back to training_summary activities if present
        activities = ctx.get("training_summary", {}).get("activities", [])

    for act in sorted(activities, key=lambda a: a.get("date", ""), reverse=True):
        name = (act.get("name") or act.get("activity_name") or "").lower()
        if any(kw in name for kw in _RACE_KEYWORDS):
            return act.get("name") or act.get("activity_name") or "recent race"

    return "recent activity"
