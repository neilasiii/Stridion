# Training Plans

> Each plan block below corresponds to a `plan_id` in `data/coach.sqlite`.
> The authoritative plan data lives in SQLite (`plans` + `plan_days` tables).
> This file is a human-readable mirror/snapshot for review and annotation.
>
> Authority model:
>   - Plans in SQLite are the PRIMARY source for Garmin workout generation.
>   - FinalSurge/ICS is an OPTIONAL input channel only.


## [2026-02-17 16:20 UTC] `20260216-abc12345`

Week of 2026-02-16 | Phase: Base | 7 days

<details><summary>Full plan</summary>

```json
{
  "week": "2026-02-16",
  "phase": "base",
  "days": 7
}
```

</details>

## [2026-02-21 09:08 UTC] `20260216-07373841`

Phase: taper | Week: 2026-02-16–2026-02-22 | Volume: 12.2 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-16",
  "week_end": "2026-02-22",
  "phase": "taper",
  "days": [
    {
      "date": "2026-02-16",
      "intent": "Rest \u2014 taper begins, preserve freshness",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [
        {
          "label": "warmup",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Light walking or gentle stretching only"
        },
        {
          "label": "main",
          "duration_min": 10,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Full rest day \u2014 no running"
        },
        {
          "label": "cooldown",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Gentle foam roll or light mobility"
        }
      ],
      "safety_flags": [
        "rest_enforced: taper day 1, consistent with active plan preview"
      ],
      "rationale": "First day of taper. Full rest to begin accumulating freshness. Consistent with active plan and prior intensity_reduction decision on 2026-02-17."
    },
    {
      "date": "2026-02-17",
      "intent": "Easy taper run with strides \u2014 maintain neuromuscular sharpness",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "warmup",
          "duration_min": 10,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": "Very easy, conversational E pace"
        },
        {
          "label": "main",
          "duration_min": 29,
          "target_metric": "rpe",
          "target_value": "easy + strides",
          "reps": null,
          "notes": "6x20s strides @ 5K pace on 60s easy jog"
        },
        {
          "label": "cooldown",
          "duration_min": 6,
          "target_metric": "pace",
          "target_value": "11:00-11:10/mi",
          "reps": null,
          "notes": "Easy walk/jog to finish"
        }
      ],
      "safety_flags": [
        "intensity_reduction_applied: tempo downgraded to easy per 2026-02-17 decision (HRV 42, 12th percentile)",
        "stride_rewrite_applied"
      ],
      "rationale": "Easy run with strides per taper protocol. Tempo downgraded to easy per logged intensity_reduction decision. Strides maintain leg turnover without fatigue accumulation."
    },
    {
      "date": "2026-02-18",
      "intent": "Easy taper run \u2014 mid-week volume reduction",
      "workout_type": "easy",
      "duration_min": 35,
      "structure_steps": [
        {
          "label": "warmup",
          "duration_min": 8,
          "target_metric": "pace",
          "target_value": "10:45-11:10/mi",
          "reps": null,
          "notes": "Start very easy, no pressure on pace"
        },
        {
          "label": "main",
          "duration_min": 22,
          "target_metric": "pace",
          "target_value": "10:00-10:35/mi",
          "reps": null,
          "notes": "Easy aerobic effort, comfortable throughout"
        },
        {
          "label": "cooldown",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 3",
          "reps": null,
          "notes": "Walk to finish, light stretching"
        }
      ],
      "safety_flags": [],
      "rationale": "Mid-taper easy run. Volume intentionally reduced from prior session. No hard effort. No consecutive hard days. Preserving legs ahead of rest day and final shakeouts."
    },
    {
      "date": "2026-02-19",
      "intent": "Rest \u2014 mid-taper recovery after back-to-back runs",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [
        {
          "label": "warmup",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Optional light walk"
        },
        {
          "label": "main",
          "duration_min": 10,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Full rest \u2014 no running"
        },
        {
          "label": "cooldown",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Foam roll, mobility if desired"
        }
      ],
      "safety_flags": [],
      "rationale": "Rest after back-to-back easy days (Tue-Wed). Supports freshness accumulation in taper. Legs recover fully before final pre-race shakeouts."
    },
    {
      "date": "2026-02-20",
      "intent": "Easy shakeout \u2014 maintain running economy, low load",
      "workout_type": "easy",
      "duration_min": 30,
      "structure_steps": [
        {
          "label": "warmup",
          "duration_min": 7,
          "target_metric": "pace",
          "target_value": "10:45-11:10/mi",
          "reps": null,
          "notes": "Very easy, let body wake up"
        },
        {
          "label": "main",
          "duration_min": 18,
          "target_metric": "pace",
          "target_value": "10:00-10:35/mi",
          "reps": null,
          "notes": "Easy effort, check in with body"
        },
        {
          "label": "cooldown",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 3",
          "reps": null,
          "notes": "Easy walk, light mobility"
        }
      ],
      "safety_flags": [],
      "rationale": "Short shakeout to maintain running economy without taxing legs. Volume intentionally minimal in late taper. Easy conversational effort only throughout."
    },
    {
      "date": "2026-02-21",
      "intent": "Very easy shakeout \u2014 final run before race week",
      "workout_type": "easy",
      "duration_min": 25,
      "structure_steps": [
        {
          "label": "warmup",
          "duration_min": 5,
          "target_metric": "pace",
          "target_value": "11:00-11:30/mi",
          "reps": null,
          "notes": "Walk into very easy jog"
        },
        {
          "label": "main",
          "duration_min": 15,
          "target_metric": "pace",
          "target_value": "10:00-10:35/mi",
          "reps": null,
          "notes": "Easy aerobic, legs should feel fresh"
        },
        {
          "label": "cooldown",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 2",
          "reps": null,
          "notes": "Walk out, light stretch"
        }
      ],
      "safety_flags": [
        "body_battery_50: adequate for easy effort; no intensity elevation warranted",
        "hrv_null_today: defaulting to easy effort per conservative protocol"
      ],
      "rationale": "Body battery 50 (above 7d avg 38.6). HRV and training readiness null today \u2014 easy only. Very short run to keep legs fresh. Final tune-up before full taper rest."
    },
    {
      "date": "2026-02-22",
      "intent": "Rest \u2014 end of taper week, maximum freshness",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [
        {
          "label": "warmup",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Light walk or gentle movement only"
        },
        {
          "label": "main",
          "duration_min": 10,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Full rest \u2014 no running"
        },
        {
          "label": "cooldown",
          "duration_min": 5,
          "target_metric": "rpe",
          "target_value": "RPE 1",
          "reps": null,
          "notes": "Legs up the wall, foam roll, hydrate well"
        }
      ],
      "safety_flags": [],
      "rationale": "Final rest day of taper week. No activity \u2014 allow full absorption of taper load reduction. Arrive at race week with legs fully recovered and glycogen stores loaded."
    }
  ],
  "weekly_volume_miles": 12.2,
  "safety_flags": [
    "no_activities_last_14d: volume baseline is 0.0 miles \u2014 10pct WoW rule unenforceable, taper defaults applied",
    "hrv_null_today: relying on 7d trend avg HRV 69.6 for readiness assessment",
    "training_readiness_null_today: relying on 7d trend avg 58.3, above 50 threshold \u2014 medium confidence"
  ],
  "rationale": "Taper week, medium readiness confidence. Activity cache empty \u2014 volume baseline unanchored. Body battery 50 today (above 7d avg 38.6). Conservative taper: easy runs only, no hard sessions, 3 rest days to protect race freshness.",
  "context_hash": "00aaf815fb796d7b9e96c5cf134030f3a827155fba06a026086bb002b7427031"
}
```

</details>

## [2026-02-21 17:07 UTC] `20260216-79ad8869`

Phase: taper | Week: 2026-02-16–2026-02-22 | Volume: 12.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-16",
  "week_end": "2026-02-22",
  "phase": "taper",
  "days": [
    {
      "date": "2026-02-16",
      "intent": "Rest \u2014 taper begins, preserve freshness",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "rest_enforced: taper day 1"
      ],
      "rationale": "First day of taper. Full rest to begin accumulating freshness. Consistent with active plan."
    },
    {
      "date": "2026-02-17",
      "intent": "Easy taper run with strides \u2014 maintain neuromuscular sharpness",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "rpe",
          "target_value": "RPE 4-5",
          "reps": null,
          "notes": "6x20s strides @ RPE 8 on 60s easy jog; stay conversational otherwise"
        }
      ],
      "safety_flags": [
        "intensity_reduction_applied: tempo downgraded per 2026-02-17 HRV decision"
      ],
      "rationale": "Easy run with strides per active plan. HRV 42 on this date prompted downgrade from tempo. Strides maintain neuromuscular sharpness without hard effort."
    },
    {
      "date": "2026-02-18",
      "intent": "Easy run \u2014 maintain aerobic fitness, accumulate freshness",
      "workout_type": "easy",
      "duration_min": 35,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 35,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": "Conversational pace, fully aerobic, no surges"
        }
      ],
      "safety_flags": [],
      "rationale": "Mid-taper easy run. Short and comfortable to limit fatigue while maintaining aerobic feel. No intensity stimulus needed this week."
    },
    {
      "date": "2026-02-19",
      "intent": "Rest \u2014 mid-week taper rest, recovery priority",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "rest_enforced: mid-taper recovery day"
      ],
      "rationale": "Planned rest day in taper. Back-to-back easy days earlier in week; rest here restores freshness and prevents cumulative fatigue."
    },
    {
      "date": "2026-02-20",
      "intent": "Easy short run \u2014 maintain feel, protect freshness",
      "workout_type": "easy",
      "duration_min": 30,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 30,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": "Relaxed easy effort, keep HR low, no surges"
        }
      ],
      "safety_flags": [],
      "rationale": "Short easy run to keep legs loose heading into weekend. Volume deliberately low. Last easy day before Sat rest and Sun shakeout."
    },
    {
      "date": "2026-02-21",
      "intent": "Rest \u2014 low training readiness (35), taper week enforces rest",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "training_readiness_35: mandatory_rest_enforced",
        "sleep_short_6h_score_50: additional_rest_justified",
        "rhr_elevated_vs_trend: rest_supported"
      ],
      "rationale": "TR 35 triggers mandatory rest per safety rule. Sleep 6.1h score 50. RHR 50 vs 7d avg 47.5. Taper context amplifies rest priority. Consistent with today_adjustment decisions."
    },
    {
      "date": "2026-02-22",
      "intent": "Easy shakeout \u2014 light legs, taper tune-up",
      "workout_type": "easy",
      "duration_min": 25,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 25,
          "target_metric": "rpe",
          "target_value": "RPE 4",
          "reps": null,
          "notes": "Very light movement only. Stop if fatigued. Legs should feel fresh."
        }
      ],
      "safety_flags": [],
      "rationale": "Final taper day. Light shakeout to flush legs and maintain aerobic feel after Sat rest. 25 min at RPE 4 \u2014 minimal stimulus, maximal freshness preservation."
    }
  ],
  "weekly_volume_miles": 12.0,
  "safety_flags": [
    "taper_week: no hard sessions permitted",
    "training_readiness_today_35: rest enforced 2026-02-21",
    "activity_cache_empty: volume baseline unanchored, conservative volume applied",
    "medium_readiness_confidence: conservative taper maintained"
  ],
  "rationale": "Taper week, unanchored volume baseline. TR 35 today enforces Saturday rest. Easy runs Tue/Wed/Fri/Sun preserve aerobic fitness without fatigue accumulation. No hard sessions. 3 rest days protect race freshness.",
  "context_hash": "07373841687a1453521bc3771c159f24abbc305d80492edb36f82cee76f1a303"
}
```

</details>

## [2026-02-21 19:15 UTC] `20260222-b8ed1884`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 9.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Race day \u2014 2026 Publix Gasparilla Distance Classic Half Marathon",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "race_day: A-race half marathon, no additional training"
      ],
      "rationale": "A-race: Publix Gasparilla Half Marathon. Plan marks rest per race day rule; actual race effort is 13.1 miles. Execute race plan only."
    },
    {
      "date": "2026-02-23",
      "intent": "Rest \u2014 post-race day 1, mandatory full recovery",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "post_race_recovery: day 1 \u2014 no running"
      ],
      "rationale": "Day 1 after half marathon. Complete rest required. Muscle repair and glycogen replenishment take full priority over any training stimulus."
    },
    {
      "date": "2026-02-24",
      "intent": "Rest \u2014 childcare constraint + post-race recovery day 2",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "constraint_enforced: wife's nursing schedule \u2014 NurseGrid",
        "post_race_recovery: day 2"
      ],
      "rationale": "Constrained day (wife NICU shift). Aligns perfectly with post-race day 2 recovery. No training possible or advisable."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy shakeout \u2014 post-race day 3, gentle return if legs ready",
      "workout_type": "easy",
      "duration_min": 25,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 25,
          "target_metric": "rpe",
          "target_value": "RPE 3-4",
          "reps": null,
          "notes": "Skip if still sore. Stop at sharp pain. Fully conversational, no surges."
        }
      ],
      "safety_flags": [
        "post_race_recovery: day 3 \u2014 conditional on absence of soreness"
      ],
      "rationale": "Day 3 post-race. Very gentle shakeout only if legs feel ready. RPE 3-4, 25 min max. Skip entirely if residual soreness or fatigue remains."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy recovery run \u2014 day 4 post-race, aerobic base restart",
      "workout_type": "easy",
      "duration_min": 35,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 35,
          "target_metric": "rpe",
          "target_value": "RPE 4-5",
          "reps": null,
          "notes": "Conversational pace throughout, no surges, fully aerobic only"
        }
      ],
      "safety_flags": [],
      "rationale": "Day 4 post-race. Building back gently. 35 min easy at RPE 4-5. Aerobic only; no surges or intensity whatsoever."
    },
    {
      "date": "2026-02-27",
      "intent": "Rest \u2014 childcare constraint, wife nursing shift",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "constraint_enforced: wife's nursing schedule \u2014 NurseGrid"
      ],
      "rationale": "Constrained day per NurseGrid calendar. Also supports continued post-race recovery ahead of Saturday's easy run."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy run \u2014 base rebuild, 6 days post-race",
      "workout_type": "easy",
      "duration_min": 40,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 40,
          "target_metric": "rpe",
          "target_value": "RPE 4-5",
          "reps": null,
          "notes": "Aerobic base building, conversational effort, no intensity or surges"
        }
      ],
      "safety_flags": [],
      "rationale": "6 days post-race. Longer easy run begins base rebuild. Fully aerobic and conversational. No intensity until readiness metrics recover next week."
    }
  ],
  "weekly_volume_miles": 9.0,
  "safety_flags": [
    "race_day_2026-02-22: A-race half marathon \u2014 plan type rest per race rule",
    "post_race_recovery_week: no hard sessions this week",
    "constraint_enforced_2026-02-24: wife NICU shift",
    "constraint_enforced_2026-02-27: wife NICU shift"
  ],
  "rationale": "Gasparilla Half on 2/22. Race day rest, full recovery Mon+Tue (constrained). Gentle return Wed-Thu. Fri constrained. Sat easy base rebuild. No intensity all week. ~9mi training volume.",
  "context_hash": "79ad8869ca64ab571aae5527403407e31b3b109ce60b5d9e6f40dcd44862edf2"
}
```

</details>

## [2026-02-22 03:01 UTC] `20260222-2faf7702`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 9.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Race day \u2014 2026 Publix Gasparilla Distance Classic Half Marathon",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "race_day: A-race half marathon, no additional training"
      ],
      "rationale": "A-race: Publix Gasparilla Half Marathon. Plan marks rest per race day rule; actual race effort is 13.1 miles. Execute race plan only."
    },
    {
      "date": "2026-02-23",
      "intent": "Rest \u2014 post-race day 1, mandatory full recovery",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "post_race_recovery: day 1 \u2014 no running"
      ],
      "rationale": "Day 1 after half marathon. Complete rest required. Muscle repair and glycogen replenishment take full priority over any training stimulus."
    },
    {
      "date": "2026-02-24",
      "intent": "Rest \u2014 childcare constraint + post-race recovery day 2",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "constraint_enforced: wife's nursing schedule \u2014 NurseGrid",
        "post_race_recovery: day 2 \u2014 no running"
      ],
      "rationale": "Constrained day (wife NICU shift). Aligns perfectly with post-race day 2 recovery. No training possible or advisable."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy shakeout \u2014 post-race day 3, gentle return if legs ready",
      "workout_type": "easy",
      "duration_min": 25,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 25,
          "target_metric": "rpe",
          "target_value": "RPE 3-4",
          "reps": null,
          "notes": "Skip if still sore. Walk breaks fine. Fully conversational, no surges."
        }
      ],
      "safety_flags": [
        "post_race_recovery: day 3 \u2014 conditional on absence of soreness"
      ],
      "rationale": "Day 3 post-race. Very gentle shakeout only. Walk breaks encouraged. If legs feel heavy or sore, convert to full rest. No pace targets."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy base \u2014 post-race day 4, aerobic flush",
      "workout_type": "easy",
      "duration_min": 30,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 30,
          "target_metric": "rpe",
          "target_value": "RPE 4-5",
          "reps": null,
          "notes": "Comfortable aerobic pace. Reduce to 20 min or rest if fatigue lingers."
        }
      ],
      "safety_flags": [
        "post_race_recovery: day 4 \u2014 easy only, no quality"
      ],
      "rationale": "Day 4 post-race. Easy aerobic run to flush metabolic waste and restore circulation. Reduce to 20 min or rest if race fatigue persists."
    },
    {
      "date": "2026-02-27",
      "intent": "Rest \u2014 childcare constraint (wife's nursing shift)",
      "workout_type": "rest",
      "duration_min": 0,
      "structure_steps": [],
      "safety_flags": [
        "constraint_enforced: wife's nursing schedule \u2014 NurseGrid"
      ],
      "rationale": "Constrained day (wife NICU shift). Also serves as additional post-race recovery. No training possible."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy base rebuild \u2014 post-race day 6, begin next block",
      "workout_type": "easy",
      "duration_min": 35,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 35,
          "target_metric": "rpe",
          "target_value": "RPE 4-5",
          "reps": null,
          "notes": "Steady easy pace. Run by feel. Good form focus, no watch pressure."
        }
      ],
      "safety_flags": [
        "post_race_recovery: day 6 \u2014 begin base rebuild, easy only"
      ],
      "rationale": "Day 6 post-race. Building back toward normal volume. Easy aerobic effort only. Sets foundation for next training block. No hard efforts this week."
    }
  ],
  "weekly_volume_miles": 9.0,
  "safety_flags": [
    "race_day_2026-02-22: A-race half marathon \u2014 plan marks rest per race rule",
    "post_race_recovery_week: no hard sessions this week",
    "constraints_enforced: 2026-02-24 and 2026-02-27 wife nursing shifts",
    "low_training_readiness_prerace: TR 35 on 2026-02-21 \u2014 conservative post-race rebuild"
  ],
  "rationale": "Gasparilla Half on 2/22 (A-race). Post-race recovery week: full rest Sun\u2013Tue, constrained days align with recovery. Gentle shakeout Wed, easy runs Thu+Sat. No intensity. ~9mi planned training volume.",
  "context_hash": "b8ed1884cb5356944d35a9e3e23cf75ca9a8711b262a21543e64c56ee070c196"
}
```

</details>

## [2026-02-23 01:54 UTC] `20260222-b5c0de3c`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:54 UTC] `20260222-b3f788f6`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 15.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 15.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:54 UTC] `20260222-cc103b2c`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 26.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 26.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:54 UTC] `20260222-998235f9`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-b5c0de3c`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-b3f788f6`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 15.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 15.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-cc103b2c`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 26.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 26.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-998235f9`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-b5c0de3c`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-b3f788f6`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 15.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 15.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-cc103b2c`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 26.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 26.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 01:55 UTC] `20260222-998235f9`

Phase: base | Week: 2026-02-22–2026-02-28 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-02-22",
  "week_end": "2026-02-28",
  "phase": "base",
  "days": [
    {
      "date": "2026-02-22",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-23",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-24",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-25",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-26",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-27",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-02-28",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:46 UTC] `20260301-b5c0de3c`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:46 UTC] `20260301-b3f788f6`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 15.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 15.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:46 UTC] `20260301-7a878d5d`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:46 UTC] `20260301-b942defc`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-f8209820`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 35.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 35.0,
  "safety_flags": [],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-f8209820`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 35.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 35.0,
  "safety_flags": [],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-b5c0de3c`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-b3f788f6`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 15.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 15.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-7a878d5d`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 14:48 UTC] `20260301-b942defc`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-f8209820`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 35.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 35.0,
  "safety_flags": [],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-b5c0de3c`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-b3f788f6`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 15.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 15.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-7a878d5d`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-23 16:06 UTC] `20260301-b942defc`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-f8209820`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 35.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 35.0,
  "safety_flags": [],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-9206be64`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic base."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week.",
  "context_hash": "h001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-b5c0de3c`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-b3f788f6`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 15.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 15.0,
  "safety_flags": [
    "low_readiness_confidence"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-7a878d5d`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.0 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.0,
  "safety_flags": [
    "macro_guided",
    "macro_cap_exceeded",
    "macro_cap_clamped"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>

## [2026-02-24 14:40 UTC] `20260301-b942defc`

Phase: base | Week: 2026-03-01–2026-03-07 | Volume: 20.3 mi

<details><summary>Full plan</summary>

```json
{
  "week_start": "2026-03-01",
  "week_end": "2026-03-07",
  "phase": "base",
  "days": [
    {
      "date": "2026-03-01",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-02",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-03",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-04",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-05",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-06",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    },
    {
      "date": "2026-03-07",
      "intent": "Easy aerobic run",
      "workout_type": "easy",
      "duration_min": 45,
      "structure_steps": [
        {
          "label": "main",
          "duration_min": 45,
          "target_metric": "pace",
          "target_value": "10:30-11:10/mi",
          "reps": null,
          "notes": null
        }
      ],
      "safety_flags": [],
      "rationale": "Aerobic conditioning."
    }
  ],
  "weekly_volume_miles": 20.3,
  "safety_flags": [
    "macro_guided"
  ],
  "rationale": "Base training week. Building aerobic fitness.",
  "context_hash": "testhash0001"
}
```

</details>
