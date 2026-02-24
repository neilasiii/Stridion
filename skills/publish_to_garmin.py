"""
Skills wrapper: publish internal plan workouts to Garmin Connect.

Uses the sacred upload path (src/auto_workout_generator + src/workout_uploader)
as black boxes.

Dedupe/update authority (non-negotiable):
  data/generated_workouts.json is the SOLE source of truth for Garmin publish
  state per date. For each running date:
    - same signature  -> skip (already up to date)
    - changed signature -> replace workout on Garmin
    - missing entry -> create new workout on Garmin

Authority rule (non-negotiable):
  Source is always the internal SQLite plan. FinalSurge/ICS is not read here.
"""

import hashlib
import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
_SRC = str(PROJECT_ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

log = logging.getLogger("skills.publish_to_garmin")

_GENERATED_LOG = PROJECT_ROOT / "data" / "generated_workouts.json"


def _load_generated_log() -> Dict[str, Any]:
    """Load generated_workouts.json with backward-compatible defaults."""
    if not _GENERATED_LOG.exists():
        return {"running": {}, "strength": {}, "mobility": {}, "week_snapshots": {}}

    try:
        with open(_GENERATED_LOG) as f:
            data = json.load(f)
    except Exception as exc:
        log.warning("Could not read generated_workouts.json: %s — starting fresh", exc)
        return {"running": {}, "strength": {}, "mobility": {}, "week_snapshots": {}}

    if not isinstance(data, dict):
        return {"running": {}, "strength": {}, "mobility": {}, "week_snapshots": {}}

    data.setdefault("running", {})
    data.setdefault("strength", {})
    data.setdefault("mobility", {})
    data.setdefault("week_snapshots", {})
    if not isinstance(data["running"], dict):
        data["running"] = {}
    return data


def _save_generated_log(data: Dict[str, Any]) -> None:
    """Persist generated_workouts.json safely."""
    _GENERATED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_GENERATED_LOG, "w") as f:
        json.dump(data, f, indent=2)


def _workout_signature(workout: Dict[str, Any]) -> str:
    """
    Stable signature for Garmin publish dedupe/update decisions.

    Signature is derived from renderer outputs that define actual Garmin content.
    """
    payload = {
        "scheduled_date": workout.get("scheduled_date"),
        "name": workout.get("name"),
        "description": workout.get("description"),
        "source": workout.get("source"),
        "degraded": bool(workout.get("_degraded", False)),
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _running_entry(log_data: Dict[str, Any], target_date: str) -> Optional[Dict[str, Any]]:
    """
    Return running entry dict for target_date, or None when missing/invalid.
    """
    running = log_data.get("running", {})
    entry = running.get(target_date)
    return entry if isinstance(entry, dict) else None


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
            prepared      List of workout dicts ready to upload/update
            published     List of dates uploaded/updated in Garmin
            removed       List of dates removed from Garmin (no longer running)
            skipped       List of dicts with date + reason
            degraded      List of dates that fell back to easy-run rendering
            dry_run       bool
            warnings      List of non-fatal warnings (live mode)
    """
    from skills.plans import get_active_sessions
    from skills.internal_plan_to_scheduled_workouts import convert

    sessions = get_active_sessions(db_path=db_path)
    if not sessions:
        log.warning("No active plan — nothing to publish")
        return {
            "prepared": [],
            "published": [],
            "removed": [],
            "skipped": [],
            "degraded": [],
            "dry_run": dry_run,
            "warnings": [],
        }

    workouts = convert(sessions, db_path=db_path)
    log_data = _load_generated_log()
    running_log = log_data["running"]
    session_by_date = {s.get("date"): s for s in sessions if s.get("date")}

    today = date.today()
    cutoff = today + timedelta(days=days)
    prepared: List[Dict[str, Any]] = []
    to_remove: List[str] = []
    skipped: List[Dict[str, str]] = []

    for wo in workouts:
        wo_date = wo["scheduled_date"]
        try:
            dt = date.fromisoformat(wo_date)
        except ValueError:
            skipped.append({"date": wo_date, "reason": "invalid date format"})
            continue

        if dt < today:
            skipped.append({"date": wo_date, "reason": "past date"})
            continue
        if dt > cutoff:
            skipped.append({"date": wo_date, "reason": f"beyond {days}-day window"})
            continue

        signature = _workout_signature(wo)
        existing = _running_entry(log_data, wo_date)
        existing_signature = existing.get("signature") if existing else None

        if existing and existing_signature == signature:
            skipped.append({"date": wo_date, "reason": "unchanged (already up to date in Garmin)"})
            continue

        wo_copy = dict(wo)
        wo_copy["_signature"] = signature
        wo_copy["_existing_entry"] = existing
        wo_copy["_action"] = "update" if existing else "create"
        prepared.append(wo_copy)

    # If a date in the active plan is no longer a running day but a running
    # workout exists in generated_workouts.json, remove it in live mode.
    for log_date, entry in list(running_log.items()):
        try:
            dt = date.fromisoformat(log_date)
        except ValueError:
            continue
        if dt < today or dt > cutoff:
            continue
        session = session_by_date.get(log_date)
        if not session:
            continue
        session_type = session.get("workout_type")
        if session_type is None:
            # Defensive: if session shape is partial, avoid destructive deletes.
            continue
        if session_type in ("easy", "tempo", "interval", "long"):
            continue
        if isinstance(entry, dict) and entry.get("garmin_id") is not None:
            to_remove.append(log_date)

    degraded = [wo["scheduled_date"] for wo in prepared if wo.get("_degraded")]

    if dry_run:
        print(f"[DRY RUN] Would upload/update {len(prepared)} workout(s):")
        for wo in prepared:
            flag = " [DEGRADED->easy]" if wo.get("_degraded") else ""
            action = wo.get("_action", "create")
            print(f"  {wo['scheduled_date']}: {wo['name']} [{action}]{flag}")
        if skipped:
            print(f"\n[DRY RUN] Skipped {len(skipped)}:")
            for s in skipped:
                print(f"  {s['date']}: {s['reason']}")
        if to_remove:
            print(f"\n[DRY RUN] Would remove {len(to_remove)} obsolete running workout(s):")
            for d in to_remove:
                print(f"  {d}: day is no longer a running workout")
        return {
            "prepared": prepared,
            "published": [],
            "removed": [],
            "skipped": skipped,
            "degraded": degraded,
            "dry_run": True,
            "warnings": [],
        }

    from workout_parser import parse_workout_description
    from auto_workout_generator import generate_garmin_workout, generate_workout_name
    from workout_uploader import (
        delete_workout,
        get_garmin_client,
        schedule_workout,
        upload_workout,
    )
    from memory.db import DB_PATH as _DEFAULT_DB, init_db, insert_event

    init_db(db_path or _DEFAULT_DB)
    client = get_garmin_client()
    published: List[str] = []
    removed: List[str] = []
    warnings: List[str] = []
    log_dirty = False

    for wo in prepared:
        wo_date = wo["scheduled_date"]
        existing = wo.get("_existing_entry") or {}
        prev_id = existing.get("garmin_id")

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

            # Best-effort cleanup of replaced workout to avoid duplicates.
            if prev_id and str(prev_id) != str(garmin_id):
                try:
                    deleted = delete_workout(client, int(prev_id), quiet=True)
                except Exception:
                    deleted = False
                if not deleted:
                    warn = (
                        f"{wo_date}: new workout published ({garmin_id}) but could not "
                        f"delete previous workout {prev_id}"
                    )
                    warnings.append(warn)
                    log.warning(warn)

            insert_event(
                event_type="garmin_publish_internal",
                payload={
                    "date": wo_date,
                    "garmin_id": garmin_id,
                    "name": garmin_name,
                    "degraded": wo.get("_degraded", False),
                    "action": wo.get("_action", "create"),
                    "previous_garmin_id": prev_id,
                    "signature": wo.get("_signature"),
                },
                source="skills.publish_to_garmin",
                db_path=db_path or _DEFAULT_DB,
            )

            running_log[wo_date] = {
                "garmin_id": garmin_id,
                "name": garmin_name,
                "description": wo.get("description", ""),
                "source": "internal_plan",
                "signature": wo.get("_signature"),
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
            log_dirty = True

            log.info("Published %s -> Garmin %s (%s)", wo_date, garmin_id, wo.get("_action", "create"))
            published.append(wo_date)

        except Exception as exc:
            log.error("Failed to publish %s: %s", wo_date, exc)
            skipped.append({"date": wo_date, "reason": f"upload error: {exc}"})

    for remove_date in to_remove:
        entry = _running_entry(log_data, remove_date) or {}
        garmin_id = entry.get("garmin_id")
        if garmin_id is None:
            continue
        try:
            deleted = delete_workout(client, int(garmin_id), quiet=True)
        except Exception as exc:
            deleted = False
            warnings.append(f"{remove_date}: delete failed for Garmin workout {garmin_id} ({exc})")
        if not deleted:
            warnings.append(f"{remove_date}: could not delete obsolete Garmin workout {garmin_id}")
            continue

        insert_event(
            event_type="garmin_publish_internal",
            payload={
                "date": remove_date,
                "garmin_id": garmin_id,
                "action": "remove",
                "reason": "day no longer running workout",
            },
            source="skills.publish_to_garmin",
            db_path=db_path or _DEFAULT_DB,
        )
        running_log.pop(remove_date, None)
        log_dirty = True
        removed.append(remove_date)

    if log_dirty:
        try:
            _save_generated_log(log_data)
        except Exception as exc:
            warn = f"Failed to update generated_workouts.json: {exc}"
            warnings.append(warn)
            log.warning(warn)

    return {
        "prepared": prepared,
        "published": published,
        "removed": removed,
        "skipped": skipped,
        "degraded": degraded,
        "dry_run": False,
        "warnings": warnings,
    }
