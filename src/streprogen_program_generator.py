#!/usr/bin/env python3
"""
Streprogen Program Generator for Runners

Generates multi-week periodized strength programs using the streprogen library.
Designed specifically for distance runners with lower intensity defaults and
runner-specific exercise selection.

Usage:
    python3 src/streprogen_program_generator.py --generate --duration 4 --phase foundation
    python3 src/streprogen_program_generator.py --view
    python3 src/streprogen_program_generator.py --archive
"""

import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import streprogen

# Paths
PROGRAM_DIR = Path(__file__).parent.parent / "data" / "strength_programs"
CURRENT_PROGRAM_FILE = PROGRAM_DIR / "current_program.json"
ARCHIVE_DIR = PROGRAM_DIR / "archive"


class RunnerStrengthProgramGenerator:
    """Generate periodized strength programs for distance runners."""

    # Runner-specific exercise database
    EXERCISES = {
        "A": {  # Squat + Push
            "name": "Squat + Push",
            "primary": [
                {"name": "Goblet Squat", "start_weight": 20, "reps": [6, 10], "weekly_inc": 1.5},
            ],
            "secondary": [
                {"name": "Push-ups", "start_weight": 0, "reps": [8, 12], "weekly_inc": 1.5},
            ],
            "accessories": [
                {"name": "Dead Bug", "sets": 3, "reps": 10, "static": True},
                {"name": "Calf Raises", "sets": 3, "reps": 15, "static": True},
            ]
        },
        "B": {  # Hinge + Pull
            "name": "Hinge + Pull",
            "primary": [
                {"name": "DB RDL", "start_weight": 15, "reps": [6, 10], "weekly_inc": 2.0},
            ],
            "secondary": [
                {"name": "Chest-supported Row", "start_weight": 10, "reps": [8, 12], "weekly_inc": 1.5},
            ],
            "accessories": [
                {"name": "Pallof Press", "sets": 3, "reps": "10 each", "static": True},
                {"name": "Bent-knee Calf Raise", "sets": 3, "reps": 15, "static": True},
            ]
        },
        "C": {  # Unilateral + Velocity
            "name": "Unilateral + Velocity",
            "primary": [
                {"name": "Reverse Lunge", "start_weight": 10, "reps": [6, 10], "weekly_inc": 1.5},
            ],
            "secondary": [
                {"name": "Step-ups", "start_weight": 0, "reps": [8, 10], "weekly_inc": 1.5},
            ],
            "accessories": [
                {"name": "Suitcase Carry", "sets": 3, "reps": "30s each", "static": True},
                {"name": "Single-leg Calf Raise", "sets": 3, "reps": "12 each", "static": True},
            ]
        }
    }

    def __init__(self, duration_weeks=4, intensity=75, units="kg"):
        """
        Initialize program generator.

        Args:
            duration_weeks: Length of program (4-8 weeks)
            intensity: Intensity level (75 = runner-friendly, 83 = default)
            units: Weight units ("kg" or "lb")
        """
        self.duration = duration_weeks
        self.intensity = intensity
        self.units = units

    def generate_program(self, phase="Foundation", start_date=None):
        """
        Generate a complete strength program.

        Args:
            phase: Training phase name (Foundation, Build, Maintain)
            start_date: Start date (YYYY-MM-DD string or datetime)

        Returns:
            dict: Complete program with all sessions and weekly workouts
        """
        if start_date is None:
            start_date = datetime.now()
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")

        program_id = f"{start_date.strftime('%Y-%m-%d')}_{phase.lower()}"
        end_date = start_date + timedelta(weeks=self.duration)

        # Generate each session type (A, B, C)
        sessions = {}
        for session_type, exercises in self.EXERCISES.items():
            sessions[session_type] = self._generate_session(session_type, exercises)

        # Create program structure
        program = {
            "program_id": program_id,
            "phase": phase,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "current_week": 1,
            "parameters": {
                "duration_weeks": self.duration,
                "intensity": self.intensity,
                "units": self.units
            },
            "sessions": sessions,
            "weekly_workouts": [],
            "completion_history": [],
            "adherence_metrics": {
                "total_scheduled": 0,
                "total_completed": 0,
                "completion_rate": 0.0
            }
        }

        return program

    def _generate_session(self, session_type, exercises):
        """Generate a single session using streprogen."""
        # Create streprogen program
        program = streprogen.Program(
            name=f"Session {session_type}",
            duration=self.duration,
            reps_per_exercise=25,  # Total reps per exercise
            intensity=self.intensity,
            units=self.units
        )

        session_data = {
            "name": exercises["name"],
            "exercises": [],
            "weekly_progression": []
        }

        # Create a day to hold all exercises
        day = streprogen.Day(name=f"Session {session_type}")

        # Add primary exercises (progressive)
        for ex in exercises["primary"]:
            ex_obj = streprogen.DynamicExercise(
                name=ex["name"],
                start_weight=ex["start_weight"],
                final_weight=None,  # Use percent_inc_per_week instead
                min_reps=ex["reps"][0],
                max_reps=ex["reps"][1],
                percent_inc_per_week=ex["weekly_inc"]
            )
            day.add_exercises(ex_obj)
            session_data["exercises"].append({
                "name": ex["name"],
                "type": "dynamic",
                "start_weight": ex["start_weight"],
                "reps_range": ex["reps"],
                "weekly_increase": ex["weekly_inc"]
            })

        # Add secondary exercises (progressive)
        for ex in exercises["secondary"]:
            ex_obj = streprogen.DynamicExercise(
                name=ex["name"],
                start_weight=ex["start_weight"],
                final_weight=None,  # Use percent_inc_per_week instead
                min_reps=ex["reps"][0],
                max_reps=ex["reps"][1],
                percent_inc_per_week=ex["weekly_inc"]
            )
            day.add_exercises(ex_obj)
            session_data["exercises"].append({
                "name": ex["name"],
                "type": "dynamic",
                "start_weight": ex["start_weight"],
                "reps_range": ex["reps"],
                "weekly_increase": ex["weekly_inc"]
            })

        # Add accessories (static)
        for ex in exercises["accessories"]:
            ex_obj = streprogen.StaticExercise(
                name=ex["name"],
                sets_reps=f"{ex['sets']} x {ex['reps']}"
            )
            day.add_exercises(ex_obj)
            session_data["exercises"].append({
                "name": ex["name"],
                "type": "static",
                "sets": ex["sets"],
                "reps": ex["reps"]
            })

        # Add day to program
        program.add_days(day)

        # Render program to generate workout progression
        program.render()

        # Get text representation of the program
        rendered_text = program.to_txt()
        session_data["rendered_program"] = rendered_text

        # Parse rendered output to extract weekly workout details
        # Parse the rendered text into structured weekly data
        weekly_workouts = self._parse_rendered_program(rendered_text, self.duration)
        for week_num, workout_data in enumerate(weekly_workouts, start=1):
            session_data["weekly_progression"].append({
                "week": week_num,
                "workout": workout_data
            })

        return session_data

    def _parse_rendered_program(self, rendered_text, num_weeks):
        """
        Parse the rendered program text into structured weekly workout data.

        Returns a list of dicts, one per week, with exercise details.
        """
        workouts = []
        lines = rendered_text.split('\n')

        # Simple parsing - extract week sections
        current_week = None
        current_exercises = []

        for line in lines:
            line = line.strip()

            # Detect week headers
            if line.startswith('Week '):
                if current_week is not None:
                    # Save previous week
                    workouts.append({
                        "week": current_week,
                        "exercises": current_exercises.copy()
                    })
                current_week = int(line.split()[1])
                current_exercises = []

            # Detect exercise lines (have 'x' for sets/reps)
            elif ' x ' in line and current_week is not None:
                # Parse exercise line like "Goblet Squat   10 x 15kg   10 x 15kg"
                parts = line.split()
                if len(parts) >= 3:
                    # Extract exercise name (everything before the first number)
                    name_parts = []
                    for part in parts:
                        if 'x' in part or part[0].isdigit():
                            break
                        name_parts.append(part)

                    if name_parts:
                        exercise_name = ' '.join(name_parts)
                        # Extract sets (remaining parts)
                        sets_str = ' '.join(parts[len(name_parts):])
                        current_exercises.append({
                            "name": exercise_name,
                            "sets": sets_str
                        })

        # Save last week
        if current_week is not None:
            workouts.append({
                "week": current_week,
                "exercises": current_exercises
            })

        # Fill in any missing weeks with empty data
        while len(workouts) < num_weeks:
            workouts.append({
                "week": len(workouts) + 1,
                "exercises": []
            })

        return workouts

    def _extract_week_data(self, program, week_num):
        """Extract workout data for a specific week."""
        # This is simplified - in reality we'd parse the rendered program
        # For now, return placeholder structure
        return {
            "week": week_num,
            "exercises": []
        }

    def save_program(self, program):
        """Save program to current_program.json."""
        PROGRAM_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(exist_ok=True)

        # Archive existing program if it exists
        if CURRENT_PROGRAM_FILE.exists():
            self._archive_current_program()

        # Save new program
        with open(CURRENT_PROGRAM_FILE, 'w') as f:
            json.dump(program, f, indent=2)

        print(f"✓ Program saved: {program['program_id']}")
        print(f"  Phase: {program['phase']}")
        print(f"  Duration: {program['parameters']['duration_weeks']} weeks")
        print(f"  Start: {program['start_date']}")
        print(f"  End: {program['end_date']}")

    def _archive_current_program(self):
        """Move current program to archive."""
        with open(CURRENT_PROGRAM_FILE, 'r') as f:
            current = json.load(f)

        archive_file = ARCHIVE_DIR / f"{current['program_id']}.json"
        with open(archive_file, 'w') as f:
            json.dump(current, f, indent=2)

        print(f"✓ Archived previous program: {current['program_id']}")

    def view_current_program(self):
        """Display current program summary."""
        if not CURRENT_PROGRAM_FILE.exists():
            print("No active program found.")
            return

        with open(CURRENT_PROGRAM_FILE, 'r') as f:
            program = json.load(f)

        print(f"\n{'='*60}")
        print(f"Current Program: {program['program_id']}")
        print(f"{'='*60}")
        print(f"Phase: {program['phase']}")
        print(f"Duration: {program['parameters']['duration_weeks']} weeks")
        print(f"Start: {program['start_date']} → End: {program['end_date']}")
        print(f"Current Week: {program['current_week']}")
        print(f"Intensity: {program['parameters']['intensity']}")
        print(f"\nSessions:")

        for session_type, session in program['sessions'].items():
            print(f"\n  Session {session_type}: {session['name']}")
            for ex in session['exercises']:
                if ex['type'] == 'dynamic':
                    print(f"    - {ex['name']}: {ex['start_weight']}{program['parameters']['units']} "
                          f"({ex['reps_range'][0]}-{ex['reps_range'][1]} reps)")
                else:
                    print(f"    - {ex['name']}: {ex['sets']} x {ex['reps']}")

        print(f"\nAdherence:")
        metrics = program['adherence_metrics']
        print(f"  Completed: {metrics['total_completed']}/{metrics['total_scheduled']} "
              f"({metrics['completion_rate']:.1%})")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Generate runner-specific strength programs")
    parser.add_argument('--generate', action='store_true', help="Generate new program")
    parser.add_argument('--view', action='store_true', help="View current program")
    parser.add_argument('--archive', action='store_true', help="Archive current program")
    parser.add_argument('--duration', type=int, default=4, help="Program duration in weeks (default: 4)")
    parser.add_argument('--phase', type=str, default="Foundation", help="Training phase (default: Foundation)")
    parser.add_argument('--intensity', type=int, default=75, help="Intensity level (default: 75 for runners)")
    parser.add_argument('--start-date', type=str, help="Start date (YYYY-MM-DD, default: today)")

    args = parser.parse_args()

    generator = RunnerStrengthProgramGenerator(
        duration_weeks=args.duration,
        intensity=args.intensity
    )

    if args.generate:
        print(f"Generating {args.duration}-week {args.phase} program...")
        program = generator.generate_program(
            phase=args.phase,
            start_date=args.start_date
        )
        generator.save_program(program)
    elif args.view:
        generator.view_current_program()
    elif args.archive:
        if CURRENT_PROGRAM_FILE.exists():
            generator._archive_current_program()
        else:
            print("No current program to archive.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
