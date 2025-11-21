#!/bin/bash
# Migrate data from JSON files to PostgreSQL

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Migrating data from JSON to PostgreSQL..."
python3 src/database/migrate_json_to_db.py

echo ""
echo "Data migration complete!"
