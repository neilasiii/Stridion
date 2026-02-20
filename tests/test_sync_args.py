"""
Tests for B11-007 — --days and --check-only flags on `coach sync`.

Scope:
  - skills/garmin_sync.run() passes --days to sync_garmin_data.sh
  - skills/garmin_sync.run() passes --check-only to sync_garmin_data.sh
  - With neither flag, falls back to smart_sync.sh (existing behaviour)
  - CLI argparse wires the flags through to run()
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

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
    """skills/garmin_sync.run() — command-selection logic."""

    def _call_run(self, **kwargs):
        """Call skills.garmin_sync.run() with subprocess mocked."""
        from skills import garmin_sync

        # init_db, log_task_*, record_sync_*, insert_event are imported locally
        # inside run(), so patch them at the memory.db level.
        with (
            patch("skills.garmin_sync.subprocess.run", return_value=_fake_proc()) as mock_sp,
            patch("memory.db.init_db"),
            patch("memory.db.log_task_start", return_value=1),
            patch("memory.db.log_task_finish"),
            patch("memory.db.record_sync_start", return_value="rid"),
            patch("memory.db.record_sync_finish"),
            patch("memory.db.insert_event", return_value="a" * 32),
        ):
            garmin_sync.run(**kwargs)
            return mock_sp.call_args

    def test_default_uses_smart_sync(self):
        args = self._call_run()
        cmd = args[0][0]
        assert "smart_sync.sh" in cmd[-1] or any("smart_sync" in p for p in cmd)

    def test_force_uses_smart_sync_with_force(self):
        args = self._call_run(force=True)
        cmd = args[0][0]
        assert any("smart_sync" in p for p in cmd)
        assert "--force" in cmd

    def test_days_uses_sync_garmin_data(self):
        args = self._call_run(days=7)
        cmd = args[0][0]
        assert any("sync_garmin_data" in p for p in cmd)
        assert "--days" in cmd
        assert "7" in cmd

    def test_check_only_uses_sync_garmin_data(self):
        args = self._call_run(check_only=True)
        cmd = args[0][0]
        assert any("sync_garmin_data" in p for p in cmd)
        assert "--check-only" in cmd

    def test_days_and_check_only_combined(self):
        args = self._call_run(days=14, check_only=True)
        cmd = args[0][0]
        assert any("sync_garmin_data" in p for p in cmd)
        assert "--days" in cmd
        assert "14" in cmd
        assert "--check-only" in cmd


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
