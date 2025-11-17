# Workout Library Schema

## Overview

The workout library is a searchable database of workouts and training blocks across all coaching domains (running, strength, mobility, nutrition). Each workout is stored as a structured JSON object with metadata for filtering and searching.

## Data Structure

### Workout Object

```json
{
  "id": "unique_workout_id",
  "name": "Workout Name",
  "domain": "running|strength|mobility|nutrition",
  "type": "workout_type",
  "description": "Brief description of the workout",
  "tags": ["tag1", "tag2", "tag3"],
  "difficulty": "beginner|intermediate|advanced|elite",
  "duration_minutes": 60,
  "equipment": ["equipment1", "equipment2"],
  "created_date": "2025-11-17",
  "modified_date": "2025-11-17",
  "training_phase": "base|quality|race_specific|taper|recovery",
  "vdot_range": [40, 50],
  "content": {
    // Domain-specific workout details
  }
}
```

### Domain-Specific Content Structures

#### Running Workouts

```json
{
  "domain": "running",
  "type": "intervals|tempo|easy|long_run|recovery|race_pace",
  "content": {
    "warmup": {
      "duration_minutes": 15,
      "description": "Easy jog",
      "pace": "easy"
    },
    "main_set": [
      {
        "repetitions": 8,
        "work_duration": "3:00",
        "work_pace": "T",
        "recovery_duration": "1:00",
        "recovery_type": "jog|walk|rest",
        "description": "800m repeats at threshold pace"
      }
    ],
    "cooldown": {
      "duration_minutes": 10,
      "description": "Easy jog",
      "pace": "easy"
    },
    "total_duration_minutes": 60,
    "total_distance_miles": 8.0,
    "estimated_tss": 85
  }
}
```

#### Strength Workouts

```json
{
  "domain": "strength",
  "type": "foundation|power|maintenance|pre_run|post_run",
  "content": {
    "warmup": {
      "duration_minutes": 5,
      "exercises": ["dynamic_stretching", "activation_drills"]
    },
    "circuits": [
      {
        "name": "Lower Body Power",
        "rounds": 3,
        "exercises": [
          {
            "name": "Bulgarian Split Squat",
            "sets": 3,
            "reps": "8-10 per leg",
            "rest_seconds": 90,
            "equipment": ["dumbbells", "bench"],
            "notes": "Focus on controlled eccentric"
          }
        ]
      }
    ],
    "cooldown": {
      "duration_minutes": 5,
      "exercises": ["static_stretching"]
    },
    "total_duration_minutes": 45,
    "focus_areas": ["glutes", "hamstrings", "core"]
  }
}
```

#### Mobility Workouts

```json
{
  "domain": "mobility",
  "type": "dynamic|static|recovery|pre_run|post_run|maintenance",
  "content": {
    "timing": "pre_workout|post_workout|standalone",
    "sequences": [
      {
        "name": "Hip Mobility Series",
        "exercises": [
          {
            "name": "90/90 Hip Stretch",
            "duration_seconds": 60,
            "repetitions": null,
            "per_side": true,
            "equipment": ["mat"],
            "notes": "Focus on square hips, upright posture"
          }
        ]
      }
    ],
    "total_duration_minutes": 20,
    "focus_areas": ["hips", "ankles", "thoracic_spine"]
  }
}
```

#### Nutrition Plans

```json
{
  "domain": "nutrition",
  "type": "daily_plan|race_day|long_run|recovery|pre_workout|during_workout|post_workout",
  "content": {
    "timing": "specific timing context",
    "meals": [
      {
        "name": "Pre-Long Run Breakfast",
        "timing": "-2 to -3 hours before run",
        "foods": [
          {
            "item": "Gluten-free oatmeal",
            "quantity": "1 cup cooked",
            "macros": {
              "calories": 150,
              "carbs_g": 27,
              "protein_g": 5,
              "fat_g": 3
            }
          }
        ],
        "total_macros": {
          "calories": 450,
          "carbs_g": 75,
          "protein_g": 15,
          "fat_g": 10
        },
        "dietary_constraints": ["gluten_free", "dairy_free"],
        "notes": "Easy to digest, minimal fiber"
      }
    ],
    "hydration": {
      "pre": "16-20 oz water",
      "during": "6-8 oz every 15-20 min",
      "post": "16-24 oz per lb lost"
    }
  }
}
```

### Training Block Object

For multi-day or multi-week structured programs:

```json
{
  "id": "unique_block_id",
  "name": "Training Block Name",
  "type": "training_block",
  "domain": "multi_domain",
  "description": "Description of the training block",
  "tags": ["tag1", "tag2"],
  "difficulty": "intermediate",
  "duration_weeks": 4,
  "training_phase": "base",
  "created_date": "2025-11-17",
  "workouts": [
    {
      "week": 1,
      "day": 1,
      "workout_id": "workout_id_reference",
      "notes": "Week 1 focuses on foundation"
    }
  ]
}
```

## Metadata Tags

### Common Tags
- Target race distance: `5k`, `10k`, `half_marathon`, `marathon`, `ultra`
- Training phase: `base_building`, `early_quality`, `race_specific`, `taper`, `recovery`
- Workout focus: `speed`, `endurance`, `tempo`, `hills`, `track`, `trail`
- Difficulty: `beginner`, `intermediate`, `advanced`, `elite`

### Running-Specific Tags
- `intervals`, `threshold`, `easy_run`, `long_run`, `recovery`, `race_pace`
- `track_workout`, `hill_workout`, `fartlek`, `progression_run`
- `vo2_max`, `lactate_threshold`, `aerobic_development`

### Strength-Specific Tags
- `lower_body`, `upper_body`, `core`, `full_body`
- `explosive_power`, `strength_endurance`, `hypertrophy`, `stabilization`
- `injury_prevention`, `running_economy`

### Mobility-Specific Tags
- `hip_mobility`, `ankle_mobility`, `thoracic_mobility`
- `dynamic_stretching`, `static_stretching`, `foam_rolling`
- `pre_run`, `post_run`, `recovery_day`

### Nutrition-Specific Tags
- `race_nutrition`, `long_run_fueling`, `recovery_meal`
- `gluten_free`, `dairy_free`, `vegan`, `vegetarian`
- `carb_loading`, `protein_focus`, `anti_inflammatory`

## Search & Filter Capabilities

### Search Fields
- Full-text search on: name, description, notes
- Tag matching (exact or partial)
- Domain filtering
- Type filtering
- Difficulty level
- Duration range
- Training phase
- VDOT range (for running workouts)
- Equipment availability

### Sort Options
- Created date (newest/oldest)
- Modified date (newest/oldest)
- Duration (shortest/longest)
- Difficulty (easiest/hardest)
- Name (alphabetical)
- Relevance (search results)

## File Structure

```
data/library/
├── workouts/
│   ├── running/
│   │   ├── intervals/
│   │   ├── tempo/
│   │   ├── long_runs/
│   │   └── recovery/
│   ├── strength/
│   │   ├── foundation/
│   │   ├── power/
│   │   └── maintenance/
│   ├── mobility/
│   │   ├── pre_run/
│   │   ├── post_run/
│   │   └── recovery/
│   └── nutrition/
│       ├── daily_plans/
│       ├── race_day/
│       └── workout_fueling/
├── blocks/
│   └── training_blocks/
└── workout_library.json  # Main index file
```

## Usage Examples

### Search Examples

```python
# Find all threshold workouts for VDOT 45-50
search(domain="running", type="tempo", vdot_range=[45, 50])

# Find beginner strength workouts with minimal equipment
search(domain="strength", difficulty="beginner", equipment=["bodyweight", "mat"])

# Find post-run mobility routines under 15 minutes
search(domain="mobility", tags=["post_run"], duration_max=15)

# Find race day nutrition plans that are gluten-free
search(domain="nutrition", type="race_day", tags=["gluten_free"])
```

### Integration with Coaching Agents

Agents can:
1. Search library for appropriate workouts based on athlete context
2. Customize workouts from templates using athlete's VDOT and preferences
3. Combine workouts into training blocks
4. Save new workout variations back to library
5. Track which workouts athlete has completed
