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

DATA QUALITY RULE:
If data_quality.readiness_confidence == "low":
  - Reduce intensity by one level (e.g., planned tempo → easy with strides).
  - Keep running day count per athlete.weekly_structure.runs_per_week.
  - Do NOT increase volume vs training_summary.total_miles baseline.
  - Preserve quality session if macro permits; reduce duration/intensity rather
    than eliminating it entirely.
  - Add "low_readiness_confidence" to plan-level safety_flags.
If data_quality.has_health_cache is false:
  - Treat as low readiness confidence regardless of other signals.

RACE RULES (check context_packet.upcoming_races before planning):
- Race day itself → workout_type "rest", intent "Race day — {race name}", duration_min 0.
- Week containing a race → taper phase; no hard sessions in the 2 days before race day.
- If upcoming_races is empty, plan normally.

MACRO PLAN RULES (check context_packet.macro_guidance):
If macro_guidance is present and non-null:
  - phase SHOULD match macro_guidance.current_week.phase.
    Deviate only if: readiness severely degraded, constraint blocks required session
    types, or race just completed. On deviation add "macro_deviation" to safety_flags
    and explain in rationale.
  - weekly_volume_miles: target macro_guidance.current_week.target_volume_miles.
    May reduce up to 20% for low readiness. Never EXCEED the target.
  - quality_sessions: do NOT exceed quality_sessions_allowed. If 0, easy/rest/cross only.
  - long run: do NOT exceed long_run_max_min minutes.
  - paces: use macro_guidance.current_week.paces for all target_value fields.
  - Follow planner_notes literally unless a safety rule overrides.
  - Add "macro_guided" to plan-level safety_flags when macro_guidance is applied.
If macro_guidance is null: infer phase from race proximity and training history.

ATHLETE STRUCTURE RULES (check context_packet.athlete.weekly_structure):
- Total running days MUST equal athlete.weekly_structure.runs_per_week (default 4).
- Include exactly 1 quality session per week during quality/race_specific phase,
  unless macro quality_sessions_allowed == 0 OR BOTH of these are true:
  training_readiness < 40 AND RHR is elevated > 5 bpm above baseline.
  A single low-confidence signal is NOT enough to drop the quality session — reduce
  it instead (shorter duration, lower intensity).
- Quality session must be harder than or equal to last week's quality in total
  quality volume. Never regress without a documented reason in rationale.
- Remaining running days = easy or long. Place around constraint dates.

RPE RULES (check context_packet.rpe_history):
If rpe_history is present and session_count >= 3:
  - "easy_rpe_elevated" in flags → easy runs feel harder than expected.
    Reduce E-pace target by 15–20 sec/mi. Note in rationale. Do NOT increase volume.
  - "quality_rpe_low" in flags → quality sessions feel too easy.
    Increase quality duration or reps by ~10%. Note potential fitness improvement ahead of VDOT update.
  - "high_overall_effort" in flags → athlete is working hard across all run types.
    Reduce week volume by 5–10% vs macro target. Keep quality session but shorten.
    Add "high_overall_rpe" to safety_flags.
  - "watch_harder_than_reported" in flags → watch self-eval is consistently harder than
    what athlete tells the coach. Trust the watch. Apply same adjustments as easy_rpe_elevated
    or high_overall_effort as appropriate. Note in rationale.
  - "watch_easier_than_reported" in flags → athlete reports harder to coach than watch shows.
    No load adjustment needed.
If rpe_history is absent or session_count < 3: ignore RPE signal, plan from readiness only.

OUTPUT RULES:
- Output ONLY a single JSON object. No markdown fences. No prose.
- Every field in the schema is required unless marked Optional.
- Rationale fields: max 200 chars each (300 for top-level).
- structure_steps: easy/recovery runs → single "main" step only (no warmup/cooldown). Tempo/interval/long runs → warmup + main/intervals + cooldown. Rest/cross days → empty array.
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


def _call_llm(system: str, user: str, timeout: int = 120, model: Optional[str] = None) -> str:
    """
    Call Claude CLI in headless mode. Returns raw text output.
    Raises RuntimeError on non-zero exit or empty response.

    Args:
        model: Optional model alias or full ID (e.g. "haiku", "sonnet",
               "claude-haiku-4-5-20251001"). When None, the CLI uses its
               default model (currently Sonnet 4.6).

    SDK fallback is opt-in: set BRAIN_ALLOW_SDK_FALLBACK=1 to enable.
    When set, the SDK is used directly (bypassing the CLI entirely).
    Useful when running inside a Claude Code session where nested CLI
    calls are blocked.
    """
    if os.environ.get("BRAIN_ALLOW_SDK_FALLBACK") == "1":
        return _call_anthropic_sdk(system, user, model=model)

    claude = _find_claude()
    if claude is None:
        raise RuntimeError(
            "claude CLI not found. Searched:\n  "
            + "\n  ".join(str(p) for p in CLAUDE_PATHS)
            + "\nFix: install claude CLI at one of the above paths, "
            "or set BRAIN_ALLOW_SDK_FALLBACK=1 to enable the anthropic SDK fallback."
        )

    full_prompt = f"{system}\n\n{user}"
    log.debug("Calling claude CLI, prompt_len=%d chars, model=%s", len(full_prompt), model or "default")

    # Strip CLAUDECODE so the subprocess is not treated as a nested session.
    # This is the documented bypass: the child process is headless/one-shot
    # and does not share interactive state with the parent session.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    cmd = [claude, "-p", full_prompt, "--output-format", "text"]
    if model:
        cmd += ["--model", model]

    result = subprocess.run(
        cmd,
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


def _call_anthropic_sdk(system: str, user: str, model: Optional[str] = None) -> str:
    """Fallback LLM call: tries anthropic SDK first, then Gemini."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            import anthropic  # type: ignore
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=model or MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text
        except Exception as e:
            log.warning("anthropic SDK call failed (%s), trying Gemini", e)

    # Gemini fallback
    return _call_gemini(system, user)


def _call_gemini(system: str, user: str) -> str:
    """Call Gemini API using the project's configured key."""
    import urllib.request as _req
    import urllib.error as _uerr

    gemini_env = PROJECT_ROOT / "config" / "gemini_api.env"
    gemini_key = ""
    if gemini_env.exists():
        for line in gemini_env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                gemini_key = line.split("=", 1)[1].strip()
    gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY", "")
    if not gemini_key:
        raise RuntimeError("No LLM backend available: no ANTHROPIC_API_KEY and no GEMINI_API_KEY")

    import json as _json
    url = (
        f"https://generativelanguage.googleapis.com/v1/models/"
        f"gemini-2.0-flash:generateContent?key={gemini_key}"
    )
    # v1 API does not support system_instruction — prepend system as context
    combined = f"{system}\n\n{user}"
    payload = _json.dumps({
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {"maxOutputTokens": 4096},
    }).encode()
    request = _req.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with _req.urlopen(request, timeout=120) as resp:
            data = _json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except _uerr.HTTPError as e:
        raise RuntimeError(f"Gemini API error {e.code}: {e.read()[:300]}")


# ── JSON extraction ────────────────────────────────────────────────────────────

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```$", re.MULTILINE)


def _try_strict_extract(text: str) -> Optional[str]:
    """
    Strict extraction: strip fences, then accept ONLY if the result starts
    with '{' and ends with '}'. Returns None if the output is not clean JSON.
    """
    s = _JSON_FENCE_RE.sub("", text).strip()
    if s.startswith("{") and s.endswith("}"):
        return s
    return None


def _brace_search_last(text: str) -> str:
    """
    Last-resort extraction: find the LAST top-level balanced JSON object.

    Scans BACKWARD from the last '}' to its matching '{'.  This correctly
    handles nested braces (rfind('{') would land inside a nested object and
    return a fragment, not the root object).

    Raises ValueError if no balanced object is found.
    """
    last_close = text.rfind("}")
    if last_close == -1:
        raise ValueError(f"No JSON object found in output:\n{text[:300]}")
    depth = 0
    for i in range(last_close, -1, -1):
        ch = text[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                return text[i : last_close + 1]
    raise ValueError(f"Unbalanced JSON braces in output:\n{text[:300]}")


def _extract_or_reprompt(raw: str, system: str) -> str:
    """
    Three-step JSON extraction with one format reprompt:
      1. Strict: text must start/end with { / } after fence stripping.
      2. Format reprompt: 'Output JSON only. No text, no markdown.'
      3. Last-resort brace search on the reprompted output.

    Returns a JSON string. Raises ValueError on complete failure.
    """
    strict = _try_strict_extract(raw)
    if strict is not None:
        return strict

    # Step 2: one format-level reprompt
    log.warning("LLM output not clean JSON (len=%d) — reprompting for format", len(raw))
    reprompted = _call_llm(
        system,
        "Output JSON only. No text, no markdown. No explanation.\n\nPrevious output:\n" + raw[:500],
    )
    strict2 = _try_strict_extract(reprompted)
    if strict2 is not None:
        log.info("Format reprompt succeeded")
        return strict2

    # Step 3: last resort — search reprompted output for last balanced object
    log.warning("Strict extract failed after format reprompt — using brace search")
    return _brace_search_last(reprompted)


# ── Observability ──────────────────────────────────────────────────────────────

_EXPECTED_PACKET_KEYS = {
    "today", "athlete", "training_summary", "readiness_trend",
    "plan_authority", "active_plan", "macro_guidance", "constraints",
    "recent_decisions", "vault_excerpts", "data_quality",
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
    """Return the upcoming Sunday for the planning week (weeks run Sun–Sat).

    If called on Saturday, returns tomorrow (the start of next week).
    If called on Sunday, returns today.
    Any other day returns the coming Sunday.
    """
    if week_start is not None:
        return week_start
    today = date.today()
    # weekday(): 0=Mon … 5=Sat, 6=Sun
    # Days until next Sunday: (6 - today.weekday()) % 7
    # → Sun=0 (today), Mon=6, Tue=5, …, Sat=1
    days_ahead = (6 - today.weekday()) % 7
    return today + timedelta(days=days_ahead)


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
        week_start:     Sunday of the week to plan (default: upcoming Sunday).
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
    raw = _call_llm(_SYSTEM_PLAN_WEEK, user_prompt, timeout=300, model="claude-haiku-4-5-20251001")
    decision = _parse_and_validate_plan(raw, ctx_hash, _SYSTEM_PLAN_WEEK)
    decision = _enforce_stride_rules(decision)

    # ── Enforce DATA QUALITY safety flag deterministically ─────────────────
    # The LLM prompt asks for this flag, but we cannot rely on the LLM.
    # Append it here unconditionally when the condition is true.
    dq = context_packet.get("data_quality", {})
    _low_conf = (
        dq.get("readiness_confidence") == "low"
        or not dq.get("has_health_cache", True)
    )
    if _low_conf and "low_readiness_confidence" not in decision.safety_flags:
        decision.safety_flags.append("low_readiness_confidence")
        log.info("Enforced low_readiness_confidence safety flag")

    # ── Enforce macro_guided flag deterministically ─────────────────────────
    # When macro_guidance is present (not None, not truncated), always mark.
    mg = context_packet.get("macro_guidance")
    if isinstance(mg, dict) and not mg.get("_truncated"):
        if "macro_guided" not in decision.safety_flags:
            decision.safety_flags.append("macro_guided")
            log.info("Enforced macro_guided safety flag")

        # ── Enforce macro volume cap ─────────────────────────────────────
        # The LLM prompt says "Never exceed the target", but we cannot
        # fully rely on that. Flag over-volume plans for operator visibility.
        # We do NOT silently clamp — the flag triggers a warning, letting the
        # weekly planner rationale (and the human reviewer) see the overage.
        macro_target_vol = (
            mg.get("current_week", {}).get("target_volume_miles")
        )
        if (
            macro_target_vol is not None
            and isinstance(macro_target_vol, (int, float))
            and decision.weekly_volume_miles > macro_target_vol + 0.5  # 0.5 mi tolerance
        ):
            if "macro_cap_exceeded" not in decision.safety_flags:
                decision.safety_flags.append("macro_cap_exceeded")
                log.warning(
                    "macro_cap_exceeded: plan volume %.1f mi exceeds macro target %.1f mi",
                    decision.weekly_volume_miles, macro_target_vol,
                )
            # Clamp to macro ceiling — macro is authoritative; readiness/constraints
            # can reduce volume below target but never increase it above.
            decision.weekly_volume_miles = float(macro_target_vol)
            if "macro_cap_clamped" not in decision.safety_flags:
                decision.safety_flags.append("macro_cap_clamped")
                log.info(
                    "macro_cap_clamped: weekly_volume_miles clamped to %.1f mi",
                    macro_target_vol,
                )

    # ── Persist ───────────────────────────────────────────────────────────
    plan_id = insert_plan(
        start_date=ws,
        end_date=we,
        plan_json=decision.model_dump(),
        context_hash=ctx_hash,
        status="draft",
        db_path=db,
    )
    # Only persist days that are today or in the future (never backfill past days)
    today_iso = date.today().isoformat()
    future_rows = [r for r in decision.as_plan_days_rows() if r["day"] >= today_iso]
    insert_plan_days(plan_id, future_rows, db_path=db)
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


def _enforce_stride_rules(decision: PlanDecision) -> PlanDecision:
    """
    Post-LLM enforcement: for every 'easy' day whose intent mentions strides,
    validate the structure_steps.  If invalid (multi-minute interval reps that
    cannot be strides), apply a deterministic rewrite to canonical 6×20 s format.

    This runs AFTER Pydantic validation so the decision is already structurally
    sound.  It only mutates days that fail stride validation.
    """
    from .stride_rules import is_stride_intent, validate_strides, rewrite_strides
    from .schemas import WorkoutStep

    for day in decision.days:
        if day.workout_type != "easy":
            continue
        if not is_stride_intent(day.intent):
            continue

        steps_dicts = [s.model_dump() for s in day.structure_steps]
        ok, reason = validate_strides(steps_dicts)
        if ok:
            continue

        log.warning(
            "Stride rule violation on %s: %s — rewriting",
            day.date, reason,
        )
        new_steps_dicts, rewrite_note = rewrite_strides(steps_dicts, day.duration_min)
        day.structure_steps = [WorkoutStep.model_validate(s) for s in new_steps_dicts]

        flags = list(day.safety_flags)
        if "stride_rewrite_applied" not in flags:
            flags.append("stride_rewrite_applied")
        day.safety_flags = flags

        log.info("Stride rewrite applied on %s: %s", day.date, rewrite_note)

    return decision


def _parse_and_validate_plan(raw: str, ctx_hash: str, system: str) -> PlanDecision:
    """
    Extract + validate a PlanDecision from raw LLM output.

    Extraction (up to 2 LLM calls):
      _extract_or_reprompt: strict → format-reprompt → brace-search

    Schema validation (1 additional reprompt on ValidationError):
      Attempt 0 → attempt 1 ("Fix JSON only") → raise
    """
    json_str = _extract_or_reprompt(raw, system)

    for attempt in range(2):
        try:
            data = json.loads(json_str)
            data.setdefault("context_hash", ctx_hash)
            data = _truncate_plan_data(data)
            return PlanDecision.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            if attempt == 0:
                log.warning("plan schema attempt 1 failed: %s — reprompting", exc)
                fix_raw = _call_llm(system, _FIX_JSON_PROMPT.format(error=str(exc)[:200])
                                    + f"\n\nPrevious output:\n{json_str[:500]}")
                json_str = _extract_or_reprompt(fix_raw, system)
            else:
                raise RuntimeError(
                    f"Brain returned invalid plan JSON after reprompts: {exc}\n\nLast:\n{json_str[:400]}"
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
    adjustment = _parse_and_validate_adjustment(raw, today_str, original_intent, _SYSTEM_ADJUST_TODAY)

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
    raw: str, today_str: str, original_intent: Optional[str], system: str
) -> TodayAdjustment:
    """Extract + validate TodayAdjustment. One schema reprompt on failure."""
    json_str = _extract_or_reprompt(raw, system)

    for attempt in range(2):
        try:
            data = json.loads(json_str)
            data.setdefault("date", today_str)
            if original_intent and not data.get("original_intent"):
                data["original_intent"] = original_intent
            data = _truncate_adjustment_data(data)
            return TodayAdjustment.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            if attempt == 0:
                log.warning("adjust schema attempt 1 failed: %s — reprompting", exc)
                fix_raw = _call_llm(system, _FIX_JSON_PROMPT.format(error=str(exc)[:200])
                                    + f"\n\nPrevious output:\n{json_str[:500]}")
                json_str = _extract_or_reprompt(fix_raw, system)
            else:
                raise RuntimeError(
                    f"Brain returned invalid adjustment JSON after reprompts: {exc}"
                ) from exc

    raise RuntimeError("unreachable")  # mypy
