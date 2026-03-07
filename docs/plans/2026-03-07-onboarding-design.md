# Onboarding Workflow Design

**Date:** 2026-03-07
**Status:** Approved, pending implementation

## Overview

An interactive onboarding wizard for new users who clone the repo and open Claude Code. Covers both self-setup athletes and developers adapting the system for a different athlete.

Entry is prompted (not automatic): Claude detects a fresh clone, offers to start onboarding, and waits for the user to say yes before proceeding.

## Architecture

**Option chosen: Agent + setup script**

- `.claude/agents/onboarding-wizard.md` — handles the conversation, questions, and sequencing
- `bin/check_setup.py` — handles all system checks, outputs JSON for agent consumption
- CLAUDE.md — two small additions: first-run detection block, re-onboarding note

## Components

### 1. First-Run Detection (CLAUDE.md)

At session start, Claude silently runs:

```bash
python3 bin/check_setup.py --json 2>/dev/null
```

If `"onboarding_needed": true`, Claude prompts:

> "I notice this looks like a fresh setup. Want me to walk you through getting everything configured? It takes about 10–15 minutes and covers Garmin sync, your athlete profile, and optionally the Discord bot. Just say **yes** to start."

- User says yes → invoke `@onboarding-wizard`
- User says no → proceed normally
- Does not repeat once `data/athlete/goals.md` exists

CLAUDE.md also gets a note in the Key Commands section:

> Re-run onboarding anytime with `@onboarding-wizard` — it skips steps that are already complete.

### 2. `bin/check_setup.py`

Standalone Python script. Checks all prerequisites, outputs structured JSON.

**Invocation:**
```bash
python3 bin/check_setup.py           # Human-readable checklist
python3 bin/check_setup.py --json    # JSON for agent consumption
python3 bin/check_setup.py --fix     # Auto-fix where possible
```

**Checks:**

| Check | Auto-fixable? |
|---|---|
| Python >= 3.8 | No |
| pip deps (requirements.txt) | Yes |
| data/ subdirectories exist | Yes (mkdir) |
| Athlete context files present | No (need interview) |
| Garmin credentials set | No |
| Garmin auth (live API test) | No |
| Health data cache exists + non-empty | No (need sync) |
| SQLite DB initialized | Yes |
| Discord config present | No |
| Systemd service installed + enabled | No |

**JSON output shape:**
```json
{
  "onboarding_needed": true,
  "checks": {
    "python": {"ok": true, "version": "3.11.2"},
    "deps": {"ok": false, "missing": ["garminconnect"]},
    "garmin_auth": {"ok": false, "reason": "no credentials"},
    "health_cache": {"ok": false},
    "athlete_files": {"ok": false, "missing": ["goals.md"]},
    "discord": {"ok": false},
    "systemd": {"ok": false}
  }
}
```

`onboarding_needed` is true if athlete files or health cache are missing.

### 3. Onboarding Wizard Agent (`.claude/agents/onboarding-wizard.md`)

Runs six phases in sequence. Calls `check_setup.py` at the start of each phase to skip what's already done.

**Phase 1 — System checks**
Call `check_setup.py --json`, display results as a checklist. Auto-fix anything fixable (install deps, create dirs). Surface blockers clearly.

**Phase 2 — Garmin setup**
- If credentials missing: ask for email/password, write to `~/.bashrc`, test auth
- If auth fails with 403: explain token-based auth, run `python3 bin/generate_garmin_tokens.py`, walk through browser step
- Once auth works: run `bash bin/sync_garmin_data.sh --days 90`, summarize results ("Found 47 runs, latest was March 1")

**Phase 3 — Athlete interview (conversational, one question at a time)**
1. Name
2. Recent race result (distance + time) → VDOT calculated immediately
3. Upcoming races (date, distance, goal time)
4. Available training days and preferred time of day
5. Any injuries or physical constraints
6. Dietary restrictions
7. Communication style preference (BRIEF / STANDARD / DETAILED)

Agent writes all `data/athlete/` files at the end of this phase.

**Phase 4 — Discord bot setup (optional)**
Agent asks: "Want to set up the Discord bot? It gives you daily reports and lets you check workouts from your phone."

If yes, walks through:
1. Create application at discord.dev, copy token
2. User pastes token → agent writes to `config/discord.env`
3. Get server ID and channel IDs (agent explains how: Developer Mode in Discord)
4. Agent writes channel config
5. Install systemd service
6. Verify: send a test ping

If no, skips cleanly.

**Phase 5 — Final status board**
Call `check_setup.py --json` again, render full checklist with ✅ / ⚠️ / ❌. Explain any remaining gaps and how to fix them later.

**Phase 6 — Plan offer**
"Your profile is complete. Want me to generate your first training plan now?"
- Yes → invoke macro planner
- No → explain how to do it later (`/coach_plan` in Discord or `@vdot-running-coach` in Claude Code)

## Success Criteria

- A user with zero prior setup can go from fresh clone to first training plan in one session
- A developer forking for a different athlete can complete setup without reading any docs
- Re-running `@onboarding-wizard` is safe at any time — completed steps are skipped
- `bin/check_setup.py` works standalone as a diagnostic tool independent of onboarding

## Out of Scope

- FinalSurge / TrainingPeaks calendar import (covered in existing docs, not part of onboarding)
- Mobile / Termux setup
- Multi-athlete support
