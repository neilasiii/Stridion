# Athlete Pattern Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mine 15 months of Garmin data to discover Athlete's personal training patterns and feed them into the Brain's context packet so plan generation starts from observed reality, not generic VDOT tables.

**Architecture:** A single `src/athlete_pattern_analyzer.py` module does three things: (1) classifies unlabeled workouts using HR zones + split structure + name heuristics, (2) joins run data with same-day recovery metrics and computes 5 statistical patterns, (3) writes a structured `data/athlete/learned_patterns.md`. The Brain reads this file via a new `_load_athlete_patterns()` function wired into `build_context_packet()`. A daily hook keeps it fresh.

**Tech Stack:** Python stdlib only (statistics, collections, re) — no pandas/numpy needed given dataset size (~250 runs × ~470 days). Data sourced from `data/health/health_data_cache.json`.

---

## Context: Data Available

- **253 running activities** (Nov 2024 – Feb 2026), each with: `date`, `activity_name`, `duration_seconds`, `distance_miles`, `avg_heart_rate`, `pace_per_mile`, `hr_zones` (zones 1–5 with `time_in_zone_seconds`), `splits` (typed: INTERVAL_WARMUP, INTERVAL_ACTIVE, INTERVAL_REST, INTERVAL_RECOVERY, INTERVAL_COOLDOWN)
- **469 days** of: `hrv_readings[].{date, last_night_avg, status}`, `body_battery[].{date, latest_level}`, `training_readiness[].{date, score}`, `sleep_sessions[].{date, total_duration_minutes}`, `resting_hr_readings[]` (list of `[timestamp, bpm]`)
- 251/253 runs have `hr_zones`, 248/253 have `splits`

## Context: Key Classifications

Unlabeled runs (136/253) include easy-labeled-with-E shorthand ("30 min E", "40' E"), races (Local race series (specific names vary by athlete)), and pre-FinalSurge workouts. Classifier must handle all three.

## Context: Brain Integration Point

`memory/retrieval.py::build_context_packet()` (line 831) builds the dict the Brain LLM receives. Add `"athlete_patterns": _load_athlete_patterns()` to this dict. The function reads from `data/athlete/learned_patterns.md` — if file doesn't exist yet, returns `None` (Brain prompt handles missing key gracefully already).

---

## Task 1: Workout Classifier

**Files:**
- Create: `src/athlete_pattern_analyzer.py`
- Test: `tests/test_athlete_pattern_analyzer.py`

**Step 1: Write failing tests**

```python
# tests/test_athlete_pattern_analyzer.py
import sys
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
        assert classify_run(_run("Local Running Club", dist=13.25, avg_hr=172)) == "race"

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
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py -v
```
Expected: `ModuleNotFoundError: No module named 'athlete_pattern_analyzer'`

**Step 3: Implement `classify_run()`**

Create `src/athlete_pattern_analyzer.py`:

```python
"""
Athlete Pattern Analyzer

Classifies workouts and mines historical Garmin data to discover
Athlete's personal training patterns for use by the Brain LLM.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).parent.parent
_HEALTH_CACHE = _REPO_ROOT / "data" / "health" / "health_data_cache.json"
_OUTPUT_PATH = _REPO_ROOT / "data" / "athlete" / "learned_patterns.md"

# ── Workout type labels ──────────────────────────────────────────────────────

_KEYWORD_MAP = [
    # (pattern, label)   — checked in order, first match wins
    (r'\beast\b|\b easy \b|easy run|\blong run\b', 'easy'),    # name contains "easy"
    (r'\blong\b', 'long'),
    (r'tempo|threshold', 'tempo'),
    (r'interval|repeat|fartlek|x\d+\s*(min|sec|m\b)|strides', 'interval'),
    (r'marathon|half marathon|\bhm\b|race|5k|10k|15k', 'race'),
    # Brant shorthand: "30 min E", "45' E", "E$", " E " (standalone capital E)
    (r'\d+\s*(min|\')\s*[Ee]\b|[Ee]\s*$|\s[Ee]\s', 'easy'),
]

_RACE_DISTANCE_MIN_MI = 12.0   # anything ≥ this + high avg HR = race
_LONG_DISTANCE_MIN_MI = 9.0    # long run threshold
_LONG_DURATION_MIN_S  = 70 * 60

# Zone 3+ is "quality effort" territory for the athlete (threshold ~157 bpm per zone data)
_QUALITY_ZONE_MIN = 3
_QUALITY_PCT_TEMPO    = 0.30   # ≥30% in z3+ → sustained quality → tempo
_QUALITY_PCT_INTERVAL = 0.15   # ≥15% in z3+ with intervals → interval
_EASY_PCT_MAX         = 0.12   # <12% in z3+ → easy

# Structured split: INTERVAL_ACTIVE is present AND INTERVAL_REST/RECOVERY present
_STRUCTURED_ACTIVE_TYPES = {"INTERVAL_ACTIVE"}
_STRUCTURED_REST_TYPES   = {"INTERVAL_REST", "INTERVAL_RECOVERY"}
_TEMPO_REPEAT_MIN_S      = 8 * 60   # active repeats ≥ 8min = tempo, shorter = interval


def _zone_quality_pct(activity: Dict) -> float:
    """Fraction of total duration spent in zone 3 or above."""
    zones = activity.get("hr_zones") or []
    if not zones:
        return 0.0
    total = activity.get("duration_seconds") or sum(
        z.get("time_in_zone_seconds", 0) for z in zones
    )
    if not total:
        return 0.0
    quality_s = sum(
        z.get("time_in_zone_seconds", 0)
        for z in zones
        if z.get("zone_number", 0) >= _QUALITY_ZONE_MIN
    )
    return quality_s / total


def _has_structured_intervals(activity: Dict) -> Optional[str]:
    """
    Return 'interval' or 'tempo' if splits contain structured INTERVAL_ACTIVE repeats,
    else None.
    """
    splits = activity.get("splits") or []
    split_types = {s.get("type") for s in splits}
    if not (_STRUCTURED_ACTIVE_TYPES & split_types and _STRUCTURED_REST_TYPES & split_types):
        return None
    active_durations = [
        s.get("duration_seconds", 0)
        for s in splits
        if s.get("type") in _STRUCTURED_ACTIVE_TYPES
    ]
    if not active_durations:
        return None
    avg_active = statistics.mean(active_durations)
    return "tempo" if avg_active >= _TEMPO_REPEAT_MIN_S else "interval"


def classify_run(activity: Dict) -> str:
    """
    Classify a running activity as: easy | long | tempo | interval | race.

    Priority order:
    1. Name keywords (highest confidence for labeled workouts)
    2. Race distance heuristic (>= 12 mi + high HR)
    3. Structured split detection (INTERVAL_ACTIVE + REST → interval or tempo)
    4. HR zone percentage (sustained quality → tempo; low quality → easy/long)
    """
    name = (activity.get("activity_name") or "").lower()

    # 1. Name keywords
    for pattern, label in _KEYWORD_MAP:
        if re.search(pattern, name, re.IGNORECASE):
            # Sanity check: if name says "easy" but it's marathon distance → race
            if label == "easy" and activity.get("distance_miles", 0) > _RACE_DISTANCE_MIN_MI:
                return "race"
            return label

    dist = activity.get("distance_miles") or 0.0
    dur  = activity.get("duration_seconds") or 0.0
    hr   = activity.get("avg_heart_rate") or 0.0

    # 2. Race distance (unlabeled long-distance, high-HR)
    if dist >= _RACE_DISTANCE_MIN_MI and hr > 155:
        return "race"

    # 3. Structured splits
    structured = _has_structured_intervals(activity)
    if structured:
        return structured

    # 4. HR zone percentage
    q_pct = _zone_quality_pct(activity)
    if q_pct >= _QUALITY_PCT_TEMPO:
        return "tempo"
    if dist >= _LONG_DISTANCE_MIN_MI or dur >= _LONG_DURATION_MIN_S:
        return "long"
    return "easy"
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestClassifyRunByName \
                  tests/test_athlete_pattern_analyzer.py::TestClassifyRunByStructure \
                  tests/test_athlete_pattern_analyzer.py::TestClassifyRunByZones -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add src/athlete_pattern_analyzer.py tests/test_athlete_pattern_analyzer.py
git commit -m "feat(patterns): implement run classifier (keyword + structure + HR zones)"
```

---

## Task 2: Data Joiner — pair each run with its recovery metrics

**Files:**
- Modify: `src/athlete_pattern_analyzer.py` (add `_load_data()` and `_join_runs_with_recovery()`)
- Test: `tests/test_athlete_pattern_analyzer.py` (add `TestDataJoiner`)

**Step 1: Write failing tests**

```python
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
```

Add `import pytest` at the top of the test file.

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestDataJoiner -v
```
Expected: `ImportError: cannot import name '_join_runs_with_recovery'`

**Step 3: Implement `_load_data()` and `_join_runs_with_recovery()`**

Append to `src/athlete_pattern_analyzer.py`:

```python
# ── Data loading ─────────────────────────────────────────────────────────────

def _load_data() -> Dict:
    """Load health cache JSON. Returns empty dict if unavailable."""
    try:
        with open(_HEALTH_CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def _build_date_map(items: List, date_field: str = "date") -> Dict[str, Dict]:
    """Index a list of metric dicts by YYYY-MM-DD date."""
    m = {}
    for item in items:
        if isinstance(item, dict):
            key = str(item.get(date_field, ""))[:10]
        elif isinstance(item, list):
            key = str(item[0])[:10]
        else:
            continue
        if key:
            m[key] = item
    return m


def _join_runs_with_recovery(
    activities: List[Dict],
    hrv_map: Dict[str, Dict],
    bb_map: Dict[str, Dict],
    readiness_map: Dict[str, Dict],
    sleep_map: Dict[str, Dict],
) -> List[Dict]:
    """
    Join running activities with same-day recovery metrics.
    Returns one dict per run with all fields needed for pattern analysis.
    """
    results = []
    for a in activities:
        if a.get("activity_type", "").upper() not in (
            "RUNNING", "TRAIL_RUNNING", "ROAD_RUNNING"
        ):
            continue
        day = str(a.get("date", ""))[:10]

        hrv_rec  = hrv_map.get(day) or {}
        bb_rec   = bb_map.get(day) or {}
        rdy_rec  = readiness_map.get(day) or {}
        slp_rec  = sleep_map.get(day) or {}

        sleep_min = slp_rec.get("total_duration_minutes")

        results.append({
            "date":             day,
            "workout_type":     classify_run(a),
            "distance_miles":   a.get("distance_miles"),
            "duration_min":     (a.get("duration_seconds") or 0) / 60,
            "pace_per_mile":    a.get("pace_per_mile"),
            "avg_heart_rate":   a.get("avg_heart_rate"),
            "quality_zone_pct": _zone_quality_pct(a),
            # Same-day recovery (morning data — available before the run)
            "hrv_last_night":   hrv_rec.get("last_night_avg"),
            "hrv_status":       hrv_rec.get("status"),
            "body_battery":     bb_rec.get("latest_level") or bb_rec.get("charged"),
            "readiness_score":  rdy_rec.get("score"),
            "sleep_hours":      round(sleep_min / 60, 2) if sleep_min else None,
        })
    return results
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestDataJoiner -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add src/athlete_pattern_analyzer.py tests/test_athlete_pattern_analyzer.py
git commit -m "feat(patterns): data joiner — pair runs with same-day recovery metrics"
```

---

## Task 3: Pattern Analyzer — compute the 5 statistical patterns

**Files:**
- Modify: `src/athlete_pattern_analyzer.py` (add `analyze_patterns()`)
- Test: `tests/test_athlete_pattern_analyzer.py` (add `TestAnalyzePatterns`)

**Step 1: Write failing tests**

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestAnalyzePatterns -v
```
Expected: `ImportError: cannot import name 'analyze_patterns'`

**Step 3: Implement `analyze_patterns()`**

Append to `src/athlete_pattern_analyzer.py`:

```python
# ── Pattern analysis ─────────────────────────────────────────────────────────

def _safe_median(values):
    filtered = [v for v in values if v is not None]
    return round(statistics.median(filtered), 1) if len(filtered) >= 3 else None


def _safe_mean(values):
    filtered = [v for v in values if v is not None]
    return round(statistics.mean(filtered), 1) if len(filtered) >= 3 else None


def _bucket_pace_by_hr(runs: List[Dict], hr_step: int = 5) -> Dict[int, float]:
    """
    For easy runs, compute median pace per HR bucket (bucket = nearest 5bpm).
    Returns {hr_bucket: median_pace} e.g. {130: 10.25, 135: 10.05, ...}
    """
    buckets: Dict[int, List[float]] = defaultdict(list)
    for r in runs:
        hr = r.get("avg_heart_rate")
        pace = r.get("pace_per_mile")
        if hr and pace and r.get("workout_type") == "easy":
            bucket = round(hr / hr_step) * hr_step
            buckets[bucket].append(pace)
    return {
        hr: round(statistics.median(paces), 2)
        for hr, paces in sorted(buckets.items())
        if len(paces) >= 3
    }


def analyze_patterns(joined_runs: List[Dict]) -> Dict:
    """
    Compute 5 statistical patterns from joined run+recovery data.

    Returns a dict with keys:
      hrv_calibration, aerobic_efficiency, quality_predictors,
      recovery_signature, volume_tolerance
    """
    if not joined_runs:
        return {
            "hrv_calibration":   {"median_hrv": None, "hrv_range": None},
            "aerobic_efficiency": {"pace_at_hr": {}, "trend_note": None},
            "quality_predictors": {"hrv_median_good": None, "hrv_median_poor": None},
            "recovery_signature": {"days_to_hrv_recovery": None},
            "volume_tolerance":   {"sustainable_weekly_miles": None},
        }

    easy_runs    = [r for r in joined_runs if r["workout_type"] == "easy"]
    long_runs    = [r for r in joined_runs if r["workout_type"] == "long"]
    quality_runs = [r for r in joined_runs if r["workout_type"] in ("tempo", "interval")]
    race_runs    = [r for r in joined_runs if r["workout_type"] == "race"]

    # ── 1. HRV Calibration ───────────────────────────────────────────────────
    all_hrv = [r["hrv_last_night"] for r in joined_runs if r.get("hrv_last_night")]
    hrv_sorted = sorted(all_hrv)
    hrv_median = _safe_median(all_hrv)
    hrv_p25    = round(hrv_sorted[len(hrv_sorted) // 4], 1) if len(hrv_sorted) >= 4 else None
    hrv_p75    = round(hrv_sorted[3 * len(hrv_sorted) // 4], 1) if len(hrv_sorted) >= 4 else None

    # Garmin "BALANCED" boundary: minimum HRV that was tagged BALANCED
    balanced_hrvs = [
        r["hrv_last_night"] for r in joined_runs
        if r.get("hrv_status", "").upper() == "BALANCED" and r.get("hrv_last_night")
    ]
    garmin_balanced_floor = round(min(balanced_hrvs), 1) if balanced_hrvs else None

    hrv_calibration = {
        "median_hrv":          hrv_median,
        "hrv_range":           (round(min(all_hrv), 1), round(max(all_hrv), 1)) if all_hrv else None,
        "p25_hrv":             hrv_p25,
        "p75_hrv":             hrv_p75,
        "garmin_balanced_floor": garmin_balanced_floor,
        "n_days":              len(all_hrv),
    }

    # ── 2. Aerobic Efficiency (easy run pace-at-HR) ───────────────────────────
    pace_at_hr = _bucket_pace_by_hr(easy_runs + long_runs)

    # Fitness trend: compare first-third vs last-third of easy runs by date
    easy_by_date = sorted(easy_runs, key=lambda r: r["date"])
    trend_note = None
    if len(easy_by_date) >= 9:
        n3 = len(easy_by_date) // 3
        early = [r["pace_per_mile"] for r in easy_by_date[:n3] if r.get("pace_per_mile")]
        late  = [r["pace_per_mile"] for r in easy_by_date[-n3:] if r.get("pace_per_mile")]
        if early and late:
            early_med = statistics.median(early)
            late_med  = statistics.median(late)
            delta_pct = round(100 * (early_med - late_med) / early_med, 1)
            if delta_pct > 2:
                trend_note = f"Aerobic efficiency improved {delta_pct}% over the data window (same HR → faster pace)"
            elif delta_pct < -2:
                trend_note = f"Aerobic efficiency declined {abs(delta_pct)}% over the data window"
            else:
                trend_note = "Aerobic efficiency stable over the data window"

    aerobic_efficiency = {
        "pace_at_hr":  pace_at_hr,
        "trend_note":  trend_note,
        "n_easy_runs": len(easy_runs),
    }

    # ── 3. Quality Session Predictors ────────────────────────────────────────
    # Split quality runs into "good" (≤ median pace) and "poor" (> median pace)
    # Lower pace = faster = better for quality sessions
    quality_paces = [r["pace_per_mile"] for r in quality_runs if r.get("pace_per_mile")]
    quality_predictors: Dict = {
        "hrv_median_good": None,
        "hrv_median_poor": None,
        "sleep_median_good": None,
        "sleep_median_poor": None,
        "bb_median_good": None,
        "bb_median_poor": None,
        "good_pct_with_all_conditions_met": None,
        "n_quality_sessions": len(quality_runs),
    }

    if len(quality_paces) >= 4:
        pace_cutoff = statistics.median(quality_paces)
        good_q = [r for r in quality_runs if r.get("pace_per_mile") and r["pace_per_mile"] <= pace_cutoff]
        poor_q = [r for r in quality_runs if r.get("pace_per_mile") and r["pace_per_mile"] > pace_cutoff]

        quality_predictors.update({
            "pace_cutoff_min_per_mile": round(pace_cutoff, 2),
            "hrv_median_good":   _safe_median([r["hrv_last_night"] for r in good_q]),
            "hrv_median_poor":   _safe_median([r["hrv_last_night"] for r in poor_q]),
            "sleep_median_good": _safe_median([r["sleep_hours"] for r in good_q]),
            "sleep_median_poor": _safe_median([r["sleep_hours"] for r in poor_q]),
            "bb_median_good":    _safe_median([r["body_battery"] for r in good_q]),
            "bb_median_poor":    _safe_median([r["body_battery"] for r in poor_q]),
        })

        # Derive thresholds: conditions that predict good quality sessions
        hrv_thresh    = quality_predictors["hrv_median_good"]
        sleep_thresh  = quality_predictors["sleep_median_good"]
        bb_thresh     = quality_predictors["bb_median_good"]

        if hrv_thresh and sleep_thresh and bb_thresh and len(quality_runs) >= 6:
            met_and_good = sum(
                1 for r in quality_runs
                if (r.get("hrv_last_night") or 0) >= hrv_thresh
                and (r.get("sleep_hours") or 0) >= sleep_thresh
                and (r.get("body_battery") or 0) >= bb_thresh
                and r.get("pace_per_mile", float("inf")) <= pace_cutoff
            )
            met_total = sum(
                1 for r in quality_runs
                if (r.get("hrv_last_night") or 0) >= hrv_thresh
                and (r.get("sleep_hours") or 0) >= sleep_thresh
                and (r.get("body_battery") or 0) >= bb_thresh
            )
            if met_total > 0:
                quality_predictors["good_pct_with_all_conditions_met"] = round(
                    100 * met_and_good / met_total
                )

    # ── 4. Recovery Signature ────────────────────────────────────────────────
    # After each quality session: how many days until HRV returns to median?
    hrv_baseline = hrv_median or 65.0
    recovery_days_list = []
    quality_dates = sorted({r["date"] for r in quality_runs})
    hrv_by_date = {
        r["date"]: r["hrv_last_night"]
        for r in joined_runs
        if r.get("hrv_last_night")
    }

    for qdate in quality_dates:
        qd = datetime.strptime(qdate, "%Y-%m-%d").date()
        for n in range(1, 6):
            check_date = (qd + timedelta(days=n)).isoformat()
            hrv_val = hrv_by_date.get(check_date)
            if hrv_val and hrv_val >= hrv_baseline * 0.97:
                recovery_days_list.append(n)
                break

    recovery_signature = {
        "days_to_hrv_recovery": _safe_median(recovery_days_list),
        "n_quality_sessions_analysed": len(quality_dates),
        "hrv_baseline_used": hrv_baseline,
    }

    # ── 5. Volume Tolerance ───────────────────────────────────────────────────
    # Group runs by ISO week, compute weekly mileage, cross with that week's avg readiness
    weekly: Dict[str, Dict] = defaultdict(lambda: {"miles": 0.0, "readiness": [], "hrv": [], "rhr": []})
    for r in joined_runs:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            week_key = d.strftime("%Y-W%W")
        except Exception:
            continue
        weekly[week_key]["miles"] += r.get("distance_miles") or 0.0
        if r.get("readiness_score"):
            weekly[week_key]["readiness"].append(r["readiness_score"])
        if r.get("hrv_last_night"):
            weekly[week_key]["hrv"].append(r["hrv_last_night"])

    week_summaries = [
        {
            "week": k,
            "miles": round(v["miles"], 1),
            "avg_readiness": _safe_mean(v["readiness"]),
            "avg_hrv": _safe_mean(v["hrv"]),
        }
        for k, v in weekly.items()
        if v["miles"] >= 10  # exclude weeks with too little data (travel, sick)
    ]

    # Find mileage threshold where readiness starts declining
    sustainable_miles = None
    if len(week_summaries) >= 8:
        with_readiness = [w for w in week_summaries if w["avg_readiness"]]
        if with_readiness:
            high_vol = sorted(with_readiness, key=lambda w: w["miles"])
            # Upper third of weeks by volume
            n3 = max(1, len(high_vol) // 3)
            low_vol_rdy  = _safe_mean([w["avg_readiness"] for w in high_vol[:n3]])
            high_vol_rdy = _safe_mean([w["avg_readiness"] for w in high_vol[-n3:]])
            all_miles = sorted(w["miles"] for w in high_vol)
            if low_vol_rdy and high_vol_rdy and high_vol_rdy < low_vol_rdy - 5:
                # Readiness drops in high-volume weeks — find the boundary
                sustainable_miles = round(statistics.median(all_miles[n3:n3*2]), 1)

    peak_week = max((w["miles"] for w in week_summaries), default=None)
    volume_tolerance = {
        "sustainable_weekly_miles": sustainable_miles,
        "peak_week_miles":          round(peak_week, 1) if peak_week else None,
        "n_weeks_analysed":         len(week_summaries),
    }

    return {
        "hrv_calibration":    hrv_calibration,
        "aerobic_efficiency": aerobic_efficiency,
        "quality_predictors": quality_predictors,
        "recovery_signature": recovery_signature,
        "volume_tolerance":   volume_tolerance,
    }
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestAnalyzePatterns -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add src/athlete_pattern_analyzer.py tests/test_athlete_pattern_analyzer.py
git commit -m "feat(patterns): compute HRV calibration, aerobic efficiency, quality predictors, recovery, volume tolerance"
```

---

## Task 4: Pattern Writer — generate `data/athlete/learned_patterns.md`

**Files:**
- Modify: `src/athlete_pattern_analyzer.py` (add `write_patterns()` and `run_analysis()`)
- Test: `tests/test_athlete_pattern_analyzer.py` (add `TestWritePatterns`)

**Step 1: Write failing tests**

```python
import tempfile
from pathlib import Path

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
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestWritePatterns -v
```
Expected: `ImportError: cannot import name 'write_patterns'`

**Step 3: Implement `write_patterns()` and `run_analysis()`**

Append to `src/athlete_pattern_analyzer.py`:

```python
# ── Output writer ────────────────────────────────────────────────────────────

def write_patterns(
    patterns: Dict,
    out_path: Path = _OUTPUT_PATH,
    n_runs: int = 0,
    date_range: Tuple[str, str] = ("", ""),
) -> None:
    """Write discovered patterns to a markdown file the Brain can read."""
    hrv  = patterns["hrv_calibration"]
    aero = patterns["aerobic_efficiency"]
    qp   = patterns["quality_predictors"]
    rec  = patterns["recovery_signature"]
    vol  = patterns["volume_tolerance"]

    def _fmt(v, unit="", fallback="n/a"):
        return f"{v}{unit}" if v is not None else fallback

    # Aerobic efficiency table
    pace_rows = "\n".join(
        f"| {hr} bpm | {pace:.2f} min/mi |"
        for hr, pace in sorted(aero["pace_at_hr"].items())
    ) if aero["pace_at_hr"] else "| (insufficient data) | |"

    # Quality predictor conditions
    hrv_thresh   = qp.get("hrv_median_good")
    sleep_thresh = qp.get("sleep_median_good")
    bb_thresh    = qp.get("bb_median_good")
    good_pct     = qp.get("good_pct_with_all_conditions_met")

    conditions_text = ""
    if hrv_thresh and sleep_thresh and bb_thresh:
        conditions_text = (
            f"When HRV ≥ {hrv_thresh} ms AND sleep ≥ {sleep_thresh} hrs AND "
            f"body battery ≥ {bb_thresh}: quality session hits target or better "
            + (f"{good_pct}% of the time." if good_pct else "(insufficient data to compute rate).")
        )
    else:
        conditions_text = "Insufficient quality session data to compute predictor thresholds."

    lines = [
        "# Learned Athlete Patterns",
        "",
        f"_Last updated: {date.today().isoformat()} | "
        f"Derived from {n_runs} runs + recovery data ({date_range[0]} – {date_range[1]})_",
        "",
        "---",
        "",
        "## HRV Calibration",
        f"- **Baseline (median):** {_fmt(hrv['median_hrv'], ' ms')} "
        f"| Range: {_fmt(hrv['hrv_range'])} over {hrv['n_days']} days",
        f"- **25th–75th percentile:** {_fmt(hrv['p25_hrv'], ' ms')} – {_fmt(hrv['p75_hrv'], ' ms')}",
        f"- **Garmin BALANCED floor (personal):** {_fmt(hrv['garmin_balanced_floor'], ' ms')} "
        f"(days Garmin tags BALANCED go no lower than this)",
        "",
        "## Aerobic Efficiency (Easy-Run Pace at Heart Rate)",
        "",
        "| Avg HR | Median Pace |",
        "|--------|-------------|",
        pace_rows,
        "",
        f"_{aero['trend_note'] or 'Trend data unavailable.'} ({aero['n_easy_runs']} easy runs analysed)_",
        "",
        "## Quality Session Predictors",
        f"- **Sessions analysed:** {qp['n_quality_sessions']}",
        f"- **Good session threshold:** ≤ {_fmt(qp.get('pace_cutoff_min_per_mile'), ' min/mi')}",
        f"- **HRV on good days:** {_fmt(qp.get('hrv_median_good'), ' ms')} median "
        f"(vs {_fmt(qp.get('hrv_median_poor'), ' ms')} on poor days)",
        f"- **Sleep on good days:** {_fmt(qp.get('sleep_median_good'), ' hrs')} median "
        f"(vs {_fmt(qp.get('sleep_median_poor'), ' hrs')} on poor days)",
        f"- **Body battery on good days:** {_fmt(qp.get('bb_median_good'))} "
        f"(vs {_fmt(qp.get('bb_median_poor'))} on poor days)",
        f"- **Combined predictor:** {conditions_text}",
        "",
        "## Recovery Signature",
        f"- **Days for HRV to recover after quality session:** "
        f"{_fmt(rec['days_to_hrv_recovery'])} days (median, baseline = {rec['hrv_baseline_used']} ms)",
        f"- **Quality sessions analysed:** {rec['n_quality_sessions_analysed']}",
        f"- **Implication:** Schedule quality sessions at least "
        f"{int(rec['days_to_hrv_recovery'] or 2)} full rest/easy days apart.",
        "",
        "## Volume Tolerance",
        f"- **Sustainable weekly volume:** "
        f"~{_fmt(vol['sustainable_weekly_miles'], ' miles/week')} "
        f"(recovery metrics stable below this)",
        f"- **Peak week in data:** {_fmt(vol['peak_week_miles'], ' miles')}",
        f"- **Weeks analysed:** {vol['n_weeks_analysed']}",
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))


def run_analysis(cache_path: Path = _HEALTH_CACHE, out_path: Path = _OUTPUT_PATH) -> Dict:
    """
    Full pipeline: load data → classify → join → analyze → write.
    Returns the patterns dict.
    """
    cache = _load_data() if cache_path == _HEALTH_CACHE else json.loads(cache_path.read_text())

    activities = [
        a for a in cache.get("activities", [])
        if a.get("activity_type", "").upper() in ("RUNNING", "TRAIL_RUNNING", "ROAD_RUNNING")
    ]

    hrv_map      = _build_date_map(cache.get("hrv_readings", []))
    bb_map       = _build_date_map(cache.get("body_battery", []))
    readiness_map = _build_date_map(cache.get("training_readiness", []))
    sleep_map    = _build_date_map(cache.get("sleep_sessions", []))

    joined = _join_runs_with_recovery(activities, hrv_map, bb_map, readiness_map, sleep_map)
    patterns = analyze_patterns(joined)

    if activities:
        dates = sorted(a.get("date", "")[:10] for a in activities if a.get("date"))
        date_range = (dates[0], dates[-1]) if dates else ("", "")
    else:
        date_range = ("", "")

    write_patterns(patterns, out_path=out_path, n_runs=len(activities), date_range=date_range)
    return patterns
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestWritePatterns -v
```
Expected: all PASS

**Step 5: Commit**

```bash
git add src/athlete_pattern_analyzer.py tests/test_athlete_pattern_analyzer.py
git commit -m "feat(patterns): write_patterns() and run_analysis() — full pipeline to learned_patterns.md"
```

---

## Task 5: Wire into Brain context packet

**Files:**
- Modify: `memory/retrieval.py` (add `_load_athlete_patterns()`, add key to `build_context_packet()`)
- Test: `tests/test_retrieval.py` (add one test for the new key)

**Context:** `build_context_packet()` is at line 831. The packet dict is constructed around line 941. The function reads from `_load_health_cache()` and several helper functions. Add `athlete_patterns` as a top-level key — value is a short string summary from `learned_patterns.md`, or `None` if the file doesn't exist yet.

**Step 1: Write failing test**

```python
# In tests/test_retrieval.py — add to existing file
def test_context_packet_has_athlete_patterns_key():
    """build_context_packet() always includes athlete_patterns key (may be None)."""
    from memory.retrieval import build_context_packet
    import tempfile, os
    # Run with empty DB and no patterns file — should not crash
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
    try:
        packet = build_context_packet(db_path=db_path)
        assert "athlete_patterns" in packet  # key exists even if value is None
    finally:
        os.unlink(db_path)
```

**Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_retrieval.py::test_context_packet_has_athlete_patterns_key -v
```
Expected: `AssertionError` (key not in packet)

**Step 3: Implement `_load_athlete_patterns()` in `memory/retrieval.py`**

Find the imports at the top of `memory/retrieval.py` and add after them (or near other file-load helpers):

```python
_ATHLETE_PATTERNS_PATH = _PROJECT_ROOT / "data" / "athlete" / "learned_patterns.md"

def _load_athlete_patterns() -> Optional[str]:
    """
    Load learned athlete patterns from data/athlete/learned_patterns.md.
    Returns the file content as a string, or None if the file doesn't exist yet.
    Run `coach analyze-patterns` to generate this file.
    """
    if _ATHLETE_PATTERNS_PATH.exists():
        try:
            return _ATHLETE_PATTERNS_PATH.read_text()
        except Exception:
            pass
    return None
```

Then in `build_context_packet()`, find where the packet dict is assembled and add the new key:

```python
# Add to the packet dict (near line 941, alongside other top-level keys):
"athlete_patterns": _load_athlete_patterns(),
```

**Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_retrieval.py::test_context_packet_has_athlete_patterns_key -v
```
Expected: PASS

**Step 5: Run full retrieval test suite to confirm nothing broken**

```bash
python3 -m pytest tests/test_retrieval.py -v
```
Expected: all PASS

**Step 6: Commit**

```bash
git add memory/retrieval.py tests/test_retrieval.py
git commit -m "feat(patterns): wire athlete_patterns into Brain context packet"
```

---

## Task 6: Daily refresh hook + CLI command

**Files:**
- Modify: `agent/runner.py` — call `run_analysis()` in `run_daily_deep()`
- Modify: `cli/coach.py` — add `analyze-patterns` subcommand
- Test: `tests/test_athlete_pattern_analyzer.py` — add `TestRunAnalysis` integration test

**Context:** `agent/runner.py::run_daily_deep()` runs at 4am daily (from line 229). It already handles plan staleness checks. Add pattern refresh here — runs once per day using cached data (no network I/O). `cli/coach.py` uses argparse subcommands; add `analyze-patterns` following the same pattern as existing commands.

**Step 1: Write failing integration test**

```python
class TestRunAnalysis:
    def test_run_analysis_with_empty_cache_does_not_crash(self):
        """run_analysis() with empty data writes a valid file without raising."""
        import tempfile
        from athlete_pattern_analyzer import run_analysis
        empty_cache = {"activities": [], "hrv_readings": [], "body_battery": [],
                       "training_readiness": [], "sleep_sessions": []}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(empty_cache, f)
            cache_path = Path(f.name)
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            out_path = Path(f.name)
        try:
            patterns = run_analysis(cache_path=cache_path, out_path=out_path)
            assert "hrv_calibration" in patterns
            assert out_path.read_text()  # file was written
        finally:
            cache_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)
```

**Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestRunAnalysis -v
```
Expected: `ImportError` or test failure — the function may exist but test path is new

**Step 3: Wire into `agent/runner.py::run_daily_deep()`**

In `agent/runner.py`, add after existing imports:

```python
from src.athlete_pattern_analyzer import run_analysis as _refresh_patterns
```

In `run_daily_deep()` (around line 229), add at the end of the function body:

```python
# Refresh learned athlete patterns from latest Garmin data (no network I/O)
try:
    _refresh_patterns()
    logger.info("[daily_deep] Athlete patterns refreshed")
except Exception as exc:
    logger.warning(f"[daily_deep] Pattern refresh failed: {exc}")
```

**Step 4: Add `analyze-patterns` to `cli/coach.py`**

Find where subcommands are registered in `cli/coach.py` (look for `add_parser` calls). Add:

```python
# In the subparsers section:
p_patterns = subparsers.add_parser(
    "analyze-patterns",
    help="Mine historical Garmin data to discover athlete-specific training patterns",
)
p_patterns.set_defaults(cmd="analyze-patterns")
```

In the command dispatch section (where `args.cmd` is checked), add:

```python
elif args.cmd == "analyze-patterns":
    import sys as _sys
    _sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from athlete_pattern_analyzer import run_analysis
    patterns = run_analysis()
    hrv = patterns["hrv_calibration"]
    aero = patterns["aerobic_efficiency"]
    rec = patterns["recovery_signature"]
    vol = patterns["volume_tolerance"]
    print(f"✓ Patterns written to data/athlete/learned_patterns.md")
    print(f"  HRV baseline: {hrv['median_hrv']} ms (range {hrv['hrv_range']})")
    print(f"  Aerobic efficiency: {len(aero['pace_at_hr'])} HR buckets computed")
    print(f"  Recovery signature: {rec['days_to_hrv_recovery']} days to HRV recovery")
    print(f"  Volume tolerance: ~{vol['sustainable_weekly_miles']} mi/week sustainable")
```

**Step 5: Run test to verify it passes**

```bash
python3 -m pytest tests/test_athlete_pattern_analyzer.py::TestRunAnalysis -v
```
Expected: PASS

**Step 6: Smoke test the CLI command**

```bash
python3 cli/coach.py analyze-patterns
```
Expected output:
```
✓ Patterns written to data/athlete/learned_patterns.md
  HRV baseline: XX ms (range (...))
  Aerobic efficiency: N HR buckets computed
  Recovery signature: X days to HRV recovery
  Volume tolerance: ~XX mi/week sustainable
```

Verify file exists:
```bash
head -30 data/athlete/learned_patterns.md
```

**Step 7: Run full test suite**

```bash
python3 -m pytest tests/ -v --ignore=tests/test_ai_call.py --ignore=tests/test_location_fix.py \
    --ignore=tests/test_location_geocoding.py --ignore=tests/test_session.py
```
Expected: all pass (336+ tests)

**Step 8: Commit**

```bash
git add src/athlete_pattern_analyzer.py tests/test_athlete_pattern_analyzer.py \
        agent/runner.py cli/coach.py
git commit -m "feat(patterns): daily refresh hook + analyze-patterns CLI command"
```

---

## Final: Run analysis and push

```bash
# Generate patterns from real data
python3 cli/coach.py analyze-patterns

# Commit the generated file
git add data/athlete/learned_patterns.md
git commit -m "data: initial learned athlete patterns from 15 months of Garmin data"

# Push everything
git push
```

---

## What Gets Built

After this plan executes:

1. **`src/athlete_pattern_analyzer.py`** — classifier + analyzer + writer (stdlib only, ~300 lines)
2. **`tests/test_athlete_pattern_analyzer.py`** — full test suite for all components
3. **`data/athlete/learned_patterns.md`** — Athlete's personal patterns in markdown, auto-refreshed daily
4. **`memory/retrieval.py`** — Brain context packet now includes `athlete_patterns` key
5. **`agent/runner.py`** — Pattern refresh runs at 4am via `run_daily_deep()`
6. **`cli/coach.py`** — `coach analyze-patterns` command to trigger manually

The Brain will now know, for example: "Athlete's HRV baseline is 67ms; quality sessions fall short when HRV < 57ms; schedule quality sessions ≥2 days apart; aerobic efficiency improved 6% this block" — all derived from 15 months of real data, refreshed daily.
