#!/usr/bin/env python3
"""
VDOT Calculator

Implements Jack Daniels' VDOT methodology for:
- Calculating VDOT from race performances
- Generating training paces from VDOT
- Predicting race times from VDOT

Based on:
- "Daniels' Running Formula" by Jack Daniels, PhD
- VDOT tables and pace calculations from proven running science
"""

import json
import sys
import math
import argparse
from typing import Dict, Any, Optional
from pathlib import Path


# VDOT pace calculation constants
# These are empirically derived from Jack Daniels' research
VDOT_VELOCITY_CONSTANTS = {
    'E': 0.65,   # Easy pace: 65% of VDOT
    'M': 0.78,   # Marathon pace: 78% of VDOT
    'T': 0.88,   # Threshold pace: 88% of VDOT
    'I': 0.98,   # Interval pace: 98% of VDOT
    'R': 1.05    # Repetition pace: 105% of VDOT
}

# Standard race distances (meters)
RACE_DISTANCES = {
    '5K': 5000,
    '10K': 10000,
    'Half': 21097.5,
    'Marathon': 42195
}


class VDOTCalculator:
    """
    Calculate VDOT and training paces using Jack Daniels' formulas.
    """

    def __init__(self):
        """Initialize calculator."""
        pass

    def calculate_vo2(self, velocity_mpm: float) -> float:
        """
        Calculate VO2 from running velocity using Jack Daniels' formula.

        VO2 = -4.60 + 0.182258 * v + 0.000104 * v²
        where v is velocity in meters/minute

        Args:
            velocity_mpm: Velocity in meters per minute

        Returns:
            VO2 in ml/kg/min
        """
        v = velocity_mpm
        vo2 = -4.60 + 0.182258 * v + 0.000104 * (v ** 2)
        return vo2

    def calculate_percent_max(self, time_seconds: float) -> float:
        """
        Calculate percentage of VO2max based on race duration.

        Uses Jack Daniels' oxygen cost curves accounting for
        the fact that longer efforts can't sustain max VO2.

        Args:
            time_seconds: Race time in seconds

        Returns:
            Percentage of VO2max (0-1.0)
        """
        time_minutes = time_seconds / 60

        # Daniels' continuous formula for percent of VO2max sustainable
        # Based on empirical data from "Daniels' Running Formula"
        # percent = 0.8 + 0.1894393 * e^(-0.012778*t) + 0.2989558 * e^(-0.1932605*t)
        # where t is time in minutes

        import math
        percent = (0.8 +
                  0.1894393 * math.exp(-0.012778 * time_minutes) +
                  0.2989558 * math.exp(-0.1932605 * time_minutes))

        # Clamp to reasonable range
        return max(0.75, min(1.0, percent))

    def calculate_vdot_from_race(self, distance_meters: float, time_seconds: float) -> float:
        """
        Calculate VDOT from race performance.

        This is the gold standard for VDOT calculation.

        Args:
            distance_meters: Race distance in meters
            time_seconds: Finish time in seconds

        Returns:
            VDOT value (rounded to 1 decimal)
        """
        # Calculate velocity (meters per minute)
        velocity_mpm = distance_meters / (time_seconds / 60)

        # Calculate VO2 at this velocity
        vo2 = self.calculate_vo2(velocity_mpm)

        # Adjust for percentage of VO2max sustainable at this duration
        percent_max = self.calculate_percent_max(time_seconds)

        # VDOT = actual VO2 / percentage sustainable
        vdot = vo2 / percent_max

        return round(vdot, 1)

    def get_training_paces(self, vdot: float) -> Dict[str, str]:
        """
        Calculate training paces for a given VDOT.

        Args:
            vdot: VDOT value

        Returns:
            Dictionary of training pace ranges (min:sec per mile)
        """
        paces = {}

        for pace_type, velocity_factor in VDOT_VELOCITY_CONSTANTS.items():
            # Calculate velocity for this pace type
            vo2_target = vdot * velocity_factor

            # Solve for velocity from VO2 (inverse of calculate_vo2)
            # VO2 = -4.60 + 0.182258*v + 0.000104*v²
            # Rearranged: 0.000104*v² + 0.182258*v - (VO2 + 4.60) = 0
            a = 0.000104
            b = 0.182258
            c = -(vo2_target + 4.60)

            # Quadratic formula
            discriminant = b**2 - 4*a*c
            if discriminant < 0:
                paces[pace_type] = "N/A"
                continue

            velocity_mpm = (-b + math.sqrt(discriminant)) / (2 * a)

            # Convert to pace per mile
            meters_per_mile = 1609.34
            minutes_per_mile = meters_per_mile / velocity_mpm

            # Easy pace gets a range (slower end)
            if pace_type == 'E':
                slower_pace = minutes_per_mile * 1.04  # 4% slower upper bound
                min_min = int(minutes_per_mile)
                min_sec = int((minutes_per_mile - min_min) * 60)
                max_min = int(slower_pace)
                max_sec = int((slower_pace - max_min) * 60)
                paces[pace_type] = f"{min_min}:{min_sec:02d}-{max_min}:{max_sec:02d}"
            # Marathon pace gets narrow range
            elif pace_type == 'M':
                faster_pace = minutes_per_mile * 0.98
                slower_pace = minutes_per_mile * 1.02
                min_min = int(faster_pace)
                min_sec = int((faster_pace - min_min) * 60)
                max_min = int(slower_pace)
                max_sec = int((slower_pace - max_min) * 60)
                paces[pace_type] = f"{min_min}:{min_sec:02d}-{max_min}:{max_sec:02d}"
            else:
                # Threshold, Interval, Repetition get narrow ranges
                faster_pace = minutes_per_mile * 0.98
                slower_pace = minutes_per_mile * 1.02
                min_min = int(faster_pace)
                min_sec = int((faster_pace - min_min) * 60)
                max_min = int(slower_pace)
                max_sec = int((slower_pace - max_min) * 60)
                paces[pace_type] = f"{min_min}:{min_sec:02d}-{max_min}:{max_sec:02d}"

        return paces

    def predict_race_times(self, vdot: float) -> Dict[str, str]:
        """
        Predict race times for standard distances based on VDOT.

        Args:
            vdot: VDOT value

        Returns:
            Dictionary of predicted race times (formatted as H:MM:SS or MM:SS)
        """
        predictions = {}

        for race_name, distance_meters in RACE_DISTANCES.items():
            # Estimate race time by iterating to find time where calculated VDOT matches input
            # Use binary search for efficiency
            min_time = 300  # 5 minutes minimum
            max_time = 21600  # 6 hours maximum
            tolerance = 0.5  # VDOT tolerance

            best_time = None
            iterations = 0
            max_iterations = 50

            while iterations < max_iterations:
                test_time = (min_time + max_time) / 2
                test_vdot = self.calculate_vdot_from_race(distance_meters, test_time)

                if abs(test_vdot - vdot) < tolerance:
                    best_time = test_time
                    break
                elif test_vdot < vdot:
                    # Need to go faster (less time)
                    max_time = test_time
                else:
                    # Need to go slower (more time)
                    min_time = test_time

                iterations += 1

            if best_time:
                total_seconds = int(best_time)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60

                if hours > 0:
                    predictions[race_name] = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    predictions[race_name] = f"{minutes}:{seconds:02d}"

        return predictions


def parse_time(time_str: str) -> int:
    """
    Parse time string to seconds.

    Supports formats:
    - HH:MM:SS
    - MM:SS
    - SS

    Args:
        time_str: Time string

    Returns:
        Total seconds
    """
    parts = time_str.split(':')

    if len(parts) == 3:
        # HH:MM:SS
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        # MM:SS
        return int(parts[0]) * 60 + int(parts[1])
    else:
        # Just seconds
        return int(parts[0])


def main():
    parser = argparse.ArgumentParser(
        description='VDOT Calculator using Jack Daniels methodology'
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--race', nargs=2, metavar=('DISTANCE', 'TIME'),
                      help='Calculate VDOT from race (e.g., --race Marathon 3:45:00)')
    group.add_argument('--vdot', type=float,
                      help='Get training paces for VDOT value')
    group.add_argument('--predict', type=float,
                      help='Predict race times for VDOT value')

    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    calc = VDOTCalculator()

    if args.race:
        distance_name, time_str = args.race

        if distance_name not in RACE_DISTANCES:
            print(f"Error: Unknown distance '{distance_name}'", file=sys.stderr)
            print(f"Valid distances: {', '.join(RACE_DISTANCES.keys())}", file=sys.stderr)
            sys.exit(1)

        try:
            time_seconds = parse_time(time_str)
        except ValueError:
            print(f"Error: Invalid time format '{time_str}'", file=sys.stderr)
            print("Use HH:MM:SS, MM:SS, or SS format", file=sys.stderr)
            sys.exit(1)

        distance_meters = RACE_DISTANCES[distance_name]
        vdot = calc.calculate_vdot_from_race(distance_meters, time_seconds)

        if args.json:
            output = {
                'vdot': vdot,
                'race': {
                    'distance': distance_name,
                    'time': time_str
                }
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"VDOT from {distance_name} in {time_str}: {vdot}")
            print()
            print("Training Paces:")
            paces = calc.get_training_paces(vdot)
            print(f"  Easy (E):       {paces['E']} /mile")
            print(f"  Marathon (M):   {paces['M']} /mile")
            print(f"  Threshold (T):  {paces['T']} /mile")
            print(f"  Interval (I):   {paces['I']} /mile")
            print(f"  Repetition (R): {paces['R']} /mile")

    elif args.vdot:
        vdot = args.vdot
        paces = calc.get_training_paces(vdot)

        if args.json:
            output = {
                'vdot': vdot,
                'paces': paces
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Training Paces for VDOT {vdot}:")
            print(f"  Easy (E):       {paces['E']} /mile")
            print(f"  Marathon (M):   {paces['M']} /mile")
            print(f"  Threshold (T):  {paces['T']} /mile")
            print(f"  Interval (I):   {paces['I']} /mile")
            print(f"  Repetition (R): {paces['R']} /mile")

    elif args.predict:
        vdot = args.predict
        predictions = calc.predict_race_times(vdot)

        if args.json:
            output = {
                'vdot': vdot,
                'predictions': predictions
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Race Time Predictions for VDOT {vdot}:")
            print(f"  5K        : {predictions.get('5K', 'N/A')}")
            print(f"  10K       : {predictions.get('10K', 'N/A')}")
            print(f"  Half      : {predictions.get('Half', 'N/A')}")
            print(f"  Marathon  : {predictions.get('Marathon', 'N/A')}")


if __name__ == '__main__':
    main()
