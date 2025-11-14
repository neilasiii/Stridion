# Health Data System Documentation

## Overview

This system provides automated parsing and incremental updating of health data from wearable devices (Garmin, Health Connect) to inform coaching decisions with objective metrics.

---

## For Coaching Agents

### When to Check Health Data

Coaching agents should check for new health data when:
1. Beginning a coaching session
2. User mentions completing a workout
3. User uploads new health data
4. Making recovery-based recommendations
5. Adjusting training based on fatigue/readiness

### How to Check for New Data

**Simple Method (Recommended for Agents):**

```bash
bash bin/check_health_data.sh
```

This will:
- Check for new health data files
- Update the cache with any new data
- Display a 14-day summary

**Manual Python Method:**

```bash
# Just update without output
python3 src/update_health_data.py --quiet

# Update and show summary
python3 src/update_health_data.py --summary --days 14

# Only check if new data exists (no update)
python3 src/update_health_data.py --check-only
```

### Accessing Health Data in Agent Prompts

The health data cache is stored in: `data/health/health_data_cache.json`

This JSON file contains:
- **activities**: All parsed workouts with pace, HR, distance
- **sleep_sessions**: Nightly sleep with stages and efficiency
- **vo2_max_readings**: VO2 max estimates
- **weight_readings**: Body weight trends
- **resting_hr_readings**: Daily resting heart rate
- **last_updated**: Timestamp of last cache update

**Example: Read recent activities**

```python
import json
with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Get last 5 runs
recent_runs = [a for a in cache['activities'] if a['activity_type'] == 'RUNNING'][:5]

for run in recent_runs:
    print(f"{run['date']}: {run['distance_miles']:.1f} mi @ {run['avg_heart_rate']} bpm avg HR")
```

**Example: Check recovery status**

```python
import json
with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Check recent RHR trend
recent_rhr = cache['resting_hr_readings'][:7]  # Last 7 days
avg_rhr = sum(r[1] for r in recent_rhr) / len(recent_rhr)

if avg_rhr > 48:
    print("RHR elevated - consider recovery day")
```

---

## System Architecture

### Components

1. **`health_data_parser.py`**: Core parsing library
   - Parses CSV/TCX/FIT files from Health Connect export
   - Provides data classes for Activities, Sleep, VO2 max, etc.

2. **`update_health_data.py`**: Incremental update script
   - Tracks file modification times
   - Only processes new/changed files
   - Updates `data/health/health_data_cache.json`

3. **`check_health_data.sh`**: Simple wrapper for agents
   - One command to update and view summary

4. **`data/health/health_data_cache.json`**: Persistent cache
   - Stores all parsed health data
   - Updated incrementally (no reprocessing)
   - Sorted newest-first

### Data Flow

```
Health Connect Export (CSVs)
           ↓
  health_data_parser.py (reads files)
           ↓
  update_health_data.py (incremental update)
           ↓
  data/health/health_data_cache.json (persistent storage)
           ↓
  Coaching Agents (read JSON for decisions)
```

---

## For Users: Updating Health Data

### Step 1: Export Data from Health Connect

1. Open Health Connect app on your phone
2. Navigate to Settings → Export Data
3. Select data types: Activities, Sleep, Heart Rate, VO2 Max, Weight
4. Export to file

### Step 2: Upload to health_connect_export/

Place the exported folder in the project's `health_connect_export/` directory:
```
<project-root>/health_connect_export/
```

The system expects this structure:
```
health_connect_export/
├── Health Sync Activities/
│   ├── RUNNING *.csv
│   ├── WALKING *.csv
│   └── *.tcx, *.gpx, *.fit files
├── Health Sync Sleep/
│   └── Sleep *.csv
├── Health Sync Heart rate/
│   ├── RHR *.csv
│   ├── HRV *.csv
│   └── Heart rate *.csv
├── Health Sync VO2 max/
│   └── VO2 max *.csv
└── Health Sync Weight/
    └── Weight *.csv
```

### Step 3: Run Update

```bash
python3 src/update_health_data.py
```

You should see output like:
```
✓ Health data updated! Added 15 new entries:
  • 3 new activities
  • 2 new sleep sessions
  • 1 new VO2 max readings
  • 2 new weight readings
  • 7 new resting HR readings

Cache updated: 2025-11-13 16:29:01
```

---

## Supported Data Types

### Activities
- **Sources**: Garmin CSV exports
- **Metrics**: Date, distance, duration, pace, avg HR, max HR, calories
- **Types**: Running, Walking
- **Note**: TCX/GPX files available but not yet parsed for detailed HR zones

### Sleep
- **Sources**: Health Connect sleep tracking
- **Metrics**: Total duration, light/deep/REM/awake minutes, efficiency %
- **Note**: Some duplicate data in exports - use date-level aggregates

### VO2 Max
- **Sources**: Garmin estimates
- **Metrics**: VO2 max value (ml/kg/min)
- **Frequency**: Updated after qualifying runs

### Weight
- **Sources**: Smart scale (via Health Connect)
- **Metrics**: Weight (lbs), body fat %, muscle % (when available)

### Resting Heart Rate (RHR)
- **Sources**: Wearable overnight tracking
- **Metrics**: Daily RHR (bpm)
- **Use**: Key recovery indicator - rising RHR = incomplete recovery

### Heart Rate Variability (HRV)
- **Status**: Files present but not fully parsed yet
- **Future**: Will provide additional recovery metric

---

## Coaching Integration Examples

### Example 1: Adjust Workout Based on RHR

```python
import json
from datetime import datetime, timedelta

with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Get RHR from last 3 days
recent_rhr = cache['resting_hr_readings'][:3]
avg_rhr_3d = sum(r[1] for r in recent_rhr) / 3

# Get baseline RHR (last 30 days)
baseline_rhr = cache['resting_hr_readings'][:30]
avg_rhr_baseline = sum(r[1] for r in baseline_rhr) / 30

# If RHR elevated by 5+ bpm, recommend easy day
if avg_rhr_3d > (avg_rhr_baseline + 5):
    print("⚠️ RHR elevated - recommend EASY run or rest day")
elif avg_rhr_3d > (avg_rhr_baseline + 3):
    print("⚠️ RHR slightly elevated - reduce intensity if planned hard session")
else:
    print("✓ RHR normal - proceed with scheduled workout")
```

### Example 2: Validate VDOT from Recent Runs

```python
import json

with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Get runs from last 7 days
recent_runs = [a for a in cache['activities']
               if a['activity_type'] == 'RUNNING'][:5]

# Check if athlete is running faster/slower than prescribed paces
for run in recent_runs:
    pace = run.get('pace_per_mile')
    hr = run.get('avg_heart_rate')

    if pace and hr:
        print(f"{run['date']}: {pace:.1f} min/mi @ {hr} bpm")

        # If easy runs (HR 120-140) are consistently > 10:30/mi
        # Current VDOT may be too high
        # If threshold runs (HR 145-160) are < 8:00/mi
        # Current VDOT may be too low
```

### Example 3: Sleep-Informed Workout Adjustment

```python
import json

with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

last_night = cache['sleep_sessions'][0]

total_sleep_hrs = last_night['total_duration_minutes'] / 60
deep_sleep_min = last_night['deep_sleep_minutes']
efficiency = last_night['sleep_efficiency']

if total_sleep_hrs < 6.0 or efficiency < 70:
    print("🛑 Poor sleep detected - strongly recommend EASY or REST")
elif total_sleep_hrs < 7.0 or deep_sleep_min < 60:
    print("⚠️ Suboptimal sleep - consider reducing intensity today")
else:
    print("✓ Good sleep quality - proceed with planned workout")
```

---

## Troubleshooting

### No Data Appearing After Update

1. Check file structure matches expected paths
2. Verify CSV files have correct headers
3. Run with verbose output: `python3 src/update_health_data.py`
4. Check `data/health/health_data_cache.json` for errors

### Duplicate Entries

- The system de-duplicates by timestamp
- If you re-export the same date range, it won't create duplicates
- File modification times are tracked to avoid reprocessing

### Old Data Not Clearing

- The cache is additive (never deletes old data)
- To reset: `rm data/health/health_data_cache.json && python3 src/update_health_data.py`

---

## Future Enhancements

1. **HRV Parsing**: Full HRV data integration for recovery tracking
2. **TCX Detail Parsing**: Second-by-second HR zones during workouts
3. **Automated Trends**: Weekly/monthly summary reports
4. **VDOT Calculator**: Automatic VDOT estimation from workout data
5. **Training Load Metrics**: TSS/ATL/CTL calculation
6. **Web Dashboard**: Visual trends and charts

---

## For Developers

### Adding New Data Types

1. Create parser in `health_data_parser.py`:
   ```python
   @dataclass
   class NewDataType:
       timestamp: datetime
       value: float
   ```

2. Add parsing method:
   ```python
   def parse_new_data(self, days: int = 30) -> List[NewDataType]:
       # Implementation
       pass
   ```

3. Update `update_health_data.py` to track new files

4. Add to cache structure in `IncrementalHealthDataManager`

### Running Tests

```bash
# Test parser directly
python3 src/health_data_parser.py

# Test incremental updates
python3 src/update_health_data.py --check-only
python3 src/update_health_data.py --summary
```

---

**Last Updated**: 2025-11-13
**Maintained By**: Neil Stagner
**For Support**: Check parse errors in `health_data_parser.py` or cache issues in `update_health_data.py`
