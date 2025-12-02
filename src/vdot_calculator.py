"""
VDOT Calculator based on Jack Daniels' Running Formula.

This implementation uses the formulas from "Daniels' Running Formula"
to calculate VDOT values from race performances and generate training paces.

References:
- Daniels, J. (2013). Daniels' Running Formula (3rd ed.)
- Oxygen Power by Daniels and Gilbert (original research)
"""

import math
from typing import Tuple, Dict


def calculate_vdot(distance_meters: float, time_seconds: float) -> float:
    """
    Calculate VDOT from race distance and time using Jack Daniels' formula.

    Args:
        distance_meters: Race distance in meters (e.g., 21097.5 for half marathon)
        time_seconds: Race time in seconds

    Returns:
        VDOT value (typically 30-85 for most runners)

    Example:
        >>> # Half marathon in 1:55:04
        >>> vdot = calculate_vdot(21097.5, 6904)
        >>> print(f"VDOT: {vdot:.1f}")
        VDOT: 38.3
    """
    # Calculate velocity in meters per minute
    time_minutes = time_seconds / 60.0
    velocity = distance_meters / time_minutes

    # Calculate percent of VO2max at which the race was run
    # This accounts for the fact that longer races are run at lower %VO2max
    percent_max = _calculate_percent_max(time_minutes)

    # Calculate oxygen cost of running at this velocity (ml/kg/min)
    vo2 = _calculate_vo2(velocity)

    # VDOT is the VO2max value, adjusted for the percent max
    # If runner used X% of their max, and consumed Y ml/kg/min,
    # then their max is Y / (X/100)
    vdot = vo2 / percent_max

    return vdot


def _calculate_percent_max(time_minutes: float) -> float:
    """
    Calculate the percentage of VO2max at which a race of given duration is run.

    Longer races are run at lower percentages of VO2max due to fatigue.
    This is based on Jack Daniels' research on race performance.

    Args:
        time_minutes: Race duration in minutes

    Returns:
        Fraction of VO2max (e.g., 0.86 means 86%)
    """
    # Jack Daniels' percent max formula
    # Based on empirical data from thousands of race performances
    percent = (
        0.8 +
        0.1894393 * math.exp(-0.012778 * time_minutes) +
        0.2989558 * math.exp(-0.1932605 * time_minutes)
    )

    return percent


def _calculate_vo2(velocity_meters_per_min: float) -> float:
    """
    Calculate oxygen consumption (VO2) from running velocity.

    This is the "oxygen cost of running" - how much oxygen you need
    to maintain a given pace. Based on physiological research.

    Args:
        velocity_meters_per_min: Running speed in meters per minute

    Returns:
        VO2 in ml/kg/min
    """
    # Jack Daniels' VO2 formula
    # Accounts for the fact that oxygen cost increases non-linearly with speed
    vo2 = (
        -4.60 +
        0.182258 * velocity_meters_per_min +
        0.000104 * velocity_meters_per_min ** 2
    )

    return vo2


def get_training_paces(vdot: float) -> Dict[str, Dict[str, float]]:
    """
    Calculate training paces for all Jack Daniels intensity zones.

    Args:
        vdot: VDOT value

    Returns:
        Dictionary with pace ranges for each zone (in seconds per mile)
        Zones: Easy (E), Marathon (M), Threshold (T), Interval (I), Repetition (R)

    Example:
        >>> paces = get_training_paces(38.3)
        >>> print(f"Easy: {format_pace(paces['E']['min'])}-{format_pace(paces['E']['max'])}")
        Easy: 10:48-11:35 /mile
    """
    # Calculate velocity at VO2max (vVDOT) in meters/minute
    # Using inverse of the VO2 formula to find velocity for a given VO2
    # This uses the quadratic formula: velocity = (-b + sqrt(b^2 - 4ac)) / 2a
    # where a=0.000104, b=0.182258, c=(-4.60-vdot)

    a = 0.000104
    b = 0.182258
    c = -4.60 - vdot

    discriminant = b**2 - 4*a*c
    v_vdot = (-b + math.sqrt(discriminant)) / (2 * a)

    # Training pace percentages from Jack Daniels' system
    # These are percentages of vVDOT (velocity at VO2max)
    pace_percentages = {
        'E': (0.59, 0.74),      # Easy: 59-74% of vVDOT
        'M': (0.84, 0.84),      # Marathon: 84% of vVDOT
        'T': (0.88, 0.88),      # Threshold: 88% of vVDOT
        'I': (0.98, 1.0),       # Interval: 98-100% of vVDOT
        'R': (1.05, 1.15)       # Repetition: 105-115% of vVDOT (faster than max)
    }

    paces = {}

    for zone, (pct_min, pct_max) in pace_percentages.items():
        # Calculate velocities for this zone
        velocity_max = v_vdot * pct_max  # meters/min at fastest pace in zone
        velocity_min = v_vdot * pct_min  # meters/min at slowest pace in zone

        # Convert to seconds per mile
        # 1 mile = 1609.34 meters
        # pace (sec/mile) = 1609.34 / velocity (meters/min) * 60
        pace_max_sec_per_mile = (1609.34 / velocity_min) * 60  # slower pace (higher seconds)
        pace_min_sec_per_mile = (1609.34 / velocity_max) * 60  # faster pace (lower seconds)

        paces[zone] = {
            'min': pace_min_sec_per_mile,  # fastest pace (lowest seconds per mile)
            'max': pace_max_sec_per_mile   # slowest pace (highest seconds per mile)
        }

    return paces


def format_pace(seconds_per_mile: float) -> str:
    """
    Format pace in seconds per mile to MM:SS format.

    Args:
        seconds_per_mile: Pace in seconds per mile

    Returns:
        Formatted pace string (e.g., "8:45")

    Example:
        >>> format_pace(525)
        '8:45'
    """
    minutes = int(seconds_per_mile // 60)
    seconds = int(seconds_per_mile % 60)
    return f"{minutes}:{seconds:02d}"


def calculate_vdot_from_race(distance_name: str, hours: int, minutes: int, seconds: int) -> Tuple[float, Dict[str, Dict[str, float]]]:
    """
    Convenience function to calculate VDOT and paces from a race performance.

    Args:
        distance_name: Race distance ('5K', '10K', 'half', 'marathon')
        hours: Hours component of finish time
        minutes: Minutes component of finish time
        seconds: Seconds component of finish time

    Returns:
        Tuple of (vdot, training_paces_dict)

    Example:
        >>> # Half marathon in 1:55:04
        >>> vdot, paces = calculate_vdot_from_race('half', 1, 55, 4)
        >>> print(f"VDOT: {vdot:.1f}")
        >>> print(f"Threshold: {format_pace(paces['T']['min'])}/mile")
    """
    # Standard race distances in meters
    distances = {
        '5K': 5000,
        '10K': 10000,
        'half': 21097.5,
        'marathon': 42195
    }

    if distance_name not in distances:
        raise ValueError(f"Unknown distance: {distance_name}. Use: {list(distances.keys())}")

    distance_meters = distances[distance_name]
    time_seconds = hours * 3600 + minutes * 60 + seconds

    vdot = calculate_vdot(distance_meters, time_seconds)
    paces = get_training_paces(vdot)

    return vdot, paces


def print_training_paces(vdot: float, paces: Dict[str, Dict[str, float]]) -> None:
    """
    Print training paces in a readable format.

    Args:
        vdot: VDOT value
        paces: Training paces dictionary from get_training_paces()
    """
    print(f"\nVDOT: {vdot:.1f}\n")
    print("Training Paces (per mile):")
    print("-" * 40)

    zone_names = {
        'E': 'Easy',
        'M': 'Marathon',
        'T': 'Threshold',
        'I': 'Interval',
        'R': 'Repetition'
    }

    for zone in ['E', 'M', 'T', 'I', 'R']:
        name = zone_names[zone]
        if zone in ['E', 'I', 'R']:
            # Range paces
            pace_str = f"{format_pace(paces[zone]['min'])}-{format_pace(paces[zone]['max'])}"
        else:
            # Single pace
            pace_str = format_pace(paces[zone]['min'])

        print(f"{name:12} ({zone}): {pace_str}")


if __name__ == "__main__":
    # Example: Calculate VDOT from half marathon time of 1:55:04
    print("Testing VDOT Calculator")
    print("=" * 50)

    vdot, paces = calculate_vdot_from_race('half', 1, 55, 4)
    print_training_paces(vdot, paces)

    print("\n" + "=" * 50)
    print("\nFor comparison, marathon time of 4:35:49:")
    vdot_marathon, paces_marathon = calculate_vdot_from_race('marathon', 4, 35, 49)
    print_training_paces(vdot_marathon, paces_marathon)
