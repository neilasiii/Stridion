"""
Tests for Phase 12 — Observability + Parity Guardrails.

Scope:
  D12-1  coach db sanity  — outputs DB path, sync freshness, row counts, status
  D12-2  coach parity     — SQLite vs JSON comparison with correct exit codes
  D12-3  retrieval logging — source=sqlite logged; source=json_fallback logged
"""
import json
import logging
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


PROJECT_ROOT = Path(__file__).parent.parent


# ── helpers ───────────────────────────────────────────────────────────────────

def _tmp_db():
    import tempfile
    tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tf.close()
    return Path(tf.name)


def _init_db_with_today(db):
    """Init DB and insert one daily_metrics row for today."""
    from memory.db import init_db, upsert_daily_metrics
    init_db(db_path=db)
    today = date.today()
    upsert_daily_metrics(
        today,
        hrv_rmssd=65.0, resting_hr=48.0, sleep_score=80.0,
        sleep_duration_h=7.5, body_battery=90, training_readiness=75,
        stress_avg=22.0, db_path=db,
    )
    return today


# ── D12-1: coach db sanity ────────────────────────────────────────────────────

class TestDbSanity:
    """_db_sanity() must return 0 (HEALTHY) when data is fresh, 1 (DEGRADED) otherwise."""

    def _run_sanity(self, db, capsys, last_sync_age_min=5):
        """Call _db_sanity() with a patched DB_PATH and mocked sync run."""
        from cli.coach import _db_sanity
        from datetime import datetime

        finished_at = (
            datetime.utcnow() - timedelta(minutes=last_sync_age_min)
        ).isoformat()

        fake_sync = {
            "run_id":      "abc123",
            "started_at":  finished_at,
            "finished_at": finished_at,
            "status":      "success",
            "source":      "agent",
        }

        with (
            patch("cli.coach.DB_PATH", db) if False else patch("memory.db.DB_PATH", db),
            patch("memory.db.get_last_sync_run", return_value=fake_sync),
            patch("memory.retrieval._rollup_readiness_from_sqlite",
                  return_value={"source": "sqlite"}),
        ):
            # _db_sanity uses get_last_sync_run and DB_PATH directly;
            # we patch at the import level inside the function.
            from memory import db as _db_mod
            orig_path = _db_mod.DB_PATH
            _db_mod.DB_PATH = db
            try:
                rc = _db_sanity()
            finally:
                _db_mod.DB_PATH = orig_path
        return rc

    def test_healthy_when_today_row_present(self, tmp_path, capsys):
        db = tmp_path / "test.sqlite"
        _init_db_with_today(db)

        from cli.coach import _db_sanity
        from datetime import datetime
        from memory import db as _db_mod

        finished_at = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        fake_sync = {
            "finished_at": finished_at, "started_at": finished_at,
            "status": "success", "source": "test",
        }

        orig = _db_mod.DB_PATH
        _db_mod.DB_PATH = db
        try:
            with (
                patch("memory.db.get_last_sync_run", return_value=fake_sync),
                patch("memory.retrieval._rollup_readiness_from_sqlite",
                      return_value={"source": "sqlite"}),
            ):
                rc = _db_sanity()
        finally:
            _db_mod.DB_PATH = orig

        out = capsys.readouterr().out
        assert rc == 0
        assert "HEALTHY" in out
        assert "DEGRADED" not in out

    def test_degraded_when_today_row_missing(self, tmp_path, capsys):
        db = tmp_path / "test.sqlite"
        from memory.db import init_db, upsert_daily_metrics
        init_db(db_path=db)
        # Insert YESTERDAY only
        yesterday = date.today() - timedelta(days=1)
        upsert_daily_metrics(yesterday, hrv_rmssd=60.0, db_path=db)

        from cli.coach import _db_sanity
        from datetime import datetime
        from memory import db as _db_mod

        finished_at = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        fake_sync = {
            "finished_at": finished_at, "started_at": finished_at,
            "status": "success", "source": "test",
        }

        orig = _db_mod.DB_PATH
        _db_mod.DB_PATH = db
        try:
            with (
                patch("memory.db.get_last_sync_run", return_value=fake_sync),
                patch("memory.retrieval._rollup_readiness_from_sqlite",
                      return_value={"source": "sqlite"}),
            ):
                rc = _db_sanity()
        finally:
            _db_mod.DB_PATH = orig

        out = capsys.readouterr().out
        assert rc == 1
        assert "DEGRADED" in out
        assert "today missing" in out

    def test_output_contains_required_sections(self, tmp_path, capsys):
        db = tmp_path / "test.sqlite"
        _init_db_with_today(db)

        from cli.coach import _db_sanity
        from datetime import datetime
        from memory import db as _db_mod

        finished_at = (datetime.utcnow() - timedelta(minutes=3)).isoformat()
        fake_sync = {
            "finished_at": finished_at, "started_at": finished_at,
            "status": "success", "source": "agent",
        }

        orig = _db_mod.DB_PATH
        _db_mod.DB_PATH = db
        try:
            with (
                patch("memory.db.get_last_sync_run", return_value=fake_sync),
                patch("memory.retrieval._rollup_readiness_from_sqlite",
                      return_value={"source": "sqlite"}),
            ):
                _db_sanity()
        finally:
            _db_mod.DB_PATH = orig

        out = capsys.readouterr().out
        assert "DB:" in out
        assert "Sync:" in out
        assert "daily_metrics" in out
        assert "activities" in out
        assert "Retrieval:" in out
        assert "Status:" in out

    def test_degraded_when_retrieval_falls_back(self, tmp_path, capsys):
        db = tmp_path / "test.sqlite"
        _init_db_with_today(db)

        from cli.coach import _db_sanity
        from datetime import datetime
        from memory import db as _db_mod

        finished_at = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        fake_sync = {
            "finished_at": finished_at, "started_at": finished_at,
            "status": "success", "source": "test",
        }

        orig = _db_mod.DB_PATH
        _db_mod.DB_PATH = db
        try:
            with (
                patch("memory.db.get_last_sync_run", return_value=fake_sync),
                patch("memory.retrieval._rollup_readiness_from_sqlite",
                      return_value=None),   # forces fallback
            ):
                rc = _db_sanity()
        finally:
            _db_mod.DB_PATH = orig

        out = capsys.readouterr().out
        assert rc == 1
        assert "json_fallback" in out
        assert "DEGRADED" in out


# ── D12-2: coach parity ───────────────────────────────────────────────────────

class TestParityCommand:
    """cmd_parity() must compare SQLite vs JSON for key metrics with correct exit codes.

    DB_PATH is baked in as a default arg at module load time, so we cannot
    redirect it by patching the module attribute.  Instead we mock
    memory.db.get_daily_metrics (which cmd_parity imports at call-time via
    `from memory.db import get_daily_metrics`) to return controlled rows.
    """

    def _build_cache(self, day: str, tr=75, bb=85, hrv=65) -> dict:
        return {
            "training_readiness": [{"date": day, "score": tr}],
            "body_battery":       [{"date": day, "latest_level": bb, "charged": 90}],
            "hrv_readings":       [{"date": day, "last_night_avg": hrv}],
        }

    def _fake_row(self, day: str, tr=75, bb=85, hrv=65):
        return {
            "day": day, "training_readiness": float(tr),
            "body_battery": float(bb), "hrv_rmssd": float(hrv),
            "resting_hr": 48.0, "sleep_score": 80.0,
            "sleep_duration_h": 7.5, "stress_avg": 22.0,
        }

    def _run_parity(self, day_str, sqlite_rows, cache_content=None, cache_missing=False):
        from cli.coach import cmd_parity, _build_parser
        args = _build_parser().parse_args(["parity", "--day", day_str])

        patches = [patch("memory.db.get_daily_metrics", return_value=sqlite_rows)]

        if cache_missing:
            patches.append(
                patch("memory.retrieval.HEALTH_CACHE",
                      Path("/nonexistent/path/cache.json"))
            )
        elif cache_content is not None:
            tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(cache_content, tf)
            tf.close()
            tf_path = Path(tf.name)
            patches.append(patch("memory.retrieval.HEALTH_CACHE", tf_path))
        else:
            tf_path = None

        try:
            ctx = patches[0].__enter__()
            for p in patches[1:]:
                p.__enter__()
            rc = cmd_parity(args)
        finally:
            for p in reversed(patches):
                p.__exit__(None, None, None)
            if cache_content is not None and not cache_missing:
                tf_path.unlink(missing_ok=True)
        return rc

    def test_happy_match_returns_0(self, capsys):
        today = date.today().isoformat()
        rows  = [self._fake_row(today, tr=75, bb=85, hrv=65)]
        cache = self._build_cache(today, tr=75, bb=85, hrv=65)
        rc    = self._run_parity(today, rows, cache_content=cache)
        assert rc == 0
        out = capsys.readouterr().out
        assert "✓" in out
        assert "✗" not in out

    def test_mismatch_returns_2(self, capsys):
        today = date.today().isoformat()
        rows  = [self._fake_row(today, tr=75, bb=85, hrv=65)]
        # JSON says tr=50 — mismatch
        cache = self._build_cache(today, tr=50, bb=85, hrv=65)
        rc    = self._run_parity(today, rows, cache_content=cache)
        assert rc == 2
        out = capsys.readouterr().out
        assert "✗" in out

    def test_missing_json_returns_0(self, capsys):
        """Missing JSON cache is informational only, not an error."""
        today = date.today().isoformat()
        rows  = [self._fake_row(today)]
        rc    = self._run_parity(today, rows, cache_missing=True)
        assert rc == 0
        out = capsys.readouterr().out
        assert "not found" in out

    def test_missing_sqlite_row_returns_0(self, capsys):
        """No SQLite row for the day — nothing to compare, not an error."""
        today = date.today().isoformat()
        cache = self._build_cache(today, tr=75, bb=85, hrv=65)
        rc    = self._run_parity(today, [], cache_content=cache)
        assert rc == 0

    def test_output_format(self, capsys):
        today = date.today().isoformat()
        rows  = [self._fake_row(today, tr=75, bb=90, hrv=65)]
        cache = self._build_cache(today, tr=75, bb=90, hrv=65)
        self._run_parity(today, rows, cache_content=cache)
        out = capsys.readouterr().out
        assert "training_readiness" in out
        assert "body_battery_max"   in out
        assert "hrv"                in out
        assert "sqlite="            in out
        assert "json="              in out

    def test_invalid_date_returns_1(self, capsys):
        rc = self._run_parity("not-a-date", [])
        assert rc == 1


# ── D12-3: retrieval fallback logging ─────────────────────────────────────────

class TestRetrievalLogging:
    """_rollup_readiness_from_sqlite() must emit appropriate log messages."""

    def _make_db(self, tmp_path):
        db = tmp_path / "test.sqlite"
        from memory.db import init_db
        init_db(db_path=db)
        return db

    def test_sqlite_success_logs_info(self, tmp_path, caplog):
        db = self._make_db(tmp_path)
        from memory.db import upsert_daily_metrics
        from memory.retrieval import _rollup_readiness_from_sqlite

        upsert_daily_metrics(date.today(), hrv_rmssd=65.0, db_path=db)

        with caplog.at_level(logging.INFO, logger="memory.retrieval"):
            result = _rollup_readiness_from_sqlite(7, db)

        assert result is not None
        assert result.get("source") == "sqlite"
        assert any(
            "source=sqlite" in r.message for r in caplog.records
        ), f"Expected 'source=sqlite' in logs; got: {[r.message for r in caplog.records]}"

    def test_empty_table_logs_warning(self, tmp_path, caplog):
        db = self._make_db(tmp_path)
        from memory.retrieval import _rollup_readiness_from_sqlite

        with caplog.at_level(logging.WARNING, logger="memory.retrieval"):
            result = _rollup_readiness_from_sqlite(7, db)

        assert result is None
        assert any(
            "json_fallback" in r.message for r in caplog.records
        ), f"Expected 'json_fallback' in logs; got: {[r.message for r in caplog.records]}"

    def test_sqlite_error_logs_warning(self, tmp_path, caplog):
        # _rollup_readiness_from_sqlite does `from .db import get_daily_metrics`
        # at call time — patch at the source (memory.db) so the import gets the mock.
        from memory.retrieval import _rollup_readiness_from_sqlite

        with (
            patch("memory.db.get_daily_metrics",
                  side_effect=Exception("disk I/O error")),
            caplog.at_level(logging.WARNING, logger="memory.retrieval"),
        ):
            result = _rollup_readiness_from_sqlite(7, tmp_path / "test.sqlite")

        assert result is None
        assert any(
            "json_fallback" in r.message and "sqlite_error" in r.message
            for r in caplog.records
        )

    def test_log_contains_days_back_and_date(self, tmp_path, caplog):
        db = self._make_db(tmp_path)
        from memory.db import upsert_daily_metrics
        from memory.retrieval import _rollup_readiness_from_sqlite

        today = date.today()
        upsert_daily_metrics(today, hrv_rmssd=70.0, db_path=db)

        with caplog.at_level(logging.INFO, logger="memory.retrieval"):
            _rollup_readiness_from_sqlite(7, db)

        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any(
            "days_back=7" in m and today.isoformat() in m
            for m in info_msgs
        ), f"Expected days_back + date in log; got: {info_msgs}"
