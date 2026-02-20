"""
Tests for B11-019 — sync_runs table + freshness visibility.

Scope:
  - init_db() creates the sync_runs table (additive, no existing tables dropped)
  - record_sync_start() inserts a 'running' row and returns a run_id
  - record_sync_finish() updates status / finished_at / error_summary
  - get_last_sync_run() returns the most recent row (optionally filtered by status)
  - skills/garmin_sync.run() records a sync_run row (subprocess mocked)
"""
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _tmp_db() -> Path:
    """Return a path to a fresh temp SQLite file."""
    tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tf.close()
    return Path(tf.name)


# ── schema tests ──────────────────────────────────────────────────────────────

class TestSyncRunsSchema:
    """init_db() must create the sync_runs table without breaking existing tables."""

    def test_init_db_creates_sync_runs_table(self):
        import sqlite3
        from memory.db import init_db

        db = _tmp_db()
        try:
            init_db(db_path=db)
            conn = sqlite3.connect(str(db))
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            conn.close()
            assert "sync_runs" in tables, "sync_runs table not found after init_db()"
        finally:
            db.unlink(missing_ok=True)

    def test_existing_tables_still_present(self):
        """Additive migration — no existing tables must be removed."""
        import sqlite3
        from memory.db import init_db

        db = _tmp_db()
        try:
            init_db(db_path=db)
            conn = sqlite3.connect(str(db))
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            conn.close()
            for expected in ("task_runs", "state", "plans", "events", "metrics"):
                assert expected in tables, f"Expected table {expected!r} missing after init_db()"
        finally:
            db.unlink(missing_ok=True)


# ── record helpers ─────────────────────────────────────────────────────────────

class TestRecordSyncHelpers:
    """record_sync_start / record_sync_finish / get_last_sync_run round-trips."""

    def setup_method(self):
        from memory.db import init_db
        self.db = _tmp_db()
        init_db(db_path=self.db)

    def teardown_method(self):
        self.db.unlink(missing_ok=True)

    def test_record_sync_start_returns_run_id(self):
        from memory.db import record_sync_start
        rid = record_sync_start(source="cli", db_path=self.db)
        assert isinstance(rid, str) and len(rid) > 0

    def test_record_sync_start_creates_running_row(self):
        import sqlite3
        from memory.db import record_sync_start

        rid = record_sync_start(source="agent", days_requested=7, db_path=self.db)

        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM sync_runs WHERE run_id = ?", (rid,)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["status"] == "running"
        assert row["source"] == "agent"
        assert row["days_requested"] == 7
        assert row["finished_at"] is None

    def test_record_sync_finish_updates_row(self):
        import sqlite3
        from memory.db import record_sync_start, record_sync_finish

        rid = record_sync_start(source="cli", db_path=self.db)
        record_sync_finish(rid, "success", days_synced=14, db_path=self.db)

        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM sync_runs WHERE run_id = ?", (rid,)
        ).fetchone()
        conn.close()

        assert row["status"] == "success"
        assert row["days_synced"] == 14
        assert row["finished_at"] is not None
        assert row["error_summary"] is None

    def test_record_sync_finish_records_error_summary(self):
        import sqlite3
        from memory.db import record_sync_start, record_sync_finish

        rid = record_sync_start(source="agent", db_path=self.db)
        record_sync_finish(rid, "failed", error_summary="network timeout", db_path=self.db)

        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM sync_runs WHERE run_id = ?", (rid,)
        ).fetchone()
        conn.close()

        assert row["status"] == "failed"
        assert row["error_summary"] == "network timeout"

    def test_get_last_sync_run_returns_most_recent(self):
        from memory.db import record_sync_start, record_sync_finish, get_last_sync_run

        rid1 = record_sync_start(source="agent", db_path=self.db)
        record_sync_finish(rid1, "success", db_path=self.db)

        rid2 = record_sync_start(source="cli", db_path=self.db)
        record_sync_finish(rid2, "failed", error_summary="auth error", db_path=self.db)

        last = get_last_sync_run(db_path=self.db)
        assert last is not None
        assert last["run_id"] == rid2

    def test_get_last_sync_run_filtered_by_success(self):
        from memory.db import record_sync_start, record_sync_finish, get_last_sync_run

        rid_ok = record_sync_start(source="agent", db_path=self.db)
        record_sync_finish(rid_ok, "success", db_path=self.db)

        rid_fail = record_sync_start(source="cli", db_path=self.db)
        record_sync_finish(rid_fail, "failed", db_path=self.db)

        last_ok = get_last_sync_run(status="success", db_path=self.db)
        assert last_ok is not None
        assert last_ok["run_id"] == rid_ok
        assert last_ok["status"] == "success"

    def test_get_last_sync_run_returns_none_when_empty(self):
        from memory.db import get_last_sync_run
        assert get_last_sync_run(db_path=self.db) is None


# ── skills integration test ───────────────────────────────────────────────────

class TestSkillsGarminSyncRecordsSyncRun:
    """skills/garmin_sync.run() must write a sync_run row (subprocess mocked)."""

    def test_successful_sync_writes_success_row(self):
        from memory.db import init_db, get_last_sync_run

        db = _tmp_db()
        try:
            init_db(db_path=db)

            fake_result = MagicMock()
            fake_result.returncode = 0
            fake_result.stdout = "Sync complete\n"
            fake_result.stderr = ""

            with (
                patch("skills.garmin_sync.subprocess.run", return_value=fake_result),
                patch("memory.db.DB_PATH", db),
                patch("memory.db.init_db"),   # already called above
            ):
                from skills import garmin_sync
                # Re-patch DB_PATH inside the module scope used at runtime
                with patch.object(
                    __import__("memory.db", fromlist=["record_sync_start"]),
                    "DB_PATH", db,
                ):
                    # Call with explicit db_path not supported by skills layer;
                    # instead patch the module-level DB_PATH constant directly.
                    pass

            # Simpler approach: patch record_sync_start/finish to capture calls
            calls = []

            def fake_start(source="agent", days_requested=None, run_id=None, db_path=db):
                rid = "test-run-id"
                calls.append(("start", source, rid))
                return rid

            def fake_finish(run_id, status, days_synced=None, error_summary=None, db_path=db):
                calls.append(("finish", run_id, status, error_summary))

            with (
                patch("skills.garmin_sync.subprocess.run", return_value=fake_result),
                patch("memory.db.record_sync_start", side_effect=fake_start),
                patch("memory.db.record_sync_finish", side_effect=fake_finish),
                patch("memory.db.log_task_start", return_value=1),
                patch("memory.db.log_task_finish"),
                patch("memory.db.insert_event", return_value="ev-id"),
                patch("memory.db.init_db"),
            ):
                import importlib
                import skills.garmin_sync as gsk
                importlib.reload(gsk)   # ensure fresh import sees patches
                result = gsk.run(force=False, source="cli")

            assert result["success"] is True
            start_calls = [c for c in calls if c[0] == "start"]
            finish_calls = [c for c in calls if c[0] == "finish"]
            assert len(start_calls) == 1, "record_sync_start must be called once"
            assert start_calls[0][1] == "cli", "source must be propagated"
            assert len(finish_calls) == 1, "record_sync_finish must be called once"
            assert finish_calls[0][2] == "success"

        finally:
            db.unlink(missing_ok=True)
