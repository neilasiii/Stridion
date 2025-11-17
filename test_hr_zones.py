#!/usr/bin/env python3
"""
Test script to check if Garmin Connect API provides heart rate zone data.
"""

import os
import sys
import json
from datetime import date
from garminconnect import Garmin


def test_hr_zone_methods(client):
    """Test various methods that might contain HR zone data."""
    print("\n" + "="*60)
    print("Testing Heart Rate Zone Methods")
    print("="*60)

    # Method 1: get_user_profile
    print(f"\n1. Testing get_user_profile()...")
    try:
        profile = client.get_user_profile()
        if profile:
            print(f"   Type: {type(profile)}")
            if isinstance(profile, dict):
                # Look for HR zone related keys
                hr_keys = [k for k in profile.keys() if 'heart' in k.lower() or 'hr' in k.lower() or 'zone' in k.lower()]
                if hr_keys:
                    print(f"   ✓ Found HR-related keys: {hr_keys}")
                    for key in hr_keys:
                        print(f"     {key}: {profile[key]}")
                else:
                    print(f"   Keys: {list(profile.keys())}")
                    print(f"   (No obvious HR zone keys)")
        else:
            print(f"   ✗ No profile returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 2: get_userprofile_settings
    print(f"\n2. Testing get_userprofile_settings()...")
    try:
        settings = client.get_userprofile_settings()
        if settings:
            print(f"   Type: {type(settings)}")
            if isinstance(settings, dict):
                # Look for HR zone related keys
                hr_keys = [k for k in settings.keys() if 'heart' in k.lower() or 'hr' in k.lower() or 'zone' in k.lower()]
                if hr_keys:
                    print(f"   ✓ Found HR-related keys: {hr_keys}")
                    for key in hr_keys:
                        print(f"     {key}: {settings[key]}")
                else:
                    print(f"   Keys: {list(settings.keys())}")
                    print(f"   (No obvious HR zone keys)")
        else:
            print(f"   ✗ No settings returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 3: get_lactate_threshold
    print(f"\n3. Testing get_lactate_threshold()...")
    try:
        today = date.today()
        lt_data = client.get_lactate_threshold(today.isoformat())
        if lt_data:
            print(f"   Type: {type(lt_data)}")
            print(f"   Data: {json.dumps(lt_data, indent=2)}")
        else:
            print(f"   ✗ No lactate threshold data returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 4: get_heart_rates (check if it has zone info)
    print(f"\n4. Testing get_heart_rates() for today...")
    try:
        today = date.today()
        hr_data = client.get_heart_rates(today.isoformat())
        if hr_data:
            print(f"   Type: {type(hr_data)}")
            if isinstance(hr_data, dict):
                # Look for zone related keys
                zone_keys = [k for k in hr_data.keys() if 'zone' in k.lower()]
                if zone_keys:
                    print(f"   ✓ Found zone-related keys: {zone_keys}")
                    for key in zone_keys:
                        print(f"     {key}: {hr_data[key]}")
                else:
                    print(f"   Keys: {list(hr_data.keys())[:20]}")  # First 20 keys
        else:
            print(f"   ✗ No heart rate data returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 5: Check if training status has zone info
    print(f"\n5. Testing get_training_status() for HR zones...")
    try:
        today = date.today()
        training_status = client.get_training_status(today.isoformat())
        if training_status:
            print(f"   Type: {type(training_status)}")
            if isinstance(training_status, dict):
                # Look for zone or HR keys
                zone_keys = [k for k in training_status.keys() if 'zone' in k.lower() or 'heart' in k.lower()]
                if zone_keys:
                    print(f"   ✓ Found zone/HR-related keys: {zone_keys}")
                    for key in zone_keys:
                        print(f"     {key}: {training_status[key]}")
                else:
                    print(f"   Keys: {list(training_status.keys())}")
        else:
            print(f"   ✗ No training status returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 6: Check available API endpoints
    print(f"\n6. Checking Garmin client for zone-related URLs...")
    zone_attrs = [a for a in dir(client) if 'zone' in a.lower()]
    if zone_attrs:
        print(f"   Found zone-related attributes: {zone_attrs}")
    else:
        print(f"   No zone-related attributes found")


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

    # Run diagnostic tests
    test_hr_zone_methods(client)

    print("\n" + "="*60)
    print("Diagnostic tests complete")
    print("="*60)


if __name__ == '__main__':
    main()
