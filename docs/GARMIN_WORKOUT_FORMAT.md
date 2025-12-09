# Garmin Workout JSON Format

Complete reference for creating structured workouts that can be uploaded to Garmin Connect.

**Source:** Documented from garmin-connect-mcp-client and Garmin Connect API analysis.

## Table of Contents

- [Root Structure](#root-structure)
- [Step Types](#step-types)
- [Type Mappings](#type-mappings)
- [Pace Zone Conversion](#pace-zone-conversion)
- [Duration and Distance Calculations](#duration-and-distance-calculations)
- [Composition Rules](#composition-rules)
- [Common Errors to Avoid](#common-errors-to-avoid)
- [Complete Examples](#complete-examples)

---

## Root Structure

Every workout must start with this structure:

```json
{
  "workoutName": "YYYY-MM-DD - Workout Name",
  "sportType": {
    "sportTypeId": 1,
    "sportTypeKey": "running",
    "displayOrder": 1
  },
  "author": {},
  "estimatedDurationInSecs": 3600,
  "workoutSegments": [
    {
      "segmentOrder": 1,
      "sportType": {
        "sportTypeId": 1,
        "sportTypeKey": "running",
        "displayOrder": 1
      },
      "workoutSteps": [...]
    }
  ]
}
```

**Required Fields:**
- `workoutName` - Display name for the workout
- `sportType` - Sport type object (running, cycling, etc.)
- `workoutSegments` - Array containing workout segments (usually just one)

**Optional Fields:**
- `author` - Empty object or author info
- `estimatedDurationInSecs` - Total estimated duration (sum of all executable steps including repetitions)

---

## Step Types

### ExecutableStepDTO (Single Step)

Used for warmup, cooldown, intervals, recovery - any single, non-repeating step.

```json
{
  "type": "ExecutableStepDTO",
  "stepOrder": 1,
  "stepType": {
    "stepTypeId": 1,
    "stepTypeKey": "warmup",
    "displayOrder": 1
  },
  "endCondition": {
    "conditionTypeId": 2,
    "conditionTypeKey": "time",
    "displayOrder": 2,
    "displayable": true
  },
  "endConditionValue": 900,
  "targetType": {
    "workoutTargetTypeId": 1,
    "workoutTargetTypeKey": "no.target",
    "displayOrder": 1
  },
  "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
  "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
  "numberOfIterations": 1,
  "workoutSteps": [],
  "smartRepeat": false
}
```

**Key Rules for ExecutableStepDTO:**
- `numberOfIterations` must be 1
- `workoutSteps` must be empty array
- `smartRepeat` must be false
- **FORBIDDEN:** Setting `numberOfIterations != 1`, adding child steps, or `smartRepeat=true`

### RepeatGroupDTO (Repeating Intervals)

Used for interval sessions like "10x(400m @ 5K pace + 90s recovery)".

```json
{
  "type": "RepeatGroupDTO",
  "stepOrder": 2,
  "stepType": {
    "stepTypeId": 6,
    "stepTypeKey": "repeat",
    "displayOrder": 6
  },
  "numberOfIterations": 10,
  "endCondition": {
    "conditionTypeId": 7,
    "conditionTypeKey": "iterations",
    "displayOrder": 7,
    "displayable": false
  },
  "endConditionValue": 10,
  "targetType": {
    "workoutTargetTypeId": 1,
    "workoutTargetTypeKey": "no.target",
    "displayOrder": 1
  },
  "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
  "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
  "smartRepeat": false,
  "workoutSteps": [
    {
      "type": "ExecutableStepDTO",
      "stepOrder": 1,
      "stepType": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
      "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance", "displayOrder": 3, "displayable": true},
      "endConditionValue": 400,
      ...
    },
    {
      "type": "ExecutableStepDTO",
      "stepOrder": 2,
      "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
      "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
      "endConditionValue": 90,
      ...
    }
  ]
}
```

**Key Rules for RepeatGroupDTO:**
- `stepType` must be "repeat" (id=6)
- `endCondition` must be "iterations" (id=7)
- `numberOfIterations` = number of repeats (must be >= 1)
- `workoutSteps` contains child steps to repeat
- **FORBIDDEN:** Setting `targetValueOne`, `targetValueTwo` on the repeat group itself

---

## Type Mappings

### Step Types

| stepTypeKey | stepTypeId | displayOrder | Usage |
|-------------|------------|--------------|-------|
| `warmup` | 1 | 1 | Warmup phase |
| `cooldown` | 2 | 2 | Cooldown phase |
| `interval` | 3 | 3 | Fast interval/work period |
| `recovery` | 4 | 4 | Recovery/rest period |
| `repeat` | 6 | 6 | Repeat group container |

### End Conditions

| conditionTypeKey | conditionTypeId | displayOrder | displayable | Unit |
|------------------|-----------------|--------------|-------------|------|
| `time` | 2 | 2 | true | Seconds |
| `distance` | 3 | 3 | true | Meters |
| `iterations` | 7 | 7 | false | Count (for RepeatGroupDTO) |

### Target Types

| workoutTargetTypeKey | workoutTargetTypeId | displayOrder | Description |
|---------------------|---------------------|--------------|-------------|
| `no.target` | 1 | 1 | No specific target/easy effort |
| `pace.zone` | 6 | 6 | Pace target in min/km (shows as min/km on watch) |

**Important:** Use `pace.zone` if you want pace displayed as min/km. Do NOT use `speed.zone`.

### Sport Types

| sportTypeKey | sportTypeId | displayOrder |
|--------------|-------------|--------------|
| `running` | 1 | 1 |
| `cycling` | 2 | 2 |
| `swimming` | 3 | 3 |

---

## Pace Zone Conversion

**CRITICAL:** Garmin stores pace targets in meters/second (m/s), but you input them as min/km.

### Conversion Formula

For any pace in "m:ss/km" format (e.g., 3:50/km):

1. **Parse:** `minutes = 3`, `seconds = 50`
2. **Calculate total seconds:** `paceSec = (minutes × 60) + seconds = 230`
3. **Validate range:** If `paceSec < 60` or `paceSec > 420`, use `no.target` instead
4. **Create ±5s tolerance band:**
   - `slowerSec = paceSec + 5 = 235` (slower pace)
   - `fasterSec = paceSec - 5 = 225` (faster pace)
5. **Convert to m/s:**
   - `slowerMs = 1000 / slowerSec = 1000 / 235 = 4.255` (slower = lower m/s)
   - `fasterMs = 1000 / fasterSec = 1000 / 225 = 4.444` (faster = higher m/s)
6. **Apply to workout:**
   - `targetValueOne = slowerMs = 4.255` (SLOWER bound - lower m/s)
   - `targetValueTwo = fasterMs = 4.444` (FASTER bound - higher m/s)

**CRITICAL RULE:** `targetValueOne` < `targetValueTwo` (targetValueOne is SLOWER pace = lower m/s value)

### Example: 5:00/km pace

```
paceSec = 300 seconds
slowerSec = 305 (5:05/km - slower)
fasterSec = 295 (4:55/km - faster)
slowerMs = 1000/305 = 3.279 m/s (lower value)
fasterMs = 1000/295 = 3.390 m/s (higher value)

JSON:
{
  "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone", "displayOrder": 6},
  "targetValueOne": 3.279,  // SLOWER (lower m/s)
  "targetValueTwo": 3.390,  // FASTER (higher m/s)
  "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
  "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0}
}
```

**Note:** Do NOT include `zoneNumber` field - it causes Garmin to use predefined zones instead of custom pace values.

### Pace Target Rules

- **Never** set pace target on warmup (use `no.target`)
- **Never** set pace target on recovery (use `no.target`)
- **Never** set pace target on cooldown (use `no.target`)
- **Never** set pace target on RepeatGroupDTO level (only on child steps)
- **Never** include `zoneNumber` field for custom pace targets (causes Garmin to ignore custom values)
- **Never** include `targetValueUnit` field (should be omitted entirely)

---

## Duration and Distance Calculations

### Units

- **Time:** Seconds
- **Distance:** Meters

### Estimated Duration Calculation

`estimatedDurationInSecs` must equal the sum of ALL executable step durations, including repetitions.

**For time-based steps:** Use `endConditionValue` directly

**For distance-based steps with pace target:**
```
estimated_duration = distance_meters / average_pace_ms
average_pace_ms = (targetValueOne + targetValueTwo) / 2
```

**Example:**
```
Warmup: 900s (15 min)
+ RepeatGroupDTO 10x:
    - 400m interval @ 3.390-3.279 m/s avg = 400/3.335 = 120s
    - 90s recovery
    = 10 × (120 + 90) = 2100s
+ Cooldown: 600s (10 min)
= 900 + 2100 + 600 = 3600s total
```

---

## Composition Rules

### Workout Type Guidelines

**Interval/VMA/Hills workouts:**
- Require at least one `RepeatGroupDTO`
- Example: "10x(400m @ 5K pace + 90s recovery)"

**Tempo/Endurance/Easy/Long Run workouts:**
- No `RepeatGroupDTO` needed
- Only `ExecutableStepDTO` steps
- Example: "15 min warmup + 40 min @ tempo pace + 10 min cooldown"

### Default Phases

If not specified:
- **Warmup:** 300s (5 minutes)
- **Cooldown:** 300s (5 minutes)

### Common Patterns

**"10x(30/30)" - Fartlek:**
```json
{
  "type": "RepeatGroupDTO",
  "numberOfIterations": 10,
  "workoutSteps": [
    {
      "type": "ExecutableStepDTO",
      "stepType": "interval",
      "endConditionValue": 30,
      ...
    },
    {
      "type": "ExecutableStepDTO",
      "stepType": "recovery",
      "endConditionValue": 30,
      ...
    }
  ]
}
```

**"2 sets of 10x(30/30) with 3 min rest between sets:"**
```
ExecutableStepDTO (warmup)
+ RepeatGroupDTO (10 iterations of 30/30)
+ ExecutableStepDTO (180s recovery)
+ RepeatGroupDTO (10 iterations of 30/30)
+ ExecutableStepDTO (cooldown)
```

**"Strides" (Lignes droites):**
```
RepeatGroupDTO (3 iterations):
  - 100m interval (no pace target)
  - 45s recovery
```

---

## Common Errors to Avoid

### DO NOT Include Auto-Generated IDs

Garmin generates these automatically:
- ❌ `workoutId`
- ❌ `ownerId`
- ❌ `stepId`
- ❌ `childStepId`

Use `auto_clean=true` in the uploader to remove these automatically.

### Structure Mistakes

- ❌ **DO NOT** wrap workout in an array: `[{workout}]`
- ❌ **DO NOT** wrap in an "output" object: `{"output": {workout}}`
- ✅ **DO** send the workout object directly: `{workoutName: ..., sportType: ...}`

### Field Mistakes

- ❌ **DO NOT** use "kind" field (doesn't exist)
- ❌ **DO NOT** omit required IDs (include `stepTypeId`, `conditionTypeId`, etc., not just keys)
- ❌ **DO NOT** set `targetValueOne < targetValueTwo` for pace zones

### Logical Mistakes

- ❌ Setting pace targets on warmup/cooldown/recovery
- ❌ Setting pace targets on RepeatGroupDTO level
- ❌ Using `speed.zone` when you want min/km display (use `pace.zone`)
- ❌ Forgetting to include all step durations in `estimatedDurationInSecs`

---

## Complete Examples

### Example 1: Simple Tempo Run

```json
{
  "workoutName": "2025-01-15 - Tempo Run 40min",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
  "author": {},
  "estimatedDurationInSecs": 3300,
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
    "workoutSteps": [
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 1,
        "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
        "endConditionValue": 900,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "numberOfIterations": 1,
        "workoutSteps": [],
        "smartRepeat": false
      },
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 2,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
        "endConditionValue": 2400,
        "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone", "displayOrder": 6},
        "targetValueOne": 3.390,
        "targetValueTwo": 3.279,
        "targetValueUnit": null,
        "zoneNumber": 1,
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "numberOfIterations": 1,
        "workoutSteps": [],
        "smartRepeat": false
      },
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 3,
        "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
        "endConditionValue": 600,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "numberOfIterations": 1,
        "workoutSteps": [],
        "smartRepeat": false
      }
    ]
  }]
}
```

### Example 2: Interval Workout (8x400m)

```json
{
  "workoutName": "2025-01-16 - 8x400m @ 5K Pace",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
  "author": {},
  "estimatedDurationInSecs": 2640,
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
    "workoutSteps": [
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 1,
        "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
        "endConditionValue": 600,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "numberOfIterations": 1,
        "workoutSteps": [],
        "smartRepeat": false
      },
      {
        "type": "RepeatGroupDTO",
        "stepOrder": 2,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
        "numberOfIterations": 8,
        "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations", "displayOrder": 7, "displayable": false},
        "endConditionValue": 8,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "smartRepeat": false,
        "workoutSteps": [
          {
            "type": "ExecutableStepDTO",
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance", "displayOrder": 3, "displayable": true},
            "endConditionValue": 400,
            "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone", "displayOrder": 6},
            "targetValueOne": 4.444,
            "targetValueTwo": 4.255,
            "targetValueUnit": null,
            "zoneNumber": 1,
            "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
            "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
            "numberOfIterations": 1,
            "workoutSteps": [],
            "smartRepeat": false
          },
          {
            "type": "ExecutableStepDTO",
            "stepOrder": 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
            "endConditionValue": 90,
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
            "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
            "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
            "numberOfIterations": 1,
            "workoutSteps": [],
            "smartRepeat": false
          }
        ]
      },
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 3,
        "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": true},
        "endConditionValue": 600,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "numberOfIterations": 1,
        "workoutSteps": [],
        "smartRepeat": false
      }
    ]
  }]
}
```

---

## Automatic Workout Generation

The system can automatically generate Garmin workouts from FinalSurge coach descriptions using `src/auto_workout_generator.py` and `src/workout_parser.py`.

### Supported Coach Formats

| Format | Example | Generated Structure |
|--------|---------|---------------------|
| Simple run | `30 min E` | Single interval step with pace |
| Easy + strides | `60 min E + 3x20 sec strides @ 5k on 40 sec recovery` | Easy interval + RepeatGroupDTO |
| Tempo | `20 min warm up 25 min @ tempo 20 min warm down` | Warmup + Tempo interval + Cooldown |
| Tempo intervals | `20 min warm up 5x5 min @ tempo on 1 min recovery 20 min warm down` | Warmup + RepeatGroupDTO + Cooldown |
| Mixed pace | `30 min E 30 min M 30 min E` | Sequential interval steps |

### Pace Mappings (Coach → Garmin m/s)

Paces are converted from coach-prescribed mile paces to Garmin's meters/second format:

| Pace Type | Mile Pace | m/s Range |
|-----------|-----------|-----------|
| Easy (E) | 10:00-11:10 | 2.402-2.681 |
| Marathon (M) | 9:05-9:15 | 2.899-2.954 |
| Tempo (T) | 8:30-8:40 | 3.095-3.156 |
| 5K | 7:55-8:05 | 3.318-3.387 |

### Auto-Generation Commands

```bash
# Preview what would be generated
python3 src/auto_workout_generator.py --check-only

# Generate and upload all new workouts
python3 src/auto_workout_generator.py

# Runs automatically during sync
bash bin/sync_garmin_data.sh
```

---

## References

- **MCP Server Documentation:** [garmin-connect-mcp-client](https://github.com/Mart1M/garmin-connect-mcp-client)
- **Python Library:** [garminconnect](https://github.com/cyberjunky/python-garminconnect)
- **Workout Uploader:** `src/workout_uploader.py`
- **Workout Parser:** `src/workout_parser.py`
- **Auto Generator:** `src/auto_workout_generator.py`

## Usage

```bash
# Upload a workout from JSON file
bash bin/upload_workout.sh path/to/workout.json

# Or use Python directly
python3 src/workout_uploader.py path/to/workout.json

# Auto-generate from FinalSurge
python3 src/auto_workout_generator.py
```
