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

PROJECT_ROOT = Path(__file__).parent.parent
_HEALTH_CACHE = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
_OUTPUT_PATH = PROJECT_ROOT / "data" / "athlete" / "learned_patterns.md"

# ── Workout type labels ──────────────────────────────────────────────────────

_KEYWORD_MAP = [
    # (pattern, label)   — checked in order, first match wins
    (r'\beasy\b|\b easy \b|easy run', 'easy'),    # name contains "easy"
    (r'\blong run\b|\blong\b', 'long'),
    (r'tempo|threshold', 'tempo'),
    (r'interval|repeat|fartlek|x\d+\s*(min|sec|m\b)|strides', 'interval'),
    (r'marathon|half marathon|\bhm\b|race|5k|10k|15k', 'race'),
    # Coach shorthand: "30 min E", "45' E", "E$", " E " (standalone capital E)
    (r'\d+\s*(min|\')\s*[Ee]\b|[Ee]\s*$|\s[Ee]\s', 'easy'),
]

_RACE_DISTANCE_MIN_MI = 12.0   # anything >= this + high avg HR = race
_LONG_DISTANCE_MIN_MI = 9.0    # long run threshold
_LONG_DURATION_MIN_S  = 70 * 60

# Zone 3+ is "quality effort" territory for the athlete (threshold derived from zone data)
_QUALITY_ZONE_MIN = 3
_QUALITY_PCT_TEMPO    = 0.30   # >=30% in z3+ → sustained quality → tempo
_QUALITY_PCT_INTERVAL = 0.15   # >=15% in z3+ with intervals → interval
_EASY_PCT_MAX         = 0.12   # <12% in z3+ → easy

# Structured split: INTERVAL_ACTIVE is present AND INTERVAL_REST/RECOVERY present
_STRUCTURED_ACTIVE_TYPES = {"INTERVAL_ACTIVE"}
_STRUCTURED_REST_TYPES   = {"INTERVAL_REST", "INTERVAL_RECOVERY"}
_TEMPO_REPEAT_MIN_S      = 8 * 60   # active repeats >= 8min = tempo, shorter = interval


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


def analyze_patterns(
    joined_runs: List[Dict],
    all_hrv_by_date: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Compute 5 statistical patterns from joined run+recovery data.

    Returns a dict with keys:
      hrv_calibration, aerobic_efficiency, quality_predictors,
      recovery_signature, volume_tolerance
    """
    if not joined_runs:
        return {
            "hrv_calibration":   {"median_hrv": None, "hrv_range": None, "n_days": 0,
                                  "p25_hrv": None, "p75_hrv": None, "garmin_balanced_floor": None},
            "aerobic_efficiency": {"pace_at_hr": {}, "trend_note": None, "n_easy_runs": 0},
            "quality_predictors": {"hrv_median_good": None, "hrv_median_poor": None,
                                   "n_quality_sessions": 0},
            "recovery_signature": {"days_to_hrv_recovery": None,
                                   "n_quality_sessions_analysed": 0, "hrv_baseline_used": 65.0},
            "volume_tolerance":   {"sustainable_weekly_miles": None,
                                   "peak_week_miles": None, "n_weeks_analysed": 0},
        }

    easy_runs    = [r for r in joined_runs if r["workout_type"] == "easy"]
    long_runs    = [r for r in joined_runs if r["workout_type"] == "long"]
    quality_runs = [r for r in joined_runs if r["workout_type"] in ("tempo", "interval")]

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
    # Prefer the full daily HRV map (includes rest days) when provided; otherwise
    # fall back to run-day-only data (may overestimate recovery if rest days exist).
    hrv_by_date: Dict[str, float] = all_hrv_by_date if all_hrv_by_date is not None else {
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
    weekly: Dict[str, Dict] = defaultdict(lambda: {"miles": 0.0, "readiness": [], "hrv": []})
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
            f"When HRV >= {hrv_thresh} ms AND sleep >= {sleep_thresh} hrs AND "
            f"body battery >= {bb_thresh}: quality session hits target or better "
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
        f"- **Good session threshold:** <= {_fmt(qp.get('pace_cutoff_min_per_mile'), ' min/mi')}",
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
    if cache_path == _HEALTH_CACHE:
        cache = _load_data()
    else:
        cache = json.loads(cache_path.read_text())

    activities = [
        a for a in cache.get("activities", [])
        if a.get("activity_type", "").upper() in ("RUNNING", "TRAIL_RUNNING", "ROAD_RUNNING")
    ]

    hrv_map       = _build_date_map(cache.get("hrv_readings", []))
    bb_map        = _build_date_map(cache.get("body_battery", []))
    readiness_map = _build_date_map(cache.get("training_readiness", []))
    sleep_map     = _build_date_map(cache.get("sleep_sessions", []))

    # Build scalar HRV map covering ALL days (including rest days) so recovery
    # signature is measured from actual first recovery day, not first run day.
    all_hrv_by_date: Dict[str, float] = {
        k: v.get("last_night_avg") if isinstance(v, dict) else v
        for k, v in hrv_map.items()
        if (v.get("last_night_avg") if isinstance(v, dict) else v) is not None
    }

    joined = _join_runs_with_recovery(activities, hrv_map, bb_map, readiness_map, sleep_map)
    patterns = analyze_patterns(joined, all_hrv_by_date=all_hrv_by_date or None)

    # Guard: if no activities were found (empty/failed cache load) and valid
    # patterns already exist, preserve them rather than overwriting with n/a data.
    if not activities and out_path.exists():
        return patterns

    if activities:
        dates = sorted(a.get("date", "")[:10] for a in activities if a.get("date"))
        date_range = (dates[0], dates[-1]) if dates else ("", "")
    else:
        date_range = ("", "")

    write_patterns(patterns, out_path=out_path, n_runs=len(activities), date_range=date_range)
    return patterns
