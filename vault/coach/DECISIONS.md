# Coaching Decisions Log

> Append-only. Each entry is written by `memory.vault.append_decision()`.
> Newest entries at the bottom. Do not delete or reorder entries.
> Human edits to add context/annotations are welcome.


## [2026-02-17 16:20 UTC] intensity_reduction — Downgrade tempo to easy due to low HRV

**Rationale:** HRV 42 is at 12th percentile over last 30 days. Conservative adjustment per low-readiness protocol.

```json
{
  "adjusted_workout": "Easy 60 min",
  "date": "2026-02-17",
  "original_workout": "Tempo 5\u00d75 min",
  "summary": "Downgrade tempo to easy due to low HRV",
  "type": "intensity_reduction"
}
```

## [2026-02-21 09:08 UTC] plan_generated — taper week 2026-02-16

**Rationale:** Taper week, medium readiness confidence. Activity cache empty — volume baseline unanchored. Body battery 50 today (above 7d avg 38.6). Conservative taper: easy runs only, no hard sessions, 3 rest days to protect race freshness.

```json
{
  "phase": "taper",
  "plan_id": "20260216-07373841",
  "safety_flags": [
    "no_activities_last_14d: volume baseline is 0.0 miles \u2014 10pct WoW rule unenforceable, taper defaults applied",
    "hrv_null_today: relying on 7d trend avg HRV 69.6 for readiness assessment",
    "training_readiness_null_today: relying on 7d trend avg 58.3, above 50 threshold \u2014 medium confidence"
  ],
  "summary": "taper week 2026-02-16",
  "type": "plan_generated",
  "volume_mi": 12.2,
  "week_end": "2026-02-22",
  "week_start": "2026-02-16"
}
```

## [2026-02-21 12:11 UTC] today_adjustment

**Rationale:** TR 35 well below 50 threshold; sleep short and scored low; RHR elevated vs trend. Taper week context makes rest the dominant call — freshness > movement today.

```json
{
  "adjusted_intent": "Rest \u2014 low training readiness (35), taper week, preserve race freshness",
  "adjustment_reason": "low_readiness",
  "date": "2026-02-21",
  "original_intent": null,
  "safety_flags": [
    "training_readiness_below_threshold: 35 < 50 triggers low-readiness protocol",
    "sleep_below_average: 6.1h vs 7.5h 7d avg, sleep score 50 vs 67 avg",
    "rhr_elevated: 50 vs 47.5 avg \u2014 mild systemic stress",
    "taper_week: plan phase=taper, rest enforced to protect freshness",
    "original_intent_unknown: active_plan truncated, day not confirmed"
  ],
  "type": "today_adjustment"
}
```

## [2026-02-21 15:12 UTC] today_adjustment

**Rationale:** TR 35 triggers mandatory rest rule. Sleep short and scored low, RHR elevated vs trend. Taper week amplifies rest priority — any training stimulus today costs more freshness than it returns.

```json
{
  "adjusted_intent": "Rest \u2014 low training readiness (35), taper week, protect race freshness",
  "adjustment_reason": "low_readiness",
  "date": "2026-02-21",
  "original_intent": "Easy taper run \u2014 maintain aerobic touch, preserve freshness",
  "safety_flags": [
    "tr_below_threshold: 35 < 50 triggers rest rule",
    "sleep_score_low: 50 vs 67.1 7d avg",
    "sleep_short: 6.1h vs 7.5h 7d avg",
    "rhr_elevated: 50 vs 47.5 7d avg",
    "taper_week: freshness accumulation takes priority over any stimulus",
    "consistent_with_prior_decision: 12:11 UTC today_adjustment already called rest"
  ],
  "type": "today_adjustment"
}
```

## [2026-02-21 17:07 UTC] plan_generated — taper week 2026-02-16

**Rationale:** Taper week, unanchored volume baseline. TR 35 today enforces Saturday rest. Easy runs Tue/Wed/Fri/Sun preserve aerobic fitness without fatigue accumulation. No hard sessions. 3 rest days protect race freshness.

```json
{
  "phase": "taper",
  "plan_id": "20260216-79ad8869",
  "safety_flags": [
    "taper_week: no hard sessions permitted",
    "training_readiness_today_35: rest enforced 2026-02-21",
    "activity_cache_empty: volume baseline unanchored, conservative volume applied",
    "medium_readiness_confidence: conservative taper maintained"
  ],
  "summary": "taper week 2026-02-16",
  "type": "plan_generated",
  "volume_mi": 12.0,
  "week_end": "2026-02-22",
  "week_start": "2026-02-16"
}
```

## [2026-02-21 19:15 UTC] plan_generated — base week 2026-02-22

**Rationale:** Gasparilla Half on 2/22. Race day rest, full recovery Mon+Tue (constrained). Gentle return Wed-Thu. Fri constrained. Sat easy base rebuild. No intensity all week. ~9mi training volume.

```json
{
  "phase": "base",
  "plan_id": "20260222-b8ed1884",
  "safety_flags": [
    "race_day_2026-02-22: A-race half marathon \u2014 plan type rest per race rule",
    "post_race_recovery_week: no hard sessions this week",
    "constraint_enforced_2026-02-24: wife NICU shift",
    "constraint_enforced_2026-02-27: wife NICU shift"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 9.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-22 03:01 UTC] plan_generated — base week 2026-02-22

**Rationale:** Gasparilla Half on 2/22 (A-race). Post-race recovery week: full rest Sun–Tue, constrained days align with recovery. Gentle shakeout Wed, easy runs Thu+Sat. No intensity. ~9mi planned training volume.

```json
{
  "phase": "base",
  "plan_id": "20260222-2faf7702",
  "safety_flags": [
    "race_day_2026-02-22: A-race half marathon \u2014 plan marks rest per race rule",
    "post_race_recovery_week: no hard sessions this week",
    "constraints_enforced: 2026-02-24 and 2026-02-27 wife nursing shifts",
    "low_training_readiness_prerace: TR 35 on 2026-02-21 \u2014 conservative post-race rebuild"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 9.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-22 13:23 UTC] today_adjustment

**Rationale:** TR=4 (critical) aligns with expected pre/race-day taper effect. Plan and readiness agree: rest. Execute Gasparilla Half Marathon only. Zero supplemental training today.

```json
{
  "adjusted_intent": "Race day \u2014 Gasparilla Half Marathon. Execute race only, no training.",
  "adjustment_reason": "low_readiness",
  "date": "2026-02-22",
  "original_intent": "Race day \u2014 2026 Publix Gasparilla Distance Classic Half Marathon",
  "safety_flags": [
    "race_day: A-race half marathon \u2014 no additional training",
    "critical_low_readiness: training_readiness=4 (threshold 50)",
    "plan_enforced_rest: active plan marks today rest per race day rule"
  ],
  "type": "today_adjustment"
}
```

## [2026-02-22 19:41 UTC] macro_plan_generated

**Rationale:** 12-week base block from 0 to 28 mi/wk for VDOT 38. Weeks 1-8 pure aerobic base with 3:1 build:recovery cycles. Weeks 9-12 introduce structured quality. No taper — block peaks at week 12.

```json
{
  "macro_id": "base-v38-d24e47db",
  "mode": "base_block",
  "peak_miles": 28.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-22 20:39 UTC] macro_plan_generated

**Rationale:** Building aerobic base from minimal current mileage. Gradual weekly ramp (≤10%) to peak 10.5 mi by week 10. Quality phase begins week 8 with single tempo session. Final 2 weeks hold/reduce for sustainable block completion and readiness for next cycle.

```json
{
  "macro_id": "base-v38-1ed16938",
  "mode": "base_block",
  "peak_miles": 10.5,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-22 22:25 UTC] macro_plan_generated

**Rationale:** Post-race recovery Week 1 (14 mi). Aerobic base build through Week 4. Quality phase starts Week 5 (1 session/week). Escalates to 2 sessions/week from Week 7 with moderate→high intensity. Peak at 23.1 mi Week 10. Final 2 weeks reduce to 22.4 mi with 1 session/week for sustainable block finish.

```json
{
  "macro_id": "base-v51-7908d97c",
  "mode": "base_block",
  "peak_miles": 23.1,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-22 22:40 UTC] macro_plan_generated

**Rationale:** Post-race recovery (week 1: 14.5 mi, zero quality). Build aerobic base weeks 2-6 at 0-1 quality sessions. Quality phase weeks 7-12 adds tempo/intervals, ramping 1-2 sessions. Weeks 11-12 hold 28.0 mi peak with moderate intensity.

```json
{
  "macro_id": "base-v51-62255303",
  "mode": "base_block",
  "peak_miles": 28.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 01:54 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:54 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:54 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-cc103b2c",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 26.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:54 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-998235f9",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-40f4c601",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 01:55 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-ad4771ad",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 01:55 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-4b0ce1a2",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-cc103b2c",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 26.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-998235f9",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-d5d67afd",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 01:55 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-395e8e86",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 01:55 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-894e797d",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-02-22",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-cc103b2c",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 26.0,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 01:55 UTC] plan_generated — base week 2026-02-22

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260222-998235f9",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-02-22",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-02-28",
  "week_start": "2026-02-22"
}
```

## [2026-02-23 11:46 UTC] today_adjustment

**Rationale:** Day 1 post-half marathon. Training readiness 2/100 is critically low. HRV 54 below 67 avg, RHR elevated. Plan and all metrics agree: complete rest only.

```json
{
  "adjusted_intent": "Full rest \u2014 post-race day 1, training readiness critically low",
  "adjustment_reason": "low_readiness",
  "date": "2026-02-23",
  "original_intent": "Rest \u2014 post-race day 1, mandatory full recovery",
  "safety_flags": [
    "post_race_recovery: day 1 \u2014 no running",
    "training_readiness: 2/100 \u2014 critically low",
    "hrv_below_trend: 54 vs 7-day avg 67",
    "rhr_elevated: 51 vs 7-day avg 48"
  ],
  "type": "today_adjustment"
}
```

## [2026-02-23 14:46 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-7644ddf2",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:46 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-8fffb5bc",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:46 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-cfd77781",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-e673f245",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-e0611df3",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:48 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-c3a45150",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:48 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-ba1fa9ad",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:48 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-e08a50d1",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 14:48 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 15:19 UTC] macro_plan_generated

**Rationale:** Post-race recovery (13.2 mi effort) capped Week 1 at 12 mi. Progressive base phase Weeks 2-4 re-establishes aerobic foundation. Quality work introduced Week 5 (1 session, low intensity), ramping to 2 sessions by Week 6. Weeks 9-10 peak at 24 mi with high intensity stimulus. Final 2 weeks hold/reduce

```json
{
  "macro_id": "base-v50-4d387808",
  "mode": "base_block",
  "peak_miles": 24.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:06 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-96b393ba",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 16:06 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-6afa6a63",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 16:06 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-9a7eefe0",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 16:06 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-eeb607eb",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:06 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-23 16:09 UTC] macro_plan_generated

**Rationale:** Post-race recovery: Week 1 drops from current 24.1 to 14 mi (no quality). Ramp 4-5% weekly to 23.5 mi peak (week 10). Base weeks 1-6 build aerobic fitness. Quality weeks 7-12 add tempo (week 7, 1 session) then intervals (week 10, 2 sessions). Final 2 weeks reduce to 22/20.5 mi for sustainable finish

```json
{
  "macro_id": "base-v37-1a9d378b",
  "mode": "base_block",
  "peak_miles": 23.5,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 14:14 UTC] today_adjustment

**Rationale:** Constrained day (wife NICU shift) + post-race day 2 + training readiness=25. All three factors independently mandate full rest. No training.

```json
{
  "adjusted_intent": "Rest \u2014 constraint enforced + low readiness + post-race recovery day 2",
  "adjustment_reason": "constraint",
  "date": "2026-02-24",
  "original_intent": "Rest \u2014 childcare constraint + post-race recovery day 2",
  "safety_flags": [
    "constraint_enforced: wife NICU shift 2026-02-24",
    "post_race_recovery: day 2 after half marathon \u2014 no running",
    "low_readiness: training_readiness=25 (threshold 50)"
  ],
  "type": "today_adjustment"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 14:40 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-7fc3bb31",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 14:40 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-56aca907",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 14:40 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-29f92038",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 14:40 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-f45a4155",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 14:40 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-52cc00aa",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:41 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-6febb620",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:41 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-3227747b",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:41 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-6736cd38",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:41 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-084e3a77",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:46 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-5a6d85e9",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:46 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-1eae82ee",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:46 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-0c155203",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:46 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-f05cdea1",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:54 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-3d6d63de",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:54 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-4fe90fc2",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:54 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-7e1abe63",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:54 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-5711763e",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:56 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-1ddafbfe",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:56 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-0d5813fe",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:56 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-37bb822f",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 16:56 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-4671b892",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 17:33 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-1ca5efba",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 17:33 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-2ad59928",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 17:33 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-39aba509",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 17:33 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-0fdb40ef",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:18 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-2896a3e1",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:18 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-0f263b47",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:18 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-47100cb8",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:18 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-135a598b",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:26 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-92ddda60",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:26 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-936006a8",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:26 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-a7dfbbc3",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-5f572da0",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:31 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-2ac7e92c",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:31 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-d1380934",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:31 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-f493c976",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 19:31 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-bd22203e",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:26 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-7b80c3f1",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:26 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-75facd51",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:26 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-1e4c9968",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:26 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-d77843a5",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:28 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-9415bfdc",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:28 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-46a4448d",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:28 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-da8059d7",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:28 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-3c667589",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:32 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-bc4f72d0",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:32 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-abf4b296",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:32 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-6a592da6",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:32 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-f8209820",
  "safety_flags": [],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 35.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week.

```json
{
  "phase": "base",
  "plan_id": "20260301-9206be64",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] macro_plan_generated

**Rationale:** Short-race recovery block starting at 20 mi/wk.

```json
{
  "macro_id": "base-v51-b1a0c252",
  "mode": "base_block",
  "peak_miles": 22.0,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:34 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-62e06290",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:34 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-cc6afb4f",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:34 UTC] macro_plan_generated

**Rationale:** Recovery block after race. Starting at 10.0 mi/wk. VDOT 50.6.

```json
{
  "macro_id": "base-v51-afa8bcc7",
  "mode": "base_block",
  "peak_miles": 15.6,
  "race_date": null,
  "race_name": null,
  "start_week": "2026-03-01",
  "total_weeks": 12,
  "type": "macro_plan_generated"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b5c0de3c",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b3f788f6",
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 15.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-7a878d5d",
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.0,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```

## [2026-02-24 23:34 UTC] plan_generated — base week 2026-03-01

**Rationale:** Base training week. Building aerobic fitness.

```json
{
  "phase": "base",
  "plan_id": "20260301-b942defc",
  "safety_flags": [
    "macro_guided"
  ],
  "summary": "base week 2026-03-01",
  "type": "plan_generated",
  "volume_mi": 20.3,
  "week_end": "2026-03-07",
  "week_start": "2026-03-01"
}
```
