#!/usr/bin/env python3
"""
Heartbeat runner for the running coach system.

Loop interval: 15 minutes.
Daily deep run:  4am local time (daily rollover + stale plan check).

Lock: SQLite state key "runner_lock" — prevents concurrent instances and
      concurrent Discord-bot export/sync from colliding.

Brain calls (intentionally rare — only when needed):
  - Context hash changed materially → on_readiness_change may call adjust_today
  - Daily deep run + stale plan → plan_week
  No speculative LLM calls.

Usage:
    python3 agent/runner.py                # run forever
    python3 agent/runner.py --once         # one cycle and exit (same as coach agent run-once)
    python3 agent/runner.py --daily        # force a daily-deep run and exit
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("agent.runner")

LOOP_INTERVAL_SEC = 15 * 60   # 15 minutes
DAILY_HOUR_LOCAL  = 4         # 4am local — trigger daily deep run

# State keys
_STATE_LAST_HASH       = "runner_last_context_hash"
_STATE_LAST_ROLLOVER   = "runner_last_daily_rollover"
_STATE_LAST_SYNC       = "runner_last_sync_ts"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _owner() -> str:
    return f"runner:{os.getpid()}"


def _should_do_daily_deep(db_path=None) -> bool:
    """Return True if daily deep run has not yet happened today."""
    from memory.db import get_state, DB_PATH

    raw = get_state(_STATE_LAST_ROLLOVER, db_path=db_path or DB_PATH)
    return raw != date.today().isoformat()


def _mark_daily_done(db_path=None) -> None:
    from memory.db import set_state, DB_PATH
    set_state(_STATE_LAST_ROLLOVER, date.today().isoformat(), db_path=db_path or DB_PATH)


def _get_last_context_hash(db_path=None) -> str:
    from memory.db import get_state, DB_PATH
    return get_state(_STATE_LAST_HASH, db_path=db_path or DB_PATH) or ""


def _save_context_hash(ctx_hash: str, db_path=None) -> None:
    from memory.db import set_state, DB_PATH
    set_state(_STATE_LAST_HASH, ctx_hash, db_path=db_path or DB_PATH)


# ── Core cycle ────────────────────────────────────────────────────────────────

def run_cycle(db_path=None) -> dict:
    """
    One complete heartbeat cycle.

    Steps:
      1. Acquire SQLite lock (skip cycle if lock held by another process).
      2. Run Garmin sync.
      3. Build context packet + compute hash.
      4. If hash changed: run on_sync hook + on_readiness_change hook.
      5. If inbox notes exist: run on_constraints_change hook.
      6. Release lock.

    Returns summary dict with keys:
        lock_acquired, sync_success, hash_changed, hooks_run, needs_replan,
        readiness_triggered, new_context_hash
    """
    from agent.lock import acquire_lock, release_lock, refresh_lock
    from memory.db import init_db, log_task_start, log_task_finish, DB_PATH as _DEFAULT_DB
    from memory.retrieval import build_context_packet, hash_context_packet

    db = db_path or _DEFAULT_DB
    init_db(db)
    owner = _owner()

    summary = {
        "lock_acquired":        False,
        "sync_success":         False,
        "hash_changed":         False,
        "hooks_run":            [],
        "needs_replan":         False,
        "readiness_triggered":  False,
        "new_context_hash":     None,
    }

    # ── 1. Acquire lock ────────────────────────────────────────────────────
    if not acquire_lock(owner, db_path=db):
        log.info("Lock busy — skipping cycle")
        return summary

    summary["lock_acquired"] = True
    run_id = log_task_start("agent_cycle", db_path=db)

    try:
        # ── 2. Garmin sync ─────────────────────────────────────────────────
        from skills.garmin_sync import run as garmin_run

        log.info("Running Garmin sync…")
        sync_result = garmin_run()
        summary["sync_success"] = sync_result["success"]

        if not sync_result["success"]:
            log.warning("Garmin sync failed — skipping hooks")
            log_task_finish(run_id, "partial", details=summary, db_path=db)
            return summary

        refresh_lock(owner, db_path=db)

        # ── 3. Context packet + hash ────────────────────────────────────────
        ctx = build_context_packet(db_path=db)
        new_hash = hash_context_packet(ctx)
        old_hash = _get_last_context_hash(db)
        hash_changed = new_hash != old_hash
        summary["hash_changed"] = hash_changed
        summary["new_context_hash"] = new_hash[:12]

        # ── 4. Post-sync hooks (if hash changed or first run) ──────────────
        if hash_changed:
            log.info("Context hash changed (%s → %s) — running hooks", old_hash[:12], new_hash[:12])

            # on_sync: metrics rollup + vault stub
            from hooks.on_sync import run as on_sync
            sync_hook = on_sync(db_path=db)
            summary["hooks_run"].append("on_sync")
            log.info("on_sync: metrics_updated=%s vault_written=%s",
                     sync_hook["metrics_updated"], sync_hook["vault_written"])

            refresh_lock(owner, db_path=db)

            # on_readiness_change: may call Brain adjust_today
            from hooks.on_readiness_change import run as on_readiness
            readiness_result = on_readiness(ctx, db_path=db)
            summary["hooks_run"].append("on_readiness_change")
            summary["readiness_triggered"] = readiness_result["triggered"]
            log.info("on_readiness_change: triggered=%s reason=%s",
                     readiness_result["triggered"], readiness_result["reason"])

            _save_context_hash(new_hash, db)
            refresh_lock(owner, db_path=db)

        # ── 5. Constraint inbox check (always) ─────────────────────────────
        from hooks.on_constraints_change import run as on_constraints
        constraints_result = on_constraints(db_path=db)
        if constraints_result["new_constraints"]:
            summary["hooks_run"].append("on_constraints_change")
            summary["needs_replan"] = constraints_result["needs_replan"]
            log.info(
                "on_constraints_change: %d new events, needs_replan=%s",
                len(constraints_result["new_constraints"]),
                constraints_result["needs_replan"],
            )

        log_task_finish(run_id, "success", details=summary, db_path=db)

    except Exception as exc:
        log.exception("Cycle error: %s", exc)
        log_task_finish(
            run_id, "failed",
            details={"error": str(exc), **summary},
            db_path=db,
        )
    finally:
        release_lock(owner, db_path=db)

    return summary


# ── Daily deep run ────────────────────────────────────────────────────────────

def run_daily_deep(db_path=None) -> dict:
    """
    Daily 4am routine.

    Steps:
      1. Acquire lock.
      2. on_daily_rollover: write vault daily note, check plan staleness.
      3. on_constraints_change: ingest inbox.
      4. If plan stale: call brain.plan_week() → insert + activate plan.
      5. Release lock.

    Returns summary dict.
    """
    from agent.lock import acquire_lock, release_lock, refresh_lock
    from memory.db import init_db, log_task_start, log_task_finish, DB_PATH as _DEFAULT_DB
    from memory.retrieval import build_context_packet

    db = db_path or _DEFAULT_DB
    init_db(db)
    owner = _owner()

    summary = {
        "lock_acquired": False,
        "vault_written": False,
        "plan_is_stale": False,
        "new_plan_id":   None,
        "plan_error":    None,
    }

    if not acquire_lock(owner, db_path=db):
        log.warning("Daily deep: lock busy — deferring")
        return summary

    summary["lock_acquired"] = True
    run_id = log_task_start("agent_daily", db_path=db)

    try:
        # ── Daily rollover ─────────────────────────────────────────────────
        from hooks.on_daily_rollover import run as on_rollover
        rollover = on_rollover(db_path=db)
        summary["vault_written"] = rollover["vault_written"]
        summary["plan_is_stale"] = rollover["plan_is_stale"]
        log.info("on_daily_rollover: vault_written=%s plan_is_stale=%s",
                 rollover["vault_written"], rollover["plan_is_stale"])
        _mark_daily_done(db)

        refresh_lock(owner, db_path=db)

        # ── Constraint inbox ───────────────────────────────────────────────
        from hooks.on_constraints_change import run as on_constraints
        on_constraints(db_path=db)

        refresh_lock(owner, db_path=db)

        # ── Re-plan if stale ───────────────────────────────────────────────
        if rollover["plan_is_stale"]:
            log.info("Plan stale — calling brain.plan_week()")
            try:
                from brain import plan_week
                ctx = build_context_packet(db_path=db)
                decision = plan_week(ctx, force=False, db_path=db)
                summary["new_plan_id"] = decision.context_hash[:12]
                log.info(
                    "New plan generated: %s→%s phase=%s vol=%.1fmi",
                    decision.week_start, decision.week_end,
                    decision.phase, decision.weekly_volume_miles,
                )
            except Exception as exc:
                log.error("plan_week failed: %s", exc)
                summary["plan_error"] = str(exc)

        log_task_finish(run_id, "success", details=summary, db_path=db)

    except Exception as exc:
        log.exception("Daily deep error: %s", exc)
        log_task_finish(run_id, "failed", details={"error": str(exc), **summary}, db_path=db)
    finally:
        release_lock(owner, db_path=db)

    return summary


# ── Forever loop ──────────────────────────────────────────────────────────────

def run_forever(db_path=None) -> None:
    """
    Main loop. Runs run_cycle() every LOOP_INTERVAL_SEC.
    At 4am local time (first cycle after 4am that hasn't run daily deep yet):
    also runs run_daily_deep().

    systemd will restart the process on exit; SIGTERM triggers a clean shutdown.
    """
    _shutdown = False

    def _handle_sigterm(sig, frame):
        nonlocal _shutdown
        log.info("SIGTERM received — shutting down after current cycle")
        _shutdown = True

    signal.signal(signal.SIGTERM, _handle_sigterm)

    log.info("Agent runner started (pid=%d, interval=%ds)", os.getpid(), LOOP_INTERVAL_SEC)

    while not _shutdown:
        now_local = datetime.now()

        # Daily deep run at 4am
        if now_local.hour >= DAILY_HOUR_LOCAL and _should_do_daily_deep(db_path):
            log.info("Daily deep run triggered (hour=%d)", now_local.hour)
            run_daily_deep(db_path)

        # Standard heartbeat cycle
        run_cycle(db_path)

        if not _shutdown:
            log.debug("Sleeping %ds until next cycle", LOOP_INTERVAL_SEC)
            # Sleep in small chunks so SIGTERM is handled promptly
            for _ in range(LOOP_INTERVAL_SEC // 5):
                if _shutdown:
                    break
                time.sleep(5)

    log.info("Agent runner stopped cleanly")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="agent/runner.py",
        description="Running coach heartbeat agent",
    )
    parser.add_argument(
        "--once",   action="store_true",
        help="Run one heartbeat cycle and exit",
    )
    parser.add_argument(
        "--daily",  action="store_true",
        help="Force one daily-deep run and exit",
    )
    args = parser.parse_args()

    from memory.db import init_db
    init_db()

    if args.daily:
        result = run_daily_deep()
        print(json.dumps(result, indent=2))
        return 0

    if args.once:
        result = run_cycle()
        print(json.dumps(result, default=str, indent=2))
        return 0

    run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
