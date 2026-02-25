"""
Tests for B11-007 — --days and --check-only flags on `coach sync`.
Tests for B11-008 — native Python cache-age check in skills/garmin_sync.run().

Scope:
  - skills/garmin_sync.run() passes --days to sync_garmin_data.sh
  - skills/garmin_sync.run() passes --check-only to sync_garmin_data.sh
  - With stale / absent cache, run() calls sync_garmin_data.sh
  - With fresh cache and force=False, run() returns skipped=True without subprocess
  - force=True bypasses cache-age check
  - CLI argparse wires the flags through to run()
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _fake_proc(rc=0, stdout="ok\n", stderr=""):
    m = MagicMock()
    m.returncode = rc
    m.stdout = stdout
    m.stderr = stderr
    return m


class TestGarminSyncRunDaysFlag:
    """skills/garmin_sync.run() — command-selection and cache-age logic."""

    def _call_run(self, stale_cache=True, **kwargs):
        """
        Call skills.garmin_sync.run() with subprocess and cache-age mocked.
        stale_cache=True simulates an old / absent cache (forces sync).
        stale_cache=False simulates a fresh cache.
        """
        from skills import garmin_sync

        age = 999.0 if stale_cache else 1.0  # minutes

        # init_db, log_task_*, record_sync_*, insert_event are imported locally
        # inside run(), so patch them at the memory.db level.
        with (
            patch("skills.garmin_sync._cache_age_minutes", return_value=age),
            patch("skills.garmin_sync.subprocess.run", return_value=_fake_proc()) as mock_sp,
            patch("memory.db.init_db"),
            patch("memory.db.log_task_start", return_value=1),
            patch("memory.db.log_task_finish"),
            patch("memory.db.record_sync_start", return_value="rid"),
            patch("memory.db.record_sync_finish"),
            patch("memory.db.insert_event", return_value="a" * 32),
        ):
            result = garmin_sync.run(**kwargs)
            return result, mock_sp.call_args

    # ── B11-007: --days / --check-only routing ───────────────────────────────

    def test_days_uses_sync_garmin_data(self):
        _, args = self._call_run(days=7)
        cmd = args[0][0]
        assert any("sync_garmin_data" in p for p in cmd)
        assert "--days" in cmd
        assert "7" in cmd

    def test_check_only_uses_sync_garmin_data(self):
        _, args = self._call_run(check_only=True)
        cmd = args[0][0]
        assert any("sync_garmin_data" in p for p in cmd)
        assert "--check-only" in cmd

    def test_days_and_check_only_combined(self):
        _, args = self._call_run(days=14, check_only=True)
        cmd = args[0][0]
        assert any("sync_garmin_data" in p for p in cmd)
        assert "--days" in cmd
        assert "14" in cmd
        assert "--check-only" in cmd

    # ── B11-008: native Python cache-age check ───────────────────────────────

    def test_stale_cache_triggers_sync(self):
        result, sp_args = self._call_run(stale_cache=True)
        assert result["skipped"] is False
        assert sp_args is not None, "subprocess.run should have been called"

    def test_fresh_cache_skips_sync(self):
        result, sp_args = self._call_run(stale_cache=False)
        assert result["skipped"] is True
        assert result["success"] is True
        assert sp_args is None, "subprocess.run should NOT have been called"

    def test_force_bypasses_cache_check(self):
        result, sp_args = self._call_run(stale_cache=False, force=True)
        assert result["skipped"] is False
        assert sp_args is not None, "force=True must trigger subprocess regardless of cache age"

    def test_default_uses_sync_garmin_data_not_smart_sync(self):
        """After B11-008: default path calls sync_garmin_data.sh, not smart_sync.sh."""
        _, sp_args = self._call_run(stale_cache=True)
        cmd = sp_args[0][0]
        assert any("sync_garmin_data" in p for p in cmd)
        assert not any("smart_sync" in p for p in cmd)

    def test_sync_enforces_no_auto_workout_generation(self):
        """Sync must not auto-publish workouts; export-garmin is explicit."""
        _, sp_args = self._call_run(stale_cache=True)
        cmd = sp_args[0][0]
        assert "--no-auto-workouts" in cmd


class TestCoachSyncCLIArgs:
    """CLI argparse wires --days / --check-only through to run()."""

    def _invoke_cli(self, extra_args):
        """Parse args with the real argparse setup."""
        from cli.coach import _build_parser
        return _build_parser().parse_args(["sync"] + extra_args)

    def test_days_arg_parsed(self):
        args = self._invoke_cli(["--days", "7"])
        assert args.days == 7

    def test_check_only_arg_parsed(self):
        args = self._invoke_cli(["--check-only"])
        assert args.check_only is True

    def test_force_still_works(self):
        args = self._invoke_cli(["--force"])
        assert args.force is True

    def test_defaults(self):
        args = self._invoke_cli([])
        assert args.days is None
        assert args.check_only is False
        assert args.force is False
