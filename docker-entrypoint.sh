#!/bin/bash
set -e

echo "🚀 Starting Running Coach Service..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
until pg_isready -h postgres -U coach; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Check if database is initialized
echo "🔍 Checking database initialization..."
TABLE_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" -eq "0" ]; then
  echo "📊 Database empty - initializing tables..."

  # Run database initialization
  python3 src/database/init_db.py create

  # Run migrations
  alembic upgrade head

  echo "✅ Database initialized successfully!"
else
  echo "✅ Database already initialized ($TABLE_COUNT tables found)"

  # Run any pending migrations
  echo "🔄 Checking for pending migrations..."
  alembic upgrade head
fi

echo "🌐 Starting web server..."
exec python -m src.web.app
