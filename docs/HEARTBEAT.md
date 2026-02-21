# Heartbeat Agent — Architecture & Operations Guide

_Verified against: `agent/runner.py`, `agent/lock.py`, `deploy/running-coach-agent.service`._
_Last updated: 2026-02-21._

---

## 1. What runs sync and where

The **heartbeat agent is the sole background syncer.** The Discord bot does not perform scheduled syncs.

| Process | File | Trigger | Sync path |
|---|---|---|---|
| **Heartbeat agent** | `agent/runner.py` | Every 15 min (systemd loop) | `skills/garmin_sync.run()` |
| **Discord bot** | `src/discord_bot.py` | User `/coach_sync` command only | `python3 cli/coach.py sync` subprocess |

The heartbeat agent calls `skills/garmin_sync.run()` directly, which delegates to `bin/smart_sync.sh → bin/sync_garmin_data.sh → src/garmin_sync.py`. The Discord bot's `/coach_sync` command spawns the same CLI path on demand (e.g., after completing a workout).

---

## 2. Heartbeat frequency

```
LOOP_INTERVAL_SEC = 15 * 60   # agent/runner.py:41 — 900 seconds / 15 minutes
```

Each loop iteration:
1. Checks if the **daily deep run** should fire (4am local, once per day).
2. Runs `run_cycle()` — which itself calls `skills/garmin_sync.run()`.

> **Cache freshness**: the heartbeat runs sync every 15 min, but `skills/garmin_sync.run()`
> delegates to `bin/smart_sync.sh` which only actually hits the Garmin API when the cache
> is older than **30 minutes** (default `MAX_AGE_MINUTES=30` in `bin/smart_sync.sh:18`).
> This means a fresh cache is never older than ~45 min (15 min loop gap + 30 min threshold).

---

## 3. Daily deep run (4am)

Triggered once per calendar day, at or after 4:00 AM local time:

```
DAILY_HOUR_LOCAL = 4   # agent/runner.py:42
```

What it does (in order):
1. **`on_daily_rollover`** — writes a vault daily note; checks if the active plan is stale (>7 days since generation).
2. **`on_constraints_change`** — ingests any new notes from `vault/inbox/`.
3. **`brain.plan_week()`** — if plan is stale, calls the LLM to generate a new 7-day plan.

The date of the last daily deep is stored in SQLite:
```
state key: "runner_last_daily_rollover"  → value: YYYY-MM-DD (today's date)
```

---

## 4. Lock coordination

**Purpose:** Prevents the heartbeat agent and a concurrent Discord bot operation (e.g., `/coach_plan`, `/coach_export`) from colliding on SQLite writes or Garmin API calls.

**Mechanism:** SQLite state key `runner_lock` (defined in `agent/lock.py`).

```
Lock value (JSON):
  { "owner": "runner:<pid>", "acquired_at": "...", "expires_at": "..." }

TTL: 20 minutes (LOCK_TTL_MIN = 20 in agent/lock.py:24)
```

**Acquire behavior:**
- If lock is free → acquire and proceed.
- If lock is held and **not expired** → skip this cycle, log "Lock busy".
- If lock is held but **expired** (>20 min) → override stale lock, proceed.

**Refresh:** `refresh_lock()` is called between steps within a cycle to extend TTL and prevent mid-cycle expiry.

**CLI inspection:**
```bash
python3 cli/coach.py agent status   # shows current lock state + recent task_runs
```

---

## 5. How to change the heartbeat interval

**Step 1:** Edit `agent/runner.py`:
```python
LOOP_INTERVAL_SEC = 15 * 60   # change this value (seconds)
```

**Step 2:** Consider adjusting the cache freshness threshold to match:
```bash
# bin/smart_sync.sh line 18:
MAX_AGE_MINUTES=30   # should be ≤ LOOP_INTERVAL_SEC / 60
```

**Step 3:** Restart the service:
```bash
sudo systemctl restart running-coach-agent
journalctl -u running-coach-agent -f   # verify restart
```

No systemd unit changes needed — the interval is purely in Python code.

---

## 6. How to change the daily deep run time

Edit `agent/runner.py`:
```python
DAILY_HOUR_LOCAL = 4   # change to desired hour (0–23, local time)
```

Restart the service. Note: the runner compares `datetime.now().hour >= DAILY_HOUR_LOCAL`, so it fires on the **first cycle at or after** the target hour, not exactly at it (±15 min jitter from loop interval).

---

## 7. Systemd service management

**Service name:** `running-coach-agent`
**Service file:** `deploy/running-coach-agent.service`

```bash
# Status
sudo systemctl status running-coach-agent

# Start / stop / restart
sudo systemctl start running-coach-agent
sudo systemctl stop running-coach-agent
sudo systemctl restart running-coach-agent

# Enable on boot
sudo systemctl enable running-coach-agent

# Live logs
journalctl -u running-coach-agent -f

# One-shot manual run (without starting the loop)
python3 agent/runner.py --once     # one cycle
python3 agent/runner.py --daily    # force daily deep run
python3 cli/coach.py agent run-once  # same as --once via CLI
python3 cli/coach.py agent status    # lock + recent task_runs
```

**Restart policy:** `Restart=on-failure` with `RestartSec=30s`. A clean `sys.exit(0)` does not trigger a restart.

---

## 8. Discord bot sync digest (read-only)

The Discord bot posts a **heartbeat digest** to `#sync-log` four times a day via `sync_digest_task`:

| Schedule | Channel |
|---|---|
| midnight, 6:00 AM, noon, 6:00 PM EST | `#sync-log` |

This task reads SQLite only (`task_runs`, `sync_runs`, `daily_metrics`) — it does **not** trigger a Garmin sync. Each digest summarises the last 6 hours of agent activity: cycle count, data change count, last sync age, whether a readiness adjustment fired, and today's metrics snapshot (readiness, body battery, sleep score, HRV).

---

## 9. Stale cache — root causes

If you see "cache is N minutes old":

| Cause | Diagnosis | Fix |
|---|---|---|
| Agent not running | `systemctl status running-coach-agent` → inactive | `sudo systemctl start running-coach-agent` |
| Agent loop sleeping | Normal — max staleness is ~45 min | Force sync: `python3 cli/coach.py sync --force` |
| Garmin sync failing | `python3 cli/coach.py agent status` → task_runs shows `failed` | Check auth: `python3 src/garmin_token_auth.py --test` |
| Lock stuck | `agent status` → lock HELD with old PID | Lock auto-expires after 20 min; or restart agent |
| Cache threshold too high | `smart_sync.sh MAX_AGE_MINUTES` | Lower threshold or force sync with `--force` |
