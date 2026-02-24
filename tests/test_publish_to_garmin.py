import json
from datetime import date
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
