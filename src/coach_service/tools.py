"""
Tool definitions and execution for coaching agents.

Provides a safe, sandboxed way for AI agents to execute predefined commands.
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Callable
from datetime import datetime


class ToolExecutor:
    """Executes predefined tools/commands for AI agents."""

    def __init__(self, project_root: Path):
        """
        Initialize tool executor.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Define available tools with their schemas and execution functions.

        Returns:
            Dictionary of tool definitions
        """
        return {
            "sync_health_data": {
                "description": "Sync health data from Garmin Connect. Use this when you need up-to-date health metrics, activities, sleep data, or when the user mentions completing a workout.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days of data to sync (default: 30)",
                            "default": 30
                        }
                    }
                },
                "function": self._sync_health_data
            },
            "list_recent_activities": {
                "description": "List recent activities from health data cache. Faster than full sync when you just need to check recent workouts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of activities to return (default: 10)",
                            "default": 10
                        }
                    }
                },
                "function": self._list_recent_activities
            },
            "get_workout_from_library": {
                "description": "Search the workout library for pre-built workouts. Use this to find workouts matching specific criteria like domain, type, difficulty, or duration.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Workout domain: running, strength, mobility, or nutrition",
                            "enum": ["running", "strength", "mobility", "nutrition"]
                        },
                        "type": {
                            "type": "string",
                            "description": "Workout type (e.g., easy, tempo, intervals, recovery)"
                        },
                        "difficulty": {
                            "type": "string",
                            "description": "Difficulty level: beginner, intermediate, or advanced",
                            "enum": ["beginner", "intermediate", "advanced"]
                        },
                        "duration_max": {
                            "type": "integer",
                            "description": "Maximum duration in minutes"
                        }
                    }
                },
                "function": self._get_workout_from_library
            },
            "save_training_plan": {
                "description": "Save a training plan to the athlete's plans directory. Use this when creating a multi-day or multi-week training plan.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Filename for the plan (e.g., 'week1_base_building.md')"
                        },
                        "content": {
                            "type": "string",
                            "description": "Markdown content of the training plan"
                        }
                    },
                    "required": ["filename", "content"]
                },
                "function": self._save_training_plan
            },
            "read_athlete_file": {
                "description": "Read a specific athlete context file. Use this to get detailed information from goals, training history, preferences, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path relative to data/athlete/ (e.g., 'goals.md', 'training_history.md')"
                        }
                    },
                    "required": ["file_path"]
                },
                "function": self._read_athlete_file
            },
            "get_current_date": {
                "description": "Get the current date and time. Use this when you need to know today's date for workout planning, scheduling, or calculating dates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "Date format: 'full' (default, includes time), 'date' (date only), or 'iso' (ISO 8601 format)",
                            "enum": ["full", "date", "iso"],
                            "default": "full"
                        }
                    }
                },
                "function": self._get_current_date
            },
            "calculate_date_info": {
                "description": "Calculate the day of week for any date. Use this when you need to know what day of the week a specific date falls on (e.g., 'What day is 2025-11-24?'). This ensures accurate day-of-week labels when creating schedules or plans.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (e.g., '2025-11-24')"
                        }
                    },
                    "required": ["date"]
                },
                "function": self._calculate_date_info
            },
            "calculate_vdot": {
                "description": "Calculate VDOT from race performance using Jack Daniels' official formula. Also returns training paces for all zones (Easy, Marathon, Threshold, Interval, Repetition). Use this when athlete reports a race result or asks about their training paces.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "distance": {
                            "type": "string",
                            "description": "Race distance: '5K', '10K', 'half', or 'marathon'",
                            "enum": ["5K", "10K", "half", "marathon"]
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Hours component of finish time"
                        },
                        "minutes": {
                            "type": "integer",
                            "description": "Minutes component of finish time"
                        },
                        "seconds": {
                            "type": "integer",
                            "description": "Seconds component of finish time"
                        }
                    },
                    "required": ["distance", "hours", "minutes", "seconds"]
                },
                "function": self._calculate_vdot
            }
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas in Gemini function calling format.

        Returns:
            List of tool schemas
        """
        schemas = []
        for name, tool_def in self.tools.items():
            schema = {
                "name": name,
                "description": tool_def["description"],
                "parameters": tool_def["parameters"]
            }
            schemas.append(schema)
        return schemas

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool

        Returns:
            Dictionary with 'success' boolean and 'result' or 'error'
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

        try:
            tool_def = self.tools[tool_name]
            function = tool_def["function"]
            result = function(parameters)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # Tool implementation methods

    def _sync_health_data(self, params: Dict[str, Any]) -> str:
        """Sync health data from Garmin Connect."""
        days = params.get("days", 30)
        script_path = self.project_root / "bin" / "sync_garmin_data.sh"

        try:
            result = subprocess.run(
                ["bash", str(script_path), "--days", str(days)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project_root)
            )

            if result.returncode == 0:
                return f"Health data synced successfully (last {days} days).\n\nOutput:\n{result.stdout}"
            else:
                return f"Health data sync failed.\n\nError:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "Health data sync timed out after 60 seconds."
        except Exception as e:
            return f"Error running sync: {str(e)}"

    def _list_recent_activities(self, params: Dict[str, Any]) -> str:
        """List recent activities from cache."""
        limit = params.get("limit", 10)
        cache_path = self.project_root / "data" / "health" / "health_data_cache.json"

        if not cache_path.exists():
            return "No health data cache found. Run sync_health_data first."

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            activities = data.get('activities', [])[:limit]
            if not activities:
                return "No activities found in cache."

            result = f"Recent {len(activities)} activities:\n\n"
            for act in activities:
                date = act.get('date', 'Unknown')[:10]
                act_type = act.get('activity_type', 'Unknown')
                distance = act.get('distance_miles', 0)
                duration_min = act.get('duration_seconds', 0) / 60
                avg_hr = act.get('avg_heart_rate', 'N/A')
                result += f"- {date}: {act_type}, {distance:.2f} mi, {duration_min:.1f} min, Avg HR: {avg_hr}\n"

            return result
        except Exception as e:
            return f"Error reading activities: {str(e)}"

    def _get_workout_from_library(self, params: Dict[str, Any]) -> str:
        """Search workout library."""
        script_path = self.project_root / "bin" / "workout_library.sh"

        # Build search command
        cmd = ["bash", str(script_path), "search"]

        if "domain" in params:
            cmd.extend(["--domain", params["domain"]])
        if "type" in params:
            cmd.extend(["--type", params["type"]])
        if "difficulty" in params:
            cmd.extend(["--difficulty", params["difficulty"]])
        if "duration_max" in params:
            cmd.extend(["--duration-max", str(params["duration_max"])])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_root)
            )

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Workout search failed: {result.stderr}"
        except Exception as e:
            return f"Error searching workout library: {str(e)}"

    def _save_training_plan(self, params: Dict[str, Any]) -> str:
        """Save a training plan."""
        filename = params.get("filename", "")
        content = params.get("content", "")

        if not filename:
            return "Error: filename is required"
        if not content:
            return "Error: content is required"

        # Sanitize filename
        filename = filename.replace("/", "_").replace("\\", "_")
        if not filename.endswith(".md"):
            filename += ".md"

        plan_path = self.project_root / "data" / "plans" / filename

        try:
            with open(plan_path, 'w') as f:
                f.write(content)
            return f"Training plan saved successfully to: data/plans/{filename}"
        except Exception as e:
            return f"Error saving training plan: {str(e)}"

    def _read_athlete_file(self, params: Dict[str, Any]) -> str:
        """Read an athlete context file."""
        file_path = params.get("file_path", "")

        if not file_path:
            return "Error: file_path is required"

        # Sanitize path (prevent directory traversal)
        file_path = file_path.replace("..", "").lstrip("/")
        full_path = self.project_root / "data" / "athlete" / file_path

        if not full_path.exists():
            return f"File not found: {file_path}"

        try:
            with open(full_path, 'r') as f:
                content = f.read()
            return f"Contents of {file_path}:\n\n{content}"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _get_current_date(self, params: Dict[str, Any]) -> str:
        """Get current date and time."""
        format_type = params.get("format", "full")
        now = datetime.now()

        if format_type == "date":
            return now.strftime("%Y-%m-%d")
        elif format_type == "iso":
            return now.isoformat()
        else:  # full
            return now.strftime("%Y-%m-%d %H:%M:%S (%A)")

    def _calculate_date_info(self, params: Dict[str, Any]) -> str:
        """Calculate day of week and other info for a given date."""
        date_str = params.get("date", "")

        if not date_str:
            return "Error: date parameter is required (format: YYYY-MM-DD)"

        try:
            # Parse the date string
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            # Return formatted info
            day_name = date_obj.strftime("%A")
            month_name = date_obj.strftime("%B")
            day_num = date_obj.strftime("%d").lstrip("0")
            year = date_obj.strftime("%Y")

            return f"{day_name}, {month_name} {day_num}, {year}"
        except ValueError as e:
            return f"Error parsing date '{date_str}': {str(e)}. Please use YYYY-MM-DD format."

    def _calculate_vdot(self, params: Dict[str, Any]) -> str:
        """Calculate VDOT and training paces from race performance."""
        distance = params.get("distance", "")
        hours = params.get("hours", 0)
        minutes = params.get("minutes", 0)
        seconds = params.get("seconds", 0)

        if not distance:
            return "Error: distance parameter is required"

        try:
            # Add src directory to path to import vdot_calculator
            src_path = self.project_root / "src"
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))

            from vdot_calculator import calculate_vdot_from_race, format_pace

            # Calculate VDOT and paces
            vdot, paces = calculate_vdot_from_race(distance, hours, minutes, seconds)

            # Format output
            result = f"Race Time: {hours}:{minutes:02d}:{seconds:02d} ({distance})\n"
            result += f"VDOT: {vdot:.1f}\n\n"
            result += "Training Paces (per mile):\n"
            result += "-" * 40 + "\n"

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

                result += f"{name:12} ({zone}): {pace_str}\n"

            return result

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error calculating VDOT: {str(e)}"
