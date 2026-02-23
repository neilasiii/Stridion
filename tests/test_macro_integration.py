"""
Macro plan integration tests — stress-testing the full pipeline.

Covers:
  2. End-to-end post-race macro integration
     - Context packet with race today (13.25 mi) → Week 1 recovery constraints
     - macro_id activated in DB after generate_macro_plan succeeds
  3. Weekly planner stress tests
     - A) Low readiness → low_readiness_confidence flag (deterministic)
     - B) Empty health data → plan_week doesn't crash, produces safe plan
     - C) macro_guidance present + LLM returns over-volume → macro_cap_exceeded flag
  4. Failure mode simulation
     - Invalid plan (quality in recovery week) → MacroValidationError raised
     - set_active_macro_plan NOT called; get_active_macro_plan_id still None
"""
from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _next_sunday() -> str:
    today = date.today()
    days = (6 - today.weekday()) % 7
    return (today + timedelta(days=days)).isoformat()


def _sundays(n: int, start: Optional[str] = None) -> List[str]:
    base = date.fromisoformat(start or _next_sunday())
    return [(base + timedelta(days=7 * i)).isoformat() for i in range(n)]


def _make_macro_week_dict(
    week_number: int,
    week_start: str,
    phase: str = "base",
    volume: float = 20.0,
    lr_min: int = 70,
    intensity: str = "low",
    quality: int = 0,
    key_type: str = "long",
    notes: str = "Base aerobic week.",
    rationale: str = "Build aerobic base.",
) -> dict:
    return {
        "week_number": week_number,
        "week_start": week_start,
        "phase": phase,
        "target_volume_miles": volume,
        "long_run_max_min": lr_min,
        "intensity_budget": intensity,
        "quality_sessions_allowed": quality,
        "key_workout_type": key_type,
        "paces": {
            "easy": "10:30-11:10/mi",
            "tempo": None,
            "interval": None,
            "long_run": "11:10-11:50/mi",
        },
        "planner_notes": notes,
        "phase_rationale": rationale,
    }


def _make_recovery_macro_json(start_week: str, vdot: float, week1_cap: float) -> str:
    """
    Build a valid 12-week base_block macro plan JSON string with Week 1 as recovery.

    Used to mock the LLM response in generate_macro_plan tests.

    Validation rules this plan must satisfy:
      - Volume ramp in base phase: ≤10% per week, no 3+ consecutive >7%
        → alternate between ~8% and ~5% ramp weeks
      - Quality ramp: 0→1→2 only; no simultaneous quality + LR increase >10%
        → introduce quality with flat LR, then increase LR the next week
    """
    sundays = _sundays(12, start_week)
    weeks = []

    # Week 1: post-race recovery
    lr1 = max(40, int(week1_cap * 10 * 0.38))
    weeks.append(_make_macro_week_dict(
        1, sundays[0], phase="base",
        volume=week1_cap,
        lr_min=lr1,
        intensity="low", quality=0, key_type="easy",
        notes="Post-race recovery. Easy only.",
        rationale="Recovery week after race effort.",
    ))

    # Weeks 2–5: gradual base build.
    # Alternate: 8%, 8%, 5%, 8% to avoid 3 consecutive >7% (rule: no 3+ at >7%).
    # The 5% break on week 4 resets the streak counter.
    ramp_pcts = [0.08, 0.08, 0.05, 0.08]  # weeks 2-5
    prev_vol = week1_cap
    prev_lr = lr1
    for i, pct in enumerate(ramp_pcts):
        vol = round(min(prev_vol * (1 + pct), 26.0), 1)
        # LR grows at same rate as volume — stays within 62% cap
        lr = min(100, int(vol * 10 * 0.38))
        weeks.append(_make_macro_week_dict(
            i + 2, sundays[i + 1], phase="base",
            volume=vol, lr_min=lr, intensity="low", quality=0,
        ))
        prev_vol = vol
        prev_lr = lr

    # Week 6: introduce quality=1 with FLAT long run (avoid simultaneous quality+LR spike).
    vol6 = round(min(prev_vol * 1.05, 27.0), 1)
    lr6 = prev_lr  # flat — no LR increase when introducing quality
    weeks.append(_make_macro_week_dict(
        6, sundays[5], phase="quality",
        volume=vol6, lr_min=lr6, intensity="moderate", quality=1,
        key_type="tempo",
        notes="First quality week. One tempo session. LR held flat.",
    ))
    prev_vol = vol6
    prev_lr = lr6

    # Week 7: increase LR now (quality stays at 1, so no simultaneous spike).
    vol7 = round(min(prev_vol * 1.04, 27.5), 1)
    lr7 = min(105, int(vol7 * 10 * 0.40))
    weeks.append(_make_macro_week_dict(
        7, sundays[6], phase="quality",
        volume=vol7, lr_min=lr7, intensity="moderate", quality=1,
        key_type="tempo",
    ))
    prev_vol = vol7
    prev_lr = lr7

    # Week 8: bump quality to 2, keep LR flat again.
    vol8 = round(min(prev_vol * 1.03, 28.0), 1)
    lr8 = prev_lr  # flat when adding second quality session
    weeks.append(_make_macro_week_dict(
        8, sundays[7], phase="quality",
        volume=vol8, lr_min=lr8, intensity="high", quality=2,
        key_type="interval",
    ))
    prev_vol = vol8
    prev_lr = lr8

    # Weeks 9–10: quality peak, small volume step.
    for i in range(8, 10):
        vol = round(min(prev_vol * 1.02, 28.0), 1)
        lr = min(110, int(vol * 10 * 0.40))
        weeks.append(_make_macro_week_dict(
            i + 1, sundays[i], phase="quality",
            volume=vol, lr_min=lr, intensity="high", quality=2,
            key_type="interval",
        ))
        prev_vol = vol
        prev_lr = lr

    peak_vol = max(w["target_volume_miles"] for w in weeks)

    # Weeks 11–12: hold/reduce (end-of-block must not be peak+high+2Q simultaneously).
    for i in range(10, 12):
        vol = round(peak_vol * 0.94, 1)
        lr = min(100, int(vol * 10 * 0.38))
        weeks.append(_make_macro_week_dict(
            i + 1, sundays[i], phase="quality",
            volume=vol, lr_min=lr, intensity="moderate", quality=1,
        ))

    plan = {
        "mode": "base_block",
        "race_date": None,
        "race_name": None,
        "race_distance": None,
        "vdot": vdot,
        "start_week": start_week,
        "total_weeks": 12,
        "peak_weekly_miles": peak_vol,
        "rationale": (
            f"Recovery block after race. Starting at {week1_cap:.1f} mi/wk. "
            f"VDOT {vdot:.1f}."
        )[:300],
        "weeks": weeks,
    }
    return json.dumps(plan)


def _make_plan_day_dict(
    day_date: str,
    workout_type: str = "easy",
    duration_min: int = 45,
    intent: str = "Easy aerobic run",
) -> dict:
    return {
        "date": day_date,
        "intent": intent[:80],
        "workout_type": workout_type,
        "duration_min": duration_min,
        "structure_steps": [
            {
                "label": "main",
                "duration_min": duration_min,
                "target_metric": "pace",
                "target_value": "10:30-11:10/mi",
            }
        ],
        "safety_flags": [],
        "rationale": "Aerobic conditioning.",
    }


def _make_plan_decision_json(
    week_start: str,
    weekly_volume_miles: float = 20.0,
    phase: str = "base",
    context_hash: str = "testhash0001",
) -> str:
    """
    Build a minimal valid PlanDecision JSON string for mocking _call_llm in plan_week.
    """
    ws = date.fromisoformat(week_start)
    we = ws + timedelta(days=6)
    days = [
        _make_plan_day_dict((ws + timedelta(days=i)).isoformat())
        for i in range(7)
    ]
    return json.dumps({
        "week_start": week_start,
        "week_end": we.isoformat(),
        "phase": phase,
        "days": days,
        "weekly_volume_miles": weekly_volume_miles,
        "safety_flags": [],
        "rationale": "Base training week. Building aerobic fitness.",
        "context_hash": context_hash,
    })


def _minimal_context_packet(
    vo2_max: float = 50.6,
    total_miles: float = 24.0,
    recent_runs: Optional[List] = None,
    training_readiness: Optional[float] = None,
    has_health_cache: bool = True,
    macro_guidance: Optional[Dict] = None,
) -> Dict:
    """Build a minimal context packet for planner/macro tests."""
    today = date.today().isoformat()
    packet: Dict = {
        "athlete": {"vo2_max": vo2_max, "rhr_latest": 48},
        "training_summary": {
            "total_miles": total_miles,
            "period_days": 14,
            "recent_runs": recent_runs or [],
        },
        "upcoming_races": [],
        "data_quality": {
            "has_health_cache": has_health_cache,
            "readiness_confidence": "low" if training_readiness is not None and training_readiness < 50 else "ok",
        },
        "readiness": {
            "today": {
                "training_readiness": training_readiness,
                "body_battery_max": 60,
                "hrv": 45.0,
            }
        },
    }
    if macro_guidance is not None:
        packet["macro_guidance"] = macro_guidance
    return packet


# ── 2. End-to-end post-race macro integration ─────────────────────────────────

class TestPostRaceMacroIntegration:
    """
    Integration test: context packet with a 13.25mi race today →
    generate_macro_plan produces a valid plan with Week 1 recovery constraints,
    and the macro_id is activated in the DB.
    """

    def _race_context_packet(self, race_distance_mi: float = 13.25) -> Dict:
        today = date.today().isoformat()
        return _minimal_context_packet(
            vo2_max=50.6,
            total_miles=24.0,
            recent_runs=[{"date": today, "distance_mi": race_distance_mi}],
        )

    def test_week1_recovery_constraints_satisfied(self, tmp_path):
        """Week 1 must have quality=0, intensity∈{none,low}, volume≤cap."""
        from brain.macro_plan import generate_macro_plan, _detect_post_race_recovery, _extract_macro_inputs

        packet = self._race_context_packet()

        # Verify post-race detection fires correctly before the LLM call
        post_race = _detect_post_race_recovery(packet)
        assert post_race["required"] is True, "Post-race should be detected"
        assert post_race["days_ago"] == 0

        inputs = _extract_macro_inputs(packet)
        assert inputs["post_race_recovery_required"] is True
        week1_cap = inputs["week1_cap_miles"]
        assert week1_cap is not None and week1_cap > 0
        start_week = inputs["start_week"]

        mock_json = _make_recovery_macro_json(start_week, 50.6, week1_cap)

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            plan = generate_macro_plan(packet, force=True, db_path=db)

        w1 = plan.weeks[0]
        assert w1.quality_sessions_allowed == 0, "Week 1 must have 0 quality sessions"
        assert w1.intensity_budget in ("none", "low"), (
            f"Week 1 intensity must be none or low, got {w1.intensity_budget}"
        )
        assert w1.target_volume_miles <= week1_cap + 0.1, (
            f"Week 1 volume {w1.target_volume_miles:.1f} exceeds cap {week1_cap:.1f}"
        )

    def test_macro_id_activated_in_db(self, tmp_path):
        """After successful generation, get_active_macro_plan_id returns non-None."""
        from brain.macro_plan import generate_macro_plan, _extract_macro_inputs
        from memory.db import get_active_macro_plan_id

        packet = self._race_context_packet()
        inputs = _extract_macro_inputs(packet)
        mock_json = _make_recovery_macro_json(
            inputs["start_week"], 50.6, inputs.get("week1_cap_miles") or 14.5
        )

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            generate_macro_plan(packet, force=True, db_path=db)

        macro_id = get_active_macro_plan_id(db_path=db)
        assert macro_id is not None, "Macro ID should be set after successful generation"
        assert len(macro_id) > 5

    def test_plan_has_12_weeks(self, tmp_path):
        """base_block always generates exactly 12 weeks."""
        from brain.macro_plan import generate_macro_plan, _extract_macro_inputs

        packet = self._race_context_packet()
        inputs = _extract_macro_inputs(packet)
        mock_json = _make_recovery_macro_json(
            inputs["start_week"], 50.6, inputs.get("week1_cap_miles") or 14.5
        )

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            plan = generate_macro_plan(packet, force=True, db_path=db)

        assert plan.total_weeks == 12
        assert len(plan.weeks) == 12


# ── 3. Weekly planner stress tests ────────────────────────────────────────────

class TestPlannerStressTests:
    """
    Stress tests for plan_week's deterministic post-LLM enforcement.

    All tests mock _call_llm so no actual LLM subprocess is spawned.
    """

    def _week_start(self) -> str:
        """Return the upcoming Sunday as ISO string."""
        return _next_sunday()

    def test_A_low_readiness_adds_flag(self, tmp_path):
        """
        Scenario A: training_readiness < 50 → low_readiness_confidence in safety_flags.

        This flag is added deterministically by plan_week, regardless of LLM output.
        """
        from brain.planner import plan_week

        ws = self._week_start()
        mock_json = _make_plan_decision_json(ws, weekly_volume_miles=20.0)
        packet = _minimal_context_packet(
            training_readiness=38.0,   # well below 50 → low confidence
            has_health_cache=True,
        )
        # readiness_confidence is set to "low" when training_readiness < 50
        packet["data_quality"]["readiness_confidence"] = "low"

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db, week_start=date.fromisoformat(ws))

        assert "low_readiness_confidence" in decision.safety_flags, (
            f"Expected low_readiness_confidence in {decision.safety_flags}"
        )

    def test_B_empty_health_data_no_crash(self, tmp_path):
        """
        Scenario B: no health data (has_health_cache=False) → plan_week
        completes without crashing and adds low_readiness_confidence flag.
        """
        from brain.planner import plan_week

        ws = self._week_start()
        mock_json = _make_plan_decision_json(ws, weekly_volume_miles=15.0)
        packet = _minimal_context_packet(
            vo2_max=None,
            total_miles=0.0,
            recent_runs=[],
            has_health_cache=False,
        )
        packet["data_quality"] = {
            "has_health_cache": False,
            "readiness_confidence": "low",
        }

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db, week_start=date.fromisoformat(ws))

        # Should complete without exception
        assert decision is not None
        assert decision.weekly_volume_miles >= 0
        assert "low_readiness_confidence" in decision.safety_flags

    def test_C_macro_cap_exceeded_flag(self, tmp_path):
        """
        Scenario C: macro_guidance present with target=20 mi but LLM returns
        26 mi (over-volume) → macro_cap_exceeded added to safety_flags.
        """
        from brain.planner import plan_week

        ws = self._week_start()
        # LLM returns 26 mi — 6 mi over the 20 mi macro target
        mock_json = _make_plan_decision_json(ws, weekly_volume_miles=26.0)

        macro_guidance = {
            "macro_id": "base-v51-test",
            "mode": "base_block",
            "race_date": None,
            "total_weeks": 12,
            "weeks_remaining": 10,
            "current_week": {
                "week_number": 3,
                "week_start": ws,
                "phase": "base",
                "target_volume_miles": 20.0,  # cap
                "long_run_max_min": 75,
                "intensity_budget": "low",
                "quality_sessions_allowed": 0,
                "key_workout_type": "long",
                "paces": {"easy": "10:30-11:10/mi", "long_run": "11:10-11:50/mi"},
                "planner_notes": "Base aerobic week.",
                "phase_rationale": "Building aerobic foundation.",
            },
        }
        packet = _minimal_context_packet(macro_guidance=macro_guidance)

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db, week_start=date.fromisoformat(ws))

        assert "macro_guided" in decision.safety_flags, (
            f"Expected macro_guided in {decision.safety_flags}"
        )
        assert "macro_cap_exceeded" in decision.safety_flags, (
            f"Expected macro_cap_exceeded in {decision.safety_flags} "
            f"(plan={decision.weekly_volume_miles:.1f} mi, target=20.0 mi)"
        )

    def test_C_within_macro_cap_no_flag(self, tmp_path):
        """
        Volume within cap (≤ target + 0.5 tolerance) → macro_cap_exceeded NOT added.
        """
        from brain.planner import plan_week

        ws = self._week_start()
        mock_json = _make_plan_decision_json(ws, weekly_volume_miles=20.3)  # within tolerance

        macro_guidance = {
            "macro_id": "base-v51-test",
            "mode": "base_block",
            "current_week": {
                "week_number": 3,
                "week_start": ws,
                "phase": "base",
                "target_volume_miles": 20.0,
                "long_run_max_min": 75,
                "intensity_budget": "low",
                "quality_sessions_allowed": 0,
                "key_workout_type": "long",
                "paces": {"easy": "10:30-11:10/mi", "long_run": "11:10-11:50/mi"},
                "planner_notes": "Base week.",
                "phase_rationale": "Base.",
            },
        }
        packet = _minimal_context_packet(macro_guidance=macro_guidance)

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=mock_json):
            decision = plan_week(packet, force=True, db_path=db, week_start=date.fromisoformat(ws))

        assert "macro_cap_exceeded" not in decision.safety_flags, (
            f"macro_cap_exceeded should not be set at 20.3 mi with 20.0 target "
            f"(0.5 tolerance); flags={decision.safety_flags}"
        )
        assert "macro_guided" in decision.safety_flags


# ── 4. Failure mode simulation ────────────────────────────────────────────────

class TestFailureMode:
    """
    Invalid macro plan → MacroValidationError raised, set_active_macro_plan NOT called.
    """

    def _make_invalid_recovery_json(self, start_week: str, vdot: float) -> str:
        """
        Return a macro plan JSON that intentionally violates recovery rules:
        - Week 1 has quality=2 and high intensity despite needing recovery.
        """
        sundays = _sundays(12, start_week)
        weeks = []
        # Week 1: INVALID — quality=2 in recovery week
        weeks.append(_make_macro_week_dict(
            1, sundays[0], phase="base",
            volume=25.0,          # way over any recovery cap
            lr_min=120,
            intensity="high",     # INVALID for recovery
            quality=2,            # INVALID for recovery
            key_type="interval",
        ))
        for i in range(1, 12):
            weeks.append(_make_macro_week_dict(i + 1, sundays[i], volume=25.0))
        # Make end-of-block safe to avoid triggering E check
        weeks[-1]["intensity_budget"] = "low"
        weeks[-1]["quality_sessions_allowed"] = 0

        return json.dumps({
            "mode": "base_block",
            "race_date": None,
            "race_name": None,
            "race_distance": None,
            "vdot": vdot,
            "start_week": start_week,
            "total_weeks": 12,
            "peak_weekly_miles": 25.0,
            "rationale": "Test invalid plan — from scratch.",
            "weeks": weeks,
        })

    def test_invalid_plan_raises_validation_error(self, tmp_path):
        """MacroValidationError raised when LLM returns plan violating recovery rules."""
        from brain.macro_plan import generate_macro_plan, MacroValidationError, _extract_macro_inputs

        today = date.today().isoformat()
        packet = _minimal_context_packet(
            recent_runs=[{"date": today, "distance_mi": 13.25}]
        )
        inputs = _extract_macro_inputs(packet)
        invalid_json = self._make_invalid_recovery_json(inputs["start_week"], 50.6)

        db = tmp_path / "test_coach.db"
        with patch("brain.planner._call_llm", return_value=invalid_json):
            with pytest.raises(MacroValidationError) as exc_info:
                generate_macro_plan(packet, force=True, db_path=db)

        err = exc_info.value
        assert len(err.errors) > 0, "Should have at least one validation error"
        # At least one error should mention recovery violation
        combined = " ".join(err.errors).lower()
        assert any(
            kw in combined
            for kw in ("quality", "recovery", "volume", "intensity", "cap")
        ), f"Expected recovery-related error; got: {err.errors}"

    def test_invalid_plan_not_activated_in_db(self, tmp_path):
        """After MacroValidationError, get_active_macro_plan_id must remain None."""
        from brain.macro_plan import generate_macro_plan, MacroValidationError, _extract_macro_inputs
        from memory.db import get_active_macro_plan_id, init_db

        today = date.today().isoformat()
        packet = _minimal_context_packet(
            recent_runs=[{"date": today, "distance_mi": 13.25}]
        )
        inputs = _extract_macro_inputs(packet)
        invalid_json = self._make_invalid_recovery_json(inputs["start_week"], 50.6)

        db = tmp_path / "test_coach.db"
        init_db(db_path=db)

        with patch("brain.planner._call_llm", return_value=invalid_json):
            with pytest.raises(MacroValidationError):
                generate_macro_plan(packet, force=True, db_path=db)

        macro_id = get_active_macro_plan_id(db_path=db)
        assert macro_id is None, (
            f"set_active_macro_plan must NOT be called after validation failure; "
            f"got macro_id={macro_id}"
        )

    def test_invalid_plan_audited_as_validation_failed(self, tmp_path):
        """Failed plan is inserted with status='validation_failed' for audit."""
        import sqlite3
        from brain.macro_plan import generate_macro_plan, MacroValidationError, _extract_macro_inputs
        from memory.db import init_db

        today = date.today().isoformat()
        packet = _minimal_context_packet(
            recent_runs=[{"date": today, "distance_mi": 13.25}]
        )
        inputs = _extract_macro_inputs(packet)
        invalid_json = self._make_invalid_recovery_json(inputs["start_week"], 50.6)

        db = tmp_path / "test_coach.db"
        init_db(db_path=db)

        with patch("brain.planner._call_llm", return_value=invalid_json):
            with pytest.raises(MacroValidationError):
                generate_macro_plan(packet, force=True, db_path=db)

        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute(
                "SELECT status FROM macro_plans WHERE status = 'validation_failed'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, (
            "A 'validation_failed' row should be inserted in macro_plans for audit"
        )
