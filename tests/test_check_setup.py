# tests/test_check_setup.py
import json
import sys
import os
import subprocess
from pathlib import Path
import pytest

SCRIPT = Path(__file__).parent.parent / "bin" / "check_setup.py"

def run_check(args=(), env_overrides=None, tmp_path=None):
    """Run check_setup.py with --json, return parsed output."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    cmd = [sys.executable, str(SCRIPT), "--json"]
    if tmp_path:
        cmd += ["--root", str(tmp_path)]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return json.loads(result.stdout)


def test_python_check_passes(tmp_path):
    data = run_check(tmp_path=tmp_path)
    assert data["checks"]["python"]["ok"] is True
    assert "version" in data["checks"]["python"]


def test_athlete_files_missing_when_no_goals(tmp_path):
    data = run_check(tmp_path=tmp_path)
    assert data["checks"]["athlete_files"]["ok"] is False
    assert "goals.md" in data["checks"]["athlete_files"]["missing"]


def test_athlete_files_ok_when_present(tmp_path):
    athlete_dir = tmp_path / "data" / "athlete"
    athlete_dir.mkdir(parents=True)
    required = ["goals.md", "training_preferences.md", "upcoming_races.md"]
    for f in required:
        (athlete_dir / f).write_text("# content")
    data = run_check(tmp_path=tmp_path)
    assert data["checks"]["athlete_files"]["ok"] is True


def test_health_cache_missing(tmp_path):
    data = run_check(tmp_path=tmp_path)
    assert data["checks"]["health_cache"]["ok"] is False


def test_health_cache_present(tmp_path):
    cache_dir = tmp_path / "data" / "health"
    cache_dir.mkdir(parents=True)
    (cache_dir / "health_data_cache.json").write_text('{"activities": [1]}')
    data = run_check(tmp_path=tmp_path)
    assert data["checks"]["health_cache"]["ok"] is True


def test_onboarding_needed_when_athlete_files_missing(tmp_path):
    data = run_check(tmp_path=tmp_path)
    assert data["onboarding_needed"] is True


def test_onboarding_not_needed_when_complete(tmp_path):
    athlete_dir = tmp_path / "data" / "athlete"
    athlete_dir.mkdir(parents=True)
    for f in ["goals.md", "training_preferences.md", "upcoming_races.md"]:
        (athlete_dir / f).write_text("# content")
    cache_dir = tmp_path / "data" / "health"
    cache_dir.mkdir(parents=True)
    (cache_dir / "health_data_cache.json").write_text('{"activities": [1]}')
    data = run_check(tmp_path=tmp_path)
    assert data["onboarding_needed"] is False


def test_garmin_credentials_missing_when_no_env(tmp_path):
    empty_token_dir = tmp_path / "no_tokens"
    empty_token_dir.mkdir()
    data = run_check(
        tmp_path=tmp_path,
        env_overrides={
            "GARMIN_EMAIL": "",
            "GARMIN_PASSWORD": "",
            "GARMIN_TOKEN_DIR": str(empty_token_dir),
        },
    )
    assert data["checks"]["garmin_creds"]["ok"] is False


def test_garmin_credentials_present(tmp_path):
    data = run_check(
        tmp_path=tmp_path,
        env_overrides={"GARMIN_EMAIL": "test@example.com", "GARMIN_PASSWORD": "secret"}
    )
    assert data["checks"]["garmin_creds"]["ok"] is True


def test_discord_config_missing(tmp_path):
    data = run_check(tmp_path=tmp_path)
    assert data["checks"]["discord"]["ok"] is False


def test_discord_config_present(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "discord.env").write_text("DISCORD_BOT_TOKEN=abc123")
    data = run_check(tmp_path=tmp_path)
    assert data["checks"]["discord"]["ok"] is True


def test_json_output_has_all_keys(tmp_path):
    data = run_check(tmp_path=tmp_path)
    assert "onboarding_needed" in data
    assert "checks" in data
    expected_keys = {"python", "deps", "athlete_files", "health_cache",
                     "garmin_creds", "discord", "systemd"}
    assert expected_keys.issubset(data["checks"].keys())
