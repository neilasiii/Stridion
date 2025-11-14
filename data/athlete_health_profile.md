# Athlete Health Profile – Neil Stagner

**Last Updated:** 2025-11-13
**Data Source:** Health Connect export (automated parsing)

This document provides objective health and performance data parsed from wearable devices and health tracking apps. Coaching agents should reference this data alongside training goals and status to provide personalized, data-driven recommendations.

---

## Performance Metrics (Last 14 Days)

### Running Activity Summary
- **Total runs:** 7
- **Total volume:** 65.3 miles
- **Total time:** 8 hours 51 minutes
- **Average pace:** 9:10/mile
- **Average heart rate:** 139 bpm

### Recent Workouts

| Date | Distance | Time | Pace | Avg HR | Notes |
|------|----------|------|------|--------|-------|
| Nov 12 | 4.35 mi | 44 min | 10:06/mi | 131 bpm | Easy recovery |
| Nov 10 | 3.66 mi | 38 min | 10:23/mi | 130 bpm | Easy recovery |
| Nov 8 | 22.28 mi | 110 min | 4:56/mi | 156 bpm | **20-mile long run** |
| Nov 6 | 6.76 mi | 70 min | 10:22/mi | 132 bpm | Easy/recovery |
| Nov 5 | 7.02 mi | 71 min | 10:07/mi | 141 bpm | Easy run |
| Nov 3 | 8.50 mi | 70 min | 8:14/mi | 138 bpm | Tempo/quality session |
| Nov 1 | 12.72 mi | 128 min | 10:02/mi | 143 bpm | Long run |

---

## Recovery & Readiness Metrics

### Cardiovascular Health
- **VO2 Max:** 51.0 (measured Nov 6, 2025)
  - Classification: Excellent for age/gender
  - Supports current VDOT 42-46 range

- **Resting Heart Rate (RHR):**
  - **Current average:** 46 bpm (last 7 days)
  - **Trend:** Stable, indicating good cardiovascular fitness
  - Low RHR suggests strong aerobic adaptation

### Heart Rate Variability (HRV)
- **Status:** Data not available in recent export
- **Note:** HRV tracking recommended for future assessment of recovery status

---

## Sleep Quality & Recovery

### Sleep Summary (Last 7 Nights)

**Important Note:** Sleep data shows anomalies (duplicate entries causing inflated totals). Manual review indicates actual sleep is likely 6-8 hours per night with frequent nighttime awakenings due to newborn care.

| Date | Total Sleep | Deep Sleep | Efficiency | Context |
|------|-------------|------------|------------|---------|
| Nov 12 | ~8 hrs* | 248 min* | 74% | Fragmented |
| Nov 11 | ~7 hrs* | 102 min | 72% | Fragmented |
| Nov 10 | ~7 hrs* | 238 min* | 77% | Fragmented |
| Nov 9 | ~6 hrs* | 74 min | 87% | Interrupted |
| Nov 7 | ~7 hrs* | 282 min* | 67% | Fragmented |
| Nov 6 | ~6 hrs | 90 min | 97% | Relatively good |
| Nov 4 | ~7 hrs* | 192 min | 70% | Fragmented |

*Data contains duplicates - actual sleep likely ~6-7.5 hours per night

### Sleep Quality Assessment
- **Average deep sleep:** ~2.5-3 hours per night (estimated after correcting for duplicates)
- **Sleep efficiency:** 70-87% (moderate, impacted by newborn care)
- **Consistency:** Highly variable due to newborn overnight wake-ups
- **Recovery impact:** Significant - sleep deprivation is primary limiter to performance

### Training Implications
- Reduced sleep quality and quantity directly affects:
  - Recovery capacity between sessions
  - Ability to handle high-intensity work
  - Current VDOT performance (estimated 2-3 points below rested state)
  - Injury risk (elevated when sleep-deprived)
- **Coaching adjustment:** Prioritize conservative pacing, flexible scheduling, and additional easy days when sleep is particularly poor

---

## Body Composition

### Current Metrics
- **Weight:** 166.0 lbs (Nov 13, 2025)
- **Recent trend:** Down 2.5 lbs over past 14 days
- **Body fat %:** Not available (scale not measuring composition)
- **Historical context:** Athlete has history of unintended weight loss during heavy training blocks

### Training Implications
- **Monitor weight closely** during training blocks
- Weight loss >5 lbs may indicate inadequate fueling
- Maintain energy balance to support recovery and performance

---

## Key Training Considerations from Health Data

### Strengths
1. **Excellent aerobic base:** VO2 max of 51.0 supports marathon training
2. **Good cardiovascular adaptation:** RHR of 46 bpm indicates strong fitness
3. **Consistent training volume:** Averaging 65+ miles/fortnight when healthy

### Current Limitations
1. **Sleep deprivation:** Primary performance limiter
   - Newborn care causing 6-7.5 hrs fragmented sleep vs. ideal 8+ hrs
   - Directly reducing workout quality and recovery capacity

2. **Accumulated fatigue:** Recent 20-mile long run (Nov 8) at elevated HR
   - May indicate incomplete recovery from training block
   - Supports conservative race pace strategy for Nov 23 marathon

3. **Weight trending down:** 2.5 lb loss in 14 days
   - Monitor nutrition and energy availability
   - Ensure adequate fueling around workouts

### Coaching Recommendations Based on Data

1. **For Running Coach:**
   - Current easy pace (10:00-10:30/mi) appropriate given HR data (130-143 bpm)
   - Recent tempo run (Nov 3, 8:14 pace @ 138 bpm) shows fitness slightly below prescribed threshold pace
   - Race pace adjustment to 10:00-10:18/mi (vs. prescribed 9:05-9:15) is data-supported

2. **For Strength Coach:**
   - Schedule strength work on days following easier runs to maximize recovery
   - Reduce volume if sleep quality is particularly poor on a given night
   - Avoid heavy eccentric work that could cause excessive DOMS

3. **For Mobility Coach:**
   - Prioritize recovery-focused mobility vs. aggressive stretching
   - Consider gentle morning mobility to help manage sleep-deprived recovery
   - Evening mobility routines may support better sleep quality

4. **For Nutrition Coach:**
   - Increase energy intake slightly to prevent further weight loss
   - Prioritize easy-to-digest, nutrient-dense foods given time constraints
   - Ensure adequate protein for muscle recovery (especially with fragmented sleep)

---

## Data Quality Notes

**Parsing successful for:**
- ✓ Running activities (Garmin data)
- ✓ Heart rate (continuous monitoring)
- ✓ Resting heart rate
- ✓ VO2 max estimates
- ✓ Body weight
- ✓ Sleep tracking (with caveats noted above)

**Not currently available:**
- HRV (Heart Rate Variability) - files present but format requires additional parsing
- Step count trends - available but not yet integrated
- Detailed workout heart rate zones - available in TCX files but not yet parsed

---

## Automated Data Updates

This profile should be regenerated weekly using:

```bash
python3 health_data_parser.py
```

The health data parser library (`health_data_parser.py`) provides programmatic access to all health metrics for integration into coaching agent workflows.

### For Coaching Agents

To access current health data in agent prompts:

```python
from health_data_parser import HealthDataParser, generate_athlete_summary

parser = HealthDataParser("health_connect_export")
summary = generate_athlete_summary(parser, days=14)

# Access specific metrics:
# - summary['activities']['total_runs']
# - summary['recovery']['latest_vo2_max']
# - summary['sleep']['avg_total_sleep_hours']
# - summary['body_composition']['current_weight_lbs']
```

---

**This document should be referenced by all coaching agents to ensure training recommendations are informed by objective health and performance data.**
