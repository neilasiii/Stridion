# Design: Sync Discord Surfaces to Internal Coach Plan

**Date:** 2026-03-01
**Status:** Approved

## Problem

Three Discord-facing surfaces still read today's workout from `health_data_cache.json → scheduled_workouts` (FinalSurge ICS data), which is no longer authoritative:

| Surface | File | Source |
|---|---|---|
| Morning report workout | `src/morning_report.py` | health cache |
| `/workout` command | `src/discord_bot.py` | health cache |
| Daily workouts task | `src/daily_workout_formatter.py` | health cache |

`/coach_today` correctly reads from the internal SQLite plan. The others do not.

Additionally, the morning report AI prompt does not require the AI to explicitly show what changed when it recommends a modification — the original plan and the adjustment are buried in narrative prose.

## Approach: Inline Fix (Approach A)

Wire `skills.plans.get_active_sessions()` directly into each surface. No new modules. Each surface tries the internal plan first and falls back to the health cache if no active plan exists.

## Design

### Section 1 — Data source pattern (all three surfaces)

Each surface gets the same pattern:

```python
from skills.plans import get_active_sessions

sessions = get_active_sessions()
today_session = next((s for s in sessions if s["date"] == today_str), None)

if today_session:
    workout = _session_to_workout(today_session)
else:
    workout = _get_from_cache(cache)  # existing fallback
```

The `_session_to_workout()` conversion maps:
- `workout_type` → name label (e.g. "Easy Run", "Tempo Run")
- `intent` → description
- `duration_min` → duration
- `structure_steps` → formatted step list
- `source` → `"internal_plan"` (for downstream branching)

### Section 2 — Morning report: adjustment display

**Prompt change — add `ORIGINAL_PLAN` section:**

The prompt explicitly states what SQLite planned:
```
ORIGINAL PLAN (from internal coach system):
Type: {workout_type}  Duration: {duration_min}min
Intent: {intent}
Steps: {formatted structure_steps or "N/A"}
```

**Prompt change — add `ADJUSTMENT` output section:**

Required between NOTIFICATION and FULL_REPORT:
```
ADJUSTMENT:
[If no modification: "As planned"]
[If modifying:
  Original: <what was planned>
  Recommended: <what to do instead>
  Reason: <one sentence — the key metric driving this>]
```

**Full report structure change:**

The ADJUSTMENT block becomes the first section of the full report, before the recovery analysis. This ensures the delta is the first thing read.

### Section 3 — `/workout` Discord command (`discord_bot.py`)

1. Call `get_active_sessions()`, find today's session
2. Build embed from `workout_type`, `duration_min`, `intent`, `structure_steps`
3. `structure_steps` rendered as numbered lines: "1. Warmup 10min → 2. Tempo 25min → 3. Cooldown 10min"
4. No internal plan → fall back to existing health cache logic unchanged
5. Emoji map: easy/long → 🏃, tempo/interval → ⚡, rest → 🛌

### Section 4 — `daily_workout_formatter.py`

1. `get_scheduled_workouts()` tries internal plan first for running sessions, falls back to health cache
2. `format_running_workout()` adds a branch: if `source == "internal_plan"`, format from `workout_type + intent + structure_steps` directly (no regex name parsing)
3. Strength/mobility display logic is untouched

## Files Changed

| File | Change |
|---|---|
| `src/morning_report.py` | `get_todays_workout()` → try internal plan; `build_ai_prompt()` → add ORIGINAL_PLAN + ADJUSTMENT sections |
| `src/discord_bot.py` | `/workout` command → try internal plan; `parse_ai_response()` → extract ADJUSTMENT block |
| `src/daily_workout_formatter.py` | `get_scheduled_workouts()` → try internal plan for running sessions |

## Fallback Behaviour

If `get_active_sessions()` returns empty (no active plan in SQLite), all surfaces degrade gracefully to their existing health cache behaviour. No errors, no user-visible change.

## Out of Scope

- Strength/mobility display (generation is disabled system-wide)
- `daily_workouts_task` timing or channel routing (unchanged)
- Morning report sleep-check logic (unchanged)
