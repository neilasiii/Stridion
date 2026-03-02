# AI Hallucination Mitigation Guide

## Overview

This document describes the hallucination prevention and detection systems built into the Running Coach platform. These systems ensure AI-generated coaching recommendations are accurate, data-driven, and trustworthy.

**Last Updated**: 2025-12-05

---

## Table of Contents

1. [What Are AI Hallucinations?](#what-are-ai-hallucinations)
2. [Hallucination Risks in This System](#hallucination-risks-in-this-system)
3. [Mitigation Strategies](#mitigation-strategies)
4. [Validation System](#validation-system)
5. [Monitoring and Logging](#monitoring-and-logging)
6. [Best Practices for Users](#best-practices-for-users)

---

## What Are AI Hallucinations?

**AI hallucinations** occur when AI models generate plausible-sounding but factually incorrect information. In a coaching context, this could include:

- **Fabricated metrics**: AI inventing RHR, HRV, or sleep scores when data is missing
- **Incorrect calculations**: AI estimating VDOT or paces instead of using formulas
- **False confidence**: AI presenting guesses as facts
- **Temporal errors**: AI confusing dates, day-of-week, or workout schedules
- **Physiologically implausible values**: AI citing impossible metrics (e.g., RHR of 120 bpm for a fit athlete)

---

## Hallucination Risks in This System

### Risk Categories (by impact)

#### **1. Health Metric Fabrication** ⚠️ HIGH RISK

**Risk**: AI invents RHR, HRV, sleep scores, or training readiness when data is missing

**Impact**: Dangerous training recommendations based on false recovery data (e.g., prescribing hard workout when athlete is actually fatigued)

**Examples**:
- ❌ "Your RHR is elevated at 55 bpm" (when no RHR data exists)
- ❌ "Sleep quality was excellent at 85" (when sleep data unavailable)
- ❌ "HRV is within normal range at 45ms" (when HRV not measured)

#### **2. Date/Day-of-Week Errors** ⚠️ HIGH RISK

**Risk**: AI assumes dates or incorrectly guesses day-of-week

**Impact**: Wrong workout recommendations, scheduling conflicts, missed quality sessions

**Examples**:
- ❌ "Today is Tuesday" (when it's actually Wednesday)
- ❌ "Your long run is scheduled for Saturday" (when it's Sunday)
- ❌ Recommending rest day on scheduled workout day

#### **3. Workout Prescription Fabrication** ⚠️ MEDIUM RISK

**Risk**: AI creates workout details not in FinalSurge or baseline plan

**Impact**: Athlete follows incorrect workout, training plan derails, periodization disrupted

**Examples**:
- ❌ "Today's scheduled workout is 3x10min tempo" (when plan shows easy run)
- ❌ "Your plan calls for 12 miles" (when scheduled distance is 10 miles)

#### **4. Pace/VDOT Estimation** ⚠️ LOW RISK (Mitigated)

**Risk**: AI guessing training paces instead of using calculator

**Impact**: Incorrect training intensities, under/overtraining

**Mitigation**: Strong tool-based system (`calculate_vdot` function) with verified accuracy

#### **5. Morning Report Fabrication** ⚠️ MEDIUM RISK

**Risk**: AI generating plausible-sounding but incorrect daily summaries

**Impact**: User trusts incorrect recovery assessment or workout recommendation

**Examples**:
- ❌ "Recovery is excellent based on 8 hours of sleep" (when sleep was 6 hours)
- ❌ "Training readiness is high at 90" (when actual readiness is 65)

---

## Mitigation Strategies

### 1. Data Integrity Protocol (All Agents)

**Location**: `docs/AGENT_SHARED_CONTEXT.md` → "Data Integrity and Anti-Hallucination Protocol"

**6 Core Rules**:

1. **Never Fabricate or Estimate Metrics**
   - If metric unavailable → state "unavailable" or "no data"
   - Never fill gaps with typical/average values
   - Never use "probably", "likely around", "estimated" for objective metrics

2. **Cite Exact Values from Data**
   - Use EXACT values from health data (no rounding beyond 1 decimal)
   - Include data source and date
   - Acknowledge when data is stale (>24 hours old)

3. **Confidence Transparency**
   - Every recommendation includes confidence level: HIGH, MEDIUM, or LOW
   - HIGH: Direct, recent data (<24 hrs old)
   - MEDIUM: Inference from multiple metrics or data 24-48 hrs old
   - LOW: General guidance without specific supporting data

4. **Acknowledge Missing Data**
   - Explicitly list what data is missing
   - Explain how recommendation would change if data available
   - Suggest obtaining missing data if critical

5. **Cross-Reference Validation**
   - Cross-check metrics for consistency
   - Verify workout paces against current VDOT
   - Check dates against scheduled workouts

6. **Physiological Plausibility**
   - Sanity-check all metric values against physiological ranges
   - Flag implausible values before using

### 2. Explicit Anti-Hallucination Instructions

**Location**: `src/generate_ai_coaching.py:138-204`

Every AI coaching prompt includes:

```markdown
**CRITICAL: DATA INTEGRITY RULES**
- If a metric is unavailable/missing, you MUST state "unavailable" or "no data"
- NEVER estimate, interpolate, or guess health metrics (RHR, HRV, sleep, etc.)
- NEVER fill data gaps with typical/average values
- If uncertain about data, err on the side of saying "I don't have that data"
- Only cite metrics that are explicitly provided in the data below
- When citing metrics, use the EXACT values provided (no rounding beyond 1 decimal)
```

### 3. Tool-Based Architecture

**Prevents hallucination by enforcing calculation tools**:

- `calculate_vdot` → Forces use of Jack Daniels formulas (no estimation)
- `get_current_date` → Mandatory date verification at session start
- `calculate_date_info` → Verifies day-of-week for any referenced date
- `smart_sync_health_data` → Ensures fresh data before recommendations

### 4. Structured Output Formats

**Reduces creative liberty**:

Morning reports use fixed structure:
```
Recovery: [2-4 word status]
Today: [specific workout recommendation]
Weather: [time window + temp]
Note: [1 key insight, <50 chars]

---DETAILED---

[Comprehensive analysis with full rationale]

**Confidence Level:** [HIGH/MEDIUM/LOW] - [brief explanation]
```

### 5. Data Freshness Warnings

**Location**: `src/generate_ai_coaching.py:126-136`

Automatic warnings when data is stale:
- Data >24 hours old → Warning in prompt
- Data >7 days old → Critical warning, recommend refusing recommendations

---

## Validation System

### Architecture

```
AI generates response
        ↓
src/ai_validation.py validates response
        ↓
Checks:
1. Data freshness
2. Metric accuracy (AI claims vs actual data)
3. Physiological plausibility
4. Data availability claims
5. Confidence scoring
        ↓
Warnings logged + confidence score calculated
        ↓
Critical warnings → Alert user
```

### Components

#### 1. `src/ai_validation.py` - Validation Module

**Functions**:

- `check_data_freshness(health_data)` - Validates cache age
  - Returns: (is_fresh, warning)
  - Thresholds: 2 hrs (LOW), 24 hrs (HIGH), 7 days (CRITICAL)

- `extract_metrics_from_text(ai_response)` - Extracts metrics from AI text
  - Uses regex to find RHR, HRV, sleep, VO2 max, etc.
  - Returns: Dictionary of extracted metrics

- `get_actual_metrics(health_data)` - Gets ground truth from cache
  - Extracts most recent values from health_data_cache.json
  - Returns: Dictionary of actual metric values

- `validate_metric_accuracy(ai_metrics, actual_metrics, tolerance_pct=10.0)` - Compares AI claims to actual data
  - Checks if metrics exist in actual data
  - Validates numeric accuracy within tolerance
  - Returns: List of warnings

- `validate_physiological_plausibility(metrics)` - Sanity checks
  - Validates against physiological ranges
  - Flags impossible values (e.g., RHR 120, HRV 300)
  - Returns: List of warnings

- `check_data_availability(ai_response, health_data)` - Detects false "unavailable" claims
  - Checks if AI claims data unavailable when it actually exists
  - Returns: List of warnings

- `calculate_confidence_score(health_data, ai_metrics)` - Confidence scoring
  - Factors: Data freshness, availability, metrics claimed without data
  - Returns: (confidence_level, details) - "HIGH"/"MEDIUM"/"LOW"

- `validate_ai_response(ai_response, health_data, tolerance_pct=10.0)` - Main validation
  - Runs all validation checks
  - Returns: (warnings, summary)

#### 2. `bin/validate_ai_report.sh` - Shell Wrapper

**Usage**:
```bash
bash bin/validate_ai_report.sh ai_response.txt
bash bin/validate_ai_report.sh --stdin < response.txt
```

**Exit Codes**:
- 0: No warnings or low/medium only
- 1: High severity warnings
- 2: Critical warnings (potential hallucination)

#### 3. Integrated Validation in `generate_ai_coaching.py`

**Auto-validation after AI generation** (lines 347-372):
- Validates every morning report
- Logs validation results to stderr
- Writes full report to `data/ai_validation.log`
- Alerts on critical warnings

### Validation Warning Severity

**CRITICAL** - Data fabrication, dangerous recommendation
- Metric claimed but doesn't exist
- Value >25% different from actual
- Physiologically impossible value
- Data >7 days old

**HIGH** - Significant discrepancy, likely hallucination
- Metric >10% different from actual
- Data >24 hours old
- False "unavailable" claim

**MEDIUM** - Moderate concern, needs review
- Cross-reference inconsistency
- AI claims data when it's actually unavailable

**LOW** - Minor issue, informational
- Data 2-24 hours old
- Minor formatting issues

---

## Monitoring and Logging

### Validation Logs

**Location**: `data/ai_validation.log`

**Contents**:
- Timestamp of validation
- Confidence score (0-100)
- Total warnings by severity
- Confidence factors
- Full warning details

**Example Entry**:
```
=== Validation: 2025-12-05T09:15:00 ===
=== AI VALIDATION REPORT ===
Confidence: HIGH (95/100)
Total Warnings: 1
  - Critical: 0
  - High: 0
  - Medium: 0
  - Low: 1
Data Fresh: Yes

WARNINGS:
  [LOW] data_freshness: Health data is 2.3 hours old (acceptable but not current).

CONFIDENCE FACTORS:
  - Data >2 hours old
```

### Morning Report Logs

**Location**: `data/morning_report.log`

**Contents**:
- Sync status
- AI generation status
- Validation summary
- Final report sent to user

### Monitoring Strategy

**Daily Review**:
- Check `data/ai_validation.log` for critical/high warnings
- Review `data/morning_report.log` for generation failures
- Monitor confidence scores (alert if consistently <50)

**Weekly Review**:
- Analyze warning patterns (frequent categories)
- Check false "unavailable" rate
- Validate physiological range assumptions

**Monthly Review**:
- Update PHYSIOLOGICAL_RANGES if needed
- Review tolerance_pct (currently 10%)
- Audit validation accuracy (false positives/negatives)

---

## Best Practices for Users

### 1. Verify Critical Decisions

**Always double-check when**:
- AI recommends skipping scheduled quality workout
- AI suggests significantly reducing workout volume
- AI claims recovery metrics you haven't seen on Garmin
- Confidence level is MEDIUM or LOW

### 2. Report Hallucinations

**If you notice AI fabricating data**:
1. Check `data/ai_validation.log` to see if it was caught
2. Verify actual data in Garmin Connect or `data/health/health_data_cache.json`
3. Report the hallucination with:
   - AI claim (exact wording)
   - Actual data value
   - Date/time of incident

### 3. Keep Data Fresh

**Sync regularly**:
- Run `bash bin/smart_sync.sh` before coaching sessions
- Enable automated sync (every 6 hours recommended)
- Force sync after completing workouts: `bash bin/smart_sync.sh --force`

### 4. Understand Confidence Levels

**HIGH confidence** → Trust recommendation, data is fresh and direct
**MEDIUM confidence** → Review recommendation, data may be inferred or stale
**LOW confidence** → Use as general guidance only, limited data support

### 5. Review Validation Logs Periodically

**Monthly check**:
```bash
# View recent validation warnings
tail -50 data/ai_validation.log

# Count critical warnings in last month
grep "CRITICAL" data/ai_validation.log | wc -l
```

---

## Technical Details

### Physiological Validation Ranges

```python
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
```

**Note**: These are conservative ranges. Athlete-specific ranges may be narrower (e.g., RHR 40-60 for trained endurance athlete).

### Metric Extraction Patterns

AI validation uses regex to extract metrics from text:

```python
# RHR patterns
r'RHR[:\s]+(\d+)'
r'resting\s+heart\s+rate[:\s]+(\d+)'
r'heart\s+rate[:\s]+(\d+)\s*bpm'

# HRV patterns
r'HRV[:\s]+(\d+)'
r'heart\s+rate\s+variability[:\s]+(\d+)'

# Sleep patterns
r'(\d+\.?\d*)\s*hours?\s+(?:of\s+)?sleep'
r'sleep[:\s]+(\d+\.?\d*)\s*(?:hrs?|hours?)'

# And more...
```

### Confidence Scoring Algorithm

```python
score = 100

# Data freshness penalty
if age_hours > 168: score -= 50   # 7+ days
elif age_hours > 24: score -= 30  # 1+ day
elif age_hours > 2: score -= 10   # 2+ hours

# Data availability penalty
if availability < 50%: score -= 30
elif availability < 80%: score -= 15

# Fabrication penalty
score -= metrics_claimed_without_data * 20

# Confidence level
if score >= 80: confidence = "HIGH"
elif score >= 50: confidence = "MEDIUM"
else: confidence = "LOW"
```

---

## Future Enhancements

### Planned Improvements

1. **Machine Learning-Based Detection**
   - Train model on known hallucination patterns
   - Detect semantic inconsistencies beyond regex

2. **Cross-Session Validation**
   - Compare AI claims across multiple sessions
   - Flag sudden metric changes (e.g., RHR 45→65 overnight)

3. **User Feedback Loop**
   - Allow users to flag hallucinations
   - Update validation rules based on reported issues

4. **Automated Alerts**
   - Push notification when critical warnings detected
   - Daily/weekly hallucination summary emails

5. **A/B Testing**
   - Compare hallucination rates across AI models
   - Optimize prompts for accuracy

6. **Validation Metrics Dashboard**
   - Visualize warning trends over time
   - Track confidence score distributions
   - Monitor data freshness patterns

---

## Related Documentation

- **[AGENT_SHARED_CONTEXT.md](AGENT_SHARED_CONTEXT.md)** - Data integrity protocol for all agents
- **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** - Overall system design
- **[AGENT_HEALTH_DATA_GUIDE.md](AGENT_HEALTH_DATA_GUIDE.md)** - Health data usage patterns

---

**Maintained By**: Athlete
**Version**: 1.0.0
**Last Updated**: 2025-12-05
