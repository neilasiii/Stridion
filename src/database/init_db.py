"""Database initialization script."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.connection import engine, init_db
from src.database.models import Base


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    try:
        init_db()
        print("✓ Database tables created successfully!")

        # Print table names
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")

        return True
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return False


def drop_tables():
    """Drop all database tables (use with caution!)."""
    response = input("Are you sure you want to DROP ALL TABLES? This cannot be undone! (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        return False

    print("Dropping all database tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped successfully!")
        return True
    except Exception as e:
        print(f"✗ Error dropping tables: {e}")
        return False


def reset_database():
    """Drop and recreate all tables (use with caution!)."""
    response = input("Are you sure you want to RESET THE DATABASE? All data will be lost! (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        return False

    print("Resetting database...")
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("✓ Dropped existing tables")

        # Create all tables
        init_db()
        print("✓ Created new tables")

        print("\n✓ Database reset successfully!")
        return True
    except Exception as e:
        print(f"✗ Error resetting database: {e}")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Database initialization and management')
    parser.add_argument('action', choices=['create', 'drop', 'reset'],
                       help='Action to perform: create tables, drop tables, or reset database')

    args = parser.parse_args()

    if args.action == 'create':
        success = create_tables()
    elif args.action == 'drop':
        success = drop_tables()
    elif args.action == 'reset':
        success = reset_database()
    else:
        print(f"Unknown action: {args.action}")
        success = False

    sys.exit(0 if success else 1)
