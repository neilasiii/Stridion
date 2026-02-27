"""
Hook: on_weekly_rollup — generates a weekly synthesis message on Saturday
evenings and queues it for Discord delivery.

Called unconditionally from agent/runner.py run_cycle(), same as
on_constraints_change. Only acts when:
  - datetime.now().weekday() == 5 (Saturday)
  - datetime.now().hour >= 19
  - No runner_last_weekly_rollup state key for today

Requires:
  - An active plan that covers the upcoming week (Saturday plan task must
    have already generated it). If not present, skips and retries next cycle.

Logic:
  1. Guard: day/time check + idempotency.
  2. Verify upcoming week is covered by the active plan.
  3. Collect last 7 days: activities, checkins (with RPE), daily metrics.
  4. Collect this past week's and next week's plan days.
  5. Call Brain LLM with synthesis prompt.
  6. Write result to state: pending_weekly_synthesis.
  7. Mark runner_last_weekly_rollup = today.

Returns: {ran: bool, synthesis_written: bool, skip_reason: str|None}
"""

import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_STATE_PENDING_KEY    = "pending_weekly_synthesis"
_STATE_LAST_ROLLUP    = "runner_last_weekly_rollup"
_TRIGGER_WEEKDAY      = 5    # Saturday
_TRIGGER_HOUR         = 19   # 7 PM local

log = logging.getLogger("hooks.on_weekly_rollup")

CLAUDE_PATHS = [
    Path.home() / ".local" / "bin" / "claude",
    Path("/usr/local/bin/claude"),
    Path("/usr/bin/claude"),
]

_SYNTHESIS_SYSTEM = """\
You are a running coach AI. Write a concise weekly synthesis message for the athlete.

FORMAT:
- 2-3 sentences summarizing last week (total load, how hard it felt based on RPE data, recovery pattern)
- 1 sentence noting any patterns (e.g., HRV drift, RPE trend, sleep issues)
- 2-3 sentences previewing next week's plan, highlighting the key quality session

TONE: Direct, practical, coach-like. Not overly positive. Max 200 words.
Do NOT include JSON or headers — plain prose only.
"""


def _find_claude() -> Optional[str]:
    for p in CLAUDE_PATHS:
        if p.exists():
            return str(p)
    return None


def _call_llm(prompt: str, timeout: int = 90) -> str:
    """Call claude CLI in headless mode. Returns raw text."""
    if os.environ.get("BRAIN_ALLOW_SDK_FALLBACK") == "1":
        return _call_sdk_fallback(prompt)

    claude = _find_claude()
    if claude is None:
        raise RuntimeError("claude CLI not found")

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    result = subprocess.run(
        [claude, "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:200]}")
    text = result.stdout.strip()
    if not text:
        raise RuntimeError("claude CLI returned empty response")
    return text


def _call_sdk_fallback(prompt: str) -> str:
    """Fallback: anthropic SDK or Gemini."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            import anthropic  # type: ignore
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=_SYNTHESIS_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            log.warning("anthropic SDK failed: %s", e)

    # Gemini fallback
    gemini_env = PROJECT_ROOT / "config" / "gemini_api.env"
    gemini_key = ""
    if gemini_env.exists():
        for line in gemini_env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                gemini_key = line.split("=", 1)[1].strip()
    gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY", "")
    if not gemini_key:
        raise RuntimeError("No LLM backend available")

    import urllib.request as _req
    import json as _json
    url = (
        f"https://generativelanguage.googleapis.com/v1/models/"
        f"gemini-2.0-flash:generateContent?key={gemini_key}"
    )
    payload = _json.dumps({
        "contents": [{"parts": [{"text": f"{_SYNTHESIS_SYSTEM}\n\n{prompt}"}]}]
    }).encode()
    req = _req.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with _req.urlopen(req, timeout=30) as resp:
        body = _json.loads(resp.read())
    return body["candidates"][0]["content"]["parts"][0]["text"].strip()


def run(db_path=None) -> Dict[str, Any]:
    """
    Generate weekly synthesis if timing and guard conditions are met.
    Returns: {ran: bool, synthesis_written: bool, skip_reason: str|None}
    """
    from memory.db import (
        get_state, set_state, get_activities, get_weekly_rpe_summary,
        get_daily_metrics, get_active_plan, get_active_plan_range,
        DB_PATH as _DEFAULT_DB,
    )

    db = db_path or _DEFAULT_DB
    result: Dict[str, Any] = {
        "ran": False,
        "synthesis_written": False,
        "skip_reason": None,
    }

    # ── 1. Guard: day/time check ───────────────────────────────────────────
    now = datetime.now()
    if now.weekday() != _TRIGGER_WEEKDAY:
        result["skip_reason"] = f"not_saturday (weekday={now.weekday()})"
        return result
    if now.hour < _TRIGGER_HOUR:
        result["skip_reason"] = f"too_early (hour={now.hour})"
        return result

    # ── 1b. Idempotency: only run once per Saturday ────────────────────────
    last_rollup = get_state(_STATE_LAST_ROLLUP, db_path=db)
    today_str = date.today().isoformat()
    if last_rollup == today_str:
        result["skip_reason"] = "already_ran_today"
        return result

    result["ran"] = True

    # ── 2. Verify upcoming week is covered by the active plan ──────────────
    plan_range = get_active_plan_range(db_path=db)
    next_monday = date.today() + timedelta(days=(7 - now.weekday()))
    if not plan_range or plan_range[1] < next_monday.isoformat():
        result["skip_reason"] = "next_week_not_planned_yet"
        log.debug("on_weekly_rollup: next week not yet in plan — deferring")
        # Don't mark as done — retry next cycle
        result["ran"] = False
        return result

    # ── 3. Collect last 7 days of data ─────────────────────────────────────
    week_start = date.today() - timedelta(days=6)  # Mon through today (Sat)
    week_end   = date.today()

    try:
        activities  = get_activities(start=week_start, end=week_end, db_path=db)
    except Exception as exc:
        log.warning("on_weekly_rollup: get_activities failed: %s", exc)
        activities = []

    try:
        checkins = get_weekly_rpe_summary(week_start=week_start, db_path=db)
    except Exception as exc:
        log.warning("on_weekly_rollup: get_weekly_rpe_summary failed: %s", exc)
        checkins = []

    try:
        metrics = get_daily_metrics(start=week_start, end=week_end, db_path=db)
    except Exception as exc:
        log.warning("on_weekly_rollup: get_daily_metrics failed: %s", exc)
        metrics = []

    # ── 4. Collect plan days ────────────────────────────────────────────────
    past_plan: List[Dict] = []
    next_plan: List[Dict] = []
    try:
        past = get_active_plan(start=week_start, end=week_end, db_path=db)
        if past:
            past_plan = past.get("days", [])
    except Exception as exc:
        log.warning("on_weekly_rollup: get_active_plan (past) failed: %s", exc)

    try:
        next_end = next_monday + timedelta(days=6)
        upcoming = get_active_plan(start=next_monday, end=next_end, db_path=db)
        if upcoming:
            next_plan = upcoming.get("days", [])
    except Exception as exc:
        log.warning("on_weekly_rollup: get_active_plan (next) failed: %s", exc)

    # ── 5. Build summary dicts (lightweight for prompt) ───────────────────
    act_summary = [
        {
            "date": a.get("activity_date"),
            "type": a.get("activity_type"),
            "name": a.get("name"),
            "distance_mi": round(a["distance_m"] / 1609.344, 2) if a.get("distance_m") else None,
            "duration_min": round(a["duration_s"] / 60, 1) if a.get("duration_s") else None,
            "avg_hr": a.get("avg_hr"),
        }
        for a in activities
    ]

    checkin_summary = [
        {
            "date": c.get("activity_date"),
            "type": c.get("activity_type"),
            "name": c.get("activity_name"),
            "rpe":  c.get("rpe"),
            "notes": c.get("effort_notes"),
        }
        for c in checkins
    ]

    metrics_summary = [
        {
            "date": m.get("day"),
            "hrv":  m.get("hrv_rmssd"),
            "rhr":  m.get("resting_hr"),
            "sleep_score": m.get("sleep_score"),
            "sleep_h":     m.get("sleep_duration_h"),
            "body_battery": m.get("body_battery"),
        }
        for m in metrics
    ]

    past_plan_summary = [
        {"date": d["day"], "intent": d["intent"]}
        for d in past_plan
    ]

    next_plan_summary = [
        {"date": d["day"], "intent": d["intent"]}
        for d in next_plan
    ]

    user_prompt = f"""{_SYNTHESIS_SYSTEM}

DATA — LAST WEEK ({week_start} to {week_end}):

Activities completed:
{json.dumps(act_summary, indent=2)}

Check-in responses (RPE and notes):
{json.dumps(checkin_summary, indent=2)}

Daily recovery metrics (HRV, RHR, sleep, body battery):
{json.dumps(metrics_summary, indent=2)}

Last week's planned workouts:
{json.dumps(past_plan_summary, indent=2)}

NEXT WEEK'S PLAN ({next_monday} to {(next_monday + timedelta(days=6))}):
{json.dumps(next_plan_summary, indent=2)}

Write the weekly synthesis now."""

    # ── 6. Call Brain LLM ─────────────────────────────────────────────────
    try:
        synthesis_text = _call_llm(user_prompt)
        log.info("on_weekly_rollup: synthesis generated (%d chars)", len(synthesis_text))
    except Exception as exc:
        log.error("on_weekly_rollup: LLM call failed: %s", exc)
        result["skip_reason"] = f"llm_error: {exc}"
        # Mark done anyway to avoid retry loop on LLM outage
        set_state(_STATE_LAST_ROLLUP, today_str, db_path=db)
        return result

    # ── 7. Write to state ─────────────────────────────────────────────────
    try:
        payload = {
            "date": today_str,
            "text": synthesis_text,
        }
        set_state(_STATE_PENDING_KEY, json.dumps(payload), db_path=db)
        result["synthesis_written"] = True
        log.info("on_weekly_rollup: pending_weekly_synthesis written")
    except Exception as exc:
        log.error("on_weekly_rollup: could not write pending_weekly_synthesis: %s", exc)

    # ── 8. Mark done for today ─────────────────────────────────────────────
    try:
        set_state(_STATE_LAST_ROLLUP, today_str, db_path=db)
    except Exception as exc:
        log.warning("on_weekly_rollup: could not mark rollup done: %s", exc)

    return result
