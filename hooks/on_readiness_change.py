"""
Hook: on_readiness_change — triggers Brain adjust_today() on readiness drop.

Called after a successful sync when data_quality.readiness_confidence is
medium or high. If today's training_readiness falls below READINESS_LOW OR
drops more than READINESS_DROP_THRESHOLD relative to yesterday's, the Brain
is asked to adjust today's workout.

Brain is NOT called when:
  - readiness_confidence is "low" (not enough data to act on)
  - Today's sleep data has not yet been synced (sleep_hours missing from context)
  - Today's adjustment has already been recorded in SQLite today
  - No active plan exists

Returns:
    {
        "triggered":    bool,      # True if Brain was called
        "reason":       str,       # Why triggered or why not
        "adjustment":   dict | None,  # TodayAdjustment.model_dump() if triggered
    }
"""

import logging
import json
from datetime import date, timedelta
from typing import Any, Dict, Optional

log = logging.getLogger("hooks.on_readiness_change")

READINESS_LOW = 45           # absolute threshold (0-100)
READINESS_DROP_THRESHOLD = 15  # relative drop from yesterday triggers action
RUNNING_WORKOUT_TYPES = {"easy", "tempo", "interval", "long"}


def _events_for_day(event_type: str, target_date: str, db_path) -> list[Dict[str, Any]]:
    """Return parsed event payloads for a specific date and event type."""
    from memory.db import query_events

    matches: list[Dict[str, Any]] = []
    recent = query_events(event_type=event_type, limit=20, db_path=db_path)
    for ev in recent:
        try:
            payload = json.loads(ev.get("payload_json", "{}"))
        except Exception:
            payload = {}
        if payload.get("date") == target_date:
            matches.append(payload)
    return matches


def _is_running_workout_type(workout_type: Any) -> Optional[bool]:
    """Return True/False when workout type is known, else None."""
    if workout_type is None:
        return None
    return str(workout_type).strip().lower() in RUNNING_WORKOUT_TYPES


def _publish_succeeded_for_day(
    publish_result: Dict[str, Any],
    target_date: str,
    expected_running: Optional[bool],
) -> tuple[bool, str]:
    """
    Determine whether publish() actually succeeded for target_date.

    publish() can report per-workout failures in skipped/warnings without raising.
    """
    if not isinstance(publish_result, dict):
        return False, "invalid publish result shape"

    published = publish_result.get("published", []) or []
    removed = publish_result.get("removed", []) or []
    skipped = publish_result.get("skipped", []) or []
    warnings = publish_result.get("warnings", []) or []

    if target_date in published:
        return True, "published"
    if target_date in removed:
        return True, "removed"

    for entry in skipped:
        if not isinstance(entry, dict) or entry.get("date") != target_date:
            continue
        reason = str(entry.get("reason", "unknown"))
        if "unchanged" in reason.lower():
            return True, reason
        return False, reason

    for warning in warnings:
        warning_text = str(warning)
        if target_date in warning_text:
            return False, warning_text

    # Non-running adjustments can be valid no-ops when Garmin already has
    # nothing to remove for the date.
    if expected_running is False:
        return True, "non_running_noop"
    if expected_running is True:
        return False, "no outcome for expected running workout"
    return False, "no outcome for target date"


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
    today_str = today.isoformat()

    # ── Gate: confidence must be medium or high ────────────────────────────
    dq = context_packet.get("data_quality", {})
    confidence = dq.get("readiness_confidence", "low")
    if confidence == "low":
        log.debug("Readiness confidence=%s — skipping adjust_today", confidence)
        return {"triggered": False, "reason": f"confidence={confidence}", "adjustment": None}

    # ── Gate: active plan must exist ───────────────────────────────────────
    pa = context_packet.get("plan_authority", {})
    active_plan_id = pa.get("active_plan_id")
    if not active_plan_id:
        log.debug("No active plan — skipping adjust_today")
        return {"triggered": False, "reason": "no_active_plan", "adjustment": None}

    # If today's adjustment already exists but publish never succeeded, retry
    # Garmin publish without re-running the Brain.
    prior_adjustments = _events_for_day("today_adjustment", today_str, db)
    if prior_adjustments:
        from memory.db import insert_event
        publish_events = _events_for_day("today_adjustment_garmin_publish", today_str, db)
        already_published = any(p.get("status") == "success" for p in publish_events)
        if already_published:
            return {"triggered": False, "reason": "already_adjusted_today", "adjustment": None}

        try:
            from skills.publish_to_garmin import publish
            expected_running = _is_running_workout_type(prior_adjustments[0].get("workout_type"))
            publish_result = publish(days=1, dry_run=False, db_path=db)
            publish_ok, publish_outcome = _publish_succeeded_for_day(
                publish_result,
                target_date=today_str,
                expected_running=expected_running,
            )
            if not publish_ok:
                raise RuntimeError(f"publish did not succeed for {today_str}: {publish_outcome}")
            insert_event(
                event_type="today_adjustment_garmin_publish",
                payload={
                    "date": today_str,
                    "status": "success",
                    "mode": "retry",
                    "outcome": publish_outcome,
                },
                source="on_readiness_change",
                db_path=db,
            )
            return {
                "triggered": False,
                "reason": "already_adjusted_today_publish_retried",
                "adjustment": None,
            }
        except Exception as retry_exc:
            log.warning("Garmin publish retry for adjusted day failed: %s", retry_exc)
            insert_event(
                event_type="today_adjustment_garmin_publish",
                payload={
                    "date": today_str,
                    "status": "failed",
                    "mode": "retry",
                    "error": str(retry_exc)[:300],
                },
                source="on_readiness_change",
                db_path=db,
            )
            return {
                "triggered": False,
                "reason": "already_adjusted_today_publish_retry_failed",
                "adjustment": None,
            }

    # ── Gate: sleep data must be available for today ───────────────────────
    # Readiness scores can be incomplete before the night's sleep is synced.
    # Wait until sleep_hours is populated in the context packet.
    rt_check = context_packet.get("readiness_trend", {})
    today_rt_check = rt_check.get("today", {}) if isinstance(rt_check, dict) else {}
    if not today_rt_check.get("sleep_hours"):
        log.debug("No sleep data for today yet — deferring adjust_today")
        return {"triggered": False, "reason": "no_sleep_today", "adjustment": None}

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

    # ── Call Brain: adjust_today ───────────────────────────────────────────
    log.info("Triggering adjust_today: %s", trigger_reason)

    try:
        from brain import adjust_today
        from memory.db import insert_event, insert_plan_days

        adjustment = adjust_today(context_packet, db_path=db)
        log.info(
            "adjust_today complete: type=%s reason=%s",
            adjustment.workout_type,
            adjustment.adjustment_reason,
        )

        # Persist the adjusted workout into today's active plan row so all
        # downstream reads (brief/schedule/export) reflect the change.
        adjusted_workout = adjustment.model_dump()
        # TodayAdjustment uses adjusted_intent as the canonical text, while
        # plan_days.workout_json expects intent for downstream readers.
        adjusted_workout["intent"] = adjustment.adjusted_intent
        try:
            insert_plan_days(
                active_plan_id,
                [
                    {
                        "day": today_str,
                        "intent": adjustment.adjusted_intent,
                        "workout_json": adjusted_workout,
                    }
                ],
                db_path=db,
            )
            log.info("Updated plan_days for %s from readiness adjustment", today_str)

            # Record adjustment after successful persistence so dedup reflects
            # committed state.
            insert_event(
                event_type="today_adjustment",
                payload={
                    "date":         today_str,
                    "workout_type": adjustment.workout_type,
                    "reason":       adjustment.adjustment_reason,
                },
                source="on_readiness_change",
                db_path=db,
            )

            # Push today's change to Garmin immediately (best effort).
            try:
                from skills.publish_to_garmin import publish
                publish_result = publish(days=1, dry_run=False, db_path=db)
                publish_ok, publish_outcome = _publish_succeeded_for_day(
                    publish_result,
                    target_date=today_str,
                    expected_running=_is_running_workout_type(adjustment.workout_type),
                )
                if not publish_ok:
                    raise RuntimeError(f"publish did not succeed for {today_str}: {publish_outcome}")
                insert_event(
                    event_type="today_adjustment_garmin_publish",
                    payload={
                        "date": today_str,
                        "status": "success",
                        "mode": "initial",
                        "outcome": publish_outcome,
                    },
                    source="on_readiness_change",
                    db_path=db,
                )
            except Exception as publish_exc:
                log.warning("Garmin publish after readiness adjustment failed: %s", publish_exc)
                insert_event(
                    event_type="today_adjustment_garmin_publish",
                    payload={
                        "date": today_str,
                        "status": "failed",
                        "mode": "initial",
                        "error": str(publish_exc)[:300],
                    },
                    source="on_readiness_change",
                    db_path=db,
                )
        except Exception as persist_exc:
            log.warning("Could not persist adjusted workout to plan_days: %s", persist_exc)
            return {
                "triggered":  False,
                "reason":     f"persist_error: {persist_exc}",
                "adjustment": None,
            }

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
