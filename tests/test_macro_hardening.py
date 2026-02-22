"""
Tests for macro plan hardening pass.

Covers:
  A) Post-race recovery enforcement
     - _detect_post_race_recovery returns required=True when recent long run
     - No detection when no qualifying run
  B) Validation: post-race recovery constraints
     - Fails when Week 1 volume exceeds cap
     - Fails when Week 1 has quality sessions during recovery
     - Fails when Week 1 has high intensity during recovery
  C) Long run caps
     - Early-block (weeks 1-4): exceeding 50% triggers error
     - After week 4: 50% cap does not apply (only 62% applies)
  D) Quality ramp
     - 0→2 jump triggers error
     - Simultaneous quality + LR increase triggers error
     - Gradual 0→1→2 passes
  E) End-of-block stress (base_block)
     - Final week = peak + high + 2 quality → error
     - Final week = peak + moderate + 2 quality → passes
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_sunday() -> str:
    """Return the upcoming Sunday (or today if today is Sunday) as ISO string."""
    today = date.today()
    days = (6 - today.weekday()) % 7
    return (today + timedelta(days=days)).isoformat()


def _sundays(n: int, start: Optional[str] = None) -> List[str]:
    """Return n consecutive Sunday ISO strings starting from start (or next Sunday)."""
    base = date.fromisoformat(start or _next_sunday())
    return [(base + timedelta(days=7 * i)).isoformat() for i in range(n)]


def _make_macro_week(
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
    """Build a minimal MacroWeek-compatible dict."""
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


def _make_valid_base_block(n: int = 4, start: Optional[str] = None) -> dict:
    """Build a minimal valid base_block MacroPlan dict."""
    s = _next_sunday() if start is None else start
    sundays = _sundays(n, s)
    weeks = [
        _make_macro_week(i + 1, sundays[i], volume=20.0 + i * 1.0, lr_min=70)
        for i in range(n)
    ]
    # Last week should not be peak + high + 2Q (prevent check 13 from triggering)
    weeks[-1]["intensity_budget"] = "low"
    weeks[-1]["quality_sessions_allowed"] = 0
    return {
        "mode": "base_block",
        "race_date": None,
        "race_name": None,
        "race_distance": None,
        "vdot": 38.3,
        "start_week": s,
        "total_weeks": n,
        "peak_weekly_miles": max(w["target_volume_miles"] for w in weeks),
        "rationale": f"Aerobic base block starting at {weeks[0]['target_volume_miles']} mi/wk.",
        "weeks": weeks,
    }


def _validate(plan_dict: dict, **kwargs):
    """Validate a plan dict through Pydantic + validate_macro_plan."""
    from brain.schemas import MacroPlan
    from brain.macro_plan import validate_macro_plan

    plan = MacroPlan.model_validate(plan_dict)
    return validate_macro_plan(plan, **kwargs)


# ── A) Post-race recovery detection ──────────────────────────────────────────


class TestPostRaceDetection:
    def _packet(self, runs):
        """Build a minimal context packet with given recent_runs."""
        total_mi = sum(r.get("distance_mi", 0) for r in runs)
        return {
            "training_summary": {
                "recent_runs": runs,
                "total_miles": total_mi * 2,  # approximate 2-week total
                "period_days": 14,
            }
        }

    def test_long_run_7_days_ago_triggers_recovery(self):
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today()
        runs = [
            {"date": (today - timedelta(days=3)).isoformat(), "distance_mi": 13.2},
        ]
        result = _detect_post_race_recovery(self._packet(runs))
        assert result["required"] is True
        assert result["days_ago"] == 3
        assert result["approx_distance_mi"] == 13.2
        assert result["recovery_weeks"] == 1  # half marathon distance

    def test_marathon_run_triggers_2_week_recovery(self):
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today()
        runs = [
            {"date": (today - timedelta(days=5)).isoformat(), "distance_mi": 26.3},
        ]
        result = _detect_post_race_recovery(self._packet(runs))
        assert result["required"] is True
        assert result["recovery_weeks"] == 2

    def test_short_run_does_not_trigger_recovery(self):
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today()
        runs = [
            {"date": (today - timedelta(days=2)).isoformat(), "distance_mi": 6.2},
        ]
        result = _detect_post_race_recovery(self._packet(runs))
        assert result["required"] is False
        assert result["recovery_weeks"] == 0

    def test_run_8_days_ago_does_not_trigger(self):
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today()
        runs = [
            # 8 days ago — just outside the 7-day window
            {"date": (today - timedelta(days=8)).isoformat(), "distance_mi": 15.0},
        ]
        result = _detect_post_race_recovery(self._packet(runs))
        assert result["required"] is False

    def test_empty_runs_returns_not_required(self):
        from brain.macro_plan import _detect_post_race_recovery

        result = _detect_post_race_recovery({"training_summary": {"recent_runs": []}})
        assert result["required"] is False
        assert result["days_ago"] == 0
        assert result["week_load_mi"] == 0.0

    def test_picks_longest_recent_run(self):
        from brain.macro_plan import _detect_post_race_recovery

        today = date.today()
        runs = [
            {"date": (today - timedelta(days=6)).isoformat(), "distance_mi": 12.0},
            {"date": (today - timedelta(days=2)).isoformat(), "distance_mi": 14.5},
        ]
        result = _detect_post_race_recovery(self._packet(runs))
        assert result["required"] is True
        assert result["approx_distance_mi"] == 14.5  # picked the longer one

    def test_missing_training_summary_returns_not_required(self):
        from brain.macro_plan import _detect_post_race_recovery

        result = _detect_post_race_recovery({})
        assert result["required"] is False


# ── B) Validation: post-race recovery constraints ─────────────────────────────


class TestPostRaceValidation:
    def _plan_with_week1(self, volume: float, quality: int = 0, intensity: str = "low") -> dict:
        s = _next_sunday()
        sundays = _sundays(4, s)
        weeks = []
        for i in range(4):
            vol   = volume if i == 0 else 20.0 + i
            qual  = quality if i == 0 else 0
            inten = intensity if i == 0 else "low"
            lr    = int(min(vol * 10 * 0.40, vol * 10 * 0.50 - 1))  # 40% → safe
            weeks.append(_make_macro_week(
                i + 1, sundays[i],
                volume=vol, lr_min=lr, quality=qual, intensity=inten,
            ))
        return {
            "mode": "base_block",
            "race_date": None,
            "race_name": None,
            "race_distance": None,
            "vdot": 38.3,
            "start_week": s,
            "total_weeks": 4,
            "peak_weekly_miles": max(w["target_volume_miles"] for w in weeks),
            "rationale": f"Base block starting at {volume:.1f} mi/wk for recovery.",
            "weeks": weeks,
        }

    def test_volume_exceeds_cap_fails(self):
        plan = self._plan_with_week1(volume=25.0)
        result = _validate(plan, post_race_cap_miles=15.0, post_race_recovery_weeks=1)
        assert not result.ok
        assert any("post-race recovery" in e and "volume" in e for e in result.errors)

    def test_volume_within_cap_passes(self):
        plan = self._plan_with_week1(volume=14.0)
        result = _validate(plan, post_race_cap_miles=15.0, post_race_recovery_weeks=1)
        # Should not flag post-race volume (14.0 < 15.0 * 1.15 + 0.5 = 17.75)
        post_race_errors = [e for e in result.errors if "post-race recovery" in e and "volume" in e]
        assert not post_race_errors

    def test_quality_sessions_during_recovery_fails(self):
        plan = self._plan_with_week1(volume=12.0, quality=1)
        result = _validate(plan, post_race_cap_miles=15.0, post_race_recovery_weeks=1)
        assert not result.ok
        assert any("quality_sessions_allowed" in e for e in result.errors)

    def test_high_intensity_during_recovery_fails(self):
        plan = self._plan_with_week1(volume=12.0, intensity="high")
        result = _validate(plan, post_race_cap_miles=15.0, post_race_recovery_weeks=1)
        assert not result.ok
        assert any("intensity_budget" in e for e in result.errors)

    def test_no_post_race_cap_skips_check(self):
        """When post_race_cap_miles=None, post-race checks are skipped entirely."""
        plan = self._plan_with_week1(volume=30.0, quality=2, intensity="high")
        # Would fail post-race checks, but cap is not set
        result = _validate(plan)  # no post_race_cap_miles
        post_race_errors = [e for e in result.errors if "post-race recovery" in e]
        assert not post_race_errors

    def test_two_recovery_weeks_enforced(self):
        """With recovery_weeks=2, both weeks must obey constraints."""
        s = _next_sunday()
        sundays = _sundays(4, s)
        weeks = [
            _make_macro_week(1, sundays[0], volume=12.0, lr_min=48, quality=0, intensity="low"),
            _make_macro_week(2, sundays[1], volume=25.0, lr_min=90, quality=1, intensity="moderate"),
            _make_macro_week(3, sundays[2], volume=22.0, lr_min=80, quality=0),
            _make_macro_week(4, sundays[3], volume=23.0, lr_min=82, quality=0),
        ]
        plan = {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 4,
            "peak_weekly_miles": 25.0,
            "rationale": "Post-marathon base block starting at 12.0 mi/wk.",
            "weeks": weeks,
        }
        result = _validate(plan, post_race_cap_miles=14.0, post_race_recovery_weeks=2)
        assert not result.ok
        # Week 2 violates volume cap AND quality
        post_errors = [e for e in result.errors if "post-race recovery" in e]
        assert len(post_errors) >= 2  # volume cap + quality_sessions


# ── C) Long run early-block cap ───────────────────────────────────────────────


class TestEarlyBlockLRCap:
    def test_week1_lr_exceeds_50pct_fails(self):
        s = _next_sunday()
        sundays = _sundays(4, s)
        # 20 mi week → 200 min; 50% = 100 min; setting 105 should fail
        weeks = [
            _make_macro_week(1, sundays[0], volume=20.0, lr_min=105),  # 52.5% > 50%
            _make_macro_week(2, sundays[1], volume=20.0, lr_min=80),
            _make_macro_week(3, sundays[2], volume=20.0, lr_min=80),
            _make_macro_week(4, sundays[3], volume=20.0, lr_min=80),
        ]
        plan = _make_valid_base_block(4, s)
        plan["weeks"] = weeks
        result = _validate(plan)
        assert not result.ok
        assert any("early-block LR cap" in e for e in result.errors)

    def test_week4_lr_at_50pct_passes(self):
        s = _next_sunday()
        sundays = _sundays(4, s)
        # 20 mi week → 200 min; 50% = 100 min; exactly 100 min should pass (within tolerance)
        weeks = [
            _make_macro_week(i + 1, sundays[i], volume=20.0, lr_min=100)
            for i in range(4)
        ]
        plan = _make_valid_base_block(4, s)
        plan["weeks"] = weeks
        result = _validate(plan)
        lr_errors = [e for e in result.errors if "early-block LR cap" in e]
        assert not lr_errors  # 100 min at 100 min limit → passes (within 0.5 min tolerance)

    def test_week5_lr_above_50pct_uses_62pct_cap_only(self):
        """Week 5+ only subject to 62% cap, not 50%."""
        s = _next_sunday()
        sundays = _sundays(6, s)
        weeks = [
            # Weeks 1-4 safe
            _make_macro_week(i + 1, sundays[i], volume=20.0, lr_min=80)
            for i in range(4)
        ]
        # Week 5: 20 mi, 105 min LR (52.5%) — exceeds 50% but week > 4 so only 62% applies
        weeks.append(_make_macro_week(5, sundays[4], volume=20.0, lr_min=105))
        weeks.append(_make_macro_week(6, sundays[5], volume=21.0, lr_min=80, quality=1))
        plan = {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 6,
            "peak_weekly_miles": 21.0,
            "rationale": "Aerobic base starting at 20.0 mi/wk.",
            "weeks": weeks,
        }
        result = _validate(plan)
        lr_errors = [e for e in result.errors if "early-block LR cap" in e and "week 5" in e]
        assert not lr_errors  # week 5 is not subject to 50% cap


# ── D) Quality ramp ───────────────────────────────────────────────────────────


class TestQualityRamp:
    def _make_quality_plan(self, quality_sequence, lr_sequence, volumes=None):
        """Build a plan with given quality and LR sequences."""
        n = len(quality_sequence)
        s = _next_sunday()
        sundays = _sundays(n, s)
        vols = volumes or [20.0] * n
        weeks = []
        for i in range(n):
            q = quality_sequence[i]
            lr = lr_sequence[i]
            vol = vols[i]
            phase = "quality" if q > 0 else "base"
            intensity = "moderate" if q > 0 else "low"
            key = "tempo" if q > 0 else "long"
            weeks.append(_make_macro_week(
                i + 1, sundays[i], phase=phase, volume=vol, lr_min=lr,
                quality=q, intensity=intensity, key_type=key,
            ))
        peak = max(w["target_volume_miles"] for w in weeks)
        return {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": n,
            "peak_weekly_miles": peak,
            "rationale": f"Base block starting at {vols[0]:.1f} mi/wk.",
            "weeks": weeks,
        }

    def test_quality_jump_0_to_2_fails(self):
        plan = self._make_quality_plan(
            quality_sequence=[0, 2],
            lr_sequence=[70, 70],
        )
        result = _validate(plan)
        assert not result.ok
        assert any("0→2" in e for e in result.errors)

    def test_gradual_quality_0_1_2_passes(self):
        plan = self._make_quality_plan(
            quality_sequence=[0, 0, 1, 2],
            lr_sequence=[70, 72, 72, 74],
        )
        result = _validate(plan)
        ramp_errors = [e for e in result.errors if "0→2" in e]
        assert not ramp_errors

    def test_simultaneous_quality_and_lr_increase_fails(self):
        """Quality 0→1 AND LR increases >10% in same week → error."""
        plan = self._make_quality_plan(
            quality_sequence=[0, 1],
            lr_sequence=[70, 78],  # 78/70 = 11.4% increase
        )
        result = _validate(plan)
        assert not result.ok
        assert any("simultaneous quality increase" in e for e in result.errors)

    def test_quality_increase_with_small_lr_increase_passes(self):
        """Quality 0→1 AND LR increases ≤10% → ok."""
        plan = self._make_quality_plan(
            quality_sequence=[0, 1],
            lr_sequence=[70, 76],  # 76/70 = 8.6% increase → ok
        )
        result = _validate(plan)
        sim_errors = [e for e in result.errors if "simultaneous quality increase" in e]
        assert not sim_errors

    def test_quality_increase_with_lr_decrease_passes(self):
        """Quality 0→1 AND LR decreases → definitely ok."""
        plan = self._make_quality_plan(
            quality_sequence=[0, 1],
            lr_sequence=[80, 70],
        )
        result = _validate(plan)
        sim_errors = [e for e in result.errors if "simultaneous quality increase" in e]
        assert not sim_errors


# ── E) End-of-block stress ────────────────────────────────────────────────────


class TestEndOfBlockStress:
    def _make_final_week_plan(self, final_volume, final_intensity, final_quality):
        """Make a 4-week base_block where Week 4 has given params."""
        s = _next_sunday()
        sundays = _sundays(4, s)
        weeks = [
            _make_macro_week(1, sundays[0], volume=20.0, lr_min=70, quality=0),
            _make_macro_week(2, sundays[1], volume=22.0, lr_min=75, quality=0),
            _make_macro_week(3, sundays[2], volume=24.0, lr_min=80, quality=1,
                             phase="quality", intensity="moderate", key_type="tempo"),
        ]
        peak_so_far = 24.0
        # Final week
        weeks.append(_make_macro_week(
            4, sundays[3], volume=final_volume, lr_min=80,
            quality=final_quality, intensity=final_intensity,
            phase="quality" if final_quality > 0 else "base",
            key_type="tempo" if final_quality > 0 else "long",
        ))
        peak = max(peak_so_far, final_volume)
        return {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 4,
            "peak_weekly_miles": peak,
            "rationale": "Aerobic base starting at 20.0 mi/wk.",
            "weeks": weeks,
        }

    def test_peak_high_2quality_final_week_fails(self):
        plan = self._make_final_week_plan(
            final_volume=26.0,   # new peak
            final_intensity="high",
            final_quality=2,
        )
        result = _validate(plan)
        assert not result.ok
        assert any("unsustainable block finish" in e for e in result.errors)

    def test_peak_moderate_2quality_passes(self):
        """Peak volume + moderate intensity + 2 quality → not flagged."""
        plan = self._make_final_week_plan(
            final_volume=26.0,
            final_intensity="moderate",
            final_quality=2,
        )
        result = _validate(plan)
        finish_errors = [e for e in result.errors if "unsustainable block finish" in e]
        assert not finish_errors

    def test_holddown_final_week_passes(self):
        """Final week below peak → not flagged."""
        plan = self._make_final_week_plan(
            final_volume=22.0,   # not the peak (24.0 was peak)
            final_intensity="high",
            final_quality=2,
        )
        result = _validate(plan)
        finish_errors = [e for e in result.errors if "unsustainable block finish" in e]
        assert not finish_errors

    def test_race_targeted_not_checked(self):
        """End-of-block stress rule only applies to base_block."""
        s = _next_sunday()
        sundays = _sundays(4, s)
        # A race_targeted plan with a taper at the end
        weeks = [
            _make_macro_week(1, sundays[0], phase="base", volume=20.0, lr_min=70),
            _make_macro_week(2, sundays[1], phase="base", volume=22.0, lr_min=75),
            _make_macro_week(3, sundays[2], phase="quality", volume=22.0, lr_min=75,
                             quality=1, intensity="moderate", key_type="tempo"),
            _make_macro_week(4, sundays[3], phase="taper", volume=26.0, lr_min=80,
                             quality=2, intensity="high", key_type="tempo"),
        ]
        plan = {
            "mode": "race_targeted",
            "race_date": (date.fromisoformat(sundays[3]) + timedelta(days=6)).isoformat(),
            "race_name": "Test Race",
            "race_distance": "half_marathon",
            "vdot": 38.3, "start_week": s, "total_weeks": 4,
            "peak_weekly_miles": 26.0,
            "rationale": "Race-targeted block starting at 20.0 mi/wk.",
            "weeks": weeks,
        }
        result = _validate(plan)
        finish_errors = [e for e in result.errors if "unsustainable block finish" in e]
        assert not finish_errors  # rule does not apply to race_targeted


# ── B) Rationale consistency ───────────────────────────────────────────────────


class TestRationaleConsistency:
    def test_from_zero_rationale_flagged_when_week1_nonzero(self):
        s = _next_sunday()
        sundays = _sundays(3, s)
        weeks = [
            _make_macro_week(1, sundays[0], volume=20.0, lr_min=70),
            _make_macro_week(2, sundays[1], volume=21.0, lr_min=73),
            _make_macro_week(3, sundays[2], volume=22.0, lr_min=76),
        ]
        plan = {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 3,
            "peak_weekly_miles": 22.0,
            "rationale": "Building aerobic base from 0 miles per week to marathon fitness.",
            "weeks": weeks,
        }
        result = _validate(plan)
        assert not result.ok
        assert any("'from 0'" in e or "from 0" in e for e in result.errors)

    def test_accurate_rationale_passes(self):
        s = _next_sunday()
        sundays = _sundays(3, s)
        weeks = [
            _make_macro_week(1, sundays[0], volume=20.0, lr_min=70),
            _make_macro_week(2, sundays[1], volume=21.0, lr_min=73),
            _make_macro_week(3, sundays[2], volume=22.0, lr_min=76),
        ]
        plan = {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 3,
            "peak_weekly_miles": 22.0,
            "rationale": "Aerobic base block starting at 20 mi/wk, building to 22 mi.",
            "weeks": weeks,
        }
        result = _validate(plan)
        rationale_errors = [e for e in result.errors if "'from 0'" in e or "from 0" in e]
        assert not rationale_errors

    def test_from_zero_ignored_when_week1_truly_zero(self):
        """If Week 1 volume is 0 (rest week), 'from 0' in rationale is accurate."""
        s = _next_sunday()
        sundays = _sundays(2, s)
        weeks = [
            _make_macro_week(1, sundays[0], volume=0.0, lr_min=0, key_type="rest",
                             intensity="none", quality=0),
            _make_macro_week(2, sundays[1], volume=15.0, lr_min=55),
        ]
        plan = {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 2,
            "peak_weekly_miles": 15.0,
            "rationale": "Starting from 0 miles this week (complete rest), then building.",
            "weeks": weeks,
        }
        result = _validate(plan)
        rationale_errors = [e for e in result.errors if "'from 0'" in e or "from 0" in e]
        assert not rationale_errors  # Week 1 is actually 0 — rationale is accurate


# ── Integration: valid plan passes all checks ──────────────────────────────────


class TestIntegrationValidPlan:
    def test_clean_4week_base_block_passes(self):
        s = _next_sunday()
        sundays = _sundays(4, s)
        weeks = [
            _make_macro_week(1, sundays[0], volume=20.0, lr_min=70),   # 35% of 200min
            _make_macro_week(2, sundays[1], volume=21.0, lr_min=73),
            _make_macro_week(3, sundays[2], volume=22.0, lr_min=76),
            _make_macro_week(4, sundays[3], volume=22.0, lr_min=76),   # hold, not new peak
        ]
        plan = {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 4,
            "peak_weekly_miles": 22.0,
            "rationale": "Aerobic base block starting at 20.0 mi/wk.",
            "weeks": weeks,
        }
        result = _validate(plan)
        assert result.ok, f"Expected clean plan to pass but got errors: {result.errors}"

    def test_gradual_quality_intro_passes(self):
        s = _next_sunday()
        sundays = _sundays(5, s)
        weeks = [
            _make_macro_week(1, sundays[0], volume=20.0, lr_min=70, quality=0),
            _make_macro_week(2, sundays[1], volume=21.0, lr_min=73, quality=0),
            _make_macro_week(3, sundays[2], volume=22.0, lr_min=76, quality=0),
            # Week 4: introduce 1 quality session, no LR increase
            _make_macro_week(4, sundays[3], volume=22.0, lr_min=76, quality=1,
                             phase="quality", intensity="moderate", key_type="tempo"),
            # Week 5: now 2 quality (still no LR spike)
            _make_macro_week(5, sundays[4], volume=22.0, lr_min=76, quality=2,
                             phase="quality", intensity="moderate", key_type="tempo"),
        ]
        plan = {
            "mode": "base_block",
            "race_date": None, "race_name": None, "race_distance": None,
            "vdot": 38.3, "start_week": s, "total_weeks": 5,
            "peak_weekly_miles": 22.0,
            "rationale": "Base block at 20.0 mi/wk building to quality phase.",
            "weeks": weeks,
        }
        result = _validate(plan)
        assert result.ok, f"Expected gradual quality plan to pass but got: {result.errors}"
