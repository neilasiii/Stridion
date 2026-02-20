# Backlog — running-coach refactor

_Last updated: 2026-02-20 (batch run: B11-001–003, B11-005–006, B11-015, B11-017 DONE). See `docs/PHASE_11_AUDIT.md` for full rationale._

---

## How to Use This Backlog

1. **Iterative execution**: Paste `docs/BACKLOG_RUNNER_PROMPT.md` into Claude Code. Claude picks the next unblocked item, implements it, updates this file.
2. **One item per run**: Each Claude Code session completes exactly 1 backlog item then stops. This fits within Claude usage limits and keeps diffs reviewable.
3. **Status values**: `TODO` | `IN PROGRESS` | `DONE` | `BLOCKED` | `DEFERRED`
4. **Dependency notation**: Item IDs in the `Dependencies` column must be `DONE` before an item can be started.
5. **Safety gates** (see below) run before every destructive change.
6. **Adding items**: Claude may *suggest* new items at the end of a run but must NOT add them to the table without user approval.

---

## Safety Gates

Before executing any item tagged **Risk: M** or **Risk: H**, Claude MUST run all three gates and report results:

```bash
# Gate 1: Tests pass
python -m pytest tests/ -x -q

# Gate 2: No new secret leaks
gitleaks detect --source . --no-git --log-level warn 2>&1 | tail -20

# Gate 3: All modified Python files are syntactically valid
python -m compileall <modified-files> -q
```

If any gate fails, stop and report. Do NOT continue to the implementation.

---

## Backlog Table

| ID | Title | Scope | Files Touched | Acceptance Criteria | Risk | Est. Tokens | Status | Dependencies | Notes |
|---|---|---|---|---|---|---|---|---|---|
| B11-001 | Delete broken security tests | Cleanup | `tests/test_security.py` | File deleted; `pytest tests/` still passes | L | S | **DONE** | — | Deleted 2026-02-20; `src/web.app` never existed; 59 tests pass |
| B11-002 | Delete one-off bin cleanup scripts | Cleanup | `bin/delete_strength_mobility_next_week.py`, `bin/delete_strength_mobility_workouts.py`, `bin/fix_strength_rotation.py`, `bin/remove_finalsurge_strength.py` | Files deleted; `pytest tests/` passes; no other file imports them | L | S | **DONE** | — | Deleted 2026-02-20; all were untracked (never committed); zero callers confirmed via rg |
| B11-003 | Archive orphaned src/ files | Cleanup | `src/discord_bot_streaming.py`, `src/test_streprogen.py`, `src/coach_service/` (entire dir) | Files moved to `archive/` dir; `pytest tests/` passes; no imports broken | L | S | **DONE** | — | Moved to `archive/src/` 2026-02-20; zero callers confirmed via rg; 59 tests pass |
| B11-004 | Delete pre-Memory OS planned workout stack | Cleanup | `src/planned_workout_manager.py`, `src/planned_workout_cli.py`, `src/extract_baseline_plan.py`, `bin/planned_workouts.sh` | Files deleted; `pytest tests/` passes; no callers exist | M | S | **TODO** | B11-003 | Verify `bin/planned_workouts.sh` is the only external caller before deleting |
| B11-005 | Move root-level test files into tests/ | Cleanup | `test_ai_call.py`, `test_location_fix.py`, `test_location_geocoding.py`, `test_session.py` | Files moved to `tests/`; `pytest tests/` passes; root dir clean | L | S | **DONE** | B11-001 | Moved 2026-02-20; added `tests/conftest.py` collect_ignore for 4 standalone scripts; 59 tests pass |
| B11-006 | Fix smart_sync.sh Termux shebang | Bug fix | `bin/smart_sync.sh` | Line 1 changed to `#!/usr/bin/env bash`; smoke test `bash bin/smart_sync.sh` still works | L | S | **DONE** | — | Fixed 2026-02-20; was `#!/data/data/com.termux/...`; now `#!/usr/bin/env bash`; bash -n syntax OK |
| B11-007 | Add `--days` and `--check-only` to `coach sync` | Enhancement | `cli/coach.py`, `skills/garmin_sync.py` | `coach sync --days 7` and `coach sync --check-only` work; tests pass | M | M | **TODO** | — | Currently only available by running `src/garmin_sync.py` directly |
| B11-008 | Move cache-age check from bash into Python | Refactor | `skills/garmin_sync.py`, `bin/smart_sync.sh` | `skills/garmin_sync.run(max_age_minutes=30)` implements age check natively; `smart_sync.sh` kept as thin shim calling `coach sync`; test added | M | M | **TODO** | B11-007 | Eliminates shell fork overhead for cache-hit path; makes skill unit-testable |
| B11-009 | Cap `memory/retrieval.py` to last-N activities | Performance | `memory/retrieval.py` | Context packet loads only last 14 days of activities (not full cache); test verifies token count drops; brain behavior unchanged | M | M | **TODO** | — | Full health cache loaded on every LLM call; high token cost risk |
| B11-010 | Add `daily_metrics` table to SQLite schema | Schema | `memory/db.py` | `daily_metrics` table created via `init_db()`; migration is additive (no existing data dropped); `pytest tests/` passes | M | M | **TODO** | — | Required for Stage 1 of SQLite migration |
| B11-011 | Add `activities` table to SQLite schema | Schema | `memory/db.py` | `activities` table created via `init_db()`; migration additive; `pytest tests/` passes | M | M | **TODO** | B11-010 | Required for Stage 1 |
| B11-012 | Wire post-sync SQLite ingest (daily metrics) | Integration | `skills/garmin_sync.py`, `memory/db.py` | After successful sync, `daily_metrics` rows inserted/updated for synced date range; smoke test shows rows present after `coach sync` | M | M | **TODO** | B11-010, B11-008 | Stage 1 write-through; JSON cache still primary read path |
| B11-013 | Wire post-sync SQLite ingest (activities) | Integration | `skills/garmin_sync.py`, `memory/db.py` | After successful sync, `activities` rows inserted/updated; smoke test shows rows present | M | M | **TODO** | B11-011, B11-012 | Stage 1 write-through; depends on B11-012 pattern |
| B11-014 | Update `memory/retrieval.py` to read daily_metrics from SQLite | Migration | `memory/retrieval.py` | Context packet reads recovery metrics from `daily_metrics` table; falls back to JSON cache if table empty; unit test added | H | M | **TODO** | B11-012 | Stage 2 — read from SQLite. Test with empty table (fallback path) and populated table |
| B11-015 | Archive bin/delete_all_workouts.py with safety gate | Safety | `bin/delete_all_workouts.py` | Script moved to `archive/`; or wrapped with `--confirm` prompt before any Garmin API calls | M | S | **DONE** | — | Added `--confirm` required flag 2026-02-20; exits safely without it; docstring updated; 59 tests pass |
| B11-016 | Migrate morning_report to `coach morning-report` CLI subcommand | Architecture | `cli/coach.py`, `src/morning_report.py` | `coach morning-report` command works; `src/discord_bot.py` updated to call `coach morning-report` instead of `python3 src/morning_report.py`; tests pass | H | L | **TODO** | — | Aligns morning_report with CLI-first design; eliminates inconsistency where bot calls src/ directly |
| B11-017 | Audit and document actual heartbeat mechanism | Documentation | `docs/HEARTBEAT.md`, possibly `src/discord_bot.py`, `agent/runner.py`, systemd units | `docs/HEARTBEAT.md` created describing: (1) where sync runs (bot loop vs systemd vs cron), (2) frequency, (3) lock coordination, (4) how to change interval; verified against actual code + systemd state | L | S | **DONE** | — | Created `docs/HEARTBEAT.md` 2026-02-20; verified against runner.py, lock.py, service file; 9 sections |
| B11-018 | Make schedule output mobile-first by default | UX | `cli/coach.py`, `src/discord_bot.py`, possibly schedule formatter | `/coach_schedule` defaults to compact/mobile format; long lines wrapped; no horizontal scrolling needed on mobile; table format still available via `--format table` | L | S | **TODO** | — | Mobile is primary interface; current aligned table format degrades on Discord mobile |
| B11-019 | Add `sync_runs` table + freshness visibility | Observability / Sync provenance | `memory/db.py`, `skills/garmin_sync.py`, `cli/coach.py`, `src/discord_bot.py` (and tests as needed) | (1) New SQLite table `sync_runs` created by `init_db()` (additive; no existing tables altered/dropped). (2) Every `coach sync` writes a row with: `started_at`, `finished_at`, `status`, `source`, `days_requested`, `days_synced`, `error_summary` (nullable), `run_id`. (3) `coach agent status` displays: last successful sync timestamp, age in minutes, last run status + error summary if failed. (4) Discord `/coach_status` embed includes same freshness fields. (5) Tests added for table creation + at least one "sync run recorded" path (mocking ok). | M | M | **TODO** | — | Unblocks safe JSON→SQLite migration by removing guesswork about staleness/heartbeat. Freshness must be derived from `sync_runs` success timestamps, not file mtime. |

---

## Deferred / Not Actionable Yet

| ID | Title | Reason Deferred |
|---|---|---|
| B11-D01 | Stage 2: Read exclusively from SQLite (remove JSON cache reads) | Requires B11-013 and B11-014 to be stable for ≥1 week |
| B11-D02 | Stage 3: Remove `health_data_cache.json` | Requires Stage 2 proven stable |
| B11-D03 | Remove ICS constraint rescheduling from `src/garmin_sync.py` | Requires Brain to handle all rescheduling (not yet verified) |
| B11-D04 | Deprecate `bin/sync_garmin_data.sh` in favor of native Python | Requires B11-008 fully stable |
| B11-D05 | Add `coach morning-report` and wire Discord bot | Requires B11-016 |

---

## Completed Items

_(moved here after status = DONE)_

| ID | Title | Completed | Notes |
|---|---|---|---|
| — | Phase 11 audit docs created | 2026-02-20 | `docs/PHASE_11_AUDIT.md`, `docs/BACKLOG.md`, `docs/BACKLOG_RUNNER_PROMPT.md` |
| B11-001 | Delete broken security tests | 2026-02-20 | `git rm tests/test_security.py`; 59 tests pass |
| B11-002 | Delete one-off bin cleanup scripts | 2026-02-20 | Removed 4 untracked bin/ scripts; zero callers; 59 tests pass |
| B11-003 | Archive orphaned src/ files | 2026-02-20 | `git mv` to `archive/src/`; zero callers; 59 tests pass |
| B11-005 | Move root-level test files into tests/ | 2026-02-20 | Moved 4 files; added `tests/conftest.py` collect_ignore; 59 tests pass |
| B11-015 | Archive delete_all_workouts.py with safety gate | 2026-02-20 | Added `--confirm` required guard; exits safely without it; 59 tests pass |
| B11-017 | Audit and document heartbeat mechanism | 2026-02-20 | Created `docs/HEARTBEAT.md`; 9 sections; verified against code + service file |
| B11-006 | Fix smart_sync.sh Termux shebang | 2026-02-20 | Line 1 → `#!/usr/bin/env bash`; `bash -n` syntax OK; 59 tests pass |
