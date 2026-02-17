"""
Skills wrapper: publish internal plan workouts to Garmin Connect.

Uses the sacred upload path (src/auto_workout_generator + src/workout_uploader)
as black boxes. Does NOT write to data/generated_workouts.json.

Dedupe authority (non-negotiable):
  data/generated_workouts.json is the SOLE authoritative gate for "this date is
  already on Garmin Connect". A date present in that log is skipped unconditionally.
  SQLite (type="garmin_publish_internal") records publish attempts/results for
  audit purposes only — it NEVER causes a workout to be skipped.

Authority rule (non-negotiable):
  Source is always the internal SQLite plan. FinalSurge/ICS is not read here.
"""

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
_SRC = str(PROJECT_ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

log = logging.getLogger("skills.publish_to_garmin")

_GENERATED_LOG = PROJECT_ROOT / "data" / "generated_workouts.json"


def _date_in_generated_log(target_date: str) -> bool:
    """
    Return True if data/generated_workouts.json has a running entry for target_date.

    This is the ONLY authoritative dedupe gate.  If this returns True the workout
    is already on Garmin Connect (published by the auto_workout_generator sacred path)
    and must not be uploaded again.
    """
    if not _GENERATED_LOG.exists():
        return False
    try:
        with open(_GENERATED_LOG) as f:
            data = json.load(f)
        return target_date in data.get("running", {})
    except Exception as exc:
        log.warning("Could not read generated_workouts.json: %s — assuming date not present", exc)
        return False


def publish(
    days: int = 7,
    dry_run: bool = True,
    db_path=None,
) -> Dict[str, Any]:
    """
    Publish upcoming running workouts from the internal plan to Garmin Connect.

    Args:
        days:    Number of days ahead to include (default 7).
        dry_run: If True, print what would be uploaded without calling Garmin APIs.
        db_path: Override SQLite path (testing).

    Returns:
        dict with keys:
            prepared      List of workout dicts ready to upload
            published     List of dates actually uploaded (empty when dry_run=True)
            skipped       List of dicts with date + reason for each skip
            degraded      List of dates that fell back to easy-run rendering
            dry_run       bool
    """
    from skills.plans import get_active_sessions
    from skills.internal_plan_to_scheduled_workouts import convert

    # ── Collect upcoming internal plan sessions ────────────────────────────
    sessions = get_active_sessions(db_path=db_path)
    if not sessions:
        log.warning("No active plan — nothing to publish")
        return {
            "prepared": [], "published": [], "skipped": [],
            "degraded": [], "dry_run": dry_run,
        }

    # ── Convert to parser-compatible workout objects ───────────────────────
    workouts = convert(sessions, db_path=db_path)

    # ── Filter: upcoming dates within window ──────────────────────────────
    today = date.today()
    cutoff = today + timedelta(days=days)
    prepared = []
    skipped = []

    for wo in workouts:
        wo_date = wo["scheduled_date"]
        try:
            dt = date.fromisoformat(wo_date)
        except ValueError:
            skipped.append({"date": wo_date, "reason": "invalid date format"})
            continue

        if dt < today:
            log.debug("SKIP %s: past date", wo_date)
            skipped.append({"date": wo_date, "reason": "past date"})
            continue
        if dt > cutoff:
            log.debug("SKIP %s: beyond %d-day window", wo_date, days)
            skipped.append({"date": wo_date, "reason": f"beyond {days}-day window"})
            continue

        # Sole authoritative dedupe gate: generated_workouts.json.
        # SQLite garmin_publish_internal events are audit records only; they do
        # NOT gate uploads (generated_workouts.json may disagree after re-runs).
        if _date_in_generated_log(wo_date):
            log.info(
                "SKIP %s: date found in generated_workouts.json — "
                "a Garmin running workout already exists for this date",
                wo_date,
            )
            skipped.append({
                "date": wo_date,
                "reason": "date in generated_workouts.json (Garmin workout already exists)",
            })
            continue

        prepared.append(wo)

    degraded = [wo["scheduled_date"] for wo in prepared if wo.get("_degraded")]

    # ── Dry-run mode ──────────────────────────────────────────────────────
    if dry_run:
        print(f"[DRY RUN] Would upload {len(prepared)} workout(s):")
        for wo in prepared:
            flag = " [DEGRADED→easy]" if wo.get("_degraded") else ""
            print(f"  {wo['scheduled_date']}: {wo['name']}{flag}")
        if skipped:
            print(f"\n[DRY RUN] Skipped {len(skipped)}:")
            for s in skipped:
                print(f"  {s['date']}: {s['reason']}")
        return {
            "prepared":  prepared,
            "published": [],
            "skipped":   skipped,
            "degraded":  degraded,
            "dry_run":   True,
        }

    # ── Live publish ──────────────────────────────────────────────────────
    from workout_parser import parse_workout_description
    from auto_workout_generator import generate_garmin_workout, generate_workout_name
    from workout_uploader import upload_workout, schedule_workout, get_garmin_client
    from memory.db import init_db, insert_event, DB_PATH as _DEFAULT_DB

    init_db(db_path or _DEFAULT_DB)
    client = get_garmin_client()
    published = []

    for wo in prepared:
        wo_date = wo["scheduled_date"]
        try:
            parsed = parse_workout_description(wo["name"])
            garmin_name = generate_workout_name(wo_date, parsed)
            garmin_workout = generate_garmin_workout(
                parsed,
                garmin_name,
                coach_description=wo["description"],
            )

            response = upload_workout(client, garmin_workout, quiet=True)
            garmin_id = response.get("workoutId")
            schedule_workout(client, garmin_id, wo_date, quiet=True)

            # Record idempotency event in SQLite
            insert_event(
                event_type="garmin_publish_internal",
                payload={
                    "date":       wo_date,
                    "garmin_id":  garmin_id,
                    "name":       garmin_name,
                    "degraded":   wo.get("_degraded", False),
                },
                source="skills.publish_to_garmin",
                db_path=db_path or _DEFAULT_DB,
            )

            log.info("Published %s → Garmin %s", wo_date, garmin_id)
            published.append(wo_date)

        except Exception as exc:
            log.error("Failed to publish %s: %s", wo_date, exc)
            skipped.append({"date": wo_date, "reason": f"upload error: {exc}"})

    return {
        "prepared":  prepared,
        "published": published,
        "skipped":   skipped,
        "degraded":  degraded,
        "dry_run":   False,
    }
