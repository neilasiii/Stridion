#!/bin/bash
#
# Workout Library CLI
# Browse, search, and manage workouts from the running coach workout library
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$REPO_ROOT/src/workout_library_cli.py"

# Ensure Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: workout_library_cli.py not found at $PYTHON_SCRIPT"
    exit 1
fi

# Run the Python CLI with all arguments
python3 "$PYTHON_SCRIPT" "$@"
