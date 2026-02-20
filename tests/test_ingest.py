"""
Tests for B11-012 (daily_metrics ingest) and B11-013 (activities ingest).

Scope:
  - _ingest_daily_metrics() maps each cache section to the right column
  - _ingest_activities() maps activity fields correctly
  - run() calls both ingest functions after a successful sync
  - run() skips ingest on check_only or failed sync
  - ingest uses the days param to filter stale data
"""
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _tmp_db() -> Path:
    tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tf.close()
    return Path(tf.name)


def _today() -> str:
    return date.today().isoformat()


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _make_health_cache(n_days: int = 3) -> dict:
    """Build a minimal health cache for the last n_days."""
    cache = {
        "last_updated": _today(),
        "hrv_readings": [],
        "sleep_sessions": [],
        "body_battery": [],
        "training_readiness": [],
        "resting_hr_readings": [],
        "stress_readings": [],
        "activities": [],
    }
    for i in range(n_days):
        d = _days_ago(i)
        cache["hrv_readings"].append({"date": d, "last_night_avg": 60 + i, "weekly_avg": 62})
        cache["sleep_sessions"].append({
            "date": d, "total_duration_minutes": 420.0 + i * 10,
            "sleep_score": 75.0 + i,
        })
        cache["body_battery"].append({"date": d, "latest_level": 80 - i, "charged": 90})
        cache["training_readiness"].append({"date": d, "score": 70 + i})
        cache["resting_hr_readings"].append([f"{d}T12:00:00", 50 - i])
        cache["stress_readings"].append({"date": d, "avg_stress": 25 + i})

        cache["activities"].append({
            "activity_id": 1000 + i,
            "date": f"{d}T07:00:00",
            "activity_name": f"Run day {i}",
            "activity_type": "RUNNING",
            "duration_seconds": 3600.0,
            "distance_miles": 6.0,
            "avg_heart_rate": 150.0,
            "max_heart_rate": 170.0,
            "pace_per_mile": 10.0,
            "calories": 600.0,
        })

    return cache


def _fake_proc(rc=0, stdout="Sync complete\n", stderr=""):
    m = MagicMock()
    m.returncode = rc
    m.stdout = stdout
    m.stderr = stderr
    return m


# ── Unit: _ingest_daily_metrics ───────────────────────────────────────────────

class TestIngestDailyMetrics:
    def setup_method(self):
        self.db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=self.db)

    def test_inserts_row_per_date(self):
        from skills.garmin_sync import _ingest_daily_metrics
        from memory.db import get_daily_metrics

        health = _make_health_cache(n_days=3)
        count = _ingest_daily_metrics(health, days=7, db_path=self.db)

        assert count == 3
        rows = get_daily_metrics(
            date.today() - timedelta(days=7), date.today(), db_path=self.db
        )
        assert len(rows) == 3

    def test_hrv_mapped_to_hrv_rmssd(self):
        from skills.garmin_sync import _ingest_daily_metrics
        from memory.db import get_daily_metrics

        health = _make_health_cache(n_days=1)
        _ingest_daily_metrics(health, days=7, db_path=self.db)

        rows = get_daily_metrics(date.today(), date.today(), db_path=self.db)
        assert rows[0]["hrv_rmssd"] == 60  # last_night_avg from day 0

    def test_sleep_duration_h_converted(self):
        from skills.garmin_sync import _ingest_daily_metrics
        from memory.db import get_daily_metrics

        health = _make_health_cache(n_days=1)
        _ingest_daily_metrics(health, days=7, db_path=self.db)

        rows = get_daily_metrics(date.today(), date.today(), db_path=self.db)
        assert rows[0]["sleep_duration_h"] == pytest.approx(420.0 / 60, rel=1e-3)

    def test_resting_hr_from_list_format(self):
        from skills.garmin_sync import _ingest_daily_metrics
        from memory.db import get_daily_metrics

        health = _make_health_cache(n_days=1)
        _ingest_daily_metrics(health, days=7, db_path=self.db)

        rows = get_daily_metrics(date.today(), date.today(), db_path=self.db)
        assert rows[0]["resting_hr"] == 50  # first entry value

    def test_old_dates_excluded(self):
        from skills.garmin_sync import _ingest_daily_metrics
        from memory.db import get_daily_metrics

        health = _make_health_cache(n_days=5)
        # days=1 → cutoff = yesterday; only today and yesterday pass (2 rows)
        count = _ingest_daily_metrics(health, days=1, db_path=self.db)

        assert count == 2

    def test_missing_section_yields_null(self):
        from skills.garmin_sync import _ingest_daily_metrics
        from memory.db import get_daily_metrics

        # cache with only hrv, no sleep/BB/TR
        d = _today()
        health = {
            "hrv_readings": [{"date": d, "last_night_avg": 55}],
            "sleep_sessions": [],
            "body_battery": [],
            "training_readiness": [],
            "resting_hr_readings": [],
            "stress_readings": [],
        }
        _ingest_daily_metrics(health, days=7, db_path=self.db)
        rows = get_daily_metrics(date.today(), date.today(), db_path=self.db)
        assert rows[0]["hrv_rmssd"] == pytest.approx(55)
        assert rows[0]["sleep_score"] is None
        assert rows[0]["body_battery"] is None


# ── Unit: _ingest_activities ──────────────────────────────────────────────────

class TestIngestActivities:
    def setup_method(self):
        self.db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=self.db)

    def test_inserts_row_per_activity(self):
        from skills.garmin_sync import _ingest_activities
        from memory.db import get_activities

        health = _make_health_cache(n_days=3)
        count = _ingest_activities(health, days=7, db_path=self.db)

        assert count == 3
        rows = get_activities(date.today() - timedelta(days=7), date.today(),
                              db_path=self.db)
        assert len(rows) == 3

    def test_distance_converted_to_metres(self):
        from skills.garmin_sync import _ingest_activities
        from memory.db import get_activities

        health = _make_health_cache(n_days=1)
        _ingest_activities(health, days=7, db_path=self.db)

        rows = get_activities(date.today(), date.today(), db_path=self.db)
        assert rows[0]["distance_m"] == pytest.approx(6.0 * 1609.34, rel=1e-4)

    def test_pace_converted_to_seconds_per_mile(self):
        from skills.garmin_sync import _ingest_activities
        from memory.db import get_activities

        health = _make_health_cache(n_days=1)
        _ingest_activities(health, days=7, db_path=self.db)

        rows = get_activities(date.today(), date.today(), db_path=self.db)
        # pace_per_mile = 10.0 min/mile → 600 s/mile
        assert rows[0]["avg_pace_s"] == pytest.approx(600.0)

    def test_activity_type_lowercased(self):
        from skills.garmin_sync import _ingest_activities
        from memory.db import get_activities

        health = _make_health_cache(n_days=1)
        _ingest_activities(health, days=7, db_path=self.db)

        rows = get_activities(date.today(), date.today(), db_path=self.db)
        assert rows[0]["activity_type"] == "running"

    def test_old_activities_excluded(self):
        from skills.garmin_sync import _ingest_activities
        from memory.db import get_activities

        health = _make_health_cache(n_days=5)
        # days=1 → cutoff = yesterday; only today and yesterday pass (2 rows)
        count = _ingest_activities(health, days=1, db_path=self.db)
        assert count == 2

    def test_upsert_idempotent(self):
        from skills.garmin_sync import _ingest_activities
        from memory.db import get_activities

        health = _make_health_cache(n_days=2)
        _ingest_activities(health, days=7, db_path=self.db)
        _ingest_activities(health, days=7, db_path=self.db)  # second call

        rows = get_activities(date.today() - timedelta(days=7), date.today(),
                              db_path=self.db)
        assert len(rows) == 2  # not doubled


# ── Integration: run() wires ingest after successful sync ─────────────────────

class TestRunIngestsAfterSync:
    """run() must ingest both tables after a successful sync."""

    def setup_method(self):
        self.db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=self.db)

    def _run_sync(self, rc=0, health=None, **kwargs):
        from skills import garmin_sync

        fake_health = health if health is not None else _make_health_cache(n_days=2)

        with (
            patch("skills.garmin_sync._cache_age_minutes", return_value=999.0),
            patch("skills.garmin_sync.subprocess.run", return_value=_fake_proc(rc=rc)),
            patch("skills.garmin_sync._load_cache", return_value=fake_health),
            patch("memory.db.init_db"),
        ):
            return garmin_sync.run(source="test", db_path=self.db, **kwargs)

    def test_successful_sync_ingests_daily_metrics(self):
        result = self._run_sync()
        assert result["ingest_metrics_rows"] == 2

    def test_successful_sync_ingests_activities(self):
        result = self._run_sync()
        assert result["ingest_activities_rows"] == 2

    def test_failed_sync_skips_ingest(self):
        result = self._run_sync(rc=1)
        assert result["ingest_metrics_rows"] == 0
        assert result["ingest_activities_rows"] == 0

    def test_check_only_skips_ingest(self):
        result = self._run_sync(check_only=True)
        assert result["ingest_metrics_rows"] == 0
        assert result["ingest_activities_rows"] == 0

    def test_days_param_limits_ingest(self):
        health = _make_health_cache(n_days=5)
        # days=1 → cutoff = yesterday; today + yesterday = 2 rows
        result = self._run_sync(health=health, days=1)
        assert result["ingest_metrics_rows"] == 2
        assert result["ingest_activities_rows"] == 2
