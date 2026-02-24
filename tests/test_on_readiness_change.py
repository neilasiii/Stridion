"""
Tests for hooks/on_readiness_change.py

Coverage:
  - Brain is called when readiness < READINESS_LOW
  - SQLite today_adjustment event is inserted after a successful call
  - Deduplication guard fires on a second call in the same day (Brain NOT called twice)
  - Brain is skipped when readiness is OK
  - Brain is skipped when confidence is "low"
  - Brain is skipped when no active plan exists
  - Brain is skipped (no event written) when it raises an exception
"""
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────

def _tmp_db() -> Path:
    tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tf.close()
    return Path(tf.name)


def _base_context(
    readiness_today: int = 35,
    confidence: str = "high",
    active_plan_id: str = "test-plan-001",
    sleep_hours: float | None = 7.0,
) -> dict:
    """Minimal context packet that would trigger on_readiness_change."""
    today_metrics: dict = {"training_readiness": readiness_today}
    if sleep_hours is not None:
        today_metrics["sleep_hours"] = sleep_hours
    return {
        "today": date.today().isoformat(),
        "data_quality": {"readiness_confidence": confidence},
        "plan_authority": {"active_plan_id": active_plan_id},
        "readiness_trend": {
            "today": today_metrics,
        },
    }


def _fake_adjustment() -> MagicMock:
    """Return a mock TodayAdjustment with the required fields."""
    adj = MagicMock()
    adj.workout_type = "rest"
    adj.adjustment_reason = "low_readiness"
    adj.adjusted_intent = "Recovery day due to low readiness."
    adj.rationale = "Readiness is below threshold."
    adj.model_dump.return_value = {
        "date": date.today().isoformat(),
        "workout_type": "rest",
        "adjustment_reason": "low_readiness",
    }
    return adj


def _run(ctx, db):
    from hooks.on_readiness_change import run
    return run(ctx, db_path=db)


# ── deduplication tests ───────────────────────────────────────────────────────

class TestReadinessChangeDedup:
    """Deduplication guard: Brain must not be called more than once per day."""

    def test_first_call_triggers_brain_and_writes_event(self):
        """First low-readiness cycle: Brain is called and event written to SQLite."""
        db = _tmp_db()
        from memory.db import init_db, query_events
        init_db(db_path=db)

        ctx = _base_context(readiness_today=35)
        fake_adj = _fake_adjustment()

        # get_metrics_range is lazy-imported from memory.db inside run(), so patch the source
        with (
            patch("memory.db.get_metrics_range", return_value=[]),
            patch("brain.adjust_today", return_value=fake_adj) as mock_brain,
            patch("memory.db.insert_plan_days") as mock_persist,
            patch("skills.publish_to_garmin.publish") as mock_publish,
        ):
            result = _run(ctx, db)

        assert result["triggered"] is True
        assert "readiness 35" in result["reason"]
        mock_brain.assert_called_once()
        mock_persist.assert_called_once()
        mock_publish.assert_called_once_with(days=1, dry_run=False, db_path=db)
        persist_args, persist_kwargs = mock_persist.call_args
        assert persist_args[0] == "test-plan-001"
        assert persist_args[1][0]["day"] == date.today().isoformat()
        assert persist_args[1][0]["intent"] == "Recovery day due to low readiness."
        assert persist_args[1][0]["workout_json"]["intent"] == "Recovery day due to low readiness."
        assert persist_kwargs["db_path"] == db

        # SQLite event must exist
        events = query_events(event_type="today_adjustment", db_path=db)
        assert len(events) == 1
        payload = json.loads(events[0]["payload_json"])
        assert payload["date"] == date.today().isoformat()
        assert payload["workout_type"] == "rest"

    def test_second_call_blocked_by_dedup(self):
        """Second call on the same day must return already_adjusted_today without calling Brain."""
        db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=db)

        ctx = _base_context(readiness_today=35)
        fake_adj = _fake_adjustment()

        with (
            patch("memory.db.get_metrics_range", return_value=[]),
            patch("brain.adjust_today", return_value=fake_adj) as mock_brain,
            patch("memory.db.insert_plan_days") as mock_persist,
            patch("skills.publish_to_garmin.publish") as mock_publish,
        ):
            first = _run(ctx, db)
            second = _run(ctx, db)

        assert first["triggered"] is True
        assert second["triggered"] is False
        assert second["reason"] == "already_adjusted_today"
        # Brain must have been called exactly once across both cycles
        mock_brain.assert_called_once()
        mock_persist.assert_called_once()
        mock_publish.assert_called_once_with(days=1, dry_run=False, db_path=db)

    def test_no_event_written_on_brain_failure(self):
        """If Brain raises, no SQLite event is written so the next cycle can retry."""
        db = _tmp_db()
        from memory.db import init_db, query_events
        init_db(db_path=db)

        ctx = _base_context(readiness_today=35)

        with patch("memory.db.get_metrics_range", return_value=[]):
            with patch("brain.adjust_today", side_effect=RuntimeError("LLM timeout")):
                result = _run(ctx, db)

        assert result["triggered"] is False
        assert "brain_error" in result["reason"]
        events = query_events(event_type="today_adjustment", db_path=db)
        assert len(events) == 0


# ── gate tests ────────────────────────────────────────────────────────────────

class TestReadinessChangeGates:
    """Early-exit gates: Brain must not be called under various skip conditions."""

    def test_no_sleep_today_skips(self):
        """Brain is not called when today's sleep data has not yet been synced."""
        db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=db)
        ctx = _base_context(readiness_today=35, sleep_hours=None)
        with patch("brain.adjust_today") as mock_brain:
            result = _run(ctx, db)
        assert result["triggered"] is False
        assert result["reason"] == "no_sleep_today"
        mock_brain.assert_not_called()

    def test_low_confidence_skips(self):
        db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=db)
        ctx = _base_context(confidence="low")
        with patch("brain.adjust_today") as mock_brain:
            result = _run(ctx, db)
        assert result["triggered"] is False
        assert result["reason"] == "confidence=low"
        mock_brain.assert_not_called()

    def test_no_active_plan_skips(self):
        db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=db)
        ctx = _base_context(active_plan_id="")
        with patch("brain.adjust_today") as mock_brain:
            result = _run(ctx, db)
        assert result["triggered"] is False
        assert result["reason"] == "no_active_plan"
        mock_brain.assert_not_called()

    def test_readiness_ok_skips(self):
        """Readiness well above threshold with no meaningful drop — Brain not called."""
        db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=db)
        # today=70, yesterday=72 → drop=2, below threshold=15; today > LOW=45
        ctx = _base_context(readiness_today=70)
        with patch("memory.db.get_metrics_range",
                   return_value=[{"training_readiness": 72}]):
            with patch("brain.adjust_today") as mock_brain:
                result = _run(ctx, db)
        assert result["triggered"] is False
        assert "readiness_ok" in result["reason"]
        mock_brain.assert_not_called()

    def test_drop_threshold_triggers(self):
        """A drop >= READINESS_DROP_THRESHOLD triggers Brain even when above READINESS_LOW."""
        db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=db)
        # today=52 (above LOW=45), yesterday=68 → drop=16 >= threshold=15
        ctx = _base_context(readiness_today=52)
        fake_adj = _fake_adjustment()
        with (
            patch("memory.db.get_metrics_range",
                  return_value=[{"training_readiness": 68}]),
            patch("brain.adjust_today", return_value=fake_adj) as mock_brain,
            patch("memory.db.insert_plan_days") as mock_persist,
            patch("skills.publish_to_garmin.publish") as mock_publish,
        ):
            result = _run(ctx, db)
        assert result["triggered"] is True
        assert "dropped 16" in result["reason"]
        mock_brain.assert_called_once()
        mock_persist.assert_called_once()
        mock_publish.assert_called_once_with(days=1, dry_run=False, db_path=db)
