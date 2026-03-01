"""Tests: morning_report reads internal plan before health cache."""
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _make_session(d: str, wtype: str = "easy", dur: int = 45, intent: str = "Easy effort", steps=None):
    return {
        "date": d,
        "workout_type": wtype,
        "duration_min": dur,
        "intent": intent,
        "structure_steps": steps or [],
        "safety_flags": [],
        "plan_id": "test-plan",
    }


class TestSessionToWorkout:
    """_session_to_workout converts SQLite session → workout dict."""

    def _convert(self, session):
        from morning_report import _session_to_workout
        return _session_to_workout(session)

    def test_sets_source_to_internal_plan(self):
        w = self._convert(_make_session("2026-03-01"))
        assert w["source"] == "internal_plan"

    def test_easy_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="easy"))
        assert w["name"] == "Easy Run"

    def test_tempo_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="tempo"))
        assert w["name"] == "Tempo Run"

    def test_long_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="long"))
        assert w["name"] == "Long Run"

    def test_interval_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="interval"))
        assert w["name"] == "Interval Run"

    def test_intent_in_description(self):
        w = self._convert(_make_session("2026-03-01", intent="Keep it easy, conversational"))
        assert "Keep it easy, conversational" in w["description"]

    def test_duration_min_preserved(self):
        w = self._convert(_make_session("2026-03-01", dur=60))
        assert w["duration_min"] == 60

    def test_steps_in_description(self):
        steps = [
            {"label": "warmup", "duration_min": 10, "reps": None, "target_value": "easy"},
            {"label": "main", "duration_min": 25, "reps": None, "target_value": "tempo"},
            {"label": "cooldown", "duration_min": 10, "reps": None, "target_value": "easy"},
        ]
        w = self._convert(_make_session("2026-03-01", steps=steps))
        assert "Warmup" in w["description"]
        assert "10min" in w["description"]
        assert "Main" in w["description"]
        assert "25min" in w["description"]

    def test_no_steps_no_structure_section(self):
        w = self._convert(_make_session("2026-03-01", steps=[]))
        assert "Structure:" not in w["description"]


class TestGetTodaysWorkout:
    """get_todays_workout prefers internal plan over health cache."""

    def _call(self, sessions, cache_workouts, today_str=None):
        from morning_report import get_todays_workout
        cache = {"scheduled_workouts": cache_workouts}
        with patch("morning_report.get_active_sessions", return_value=sessions):
            return get_todays_workout(cache)

    def test_returns_internal_plan_when_available(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="tempo", dur=55)]
        result = self._call(sessions, [])
        assert result is not None
        assert result[0]["source"] == "internal_plan"
        assert result[0]["name"] == "Tempo Run"

    def test_falls_back_to_cache_when_no_plan(self):
        today = date.today().isoformat()
        cache_workouts = [{
            "scheduled_date": today,
            "name": "Easy 30min",
            "description": "Easy run",
            "source": "ics_calendar",
        }]
        result = self._call([], cache_workouts)
        assert result is not None
        assert result[0]["source"] != "internal_plan"

    def test_rest_day_returns_none(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="rest", dur=0)]
        result = self._call(sessions, [])
        assert result is None

    def test_wrong_date_session_ignored(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        sessions = [_make_session(yesterday, wtype="easy")]
        result = self._call(sessions, [])
        assert result is None

    def test_falls_back_to_cache_when_sessions_exist_but_no_today_match(self):
        """If plan has sessions but none for today, fall back to health cache."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = [_make_session(yesterday), _make_session(tomorrow)]
        today = date.today().isoformat()
        cache_workouts = [{
            "scheduled_date": today,
            "name": "Cache Easy Run",
            "description": "From cache",
            "source": "ics_calendar",
        }]
        result = self._call(sessions, cache_workouts)
        assert result is not None
        assert result[0]["source"] != "internal_plan"
        assert result[0]["name"] == "Cache Easy Run"


class TestGetUpcomingWorkouts:
    """get_upcoming_workouts prefers internal plan over health cache."""

    def _call(self, sessions, cache_workouts, days=3):
        from morning_report import get_upcoming_workouts
        cache = {"scheduled_workouts": cache_workouts}
        with patch("morning_report.get_active_sessions", return_value=sessions):
            return get_upcoming_workouts(cache, days=days)

    def test_returns_internal_plan_sessions(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = [_make_session(tomorrow, wtype="long", dur=90, intent="Long easy run")]
        result = self._call(sessions, [])
        assert len(result) == 1
        assert result[0]["source"] == "internal_plan"
        assert result[0]["name"] == "Long Run"

    def test_excludes_today_and_past(self):
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        sessions = [_make_session(today), _make_session(yesterday)]
        result = self._call(sessions, [])
        assert result == []

    def test_excludes_beyond_window(self):
        far = (date.today() + timedelta(days=10)).isoformat()
        sessions = [_make_session(far)]
        result = self._call(sessions, [], days=5)
        assert result == []

    def test_rest_days_excluded(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = [_make_session(tomorrow, wtype="rest")]
        result = self._call(sessions, [])
        assert result == []

    def test_falls_back_to_cache_when_no_plan(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        cache_workouts = [{"scheduled_date": tomorrow, "name": "Easy run", "description": "", "domain": "running"}]
        result = self._call([], cache_workouts)
        assert len(result) == 1

    def test_falls_back_to_cache_when_sessions_exist_but_none_in_window(self):
        """If plan has sessions but none fall in the upcoming window, use cache."""
        # Session is 30 days away — outside the 3-day window
        far_future = (date.today() + timedelta(days=30)).isoformat()
        sessions = [_make_session(far_future, wtype="easy")]
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        cache_workouts = [{"scheduled_date": tomorrow, "name": "Cache Easy Run", "description": "", "domain": "running"}]
        result = self._call(sessions, cache_workouts, days=3)
        assert len(result) == 1
        assert result[0]["name"] == "Cache Easy Run"


class TestParseAiResponse:
    """parse_ai_response extracts notification, adjustment, and full report."""

    def _parse(self, text):
        from morning_report import parse_ai_response
        return parse_ai_response(text)

    def test_extracts_notification(self):
        text = "NOTIFICATION:\n45min E as planned. Recovery excellent.\nADJUSTMENT:\nAs planned\nFULL_REPORT:\n## Recovery\nAll good."
        notif, _ = self._parse(text)
        assert "45min E as planned" in notif

    def test_as_planned_not_prepended_to_report(self):
        text = "NOTIFICATION:\nAs planned.\nADJUSTMENT:\nAs planned\nFULL_REPORT:\n## Recovery\nGood numbers."
        _, report = self._parse(text)
        assert "## Adjustment" not in report
        assert not report.startswith("## Adjustment")  # no Adjustment header prepended
        assert "As planned" not in report.split("## Recovery")[0]

    def test_modification_prepended_to_full_report(self):
        text = (
            "NOTIFICATION:\n45min E → 30min E (HRV low).\n"
            "ADJUSTMENT:\nOriginal: Easy 45min\nRecommended: Easy 30min\nReason: HRV well below norm.\n"
            "FULL_REPORT:\n## Recovery\nHRV tanked."
        )
        _, report = self._parse(text)
        assert report.startswith("## Adjustment")
        assert "Original: Easy 45min" in report
        assert "## Recovery" in report

    def test_missing_adjustment_section_still_parses(self):
        """Backwards compat: AI skips ADJUSTMENT — report still parses."""
        text = "NOTIFICATION:\nAs planned.\nFULL_REPORT:\n## Recovery\nAll good."
        notif, report = self._parse(text)
        assert "As planned" in notif
        assert "## Recovery" in report

    def test_notification_trimmed_to_240_chars(self):
        long_notif = "X" * 300
        text = f"NOTIFICATION:\n{long_notif}\nADJUSTMENT:\nAs planned\nFULL_REPORT:\n## Recovery\nOk."
        notif, _ = self._parse(text)
        assert len(notif) <= 240

    def test_adjustment_case_insensitive_as_planned(self):
        """'AS PLANNED' (uppercase) also suppresses the Adjustment header."""
        text = "NOTIFICATION:\nOk.\nADJUSTMENT:\nAS PLANNED\nFULL_REPORT:\n## Recovery\nGood."
        _, report = self._parse(text)
        assert "## Adjustment" not in report


class TestHasTodaysReadinessData:
    """has_todays_readiness_data blocks until all recovery metrics have today's date."""

    TODAY = date.today().isoformat()
    YESTERDAY = (date.today() - timedelta(days=1)).isoformat()

    def _call(self, cache):
        from morning_report import has_todays_readiness_data
        with patch("morning_report.load_health_data", return_value=cache):
            return has_todays_readiness_data()

    def _full_cache(self, sleep_date=None, hrv_date=None, bb_date=None, readiness_date=None):
        """Build a cache where every metric has today's date by default."""
        t = self.TODAY
        return {
            "sleep_sessions":     [{"date": sleep_date or t, "total_duration_minutes": 420}],
            "hrv_readings":       [{"date": hrv_date or t, "last_night_avg": 45, "status": "balanced"}],
            "body_battery":       [{"date": bb_date or t, "latest_level": 72}],
            "training_readiness": [{"date": readiness_date or t, "score": 65, "level": "good"}],
        }

    def test_returns_true_when_all_metrics_are_today(self):
        assert self._call(self._full_cache()) is True

    def test_returns_false_when_no_sleep(self):
        cache = self._full_cache()
        cache["sleep_sessions"] = []
        assert self._call(cache) is False

    def test_returns_false_when_sleep_is_yesterday(self):
        assert self._call(self._full_cache(sleep_date=self.YESTERDAY)) is False

    def test_returns_false_when_hrv_is_yesterday(self):
        assert self._call(self._full_cache(hrv_date=self.YESTERDAY)) is False

    def test_returns_false_when_body_battery_is_yesterday(self):
        assert self._call(self._full_cache(bb_date=self.YESTERDAY)) is False

    def test_returns_false_when_readiness_is_yesterday(self):
        assert self._call(self._full_cache(readiness_date=self.YESTERDAY)) is False

    def test_missing_metric_does_not_block(self):
        """If a metric has never been in the cache (empty list), don't block on it."""
        cache = self._full_cache()
        cache["hrv_readings"] = []  # device doesn't provide HRV
        assert self._call(cache) is True

    def test_returns_false_on_load_error(self):
        from morning_report import has_todays_readiness_data
        with patch("morning_report.load_health_data", side_effect=Exception("disk error")):
            assert has_todays_readiness_data() is False
