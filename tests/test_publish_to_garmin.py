import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch


def test_dry_run_skips_when_signature_unchanged(tmp_path: Path):
    import skills.publish_to_garmin as pub

    target_date = date.today().isoformat()
    workout = {
        "scheduled_date": target_date,
        "name": "45 min E",
        "description": "Easy run",
        "source": "internal_plan",
        "_degraded": False,
    }
    signature = pub._workout_signature(workout)

    log_path = tmp_path / "generated_workouts.json"
    log_path.write_text(
        json.dumps(
            {
                "running": {
                    target_date: {
                        "garmin_id": 111,
                        "signature": signature,
                    }
                }
            }
        )
    )

    with (
        patch.object(pub, "_GENERATED_LOG", log_path),
        patch("skills.plans.get_active_sessions", return_value=[{"date": target_date}]),
        patch("skills.internal_plan_to_scheduled_workouts.convert", return_value=[workout]),
    ):
        result = pub.publish(days=1, dry_run=True)

    assert result["prepared"] == []
    assert any("unchanged" in s["reason"] for s in result["skipped"])


def test_signature_changes_when_structure_changes_even_if_text_matches():
    import skills.publish_to_garmin as pub

    target_date = date.today().isoformat()
    base = {
        "scheduled_date": target_date,
        "name": "50 min E",
        "description": "Aerobic run",
        "source": "internal_plan",
        "_degraded": False,
    }
    with_steps_a = {
        **base,
        "_signature_context": {
            "workout_type": "easy",
            "duration_min": 50,
            "intent": "Aerobic run",
            "structure_steps": [
                {"label": "warmup", "duration_min": 10},
                {"label": "main", "duration_min": 30},
                {"label": "cooldown", "duration_min": 10},
            ],
        },
    }
    with_steps_b = {
        **base,
        "_signature_context": {
            "workout_type": "easy",
            "duration_min": 50,
            "intent": "Aerobic run",
            "structure_steps": [
                {"label": "warmup", "duration_min": 5},
                {"label": "main", "duration_min": 40},
                {"label": "cooldown", "duration_min": 5},
            ],
        },
    }

    assert pub._workout_signature(with_steps_a) != pub._workout_signature(with_steps_b)


def test_live_publish_replaces_changed_workout_and_updates_log(tmp_path: Path):
    import skills.publish_to_garmin as pub

    target_date = date.today().isoformat()
    workout = {
        "scheduled_date": target_date,
        "name": "30 min E",
        "description": "Adjusted easy day",
        "source": "internal_plan",
        "_degraded": False,
    }
    new_signature = pub._workout_signature(workout)

    log_path = tmp_path / "generated_workouts.json"
    log_path.write_text(
        json.dumps(
            {
                "running": {
                    target_date: {
                        "garmin_id": 111,
                        "signature": "old-signature",
                    }
                }
            }
        )
    )

    with (
        patch.object(pub, "_GENERATED_LOG", log_path),
        patch("skills.plans.get_active_sessions", return_value=[{"date": target_date}]),
        patch("skills.internal_plan_to_scheduled_workouts.convert", return_value=[workout]),
        patch("workout_parser.parse_workout_description", return_value=object()),
        patch("auto_workout_generator.generate_workout_name", return_value="Updated Workout"),
        patch("auto_workout_generator.generate_garmin_workout", return_value={"workoutName": "Updated Workout"}),
        patch("workout_uploader.get_garmin_client", return_value=object()),
        patch("workout_uploader.upload_workout", return_value={"workoutId": 222}),
        patch("workout_uploader.schedule_workout", return_value=True),
        patch("workout_uploader.delete_workout", return_value=True) as mock_delete,
        patch("memory.db.init_db"),
        patch("memory.db.insert_event", return_value="event-id"),
    ):
        result = pub.publish(days=1, dry_run=False)

    assert target_date in result["published"]
    mock_delete.assert_called_once()
    _, delete_args, _ = mock_delete.mock_calls[0]
    assert delete_args[1] == 111

    saved = json.loads(log_path.read_text())
    assert saved["running"][target_date]["garmin_id"] == 222
    assert saved["running"][target_date]["signature"] == new_signature


def test_live_publish_removes_obsolete_running_workout_for_rest_day(tmp_path: Path):
    import skills.publish_to_garmin as pub

    target_date = date.today().isoformat()
    log_path = tmp_path / "generated_workouts.json"
    log_path.write_text(
        json.dumps(
            {
                "running": {
                    target_date: {
                        "garmin_id": 333,
                        "signature": "any",
                    }
                }
            }
        )
    )

    with (
        patch.object(pub, "_GENERATED_LOG", log_path),
        patch(
            "skills.plans.get_active_sessions",
            return_value=[
                {
                    "date": target_date,
                    "workout_type": "rest",
                }
            ],
        ),
        patch("skills.internal_plan_to_scheduled_workouts.convert", return_value=[]),
        patch("workout_uploader.get_garmin_client", return_value=object()),
        patch("workout_uploader.delete_workout", return_value=True) as mock_delete,
        patch("memory.db.init_db"),
        patch("memory.db.insert_event", return_value="event-id"),
    ):
        result = pub.publish(days=1, dry_run=False)

    assert result["removed"] == [target_date]
    mock_delete.assert_called_once()
    _, delete_args, _ = mock_delete.mock_calls[0]
    assert delete_args[1] == 333

    saved = json.loads(log_path.read_text())
    assert target_date not in saved["running"]


def test_live_publish_does_not_remove_unknown_running_variant(tmp_path: Path):
    import skills.publish_to_garmin as pub

    target_date = date.today().isoformat()
    log_path = tmp_path / "generated_workouts.json"
    log_path.write_text(
        json.dumps(
            {
                "running": {
                    target_date: {
                        "garmin_id": 444,
                        "signature": "sig",
                    }
                }
            }
        )
    )

    with (
        patch.object(pub, "_GENERATED_LOG", log_path),
        patch(
            "skills.plans.get_active_sessions",
            return_value=[
                {
                    "date": target_date,
                    "workout_type": "recovery",
                }
            ],
        ),
        patch("skills.internal_plan_to_scheduled_workouts.convert", return_value=[]),
        patch("workout_uploader.get_garmin_client", return_value=object()),
        patch("workout_uploader.delete_workout", return_value=True) as mock_delete,
        patch("memory.db.init_db"),
        patch("memory.db.insert_event", return_value="event-id"),
    ):
        result = pub.publish(days=1, dry_run=False)

    assert result["removed"] == []
    mock_delete.assert_not_called()
    saved = json.loads(log_path.read_text())
    assert saved["running"][target_date]["garmin_id"] == 444


def test_dry_run_flags_logged_date_missing_from_active_plan(tmp_path: Path):
    import skills.publish_to_garmin as pub

    today_str = date.today().isoformat()
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
    log_path = tmp_path / "generated_workouts.json"
    log_path.write_text(
        json.dumps(
            {
                "running": {
                    today_str: {
                        "garmin_id": 555,
                        "signature": "sig",
                    }
                }
            }
        )
    )

    with (
        patch.object(pub, "_GENERATED_LOG", log_path),
        patch(
            "skills.plans.get_active_sessions",
            return_value=[
                {
                    "date": tomorrow_str,
                    "workout_type": "rest",
                }
            ],
        ),
        patch("skills.internal_plan_to_scheduled_workouts.convert", return_value=[]),
    ):
        result = pub.publish(days=1, dry_run=True)

    assert result["removed"] == []
    assert any(
        s["date"] == today_str and "no active plan session" in s["reason"]
        for s in result["skipped"]
    )


def test_live_remove_delete_exception_emits_single_warning(tmp_path: Path):
    import skills.publish_to_garmin as pub

    target_date = date.today().isoformat()
    log_path = tmp_path / "generated_workouts.json"
    log_path.write_text(
        json.dumps(
            {
                "running": {
                    target_date: {
                        "garmin_id": 777,
                        "signature": "sig",
                    }
                }
            }
        )
    )

    with (
        patch.object(pub, "_GENERATED_LOG", log_path),
        patch(
            "skills.plans.get_active_sessions",
            return_value=[
                {
                    "date": target_date,
                    "workout_type": "rest",
                }
            ],
        ),
        patch("skills.internal_plan_to_scheduled_workouts.convert", return_value=[]),
        patch("workout_uploader.get_garmin_client", return_value=object()),
        patch("workout_uploader.delete_workout", side_effect=RuntimeError("api timeout")),
        patch("memory.db.init_db"),
        patch("memory.db.insert_event", return_value="event-id"),
    ):
        result = pub.publish(days=1, dry_run=False)

    relevant = [w for w in result["warnings"] if target_date in w]
    assert len(relevant) == 1
    assert "delete failed for Garmin workout 777" in relevant[0]
    assert "could not delete obsolete" not in relevant[0]


def test_live_publish_same_day_mixed_sessions_does_not_remove_running_workout(tmp_path: Path):
    import skills.publish_to_garmin as pub

    target_date = date.today().isoformat()
    log_path = tmp_path / "generated_workouts.json"
    log_path.write_text(
        json.dumps(
            {
                "running": {
                    target_date: {
                        "garmin_id": 888,
                        "signature": "sig",
                    }
                }
            }
        )
    )

    with (
        patch.object(pub, "_GENERATED_LOG", log_path),
        patch(
            "skills.plans.get_active_sessions",
            return_value=[
                {"date": target_date, "workout_type": "strength"},
                {"date": target_date, "workout_type": "easy"},
            ],
        ),
        patch("skills.internal_plan_to_scheduled_workouts.convert", return_value=[]),
        patch("workout_uploader.get_garmin_client", return_value=object()),
        patch("workout_uploader.delete_workout", return_value=True) as mock_delete,
        patch("memory.db.init_db"),
        patch("memory.db.insert_event", return_value="event-id"),
    ):
        result = pub.publish(days=1, dry_run=False)

    assert result["removed"] == []
    mock_delete.assert_not_called()
