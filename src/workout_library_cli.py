#!/usr/bin/env python3
"""
Workout Library CLI

Command-line interface for browsing, searching, and managing the workout library.
"""

import argparse
import json
import sys
from typing import List, Dict, Any
from workout_library import WorkoutLibrary


def format_workout_summary(workout: Dict[str, Any]) -> str:
    """Format a workout as a one-line summary"""
    name = workout.get("name", "Untitled")
    domain = workout.get("domain", "unknown").upper()
    workout_type = workout.get("type", "unknown")
    difficulty = workout.get("difficulty", "unknown")
    duration = workout.get("duration_minutes", "?")

    return f"[{domain}] {name} | {workout_type} | {difficulty} | {duration} min"


def format_workout_detail(workout: Dict[str, Any]) -> str:
    """Format a workout with full details"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"NAME: {workout.get('name', 'Untitled')}")
    lines.append(f"ID: {workout.get('id', 'unknown')}")
    lines.append(f"DOMAIN: {workout.get('domain', 'unknown')}")
    lines.append(f"TYPE: {workout.get('type', 'unknown')}")
    lines.append(f"DIFFICULTY: {workout.get('difficulty', 'unknown')}")
    lines.append(f"DURATION: {workout.get('duration_minutes', '?')} minutes")

    if workout.get('training_phase'):
        lines.append(f"TRAINING PHASE: {workout['training_phase']}")

    if workout.get('vdot_range'):
        lines.append(f"VDOT RANGE: {workout['vdot_range'][0]}-{workout['vdot_range'][1]}")

    if workout.get('equipment'):
        lines.append(f"EQUIPMENT: {', '.join(workout['equipment']) if workout['equipment'] else 'None'}")

    if workout.get('tags'):
        lines.append(f"TAGS: {', '.join(workout['tags'])}")

    lines.append(f"\nDESCRIPTION:")
    lines.append(workout.get('description', 'No description'))

    lines.append(f"\nCONTENT:")
    lines.append(json.dumps(workout.get('content', {}), indent=2))

    if workout.get('created_date'):
        lines.append(f"\nCREATED: {workout['created_date']}")
    if workout.get('modified_date'):
        lines.append(f"MODIFIED: {workout['modified_date']}")

    lines.append("=" * 80)
    return "\n".join(lines)


def cmd_list(args):
    """List all workouts"""
    library = WorkoutLibrary()

    workouts = library.list_all_workouts(domain=args.domain)

    if not workouts:
        print("No workouts found.")
        return

    print(f"Found {len(workouts)} workout(s):\n")

    for workout in workouts:
        print(format_workout_summary(workout))


def cmd_search(args):
    """Search for workouts"""
    library = WorkoutLibrary()

    # Build search parameters
    search_params = {}

    if args.domain:
        search_params['domain'] = args.domain
    if args.type:
        search_params['workout_type'] = args.type
    if args.difficulty:
        search_params['difficulty'] = args.difficulty
    if args.training_phase:
        search_params['training_phase'] = args.training_phase
    if args.tags:
        search_params['tags'] = args.tags
    if args.duration_min:
        search_params['duration_min'] = args.duration_min
    if args.duration_max:
        search_params['duration_max'] = args.duration_max
    if args.vdot_min and args.vdot_max:
        search_params['vdot_range'] = [args.vdot_min, args.vdot_max]
    if args.equipment:
        search_params['equipment'] = args.equipment
    if args.query:
        search_params['query'] = args.query
    if args.limit:
        search_params['limit'] = args.limit

    results = library.search(**search_params)

    if not results:
        print("No workouts found matching your criteria.")
        return

    print(f"Found {len(results)} workout(s):\n")

    for workout in results:
        print(format_workout_summary(workout))


def cmd_get(args):
    """Get a specific workout by ID"""
    library = WorkoutLibrary()

    workout = library.get_workout(args.workout_id)

    if not workout:
        print(f"Workout not found: {args.workout_id}")
        return

    print(format_workout_detail(workout))


def cmd_stats(args):
    """Show library statistics"""
    library = WorkoutLibrary()

    stats = library.get_stats()

    print("=" * 80)
    print("WORKOUT LIBRARY STATISTICS")
    print("=" * 80)
    print(f"\nTotal Workouts: {stats['total_workouts']}")

    print(f"\nBy Domain:")
    for domain, count in sorted(stats['by_domain'].items()):
        print(f"  {domain:15} {count:3}")

    print(f"\nBy Type:")
    for workout_type, count in sorted(stats['by_type'].items()):
        print(f"  {workout_type:20} {count:3}")

    print(f"\nBy Difficulty:")
    for difficulty, count in sorted(stats['by_difficulty'].items()):
        print(f"  {difficulty:15} {count:3}")

    print(f"\nBy Training Phase:")
    for phase, count in sorted(stats['by_training_phase'].items()):
        print(f"  {phase:20} {count:3}")

    print("=" * 80)


def cmd_export(args):
    """Export a workout as JSON"""
    library = WorkoutLibrary()

    workout = library.get_workout(args.workout_id)

    if not workout:
        print(f"Workout not found: {args.workout_id}")
        sys.exit(1)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(workout, f, indent=2)
        print(f"Workout exported to: {args.output}")
    else:
        print(json.dumps(workout, indent=2))


def cmd_import(args):
    """Import a workout from JSON"""
    library = WorkoutLibrary()

    try:
        with open(args.file, 'r') as f:
            workout = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    try:
        workout_id = library.add_workout(workout)
        print(f"Workout imported successfully!")
        print(f"ID: {workout_id}")
        print(f"Name: {workout.get('name', 'Untitled')}")
    except Exception as e:
        print(f"Error importing workout: {e}")
        sys.exit(1)


def cmd_delete(args):
    """Delete a workout"""
    library = WorkoutLibrary()

    if not args.force:
        # Show workout first
        workout = library.get_workout(args.workout_id)
        if not workout:
            print(f"Workout not found: {args.workout_id}")
            sys.exit(1)

        print(format_workout_summary(workout))
        confirm = input("\nAre you sure you want to delete this workout? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return

    success = library.delete_workout(args.workout_id)

    if success:
        print(f"Workout deleted: {args.workout_id}")
    else:
        print(f"Workout not found: {args.workout_id}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Workout Library - Browse and manage running coach workouts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all workouts
  %(prog)s list

  # List only running workouts
  %(prog)s list --domain running

  # Search for threshold workouts
  %(prog)s search --type tempo

  # Search for beginner workouts under 30 minutes
  %(prog)s search --difficulty beginner --duration-max 30

  # Search for workouts by tags
  %(prog)s search --tags intervals vo2_max

  # Get a specific workout
  %(prog)s get <workout-id>

  # Show library statistics
  %(prog)s stats

  # Export a workout to JSON
  %(prog)s export <workout-id> --output my_workout.json

  # Import a workout from JSON
  %(prog)s import my_workout.json
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # List command
    list_parser = subparsers.add_parser('list', help='List all workouts')
    list_parser.add_argument('--domain', choices=['running', 'strength', 'mobility', 'nutrition'],
                             help='Filter by domain')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for workouts')
    search_parser.add_argument('--domain', choices=['running', 'strength', 'mobility', 'nutrition'],
                               help='Filter by domain')
    search_parser.add_argument('--type', help='Filter by workout type')
    search_parser.add_argument('--difficulty', choices=['beginner', 'intermediate', 'advanced', 'elite'],
                               help='Filter by difficulty')
    search_parser.add_argument('--training-phase',
                               choices=['base', 'quality', 'race_specific', 'taper', 'recovery'],
                               help='Filter by training phase')
    search_parser.add_argument('--tags', nargs='+', help='Filter by tags (must have ALL)')
    search_parser.add_argument('--duration-min', type=int, help='Minimum duration (minutes)')
    search_parser.add_argument('--duration-max', type=int, help='Maximum duration (minutes)')
    search_parser.add_argument('--vdot-min', type=int, help='Minimum VDOT')
    search_parser.add_argument('--vdot-max', type=int, help='Maximum VDOT')
    search_parser.add_argument('--equipment', nargs='+', help='Required equipment')
    search_parser.add_argument('--query', help='Search text in name and description')
    search_parser.add_argument('--limit', type=int, help='Maximum number of results')

    # Get command
    get_parser = subparsers.add_parser('get', help='Get a specific workout')
    get_parser.add_argument('workout_id', help='Workout ID')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show library statistics')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export a workout as JSON')
    export_parser.add_argument('workout_id', help='Workout ID')
    export_parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import a workout from JSON')
    import_parser.add_argument('file', help='JSON file to import')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a workout')
    delete_parser.add_argument('workout_id', help='Workout ID')
    delete_parser.add_argument('--force', '-f', action='store_true',
                               help='Delete without confirmation')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to command handler
    commands = {
        'list': cmd_list,
        'search': cmd_search,
        'get': cmd_get,
        'stats': cmd_stats,
        'export': cmd_export,
        'import': cmd_import,
        'delete': cmd_delete
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
