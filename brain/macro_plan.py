"""
Brain Macro Planner — LLM-powered long-range periodization block.

Public API:
    generate_macro_plan(context_packet, force=False, db_path=None) -> MacroPlan
    validate_macro_plan(plan: MacroPlan, *, post_race_cap_miles=None,
                        post_race_recovery_weeks=0) -> MacroValidationResult

The macro plan is a rail, not a cage: it gives the weekly planner a
deterministic arc (phase, volume target, intensity budget, paces) to
execute, while allowing deviation when readiness or constraints demand it.

Two modes:
  race_targeted  — future race in upcoming_races.md → base → quality →
                   race_specific → taper toward race date
  base_block     — no future race → open-ended base → quality focused on
                   marathon fitness, no race_specific, no taper, 12 weeks

Validation is always run before set_active_macro_plan() is called.
On failure: plan inserted as status="validation_failed" for audit, then
MacroValidationError is raised.

LLM call happens OUTSIDE the DB transaction (transaction safety rule).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import MacroPlan, MacroWeek, MacroModeT, RaceDistanceT
from .llm import call_llm as _call_llm, _try_strict_extract, _brace_search_last, _JSON_FENCE_RE

log = logging.getLogger("brain.macro_plan")

MAX_TOKENS_MACRO = 4096

# Haiku is 5-10× faster than Sonnet for structured JSON generation — the macro
# plan is a template-filling task (apply rules, output week objects), not a
# complex reasoning task, so speed wins here.
_MACRO_MODEL = "claude-haiku-4-5-20251001"

# Number of days after a short race during which quality sessions are prohibited.
# Applies when a race-level effort < 10 mi is detected (5k, 10k, etc.).
POST_RACE_SHORT_NO_QUALITY_DAYS: int = 4

# Keywords (lowercase) that indicate a race-level effort in an activity name.
# Used by _detect_post_race_recovery to identify short races by name when
# distance is absent or < 10 miles.
_RACE_KEYWORDS: frozenset = frozenset([
    "race", "5k", "10k", "5 km", "10 km", "half", "marathon", "hm",
])

# ── Validation ─────────────────────────────────────────────────────────────────


class MacroValidationError(Exception):
    def __init__(self, errors: List[str]) -> None:
        self.errors = errors

    def __str__(self) -> str:
        return "Macro plan validation failed:\n" + "\n".join(
            f"  - {e}" for e in self.errors
        )


@dataclass
class MacroValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)


def validate_macro_plan(
    plan: MacroPlan,
    *,
    post_race_cap_miles: Optional[float] = None,
    post_race_recovery_weeks: int = 0,
    short_race_no_quality_days: int = 0,
) -> MacroValidationResult:
    """
    Run all structural and training-science invariants.

    Args:
        plan: The MacroPlan to validate.
        post_race_cap_miles: If set, Week 1 (and recovery weeks) must not
            exceed this volume. Provided by _extract_macro_inputs() when a
            recent race-level effort is detected.
        post_race_recovery_weeks: How many weeks must obey recovery constraints.
            Default 0 means post-race check is skipped even if cap is set.
        short_race_no_quality_days: When > 0, Week 1 must have
            quality_sessions_allowed == 0 (short-race no-quality window).
            Does NOT enforce a volume cap (use post_race_cap_miles for that).

    Returns MacroValidationResult(ok=True) on success, or
    MacroValidationResult(ok=False, errors=[...]) with human-readable
    errors (each ≤120 chars).
    """
    errors: List[str] = []
    weeks = plan.weeks

    # 1. Week count matches declared total
    if len(weeks) != plan.total_weeks:
        errors.append(
            f"week count mismatch: expected {plan.total_weeks}, got {len(weeks)}"
        )

    # 2. start_week must be a Sunday; each week_start must be a Sunday and contiguous
    plan_start: Optional[date] = None
    try:
        plan_start = date.fromisoformat(plan.start_week)
        if plan_start.weekday() != 6:  # 6 = Sunday
            errors.append(
                f"start_week {plan.start_week} is not a Sunday "
                f"(weekday={plan_start.weekday()})"
            )
    except ValueError:
        errors.append(f"start_week '{plan.start_week}' is not a valid ISO date")

    for i, w in enumerate(weeks):
        if w.week_number != i + 1:
            errors.append(f"week {i+1} has week_number={w.week_number}")
        try:
            this_ws = date.fromisoformat(w.week_start)
            if this_ws.weekday() != 6:
                errors.append(
                    f"week {w.week_number} start {w.week_start} is not a Sunday"
                )
        except ValueError:
            errors.append(
                f"week {w.week_number} start '{w.week_start}' is not a valid ISO date"
            )
            continue
        if i > 0:
            try:
                prev_ws = date.fromisoformat(weeks[i - 1].week_start)
                if this_ws != prev_ws + timedelta(days=7):
                    errors.append(
                        f"week {w.week_number} start {w.week_start} "
                        f"not contiguous with prior week"
                    )
            except ValueError:
                pass  # prior week start already reported above

    # 3. Full span check: last week_start must equal start_week + 7*(total_weeks-1)
    if plan_start is not None and len(weeks) == plan.total_weeks and weeks:
        expected_last = plan_start + timedelta(days=7 * (plan.total_weeks - 1))
        try:
            actual_last = date.fromisoformat(weeks[-1].week_start)
            if actual_last != expected_last:
                errors.append(
                    f"span mismatch: last week_start {weeks[-1].week_start} "
                    f"should be {expected_last.isoformat()} "
                    f"(start_week + 7×{plan.total_weeks - 1})"
                )
        except ValueError:
            pass  # already reported

    # 4. Phase progression — no regression allowed
    valid_race_seq = ["base", "quality", "race_specific", "taper"]
    valid_base_seq = ["base", "quality"]
    allowed_phases = valid_race_seq if plan.mode == "race_targeted" else valid_base_seq
    prev_phase_rank = -1
    for w in weeks:
        if w.phase not in allowed_phases:
            errors.append(
                f"week {w.week_number}: phase '{w.phase}' "
                f"not allowed in mode '{plan.mode}'"
            )
            continue
        rank = allowed_phases.index(w.phase)
        if rank < prev_phase_rank:
            errors.append(
                f"week {w.week_number}: phase regression '{w.phase}' "
                f"after '{allowed_phases[prev_phase_rank]}'"
            )
        prev_phase_rank = rank

    # 5. Taper length + position (race_targeted only)
    if plan.mode == "race_targeted":
        expected_taper = 2 if plan.race_distance == "marathon" else 1
        taper_weeks = [w for w in weeks if w.phase == "taper"]
        if len(taper_weeks) < expected_taper:
            errors.append(
                f"taper too short: {len(taper_weeks)} week(s), "
                f"expected {expected_taper} for race_distance='{plan.race_distance}'"
            )
        # Taper must be the final N weeks
        if len(weeks) >= expected_taper:
            tail_phases = [w.phase for w in weeks[-expected_taper:]]
            if any(p != "taper" for p in tail_phases):
                errors.append(
                    f"taper must be the last {expected_taper} week(s) of the block; "
                    f"found {tail_phases} in tail"
                )

    # 6. No taper/race_specific in base_block
    if plan.mode == "base_block":
        bad = [w for w in weeks if w.phase in ("taper", "race_specific")]
        if bad:
            errors.append(
                f"base_block must not contain taper/race_specific phases "
                f"(found at weeks {[w.week_number for w in bad]})"
            )

    # 7. Volume ramp constraints (base phase only)
    for w in weeks:
        if not (w.volume_floor_miles <= w.volume_target_miles <= w.volume_ceiling_miles):
            errors.append(
                f"week {w.week_number}: invalid volume band "
                f"({w.volume_floor_miles:.1f} <= {w.volume_target_miles:.1f} <= {w.volume_ceiling_miles:.1f} violated)"
            )

    base_vols = [
        (w.week_number, w.volume_target_miles, w.volume_ceiling_miles)
        for w in weeks
        if w.phase == "base"
    ]
    consec_big_ramps = 0
    for i in range(1, len(base_vols)):
        prev_week_num = base_vols[i - 1][0]
        curr_week_num = base_vols[i][0]
        # Skip ramp check for non-consecutive base weeks (quality block in between).
        # Comparing e.g. week 6 base to week 11 base after quality weeks 7-10
        # would produce a false positive since quality drove volume up legitimately.
        if curr_week_num != prev_week_num + 1:
            consec_big_ramps = 0
            continue
        prev_vol = base_vols[i - 1][1]
        curr_vol = base_vols[i][1]
        prev_ceil = base_vols[i - 1][2]
        curr_ceil = base_vols[i][2]
        if prev_vol > 0:
            pct = (curr_vol - prev_vol) / prev_vol
            if pct > 0.10 + 1e-9:  # epsilon for float precision at exactly 10%
                errors.append(
                    f"week {base_vols[i][0]}: volume ramp {pct:.0%} exceeds 10% cap"
                )
            consec_big_ramps = consec_big_ramps + 1 if pct > 0.07 else 0
            if consec_big_ramps > 2:
                errors.append(
                    f"week {base_vols[i][0]}: 3+ consecutive ramps >7%"
                )
        if prev_ceil > 0:
            ceil_pct = (curr_ceil - prev_ceil) / prev_ceil
            if ceil_pct > 0.12 + 1e-9:
                errors.append(
                    f"week {base_vols[i][0]}: ceiling ramp {ceil_pct:.0%} exceeds 12% cap"
                )

    # 8. Zero/low volume rules
    for w in weeks:
        if w.volume_target_miles == 0 and w.key_workout_type != "rest":
            errors.append(
                f"week {w.week_number}: zero volume but "
                f"key_workout_type='{w.key_workout_type}' (must be 'rest')"
            )
        if w.volume_target_miles < 6 and w.quality_sessions_allowed > 0:
            errors.append(
                f"week {w.week_number}: volume {w.volume_target_miles:.1f}mi < 6 "
                f"but quality_sessions_allowed={w.quality_sessions_allowed} (must be 0)"
            )

    # 9. long_run_max_min sanity (≤ 62% of weekly volume at ~10 min/mi, general cap)
    for w in weeks:
        if w.volume_target_miles > 0:
            volume_mins_approx = w.volume_target_miles * 10
            if w.long_run_max_min > volume_mins_approx * 0.62:
                errors.append(
                    f"week {w.week_number}: long_run_max_min {w.long_run_max_min} "
                    f"exceeds 62% of ~{volume_mins_approx:.0f}min weekly volume"
                )

    # 10. Rationale consistency — warn if "from 0" language when Week 1 > 5 mi
    if weeks and plan.weeks[0].volume_target_miles > 5.0:
        if re.search(r"\bfrom\s+0\b", plan.rationale, re.IGNORECASE):
            errors.append(
                "rationale mentions 'from 0' but Week 1 volume > 5 mi "
                "(misleading — reference actual Week 1 target volume)"
            )

    # 11. Early-block long run cap (weeks 1-4): ≤ 50% of weekly volume
    for w in weeks:
        if 1 <= w.week_number <= 4 and w.volume_target_miles > 0:
            vol_mins = w.volume_target_miles * 10
            if w.long_run_max_min > vol_mins * 0.50 + 0.5:  # 0.5 min tolerance
                errors.append(
                    f"week {w.week_number}: early-block LR cap exceeded — "
                    f"long_run_max_min {w.long_run_max_min} exceeds 50% of "
                    f"~{vol_mins:.0f}min weekly volume"
                )

    # 12. Quality ramp — no 0→2 jump; no simultaneous quality + LR spike
    for i in range(1, len(weeks)):
        prev_q  = weeks[i - 1].quality_sessions_allowed
        curr_q  = weeks[i].quality_sessions_allowed
        prev_lr = weeks[i - 1].long_run_max_min
        curr_lr = weeks[i].long_run_max_min
        q_jump  = curr_q - prev_q
        lr_pct  = (curr_lr - prev_lr) / prev_lr if prev_lr > 0 else 0.0
        if prev_q == 0 and curr_q == 2:
            errors.append(
                f"week {weeks[i].week_number}: quality jumped 0→2 in one step "
                f"(introduce gradually — start with 1 quality session)"
            )
        if q_jump > 0 and lr_pct > 0.10 + 1e-9:
            errors.append(
                f"week {weeks[i].week_number}: simultaneous quality increase "
                f"(+{q_jump} session) and LR cap increase "
                f"({lr_pct:.0%}) — too much stress spike"
            )

    # 13. End-of-block stress (base_block only)
    if plan.mode == "base_block" and weeks:
        final    = weeks[-1]
        peak_vol = max((w.volume_target_miles for w in weeks), default=0.0)
        if (
            final.volume_target_miles >= peak_vol - 0.1
            and final.intensity_budget == "high"
            and final.quality_sessions_allowed == 2
        ):
            errors.append(
                f"week {final.week_number}: base_block ends at peak volume "
                f"({final.volume_target_miles:.1f}mi) with high intensity + "
                f"2 quality sessions — unsustainable block finish; "
                f"reduce volume or intensity in final week"
            )

    # 14. Post-race recovery constraints (only when post_race_cap_miles is provided)
    if post_race_cap_miles is not None and weeks:
        n_recovery = max(1, post_race_recovery_weeks) if post_race_recovery_weeks else 1
        for rw in weeks[:n_recovery]:
            if rw.volume_ceiling_miles > post_race_cap_miles * 1.15 + 0.5:
                errors.append(
                    f"week {rw.week_number}: post-race recovery required — "
                    f"ceiling {rw.volume_ceiling_miles:.1f}mi exceeds cap "
                    f"{post_race_cap_miles:.1f}mi (with 15% slack)"
                )
            if rw.quality_sessions_allowed > 0:
                errors.append(
                    f"week {rw.week_number}: post-race recovery required — "
                    f"quality_sessions_allowed must be 0, "
                    f"got {rw.quality_sessions_allowed}"
                )
            if rw.intensity_budget not in ("none", "low"):
                errors.append(
                    f"week {rw.week_number}: post-race recovery required — "
                    f"intensity_budget must be 'none' or 'low', "
                    f"got '{rw.intensity_budget}'"
                )

    # 15. Short-race no-quality window (short_race_no_quality_days > 0)
    # A recent short race (5k/10k/etc.) requires no quality in Week 1.
    # Volume cap is NOT enforced here (short races don't need mileage reduction).
    if short_race_no_quality_days > 0 and weeks:
        rw = weeks[0]
        if rw.quality_sessions_allowed > 0:
            errors.append(
                f"week {rw.week_number}: short-race no-quality window "
                f"({short_race_no_quality_days} days) — "
                f"quality_sessions_allowed must be 0, "
                f"got {rw.quality_sessions_allowed}"
            )

    return MacroValidationResult(ok=len(errors) == 0, errors=errors)


# ── Race detection ─────────────────────────────────────────────────────────────


def _has_race_keyword(run: Dict) -> bool:
    """Return True if the run's name or title contains a race keyword."""
    name = (run.get("name") or run.get("title") or "").lower()
    return any(kw in name for kw in _RACE_KEYWORDS)


def _detect_post_race_recovery(context_packet: Dict) -> Dict:
    """
    Detect if a race-level effort occurred in the last 7 days.

    Two modes of detection:
      Long race (dist >= 10.0 mi): enforces 1–2 full recovery weeks with volume cap.
      Short race (dist < 10.0 mi or keyword-only): enforces a no-quality window
        of POST_RACE_SHORT_NO_QUALITY_DAYS days only (no volume cap).

    Uses training_summary.recent_runs from the context packet.
    Long race takes priority over short race when both are detected.

    Returns:
        {
            "required":           bool,
            "short_race_mode":    bool,   # True = short race (no volume cap)
            "no_quality_days":    int,    # POST_RACE_SHORT_NO_QUALITY_DAYS if short, else 0
            "days_ago":           int,    # 0 if not required
            "approx_distance_mi": float,  # 0.0 if not required or keyword-only
            "week_load_mi":       float,  # rolling weekly avg from training summary
            "recovery_weeks":     int,    # 0 if not required or short, else 1 or 2
        }
    """
    today = date.today()
    recent_runs = (
        context_packet.get("training_summary", {}).get("recent_runs", []) or []
    )

    long_candidate: Optional[Dict] = None   # dist >= 10.0 mi
    short_candidate: Optional[Dict] = None  # dist < 10.0 mi or keyword-only

    for run in recent_runs:
        run_date_str = run.get("date", "")
        dist = float(run.get("distance_mi", 0) or 0)
        try:
            run_date = date.fromisoformat(run_date_str)
        except ValueError:
            continue
        days_ago = (today - run_date).days
        if days_ago > 7:
            continue

        if dist >= 10.0:
            if long_candidate is None or dist > long_candidate["dist"]:
                long_candidate = {"days_ago": days_ago, "dist": dist}
        elif _has_race_keyword(run):
            # Short race: keyword match without long-race distance
            if short_candidate is None or days_ago < short_candidate["days_ago"]:
                short_candidate = {"days_ago": days_ago, "dist": dist}

    ts = context_packet.get("training_summary", {})
    total_mi = float(ts.get("total_miles", 0) or 0)
    period_days = int(ts.get("period_days", 14) or 14)
    week_load = (total_mi / period_days * 7) if period_days > 0 else 0.0

    # Long race takes priority
    if long_candidate is not None:
        dist_mi = long_candidate["dist"]
        days_ago = long_candidate["days_ago"]

        # Half-marathon recovery window: 5 days (empirically: quality session is viable on day 5 post-HM).
        # The check uses days_ago at block start, not at generation time, so that a macro
        # generated mid-week correctly sees the recovery as already elapsed by Sunday.
        days_until_sunday = (6 - today.weekday()) % 7
        days_ago_at_block_start = days_ago + days_until_sunday

        if dist_mi >= 24.0:
            # Marathon: 2 full recovery weeks regardless of timing
            recovery_weeks = 2
        elif days_ago_at_block_start <= 7:
            # Half marathon: block starts before recovery window closes — enforce week 1 recovery
            recovery_weeks = 1
        else:
            # Half marathon: recovery window already elapsed by the time the block starts
            # No need to enforce a no-quality week; athlete is ready to train normally
            recovery_weeks = 0

        log.info(
            "post_race_recovery detected (long): dist_mi=%.1f days_ago=%d recovery_weeks=%d",
            dist_mi, days_ago, recovery_weeks,
        )
        return {
            "required":           recovery_weeks > 0,
            "short_race_mode":    False,
            "no_quality_days":    0,
            "days_ago":           days_ago,
            "approx_distance_mi": round(dist_mi, 1),
            "week_load_mi":       round(week_load, 1),
            "recovery_weeks":     recovery_weeks,
        }

    if short_candidate is not None:
        dist_mi = short_candidate["dist"]
        log.info(
            "post_race_recovery detected (short): dist_mi=%.1f days_ago=%d no_quality_days=%d",
            dist_mi, short_candidate["days_ago"], POST_RACE_SHORT_NO_QUALITY_DAYS,
        )
        return {
            "required":           True,
            "short_race_mode":    True,
            "no_quality_days":    POST_RACE_SHORT_NO_QUALITY_DAYS,
            "days_ago":           short_candidate["days_ago"],
            "approx_distance_mi": round(dist_mi, 1),
            "week_load_mi":       round(week_load, 1),
            "recovery_weeks":     0,
        }

    return {
        "required":           False,
        "short_race_mode":    False,
        "no_quality_days":    0,
        "days_ago":           0,
        "approx_distance_mi": 0.0,
        "week_load_mi":       0.0,
        "recovery_weeks":     0,
    }


# ── LLM prompt construction ───────────────────────────────────────────────────

_MACRO_SCHEMA_HINT = """\
Required JSON structure (output ONLY this, no prose, no markdown fences):
{
  "mode": "base_block" | "race_targeted",
  "race_date": null | "YYYY-MM-DD",
  "race_name": null | "<string max 120 chars>",
  "race_distance": null | "marathon" | "half_marathon" | "10k" | "5k" | "other",
  "vdot": <float>,
  "start_week": "YYYY-MM-DD",
  "total_weeks": <int>,
  "peak_weekly_miles": <float>,
  "rationale": "<max 300 chars>",
  "weeks": [
    {
      "week_number": <int 1-52>,
      "week_start": "YYYY-MM-DD",
      "phase": "base" | "quality" | "race_specific" | "taper",
      "volume_floor_miles": <float 0-150>,
      "volume_target_miles": <float 0-150>,
      "volume_ceiling_miles": <float 0-150>,
      "long_run_max_min": <int 0-300>,
      "intensity_budget": "none" | "low" | "moderate" | "high",
      "quality_sessions_allowed": <int 0-2>,
      "key_workout_type": "easy" | "tempo" | "interval" | "long" | "strength" | "rest" | "cross",
      "recommended_session_types": ["easy"|"tempo"|"interval"|"long"|"strength"|"rest"|"cross", ...],
      "paces": {
        "easy": "<e.g. '10:30-11:10/mi' — max 20 chars>",
        "tempo": null | "<max 20 chars>",
        "interval": null | "<max 20 chars>",
        "long_run": "<max 20 chars>"
      },
      "planner_notes": "<max 200 chars: specific instructions for the weekly planner>",
      "phase_rationale": "<max 200 chars>"
    }
  ]
}"""


def _extract_macro_inputs(context_packet: Dict) -> Dict:
    """
    Determine mode, race info, block length, VDOT, current weekly mileage,
    and post-race recovery constraints from the context packet.

    Returns a dict with all inputs needed to build the LLM prompt.
    """
    races = context_packet.get("upcoming_races", []) or []
    today = date.today()

    # Detect recent race-level effort for recovery enforcement
    post_race = _detect_post_race_recovery(context_packet)

    # Find the target race: A-priority first, then first available
    target_race = None
    for r in races:
        if str(r.get("priority", "")).upper().startswith("A"):
            target_race = r
            break
    if target_race is None and races:
        target_race = races[0]

    # Upcoming Sunday (start of macro block)
    days_until_sunday = (6 - today.weekday()) % 7
    start_week = today + timedelta(days=days_until_sunday)

    # Current weekly mileage from training_summary
    ts = context_packet.get("training_summary", {})
    total_mi = float(ts.get("total_miles", 0) or 0)
    period_days = int(ts.get("period_days", 14) or 14)
    weekly_avg = (total_mi / period_days * 7) if period_days > 0 else 0.0

    # VDOT from athlete snapshot.
    # Priority: race-derived VDOT (from actual performance) > Garmin VO2max > 38.0 default.
    # Garmin's physiological VO2max estimate inflates by ~25-35% relative to
    # race performance and must NOT be used directly as Jack Daniels VDOT.
    athlete = context_packet.get("athlete", {})
    vdot_race = athlete.get("vdot_race_derived")
    vdot_garmin = athlete.get("vo2_max")
    if vdot_race is not None:
        vdot = float(vdot_race)
        log.info("VDOT source=race_derived value=%.1f", vdot)
    elif vdot_garmin is not None:
        vdot = float(vdot_garmin)
        log.warning(
            "VDOT source=garmin_vo2max value=%.1f — no recent race found; "
            "Garmin VO2max may overestimate fitness by 25-35%%",
            vdot,
        )
    else:
        vdot = 38.0
        log.warning("VDOT source=default value=38.0 — no athlete data available")

    # Week 1 volume cap for long-race recovery only (not for short races).
    # Short races enforce a no-quality window but NOT a volume cap.
    # Marathon (>=24mi): 60/70% cap — significant recovery needed.
    # Half marathon (<24mi): 85/90% cap — volume can stay near normal, only quality is restricted.
    week1_cap_miles: Optional[float] = None
    if post_race["required"] and not post_race["short_race_mode"]:
        wk_load = post_race["week_load_mi"] if post_race["week_load_mi"] > 0 else weekly_avg
        dist_mi = post_race["approx_distance_mi"]
        if dist_mi >= 24.0:
            cap_a = 0.60 * wk_load if wk_load > 0 else 14.0
            cap_b = 0.70 * weekly_avg if weekly_avg > 0 else 14.0
        else:
            # Half marathon or similar: keep volume close to normal, just cut quality
            cap_a = 0.85 * wk_load if wk_load > 0 else 18.0
            cap_b = 0.90 * weekly_avg if weekly_avg > 0 else 18.0
        week1_cap_miles = max(round(min(cap_a, cap_b, 20.0), 1), 10.0)  # floor 10 mi

    # Short-race no-quality days: pass through for prompt injection + validation
    short_race_no_quality_days = post_race.get("no_quality_days", 0)

    if target_race:
        race_date_str = target_race.get("date", "")
        try:
            race_d = date.fromisoformat(race_date_str)
        except ValueError:
            race_d = None

        if race_d and race_d > start_week:
            # Weeks from start_week to race_date (inclusive of week containing race)
            block_weeks = max(1, (race_d - start_week).days // 7)
            block_weeks = min(block_weeks, 52)

            # Map distance text to RaceDistanceT
            dist_text = str(target_race.get("distance", "") or "").lower()
            if "marathon" in dist_text and "half" not in dist_text:
                race_distance: RaceDistanceT = "marathon"
            elif "half" in dist_text or "13.1" in dist_text:
                race_distance = "half_marathon"
            elif "10k" in dist_text or "10 k" in dist_text:
                race_distance = "10k"
            elif "5k" in dist_text or "5 k" in dist_text:
                race_distance = "5k"
            else:
                race_distance = "other"

            return {
                "mode":                           "race_targeted",
                "race_date":                      race_date_str,
                "race_name":                      str(target_race.get("name", "Race") or "Race")[:120],
                "race_distance":                  race_distance,
                "block_weeks":                    block_weeks,
                "vdot":                           vdot,
                "current_weekly_miles":           round(weekly_avg, 1),
                "start_week":                     start_week.isoformat(),
                "post_race_recovery_required":    post_race["required"],
                "post_race_recovery_days_ago":    post_race["days_ago"],
                "post_race_approx_distance_mi":   post_race["approx_distance_mi"],
                "post_race_recovery_week_count":  post_race["recovery_weeks"],
                "post_race_short_race_mode":      post_race["short_race_mode"],
                "short_race_no_quality_days":     short_race_no_quality_days,
                "week1_cap_miles":                week1_cap_miles,
            }

    # No valid future race → base_block, 12 weeks
    return {
        "mode":                           "base_block",
        "race_date":                      None,
        "race_name":                      None,
        "race_distance":                  None,
        "block_weeks":                    12,
        "vdot":                           vdot,
        "current_weekly_miles":           round(weekly_avg, 1),
        "start_week":                     start_week.isoformat(),
        "post_race_recovery_required":    post_race["required"],
        "post_race_recovery_days_ago":    post_race["days_ago"],
        "post_race_approx_distance_mi":   post_race["approx_distance_mi"],
        "post_race_recovery_week_count":  post_race["recovery_weeks"],
        "post_race_short_race_mode":      post_race["short_race_mode"],
        "short_race_no_quality_days":     short_race_no_quality_days,
        "week1_cap_miles":                week1_cap_miles,
    }


def _build_macro_prompts(inputs: Dict) -> tuple:
    """Build (system_prompt, user_prompt) for the macro plan LLM call."""
    mode         = inputs["mode"]
    total_weeks  = inputs["block_weeks"]
    start_week   = inputs["start_week"]
    vdot         = inputs["vdot"]
    weekly_miles = inputs["current_weekly_miles"]

    # Pre-compute all week starts (help LLM avoid date arithmetic errors)
    ws_date = date.fromisoformat(start_week)
    week_starts_lines = "\n".join(
        f"  Week {i+1}: {(ws_date + timedelta(days=7*i)).isoformat()}"
        for i in range(total_weeks)
    )

    if mode == "base_block":
        mode_rules = (
            "MODE: base_block\n"
            '- Allowed phases: only "base" and "quality". '
            'No "race_specific". No "taper".\n'
            "- race_date, race_name, race_distance MUST be null.\n"
            "- Build aerobic fitness throughout. No taper at the end.\n"
            "- PHASE PROGRESSION IS ONE-WAY: once any week is assigned 'quality', "
            "ALL subsequent weeks must also be 'quality'. Do NOT go back to 'base' "
            "after 'quality'. End-of-block down-volume weeks stay 'quality' — "
            "reduce intensity/volume within the quality phase instead.\n"
            "- END-OF-BLOCK: final 2 weeks must HOLD or REDUCE from peak volume. "
            "Do NOT make the last week simultaneously: peak volume + "
            "intensity_budget='high' + quality_sessions_allowed=2. "
            "Prefer a steady, sustainable block finish."
        )
        race_context = ""
    else:
        taper_note = (
            "2-week taper (last 2 weeks)" if inputs["race_distance"] == "marathon"
            else "1-week taper (last 1 week)"
        )
        mode_rules = (
            "MODE: race_targeted\n"
            f"- race_date = \"{inputs['race_date']}\"\n"
            f"- race_name = \"{inputs['race_name']}\"\n"
            f"- race_distance = \"{inputs['race_distance']}\"\n"
            f"- {taper_note} at the end of the block.\n"
            "- Allowed phases: base → quality → race_specific → taper (no regression).\n"
            "- Do NOT place taper/race_specific before quality phase."
        )
        race_context = (
            f"\nRace: {inputs['race_name']} on {inputs['race_date']} "
            f"({inputs['race_distance']})"
        )

    # Post-race recovery block (injected into prompt when recent race detected)
    if inputs.get("post_race_recovery_required"):
        days_ago = inputs["post_race_recovery_days_ago"]
        dist     = inputs["post_race_approx_distance_mi"]

        if inputs.get("post_race_short_race_mode"):
            # Short race (5k/10k/etc.): no-quality window only, no volume cap.
            nq_days = inputs.get("short_race_no_quality_days", POST_RACE_SHORT_NO_QUALITY_DAYS)
            recovery_note = (
                f"SHORT-RACE NO-QUALITY WINDOW:\n"
                f"- A short race effort ({dist:.1f} mi) was completed {days_ago} day(s) ago.\n"
                f"- For the first {nq_days} days after the race: no quality sessions, easy only.\n"
                f"- Week 1 MUST have quality_sessions_allowed = 0.\n"
                f"- Volume cap is NOT enforced — continue normal base-phase mileage ramp.\n"
                f"- intensity_budget for Week 1 should be 'low'.\n"
                f"- planner_notes for Week 1 must mention 'short-race recovery'.\n\n"
            )
        else:
            # Long race (half/marathon): full volume cap + quality=0 + low intensity.
            cap   = inputs["week1_cap_miles"]
            n_rec = inputs.get("post_race_recovery_week_count", 1)
            recovery_note = (
                f"POST-RACE RECOVERY REQUIREMENT:\n"
                f"- A race-level effort ({dist:.1f} mi) was completed {days_ago} day(s) ago.\n"
                f"- Weeks 1–{n_rec} MUST be recovery weeks:\n"
                f"  * volume_target_miles <= {cap:.1f} mi (hard cap)\n"
                f"  * quality_sessions_allowed = 0\n"
                f"  * intensity_budget = 'none' or 'low'\n"
                f"  * key_workout_type = 'easy' or 'rest'\n"
                f"  * planner_notes must mention 'post-race recovery'\n\n"
            )
    else:
        recovery_note = ""

    system = (
        f"You are a running coach AI. Generate a {total_weeks}-week {mode} "
        f"macro training block.\n\n"
        f"{mode_rules}\n\n"
        f"{recovery_note}"
        f"TRAINING CONTEXT:\n"
        f"- Athlete VDOT: {vdot:.1f}\n"
        f"- Current weekly mileage: {weekly_miles:.1f} mi/week\n"
        f"- Block start: {start_week}\n"
        f"- Total weeks: {total_weeks}"
        f"{race_context}\n\n"
        f"PHASE GUIDELINES:\n"
        + (
            f"- base week 1+: quality_sessions_allowed = 1 "
            f"(no post-race recovery required — start quality from week 1)\n"
            if not inputs.get("post_race_recovery_required")
            else (
                f"- base weeks 1–{inputs.get('post_race_recovery_week_count', 1)}: "
                f"quality_sessions_allowed = 0 (see POST-RACE RECOVERY REQUIREMENT above)\n"
                f"- base week {inputs.get('post_race_recovery_week_count', 1) + 1}: "
                f"quality_sessions_allowed = 1 (MANDATORY — first week after recovery block)\n"
                f"- base week {inputs.get('post_race_recovery_week_count', 1) + 2}+: "
                f"quality_sessions_allowed = 1\n"
            )
        )
        + f"- quality: add tempo/interval work (max 2 sessions/week), budget 'moderate'/'high'\n"
        f"- race_specific: race-pace work, begin volume reduction, budget 'moderate'\n"
        f"- taper: reduce volume 20-30%/week, maintain intensity, preserve fitness\n\n"
        f"VOLUME RAMP (base phase only):\n"
        f"- Start Week 1 close to current weekly mileage ({weekly_miles:.1f} mi/wk). "
        f"Do NOT drop to 0 or start from scratch.\n"
        f"- Max 10% increase week-over-week\n"
        f"- No more than 2 consecutive weeks of >7% increase\n"
        f"- Volume == 0 → key_workout_type must be 'rest'\n"
        f"- Volume < 6 mi → quality_sessions_allowed must be 0\n\n"
        f"LONG RUN (target 35-45% of weekly volume at ~10 min/mi):\n"
        f"- TARGET long_run_max_min = 35-45% of (volume_target_miles × 10 min)\n"
        f"  Example: 20 mi/wk → target 70-90 min long run\n"
        f"- Hard cap (any week): ≤ 62% of (volume_target_miles × 10 min)\n"
        f"- Early-block cap (weeks 1-4): ≤ 50% of (volume_target_miles × 10 min)\n\n"
        f"QUALITY RAMP (avoid sudden stress spikes):\n"
        f"- First quality week: quality_sessions_allowed = 1 (NEVER jump 0→2)\n"
        f"- Do NOT simultaneously increase quality_sessions_allowed AND "
        f"long_run_max_min by >10% in the same week\n"
        f"- Build intensity_budget gradually: none → low → moderate → high\n\n"
        f"PACES (VDOT {vdot:.1f}):\n"
        f"- Easy: approximately 10:30-11:10/mi (adjust for exact VDOT)\n"
        f"- Long run: approximately 11:00-11:40/mi\n"
        f"- Tempo: approximately 9:00-9:20/mi\n"
        f"- Interval: approximately 8:30-8:45/mi\n\n"
        f"OUTPUT RULES:\n"
        f"- Output ONLY a single JSON object. No markdown fences. No prose.\n"
        f"- Generate EXACTLY {total_weeks} week entries.\n"
        f"- week_start for each week MUST match the exact Sunday listed below.\n"
        f"- week_number must be 1-indexed and sequential.\n"
        f"- Phases must not regress (e.g., quality cannot follow taper).\n"
        f"- rationale: reference actual Week 1 volume ({weekly_miles:.1f} mi/wk currently). "
        f"NEVER write 'from 0 miles' or 'starting from scratch' — "
        f"the athlete is already training."
    )

    user = (
        f"Generate a {total_weeks}-week {mode} macro plan starting {start_week}.\n\n"
        f"Week starts (use EXACTLY these dates — copy them verbatim):\n"
        f"{week_starts_lines}\n\n"
        f"{_MACRO_SCHEMA_HINT}"
    )

    return system, user


def _truncate_macro_data(data: Dict) -> Dict:
    """Pre-validation truncation to schema limits (LLMs ignore char caps)."""
    def _t(s: Any, n: int) -> Any:
        return s[:n] if isinstance(s, str) else s

    data["rationale"] = _t(data.get("rationale", ""), 300)
    if data.get("race_name"):
        data["race_name"] = _t(data["race_name"], 120)

    for week in data.get("weeks", []):
        week["planner_notes"]   = _t(week.get("planner_notes", ""), 200)
        week["phase_rationale"] = _t(week.get("phase_rationale", ""), 200)
        paces = week.get("paces", {})
        if isinstance(paces, dict):
            for k in ("easy", "tempo", "interval", "long_run"):
                if paces.get(k):
                    paces[k] = _t(paces[k], 20)

    return data


def _parse_and_validate_macro(raw_text: str, system: str) -> MacroPlan:
    """
    Extract JSON from raw LLM output and validate with Pydantic.
    One format reprompt, then one schema reprompt on failure.
    """
    # Step 1: strict extract
    json_str = _try_strict_extract(raw_text)
    if json_str is None:
        log.warning("Macro LLM output not clean JSON — reprompting for format")
        reprompted = _call_llm(
            system,
            "Output JSON only. No text, no markdown. No explanation.\n\n"
            "Previous output:\n" + raw_text[:500],
            timeout=120,
            model=_MACRO_MODEL,
        )
        json_str = _try_strict_extract(reprompted)
        if json_str is None:
            log.warning("Format reprompt failed — using brace search")
            json_str = _brace_search_last(reprompted)

    # Schema validation with one reprompt
    for attempt in range(2):
        try:
            data = json.loads(json_str)
            data = _truncate_macro_data(data)
            return MacroPlan.model_validate(data)
        except Exception as exc:
            if attempt == 0:
                log.warning("Macro schema attempt 1 failed: %s — reprompting", exc)
                fix_raw = _call_llm(
                    system,
                    f"The JSON you returned failed schema validation. "
                    f"Return ONLY a corrected JSON object. No explanation. No markdown. "
                    f"Error: {str(exc)[:200]}\n\nPrevious output:\n{json_str[:600]}",
                    timeout=120,
                    model=_MACRO_MODEL,
                )
                json_str_2 = _try_strict_extract(fix_raw)
                json_str = json_str_2 if json_str_2 is not None else _brace_search_last(fix_raw)
            else:
                raise RuntimeError(
                    f"Brain returned invalid macro plan JSON after reprompts: {exc}"
                ) from exc

    raise RuntimeError("unreachable")  # mypy


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_macro_plan(
    context_packet: Dict,
    force: bool = False,
    db_path=None,
) -> MacroPlan:
    """
    Generate (or retrieve cached) macro periodization plan.

    TRANSACTION SAFETY:
      LLM call happens OUTSIDE any DB transaction.
      DB writes (insert + activate) happen AFTER LLM call completes.

    If force=False and an active macro plan exists, returns it immediately
    without an LLM call.

    On validation failure:
      - Plan inserted with status="validation_failed" (for audit).
      - MacroValidationError raised (NOT set as active).

    Returns:
        MacroPlan — validated Pydantic object.

    Raises:
        MacroValidationError: if the generated plan fails structural checks.
    """
    from memory.db import (
        DB_PATH as _DEFAULT_DB,
        insert_macro_plan,
        set_active_macro_plan,
        get_active_macro_plan,
        init_db,
    )
    from memory.vault import append_decision

    if db_path is None:
        from memory.db import DB_PATH as _DEFAULT_DB
        db_path = _DEFAULT_DB

    db_path = Path(db_path)
    init_db(db_path)

    # ── Cache check ──────────────────────────────────────────────────────────
    if not force:
        existing = get_active_macro_plan(db_path=db_path)
        if existing:
            log.info(
                "Macro plan cache HIT — reusing macro_id=%s", existing["macro_id"]
            )
            try:
                return MacroPlan.model_validate(existing["plan"])
            except Exception:
                log.warning("Cached macro plan failed Pydantic validation, regenerating")

    # ── Extract inputs from context packet ───────────────────────────────────
    inputs = _extract_macro_inputs(context_packet)
    log.info(
        "generate_macro_plan mode=%s block_weeks=%d start_week=%s vdot=%.1f "
        "post_race=%s week1_cap=%s",
        inputs["mode"], inputs["block_weeks"], inputs["start_week"], inputs["vdot"],
        inputs.get("post_race_recovery_required", False),
        inputs.get("week1_cap_miles"),
    )

    # ── Build prompt ─────────────────────────────────────────────────────────
    system, user = _build_macro_prompts(inputs)

    # ── LLM call (OUTSIDE DB transaction) ───────────────────────────────────
    import subprocess as _subprocess
    try:
        raw = _call_llm(system, user, timeout=420, model=_MACRO_MODEL)
    except _subprocess.TimeoutExpired:
        raise RuntimeError(
            "Macro plan generation timed out (7 min). "
            "The LLM is likely overloaded — try again in a few minutes."
        )

    # ── Parse + Pydantic validation ──────────────────────────────────────────
    plan = _parse_and_validate_macro(raw, system)

    # ── Post-parse fixup: enforce volume ramp constraints ────────────────────
    # Haiku regularly generates volume jumps that exceed 10% or 3+ consecutive
    # >7% ramps. Normalise the progression deterministically.
    consec_big = 0
    for i in range(1, len(plan.weeks)):
        prev = plan.weeks[i - 1]
        curr = plan.weeks[i]
        if prev.volume_target_miles > 0 and curr.phase == "base":
            pct = (curr.volume_target_miles - prev.volume_target_miles) / prev.volume_target_miles
            import math as _math
            # Cap at 10% — use floor to avoid rounding past the limit
            if pct > 0.10 + 1e-9:
                capped = _math.floor(prev.volume_target_miles * 1.099 * 10) / 10
                log.info("volume ramp fixup: week %d %.1f→%.1f", curr.week_number, curr.volume_target_miles, capped)
                curr.volume_target_miles = capped
                pct = (capped - prev.volume_target_miles) / prev.volume_target_miles
            # Track consecutive >7% ramps and flatten the third
            consec_big = consec_big + 1 if pct > 0.07 else 0
            if consec_big >= 3:
                flattened = _math.floor(prev.volume_target_miles * 1.05 * 10) / 10
                log.info("consec ramp fixup: week %d %.1f→%.1f", curr.week_number, curr.volume_target_miles, flattened)
                curr.volume_target_miles = flattened
                consec_big = 1  # reset streak

    for week in plan.weeks:
        if week.volume_floor_miles > week.volume_target_miles:
            week.volume_floor_miles = max(0.0, round(week.volume_target_miles * 0.9, 1))
        if week.volume_ceiling_miles < week.volume_target_miles:
            week.volume_ceiling_miles = round(week.volume_target_miles * 1.1, 1)

    # ── Post-parse fixup: enforce simultaneous quality+LR constraint ─────────
    # Validation rule 12 rejects plans where quality increases AND long_run_max_min
    # increases >10% in the same week. Haiku consistently violates this despite
    # the prompt warning. Cap the LR to stay within 10% when quality also increases.
    for i in range(1, len(plan.weeks)):
        prev = plan.weeks[i - 1]
        curr = plan.weeks[i]
        if curr.quality_sessions_allowed > prev.quality_sessions_allowed and prev.long_run_max_min > 0:
            max_lr = round(prev.long_run_max_min * 1.09)  # 9% headroom (under 10% limit)
            if curr.long_run_max_min > max_lr:
                log.info(
                    "lr cap fixup: week %d LR %d→%d (quality also increased)",
                    curr.week_number, curr.long_run_max_min, max_lr,
                )
                curr.long_run_max_min = max_lr

    # ── Structural validation layer ──────────────────────────────────────────
    result = validate_macro_plan(
        plan,
        post_race_cap_miles=inputs.get("week1_cap_miles"),
        post_race_recovery_weeks=inputs.get("post_race_recovery_week_count", 0),
        short_race_no_quality_days=inputs.get("short_race_no_quality_days", 0),
    )

    if not result.ok:
        # Audit insert (status="validation_failed") — no activation
        try:
            insert_macro_plan(
                mode=inputs["mode"],
                race_date=inputs.get("race_date"),
                race_name=inputs.get("race_name"),
                start_week=inputs["start_week"],
                total_weeks=inputs["block_weeks"],
                vdot=inputs["vdot"],
                plan_json=plan.model_dump(),
                status="validation_failed",
                db_path=db_path,
            )
        except Exception as audit_exc:
            log.warning("Could not audit-insert failed macro plan: %s", audit_exc)
        for err in result.errors:
            log.error("Macro validation error: %s", err)
        raise MacroValidationError(result.errors)

    # ── Persist (validation passed) ──────────────────────────────────────────
    macro_id = insert_macro_plan(
        mode=inputs["mode"],
        race_date=inputs.get("race_date"),
        race_name=inputs.get("race_name"),
        start_week=inputs["start_week"],
        total_weeks=inputs["block_weeks"],
        vdot=inputs["vdot"],
        plan_json=plan.model_dump(),
        status="draft",
        db_path=db_path,
    )
    set_active_macro_plan(macro_id, db_path=db_path)

    # ── Vault ────────────────────────────────────────────────────────────────
    append_decision(
        {
            "type":        "macro_plan_generated",
            "macro_id":    macro_id,
            "mode":        inputs["mode"],
            "start_week":  inputs["start_week"],
            "total_weeks": inputs["block_weeks"],
            "race_date":   inputs.get("race_date"),
            "race_name":   inputs.get("race_name"),
            "peak_miles":  plan.peak_weekly_miles,
        },
        rationale=plan.rationale[:300],
    )

    log.info(
        "generate_macro_plan activated macro_id=%s mode=%s weeks=%d "
        "peak_miles=%.1f vdot=%.1f post_race_recovery=%s",
        macro_id,
        inputs["mode"],
        inputs["block_weeks"],
        plan.peak_weekly_miles,
        inputs["vdot"],
        inputs.get("post_race_recovery_required", False),
    )
    return plan
