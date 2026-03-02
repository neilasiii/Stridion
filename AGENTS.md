# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `src/` (Garmin sync, planning logic, Discord bot, and utility modules). CLI entrypoints are in `cli/` (`python3 cli/coach.py ...`). Planning/orchestration logic is split across `brain/`, `memory/`, `agent/`, and `hooks/`. Tests are in `tests/` and follow `test_*.py` naming. Operational scripts are in `bin/`, and long-form documentation is in `docs/`. Runtime state and generated artifacts are stored under `data/` and `vault/`.

## Build, Test, and Development Commands
- `python3 -m pip install -r requirements.txt -r requirements-dev.txt`: install runtime + dev dependencies.
- `python3 cli/coach.py --help`: list CLI commands.
- `python3 cli/coach.py sync`: pull Garmin health/activity data into local cache.
- `python3 cli/coach.py plan --week`: generate the weekly plan.
- `python3 -m pytest`: run full test suite from `tests/`.
- `python3 -m pytest --cov=src --cov-report=term-missing`: run tests with coverage details.
- `black src tests cli brain memory agent hooks`: format code.
- `flake8 src tests cli brain memory agent hooks`: lint for style/issues.
- `mypy src`: run static type checks.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation and PEP 8 conventions. Prefer explicit, descriptive names (`sync_garmin_data`, `test_publish_to_garmin`). Use `snake_case` for functions/files, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Keep modules focused by domain (planning in `brain/`, persistence in `memory/`, integrations in `src/`). Run `black` and `flake8` before opening a PR.

## Testing Guidelines
Pytest is configured in `pytest.ini` with strict markers and verbose output. Place tests in `tests/` and name files/functions as `test_*.py` / `test_*`. Use markers (`unit`, `integration`, `security`, `slow`) where appropriate. Add or update tests for behavior changes, especially around planner rails, sync flows, and CLI command paths.

## Commit & Pull Request Guidelines
Recent history favors Conventional Commit style with optional scopes, e.g. `fix(macro): ...`, `test(macro): ...`, `docs(readme): ...`, `chore(data): ...`. Keep subject lines imperative and specific. For PRs, include:
- a short problem/solution summary,
- linked issue(s) when applicable,
- test evidence (commands + results),
- sample CLI output or screenshots for user-visible command changes.

Keep PRs focused; separate refactors from behavior changes when possible.
