"""
Memory OS for the running coach system.

Provides:
  - SQLite-backed persistent storage (db.py)
  - Obsidian-compatible markdown vault (vault.py)
  - Context packet assembly for the Brain (retrieval.py)

Usage:
    from memory import init_db, insert_plan, build_context_packet
    init_db()
"""

from .db import (
    init_db,
    upsert_athlete_profile,
    get_athlete_profile,
    insert_event,
    query_events,
    set_state,
    get_state,
    upsert_metrics,
    get_metrics_range,
    insert_plan,
    insert_plan_days,
    set_active_plan,
    get_active_plan,
    get_active_plan_id,
    get_active_plan_range,
    get_plan_meta,
    log_task_start,
    log_task_finish,
    insert_macro_plan,
    set_active_macro_plan,
    get_active_macro_plan,
    get_active_macro_plan_id,
    DB_PATH,
)

from .vault import (
    write_daily_note,
    append_decision,
    write_plan_snapshot,
    ingest_inbox_notes,
    get_recent_decisions,
)

from .retrieval import (
    build_context_packet,
    hash_context_packet,
)

__all__ = [
    # db
    "DB_PATH",
    "init_db",
    "upsert_athlete_profile",
    "get_athlete_profile",
    "insert_event",
    "query_events",
    "set_state",
    "get_state",
    "upsert_metrics",
    "get_metrics_range",
    "insert_plan",
    "insert_plan_days",
    "set_active_plan",
    "get_active_plan",
    "get_active_plan_id",
    "get_active_plan_range",
    "get_plan_meta",
    "log_task_start",
    "log_task_finish",
    "insert_macro_plan",
    "set_active_macro_plan",
    "get_active_macro_plan",
    "get_active_macro_plan_id",
    # vault
    "write_daily_note",
    "append_decision",
    "write_plan_snapshot",
    "ingest_inbox_notes",
    "get_recent_decisions",
    # retrieval
    "build_context_packet",
    "hash_context_packet",
]
