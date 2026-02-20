"""
Tests for B11-010 — daily_metrics table in SQLite schema.

Scope:
  - init_db() creates daily_metrics table (additive, no existing tables dropped)
  - upsert_daily_metrics() inserts and updates rows idempotently
  - get_daily_metrics() returns rows in date range
  - NULL columns are allowed for missing metrics
"""
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

import pytest


def _tmp_db() -> Path:
    tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tf.close()
    return Path(tf.name)


class TestDailyMetricsSchema:
    def setup_method(self):
        self.db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=self.db)

    def test_table_exists_after_init(self):
        conn = sqlite3.connect(str(self.db))
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_metrics'"
        ).fetchone()
        conn.close()
        assert row is not None, "daily_metrics table not created by init_db()"

    def test_existing_tables_not_dropped(self):
        """Additive migration: other tables must survive."""
        conn = sqlite3.connect(str(self.db))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        for expected in ("plans", "plan_days", "events", "state", "sync_runs"):
            assert expected in tables, f"table {expected!r} was dropped"

    def test_upsert_inserts_row(self):
        from memory.db import upsert_daily_metrics, get_daily_metrics

        d = date(2026, 2, 1)
        upsert_daily_metrics(
            d, hrv_rmssd=45.2, resting_hr=52.0, sleep_score=76.0,
            sleep_duration_h=7.5, body_battery=80, training_readiness=65,
            stress_avg=28.0, raw={"source": "garmin"}, db_path=self.db,
        )
        rows = get_daily_metrics(d, d, db_path=self.db)
        assert len(rows) == 1
        assert rows[0]["hrv_rmssd"] == pytest.approx(45.2)
        assert rows[0]["resting_hr"] == pytest.approx(52.0)
        assert rows[0]["sleep_score"] == pytest.approx(76.0)

    def test_upsert_updates_existing_row(self):
        from memory.db import upsert_daily_metrics, get_daily_metrics

        d = date(2026, 2, 2)
        upsert_daily_metrics(d, hrv_rmssd=40.0, db_path=self.db)
        upsert_daily_metrics(d, hrv_rmssd=55.0, db_path=self.db)

        rows = get_daily_metrics(d, d, db_path=self.db)
        assert len(rows) == 1
        assert rows[0]["hrv_rmssd"] == pytest.approx(55.0)

    def test_null_columns_allowed(self):
        from memory.db import upsert_daily_metrics, get_daily_metrics

        d = date(2026, 2, 3)
        upsert_daily_metrics(d, db_path=self.db)  # all metrics None

        rows = get_daily_metrics(d, d, db_path=self.db)
        assert len(rows) == 1
        assert rows[0]["hrv_rmssd"] is None
        assert rows[0]["resting_hr"] is None

    def test_get_daily_metrics_range(self):
        from memory.db import upsert_daily_metrics, get_daily_metrics

        for i in range(5):
            upsert_daily_metrics(date(2026, 2, i + 1), hrv_rmssd=float(40 + i), db_path=self.db)

        rows = get_daily_metrics(date(2026, 2, 2), date(2026, 2, 4), db_path=self.db)
        assert len(rows) == 3
        assert [r["day"] for r in rows] == ["2026-02-02", "2026-02-03", "2026-02-04"]

    def test_get_daily_metrics_empty_range(self):
        from memory.db import get_daily_metrics

        rows = get_daily_metrics(date(2026, 1, 1), date(2026, 1, 7), db_path=self.db)
        assert rows == []
