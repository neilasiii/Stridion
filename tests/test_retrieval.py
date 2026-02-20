"""
Tests for memory/retrieval.py — context packet builder.

Scope: B11-009 — verify activities are capped to days_back before rollup
so the full 60-day cache is never loaded into the in-memory health dict
during context-packet construction.
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
