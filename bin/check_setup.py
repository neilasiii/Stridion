#!/usr/bin/env python3
"""
check_setup.py — System check script for running-coach onboarding.

Usage:
    python3 bin/check_setup.py           # Human-readable output
    python3 bin/check_setup.py --json    # JSON output for agent consumption
    python3 bin/check_setup.py --fix     # Auto-fix where possible
    python3 bin/check_setup.py --json --root /some/path  # Use alternate root (for testing)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _project_root(override=None):
    if override:
        return Path(override)
    return Path(__file__).parent.parent


def check_python():
    v = sys.version_info
    ok = v >= (3, 8)
    return {"ok": ok, "version": f"{v.major}.{v.minor}.{v.micro}"}


def check_deps(root):
    req = root / "requirements.txt"
    if not req.exists():
        return {"ok": False, "reason": "requirements.txt not found"}
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return {"ok": True}
    missing = []
    for line in result.stdout.splitlines():
        if "not installed" in line.lower():
            pkg = line.split()[0]
            missing.append(pkg)
    return {"ok": False, "missing": missing or ["see pip check output"]}


def check_athlete_files(root):
    athlete_dir = root / "data" / "athlete"
    required = ["goals.md", "training_preferences.md", "upcoming_races.md"]
    missing = [f for f in required if not (athlete_dir / f).exists()]
    return {"ok": len(missing) == 0, "missing": missing}


def check_health_cache(root):
    cache = root / "data" / "health" / "health_data_cache.json"
    if not cache.exists():
        return {"ok": False, "reason": "file not found"}
    try:
        data = json.loads(cache.read_text())
        if not data:
            return {"ok": False, "reason": "empty"}
        return {"ok": True}
    except json.JSONDecodeError:
        return {"ok": False, "reason": "invalid JSON"}


def check_garmin_creds():
    email = os.environ.get("GARMIN_EMAIL", "").strip()
    password = os.environ.get("GARMIN_PASSWORD", "").strip()
    token_dir_override = os.environ.get("GARMIN_TOKEN_DIR", "").strip()
    token_dir = Path(token_dir_override) if token_dir_override else Path.home() / ".garminconnect"
    has_tokens = token_dir.exists() and any(token_dir.iterdir())
    if (email and password) or has_tokens:
        return {"ok": True, "method": "tokens" if has_tokens else "password"}
    return {"ok": False, "reason": "no credentials or tokens found"}


def check_discord(root):
    cfg = root / "config" / "discord.env"
    if not cfg.exists():
        return {"ok": False, "reason": "config/discord.env not found"}
    content = cfg.read_text()
    if "DISCORD_BOT_TOKEN" not in content:
        return {"ok": False, "reason": "DISCORD_BOT_TOKEN not set in config/discord.env"}
    return {"ok": True}


def check_systemd():
    result = subprocess.run(
        ["systemctl", "is-enabled", "running-coach-bot"],
        capture_output=True, text=True
    )
    ok = result.returncode == 0 and result.stdout.strip() == "enabled"
    return {"ok": ok}


def auto_fix(root):
    fixes = []
    for d in ["data/athlete", "data/health", "data/plans", "data/calendar", "config"]:
        path = root / d
        if not path.exists():
            path.mkdir(parents=True)
            fixes.append(f"Created {d}/")
    req = root / "requirements.txt"
    if req.exists():
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req), "-q"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            fixes.append("Installed Python dependencies")
    return fixes


def run_checks(root):
    return {
        "python": check_python(),
        "deps": check_deps(root),
        "athlete_files": check_athlete_files(root),
        "health_cache": check_health_cache(root),
        "garmin_creds": check_garmin_creds(),
        "discord": check_discord(root),
        "systemd": check_systemd(),
    }


def onboarding_needed(checks):
    return (
        not checks["athlete_files"]["ok"] or
        not checks["health_cache"]["ok"]
    )


def print_human(checks, needed):
    icons = {True: "OK", False: "MISSING"}
    print("\nRunning Coach -- Setup Status\n" + "=" * 32)
    labels = {
        "python": "Python >= 3.8",
        "deps": "Python dependencies",
        "athlete_files": "Athlete profile files",
        "health_cache": "Garmin health data",
        "garmin_creds": "Garmin credentials",
        "discord": "Discord bot config",
        "systemd": "Discord bot service",
    }
    for key, label in labels.items():
        c = checks[key]
        icon = icons[c["ok"]]
        detail = ""
        if not c["ok"]:
            detail = f" -- {c.get('reason') or ', '.join(c.get('missing', []))}"
        print(f"  [{icon}] {label}{detail}")
    print()
    if needed:
        print("Onboarding needed: run @onboarding-wizard in Claude Code")
    else:
        print("All clear -- system ready")
    print()


def main():
    parser = argparse.ArgumentParser(description="Check running-coach setup")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--fix", action="store_true", help="Auto-fix where possible")
    parser.add_argument("--root", help="Project root override (for testing)")
    args = parser.parse_args()

    root = _project_root(args.root)

    if args.fix:
        fixes = auto_fix(root)
        if fixes:
            print("Fixed:\n" + "\n".join(f"  - {f}" for f in fixes))

    checks = run_checks(root)
    needed = onboarding_needed(checks)

    if args.json:
        print(json.dumps({"onboarding_needed": needed, "checks": checks}))
    else:
        print_human(checks, needed)


if __name__ == "__main__":
    main()
