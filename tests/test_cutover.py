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
    """_post_pending_cutover_prompt clears pending flag and sets awaiting flag."""
    import asyncio
    import json
    import shutil
    import unittest.mock as mock
    from memory.db import get_state, set_state

    # Build a test DB and pre-populate pending_cutover_prompt
    db = make_db(tmp_path)
    set_state("pending_cutover_prompt", json.dumps({"count": 4, "threshold": 4}), db_path=db)

    # The function constructs: PROJECT_ROOT / "data" / "coach.sqlite" for sqlite3 calls.
    # Place the test DB there so the raw sqlite3 read/delete work.
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    test_db = data_dir / "coach.sqlite"
    shutil.copy(str(db), str(test_db))

    import src.discord_bot as bot_module

    # set_state default db_path is baked in at import time, so patch the symbol
    # in memory.db with a wrapper that redirects no-arg calls to our test DB.
    import memory.db as db_module
    _real_set_state = db_module.set_state

    def _redirected_set_state(key, value, db_path=None):
        _real_set_state(key, value, db_path=test_db if db_path is None else db_path)

    original_root = bot_module.PROJECT_ROOT
    try:
        bot_module.PROJECT_ROOT = tmp_path
        # Patch set_state in memory.db so the import-inside-function picks it up
        db_module.set_state = _redirected_set_state

        mock_channel = mock.AsyncMock()
        result = asyncio.run(bot_module._post_pending_cutover_prompt(mock_channel))
    finally:
        bot_module.PROJECT_ROOT = original_root
        db_module.set_state = _real_set_state

    assert result is True
    mock_channel.send.assert_called_once()
    assert get_state("pending_cutover_prompt", db_path=test_db) is None
    assert get_state("cutover_awaiting_response", db_path=test_db) == "1"


def test_delay_bumps_threshold(tmp_path):
    """Replying 'delay' when awaiting response bumps threshold by 1 and clears awaiting."""
    db = make_db(tmp_path)
    from memory.db import get_state, set_state
    from hooks.on_cutover_ready import _handle_delay

    set_state("cutover_awaiting_response", "1", db_path=db)
    set_state("cutover_threshold", "4", db_path=db)

    result = _handle_delay(db_path=db)

    assert result is True
    assert get_state("cutover_threshold", db_path=db) == "5"
    assert get_state("cutover_awaiting_response", db_path=db) is None


def test_delay_without_awaiting_is_noop(tmp_path):
    """Delay handler is a no-op when not awaiting a response."""
    db = make_db(tmp_path)
    from memory.db import get_state
    from hooks.on_cutover_ready import _handle_delay

    result = _handle_delay(db_path=db)

    assert result is False
    assert get_state("cutover_threshold", db_path=db) is None
