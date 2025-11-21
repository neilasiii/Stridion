"""Migrate training plans from markdown files to PostgreSQL database."""

import sys
import os
import re
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.connection import get_db_session
from src.database.models import TrainingPlan, Race

# Default athlete ID (single-athlete system for now)
DEFAULT_ATHLETE_ID = 1


def parse_plan_metadata(content, filename):
    """Extract metadata from plan content."""
    metadata = {
        'plan_name': filename.replace('.md', '').replace('_', ' ').title(),
        'description': None,
        'plan_type': 'general',
        'start_date': None,
        'end_date': None,
        'goal_race_id': None,
    }

    # Extract title from first heading
    title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
    if title_match:
        metadata['plan_name'] = title_match.group(1).strip()

    # Determine plan type from name/content
    name_lower = filename.lower()
    content_lower = content.lower()

    if 'taper' in name_lower or 'taper' in content_lower:
        metadata['plan_type'] = 'taper'
    elif 'recovery' in name_lower or 'recovery' in content_lower:
        metadata['plan_type'] = 'recovery'
    elif 'base' in name_lower or 'base' in content_lower:
        metadata['plan_type'] = 'base'
    elif 'quality' in name_lower or 'quality' in content_lower:
        metadata['plan_type'] = 'quality'
    elif 'race' in name_lower or 'specific' in name_lower:
        metadata['plan_type'] = 'race_specific'

    # Extract race date
    race_date_match = re.search(r'\*\*Race Date:\*\*\s+(.+)', content)
    if race_date_match:
        try:
            date_str = race_date_match.group(1).strip()
            # Try to parse the date
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d']:
                try:
                    race_date = datetime.strptime(date_str, fmt)
                    metadata['end_date'] = race_date
                    break
                except:
                    continue
        except:
            pass

    # Extract start date if present
    start_date_match = re.search(r'\*\*Start Date:\*\*\s+(.+)', content)
    if start_date_match:
        try:
            date_str = start_date_match.group(1).strip()
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d']:
                try:
                    metadata['start_date'] = datetime.strptime(date_str, fmt)
                    break
                except:
                    continue
        except:
            pass

    # If we have end date but no start date, infer from plan type
    if metadata['end_date'] and not metadata['start_date']:
        if metadata['plan_type'] == 'taper':
            # Taper plans usually 2-3 weeks
            from datetime import timedelta
            metadata['start_date'] = metadata['end_date'] - timedelta(days=21)
        elif metadata['plan_type'] == 'recovery':
            # Recovery plans usually 2-4 weeks after race
            from datetime import timedelta
            metadata['start_date'] = metadata['end_date']
            metadata['end_date'] = metadata['end_date'] + timedelta(days=28)

    # Extract description (first paragraph after title)
    desc_match = re.search(r'^#[^\n]+\n\n(.+?)(?:\n\n|\n#)', content, re.MULTILINE | re.DOTALL)
    if desc_match:
        metadata['description'] = desc_match.group(1).strip()[:500]  # Limit to 500 chars

    return metadata


def find_associated_race(plan_metadata, session):
    """Find the associated race for a plan."""
    if not plan_metadata['end_date']:
        return None

    # Look for races near the end date (within 7 days)
    from datetime import timedelta
    start_window = plan_metadata['end_date'] - timedelta(days=3)
    end_window = plan_metadata['end_date'] + timedelta(days=3)

    race = session.query(Race).filter(
        Race.date >= start_window,
        Race.date <= end_window,
        Race.athlete_id == DEFAULT_ATHLETE_ID
    ).first()

    return race.id if race else None


def migrate_training_plans(athlete_id=DEFAULT_ATHLETE_ID):
    """Migrate training plans from markdown files."""
    plans_dir = Path(__file__).parent.parent.parent / 'data' / 'plans'

    if not plans_dir.exists():
        print(f"✗ Plans directory not found: {plans_dir}")
        return False

    print(f"Migrating training plans from {plans_dir}...")

    try:
        plan_files = list(plans_dir.glob('*.md'))

        if not plan_files:
            print("  - No plan files found")
            return True

        with get_db_session() as session:
            migrated = 0
            skipped = 0

            for plan_file in plan_files:
                try:
                    print(f"\n  Processing: {plan_file.name}")

                    with open(plan_file, 'r') as f:
                        content = f.read()

                    # Parse metadata
                    metadata = parse_plan_metadata(content, plan_file.name)

                    # Find associated race
                    metadata['goal_race_id'] = find_associated_race(metadata, session)
                    if metadata['goal_race_id']:
                        print(f"    - Associated with race ID: {metadata['goal_race_id']}")

                    # Check if plan already exists (by name and athlete)
                    existing = session.query(TrainingPlan).filter_by(
                        athlete_id=athlete_id,
                        plan_name=metadata['plan_name']
                    ).first()

                    if existing:
                        print(f"    - Skipping (already exists)")
                        skipped += 1
                        continue

                    # Create new plan
                    plan = TrainingPlan(
                        athlete_id=athlete_id,
                        plan_name=metadata['plan_name'],
                        description=metadata['description'],
                        plan_type=metadata['plan_type'],
                        start_date=metadata['start_date'],
                        end_date=metadata['end_date'],
                        goal_race_id=metadata['goal_race_id'],
                        content=content,
                        content_format='markdown',
                        version=1,
                        is_current=True,
                        status='active' if metadata['end_date'] and metadata['end_date'] > datetime.utcnow() else 'completed',
                    )

                    session.add(plan)
                    migrated += 1

                    print(f"    ✓ Migrated as '{metadata['plan_type']}' plan")
                    if metadata['start_date']:
                        print(f"      Start: {metadata['start_date'].strftime('%Y-%m-%d')}")
                    if metadata['end_date']:
                        print(f"      End: {metadata['end_date'].strftime('%Y-%m-%d')}")

                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    continue

            print(f"\n✓ Training plans: {migrated} migrated, {skipped} skipped")
            return True

    except Exception as e:
        print(f"✗ Error during training plan migration: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run training plan migration."""
    print("=" * 60)
    print("Training Plan Migration")
    print("=" * 60)

    success = migrate_training_plans()

    print("\n" + "=" * 60)
    print(f"Migration {'COMPLETE' if success else 'FAILED'}")
    print("=" * 60)

    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
