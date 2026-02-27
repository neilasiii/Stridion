"""
Hook: on_obs_missed — detects when the obs_test_task ran but failed to post to Discord.

Called from agent/runner.py each heartbeat cycle (every 15 min).

Logic:
  - Reads data/obs_test_state.json
  - If obs is active (runs > 0) AND it's past 8:30 AM AND last_sent_date < today:
      → runs `coach db sanity` + `coach parity` subprocess checks
      → writes results to SQLite state as pending_obs_result (JSON)
      → Discord bot reads this on next on_ready or sync_digest and posts it

Returns dict: checked (bool), pending_written (bool), reason (str).
"""

import json
import logging
import subprocess
from datetime import date, datetime, time, timezone, timedelta
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent
_OBS_TEST_STATE = PROJECT_ROOT / "data" / "obs_test_state.json"
_STATE_PENDING_KEY = "obs_pending_result"

# Must be past this time before we flag a miss (matches Discord task schedule)
_OBS_SCHEDULED_HOUR = 8
_OBS_SCHEDULED_MIN  = 30
EST = timezone(timedelta(hours=-5))

log = logging.getLogger("hooks.on_obs_missed")


def run(db_path=None) -> Dict[str, Any]:
    """
    Check whether today's obs report was missed and, if so, run the checks
    and write a pending result for the Discord bot to deliver.
    """
    from memory.db import set_state, get_state, DB_PATH as _DEFAULT_DB
    db = db_path or _DEFAULT_DB

    result = {"checked": False, "pending_written": False, "reason": "not_due"}

    # ── 1. Is obs active? ───────────────────────────────────────────────────
    if not _OBS_TEST_STATE.exists():
        result["reason"] = "obs_not_started"
        return result

    try:
        state = json.loads(_OBS_TEST_STATE.read_text())
    except Exception as exc:
        log.warning("Could not read obs state: %s", exc)
        result["reason"] = "state_read_error"
        return result

    runs = state.get("runs", 0)
    if runs == 0:
        result["reason"] = "obs_not_started"
        return result

    # ── 2. Is it past 8:30 AM EST today? ───────────────────────────────────
    now_est = datetime.now(EST)
    cutoff = now_est.replace(hour=_OBS_SCHEDULED_HOUR, minute=_OBS_SCHEDULED_MIN, second=0, microsecond=0)
    if now_est < cutoff:
        result["reason"] = "before_scheduled_time"
        return result

    # ── 3. Was today's result already sent? ─────────────────────────────────
    today_str = date.today().isoformat()
    last_sent = state.get("last_sent_date", "")
    if last_sent == today_str:
        result["reason"] = "already_sent"
        return result

    # ── 4. Is there already a pending result for today? ─────────────────────
    existing_pending = get_state(_STATE_PENDING_KEY, db_path=db)
    if existing_pending:
        try:
            pending = json.loads(existing_pending)
            if pending.get("date") == today_str:
                result["reason"] = "pending_already_written"
                return result
        except Exception:
            pass  # malformed — overwrite below

    # ── 5. Run checks ────────────────────────────────────────────────────────
    result["checked"] = True
    log.info("obs missed for %s (runs=%d, last_sent=%r) — running checks", today_str, runs, last_sent)

    rc_sanity, out_sanity = _run_coach(["db", "sanity"])
    rc_parity, out_parity = _run_coach(["parity", "--day", today_str])

    sanity_pass = rc_sanity == 0
    parity_pass = rc_parity == 0
    overall_pass = sanity_pass and parity_pass

    pending_payload = {
        "date":         today_str,
        "run_number":   runs,
        "overall_pass": overall_pass,
        "sanity_pass":  sanity_pass,
        "parity_pass":  parity_pass,
        "rc_sanity":    rc_sanity,
        "rc_parity":    rc_parity,
        "out_sanity":   out_sanity[:800],
        "out_parity":   out_parity[:400] if not parity_pass else "",
        "detected_by":  "heartbeat_agent",
    }

    set_state(_STATE_PENDING_KEY, json.dumps(pending_payload), db_path=db)
    result["pending_written"] = True
    result["reason"] = "pending_written"
    log.info(
        "obs pending result written: sanity=%s parity=%s overall=%s",
        "PASS" if sanity_pass else "FAIL",
        "PASS" if parity_pass else "FAIL",
        "PASS" if overall_pass else "FAIL",
    )
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_coach(args: list) -> tuple[int, str]:
    """Run `python3 cli/coach.py <args>` and return (returncode, stdout)."""
    try:
        proc = subprocess.run(
            ["python3", str(PROJECT_ROOT / "cli" / "coach.py")] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        return proc.returncode, proc.stdout
    except Exception as exc:
        log.error("coach CLI error (%s): %s", args, exc)
        return 1, str(exc)
