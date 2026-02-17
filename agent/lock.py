"""
SQLite-backed exclusive lock for the agent runner.

Lock state is stored in memory.state as key="runner_lock" with a JSON value:
    {
        "owner":       "runner:{pid}",
        "acquired_at": "2026-02-17T04:00:00",
        "expires_at":  "2026-02-17T04:20:00",
    }

Expiry (default 20 min) prevents stale locks from blocking indefinitely.
The runner refreshes the lock while it works so it never expires mid-cycle.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger("agent.lock")

LOCK_KEY = "runner_lock"
LOCK_TTL_MIN = 20


def _owner_tag() -> str:
    return f"runner:{os.getpid()}"


def acquire_lock(owner: Optional[str] = None, db_path=None) -> bool:
    """
    Try to acquire the runner lock.

    Returns True if the lock was acquired (caller must call release_lock).
    Returns False if the lock is currently held by another owner and not expired.
    """
    from memory.db import get_state, set_state, init_db, DB_PATH

    db = db_path or DB_PATH
    init_db(db)
    owner = owner or _owner_tag()

    raw = get_state(LOCK_KEY, db_path=db)
    if raw:
        try:
            existing = json.loads(raw)
            expires = datetime.fromisoformat(existing["expires_at"])
            if datetime.utcnow() < expires:
                log.debug(
                    "Lock held by %s until %s — cannot acquire",
                    existing.get("owner"), existing["expires_at"],
                )
                return False
            log.info(
                "Stale lock from %s (expired %s) — overriding",
                existing.get("owner"), existing["expires_at"],
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            log.warning("Corrupt lock value — overriding")

    now = datetime.utcnow()
    set_state(
        LOCK_KEY,
        json.dumps({
            "owner":       owner,
            "acquired_at": now.isoformat(),
            "expires_at":  (now + timedelta(minutes=LOCK_TTL_MIN)).isoformat(),
        }),
        db_path=db,
    )
    log.info("Lock acquired by %s", owner)
    return True


def release_lock(owner: Optional[str] = None, db_path=None) -> None:
    """Release the lock if we own it."""
    from memory.db import get_state, set_state, DB_PATH

    db = db_path or DB_PATH
    owner = owner or _owner_tag()
    raw = get_state(LOCK_KEY, db_path=db)
    if not raw:
        return

    try:
        existing = json.loads(raw)
        if existing.get("owner") != owner:
            log.warning(
                "release_lock: called by %s but owner is %s — skipping",
                owner, existing.get("owner"),
            )
            return
    except (json.JSONDecodeError, KeyError):
        pass  # corrupt — clear it anyway

    set_state(LOCK_KEY, "", db_path=db)
    log.info("Lock released by %s", owner)


def refresh_lock(owner: Optional[str] = None, db_path=None) -> None:
    """Extend lock expiry while still working to prevent mid-cycle expiry."""
    from memory.db import get_state, set_state, DB_PATH

    db = db_path or DB_PATH
    owner = owner or _owner_tag()
    raw = get_state(LOCK_KEY, db_path=db)
    if not raw:
        return

    try:
        lock = json.loads(raw)
        if lock.get("owner") != owner:
            return
        now = datetime.utcnow()
        lock["expires_at"] = (now + timedelta(minutes=LOCK_TTL_MIN)).isoformat()
        set_state(LOCK_KEY, json.dumps(lock), db_path=db)
    except Exception:
        pass


def get_lock_state(db_path=None) -> Optional[dict]:
    """Return current lock dict (with 'expired' bool added), or None if free."""
    from memory.db import get_state, DB_PATH

    raw = get_state(LOCK_KEY, db_path=db_path or DB_PATH)
    if not raw:
        return None
    try:
        lock = json.loads(raw)
        lock["expired"] = datetime.utcnow() >= datetime.fromisoformat(lock["expires_at"])
        return lock
    except Exception:
        return None
