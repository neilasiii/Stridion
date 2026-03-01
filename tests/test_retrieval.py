"""
Tests for memory/retrieval.py — context packet builder.

Scope:
  B11-009 — verify activities are capped to days_back before rollup
  B11-014 — readiness_trend reads from daily_metrics SQLite when populated;
            falls back cleanly to JSON cache when table is empty
"""
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_activity(days_ago: int, activity_type: str = "running") -> dict:
    """Return a minimal activity dict with a startTimeLocal matching days_ago."""
    d = (date.today() - timedelta(days=days_ago)).isoformat()
    return {
        "startTimeLocal": d + "T07:00:00",
        "activityType": {"typeKey": activity_type},
        "distance": 8046.72,   # 5 miles in metres
        "duration": 2700,
        "averageHR": 145,
    }


def _make_health_cache(activity_days_ago: list) -> dict:
    """Build a minimal health cache with activities at the given offsets."""
    return {
        "activities": [_make_activity(d) for d in activity_days_ago],
        "hrv": [],
        "sleep": [],
        "body_battery": [],
        "training_readiness": [],
        "resting_hr": [],
        "vo2_max": None,
        "last_updated": date.today().isoformat(),
    }


# ── tests ─────────────────────────────────────────────────────────────────────

class TestActivitiesCap:
    """Verify that build_context_packet trims activities to days_back."""

    def _build_packet(self, health_cache: dict, days_back: int = 14):
        """Call build_context_packet with a patched health cache (no DB needed)."""
        from memory.retrieval import build_context_packet

        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
            db_path = Path(tf.name)

        try:
            # Patch _load_health_cache to return our synthetic data
            with patch("memory.retrieval._load_health_cache", return_value=health_cache):
                # init_db is called inside; use temp DB to avoid side effects
                from memory.db import init_db
                init_db(db_path=db_path)
                packet = build_context_packet(days_back=days_back, db_path=db_path)
        finally:
            db_path.unlink(missing_ok=True)

        return packet

    def test_old_activities_excluded_from_training_summary(self):
        """Activities older than days_back must not appear in training_summary."""
        # 2 recent activities + 1 old activity (30 days ago, outside 14-day window)
        health = _make_health_cache(activity_days_ago=[1, 5, 30])
        packet = self._build_packet(health, days_back=14)

        ts = packet["training_summary"]
        assert ts["count"] == 2, f"Expected 2 recent activities, got {ts['count']}"

        run_dates = [r["date"] for r in ts["recent_runs"]]
        cutoff = (date.today() - timedelta(days=14)).isoformat()
        for d in run_dates:
            assert d >= cutoff, f"Old activity date {d!r} should have been excluded"

    def test_no_activities_in_window_returns_zero(self):
        """If all activities are older than days_back, count should be 0."""
        health = _make_health_cache(activity_days_ago=[20, 25, 30])
        packet = self._build_packet(health, days_back=14)

        ts = packet["training_summary"]
        assert ts["count"] == 0
        assert ts["recent_runs"] == []

    def test_all_recent_activities_included(self):
        """Activities within days_back are all counted (up to cap of 7 in recent_runs)."""
        health = _make_health_cache(activity_days_ago=[1, 3, 5, 7, 10, 12])
        packet = self._build_packet(health, days_back=14)

        ts = packet["training_summary"]
        assert ts["count"] == 6, f"All 6 recent activities should be counted, got {ts['count']}"

    def test_packet_size_bounded(self):
        """packet_size_chars should be reasonable even with many historical activities."""
        # 50 old activities + 5 recent ones
        old = list(range(15, 65))   # 15–64 days ago
        recent = [1, 3, 5, 8, 12]
        health = _make_health_cache(activity_days_ago=old + recent)

        packet = self._build_packet(health, days_back=14)

        size = packet["data_quality"]["packet_size_chars"]
        # With 50 old activities excluded, packet should be small
        assert size < 8_000, f"Packet too large: {size} chars (expected <8000)"

        ts = packet["training_summary"]
        assert ts["count"] == 5, "Only the 5 recent activities should be counted"


# ── B11-014: readiness_trend SQLite vs JSON fallback ──────────────────────────

class TestReadinessTrendSQLitePath:
    """readiness_trend should come from daily_metrics when rows are present."""

    def _empty_health(self):
        return {
            "activities": [],
            "hrv": [], "sleep": [], "body_battery": [],
            "training_readiness": [], "resting_hr": [],
            "vo2_max": None, "last_updated": date.today().isoformat(),
        }

    def _build_packet_with_db(self, db_path):
        from memory.retrieval import build_context_packet
        from memory.db import init_db
        init_db(db_path=db_path)
        with patch("memory.retrieval._load_health_cache", return_value=self._empty_health()):
            return build_context_packet(days_back=7, db_path=db_path)

    def test_sqlite_path_used_when_rows_present(self, tmp_path):
        from memory.db import init_db, upsert_daily_metrics
        db = tmp_path / "test.sqlite"
        init_db(db_path=db)

        today = date.today()
        upsert_daily_metrics(
            today,
            hrv_rmssd=65.0, resting_hr=48.0, sleep_score=82.0,
            sleep_duration_h=7.8, body_battery=90, training_readiness=75,
            stress_avg=20.0, db_path=db,
        )

        packet = self._build_packet_with_db(db)
        rt = packet["readiness_trend"]

        assert rt.get("source") == "sqlite", "Expected source='sqlite' when rows present"
        assert rt["today"]["hrv"] == pytest.approx(65.0)
        assert rt["today"]["sleep_score"] == pytest.approx(82.0)
        assert rt["today"]["body_battery_max"] == pytest.approx(90)
        assert rt["today"]["training_readiness"] == pytest.approx(75)
        assert rt["today"]["rhr"] == pytest.approx(48.0)

    def test_trend_averages_over_multiple_days(self, tmp_path):
        from memory.db import init_db, upsert_daily_metrics
        db = tmp_path / "test.sqlite"
        init_db(db_path=db)

        today = date.today()
        for i in range(3):
            upsert_daily_metrics(
                today - timedelta(days=i),
                hrv_rmssd=60.0 + i * 5, db_path=db,
            )

        packet = self._build_packet_with_db(db)
        rt = packet["readiness_trend"]

        # avg_hrv should be mean of 60, 65, 70 = 65
        assert rt["trend"]["avg_hrv"] == pytest.approx(65.0)

    def test_fallback_to_json_when_table_empty(self, tmp_path):
        """With empty daily_metrics table, readiness_trend must not have source='sqlite'."""
        from memory.db import init_db
        db = tmp_path / "test.sqlite"
        init_db(db_path=db)  # empty table

        packet = self._build_packet_with_db(db)
        rt = packet["readiness_trend"]

        assert rt.get("source") != "sqlite", "Empty table must trigger JSON fallback"
        assert "period_days" in rt  # still returns a valid (empty) dict

    def test_fallback_when_sqlite_unavailable(self, tmp_path):
        """If get_daily_metrics raises, must fall back gracefully."""
        from memory.db import init_db
        db = tmp_path / "test.sqlite"
        init_db(db_path=db)

        with patch("memory.retrieval._rollup_readiness_from_sqlite", return_value=None):
            packet = self._build_packet_with_db(db)

        rt = packet["readiness_trend"]
        assert "period_days" in rt


def test_context_packet_has_athlete_patterns_key(tmp_path):
    """build_context_packet() always includes athlete_patterns key (may be None)."""
    from memory.retrieval import build_context_packet
    from memory.db import init_db
    db_path = tmp_path / "test.sqlite"
    init_db(db_path=db_path)
    packet = build_context_packet(db_path=db_path)
    assert "athlete_patterns" in packet  # key exists even if value is None
