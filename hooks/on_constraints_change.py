"""
Hook: on_constraints_change — runs after vault inbox ingestion.

If new constraint events were inserted for dates within the next 7 days,
sets a replan flag so the runner can decide whether to call brain.plan_week().

The hook NEVER calls the Brain directly — it only signals the need.
The runner owns the decision to re-plan (respects lock, brain call budget, etc.).

Returns:
    {
        "new_constraints":   List[dict],   # newly inserted constraint events
        "near_constraints":  List[str],    # dates within next 7 days
        "needs_replan":      bool,
    }
"""

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List

log = logging.getLogger("hooks.on_constraints_change")

REPLAN_WINDOW_DAYS = 7


def run(db_path=None) -> Dict[str, Any]:
    """
    Ingest vault/inbox/ notes and check for near-term constraint changes.

    Returns summary dict. Safe to call even when inbox is empty.
    """
    from memory.vault import ingest_inbox_notes

    # ── Ingest inbox notes ─────────────────────────────────────────────────
    new_events = ingest_inbox_notes(db_path=db_path)

    if not new_events:
        log.debug("No new constraint events from inbox")
        return {"new_constraints": [], "near_constraints": [], "needs_replan": False}

    log.info("Inbox ingestion: %d new constraint event(s)", len(new_events))

    # ── Check if any fall within replan window ─────────────────────────────
    today = date.today()
    cutoff = today + timedelta(days=REPLAN_WINDOW_DAYS)
    near: List[str] = []

    for ev in new_events:
        payload = ev.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass

        # Constraint events store date in payload or in the event date field
        ev_date_str = payload.get("date") or ev.get("date", "")
        if not ev_date_str:
            continue
        try:
            ev_date = date.fromisoformat(ev_date_str[:10])
        except ValueError:
            continue

        if today <= ev_date <= cutoff:
            near.append(ev_date_str[:10])
            log.info(
                "Near-term constraint on %s — re-plan may be warranted", ev_date_str[:10]
            )

    needs_replan = len(near) > 0

    return {
        "new_constraints":  new_events,
        "near_constraints": near,
        "needs_replan":     needs_replan,
    }
