# Agent Guide: Coaching System Integration

This guide provides coaching agents with quick reference for all system integrations: health data, planned workouts, and the workout library.

## Quick Start

### Session Initialization

At the start of any coaching session:

```bash
# Smart sync (checks cache age, syncs only if needed)
bash bin/smart_sync.sh

# Force sync if user reports new workout
bash bin/smart_sync.sh --force
```

This fetches latest Garmin Connect data, updates the cache, and provides a summary.

### Environment Requirements

- `GARMIN_EMAIL` and `GARMIN_PASSWORD` environment variables must be set
- Or use token-based authentication (see GARMIN_TOKEN_AUTH.md)

---

## Health Data Integration

### Data Location

**`data/health/health_data_cache.json`** - All Garmin Connect metrics in JSON format

### Available Metrics

**Activity & Performance:**
- `activities[]` - All activity types with splits, HR, pace, intervals, HR zones
- `vo2_max_readings[]` - VO2 max estimates
- `lactate_threshold{}` - Auto-detected threshold HR and pace
- `race_predictions{}` - 5K, 10K, half marathon, marathon time predictions
- `training_status{}` - Training load balance, VO2 max trends

**Recovery & Readiness:**
- `training_readiness[]` - Daily readiness score (0-100) with contributing factors
- `hrv_readings[]` - Heart rate variability daily summaries
- `body_battery[]` - Energy charged/drained throughout day
- `resting_hr_readings[]` - Daily resting heart rate
- `sleep_sessions[]` - Sleep duration, stages, quality score

**Health Monitoring:**
- `stress_readings[]` - All-day stress levels
- `spo2_readings[]` - Blood oxygen saturation
- `weight_readings[]` - Body weight and composition
- `scheduled_workouts[]` - Planned workouts from FinalSurge/TrainingPeaks

### Quick Access Pattern

```python
import json

with open('data/health/health_data_cache.json', 'r') as f:
    health = json.load(f)

# Recent activities
recent_runs = [a for a in health['activities']
               if a['activity_type'] == 'RUNNING'][:7]

# Current readiness
readiness = health['training_readiness'][0] if health['training_readiness'] else None

# Recovery metrics
avg_rhr_7d = sum(r[1] for r in health['resting_hr_readings'][:7]) / 7
last_night = health['sleep_sessions'][0] if health['sleep_sessions'] else None
latest_hrv = health['hrv_readings'][0] if health['hrv_readings'] else None

# Scheduled workouts
scheduled = health.get('scheduled_workouts', [])
```

### Pre-Workout Health Checks

**Priority 1: Training Readiness Score**
```python
readiness = health['training_readiness'][0]
score = readiness['score']  # 0-100
level = readiness['level']  # POOR, LOW, MODERATE, HIGH, EXCELLENT

if level == 'POOR' or score < 30:
    # Recommend easy day or rest
elif level == 'LOW' or score < 50:
    # Reduce intensity by 1-2 zones
elif level == 'MODERATE':
    # Proceed with caution, avoid breakthrough workouts
```

**HRV Status**
```python
hrv = health['hrv_readings'][0]
if hrv['status'] == 'UNBALANCED' or hrv['last_night_avg'] < hrv['weekly_avg'] * 0.85:
    # Consider reducing intensity or adding recovery
```

**RHR Elevation**
```python
recent_rhr = health['resting_hr_readings'][:3]
avg_recent = sum(r[1] for r in recent_rhr) / 3
baseline = sum(r[1] for r in health['resting_hr_readings'][:30]) / 30

if avg_recent > baseline + 5:
    # Strongly recommend easy day or rest
```

**Body Battery**
```python
battery = health['body_battery'][0]
if battery['charged'] < battery['drained']:
    # Not recovering - consider rest or easy day
```

### Domain-Specific Metrics

**Running Coach:**
- Training readiness (primary decision metric)
- HRV status and trends
- Race predictions vs goals
- Training load balance feedback
- Scheduled workouts comparison
- Activity intervals analysis

**Strength Coach:**
- Training readiness before heavy sessions
- Body battery and HRV for recovery assessment
- Recent running load (avoid conflicts with quality runs)
- Stress levels (high stress = skip additional physical stress)

**Mobility Coach:**
- Training readiness recovery time
- Post-workout analysis (total hard minutes, distance)
- HRV and stress for work type (restorative vs dynamic)
- Body battery for timing recommendations

**Nutrition Coach:**
- Training load and acute load (recovery nutrition needs)
- Scheduled workouts (fueling strategy timing)
- Body battery trends (nutritional adequacy check)
- Weight trends (caloric intake assessment)
- Activity analysis (during-workout fueling needs)

### Key Data Structures

**Training Readiness:**
```python
{
    'date': '2025-11-16',
    'score': 20,  # 0-100
    'level': 'POOR',  # POOR, LOW, MODERATE, HIGH, EXCELLENT
    'recovery_time': 1689,  # minutes still needed
    'sleep_score': 52,
    'acute_load': 419
}
```

**Activity with Splits:**
```python
{
    'activity_id': 20998702041,
    'activity_name': 'Morning Run - Intervals',
    'activity_type': 'RUNNING',
    'duration_seconds': 5401,
    'distance_miles': 8.69,
    'avg_heart_rate': 158,
    'splits': [
        {
            'type': 'INTERVAL_ACTIVE',
            'distance_miles': 3.29,
            'duration_seconds': 1800,
            'avg_heart_rate': 167,
            'pace_per_mile': 9.12
        }
    ]
}
```

---

## Planned Workouts System

### CRITICAL: Workout Priority Rules

**ALWAYS prioritize in this order:**

1. **FinalSurge Scheduled Workouts** (Priority 1)
   - Location: `data/health/health_data_cache.json` → `scheduled_workouts[]`
   - Source identifier: `"source": "ics_calendar"`
   - Represents athlete's current training decisions
   - **Use these when they exist for a given date**

2. **Baseline Plan Workouts** (Priority 2)
   - Location: `data/plans/planned_workouts.json`
   - **Use ONLY when no FinalSurge workout exists**
   - Represents general training framework

**Why this matters:** FinalSurge reflects active training decisions, baseline plan is static reference.

### FinalSurge Lookahead Rule

**ALL agents must check upcoming FinalSurge workouts before making recommendations.**

```bash
# Check FinalSurge workouts for next 14 days
python3 -c "
import json
from datetime import date, timedelta

with open('data/health/health_data_cache.json') as f:
    cache = json.load(f)

today = date.today()
end_date = today + timedelta(days=14)
scheduled = cache.get('scheduled_workouts', [])

upcoming = [w for w in scheduled
            if today.isoformat() <= w.get('scheduled_date', '') <= end_date.isoformat()]

if upcoming:
    print('Upcoming FinalSurge workouts:')
    for w in sorted(upcoming, key=lambda x: x['scheduled_date']):
        print(f"  {w['scheduled_date']}: {w['name']}")
else:
    print('No FinalSurge workouts in next 14 days')
"
```

**Domain-specific conflict avoidance:**
- **Strength:** Heavy lower body 48+ hours before FinalSurge quality running
- **Mobility:** Intensive sessions (40+ min) avoid day before FinalSurge quality
- **Nutrition:** Familiar foods day before quality, pre-run fueling 2-3 hrs before
- **Running:** Easy runs fill gaps, quality work only if no FinalSurge scheduled

### Checking Today's Workout

```bash
# 1. FIRST: Check FinalSurge (Priority 1)
python3 -c "
import json
from datetime import date

with open('data/health/health_data_cache.json') as f:
    cache = json.load(f)

today = date.today().isoformat()
fs_workouts = [w for w in cache.get('scheduled_workouts', [])
               if w.get('scheduled_date') == today]

if fs_workouts:
    print('FinalSurge workout found:')
    print(f"  Name: {fs_workouts[0]['name']}")
    print(f"  Description: {fs_workouts[0].get('description', 'N/A')}")
else:
    print('No FinalSurge workout - check baseline plan')
"

# 2. ONLY if no FinalSurge: Check baseline plan (Priority 2)
bash bin/planned_workouts.sh list --today -v
```

### Common Commands

```bash
# View upcoming workouts (baseline plan)
bash bin/planned_workouts.sh list --upcoming 7 -v

# Week summary
bash bin/planned_workouts.sh summary --week 3

# Mark workout complete
bash bin/planned_workouts.sh complete <workout_id> \
  --garmin-id 21089008771 \
  --duration 30 \
  --distance 3.1 \
  --pace "10:20/mile" \
  --hr 140 \
  --notes "Felt great"

# Mark workout skipped
bash bin/planned_workouts.sh skip <workout_id> \
  --reason "Poor sleep, prioritized recovery"

# Add adjustment
bash bin/planned_workouts.sh adjust <workout_id> \
  --reason "Recovery metrics show elevated RHR" \
  --change "Reduced from 45 min to 30 min" \
  --modified-by "vdot-running-coach"
```

### Best Practices

1. **ALWAYS check FinalSurge first** - Primary source of truth
2. **Baseline plan is fallback only** - Use when no FinalSurge exists
3. **Check lookahead before recommending** - Ensure no conflicts with FinalSurge quality
4. **Update status after workouts** - Keep system current
5. **Link to Garmin activities** - Use `--garmin-id` when marking complete
6. **Document adjustments** - Clear reasoning for future reference

---

## Workout Library

### Overview

Pre-built workout database across all domains (running, strength, mobility, nutrition) with searchable metadata.

### Quick Commands

```bash
# Search for specific workouts
bash bin/workout_library.sh search --domain running --type tempo
bash bin/workout_library.sh search --difficulty beginner --duration-max 30
bash bin/workout_library.sh search --tags gluten_free dairy_free

# Get workout details
bash bin/workout_library.sh get <workout-id>

# Library statistics
bash bin/workout_library.sh stats
```

### Python API

```python
from workout_library import WorkoutLibrary

library = WorkoutLibrary()

# Search with filters
results = library.search(
    domain="running",
    workout_type="tempo",
    vdot_range=[45, 55],
    training_phase="race_specific"
)

# Get specific workout
workout = library.get_workout(workout_id)
```

### Common Search Patterns

**By training phase:**
```python
workouts = library.search(training_phase="base")  # Base building
workouts = library.search(training_phase="quality")  # Intervals/threshold
workouts = library.search(training_phase="race_specific")  # Race pace
```

**By duration:**
```python
workouts = library.search(duration_max=30)  # Short (<30 min)
workouts = library.search(duration_min=30, duration_max=60)  # Medium
workouts = library.search(duration_min=90)  # Long (>90 min)
```

**By tags:**
```python
workouts = library.search(tags=["vo2_max"])
workouts = library.search(tags=["injury_prevention"])
workouts = library.search(tags=["race_specific", "marathon"])
```

**By equipment:**
```python
workouts = library.search(equipment=["bodyweight", "mat"])  # Minimal
workouts = library.search(equipment=["dumbbells", "bench"])  # Home gym
```

### Domain-Specific Usage

**Running Coach:**
- Search by VDOT range for appropriate difficulty
- Customize paces from athlete's current_training_status.md
- Reference workout name when presenting ("Classic Yasso 800s")

**Strength Coach:**
- Filter by training phase (base vs race-specific)
- Check equipment availability (training_preferences.md)
- Avoid heavy lower body before quality running

**Mobility Coach:**
- Search by tags (pre_run, post_run, recovery)
- Filter by duration for time-constrained athletes
- Consider intensity based on recent training load

**Nutrition Coach:**
- Filter by dietary restrictions (gluten_free, dairy_free)
- Search by workout type (long_run, race_day)
- Customize portions based on body weight and training load

### Customization Checklist

When using library workouts, customize based on:

1. **Athlete's VDOT** - Calculate exact paces from VDOT tables
2. **Schedule constraints** - Available time, equipment, upcoming workouts
3. **Health data** - RHR elevation, sleep quality, readiness score
4. **Dietary constraints** - Gluten-free, dairy-free requirements
5. **Training phase** - Base, quality, race-specific, taper

### Best Practices

1. **Search before creating** - Check if similar workout exists
2. **Customize to athlete** - Never copy-paste; adapt to context
3. **Reference the source** - "Based on Classic Yasso 800s workout"
4. **Explain the purpose** - Why this workout fits their goals
5. **Show progression** - Use library for beginner → advanced variations
6. **Build variety** - Avoid repeating same workout frequently

---

## Common Workflows

### Example 1: Morning Report

```bash
# 1. Sync health data
bash bin/smart_sync.sh

# 2. Check FinalSurge workout for today (Priority 1)
python3 -c "
import json
from datetime import date
cache = json.load(open('data/health/health_data_cache.json'))
today = date.today().isoformat()
fs = [w for w in cache.get('scheduled_workouts', []) if w.get('scheduled_date') == today]
if fs:
    print(f\"FinalSurge: {fs[0]['name']}\")
else:
    print('No FinalSurge workout')
"

# 3. Check baseline plan (Priority 2, only if no FinalSurge)
bash bin/planned_workouts.sh list --today -v

# 4. Check readiness metrics
python3 -c "
import json
cache = json.load(open('data/health/health_data_cache.json'))
r = cache['training_readiness'][0] if cache['training_readiness'] else None
if r:
    print(f\"Readiness: {r['score']}/100 ({r['level']})\")
    print(f\"Recovery time: {r['recovery_time']} min\")
"

# 5. Provide guidance based on FinalSurge (or baseline) + readiness
```

### Example 2: Pre-Workout Readiness Check

```python
# User: "I have a threshold workout scheduled. Ready to go?"

# 1. Check scheduled workout (FinalSurge first, then baseline)
# 2. Check training readiness
readiness = health['training_readiness'][0]

# 3. Multi-signal assessment
signals = {
    'readiness_poor': readiness['level'] == 'POOR',
    'hrv_low': hrv['status'] == 'UNBALANCED',
    'rhr_elevated': avg_rhr > baseline + 5,
    'poor_sleep': sleep_score < 50,
    'high_stress': stress['avg_stress'] > 40
}

# 4. Make go/modify/no-go recommendation
red_flags = sum(signals.values())
if red_flags >= 3:
    # Recommend rest or significant modification
elif red_flags >= 2:
    # Recommend modification (reduce intensity/duration)
else:
    # Proceed with planned workout
```

### Example 3: Post-Workout Recovery

```bash
# 1. Sync to get latest activity
bash bin/smart_sync.sh --force

# 2. Analyze last workout
python3 -c "
import json
cache = json.load(open('data/health/health_data_cache.json'))
last = cache['activities'][0]
print(f\"Distance: {last['distance_miles']} mi\")
print(f\"Duration: {last['duration_seconds'] / 60:.1f} min\")
print(f\"Avg HR: {last['avg_heart_rate']} bpm\")
print(f\"Pace: {last['pace_per_mile']:.2f}/mi\")
"

# 3. Check current recovery status
# (readiness, HRV, body battery)

# 4. Recommend recovery protocol
# (nutrition, mobility, rest day vs easy run)
```

### Example 4: Library Workout Selection

```python
# User: "I need a good threshold workout for my marathon training"

# 1. Get athlete's current VDOT
vdot = 48  # from current_training_status.md

# 2. Check upcoming FinalSurge schedule (lookahead)
# Ensure recommendation doesn't interfere

# 3. Search library
workouts = library.search(
    domain="running",
    workout_type="tempo",
    vdot_range=[vdot - 5, vdot + 5],
    training_phase="race_specific"
)

# 4. Select appropriate workout
workout = workouts[1]  # "Cruise Intervals - 5x1 Mile"

# 5. Customize paces
threshold_pace = "7:45/mi"  # From athlete's VDOT table

# 6. Present with full context and purpose explanation
```

---

## Data Structure Reference

### Scheduled Workout (FinalSurge)
```python
{
    'workout_id': 1380180174,
    'name': '20 min warm up 80-100 min @ M pace 20 min warm down',
    'description': None,
    'sport_type': 'running',
    'estimated_duration_seconds': 8400,
    'workout_provider': 'FinalSurge',
    'scheduled_date': '2025-11-16',
    'source': 'ics_calendar'
}
```

### Planned Workout (Baseline)
```python
{
    'id': 'unique-id',
    'date': '2025-12-02',
    'week_number': 1,
    'phase': 'recovery',
    'domain': 'running',
    'workout': {
        'type': 'easy_run',
        'duration_minutes': 25,
        'description': '25 min Easy (E pace, HR <140)',
        'pace_target': 'E pace 10:20-10:40/mi',
        'hr_target': 'HR <140 bpm',
        'intensity': 'easy'
    },
    'status': 'planned',
    'actual_performance': null,
    'adjustments': []
}
```

---

## Troubleshooting

**Authentication fails:**
```bash
echo $GARMIN_EMAIL && echo $GARMIN_PASSWORD
rm -rf ~/.garminconnect && bash bin/sync_garmin_data.sh
```

**Health data seems stale:**
```bash
python3 src/garmin_sync.py --days 30 --summary
```

**No FinalSurge workouts appearing:**
- Check `config/calendar_sources.json` is configured
- Verify ICS URL is valid and accessible
- Run sync to refresh scheduled workouts

**Baseline plan vs FinalSurge conflict:**
- ALWAYS prioritize FinalSurge
- Document deviation if they differ
- Update baseline plan if pattern persists

**Library search returns no results:**
- Broaden search criteria
- Remove restrictive filters (equipment, VDOT)
- Search by domain only, then filter manually

---

For complete technical details:
- **Health Data System:** `docs/HEALTH_DATA_SYSTEM.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Garmin Authentication:** `docs/GARMIN_TOKEN_AUTH.md`
