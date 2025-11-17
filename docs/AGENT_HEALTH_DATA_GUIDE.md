# Agent Guide: Using Health Data

## Quick Start for Coaching Agents

When starting a coaching session or when the user mentions new workout data:

```bash
bash bin/sync_garmin_data.sh
```

This command:
1. Fetches latest data from Garmin Connect API
2. Updates the cache incrementally
3. Shows a 14-day summary

**Note:** Requires `GARMIN_EMAIL` and `GARMIN_PASSWORD` environment variables to be set.

---

## Reading Current Health Metrics

The health data cache is in: **`data/health/health_data_cache.json`**

### Available Data Types

**Activity Data:**
- `activities[]` - Running/walking activities with splits, HR, pace, **activity names**, **HR zones** (time-in-zone data)
- `scheduled_workouts[]` - Planned workouts from training platforms (e.g., FinalSurge)

**Performance Metrics:**
- `vo2_max_readings[]` - VO2 max estimates
- `lactate_threshold{}` - Auto-detected threshold HR (bpm) and pace - **NEW**
- `race_predictions{}` - 5K, 10K, half marathon, marathon time predictions
- `training_status{}` - Training load balance, VO2 max trends

**Recovery & Readiness:**
- `training_readiness[]` - Daily readiness score (0-100) with contributing factors
- `hrv_readings[]` - Heart rate variability (HRV) daily summaries
- `body_battery[]` - Energy charged/drained throughout day
- `resting_hr_readings[]` - Daily resting heart rate
- `sleep_sessions[]` - Sleep duration, efficiency, stages

**Health Monitoring:**
- `stress_readings[]` - All-day stress levels
- `spo2_readings[]` - Blood oxygen saturation
- `weight_readings[]` - Body weight, composition (when available)

### Quick Python Access

```python
import json

# Load the cache
with open('data/health/health_data_cache.json', 'r') as f:
    health = json.load(f)

# Access recent data
recent_runs = [a for a in health['activities']
               if a['activity_type'] == 'RUNNING'][:7]

latest_vo2 = health['vo2_max_readings'][0]['vo2_max'] if health['vo2_max_readings'] else None

avg_rhr_7d = sum(r[1] for r in health['resting_hr_readings'][:7]) / 7

last_night_sleep = health['sleep_sessions'][0] if health['sleep_sessions'] else None

# NEW METRICS
training_readiness = health['training_readiness'][0] if health['training_readiness'] else None
latest_hrv = health['hrv_readings'][0] if health['hrv_readings'] else None
race_preds = health.get('race_predictions', {})
scheduled = health.get('scheduled_workouts', [])
body_battery = health['body_battery'][0] if health['body_battery'] else None
```

---

## Key Metrics for Each Coaching Domain

### Running Coach

**Check Before Prescribing Workouts:**

1. **Training Readiness Score** (PRIORITY CHECK)
   ```python
   readiness = health['training_readiness'][0]
   score = readiness['score']  # 0-100
   level = readiness['level']  # POOR, LOW, MODERATE, HIGH, EXCELLENT
   recovery_time = readiness['recovery_time']  # minutes

   if level == 'POOR' or score < 30:
       # Strongly recommend easy day or rest
       # Example: Score 20 = significantly compromised readiness
   elif level == 'LOW' or score < 50:
       # Reduce workout intensity by 1-2 zones
   elif level == 'MODERATE':
       # Proceed with caution, avoid breakthrough workouts
   ```

2. **Compare Scheduled vs. Actual Workouts**
   ```python
   # Check if athlete completed planned workout
   scheduled = health['scheduled_workouts']
   recent_run = health['activities'][0]

   # Example: Scheduled "20 min warm up 80-100 min @ M pace 20 min warm down"
   # Check if splits show the structure was followed
   intervals = [s for s in recent_run['splits'] if s['type'] == 'INTERVAL_ACTIVE']

   # Workout name often describes the session intent
   workout_name = recent_run.get('activity_name', '')
   # Example: "Altamonte Springs - 2:30 alternating 30 min E/ 30 mi"
   ```

3. **Activity Intervals Analysis**
   ```python
   # Use split data to analyze workout structure
   for split in recent_run['splits']:
       if split['type'] == 'INTERVAL_ACTIVE':
           pace = split['pace_per_mile']
           hr = split['avg_heart_rate']
           distance = split['distance_miles']
           # Compare to prescribed paces for that workout type
   ```

4. **HRV Status**
   ```python
   hrv = health['hrv_readings'][0]
   status = hrv['status']  # BALANCED, UNBALANCED, LOW, etc.
   weekly_avg = hrv['weekly_avg']
   last_night = hrv['last_night_avg']

   if status == 'UNBALANCED' or last_night < weekly_avg * 0.85:
       # Consider reducing intensity or adding recovery day
   ```

5. **Training Load Balance**
   ```python
   training_status = health.get('training_status', {})
   load = training_status.get('training_load', {})
   feedback = load.get('feedback')

   # Example: 'AEROBIC_HIGH_SHORTAGE' means need more tempo/threshold work
   # Example: 'AEROBIC_LOW_SHORTAGE' means need more easy miles
   if feedback == 'AEROBIC_HIGH_SHORTAGE':
       # Prioritize threshold and tempo runs
   ```

6. **Race Predictions vs. Goals**
   ```python
   preds = health.get('race_predictions', {})
   marathon_time = preds.get('time_marathon')  # seconds

   if marathon_time:
       pred_hours = marathon_time / 3600
       # Example: 15007 seconds = 4:10:07
       # Compare to athlete goal (4:00:00 = 14400 seconds)
       # Use to calibrate VDOT and pace prescriptions
   ```

7. **Recovery Status (Traditional Metrics)**
   ```python
   # Is RHR elevated?
   recent_rhr = health['resting_hr_readings'][:3]
   avg_recent = sum(r[1] for r in recent_rhr) / 3
   baseline = sum(r[1] for r in health['resting_hr_readings'][:30]) / 30

   if avg_recent > baseline + 5:
       # Strongly recommend easy day or rest
   ```

8. **Body Battery**
   ```python
   battery = health['body_battery'][0]
   net_energy = battery['charged'] - battery['drained']

   if net_energy < 0:
       # Not fully recovering - consider rest or easy day
   ```

### Strength Coach

**Check Before Scheduling Strength:**

1. **Training Readiness** (PRIORITY)
   ```python
   readiness = health['training_readiness'][0]

   if readiness['level'] == 'POOR':
       # Skip strength or do very light bodyweight only
   elif readiness['level'] == 'LOW':
       # Reduce volume by 30-50%, avoid heavy lifts
   elif readiness['recovery_time'] > 1440:  # >24 hours
       # Scale back intensity significantly
   ```

2. **Body Battery & HRV**
   ```python
   battery = health['body_battery'][0]
   hrv = health['hrv_readings'][0]

   if battery['charged'] - battery['drained'] < 10 or hrv['status'] == 'UNBALANCED':
       # Consider postponing strength session or focus on mobility instead
   ```

3. **Recent Running Load**
   ```python
   # Check scheduled workouts to avoid conflicts
   scheduled = health['scheduled_workouts']
   today_workout = [w for w in scheduled if 'today' in w['updated_date']]

   # Don't schedule heavy leg work day before key run
   if today_workout and 'M pace' in today_workout[0]['name']:
       # Recommend lighter strength or upper body focus
   ```

4. **Stress Levels**
   ```python
   stress = health['stress_readings'][0]

   if stress['avg_stress'] > 40 or stress['max_stress'] > 80:
       # High stress = avoid additional physical stress
       # Recommend restorative work instead
   ```

### Mobility Coach

**Check Before Recommending Mobility:**

1. **Training Readiness & Recovery Time**
   ```python
   readiness = health['training_readiness'][0]

   if readiness['recovery_time'] > 720:  # >12 hours
       # Prioritize restorative, gentle mobility
       # Focus on parasympathetic activation
   elif readiness['sleep_score'] < 50:
       # Add evening mobility routine to support sleep
   ```

2. **Post-Workout Analysis**
   ```python
   # Use split data to assess workout intensity
   last_run = health['activities'][0]
   intervals = [s for s in last_run['splits'] if s['type'] == 'INTERVAL_ACTIVE']

   total_hard_mins = sum(s['duration_seconds']/60 for s in intervals
                         if s.get('avg_heart_rate', 0) > 165)

   if total_hard_mins > 30 or last_run['distance_miles'] > 15:
       # Prioritize recovery mobility (gentle, restorative)
   else:
       # Can include more dynamic mobility
   ```

3. **HRV & Stress**
   ```python
   hrv = health['hrv_readings'][0]
   stress = health['stress_readings'][0]

   if hrv['status'] != 'BALANCED' or stress['avg_stress'] > 35:
       # Focus on calming, parasympathetic work
       # Gentle stretching, breathing exercises
   ```

4. **Body Battery**
   ```python
   battery = health['body_battery'][0]

   if battery['drained'] > battery['charged']:
       # Recommend evening restorative mobility to aid recovery
   ```

### Nutrition Coach

**Check Before Meal Planning:**

1. **Training Load & Readiness**
   ```python
   readiness = health['training_readiness'][0]
   training_status = health.get('training_status', {})
   load = training_status.get('training_load', {})

   acute_load = readiness.get('acute_load', 0)

   # High acute load = prioritize recovery nutrition
   if acute_load > 400:
       # Emphasize recovery meals, anti-inflammatory foods
       # Increase carb intake to support glycogen replenishment
   ```

2. **Scheduled Workouts**
   ```python
   # Plan nutrition around upcoming key workouts
   scheduled = health['scheduled_workouts']
   upcoming = [w for w in scheduled if 'M pace' in w['name'] or 'threshold' in w['name'].lower()]

   if upcoming:
       # Pre-workout: carb-loading recommendations
       # During: fueling strategy based on duration
       # Post: recovery nutrition timing
   ```

3. **Body Battery & Recovery**
   ```python
   battery = health['body_battery'][0]

   if battery['charged'] < battery['drained']:
       # Not recovering well - check nutrition adequacy
       # May need more calories, better meal timing, or sleep nutrition
   ```

4. **Weight Trends**
   ```python
   if health['weight_readings']:
       current_weight = health['weight_readings'][0]['weight_lbs']
       week_ago = [w for w in health['weight_readings']
                   if (datetime.now() - datetime.fromisoformat(w['timestamp'])).days == 7]

       if week_ago:
           change = current_weight - week_ago[0]['weight_lbs']
           if change < -2.0:
               # Recommend increased caloric intake
   ```

5. **Activity Analysis**
   ```python
   # Check recent workout intensity and duration for fueling needs
   recent_run = health['activities'][0]
   intervals = [s for s in recent_run['splits'] if s['type'] == 'INTERVAL_ACTIVE']

   total_cals = sum(s.get('calories', 0) for s in intervals)
   duration_hrs = sum(s['duration_seconds'] for s in intervals) / 3600

   if duration_hrs > 1.5:
       # During-workout fueling recommendations
       # 30-60g carbs/hour for runs >90 minutes
   ```

6. **SpO2 Monitoring**
   ```python
   spo2 = health['spo2_readings'][0]

   if spo2.get('avg_spo2', 100) < 93:
       # May indicate iron deficiency or altitude issues
       # Recommend checking iron status, increasing iron-rich foods
   ```

---

## Agent Workflow Example

### Example 1: Post-Long Run Recovery (Using New Metrics)

```markdown
User: "I just finished my long run. What should I do for recovery?"

Agent Actions:
1. Sync health data: `bash bin/sync_garmin_data.sh`
2. Read cache: Review last run details (distance, HR, pace, splits)
3. Check readiness metrics: Training readiness, HRV, body battery
4. Assess: Compare to scheduled workout and recovery metrics
5. Recommend: Provide evidence-based recovery protocol

Response:
"I see you completed a 20.3-mile run this morning at 9:52/mi pace with an
average HR of 156 bpm. Looking at your splits, you maintained great consistency
with your interval paces staying in the 9:45-10:05 range.

**Current Recovery Status:**
- Training Readiness: 35/100 (LOW) - Expected after a long run
- Recovery Time Needed: 18 hours
- HRV: 62 ms last night (below your weekly average of 71 ms)
- Body Battery: Currently at 45, drained 55 points during the run
- Sleep: 6.2 hours last night (52/100 sleep score)

This was a demanding effort, and your body is showing it needs focused recovery:

**Immediate (Next 2 Hours):**
- Nutrition: 30g protein + 60g carbs for glycogen replenishment
- Hydration: 16-20 oz water with electrolytes
- Mobility: 20-min gentle hip/leg recovery routine (no aggressive stretching)

**Rest of Today:**
- Continue hydrating, aim for light movement (walking)
- Focus on sleep nutrition tonight - consider magnesium, tart cherry juice

**Tomorrow:**
- Monitor RHR when you wake - if elevated >5 bpm, take full rest day
- If RHR normal: Easy 30-40 min recovery run (10:30-11:00/mi, HR <140)
- Check training readiness score - if still <40, extend recovery another day

Your scheduled workout for Monday shows '45 min E' which aligns well with recovery needs."
```

### Example 2: Pre-Workout Readiness Check

```markdown
User: "Good morning! I have a threshold workout scheduled today. Ready to go?"

Agent Actions:
1. Sync health data: `bash bin/sync_garmin_data.sh`
2. Check training readiness score
3. Review scheduled workout
4. Assess HRV, sleep, body battery, stress
5. Make go/no-go recommendation

Response:
"Good morning! Let me check your readiness for today's threshold session.

**Scheduled Workout:** '20 min warm up 3x4 min @ 5k pace on 2 min recovery 20 min warm down'

**Current Readiness Metrics:**
- Training Readiness: 20/100 (POOR) ⚠️
- Recovery Time Still Needed: 28 hours
- HRV: 55 ms (significantly below weekly average of 71 ms)
- Body Battery: Net -15 (drained more than charged yesterday)
- Sleep: 5.1 hours (Poor quality, 45/100 score)
- Stress: Average 42 (elevated)
- RHR: 51 bpm (baseline 46 bpm, elevated +5 bpm)

**Recommendation: Modify Workout**

Your body is showing clear signs it's not ready for a breakthrough threshold session.
Multiple red flags indicate compromised readiness:
- Poor sleep quality and duration
- Elevated RHR (5+ bpm above baseline)
- HRV significantly depressed
- High stress levels
- Still recovering from recent training load

**Modified Workout:**
Instead of threshold intervals, do 40-50 minutes easy (10:30-11:10 pace, HR <145).
This maintains training consistency while respecting recovery needs.

**Why This Matters:**
Pushing through with intervals today risks:
- Poor workout quality (won't hit target paces anyway)
- Extended recovery time needed
- Increased injury risk
- Compromised adaptation

Let's reschedule the threshold work for later this week when you're properly recovered."
```

---

## Common Patterns

### Pattern 1: Pre-Workout Health Check

```python
# Before prescribing any workout
rhr_status = check_rhr_elevation()
sleep_quality = check_last_night_sleep()
recent_load = calculate_weekly_volume()

if rhr_status == "elevated" or sleep_quality == "poor":
    recommend_conservative_option()
elif recent_load == "high":
    recommend_recovery_focus()
else:
    proceed_with_planned_workout()
```

### Pattern 2: VDOT Validation

```python
# After reviewing recent workout data
prescribed_easy_pace = 10.5  # min/mile
actual_runs = get_recent_easy_runs()

avg_actual_pace = mean(run['pace_per_mile'] for run in actual_runs)
avg_actual_hr = mean(run['avg_heart_rate'] for run in actual_runs)

if avg_actual_pace > prescribed_easy_pace + 0.5 and avg_actual_hr > 145:
    # Paces may be too aggressive for current fitness
    recommend_vdot_adjustment()
```

### Pattern 3: Fatigue Detection

```python
# Multi-signal fatigue check
signals = {
    'rhr_elevated': avg_rhr_3d > baseline_rhr + 5,
    'poor_sleep': total_sleep_hours < 6.5,
    'high_volume': miles_7d > miles_30d_avg * 1.3,
    'performance_decline': recent_pace_trend_slower()
}

fatigue_count = sum(signals.values())
if fatigue_count >= 3:
    recommend_recovery_block()
elif fatigue_count >= 2:
    reduce_intensity_this_week()
```

---

## Important Notes

1. **Always sync data at session start** - Run `bash bin/sync_garmin_data.sh`
2. **Use objective metrics to support recommendations**
3. **Never ignore multiple red flags (RHR, sleep, performance)**
4. **Communicate the "why" - show the athlete the data**
5. **Data is pulled directly from Garmin Connect** - no manual exports needed

---

## Troubleshooting for Agents

**If authentication fails:**
```bash
# Verify environment variables are set
echo $GARMIN_EMAIL
echo $GARMIN_PASSWORD

# Remove token cache and re-authenticate
rm -rf ~/.garminconnect
bash bin/sync_garmin_data.sh
```

**If health data seems stale:**
```bash
# Manually trigger sync with verbose output
python3 src/garmin_sync.py --days 30 --summary
```

**If no recent activities appear:**
- Check `last_updated` timestamp in cache
- Verify data exists in Garmin Connect web/app
- Check for API errors in sync output
- Some data types (weight, VO2 max) may not be recorded daily

**If sync is slow:**
- Reduce sync window: `bash bin/sync_garmin_data.sh --days 14`
- Default is 30 days, which is usually sufficient

---

## Data Source Notes

All data comes directly from Garmin Connect API:
- **Activities**: Synced immediately after upload to Garmin Connect (includes splits/laps, activity names)
- **Sleep**: Usually available next morning (requires compatible Garmin device)
- **VO2 Max**: Calculated by Garmin from GPS runs with HR data
- **Weight**: Manual entry in Garmin Connect or compatible scale
- **Resting HR**: Calculated daily by Garmin device
- **HRV**: Calculated nightly by compatible Garmin devices (Forerunner 265, etc.)
- **Training Readiness**: Calculated daily by Garmin using multiple factors
- **Body Battery**: Tracked throughout day by Garmin device
- **Stress**: All-day stress tracking from HRV measurements
- **SpO2**: Blood oxygen measured by compatible devices
- **Race Predictions**: Updated by Garmin based on recent fitness
- **Training Status**: Garmin's AI analysis of training load and balance
- **Scheduled Workouts**: Synced from connected training platforms (FinalSurge, TrainingPeaks, etc.)

**Data Latency**: Most recent data is typically available within minutes of syncing with Garmin Connect mobile app or uploading from device.

---

## Data Structure Reference

### Activity Structure (with new fields)
```python
{
    'activity_id': 20998702041,
    'date': '2025-11-15T11:47:02',
    'activity_name': 'Altamonte Springs - 2:30 alternating 30 min E/ 30 mi',  # NEW
    'activity_type': 'RUNNING',
    'duration_seconds': 5401.50,
    'distance_miles': 8.69,
    'calories': 1033.0,
    'avg_heart_rate': 158.0,
    'max_heart_rate': 178.0,
    'avg_speed': 5.79,
    'pace_per_mile': 10.36,
    'splits': [  # NEW - detailed lap/interval data
        {
            'type': 'INTERVAL_ACTIVE',  # or RWD_RUN, RWD_WALK, RWD_STAND
            'distance_miles': 3.29,
            'duration_seconds': 1800.0,
            'avg_heart_rate': 167.0,
            'max_heart_rate': 175.0,
            'avg_speed_mph': 6.58,
            'pace_per_mile': 9.12,
            'avg_cadence': 152.9,
            'avg_power': 333.0,
            'calories': 401.0
        }
    ]
}
```

### Training Readiness Structure (NEW)
```python
{
    'date': '2025-11-16',
    'score': 20,  # 0-100
    'level': 'POOR',  # POOR, LOW, MODERATE, HIGH, EXCELLENT
    'recovery_time': 1689,  # minutes still needed
    'sleep_score': 52,  # 0-100
    'hrv_feedback': 'GOOD',
    'stress_feedback': 'GOOD',
    'acute_load': 419
}
```

### HRV Structure (NEW)
```python
{
    'date': '2025-11-16',
    'weekly_avg': 71,  # ms
    'last_night_avg': 68,  # ms
    'last_night_5min_high': 90,  # ms
    'status': 'BALANCED',  # BALANCED, UNBALANCED, LOW, etc.
    'baseline_low_upper': 60,
    'baseline_balanced_low': 63,
    'baseline_balanced_upper': 74
}
```

### Body Battery Structure (NEW)
```python
{
    'date': '2025-11-16',
    'charged': 74,  # energy gained
    'drained': 35   # energy spent
    # Net = charged - drained
}
```

### Race Predictions Structure (NEW)
```python
{
    'date': '2025-11-16',
    'time_5k': 1458,  # seconds (24:18)
    'time_10k': 3054,  # seconds (50:54)
    'time_half_marathon': 6800,  # seconds (1:53:20)
    'time_marathon': 15007  # seconds (4:10:07)
}
```

### Training Status Structure (NEW)
```python
{
    'date': '2025-11-16',
    'vo2_max': {
        'date': '2025-11-14',
        'value': 51.0,
        'precise_value': 50.6
    },
    'training_load': {
        'date': '2025-11-16',
        'aerobic_low': 1311.9,
        'aerobic_high': 534.1,
        'anaerobic': 0.0,
        'feedback': 'AEROBIC_HIGH_SHORTAGE'  # Need more tempo/threshold
    }
}
```

### Scheduled Workout Structure (NEW)
```python
{
    'workout_id': 1380180174,
    'name': '20 min warm up 80-100 min @ M pace/ effort 20 min warm down',
    'description': None,
    'sport_type': 'running',
    'estimated_duration_seconds': 8400,  # 140 minutes
    'estimated_distance_meters': None,
    'workout_provider': 'FinalSurge',
    'created_date': '2025-11-10T06:46:05.0',
    'updated_date': '2025-11-13T06:45:38.0'
}
```

### Stress Structure (NEW)
```python
{
    'date': '2025-11-16',
    'avg_stress': 18,  # 0-100
    'max_stress': 90   # 0-100
}
```

### SpO2 Structure (NEW)
```python
{
    'date': '2025-11-16',
    'avg_spo2': 95.0,  # %
    'lowest_spo2': 86,  # %
    'avg_sleep_spo2': 95.0  # %
}
```

---

For full technical details, see: **`docs/HEALTH_DATA_SYSTEM.md`**
