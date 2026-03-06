"""
Hook: on_cutover_ready — detects when successful Saturday auto-plans
have reached the cutover threshold and queues a prompt for Discord.

State keys:
  saturday_plan_success_count
  cutover_threshold
  pending_cutover_prompt
  cutover_awaiting_response
  cutover_confirmed           (set on /coach_cutover confirm; prevents re-queue)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent

log = logging.getLogger("hooks.on_cutover_ready")

_COUNT_KEY = "saturday_plan_success_count"
_THRESHOLD_KEY = "cutover_threshold"
_PROMPT_KEY = "pending_cutover_prompt"
_AWAITING_KEY = "cutover_awaiting_response"
_CONFIRMED_KEY = "cutover_confirmed"
_DEFAULT_THRESHOLD = 4


def _increment_success_count(db_path=None) -> int:
    """Increment saturday_plan_success_count by 1 and return the new value."""
    from memory.db import DB_PATH as _DEFAULT_DB, get_state, set_state

    db = db_path or _DEFAULT_DB
    current = int(get_state(_COUNT_KEY, default="0", db_path=db) or "0")
    new_count = current + 1
    set_state(_COUNT_KEY, str(new_count), db_path=db)
    log.info("on_cutover_ready: success count -> %d", new_count)
    return new_count


def run(db_path=None) -> Dict[str, Any]:
    """
    Queue pending_cutover_prompt once count >= threshold.
    Guard against re-queueing when prompt is already pending or awaiting response.
    """
    from memory.db import DB_PATH as _DEFAULT_DB, get_state, set_state

    db = db_path or _DEFAULT_DB
    count = int(get_state(_COUNT_KEY, default="0", db_path=db) or "0")
    threshold = int(
        get_state(_THRESHOLD_KEY, default=str(_DEFAULT_THRESHOLD), db_path=db) or str(_DEFAULT_THRESHOLD)
    )
    result: Dict[str, Any] = {
        "pending_written": False,
        "count": count,
        "threshold": threshold,
    }

    if count < threshold:
        return result

    # Already confirmed — never re-queue after cutover is complete
    if get_state(_CONFIRMED_KEY, db_path=db):
        log.debug("on_cutover_ready: cutover already confirmed — skipping")
        return result

    if get_state(_PROMPT_KEY, db_path=db) or get_state(_AWAITING_KEY, db_path=db):
        return result

    payload = {"count": count, "threshold": threshold}
    set_state(_PROMPT_KEY, json.dumps(payload), db_path=db)
    result["pending_written"] = True
    return result


def _handle_delay(db_path=None) -> bool:
    """
    Called when athlete replies 'delay'. Bumps threshold by 1, clears awaiting flag.
    Returns True if delay was applied, False if not currently awaiting a response.
    """

    from memory.db import DB_PATH as _DEFAULT_DB, delete_state, get_state, set_state

    db = db_path or _DEFAULT_DB

    if not get_state(_AWAITING_KEY, db_path=db):
        return False

    threshold = int(
        get_state(_THRESHOLD_KEY, default=str(_DEFAULT_THRESHOLD), db_path=db) or str(_DEFAULT_THRESHOLD)
    )
    new_threshold = threshold + 1
    set_state(_THRESHOLD_KEY, str(new_threshold), db_path=db)

    # Delete awaiting flag — hook will re-queue when count catches up
    delete_state(_AWAITING_KEY, db_path=db)

    log.info("on_cutover_ready: delay applied — new threshold %d", new_threshold)
    return True
