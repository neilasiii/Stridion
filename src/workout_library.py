#!/usr/bin/env python3
"""
Workout Library Manager

Provides CRUD operations and search functionality for the workout library.
Supports workouts across all coaching domains: running, strength, mobility, nutrition.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class WorkoutLibrary:
    """Main interface for workout library operations"""

    def __init__(self, library_path: str = None):
        """
        Initialize workout library

        Args:
            library_path: Path to workout_library.json (defaults to data/library/)
        """
        if library_path is None:
            # Default to data/library/workout_library.json
            script_dir = Path(__file__).parent
            repo_root = script_dir.parent
            library_path = repo_root / "data" / "library" / "workout_library.json"

        self.library_path = Path(library_path)
        self.library_dir = self.library_path.parent

        # Ensure library directory exists
        self.library_dir.mkdir(parents=True, exist_ok=True)

        # Load or initialize library
        self.workouts = self._load_library()

    def _load_library(self) -> Dict[str, Dict]:
        """Load workout library from JSON file"""
        if not self.library_path.exists():
            # Initialize empty library
            return {
                "metadata": {
                    "created_date": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat(),
                    "version": "1.0"
                },
                "workouts": {},
                "blocks": {}
            }

        try:
            with open(self.library_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading library: {e}")
            print("Initializing new library")
            return {
                "metadata": {
                    "created_date": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat(),
                    "version": "1.0"
                },
                "workouts": {},
                "blocks": {}
            }

    def _save_library(self):
        """Save workout library to JSON file"""
        # Update last modified timestamp
        self.workouts["metadata"]["last_modified"] = datetime.now().isoformat()

        # Write to temp file first, then rename (atomic operation)
        temp_path = self.library_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w') as f:
                json.dump(self.workouts, f, indent=2)
            temp_path.replace(self.library_path)
        except Exception as e:
            print(f"Error saving library: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise

    def add_workout(self, workout: Dict[str, Any]) -> str:
        """
        Add a new workout to the library

        Args:
            workout: Workout dictionary (must include name, domain, type, content)

        Returns:
            Workout ID
        """
        # Validate required fields
        required_fields = ["name", "domain", "type", "content"]
        for field in required_fields:
            if field not in workout:
                raise ValueError(f"Missing required field: {field}")

        # Validate domain
        valid_domains = ["running", "strength", "mobility", "nutrition", "multi_domain"]
        if workout["domain"] not in valid_domains:
            raise ValueError(f"Invalid domain: {workout['domain']}. Must be one of {valid_domains}")

        # Generate ID if not provided
        if "id" not in workout:
            workout["id"] = str(uuid.uuid4())

        # Add timestamps
        now = datetime.now().isoformat()
        workout["created_date"] = now
        workout["modified_date"] = now

        # Set defaults
        if "tags" not in workout:
            workout["tags"] = []
        if "difficulty" not in workout:
            workout["difficulty"] = "intermediate"
        if "equipment" not in workout:
            workout["equipment"] = []

        # Add to library
        self.workouts["workouts"][workout["id"]] = workout
        self._save_library()

        return workout["id"]

    def get_workout(self, workout_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a workout by ID

        Args:
            workout_id: Workout ID

        Returns:
            Workout dictionary or None if not found
        """
        return self.workouts["workouts"].get(workout_id)

    def update_workout(self, workout_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing workout

        Args:
            workout_id: Workout ID
            updates: Dictionary of fields to update

        Returns:
            True if successful, False if workout not found
        """
        if workout_id not in self.workouts["workouts"]:
            return False

        # Update fields
        workout = self.workouts["workouts"][workout_id]
        for key, value in updates.items():
            if key not in ["id", "created_date"]:  # Don't allow changing ID or creation date
                workout[key] = value

        # Update modified timestamp
        workout["modified_date"] = datetime.now().isoformat()

        self._save_library()
        return True

    def delete_workout(self, workout_id: str) -> bool:
        """
        Delete a workout from the library

        Args:
            workout_id: Workout ID

        Returns:
            True if deleted, False if not found
        """
        if workout_id not in self.workouts["workouts"]:
            return False

        del self.workouts["workouts"][workout_id]
        self._save_library()
        return True

    def search(self,
               domain: Optional[str] = None,
               workout_type: Optional[str] = None,
               tags: Optional[List[str]] = None,
               difficulty: Optional[str] = None,
               duration_min: Optional[int] = None,
               duration_max: Optional[int] = None,
               training_phase: Optional[str] = None,
               vdot_range: Optional[List[int]] = None,
               equipment: Optional[List[str]] = None,
               query: Optional[str] = None,
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search workouts with various filters

        Args:
            domain: Filter by domain (running, strength, mobility, nutrition)
            workout_type: Filter by workout type
            tags: Filter by tags (workout must have ALL specified tags)
            difficulty: Filter by difficulty level
            duration_min: Minimum duration in minutes
            duration_max: Maximum duration in minutes
            training_phase: Filter by training phase
            vdot_range: Filter by VDOT range [min, max] (running only)
            equipment: Filter by available equipment (workout must use ONLY these items)
            query: Full-text search in name and description
            limit: Maximum number of results to return

        Returns:
            List of matching workouts
        """
        results = []

        for workout_id, workout in self.workouts["workouts"].items():
            # Domain filter
            if domain and workout.get("domain") != domain:
                continue

            # Type filter
            if workout_type and workout.get("type") != workout_type:
                continue

            # Difficulty filter
            if difficulty and workout.get("difficulty") != difficulty:
                continue

            # Training phase filter
            if training_phase and workout.get("training_phase") != training_phase:
                continue

            # Tags filter (must have ALL specified tags)
            if tags:
                workout_tags = set(workout.get("tags", []))
                if not all(tag in workout_tags for tag in tags):
                    continue

            # Duration filters
            workout_duration = workout.get("duration_minutes")
            if workout_duration:
                if duration_min and workout_duration < duration_min:
                    continue
                if duration_max and workout_duration > duration_max:
                    continue

            # VDOT range filter (running workouts)
            if vdot_range:
                workout_vdot = workout.get("vdot_range")
                if not workout_vdot:
                    continue
                # Check if ranges overlap
                if workout_vdot[1] < vdot_range[0] or workout_vdot[0] > vdot_range[1]:
                    continue

            # Equipment filter (workout must use ONLY specified equipment)
            if equipment:
                workout_equipment = set(workout.get("equipment", []))
                available_equipment = set(equipment)
                if not workout_equipment.issubset(available_equipment):
                    continue

            # Full-text search
            if query:
                query_lower = query.lower()
                searchable_text = f"{workout.get('name', '')} {workout.get('description', '')}".lower()
                if query_lower not in searchable_text:
                    continue

            results.append(workout)

        # Apply limit
        if limit:
            results = results[:limit]

        return results

    def list_all_workouts(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all workouts, optionally filtered by domain

        Args:
            domain: Optional domain filter

        Returns:
            List of workouts
        """
        workouts = list(self.workouts["workouts"].values())

        if domain:
            workouts = [w for w in workouts if w.get("domain") == domain]

        return workouts

    def get_stats(self) -> Dict[str, Any]:
        """
        Get library statistics

        Returns:
            Dictionary with counts by domain, type, difficulty, etc.
        """
        workouts = self.workouts["workouts"].values()

        stats = {
            "total_workouts": len(workouts),
            "by_domain": {},
            "by_type": {},
            "by_difficulty": {},
            "by_training_phase": {}
        }

        for workout in workouts:
            # Count by domain
            domain = workout.get("domain", "unknown")
            stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1

            # Count by type
            workout_type = workout.get("type", "unknown")
            stats["by_type"][workout_type] = stats["by_type"].get(workout_type, 0) + 1

            # Count by difficulty
            difficulty = workout.get("difficulty", "unknown")
            stats["by_difficulty"][difficulty] = stats["by_difficulty"].get(difficulty, 0) + 1

            # Count by training phase
            phase = workout.get("training_phase", "unknown")
            stats["by_training_phase"][phase] = stats["by_training_phase"].get(phase, 0) + 1

        return stats

    def add_training_block(self, block: Dict[str, Any]) -> str:
        """
        Add a training block (multi-day/week program)

        Args:
            block: Training block dictionary

        Returns:
            Block ID
        """
        # Generate ID if not provided
        if "id" not in block:
            block["id"] = str(uuid.uuid4())

        # Add timestamps
        now = datetime.now().isoformat()
        block["created_date"] = now
        block["modified_date"] = now

        # Add to library
        self.workouts["blocks"][block["id"]] = block
        self._save_library()

        return block["id"]

    def get_training_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get a training block by ID"""
        return self.workouts["blocks"].get(block_id)

    def list_training_blocks(self) -> List[Dict[str, Any]]:
        """List all training blocks"""
        return list(self.workouts["blocks"].values())


def main():
    """Example usage"""
    library = WorkoutLibrary()

    # Example: Add a threshold workout
    threshold_workout = {
        "name": "Classic 20-Minute Threshold",
        "domain": "running",
        "type": "tempo",
        "description": "Continuous 20-minute run at threshold pace",
        "tags": ["threshold", "tempo", "lactate_threshold"],
        "difficulty": "intermediate",
        "duration_minutes": 40,
        "equipment": [],
        "training_phase": "quality",
        "vdot_range": [40, 60],
        "content": {
            "warmup": {
                "duration_minutes": 15,
                "description": "Easy jog",
                "pace": "easy"
            },
            "main_set": [
                {
                    "repetitions": 1,
                    "work_duration": "20:00",
                    "work_pace": "T",
                    "description": "Continuous threshold run"
                }
            ],
            "cooldown": {
                "duration_minutes": 10,
                "description": "Easy jog",
                "pace": "easy"
            },
            "total_duration_minutes": 45,
            "estimated_tss": 65
        }
    }

    workout_id = library.add_workout(threshold_workout)
    print(f"Added workout: {workout_id}")

    # Search for tempo workouts
    results = library.search(domain="running", workout_type="tempo")
    print(f"\nFound {len(results)} tempo workouts")

    # Get stats
    stats = library.get_stats()
    print(f"\nLibrary stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    main()
