#!/usr/bin/env python3
"""
Enhanced test script to check Garmin Connect API for heart rate zone data.
Tests the promising get_activity_hr_in_timezones method.
"""

import os
import sys
import json
from datetime import date
from garminconnect import Garmin


def test_activity_hr_zones(client, activity_id):
    """Test the get_activity_hr_in_timezones method with a real activity."""
    print("\n" + "="*60)
    print("Testing Activity HR Zone Data")
    print("="*60)

    print(f"\nTesting get_activity_hr_in_timezones({activity_id})...")
    try:
        hr_zones = client.get_activity_hr_in_timezones(activity_id)
        if hr_zones:
            print(f"   ✓ Data returned!")
            print(f"   Type: {type(hr_zones)}")
            print(f"\n   Full response:")
            print(json.dumps(hr_zones, indent=2))
        else:
            print(f"   ✗ No HR zone data returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")


def test_lactate_threshold(client):
    """Test lactate threshold method (no arguments)."""
    print("\n" + "="*60)
    print("Testing Lactate Threshold")
    print("="*60)

    print(f"\nTesting get_lactate_threshold()...")
    try:
        lt_data = client.get_lactate_threshold()
        if lt_data:
            print(f"   ✓ Data returned!")
            print(f"   Type: {type(lt_data)}")
            print(f"\n   Full response:")
            print(json.dumps(lt_data, indent=2))
        else:
            print(f"   ✗ No lactate threshold data returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")


def test_user_profile_zones(client):
    """Check if user profile or settings contain HR zone data."""
    print("\n" + "="*60)
    print("Testing User Profile for HR Zones")
    print("="*60)

    # Test user profile
    print(f"\n1. Testing get_user_profile()...")
    try:
        profile = client.get_user_profile()
        if profile and isinstance(profile, dict):
            # Look for userData which might contain zone settings
            if 'userData' in profile:
                user_data = profile['userData']
                print(f"   Found userData with keys: {list(user_data.keys())}")

                # Look for HR or zone related fields
                hr_fields = [k for k in user_data.keys() if 'heart' in k.lower() or 'hr' in k.lower() or 'zone' in k.lower() or 'max' in k.lower()]
                if hr_fields:
                    print(f"   ✓ Found HR-related fields: {hr_fields}")
                    for field in hr_fields:
                        print(f"     {field}: {user_data[field]}")
            else:
                print(f"   Keys: {list(profile.keys())}")
        else:
            print(f"   ✗ No profile data returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Test user settings
    print(f"\n2. Testing get_userprofile_settings()...")
    try:
        settings = client.get_userprofile_settings()
        if settings and isinstance(settings, dict):
            # Look for zone or HR related settings
            hr_settings = [k for k in settings.keys() if 'heart' in k.lower() or 'hr' in k.lower() or 'zone' in k.lower() or 'max' in k.lower()]
            if hr_settings:
                print(f"   ✓ Found HR-related settings: {hr_settings}")
                for setting in hr_settings:
                    print(f"     {setting}: {settings[setting]}")
            else:
                print(f"   All settings keys: {list(settings.keys())[:20]}")
        else:
            print(f"   ✗ No settings returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")


def get_recent_activity_id():
    """Get a recent activity ID from the health cache."""
    try:
        with open('data/health/health_data_cache.json', 'r') as f:
            cache = json.load(f)

        activities = cache.get('activities', [])
        if activities:
            # Get most recent running activity
            for activity in activities:
                if activity['activity_type'] == 'RUNNING':
                    return activity['activity_id']

        return None
    except Exception as e:
        print(f"Warning: Could not read health cache: {e}")
        return None


def main():
    # Get credentials from environment
    email = os.getenv('GARMIN_EMAIL')
    password = os.getenv('GARMIN_PASSWORD')

    if not email or not password:
        print("Error: GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set")
        sys.exit(1)

    print("Authenticating with Garmin Connect...")
    try:
        client = Garmin(email, password)
        client.login()
        print("✓ Authentication successful\n")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)

    # Get a recent activity ID to test with
    activity_id = get_recent_activity_id()
    if activity_id:
        print(f"Using recent activity ID: {activity_id}\n")
    else:
        print("Warning: No recent activity found in cache. Using manual ID if needed.\n")
        # Fallback: use the most recent from the output you shared
        activity_id = 20998702041  # From Nov 15

    # Run diagnostic tests
    test_activity_hr_zones(client, activity_id)
    test_lactate_threshold(client)
    test_user_profile_zones(client)

    print("\n" + "="*60)
    print("Diagnostic tests complete")
    print("="*60)
    print("\nNext steps:")
    print("- If get_activity_hr_in_timezones shows HR zone data, we can add it to activities")
    print("- If lactate threshold provides zone boundaries, we can store those")
    print("- If user profile has max HR, we can calculate default zones")


if __name__ == '__main__':
    main()
