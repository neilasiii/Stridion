"""
Brain Planner — LLM-powered workout prescription.

Public API:
    plan_week(context_packet, force=False, week_start=None, db_path=None)
        -> PlanDecision

    adjust_today(context_packet, db_path=None)
        -> TodayAdjustment

The Brain:
  - Reads ONLY the Context Packet (never raw health cache or FinalSurge directly).
  - Outputs strict JSON validated by Pydantic schemas.
  - On invalid JSON: one reprompt "Fix JSON only", then raises.
  - Caches by context_hash — skips LLM if nothing changed (override with force=True).
  - Persists every new plan to SQLite + vault.

LLM backend:
  Primary  — claude CLI subprocess (-p prompt --output-format text)
  Fallback — anthropic SDK (if installed)
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError

from .schemas import PlanDecision, TodayAdjustment, HARD_TYPES

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

log = logging.getLogger("brain.planner")

# ── LLM config ────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 2048
CLAUDE_PATHS = [
    Path.home() / ".local" / "bin" / "claude",
    Path("/usr/local/bin/claude"),
    Path("/usr/bin/claude"),
]

# ── Prompt templates ──────────────────────────────────────────────────────────

_SYSTEM_PLAN_WEEK = """\
You are a running coach AI. Your job is to prescribe a 7-day training week.

AUTHORITY RULE (non-negotiable):
- The authoritative plan is the internal SQLite plan, not FinalSurge/ICS.
- Do NOT use scheduled_workouts as a plan source. Plan from context only.

SAFETY RULES (enforced — violations will be flagged):
1. No two consecutive hard days. Hard = tempo, interval, long.
2. If readiness_trend.today.training_readiness < 50, OR
   readiness_trend.today.hrv is present and low: reduce intensity first.
3. Week-over-week volume increase must be ≤ 10% vs training_summary unless
   explicitly permitted by context (e.g., post-taper return).
4. Constraint dates (constraints[]) must be rest or cross-train.

OUTPUT RULES:
- Output ONLY a single JSON object. No markdown fences. No prose.
- Every field in the schema is required unless marked Optional.
- Rationale fields: max 200 chars each (300 for top-level).
- structure_steps: warmup + main + cooldown minimum for non-rest days.
"""

_SYSTEM_ADJUST_TODAY = """\
You are a running coach AI. Adjust today's workout based on current readiness.

AUTHORITY RULE: Plan from context packet only. FinalSurge is not authoritative.

SAFETY RULES:
1. Low readiness (training_readiness < 50 or HRV low) → reduce to easy/rest.
2. Constraint on today → rest or cross-train.
3. Output ONLY a single JSON object. No markdown fences. No prose.
"""

_PLAN_SCHEMA_HINT = """\
Required output JSON structure (all fields required unless marked optional):
{
  "week_start": "YYYY-MM-DD",
  "week_end":   "YYYY-MM-DD",
  "phase": "base"|"quality"|"race_specific"|"taper",
  "weekly_volume_miles": <float>,
  "safety_flags": ["<string>", ...],
  "rationale": "<max 300 chars>",
  "context_hash": "<echo the context_hash from input>",
  "days": [  // exactly 7 entries, one per day
    {
      "date": "YYYY-MM-DD",
      "intent": "<one-liner, max 80 chars>",
      "workout_type": "easy"|"tempo"|"interval"|"long"|"strength"|"rest"|"cross",
      "duration_min": <int 0-300>,
      "structure_steps": [
        {
          "label": "warmup"|"main"|"cooldown"|"interval"|"recovery",
          "duration_min": <int 1-120>,
          "target_metric": "pace"|"hr"|"power"|"rpe",
          "target_value": "<e.g. '10:30-11:10/mi' or 'RPE 4'>",
          "reps": <optional int for intervals>,
          "notes": "<optional, max 80 chars>"
        }
      ],
      "safety_flags": ["<string>", ...],
      "rationale": "<max 200 chars>"
    }
  ]
}"""

_ADJUST_SCHEMA_HINT = """\
Required output JSON structure:
{
  "date": "YYYY-MM-DD",
  "original_intent": "<from active plan or null>",
  "adjusted_intent": "<max 80 chars>",
  "workout_type": "easy"|"tempo"|"interval"|"long"|"strength"|"rest"|"cross",
  "duration_min": <int 0-300>,
  "structure_steps": [
    {"label":"warmup"|"main"|"cooldown","duration_min":<int>,"target_metric":"pace"|"hr"|"power"|"rpe","target_value":"<str>"}
  ],
  "adjustment_reason": "low_readiness"|"constraint"|"illness"|"missed_workout"|"weather"|"other",
  "readiness_score": <0-100 or null>,
  "alternatives": ["<alt 1>","<alt 2>"],
  "safety_flags": ["<string>", ...],
  "rationale": "<max 200 chars>"
}"""

_FIX_JSON_PROMPT = (
    "The JSON you returned failed schema validation. "
    "Return ONLY a corrected JSON object. No explanation. No markdown. "
    "Error: {error}"
)


# ── LLM call ──────────────────────────────────────────────────────────────────

def _find_claude() -> Optional[str]:
    for p in CLAUDE_PATHS:
        if p.exists():
            return str(p)
    return None


def _call_llm(system: str, user: str, timeout: int = 120) -> str:
    """
    Call Claude CLI in headless mode. Returns raw text output.
    Raises RuntimeError on non-zero exit or empty response.
    """
    claude = _find_claude()
    if claude is None:
        # Attempt anthropic SDK as fallback
        return _call_anthropic_sdk(system, user)

    full_prompt = f"{system}\n\n{user}"
    log.debug("Calling claude CLI, prompt_len=%d chars", len(full_prompt))

    # Strip CLAUDECODE so the subprocess is not treated as a nested session.
    # This is the documented bypass: the child process is headless/one-shot
    # and does not share interactive state with the parent session.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    result = subprocess.run(
        [claude, "-p", full_prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(PROJECT_ROOT),
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited {result.returncode}: {result.stderr[:300]}"
        )

    text = result.stdout.strip()
    if not text:
        raise RuntimeError("claude CLI returned empty response")

    log.debug("LLM response_len=%d chars", len(text))
    return text


def _call_anthropic_sdk(system: str, user: str) -> str:
    """Fallback: use anthropic Python SDK if installed."""
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise RuntimeError(
            "No LLM backend available. Install 'anthropic' SDK or ensure "
            "claude CLI is accessible at one of: "
            + ", ".join(str(p) for p in CLAUDE_PATHS)
        )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


# ── JSON extraction ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """
    Strip markdown fences and extract the first JSON object from text.
    Tries: verbatim → strip fences → find {...} substring.
    """
    stripped = text.strip()

    # 1) Try verbatim
    if stripped.startswith("{"):
        return stripped

    # 2) Strip ```json ... ``` or ``` ... ``` fences
    fence = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.MULTILINE)
    fence = re.sub(r"\s*```$", "", fence, flags=re.MULTILINE).strip()
    if fence.startswith("{"):
        return fence

    # 3) Find first { ... } block
    m = re.search(r"\{[\s\S]*\}", stripped)
    if m:
        return m.group(0)

    raise ValueError(f"No JSON object found in LLM output:\n{text[:300]}")


# ── Observability ──────────────────────────────────────────────────────────────

_EXPECTED_PACKET_KEYS = {
    "today", "athlete", "training_summary", "readiness_trend",
    "plan_authority", "active_plan", "constraints",
    "recent_decisions", "vault_excerpts",
}


def _log_packet_stats(packet: Dict) -> None:
    packet_json = json.dumps(packet, default=str)
    log.info("Context packet: %d chars", len(packet_json))

    missing = _EXPECTED_PACKET_KEYS - set(packet.keys())
    if missing:
        log.warning("Context packet missing keys: %s", missing)

    rt = packet.get("readiness_trend", {})
    today_rt = rt.get("today", {}) if isinstance(rt, dict) else {}
    for field in ("sleep_hours", "hrv", "body_battery_max", "training_readiness"):
        if today_rt.get(field) is None:
            log.info("Health field not available: readiness_trend.today.%s", field)

    pa = packet.get("plan_authority", {})
    if isinstance(pa, dict):
        log.info(
            "plan_authority: active=%s range=%s finalsurge_auth=%s",
            pa.get("active_plan_id"),
            pa.get("active_plan_range"),
            pa.get("finalsurge_authoritative"),
        )


# ── Pre-validation truncation ─────────────────────────────────────────────────

def _truncate_plan_data(data: Dict) -> Dict:
    """
    Truncate string fields to schema limits before Pydantic validation.
    LLMs reliably ignore exact char caps even after reprompting; truncation
    here is cheaper and more reliable than a second round-trip.
    """
    def _t(s, n): return s[:n] if isinstance(s, str) else s

    for day in data.get("days", []):
        day["intent"]    = _t(day.get("intent", ""), 80)
        day["rationale"] = _t(day.get("rationale", ""), 200)
        for step in day.get("structure_steps", []):
            step["target_value"] = _t(step.get("target_value", ""), 50)
            if "notes" in step and step["notes"]:
                step["notes"] = _t(step["notes"], 80)

    data["rationale"] = _t(data.get("rationale", ""), 300)
    return data


def _truncate_adjustment_data(data: Dict) -> Dict:
    """Same pre-validation truncation for TodayAdjustment."""
    def _t(s, n): return s[:n] if isinstance(s, str) else s

    data["adjusted_intent"] = _t(data.get("adjusted_intent", ""), 80)
    data["rationale"]       = _t(data.get("rationale", ""), 200)
    for step in data.get("structure_steps", []):
        step["target_value"] = _t(step.get("target_value", ""), 50)
        if step.get("notes"):
            step["notes"] = _t(step["notes"], 80)
    return data


# ── Cache check ────────────────────────────────────────────────────────────────

def _find_plan_by_hash(ctx_hash: str, db_path) -> Optional[Dict]:
    """Return the most recent plan row whose context_hash matches, or None."""
    import sqlite3
    from memory.db import DB_PATH as _DEFAULT_DB

    db = Path(db_path or _DEFAULT_DB)
    if not db.exists():
        return None

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """SELECT plan_id, plan_json, status FROM plans
               WHERE context_hash = ? AND status IN ('active', 'draft')
               ORDER BY created_at DESC LIMIT 1""",
            (ctx_hash,),
        ).fetchone()
        if row:
            return {"plan_id": row["plan_id"], "plan": json.loads(row["plan_json"]), "status": row["status"]}
        return None
    finally:
        conn.close()


# ── Week boundary helpers ─────────────────────────────────────────────────────

def _resolve_week_start(week_start: Optional[date]) -> date:
    """Return the ISO Monday for the planning week."""
    if week_start is not None:
        return week_start
    today = date.today()
    # Monday of current week
    return today - timedelta(days=today.weekday())


# ── plan_week ─────────────────────────────────────────────────────────────────

def plan_week(
    context_packet: Dict,
    force: bool = False,
    week_start: Optional[date] = None,
    db_path=None,
) -> PlanDecision:
    """
    Generate a 7-day training plan from the context packet.

    Args:
        context_packet: Output of memory.build_context_packet().
        force:          Skip cache check and always call the LLM.
        week_start:     Monday of the week to plan (default: current ISO week).
        db_path:        Override SQLite path (testing).

    Returns:
        PlanDecision — validated, persisted, vault-documented.
    """
    from memory import (
        hash_context_packet, insert_plan, insert_plan_days,
        set_active_plan, init_db, DB_PATH as _DEFAULT_DB,
    )
    from memory.vault import append_decision, write_plan_snapshot

    _log_packet_stats(context_packet)

    ctx_hash = hash_context_packet(context_packet)
    log.info("plan_week context_hash=%s force=%s", ctx_hash[:12], force)

    db = db_path or _DEFAULT_DB
    init_db(db)

    # ── Cache check ────────────────────────────────────────────────────────
    if not force:
        cached = _find_plan_by_hash(ctx_hash, db)
        if cached:
            log.info("Cache HIT — reusing plan %s", cached["plan_id"])
            try:
                return PlanDecision.model_validate(cached["plan"])
            except ValidationError:
                log.warning("Cached plan failed validation, re-generating")

    # ── Build prompt ───────────────────────────────────────────────────────
    ws = _resolve_week_start(week_start)
    we = ws + timedelta(days=6)

    user_prompt = (
        f"Plan the week {ws.isoformat()} to {we.isoformat()}.\n\n"
        f"CONTEXT PACKET:\n{json.dumps(context_packet, default=str, indent=2)}\n\n"
        f"{_PLAN_SCHEMA_HINT}"
    )

    # ── Call LLM ──────────────────────────────────────────────────────────
    raw = _call_llm(_SYSTEM_PLAN_WEEK, user_prompt)
    decision = _parse_and_validate_plan(raw, ctx_hash)

    # ── Persist ───────────────────────────────────────────────────────────
    plan_id = insert_plan(
        start_date=ws,
        end_date=we,
        plan_json=decision.model_dump(),
        context_hash=ctx_hash,
        status="draft",
        db_path=db,
    )
    insert_plan_days(plan_id, decision.as_plan_days_rows(), db_path=db)
    set_active_plan(plan_id, db_path=db)

    # ── Vault ──────────────────────────────────────────────────────────────
    decision_record = {
        "type":       "plan_generated",
        "plan_id":    plan_id,
        "week_start": ws.isoformat(),
        "week_end":   we.isoformat(),
        "phase":      decision.phase,
        "volume_mi":  decision.weekly_volume_miles,
        "summary":    f"{decision.phase} week {ws.isoformat()}",
        "safety_flags": decision.safety_flags,
    }
    append_decision(decision_record, rationale=decision.rationale[:300])
    write_plan_snapshot(
        plan_id=plan_id,
        summary=(
            f"Phase: {decision.phase} | "
            f"Week: {ws.isoformat()}–{we.isoformat()} | "
            f"Volume: {decision.weekly_volume_miles:.1f} mi"
        ),
        plan_data=decision.model_dump(),
    )

    log.info("plan_week persisted plan_id=%s", plan_id)
    return decision


def _parse_and_validate_plan(raw: str, ctx_hash: str) -> PlanDecision:
    """
    Extract JSON from LLM output, validate with Pydantic.
    On failure: one reprompt "Fix JSON only". Raises on second failure.
    """
    for attempt in range(2):
        try:
            json_str = _extract_json(raw)
            data = json.loads(json_str)
            data.setdefault("context_hash", ctx_hash)
            # Truncate string fields to schema limits before validation.
            # LLMs reliably exceed char caps; truncation is cheaper than reprompts.
            data = _truncate_plan_data(data)
            return PlanDecision.model_validate(data)
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            if attempt == 0:
                log.warning("plan parse attempt 1 failed: %s — reprompting", exc)
                fix_prompt = _FIX_JSON_PROMPT.format(error=str(exc)[:200])
                raw = _call_llm(_SYSTEM_PLAN_WEEK, f"{fix_prompt}\n\nPrevious output:\n{raw}")
            else:
                raise RuntimeError(
                    f"Brain returned invalid JSON after reprompt: {exc}\n\nRaw:\n{raw[:500]}"
                ) from exc

    raise RuntimeError("unreachable")  # mypy


# ── adjust_today ──────────────────────────────────────────────────────────────

def adjust_today(
    context_packet: Dict,
    db_path=None,
) -> TodayAdjustment:
    """
    Generate a readiness-based adjustment for today's workout.

    Does not create a new plan version.
    Persists the decision to the vault only.

    Returns:
        TodayAdjustment — validated Pydantic object.
    """
    from memory.vault import append_decision

    _log_packet_stats(context_packet)

    today_str = context_packet.get("today", date.today().isoformat())

    # Original intent from active plan
    original_intent = None
    active = context_packet.get("active_plan")
    if isinstance(active, dict):
        for d in active.get("days", []):
            if d.get("day") == today_str:
                original_intent = d.get("intent")
                break

    user_prompt = (
        f"Today is {today_str}. "
        + (f"Original planned workout: {original_intent}. " if original_intent else "")
        + f"Adjust today's workout based on current readiness.\n\n"
        f"CONTEXT PACKET:\n{json.dumps(context_packet, default=str, indent=2)}\n\n"
        f"{_ADJUST_SCHEMA_HINT}"
    )

    raw = _call_llm(_SYSTEM_ADJUST_TODAY, user_prompt)
    adjustment = _parse_and_validate_adjustment(raw, today_str, original_intent)

    # Persist to vault only
    append_decision(
        {
            "type":             "today_adjustment",
            "date":             today_str,
            "original_intent":  adjustment.original_intent,
            "adjusted_intent":  adjustment.adjusted_intent,
            "adjustment_reason": adjustment.adjustment_reason,
            "safety_flags":     adjustment.safety_flags,
        },
        rationale=adjustment.rationale[:200],
    )

    log.info(
        "adjust_today date=%s type=%s reason=%s",
        today_str, adjustment.workout_type, adjustment.adjustment_reason,
    )
    return adjustment


def _parse_and_validate_adjustment(
    raw: str, today_str: str, original_intent: Optional[str]
) -> TodayAdjustment:
    """Extract + validate TodayAdjustment. One reprompt on failure."""
    for attempt in range(2):
        try:
            json_str = _extract_json(raw)
            data = json.loads(json_str)
            data.setdefault("date", today_str)
            if original_intent and not data.get("original_intent"):
                data["original_intent"] = original_intent
            data = _truncate_adjustment_data(data)
            return TodayAdjustment.model_validate(data)
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            if attempt == 0:
                log.warning("adjust parse attempt 1 failed: %s — reprompting", exc)
                fix_prompt = _FIX_JSON_PROMPT.format(error=str(exc)[:200])
                raw = _call_llm(_SYSTEM_ADJUST_TODAY, f"{fix_prompt}\n\nPrevious output:\n{raw}")
            else:
                raise RuntimeError(
                    f"Brain returned invalid adjustment JSON after reprompt: {exc}"
                ) from exc

    raise RuntimeError("unreachable")  # mypy
