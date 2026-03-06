# Replacing Brant: Full Roadmap Design

**Date:** 2026-03-06
**Status:** Approved
**Context:** Phases 1-4 complete. FinalSurge cutover built and in 4-week validation window. Core fear identified: system could injure Neil the way Runna did — a rigid plan that ignores real data. Roadmap closes that gap.

---

## Core Insight

Brant's value is not constant plan adjustments (he only changes things when asked). His value is being a trusted, experienced safety net. The system already generates better plans than Runna and is more proactive than Brant. The missing piece: actively monitoring for overtraining signals and intervening before injury, without being asked.

---

## Step 1 — Injury Risk Monitor (immediate)

**Goal:** Close the safety gap. Make the system trustworthy enough to stop paying Brant.

### Signals monitored (6 total, from existing Garmin data)

1. **Weekly load spike** — actual executed mileage increased >10% over prior week (uses real completed runs, not planned)
2. **HRV suppression streak** — HRV below personal baseline (from `data/athlete/learned_patterns.md`) for 3+ consecutive days
3. **Easy RPE elevation** — easy runs reporting higher than expected effort from check-in data
4. **Body battery chronic drain** — ending each day below 30% without overnight recovery
5. **Sleep debt accumulation** — 3+ nights under 6.5 hours in the same week
6. **ATL/CTL ratio spike** — acute training load spiking relative to chronic load (already in health data cache)

### Severity levels

- **Yellow (2 signals)** — heads up, consider backing off. Alert posted to #coach.
- **Orange (3 signals)** — strong recommendation to modify this week's remaining workouts.
- **Red (3+ signals including load spike)** — direct recommendation for unplanned rest day.

### Alert format (plain English, not buried in morning report)

> "Your load jumped 14% this week and HRV has been suppressed 4 days in a row. I'd recommend treating Thursday's quality session as easy instead. Want me to update the plan?"

Neil replies yes/no. Yes triggers Brain LLM to regenerate remaining week days at reduced load. No is noted and monitor resets.

**Guard:** Once an alert fires, same signals cannot re-trigger for 7 days. Prevents spam.

### Architecture

- **`hooks/on_injury_risk.py`** — new heartbeat hook. Reads health cache + RPE from SQLite. Computes 6 signals. Writes `pending_injury_risk_alert` to SQLite state when threshold met. Runs every 15 min via existing agent.
- **`src/discord_bot.py`** — `_post_pending_injury_risk()` delivers alert to #coach. Handles yes/no reply to trigger plan adjustment. Wired into `on_ready` + `checkin_delivery_task`.
- **`agent/runner.py`** — one new line in `run_cycle()` to call the hook.
- **`brain/planner.py`** — existing week regeneration used on yes reply (no changes needed).

---

## Step 2 — FinalSurge Cutover (~4 weeks out)

Already fully built. After 4 clean Saturday auto-plans, heartbeat agent prompts Neil in #coach. Neil runs `/coach_cutover confirm`, reviews readiness report, internal plan becomes authoritative. No further development needed — just time.

---

## Step 3 — Move to 5 Runs/Week (~6-8 weeks out)

From observation, Brant programs 5 runs/week + 2 quality sessions (tempo + 5k pace intervals). System currently targets 4 runs/week + 1 quality.

Before changing the system: confirm this is actually what Brant does in this base block. Then replicate.

Changes when ready:
1. Bump `preferred_runs_per_week` from 4 to 5 in `memory/retrieval.py`
2. Regenerate macro with `quality_sessions_allowed=2` for quality/race-specific weeks
3. Add 5k-pace intervals as a session type alongside tempo in the planner prompt

---

## Step 4 — Race Coaching (before next A-race)

System goes quiet approaching race day. Need to add:

1. **Auto-taper detection** — macro plan knows race date; system automatically shifts to taper mode 2-3 weeks out without manual intervention
2. **Race morning message** — pacing advice, conditions-adjusted target, what to expect
3. **Post-race recovery week** — automatic easy week generation after race, no planning needed

---

## Ongoing — System Learns Neil Over Time

Pattern analyzer already runs daily at 4 AM. Over months it refines:
- Personal HRV thresholds (vs. population defaults)
- Volume tolerance ceiling
- Quality session predictors (HRV/sleep combos that predict good vs. poor sessions)
- Recovery signature (how many days to bounce back after quality work)

Each new training block starts with a more accurate model. Compounding value over time.

---

## Implementation Order

1. **Injury risk monitor** (Step 1) — build now, this week
2. **FinalSurge cutover** (Step 2) — wait for 4-week validation window (no dev work)
3. **5 runs/week** (Step 3) — observe Brant's block first, implement when pattern confirmed
4. **Race coaching** (Step 4) — implement before next A-race, timing TBD
