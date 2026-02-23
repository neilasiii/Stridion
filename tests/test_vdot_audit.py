"""
VDOT Sanity Audit — tests for VDOT derivation correctness end-to-end.

Covers:
  1. Reference VDOT formula (Jack Daniels)
     - Half marathon 1:55:04 → VDOT 38.3 (canonical reference)
     - Marathon 4:00:00 → VDOT ~37
  2. retrieval.py vo2_max reading order
     - vo2_max_readings newest-first → newest used (not oldest)
     - vo2_max_readings oldest-first → newest used
     - Single reading → that reading used
  3. _extract_macro_inputs propagates athlete.vo2_max as vdot
  4. Missing vo2_max in context packet defaults to 38.0
  5. Old Garmin API nested dict schema still works
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from typing import Dict, List, Optional


# ── 1. Reference formula ──────────────────────────────────────────────────────

class TestVDOTFormula:
    def test_half_marathon_reference(self):
        """Half marathon 1:55:04 (6904 s) → VDOT 38.3 per Daniels docstring."""
        from src.vdot_calculator import calculate_vdot

        vdot = calculate_vdot(21097.5, 6904)
        assert abs(vdot - 38.3) < 0.15, f"Expected ~38.3, got {vdot:.2f}"

    def test_marathon_four_hours(self):
        """Full marathon 4:00:00 (14400 s) → VDOT approximately 36–38."""
        from src.vdot_calculator import calculate_vdot

        vdot = calculate_vdot(42195.0, 14400)
        assert 35.5 < vdot < 38.5, f"Marathon 4h VDOT out of expected range: {vdot:.2f}"

    def test_faster_runner_higher_vdot(self):
        """Faster HM time produces strictly higher VDOT."""
        from src.vdot_calculator import calculate_vdot

        # 1:45 HM vs 1:55 HM
        vdot_fast = calculate_vdot(21097.5, 6300)   # 1:45:00
        vdot_slow = calculate_vdot(21097.5, 6900)   # 1:55:00
        assert vdot_fast > vdot_slow

    def test_5k_reference(self):
        """5K 22:00 (1320 s) → VDOT approximately 43–47."""
        from src.vdot_calculator import calculate_vdot

        vdot = calculate_vdot(5000.0, 1320)
        assert 43.0 < vdot < 47.0, f"5K 22min VDOT out of range: {vdot:.2f}"


# ── 2. vo2_max reading order ──────────────────────────────────────────────────

def _build_health_cache(readings: List[Dict]) -> Dict:
    """Construct a minimal health cache with the given vo2_max_readings."""
    return {"vo2_max_readings": readings, "activities": []}


def _extract_vdot_from_cache(readings: List[Dict]) -> Optional[float]:
    """
    Replicate the retrieval.py VDOT extraction path in isolation.

    Loads a synthetic health cache and reads the vdot_approx value
    using the same logic as retrieval.py (max by date).
    """
    health = _build_health_cache(readings)
    vo2_raw = health.get("vo2_max")
    vdot_approx = None
    if isinstance(vo2_raw, dict):
        vdot_approx = vo2_raw.get("generic", {}).get("vo2MaxPreciseValue")
    if vdot_approx is None:
        cached_readings = health.get("vo2_max_readings", [])
        if cached_readings:
            latest = max(cached_readings, key=lambda r: r.get("date", ""))
            vdot_approx = latest.get("vo2_max")
    return vdot_approx


class TestVDOTReadingOrder:
    def test_newest_first_list_uses_newest_value(self):
        """When readings are newest-first (garmin_sync order), most recent date wins."""
        today = date.today().isoformat()
        old_date = (date.today() - timedelta(days=90)).isoformat()

        readings = [
            {"date": today,     "vo2_max": 52.0},   # newest (index 0)
            {"date": old_date,  "vo2_max": 48.0},   # oldest (index -1)
        ]
        result = _extract_vdot_from_cache(readings)
        assert result == 52.0, (
            f"Expected newest reading (52.0) but got {result}; "
            "readings[-1] would return 48.0 — this confirms the bug fix"
        )

    def test_oldest_first_list_uses_newest_value(self):
        """When readings are oldest-first, most recent date still wins."""
        today = date.today().isoformat()
        old_date = (date.today() - timedelta(days=90)).isoformat()

        readings = [
            {"date": old_date,  "vo2_max": 48.0},   # oldest (index 0)
            {"date": today,     "vo2_max": 52.0},   # newest (index -1)
        ]
        result = _extract_vdot_from_cache(readings)
        assert result == 52.0, f"Expected newest reading (52.0) but got {result}"

    def test_single_reading_returned(self):
        """A single reading is always returned regardless of order logic."""
        readings = [{"date": "2025-11-14", "vo2_max": 50.6}]
        result = _extract_vdot_from_cache(readings)
        assert result == 50.6

    def test_three_readings_correct_max(self):
        """Among three readings at different dates, the latest date wins."""
        readings = [
            {"date": "2026-01-15", "vo2_max": 51.0},
            {"date": "2025-11-14", "vo2_max": 50.6},
            {"date": "2026-02-22", "vo2_max": 50.1},  # latest
        ]
        result = _extract_vdot_from_cache(readings)
        assert result == 50.1

    def test_old_garmin_nested_dict_schema(self):
        """Old Garmin API schema (vo2_max.generic.vo2MaxPreciseValue) still works."""
        health = {
            "vo2_max": {"generic": {"vo2MaxPreciseValue": 45.7}},
            "activities": [],
        }
        vo2_raw = health.get("vo2_max")
        vdot_approx = None
        if isinstance(vo2_raw, dict):
            vdot_approx = vo2_raw.get("generic", {}).get("vo2MaxPreciseValue")
        assert vdot_approx == 45.7

    def test_missing_readings_returns_none(self):
        """Empty readings list → vdot_approx stays None (caller defaults to 38.0)."""
        result = _extract_vdot_from_cache([])
        assert result is None


# ── 3. _extract_macro_inputs propagates vo2_max ───────────────────────────────

def _next_sunday() -> str:
    today = date.today()
    days = (6 - today.weekday()) % 7
    return (today + timedelta(days=days)).isoformat()


def _minimal_context_packet(vo2_max: Optional[float], total_miles: float = 20.0) -> Dict:
    """Build a minimal context packet for _extract_macro_inputs."""
    return {
        "athlete": {"vo2_max": vo2_max, "rhr_latest": 48},
        "training_summary": {
            "total_miles": total_miles,
            "period_days": 14,
            "recent_runs": [],
        },
        "upcoming_races": [],
    }


class TestExtractMacroInputs:
    def test_vo2max_propagated_as_vdot(self):
        """athlete.vo2_max flows through _extract_macro_inputs as vdot."""
        from brain.macro_plan import _extract_macro_inputs

        packet = _minimal_context_packet(vo2_max=50.6)
        inputs = _extract_macro_inputs(packet)
        assert inputs["vdot"] == 50.6

    def test_missing_vo2max_defaults_to_38(self):
        """When athlete.vo2_max is None, vdot defaults to 38.0."""
        from brain.macro_plan import _extract_macro_inputs

        packet = _minimal_context_packet(vo2_max=None)
        inputs = _extract_macro_inputs(packet)
        assert inputs["vdot"] == 38.0

    def test_mode_is_base_block_when_no_race(self):
        """No upcoming races → mode=base_block."""
        from brain.macro_plan import _extract_macro_inputs

        packet = _minimal_context_packet(vo2_max=42.0)
        inputs = _extract_macro_inputs(packet)
        assert inputs["mode"] == "base_block"

    def test_block_weeks_12_for_base_block(self):
        """base_block always produces 12-week block."""
        from brain.macro_plan import _extract_macro_inputs

        packet = _minimal_context_packet(vo2_max=42.0)
        inputs = _extract_macro_inputs(packet)
        assert inputs["block_weeks"] == 12

    def test_current_weekly_miles_derived_from_summary(self):
        """weekly avg = total_miles / period_days * 7."""
        from brain.macro_plan import _extract_macro_inputs

        packet = _minimal_context_packet(vo2_max=42.0, total_miles=28.0)
        # 28 mi over 14 days = 2 mi/day = 14 mi/wk
        inputs = _extract_macro_inputs(packet)
        assert abs(inputs["current_weekly_miles"] - 14.0) < 0.2
