#!/bin/bash
# Manage athlete data in the database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Show usage
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  migrate               Migrate athlete data from markdown to database"
    echo "  show-profile          Show athlete profile information"
    echo "  show-status           Show current training status"
    echo "  show-prefs            Show communication preferences"
    echo "  list-races            List all races"
    echo "  list-docs             List all athlete documents"
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
        echo "Migrating athlete data from markdown files..."
        python3 src/database/migrate_athlete_data.py
        ;;

    show-profile)
        echo "Athlete Profile:"
        echo "================"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT id, name, email, is_active, created_at FROM athlete_profiles;"
        ;;

    show-status)
        echo "Current Training Status:"
        echo "========================"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT vdot_prescribed, vdot_current, current_phase, weekly_volume_hours, weekly_run_count, valid_from FROM training_status WHERE valid_until IS NULL;"
        ;;

    show-prefs)
        echo "Communication Preferences:"
        echo "=========================="
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT detail_level, include_paces, show_weekly_mileage, include_heart_rate_targets FROM communication_preferences;"
        ;;

    list-races)
        echo "Races:"
        echo "======"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT name, date, distance, priority, status, goal_time_a FROM races ORDER BY date;"
        ;;

    list-docs)
        echo "Athlete Documents:"
        echo "=================="
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT id, document_type, title, version, is_current, updated_at FROM athlete_documents WHERE is_current = true ORDER BY document_type;"
        ;;

    *)
        echo "Unknown command: $COMMAND"
        echo ""
        show_usage
        ;;
esac
