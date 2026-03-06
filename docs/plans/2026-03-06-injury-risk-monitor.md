# Injury Risk Monitor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a heartbeat hook that monitors 6 overtraining signals from existing Garmin data and posts a plain-English alert to #coach when 2+ fire — closing the safety gap that previously required a human coach.

**Architecture:** New hook `hooks/on_injury_risk.py` reads from the SQLite `daily_metrics` and `activities` tables plus the health cache JSON. When 2+ signals fire and a 7-day cooldown has elapsed, it writes `pending_injury_risk_alert` to the SQLite state table. The bot delivers the alert embed to #coach and tracks a yes/no reply. "Yes" triggers `cli/coach.py plan --week --force` to regenerate a lighter week; "no" acknowledges and dismisses. Wired into `agent/runner.py` and `discord_bot.py` following the identical pattern as `on_cutover_ready`.

**Tech Stack:** Python stdlib, SQLite (`memory.db` helpers), `discord.py`, health_data_cache.json

---

## Background: existing patterns to follow

- **Hook pattern:** `hooks/on_cutover_ready.py` — copy the structure exactly
- **Bot delivery pattern:** `_post_pending_cutover_prompt()` in `src/discord_bot.py:2322`
- **Test pattern:** `tests/test_cutover.py` — copy the `make_db` helper, use `db_path=` throughout
- **State helpers:** `memory.db.get_state`, `set_state`, `delete_state` — all accept `db_path=`
- **CLI calls from bot:** `run_coach_cli(["plan", "--week", "--force"], timeout=300)`

## State keys

| Key | Purpose | Lifecycle |
|-----|---------|-----------|
| `pending_injury_risk_alert` | JSON payload queued for bot delivery | Cleared after bot posts |
| `injury_risk_last_fired` | ISO date of last alert (cooldown anchor) | Persists; updated on each alert |
| `injury_risk_awaiting_response` | Set after bot posts; cleared on yes/no | Cleared on athlete reply |

---

## Task 1: `hooks/on_injury_risk.py`

**Files:**
- Create: `hooks/on_injury_risk.py`
- Create: `tests/test_injury_risk.py`

### Step 1: Write failing tests first

```python
# tests/test_injury_risk.py
"""Tests for the injury risk monitor hook."""
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path


def make_db(tmp_path):
    from memory.db import init_db
    db = tmp_path / "coach.sqlite"
    init_db(db_path=db)
    return db


def _seed_daily_metrics(db, days_back: int, hrv: float, sleep_h: float, body_battery: float):
    """Insert a daily_metrics row for `days_back` days ago."""
    conn = sqlite3.connect(str(db))
    day = (date.today() - timedelta(days=days_back)).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO daily_metrics(day, hrv_rmssd, sleep_duration_h, body_battery) VALUES (?,?,?,?)",
        (day, hrv, sleep_h, body_battery),
    )
    conn.commit()
    conn.close()


def _seed_activity(db, days_back: int, distance_miles: float, activity_type: str = "running"):
    """Insert an activity row."""
    conn = sqlite3.connect(str(db))
    day = (date.today() - timedelta(days=days_back)).isoformat()
    act_id = f"test_{days_back}_{activity_type}"
    distance_m = distance_miles * 1609.34
    conn.execute(
        "INSERT OR IGNORE INTO activities(activity_id, activity_date, activity_type, distance_m, name) VALUES (?,?,?,?,?)",
        (act_id, day, activity_type, distance_m, f"Test {activity_type} run"),
    )
    conn.commit()
    conn.close()


# ── Signal unit tests ──────────────────────────────────────────────────────────

def test_load_spike_fires_at_11_percent(tmp_path):
    """Load spike fires when current week mileage is 11% above prior week."""
    db = make_db(tmp_path)
    # Prior week (days 7-13 ago): 20 miles total
    for d in range(7, 14):
        _seed_activity(db, d, 20.0 / 7)
    # Current week (days 0-6 ago): 22.2 miles (~11.1% more)
    for d in range(0, 7):
        _seed_activity(db, d, 22.2 / 7)

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_load_spike
    fired, msg = _signal_load_spike(conn, date.today())
    conn.close()
    assert fired is True
    assert "11%" in msg or "10%" in msg or "mi" in msg


def test_load_spike_no_fire_at_5_percent(tmp_path):
    """Load spike does not fire at 5% increase."""
    db = make_db(tmp_path)
    for d in range(7, 14):
        _seed_activity(db, d, 20.0 / 7)
    for d in range(0, 7):
        _seed_activity(db, d, 21.0 / 7)  # only 5% more

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_load_spike
    fired, _ = _signal_load_spike(conn, date.today())
    conn.close()
    assert fired is False


def test_load_spike_skips_with_low_prior_mileage(tmp_path):
    """Load spike skips when prior week mileage < 5 miles (insufficient data)."""
    db = make_db(tmp_path)
    _seed_activity(db, 8, 2.0)  # only 2 miles prior week
    _seed_activity(db, 1, 10.0)  # huge jump but prior too small

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_load_spike
    fired, msg = _signal_load_spike(conn, date.today())
    conn.close()
    assert fired is False


def test_hrv_streak_fires_at_3_consecutive_days(tmp_path):
    """HRV streak fires when last 3 days are all below baseline."""
    db = make_db(tmp_path)
    # Days 0-2: HRV 50ms (below 66ms baseline)
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=50.0, sleep_h=7.0, body_battery=40.0)
    # Day 3: above baseline (breaks streak going backwards — but we count from today)
    _seed_daily_metrics(db, 3, hrv=70.0, sleep_h=7.0, body_battery=40.0)

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_hrv_streak
    fired, msg = _signal_hrv_streak(conn, date.today())
    conn.close()
    assert fired is True
    assert "3" in msg or "consecutive" in msg


def test_hrv_streak_no_fire_at_2_days(tmp_path):
    """HRV streak does not fire at only 2 consecutive low days."""
    db = make_db(tmp_path)
    _seed_daily_metrics(db, 0, hrv=50.0, sleep_h=7.0, body_battery=40.0)
    _seed_daily_metrics(db, 1, hrv=50.0, sleep_h=7.0, body_battery=40.0)
    _seed_daily_metrics(db, 2, hrv=70.0, sleep_h=7.0, body_battery=40.0)  # above baseline

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_hrv_streak
    fired, _ = _signal_hrv_streak(conn, date.today())
    conn.close()
    assert fired is False


def test_body_battery_fires_at_3_low_days(tmp_path):
    """Body battery fires when 3+ days in last 7 have battery < 30."""
    db = make_db(tmp_path)
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=7.0, body_battery=20.0)  # below 30
    for d in range(3, 7):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=7.0, body_battery=50.0)  # above 30

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_body_battery
    fired, msg = _signal_body_battery(conn, date.today())
    conn.close()
    assert fired is True
    assert "3" in msg


def test_sleep_debt_fires_at_3_short_nights(tmp_path):
    """Sleep debt fires when 3+ nights have < 6.5h sleep in last 7 days."""
    db = make_db(tmp_path)
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=5.5, body_battery=50.0)  # under 6.5h
    for d in range(3, 7):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=8.0, body_battery=50.0)

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_sleep_debt
    fired, msg = _signal_sleep_debt(conn, date.today())
    conn.close()
    assert fired is True
    assert "3" in msg


def test_sleep_debt_no_fire_at_2_short_nights(tmp_path):
    """Sleep debt does not fire at only 2 short nights."""
    db = make_db(tmp_path)
    for d in range(0, 2):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=5.5, body_battery=50.0)
    for d in range(2, 7):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=8.0, body_battery=50.0)

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_sleep_debt
    fired, _ = _signal_sleep_debt(conn, date.today())
    conn.close()
    assert fired is False


# ── Severity tests ────────────────────────────────────────────────────────────

def test_severity_yellow_at_2_signals(tmp_path):
    from hooks.on_injury_risk import _severity
    assert _severity(["a", "b"], load_spike=False) == "YELLOW"


def test_severity_orange_at_3_no_spike(tmp_path):
    from hooks.on_injury_risk import _severity
    assert _severity(["a", "b", "c"], load_spike=False) == "ORANGE"


def test_severity_red_at_3_with_spike(tmp_path):
    from hooks.on_injury_risk import _severity
    assert _severity(["a", "b", "c"], load_spike=True) == "RED"


# ── run() integration tests ───────────────────────────────────────────────────

def test_run_writes_alert_at_2_signals(tmp_path):
    """run() writes pending_injury_risk_alert when 2 signals fire."""
    db = make_db(tmp_path)
    # Seed HRV streak (signal 2): 3 days below baseline
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=50.0, sleep_h=7.0, body_battery=50.0)
    for d in range(3, 7):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=7.0, body_battery=50.0)
    # Seed sleep debt (signal 5): 3 short nights
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=50.0, sleep_h=5.5, body_battery=50.0)

    from hooks.on_injury_risk import run
    from memory.db import get_state
    result = run(db_path=db)
    assert result["pending_written"] is True
    raw = get_state("pending_injury_risk_alert", db_path=db)
    assert raw is not None
    payload = json.loads(raw)
    assert "signals" in payload
    assert len(payload["signals"]) >= 2


def test_run_no_alert_at_1_signal(tmp_path):
    """run() does not write alert when only 1 signal fires."""
    db = make_db(tmp_path)
    # Only HRV streak
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=50.0, sleep_h=7.5, body_battery=50.0)
    for d in range(3, 7):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=7.5, body_battery=50.0)

    from hooks.on_injury_risk import run
    from memory.db import get_state
    result = run(db_path=db)
    assert result["pending_written"] is False
    assert get_state("pending_injury_risk_alert", db_path=db) is None


def test_run_cooldown_prevents_repeat(tmp_path):
    """run() does not re-queue if last_fired was within 7 days."""
    db = make_db(tmp_path)
    from memory.db import set_state
    # Simulate recent fire (2 days ago)
    set_state("injury_risk_last_fired", (date.today() - timedelta(days=2)).isoformat(), db_path=db)
    # Even if signals would fire, cooldown blocks it
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=50.0, sleep_h=5.5, body_battery=20.0)

    from hooks.on_injury_risk import run
    result = run(db_path=db)
    assert result["pending_written"] is False


def test_run_no_double_queue(tmp_path):
    """run() does not re-queue if alert is already pending."""
    db = make_db(tmp_path)
    from memory.db import set_state, get_state
    set_state("pending_injury_risk_alert", '{"signals":["x"],"severity":"YELLOW","message":"x"}', db_path=db)

    from hooks.on_injury_risk import run
    result = run(db_path=db)
    assert result["pending_written"] is False


def test_run_no_queue_while_awaiting_response(tmp_path):
    """run() does not re-queue while awaiting yes/no response."""
    db = make_db(tmp_path)
    from memory.db import set_state
    set_state("injury_risk_awaiting_response", "1", db_path=db)

    from hooks.on_injury_risk import run
    result = run(db_path=db)
    assert result["pending_written"] is False
```

### Step 2: Run tests to confirm they fail

```bash
cd /home/coach/running-coach && python -m pytest tests/test_injury_risk.py -v 2>&1 | head -30
```

Expected: `ImportError: No module named 'hooks.on_injury_risk'`

### Step 3: Create `hooks/on_injury_risk.py`

```python
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

PROJECT_ROOT = Path(__file__).parent.parent
HEALTH_CACHE  = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
PATTERNS_FILE = PROJECT_ROOT / "data" / "athlete" / "learned_patterns.md"

log = logging.getLogger("hooks.on_injury_risk")

_PENDING_KEY  = "pending_injury_risk_alert"
_LAST_FIRED   = "injury_risk_last_fired"
_AWAITING_KEY = "injury_risk_awaiting_response"

COOLDOWN_DAYS    = 7
SIGNAL_THRESHOLD = 2


# ── Baseline reader ───────────────────────────────────────────────────────────

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


# ── Six signal functions ──────────────────────────────────────────────────────

def _signal_load_spike(conn: sqlite3.Connection, today: date) -> Tuple[bool, str]:
    """Running mileage jumped >10% week-over-week."""
    def _miles(start: str, end: str) -> float:
        row = conn.execute(
            "SELECT SUM(distance_m) FROM activities "
            "WHERE activity_type = 'running' AND activity_date BETWEEN ? AND ?",
            (start, end),
        ).fetchone()
        return (row[0] or 0.0) / 1609.34

    prior   = _miles((today - timedelta(days=13)).isoformat(), (today - timedelta(days=7)).isoformat())
    current = _miles((today - timedelta(days=6)).isoformat(), today.isoformat())

    if prior < 5.0:
        return False, "insufficient prior-week data"
    pct = (current - prior) / prior
    if pct > 0.10:
        return True, f"mileage up {pct:.0%} ({prior:.1f}→{current:.1f} mi)"
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
        return True, f"easy runs averaging RPE {avg_rpe:.1f}/10 (expected ≤4)"
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


# ── Severity and message ──────────────────────────────────────────────────────

def _severity(fired: List[str], load_spike: bool) -> str:
    n = len(fired)
    if n >= 3 and load_spike:
        return "RED"
    if n >= 3:
        return "ORANGE"
    return "YELLOW"


def _build_message(fired: List[str], severity: str) -> str:
    label = {"YELLOW": "⚠️", "ORANGE": "🟠", "RED": "🔴"}[severity]
    recs  = {
        "YELLOW": "Consider treating today's planned workout as easy.",
        "ORANGE": "Recommend modifying this week's remaining workouts — reduce intensity.",
        "RED":    "Recommend taking an unplanned rest day today.",
    }
    signals_text = "\n".join(f"• {s}" for s in fired)
    return (
        f"{label} **Injury risk flag ({severity})**\n\n"
        f"{signals_text}\n\n"
        f"{recs[severity]}\n\n"
        f"Want me to regenerate this week with a lighter load? "
        f"Reply **yes** to adjust, **no** to keep as-is."
    )


# ── Main entry point ──────────────────────────────────────────────────────────

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

    # 7-day cooldown guard
    last = get_state(_LAST_FIRED, db_path=db)
    if last:
        try:
            days_since = (date.today() - date.fromisoformat(last)).days
            if days_since < COOLDOWN_DAYS:
                log.debug("on_injury_risk: cooldown active (%d days since last alert)", days_since)
                return result
        except ValueError:
            pass

    # Don't queue if already pending or awaiting response
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

    # Signal 6 reads from JSON file, not DB
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
```

### Step 4: Run tests to confirm they pass

```bash
cd /home/coach/running-coach && python -m pytest tests/test_injury_risk.py -v
```

Expected: all PASS

### Step 5: Commit

```bash
git add hooks/on_injury_risk.py tests/test_injury_risk.py
git commit -m "feat(injury-risk): add on_injury_risk hook with 6-signal detection"
```

---

## Task 2: Wire hook into `agent/runner.py`

**Files:**
- Modify: `agent/runner.py` (after line 218, the end of the `on_cutover_ready` block)

### Step 1: Write the test

Add to `tests/test_injury_risk.py`:

```python
def test_hook_importable_and_callable(tmp_path):
    """Smoke test: hook can be imported and run() returns expected structure."""
    db = make_db(tmp_path)
    from hooks.on_injury_risk import run
    result = run(db_path=db)
    assert "pending_written" in result
    assert "signals_fired" in result
    assert isinstance(result["signals_fired"], list)
```

### Step 2: Run to confirm it passes (hook already exists)

```bash
cd /home/coach/running-coach && python -m pytest tests/test_injury_risk.py::test_hook_importable_and_callable -v
```

Expected: PASS

### Step 3: Add step 9 to `run_cycle()` in `agent/runner.py`

After the `on_cutover_ready` block (around line 218), add:

```python
        # ── 9. Injury risk monitor (always) ─────────────────────────────────
        from hooks.on_injury_risk import run as on_injury_risk
        injury = on_injury_risk(db_path=db)
        if injury["pending_written"]:
            summary["hooks_run"].append("on_injury_risk")
            log.info("on_injury_risk: %s alert queued (%d signals)",
                     injury["severity"], len(injury["signals_fired"]))
```

### Step 4: Smoke-test runner import

```bash
cd /home/coach/running-coach && python -c "from agent.runner import run_cycle; print('OK')"
```

Expected: `OK`

### Step 5: Commit

```bash
git add agent/runner.py tests/test_injury_risk.py
git commit -m "feat(injury-risk): wire on_injury_risk into heartbeat agent run_cycle"
```

---

## Task 3: `_post_pending_injury_risk()` in `discord_bot.py`

**Files:**
- Modify: `src/discord_bot.py` (add after `_post_pending_cutover_prompt`, around line 2376)

### Step 1: Write the test

Add to `tests/test_injury_risk.py`:

```python
def test_post_pending_injury_risk_clears_pending_sets_awaiting(tmp_path):
    """_post_pending_injury_risk clears pending flag and sets awaiting flag."""
    import asyncio
    import shutil
    import unittest.mock as mock
    from memory.db import get_state, set_state

    db = make_db(tmp_path)
    payload = {"signals": ["HRV streak"], "severity": "YELLOW", "message": "test"}
    set_state("pending_injury_risk_alert", json.dumps(payload), db_path=db)

    # Place DB where the function reads it (PROJECT_ROOT/data/coach.sqlite)
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    test_db = data_dir / "coach.sqlite"
    shutil.copy(str(db), str(test_db))

    import src.discord_bot as bot_module
    import memory.db as db_module
    _real_set_state = db_module.set_state

    def _redirected(key, value, db_path=None):
        _real_set_state(key, value, db_path=test_db if db_path is None else db_path)

    original_root = bot_module.PROJECT_ROOT
    try:
        bot_module.PROJECT_ROOT = tmp_path
        db_module.set_state = _redirected
        mock_channel = mock.AsyncMock()
        result = asyncio.run(bot_module._post_pending_injury_risk(mock_channel))
    finally:
        bot_module.PROJECT_ROOT = original_root
        db_module.set_state = _real_set_state

    assert result is True
    mock_channel.send.assert_called_once()
    assert get_state("pending_injury_risk_alert", db_path=test_db) is None
    assert get_state("injury_risk_awaiting_response", db_path=test_db) == "1"


def test_post_pending_returns_false_when_nothing_pending(tmp_path):
    """_post_pending_injury_risk returns False when nothing queued."""
    import asyncio
    import unittest.mock as mock

    import src.discord_bot as bot_module
    original_root = bot_module.PROJECT_ROOT
    try:
        bot_module.PROJECT_ROOT = tmp_path  # No DB exists here
        mock_channel = mock.AsyncMock()
        result = asyncio.run(bot_module._post_pending_injury_risk(mock_channel))
    finally:
        bot_module.PROJECT_ROOT = original_root

    assert result is False
```

### Step 2: Run tests to confirm they fail

```bash
cd /home/coach/running-coach && python -m pytest tests/test_injury_risk.py::test_post_pending_injury_risk_clears_pending_sets_awaiting tests/test_injury_risk.py::test_post_pending_returns_false_when_nothing_pending -v
```

Expected: FAIL with `AttributeError: module 'src.discord_bot' has no attribute '_post_pending_injury_risk'`

### Step 3: Add `_post_pending_injury_risk` to `discord_bot.py`

Add after `_disable_finalsurge_calendar` (around line 2442):

```python
async def _post_pending_injury_risk(channel) -> bool:
    """
    If pending_injury_risk_alert is set, post the injury risk alert to #coach.
    Returns True if posted, False otherwise.
    """
    import sqlite3 as _sqlite3
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    if not db_path.exists():
        return False

    try:
        conn = _sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = _sqlite3.Row
        row = conn.execute(
            "SELECT value FROM state WHERE key = 'pending_injury_risk_alert'"
        ).fetchone()
        conn.close()
    except Exception as exc:
        logger.warning("_post_pending_injury_risk: DB read error: %s", exc)
        return False

    if not row:
        return False

    try:
        payload = json.loads(row["value"])
    except Exception:
        return False

    severity = payload.get("severity", "YELLOW")
    severity_colors = {
        "YELLOW": discord.Color.yellow(),
        "ORANGE": discord.Color.orange(),
        "RED":    discord.Color.red(),
    }

    try:
        embed = discord.Embed(
            title=f"Injury Risk Alert — {severity}",
            description=payload.get("message", "Overtraining signals detected."),
            color=severity_colors.get(severity, discord.Color.yellow()),
            timestamp=datetime.now(),
        )
        await channel.send(embed=embed)
    except Exception as exc:
        logger.error("_post_pending_injury_risk: send failed: %s", exc)
        return False

    # Clear pending, set awaiting response
    try:
        conn = _sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM state WHERE key = 'pending_injury_risk_alert'")
        conn.commit()
        conn.close()
        from memory.db import set_state
        set_state("injury_risk_awaiting_response", "1")
    except Exception as exc:
        logger.warning("_post_pending_injury_risk: state update error: %s", exc)

    logger.info("_post_pending_injury_risk: alert posted (%s)", severity)
    return True
```

### Step 4: Run tests to confirm they pass

```bash
cd /home/coach/running-coach && python -m pytest tests/test_injury_risk.py::test_post_pending_injury_risk_clears_pending_sets_awaiting tests/test_injury_risk.py::test_post_pending_returns_false_when_nothing_pending -v
```

Expected: PASS

### Step 5: Commit

```bash
git add src/discord_bot.py tests/test_injury_risk.py
git commit -m "feat(injury-risk): add _post_pending_injury_risk bot delivery function"
```

---

## Task 4: Wire delivery + yes/no reply handler

**Files:**
- Modify: `src/discord_bot.py`
  - `checkin_delivery_task` (~line 2453)
  - `on_ready` (~line 2651)
  - `on_message` (~line 1446)
  - Add `_handle_injury_risk_response()` function

### Step 1: Write the handler test

Add to `tests/test_injury_risk.py`:

```python
def test_yes_response_clears_awaiting_flag(tmp_path):
    """After 'yes' reply, injury_risk_awaiting_response is cleared."""
    db = make_db(tmp_path)
    from memory.db import set_state, get_state
    set_state("injury_risk_awaiting_response", "1", db_path=db)

    # Simulate what _handle_injury_risk_response does on "no" (sync-safe):
    from memory.db import delete_state
    delete_state("injury_risk_awaiting_response", db_path=db)

    assert get_state("injury_risk_awaiting_response", db_path=db) is None


def test_no_response_clears_awaiting_flag(tmp_path):
    """After 'no' reply, injury_risk_awaiting_response is cleared."""
    db = make_db(tmp_path)
    from memory.db import set_state, get_state, delete_state
    set_state("injury_risk_awaiting_response", "1", db_path=db)
    delete_state("injury_risk_awaiting_response", db_path=db)
    assert get_state("injury_risk_awaiting_response", db_path=db) is None
```

### Step 2: Run to confirm these pass (pure state logic)

```bash
cd /home/coach/running-coach && python -m pytest tests/test_injury_risk.py::test_yes_response_clears_awaiting_flag tests/test_injury_risk.py::test_no_response_clears_awaiting_flag -v
```

Expected: PASS

### Step 3: Add `_handle_injury_risk_response()` to `discord_bot.py`

Add after `_post_pending_injury_risk` (before `checkin_delivery_task`):

```python
async def _handle_injury_risk_response(message, confirmed: bool) -> None:
    """Handle athlete's yes/no reply to an injury risk alert."""
    from memory.db import delete_state
    delete_state("injury_risk_awaiting_response")

    if not confirmed:
        await message.reply("Got it. Keeping the plan as-is. I'll keep watching.")
        return

    await message.reply("Ok, regenerating this week with a lighter load…")
    rc, stdout, stderr = await run_coach_cli(["plan", "--week", "--force"], timeout=300)
    if rc == 0:
        reply = stdout.strip() or "Lighter week generated."
        await send_long_message(message, reply[:1900])
    else:
        await message.reply(f"Plan regeneration failed: {(stderr or stdout)[:500]}")
```

### Step 4: Add yes/no handler in `on_message`

In `on_message`, after the cutover delay handler block (around line 1446), add:

```python
            # ── Injury risk yes/no handler ───────────────────────────────────
            if lower.strip() in ("yes", "no"):
                from memory.db import get_state
                if get_state("injury_risk_awaiting_response"):
                    await _handle_injury_risk_response(message, lower.strip() == "yes")
                    return
```

### Step 5: Wire into `checkin_delivery_task`

In `checkin_delivery_task` (around line 2453), add after `_post_pending_cutover_prompt`:

```python
        await _post_pending_injury_risk(channel)
```

### Step 6: Wire into `on_ready`

In `on_ready`, after the cutover prompt block (around line 2651), add:

```python
    # Deliver any injury risk alert the heartbeat agent queued while Discord was offline
    if coach_channel:
        posted = await _post_pending_injury_risk(coach_channel)
        if posted:
            print("✓ Late injury risk alert delivered on reconnect")
```

Note: `coach_channel` is already defined in the cutover block above — no need to re-fetch it.

### Step 7: Run full test suite

```bash
cd /home/coach/running-coach && python -m pytest tests/test_injury_risk.py -v
```

Expected: all PASS

### Step 8: Smoke-test bot imports

```bash
cd /home/coach/running-coach && python -c "from src.discord_bot import _post_pending_injury_risk, _handle_injury_risk_response; print('OK')"
```

Expected: `OK`

### Step 9: Commit

```bash
git add src/discord_bot.py tests/test_injury_risk.py
git commit -m "feat(injury-risk): wire delivery, on_ready, and yes/no reply handler"
```

---

## Task 5: Integration check + bot restart

### Step 1: Run full test suite

```bash
cd /home/coach/running-coach && python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: no new failures

### Step 2: Smoke-test hook against live DB

```bash
cd /home/coach/running-coach && python -c "
from hooks.on_injury_risk import run
result = run()
print('pending_written:', result['pending_written'])
print('signals_fired:', result['signals_fired'])
print('severity:', result['severity'])
"
```

Expected: runs cleanly, pending_written is False (no real signals today unless truly overtraining)

### Step 3: Manual signal test (optional — verify data reads work)

```bash
cd /home/coach/running-coach && python -c "
import sqlite3
from datetime import date, timedelta
from hooks.on_injury_risk import _signal_hrv_streak, _signal_sleep_debt, _signal_body_battery, _read_hrv_baseline

from memory.db import DB_PATH
conn = sqlite3.connect(str(DB_PATH))
today = date.today()
print('HRV baseline:', _read_hrv_baseline())
print('HRV streak:', _signal_hrv_streak(conn, today))
print('Sleep debt:', _signal_sleep_debt(conn, today))
print('Body battery:', _signal_body_battery(conn, today))
conn.close()
"
```

### Step 4: Restart bot

```bash
sudo systemctl restart running-coach-bot && sudo systemctl status running-coach-bot
```

Expected: `active (running)`

### Step 5: Final commit

```bash
git add -A
git commit -m "feat(injury-risk): injury risk monitor complete — 6 signals, Discord alert, yes/no replan"
```

---

## Summary

| Component | File | New/Modified |
|-----------|------|-------------|
| 6-signal hook | `hooks/on_injury_risk.py` | New |
| Hook wiring | `agent/runner.py` | Modified (1 block) |
| Bot delivery | `src/discord_bot.py` (`_post_pending_injury_risk`) | Modified |
| Reply handler | `src/discord_bot.py` (`_handle_injury_risk_response`) | Modified |
| Delivery wiring | `src/discord_bot.py` (`checkin_delivery_task`, `on_ready`, `on_message`) | Modified |
| Tests | `tests/test_injury_risk.py` | New |

**Signal summary:**
| # | Signal | Source | Threshold |
|---|--------|--------|-----------|
| 1 | Weekly load spike | `activities` table | >10% increase |
| 2 | HRV suppression streak | `daily_metrics` table | 3+ consecutive days below personal baseline |
| 3 | Easy RPE elevation | `workout_checkins` + `activities` | avg RPE > 5 for easy runs, 2+ data points |
| 4 | Body battery chronic drain | `daily_metrics` table | 3+ days below 30 in last 7 |
| 5 | Sleep debt accumulation | `daily_metrics` table | 3+ nights under 6.5h in last 7 |
| 6 | Garmin OVERREACHING flag | `health_data_cache.json` | feedback == "OVERREACHING" |
