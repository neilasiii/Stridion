# Running Coach

An AI-powered running coach that generates structured weekly training plans, publishes workouts directly to Garmin Connect, and monitors daily readiness — built on a persistent Memory OS and a Brain LLM planner.

- **VDOT-based plans** (Jack Daniels methodology) — derived from actual race performance, not Garmin's VO2max estimate
- **Garmin Connect integration** — syncs sleep, HRV, body battery, VO2 max, and activities
- **Macro plan layer** — LLM-generated 12–16 week periodization arc (base → quality → race-specific → taper) that rails the weekly planner
- **Background agent** — runs every 15 minutes; re-plans at 4am if plan is stale
- **Discord bot** — primary day-to-day interface
- **CLI** — available for headless / ops use

> **Note:** Strength, mobility, and nutrition coaching are currently stubbed. This system runs in running-only mode.

---

## Quick Start

### Prerequisites

- Python 3.10+
- A Garmin Connect account with a paired Garmin device
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (for AI coaching)
- A Discord bot token (optional — for the Discord interface)
- An Anthropic API key (for the Brain LLM planner)

### 1. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Verify:

```bash
claude --version
```

See the [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for full setup instructions and authentication.

### 2. Clone and install dependencies

```bash
git clone https://github.com/neilasiii/running-coach.git
cd running-coach
pip install -r requirements.txt
```

### 3. Set up Garmin authentication

**Option A — Token-based (recommended for servers/bots)**

Generate tokens on a machine with browser access:

```bash
python3 bin/generate_garmin_tokens.py
```

Follow the prompts, then copy `~/.garminconnect/` to your target machine.

**Option B — Password auth (simple)**

```bash
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword
```

See [docs/GARMIN_TOKEN_AUTH.md](docs/GARMIN_TOKEN_AUTH.md) for the full authentication guide.

### 4. Configure the AI planner

```bash
cp config/gemini_api.env.example config/gemini_api.env
# Add your GEMINI_API_KEY (free tier works: https://aistudio.google.com/app/apikey)
# Used as Claude fallback — also set ANTHROPIC_API_KEY in your environment
```

### 5. Set up your athlete profile

Template files are included in the repo. Copy and edit them:

```bash
cd data/athlete/
for f in *.example; do cp "$f" "${f%.example}"; done
cd ../..
```

Then edit each file in `data/athlete/` with your own details:

| File | What to fill in |
|---|---|
| `goals.md` | Race goals, training objectives |
| `upcoming_races.md` | Race schedule, goal times, priority |
| `training_preferences.md` | Schedule, dietary restrictions, coaching style |
| `current_training_status.md` | Current VDOT and training paces |
| `communication_preferences.md` | Response detail level (BRIEF / STANDARD / DETAILED) |
| `schedule_constraints.md` | Work schedule, childcare constraints, blocked days |
| `training_history.md` | Injury history, past races, background |

Calculate your VDOT from a recent race result:

```bash
python3 src/vdot_calculator.py
```

These files are gitignored — your personal data stays local.

### 6. Initial Garmin sync

```bash
python3 cli/coach.py sync
```

### 7. Generate your first training week

```bash
# Generate this week's plan (calls Brain LLM)
python3 cli/coach.py plan --week

# Preview Garmin workout upload (dry run — no API calls)
python3 cli/coach.py export-garmin

# See today's workout
python3 cli/coach.py brief --today

# Upload to Garmin (after reviewing dry run)
python3 cli/coach.py export-garmin --live
```

### 8. (Optional) Set up the Discord bot

```bash
cp config/discord_bot.env.example config/discord_bot.env
# Add your DISCORD_BOT_TOKEN

bash bin/start_discord_bot.sh
```

Or install as a systemd service:

```bash
# Edit deploy/running-coach-bot.service to set correct paths
sudo cp deploy/running-coach-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable running-coach-bot
sudo systemctl start running-coach-bot
```

---

## Architecture

```
Garmin Connect API
        │
src/garmin_sync.py  ──►  data/health/health_data_cache.json
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
- Macro planner prefers `vdot_race_derived`; falls back to a safe default if none found

---

## Macro Plan System

The macro plan gives the weekly planner a deterministic periodization arc. It is a **rail, not a cage** — readiness can reduce weekly volume, but the macro target is the ceiling.

| Mode | Trigger | Structure |
|---|---|---|
| `race_targeted` | Future race in `upcoming_races.md` | base → quality → race_specific → taper |
| `base_block` | No future race | base → quality (12 weeks, no taper) |

**Key behaviors:**
- Cache-first: no LLM call if an active macro plan already exists (override with `--force`)
- Validation gate: 9-check structural validator runs before plan is activated (Sunday alignment, phase progression, taper rules, volume ramp ≤15%/wk, long run sanity, etc.)
- Volume ceiling: weekly planner auto-clamped to macro target (0.5 mi tolerance)
- Short-race recovery: 4-day no-quality window after races < 10 mi; no volume cap
- Long-race recovery: full cap + recovery weeks after half/marathon

```bash
python3 cli/coach.py plan --macro          # generate (cached; no LLM if active plan exists)
python3 cli/coach.py plan --macro --show   # print table of all weeks
python3 cli/coach.py plan --macro --force  # regenerate even if active plan exists
```

---

## CLI Reference

```bash
python3 cli/coach.py --help
```

| Command | What it does | Calls LLM? |
|---|---|---|
| `sync` | Sync Garmin health data | No |
| `brief --today` | Show today's workout | No |
| `plan --week` | Generate this week's plan | **Yes** |
| `plan --macro` | Generate / view macro arc | **Yes** (first time) |
| `export-garmin` | Preview Garmin upload (dry run) | No |
| `export-garmin --live` | Upload workouts to Garmin | No |

---

## Discord Interface

| Command | What it does | Calls LLM? |
|---|---|---|
| `/coach_today` | Show today's plan from SQLite | No |
| `/coach_sync` | Sync Garmin data | No |
| `/coach_plan` | Generate new weekly plan + publish to Garmin | **Yes** |
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
| `plan` | Generates new plan (LLM) |
| `ai: <question>` | Direct Claude/Gemini question |

See **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** for the full command reference.

---

## Systemd Services

### Discord Bot

```bash
sudo systemctl status running-coach-bot
sudo systemctl restart running-coach-bot
sudo journalctl -u running-coach-bot -f
```

### Heartbeat Agent

```bash
sudo cp deploy/running-coach-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable running-coach-agent
sudo systemctl start running-coach-agent
```

The agent runs every 15 minutes. At 4am it performs a daily deep run: writes a vault note, checks plan staleness, and re-plans if needed. Both services share a SQLite lock so they never conflict.

---

## Documentation

| Document | Contents |
|---|---|
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | Daily workflow, all commands, debugging playbook |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Technical architecture detail |
| [docs/TRAINING_PHILOSOPHY.md](docs/TRAINING_PHILOSOPHY.md) | VDOT periodization and training principles |
| [docs/GARMIN_TOKEN_AUTH.md](docs/GARMIN_TOKEN_AUTH.md) | Token-based Garmin authentication setup |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Detailed setup guide |

---

## License / Disclaimer

Personal training tool — not medical advice. Training recommendations are generated by an AI model and should be used at your own discretion. Always consult a qualified coach or physician before making significant changes to your training load.
