"""
Skills wrapper: Garmin sync.

Calls sync_garmin_data.sh after a native Python cache-age check.
After a successful sync, ingests recovery metrics and activities into SQLite
(B11-012, B11-013) — JSON cache remains the primary read path for now.

Does NOT modify health_data_cache.json format — that remains owned by
src/garmin_sync.py (sacred invariant).
"""

import json
import logging
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
CACHE_FILE = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
log = logging.getLogger("skills.garmin_sync")

# Default lookback used when --days is not specified
DEFAULT_INGEST_DAYS = 30


def _cache_age_minutes() -> Optional[float]:
    """
    Return the age of health_data_cache.json in minutes, or None if
    the file is absent or the timestamp cannot be parsed.
    """
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        ts_str = data.get("last_updated", "")
        if not ts_str:
            return None
        last_updated = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - last_updated).total_seconds() / 60
    except Exception:
        return None


def _load_cache() -> dict:
    """Load and return the health cache JSON, or empty dict on failure."""
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


# ── Post-sync SQLite ingest ────────────────────────────────────────────────────

def _ingest_daily_metrics(health: dict, days: int, db_path) -> int:
    """
    Upsert recovery metrics from the health cache into the daily_metrics table.

    Reads from these cache sections (actual keys in health_data_cache.json):
      hrv_readings, sleep_sessions, body_battery, training_readiness,
      resting_hr_readings, stress_readings

    Returns the number of date rows upserted.
    """
    from memory.db import upsert_daily_metrics

    cutoff = (date.today() - timedelta(days=days)).isoformat()

    # Index each section by date string for O(1) lookup
    hrv_by_date   = {r["date"]: r for r in health.get("hrv_readings", [])
                     if r.get("date", "") >= cutoff}
    sleep_by_date = {r["date"]: r for r in health.get("sleep_sessions", [])
                     if r.get("date", "") >= cutoff}
    bb_by_date    = {r["date"]: r for r in health.get("body_battery", [])
                     if r.get("date", "") >= cutoff}
    tr_by_date    = {r["date"]: r for r in health.get("training_readiness", [])
                     if r.get("date", "") >= cutoff}
    stress_by_date = {r["date"]: r for r in health.get("stress_readings", [])
                      if r.get("date", "") >= cutoff}

    # resting_hr_readings entries are [datetime_str, value]
    rhr_by_date: dict = {}
    for entry in health.get("resting_hr_readings", []):
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            d_str = str(entry[0])[:10]
            if d_str >= cutoff:
                rhr_by_date[d_str] = entry[1]

    all_dates = (
        set(hrv_by_date)
        | set(sleep_by_date)
        | set(bb_by_date)
        | set(tr_by_date)
        | set(stress_by_date)
        | set(rhr_by_date)
    )

    count = 0
    for d_str in all_dates:
        try:
            d = date.fromisoformat(d_str)
        except ValueError:
            continue

        hrv_row   = hrv_by_date.get(d_str, {})
        sleep_row = sleep_by_date.get(d_str, {})
        bb_row    = bb_by_date.get(d_str, {})
        tr_row    = tr_by_date.get(d_str, {})
        stress_row = stress_by_date.get(d_str, {})

        sleep_min = sleep_row.get("total_duration_minutes")

        upsert_daily_metrics(
            day=d,
            hrv_rmssd=hrv_row.get("last_night_avg"),
            resting_hr=rhr_by_date.get(d_str),
            sleep_score=sleep_row.get("sleep_score"),
            sleep_duration_h=sleep_min / 60 if sleep_min is not None else None,
            body_battery=bb_row.get("latest_level"),
            training_readiness=tr_row.get("score"),
            stress_avg=stress_row.get("avg_stress"),
            raw={
                "hrv": hrv_row,
                "sleep": sleep_row,
                "body_battery": bb_row,
                "training_readiness": tr_row,
                "stress": stress_row,
            },
            db_path=db_path,
        )
        count += 1

    log.info("Ingested daily_metrics: %d rows for last %d days", count, days)
    return count


def _ingest_activities(health: dict, days: int, db_path) -> int:
    """
    Upsert activities from the health cache into the activities table.

    pace_per_mile (float, minutes/mile) is converted to seconds/mile for storage.
    Splits and hr_zones are excluded from raw_json to keep row size small.

    Returns the number of activity rows upserted.
    """
    from memory.db import upsert_activity

    cutoff = (date.today() - timedelta(days=days)).isoformat()

    count = 0
    for act in health.get("activities", []):
        act_date_str = str(act.get("date", ""))[:10]
        if not act_date_str or act_date_str < cutoff:
            continue
        try:
            act_date = date.fromisoformat(act_date_str)
        except ValueError:
            continue

        pace_raw = act.get("pace_per_mile")
        dist_mi  = act.get("distance_miles")

        upsert_activity(
            activity_id=str(act.get("activity_id", "")),
            activity_date=act_date,
            activity_type=str(act.get("activity_type", "unknown")).lower(),
            name=act.get("activity_name"),
            duration_s=act.get("duration_seconds"),
            distance_m=dist_mi * 1609.34 if dist_mi is not None else None,
            avg_hr=act.get("avg_heart_rate"),
            max_hr=act.get("max_heart_rate"),
            avg_pace_s=pace_raw * 60 if pace_raw is not None else None,
            calories=act.get("calories"),
            raw={k: v for k, v in act.items() if k not in ("splits", "hr_zones")},
            db_path=db_path,
        )
        count += 1

    log.info("Ingested activities: %d rows for last %d days", count, days)
    return count


# ── Main sync entry point ──────────────────────────────────────────────────────

def run(
    force: bool = False,
    source: str = "agent",
    days: int = None,
    check_only: bool = False,
    max_age_minutes: int = 30,
    db_path=None,
) -> dict:
    """
    Run Garmin sync and record a sync event in SQLite.

    Cache-age check is performed natively in Python:
    - If cache is younger than max_age_minutes and force=False, skip sync.
    - If cache is stale, absent, or force=True, run sync_garmin_data.sh.

    After a successful (non-check-only) sync, ingests daily_metrics and
    activities from the updated cache into SQLite write-through tables.

    Args:
        force:           Skip cache-age check and always sync.
        source:          Who triggered this sync ('agent', 'cli', 'discord', …).
        days:            Number of days to pass to sync_garmin_data.sh.
        check_only:      Pass --check-only to sync_garmin_data.sh (preview).
        max_age_minutes: Maximum acceptable cache age in minutes (default 30).
        db_path:         Override the default SQLite DB path (for testing).

    Returns:
        dict with keys: success, returncode, stdout, stderr, event_id, summary,
                        skipped (True when cache-hit short-circuit fired),
                        ingest_metrics_rows, ingest_activities_rows.
    """
    from memory.db import (
        DB_PATH as _DEFAULT_DB,
        init_db, insert_event, log_task_start, log_task_finish,
        record_sync_start, record_sync_finish,
    )

    if db_path is None:
        db_path = _DEFAULT_DB

    init_db(db_path=db_path)

    # ── Cache-age check ────────────────────────────────────────────────────────
    if not force and not check_only:
        age = _cache_age_minutes()
        if age is not None and age < max_age_minutes:
            log.info(
                "Cache is %.1f min old (max %d min) — skipping sync",
                age, max_age_minutes,
            )
            return {
                "success": True,
                "returncode": 0,
                "stdout": f"Cache is {age:.0f}m old (max {max_age_minutes}m). Skipping sync.",
                "stderr": "",
                "event_id": "skipped",
                "summary": f"Cache fresh ({age:.0f}m); skipped.",
                "skipped": True,
                "ingest_metrics_rows": 0,
                "ingest_activities_rows": 0,
            }

    # ── Build sync command ─────────────────────────────────────────────────────
    cmd = ["bash", str(PROJECT_ROOT / "bin" / "sync_garmin_data.sh")]
    if days is not None:
        cmd += ["--days", str(days)]
    if check_only:
        cmd.append("--check-only")

    run_id = log_task_start("garmin_sync", db_path=db_path)
    sync_run_id = record_sync_start(source=source, days_requested=days, db_path=db_path)

    log.info("Running Garmin sync: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        log_task_finish(
            run_id, "failed",
            details={"error": "timeout", "timeout_sec": 180},
            db_path=db_path,
        )
        record_sync_finish(sync_run_id, "failed", error_summary="timeout after 180s",
                           db_path=db_path)
        raise RuntimeError("garmin_sync timed out after 180s") from exc

    success = result.returncode == 0
    summary = (result.stdout if success else result.stderr).strip()[:500]

    if success:
        log_task_finish(run_id, "success", details={"summary": summary[:200]},
                        db_path=db_path)
        record_sync_finish(sync_run_id, "success", db_path=db_path)
    else:
        log.warning("Garmin sync failed rc=%d stderr: %s", result.returncode, result.stderr[:300])
        log_task_finish(
            run_id, "failed",
            details={"returncode": result.returncode, "stderr": result.stderr[:500]},
            db_path=db_path,
        )
        record_sync_finish(
            sync_run_id, "failed",
            error_summary=result.stderr[:200] if result.stderr else f"rc={result.returncode}",
            db_path=db_path,
        )

    event_id = insert_event(
        event_type="garmin_sync",
        payload={
            "returncode": result.returncode,
            "force": force,
            "success": success,
            "summary": summary[:200],
        },
        source="skills.garmin_sync",
        db_path=db_path,
    )

    log.info("Garmin sync rc=%d event_id=%s task_run_id=%d", result.returncode, event_id[:8], run_id)

    # ── Post-sync ingest (only on success, not check-only) ─────────────────────
    ingest_days = days if days is not None else DEFAULT_INGEST_DAYS
    metrics_rows = 0
    activities_rows = 0

    if success and not check_only:
        health = _load_cache()
        try:
            metrics_rows = _ingest_daily_metrics(health, ingest_days, db_path)
        except Exception as exc:
            log.warning("daily_metrics ingest failed: %s", exc)
        try:
            activities_rows = _ingest_activities(health, ingest_days, db_path)
        except Exception as exc:
            log.warning("activities ingest failed: %s", exc)

    return {
        "success": success,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "event_id": event_id,
        "summary": summary,
        "skipped": False,
        "ingest_metrics_rows": metrics_rows,
        "ingest_activities_rows": activities_rows,
    }
