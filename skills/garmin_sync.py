"""
Skills wrapper: Garmin sync.

Runs bin/smart_sync.sh and records the sync event in SQLite.
Does NOT modify health_data_cache.json format — that remains owned by
src/garmin_sync.py (sacred invariant).
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
log = logging.getLogger("skills.garmin_sync")


def run(
    force: bool = False,
    source: str = "agent",
    days: int = None,
    check_only: bool = False,
) -> dict:
    """
    Run Garmin sync and record a sync event in SQLite.

    Args:
        force:      Pass --force to smart_sync.sh (skips cache-age check).
        source:     Who triggered this sync ('agent', 'cli', 'discord', etc.).
        days:       Number of days to sync. If set, calls sync_garmin_data.sh
                    directly to pass the --days flag through.
        check_only: Preview what would be synced without writing. If set,
                    calls sync_garmin_data.sh directly with --check-only.

    Returns:
        dict with keys: success, returncode, stdout, stderr, event_id, summary
    """
    if days is not None or check_only:
        # --days / --check-only require sync_garmin_data.sh (smart_sync.sh
        # doesn't propagate these flags).
        cmd = ["bash", str(PROJECT_ROOT / "bin" / "sync_garmin_data.sh")]
        if days is not None:
            cmd += ["--days", str(days)]
        if check_only:
            cmd.append("--check-only")
    else:
        # Default path: smart_sync.sh handles cache-age check.
        cmd = ["bash", str(PROJECT_ROOT / "bin" / "smart_sync.sh")]
        if force:
            cmd.append("--force")

    from memory.db import (
        init_db, insert_event, log_task_start, log_task_finish,
        record_sync_start, record_sync_finish,
    )

    init_db()
    run_id = log_task_start("garmin_sync")
    sync_run_id = record_sync_start(source=source)

    log.info("Running Garmin sync: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        log_task_finish(
            run_id, "failed",
            details={"error": "timeout", "timeout_sec": 180},
        )
        record_sync_finish(sync_run_id, "failed", error_summary="timeout after 180s")
        raise RuntimeError("garmin_sync timed out after 180s") from exc

    success = result.returncode == 0
    summary = (result.stdout if success else result.stderr).strip()[:500]

    if success:
        log_task_finish(run_id, "success", details={"summary": summary[:200]})
        record_sync_finish(sync_run_id, "success")
    else:
        log.warning("Garmin sync failed rc=%d stderr: %s", result.returncode, result.stderr[:300])
        log_task_finish(
            run_id, "failed",
            details={"returncode": result.returncode, "stderr": result.stderr[:500]},
        )
        record_sync_finish(
            sync_run_id, "failed",
            error_summary=result.stderr[:200] if result.stderr else f"rc={result.returncode}",
        )

    # Append-only event log (each run unique via ts-derived id)
    event_id = insert_event(
        event_type="garmin_sync",
        payload={
            "returncode": result.returncode,
            "force": force,
            "success": success,
            "summary": summary[:200],
        },
        source="skills.garmin_sync",
    )

    log.info("Garmin sync rc=%d event_id=%s task_run_id=%d", result.returncode, event_id[:8], run_id)

    return {
        "success": success,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "event_id": event_id,
        "summary": summary,
    }
