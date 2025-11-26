#!/bin/bash
#
# Garmin Connect Token Setup Helper
#
# This script helps you set up token-based authentication for Garmin Connect.
# Token-based auth is more reliable for automated/bot access than password auth.
#
# Usage:
#   bash bin/setup_garmin_tokens.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================================================"
echo "Garmin Connect Token-Based Authentication Setup"
echo "========================================================================"
echo ""
echo "Password authentication is often blocked by Garmin's bot protection."
echo "Token-based authentication is more reliable for automated access."
echo ""
echo "Choose an option:"
echo ""
echo "  1. Extract tokens manually (recommended)"
echo "  2. Try password authentication and save tokens"
echo "  3. Test existing tokens"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
  1)
    echo ""
    python3 "$PROJECT_ROOT/src/garmin_token_auth.py" --extract
    ;;
  2)
    echo ""
    python3 "$PROJECT_ROOT/src/garmin_token_auth.py" --test
    ;;
  3)
    echo ""
    python3 "$PROJECT_ROOT/src/garmin_token_auth.py" --test
    ;;
  *)
    echo "Invalid choice"
    exit 1
    ;;
esac
