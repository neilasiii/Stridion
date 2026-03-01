"""
Tests for race-derived VDOT logic in memory/retrieval.py.

Covers:
- _is_race_distance()         — distance band matching
- _has_race_keyword_activity() — name/title keyword detection
- _derive_vdot_from_activities() — integration: correct race picked, non-races skipped,
                                    ordering, fallback to None

No HR thresholds are used — races are identified by distance bands or name keywords only.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

import pytest

from memory.retrieval import (
    _derive_vdot_from_activities,
    _has_race_keyword_activity,
    _is_race_distance,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _run(dist_mi: float, dur_min: float, name: str = "Easy Run", days_ago: int = 10) -> Dict:
    """Build a minimal 'new-schema' running activity."""
    return {
        "date":           _days_ago(days_ago),
        "activity_type":  "RUNNING",
        "distance_miles": dist_mi,
        "duration_seconds": dur_min * 60,
        "avg_heart_rate": 145,
        "activity_name":  name,
    }


# ── _is_race_distance ────────────────────────────────────────────────────────
# NOTE: _is_race_distance() matches by distance ONLY for long races (half/marathon).
# Short races (5k/10k/15k) are NOT matched by distance alone — they require a keyword
# match via _has_race_keyword_activity(), because easy training runs of similar length
# are common and would otherwise contaminate VDOT with non-race effort.

class TestIsRaceDistance:
    def test_5k_requires_keyword_not_distance(self):
        # 5k requires keyword match — distance alone is not sufficient
        assert not _is_race_distance(3.107)

    def test_5k_short_of_exact_also_rejected(self):
        # Still requires keyword regardless of how close to 5k distance
        assert not _is_race_distance(3.0)

    def test_5k_just_outside(self):
        assert not _is_race_distance(2.89)

    def test_10k_requires_keyword_not_distance(self):
        # 10k requires keyword match — distance alone is not sufficient
        assert not _is_race_distance(6.214)

    def test_10k_short_of_exact_also_rejected(self):
        assert not _is_race_distance(6.0)

    def test_15k_requires_keyword_not_distance(self):
        # 15k requires keyword match — distance alone is not sufficient
        assert not _is_race_distance(9.321)

    def test_half_marathon_exact(self):
        assert _is_race_distance(13.109)

    def test_half_marathon_slightly_long(self):
        # Tampa Running: 13.25 mi — this is the real-world case that prompted the feature
        assert _is_race_distance(13.25)

    def test_half_marathon_upper_edge(self):
        assert _is_race_distance(13.70)   # 13.109 + 0.60 = 13.709

    def test_half_marathon_lower_edge(self):
        assert _is_race_distance(12.51)   # 13.109 - 0.60 = 12.509

    def test_half_marathon_outside(self):
        assert not _is_race_distance(12.4)

    def test_marathon_exact(self):
        assert _is_race_distance(26.219)

    def test_marathon_within_tolerance(self):
        assert _is_race_distance(26.0)

    def test_generic_training_run(self):
        assert not _is_race_distance(8.0)   # not near any standard distance

    def test_very_short_run(self):
        assert not _is_race_distance(0.5)

    def test_zero(self):
        assert not _is_race_distance(0.0)


# ── _has_race_keyword_activity ───────────────────────────────────────────────

class TestHasRaceKeywordActivity:
    def test_activity_name_race(self):
        assert _has_race_keyword_activity({"activity_name": "Boston Race 2026"})

    def test_activity_name_5k(self):
        assert _has_race_keyword_activity({"activity_name": "Neighborhood 5k"})

    def test_activity_name_10k(self):
        assert _has_race_keyword_activity({"activity_name": "10k Run"})

    def test_activity_name_half_marathon(self):
        assert _has_race_keyword_activity({"activity_name": "Clearwater Half Marathon"})

    def test_activity_name_hm(self):
        assert _has_race_keyword_activity({"activity_name": "Tamp HM 2026"})

    def test_activity_name_marathon(self):
        assert _has_race_keyword_activity({"activity_name": "Chicago Marathon"})

    def test_name_field_fallback(self):
        assert _has_race_keyword_activity({"name": "Local 5 km Run"})

    def test_title_field_fallback(self):
        assert _has_race_keyword_activity({"title": "race day effort"})

    def test_case_insensitive(self):
        assert _has_race_keyword_activity({"activity_name": "MARATHON TRAINING RACE"})

    def test_tampa_running_no_keyword(self):
        # "Tampa Running" does NOT contain any keyword — must rely on distance band
        assert not _has_race_keyword_activity({"activity_name": "Tampa Running"})

    def test_easy_run_not_race(self):
        assert not _has_race_keyword_activity({"activity_name": "Easy Run"})

    def test_tempo_not_race(self):
        assert not _has_race_keyword_activity({"activity_name": "Tempo Intervals"})

    def test_empty_name(self):
        assert not _has_race_keyword_activity({})

    def test_all_empty_strings(self):
        assert not _has_race_keyword_activity({"activity_name": "", "name": "", "title": ""})


# ── _derive_vdot_from_activities ─────────────────────────────────────────────

class TestDeriveVdotFromActivities:
    """
    Integration tests — verify that the correct race is identified and that
    non-race activities are properly excluded.
    """

    def test_hm_by_distance_band(self):
        """Tampa Running (13.25 mi, 119.2 min) should yield VDOT ≈ 37.2."""
        health = {
            "activities": [
                _run(dist_mi=13.25, dur_min=119.2, name="Tampa Running", days_ago=30),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is not None
        assert 35.0 <= result <= 40.0, f"Expected ~37.2, got {result}"

    def test_hm_canonical_vdot(self):
        """HM 1:55:04 = 115.07 min → VDOT ≈ 38.3 (canonical reference)."""
        health = {
            "activities": [
                _run(dist_mi=13.109, dur_min=115.07, name="Half Marathon Race", days_ago=20),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is not None
        assert 37.5 <= result <= 39.0, f"Expected ~38.3, got {result}"

    def test_5k_by_keyword(self):
        """Activity named '5k Race' qualifies via keyword (even if dist is 3.05 mi ≈ 5k)."""
        health = {
            "activities": [
                _run(dist_mi=3.10, dur_min=27.0, name="5k Race", days_ago=15),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is not None

    def test_easy_run_excluded(self):
        """Normal easy run — not in any distance band and no keyword → excluded.
        7.5 mi sits between 10k upper edge (6.514) and HM lower edge (12.509) — in no band."""
        health = {
            "activities": [
                _run(dist_mi=7.5, dur_min=80.0, name="Easy Run", days_ago=5),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is None

    def test_tempo_excluded(self):
        """Tempo intervals with high effort — excluded (no keyword, not race distance)."""
        health = {
            "activities": [
                _run(dist_mi=7.5, dur_min=60.0, name="Tempo Intervals", days_ago=7),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is None

    def test_most_recent_race_used(self):
        """When multiple qualifying races exist, the most recent one is returned."""
        health = {
            "activities": [
                _run(dist_mi=13.25, dur_min=119.2, name="Tampa Running", days_ago=60),   # older
                _run(dist_mi=13.109, dur_min=112.0, name="Half Marathon Race", days_ago=10), # newer, faster
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        # Newer race (112 min HM) should yield higher VDOT than older (119.2 min)
        assert result is not None
        # 112 min HM ≈ VDOT 39–40
        assert result > 38.0, f"Expected newer/faster race VDOT, got {result}"

    def test_older_race_not_used_when_newer_exists(self):
        """Older race exists beyond lookback window and is not used."""
        health = {
            "activities": [
                _run(dist_mi=13.25, dur_min=119.2, name="Tampa Running", days_ago=95),  # outside 90-day window
                _run(dist_mi=6.214, dur_min=55.0, name="10k Race", days_ago=20),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        # Only the 10k should qualify
        assert result is not None
        # 10k 55 min → reasonable VDOT
        assert result > 0

    def test_no_activities_returns_none(self):
        result = _derive_vdot_from_activities({}, lookback_days=90)
        assert result is None

    def test_empty_activities_list_returns_none(self):
        result = _derive_vdot_from_activities({"activities": []}, lookback_days=90)
        assert result is None

    def test_all_activities_outside_lookback(self):
        """Activities exist but all are older than lookback_days → None."""
        health = {
            "activities": [
                _run(dist_mi=13.25, dur_min=119.2, name="Tampa Running", days_ago=100),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is None

    def test_non_running_activity_excluded(self):
        """Cycling or strength activities never qualify regardless of distance/name."""
        health = {
            "activities": [
                {
                    "date":           _days_ago(10),
                    "activity_type":  "CYCLING",
                    "distance_miles": 13.1,
                    "duration_seconds": 115 * 60,
                    "activity_name":  "Half Marathon Race",  # keyword, but wrong type
                },
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is None

    def test_zero_distance_excluded(self):
        """Activity with zero distance is skipped."""
        health = {
            "activities": [
                _run(dist_mi=0.0, dur_min=30.0, name="Marathon", days_ago=5),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is None

    def test_keyword_and_distance_both_work(self):
        """Activity that qualifies via BOTH keyword and distance band — still included once."""
        health = {
            "activities": [
                _run(dist_mi=13.109, dur_min=115.0, name="Half Marathon Race", days_ago=10),
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        assert result is not None

    def test_mixed_bag_only_races_used(self):
        """Mix of races and training runs — only qualifying races contribute.

        Training runs at 8.0 mi and 7.5 mi are not in any race band and have no keywords.
        Tampa Running (13.25 mi, HM band) and Parkrun (3.107 mi, 5k band) qualify.
        Parkrun is more recent (14d vs 30d) → it should be returned.
        Parkrun 24:00 5k → VDOT ≈ 37 (confirmed via calculator).
        """
        health = {
            "activities": [
                _run(dist_mi=8.0,  dur_min=72.0,  name="Long Run",      days_ago=3),   # training (no band, no keyword)
                _run(dist_mi=7.5,  dur_min=65.0,  name="Tempo Workout", days_ago=7),   # training (no band, no keyword)
                _run(dist_mi=13.25, dur_min=119.2, name="Tampa Running", days_ago=30),  # race (HM band)
                _run(dist_mi=3.107, dur_min=24.0,  name="Parkrun",       days_ago=14),  # race (5k band)
            ]
        }
        result = _derive_vdot_from_activities(health, lookback_days=90)
        # Most recent qualifying: Parkrun (14d ago). 5k in 24:00 → VDOT ≈ 37.
        assert result is not None
        assert 34.0 <= result <= 42.0, f"Expected Parkrun 5k VDOT ~37, got {result}"
