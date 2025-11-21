#!/bin/bash
# Manage users and athlete associations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Show usage
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list-users            List all users"
    echo "  list-athletes         List all athletes"
    echo "  list-associations     List user-athlete associations"
    echo "  create-user <username> <email> <name>    Create new user"
    echo "  link-athlete <user_id> <athlete_id>      Link user to athlete"
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
    list-users)
        echo "Users:"
        echo "======"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT id, username, email, full_name, role, is_active, created_at FROM users ORDER BY id;"
        ;;

    list-athletes)
        echo "Athletes:"
        echo "========="
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT id, name, email, is_active, created_at FROM athlete_profiles ORDER BY id;"
        ;;

    list-associations)
        echo "User-Athlete Associations:"
        echo "=========================="
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "SELECT ua.id, u.username, a.name as athlete_name, ua.relationship, ua.can_view, ua.can_edit, ua.can_coach
             FROM user_athletes ua
             JOIN users u ON ua.user_id = u.id
             JOIN athlete_profiles a ON ua.athlete_id = a.id
             ORDER BY ua.id;"
        ;;

    create-user)
        if [ $# -lt 3 ]; then
            echo "Error: Missing arguments"
            echo "Usage: $0 create-user <username> <email> <full_name>"
            exit 1
        fi
        USERNAME=$1
        EMAIL=$2
        FULL_NAME=$3

        echo "Creating user: $USERNAME ($EMAIL)"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "INSERT INTO users (username, email, full_name, role, is_active)
             VALUES ('$USERNAME', '$EMAIL', '$FULL_NAME', 'athlete', true)
             RETURNING id, username, email;"
        ;;

    link-athlete)
        if [ $# -lt 2 ]; then
            echo "Error: Missing arguments"
            echo "Usage: $0 link-athlete <user_id> <athlete_id>"
            exit 1
        fi
        USER_ID=$1
        ATHLETE_ID=$2

        echo "Linking user $USER_ID to athlete $ATHLETE_ID"
        docker exec -it running-coach-postgres psql -U coach -d running_coach -c \
            "INSERT INTO user_athletes (user_id, athlete_id, relationship, can_view, can_edit, can_coach)
             VALUES ($USER_ID, $ATHLETE_ID, 'self', true, true, false)
             RETURNING id, user_id, athlete_id, relationship;"
        ;;

    *)
        echo "Unknown command: $COMMAND"
        echo ""
        show_usage
        ;;
esac
