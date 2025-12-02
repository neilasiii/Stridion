# Agent Quick Reference: Planned Workouts System

## Overview

The Planned Workouts system stores the athlete's scheduled training plan workouts extracted from baseline plans. This provides agents with quick access to planned workouts, completion status, and adjustment history.

## CRITICAL: Workout Priority Rules

**Coaches must ALWAYS prioritize workouts in this order:**

1. **FinalSurge Scheduled Workouts** (Priority 1 - PRIMARY SOURCE)
   - Location: `data/health/health_data_cache.json` → `scheduled_workouts` array
   - Identifier: `"source": "ics_calendar"`
   - These represent the athlete's CURRENT training decisions
   - **ALWAYS use these when they exist for a given date**

2. **Baseline Plan Workouts** (Priority 2 - FALLBACK ONLY)
   - Location: `data/plans/planned_workouts.json`
   - Use ONLY when no FinalSurge workout exists for that date
   - Represents general training framework, not current decisions

**Why this matters:**
- FinalSurge is where the athlete makes active plan adjustments
- Baseline plan is static reference created at plan start
- FinalSurge reflects reality, baseline plan reflects original intent

## CRITICAL: FinalSurge Lookahead Rule (ALL AGENTS)

**Before recommending ANY workout from baseline plan or making custom suggestions, agents MUST:**

1. **Check upcoming FinalSurge workouts** (next 7-14 days)
2. **Ensure recommendation doesn't interfere** with the running coach's planned schedule
3. **Adjust to support, not compromise** FinalSurge quality workouts

**Why lookahead is critical:**
- FinalSurge represents the running coach's plan - it's IMMOVABLE
- All other training (strength, mobility, nutrition, baseline running) must work around it
- A poorly timed recommendation can compromise key running workouts
- Quality running sessions are the athlete's highest training priority

**Conflict examples by domain:**

**Strength:**
- ❌ Heavy squats day before FinalSurge threshold run
- ✅ Heavy squats 48+ hours before FinalSurge quality work

**Mobility:**
- ❌ Deep 60-min stretching session day before FinalSurge intervals (may cause stiffness)
- ✅ Light 15-min mobility any time

**Nutrition:**
- ❌ Suggesting new foods day before FinalSurge long run
- ✅ Pre-run fueling 2-3 hrs before FinalSurge quality workout

**Running:**
- ❌ Adding easy mileage that compromises recovery before FinalSurge quality
- ✅ Easy runs that fill gaps between FinalSurge workouts

## Key Concepts

**Planned Workout**: A scheduled workout extracted from the baseline training plan
- Contains: date, domain (running/strength/mobility/nutrition), workout details, phase, week number
- Status: `planned`, `completed`, `skipped`, or `modified`
- Tracks: actual performance when completed, adjustments with reasoning

**Data Location**: `data/plans/planned_workouts.json`

## Checking for FinalSurge Scheduled Workouts

**ALWAYS do this first before checking baseline plan:**

```bash
# View FinalSurge scheduled workouts from health cache
python3 -c "
import json
from datetime import date

with open('data/health/health_data_cache.json') as f:
    cache = json.load(f)

today = date.today().isoformat()
scheduled = cache.get('scheduled_workouts', [])

# Filter for today's workouts from FinalSurge
todays_workouts = [w for w in scheduled if w.get('scheduled_date') == today]

if todays_workouts:
    print(f'FinalSurge workout for {today}:')
    for workout in todays_workouts:
        print(f'  Name: {workout[\"name\"]}')
        print(f'  Description: {workout[\"description\"]}')
        print(f'  Source: {workout[\"source\"]}')
else:
    print(f'No FinalSurge workout for {today} - check baseline plan')
"
```

**Workflow:**
1. Check FinalSurge scheduled workouts for TODAY (above script)
2. If FinalSurge workout exists TODAY → use it, provide guidance based on it
3. If no FinalSurge workout TODAY:
   a. Check upcoming FinalSurge workouts (next 7-14 days) - see below
   b. Fall back to baseline plan OR make custom recommendation
   c. Verify recommendation doesn't interfere with upcoming FinalSurge schedule
   d. Adjust timing/intensity to support FinalSurge quality workouts

**Check upcoming FinalSurge workouts (lookahead):**

```bash
# View FinalSurge scheduled workouts for next 14 days
python3 -c "
import json
from datetime import date, timedelta

with open('data/health/health_data_cache.json') as f:
    cache = json.load(f)

today = date.today()
end_date = today + timedelta(days=14)

scheduled = cache.get('scheduled_workouts', [])

# Filter for upcoming workouts
upcoming = [w for w in scheduled
            if today.isoformat() <= w.get('scheduled_date', '') <= end_date.isoformat()]

if upcoming:
    print(f'Upcoming FinalSurge workouts (next 14 days):')
    for workout in sorted(upcoming, key=lambda x: x['scheduled_date']):
        print(f\"  {workout['scheduled_date']}: {workout['name']}\")
else:
    print('No FinalSurge workouts scheduled in next 14 days')
"
```

**Use this lookahead to:**
- Identify quality running days (threshold, tempo, intervals, long runs)
- Schedule strength/mobility around those quality days
- Plan nutrition timing for key workouts
- Avoid recommending anything that would compromise FinalSurge quality

## Common Agent Use Cases

### 1. Check Baseline Plan Workout (Use ONLY if no FinalSurge workout)

```bash
bash bin/planned_workouts.sh list --today -v
```

**When to use**: Beginning of coaching session, morning reports, daily guidance

**Returns**: All workouts scheduled for today with full details including:
- Workout type and duration
- Pace/HR targets
- Week number and training phase
- Current status

### 2. View Upcoming Schedule

```bash
# Next 7 days
bash bin/planned_workouts.sh list --upcoming 7 -v

# Next 14 days
bash bin/planned_workouts.sh list --upcoming 14 -v
```

**When to use**: Weekly planning, assessing training load, making adjustments

**Returns**: All workouts in the next N days

### 3. Check Week Summary

```bash
bash bin/planned_workouts.sh summary --week 3
```

**When to use**: Evaluating adherence, weekly check-ins, progress tracking

**Returns**:
- Total workouts planned vs completed
- Completion rate
- Breakdown by domain (running, strength, mobility)

### 4. Review Recent Completion Status

```bash
# List all completed workouts
bash bin/planned_workouts.sh list --status completed -v

# List skipped workouts
bash bin/planned_workouts.sh list --status skipped -v
```

**When to use**: Understanding training adherence, identifying patterns

### 5. Check Specific Training Phase

```bash
# View all workouts in current phase
bash bin/planned_workouts.sh list --phase recovery -v
bash bin/planned_workouts.sh list --phase base_building -v
bash bin/planned_workouts.sh list --phase early_quality -v
```

**When to use**: Phase-specific guidance, ensuring phase-appropriate adjustments

## Updating Workouts

### Mark Workout as Completed

When athlete reports completing a workout:

```bash
bash bin/planned_workouts.sh complete <workout_id> \
  --garmin-id 21089008771 \
  --duration 32 \
  --distance 3.2 \
  --pace "10:15/mile" \
  --hr 138 \
  --notes "Felt great, extended by 5 minutes"
```

**Required**: workout_id (get from `list` command)
**Optional**: All performance data

### Mark Workout as Skipped

When athlete misses a workout:

```bash
bash bin/planned_workouts.sh skip <workout_id> \
  --reason "Poor sleep, prioritized recovery"
```

### Add Adjustment to Workout

When modifying the planned workout:

```bash
bash bin/planned_workouts.sh adjust <workout_id> \
  --reason "Recovery metrics show elevated RHR" \
  --change "Reduced from 45 min to 30 min easy run" \
  --modified-by "vdot-running-coach"
```

**Important**: This marks workout as "modified" and preserves the adjustment history

## Integration with Other Systems

### Health Data Cache

After marking a workout complete, link it to the Garmin activity:

1. Check `data/health/health_data_cache.json` for the activity ID
2. Use `--garmin-id` flag when marking complete
3. This creates bidirectional link: workout → activity

### Baseline Plan

The planned workouts are extracted from:
`data/plans/gasparilla_half_marathon_baseline_plan.md`

To re-extract after plan updates:

```bash
python3 src/extract_baseline_plan.py
```

**Warning**: This clears all existing completion/adjustment data!

## Example Agent Workflow

### Morning Report (CORRECT WORKFLOW)

```bash
# 1. FIRST: Check FinalSurge scheduled workout (Priority 1)
python3 -c "
import json
from datetime import date
cache = json.load(open('data/health/health_data_cache.json'))
today = date.today().isoformat()
fs_workouts = [w for w in cache.get('scheduled_workouts', []) if w.get('scheduled_date') == today]
if fs_workouts:
    print('FinalSurge workout found:')
    print(fs_workouts[0])
else:
    print('No FinalSurge workout - check baseline plan')
"

# 2. ONLY if no FinalSurge workout: Check upcoming FinalSurge (lookahead)
python3 -c "
import json
from datetime import date, timedelta
cache = json.load(open('data/health/health_data_cache.json'))
today = date.today()
upcoming = [w for w in cache.get('scheduled_workouts', [])
            if today.isoformat() <= w['scheduled_date'] <= (today + timedelta(days=14)).isoformat()]
for w in sorted(upcoming, key=lambda x: x['scheduled_date'])[:7]:
    print(f\"{w['scheduled_date']}: {w['name']}\")
"

# 3. Check baseline plan (Priority 2)
bash bin/planned_workouts.sh list --today -v

# 4. Check week progress
bash bin/planned_workouts.sh summary --week 1

# 5. Check upcoming baseline workouts
bash bin/planned_workouts.sh list --upcoming 3 -v

# 6. Provide guidance based on:
#    - FinalSurge workout (if exists) OR baseline plan workout (if no FinalSurge)
#    - Upcoming FinalSurge schedule (ensure recommendation doesn't interfere)
#    - Recent completion rate
#    - Recovery metrics
```

### Post-Workout Session

```bash
# 1. Get today's planned workout
bash bin/planned_workouts.sh list --today -v

# 2. Athlete reports completion
# Extract workout_id from output

# 3. Mark as completed with actual performance
bash bin/planned_workouts.sh complete <workout_id> \
  --duration 30 \
  --distance 3.1 \
  --pace "10:20/mile" \
  --hr 140 \
  --notes "Felt easy, good run"
```

### Weekly Check-In

```bash
# 1. Review last week's adherence
bash bin/planned_workouts.sh summary --week 1

# 2. Check upcoming week
bash bin/planned_workouts.sh list --week 2 -v

# 3. Identify any needed adjustments based on completion rate and athlete feedback
```

## Python API

For more complex operations, use the PlannedWorkoutManager directly:

```python
from planned_workout_manager import PlannedWorkoutManager

manager = PlannedWorkoutManager()

# Get today's workouts
today_workouts = manager.get_today_workouts()

# Get specific workout
workout = manager.get_workout(workout_id)

# Mark completed
manager.mark_completed(workout_id, {
    "garmin_activity_id": 21089008771,
    "date_completed": "2025-12-02",
    "duration_minutes": 30,
    "avg_hr": 140,
    "notes": "Great run"
})

# Add adjustment
manager.add_adjustment(
    workout_id,
    reason="Recovery needs",
    change="Reduced duration",
    modified_by="vdot-running-coach"
)
```

## Best Practices

1. **ALWAYS check FinalSurge first** - Priority 1 source of truth for scheduled workouts
2. **Baseline plan is fallback only** - Use only when no FinalSurge workout exists
3. **Update status after athlete reports** - Keep system current
4. **Add adjustments with clear reasoning** - Document decision-making for future reference
5. **Link to Garmin activities** - Maintain connection between plan and actual data
6. **Review adherence weekly** - Use completion rates to assess plan viability
7. **Document deviations** - Note when FinalSurge differs from baseline plan and why

## Data Schema

Each planned workout contains:

```json
{
  "id": "unique-id",
  "date": "2025-12-02",
  "week_number": 1,
  "phase": "recovery",
  "domain": "running",
  "workout": {
    "type": "easy_run",
    "duration_minutes": 25,
    "description": "25 min Easy (E pace, keep HR <140 bpm)",
    "pace_target": "E pace 10:20-10:40/mile",
    "hr_target": "HR <140 bpm",
    "intensity": "easy"
  },
  "status": "planned",
  "actual_performance": null,
  "adjustments": []
}
```

## Troubleshooting

**Q: Workout IDs are long UUIDs - how do I use them?**
A: Copy the ID from `list -v` output, or use date-based filtering to narrow down workouts

**Q: Can I modify the baseline plan markdown?**
A: Yes, but you must re-run `python3 src/extract_baseline_plan.py` to update planned workouts (this clears completion data!)

**Q: Should I update planned workouts or just make notes in conversation?**
A: Update planned workouts when making durable changes. Use conversation for ephemeral guidance.

**Q: What if athlete wants to swap workout days?**
A: Delete one workout, get the other's ID, and update its date field via adjust command or Python API
