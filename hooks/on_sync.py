"""
Hook: on_sync — runs after a successful Garmin sync.

Actions (all deterministic, no LLM):
  1. Parse today's metrics from health_data_cache.json → upsert SQLite metrics row.
  2. Write vault/daily/YYYY-MM-DD.md stub if not already present today.

Returns a summary dict. Safe to call even when cache is stale or partially populated.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent
_CACHE_PATH = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"

log = logging.getLogger("hooks.on_sync")


def run(db_path=None) -> Dict[str, Any]:
    """
    Post-sync hook. Should be called immediately after skills.garmin_sync.run()
    reports success=True.

    Returns dict with keys: metrics_updated, vault_written, today, metrics (dict).
    """
    from memory.db import upsert_metrics, init_db, DB_PATH as _DEFAULT_DB
    from memory.vault import write_daily_note

    db = db_path or _DEFAULT_DB
    init_db(db)
    today = date.today()

    # ── Load health cache ──────────────────────────────────────────────────
    if not _CACHE_PATH.exists():
        log.warning("Health cache not found at %s — skipping metrics upsert", _CACHE_PATH)
        return {"metrics_updated": False, "vault_written": False, "today": today.isoformat(), "metrics": {}}

    try:
        with open(_CACHE_PATH) as f:
            health = json.load(f)
    except Exception as exc:
        log.error("Could not load health cache: %s", exc)
        return {"metrics_updated": False, "vault_written": False, "today": today.isoformat(), "metrics": {}}

    # ── Extract today's metrics ────────────────────────────────────────────
    metrics = _extract_today_metrics(health, today)

    # ── Upsert metrics rollup ──────────────────────────────────────────────
    metrics_updated = False
    if metrics:
        upsert_metrics(today, metrics, db_path=db)
        metrics_updated = True
        log.info("Metrics upserted for %s: %s", today.isoformat(), list(metrics.keys()))

    # ── Vault daily note stub ──────────────────────────────────────────────
    vault_note_path = PROJECT_ROOT / "vault" / "daily" / f"{today.isoformat()}.md"
    vault_written = False
    if not vault_note_path.exists():
        content = _build_stub_note(today, metrics)
        write_daily_note(today, content)
        vault_written = True
        log.info("Vault daily note written for %s", today.isoformat())

    return {
        "metrics_updated": metrics_updated,
        "vault_written":   vault_written,
        "today":           today.isoformat(),
        "metrics":         metrics,
    }


# ── Metric extraction ──────────────────────────────────────────────────────────

def _extract_today_metrics(health: Dict, today: date) -> Dict[str, Any]:
    """
    Extract key recovery metrics for today from health_data_cache.json.
    Returns only fields that are actually present; never raises.
    """
    today_str = today.isoformat()
    metrics: Dict[str, Any] = {}

    # Training readiness
    tr_list = health.get("training_readiness") or []
    for row in reversed(tr_list):
        cal = row.get("calendarDate", "") or row.get("date", "")
        if cal and cal[:10] == today_str:
            score = row.get("score") or row.get("level")
            if score is not None:
                metrics["training_readiness"] = int(score)
            break

    # Body battery
    bb_list = health.get("body_battery") or []
    for row in reversed(bb_list):
        cal = row.get("calendarDate", "") or row.get("date", "")
        if cal and cal[:10] == today_str:
            highest = row.get("charged") or row.get("highest") or row.get("bodyBatteryHighest")
            if highest is not None:
                metrics["body_battery_max"] = int(highest)
            break

    # Sleep
    sleep_list = health.get("sleep_data") or health.get("sleep") or []
    if isinstance(sleep_list, list):
        for row in reversed(sleep_list):
            cal = (
                row.get("calendarDate") or row.get("sleepStartTimestampLocal", "")[:10]
                or row.get("date", "")
            )
            if cal and cal[:10] == today_str:
                hrs = row.get("sleepTimeSeconds") or row.get("totalSleepSeconds")
                if hrs:
                    metrics["sleep_hours"] = round(hrs / 3600, 2)
                score = row.get("sleepScore") or row.get("averageSpO2") and None  # don't use SpO2 as score
                sleep_score = row.get("sleepScore") or row.get("score")
                if sleep_score:
                    metrics["sleep_score"] = int(sleep_score)
                break

    # HRV (prefer last-night's reading)
    hrv_list = health.get("hrv_data") or health.get("hrv") or []
    if isinstance(hrv_list, list):
        for row in reversed(hrv_list):
            cal = row.get("calendarDate", "") or row.get("date", "")
            if cal and cal[:10] == today_str:
                val = row.get("lastNight") or row.get("weeklyAvg") or row.get("hrv5MinHigh")
                if val:
                    metrics["hrv"] = int(val)
                break

    # RHR
    rhr_list = health.get("rhr_data") or health.get("heart_rate") or []
    if isinstance(rhr_list, list):
        for row in reversed(rhr_list):
            cal = row.get("calendarDate", "") or row.get("date", "")
            if cal and cal[:10] == today_str:
                val = row.get("restingHeartRate") or row.get("rhr")
                if val:
                    metrics["rhr"] = int(val)
                break

    return metrics


def _build_stub_note(today: date, metrics: Dict[str, Any]) -> str:
    lines = [
        f"# Daily Note — {today.isoformat()}",
        "",
        "## Recovery Metrics (auto-populated from Garmin sync)",
        "",
    ]
    if metrics:
        for k, v in metrics.items():
            lines.append(f"- **{k}**: {v}")
    else:
        lines.append("_No metrics available — sync may be incomplete._")

    lines += [
        "",
        "## Coach Notes",
        "",
        "_Add notes here. They will be read during the next Brain planning cycle._",
    ]
    return "\n".join(lines)
