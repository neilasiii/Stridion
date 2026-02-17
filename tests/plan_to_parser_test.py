#!/usr/bin/env python3
"""
Parser compatibility tests for skills/internal_plan_to_scheduled_workouts.py.

Verifies that every description string produced by the skills converter is
accepted by src/workout_parser.parse_workout_description and returns a
non-empty ParsedWorkout.  Also verifies the fallback / render_degraded path.

Run:
    python3 -m pytest tests/test_plan_to_parser.py -v
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from skills.internal_plan_to_scheduled_workouts import (
    _render_description,
    convert,
)
from workout_parser import parse_workout_description


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_session(
    workout_type: str,
    duration_min: int,
    steps: List[Dict[str, Any]],
    date: str = "2026-02-20",
    intent: str = "Test session",
) -> Dict[str, Any]:
    return {
        "date":            date,
        "intent":          intent,
        "workout_type":    workout_type,
        "duration_min":    duration_min,
        "structure_steps": steps,
        "safety_flags":    [],
        "rationale":       "",
        "plan_id":         "test-plan",
    }


_EASY_STEPS = [
    {"label": "warmup",   "duration_min": 5,  "target_metric": "rpe", "target_value": "RPE 4"},
    {"label": "main",     "duration_min": 40, "target_metric": "rpe", "target_value": "RPE 5"},
    {"label": "cooldown", "duration_min": 5,  "target_metric": "rpe", "target_value": "RPE 4"},
]

_TEMPO_STEPS = [
    {"label": "warmup",   "duration_min": 20, "target_metric": "pace", "target_value": "10:30-11:10/mi"},
    {"label": "main",     "duration_min": 25, "target_metric": "pace", "target_value": "8:30-8:50/mi"},
    {"label": "cooldown", "duration_min": 15, "target_metric": "rpe",  "target_value": "RPE 4"},
]

_INTERVAL_STEPS = [
    {"label": "warmup",   "duration_min": 20, "target_metric": "rpe",  "target_value": "RPE 4"},
    {"label": "interval", "duration_min": 5,  "reps": 6,
     "target_metric": "pace", "target_value": "7:55-8:05/mi"},
    {"label": "recovery", "duration_min": 1,  "target_metric": "rpe",  "target_value": "RPE 3"},
    {"label": "cooldown", "duration_min": 15, "target_metric": "rpe",  "target_value": "RPE 4"},
]

_LONG_STEPS = [
    {"label": "warmup",   "duration_min": 10, "target_metric": "rpe", "target_value": "RPE 4"},
    {"label": "main",     "duration_min": 90, "target_metric": "rpe", "target_value": "RPE 5"},
    {"label": "cooldown", "duration_min": 10, "target_metric": "rpe", "target_value": "RPE 4"},
]


# ── Render + parse roundtrip ──────────────────────────────────────────────────

class TestRenderToParser:
    """Each test renders a description then confirms parse_workout_description
    accepts it and returns a non-trivial ParsedWorkout."""

    def _roundtrip(self, workout_type, duration_min, steps):
        desc, reason = _render_description(workout_type, duration_min, steps)
        assert reason is None, f"Unexpected degradation for {workout_type}: {reason}"
        parsed = parse_workout_description(desc)
        assert parsed is not None, f"parse returned None for {desc!r}"
        assert parsed.workout_type is not None, f"workout_type missing for {desc!r}"
        return desc, parsed

    def test_easy_renders_and_parses(self):
        desc, parsed = self._roundtrip("easy", 45, _EASY_STEPS)
        assert desc == "45 min E"
        assert parsed.workout_type == "easy"

    def test_easy_no_steps_still_parses(self):
        """Easy runs don't need structure_steps — description is always 'N min E'."""
        desc, parsed = self._roundtrip("easy", 30, [])
        assert desc == "30 min E"

    def test_long_renders_as_easy_pace(self):
        desc, parsed = self._roundtrip("long", 90, _LONG_STEPS)
        assert desc == "90 min E"
        assert parsed.workout_type == "easy"

    def test_tempo_with_warmup_cooldown(self):
        desc, parsed = self._roundtrip("tempo", 60, _TEMPO_STEPS)
        assert "warm up" in desc
        assert "@ tempo" in desc
        assert "warm down" in desc
        # parser should recognise the tempo segment
        assert parsed.workout_type in ("tempo", "easy"), (
            f"Expected tempo or easy, got {parsed.workout_type!r} for {desc!r}"
        )

    def test_tempo_no_warmup_cooldown(self):
        """Tempo with only a main step — no warmup/cooldown sections."""
        steps = [{"label": "main", "duration_min": 30, "target_metric": "pace", "target_value": "tempo"}]
        desc, parsed = self._roundtrip("tempo", 30, steps)
        assert "@ tempo" in desc
        assert parsed is not None

    def test_interval_with_reps(self):
        desc, parsed = self._roundtrip("interval", 62, _INTERVAL_STEPS)
        assert "6x5 min @ tempo on 1 min recovery" in desc
        assert parsed is not None

    def test_interval_no_reps_falls_back_to_tempo_format(self):
        """Intervals without reps render like a tempo run."""
        steps = [
            {"label": "warmup",   "duration_min": 15, "target_metric": "rpe", "target_value": "RPE 4"},
            {"label": "interval", "duration_min": 20, "target_metric": "pace", "target_value": "tempo"},
            {"label": "cooldown", "duration_min": 10, "target_metric": "rpe", "target_value": "RPE 4"},
        ]
        desc, reason = _render_description("interval", 45, steps)
        # reps is None/missing → falls through to plain tempo format
        assert "@ tempo" in desc
        parsed = parse_workout_description(desc)
        assert parsed is not None


# ── Degradation path ──────────────────────────────────────────────────────────

class TestDegradation:

    def test_tempo_no_steps_degrades(self):
        desc, reason = _render_description("tempo", 40, [])
        assert reason is not None, "Expected degradation reason"
        assert desc == "40 min E", f"Expected easy fallback, got {desc!r}"
        # Degraded description must also parse cleanly
        parsed = parse_workout_description(desc)
        assert parsed is not None

    def test_interval_no_steps_degrades(self):
        desc, reason = _render_description("interval", 55, [])
        assert reason is not None
        assert desc == "55 min E"

    def test_degraded_event_recorded_in_sqlite(self, tmp_path):
        """When convert() degrades a workout, it records a render_degraded event."""
        from memory.db import init_db, query_events

        db = tmp_path / "test.sqlite"
        init_db(db)

        sessions = [_make_session("tempo", 40, [])]  # no steps → degrades
        result = convert(sessions, db_path=db)

        assert len(result) == 1, "Degraded workout should still be included"
        assert result[0]["_degraded"] is True

        events = query_events(event_type="render_degraded", db_path=db)
        assert len(events) == 1, "Expected exactly one render_degraded event"
        payload = json.loads(events[0]["payload_json"])
        assert payload["original_workout_type"] == "tempo"
        assert payload["rendered_description"] == "40 min E"

    def test_non_running_sessions_excluded(self):
        """strength / rest / cross sessions are skipped entirely."""
        sessions = [
            _make_session("strength", 45, []),
            _make_session("rest",     0,  []),
            _make_session("cross",    30, []),
        ]
        result = convert(sessions)
        assert result == [], f"Expected empty list, got {result}"


# ── convert() end-to-end ──────────────────────────────────────────────────────

class TestConvert:

    def test_mixed_week_produces_running_only(self):
        sessions = [
            _make_session("easy",     45, _EASY_STEPS,     date="2026-02-17"),
            _make_session("rest",     0,  [],               date="2026-02-18"),
            _make_session("tempo",    60, _TEMPO_STEPS,     date="2026-02-19"),
            _make_session("strength", 40, [],               date="2026-02-20"),
            _make_session("long",     90, _LONG_STEPS,      date="2026-02-22"),
        ]
        result = convert(sessions)
        dates = [w["scheduled_date"] for w in result]
        assert dates == ["2026-02-17", "2026-02-19", "2026-02-22"]
        # All sources tagged correctly
        assert all(w["source"] == "internal_plan" for w in result)

    def test_all_names_parseable(self):
        """Every converted 'name' field must be accepted by parse_workout_description."""
        sessions = [
            _make_session("easy",     45, _EASY_STEPS),
            _make_session("long",     90, _LONG_STEPS),
            _make_session("tempo",    60, _TEMPO_STEPS),
            _make_session("interval", 62, _INTERVAL_STEPS),
        ]
        result = convert(sessions)
        for wo in result:
            parsed = parse_workout_description(wo["name"])
            assert parsed is not None, f"parse failed for {wo['name']!r}"
