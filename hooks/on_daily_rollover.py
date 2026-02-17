"""
Hook: on_daily_rollover — runs once per calendar day (at 4am local by the runner).

Actions (deterministic except vault write):
  1. Write vault/daily/YYYY-MM-DD.md with brief context summary.
  2. Check whether the active plan is stale (end_date within 2 days or absent).

Returns:
    {
        "vault_written": bool,
        "plan_is_stale": bool,
        "plan_id":       str | None,
        "today":         "YYYY-MM-DD",
    }

The runner uses plan_is_stale to decide whether to call brain.plan_week().
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict

log = logging.getLogger("hooks.on_daily_rollover")

_STALE_THRESHOLD_DAYS = 2  # plan ending within this many days is considered stale


def run(db_path=None) -> Dict[str, Any]:
    from memory.db import get_active_plan_range, get_active_plan_id, DB_PATH as _DEFAULT_DB
    from memory.vault import write_daily_note

    db = db_path or _DEFAULT_DB
    today = date.today()

    # ── Vault daily note ───────────────────────────────────────────────────
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent
    note_path = PROJECT_ROOT / "vault" / "daily" / f"{today.isoformat()}.md"
    vault_written = False

    if not note_path.exists():
        content = _build_daily_note(today, db)
        write_daily_note(today, content)
        vault_written = True
        log.info("Daily vault note written for %s", today.isoformat())
    else:
        log.debug("Daily note already exists for %s — skipping", today.isoformat())

    # ── Plan staleness check ───────────────────────────────────────────────
    plan_id = get_active_plan_id(db_path=db)
    plan_is_stale = _check_plan_stale(db)

    if plan_is_stale:
        log.info("Plan staleness detected: plan_id=%s — runner should call plan_week", plan_id)

    return {
        "vault_written": vault_written,
        "plan_is_stale": plan_is_stale,
        "plan_id":       plan_id,
        "today":         today.isoformat(),
    }


def _check_plan_stale(db_path=None) -> bool:
    """Return True if no active plan exists or plan ends within threshold days."""
    from memory.db import get_active_plan_range, DB_PATH as _DEFAULT_DB

    rng = get_active_plan_range(db_path=db_path or _DEFAULT_DB)
    if rng is None:
        log.info("No active plan in SQLite")
        return True
    try:
        _, end_str = rng
        end = date.fromisoformat(end_str)
        stale = end < date.today() + timedelta(days=_STALE_THRESHOLD_DAYS)
        log.debug("Active plan ends %s — stale=%s", end_str, stale)
        return stale
    except (ValueError, TypeError) as exc:
        log.warning("Could not parse plan end date %r: %s", rng, exc)
        return True


def _build_daily_note(today: date, db_path=None) -> str:
    """Build a brief daily note from the context packet summary."""
    try:
        from memory.retrieval import build_context_packet

        ctx = build_context_packet(db_path=db_path)
        dq = ctx.get("data_quality", {})
        ta = ctx.get("today", today.isoformat())
        pa = ctx.get("plan_authority", {})
        rt = ctx.get("readiness_trend", {})
        today_rt = rt.get("today", {}) if isinstance(rt, dict) else {}

        readiness = today_rt.get("training_readiness", "—")
        battery = today_rt.get("body_battery_max", "—")
        hrv = today_rt.get("hrv", "—")
        sleep = today_rt.get("sleep_hours", "—")
        confidence = dq.get("readiness_confidence", "unknown")

        plan_id = pa.get("active_plan_id", "none")
        plan_range = pa.get("active_plan_range")

        lines = [
            f"# Daily Note — {today.isoformat()}",
            "",
            "## Recovery Summary",
            "",
            f"- **Training Readiness**: {readiness}",
            f"- **Body Battery**: {battery}",
            f"- **HRV**: {hrv}",
            f"- **Sleep**: {sleep}h",
            f"- **Data confidence**: {confidence}",
            "",
            "## Active Plan",
            "",
            f"- **Plan ID**: {plan_id}",
            f"- **Range**: {plan_range}",
            "",
            "## Coach Notes",
            "",
            "_Add notes here. They will be included in the next Brain context packet._",
        ]
        return "\n".join(lines)

    except Exception as exc:
        log.warning("Could not build full daily note (using stub): %s", exc)
        return "\n".join([
            f"# Daily Note — {today.isoformat()}",
            "",
            "_Context packet unavailable — check data sync._",
            "",
            "## Coach Notes",
            "",
        ])
