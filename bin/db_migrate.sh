#!/bin/bash
# Migrate data from JSON/Markdown files to PostgreSQL

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "Database Migration"
echo "=========================================="
echo ""

# Parse options
MIGRATE_HEALTH_WORKOUTS=true
MIGRATE_ATHLETE=true
MIGRATE_PLANS=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --workouts-only)
            MIGRATE_ATHLETE=false
            MIGRATE_PLANS=false
            shift
            ;;
        --athlete-only)
            MIGRATE_HEALTH_WORKOUTS=false
            MIGRATE_PLANS=false
            shift
            ;;
        --plans-only)
            MIGRATE_HEALTH_WORKOUTS=false
            MIGRATE_ATHLETE=false
            shift
            ;;
        --skip-plans)
            MIGRATE_PLANS=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--workouts-only|--athlete-only|--plans-only|--skip-plans]"
            exit 1
            ;;
    esac
done

# Migrate health data and workout library
if [ "$MIGRATE_HEALTH_WORKOUTS" = true ]; then
    echo "Migrating health data and workout library from JSON..."
    python3 src/database/migrate_json_to_db.py
    echo ""
fi

# Migrate athlete data
if [ "$MIGRATE_ATHLETE" = true ]; then
    echo "Migrating athlete data from markdown files..."
    python3 src/database/migrate_athlete_data.py
    echo ""
fi

# Migrate training plans
if [ "$MIGRATE_PLANS" = true ]; then
    echo "Migrating training plans from markdown files..."
    python3 src/database/migrate_training_plans.py
    echo ""
fi

echo "=========================================="
echo "Data migration complete!"
echo "=========================================="
