#!/usr/bin/env python3
"""
Diagnostic script to test Garmin Connect API methods for VO2 max and weight data.
"""

import os
import sys
from datetime import date, timedelta
from garminconnect import Garmin

def test_vo2_max_methods(client):
    """Test various methods to fetch VO2 max data."""
    print("\n" + "="*60)
    print("Testing VO2 Max Methods")
    print("="*60)

    today = date.today()
    test_date = today - timedelta(days=7)  # Test with recent date

    # Method 1: get_stats
    print(f"\n1. Testing get_stats('{test_date.isoformat()}')...")
    try:
        stats = client.get_stats(test_date.isoformat())
        print(f"   Type: {type(stats)}")
        if stats:
            print(f"   Keys: {list(stats.keys()) if isinstance(stats, dict) else 'N/A'}")
            if isinstance(stats, dict) and 'vo2Max' in stats:
                print(f"   ✓ Found vo2Max: {stats['vo2Max']}")
            else:
                print(f"   ✗ No vo2Max field in stats")
                print(f"   Full response: {stats}")
        else:
            print(f"   ✗ No stats returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 2: get_user_summary (latest stats)
    print(f"\n2. Testing get_user_summary('{test_date.isoformat()}')...")
    try:
        summary = client.get_user_summary(test_date.isoformat())
        print(f"   Type: {type(summary)}")
        if summary:
            print(f"   Keys: {list(summary.keys()) if isinstance(summary, dict) else 'N/A'}")
            # Check for VO2 max in various possible locations
            if isinstance(summary, dict):
                if 'vo2Max' in summary:
                    print(f"   ✓ Found vo2Max: {summary['vo2Max']}")
                elif 'vo2MaxValue' in summary:
                    print(f"   ✓ Found vo2MaxValue: {summary['vo2MaxValue']}")
                else:
                    print(f"   ✗ No VO2 max field found")
                    print(f"   Full response: {summary}")
        else:
            print(f"   ✗ No summary returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 3: get_max_metrics
    print(f"\n3. Testing get_max_metrics('{test_date.isoformat()}')...")
    try:
        metrics = client.get_max_metrics(test_date.isoformat())
        print(f"   Type: {type(metrics)}")
        if metrics:
            print(f"   Keys: {list(metrics.keys()) if isinstance(metrics, dict) else 'N/A'}")
            print(f"   Full response: {metrics}")
        else:
            print(f"   ✗ No metrics returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 4: get_stats_and_body
    print(f"\n4. Testing get_stats_and_body('{test_date.isoformat()}')...")
    try:
        stats_body = client.get_stats_and_body(test_date.isoformat())
        print(f"   Type: {type(stats_body)}")
        if stats_body:
            print(f"   Keys: {list(stats_body.keys()) if isinstance(stats_body, dict) else 'N/A'}")
            # Look for VO2 max in various locations
            if isinstance(stats_body, dict):
                vo2_found = False
                for key in ['vo2Max', 'vo2MaxValue', 'maxMetrics']:
                    if key in stats_body:
                        print(f"   ✓ Found {key}: {stats_body[key]}")
                        vo2_found = True
                if not vo2_found:
                    print(f"   Full response: {stats_body}")
        else:
            print(f"   ✗ No stats/body returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 5: get_personal_record
    print(f"\n5. Testing get_personal_record()...")
    try:
        pr = client.get_personal_record()
        print(f"   Type: {type(pr)}")
        if pr:
            if isinstance(pr, dict):
                print(f"   Keys: {list(pr.keys())}")
                # Look for VO2 max
                if 'vo2Max' in pr or 'personalRecords' in pr:
                    print(f"   Sample data: {pr}")
            else:
                print(f"   Full response: {pr}")
        else:
            print(f"   ✗ No personal records returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 6: Check available methods
    print(f"\n6. Checking for VO2-related methods in Garmin client...")
    vo2_methods = [m for m in dir(client) if 'vo2' in m.lower() or 'max' in m.lower()]
    print(f"   Found methods: {vo2_methods}")


def test_weight_methods(client):
    """Test various methods to fetch weight data."""
    print("\n" + "="*60)
    print("Testing Weight Methods")
    print("="*60)

    today = date.today()
    start_date = today - timedelta(days=30)
    end_date = today

    # Method 1: get_weigh_ins
    print(f"\n1. Testing get_weigh_ins('{start_date.isoformat()}', '{end_date.isoformat()}')...")
    try:
        weigh_ins = client.get_weigh_ins(start_date.isoformat(), end_date.isoformat())
        print(f"   Type: {type(weigh_ins)}")
        if weigh_ins:
            print(f"   Keys: {list(weigh_ins.keys()) if isinstance(weigh_ins, dict) else 'N/A'}")
            if isinstance(weigh_ins, dict):
                if 'dateWeightList' in weigh_ins:
                    count = len(weigh_ins['dateWeightList']) if weigh_ins['dateWeightList'] else 0
                    print(f"   ✓ Found dateWeightList: {count} entries")
                    if count > 0:
                        print(f"   Sample entry: {weigh_ins['dateWeightList'][0]}")
                else:
                    print(f"   ✗ No dateWeightList field")
                    print(f"   Full response: {weigh_ins}")
        else:
            print(f"   ✗ No weigh-ins returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 2: get_daily_weigh_ins
    print(f"\n2. Testing get_daily_weigh_ins('{end_date.isoformat()}')...")
    try:
        daily_weigh_ins = client.get_daily_weigh_ins(end_date.isoformat())
        print(f"   Type: {type(daily_weigh_ins)}")
        if daily_weigh_ins:
            print(f"   Keys: {list(daily_weigh_ins.keys()) if isinstance(daily_weigh_ins, dict) else 'N/A'}")
            print(f"   Full response: {daily_weigh_ins}")
        else:
            print(f"   ✗ No daily weigh-ins returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 3: get_body_composition
    print(f"\n3. Testing get_body_composition('{end_date.isoformat()}')...")
    try:
        body_comp = client.get_body_composition(end_date.isoformat())
        print(f"   Type: {type(body_comp)}")
        if body_comp:
            print(f"   Keys: {list(body_comp.keys()) if isinstance(body_comp, dict) else 'N/A'}")
            print(f"   Full response: {body_comp}")
        else:
            print(f"   ✗ No body composition returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 4: get_stats_and_body (also for weight)
    print(f"\n4. Testing get_stats_and_body('{end_date.isoformat()}') for weight...")
    try:
        stats_body = client.get_stats_and_body(end_date.isoformat())
        print(f"   Type: {type(stats_body)}")
        if stats_body:
            if isinstance(stats_body, dict):
                # Look for weight-related keys
                weight_keys = [k for k in stats_body.keys() if 'weight' in k.lower() or 'body' in k.lower()]
                if weight_keys:
                    print(f"   ✓ Found weight-related keys: {weight_keys}")
                    for key in weight_keys:
                        print(f"     {key}: {stats_body[key]}")
                else:
                    print(f"   All keys: {list(stats_body.keys())}")
        else:
            print(f"   ✗ No stats/body returned")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    # Method 5: Check available methods
    print(f"\n5. Checking for weight-related methods in Garmin client...")
    weight_methods = [m for m in dir(client) if 'weight' in m.lower() or 'body' in m.lower()]
    print(f"   Found methods: {weight_methods}")


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
    test_vo2_max_methods(client)
    test_weight_methods(client)

    print("\n" + "="*60)
    print("Diagnostic tests complete")
    print("="*60)


if __name__ == '__main__':
    main()
