"""
Track F — Mapping & Validation-Prep Phase
==========================================

These tests serve two purposes:

1. **Reader/writer contracts** — assert the exact column sets that each writer
   stores and each reader returns so that any future migration can be verified
   against this baseline.

2. **Readiness parity** — compare the legacy JSON path (_rollup_readiness) with
   the SQLite path (_rollup_readiness_from_sqlite) for the same synthetic data,
   making the output-shape difference observable before any migration touches code.

NO schema changes, NO deletions, NO behavioural changes in this file.
"""
from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Dict

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def _tmp_db() -> Path:
    tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tf.close()
    return Path(tf.name)


def _today() -> date:
    return date.today()


def _days_ago(n: int) -> date:
    return _today() - timedelta(days=n)


# ── Section 1: legacy metrics table — DELETED (Track F retirement) ─────────────
# upsert_metrics, get_metrics_range, and the 'metrics' blob table DDL were
# removed from memory/db.py and memory/__init__.py.  No production callers
# remained at the time of deletion.

# ── Section 2: typed daily_metrics table (upsert_daily_metrics / get_daily_metrics) ──

class TestDailyMetricsTable:
    """
    Validates the contract for the 'daily_metrics' table (typed columns).

    Writer: skills/garmin_sync._ingest_daily_metrics() → upsert_daily_metrics()
            hooks/on_sync.py calls _ingest_daily_metrics() (active path)
    Reader: memory/retrieval._rollup_readiness_from_sqlite()
            hooks/on_weekly_rollup.py
            cli/coach.py cmd_parity + cmd_db_sanity

    These tests pin the exact column set.
    """

    EXPECTED_COLUMNS = {
        "day", "hrv_rmssd", "resting_hr", "sleep_score",
        "sleep_duration_h", "body_battery", "training_readiness",
        "stress_avg", "raw_json",
    }

    def setup_method(self):
        self.db = _tmp_db()
        from memory.db import init_db
        init_db(db_path=self.db)

    def test_row_has_all_expected_columns(self):
        from memory.db import upsert_daily_metrics, get_daily_metrics

        today = _today()
        upsert_daily_metrics(
            today,
            hrv_rmssd=60.0, resting_hr=48.0, sleep_score=78.0,
            sleep_duration_h=7.2, body_battery=85, training_readiness=70,
            stress_avg=25.0,
            db_path=self.db,
        )
        rows = get_daily_metrics(today, today, db_path=self.db)
        assert len(rows) == 1
        assert set(rows[0].keys()) == self.EXPECTED_COLUMNS

    def test_partial_upsert_leaves_other_columns_none(self):
        from memory.db import upsert_daily_metrics, get_daily_metrics

        today = _today()
        upsert_daily_metrics(today, hrv_rmssd=55.0, db_path=self.db)
        rows = get_daily_metrics(today, today, db_path=self.db)
        row = rows[0]
        assert row["hrv_rmssd"] == 55.0
        assert row["resting_hr"] is None
        assert row["sleep_score"] is None

    def test_raw_json_defaults_to_empty_object(self):
        from memory.db import upsert_daily_metrics, get_daily_metrics

        today = _today()
        upsert_daily_metrics(today, db_path=self.db)
        rows = get_daily_metrics(today, today, db_path=self.db)
        assert json.loads(rows[0]["raw_json"]) == {}


# ── Section 3: readiness path parity ──────────────────────────────────────────

class TestReadinessPathParity:
    """
    Compare _rollup_readiness (legacy JSON path) vs _rollup_readiness_from_sqlite
    (new SQLite path) for the same synthetic data.

    Goal: document where outputs AGREE and where they DIVERGE so the migration
    can close the gap deliberately.  No assertions force agreement — this is a
    mapping exercise, not a correctness gate.
    """

    def _build_health_json(self, days: int = 3) -> Dict:
        """
        Minimal health_data_cache.json structure that _rollup_readiness() reads.
        Uses the OLD key names that the JSON path expects.
        """
        hrv, sleep, bb, tr, rhr = [], [], [], [], []
        for i in range(days):
            d = (_today() - timedelta(days=i)).isoformat()
            hrv.append({
                "calendarDate": d,
                "lastNight5MinHigh": 60 + i,
                "weeklyAvg": 62,
            })
            sleep.append({
                "calendarDate": d,
                "sleepTimeSeconds": int((7.0 + i * 0.1) * 3600),
                "sleepScoreValue": 75 + i,
            })
            bb.append({"date": d, "charged": 80 + i})
            tr.append({"calendarDate": d, "score": 70 + i})
            rhr.append({"calendarDate": d, "restingHeartRate": 50 - i})
        return {
            "hrv": hrv,
            "sleep": sleep,
            "body_battery": bb,
            "training_readiness": tr,
            "resting_hr": rhr,
        }

    def _populate_sqlite(self, db: Path, days: int = 3) -> None:
        from memory.db import upsert_daily_metrics
        for i in range(days):
            d = _today() - timedelta(days=i)
            upsert_daily_metrics(
                d,
                hrv_rmssd=float(60 + i),
                resting_hr=float(50 - i),
                sleep_score=float(75 + i),
                sleep_duration_h=round(7.0 + i * 0.1, 1),
                body_battery=float(80 + i),
                training_readiness=float(70 + i),
                stress_avg=25.0,
                db_path=db,
            )

    def test_both_paths_return_same_top_level_keys(self):
        from memory.retrieval import _rollup_readiness, _rollup_readiness_from_sqlite
        from memory.db import init_db

        db = _tmp_db()
        init_db(db_path=db)
        self._populate_sqlite(db)
        health = self._build_health_json()

        sqlite_result = _rollup_readiness_from_sqlite(3, db)
        json_result   = _rollup_readiness(health, 3)

        assert sqlite_result is not None
        # Both must have period_days, today, trend
        assert "period_days" in sqlite_result
        assert "today"       in sqlite_result
        assert "trend"       in sqlite_result
        assert "period_days" in json_result
        assert "today"       in json_result
        assert "trend"       in json_result

    def test_today_subkeys_identical(self):
        """Both paths expose the same sub-keys under 'today'."""
        from memory.retrieval import _rollup_readiness, _rollup_readiness_from_sqlite
        from memory.db import init_db

        db = _tmp_db()
        init_db(db_path=db)
        self._populate_sqlite(db)
        health = self._build_health_json()

        sqlite_today = _rollup_readiness_from_sqlite(3, db)["today"]
        json_today   = _rollup_readiness(health, 3)["today"]

        assert set(sqlite_today.keys()) == set(json_today.keys()), (
            f"Key mismatch — sqlite: {set(sqlite_today.keys())} "
            f"json: {set(json_today.keys())}"
        )

    def test_trend_subkeys_identical(self):
        """Both paths expose the same sub-keys under 'trend'."""
        from memory.retrieval import _rollup_readiness, _rollup_readiness_from_sqlite
        from memory.db import init_db

        db = _tmp_db()
        init_db(db_path=db)
        self._populate_sqlite(db)
        health = self._build_health_json()

        sqlite_trend = _rollup_readiness_from_sqlite(3, db)["trend"]
        json_trend   = _rollup_readiness(health, 3)["trend"]

        assert set(sqlite_trend.keys()) == set(json_trend.keys()), (
            f"Key mismatch — sqlite: {set(sqlite_trend.keys())} "
            f"json: {set(json_trend.keys())}"
        )

    def test_sqlite_result_has_source_field_json_does_not(self):
        """
        SQLite path adds source='sqlite'; JSON path has no source field.
        This difference is intentional and must be preserved through migration.
        """
        from memory.retrieval import _rollup_readiness, _rollup_readiness_from_sqlite
        from memory.db import init_db

        db = _tmp_db()
        init_db(db_path=db)
        self._populate_sqlite(db)
        health = self._build_health_json()

        sqlite_result = _rollup_readiness_from_sqlite(3, db)
        json_result   = _rollup_readiness(health, 3)

        assert sqlite_result["source"] == "sqlite"
        assert "source" not in json_result

    def test_sqlite_fallback_when_empty(self):
        """_rollup_readiness_from_sqlite returns None when daily_metrics is empty."""
        from memory.retrieval import _rollup_readiness_from_sqlite
        from memory.db import init_db

        db = _tmp_db()
        init_db(db_path=db)
        result = _rollup_readiness_from_sqlite(7, db)
        assert result is None
