# Agent Workout Library Integration Guide

## Overview

The workout library provides a searchable database of pre-built workouts across all coaching domains (running, strength, mobility, nutrition). Agents can use this library to:

1. Find appropriate workouts based on athlete context
2. Customize workouts using athlete-specific paces and preferences
3. Suggest proven workout templates
4. Build training blocks from existing workouts

## Quick Start for Agents

### Using the Command-Line Interface

The easiest way to search the library is via the CLI:

```bash
# Search for threshold workouts
bash bin/workout_library.sh search --domain running --type tempo

# Find beginner workouts under 30 minutes
bash bin/workout_library.sh search --difficulty beginner --duration-max 30

# Find workouts for specific VDOT range
bash bin/workout_library.sh search --domain running --vdot-min 45 --vdot-max 55

# Get a specific workout by ID
bash bin/workout_library.sh get <workout-id>

# Show library statistics
bash bin/workout_library.sh stats
```

### Using the Python API

For more complex operations, use the Python API:

```python
from workout_library import WorkoutLibrary

# Initialize library
library = WorkoutLibrary()

# Search for workouts
results = library.search(
    domain="running",
    workout_type="tempo",
    vdot_range=[45, 55],
    training_phase="quality"
)

# Get a specific workout
workout = library.get_workout(workout_id)

# Add a new custom workout
new_workout_id = library.add_workout({
    "name": "Custom Threshold Session",
    "domain": "running",
    "type": "tempo",
    # ... rest of workout definition
})
```

## Integration Examples by Agent

### Running Coach (vdot-running-coach)

**When to use the library:**
- Athlete asks for a specific type of workout (intervals, tempo, long run)
- Need to suggest a proven workout template
- Creating a training plan and need variety
- Athlete asks "what's a good threshold workout?"

**Example workflow:**

```python
# User: "I need a good threshold workout for my marathon training"

# 1. Check athlete's current VDOT (from current_training_status.md)
vdot = 48

# 2. Search library for threshold workouts
from workout_library import WorkoutLibrary
library = WorkoutLibrary()

workouts = library.search(
    domain="running",
    workout_type="tempo",
    vdot_range=[vdot - 5, vdot + 5],
    training_phase="race_specific"
)

# 3. Select appropriate workout (e.g., Cruise Intervals)
workout = workouts[1]  # "Cruise Intervals - 5x1 Mile"

# 4. Customize paces based on athlete's VDOT
# Read athlete's training paces from current_training_status.md
threshold_pace = "7:45/mi"  # From VDOT table

# 5. Present customized workout
response = f"""
Based on your VDOT of {vdot}, I recommend this threshold workout:

**{workout['name']}**
{workout['description']}

Warmup: {workout['content']['warmup']['description']}
Main set: 5x1 mile at {threshold_pace} (T pace) with 1-minute jog recovery
Cooldown: {workout['content']['cooldown']['description']}

Total duration: ~{workout['duration_minutes']} minutes
"""
```

### Strength Coach (runner-strength-coach)

**When to use the library:**
- Athlete needs strength workout suggestions
- Planning a periodized strength program
- Athlete has limited equipment

**Example workflow:**

```python
# User: "What strength workout should I do today?"

# 1. Check athlete's training phase (from current_training_status.md)
training_phase = "base"

# 2. Check what equipment is available (from training_preferences.md)
available_equipment = ["dumbbells", "mat", "bench"]

# 3. Search library
workouts = library.search(
    domain="strength",
    training_phase=training_phase,
    equipment=available_equipment,
    difficulty="intermediate"
)

# 4. Select workout that doesn't conflict with running schedule
# (e.g., not heavy lower body before a long run)
workout = workouts[0]  # "Foundation Phase - Lower Body"

# 5. Present workout with any scaling needed
```

### Mobility Coach (mobility-coach-runner)

**When to use the library:**
- Athlete asks for pre-run or post-run routine
- Need specific mobility work for an area (hips, ankles)
- Athlete has limited time

**Example workflow:**

```python
# User: "I have 10 minutes before my run, what should I do?"

# 1. Search for short pre-run mobility work
workouts = library.search(
    domain="mobility",
    tags=["pre_run"],
    duration_max=10
)

# 2. Select and present
workout = workouts[0]  # "Pre-Run Dynamic Warm-Up"

# 3. Show the full sequence
```

### Nutrition Coach (endurance-nutrition-coach)

**When to use the library:**
- Athlete asks about fueling for a long run or race
- Need meal plan suggestions
- Athlete has dietary restrictions

**Example workflow:**

```python
# User: "What should I eat before my 20-mile long run?"

# 1. Search for long run fueling plans
workouts = library.search(
    domain="nutrition",
    workout_type="long_run",
    tags=["gluten_free", "dairy_free"]  # From training_preferences.md
)

# 2. Select appropriate plan
plan = workouts[0]  # "Marathon Long Run Fueling"

# 3. Present full nutrition strategy
# Show pre-run meal, during-run fueling, post-run recovery
```

## Common Search Patterns

### By Training Phase

```python
# Base building phase - easy runs and foundation work
workouts = library.search(training_phase="base")

# Quality phase - intervals and threshold
workouts = library.search(training_phase="quality")

# Race-specific phase - race pace work
workouts = library.search(training_phase="race_specific")

# Taper phase - reduced volume
workouts = library.search(training_phase="taper")
```

### By Duration

```python
# Short workouts (< 30 min)
workouts = library.search(duration_max=30)

# Medium workouts (30-60 min)
workouts = library.search(duration_min=30, duration_max=60)

# Long workouts (> 90 min)
workouts = library.search(duration_min=90)
```

### By Tags

```python
# Find VO2 max workouts
workouts = library.search(tags=["vo2_max"])

# Find injury prevention work
workouts = library.search(tags=["injury_prevention"])

# Find race-specific work
workouts = library.search(tags=["race_specific", "marathon"])
```

### By Equipment Availability

```python
# Bodyweight only
workouts = library.search(equipment=["bodyweight", "mat"])

# Home gym (dumbbells + bench)
workouts = library.search(equipment=["dumbbells", "bench", "mat"])

# Full gym access
workouts = library.search(equipment=["dumbbells", "barbell", "bench", "rack", "mat"])
```

## Customizing Workouts

When you find a workout from the library, always customize it based on:

1. **Athlete's VDOT** (for running workouts)
   - Calculate exact paces from VDOT tables in current_training_status.md
   - Adjust interval counts based on fitness level

2. **Athlete's Schedule** (from training_preferences.md)
   - Consider available time
   - Consider equipment availability
   - Consider upcoming hard workouts

3. **Athlete's Health Data** (from health_data_cache.json)
   - If RHR elevated, suggest easier variation
   - If sleep compromised, reduce intensity
   - If recovering from hard workout, suggest recovery variation

4. **Dietary Constraints** (from training_preferences.md)
   - Filter nutrition plans by gluten-free, dairy-free, etc.
   - Substitute ingredients as needed

## Creating New Workouts

Agents can add new workouts to the library:

```python
# After creating a custom workout that worked well
new_workout = {
    "name": "Custom Hill Repeats",
    "domain": "running",
    "type": "intervals",
    "description": "Short, steep hill repeats for power development",
    "tags": ["hills", "power", "strength"],
    "difficulty": "advanced",
    "duration_minutes": 50,
    "equipment": ["hills"],
    "training_phase": "quality",
    "vdot_range": [40, 65],
    "content": {
        # ... workout details
    }
}

workout_id = library.add_workout(new_workout)
print(f"Added new workout: {workout_id}")
```

## Best Practices

1. **Always search before creating** - Check if a similar workout exists first
2. **Customize to athlete** - Never just copy-paste; adapt to VDOT, schedule, preferences
3. **Reference the source** - Tell athlete "This is based on the Classic Yasso 800s workout"
4. **Explain the purpose** - Don't just prescribe; explain why this workout fits their goals
5. **Consider progression** - Use library to show progression (beginner → intermediate → advanced versions)
6. **Track what works** - Note which workouts the athlete responds well to
7. **Build variety** - Use library to ensure athlete isn't doing same workout repeatedly

## Command Reference

### Search Parameters

- `domain`: running | strength | mobility | nutrition
- `workout_type`: intervals | tempo | long_run | recovery | etc.
- `difficulty`: beginner | intermediate | advanced | elite
- `training_phase`: base | quality | race_specific | taper | recovery
- `tags`: List of tags (workout must have ALL)
- `duration_min`: Minimum duration in minutes
- `duration_max`: Maximum duration in minutes
- `vdot_range`: [min, max] VDOT range
- `equipment`: List of available equipment
- `query`: Text search in name and description
- `limit`: Max number of results

### CLI Commands

```bash
# List all workouts
bash bin/workout_library.sh list [--domain DOMAIN]

# Search with filters
bash bin/workout_library.sh search [OPTIONS]

# Get workout details
bash bin/workout_library.sh get WORKOUT_ID

# Show statistics
bash bin/workout_library.sh stats

# Export workout as JSON
bash bin/workout_library.sh export WORKOUT_ID [--output FILE]

# Import workout from JSON
bash bin/workout_library.sh import FILE

# Delete workout
bash bin/workout_library.sh delete WORKOUT_ID [--force]
```

## Example Agent Responses

### Good Response (Using Library)

> Based on your VDOT of 48 and upcoming marathon, I recommend the **Cruise Intervals - 5x1 Mile** workout from the library. This is a classic threshold workout that builds lactate clearance without the continuous fatigue of a tempo run.
>
> Here's your customized version:
> - Warmup: 15 min easy
> - Main: 5x1 mile at 7:45/mi (T pace) with 1-min jog recovery
> - Cooldown: 10 min easy
>
> This fits perfectly with your Tuesday morning schedule and won't interfere with your Saturday long run.

### Poor Response (Not Using Library)

> Do some intervals today. Maybe like 5x1 mile at threshold with short recovery? About an hour total.

## Troubleshooting

**No results found:**
- Broaden search criteria
- Remove restrictive filters (equipment, VDOT range)
- Search by domain only, then filter manually

**Too many results:**
- Add more specific filters (training_phase, difficulty, duration)
- Use tags to narrow focus
- Use query parameter for text search

**Workout doesn't fit athlete:**
- Customize the workout template
- Search for different difficulty level
- Create a new workout based on library template
