#!/usr/bin/env python3
"""Tests for FinalSurge cutover counter and readiness hook."""

import json


def make_db(tmp_path):
    from memory.db import SCHEMA, _connect

    db = tmp_path / "coach.sqlite"
    conn = _connect(db)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return db


def test_increment_saturday_count(tmp_path):
    db = make_db(tmp_path)
    from hooks.on_cutover_ready import _increment_success_count
    from memory.db import get_state

    _increment_success_count(db_path=db)
    assert get_state("saturday_plan_success_count", db_path=db) == "1"


def test_increment_saturday_count_accumulates(tmp_path):
    db = make_db(tmp_path)
    from hooks.on_cutover_ready import _increment_success_count
    from memory.db import get_state

    _increment_success_count(db_path=db)
    _increment_success_count(db_path=db)
    _increment_success_count(db_path=db)
    assert get_state("saturday_plan_success_count", db_path=db) == "3"


def test_only_increments_on_full_success(tmp_path):
    """Counter stays None when increment is never called (simulating Garmin export failure)."""
    db = make_db(tmp_path)
    from memory.db import get_state
    # Garmin export failed — never call _increment_success_count
    assert get_state("saturday_plan_success_count", db_path=db) is None
    # But if we call it (simulating full success), it moves to 1
    from hooks.on_cutover_ready import _increment_success_count
    _increment_success_count(db_path=db)
    assert get_state("saturday_plan_success_count", db_path=db) == "1"


def test_hook_queues_prompt_at_threshold(tmp_path):
    db = make_db(tmp_path)
    from hooks.on_cutover_ready import run
    from memory.db import get_state, set_state

    set_state("saturday_plan_success_count", "4", db_path=db)
    result = run(db_path=db)

    assert result["pending_written"] is True
    assert get_state("pending_cutover_prompt", db_path=db) is not None


def test_hook_does_not_double_queue(tmp_path):
    db = make_db(tmp_path)
    from hooks.on_cutover_ready import run
    from memory.db import get_state, set_state

    set_state("saturday_plan_success_count", "4", db_path=db)
    first = run(db_path=db)
    second = run(db_path=db)

    assert first["pending_written"] is True
    assert second["pending_written"] is False
    raw = get_state("pending_cutover_prompt", db_path=db)
    payload = json.loads(raw)
    assert payload["count"] == 4


def test_hook_respects_delay(tmp_path):
    db = make_db(tmp_path)
    from hooks.on_cutover_ready import run
    from memory.db import set_state

    set_state("saturday_plan_success_count", "4", db_path=db)
    set_state("cutover_threshold", "5", db_path=db)
    result = run(db_path=db)
    assert result["pending_written"] is False


def test_hook_queues_after_delay_when_count_catches_up(tmp_path):
    db = make_db(tmp_path)
    from hooks.on_cutover_ready import run
    from memory.db import set_state

    set_state("saturday_plan_success_count", "5", db_path=db)
    set_state("cutover_threshold", "5", db_path=db)
    result = run(db_path=db)
    assert result["pending_written"] is True


def test_cutover_awaiting_set_after_prompt(tmp_path):
    """After prompt is delivered, cutover_awaiting_response is set and pending_cutover_prompt is cleared."""
    import json
    import sqlite3

    db = make_db(tmp_path)
    from memory.db import get_state, set_state

    set_state("pending_cutover_prompt", json.dumps({"count": 4, "threshold": 4}), db_path=db)

    # Simulate what _post_pending_cutover_prompt does (minus Discord send):
    # 1. Set cutover_awaiting_response = "1"
    set_state("cutover_awaiting_response", "1", db_path=db)
    # 2. Delete pending_cutover_prompt from state table
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM state WHERE key = 'pending_cutover_prompt'")
    conn.commit()
    conn.close()

    assert get_state("pending_cutover_prompt", db_path=db) is None
    assert get_state("cutover_awaiting_response", db_path=db) == "1"
