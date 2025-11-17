#!/usr/bin/env python3
"""
Performance Prediction Module

Predicts race performance based on:
- Current VDOT and VO2 max
- Training load (fitness/fatigue)
- Recovery status
- Training phase
- Historical performance trends

Provides confidence-adjusted race time predictions accounting for:
- Incomplete taper (TSB negative)
- Insufficient training volume (CTL too low)
- Overtraining signals (injury risk factors)
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class PerformancePredictor:
    """
    Predict race performance based on comprehensive fitness assessment.
    """

    def __init__(self, cache_file: str):
        """
        Initialize predictor with health data cache.

        Args:
            cache_file: Path to health_data_cache.json
        """
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load health data cache"""
        if not self.cache_file.exists():
            raise FileNotFoundError(f"Cache file not found: {self.cache_file}")

        with open(self.cache_file, 'r') as f:
            return json.load(f)

    def get_current_vdot_estimate(self) -> Tuple[Optional[float], str]:
        """
        VDOT must be specified manually based on recent race performance.

        Automatic estimation from VO2max and workouts is unreliable.
        Use --vdot parameter with value from recent race result.

        Returns:
            Tuple of (None, error message)
        """
        return (None, 'VDOT must be specified manually (use --vdot parameter)')

    def calculate_fitness_adjustment(self) -> Tuple[float, str]:
        """
        Calculate race time adjustment based on fitness/fatigue state.

        Uses Training Stress Balance (TSB) to adjust predictions:
        - TSB > 0: Fresh and ready (faster)
        - TSB < -10: Fatigued (slower)

        Returns:
            Tuple of (adjustment_multiplier, explanation)
        """
        from training_analytics import TrainingLoadAnalyzer

        analyzer = TrainingLoadAnalyzer(str(self.cache_file))
        summary = analyzer.get_training_load_summary()

        if 'error' in summary:
            return (1.0, 'No adjustment (insufficient data)')

        tsb = summary['current_metrics']['tsb']
        ctl = summary['current_metrics']['ctl']

        # TSB adjustment - more aggressive for negative TSB
        if tsb > 10:
            # Well-rested
            tsb_adjustment = 0.97  # 3% faster
            tsb_note = "well-rested (TSB +{:.0f})".format(tsb)
        elif tsb > 5:
            # Fresh
            tsb_adjustment = 0.98  # 2% faster
            tsb_note = "fresh (TSB +{:.0f})".format(tsb)
        elif tsb > -5:
            # Neutral
            tsb_adjustment = 1.0
            tsb_note = "neutral form (TSB {:.0f})".format(tsb)
        elif tsb > -15:
            # Moderately fatigued
            tsb_adjustment = 1.03  # 3% slower
            tsb_note = "moderately fatigued (TSB {:.0f})".format(tsb)
        elif tsb > -25:
            # Significantly fatigued
            tsb_adjustment = 1.03  # 3% slower
            tsb_note = "significantly fatigued (TSB {:.0f})".format(tsb)
        else:
            # Severely overreached
            tsb_adjustment = 1.10  # 10% slower
            tsb_note = "severely overreached (TSB {:.0f})".format(tsb)

        # CTL adjustment (fitness level) - more aggressive for low CTL in marathon
        # For marathon: CTL should be 60-100
        # For half: CTL should be 40-70
        # Adjust if significantly below expected
        ctl_adjustment = 1.0
        ctl_note = ""

        if ctl < 30:
            ctl_adjustment = 1.06  # Low fitness - significant impact
            ctl_note = ", low fitness base (CTL {:.0f})".format(ctl)
        elif ctl < 45:
            ctl_adjustment = 1.03  # Below ideal for marathon
            ctl_note = ", moderate fitness (CTL {:.0f})".format(ctl)
        elif ctl < 60:
            ctl_adjustment = 1.02  # Adequate but not ideal
            ctl_note = ", adequate fitness (CTL {:.0f})".format(ctl)
        else:
            ctl_note = ", good fitness base (CTL {:.0f})".format(ctl)

        total_adjustment = tsb_adjustment * ctl_adjustment
        explanation = tsb_note + ctl_note

        return (total_adjustment, explanation)

    def calculate_recovery_adjustment(self) -> Tuple[float, str]:
        """
        Calculate race time adjustment based on recovery status.

        Uses sleep, RHR, HRV, and readiness to assess recovery.

        Returns:
            Tuple of (adjustment_multiplier, explanation)
        """
        from injury_risk_ml import InjuryRiskPredictor

        predictor = InjuryRiskPredictor(str(self.cache_file))

        # Get individual risk factors
        sleep_risk = predictor.analyze_sleep_risk(days=7)
        rhr_risk = predictor.analyze_rhr_risk(days=7)
        readiness_risk = predictor.analyze_readiness_risk(days=7)

        # Calculate weighted recovery score
        recovery_score = (
            (100 - sleep_risk['risk_score']) * 0.4 +
            (100 - rhr_risk['risk_score']) * 0.3 +
            (100 - readiness_risk['risk_score']) * 0.3
        )

        concerns = []

        # Determine adjustment with more aggressive penalties for poor recovery
        if recovery_score >= 80:
            adjustment = 0.99  # 1% faster
            status = "Excellent recovery"
        elif recovery_score >= 65:
            adjustment = 1.0
            status = "Good recovery"
        elif recovery_score >= 50:
            adjustment = 1.03  # 3% slower
            status = "Moderate recovery concerns"
            if sleep_risk['risk_score'] > 50:
                concerns.append("sleep deprivation")
            if rhr_risk['risk_score'] > 50:
                concerns.append("elevated RHR")
        elif recovery_score >= 35:
            adjustment = 1.06  # 6% slower
            status = "Poor recovery"
            if sleep_risk['risk_score'] > 50:
                concerns.append("sleep deprivation")
            if rhr_risk['risk_score'] > 50:
                concerns.append("elevated RHR")
            if readiness_risk['risk_score'] > 50:
                concerns.append("low readiness")
        else:
            adjustment = 1.09  # 9% slower for critical recovery issues
            status = "Critical recovery deficit"
            if sleep_risk['risk_score'] > 50:
                concerns.append("severe sleep deprivation")
            if rhr_risk['risk_score'] > 50:
                concerns.append("elevated RHR")
            if readiness_risk['risk_score'] > 50:
                concerns.append("low readiness")

        # Additional penalty for severe sleep deprivation specifically
        if sleep_risk['risk_score'] > 70:
            adjustment *= 1.01  # Extra 1% penalty for severe sleep issues
            if "sleep deprivation" in concerns:
                concerns.remove("sleep deprivation")
                concerns.insert(0, "severe sleep deprivation")

        explanation = status
        if concerns:
            explanation += " (" + ", ".join(concerns) + ")"

        return (adjustment, explanation)

    def predict_race_times(self, target_vdot: Optional[float] = None) -> Dict[str, Any]:
        """
        Predict race times with confidence adjustments.

        Args:
            target_vdot: Specific VDOT to use. If None, uses current estimate.

        Returns:
            Dictionary with predictions for all race distances
        """
        from vdot_calculator import VDOTCalculator, RACE_DISTANCES

        calc = VDOTCalculator()

        # Get VDOT
        if target_vdot:
            vdot = target_vdot
            vdot_source = "User-specified"
        else:
            vdot, vdot_source = self.get_current_vdot_estimate()
            if vdot is None:
                return {
                    'error': 'VDOT required',
                    'message': 'Please specify VDOT using --vdot parameter. Calculate from recent race: bash bin/vdot_calculator.sh --race Half 1:55:04'
                }

        # Calculate base predictions
        base_predictions = calc.predict_race_times(vdot)

        # Get adjustments
        fitness_adj, fitness_note = self.calculate_fitness_adjustment()
        recovery_adj, recovery_note = self.calculate_recovery_adjustment()

        # Get Garmin race predictions for comparison
        garmin_predictions = self.cache.get('race_predictions', {})

        # Combined adjustment
        total_adjustment = fitness_adj * recovery_adj

        # Calculate adjusted times
        adjusted_predictions = {}
        for race_name, base_time_str in base_predictions.items():
            # Parse base time
            time_parts = base_time_str.split(':')
            if len(time_parts) == 2:
                base_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
            else:
                base_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])

            # Apply adjustment
            adjusted_seconds = int(base_seconds * total_adjustment)

            # Format adjusted time
            hours = adjusted_seconds // 3600
            minutes = (adjusted_seconds % 3600) // 60
            seconds = adjusted_seconds % 60

            if hours > 0:
                adjusted_time = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                adjusted_time = f"{minutes}:{seconds:02d}"

            # Get Garmin prediction for comparison
            garmin_field_map = {
                '5K': 'time_5k',
                '10K': 'time_10k',
                'Half': 'time_half_marathon',
                'Marathon': 'time_marathon'
            }
            garmin_time = None
            if race_name in garmin_field_map:
                garmin_seconds = garmin_predictions.get(garmin_field_map[race_name])
                if garmin_seconds:
                    g_hours = garmin_seconds // 3600
                    g_minutes = (garmin_seconds % 3600) // 60
                    g_seconds = garmin_seconds % 60
                    if g_hours > 0:
                        garmin_time = f"{g_hours}:{g_minutes:02d}:{g_seconds:02d}"
                    else:
                        garmin_time = f"{g_minutes}:{g_seconds:02d}"

            adjusted_predictions[race_name] = {
                'base_time': base_time_str,
                'adjusted_time': adjusted_time,
                'garmin_prediction': garmin_time,
                'adjustment_pct': round((total_adjustment - 1) * 100, 1)
            }

        return {
            'vdot': vdot,
            'vdot_source': vdot_source,
            'predictions': adjusted_predictions,
            'adjustments': {
                'fitness': {
                    'multiplier': fitness_adj,
                    'note': fitness_note
                },
                'recovery': {
                    'multiplier': recovery_adj,
                    'note': recovery_note
                },
                'total_multiplier': total_adjustment,
                'total_pct': round((total_adjustment - 1) * 100, 1)
            }
        }

    def race_readiness_assessment(self, race_distance: str, days_until_race: int) -> Dict[str, Any]:
        """
        Assess readiness for an upcoming race.

        Args:
            race_distance: Race distance (5K, 10K, Half, Marathon)
            days_until_race: Days until race

        Returns:
            Dictionary with readiness assessment
        """
        from training_analytics import TrainingLoadAnalyzer
        from injury_risk_ml import InjuryRiskPredictor

        # Get training load
        analyzer = TrainingLoadAnalyzer(str(self.cache_file))
        summary = analyzer.get_training_load_summary()

        # Get injury risk
        predictor = InjuryRiskPredictor(str(self.cache_file))
        risk_assessment = predictor.get_comprehensive_risk_assessment()

        # Get predictions
        predictions = self.predict_race_times()

        # Assess readiness
        readiness_score = 0
        readiness_factors = []
        concerns = []
        recommendations = []

        # 1. Training volume (CTL)
        if 'current_metrics' in summary:
            ctl = summary['current_metrics']['ctl']

            if race_distance == 'Marathon':
                if ctl >= 60:
                    readiness_score += 25
                    readiness_factors.append("✓ Strong fitness base")
                elif ctl >= 45:
                    readiness_score += 15
                    readiness_factors.append("~ Moderate fitness base")
                    recommendations.append("Consider increasing weekly volume if time permits")
                else:
                    readiness_score += 5
                    concerns.append("Low fitness base for marathon distance")
                    recommendations.append("Adjust goals based on limited training volume")
            elif race_distance == 'Half':
                if ctl >= 40:
                    readiness_score += 25
                    readiness_factors.append("✓ Strong fitness base")
                else:
                    readiness_score += 15
                    readiness_factors.append("~ Adequate fitness base")

        # 2. Taper status (TSB)
        if 'current_metrics' in summary:
            tsb = summary['current_metrics']['tsb']

            if days_until_race <= 7:
                # Should be tapering
                if tsb > 5:
                    readiness_score += 25
                    readiness_factors.append("✓ Well-tapered and fresh")
                elif tsb > -5:
                    readiness_score += 15
                    readiness_factors.append("~ Taper in progress")
                else:
                    readiness_score += 5
                    concerns.append("Still carrying fatigue close to race")
                    recommendations.append("Prioritize rest and light workouts this week")
            elif days_until_race <= 14:
                # Starting taper
                if tsb > -10:
                    readiness_score += 20
                    readiness_factors.append("✓ Good form entering taper")
                else:
                    readiness_score += 10
                    concerns.append("High fatigue entering taper period")
            else:
                # Training phase - fatigue acceptable
                readiness_score += 15

        # 3. Injury risk
        overall_risk = risk_assessment['overall_risk_score']
        if overall_risk < 30:
            readiness_score += 25
            readiness_factors.append("✓ Low injury risk")
        elif overall_risk < 50:
            readiness_score += 15
            readiness_factors.append("~ Moderate injury risk")
        else:
            readiness_score += 5
            concerns.append(f"Elevated injury risk ({risk_assessment['risk_level']})")
            recommendations.extend(risk_assessment['recommendations'])

        # 4. Recovery status
        recovery_adj, recovery_note = self.calculate_recovery_adjustment()
        if recovery_adj <= 1.0:
            readiness_score += 25
            readiness_factors.append(f"✓ {recovery_note}")
        elif recovery_adj <= 1.02:
            readiness_score += 15
            readiness_factors.append(f"~ {recovery_note}")
        else:
            readiness_score += 5
            concerns.append(recovery_note)
            recommendations.append("Prioritize sleep and recovery")

        # Determine overall readiness
        if readiness_score >= 80:
            readiness_level = "EXCELLENT"
            readiness_summary = "You are well-prepared for this race."
        elif readiness_score >= 60:
            readiness_level = "GOOD"
            readiness_summary = "You are ready to race with minor adjustments."
        elif readiness_score >= 40:
            readiness_level = "FAIR"
            readiness_summary = "You can race, but manage expectations and address concerns."
        else:
            readiness_level = "POOR"
            readiness_summary = "Consider postponing or adjusting race goals significantly."

        return {
            'race_distance': race_distance,
            'days_until_race': days_until_race,
            'readiness_score': readiness_score,
            'readiness_level': readiness_level,
            'readiness_summary': readiness_summary,
            'readiness_factors': readiness_factors,
            'concerns': concerns,
            'recommendations': recommendations,
            'predicted_time': predictions['predictions'].get(race_distance, {}).get('adjusted_time')
        }


def main():
    """Command-line interface for performance prediction"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Performance Prediction')
    parser.add_argument('--cache', type=str,
                       default='data/health/health_data_cache.json',
                       help='Path to health data cache')
    parser.add_argument('--predict', action='store_true',
                       help='Predict race times')
    parser.add_argument('--vdot', type=float,
                       help='Use specific VDOT for predictions')
    parser.add_argument('--race-readiness', type=str, choices=['5K', '10K', 'Half', 'Marathon'],
                       help='Assess readiness for race distance')
    parser.add_argument('--days-until-race', type=int, default=14,
                       help='Days until race (for readiness assessment)')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    # Resolve cache path
    cache_path = Path(args.cache)
    if not cache_path.is_absolute():
        cache_path = Path(__file__).parent.parent / args.cache

    try:
        predictor = PerformancePredictor(str(cache_path))

        if args.predict:
            predictions = predictor.predict_race_times(args.vdot)

            if args.json:
                print(json.dumps(predictions, indent=2))
            else:
                print("\n" + "="*70)
                print("RACE TIME PREDICTIONS")
                print("="*70)

                print(f"\nVDOT: {predictions['vdot']} ({predictions['vdot_source']})")

                adj = predictions['adjustments']
                print(f"\nAdjustments:")
                print(f"  Fitness:  {adj['fitness']['note']}")
                print(f"  Recovery: {adj['recovery']['note']}")
                print(f"  Total adjustment: {adj['total_pct']:+.1f}%")

                print(f"\nPredicted Times:")
                print(f"\n{'Distance':<10} {'Base Time':>10} {'Adjusted':>10} {'Garmin':>10}")
                print("-" * 70)

                for race, data in predictions['predictions'].items():
                    garmin = data['garmin_prediction'] if data['garmin_prediction'] else 'N/A'
                    print(f"{race:<10} {data['base_time']:>10} {data['adjusted_time']:>10} {garmin:>10}")

                print("\n" + "="*70 + "\n")

        elif args.race_readiness:
            assessment = predictor.race_readiness_assessment(args.race_readiness, args.days_until_race)

            if args.json:
                print(json.dumps(assessment, indent=2))
            else:
                print("\n" + "="*70)
                print(f"RACE READINESS ASSESSMENT - {assessment['race_distance']}")
                print("="*70)

                print(f"\nDays Until Race: {assessment['days_until_race']}")
                print(f"Readiness Score: {assessment['readiness_score']}/100")
                print(f"Readiness Level: {assessment['readiness_level']}")
                print(f"\n{assessment['readiness_summary']}")

                if assessment['predicted_time']:
                    print(f"\nPredicted Time: {assessment['predicted_time']}")

                print(f"\nReadiness Factors:")
                for factor in assessment['readiness_factors']:
                    print(f"  {factor}")

                if assessment['concerns']:
                    print(f"\nConcerns:")
                    for concern in assessment['concerns']:
                        print(f"  ⚠ {concern}")

                if assessment['recommendations']:
                    print(f"\nRecommendations:")
                    for rec in assessment['recommendations']:
                        print(f"  • {rec}")

                print("\n" + "="*70 + "\n")

        else:
            parser.print_help()
            return 1

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
