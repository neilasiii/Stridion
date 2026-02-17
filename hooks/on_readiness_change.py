"""
Hook: on_readiness_change — triggers Brain adjust_today() on readiness drop.

Called after a successful sync when data_quality.readiness_confidence is
medium or high. If today's training_readiness falls below READINESS_LOW OR
drops more than READINESS_DROP_THRESHOLD relative to yesterday's, the Brain
is asked to adjust today's workout.

Brain is NOT called when:
  - readiness_confidence is "low" (not enough data to act on)
  - Today's adjustment has already been recorded in the vault this cycle
  - No active plan exists

Returns:
    {
        "triggered":    bool,      # True if Brain was called
        "reason":       str,       # Why triggered or why not
        "adjustment":   dict | None,  # TodayAdjustment.model_dump() if triggered
    }
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional

log = logging.getLogger("hooks.on_readiness_change")

READINESS_LOW = 45           # absolute threshold (0-100)
READINESS_DROP_THRESHOLD = 15  # relative drop from yesterday triggers action


def run(context_packet: Dict[str, Any], db_path=None) -> Dict[str, Any]:
    """
    Evaluate readiness and optionally call brain.adjust_today().

    Args:
        context_packet: Output of memory.build_context_packet() — already built
                        by the runner for this cycle (avoids double build).
        db_path:        SQLite path override.
    """
    from memory.db import get_metrics_range, DB_PATH as _DEFAULT_DB

    db = db_path or _DEFAULT_DB
    today = date.today()

    # ── Gate: confidence must be medium or high ────────────────────────────
    dq = context_packet.get("data_quality", {})
    confidence = dq.get("readiness_confidence", "low")
    if confidence == "low":
        log.debug("Readiness confidence=%s — skipping adjust_today", confidence)
        return {"triggered": False, "reason": f"confidence={confidence}", "adjustment": None}

    # ── Gate: active plan must exist ───────────────────────────────────────
    pa = context_packet.get("plan_authority", {})
    if not pa.get("active_plan_id"):
        log.debug("No active plan — skipping adjust_today")
        return {"triggered": False, "reason": "no_active_plan", "adjustment": None}

    # ── Read today's and yesterday's readiness ─────────────────────────────
    rt = context_packet.get("readiness_trend", {})
    today_rt = rt.get("today", {}) if isinstance(rt, dict) else {}
    readiness_today = today_rt.get("training_readiness")

    if readiness_today is None:
        log.debug("training_readiness not available today — skipping")
        return {"triggered": False, "reason": "no_readiness_today", "adjustment": None}

    readiness_today = int(readiness_today)

    # Yesterday from SQLite metrics (more reliable than context packet history)
    yesterday = today - timedelta(days=1)
    yesterday_metrics = get_metrics_range(yesterday, yesterday, db_path=db)
    readiness_yesterday: Optional[int] = None
    if yesterday_metrics:
        readiness_yesterday = yesterday_metrics[0].get("training_readiness")

    # ── Evaluate triggers ──────────────────────────────────────────────────
    trigger_reason: Optional[str] = None

    if readiness_today < READINESS_LOW:
        trigger_reason = f"readiness {readiness_today} < threshold {READINESS_LOW}"

    elif readiness_yesterday is not None:
        drop = int(readiness_yesterday) - readiness_today
        if drop >= READINESS_DROP_THRESHOLD:
            trigger_reason = (
                f"readiness dropped {drop} pts "
                f"({readiness_yesterday}→{readiness_today} ≥ threshold {READINESS_DROP_THRESHOLD})"
            )

    if trigger_reason is None:
        log.debug(
            "Readiness %d (yesterday=%s) — within normal range, no adjustment needed",
            readiness_today, readiness_yesterday,
        )
        return {
            "triggered": False,
            "reason": f"readiness_ok ({readiness_today})",
            "adjustment": None,
        }

    # ── Gate: avoid duplicate adjustments on the same day ─────────────────
    from memory.db import query_events
    today_str = today.isoformat()
    recent = query_events(event_type="today_adjustment", limit=5, db_path=db)
    for ev in recent:
        import json
        try:
            payload = json.loads(ev.get("payload_json", "{}"))
        except Exception:
            payload = {}
        if payload.get("date") == today_str:
            log.info(
                "Adjustment already recorded today (%s) — skipping duplicate",
                today_str,
            )
            return {"triggered": False, "reason": "already_adjusted_today", "adjustment": None}

    # ── Call Brain: adjust_today ───────────────────────────────────────────
    log.info("Triggering adjust_today: %s", trigger_reason)

    try:
        from brain import adjust_today

        adjustment = adjust_today(context_packet, db_path=db)
        log.info(
            "adjust_today complete: type=%s reason=%s",
            adjustment.workout_type,
            adjustment.adjustment_reason,
        )
        return {
            "triggered":  True,
            "reason":     trigger_reason,
            "adjustment": adjustment.model_dump(),
        }

    except Exception as exc:
        log.error("adjust_today failed: %s", exc)
        return {
            "triggered":  False,
            "reason":     f"brain_error: {exc}",
            "adjustment": None,
        }
