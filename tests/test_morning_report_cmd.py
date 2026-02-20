"""
Tests for B11-016 — coach morning-report CLI subcommand.

Scope:
  - _build_parser() exposes morning-report with all expected flags
  - cmd_morning_report() routes --check-sleep correctly (mocking run())
  - cmd_morning_report() routes --full-only, --json, --notification-only
  - discord_bot no longer references src/morning_report.py directly
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


# ── argparse wiring ────────────────────────────────────────────────────────────

class TestMorningReportParser:
    """_build_parser() must expose morning-report with all flags."""

    def _parse(self, *args):
        from cli.coach import _build_parser
        return _build_parser().parse_args(["morning-report", *args])

    def test_no_flags_defaults(self):
        args = self._parse()
        assert args.check_sleep is False
        assert args.full_only is False
        assert args.json is False
        assert args.notification_only is False
        assert args.no_weather is False

    def test_check_sleep_flag(self):
        args = self._parse("--check-sleep")
        assert args.check_sleep is True

    def test_full_only_flag(self):
        args = self._parse("--full-only")
        assert args.full_only is True

    def test_json_flag(self):
        args = self._parse("--json")
        assert args.json is True

    def test_notification_only_flag(self):
        args = self._parse("--notification-only")
        assert args.notification_only is True

    def test_no_weather_flag(self):
        args = self._parse("--no-weather")
        assert args.no_weather is True

    def test_func_is_cmd_morning_report(self):
        from cli.coach import cmd_morning_report
        args = self._parse("--check-sleep")
        assert args.func is cmd_morning_report


# ── cmd_morning_report dispatch ────────────────────────────────────────────────

class TestCmdMorningReport:
    """cmd_morning_report must call morning_report.run() with correct kwargs."""

    def _run_cmd(self, *cli_args):
        """Parse args and invoke cmd_morning_report with mocked morning_report.run."""
        from cli.coach import _build_parser, cmd_morning_report

        args = _build_parser().parse_args(["morning-report", *cli_args])
        calls = {}

        def fake_run(**kwargs):
            calls.update(kwargs)
            return 0

        src_dir = str(PROJECT_ROOT / "src")
        # Ensure src/ is importable then patch the run function
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        with patch("morning_report.run", side_effect=fake_run):
            rc = cmd_morning_report(args)

        return rc, calls

    def test_check_sleep_propagated(self):
        rc, calls = self._run_cmd("--check-sleep")
        assert rc == 0
        assert calls["check_sleep"] is True

    def test_full_only_propagated(self):
        _, calls = self._run_cmd("--full-only")
        assert calls["full_only"] is True
        assert calls["check_sleep"] is False

    def test_json_propagated(self):
        _, calls = self._run_cmd("--json")
        assert calls["as_json"] is True

    def test_notification_only_propagated(self):
        _, calls = self._run_cmd("--notification-only")
        assert calls["notification_only"] is True

    def test_no_weather_propagated(self):
        _, calls = self._run_cmd("--no-weather")
        assert calls["no_weather"] is True

    def test_returns_run_exit_code(self):
        from cli.coach import _build_parser, cmd_morning_report
        args = _build_parser().parse_args(["morning-report", "--check-sleep"])

        src_dir = str(PROJECT_ROOT / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        with patch("morning_report.run", return_value=1):
            rc = cmd_morning_report(args)
        assert rc == 1


# ── morning_report.run() unit ──────────────────────────────────────────────────

class TestMorningReportRun:
    """morning_report.run() must return int exit codes (not call sys.exit)."""

    def setup_method(self):
        src_dir = str(PROJECT_ROOT / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

    def test_check_sleep_true_returns_0(self):
        from morning_report import run
        with patch("morning_report.has_todays_sleep", return_value=True):
            rc = run(check_sleep=True)
        assert rc == 0

    def test_check_sleep_false_returns_1(self):
        from morning_report import run
        with patch("morning_report.has_todays_sleep", return_value=False):
            rc = run(check_sleep=True)
        assert rc == 1

    def test_returns_int_not_none(self):
        from morning_report import run
        with patch("morning_report.has_todays_sleep", return_value=True):
            result = run(check_sleep=True)
        assert isinstance(result, int)


# ── discord_bot no longer calls src/morning_report.py directly ─────────────────

class TestDiscordBotMigration:
    """discord_bot.py must not contain direct calls to src/morning_report.py."""

    def test_no_direct_morning_report_subprocess(self):
        bot_path = PROJECT_ROOT / "src" / "discord_bot.py"
        content = bot_path.read_text(encoding="utf-8")
        assert "src/morning_report.py" not in content, (
            "discord_bot.py still references src/morning_report.py directly; "
            "all calls should go through coach morning-report"
        )

    def test_morning_report_routed_via_coach(self):
        bot_path = PROJECT_ROOT / "src" / "discord_bot.py"
        content = bot_path.read_text(encoding="utf-8")
        assert "morning-report" in content, (
            "discord_bot.py has no reference to 'morning-report'; "
            "expected coach CLI routing"
        )
