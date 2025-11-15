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
```

---

## Key Metrics for Each Coaching Domain

### Running Coach

**Check Before Prescribing Workouts:**

1. **Recent Run Performance**
   ```python
   # Are prescribed paces matching actual performance?
   for run in recent_runs[:3]:
       pace = run['pace_per_mile']
       hr = run['avg_heart_rate']
       # If easy runs (prescribed 10:00-11:10) show HR > 150,
       # pace prescription may be too fast
   ```

2. **Recovery Status**
   ```python
   # Is RHR elevated?
   recent_rhr = health['resting_hr_readings'][:3]
   avg_recent = sum(r[1] for r in recent_rhr) / 3
   baseline = sum(r[1] for r in health['resting_hr_readings'][:30]) / 30

   if avg_recent > baseline + 5:
       # Strongly recommend easy day or rest
   ```

3. **Sleep Quality**
   ```python
   sleep = health['sleep_sessions'][0]
   if sleep['total_duration_minutes'] < 360:  # Less than 6 hours
       # Recommend conservative workout adjustment
   ```

4. **Training Load**
   ```python
   # Check recent volume
   miles_7d = sum(r['distance_miles'] for r in recent_runs)
   # If significantly higher than normal, watch for fatigue
   ```

### Strength Coach

**Check Before Scheduling Strength:**

1. **Recent Running Load**
   ```python
   # Don't schedule heavy leg work day before key run
   today = datetime.now().date()
   yesterday_run = [r for r in recent_runs
                    if r['date'].startswith(str(today - timedelta(1)))]

   if yesterday_run and yesterday_run[0]['distance_miles'] > 10:
       # Recommend lighter strength or upper body focus
   ```

2. **Recovery Metrics**
   ```python
   # If RHR elevated or sleep poor, reduce strength volume
   if avg_recent_rhr > baseline + 3 or last_sleep_hours < 6.5:
       # Scale back strength session intensity
   ```

### Mobility Coach

**Check Before Recommending Mobility:**

1. **Post-Workout Timing**
   ```python
   # If hard run or long run completed recently
   last_run = recent_runs[0]
   if last_run['distance_miles'] > 15 or last_run['avg_heart_rate'] > 155:
       # Prioritize recovery mobility (gentle, restorative)
   else:
       # Can include more dynamic mobility
   ```

2. **Sleep Quality**
   ```python
   if sleep['sleep_efficiency'] < 75:
       # Suggest evening recovery mobility to support better sleep
   ```

### Nutrition Coach

**Check Before Meal Planning:**

1. **Weight Trends**
   ```python
   current_weight = health['weight_readings'][0]['weight_lbs']
   week_ago = [w for w in health['weight_readings']
               if (datetime.now() - datetime.fromisoformat(w['timestamp'])).days == 7]

   if week_ago:
       change = current_weight - week_ago[0]['weight_lbs']
       if change < -2.0:
           # Recommend increased caloric intake
   ```

2. **Training Load**
   ```python
   # High mileage weeks need more carbs
   if miles_7d > 50:
       # Emphasize carbohydrate timing around workouts
   ```

---

## Agent Workflow Example

```markdown
User: "I just finished my long run. What should I do for recovery?"

Agent Actions:
1. Sync health data: `bash bin/sync_garmin_data.sh`
2. Read cache: Review last run details (distance, HR, pace)
3. Assess: Compare to recent training load and recovery metrics
4. Recommend: Provide evidence-based recovery protocol

Response:
"I see you completed a 20.3-mile run this morning at 9:52/mi pace with an
average HR of 156 bpm - that's a solid effort! Your RHR has been averaging
46 bpm this week (baseline), which shows good recovery capacity. However,
you only got 6.2 hours of sleep last night.

Recovery recommendations:
- Mobility: 20-min gentle hip/leg recovery routine (avoiding aggressive stretching)
- Nutrition: Prioritize protein and carbs within next 2 hours
- Hydration: Monitor throughout day
- Tomorrow: Easy 30-40 min recovery run (10:30-11:00/mi, HR <135)
- Monitor RHR tomorrow morning - if elevated, consider rest instead"
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
- **Activities**: Synced immediately after upload to Garmin Connect
- **Sleep**: Usually available next morning (requires compatible Garmin device)
- **VO2 Max**: Calculated by Garmin from GPS runs with HR data
- **Weight**: Manual entry in Garmin Connect or compatible scale
- **Resting HR**: Calculated daily by Garmin device

**Data Latency**: Most recent data is typically available within minutes of syncing with Garmin Connect mobile app or uploading from device.

---

For full technical details, see: **`docs/HEALTH_DATA_SYSTEM.md`**
