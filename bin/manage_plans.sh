#!/bin/bash
# Manage training plans

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Show usage
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  migrate               Migrate training plans from markdown files"
    echo "  list                  List all training plans"
    echo "  list-active           List active training plans"
    echo "  show <plan_id>        Show plan details"
    echo "  by-athlete <athlete_id>   Show plans for specific athlete"
    echo "  by-race <race_id>     Show plans for specific race"
    echo ""
    exit 1
}

# Check if command provided
if [ $# -eq 0 ]; then
    show_usage
fi

COMMAND=$1
shift

case $COMMAND in
    migrate)
        echo "Migrating training plans from markdown files..."
        python3 src/database/migrate_training_plans.py
        ;;

    list)
        echo "All Training Plans:"
        echo "==================="
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT id, plan_name, plan_type, start_date::date, end_date::date, status, version, is_current
             FROM training_plans
             ORDER BY start_date DESC, id DESC;"
        ;;

    list-active)
        echo "Active Training Plans:"
        echo "======================"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT id, athlete_id, plan_name, plan_type, start_date::date, end_date::date, status
             FROM training_plans
             WHERE status = 'active' AND is_current = true
             ORDER BY start_date;"
        ;;

    show)
        if [ $# -lt 1 ]; then
            echo "Error: Missing plan_id"
            echo "Usage: $0 show <plan_id>"
            exit 1
        fi
        PLAN_ID=$1

        echo "Training Plan Details:"
        echo "======================"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT * FROM training_plans WHERE id = $PLAN_ID;"
        ;;

    by-athlete)
        if [ $# -lt 1 ]; then
            echo "Error: Missing athlete_id"
            echo "Usage: $0 by-athlete <athlete_id>"
            exit 1
        fi
        ATHLETE_ID=$1

        echo "Training Plans for Athlete $ATHLETE_ID:"
        echo "========================================"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT id, plan_name, plan_type, start_date::date, end_date::date, status, version
             FROM training_plans
             WHERE athlete_id = $ATHLETE_ID AND is_current = true
             ORDER BY start_date DESC;"
        ;;

    by-race)
        if [ $# -lt 1 ]; then
            echo "Error: Missing race_id"
            echo "Usage: $0 by-race <race_id>"
            exit 1
        fi
        RACE_ID=$1

        echo "Training Plans for Race $RACE_ID:"
        echo "=================================="
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT tp.id, tp.plan_name, tp.plan_type, tp.start_date::date, tp.end_date::date, r.name as race_name
             FROM training_plans tp
             JOIN races r ON tp.goal_race_id = r.id
             WHERE tp.goal_race_id = $RACE_ID AND tp.is_current = true
             ORDER BY tp.start_date;"
        ;;

    *)
        echo "Unknown command: $COMMAND"
        echo ""
        show_usage
        ;;
esac
