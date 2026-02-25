# Running Coach (VDOT + Garmin)

A personal AI-powered running coach that generates structured weekly training plans, publishes structured workouts to Garmin Connect, and monitors daily readiness — all driven by a persistent Memory OS and a Brain LLM planner.

- VDOT-based running plans (Jack Daniels methodology) — VDOT derived from actual race performance, not Garmin VO2max
- Syncs health data directly from Garmin Connect (sleep, HRV, body battery, VO2 max, activities)
- **Macro plan layer** — LLM-generated 12–16 week periodization arc (base → quality → race-specific → taper) that rails the weekly planner
- Internal plan is authoritative — FinalSurge/ICS are optional inputs only
- Background agent runs every 15 minutes; re-plans at 4am if plan is stale
- Discord bot provides the primary day-to-day interface
- CLI available for headless / ops use

> **Note:** Strength, mobility, and nutrition coaching are currently stubbed. This system runs in running-only mode.

---

## Architecture (High Level)

```
Garmin Connect API
        │
src/garmin_sync.py  ──►  data/health/health_data_cache.json
        │
skills/garmin_sync.py (wrapper)
        │
Memory OS ─────────────────────────────────────────────────
│  data/coach.sqlite      (plans, events, metrics, state)  │
│  vault/daily/           (daily markdown notes)           │
│  vault/inbox/           (drop zone for constraint notes) │
│  vault/coach/           (DECISIONS.md, PLANS.md)         │
└──────────────────────────────────────────────────────────┘
        │
Brain
│  brain/macro_plan.py  — LLM macro periodization (12–16 wk arc)
│    generate_macro_plan()   — race_targeted or base_block mode
│    validate_macro_plan()   — 9-check structural validator
│  brain/planner.py     — weekly executor; uses macro as ceiling/rail
│    plan_week()        — generates 7-day plan, writes to SQLite
│    adjust_today()     — modifies today's session on readiness drop
└──────────────────────────────────────────────────────────
        │
Memory
│  memory/retrieval.py  — context packet builder
│    _derive_vdot_from_activities()  — VDOT from race perf (90-day lookback)
│    _get_macro_guidance()           — injects macro arc into context
│  memory/db.py         — SQLite helpers (macro_plans, plans, metrics, activities)
└──────────────────────────────────────────────────────────
        │
Skills (skills/)
│  internal_plan_to_scheduled_workouts.py — renders plan days
│  publish_to_garmin.py — calls sacred upload path
└──────────────────────────────────────────────────────────
        │
CLI (cli/coach.py)       ←── Discord bot (src/discord_bot.py)
Agent (agent/runner.py)  ←── systemd: running-coach-agent
Hooks (hooks/)           ←── on_sync, on_readiness_change,
                                on_daily_rollover, on_constraints_change
```

---

## What is Authoritative

| Layer | Role |
|---|---|
| `data/coach.sqlite` | **Authoritative source for all plan data** |
| `data/health/health_data_cache.json` | Garmin truth for all health metrics |
| `data/generated_workouts.json` | **Sole skip gate** — if a date is in this file, Garmin upload is skipped (idempotency) |
| FinalSurge / ICS calendar | Optional input to the Brain; never authoritative |
| Garmin Connect calendar | Execution layer only — receives uploads, does not drive planning |

---

## VDOT Derivation

VDOT is derived from **actual race performance** (90-day lookback), not Garmin's physiological VO2max estimate. Garmin's estimate inflates fitness by ~25–35% relative to Jack Daniels VDOT, producing unrealistic training paces.

Detection logic (`memory/retrieval.py`):
- Identifies races via standard distance bands (5k / 10k / 15k / half marathon / marathon)
- Falls back to activity name keywords (`race`, `5k`, `10k`, `half`, `marathon`, etc.)
- `vdot_race_derived` exposed in context packet alongside raw `vo2_max`
- Macro planner prefers `vdot_race_derived`; falls back to 38.0 default if none found

---

## Macro Plan System

The macro plan gives the weekly planner a deterministic periodization arc. It is a **rail, not a cage** — readiness can reduce weekly volume, but the macro target is the ceiling.

**Two modes:**

| Mode | Trigger | Structure |
|---|---|---|
| `race_targeted` | Future race in `upcoming_races.md` | base → quality → race_specific → taper |
| `base_block` | No future race | base → quality (12 weeks, no taper) |

**Key behaviors:**
- Cache-first: no LLM call if an active macro plan already exists (override with `--force`)
- Validation gate: 9-check structural validator runs before plan is activated
  - Sunday alignment, phase progression, taper rules, volume ramp caps (≤15%/wk), long run sanity, etc.
- Volume ceiling: weekly planner auto-clamped to macro target (0.5 mi tolerance)
- Short-race recovery: 4-day no-quality window after races < 10 mi (5k/10k); no volume cap
- Long-race recovery: full cap + recovery weeks after half/marathon
- Current week highlighted with `→` in `coach plan --show` output

**Model:** Claude Haiku (fast structured JSON generation, ~3 min for 12-week plan, 7 min timeout)

---

## Quick Start (Local)

```bash
# 1. Sync Garmin health data
python3 cli/coach.py sync

# 2. Generate this week's plan (calls Brain LLM — one call)
python3 cli/coach.py plan --week

# 3. Preview Garmin upload (dry run — safe, no API calls)
python3 cli/coach.py export-garmin

# 4. See today's workout
python3 cli/coach.py brief --today

# 5. Upload to Garmin (only after reviewing dry run)
python3 cli/coach.py export-garmin --live

# 6. Generate / view macro periodization plan
python3 cli/coach.py plan --macro          # generate (cached; no LLM if active plan exists)
python3 cli/coach.py plan --macro --show   # print table of all weeks
python3 cli/coach.py plan --macro --force  # regenerate even if active plan exists
```

All CLI commands: `python3 cli/coach.py --help`

---

## Discord Usage (Recommended)

The Discord bot is the primary interface. All `coach_*` commands route to `cli/coach.py`.

| Command | What it does | Calls LLM? |
|---|---|---|
| `/coach_today` | Show today's plan from SQLite | No |
| `/coach_sync` | Sync Garmin data | No |
| `/coach_plan` | Generate new weekly plan, then publish updates to Garmin | **Yes** |
| `/coach_macro` | Generate / view macro periodization plan | **Yes** (first time) |
| `/coach_export` | Preview Garmin upload (dry run) | No |
| `/coach_status` | Agent lock state + recent task runs | No |
| `/coach_memory <query>` | Search plan days and events | No |
| `/coach_note <text>` | Save constraint note to vault/inbox | No |

**#coach channel keywords** (no slash needed):

| Type | Triggers |
|---|---|
| `today` / `brief` / `workout` | Shows today's plan |
| `sync` | Runs Garmin sync |
| `plan` *(exact)* or `plan <anything>` | Generates new plan (LLM) |
| `status` / `agent` | Shows agent status |
| `ai: <question>` | Direct Claude/Gemini question |

See **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** for the full command reference and `#coach` keyword routing rules.

---

## Systemd Services

### Discord Bot (running)

```bash
sudo systemctl status running-coach-bot --no-pager
sudo systemctl restart running-coach-bot
sudo journalctl -u running-coach-bot -f
```

### Heartbeat Agent (install once)

```bash
sudo cp deploy/running-coach-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable running-coach-agent
sudo systemctl start running-coach-agent
sudo journalctl -u running-coach-agent -f
```

The agent runs every 15 minutes. At 4am it performs a daily deep run: writes a vault note, checks plan staleness, and re-plans if needed. Both services share a SQLite lock so they never conflict.

---

## Docs

| Document | Contents |
|---|---|
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | Full user guide: daily workflow, all commands, end-to-end testing checklist, debugging playbook, token discipline |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Technical architecture detail |
| [docs/TRAINING_PHILOSOPHY.md](docs/TRAINING_PHILOSOPHY.md) | VDOT periodization and training principles |
| [docs/GARMIN_TOKEN_AUTH.md](docs/GARMIN_TOKEN_AUTH.md) | Token-based Garmin authentication setup |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Initial setup guide |

The **User Guide** (`docs/USER_GUIDE.md`) is the primary reference for day-to-day use. It includes:
- Complete Discord and CLI command reference
- 10-step end-to-end testing checklist
- Debugging playbook for common failures
- Token/cost discipline guide

---

## License / Disclaimer

Personal training tool — not medical advice. Training recommendations are generated by an AI model and should be used at your own discretion. Always consult a qualified coach or physician before making significant changes to your training load.
