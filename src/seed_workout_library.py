#!/usr/bin/env python3
"""
Seed Workout Library

Populates the workout library with pre-built templates across all coaching domains.
"""

from workout_library import WorkoutLibrary


def seed_running_workouts(library: WorkoutLibrary):
    """Add running workout templates"""

    running_workouts = [
        # Interval Workouts
        {
            "name": "Classic Yasso 800s",
            "domain": "running",
            "type": "intervals",
            "description": "10x800m at 5K pace with equal recovery - marathon predictor workout",
            "tags": ["intervals", "track", "vo2_max", "marathon_training"],
            "difficulty": "intermediate",
            "duration_minutes": 75,
            "equipment": ["track"],
            "training_phase": "quality",
            "vdot_range": [35, 65],
            "content": {
                "warmup": {"duration_minutes": 20, "description": "Easy jog + strides", "pace": "easy"},
                "main_set": [
                    {
                        "repetitions": 10,
                        "work_duration": "800m",
                        "work_pace": "5K pace",
                        "recovery_duration": "equal time",
                        "recovery_type": "jog",
                        "description": "800m repeats - your time in min:sec predicts marathon time in hr:min"
                    }
                ],
                "cooldown": {"duration_minutes": 10, "description": "Easy jog", "pace": "easy"},
                "total_duration_minutes": 75,
                "estimated_tss": 95
            }
        },
        {
            "name": "VO2 Max Intervals - 5x1000m",
            "domain": "running",
            "type": "intervals",
            "description": "5x1000m at I pace with 2-3 minute recovery",
            "tags": ["intervals", "vo2_max", "track", "intensity"],
            "difficulty": "advanced",
            "duration_minutes": 60,
            "equipment": ["track"],
            "training_phase": "quality",
            "vdot_range": [40, 70],
            "content": {
                "warmup": {"duration_minutes": 15, "description": "Easy jog + drills", "pace": "easy"},
                "main_set": [
                    {
                        "repetitions": 5,
                        "work_duration": "1000m",
                        "work_pace": "I",
                        "recovery_duration": "2:30",
                        "recovery_type": "jog",
                        "description": "1000m repeats at interval pace"
                    }
                ],
                "cooldown": {"duration_minutes": 10, "description": "Easy jog", "pace": "easy"},
                "total_duration_minutes": 60,
                "estimated_tss": 85
            }
        },
        {
            "name": "Short Speed - 12x400m",
            "domain": "running",
            "type": "intervals",
            "description": "12x400m at R pace with 200m jog recovery",
            "tags": ["intervals", "speed", "track", "repetition"],
            "difficulty": "intermediate",
            "duration_minutes": 60,
            "equipment": ["track"],
            "training_phase": "quality",
            "vdot_range": [35, 65],
            "content": {
                "warmup": {"duration_minutes": 15, "description": "Easy jog + strides", "pace": "easy"},
                "main_set": [
                    {
                        "repetitions": 12,
                        "work_duration": "400m",
                        "work_pace": "R",
                        "recovery_duration": "200m jog",
                        "recovery_type": "jog",
                        "description": "400m repeats at repetition pace"
                    }
                ],
                "cooldown": {"duration_minutes": 10, "description": "Easy jog", "pace": "easy"},
                "total_duration_minutes": 60,
                "estimated_tss": 75
            }
        },

        # Tempo/Threshold Workouts
        {
            "name": "Classic 20-Minute Threshold",
            "domain": "running",
            "type": "tempo",
            "description": "Continuous 20-minute run at threshold pace",
            "tags": ["threshold", "tempo", "lactate_threshold"],
            "difficulty": "intermediate",
            "duration_minutes": 45,
            "equipment": [],
            "training_phase": "quality",
            "vdot_range": [30, 70],
            "content": {
                "warmup": {"duration_minutes": 15, "description": "Easy jog", "pace": "easy"},
                "main_set": [
                    {
                        "repetitions": 1,
                        "work_duration": "20:00",
                        "work_pace": "T",
                        "description": "Continuous threshold run"
                    }
                ],
                "cooldown": {"duration_minutes": 10, "description": "Easy jog", "pace": "easy"},
                "total_duration_minutes": 45,
                "estimated_tss": 65
            }
        },
        {
            "name": "Cruise Intervals - 5x1 Mile",
            "domain": "running",
            "type": "tempo",
            "description": "5x1 mile at T pace with 1-minute recovery",
            "tags": ["threshold", "cruise_intervals", "lactate_threshold"],
            "difficulty": "intermediate",
            "duration_minutes": 60,
            "equipment": [],
            "training_phase": "quality",
            "vdot_range": [35, 65],
            "content": {
                "warmup": {"duration_minutes": 15, "description": "Easy jog", "pace": "easy"},
                "main_set": [
                    {
                        "repetitions": 5,
                        "work_duration": "1 mile",
                        "work_pace": "T",
                        "recovery_duration": "1:00",
                        "recovery_type": "jog",
                        "description": "1-mile repeats at threshold pace"
                    }
                ],
                "cooldown": {"duration_minutes": 10, "description": "Easy jog", "pace": "easy"},
                "total_duration_minutes": 60,
                "estimated_tss": 70
            }
        },
        {
            "name": "Marathon Tempo - 10 Miles",
            "domain": "running",
            "type": "tempo",
            "description": "10-mile continuous run at marathon pace",
            "tags": ["tempo", "marathon_pace", "race_specific"],
            "difficulty": "advanced",
            "duration_minutes": 90,
            "equipment": [],
            "training_phase": "race_specific",
            "vdot_range": [40, 60],
            "content": {
                "warmup": {"duration_minutes": 15, "description": "Easy jog", "pace": "easy"},
                "main_set": [
                    {
                        "repetitions": 1,
                        "work_duration": "10 miles",
                        "work_pace": "M",
                        "description": "10 miles at marathon pace"
                    }
                ],
                "cooldown": {"duration_minutes": 10, "description": "Easy jog", "pace": "easy"},
                "total_duration_minutes": 120,
                "estimated_tss": 90
            }
        },

        # Long Runs
        {
            "name": "Foundation Long Run",
            "domain": "running",
            "type": "long_run",
            "description": "90-120 minute easy-paced long run for aerobic development",
            "tags": ["long_run", "aerobic", "endurance", "base_building"],
            "difficulty": "intermediate",
            "duration_minutes": 105,
            "equipment": [],
            "training_phase": "base",
            "vdot_range": [30, 70],
            "content": {
                "warmup": {"duration_minutes": 5, "description": "Start easy", "pace": "easy"},
                "main_set": [
                    {
                        "repetitions": 1,
                        "work_duration": "90-120 minutes",
                        "work_pace": "E",
                        "description": "Continuous easy running - don't exceed 74% max HR"
                    }
                ],
                "cooldown": {"duration_minutes": 0, "description": "None needed", "pace": None},
                "total_duration_minutes": 120,
                "estimated_tss": 75
            }
        },
        {
            "name": "Long Run with Fast Finish",
            "domain": "running",
            "type": "long_run",
            "description": "16-mile long run with final 3 miles at marathon pace",
            "tags": ["long_run", "progression", "marathon_pace", "race_specific"],
            "difficulty": "advanced",
            "duration_minutes": 135,
            "equipment": [],
            "training_phase": "race_specific",
            "vdot_range": [40, 60],
            "content": {
                "warmup": {"duration_minutes": 0, "description": "First 13 miles easy", "pace": "E"},
                "main_set": [
                    {
                        "repetitions": 1,
                        "work_duration": "13 miles",
                        "work_pace": "E",
                        "description": "Easy pace"
                    },
                    {
                        "repetitions": 1,
                        "work_duration": "3 miles",
                        "work_pace": "M",
                        "description": "Marathon pace finish"
                    }
                ],
                "cooldown": {"duration_minutes": 0, "description": "None", "pace": None},
                "total_duration_minutes": 150,
                "estimated_tss": 110
            }
        },

        # Easy/Recovery Runs
        {
            "name": "Recovery Run - 30 Minutes",
            "domain": "running",
            "type": "recovery",
            "description": "Easy 30-minute recovery run",
            "tags": ["recovery", "easy", "aerobic"],
            "difficulty": "beginner",
            "duration_minutes": 30,
            "equipment": [],
            "training_phase": "recovery",
            "vdot_range": [20, 70],
            "content": {
                "warmup": {"duration_minutes": 0, "description": "None", "pace": None},
                "main_set": [
                    {
                        "repetitions": 1,
                        "work_duration": "30:00",
                        "work_pace": "E",
                        "description": "Very easy pace - should feel effortless"
                    }
                ],
                "cooldown": {"duration_minutes": 0, "description": "None", "pace": None},
                "total_duration_minutes": 30,
                "estimated_tss": 25
            }
        },
        {
            "name": "Easy Run - 45 Minutes",
            "domain": "running",
            "type": "easy",
            "description": "Standard 45-minute easy run",
            "tags": ["easy", "aerobic", "base_building"],
            "difficulty": "beginner",
            "duration_minutes": 45,
            "equipment": [],
            "training_phase": "base",
            "vdot_range": [25, 70],
            "content": {
                "warmup": {"duration_minutes": 0, "description": "None", "pace": None},
                "main_set": [
                    {
                        "repetitions": 1,
                        "work_duration": "45:00",
                        "work_pace": "E",
                        "description": "Comfortable easy pace"
                    }
                ],
                "cooldown": {"duration_minutes": 0, "description": "None", "pace": None},
                "total_duration_minutes": 45,
                "estimated_tss": 35
            }
        }
    ]

    for workout in running_workouts:
        workout_id = library.add_workout(workout)
        print(f"Added running workout: {workout['name']} (ID: {workout_id})")


def seed_strength_workouts(library: WorkoutLibrary):
    """Add strength workout templates"""

    strength_workouts = [
        {
            "name": "Foundation Phase - Lower Body",
            "domain": "strength",
            "type": "foundation",
            "description": "Base building lower body strength workout for runners",
            "tags": ["lower_body", "foundation", "injury_prevention", "base_building"],
            "difficulty": "beginner",
            "duration_minutes": 45,
            "equipment": ["dumbbells", "bench", "mat"],
            "training_phase": "base",
            "content": {
                "warmup": {
                    "duration_minutes": 5,
                    "exercises": ["leg_swings", "hip_circles", "bodyweight_squats"]
                },
                "circuits": [
                    {
                        "name": "Lower Body Strength",
                        "rounds": 3,
                        "exercises": [
                            {
                                "name": "Goblet Squat",
                                "sets": 3,
                                "reps": "12-15",
                                "rest_seconds": 60,
                                "equipment": ["dumbbell"],
                                "notes": "Focus on depth and control"
                            },
                            {
                                "name": "Bulgarian Split Squat",
                                "sets": 3,
                                "reps": "10-12 per leg",
                                "rest_seconds": 60,
                                "equipment": ["dumbbells", "bench"],
                                "notes": "Keep torso upright"
                            },
                            {
                                "name": "Romanian Deadlift",
                                "sets": 3,
                                "reps": "12-15",
                                "rest_seconds": 60,
                                "equipment": ["dumbbells"],
                                "notes": "Feel hamstring stretch"
                            },
                            {
                                "name": "Single-Leg Calf Raise",
                                "sets": 3,
                                "reps": "15-20 per leg",
                                "rest_seconds": 45,
                                "equipment": [],
                                "notes": "Hold for 1 second at top"
                            }
                        ]
                    }
                ],
                "cooldown": {
                    "duration_minutes": 5,
                    "exercises": ["static_stretching", "foam_rolling"]
                },
                "total_duration_minutes": 45,
                "focus_areas": ["glutes", "quads", "hamstrings", "calves"]
            }
        },
        {
            "name": "Power Phase - Explosive Lower Body",
            "domain": "strength",
            "type": "power",
            "description": "Power development for running economy and speed",
            "tags": ["lower_body", "power", "explosive", "running_economy"],
            "difficulty": "advanced",
            "duration_minutes": 40,
            "equipment": ["box", "mat"],
            "training_phase": "quality",
            "content": {
                "warmup": {
                    "duration_minutes": 5,
                    "exercises": ["dynamic_stretching", "jump_rope", "activation_drills"]
                },
                "circuits": [
                    {
                        "name": "Power Circuit",
                        "rounds": 4,
                        "exercises": [
                            {
                                "name": "Box Jumps",
                                "sets": 4,
                                "reps": "6-8",
                                "rest_seconds": 90,
                                "equipment": ["box"],
                                "notes": "Focus on explosive power, step down"
                            },
                            {
                                "name": "Single-Leg Hop",
                                "sets": 4,
                                "reps": "10 per leg",
                                "rest_seconds": 60,
                                "equipment": [],
                                "notes": "Maximize height and distance"
                            },
                            {
                                "name": "Broad Jump",
                                "sets": 4,
                                "reps": "6",
                                "rest_seconds": 90,
                                "equipment": [],
                                "notes": "Land softly with control"
                            },
                            {
                                "name": "Bounding",
                                "sets": 4,
                                "reps": "20 meters",
                                "rest_seconds": 60,
                                "equipment": [],
                                "notes": "Exaggerated running motion"
                            }
                        ]
                    }
                ],
                "cooldown": {
                    "duration_minutes": 5,
                    "exercises": ["light_stretching"]
                },
                "total_duration_minutes": 40,
                "focus_areas": ["explosive_power", "running_economy", "neuromuscular"]
            }
        },
        {
            "name": "Core & Stability",
            "domain": "strength",
            "type": "foundation",
            "description": "Core strength and stability for running form",
            "tags": ["core", "stability", "injury_prevention", "running_form"],
            "difficulty": "intermediate",
            "duration_minutes": 25,
            "equipment": ["mat"],
            "training_phase": "base",
            "content": {
                "warmup": {
                    "duration_minutes": 3,
                    "exercises": ["cat_cow", "bird_dog"]
                },
                "circuits": [
                    {
                        "name": "Core Circuit",
                        "rounds": 3,
                        "exercises": [
                            {
                                "name": "Plank",
                                "sets": 3,
                                "reps": "45-60 seconds",
                                "rest_seconds": 30,
                                "equipment": ["mat"],
                                "notes": "Maintain neutral spine"
                            },
                            {
                                "name": "Side Plank",
                                "sets": 3,
                                "reps": "30-45 sec per side",
                                "rest_seconds": 30,
                                "equipment": ["mat"],
                                "notes": "Stack hips and shoulders"
                            },
                            {
                                "name": "Dead Bug",
                                "sets": 3,
                                "reps": "12-15 per side",
                                "rest_seconds": 30,
                                "equipment": ["mat"],
                                "notes": "Keep lower back pressed to floor"
                            },
                            {
                                "name": "Pallof Press",
                                "sets": 3,
                                "reps": "12-15 per side",
                                "rest_seconds": 30,
                                "equipment": ["resistance_band"],
                                "notes": "Resist rotation"
                            }
                        ]
                    }
                ],
                "cooldown": {
                    "duration_minutes": 2,
                    "exercises": ["child_pose", "cat_cow"]
                },
                "total_duration_minutes": 25,
                "focus_areas": ["core", "anti_rotation", "stability"]
            }
        }
    ]

    for workout in strength_workouts:
        workout_id = library.add_workout(workout)
        print(f"Added strength workout: {workout['name']} (ID: {workout_id})")


def seed_mobility_workouts(library: WorkoutLibrary):
    """Add mobility workout templates"""

    mobility_workouts = [
        {
            "name": "Pre-Run Dynamic Warm-Up",
            "domain": "mobility",
            "type": "dynamic",
            "description": "10-minute dynamic warm-up routine before running",
            "tags": ["pre_run", "dynamic", "warmup", "activation"],
            "difficulty": "beginner",
            "duration_minutes": 10,
            "equipment": ["mat"],
            "training_phase": "base",
            "content": {
                "timing": "pre_workout",
                "sequences": [
                    {
                        "name": "Lower Body Activation",
                        "exercises": [
                            {
                                "name": "Leg Swings - Front/Back",
                                "duration_seconds": 30,
                                "repetitions": 15,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Use wall for balance"
                            },
                            {
                                "name": "Leg Swings - Side to Side",
                                "duration_seconds": 30,
                                "repetitions": 15,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Keep hips square"
                            },
                            {
                                "name": "Walking Lunges with Twist",
                                "duration_seconds": 60,
                                "repetitions": 10,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Rotate toward front leg"
                            },
                            {
                                "name": "High Knees",
                                "duration_seconds": 30,
                                "repetitions": 20,
                                "per_side": False,
                                "equipment": [],
                                "notes": "Quick cadence"
                            },
                            {
                                "name": "Butt Kicks",
                                "duration_seconds": 30,
                                "repetitions": 20,
                                "per_side": False,
                                "equipment": [],
                                "notes": "Heels to glutes"
                            },
                            {
                                "name": "A-Skips",
                                "duration_seconds": 30,
                                "repetitions": 15,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Focus on form"
                            }
                        ]
                    }
                ],
                "total_duration_minutes": 10,
                "focus_areas": ["hips", "ankles", "hip_flexors", "glute_activation"]
            }
        },
        {
            "name": "Post-Run Static Stretch Routine",
            "domain": "mobility",
            "type": "static",
            "description": "15-minute post-run static stretching for recovery",
            "tags": ["post_run", "static", "recovery", "flexibility"],
            "difficulty": "beginner",
            "duration_minutes": 15,
            "equipment": ["mat"],
            "training_phase": "recovery",
            "content": {
                "timing": "post_workout",
                "sequences": [
                    {
                        "name": "Lower Body Static Stretches",
                        "exercises": [
                            {
                                "name": "Standing Quad Stretch",
                                "duration_seconds": 45,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Pull heel to glute, keep knees together"
                            },
                            {
                                "name": "Standing Hamstring Stretch",
                                "duration_seconds": 45,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Hinge at hips, keep back straight"
                            },
                            {
                                "name": "Figure-4 Hip Stretch",
                                "duration_seconds": 60,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": ["mat"],
                                "notes": "Lying on back, ankle on opposite knee"
                            },
                            {
                                "name": "Pigeon Pose",
                                "duration_seconds": 90,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": ["mat"],
                                "notes": "Deep hip opener"
                            },
                            {
                                "name": "Calf Stretch - Straight Leg",
                                "duration_seconds": 45,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Target gastrocnemius"
                            },
                            {
                                "name": "Calf Stretch - Bent Knee",
                                "duration_seconds": 45,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Target soleus"
                            }
                        ]
                    }
                ],
                "total_duration_minutes": 15,
                "focus_areas": ["hips", "hamstrings", "quads", "calves", "glutes"]
            }
        },
        {
            "name": "Hip Mobility & Activation",
            "domain": "mobility",
            "type": "dynamic",
            "description": "20-minute hip mobility routine for runners",
            "tags": ["hips", "mobility", "activation", "injury_prevention"],
            "difficulty": "intermediate",
            "duration_minutes": 20,
            "equipment": ["mat", "resistance_band"],
            "training_phase": "base",
            "content": {
                "timing": "standalone",
                "sequences": [
                    {
                        "name": "Hip Mobility Flow",
                        "exercises": [
                            {
                                "name": "90/90 Hip Stretch",
                                "duration_seconds": 60,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": ["mat"],
                                "notes": "Square hips, upright posture"
                            },
                            {
                                "name": "Hip CARs (Controlled Articular Rotations)",
                                "duration_seconds": 45,
                                "repetitions": 5,
                                "per_side": True,
                                "equipment": [],
                                "notes": "Full range circular motion"
                            },
                            {
                                "name": "Fire Hydrants",
                                "duration_seconds": 45,
                                "repetitions": 15,
                                "per_side": True,
                                "equipment": ["mat"],
                                "notes": "Activate hip abductors"
                            },
                            {
                                "name": "Clamshells with Band",
                                "duration_seconds": 60,
                                "repetitions": 20,
                                "per_side": True,
                                "equipment": ["mat", "resistance_band"],
                                "notes": "Keep feet together"
                            },
                            {
                                "name": "Hip Flexor Stretch with Reach",
                                "duration_seconds": 60,
                                "repetitions": None,
                                "per_side": True,
                                "equipment": ["mat"],
                                "notes": "Lunge position, reach overhead"
                            },
                            {
                                "name": "World's Greatest Stretch",
                                "duration_seconds": 90,
                                "repetitions": 5,
                                "per_side": True,
                                "equipment": ["mat"],
                                "notes": "Lunge + rotation + hamstring stretch"
                            }
                        ]
                    }
                ],
                "total_duration_minutes": 20,
                "focus_areas": ["hip_mobility", "hip_activation", "glute_med", "hip_flexors"]
            }
        }
    ]

    for workout in mobility_workouts:
        workout_id = library.add_workout(workout)
        print(f"Added mobility workout: {workout['name']} (ID: {workout_id})")


def seed_nutrition_plans(library: WorkoutLibrary):
    """Add nutrition plan templates"""

    nutrition_plans = [
        {
            "name": "Marathon Long Run Fueling",
            "domain": "nutrition",
            "type": "long_run",
            "description": "Complete fueling strategy for 18-20 mile long runs",
            "tags": ["long_run", "marathon_training", "fueling", "gluten_free", "dairy_free"],
            "difficulty": "intermediate",
            "duration_minutes": 180,
            "equipment": [],
            "training_phase": "race_specific",
            "content": {
                "timing": "Long run day",
                "meals": [
                    {
                        "name": "Pre-Run Breakfast",
                        "timing": "-2.5 to -3 hours before run",
                        "foods": [
                            {
                                "item": "Gluten-free oatmeal",
                                "quantity": "1 cup cooked",
                                "macros": {"calories": 150, "carbs_g": 27, "protein_g": 5, "fat_g": 3}
                            },
                            {
                                "item": "Banana",
                                "quantity": "1 medium",
                                "macros": {"calories": 105, "carbs_g": 27, "protein_g": 1, "fat_g": 0}
                            },
                            {
                                "item": "Almond butter",
                                "quantity": "1 tbsp",
                                "macros": {"calories": 98, "carbs_g": 3, "protein_g": 3, "fat_g": 9}
                            },
                            {
                                "item": "Maple syrup",
                                "quantity": "1 tbsp",
                                "macros": {"calories": 52, "carbs_g": 13, "protein_g": 0, "fat_g": 0}
                            }
                        ],
                        "total_macros": {"calories": 405, "carbs_g": 70, "protein_g": 9, "fat_g": 12},
                        "dietary_constraints": ["gluten_free", "dairy_free"],
                        "notes": "Familiar foods only, nothing new on long run day"
                    },
                    {
                        "name": "Pre-Run Snack",
                        "timing": "-30 to -45 minutes before run",
                        "foods": [
                            {
                                "item": "Energy gel or date",
                                "quantity": "1 gel or 2 dates",
                                "macros": {"calories": 100, "carbs_g": 25, "protein_g": 0, "fat_g": 0}
                            }
                        ],
                        "total_macros": {"calories": 100, "carbs_g": 25, "protein_g": 0, "fat_g": 0},
                        "dietary_constraints": ["gluten_free", "dairy_free"],
                        "notes": "Optional - only if you know you tolerate it well"
                    },
                    {
                        "name": "During Run Fueling",
                        "timing": "Every 45 minutes during run",
                        "foods": [
                            {
                                "item": "Energy gel or chews",
                                "quantity": "1 gel or 3 chews per 45 min",
                                "macros": {"calories": 100, "carbs_g": 25, "protein_g": 0, "fat_g": 0}
                            }
                        ],
                        "total_macros": {"calories": 300, "carbs_g": 75, "protein_g": 0, "fat_g": 0},
                        "dietary_constraints": ["gluten_free", "dairy_free"],
                        "notes": "Start at 45 min mark. For 18-mile run, take at 45, 90, 135 minutes"
                    },
                    {
                        "name": "Post-Run Recovery",
                        "timing": "Within 30 minutes of finishing",
                        "foods": [
                            {
                                "item": "Chocolate oat milk",
                                "quantity": "12 oz",
                                "macros": {"calories": 180, "carbs_g": 24, "protein_g": 4, "fat_g": 7}
                            },
                            {
                                "item": "Banana",
                                "quantity": "1 medium",
                                "macros": {"calories": 105, "carbs_g": 27, "protein_g": 1, "fat_g": 0}
                            }
                        ],
                        "total_macros": {"calories": 285, "carbs_g": 51, "protein_g": 5, "fat_g": 7},
                        "dietary_constraints": ["gluten_free", "dairy_free"],
                        "notes": "3:1 or 4:1 carb to protein ratio for glycogen replenishment"
                    }
                ],
                "hydration": {
                    "pre": "16-20 oz water 2-3 hours before, 8-10 oz 20 min before",
                    "during": "6-8 oz every 20 minutes (aim for 20-24 oz per hour)",
                    "post": "16-24 oz per pound lost during run"
                }
            }
        },
        {
            "name": "Race Day Nutrition - Marathon",
            "domain": "nutrition",
            "type": "race_day",
            "description": "Complete race day fueling plan for marathon",
            "tags": ["race_day", "marathon", "fueling", "gluten_free", "dairy_free"],
            "difficulty": "advanced",
            "duration_minutes": 300,
            "equipment": [],
            "training_phase": "race_specific",
            "content": {
                "timing": "Race day",
                "meals": [
                    {
                        "name": "Race Morning Breakfast",
                        "timing": "-3 hours before start",
                        "foods": [
                            {
                                "item": "White rice with maple syrup",
                                "quantity": "1.5 cups cooked",
                                "macros": {"calories": 240, "carbs_g": 53, "protein_g": 4, "fat_g": 0}
                            },
                            {
                                "item": "Banana",
                                "quantity": "1 medium",
                                "macros": {"calories": 105, "carbs_g": 27, "protein_g": 1, "fat_g": 0}
                            },
                            {
                                "item": "Applesauce",
                                "quantity": "4 oz",
                                "macros": {"calories": 50, "carbs_g": 14, "protein_g": 0, "fat_g": 0}
                            }
                        ],
                        "total_macros": {"calories": 395, "carbs_g": 94, "protein_g": 5, "fat_g": 0},
                        "dietary_constraints": ["gluten_free", "dairy_free"],
                        "notes": "Low fiber, easily digestible. Practice this exact meal on long runs"
                    },
                    {
                        "name": "Pre-Race Fuel",
                        "timing": "-15 minutes before start",
                        "foods": [
                            {
                                "item": "Energy gel",
                                "quantity": "1 gel",
                                "macros": {"calories": 100, "carbs_g": 25, "protein_g": 0, "fat_g": 0}
                            }
                        ],
                        "total_macros": {"calories": 100, "carbs_g": 25, "protein_g": 0, "fat_g": 0},
                        "dietary_constraints": ["gluten_free", "dairy_free"],
                        "notes": "Take with 4-6 oz water"
                    },
                    {
                        "name": "In-Race Fueling",
                        "timing": "Every 45 minutes during race",
                        "foods": [
                            {
                                "item": "Energy gel",
                                "quantity": "1 gel per 45 min",
                                "macros": {"calories": 100, "carbs_g": 25, "protein_g": 0, "fat_g": 0}
                            }
                        ],
                        "total_macros": {"calories": 600, "carbs_g": 150, "protein_g": 0, "fat_g": 0},
                        "dietary_constraints": ["gluten_free", "dairy_free"],
                        "notes": "For 4-hour marathon: gels at miles 6, 10, 14, 18, 22. Total ~60g carbs/hour"
                    }
                ],
                "hydration": {
                    "pre": "16 oz 2 hours before, 8 oz 15 min before",
                    "during": "At every aid station - small sips (4-6 oz). Alternate water and sports drink",
                    "post": "24 oz immediately, continue drinking to clear urine"
                }
            }
        },
        {
            "name": "Recovery Day Nutrition",
            "domain": "nutrition",
            "type": "recovery",
            "description": "Anti-inflammatory nutrition for rest/recovery days",
            "tags": ["recovery", "anti_inflammatory", "gluten_free", "dairy_free"],
            "difficulty": "beginner",
            "duration_minutes": 1440,
            "equipment": [],
            "training_phase": "recovery",
            "content": {
                "timing": "Full day",
                "meals": [
                    {
                        "name": "Breakfast",
                        "timing": "Morning",
                        "foods": [
                            {
                                "item": "Smoothie bowl with berries, banana, spinach, oat milk",
                                "quantity": "1 bowl",
                                "macros": {"calories": 350, "carbs_g": 65, "protein_g": 8, "fat_g": 6}
                            },
                            {
                                "item": "Chia seeds",
                                "quantity": "2 tbsp",
                                "macros": {"calories": 138, "carbs_g": 12, "protein_g": 5, "fat_g": 9}
                            }
                        ],
                        "total_macros": {"calories": 488, "carbs_g": 77, "protein_g": 13, "fat_g": 15},
                        "dietary_constraints": ["gluten_free", "dairy_free", "anti_inflammatory"],
                        "notes": "Berries provide antioxidants for recovery"
                    },
                    {
                        "name": "Lunch",
                        "timing": "Midday",
                        "foods": [
                            {
                                "item": "Grilled salmon",
                                "quantity": "5 oz",
                                "macros": {"calories": 280, "carbs_g": 0, "protein_g": 35, "fat_g": 14}
                            },
                            {
                                "item": "Quinoa",
                                "quantity": "1 cup cooked",
                                "macros": {"calories": 222, "carbs_g": 39, "protein_g": 8, "fat_g": 4}
                            },
                            {
                                "item": "Roasted vegetables",
                                "quantity": "2 cups",
                                "macros": {"calories": 100, "carbs_g": 20, "protein_g": 3, "fat_g": 2}
                            }
                        ],
                        "total_macros": {"calories": 602, "carbs_g": 59, "protein_g": 46, "fat_g": 20},
                        "dietary_constraints": ["gluten_free", "dairy_free", "anti_inflammatory"],
                        "notes": "Omega-3 rich salmon reduces inflammation"
                    },
                    {
                        "name": "Dinner",
                        "timing": "Evening",
                        "foods": [
                            {
                                "item": "Turkey or chicken",
                                "quantity": "6 oz",
                                "macros": {"calories": 240, "carbs_g": 0, "protein_g": 46, "fat_g": 5}
                            },
                            {
                                "item": "Sweet potato",
                                "quantity": "1 medium",
                                "macros": {"calories": 130, "carbs_g": 30, "protein_g": 3, "fat_g": 0}
                            },
                            {
                                "item": "Leafy greens salad",
                                "quantity": "2 cups",
                                "macros": {"calories": 50, "carbs_g": 10, "protein_g": 2, "fat_g": 1}
                            }
                        ],
                        "total_macros": {"calories": 420, "carbs_g": 40, "protein_g": 51, "fat_g": 6},
                        "dietary_constraints": ["gluten_free", "dairy_free", "anti_inflammatory"],
                        "notes": "Lean protein supports muscle repair"
                    }
                ],
                "hydration": {
                    "pre": "N/A",
                    "during": "Drink throughout day - aim for pale yellow urine",
                    "post": "N/A"
                }
            }
        }
    ]

    for plan in nutrition_plans:
        workout_id = library.add_workout(plan)
        print(f"Added nutrition plan: {plan['name']} (ID: {workout_id})")


def main():
    """Seed the workout library with all templates"""
    print("Seeding workout library...")

    library = WorkoutLibrary()

    print("\n=== Adding Running Workouts ===")
    seed_running_workouts(library)

    print("\n=== Adding Strength Workouts ===")
    seed_strength_workouts(library)

    print("\n=== Adding Mobility Workouts ===")
    seed_mobility_workouts(library)

    print("\n=== Adding Nutrition Plans ===")
    seed_nutrition_plans(library)

    print("\n=== Library Statistics ===")
    stats = library.get_stats()
    print(f"Total workouts: {stats['total_workouts']}")
    print(f"By domain: {stats['by_domain']}")
    print(f"By difficulty: {stats['by_difficulty']}")

    print("\n✅ Workout library seeded successfully!")


if __name__ == "__main__":
    main()
