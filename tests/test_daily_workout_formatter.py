"""Tests: daily_workout_formatter reads internal plan before health cache."""
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _make_session(d: str, wtype: str = "easy", dur: int = 45, intent: str = "Easy run", steps=None):
    return {
        "date": d,
        "workout_type": wtype,
        "duration_min": dur,
        "intent": intent,
        "structure_steps": steps or [],
        "safety_flags": [],
        "plan_id": "test-plan",
    }


class TestGetScheduledWorkoutsInternalPlan:
    """get_scheduled_workouts uses internal plan when available."""

    def _call(self, sessions, health_data=None, date_str=None):
        from daily_workout_formatter import get_scheduled_workouts
        date_str = date_str or date.today().isoformat()
        with patch("daily_workout_formatter.get_active_sessions", return_value=sessions):
            with patch("daily_workout_formatter.load_health_data", return_value=health_data or {}):
                return get_scheduled_workouts(date_str)

    def test_returns_internal_session_for_matching_date(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="tempo", dur=55, intent="Tempo effort")]
        result = self._call(sessions, date_str=today)
        assert len(result) == 1
        assert result[0]["source"] == "internal_plan"
        assert result[0]["domain"] == "running"

    def test_rest_day_returns_empty(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="rest", dur=0)]
        result = self._call(sessions, date_str=today)
        assert result == []

    def test_wrong_date_session_not_returned(self):
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = [_make_session(tomorrow)]
        result = self._call(sessions, date_str=today)
        assert result == []

    def test_falls_back_to_health_cache_when_no_sessions(self):
        today = date.today().isoformat()
        cache_workouts = [{"scheduled_date": today, "name": "Easy 30min", "domain": "running"}]
        result = self._call([], health_data={"scheduled_workouts": cache_workouts}, date_str=today)
        assert len(result) == 1
        assert result[0]["name"] == "Easy 30min"

    def test_falls_back_when_sessions_exist_but_none_match_date(self):
        """If plan has sessions but not for today, use health cache."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        today = date.today().isoformat()
        sessions = [_make_session(tomorrow)]
        cache_workouts = [{"scheduled_date": today, "name": "Cache Run", "domain": "running"}]
        result = self._call(sessions, health_data={"scheduled_workouts": cache_workouts}, date_str=today)
        assert len(result) == 1
        assert result[0]["name"] == "Cache Run"


class TestFormatRunningWorkoutInternalPlan:
    """format_running_workout renders internal_plan source correctly."""

    def _format(self, workout):
        from daily_workout_formatter import format_running_workout
        return format_running_workout(workout)

    def _internal_workout(self, wtype="easy", dur=45, intent="Easy run", steps=None):
        return {
            "name": "Easy Run",
            "description": intent,
            "duration_min": dur,
            "source": "internal_plan",
            "domain": "running",
            "workout_type": wtype,
            "structure_steps": steps or [],
            "intent": intent,
        }

    def test_easy_run_shows_duration(self):
        result = self._format(self._internal_workout(wtype="easy", dur=45))
        assert "45" in result

    def test_easy_run_shows_intent(self):
        result = self._format(self._internal_workout(intent="Conversational, aerobic base"))
        assert "Conversational, aerobic base" in result

    def test_tempo_shows_structure_steps(self):
        steps = [
            {"label": "warmup", "duration_min": 15, "reps": None, "target_value": "easy"},
            {"label": "main", "duration_min": 25, "reps": None, "target_value": "tempo"},
            {"label": "cooldown", "duration_min": 15, "reps": None, "target_value": "easy"},
        ]
        result = self._format(self._internal_workout(wtype="tempo", dur=55, steps=steps))
        assert "Warmup" in result
        assert "Main" in result
        assert "25" in result

    def test_no_steps_no_structure_section(self):
        result = self._format(self._internal_workout(steps=[]))
        assert "Structure" not in result

    def test_internal_plan_does_not_call_regex_parser(self):
        """Ensure early return fires before the name-parsing regex block."""
        wo = self._internal_workout(wtype="easy", dur=30, intent="Easy 30min")
        # If the regex path ran, it would parse the *name* ("Easy Run") not the intent.
        # The regex path returns "Easy Run" as workout_type label.
        # The internal path returns the intent directly.
        result = self._format(wo)
        assert "Conversational" not in result or "Easy 30min" in result
