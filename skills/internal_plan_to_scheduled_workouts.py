"""
Converts internal plan days (from SQLite) into scheduled workout objects
compatible with src/workout_parser.parse_workout_description.

Output shape per workout:
    {
        "scheduled_date": "YYYY-MM-DD",
        "name":           "<parser-compatible description, e.g. '30 min E'>",
        "description":    "<human-readable intent from plan>",
        "source":         "internal_plan",
    }

The "name" field is what workout_parser and auto_workout_generator consume.
The "description" is passed as coach_description to generate_garmin_workout.

FALLBACK RULE:
If a workout cannot be rendered safely, degrade to an easy run and record
a "render_degraded" event in SQLite.

Supported description formats (subset of workout_parser grammar):
  easy / long  →  "{N} min E"
  tempo        →  "{wu} min warm up {N} min @ tempo {cd} min warm down"
                   (omits warmup/cooldown sections if duration is 0)
  interval     →  "{wu} min warm up {R}x{N} min @ tempo on {rec} min recovery {cd} min warm down"
                   (falls back to plain tempo format if reps missing)

Only running workout types (easy, tempo, interval, long) are converted.
Strength, rest, and cross sessions are skipped.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("skills.internal_plan_to_scheduled_workouts")

# Workout types that map to Garmin running workouts
_RUNNING_TYPES = {"easy", "tempo", "interval", "long"}


def convert(
    sessions: List[Dict[str, Any]],
    db_path=None,
) -> List[Dict[str, Any]]:
    """
    Convert a list of plan sessions into scheduled workout dicts.

    Args:
        sessions: Output of skills.plans.get_active_sessions()
        db_path:  SQLite path for recording render_degraded events.

    Returns:
        List of workout dicts with scheduled_date, name, description, source.
        Only running-type sessions are included.
    """
    results = []
    for session in sessions:
        workout_type = session.get("workout_type", "rest")
        if workout_type not in _RUNNING_TYPES:
            continue  # skip strength / rest / cross

        date_ = session["date"]
        duration_min = max(session.get("duration_min", 0), 1)
        steps = session.get("structure_steps", [])
        intent = session.get("intent", "")

        name, degraded_reason = _render_description(workout_type, duration_min, steps, intent)
        if degraded_reason:
            _record_degraded(
                date=date_,
                original_type=workout_type,
                reason=degraded_reason,
                rendered=name,
                db_path=db_path,
            )

        # Stride-specific event: record when renderer had to correct invalid strides
        plan_id = session.get("plan_id", "unknown")
        _check_stride_validity(
            date=date_,
            plan_id=plan_id,
            workout_type=workout_type,
            intent=intent,
            steps=steps,
            db_path=db_path,
        )

        results.append(
            {
                "scheduled_date": date_,
                "name":           name,
                "description":    intent or f"{workout_type.title()} run",
                "source":         "internal_plan",
                "_degraded":      degraded_reason is not None,
            }
        )

    return results


# ── Description rendering ──────────────────────────────────────────────────────

def _render_description(
    workout_type: str,
    duration_min: int,
    steps: List[Dict[str, Any]],
    intent: str = "",
) -> Tuple[str, Optional[str]]:
    """
    Return (description_string, degraded_reason_or_None).

    degraded_reason is None when the workout was rendered correctly.
    When degraded, the returned description is a safe fallback easy run.

    For easy/long workouts whose intent mentions strides, emits the canonical
    stride description rather than a plain easy run.  This is the second
    enforcement point (planner already rewrites bad steps; renderer always
    emits the correct format regardless).
    """
    try:
        if workout_type in ("easy", "long"):
            if "stride" in intent.lower():
                return _render_easy_strides(duration_min), None
            return f"{duration_min} min E", None

        if workout_type in ("tempo", "interval"):
            desc = _render_structured(workout_type, duration_min, steps)
            if desc is not None:
                return desc, None
            # Structured rendering failed — fall through to degraded
            reason = f"could not render {workout_type} from steps: {[s.get('label') for s in steps]}"

        else:
            reason = f"unsupported workout_type={workout_type!r}"

    except Exception as exc:
        reason = f"render exception: {exc}"

    fallback = f"{duration_min} min E"
    log.warning("render_degraded: %s → %r", reason, fallback)
    return fallback, reason


def _render_structured(
    workout_type: str,
    duration_min: int,
    steps: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Render tempo / interval from structure_steps.
    Returns None if steps are insufficient to produce a valid string.
    """
    warmup   = _find_step(steps, "warmup")
    cooldown = _find_step(steps, "cooldown")
    mains    = _find_steps(steps, ("main", "interval"))

    if not mains:
        return None

    wu_min = warmup["duration_min"] if warmup else 0
    cd_min = cooldown["duration_min"] if cooldown else 0
    main   = mains[0]
    main_min = main.get("duration_min", max(duration_min - wu_min - cd_min, 10))
    reps   = main.get("reps")

    parts: List[str] = []

    if wu_min:
        parts.append(f"{wu_min} min warm up")

    if workout_type == "interval" and reps and reps > 1:
        rec = _find_step(steps, "recovery")
        rec_min = rec["duration_min"] if rec else 1
        parts.append(f"{reps}x{main_min} min @ tempo on {rec_min} min recovery")
    else:
        parts.append(f"{main_min} min @ tempo")

    if cd_min:
        parts.append(f"{cd_min} min warm down")

    return " ".join(parts)


def _find_step(steps: List[Dict], label: str) -> Optional[Dict]:
    return next((s for s in steps if s.get("label") == label), None)


def _find_steps(steps: List[Dict], labels: tuple) -> List[Dict]:
    return [s for s in steps if s.get("label") in labels]


# ── Stride rendering ──────────────────────────────────────────────────────────

def _render_easy_strides(duration_min: int) -> str:
    """
    Return a parser-compatible easy+strides description.

    Always uses the canonical 6×20 s format.  Sub-minute stride durations
    cannot be stored in WorkoutStep.duration_min (schema ge=1), so the
    canonical text is the only reliable representation.

    Example: "45 min E + 6x20 sec strides @ ~5K effort on 60 sec easy jog recovery"
    """
    from brain.stride_rules import CANONICAL_REPS, CANONICAL_REP_SEC, CANONICAL_RECOVERY_SEC
    return (
        f"{duration_min} min E + "
        f"{CANONICAL_REPS}x{CANONICAL_REP_SEC} sec strides "
        f"@ ~5K effort on {CANONICAL_RECOVERY_SEC} sec easy jog recovery"
    )


def _check_stride_validity(
    date: str,
    plan_id: str,
    workout_type: str,
    intent: str,
    steps: List[Dict[str, Any]],
    db_path=None,
) -> None:
    """Record a stride_validation_failed event when renderer detects bad steps."""
    if workout_type not in ("easy", "long"):
        return
    if "stride" not in intent.lower():
        return

    try:
        from brain.stride_rules import validate_strides
        ok, reason = validate_strides(steps)
        if not ok:
            log.warning(
                "stride_validation_failed at render: %s (date=%s plan=%s)",
                reason, date, plan_id,
            )
            _record_stride_failure(
                date=date, plan_id=plan_id, reason=reason, db_path=db_path
            )
    except Exception as exc:
        log.error("stride validity check error: %s", exc)


# ── Degraded event recording ───────────────────────────────────────────────────

def _record_degraded(
    date: str,
    original_type: str,
    reason: str,
    rendered: str,
    db_path=None,
) -> None:
    """Record a render_degraded event in SQLite."""
    try:
        from memory.db import init_db, insert_event, DB_PATH as _DEFAULT_DB

        init_db(db_path or _DEFAULT_DB)
        insert_event(
            event_type="render_degraded",
            payload={
                "date":                  date,
                "original_workout_type": original_type,
                "reason":                reason[:300],
                "rendered_description":  rendered,
            },
            source="skills.internal_plan_to_scheduled_workouts",
            db_path=db_path or _DEFAULT_DB,
        )
    except Exception as exc:
        log.error("Failed to record render_degraded event: %s", exc)


def _record_stride_failure(
    date: str,
    plan_id: str,
    reason: str,
    db_path=None,
) -> None:
    """Record a stride_validation_failed event in SQLite."""
    try:
        from memory.db import init_db, insert_event, DB_PATH as _DEFAULT_DB

        init_db(db_path or _DEFAULT_DB)
        insert_event(
            event_type="stride_validation_failed",
            payload={
                "date":    date,
                "plan_id": plan_id,
                "reason":  reason[:300],
            },
            source="skills.internal_plan_to_scheduled_workouts",
            db_path=db_path or _DEFAULT_DB,
        )
    except Exception as exc:
        log.error("Failed to record stride_validation_failed event: %s", exc)
