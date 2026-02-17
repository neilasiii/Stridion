# Running Coach System — User Guide

**Audience:** Neil (daily use) + ops/debug reference.
**Last updated:** 2026-02-17 (Phase 6 deploy)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start (5 minutes)](#2-quick-start-5-minutes)
3. [Daily Workflow](#3-daily-workflow)
4. [Discord Slash Command Reference](#4-discord-slash-command-reference)
5. [#coach Keyword Router Reference](#5-coach-keyword-router-reference)
6. [CLI Reference (Ops / Headless)](#6-cli-reference-ops--headless)
7. [Testing Checklist (End-to-End)](#7-testing-checklist-end-to-end)
8. [Debugging Playbook](#8-debugging-playbook)
9. [Token / Cost Discipline](#9-token--cost-discipline)
10. [Appendix — Key Files & Services](#10-appendix--key-files--services)

---

## 1. Overview

### What the system is now

The running coach is a **Brain + Body** system:

- **Brain** — a Claude-backed LLM planner (`brain/planner.py`) that generates weekly training plans and adjusts today's workout when readiness changes significantly.
- **Memory OS** — a SQLite database (`data/coach.sqlite`) + markdown vault (`vault/`) that stores plans, daily notes, athlete events, and constraint inputs.
- **Skills** — thin Python wrappers that translate internal plan data into Garmin-uploadable workouts.
- **Agent** — a background heartbeat process (15-minute loop, 4am daily deep run) that syncs Garmin data, detects health changes, and triggers the Brain only when warranted.
- **Discord bot** — a thin router that translates slash commands and channel keywords into CLI calls (`python3 cli/coach.py ...`). It contains no coaching logic itself.

### What is authoritative

**The internal SQLite plan is the single source of truth.**
`data/coach.sqlite` → `plans` + `plan_days` tables hold the active weekly plan.
FinalSurge and ICS calendars are **optional inputs only** — they can inform the Brain but cannot override it.

### What remains sacred (do not modify)

| Component | Why |
|---|---|
| `src/auto_workout_generator.py` | Garmin workout builder — converts descriptions to structured steps |
| `src/workout_uploader.py` | Garmin API upload path |
| `src/garmin_sync.py` | Garmin data fetch + health cache writer |
| `data/generated_workouts.json` | **Sole skip gate** for Garmin publish — if a date+workout is in this file, it will not be re-uploaded |

Never write to `data/generated_workouts.json` directly. Never modify the sacred `src/` files above.

---

## 2. Quick Start (5 minutes)

If you only do three things, do these:

**1. Check today's plan**
```
/coach_today
```
Shows today's workout from the internal plan: type, duration, intent, steps.

**2. Sync latest Garmin data**
```
/coach_sync
```
Pulls fresh health data (sleep, HRV, body battery, activities) and updates the cache. The agent does this automatically every 15 minutes, but run this if you just completed a workout.

**3. Check the agent is healthy**
```
/coach_status
```
Shows the SQLite lock state and the last few task runs. If you see `success` entries, everything is running fine.

---

## 3. Daily Workflow

### Morning — check in

1. **Sync** (if not auto-synced): `/coach_sync`
2. **See today's workout**: `/coach_today`
3. **Full morning report** (AI-generated): `/report` — this calls `src/morning_report.py` and includes recovery metrics + workout recommendation. The bot also sends this automatically at 5:30 AM EST to `#morning-report` once sleep data is detected.

### Making changes — notes and constraints

If something affects your schedule (travel, childcare, injury), save a note:

```
/coach_note "No run Thursday — travel to conference"
```

This writes a markdown file to `vault/inbox/` and immediately attempts ingestion. The agent will ingest it on its next heartbeat if that fails. Near-term constraints (within 7 days) set a `needs_replan` flag that the agent checks.

You can also type in `#coach`:
```
note: No run Thursday — travel
constraint: Unavailable Friday morning
```

### Planning — when to run it

**Weekly** (Monday or Sunday evening): send `plan` in `#coach` or use `/coach_plan`.

The Brain reads your full context (health data, recent activities, athlete profile, phase) and generates a 7-day plan. It writes to SQLite and activates it immediately.

**Do not run planning speculatively.** It calls Claude and consumes tokens. The agent runs it automatically at 4am if the plan is stale (end date < today + 2 days).

### Exporting to Garmin

After a new plan is generated, preview what would upload:
```
/coach_export
```

This is always a dry run. To actually push to Garmin, use the CLI:
```bash
python3 cli/coach.py export-garmin --live
```

---

## 4. Discord Slash Command Reference

All `coach_*` commands route to `python3 cli/coach.py` via the bot. No session state is maintained between calls.

| Command | What it does | LLM? | Channel |
|---|---|---|---|
| `/coach_today` | `coach brief --today` — shows today's plan from SQLite | No | Any |
| `/coach_sync` | `coach sync` — runs Garmin sync via smart_sync.sh | No | Any |
| `/coach_plan` | `coach plan --week` — calls Brain to generate new week | **Yes** | Any |
| `/coach_export` | `coach export-garmin` (dry run) — previews Garmin upload | No | Any |
| `/coach_status` | `coach agent status` — lock state + recent task_runs | No | Any |
| `/coach_memory` | `coach memory search <query>` — searches plan days + events | No | Any |
| `/coach_note` | Writes note to `vault/inbox/`, attempts immediate ingest | No | Any |

**Legacy commands (still registered, redirect only):**

| Command | Behaviour |
|---|---|
| `/sync` | Full Garmin sync with before/after diff embed (legacy rich version) |
| `/report` | Generates morning report via `src/morning_report.py` |
| `/workout` | Shows today's workouts from health cache (FinalSurge source) |
| `/status` | Recovery metrics from health cache |
| `/ask` | Direct Claude/Gemini question (no coaching context) |
| `/location` | Set weather location |
| `/running` | Stub — "running-only mode" message |
| `/strength`, `/mobility`, `/nutrition` | Stubs — redirected to agent system |

**Timeout defaults:** All `coach_*` commands time out at 180s except `/coach_sync` (300s) and `/coach_plan` (300s).

---

## 5. #coach Keyword Router Reference

Messages in `#coach` are routed deterministically — no LLM is called unless you opt in.

| Message | Routes to | LLM? |
|---|---|---|
| `today` / `brief` / `workout` | `coach brief --today` | No |
| `sync` | `coach sync` | No |
| `plan` *(exact)* or `plan <anything>` | `coach plan --week` | **Yes** |
| `status` / `agent` | `coach agent status` | No |
| `ai: <your question>` | Claude (Gemini fallback) with your text | **Yes** |
| Anything else | Help message listing slash commands | No |

**Critical guardrail:** The word "plan" in a sentence does NOT trigger planning.
`"what's the plan for dinner?"` → shows help (not a plan call).
`"plan"` → triggers `coach plan --week`.
`"plan force"` → also triggers (starts with `"plan "`).

---

## 6. CLI Reference (Ops / Headless)

Use these when Discord is down, for scripting, or when you need full output.

```bash
# Sync Garmin health data
python3 cli/coach.py sync

# Generate this week's plan (calls Brain LLM)
python3 cli/coach.py plan --week

# Force re-plan even if cache is fresh
python3 cli/coach.py plan --week --force

# Preview Garmin upload — ALWAYS start here
python3 cli/coach.py export-garmin

# Preview N days ahead
python3 cli/coach.py export-garmin --days 14

# Actually upload to Garmin (irreversible for that session)
python3 cli/coach.py export-garmin --live

# Show today's planned workout
python3 cli/coach.py brief --today

# Show agent lock state + recent task runs
python3 cli/coach.py agent status

# Run one heartbeat cycle manually (sync → hash check → hooks)
python3 cli/coach.py agent run-once

# Search plan days and events
python3 cli/coach.py memory search "tempo"
python3 cli/coach.py memory search "2026-02-17"
```

### Safe testing order

1. `python3 cli/coach.py agent status` — baseline, no side effects
2. `python3 cli/coach.py brief --today` — read-only
3. `python3 cli/coach.py sync` — writes health cache, safe
4. `python3 cli/coach.py export-garmin` — dry run, no Garmin API
5. `python3 cli/coach.py plan --week` — LLM call, writes SQLite
6. `python3 cli/coach.py export-garmin --live` — real Garmin upload

---

## 7. Testing Checklist (End-to-End)

Work through this in order. Each step confirms the one before it.

### T1 — Garmin sync works
```bash
python3 cli/coach.py sync
```
✓ Expect: `✓ Garmin sync complete (event_id=…)` with a summary line.
✗ Fail: `returncode=1` or `garminconnect` auth error → check tokens in `~/.garminconnect`.

### T2 — Agent status clean
```bash
python3 cli/coach.py agent status
```
✓ Expect: `Lock: FREE`, recent `garmin_sync` rows showing `success`.
✗ Fail: `Lock: HELD` (more than 20 min old) → lock is stale, see §8.

### T3 — Today's brief works
```bash
python3 cli/coach.py brief --today
```
✓ Expect: Plan ID, week range, today's workout type + steps.
✗ Fail: `No active plan` → run T5 first.

### T4 — Plan generation (high data quality)
```bash
python3 cli/coach.py sync  # ensure fresh data first
python3 cli/coach.py plan --week
```
✓ Expect: Phase, volume, 7 day breakdown, no `low_readiness_confidence` safety flag.
✗ Fail: Brain returns invalid JSON → see §8.

### T5 — Plan generation (low data quality)
Disconnect Garmin sync or use stale cache, then run:
```bash
python3 cli/coach.py plan --week --force
```
✓ Expect: Plan generates **and** includes `low_readiness_confidence` in safety_flags.
This flag confirms the deterministic guard is working.

### T6 — Notes ingestion
```bash
echo "# Test Note\n\nNo run Saturday — travel" > vault/inbox/test_note.md
python3 -c "
import sys; sys.path.insert(0, '.')
from memory import ingest_inbox_notes
r = ingest_inbox_notes()
print(len(r), 'event(s) ingested')
"
ls vault/inbox/processed/
```
✓ Expect: `1 event(s) ingested`, file moved to `vault/inbox/processed/`.

### T7 — Dry-run export
```bash
python3 cli/coach.py export-garmin
```
✓ Expect: `[DRY RUN]` header, list of workouts that would upload vs skip (with reasons).
No Garmin API is called. Safe to run repeatedly.

### T8 — Live export (carefully)
Only run after T7 confirms the plan looks correct:
```bash
python3 cli/coach.py export-garmin --live
```
✓ Expect: `✓ Published N workout(s)` list.
✗ Unexpected: "skipped — date in generated_workouts.json" for a workout you expected to upload → it was already uploaded. Check `data/generated_workouts.json`.

### T9 — Agent heartbeat (one cycle)
```bash
python3 cli/coach.py agent run-once
```
✓ Expect: `lock_acquired: True`, `sync_success: True`, `hooks_run` list (may be empty if hash unchanged).
✗ Fail: `lock_acquired: False` → another process holds the lock.

### T10 — Discord routing
In `#coach` channel:
- Send `today` → should reply with today's brief (no LLM).
- Send `what's the plan for dinner?` → should reply with help message (not a plan call).
- Send `plan` → should call `coach plan --week` and reply with result.
- Use `/coach_status` → should show agent status embed.
- Use `/coach_note "Test note"` → should confirm file written + ingested.

---

## 8. Debugging Playbook

### Discord bot not responding

```bash
sudo systemctl status running-coach-bot --no-pager
sudo journalctl -u running-coach-bot -n 50 --no-pager
```
If `inactive (dead)`: `sudo systemctl restart running-coach-bot`
If looping restarts: check `discord_bot.log` for the traceback.

Check on_ready completed:
```bash
sudo journalctl -u running-coach-bot --since "5 min ago" | grep "Slash commands\|Logged in"
```

### LLM failure / Claude CLI missing

The bot falls back to Gemini automatically. If both fail:
- `/coach_plan` will show an error embed.
- In `#coach`, `plan` will return `Plan generation failed (rc=1)`.

Check Claude binary: `ls ~/.local/bin/claude`
Check Gemini config: `cat config/gemini_api.env`
Manual test: `~/.local/bin/claude -p "hello" --output-format text`

### Plan generation returns invalid JSON

The Brain has a retry loop and `_brace_search_last` fallback. If it still fails:
```bash
python3 cli/coach.py plan --week --force 2>&1 | tail -20
```
The planner logs the raw LLM output before raising. Check for:
- Truncated response (timeout) — context packet too large.
- Model refusal — check prompt logs in `data/coach.sqlite` events table.

### No active plan

```bash
python3 cli/coach.py brief --today
# → "No active plan. Run 'coach plan --week' first."
```
Fix: `python3 cli/coach.py plan --week`

### export-garmin says "skipped" for everything

```bash
python3 cli/coach.py export-garmin  # check reasons
```
If reason is `date in generated_workouts.json`: the workout was already uploaded in a previous session. This is correct behaviour — the file is the dedupe gate.
If you need to re-upload: manually remove the entry from `data/generated_workouts.json` (edit the JSON array to remove that date's entry), then re-run `--live`.

If reason is `date in past`: the plan day is before today. Generate a fresh plan.

### Lock stuck

```bash
python3 cli/coach.py agent status
# → Lock: HELD by runner:12345 expires 2026-02-17T13:45:00
```
The lock has a 20-minute TTL and auto-expires. Wait, or:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from agent.lock import release_lock
release_lock('manual-override')
print('Lock released')
"
```

### Notes not ingested

Check the inbox:
```bash
ls vault/inbox/
ls vault/inbox/processed/
```
If the file is in `inbox/` but not `processed/`: ingest manually:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from memory import ingest_inbox_notes
print(ingest_inbox_notes())
"
```
If it's in `processed/`: it was ingested. Check SQLite for the event:
```bash
python3 cli/coach.py memory search "constraint"
```

---

## 9. Token / Cost Discipline

### Actions that call the Brain (LLM)

| Trigger | Command / event | Frequency |
|---|---|---|
| Weekly planning | `plan --week` / `/coach_plan` / `plan` in #coach | Once/week |
| Readiness drop | Auto via agent: readiness < 45 OR drops ≥ 15 pts | 0–1×/day |
| Stale plan at 4am | Agent daily deep run (if plan end < today + 2 days) | Rare |
| Forced re-plan | `plan --week --force` | On demand |

### Actions that do NOT call the Brain

Everything else: sync, brief, export-garmin, agent status, memory search, coach_note, all keyword routes except `plan`, all `coach_*` slash commands except `/coach_plan`.

### How to avoid accidental calls

- **Do not** send the word `plan` in a sentence in `#coach` — but the guardrail now requires exact match (`plan` alone or `plan <something>`), so normal conversation is safe.
- **Do not** call `plan --week` as a health check. Use `agent status` or `brief --today` instead.
- **Do not** run `plan --week --force` repeatedly — `--force` bypasses the LLM cache and always calls the API.

### Recommended cadence

- **Daily**: sync (automated) + brief (on demand or morning report).
- **Weekly**: one `plan --week` call on Sunday evening or Monday morning.
- **As needed**: `adjust_today` fires automatically via the agent when readiness drops — you do not need to trigger this manually.

---

## 10. Appendix — Key Files & Services

### Key files

| File / Directory | What it contains |
|---|---|
| `data/coach.sqlite` | All persistent state: plans, plan_days, events, metrics, task_runs, state KV store |
| `data/health/health_data_cache.json` | Latest Garmin data: activities, sleep, HRV, body battery, VO2, RHR, scheduled workouts |
| `data/generated_workouts.json` | Log of every workout uploaded to Garmin — the sole skip gate for re-upload prevention |
| `vault/daily/YYYY-MM-DD.md` | Daily vault notes written by the agent at rollover (4am) |
| `vault/coach/DECISIONS.md` | Persistent coaching decisions that inform future plans |
| `vault/coach/PLANS.md` | Summary of recent plans |
| `vault/inbox/` | Drop zone for constraint notes — processed on next heartbeat |
| `vault/inbox/processed/` | Ingested notes (moved here after SQLite write) |
| `discord_bot.log` | Bot application logs (logger output only — `print()` goes to journald) |
| `config/discord_bot.env` | Bot token + channel IDs (gitignored) |
| `config/gemini_api.env` | Gemini fallback API key (gitignored) |

### systemd services

| Service | What it does | Status |
|---|---|---|
| `running-coach-bot` | Discord bot — thin CLI router | Running (enabled) |
| `running-coach-agent` | Heartbeat agent — 15-min loop, 4am deep run | Deploy from `deploy/running-coach-agent.service` |

**Install the agent service (if not yet running):**
```bash
sudo cp deploy/running-coach-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable running-coach-agent
sudo systemctl start running-coach-agent
```

### Useful journalctl commands

```bash
# Bot live logs
sudo journalctl -u running-coach-bot -f

# Bot last 100 lines
sudo journalctl -u running-coach-bot -n 100 --no-pager

# Agent live logs (once installed)
sudo journalctl -u running-coach-agent -f

# Both services together
sudo journalctl -u running-coach-bot -u running-coach-agent -f

# Errors only since yesterday
sudo journalctl -u running-coach-bot --since yesterday -p err --no-pager

# Check for tracebacks in last hour
sudo journalctl -u running-coach-bot --since "1 hour ago" --no-pager | grep -i traceback
```

### Restart commands

```bash
# Restart bot (safe — agent continues running independently)
sudo systemctl restart running-coach-bot

# Check bot status
sudo systemctl status running-coach-bot --no-pager

# Reload systemd after service file changes
sudo systemctl daemon-reload
```
