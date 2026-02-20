# Phase 11 — Repo-wide Keep / Refactor / Delete Audit

_Generated: 2026-02-20. Evidence gathered via ripgrep import scans, CLI entrypoint tracing, and test-file cross-references._

---

## 1. Architecture Summary (Intended Flow)

### Authority Hierarchy (Non-Negotiable)

```
data/coach.sqlite           ← AUTHORITATIVE: plan, plan_days, events, state
data/health/health_data_cache.json  ← Garmin truth (write only by src/garmin_sync.py)
FinalSurge/ICS calendars    ← Optional input only; never authoritative
Garmin Connect API          ← Execution layer: read health, write workouts
```

### Authoritative Owner per Domain

| Domain | Authoritative Source | Written By | Read By |
|---|---|---|---|
| Training Plan | `data/coach.sqlite` → `plans`, `plan_days` | `brain/planner.py` via `memory/db.py` | `skills/plans.py`, `cli/coach.py brief` |
| Schedule | `data/coach.sqlite` → `plan_days` | `brain/planner.py` | `cli/coach.py schedule`, Discord bot |
| Garmin Workouts (published) | Garmin Connect API | `skills/publish_to_garmin.py` | Garmin device |
| Garmin Health Data | `data/health/health_data_cache.json` | `src/garmin_sync.py` only | `memory/retrieval.py` |
| Memory / Events | `data/coach.sqlite` → `events`, `state` | `memory/db.py` | `cli/coach.py memory`, brain context |
| Exports | `data/calendar/running_coach_export.ics` | `src/ics_exporter.py` | External calendars |

### Canonical Request Flows

**Sync:**
```
Discord /coach_sync or `coach sync`
  → cli/coach.py cmd_sync()
  → skills/garmin_sync.run()
  → bin/smart_sync.sh → bin/sync_garmin_data.sh
  → src/garmin_sync.py (writes health_data_cache.json)
  → memory/db.py insert_event("garmin_sync")
```

**Plan:**
```
Discord /coach_plan or `coach plan --week`
  → cli/coach.py cmd_plan()
  → memory/retrieval.py build_context_packet()
  → brain/planner.py plan_week() [LLM call]
  → memory/db.py insert_plan()
```

**Publish to Garmin:**
```
`coach export-garmin --live`
  → cli/coach.py cmd_export_garmin()
  → skills/publish_to_garmin.publish()
  → skills/internal_plan_to_scheduled_workouts.py
  → src/auto_workout_generator.py (workout description → Garmin steps)
  → src/workout_uploader.py (Garmin API POST)
  → data/generated_workouts.json updated (skip gate)
```

**Morning Report (still via Discord bot subprocess, not CLI):**
```
Discord scheduled task (5:30–10:00 AM EST)
  → src/discord_bot.py (sleep check)
  → subprocess: python3 src/morning_report.py --full-only
```

---

## 2. Module Inventory Table

### 2a. CLI / Entry Layer

| Path | Purpose | Still Used? | Who Calls It | Recommended Action | Rationale |
|---|---|---|---|---|---|
| `cli/coach.py` | Unified CLI: sync, plan, export, brief, schedule, memory, agent | **YES** | Discord bot subprocess, direct CLI | **KEEP** | Canonical entrypoint; all bot commands route here |
| `bin/sync_garmin_data.sh` | Runs `src/garmin_sync.py` + dedup + auto-workout generation | **YES** | `bin/smart_sync.sh` → this | **REFACTOR** | Called by `smart_sync.sh`; still uses legacy `auto_workout_generator.py` flow; should be gated by internal plan authority |
| `bin/smart_sync.sh` | Cache-age check wrapper around `sync_garmin_data.sh` | **YES** | `skills/garmin_sync.py` | **KEEP** | Correct abstraction; note Termux shebang on line 1 is wrong for Linux |
| `bin/daily_workouts.sh` | Shows today's workouts | Unknown | Manual use | **DELETE or ARCHIVE** | Functionality covered by `coach brief --today` + Discord `/coach_today` |
| `bin/morning_report.sh` | Generates morning readiness report | **YES** | Manual use; `bin/archive/` references | **KEEP** (low priority) | Still useful as manual fallback; bot handles automation |
| `bin/planned_workouts.sh` | Wraps `src/planned_workout_cli.py` | Unknown | Manual use | **DELETE** | `planned_workout_cli.py` is pre-SQLite legacy; functionality superseded |
| `bin/export_calendar.sh` | Exports plan to ICS | Unknown | Manual use | **KEEP** (low priority) | Useful utility; consider wiring to `coach export` subcommand |
| `bin/upload_workout.sh` | Manual workout upload | Unknown | Manual use | **ARCHIVE** | Sacred path now goes through `skills/publish_to_garmin.py`; bypassing it is dangerous |
| `bin/post_workouts_now.sh` | Force-post workouts | Unknown | Manual use | **ARCHIVE** | Same concern — bypasses sacred publish path |
| `bin/validate_ai_report.sh` | Validates AI response against health data | Unknown | Manual use | **KEEP** | Useful debugging tool; wire to CI gate |
| `bin/generate_garmin_tokens.py` | OAuth token generation | Unknown | Manual setup | **KEEP** | Required for initial auth setup |
| `bin/analyze_plan.py` | Analyze plan structure | Unknown | Manual use | **REVIEW** | Could be useful; check if it works with SQLite plans |
| `bin/delete_all_workouts.py` | Delete all Garmin workouts | Unknown | Manual use | **ARCHIVE + GATE** | Destructive; no confirmation; risky |
| `bin/delete_duplicate_workouts.py` | Dedup Garmin workouts | Unknown | Manual use | **ARCHIVE** | Duplicates functionality in `src/deduplicate_workouts.py` |
| `bin/delete_strength_mobility_next_week.py` | Remove non-running workouts | Unknown | Manual use | **DELETE** | One-off cleanup script; strength/mobility disabled anyway |
| `bin/delete_strength_mobility_workouts.py` | Remove strength/mobility | Unknown | Manual use | **DELETE** | Same — one-off cleanup |
| `bin/fix_strength_rotation.py` | Fix strength program rotation | Unknown | Manual use | **DELETE** | One-off fix script; streprogen disabled |
| `bin/remove_finalsurge_strength.py` | Remove FinalSurge strength | Unknown | Manual use | **DELETE** | Stale; FinalSurge no longer authoritative |

### 2b. Source Modules (src/)

| Path | Purpose | Still Used? | Who Calls It | Recommended Action | Rationale |
|---|---|---|---|---|---|
| `src/garmin_sync.py` | Garmin Connect API sync (2228 lines) | **YES** | `bin/sync_garmin_data.sh` (main), `tests/test_garmin_sync.py` | **REFACTOR** | Sacred but bloated; ICS/constraint logic now redundant; see D2 |
| `src/auto_workout_generator.py` | FinalSurge → Garmin structured workout steps | **YES** | `skills/publish_to_garmin.py` | **KEEP** (sacred) | Only called via sacred publish path; do not modify entrypoint |
| `src/workout_uploader.py` | Garmin API upload | **YES** | `skills/publish_to_garmin.py` | **KEEP** (sacred) | Only called via sacred publish path |
| `src/discord_bot.py` | Main Discord bot (1484 lines) | **YES** | systemd `running-coach-bot` | **KEEP + REFACTOR** | Still active; has dead code around `morning_report.py`, old session management vestiges |
| `src/morning_report.py` | AI-powered morning readiness report | **YES** | `src/discord_bot.py` (subprocess), `bin/morning_report.sh` | **KEEP** | Still wired to Discord bot scheduled task; not yet routed through CLI |
| `src/garmin_token_auth.py` | OAuth token management | **YES** | `src/garmin_sync.py` | **KEEP** | Required for auth; well-scoped |
| `src/vdot_calculator.py` | Jack Daniels VDOT calculator | Unknown | `.claude/agents/vdot-running-coach.md` docs reference | **KEEP** | Still relevant; brain/planner uses VDOT concepts |
| `src/workout_parser.py` | Parse FinalSurge workout descriptions | **YES** | `src/auto_workout_generator.py` | **KEEP** | Part of sacred publish path |
| `src/ics_parser.py` | Parse ICS calendars | **YES** | `src/garmin_sync.py` | **REFACTOR** | ICS is now optional input; used during sync for FinalSurge import |
| `src/ics_exporter.py` | Export plan to ICS | **YES** | `src/garmin_sync.py` (`--export-calendar`), `bin/export_calendar.sh` | **KEEP** | Still useful for external calendar consumers |
| `src/get_weather.py` | Weather API integration | Unknown | Docs reference only | **KEEP** | Low risk; useful for coaching decisions |
| `src/workout_scheduler.py` | Constraint rescheduling logic | **YES** | `src/garmin_sync.py` | **REFACTOR** | Rescheduling now done at plan level; this module's role reduced |
| `src/gemini_client.py` | Google Gemini API client | **YES** | `src/discord_bot.py`, `src/morning_report.py` | **KEEP** | AI fallback strategy is active |
| `src/ai_providers/` | AI backend abstraction layer (6 files) | Unknown | No direct imports found from CLI/skills | **REVIEW** | `coach_service/` uses it but `coach_service/` itself is orphaned |
| `src/coach_service/` | Service layer (4 files) | **NO** | No imports found anywhere in CLI/skills/brain | **DELETE** | Zero callers; orphaned sub-package; predates CLI architecture |
| `src/daily_workout_formatter.py` | Format today's workout | Unknown | `bin/daily_workouts.sh` | **DELETE or ARCHIVE** | `bin/daily_workouts.sh` is also candidate for deletion; covered by `coach brief` |
| `src/ai_validation.py` | Validate AI responses against health data | Unknown | `bin/validate_ai_report.sh` | **KEEP** | Defensive quality gate; wire to CI |
| `src/supplemental_workout_generator.py` | Generate strength/mobility workouts | **NO** | Commented out in `bin/sync_garmin_data.sh` | **ARCHIVE** | Feature explicitly disabled; retains value if re-enabled |
| `src/streprogen_program_generator.py` | Generate Streprogen strength programs | Unknown | `src/supplemental_workout_generator.py` (disabled) | **ARCHIVE** | Streprogen feature disabled; keep for future |
| `src/streprogen_completion_tracker.py` | Track strength program progress | Unknown | `src/supplemental_workout_generator.py` (disabled) | **ARCHIVE** | Disabled feature |
| `src/ai_strength_generator.py` | LLM-powered strength program generation | Unknown | `src/supplemental_workout_generator.py` (disabled path) | **ARCHIVE** | Disabled feature |
| `src/planned_workout_manager.py` | SQLite planned workout queries (pre-Memory OS) | Unknown | `src/planned_workout_cli.py`, `src/extract_baseline_plan.py` | **DELETE** | Predates Memory OS; replaced by `memory/db.py` + `skills/plans.py` |
| `src/planned_workout_cli.py` | CLI for planned workouts (pre-Memory OS) | Unknown | `bin/planned_workouts.sh` only | **DELETE** | Orphaned; `bin/planned_workouts.sh` is also candidate for deletion |
| `src/extract_baseline_plan.py` | Plan extraction utility | Unknown | `src/planned_workout_manager.py` only | **DELETE** | Depends on `planned_workout_manager`; both are pre-Memory OS |
| `src/morning_report.py` | AI morning report | **YES** | `src/discord_bot.py` subprocess | **KEEP (migrate to CLI later)** | Active but not routed through `cli/coach.py`; Phase 12 target |
| `src/cleanup_generated_workouts.py` | Housekeeping for generated_workouts.json | Unknown | Manual only | **ARCHIVE** | Low value; generated_workouts.json management is now via sacred path |
| `src/deduplicate_workouts.py` | Dedup scheduled_workouts in cache | **YES** | `bin/sync_garmin_data.sh` | **KEEP** | Still called by sync pipeline; consider absorbing into garmin_sync.py |
| `src/discord_bot_streaming.py` | Streaming variant of bot | **NO** | Zero imports found anywhere | **DELETE** | No callers; orphaned; streaming now in `src/discord_bot.py` directly |
| `src/environmental_adjustments.py` | Weather/humidity pacing adjustments | Unknown | No imports found | **REVIEW** | No callers found; may be used by agents at prompt level |
| `src/test_streprogen.py` | Test utility for streprogen API | Unknown | Not in tests/ dir; no imports | **DELETE** | Stale test file in wrong location; streprogen feature disabled |

### 2c. Brain / Memory / Skills / Hooks / Agent

| Path | Purpose | Still Used? | Who Calls It | Recommended Action | Rationale |
|---|---|---|---|---|---|
| `brain/planner.py` | LLM-powered planner | **YES** | `cli/coach.py cmd_plan()` | **KEEP** | Core planning logic; well-structured |
| `brain/schemas.py` | Pydantic models for plan decisions | **YES** | `brain/planner.py` | **KEEP** | Canonical schema |
| `brain/stride_rules.py` | Workout rule engine | **YES** | `brain/planner.py` | **KEEP** | Safety guardrails |
| `memory/db.py` | SQLite schema + queries | **YES** | All components | **KEEP** | Authoritative storage layer |
| `memory/retrieval.py` | Context packet builder | **YES** | `cli/coach.py cmd_plan()` | **KEEP** | Context assembly for LLM |
| `memory/vault.py` | Markdown vault interface | **YES** | `hooks/`, `brain/planner.py` | **KEEP** | Vault integration |
| `skills/garmin_sync.py` | Wrapper: runs smart_sync.sh + SQLite event | **YES** | `cli/coach.py cmd_sync()` | **KEEP** | Correct thin wrapper |
| `skills/plans.py` | Plan retrieval + metadata | **YES** | `cli/coach.py` brief/schedule | **KEEP** | Clean abstraction |
| `skills/publish_to_garmin.py` | Sacred publish path | **YES** | `cli/coach.py cmd_export_garmin()` | **KEEP** (sacred) | Never bypass |
| `skills/internal_plan_to_scheduled_workouts.py` | Render plan_days → Garmin format | **YES** | `skills/publish_to_garmin.py` | **KEEP** | Part of sacred path |
| `hooks/on_sync.py` | Post-sync hook | **YES** | `agent/runner.py` | **KEEP** | Agent-triggered hook |
| `hooks/on_readiness_change.py` | Readiness change hook | **YES** | `agent/runner.py` | **KEEP** | Recovery-aware auto-adjustment |
| `hooks/on_daily_rollover.py` | 4am daily hook | **YES** | `agent/runner.py` | **KEEP** | Daily rollover logic |
| `hooks/on_constraints_change.py` | Constraint change hook | Unknown | `agent/runner.py` (presumably) | **REVIEW** | Verify it's wired in runner.py |
| `agent/runner.py` | Heartbeat runner (15-min loop) | **YES** | systemd `running-coach-agent` | **KEEP** | Background automation core |
| `agent/lock.py` | SQLite-based distributed lock | **YES** | `agent/runner.py`, `cli/coach.py agent` | **KEEP** | Concurrency safety |

### 2d. Tests

| Path | Purpose | Still Used? | Status | Recommended Action |
|---|---|---|---|---|
| `tests/test_garmin_sync.py` | Unit tests for `src/garmin_sync.py` | **YES** | Passing (merge_data, retry_with_backoff) | **KEEP** |
| `tests/test_stride_rules.py` | Unit tests for `brain/stride_rules.py` | **YES** | Active | **KEEP** |
| `tests/test_schedule_cmd.py` | Integration tests for `coach schedule` | **YES** | Active | **KEEP** |
| `tests/test_security.py` | Security tests for `src/web/app.py` | **BROKEN** | Imports `src.web.app` which does not exist | **DELETE** |
| `tests/plan_to_parser_test.py` | Plan → parser round-trip test | Unknown | | **REVIEW** |
| `test_ai_call.py` (root) | Root-level test file | Unknown | | **MOVE or DELETE** |
| `test_location_fix.py` (root) | Root-level test file | Unknown | | **MOVE or DELETE** |
| `test_location_geocoding.py` (root) | Root-level test file | Unknown | | **MOVE or DELETE** |
| `test_session.py` (root) | Root-level test file | Unknown | | **MOVE or DELETE** |

---

## 3. Dead Code Identification

The following files are likely unused. Evidence method shown for each.

| File | Evidence of Disuse | Determination Method |
|---|---|---|
| `src/web/app.py` | **Does not exist** — `tests/test_security.py` imports it and will fail at import | `glob src/web/**` → no matches |
| `src/discord_bot_streaming.py` | Zero import references across entire codebase | `rg "discord_bot_streaming"` → 0 matches |
| `src/test_streprogen.py` | Not in `tests/`; not imported anywhere; streprogen disabled | `rg "test_streprogen"` in non-self files → 0 matches |
| `src/coach_service/` (4 files) | Not imported anywhere; predates CLI architecture | `rg "coach_service"` → 0 matches outside its own dir |
| `src/planned_workout_manager.py` | Only called by `src/planned_workout_cli.py` and `src/extract_baseline_plan.py` (both candidates for deletion) | `rg "planned_workout_manager"` → 3 files, all self-referencing |
| `src/planned_workout_cli.py` | Only called by `bin/planned_workouts.sh` (shell wrapper with no documented use) | `rg "planned_workout_cli"` → only `bin/planned_workouts.sh` |
| `src/extract_baseline_plan.py` | Only imports `planned_workout_manager` (itself dead); no imports of it found | `rg "extract_baseline_plan"` → 0 external references |
| `bin/delete_strength_mobility_next_week.py` | One-off cleanup script; strength generation disabled; imports `garmin_sync.get_garmin_client` directly | `rg "delete_strength_mobility_next_week"` → 0 callers |
| `bin/delete_strength_mobility_workouts.py` | One-off cleanup script; same pattern | `rg "delete_strength_mobility_workouts"` → 0 callers |
| `bin/fix_strength_rotation.py` | One-off fix script; streprogen disabled | `rg "fix_strength_rotation"` → 0 callers |
| `bin/remove_finalsurge_strength.py` | One-off cleanup; FinalSurge no longer authoritative | `rg "remove_finalsurge_strength"` → 0 callers |
| `examples/discord_streaming_example.py` | Example file; not imported by production code | `rg "discord_streaming_example"` → 0 callers |

---

## 4. Redundant Capability Identification

The following capabilities are now duplicated between the new SQLite-backed system and the legacy JSON/ICS flow:

| Capability | Legacy Location | New Location | Redundancy Risk |
|---|---|---|---|
| **Scheduled workout storage** | `data/health/health_data_cache.json` → `scheduled_workouts[]` (from FinalSurge ICS) | `data/coach.sqlite` → `plan_days` (from `brain/planner.py`) | HIGH — two competing sources of "what to do today"; FinalSurge ICS is no longer authoritative |
| **Workout rescheduling (constraints)** | `src/garmin_sync.py` → `_merge_calendar_workouts()` + `apply_schedule_constraints()` | `memory/retrieval.py` context packet feeds Brain which handles constraints via planning | HIGH — constraint logic split between sync-time (legacy) and plan-time (new) |
| **Workout publication tracking** | `data/generated_workouts.json` (skip gate, pre-dates SQLite) | `data/coach.sqlite` → `events` (each publish logs an event) | MEDIUM — both exist; JSON file is the active skip gate; SQLite events are audit log |
| **Training plan storage** | `data/plans/*.md` (markdown plans) | `data/coach.sqlite` → `plans` + `plan_days` | HIGH — markdown plans are stale; SQLite is authoritative |
| **Incremental sync tracking** | `health_data_cache.json` → `last_sync_date` field | `data/coach.sqlite` → `state` table key `runner_last_context_hash` | MEDIUM — different purposes but overlapping sync-state tracking |
| **Workout deduplication** | `src/deduplicate_workouts.py` (standalone script, called in sync) | Skip gate in `data/generated_workouts.json` (checked by `skills/publish_to_garmin.py`) | LOW — different layers but both solve duplicate upload problem |
| **Morning report generation** | `src/morning_report.py` (direct subprocess from Discord bot) | Not yet migrated to `cli/coach.py` | MEDIUM — inconsistency; morning_report.py bypasses the CLI architecture |

---

## 5. Risk Flags

### 5a. Secret / Config Path Risks

| Location | Risk | Severity |
|---|---|---|
| `src/garmin_sync.py:227–237` | Reads plaintext password from `config/.garmin_config.json` if env vars not set | HIGH — plaintext credentials in config file; `.gitignore` should cover it but verify |
| `config/discord_bot.env` | Discord bot token stored in tracked config dir | HIGH — not gitignored; verified: `config/discord_bot.env` is in the repo (check `.gitignore`) |
| `bin/delete_all_workouts.py` | No confirmation prompt; can wipe all Garmin workouts silently | HIGH — catastrophic if run accidentally; no guards |
| `bin/delete_strength_mobility_next_week.py` | Imports `garmin_sync.get_garmin_client` directly (bypasses skills layer) | MEDIUM — hardcodes auth path; also reads `GARMIN_EMAIL`/`GARMIN_PASSWORD` from env |
| `smart_sync.sh:1` | Termux shebang (`#!/data/data/com.termux/files/usr/bin/bash`) | LOW — runs fine with `bash bin/smart_sync.sh`; breaks if executed directly on Linux |

### 5b. Token / Memory Bloat Risks

| Location | Risk | Severity |
|---|---|---|
| `src/garmin_sync.py` main loop | Fetches 15+ data types per sync (activities, sleep, HRV, VO2, weight, RHR, stress, SpO2, body battery, race predictions, lactate threshold, training status, scheduled workouts, gear stats, daily steps, progress summary) | MEDIUM — slow; fetches more than agents actually need |
| `memory/retrieval.py build_context_packet()` | Loads full `health_data_cache.json` into context | HIGH — entire health cache (can be MB) loaded for every LLM call; only tail of recent data needed |
| `src/garmin_sync.py simplify_activity()` | Reduces per-activity tokens 1000→200, but entire activity list still loaded | MEDIUM — with 60+ days of activities, context packet can still spike |
| `src/discord_bot.py` morning report path | Calls `python3 src/morning_report.py --full-only` → spawns another Claude LLM call inside Discord bot's own LLM context | HIGH — nested LLM invocations; double token cost |

---

## 6. Garmin Sync Refactor Plan

### 6a. Feature Ranking: What to Keep

**Must Keep:**

| Feature | Current Location | Why It Matters | Belongs In |
|---|---|---|---|
| Token-first auth (OAuth) with password fallback | `get_garmin_client()` | Required for reliable unattended sync | `skills/garmin_sync.py` or dedicated `cli/garmin_auth.py` |
| Retry with exponential backoff | `retry_with_backoff()` | Garmin API rate-limits frequently (429) | Keep in sync module |
| Sleep / HRV / body battery / training readiness ingestion | `fetch_sleep_data()`, `fetch_hrv_data()`, `fetch_body_battery()`, `fetch_training_readiness()` | Core recovery metrics for every coaching decision | SQLite `metrics` table (one row per day) |
| Activity fetch with split-level detail | `fetch_activities()`, `_fetch_activity_splits()` | Coaches need HR, pace, interval splits for adaptation | SQLite `activities` table |
| Incremental sync (last_sync_date tracking) | Cache `last_sync_date` field | Avoids re-fetching 60 days of data every run | SQLite `state` table key |
| Atomic cache write (temp file + rename) | `_write_atomic()` | Prevents corrupt cache on crash/interrupt | Keep; apply to SQLite writes too |
| Data simplification for token savings | `simplify_activity()` | Reduces 1000→200 tokens per activity | Keep + extend to other data types |

**Nice to Keep:**

| Feature | Why | Belongs In |
|---|---|---|
| VO2 max / race predictions / lactate threshold | Useful for VDOT calibration and goal-setting | SQLite `metrics` table (weekly rollup) |
| Gear stats | Shoe mileage tracking for injury prevention | SQLite `gear` table (optional) |
| Daily steps | Useful for activity level context | SQLite `metrics` table |
| Body weight readings | Useful for energy availability context | SQLite `metrics` table |
| Resting HR (separate from sleep) | Backup recovery metric if HRV unavailable | SQLite `metrics` table |
| FinalSurge ICS import (as optional input) | Enables running coach's schedule to inform Brain | Stay in `src/garmin_sync.py`; flag output as `source=ics_optional` |
| ICS calendar export | Useful for external calendar consumers | Separate module `src/ics_exporter.py` (already exists) |

**Drop:**

| Feature | Why to Drop |
|---|---|
| Constraint-based rescheduling at sync time (`apply_schedule_constraints()`, `workout_scheduler.py`) | Rescheduling now happens at plan-generation time (Brain uses constraint context). Doing it at sync time creates conflicting schedule versions. |
| Auto-generation of supplemental workouts at sync time | Explicitly disabled; Brain + `coach plan --week` now owns this |
| Garmin workout template scheduling (fetching template workouts from Garmin, `fetch_scheduled_workouts()`) | SQLite `plan_days` is the authority; Garmin templates are noise |
| Direct write to `data/generated_workouts.json` in sync | Skip gate belongs exclusively to `skills/publish_to_garmin.py` |
| Progress summary fetch (`fetch_progress_summary()`) | Rarely used; noisy; saves one API call |
| SpO2 fetch (`fetch_spo2_data()`) | Low coaching relevance; rarely populated |
| Stress readings (`fetch_stress_data()`) | Low signal-to-noise; coaching agents don't act on it |

---

### 6b. SQLite vs JSON Cache — Decision Memo

#### What Belongs in SQLite

SQLite is the right home for anything that needs to be:
- Queried by date range
- Cross-referenced with plan_days
- Deduped idempotently
- Available without loading multi-MB JSON files

**Proposed tables:**

```sql
-- One row per day, covers all recovery metrics
CREATE TABLE IF NOT EXISTS daily_metrics (
    day             DATE PRIMARY KEY,
    sleep_total_min INTEGER,
    sleep_score     INTEGER,
    sleep_deep_pct  REAL,
    hrv_weekly_avg  REAL,
    hrv_last_night  REAL,
    body_battery_am INTEGER,
    body_battery_pm INTEGER,
    training_readiness_score  INTEGER,
    training_readiness_level  TEXT,   -- 'POOR'/'FAIR'/'GOOD'/'EXCELLENT'
    rhr_bpm         INTEGER,
    steps           INTEGER,
    stress_avg      INTEGER,          -- nullable
    weight_lbs      REAL,             -- nullable
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- One row per activity (run, strength, cross-train, etc.)
CREATE TABLE IF NOT EXISTS activities (
    activity_id     TEXT PRIMARY KEY,
    start_time      DATETIME NOT NULL,
    activity_type   TEXT NOT NULL,
    name            TEXT,
    duration_s      INTEGER,
    distance_mi     REAL,
    avg_hr          INTEGER,
    max_hr          INTEGER,
    avg_pace_min_mi REAL,
    calories        INTEGER,
    splits_json     TEXT,             -- JSON array of INTERVAL_* splits (nullable)
    hr_zones_json   TEXT,             -- JSON summary (nullable)
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Weekly performance snapshots (VO2 max, lactate, etc.)
CREATE TABLE IF NOT EXISTS performance_snapshots (
    snapshot_id     TEXT PRIMARY KEY,
    snapped_at      DATE NOT NULL,
    vo2_max         REAL,
    lactate_threshold_hr     INTEGER,
    lactate_threshold_pace   REAL,
    training_load_atl        REAL,
    training_load_ctl        REAL,
    training_load_tsb        REAL,
    race_pred_5k_sec         INTEGER,
    race_pred_half_sec       INTEGER,
    race_pred_marathon_sec   INTEGER,
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Gear mileage tracking
CREATE TABLE IF NOT EXISTS gear (
    gear_uuid       TEXT PRIMARY KEY,
    name            TEXT,
    distance_mi     REAL,
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Garmin sync run log (already partially in task_runs; extend or create separate)
CREATE TABLE IF NOT EXISTS sync_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    range_start     DATE,
    range_end       DATE,
    returncode      INTEGER NOT NULL,
    activities_new  INTEGER DEFAULT 0,
    days_synced     INTEGER DEFAULT 0,
    notes           TEXT
);
```

> **Note:** `daily_metrics` + `activities` + `performance_snapshots` are new; `sync_runs` extends the existing `task_runs` pattern. All existing tables (`plans`, `plan_days`, `events`, `state`, `metrics`) remain unchanged.

#### What Can Remain as Flat JSON

| File | Justification |
|---|---|
| `data/generated_workouts.json` | Skip gate; read/written by `skills/publish_to_garmin.py`; simple keyed dict; SQLite overkill unless collision rate rises |
| `data/health/health_data_cache.json` | **Transitional only** — keep during Stage 1; deprecate in Stage 2 after `daily_metrics`/`activities` tables are populated; remove in Stage 3 |
| `data/calendar/finalsurge.ics` | Input artifact; no need to parse into SQLite (already merged into `scheduled_workouts` in cache) |
| `data/calendar/running_coach_export.ics` | Output artifact; generated on demand |

#### What Should Be Derived on Demand

| Currently Stored | Derive From | Reason |
|---|---|---|
| Percentile rankings (implied by morning_report.py) | Query `daily_metrics` for last 30 rows | No need to store; simple SQL |
| `last_updated` timestamp in cache JSON | `sync_runs` table MAX(ran_at) | More reliable; survives cache reset |
| FinalSurge `scheduled_workouts` (from ICS) | Re-parse ICS on sync | Input-only; should not persist as plan authority |

#### Migration Approach

**Stage 1 — Write-Through (implement in Phase 12)**
- After each `src/garmin_sync.py` run, `skills/garmin_sync.py` post-processes the JSON and inserts rows into `daily_metrics`, `activities`, `performance_snapshots`.
- `memory/retrieval.py` reads from SQLite tables preferentially; falls back to JSON if table empty.
- Both sources exist in parallel; no behavioral change.

**Stage 2 — Read from SQLite, deprecate JSON (Phase 13)**
- `memory/retrieval.py` reads exclusively from SQLite tables.
- `health_data_cache.json` still updated by `src/garmin_sync.py` (skip gate for backward compat).
- Bot's `morning_report.py` also reads from SQLite.
- Mark `health_data_cache.json` as deprecated in `.gitignore` comments.

**Stage 3 — Remove JSON (Phase 14)**
- Remove `health_data_cache.json` reads from all code.
- `src/garmin_sync.py` writes directly to SQLite (or via a new `src/garmin_ingest.py`).
- Archive `health_data_cache.json.bak`.

---

### 6c. Where Garmin Sync Should Live

**Recommendation: Hybrid — keep sacred sync in `src/garmin_sync.py`, expose via `skills/garmin_sync.py`, add a native Python ingest layer.**

**Rationale:**

| Concern | Current | Recommended |
|---|---|---|
| **Token discipline** | `smart_sync.sh` → `sync_garmin_data.sh` → `garmin_sync.py`; shell script adds latency overhead | Move cache-age check from bash to `skills/garmin_sync.py` Python (simpler, faster, testable) |
| **Failure handling** | Shell exit codes propagated imperfectly through skill wrapper | Python exceptions propagate cleanly; `skills/garmin_sync.py` already catches `TimeoutExpired` |
| **Latency** | Cold start: ~3s shell fork overhead per sync; hot path (cache fresh): ~300ms | Native Python check eliminates fork overhead for cache-hit path |
| **Testability** | `bin/smart_sync.sh` is not testable with pytest | Python skill wrapper is unit-testable |
| **Background job** | `agent/runner.py` calls `skills/garmin_sync.run()` correctly | Keep `agent/runner.py` as the heartbeat trigger; no change needed |

**Concrete recommendation:**

1. **Keep `src/garmin_sync.py`** as the sacred data fetcher. It is the only module that writes `health_data_cache.json`. Do not break this invariant.
2. **Evolve `skills/garmin_sync.py`** to:
   - Accept `force: bool` (existing) + `max_age_minutes: int = 30` (new)
   - Implement cache-age check natively in Python (currently in `bin/smart_sync.sh`)
   - After successful sync, insert rows into `daily_metrics`/`activities` SQLite tables (Stage 1 of migration)
   - Remove dependency on `bin/smart_sync.sh` shell script (make it optional/deprecated)
3. **Add `cli/coach.py sync` options**: `--days N`, `--check-only` (currently only available via direct `src/garmin_sync.py` invocation)
4. **Keep `bin/smart_sync.sh`** for backward compatibility with any external scripts, but internally route through `skills/garmin_sync.py`.

**Do NOT** move sync to a standalone background "agent/heartbeat" job — `agent/runner.py` already serves this role and calls `skills/garmin_sync.run()`. Adding a separate heartbeat for sync creates competing timers.

---

## 7. Phase 11 Summary

### What Changed in This Phase

| Item | Status |
|---|---|
| `docs/PHASE_11_AUDIT.md` | Created (this file) |
| `docs/BACKLOG.md` | Created |
| `docs/BACKLOG_RUNNER_PROMPT.md` | Created |

No code was modified. This is an audit + planning phase only.

### What I Recommend Next (Phase 12 Headline Plan)

**Priority 1 — Safety (no behavior change, immediate risk reduction):**
1. Fix or delete `tests/test_security.py` (imports non-existent `src.web.app`)
2. Delete one-off bin/ cleanup scripts (delete_strength_mobility_*.py, fix_strength_rotation.py, remove_finalsurge_strength.py)
3. Archive `src/discord_bot_streaming.py`, `src/test_streprogen.py`, `src/planned_workout_manager.py`, `src/planned_workout_cli.py`, `src/extract_baseline_plan.py`
4. Delete `src/coach_service/` (zero callers)

**Priority 2 — Architecture cleanup:**
5. Move cache-age check from `bin/smart_sync.sh` into `skills/garmin_sync.py` (Python, testable)
6. Add `cli/coach.py sync --days N --check-only` args
7. Wire `memory/retrieval.py` to load only tail (last 14 days) of activities instead of entire cache
8. Migrate `morning_report.py` to be callable as `coach morning-report` via CLI (aligns with CLI-first design)

**Priority 3 — SQLite migration (Stage 1):**
9. Add `daily_metrics` + `activities` tables to `memory/db.py` schema
10. Wire `skills/garmin_sync.py` to populate SQLite tables after each successful sync
11. Update `memory/retrieval.py` to prefer SQLite tables over JSON for health metrics

**Phase 13+ (deferred):**
- Stage 2/3 of SQLite migration (deprecate then remove JSON cache)
- Remove ICS constraint logic from `src/garmin_sync.py` (move to Brain context)
- Deprecate `bin/sync_garmin_data.sh` in favor of native Python skill
