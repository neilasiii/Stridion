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


# Signal unit tests

def test_load_spike_fires_at_11_percent(tmp_path):
    """Load spike fires when current week mileage is 11% above prior week."""
    db = make_db(tmp_path)
    for d in range(7, 14):
        _seed_activity(db, d, 20.0 / 7)
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
        _seed_activity(db, d, 21.0 / 7)

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_load_spike
    fired, _ = _signal_load_spike(conn, date.today())
    conn.close()
    assert fired is False


def test_load_spike_skips_with_low_prior_mileage(tmp_path):
    """Load spike skips when prior week mileage < 5 miles."""
    db = make_db(tmp_path)
    _seed_activity(db, 8, 2.0)
    _seed_activity(db, 1, 10.0)

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_load_spike
    fired, msg = _signal_load_spike(conn, date.today())
    conn.close()
    assert fired is False


def test_hrv_streak_fires_at_3_consecutive_days(tmp_path):
    """HRV streak fires when last 3 days are all below baseline."""
    db = make_db(tmp_path)
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=50.0, sleep_h=7.0, body_battery=40.0)
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
    _seed_daily_metrics(db, 2, hrv=70.0, sleep_h=7.0, body_battery=40.0)

    conn = sqlite3.connect(str(db))
    from hooks.on_injury_risk import _signal_hrv_streak
    fired, _ = _signal_hrv_streak(conn, date.today())
    conn.close()
    assert fired is False


def test_body_battery_fires_at_3_low_days(tmp_path):
    """Body battery fires when 3+ days in last 7 have battery < 30."""
    db = make_db(tmp_path)
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=7.0, body_battery=20.0)
    for d in range(3, 7):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=7.0, body_battery=50.0)

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
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=5.5, body_battery=50.0)
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


# Severity tests

def test_severity_yellow_at_2_signals(tmp_path):
    from hooks.on_injury_risk import _severity
    assert _severity(["a", "b"], load_spike=False) == "YELLOW"


def test_severity_orange_at_3_no_spike(tmp_path):
    from hooks.on_injury_risk import _severity
    assert _severity(["a", "b", "c"], load_spike=False) == "ORANGE"


def test_severity_red_at_3_with_spike(tmp_path):
    from hooks.on_injury_risk import _severity
    assert _severity(["a", "b", "c"], load_spike=True) == "RED"


# run() integration tests

def test_run_writes_alert_at_2_signals(tmp_path):
    """run() writes pending_injury_risk_alert when 2 signals fire."""
    db = make_db(tmp_path)
    for d in range(0, 3):
        _seed_daily_metrics(db, d, hrv=50.0, sleep_h=7.0, body_battery=50.0)
    for d in range(3, 7):
        _seed_daily_metrics(db, d, hrv=66.0, sleep_h=7.0, body_battery=50.0)
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
    set_state("injury_risk_last_fired", (date.today() - timedelta(days=2)).isoformat(), db_path=db)
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
