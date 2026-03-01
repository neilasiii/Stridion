"""Tests for athlete_pattern_analyzer module."""
import json
import sys
import pytest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athlete_pattern_analyzer import classify_run


def _run(name="", dist=5.0, duration_s=3000, avg_hr=135, zones=None, splits=None):
    return {
        "activity_name": name,
        "distance_miles": dist,
        "duration_seconds": duration_s,
        "avg_heart_rate": avg_hr,
        "hr_zones": zones or [
            {"zone_number": 1, "time_in_zone_seconds": 2800},
            {"zone_number": 2, "time_in_zone_seconds": 200},
            {"zone_number": 3, "time_in_zone_seconds": 0},
            {"zone_number": 4, "time_in_zone_seconds": 0},
            {"zone_number": 5, "time_in_zone_seconds": 0},
        ],
        "splits": splits or [],
    }


class TestClassifyRunByName:
    def test_keyword_easy(self):
        assert classify_run(_run("Easy Run 45min")) == "easy"

    def test_shorthand_e_suffix(self):
        assert classify_run(_run("Altamonte - 30 min E")) == "easy"

    def test_shorthand_e_apostrophe(self):
        assert classify_run(_run("45' E")) == "easy"

    def test_keyword_tempo(self):
        assert classify_run(_run("20 min warm up 25 min @ tempo")) == "tempo"

    def test_keyword_interval(self):
        assert classify_run(_run("8x40sec intervals")) == "interval"

    def test_keyword_long(self):
        assert classify_run(_run("Long Run 90min")) == "long"

    def test_keyword_race(self):
        assert classify_run(_run("Tampa Running", dist=13.25, avg_hr=172)) == "race"

    def test_marathon_by_distance(self):
        assert classify_run(_run("Skunk Ape Marathon", dist=26.5, avg_hr=162)) == "race"


class TestClassifyRunByStructure:
    def _structured_splits(self, n_intervals=4, interval_min=4, interval_sec=None):
        interval_sec = interval_sec or interval_min * 60
        splits = [{"type": "INTERVAL_WARMUP", "duration_seconds": 1200}]
        for _ in range(n_intervals):
            splits.append({"type": "INTERVAL_ACTIVE", "duration_seconds": interval_sec})
            splits.append({"type": "INTERVAL_REST", "duration_seconds": 60})
        splits.append({"type": "INTERVAL_COOLDOWN", "duration_seconds": 1200})
        return splits

    def test_short_repeats_classified_as_interval(self):
        # 4x4min with rest → interval
        splits = self._structured_splits(n_intervals=4, interval_min=4)
        assert classify_run(_run(splits=splits)) == "interval"

    def test_long_repeats_classified_as_tempo(self):
        # 2x12min with recovery → tempo
        splits = self._structured_splits(n_intervals=2, interval_min=12)
        assert classify_run(_run(splits=splits)) == "tempo"

    def test_warmup_cooldown_only_not_structured(self):
        # Just warmup + cooldown, no INTERVAL_ACTIVE → fallback to zones
        splits = [
            {"type": "INTERVAL_WARMUP", "duration_seconds": 1200},
            {"type": "INTERVAL_COOLDOWN", "duration_seconds": 1200},
        ]
        # Low HR easy zones → easy
        assert classify_run(_run(splits=splits)) == "easy"


class TestClassifyRunByZones:
    def _zones(self, z1=0, z2=0, z3=0, z4=0, z5=0):
        return [
            {"zone_number": 1, "time_in_zone_seconds": z1},
            {"zone_number": 2, "time_in_zone_seconds": z2},
            {"zone_number": 3, "time_in_zone_seconds": z3},
            {"zone_number": 4, "time_in_zone_seconds": z4},
            {"zone_number": 5, "time_in_zone_seconds": z5},
        ]

    def test_mostly_z1z2_is_easy(self):
        zones = self._zones(z1=2000, z2=800, z3=0, z4=0, z5=0)
        assert classify_run(_run(duration_s=2800, zones=zones)) == "easy"

    def test_high_z3_sustained_is_tempo(self):
        # 40% of time in z3+ = tempo
        zones = self._zones(z1=600, z2=600, z3=1200, z4=0, z5=0)
        assert classify_run(_run(duration_s=2400, zones=zones)) == "tempo"

    def test_short_easy_no_zones(self):
        assert classify_run(_run(name="", dist=3.0, duration_s=1800, zones=[])) == "easy"

    def test_long_distance_low_hr_is_long(self):
        zones = self._zones(z1=3000, z2=2000, z3=100, z4=0, z5=0)
        assert classify_run(_run(dist=11.0, duration_s=5100, zones=zones)) == "long"


class TestDataJoiner:
    def _make_run(self, date_str, pace=10.0, hr=135, dist=5.0):
        return {
            "date": date_str + "T08:00:00",
            "activity_type": "RUNNING",
            "activity_name": "Easy Run",
            "distance_miles": dist,
            "duration_seconds": dist * pace * 60,
            "avg_heart_rate": hr,
            "pace_per_mile": pace,
            "hr_zones": [
                {"zone_number": z, "time_in_zone_seconds": 2800 if z == 1 else 0}
                for z in range(1, 6)
            ],
            "splits": [],
        }

    def _make_recovery(self, date_str, hrv=65, bb=70, readiness=60, sleep_min=420):
        return {
            "hrv":       {"date": date_str, "last_night_avg": hrv},
            "bb":        {"date": date_str, "latest_level": bb},
            "readiness": {"date": date_str, "score": readiness},
            "sleep":     {"date": date_str, "total_duration_minutes": sleep_min},
        }

    def test_run_joined_with_same_day_recovery(self):
        from athlete_pattern_analyzer import _join_runs_with_recovery
        run = self._make_run("2026-03-01")
        rec = self._make_recovery("2026-03-01")
        hrv_map = {"2026-03-01": rec["hrv"]}
        bb_map  = {"2026-03-01": rec["bb"]}
        rdy_map = {"2026-03-01": rec["readiness"]}
        slp_map = {"2026-03-01": rec["sleep"]}
        result = _join_runs_with_recovery([run], hrv_map, bb_map, rdy_map, slp_map)
        assert len(result) == 1
        assert result[0]["hrv_last_night"] == 65
        assert result[0]["body_battery"] == 70
        assert result[0]["readiness_score"] == 60
        assert result[0]["sleep_hours"] == pytest.approx(7.0, abs=0.1)

    def test_run_without_matching_recovery_still_included(self):
        from athlete_pattern_analyzer import _join_runs_with_recovery
        run = self._make_run("2026-03-01")
        result = _join_runs_with_recovery([run], {}, {}, {}, {})
        assert len(result) == 1
        assert result[0]["hrv_last_night"] is None

    def test_workout_type_added(self):
        from athlete_pattern_analyzer import _join_runs_with_recovery
        run = self._make_run("2026-03-01")
        run["activity_name"] = "Easy Run 45min"
        result = _join_runs_with_recovery([run], {}, {}, {}, {})
        assert result[0]["workout_type"] == "easy"


class TestAnalyzePatterns:
    """analyze_patterns() returns a dict with 5 pattern keys."""

    def _make_joined_run(self, wtype, pace, hr, hrv=65, bb=70, readiness=65,
                          sleep_h=7.0, dist=5.0, date_str="2026-01-10"):
        return {
            "date": date_str,
            "workout_type": wtype,
            "distance_miles": dist,
            "duration_min": dist * pace,
            "pace_per_mile": pace,
            "avg_heart_rate": hr,
            "quality_zone_pct": 0.5 if wtype in ("tempo","interval") else 0.05,
            "hrv_last_night": hrv,
            "hrv_status": "BALANCED",
            "body_battery": bb,
            "readiness_score": readiness,
            "sleep_hours": sleep_h,
        }

    def _easy_runs(self, n=20):
        return [
            self._make_joined_run("easy", pace=10.0 + 0.01*i, hr=134 + i % 5,
                                   date_str=f"2026-01-{i+1:02d}")
            for i in range(n)
        ]

    def _quality_runs(self):
        return [
            self._make_joined_run("tempo", pace=9.0, hr=155, hrv=70, date_str="2026-01-03"),
            self._make_joined_run("tempo", pace=9.5, hr=158, hrv=50, date_str="2026-01-10"),
            self._make_joined_run("interval", pace=8.5, hr=162, hrv=72, date_str="2026-01-17"),
            self._make_joined_run("interval", pace=9.8, hr=155, hrv=48, date_str="2026-01-24"),
        ]

    def test_returns_all_five_keys(self):
        from athlete_pattern_analyzer import analyze_patterns
        runs = self._easy_runs() + self._quality_runs()
        result = analyze_patterns(runs)
        for key in ("hrv_calibration", "aerobic_efficiency",
                    "quality_predictors", "recovery_signature", "volume_tolerance"):
            assert key in result, f"Missing key: {key}"

    def test_hrv_calibration_has_baseline(self):
        from athlete_pattern_analyzer import analyze_patterns
        runs = self._easy_runs() + self._quality_runs()
        result = analyze_patterns(runs)
        assert result["hrv_calibration"]["median_hrv"] == 65

    def test_aerobic_efficiency_has_pace_at_hr(self):
        from athlete_pattern_analyzer import analyze_patterns
        runs = self._easy_runs(20)
        result = analyze_patterns(runs)
        assert "pace_at_hr" in result["aerobic_efficiency"]
        assert len(result["aerobic_efficiency"]["pace_at_hr"]) >= 1

    def test_quality_predictors_has_thresholds(self):
        from athlete_pattern_analyzer import analyze_patterns
        runs = self._easy_runs() + self._quality_runs()
        result = analyze_patterns(runs)
        qp = result["quality_predictors"]
        assert "hrv_median_good" in qp
        assert "hrv_median_poor" in qp

    def test_empty_input_returns_none_values(self):
        from athlete_pattern_analyzer import analyze_patterns
        result = analyze_patterns([])
        assert result["hrv_calibration"]["median_hrv"] is None


class TestWritePatterns:
    def _sample_patterns(self):
        return {
            "hrv_calibration": {
                "median_hrv": 67.0, "hrv_range": (45.0, 92.0),
                "p25_hrv": 58.0, "p75_hrv": 75.0,
                "garmin_balanced_floor": 52.0, "n_days": 250,
            },
            "aerobic_efficiency": {
                "pace_at_hr": {130: 10.4, 135: 10.1, 140: 9.8},
                "trend_note": "Aerobic efficiency improved 6.2% over the data window",
                "n_easy_runs": 120,
            },
            "quality_predictors": {
                "n_quality_sessions": 42,
                "pace_cutoff_min_per_mile": 9.45,
                "hrv_median_good": 71.0, "hrv_median_poor": 57.0,
                "sleep_median_good": 7.0, "sleep_median_poor": 6.1,
                "bb_median_good": 72.0, "bb_median_poor": 58.0,
                "good_pct_with_all_conditions_met": 74,
            },
            "recovery_signature": {
                "days_to_hrv_recovery": 2.0,
                "n_quality_sessions_analysed": 42, "hrv_baseline_used": 67.0,
            },
            "volume_tolerance": {
                "sustainable_weekly_miles": 26.0,
                "peak_week_miles": 31.0, "n_weeks_analysed": 52,
            },
        }

    def test_writes_markdown_file(self):
        from athlete_pattern_analyzer import write_patterns
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            out = Path(f.name)
        write_patterns(self._sample_patterns(), out_path=out,
                        n_runs=253, date_range=("2024-11-18", "2026-02-28"))
        content = out.read_text()
        assert "## HRV Calibration" in content
        assert "67.0" in content  # median HRV
        assert "## Aerobic Efficiency" in content
        assert "130" in content   # HR bucket
        assert "## Quality Session Predictors" in content
        assert "## Recovery Signature" in content
        assert "## Volume Tolerance" in content
        out.unlink()

    def test_file_has_last_updated_line(self):
        from athlete_pattern_analyzer import write_patterns
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            out = Path(f.name)
        write_patterns(self._sample_patterns(), out_path=out,
                        n_runs=253, date_range=("2024-11-18", "2026-02-28"))
        content = out.read_text()
        assert "Last updated:" in content
        out.unlink()


class TestHRVRecoveryFromRestDays:
    """Bug fix: recovery signature must use full daily HRV map, not just run days."""

    def _quality_run(self, date_str, hrv=55):
        return {
            "date": date_str,
            "workout_type": "tempo",
            "distance_miles": 6.0,
            "duration_min": 54.0,
            "pace_per_mile": 9.0,
            "avg_heart_rate": 155,
            "quality_zone_pct": 0.45,
            "hrv_last_night": hrv,
            "hrv_status": "LOW",
            "body_battery": 55,
            "readiness_score": 55,
            "sleep_hours": 6.5,
        }

    def _easy_run(self, date_str, hrv=66):
        return {
            "date": date_str,
            "workout_type": "easy",
            "distance_miles": 5.0,
            "duration_min": 50.0,
            "pace_per_mile": 10.0,
            "avg_heart_rate": 135,
            "quality_zone_pct": 0.05,
            "hrv_last_night": hrv,
            "hrv_status": "BALANCED",
            "body_battery": 70,
            "readiness_score": 65,
            "sleep_hours": 7.0,
        }

    def _build_scenario(self):
        """
        Quality sessions on Mar 1, 8, 15.
        Rest days (day+1) on Mar 2, 9, 16 — no run, HRV=68 (recovered).
        Next runs (day+3) on Mar 4, 11, 18 — HRV=68.
        Easy runs in Feb — no overlap with Mar recovery windows.

        Without fix: recovery = 3 (next RUN day is day+3).
        With fix:    recovery = 1 (rest day HRV on day+1 detected via all_hrv_by_date).
        """
        easy = [self._easy_run(f"2026-02-{i:02d}", hrv=65) for i in range(1, 21)]
        quality = [
            self._quality_run("2026-03-01", hrv=55),
            self._quality_run("2026-03-08", hrv=55),
            self._quality_run("2026-03-15", hrv=55),
        ]
        next_runs = [
            self._easy_run("2026-03-04", hrv=68),
            self._easy_run("2026-03-11", hrv=68),
            self._easy_run("2026-03-18", hrv=68),
        ]
        all_hrv_by_date = {
            # day+1 rest days (HRV recovered)
            "2026-03-02": 68.0, "2026-03-09": 68.0, "2026-03-16": 68.0,
            # day+3 run days
            "2026-03-04": 68.0, "2026-03-11": 68.0, "2026-03-18": 68.0,
        }
        return easy + quality + next_runs, all_hrv_by_date

    def test_recovery_uses_rest_day_hrv(self):
        """HRV rebounds on a rest day (not in joined_runs) should count as day+1 recovery."""
        from athlete_pattern_analyzer import analyze_patterns
        runs, all_hrv_by_date = self._build_scenario()
        result = analyze_patterns(runs, all_hrv_by_date=all_hrv_by_date)
        rec = result["recovery_signature"]
        assert rec["days_to_hrv_recovery"] == 1.0, (
            f"Expected 1-day recovery (rest day HRV available) but got "
            f"{rec['days_to_hrv_recovery']}"
        )

    def test_recovery_falls_back_to_run_days_when_no_hrv_map(self):
        """Without all_hrv_by_date, falls back to run-days-only lookup."""
        from athlete_pattern_analyzer import analyze_patterns
        runs, _ = self._build_scenario()
        # No all_hrv_by_date — rest days on Mar 2/9/16 are invisible
        result = analyze_patterns(runs)
        rec = result["recovery_signature"]
        # Next RUN day after each quality session is day+3 (Mar 4/11/18)
        assert rec["days_to_hrv_recovery"] == 3.0


class TestCacheFailureGuard:
    """Bug fix: run_analysis() must not overwrite valid patterns when cache is empty."""

    def test_does_not_overwrite_valid_patterns_on_empty_cache(self):
        """If activities=[] and out_path exists, the existing file is preserved."""
        from athlete_pattern_analyzer import run_analysis

        empty_cache = {"activities": [], "hrv_readings": [], "body_battery": [],
                       "training_readiness": [], "sleep_sessions": []}

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(empty_cache, f)
            cache_path = Path(f.name)

        # Pre-populate out_path with valid content
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Learned Athlete Patterns\n\nValid existing content.\n")
            out_path = Path(f.name)

        try:
            run_analysis(cache_path=cache_path, out_path=out_path)
            content = out_path.read_text()
            assert "Valid existing content." in content, (
                "run_analysis() overwrote valid patterns with empty-cache data"
            )
        finally:
            cache_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)

    def test_writes_new_file_when_no_existing_patterns(self):
        """If no existing file, run_analysis() still writes empty patterns on first run."""
        from athlete_pattern_analyzer import run_analysis

        empty_cache = {"activities": [], "hrv_readings": [], "body_battery": [],
                       "training_readiness": [], "sleep_sessions": []}

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(empty_cache, f)
            cache_path = Path(f.name)

        out_path = Path(tempfile.mktemp(suffix=".md"))  # does NOT exist yet

        try:
            patterns = run_analysis(cache_path=cache_path, out_path=out_path)
            assert "hrv_calibration" in patterns
            assert out_path.exists(), "Should write new file on first run even if empty"
        finally:
            cache_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)


class TestRunAnalysis:
    def test_run_analysis_with_empty_cache_does_not_crash(self):
        """run_analysis() with empty data and no existing file writes patterns without raising."""
        from athlete_pattern_analyzer import run_analysis
        empty_cache = {"activities": [], "hrv_readings": [], "body_battery": [],
                       "training_readiness": [], "sleep_sessions": []}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(empty_cache, f)
            cache_path = Path(f.name)
        # Use a path that does NOT exist yet — guard only preserves existing files
        out_path = Path(tempfile.mkdtemp()) / "patterns_new.md"
        try:
            patterns = run_analysis(cache_path=cache_path, out_path=out_path)
            assert "hrv_calibration" in patterns
            assert out_path.read_text()  # file was written on first run
        finally:
            cache_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)
