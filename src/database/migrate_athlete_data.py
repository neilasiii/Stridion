"""Migrate athlete data from markdown files to PostgreSQL database."""

import sys
import os
import re
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.connection import get_db_session
from src.database.models import (
    AthleteProfile, TrainingStatus, CommunicationPreference,
    Race, AthleteDocument
)


# Default athlete ID (single-athlete system for now)
DEFAULT_ATHLETE_ID = 1
DEFAULT_ATHLETE_NAME = "Neil Stagner"
DEFAULT_ATHLETE_EMAIL = "neil@example.com"


def parse_communication_preferences(content):
    """Parse communication preferences from markdown content."""
    # Extract detail level
    detail_match = re.search(r'##\s+Detail Level:\s+(\w+)', content)
    detail_level = detail_match.group(1) if detail_match else 'BRIEF'

    # Default preferences
    return {
        'detail_level': detail_level,
        'include_paces': True,
        'show_weekly_mileage': True,
        'provide_calendar_views': True,
        'include_heart_rate_targets': detail_level != 'BRIEF',
        'suggest_alternatives': detail_level in ['STANDARD', 'DETAILED'],
        'offer_modifications': detail_level in ['STANDARD', 'DETAILED'],
        'comment_on_health_trends': True,
    }


def parse_training_status(content):
    """Parse training status from markdown content."""
    status_data = {}

    # Extract VDOT
    vdot_match = re.search(r'VDOT.*?(\d+)-(\d+)', content, re.IGNORECASE)
    if vdot_match:
        status_data['vdot_prescribed'] = float(vdot_match.group(2))
        status_data['vdot_current'] = float(vdot_match.group(1))

    # Extract paces
    pace_patterns = [
        (r'Easy\s*\(E\):\s*([\d:]+)-([\d:]+)', 'easy_pace'),
        (r'Marathon\s*\(M\):\s*([\d:]+)-([\d:]+)', 'marathon_pace'),
        (r'Threshold\s*\(T\):\s*([\d:]+)-([\d:]+)', 'threshold_pace'),
        (r'5K/Interval\s*\(I\):\s*([\d:]+)-([\d:]+)', 'interval_pace'),
    ]

    for pattern, field in pace_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            status_data[field] = {'min': match.group(1), 'max': match.group(2)}

    # Extract phase
    phase_match = re.search(r'Current Phase[:\s]+(.+?)(?:\n|\()', content, re.IGNORECASE)
    if phase_match:
        status_data['current_phase'] = phase_match.group(1).strip()

    # Extract volume
    volume_match = re.search(r'Weekly Volume.*?(\d+)-?(\d+)?\s*hours', content, re.IGNORECASE)
    if volume_match:
        status_data['weekly_volume_hours'] = float(volume_match.group(2) or volume_match.group(1))

    run_count_match = re.search(r'(\d+)\s+runs?\s+per\s+week', content, re.IGNORECASE)
    if run_count_match:
        status_data['weekly_run_count'] = int(run_count_match.group(1))

    return status_data


def parse_races(content):
    """Parse races from upcoming_races.md content."""
    races = []

    # Split by race sections (## headers)
    race_sections = re.split(r'\n###\s+(.+?)\n', content)

    for i in range(1, len(race_sections), 2):
        race_title = race_sections[i].strip()
        race_content = race_sections[i+1] if i+1 < len(race_sections) else ""

        # Skip non-race sections
        if 'Race Priority Definitions' in race_title or 'Notes for Coaches' in race_title or 'Post-Race Review' in race_title:
            continue

        race_data = {
            'name': race_title,
            'status': 'upcoming'
        }

        # Extract date
        date_match = re.search(r'\*\*Date:\*\*\s+(.+)', race_content)
        if date_match:
            try:
                date_str = date_match.group(1).strip()
                race_data['date'] = datetime.strptime(date_str, '%B %d, %Y')
            except:
                # Try alternate formats
                pass

        # Extract location
        loc_match = re.search(r'\*\*Location:\*\*\s+(.+)', race_content)
        if loc_match:
            race_data['location'] = loc_match.group(1).strip()

        # Extract distance
        dist_match = re.search(r'\*\*Distance:\*\*\s+(.+?)(?:\(|$)', race_content)
        if dist_match:
            distance = dist_match.group(1).strip()
            race_data['distance'] = distance

            # Set numeric distance
            if 'Marathon' in distance and 'Half' not in distance:
                race_data['distance_miles'] = 26.2
            elif 'Half Marathon' in distance:
                race_data['distance_miles'] = 13.1
            elif '10K' in distance:
                race_data['distance_miles'] = 6.2
            elif '5K' in distance:
                race_data['distance_miles'] = 3.1

        # Extract priority
        priority_match = re.search(r'\*\*Race Priority:\*\*\s+(.+?)(?:-race|$)', race_content, re.IGNORECASE)
        if priority_match:
            race_data['priority'] = priority_match.group(1).strip() + '-race'

        # Extract goals
        goal_patterns = [
            (r'\*\*A Goal.*?:\*\*\s+Sub\s+([\d:]+)', 'goal_time_a'),
            (r'\*\*B Goal.*?:\*\*\s+Sub\s+([\d:]+)', 'goal_time_b'),
            (r'\*\*C Goal.*?:\*\*\s+Sub\s+([\d:]+)', 'goal_time_c'),
        ]

        for pattern, field in goal_patterns:
            match = re.search(pattern, race_content, re.IGNORECASE)
            if match:
                race_data[field] = match.group(1)

        # Extract actual time (for completed races)
        actual_match = re.search(r'\*\*Actual Finish Time:\*\*\s+([\d:]+)', race_content)
        if actual_match:
            race_data['actual_time'] = actual_match.group(1)
            race_data['status'] = 'completed'

        # Extract strategy notes
        strategy_section = re.search(r'\*\*Race Strategy Notes:\*\*\s+(.+?)(?=\n\*\*|$)', race_content, re.DOTALL)
        if strategy_section:
            race_data['strategy_notes'] = strategy_section.group(1).strip()

        # Only add if we have minimum required fields
        if 'name' in race_data and ('date' in race_data or 'status' in race_data):
            races.append(race_data)

    return races


def migrate_athlete_profile():
    """Create or update athlete profile."""
    print(f"Migrating athlete profile...")

    with get_db_session() as session:
        # Check if athlete exists
        athlete = session.query(AthleteProfile).filter_by(id=DEFAULT_ATHLETE_ID).first()

        if athlete:
            print(f"  - Athlete profile already exists: {athlete.name}")
            return athlete.id
        else:
            # Create new athlete
            athlete = AthleteProfile(
                id=DEFAULT_ATHLETE_ID,
                name=DEFAULT_ATHLETE_NAME,
                email=DEFAULT_ATHLETE_EMAIL,
                is_active=True
            )
            session.add(athlete)
            print(f"  ✓ Created athlete profile: {DEFAULT_ATHLETE_NAME}")
            return athlete.id


def migrate_communication_preferences(athlete_id):
    """Migrate communication preferences."""
    md_path = Path(__file__).parent.parent.parent / 'data' / 'athlete' / 'communication_preferences.md'

    if not md_path.exists():
        print(f"✗ Communication preferences not found: {md_path}")
        return False

    print(f"\nMigrating communication preferences...")

    try:
        with open(md_path, 'r') as f:
            content = f.read()

        prefs_data = parse_communication_preferences(content)

        with get_db_session() as session:
            # Check if preferences exist
            prefs = session.query(CommunicationPreference).filter_by(athlete_id=athlete_id).first()

            if prefs:
                # Update existing
                for key, value in prefs_data.items():
                    setattr(prefs, key, value)
                print(f"  ✓ Updated communication preferences")
            else:
                # Create new
                prefs = CommunicationPreference(athlete_id=athlete_id, **prefs_data)
                session.add(prefs)
                print(f"  ✓ Created communication preferences")

        return True

    except Exception as e:
        print(f"  ✗ Error migrating communication preferences: {e}")
        return False


def migrate_training_status(athlete_id):
    """Migrate current training status."""
    md_path = Path(__file__).parent.parent.parent / 'data' / 'athlete' / 'current_training_status.md'

    if not md_path.exists():
        print(f"✗ Training status not found: {md_path}")
        return False

    print(f"\nMigrating training status...")

    try:
        with open(md_path, 'r') as f:
            content = f.read()

        status_data = parse_training_status(content)
        status_data['athlete_id'] = athlete_id

        with get_db_session() as session:
            # Mark any existing current status as expired
            existing = session.query(TrainingStatus).filter_by(
                athlete_id=athlete_id,
                valid_until=None
            ).all()

            for old_status in existing:
                old_status.valid_until = datetime.utcnow()

            # Create new current status
            new_status = TrainingStatus(**status_data)
            session.add(new_status)
            print(f"  ✓ Created training status (VDOT: {status_data.get('vdot_current', 'N/A')})")

        return True

    except Exception as e:
        print(f"  ✗ Error migrating training status: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_races(athlete_id):
    """Migrate races from upcoming_races.md."""
    md_path = Path(__file__).parent.parent.parent / 'data' / 'athlete' / 'upcoming_races.md'

    if not md_path.exists():
        print(f"✗ Upcoming races not found: {md_path}")
        return False

    print(f"\nMigrating races...")

    try:
        with open(md_path, 'r') as f:
            content = f.read()

        races = parse_races(content)

        with get_db_session() as session:
            migrated = 0
            for race_data in races:
                race_data['athlete_id'] = athlete_id

                # Check if race already exists (by name and date)
                existing = None
                if 'date' in race_data:
                    existing = session.query(Race).filter_by(
                        athlete_id=athlete_id,
                        name=race_data['name'],
                        date=race_data['date']
                    ).first()

                if existing:
                    print(f"  - Skipping '{race_data['name']}' (already exists)")
                else:
                    race = Race(**race_data)
                    session.add(race)
                    print(f"  ✓ Migrated race: {race_data['name']}")
                    migrated += 1

            print(f"✓ Races: {migrated} migrated")

        return True

    except Exception as e:
        print(f"  ✗ Error migrating races: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_documents(athlete_id):
    """Migrate text-based documents (goals, preferences, history, health profile)."""
    athlete_dir = Path(__file__).parent.parent.parent / 'data' / 'athlete'

    documents = [
        ('goals.md', 'goals', 'Athlete Goals'),
        ('training_preferences.md', 'training_preferences', 'Training Preferences'),
        ('training_history.md', 'training_history', 'Training History'),
        ('health_profile.md', 'health_profile', 'Health Profile'),
    ]

    print(f"\nMigrating athlete documents...")

    with get_db_session() as session:
        migrated = 0

        for filename, doc_type, title in documents:
            md_path = athlete_dir / filename

            if not md_path.exists():
                print(f"  - Skipping '{filename}' (not found)")
                continue

            try:
                with open(md_path, 'r') as f:
                    content = f.read()

                # Check if document already exists
                existing = session.query(AthleteDocument).filter_by(
                    athlete_id=athlete_id,
                    document_type=doc_type,
                    is_current=True
                ).first()

                if existing:
                    print(f"  - Skipping '{filename}' (already exists)")
                else:
                    doc = AthleteDocument(
                        athlete_id=athlete_id,
                        document_type=doc_type,
                        title=title,
                        content=content,
                        content_format='markdown',
                        version=1,
                        is_current=True
                    )
                    session.add(doc)
                    print(f"  ✓ Migrated document: {filename}")
                    migrated += 1

            except Exception as e:
                print(f"  ✗ Error migrating '{filename}': {e}")
                continue

        print(f"✓ Documents: {migrated} migrated")

    return True


def main():
    """Run all athlete data migrations."""
    print("=" * 60)
    print("Starting Athlete Data Migration")
    print("=" * 60)

    # Step 1: Create/get athlete profile
    print("\n" + "=" * 60)
    print("ATHLETE PROFILE")
    print("=" * 60)
    athlete_id = migrate_athlete_profile()

    # Step 2: Migrate communication preferences
    print("\n" + "=" * 60)
    print("COMMUNICATION PREFERENCES")
    print("=" * 60)
    prefs_success = migrate_communication_preferences(athlete_id)

    # Step 3: Migrate training status
    print("\n" + "=" * 60)
    print("TRAINING STATUS")
    print("=" * 60)
    status_success = migrate_training_status(athlete_id)

    # Step 4: Migrate races
    print("\n" + "=" * 60)
    print("RACES")
    print("=" * 60)
    races_success = migrate_races(athlete_id)

    # Step 5: Migrate documents
    print("\n" + "=" * 60)
    print("ATHLETE DOCUMENTS")
    print("=" * 60)
    docs_success = migrate_documents(athlete_id)

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Athlete Profile:              ✓ SUCCESS")
    print(f"Communication Preferences:    {'✓ SUCCESS' if prefs_success else '✗ FAILED'}")
    print(f"Training Status:              {'✓ SUCCESS' if status_success else '✗ FAILED'}")
    print(f"Races:                        {'✓ SUCCESS' if races_success else '✗ FAILED'}")
    print(f"Athlete Documents:            {'✓ SUCCESS' if docs_success else '✗ FAILED'}")
    print("=" * 60)

    return all([prefs_success, status_success, races_success, docs_success])


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
