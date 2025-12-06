#!/usr/bin/env python3
"""
AI Response Validation Module

Validates AI-generated coaching recommendations against actual health data
to detect and prevent hallucinations. This module checks:

1. Metric accuracy (AI claims match actual data)
2. Data freshness (warns if data is stale)
3. Physiological plausibility (values within expected ranges)
4. Confidence scoring (tracks data quality/source)
5. Cross-reference validation (consistency checks)

Usage:
    from ai_validation import validate_ai_response, check_data_freshness

    warnings = validate_ai_response(ai_text, health_data)
    freshness = check_data_freshness(health_data)
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


# Physiological ranges for validation
PHYSIOLOGICAL_RANGES = {
    'rhr': (30, 100),           # Resting heart rate (bpm)
    'hrv': (10, 200),            # Heart rate variability (ms)
    'vo2_max': (20, 85),         # VO2 max (ml/kg/min)
    'sleep_hours': (0, 14),      # Total sleep (hours)
    'sleep_score': (0, 100),     # Sleep quality score
    'training_readiness': (0, 100),  # Readiness score
    'body_battery': (0, 100),    # Body battery level
    'stress': (0, 100),          # Stress level
    'pace_min_per_mile': (4, 20), # Running pace (min/mile)
    'vdot': (20, 85),            # VDOT fitness score
}


class ValidationWarning:
    """Represents a validation warning with severity level."""

    SEVERITY_CRITICAL = "CRITICAL"  # Data fabrication, dangerous recommendation
    SEVERITY_HIGH = "HIGH"          # Significant discrepancy, likely hallucination
    SEVERITY_MEDIUM = "MEDIUM"      # Moderate concern, needs review
    SEVERITY_LOW = "LOW"            # Minor issue, informational only

    def __init__(self, severity: str, category: str, message: str, details: Dict[str, Any] = None):
        self.severity = severity
        self.category = category
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def __repr__(self):
        return f"[{self.severity}] {self.category}: {self.message}"

    def to_dict(self):
        return {
            'severity': self.severity,
            'category': self.category,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }


def check_data_freshness(health_data: Dict[str, Any]) -> Tuple[bool, Optional[ValidationWarning]]:
    """
    Check if health data is fresh enough for coaching decisions.

    Args:
        health_data: Health data cache dictionary

    Returns:
        (is_fresh, warning) - True if data is fresh, warning if stale
    """
    if not health_data or 'last_updated' not in health_data:
        return False, ValidationWarning(
            ValidationWarning.SEVERITY_CRITICAL,
            "data_freshness",
            "Health data cache is missing or has no timestamp",
            {'last_updated': None}
        )

    try:
        last_updated = datetime.fromisoformat(health_data['last_updated'].replace('Z', '+00:00'))
        age_hours = (datetime.now() - last_updated.replace(tzinfo=None)).total_seconds() / 3600

        if age_hours > 168:  # 7 days
            return False, ValidationWarning(
                ValidationWarning.SEVERITY_CRITICAL,
                "data_freshness",
                f"Health data is {age_hours:.1f} hours old (>7 days). Refusing recommendations.",
                {'age_hours': age_hours, 'last_updated': health_data['last_updated']}
            )
        elif age_hours > 24:  # 1 day
            return True, ValidationWarning(
                ValidationWarning.SEVERITY_HIGH,
                "data_freshness",
                f"Health data is {age_hours:.1f} hours old. Recommendations may be outdated.",
                {'age_hours': age_hours, 'last_updated': health_data['last_updated']}
            )
        elif age_hours > 2:  # 2 hours
            return True, ValidationWarning(
                ValidationWarning.SEVERITY_LOW,
                "data_freshness",
                f"Health data is {age_hours:.1f} hours old (acceptable but not current).",
                {'age_hours': age_hours, 'last_updated': health_data['last_updated']}
            )
        else:
            return True, None

    except Exception as e:
        return False, ValidationWarning(
            ValidationWarning.SEVERITY_HIGH,
            "data_freshness",
            f"Could not parse last_updated timestamp: {e}",
            {'last_updated': health_data.get('last_updated'), 'error': str(e)}
        )


def extract_metrics_from_text(text: str) -> Dict[str, Any]:
    """
    Extract health metrics mentioned in AI response.

    Args:
        text: AI-generated response text

    Returns:
        Dictionary of extracted metrics with values
    """
    metrics = {}

    # RHR patterns
    rhr_patterns = [
        r'RHR[:\s]+(\d+)',
        r'resting\s+heart\s+rate[:\s]+(\d+)',
        r'heart\s+rate.*?was\s+(\d+)\s*bpm',
        r'RHR.*?was\s+(\d+)\s*bpm',
        r'(\d+)\s*bpm.*?(?:RHR|heart\s+rate)',
    ]
    for pattern in rhr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics['rhr'] = int(match.group(1))
            break

    # HRV patterns
    hrv_patterns = [
        r'HRV[:\s]+(\d+)',
        r'heart\s+rate\s+variability[:\s]+(\d+)',
        r'HRV.*?was\s+(\d+)\s*ms',
        r'(\d+)\s*ms.*?HRV',
    ]
    for pattern in hrv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics['hrv'] = int(match.group(1))
            break

    # Sleep patterns
    sleep_patterns = [
        r'(\d+\.?\d*)\s*hours?\s+(?:of\s+)?sleep',
        r'sleep[:\s]+(\d+\.?\d*)\s*(?:hrs?|hours?)',
    ]
    for pattern in sleep_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics['sleep_hours'] = float(match.group(1))
            break

    # Sleep score
    sleep_score_patterns = [
        r'sleep\s+score[:\s]+(\d+)',
        r'sleep\s+quality[:\s]+(\d+)',
        r'score\s+of\s+(\d+)',
        r'sleep.*?score.*?(\d+)',
    ]
    for pattern in sleep_score_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics['sleep_score'] = int(match.group(1))
            break

    # Training readiness
    readiness_patterns = [
        r'readiness[:\s]+(\d+)',
        r'training\s+readiness[:\s]+(\d+)',
    ]
    for pattern in readiness_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics['training_readiness'] = int(match.group(1))
            break

    # VO2 max
    vo2_patterns = [
        r'VO2\s*max[:\s]+(\d+\.?\d*)',
        r'vo2max[:\s]+(\d+\.?\d*)',
    ]
    for pattern in vo2_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics['vo2_max'] = float(match.group(1))
            break

    return metrics


def get_actual_metrics(health_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract actual metric values from health data cache.

    Args:
        health_data: Health data cache dictionary

    Returns:
        Dictionary of actual metric values
    """
    actual = {}

    # RHR (most recent)
    if 'resting_hr_readings' in health_data and health_data['resting_hr_readings']:
        recent_rhr = health_data['resting_hr_readings'][0]
        if isinstance(recent_rhr, list) and len(recent_rhr) >= 2:
            actual['rhr'] = recent_rhr[1]

    # HRV (most recent)
    if 'hrv_readings' in health_data and health_data['hrv_readings']:
        recent_hrv = health_data['hrv_readings'][0]
        if isinstance(recent_hrv, dict):
            actual['hrv'] = recent_hrv.get('last_night_avg')

    # Sleep (most recent)
    if 'sleep_sessions' in health_data and health_data['sleep_sessions']:
        recent_sleep = health_data['sleep_sessions'][0]
        if isinstance(recent_sleep, dict):
            total_seconds = recent_sleep.get('total_sleep_seconds', 0)
            actual['sleep_hours'] = total_seconds / 3600 if total_seconds else None
            actual['sleep_score'] = recent_sleep.get('sleep_score')

    # Training readiness (most recent)
    if 'training_readiness' in health_data and health_data['training_readiness']:
        recent_readiness = health_data['training_readiness'][0]
        if isinstance(recent_readiness, dict):
            actual['training_readiness'] = recent_readiness.get('score')

    # VO2 max (most recent)
    if 'vo2_max_readings' in health_data and health_data['vo2_max_readings']:
        recent_vo2 = health_data['vo2_max_readings'][0]
        if isinstance(recent_vo2, list) and len(recent_vo2) >= 2:
            actual['vo2_max'] = recent_vo2[1]

    return actual


def validate_metric_accuracy(
    ai_metrics: Dict[str, Any],
    actual_metrics: Dict[str, Any],
    tolerance_pct: float = 10.0
) -> List[ValidationWarning]:
    """
    Validate AI-claimed metrics against actual data.

    Args:
        ai_metrics: Metrics extracted from AI response
        actual_metrics: Actual metrics from health data
        tolerance_pct: Percentage tolerance for numeric differences

    Returns:
        List of validation warnings
    """
    warnings = []

    for metric_name, ai_value in ai_metrics.items():
        actual_value = actual_metrics.get(metric_name)

        # Check if metric exists in actual data
        if actual_value is None:
            warnings.append(ValidationWarning(
                ValidationWarning.SEVERITY_HIGH,
                "metric_fabrication",
                f"AI claimed {metric_name}={ai_value} but no actual data exists",
                {'metric': metric_name, 'ai_value': ai_value, 'actual_value': None}
            ))
            continue

        # Check numeric accuracy
        if isinstance(ai_value, (int, float)) and isinstance(actual_value, (int, float)):
            diff_pct = abs(ai_value - actual_value) / actual_value * 100 if actual_value != 0 else 0

            if diff_pct > tolerance_pct:
                severity = ValidationWarning.SEVERITY_CRITICAL if diff_pct > 25 else ValidationWarning.SEVERITY_HIGH
                warnings.append(ValidationWarning(
                    severity,
                    "metric_inaccuracy",
                    f"{metric_name}: AI claimed {ai_value}, actual is {actual_value} ({diff_pct:.1f}% difference)",
                    {
                        'metric': metric_name,
                        'ai_value': ai_value,
                        'actual_value': actual_value,
                        'difference_pct': diff_pct
                    }
                ))

    return warnings


def validate_physiological_plausibility(metrics: Dict[str, Any]) -> List[ValidationWarning]:
    """
    Check if metric values are physiologically plausible.

    Args:
        metrics: Dictionary of metrics to validate

    Returns:
        List of validation warnings
    """
    warnings = []

    for metric_name, value in metrics.items():
        if metric_name not in PHYSIOLOGICAL_RANGES:
            continue

        min_val, max_val = PHYSIOLOGICAL_RANGES[metric_name]

        if not isinstance(value, (int, float)):
            continue

        if value < min_val or value > max_val:
            warnings.append(ValidationWarning(
                ValidationWarning.SEVERITY_CRITICAL,
                "physiological_implausible",
                f"{metric_name}={value} is outside physiological range [{min_val}, {max_val}]",
                {
                    'metric': metric_name,
                    'value': value,
                    'min': min_val,
                    'max': max_val
                }
            ))

    return warnings


def check_data_availability(ai_response: str, health_data: Dict[str, Any]) -> List[ValidationWarning]:
    """
    Check if AI is claiming data that doesn't exist or saying "unavailable" when it does.

    Args:
        ai_response: AI-generated text
        health_data: Health data cache

    Returns:
        List of validation warnings
    """
    warnings = []

    # Check for "unavailable" claims
    unavailable_patterns = [
        (r'RHR.*(?:unavailable|not available|no data)', 'rhr', 'resting_hr_readings'),
        (r'HRV.*(?:unavailable|not available|no data)', 'hrv', 'hrv_readings'),
        (r'sleep.*(?:unavailable|not available|no data)', 'sleep', 'sleep_sessions'),
        (r'readiness.*(?:unavailable|not available|no data)', 'readiness', 'training_readiness'),
    ]

    for pattern, metric_name, data_key in unavailable_patterns:
        if re.search(pattern, ai_response, re.IGNORECASE):
            # AI says unavailable - check if data actually exists
            if data_key in health_data and health_data[data_key]:
                warnings.append(ValidationWarning(
                    ValidationWarning.SEVERITY_MEDIUM,
                    "false_unavailable",
                    f"AI claimed {metric_name} unavailable but data exists",
                    {'metric': metric_name, 'data_key': data_key}
                ))

    return warnings


def calculate_confidence_score(
    health_data: Dict[str, Any],
    ai_metrics: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Calculate confidence score for AI recommendations.

    Args:
        health_data: Health data cache
        ai_metrics: Metrics extracted from AI response

    Returns:
        (confidence_level, details) - "HIGH", "MEDIUM", or "LOW" with explanation
    """
    score = 100
    factors = []

    # Check data freshness
    is_fresh, freshness_warning = check_data_freshness(health_data)
    if not is_fresh:
        score -= 50
        factors.append("Stale data (>7 days)")
    elif freshness_warning and freshness_warning.severity == ValidationWarning.SEVERITY_HIGH:
        score -= 30
        factors.append("Data >24 hours old")
    elif freshness_warning and freshness_warning.severity == ValidationWarning.SEVERITY_LOW:
        score -= 10
        factors.append("Data >2 hours old")

    # Check data availability
    actual_metrics = get_actual_metrics(health_data)
    available_metrics = sum(1 for v in actual_metrics.values() if v is not None)
    total_metrics = len(actual_metrics)

    if total_metrics > 0:
        availability_pct = available_metrics / total_metrics * 100
        if availability_pct < 50:
            score -= 30
            factors.append(f"Only {available_pct:.0f}% of metrics available")
        elif availability_pct < 80:
            score -= 15
            factors.append(f"{availability_pct:.0f}% of metrics available")

    # Check if AI is making claims without data
    metrics_claimed_without_data = 0
    for metric_name in ai_metrics:
        if metric_name not in actual_metrics or actual_metrics[metric_name] is None:
            metrics_claimed_without_data += 1

    if metrics_claimed_without_data > 0:
        score -= metrics_claimed_without_data * 20
        factors.append(f"AI claimed {metrics_claimed_without_data} metrics without data")

    # Determine confidence level
    if score >= 80:
        confidence = "HIGH"
    elif score >= 50:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return confidence, {
        'score': max(0, score),
        'factors': factors,
        'data_availability_pct': availability_pct if total_metrics > 0 else 0,
        'metrics_available': available_metrics,
        'metrics_total': total_metrics
    }


def validate_ai_response(
    ai_response: str,
    health_data: Dict[str, Any],
    tolerance_pct: float = 10.0
) -> Tuple[List[ValidationWarning], Dict[str, Any]]:
    """
    Comprehensive validation of AI response against health data.

    Args:
        ai_response: AI-generated coaching text
        health_data: Health data cache dictionary
        tolerance_pct: Percentage tolerance for metric differences

    Returns:
        (warnings, summary) - List of warnings and validation summary
    """
    warnings = []

    # 1. Check data freshness
    is_fresh, freshness_warning = check_data_freshness(health_data)
    if freshness_warning:
        warnings.append(freshness_warning)

    # 2. Extract metrics from AI response
    ai_metrics = extract_metrics_from_text(ai_response)
    actual_metrics = get_actual_metrics(health_data)

    # 3. Validate metric accuracy
    accuracy_warnings = validate_metric_accuracy(ai_metrics, actual_metrics, tolerance_pct)
    warnings.extend(accuracy_warnings)

    # 4. Check physiological plausibility
    plausibility_warnings = validate_physiological_plausibility(ai_metrics)
    warnings.extend(plausibility_warnings)

    # 5. Check data availability claims
    availability_warnings = check_data_availability(ai_response, health_data)
    warnings.extend(availability_warnings)

    # 6. Calculate confidence score
    confidence, confidence_details = calculate_confidence_score(health_data, ai_metrics)

    # Summary
    summary = {
        'total_warnings': len(warnings),
        'warnings_by_severity': {
            'critical': sum(1 for w in warnings if w.severity == ValidationWarning.SEVERITY_CRITICAL),
            'high': sum(1 for w in warnings if w.severity == ValidationWarning.SEVERITY_HIGH),
            'medium': sum(1 for w in warnings if w.severity == ValidationWarning.SEVERITY_MEDIUM),
            'low': sum(1 for w in warnings if w.severity == ValidationWarning.SEVERITY_LOW),
        },
        'confidence': confidence,
        'confidence_details': confidence_details,
        'ai_metrics_extracted': ai_metrics,
        'actual_metrics': actual_metrics,
        'data_fresh': is_fresh
    }

    return warnings, summary


def format_validation_report(warnings: List[ValidationWarning], summary: Dict[str, Any]) -> str:
    """
    Format validation results as human-readable report.

    Args:
        warnings: List of validation warnings
        summary: Validation summary dictionary

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=== AI VALIDATION REPORT ===")
    lines.append(f"Confidence: {summary['confidence']} ({summary['confidence_details']['score']}/100)")
    lines.append(f"Total Warnings: {summary['total_warnings']}")

    if summary['total_warnings'] > 0:
        lines.append(f"  - Critical: {summary['warnings_by_severity']['critical']}")
        lines.append(f"  - High: {summary['warnings_by_severity']['high']}")
        lines.append(f"  - Medium: {summary['warnings_by_severity']['medium']}")
        lines.append(f"  - Low: {summary['warnings_by_severity']['low']}")

    lines.append(f"Data Fresh: {'Yes' if summary['data_fresh'] else 'No'}")
    lines.append("")

    if warnings:
        lines.append("WARNINGS:")
        for w in warnings:
            lines.append(f"  [{w.severity}] {w.category}: {w.message}")
        lines.append("")

    if summary['confidence_details']['factors']:
        lines.append("CONFIDENCE FACTORS:")
        for factor in summary['confidence_details']['factors']:
            lines.append(f"  - {factor}")
        lines.append("")

    return "\n".join(lines)


def main():
    """Command-line interface for validation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: ai_validation.py <ai_response_file> [health_cache_file]")
        sys.exit(1)

    # Load AI response
    ai_response_file = Path(sys.argv[1])
    if not ai_response_file.exists():
        print(f"Error: AI response file not found: {ai_response_file}")
        sys.exit(1)

    with open(ai_response_file, 'r') as f:
        ai_response = f.read()

    # Load health data
    if len(sys.argv) > 2:
        health_cache_file = Path(sys.argv[2])
    else:
        project_root = Path(__file__).parent.parent
        health_cache_file = project_root / 'data' / 'health' / 'health_data_cache.json'

    if not health_cache_file.exists():
        print(f"Error: Health cache file not found: {health_cache_file}")
        sys.exit(1)

    with open(health_cache_file, 'r') as f:
        health_data = json.load(f)

    # Validate
    warnings, summary = validate_ai_response(ai_response, health_data)

    # Print report
    print(format_validation_report(warnings, summary))

    # Exit with error code if critical warnings
    if summary['warnings_by_severity']['critical'] > 0:
        sys.exit(2)
    elif summary['warnings_by_severity']['high'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
