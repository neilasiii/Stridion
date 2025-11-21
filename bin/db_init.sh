#!/bin/bash
# Initialize the database tables

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Initializing database..."
python3 src/database/init_db.py create

echo ""
echo "Database initialization complete!"
