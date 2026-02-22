"""
Brain Macro Planner — LLM-powered long-range periodization block.

Public API:
    generate_macro_plan(context_packet, force=False, db_path=None) -> MacroPlan
    validate_macro_plan(plan: MacroPlan) -> MacroValidationResult

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

log = logging.getLogger("brain.macro_plan")

MAX_TOKENS_MACRO = 4096

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


def validate_macro_plan(plan: MacroPlan) -> MacroValidationResult:
    """
    Run all structural and training-science invariants.

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
    base_vols = [
        (w.week_number, w.target_volume_miles)
        for w in weeks
        if w.phase == "base"
    ]
    consec_big_ramps = 0
    for i in range(1, len(base_vols)):
        prev_vol = base_vols[i - 1][1]
        curr_vol = base_vols[i][1]
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

    # 8. Zero/low volume rules
    for w in weeks:
        if w.target_volume_miles == 0 and w.key_workout_type != "rest":
            errors.append(
                f"week {w.week_number}: zero volume but "
                f"key_workout_type='{w.key_workout_type}' (must be 'rest')"
            )
        if w.target_volume_miles < 6 and w.quality_sessions_allowed > 0:
            errors.append(
                f"week {w.week_number}: volume {w.target_volume_miles:.1f}mi < 6 "
                f"but quality_sessions_allowed={w.quality_sessions_allowed} (must be 0)"
            )

    # 9. long_run_max_min sanity (≤ 62% of weekly volume at ~10 min/mi)
    for w in weeks:
        if w.target_volume_miles > 0:
            volume_mins_approx = w.target_volume_miles * 10
            if w.long_run_max_min > volume_mins_approx * 0.62:
                errors.append(
                    f"week {w.week_number}: long_run_max_min {w.long_run_max_min} "
                    f"exceeds 62% of ~{volume_mins_approx:.0f}min weekly volume"
                )

    return MacroValidationResult(ok=len(errors) == 0, errors=errors)


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
      "target_volume_miles": <float 0-150>,
      "long_run_max_min": <int 0-300>,
      "intensity_budget": "none" | "low" | "moderate" | "high",
      "quality_sessions_allowed": <int 0-2>,
      "key_workout_type": "easy" | "tempo" | "interval" | "long" | "strength" | "rest" | "cross",
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
    Determine mode, race info, block length, VDOT, and current weekly mileage
    from the context packet.

    Returns a dict with all inputs needed to build the LLM prompt.
    """
    races = context_packet.get("upcoming_races", []) or []
    today = date.today()

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

    # VDOT from athlete snapshot (VO2max ≈ VDOT in Jack Daniels system)
    vdot_raw = context_packet.get("athlete", {}).get("vo2_max")
    vdot = float(vdot_raw) if vdot_raw is not None else 38.0

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
                "mode":                "race_targeted",
                "race_date":           race_date_str,
                "race_name":           str(target_race.get("name", "Race") or "Race")[:120],
                "race_distance":       race_distance,
                "block_weeks":         block_weeks,
                "vdot":                vdot,
                "current_weekly_miles": round(weekly_avg, 1),
                "start_week":          start_week.isoformat(),
            }

    # No valid future race → base_block, 12 weeks
    return {
        "mode":                "base_block",
        "race_date":           None,
        "race_name":           None,
        "race_distance":       None,
        "block_weeks":         12,
        "vdot":                vdot,
        "current_weekly_miles": round(weekly_avg, 1),
        "start_week":          start_week.isoformat(),
    }


def _build_macro_prompts(inputs: Dict) -> tuple:
    """Build (system_prompt, user_prompt) for the macro plan LLM call."""
    mode = inputs["mode"]
    total_weeks = inputs["block_weeks"]
    start_week = inputs["start_week"]
    vdot = inputs["vdot"]
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
            "- Build aerobic fitness throughout. No taper at the end."
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

    system = (
        f"You are a running coach AI. Generate a {total_weeks}-week {mode} "
        f"macro training block.\n\n"
        f"{mode_rules}\n\n"
        f"TRAINING CONTEXT:\n"
        f"- Athlete VDOT: {vdot:.1f}\n"
        f"- Current weekly mileage: {weekly_miles:.1f} mi/week\n"
        f"- Block start: {start_week}\n"
        f"- Total weeks: {total_weeks}"
        f"{race_context}\n\n"
        f"PHASE GUIDELINES:\n"
        f"- base: aerobic foundation, easy/long only, intensity_budget 'none' or 'low'\n"
        f"- quality: add tempo/interval work (max 2 sessions/week), budget 'moderate'/'high'\n"
        f"- race_specific: race-pace work, begin volume reduction, budget 'moderate'\n"
        f"- taper: reduce volume 20-30%/week, maintain intensity, preserve fitness\n\n"
        f"VOLUME RAMP (base phase only):\n"
        f"- Max 10% increase week-over-week\n"
        f"- No more than 2 consecutive weeks of >7% increase\n"
        f"- Volume == 0 → key_workout_type must be 'rest'\n"
        f"- Volume < 6 mi → quality_sessions_allowed must be 0\n\n"
        f"LONG RUN: long_run_max_min ≤ 62% of (target_volume_miles × 10 minutes)\n\n"
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
        f"- Phases must not regress (e.g., quality cannot follow taper)."
    )

    user = (
        f"Generate a {total_weeks}-week {mode} macro plan starting {start_week}.\n\n"
        f"Week starts (use EXACTLY these dates — copy them verbatim):\n"
        f"{week_starts_lines}\n\n"
        f"{_MACRO_SCHEMA_HINT}"
    )

    return system, user


# ── JSON extraction helpers (mirrors planner.py approach) ─────────────────────

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```$", re.MULTILINE)


def _try_strict_extract(text: str) -> Optional[str]:
    s = _JSON_FENCE_RE.sub("", text).strip()
    if s.startswith("{") and s.endswith("}"):
        return s
    return None


def _brace_search_last(text: str) -> str:
    last_close = text.rfind("}")
    if last_close == -1:
        raise ValueError(f"No JSON object found in macro output:\n{text[:300]}")
    depth = 0
    for i in range(last_close, -1, -1):
        ch = text[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                return text[i : last_close + 1]
    raise ValueError(f"Unbalanced JSON braces in macro output:\n{text[:300]}")


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
    from brain.planner import _call_llm  # avoid circular import at module level

    # Step 1: strict extract
    json_str = _try_strict_extract(raw_text)
    if json_str is None:
        log.warning("Macro LLM output not clean JSON — reprompting for format")
        reprompted = _call_llm(
            system,
            "Output JSON only. No text, no markdown. No explanation.\n\n"
            "Previous output:\n" + raw_text[:500],
            timeout=120,
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
    from brain.planner import _call_llm
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
        "generate_macro_plan mode=%s block_weeks=%d start_week=%s vdot=%.1f",
        inputs["mode"], inputs["block_weeks"], inputs["start_week"], inputs["vdot"],
    )

    # ── Build prompt ─────────────────────────────────────────────────────────
    system, user = _build_macro_prompts(inputs)

    # ── LLM call (OUTSIDE DB transaction) ───────────────────────────────────
    import subprocess as _subprocess
    try:
        raw = _call_llm(system, user, timeout=600)
    except _subprocess.TimeoutExpired:
        raise RuntimeError(
            "Macro plan generation timed out (10 min). "
            "The LLM is likely overloaded — try again in a few minutes."
        )

    # ── Parse + Pydantic validation ──────────────────────────────────────────
    plan = _parse_and_validate_macro(raw, system)

    # ── Structural validation layer ──────────────────────────────────────────
    result = validate_macro_plan(plan)

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

    log.info("generate_macro_plan persisted macro_id=%s", macro_id)
    return plan
