from datetime import date, timedelta

from brain.macro_plan import validate_macro_plan
from brain.planner import (
    _enforce_structure_constraints,
    _normalize_weekly_structure,
    replan_remaining_week,
)
from brain.schemas import MacroPaces, MacroPlan, MacroWeek, PlanDecision
from memory.db import (
    get_active_plan,
    init_db,
    insert_plan,
    insert_plan_days,
    query_events,
    set_active_plan,
)


RUN_TYPES = {"easy", "tempo", "interval", "long"}


def _macro_week(i: int, ws: str, target: float, ceil: float | None = None):
    return MacroWeek(
        week_number=i,
        week_start=ws,
        phase="base",
        volume_floor_miles=max(0, target - 2),
        volume_target_miles=target,
        volume_ceiling_miles=ceil if ceil is not None else target + 2,
        long_run_max_min=60,
        intensity_budget="low",
        quality_sessions_allowed=0,
        key_workout_type="easy",
        recommended_session_types=["easy", "long"],
        paces=MacroPaces(
            easy="10:00/mi", tempo=None, interval=None, long_run="10:30/mi"
        ),
        planner_notes="",
        phase_rationale="",
    )


def _plan_for_week(
    start: date, workout_types: list[str], priorities: list[str] | None = None
) -> PlanDecision:
    priorities = priorities or ["nice_to_have"] * len(workout_types)
    return PlanDecision.model_validate(
        {
            "week_start": start.isoformat(),
            "week_end": (start + timedelta(days=6)).isoformat(),
            "phase": "base",
            "weekly_volume_miles": 20,
            "safety_flags": [],
            "rationale": "",
            "context_hash": "x",
            "days": [
                {
                    "date": (start + timedelta(days=i)).isoformat(),
                    "intent": "",
                    "workout_type": workout_types[i],
                    "priority": priorities[i],
                    "duration_min": 45 if workout_types[i] in RUN_TYPES else 0,
                    "structure_steps": (
                        [
                            {
                                "label": "main",
                                "duration_min": 45,
                                "target_metric": "rpe",
                                "target_value": "RPE 4",
                            }
                        ]
                        if workout_types[i] in RUN_TYPES
                        else []
                    ),
                    "safety_flags": [],
                    "rationale": "",
                }
                for i in range(7)
            ],
        }
    )


def _seed_active_plan(
    db_path, start: date, workout_types: list[str], priorities: list[str] | None = None
) -> str:
    decision = _plan_for_week(start, workout_types, priorities)
    pid = insert_plan(
        start,
        start + timedelta(days=6),
        decision.model_dump(),
        context_hash="seed",
        db_path=db_path,
    )
    insert_plan_days(
        pid,
        [
            {"day": d.date, "intent": d.intent, "workout_json": d.model_dump()}
            for d in decision.days
        ],
        db_path=db_path,
    )
    set_active_plan(pid, db_path=db_path)
    return pid


def test_macro_band_validation_order_and_ceiling_jump():
    start = date(2026, 1, 4)
    ok = MacroPlan(
        mode="base_block",
        race_date=None,
        race_name=None,
        race_distance=None,
        vdot=45,
        start_week=start.isoformat(),
        total_weeks=2,
        peak_weekly_miles=22,
        rationale="ok",
        weeks=[
            _macro_week(1, start.isoformat(), 20),
            _macro_week(2, (start + timedelta(days=7)).isoformat(), 21),
        ],
    )
    assert validate_macro_plan(ok).ok

    bad_order = ok.model_copy(deep=True)
    bad_order.weeks[0].volume_floor_miles = 22
    bad_order.weeks[0].volume_target_miles = 20
    assert not validate_macro_plan(bad_order).ok

    bad_jump = ok.model_copy(deep=True)
    bad_jump.weeks[1].volume_ceiling_miles = 30
    errs = validate_macro_plan(bad_jump)
    assert not errs.ok
    assert any("ceiling ramp" in e for e in errs.errors)


def test_structure_constraints_anchor_preference_and_min_backfill():
    start = date(2026, 1, 4)  # Sunday
    decision = _plan_for_week(
        start,
        ["easy", "easy", "rest", "easy", "rest", "easy", "rest"],
        [
            "optional",
            "must_do",
            "optional",
            "nice_to_have",
            "optional",
            "must_do",
            "optional",
        ],
    )
    structure = _normalize_weekly_structure(
        {
            "athlete": {
                "weekly_structure": {
                    "min_runs_per_week": 4,
                    "preferred_runs_per_week": 4,
                    "max_runs_per_week": 4,
                    "anchor_days": ["monday", "wednesday", "friday", "saturday"],
                    "non_negotiable_blocked_days": ["sunday"],
                }
            }
        }
    )
    _enforce_structure_constraints(decision, structure)

    run_days = [d for d in decision.days if d.workout_type in RUN_TYPES]
    assert len(run_days) == 4
    # Sunday blocked should be rest
    assert decision.days[0].workout_type in {"rest", "cross"}
    # Monday anchor is must_do and should survive trimming
    assert decision.days[1].workout_type in RUN_TYPES
    # Wednesday anchor should be backfilled to satisfy min=4 after blocked-day conversion
    assert decision.days[3].workout_type in RUN_TYPES


def test_replan_drops_missed_easy_and_persists_revision_metadata(tmp_path):
    db = tmp_path / "coach.sqlite"
    init_db(db)

    start = date.today() - timedelta(days=date.today().weekday() + 1)
    original_plan_id = _seed_active_plan(
        db,
        start,
        ["easy", "easy", "easy", "easy", "long", "rest", "rest"],
    )

    # Use start+1 (Monday = index 1 = "easy") as today and missed date.
    # This is day-of-week independent — index 1 is always "easy" in the seeded plan.
    today_iso = (start + timedelta(days=1)).isoformat()
    decision = replan_remaining_week({"today": today_iso}, [today_iso], db_path=db)
    assert isinstance(decision, PlanDecision)
    today_day = next(d for d in decision.days if d.date == today_iso)
    assert today_day.workout_type == "rest"
    assert "missed_easy_dropped" in today_day.safety_flags

    active = get_active_plan(db_path=db)
    assert active["supersedes_plan_id"] == original_plan_id
    assert active["replan_reason"] == "missed_workout"
    assert active["plan_revision_number"] == 2
    assert active["replan_details"]["dropped_easy"] == [today_iso]

    events = query_events(event_type="week_replanned", db_path=db)
    assert events
    assert events[0]["payload_json"]


def test_replan_moves_quality_session_with_correct_type(tmp_path):
    """Quality relocation must preserve the original workout type (not 'rest')."""
    db = tmp_path / "coach.sqlite"
    init_db(db)

    start = date.today() - timedelta(days=date.today().weekday() + 1)
    # day 1 (Monday) = tempo; day 2 (Tuesday) = easy — safe relocation slot
    _seed_active_plan(
        db,
        start,
        ["easy", "tempo", "easy", "long", "rest", "easy", "rest"],
        [
            "nice_to_have",
            "must_do",
            "nice_to_have",
            "must_do",
            "optional",
            "nice_to_have",
            "optional",
        ],
    )

    missed_date = (start + timedelta(days=1)).isoformat()  # Monday = tempo day
    decision = replan_remaining_week(
        {"today": start.isoformat()}, [missed_date], db_path=db
    )

    # The missed tempo should have been relocated, not silently dropped as rest
    relocated = [d for d in decision.days if "moved_quality_session" in d.safety_flags]
    assert relocated, "Expected quality session to be relocated"
    assert relocated[0].workout_type == "tempo", (
        f"Relocated session has wrong type: {relocated[0].workout_type!r} (expected 'tempo')"
    )

    # Original missed day should now be rest
    missed_day = next(d for d in decision.days if d.date == missed_date)
    assert missed_day.workout_type == "rest"

    # No consecutive hard days after reflow
    for i in range(1, len(decision.days)):
        assert not (
            decision.days[i - 1].workout_type in {"tempo", "interval", "long"}
            and decision.days[i].workout_type in {"tempo", "interval", "long"}
        )


def test_replan_shortens_or_drops_long_on_constraints(tmp_path):
    db = tmp_path / "coach.sqlite"
    init_db(db)

    start = date.today() - timedelta(days=date.today().weekday() + 1)
    _seed_active_plan(
        db,
        start,
        ["easy", "easy", "long", "tempo", "rest", "rest", "rest"],
    )

    missed_long_date = (start + timedelta(days=2)).isoformat()
    decision = replan_remaining_week(
        {
            "today": start.isoformat(),
            "athlete": {
                "weekly_structure": {
                    "non_negotiable_blocked_days": ["thursday", "friday"]
                }
            },
        },
        [missed_long_date],
        db_path=db,
    )

    long_days = [d for d in decision.days if d.workout_type == "long"]
    assert len(long_days) <= 1
    if long_days:
        assert long_days[0].duration_min <= 45
