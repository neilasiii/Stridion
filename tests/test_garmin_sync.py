#!/usr/bin/env python3
"""
Unit tests for garmin_sync.py

Run with: python3 -m pytest tests/test_garmin_sync.py -v
or: python3 tests/test_garmin_sync.py
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.garmin_sync import merge_data, retry_with_backoff


class TestMergeData(unittest.TestCase):
    """Test the merge_data function"""

    def test_merge_deduplicates_by_date(self):
        """Test that merge_data removes duplicates based on date field"""
        existing = [{'date': '2025-01-01', 'value': 1}]
        new = [{'date': '2025-01-01', 'value': 2}]
        result = merge_data(existing, new, 'date')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['value'], 2)  # New value should overwrite old

    def test_merge_sorts_newest_first(self):
        """Test that merge_data sorts entries newest first"""
        data = [
            {'date': '2025-01-01', 'value': 1},
            {'date': '2025-01-03', 'value': 3},
            {'date': '2025-01-02', 'value': 2}
        ]
        result = merge_data([], data, 'date')

        self.assertEqual(result[0]['date'], '2025-01-03')
        self.assertEqual(result[1]['date'], '2025-01-02')
        self.assertEqual(result[2]['date'], '2025-01-01')

    def test_merge_handles_list_format(self):
        """Test that merge_data handles list format (e.g., RHR data)"""
        existing = [['2025-01-01T12:00:00', 45]]
        new = [['2025-01-02T12:00:00', 46]]
        result = merge_data(existing, new)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], '2025-01-02T12:00:00')  # Newest first
        self.assertEqual(result[1][0], '2025-01-01T12:00:00')

    def test_merge_handles_empty_lists(self):
        """Test that merge_data handles empty input lists"""
        result = merge_data([], [], 'date')
        self.assertEqual(result, [])

    def test_merge_preserves_existing_when_no_new(self):
        """Test that existing data is preserved when no new data"""
        existing = [{'date': '2025-01-01', 'value': 1}]
        result = merge_data(existing, [], 'date')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['value'], 1)

    def test_merge_with_timestamp_key(self):
        """Test merge_data with timestamp key field (weight data)"""
        existing = [{'timestamp': '2025-01-01T08:00:00', 'weight_lbs': 165}]
        new = [{'timestamp': '2025-01-02T08:00:00', 'weight_lbs': 164}]
        result = merge_data(existing, new, 'timestamp')

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['timestamp'], '2025-01-02T08:00:00')


class TestRetryWithBackoff(unittest.TestCase):
    """Test the retry_with_backoff function"""

    def test_retry_succeeds_on_first_try(self):
        """Test that retry returns immediately on success"""
        def success_func():
            return "success"

        result = retry_with_backoff(success_func, quiet=True)
        self.assertEqual(result, "success")

    def test_retry_succeeds_after_failures(self):
        """Test that retry succeeds after network failures"""
        self.attempt = 0

        def flaky_func():
            self.attempt += 1
            if self.attempt < 2:
                raise Exception("Connection timeout error")
            return "success"

        result = retry_with_backoff(flaky_func, max_retries=3, quiet=True)
        self.assertEqual(result, "success")
        self.assertEqual(self.attempt, 2)

    def test_retry_fails_after_max_retries(self):
        """Test that retry raises exception after max retries"""
        def always_fails():
            raise ValueError("Permanent error")

        with self.assertRaises(ValueError):
            retry_with_backoff(always_fails, max_retries=2, quiet=True)

    def test_retry_handles_rate_limit(self):
        """Test that retry specifically handles rate limit errors"""
        self.attempt = 0

        def rate_limited():
            self.attempt += 1
            if self.attempt < 2:
                raise Exception("429 Too Many Requests")
            return "success"

        result = retry_with_backoff(rate_limited, max_retries=3, quiet=True)
        self.assertEqual(result, "success")


class TestUnitConversions(unittest.TestCase):
    """Test unit conversion constants"""

    def test_meters_to_miles(self):
        """Test meters to miles conversion"""
        from src.garmin_sync import METERS_TO_MILES

        # 5000 meters = ~3.107 miles
        miles = 5000 / METERS_TO_MILES
        self.assertAlmostEqual(miles, 3.107, places=2)

    def test_ms_to_mph(self):
        """Test m/s to mph conversion"""
        from src.garmin_sync import MS_TO_MPH

        # 4.47 m/s = ~10 mph
        mph = 4.47 * MS_TO_MPH
        self.assertAlmostEqual(mph, 10.0, places=1)

    def test_grams_to_lbs(self):
        """Test grams to pounds conversion"""
        from src.garmin_sync import GRAMS_TO_LBS

        # 75000 grams = ~165.35 lbs
        lbs = 75000 / GRAMS_TO_LBS
        self.assertAlmostEqual(lbs, 165.35, places=2)

    def test_minutes_to_hours(self):
        """Test minutes to hours conversion"""
        from src.garmin_sync import MINUTES_TO_HOURS

        # 420 minutes = 7 hours
        hours = 420 / MINUTES_TO_HOURS
        self.assertEqual(hours, 7.0)

    def test_milliseconds_to_seconds(self):
        """Test milliseconds to seconds conversion"""
        from src.garmin_sync import MILLISECONDS_TO_SECONDS

        # 5000 milliseconds = 5 seconds
        seconds = 5000 / MILLISECONDS_TO_SECONDS
        self.assertEqual(seconds, 5.0)


class TestSystemTimestamps(unittest.TestCase):
    """Test system timestamp functions"""

    def test_utc_now_returns_utc_timestamp(self):
        """Test that utc_now returns UTC timestamp for system operations"""
        from src.garmin_sync import utc_now

        result = utc_now()
        # Should have timezone info
        self.assertTrue(result.endswith("+00:00") or "+" in result or "Z" in result)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
