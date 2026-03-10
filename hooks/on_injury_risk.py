"""
Hook: on_injury_risk — monitors 6 overtraining signals and queues an alert
for Discord delivery when 2+ fire simultaneously.

Called from agent/runner.py run_cycle() unconditionally (always runs).

State keys used:
  pending_injury_risk_alert     - JSON payload queued for bot delivery
  injury_risk_last_fired        - ISO date when last alert was posted (7-day cooldown)
  injury_risk_awaiting_response - set after bot posts; cleared on yes/no reply
"""

import json
import logging
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from memory.retrieval import HEALTH_CACHE

PROJECT_ROOT = Path(__file__).parent.parent
PATTERNS_FILE = PROJECT_ROOT / "data" / "athlete" / "learned_patterns.md"

log = logging.getLogger("hooks.on_injury_risk")

_PENDING_KEY  = "pending_injury_risk_alert"
_LAST_FIRED   = "injury_risk_last_fired"
_AWAITING_KEY = "injury_risk_awaiting_response"

COOLDOWN_DAYS    = 7
SIGNAL_THRESHOLD = 2


def _read_hrv_baseline() -> float:
    """Parse personal HRV median from learned_patterns.md. Falls back to 66ms."""
    try:
        text = PATTERNS_FILE.read_text()
        m = re.search(r'\*\*Baseline \(median\):\*\*\s*([\d.]+)\s*ms', text)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return 66.0


def _signal_load_spike(conn: sqlite3.Connection, today: date) -> Tuple[bool, str]:
    """Running mileage jumped >10% week-over-week (Sun–Sat calendar weeks)."""
    def _miles(start: str, end: str) -> float:
        row = conn.execute(
            "SELECT SUM(distance_m) FROM activities "
            "WHERE activity_type = 'running' AND activity_date BETWEEN ? AND ?",
            (start, end),
        ).fetchone()
        return (row[0] or 0.0) / 1609.34

    # Align to Sun–Sat calendar weeks so week boundaries match FinalSurge
    days_since_sunday = (today.weekday() + 1) % 7  # Mon=0…Sun=6 → Sun=0
    curr_week_start = today - timedelta(days=days_since_sunday)
    prior_week_start = curr_week_start - timedelta(days=7)
    prior_week_end   = curr_week_start - timedelta(days=1)

    prior   = _miles(prior_week_start.isoformat(), prior_week_end.isoformat())
    current = _miles(curr_week_start.isoformat(), today.isoformat())

    if prior < 5.0:
        return False, "insufficient prior-week data"
    pct = (current - prior) / prior
    if pct > 0.10:
        return True, f"mileage up {pct:.0%} ({prior:.1f}\u2192{current:.1f} mi)"
    return False, ""


def _signal_hrv_streak(conn: sqlite3.Connection, today: date) -> Tuple[bool, str]:
    """HRV below personal baseline for 3+ consecutive days."""
    baseline = _read_hrv_baseline()
    rows = conn.execute(
        "SELECT day, hrv_rmssd FROM daily_metrics "
        "WHERE day BETWEEN ? AND ? AND hrv_rmssd IS NOT NULL ORDER BY day DESC",
        ((today - timedelta(days=6)).isoformat(), today.isoformat()),
    ).fetchall()

    if len(rows) < 3:
        return False, "insufficient data"

    streak = 0
    for _, hrv in rows:
        if hrv < baseline:
            streak += 1
        else:
            break

    if streak >= 3:
        return True, f"HRV below {baseline:.0f} ms baseline for {streak} consecutive days"
    return False, ""


def _signal_easy_rpe(conn: sqlite3.Connection, today: date) -> Tuple[bool, str]:
    """Easy runs averaging RPE > 5 in the last 7 days."""
    row = conn.execute(
        """SELECT AVG(wc.rpe), COUNT(wc.rpe)
           FROM workout_checkins wc
           JOIN activities a ON wc.activity_id = a.activity_id
           WHERE wc.activity_date BETWEEN ? AND ?
             AND wc.rpe IS NOT NULL
             AND (LOWER(a.name) LIKE '%easy%'
                  OR a.name LIKE '% E %'
                  OR a.name LIKE '% E,'
                  OR LOWER(a.name) LIKE '%easy run%')""",
        ((today - timedelta(days=6)).isoformat(), today.isoformat()),
    ).fetchone()

    avg_rpe, count = row[0], row[1]
    if not count or count < 2:
        return False, "insufficient easy-run check-in data"
    if avg_rpe > 5.0:
        return True, f"easy runs averaging RPE {avg_rpe:.1f}/10 (expected \u22644)"
    return False, ""


def _signal_body_battery(conn: sqlite3.Connection, today: date) -> Tuple[bool, str]:
    """Body battery below 30 for 3+ days in the last 7."""
    rows = conn.execute(
        "SELECT body_battery FROM daily_metrics "
        "WHERE day BETWEEN ? AND ? AND body_battery IS NOT NULL",
        ((today - timedelta(days=6)).isoformat(), today.isoformat()),
    ).fetchall()

    if len(rows) < 3:
        return False, "insufficient data"

    low_days = sum(1 for (bb,) in rows if bb < 30)
    if low_days >= 3:
        return True, f"body battery below 30 for {low_days} of the last 7 days"
    return False, ""


def _signal_sleep_debt(conn: sqlite3.Connection, today: date) -> Tuple[bool, str]:
    """Sleep under 6.5 hours for 3+ nights in the last 7."""
    rows = conn.execute(
        "SELECT sleep_duration_h FROM daily_metrics "
        "WHERE day BETWEEN ? AND ? AND sleep_duration_h IS NOT NULL",
        ((today - timedelta(days=6)).isoformat(), today.isoformat()),
    ).fetchall()

    if len(rows) < 3:
        return False, "insufficient data"

    short_nights = sum(1 for (h,) in rows if h < 6.5)
    if short_nights >= 3:
        return True, f"{short_nights} nights under 6.5 h sleep this week"
    return False, ""


def _signal_overreaching(today: date) -> Tuple[bool, str]:
    """Garmin training load feedback is OVERREACHING."""
    try:
        cache = json.loads(HEALTH_CACHE.read_text())
        feedback = (
            cache.get("training_status", {})
                 .get("training_load", {})
                 .get("feedback", "")
        )
        if feedback == "OVERREACHING":
            return True, "Garmin training status: OVERREACHING"
    except Exception:
        pass
    return False, ""


def _severity(fired: List[str], load_spike: bool) -> str:
    n = len(fired)
    if n >= 3 and load_spike:
        return "RED"
    if n >= 3:
        return "ORANGE"
    return "YELLOW"


def _build_message(fired: List[str], severity: str) -> str:
    label = {"YELLOW": "\u26a0\ufe0f", "ORANGE": "\U0001f7e0", "RED": "\U0001f534"}[severity]
    recs  = {
        "YELLOW": "Consider treating today's planned workout as easy.",
        "ORANGE": "Recommend modifying this week's remaining workouts \u2014 reduce intensity.",
        "RED":    "Recommend taking an unplanned rest day today.",
    }
    signals_text = "\n".join(f"\u2022 {s}" for s in fired)
    return (
        f"{label} **Injury risk flag ({severity})**\n\n"
        f"{signals_text}\n\n"
        f"{recs[severity]}\n\n"
        f"Want me to regenerate this week with a lighter load? "
        f"Reply **yes** to adjust, **no** to keep as-is."
    )


def run(db_path=None) -> Dict[str, Any]:
    """
    Compute 6 injury risk signals. If 2+ fire and cooldown has elapsed,
    write pending_injury_risk_alert to SQLite state.
    Returns {pending_written: bool, signals_fired: list, severity: str|None}
    """
    from memory.db import DB_PATH as _DEFAULT_DB, delete_state, get_state, set_state

    db = Path(db_path or _DEFAULT_DB)
    result: Dict[str, Any] = {
        "pending_written": False,
        "signals_fired":   [],
        "severity":        None,
    }

    last = get_state(_LAST_FIRED, db_path=db)
    if last:
        try:
            days_since = (date.today() - date.fromisoformat(last)).days
            if days_since < COOLDOWN_DAYS:
                log.debug("on_injury_risk: cooldown active (%d days since last alert)", days_since)
                return result
        except ValueError:
            pass

    if get_state(_PENDING_KEY, db_path=db) or get_state(_AWAITING_KEY, db_path=db):
        return result

    today = date.today()
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row

        fired:      List[str] = []
        load_spike: bool      = False

        ok, msg = _signal_load_spike(conn, today)
        if ok:
            fired.append(msg)
            load_spike = True

        ok, msg = _signal_hrv_streak(conn, today)
        if ok:
            fired.append(msg)

        ok, msg = _signal_easy_rpe(conn, today)
        if ok:
            fired.append(msg)

        ok, msg = _signal_body_battery(conn, today)
        if ok:
            fired.append(msg)

        ok, msg = _signal_sleep_debt(conn, today)
        if ok:
            fired.append(msg)

        conn.close()
    except Exception as exc:
        log.exception("on_injury_risk: signal computation error: %s", exc)
        return result

    ok, msg = _signal_overreaching(today)
    if ok:
        fired.append(msg)

    result["signals_fired"] = fired

    if len(fired) < SIGNAL_THRESHOLD:
        log.debug("on_injury_risk: %d/%d signals — no alert", len(fired), SIGNAL_THRESHOLD)
        return result

    severity = _severity(fired, load_spike)
    message  = _build_message(fired, severity)
    payload  = {"signals": fired, "severity": severity, "message": message}

    set_state(_PENDING_KEY, json.dumps(payload), db_path=db)
    set_state(_LAST_FIRED,  today.isoformat(),   db_path=db)

    result["pending_written"] = True
    result["severity"]        = severity
    log.info(
        "on_injury_risk: %s alert queued (%d signals: %s)",
        severity, len(fired), "; ".join(fired),
    )
    return result
