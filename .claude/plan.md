# Phase 2: Post-Workout Check-In

## What this builds

When a running or strength workout appears in Garmin after a sync, the Discord bot sends a short message in #coach: "You just completed your [workout] — how did that go?" Neil replies naturally, the existing AI coach handles the response. That's it — no forms, no buttons, no special commands needed.

This closes the biggest gap between the system and Brant: proactive post-workout follow-up.

---

## Architecture

Follows the existing `on_obs_missed` pattern exactly:

1. **Heartbeat agent detects** → writes `pending_checkin` to SQLite `state` table
2. **Discord bot delivers** → reads pending on reconnect + scheduled task → posts to #coach
3. **Neil replies** → existing conversational AI handles it (no new code needed for responses)

---

## Files Changed

### 1. `memory/db.py` — Add `workout_checkins` table

Add to `_DDL`:

```sql
CREATE TABLE IF NOT EXISTS workout_checkins (
    activity_id      TEXT PRIMARY KEY,
    activity_date    DATE NOT NULL,
    activity_type    TEXT NOT NULL,
    activity_name    TEXT,
    distance_mi      REAL,
    duration_min     REAL,
    avg_hr           REAL,
    checkin_sent_at  DATETIME,
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
);
CREATE INDEX IF NOT EXISTS checkins_date ON workout_checkins(activity_date);
```

Add helper functions:
- `upsert_checkin(activity_id, activity_date, activity_type, activity_name, distance_mi, duration_min, avg_hr)` — insert-or-ignore (never overwrites)
- `get_unsent_checkins(db_path)` → list of rows where `checkin_sent_at IS NULL`
- `mark_checkin_sent(activity_id, db_path)` — sets `checkin_sent_at = now()`

---

### 2. `hooks/on_activity_completed.py` — New hook (new file)

Called from `agent/runner.py` on every cycle where the context hash changed (same condition as `on_sync` and `on_readiness_change`).

**Logic:**
1. Query `activities` table: running + strength activities from the last 48 hours
2. For each, `upsert_checkin(...)` — insert-or-ignore creates a row if new
3. Query `get_unsent_checkins()` — find any that haven't been delivered yet
4. If any exist AND no `pending_checkin` already in state:
   - Pick the most recent unsent one
   - Write to SQLite `state` as `pending_checkin` (JSON payload with all activity fields)
5. Return `{"new_activities": N, "pending_written": bool, "reason": str}`

**Activity types to include:**
- Running: `activity_type` in `("running", "trail_running", "treadmill_running")`
- Strength: `activity_type` in `("strength_training", "indoor_rowing", "cardio")`

**Idempotency:** `upsert_checkin` uses `INSERT OR IGNORE` — safe to call every cycle.

---

### 3. `agent/runner.py` — Wire the hook

In `run_cycle()`, inside the `if hash_changed:` block, after the existing `on_readiness_change` call:

```python
# on_activity_completed: detect new workouts, queue check-in messages
from hooks.on_activity_completed import run as on_activity_completed
activity_result = on_activity_completed(db_path=db)
summary["hooks_run"].append("on_activity_completed")
if activity_result["pending_written"]:
    log.info("on_activity_completed: checkin queued for '%s'",
             activity_result.get("activity_name", "?"))
```

---

### 4. `src/discord_bot.py` — Deliver check-ins

**Add `_post_pending_checkin(channel)` function:**

```python
async def _post_pending_checkin(channel) -> bool:
    """Deliver a pending check-in if one is queued. Returns True if posted."""
    from memory.db import get_state, set_state, mark_checkin_sent, DB_PATH
    raw = get_state("pending_checkin", db_path=DB_PATH)
    if not raw:
        return False
    payload = json.loads(raw)

    name = payload.get("activity_name") or "workout"
    atype = payload.get("activity_type", "")
    distance = payload.get("distance_mi")
    duration = payload.get("duration_min")
    hr = payload.get("avg_hr")

    # Build message
    if "running" in atype:
        stats = []
        if distance: stats.append(f"{distance:.1f} mi")
        if duration: stats.append(f"{int(duration)}:{int((duration%1)*60):02d}")
        if hr: stats.append(f"avg HR {int(hr)}")
        stat_str = " · ".join(stats)
        msg = f"You just finished **{name}**" + (f" ({stat_str})" if stat_str else "") + ". How did that go?"
    else:
        dur_str = f" ({int(duration)} min)" if duration else ""
        msg = f"You logged **{name}**{dur_str}. How did it feel?"

    await channel.send(msg)
    mark_checkin_sent(payload["activity_id"])
    set_state("pending_checkin", "", db_path=DB_PATH)  # clear
    return True
```

**Add `checkin_delivery_task` (30-min loop):**

```python
@tasks.loop(minutes=30)
async def checkin_delivery_task():
    channel = bot.get_channel(CHANNELS["coach"])
    if channel:
        await _post_pending_checkin(channel)
```

**Call from `on_ready`** (after the existing `_post_pending_obs` call):
```python
coach_channel = bot.get_channel(CHANNELS["coach"])
if coach_channel:
    await _post_pending_checkin(coach_channel)
```

**Start task in `on_ready`:**
```python
if not checkin_delivery_task.is_running():
    checkin_delivery_task.start()
```

**Add to `before_scheduled_tasks` decorator chain.**

---

## What's explicitly NOT in scope for Phase 2

- Structured RPE extraction or logging from responses (Phase 3)
- VDOT updates from workout execution (Phase 3)
- Logging check-in responses back to SQLite (Phase 3)
- Changing how the AI coach handles replies (it already works)

---

## Delivery timing

- Heartbeat agent syncs every 15 min → hook detects within 15 min of Garmin upload
- `checkin_delivery_task` runs every 30 min → delivers within 30 min of detection
- On reconnect (bot restart) → delivers immediately
- Worst case: run finishes → 30 min Garmin upload lag → 30 min delivery = ~60 min total. Acceptable.

---

## Testing plan

1. Confirm `workout_checkins` table gets created on `init_db()`
2. Run hook manually with a test activity_id → confirm `pending_checkin` written to state
3. Restart Discord bot → confirm check-in message posts to #coach
4. Confirm it doesn't post twice for the same activity
