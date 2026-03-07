"""
Hardening batch 2 — tests for three surgical additions:

  1. Macro volume ceiling auto-clamp (brain/planner.py)
     - Over-cap plan is clamped to macro_target + both flags set
     - Within-tolerance plan is NOT clamped
     - No macro_guidance → no clamping

  2. Short-race recovery detection + validation (brain/macro_plan.py)
     - 5k race by keyword → short_race_mode=True, no_quality_days=4
     - Half-marathon by distance → long mode (existing behavior)
     - validate_macro_plan: short_race Week 1 quality > 0 → error
     - validate_macro_plan: short_race does NOT enforce volume cap
     - End-to-end: short-race context → generate_macro_plan enforces W1 quality=0
     - Half/marathon detection unchanged

  3. Current week highlight in _print_macro_plan (cli/coach.py)
     - Row for current week gets "→" marker
     - Row outside current week gets " " marker
     - today outside entire block → no marker on any row
"""
from __future__ import annotations

import io
import json
from datetime import date, timedelta
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# 1. Auto-clamp
# ══════════════════════════════════════════════════════════════════════════════

def _next_sunday() -> str:
    today = date.today()
    days = (6 - today.weekday()) % 7
    return (today + timedelta(days=days)).isoformat()


def _make_plan_day(day_date: str, workout_type: str = "easy", duration: int = 45) -> dict:
    return {
        "date": day_date,
        "intent": "Easy run",
        "workout_type": workout_type,
        "duration_min": duration,
        "structure_steps": [{"label": "main", "duration_min": duration,
                              "target_metric": "pace", "target_value": "10:30/mi"}],
        "safety_flags": [],
        "rationale": "Aerobic base.",
    }


def _make_week_json(ws: str, volume: float, phase: str = "base", hash_: str = "h001") -> str:
    ws_d = date.fromisoformat(ws)
    we_d = ws_d + timedelta(days=6)
    days = [_make_plan_day((ws_d + timedelta(days=i)).isoformat()) for i in range(7)]
    return json.dumps({
        "week_start": ws,
        "week_end": we_d.isoformat(),
        "phase": phase,
        "days": days,
        "weekly_volume_miles": volume,
        "safety_flags": [],
        "rationale": "Base training week.",
        "context_hash": hash_,
    })


def _macro_guidance(target_vol: float, ws: str) -> dict:
    return {
        "macro_id": "test-macro",
        "mode": "base_block",
        "current_week": {
            "week_number": 2,
            "week_start": ws,
            "phase": "base",
            "target_volume_miles": target_vol,
            "long_run_max_min": 80,
            "intensity_budget": "low",
            "quality_sessions_allowed": 0,
            "key_workout_type": "long",
            "paces": {"easy": "10:30-11:10/mi", "long_run": "11:10-11:50/mi"},
            "planner_notes": "Build aerobically.",
            "phase_rationale": "Base phase.",
        },
    }


def _context_packet(macro_guidance: Optional[dict] = None) -> dict:
    return {
        "athlete": {"vo2_max": 50.0, "rhr_latest": 50},
        "training_summary": {"total_miles": 28.0, "period_days": 14, "recent_runs": []},
        "upcoming_races": [],
        "data_quality": {"has_health_cache": True, "readiness_confidence": "ok"},
        **({"macro_guidance": macro_guidance} if macro_guidance is not None else {}),
    }


class TestAutoClamp:
    def test_over_cap_volume_is_clamped(self, tmp_path):
        """LLM returns 26 mi, macro target = 20 → clamped to 20."""
        from brain.planner import plan_week

        ws = _next_sunday()
        mock_json = _make_week_json(ws, volume=26.0)
        mg = _macro_guidance(target_vol=20.0, ws=ws)
        packet = _context_packet(macro_guidance=mg)

        db = tmp_path / "coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db,
                                 week_start=date.fromisoformat(ws))

        assert decision.weekly_volume_miles == 20.0, (
            f"Expected clamp to 20.0, got {decision.weekly_volume_miles}"
        )
        assert "macro_cap_exceeded" in decision.safety_flags
        assert "macro_cap_clamped" in decision.safety_flags

    def test_within_tolerance_not_clamped(self, tmp_path):
        """LLM returns 20.3 mi, target = 20 → within 0.5 tolerance, NOT clamped."""
        from brain.planner import plan_week

        ws = _next_sunday()
        mock_json = _make_week_json(ws, volume=20.3)
        mg = _macro_guidance(target_vol=20.0, ws=ws)
        packet = _context_packet(macro_guidance=mg)

        db = tmp_path / "coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db,
                                 week_start=date.fromisoformat(ws))

        assert decision.weekly_volume_miles == pytest.approx(20.3, abs=0.05)
        assert "macro_cap_clamped" not in decision.safety_flags
        assert "macro_cap_exceeded" not in decision.safety_flags

    def test_no_macro_guidance_no_clamp(self, tmp_path):
        """Without macro_guidance, no clamping occurs regardless of volume."""
        from brain.planner import plan_week

        ws = _next_sunday()
        mock_json = _make_week_json(ws, volume=35.0)  # high but no guidance cap
        packet = _context_packet(macro_guidance=None)

        db = tmp_path / "coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db,
                                 week_start=date.fromisoformat(ws))

        assert decision.weekly_volume_miles == pytest.approx(35.0, abs=0.1)
        assert "macro_cap_clamped" not in decision.safety_flags
        assert "macro_cap_exceeded" not in decision.safety_flags

    def test_exactly_at_cap_not_clamped(self, tmp_path):
        """LLM returns exactly the macro target → no clamping (within tolerance)."""
        from brain.planner import plan_week

        ws = _next_sunday()
        mock_json = _make_week_json(ws, volume=20.0)
        mg = _macro_guidance(target_vol=20.0, ws=ws)
        packet = _context_packet(macro_guidance=mg)

        db = tmp_path / "coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db,
                                 week_start=date.fromisoformat(ws))

        assert "macro_cap_clamped" not in decision.safety_flags


# ══════════════════════════════════════════════════════════════════════════════
# 2. Short-race recovery
# ══════════════════════════════════════════════════════════════════════════════

def _make_macro_week_dict(
    n: int, ws: str,
    phase: str = "base", volume: float = 20.0, lr: int = 70,
    intensity: str = "low", quality: int = 0,
) -> dict:
    return {
        "week_number": n, "week_start": ws, "phase": phase,
        "target_volume_miles": volume, "long_run_max_min": lr,
        "intensity_budget": intensity, "quality_sessions_allowed": quality,
        "key_workout_type": "long",
        "paces": {"easy": "10:30-11:10/mi", "tempo": None,
                  "interval": None, "long_run": "11:10-11:50/mi"},
        "planner_notes": "Aerobic base.", "phase_rationale": "Build base.",
    }


def _sundays(n: int, start: str) -> List[str]:
    base = date.fromisoformat(start)
    return [(base + timedelta(days=7 * i)).isoformat() for i in range(n)]


def _make_base_plan(n_weeks: int = 4, start: Optional[str] = None,
                    w1_quality: int = 0) -> dict:
    """Build a minimal valid base_block plan."""
    s = start or _next_sunday()
    suns = _sundays(n_weeks, s)
    weeks = [_make_macro_week_dict(i + 1, suns[i], volume=20.0 + i) for i in range(n_weeks)]
    weeks[0]["quality_sessions_allowed"] = w1_quality
    # Keep last week from hitting end-of-block stress check
    weeks[-1]["intensity_budget"] = "low"
    weeks[-1]["quality_sessions_allowed"] = 0
    return {
        "mode": "base_block", "race_date": None, "race_name": None,
        "race_distance": None, "vdot": 50.6,
        "start_week": s, "total_weeks": n_weeks,
        "peak_weekly_miles": max(w["target_volume_miles"] for w in weeks),
        "rationale": "Base block, starting at 20 mi/wk.",
        "weeks": weeks,
    }


class TestShortRaceDetection:
    def _packet(self, runs):
        total_mi = sum(r.get("distance_mi", 0) for r in runs)
        return {
            "training_summary": {
                "recent_runs": runs,
                "total_miles": total_mi * 2,
                "period_days": 14,
            }
        }

    def test_keyword_5k_race_triggers_short_mode(self):
        """Run named '5k race' with dist < 10 → short_race_mode=True."""
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today().isoformat()
        runs = [{"date": today, "distance_mi": 3.1, "name": "5k race at local park"}]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is True
        assert result["short_race_mode"] is True
        assert result["no_quality_days"] == 4
        assert result["recovery_weeks"] == 0  # no full week cap

    def test_keyword_10k_triggers_short_mode(self):
        """Run named '10k' → short_race_mode=True."""
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today().isoformat()
        runs = [{"date": today, "distance_mi": 6.2, "name": "City 10k"}]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is True
        assert result["short_race_mode"] is True
        assert result["no_quality_days"] == 4

    def test_keyword_race_no_distance_triggers_short_mode(self):
        """Run named 'race' with dist=0 (keyword-only) → short_race_mode=True."""
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today().isoformat()
        runs = [{"date": today, "distance_mi": 0.0, "name": "Neighborhood race"}]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is True
        assert result["short_race_mode"] is True

    def test_long_race_beats_short_race_keyword(self):
        """When both a short keyword-race and a long race (>= 10 mi) exist,
        long race takes priority."""
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        runs = [
            {"date": today,     "distance_mi": 3.1,  "name": "5k race"},  # short
            {"date": yesterday, "distance_mi": 13.25, "name": "Half marathon"},  # long
        ]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is True
        assert result["short_race_mode"] is False  # long race wins
        assert result["recovery_weeks"] == 1
        assert result["no_quality_days"] == 0

    def test_half_marathon_distance_is_long_mode(self):
        """13.25 mi (no name) → long mode, 1 recovery week."""
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today().isoformat()
        runs = [{"date": today, "distance_mi": 13.25}]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is True
        assert result["short_race_mode"] is False
        assert result["recovery_weeks"] == 1

    def test_marathon_distance_is_long_mode_two_weeks(self):
        """26.2 mi → long mode, 2 recovery weeks."""
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today().isoformat()
        runs = [{"date": today, "distance_mi": 26.2}]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is True
        assert result["short_race_mode"] is False
        assert result["recovery_weeks"] == 2

    def test_no_recent_runs_returns_not_required(self):
        """No runs within 7 days → required=False."""
        from brain.macro_plan import _detect_post_race_recovery

        old_date = (date.today() - timedelta(days=10)).isoformat()
        runs = [{"date": old_date, "distance_mi": 3.1, "name": "5k race"}]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is False
        assert result["short_race_mode"] is False

    def test_no_keyword_easy_run_no_trigger(self):
        """Easy 4-mile run without race keyword → not required."""
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today().isoformat()
        runs = [{"date": today, "distance_mi": 4.0, "name": "Easy morning run"}]
        result = _detect_post_race_recovery(self._packet(runs))

        assert result["required"] is False


class TestShortRaceValidation:
    def test_week1_quality_fails_when_short_race(self):
        """short_race_no_quality_days > 0 + Week 1 quality=2 → error."""
        from brain.schemas import MacroPlan
        from brain.macro_plan import validate_macro_plan

        plan_dict = _make_base_plan(n_weeks=4, w1_quality=2)
        plan = MacroPlan.model_validate(plan_dict)
        result = validate_macro_plan(plan, short_race_no_quality_days=4)

        assert not result.ok
        assert any("short-race" in e.lower() or "no-quality" in e.lower()
                   for e in result.errors)

    def test_week1_quality_zero_passes_with_short_race(self):
        """short_race_no_quality_days > 0 + Week 1 quality=0 → no error."""
        from brain.schemas import MacroPlan
        from brain.macro_plan import validate_macro_plan

        plan_dict = _make_base_plan(n_weeks=4, w1_quality=0)
        plan = MacroPlan.model_validate(plan_dict)
        result = validate_macro_plan(plan, short_race_no_quality_days=4)

        assert result.ok, f"Expected ok, got errors: {result.errors}"

    def test_short_race_does_not_enforce_volume_cap(self):
        """short_race_no_quality_days > 0 alone does NOT constrain volume."""
        from brain.schemas import MacroPlan
        from brain.macro_plan import validate_macro_plan

        plan_dict = _make_base_plan(n_weeks=4, w1_quality=0)
        # Set Week 1 volume high — should be fine because no post_race_cap_miles passed
        plan_dict["weeks"][0]["target_volume_miles"] = 28.0
        plan_dict["peak_weekly_miles"] = 28.0
        plan = MacroPlan.model_validate(plan_dict)
        result = validate_macro_plan(plan, short_race_no_quality_days=4)

        vol_errors = [e for e in result.errors if "cap" in e.lower() and "volume" in e.lower()]
        assert not vol_errors, (
            f"short_race should not trigger volume cap errors: {vol_errors}"
        )

    def test_half_marathon_validation_unchanged(self):
        """post_race_cap_miles path (half/marathon) still works independently."""
        from brain.schemas import MacroPlan
        from brain.macro_plan import validate_macro_plan

        plan_dict = _make_base_plan(n_weeks=4, w1_quality=0)
        plan_dict["weeks"][0]["target_volume_miles"] = 30.0  # well over any cap
        plan_dict["weeks"][0]["intensity_budget"] = "high"   # also invalid for recovery
        plan = MacroPlan.model_validate(plan_dict)
        result = validate_macro_plan(
            plan, post_race_cap_miles=14.5, post_race_recovery_weeks=1
        )

        assert not result.ok
        cap_errors = [e for e in result.errors if "cap" in e or "volume" in e or "intensity" in e]
        assert len(cap_errors) > 0


class TestShortRaceEndToEnd:
    """
    Full generate_macro_plan integration with a short-race context.
    Mocks _call_llm to return a plan with W1 quality=0; ensures it passes.
    """

    def _make_short_race_recovery_json(self, start_week: str, vdot: float) -> str:
        """Valid 4-week base_block plan with W1 quality=0 (short-race compliant)."""
        suns = _sundays(4, start_week)
        weeks = [
            # Week 1: easy only — short race recovery
            {**_make_macro_week_dict(1, suns[0], volume=20.0, lr=72, intensity="low", quality=0),
             "planner_notes": "Short-race recovery. Easy only for 4 days."},
            _make_macro_week_dict(2, suns[1], volume=21.0, lr=78, intensity="low", quality=0),
            _make_macro_week_dict(3, suns[2], volume=22.0, lr=82, intensity="moderate", quality=1,
                                  phase="quality"),
            {**_make_macro_week_dict(4, suns[3], volume=21.0, lr=78, intensity="low", quality=0,
                                     phase="quality"),
             "planner_notes": "End of block — hold volume."},
        ]
        return json.dumps({
            "mode": "base_block", "race_date": None, "race_name": None,
            "race_distance": None, "vdot": vdot,
            "start_week": start_week, "total_weeks": 4,
            "peak_weekly_miles": 22.0,
            "rationale": "Short-race recovery block starting at 20 mi/wk.",
            "weeks": weeks,
        })

    def test_short_race_plan_passes_validation(self, tmp_path):
        """5k race → generate_macro_plan uses short-race mode, W1 quality=0 passes."""
        from brain.macro_plan import generate_macro_plan, _extract_macro_inputs

        today = date.today().isoformat()
        packet = {
            "athlete": {"vo2_max": 50.6, "rhr_latest": 48},
            "training_summary": {
                "total_miles": 24.0, "period_days": 14,
                "recent_runs": [{"date": today, "distance_mi": 3.1,
                                 "name": "5k race — local parkrun"}],
            },
            "upcoming_races": [],
        }

        inputs = _extract_macro_inputs(packet)
        assert inputs["post_race_short_race_mode"] is True
        assert inputs["short_race_no_quality_days"] == 4
        assert inputs["week1_cap_miles"] is None  # no volume cap for short race

        mock_json = self._make_short_race_recovery_json(inputs["start_week"], 50.6)

        db = tmp_path / "coach.db"
        with patch("brain.macro_plan._call_llm", return_value=mock_json):
            plan = generate_macro_plan(packet, force=True, db_path=db)

        assert plan.weeks[0].quality_sessions_allowed == 0

    def test_short_race_plan_fails_if_w1_has_quality(self, tmp_path):
        """If LLM returns W1 quality=2, MacroValidationError raised."""
        from brain.macro_plan import generate_macro_plan, MacroValidationError, _extract_macro_inputs

        today = date.today().isoformat()
        packet = {
            "athlete": {"vo2_max": 50.6, "rhr_latest": 48},
            "training_summary": {
                "total_miles": 24.0, "period_days": 14,
                "recent_runs": [{"date": today, "distance_mi": 3.1,
                                 "name": "5k race"}],
            },
            "upcoming_races": [],
        }

        inputs = _extract_macro_inputs(packet)
        # Build plan with W1 quality=2 (invalid for short race recovery)
        suns = _sundays(4, inputs["start_week"])
        bad_weeks = [
            {**_make_macro_week_dict(1, suns[0], volume=20.0, lr=72, quality=2),
             "intensity_budget": "moderate",  # also questionable but not checked here
             "planner_notes": "Quality week."},
            _make_macro_week_dict(2, suns[1], volume=21.0),
            _make_macro_week_dict(3, suns[2], volume=22.0),
            {**_make_macro_week_dict(4, suns[3], volume=21.0),
             "quality_sessions_allowed": 0, "intensity_budget": "low"},
        ]
        bad_json = json.dumps({
            "mode": "base_block", "race_date": None, "race_name": None,
            "race_distance": None, "vdot": 50.6,
            "start_week": inputs["start_week"], "total_weeks": 4,
            "peak_weekly_miles": 22.0,
            "rationale": "Base block starting at 20 mi/wk.",
            "weeks": bad_weeks,
        })

        db = tmp_path / "coach.db"
        with patch("brain.macro_plan._call_llm", return_value=bad_json):
            with pytest.raises(MacroValidationError) as exc_info:
                generate_macro_plan(packet, force=True, db_path=db)

        assert any("short-race" in e.lower() or "no-quality" in e.lower()
                   for e in exc_info.value.errors)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Current week highlight in _print_macro_plan
# ══════════════════════════════════════════════════════════════════════════════

def _make_macro_plan_obj(n_weeks: int = 4, start: Optional[str] = None):
    """Build and return a MacroPlan Pydantic object for display tests."""
    from brain.schemas import MacroPlan

    s = start or _next_sunday()
    suns = _sundays(n_weeks, s)
    weeks = [_make_macro_week_dict(i + 1, suns[i], volume=20.0 + i) for i in range(n_weeks)]
    weeks[-1]["intensity_budget"] = "low"
    weeks[-1]["quality_sessions_allowed"] = 0
    plan_dict = {
        "mode": "base_block", "race_date": None, "race_name": None,
        "race_distance": None, "vdot": 50.6,
        "start_week": s, "total_weeks": n_weeks,
        "peak_weekly_miles": max(w["target_volume_miles"] for w in weeks),
        "rationale": "Test plan.",
        "weeks": weeks,
    }
    return MacroPlan.model_validate(plan_dict)


class TestCurrentWeekHighlight:
    def _capture_output(self, plan, today_str: str) -> str:
        """Capture stdout from _print_macro_plan with the given today date."""
        from cli.coach import _print_macro_plan

        buf = io.StringIO()
        import sys
        old = sys.stdout
        sys.stdout = buf
        try:
            _print_macro_plan(plan, "test-macro-001", today=today_str)
        finally:
            sys.stdout = old
        return buf.getvalue()

    def test_current_week_gets_arrow_marker(self):
        """Row for the week containing today has '→' prefix."""
        plan = _make_macro_plan_obj(n_weeks=4)

        # today = Week 1 start date (a Sunday)
        week1_start = plan.weeks[0].week_start
        output = self._capture_output(plan, week1_start)

        lines = output.splitlines()
        # Find the data row for week 1
        w1_line = next((l for l in lines if "base" in l and "20.0" in l), None)
        assert w1_line is not None, f"Week 1 line not found in:\n{output}"
        assert w1_line.startswith("→"), (
            f"Expected '→' marker on week 1 line, got: {repr(w1_line)}"
        )

    def test_other_weeks_get_space_marker(self):
        """Non-current week rows have ' ' (space) prefix, not '→'."""
        plan = _make_macro_plan_obj(n_weeks=4)

        week1_start = plan.weeks[0].week_start
        output = self._capture_output(plan, week1_start)

        lines = output.splitlines()
        # Week 2 should have space, not arrow
        w2_start = plan.weeks[1].week_start
        w2_line = next((l for l in lines if w2_start in l), None)
        assert w2_line is not None, f"Week 2 line not found"
        assert not w2_line.startswith("→"), (
            f"Week 2 should NOT have '→' marker: {repr(w2_line)}"
        )
        assert w2_line.startswith(" "), (
            f"Week 2 should start with ' ' (space): {repr(w2_line)}"
        )

    def test_today_in_middle_of_week_still_marks_correct_row(self):
        """today = Wednesday of Week 2 → '→' appears on Week 2 row."""
        plan = _make_macro_plan_obj(n_weeks=4)

        week2_start = date.fromisoformat(plan.weeks[1].week_start)
        wednesday = (week2_start + timedelta(days=3)).isoformat()

        output = self._capture_output(plan, wednesday)
        lines = output.splitlines()

        # Week 1 should not have arrow
        w1_line = next((l for l in lines
                        if plan.weeks[0].week_start in l), None)
        assert w1_line and not w1_line.startswith("→"), "Week 1 should not be marked"

        # Week 2 should have arrow
        w2_line = next((l for l in lines
                        if plan.weeks[1].week_start in l), None)
        assert w2_line and w2_line.startswith("→"), (
            f"Week 2 should have '→': {repr(w2_line)}"
        )

    def test_today_outside_block_no_marker(self):
        """today before block start → no '→' on any row."""
        plan = _make_macro_plan_obj(n_weeks=4)

        # A date 100 days before the block starts
        before_block = (date.fromisoformat(plan.start_week) - timedelta(days=100)).isoformat()
        output = self._capture_output(plan, before_block)

        lines = output.splitlines()
        arrow_lines = [l for l in lines if l.startswith("→")]
        assert not arrow_lines, (
            f"Expected no '→' markers when today is outside block: {arrow_lines}"
        )
