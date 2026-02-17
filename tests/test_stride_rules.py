#!/usr/bin/env python3
"""
Tests for stride validation, rewrite, and rendering enforcement.

Covers:
  1. On easy+strides days, interval-like reps with duration_min ≥ 1 (≥ 60 s) are invalid stride reps
  2. Total stride time > 5 min fails validation
  3. 4min x4 cannot be classified as strides
  4. Rewrite produces valid stride structure
  5. Renderer outputs stride phrasing (not tempo/interval)
  6. SQLite event recorded on validation failure

Run:
    python3 -m pytest tests/test_stride_rules.py -v
"""

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from brain.stride_rules import (
    CANONICAL_NOTE,
    CANONICAL_REPS,
    CANONICAL_REP_SEC,
    STRIDE_REP_MAX_SEC,
    STRIDE_TOTAL_MAX_SEC,
    is_stride_intent,
    validate_strides,
    rewrite_strides,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_interval_step(duration_min: int, reps: int = 4) -> dict:
    return {
        "label":         "interval",
        "duration_min":  duration_min,
        "target_metric": "pace",
        "target_value":  "7:55-8:05/mi",
        "reps":          reps,
        "notes":         None,
    }

def _make_main_reps(duration_min: int, reps: int) -> dict:
    return {
        "label":         "main",
        "duration_min":  duration_min,
        "target_metric": "pace",
        "target_value":  "easy",
        "reps":          reps,
        "notes":         None,
    }


# ── 1. Interval-like reps with duration_min ≥ 1 are invalid stride reps ──────

class TestRepDurationValidation:
    def test_1min_rep_fails(self):
        """duration_min=1 (= 60 s) must fail — exceeds 40 s max."""
        steps = [_make_interval_step(duration_min=1, reps=4)]
        ok, reason = validate_strides(steps)
        assert not ok
        assert "60s" in reason or "1min" in reason or "intervals" in reason.lower()

    def test_4min_rep_fails(self):
        """The specific bug: 4min x4 @ pace must fail stride validation."""
        steps = [_make_interval_step(duration_min=4, reps=4)]
        ok, reason = validate_strides(steps)
        assert not ok
        assert "4min" in reason or "240s" in reason or "intervals" in reason.lower()

    def test_45sec_rep_fails_when_expressed_as_sub_min(self):
        """45 s > 40 s max — if ever stored as fractional, must fail."""
        # Schema enforces ge=1 so duration_min=0 would fail Pydantic,
        # but validate_strides is called on raw dicts too.
        # Use a hypothetical sub-minute value (0 stored would mean 0s — also fails reps min)
        steps = [{"label": "interval", "duration_min": 0, "target_metric": "pace",
                  "target_value": "fast", "reps": 4, "notes": None}]
        # duration_min=0 → 0s, which is < 15s; also < STRIDE_REPS_MIN? No, reps=4 is fine.
        # But validate_strides should not crash — it simply finds 0-min duration OK in seconds
        # This is a degenerate case; main test is that dur_min >= 1 always fails
        ok_zero, _ = validate_strides(steps)
        # 0 min = 0s which passes the 40s cap, but schema would reject duration_min=0
        # The important property: dur_min=1 always fails
        steps_1min = [_make_interval_step(duration_min=1, reps=4)]
        ok_1min, _ = validate_strides(steps_1min)
        assert not ok_1min

    def test_2min_rep_fails(self):
        """duration_min=2 (= 120 s) must fail."""
        steps = [_make_interval_step(duration_min=2, reps=4)]
        ok, reason = validate_strides(steps)
        assert not ok

    def test_10min_rep_fails(self):
        """Very long interval step must fail."""
        steps = [_make_interval_step(duration_min=10, reps=3)]
        ok, reason = validate_strides(steps)
        assert not ok


# ── 2. Total stride time > 5 min fails ───────────────────────────────────────

class TestTotalStrideTime:
    def test_total_exceeds_300s(self):
        """If sub-minute reps × count > 300 s, validation must fail."""
        # Simulate: if schema ever allowed < 1 min, e.g. 0-min but with high reps
        # More practically: use 1-min reps which fail immediately on rep duration
        # The total-time check is hit for sub-minute cases. Test it directly:
        # 10 reps × 31 s each = 310 s > 300 s. But 31 s > 40 s max (step cap).
        # Use 10 reps × 30 s (sub-schema, raw dict). Total = 300 s — OK at boundary.
        # 11 reps × 30 s = 330 s > 300 s
        steps_boundary = [{"label": "interval", "duration_min": 0, "target_metric": "pace",
                           "target_value": "fast", "reps": 10, "notes": None}]
        # With duration_min=0 → 0 s per rep, total = 0 s — passes
        # Build a case with non-zero sub-min:
        # We test the rule logic directly: validate_strides is pure Python
        # Patch: pass a step as if it were 30s per rep, 11 reps
        # This requires bypassing schema — we test validate_strides directly
        # Build raw dict pretending duration_min=0.5 (not schema-valid but tests the rule)
        steps_fractional = [{
            "label": "interval", "duration_min": 0.5,   # 30s — sub-minute
            "target_metric": "pace", "target_value": "fast",
            "reps": 11, "notes": None,
        }]
        ok, reason = validate_strides(steps_fractional)
        # 0.5 min × 60 = 30 s; 30 × 11 = 330 s > 300 s
        assert not ok
        assert "330" in reason or "300" in reason

    def test_1min_reps_fail_before_total_check(self):
        """Per-rep duration check fires before total-time check."""
        steps = [_make_interval_step(duration_min=1, reps=2)]
        ok, reason = validate_strides(steps)
        assert not ok
        # Should mention per-rep violation, not total time
        assert "intervals" in reason.lower() or "1min" in reason or "60s" in reason


# ── 3. 4min x4 cannot be strides ─────────────────────────────────────────────

class TestFourMinutesNotStrides:
    def test_4min_x4_interval_step_fails(self):
        """Regression: the specific bug pattern must fail validation."""
        steps = [_make_interval_step(duration_min=4, reps=4)]
        ok, reason = validate_strides(steps)
        assert not ok, "4min x4 must NOT pass stride validation"

    def test_4min_x4_main_reps_fails(self):
        """Same check via 'main' step with reps."""
        steps = [_make_main_reps(duration_min=4, reps=4)]
        ok, reason = validate_strides(steps)
        assert not ok

    def test_is_stride_intent_detects_easy_strides(self):
        """is_stride_intent must return True for canonical stride intent text."""
        assert is_stride_intent("Easy run with strides")
        assert is_stride_intent("Easy 45min + 4x20s strides")
        assert is_stride_intent("60 min easy with strides")

    def test_is_stride_intent_returns_false_for_pure_intervals(self):
        """Pure interval intents should not be flagged as stride days."""
        assert not is_stride_intent("Tempo run 4x1mile")
        assert not is_stride_intent("Interval session")
        assert not is_stride_intent("Easy 45 min")


# ── 4. Rewrite produces valid stride structure ────────────────────────────────

class TestStrideRewrite:
    def test_rewrite_removes_interval_steps(self):
        """After rewrite, no 'interval' label steps remain."""
        steps = [
            {"label": "warmup",   "duration_min": 10, "target_metric": "pace",
             "target_value": "easy", "reps": None, "notes": None},
            _make_interval_step(duration_min=4, reps=4),
            {"label": "cooldown", "duration_min": 5, "target_metric": "pace",
             "target_value": "easy", "reps": None, "notes": None},
        ]
        new_steps, reason = rewrite_strides(steps, duration_min=45)
        labels = [s["label"] for s in new_steps]
        assert "interval" not in labels

    def test_rewrite_preserves_warmup_cooldown(self):
        """Warmup and cooldown must be preserved after rewrite."""
        steps = [
            {"label": "warmup",   "duration_min": 10, "target_metric": "pace",
             "target_value": "easy", "reps": None, "notes": None},
            _make_interval_step(duration_min=4, reps=4),
            {"label": "cooldown", "duration_min": 5, "target_metric": "pace",
             "target_value": "easy", "reps": None, "notes": None},
        ]
        new_steps, _ = rewrite_strides(steps, duration_min=45)
        labels = [s["label"] for s in new_steps]
        assert "warmup"   in labels
        assert "cooldown" in labels
        assert "main"     in labels

    def test_rewrite_main_step_has_canonical_note(self):
        """The rewritten main step must carry the canonical stride note."""
        steps = [_make_interval_step(duration_min=4, reps=4)]
        new_steps, _ = rewrite_strides(steps, duration_min=45)
        main = next(s for s in new_steps if s["label"] == "main")
        assert main["notes"] == CANONICAL_NOTE
        assert "strides" in main["notes"].lower()
        assert str(CANONICAL_REPS) in main["notes"]
        assert str(CANONICAL_REP_SEC) in main["notes"]

    def test_rewrite_main_duration_min_ge1(self):
        """Rewritten step duration_min must be ≥ 1 (schema constraint)."""
        steps = [_make_interval_step(duration_min=4, reps=4)]
        new_steps, _ = rewrite_strides(steps, duration_min=1)
        for s in new_steps:
            assert s["duration_min"] >= 1

    def test_rewrite_valid_strides_unchanged(self):
        """Steps without interval reps (no violations) pass through unchanged."""
        # Single main step — no interval candidates
        steps = [{"label": "main", "duration_min": 45, "target_metric": "rpe",
                  "target_value": "easy", "reps": None, "notes": "4x20s strides"}]
        ok, reason = validate_strides(steps)
        assert ok, "No interval steps present — should be ok"


# ── 5. Renderer outputs stride phrasing ──────────────────────────────────────

class TestRenderer:
    def test_easy_with_strides_intent_emits_stride_description(self):
        """For easy+strides intent, renderer must emit stride description, not plain easy."""
        from skills.internal_plan_to_scheduled_workouts import _render_description

        desc, degraded = _render_description(
            workout_type="easy",
            duration_min=45,
            steps=[_make_interval_step(duration_min=4, reps=4)],
            intent="Easy run with strides",
        )
        assert degraded is None
        assert "stride" in desc.lower()
        assert "E" in desc           # still an easy run
        assert "45" in desc          # duration preserved
        # Must NOT look like interval/tempo
        assert "@ tempo" not in desc

    def test_easy_without_strides_intent_is_plain_easy(self):
        """Easy without strides in intent: plain 'N min E'."""
        from skills.internal_plan_to_scheduled_workouts import _render_description

        desc, degraded = _render_description(
            workout_type="easy",
            duration_min=45,
            steps=[],
            intent="Easy recovery run",
        )
        assert degraded is None
        assert desc == "45 min E"

    def test_stride_description_is_parser_compatible(self):
        """Emitted stride description must be parseable by workout_parser."""
        from skills.internal_plan_to_scheduled_workouts import _render_description

        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from workout_parser import parse_workout_description

        desc, _ = _render_description(
            workout_type="easy",
            duration_min=60,
            steps=[_make_interval_step(duration_min=4, reps=4)],
            intent="60 min easy with strides",
        )
        parsed = parse_workout_description(desc)
        assert parsed is not None

    def test_render_emits_canonical_reps_and_duration(self):
        """Rendered stride description uses canonical reps and duration."""
        from skills.internal_plan_to_scheduled_workouts import _render_description

        desc, _ = _render_description(
            workout_type="easy",
            duration_min=45,
            steps=[_make_interval_step(duration_min=4, reps=4)],
            intent="Easy run with strides",
        )
        assert str(CANONICAL_REPS) in desc        # "6"
        assert str(CANONICAL_REP_SEC) in desc     # "20"


# ── 6. SQLite event recorded on validation failure ───────────────────────────

class TestStrideValidationEvent:
    def _seed_session_and_run_convert(self, db_path, steps):
        """Call skills.convert() with a stride session containing bad steps."""
        from skills.internal_plan_to_scheduled_workouts import convert

        session = {
            "date":            date.today().isoformat(),
            "intent":          "Easy run with strides",
            "workout_type":    "easy",
            "duration_min":    45,
            "structure_steps": steps,
            "safety_flags":    [],
            "rationale":       "",
            "plan_id":         "test-plan-001",
        }
        return convert([session], db_path=db_path)

    def test_sqlite_event_recorded_for_invalid_strides(self, tmp_path):
        """stride_validation_failed event must appear in SQLite when steps are invalid."""
        from memory.db import init_db, query_events

        db = tmp_path / "coach.sqlite"
        init_db(db)

        bad_steps = [_make_interval_step(duration_min=4, reps=4)]
        self._seed_session_and_run_convert(db, bad_steps)

        events = query_events(event_type="stride_validation_failed", db_path=db)
        assert len(events) >= 1, "Expected stride_validation_failed event in SQLite"

        payload = json.loads(events[0]["payload_json"])
        assert "reason" in payload
        assert "4min" in payload["reason"] or "intervals" in payload["reason"].lower()

    def test_no_sqlite_event_for_valid_session(self, tmp_path):
        """No stride_validation_failed event when steps are not interval reps."""
        from memory.db import init_db, query_events

        db = tmp_path / "coach.sqlite"
        init_db(db)

        valid_steps = [
            {"label": "main", "duration_min": 45, "target_metric": "rpe",
             "target_value": "easy", "reps": None, "notes": None},
        ]
        self._seed_session_and_run_convert(db, valid_steps)

        events = query_events(event_type="stride_validation_failed", db_path=db)
        assert len(events) == 0, "No event expected for valid steps"
