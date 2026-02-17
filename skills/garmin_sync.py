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


def run(force: bool = False) -> dict:
    """
    Run Garmin sync and record a sync event in SQLite.

    Args:
        force: Pass --force to smart_sync.sh (skips cache-age check).

    Returns:
        dict with keys: success, returncode, stdout, stderr, event_id, summary
    """
    # Invoke with bash explicitly — smart_sync.sh has a Termux shebang
    # that doesn't resolve on standard Linux. bash reads it fine regardless.
    cmd = ["bash", str(PROJECT_ROOT / "bin" / "smart_sync.sh")]
    if force:
        cmd.append("--force")

    log.info("Running Garmin sync: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=180,
    )

    success = result.returncode == 0
    summary = (result.stdout if success else result.stderr).strip()[:500]

    # Record sync event in SQLite (idempotency: each run gets a unique ts-derived id)
    from memory.db import init_db, insert_event

    init_db()
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

    log.info("Garmin sync rc=%d event_id=%s", result.returncode, event_id[:8])
    if not success:
        log.warning("Garmin sync stderr: %s", result.stderr[:300])

    return {
        "success": success,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "event_id": event_id,
        "summary": summary,
    }
