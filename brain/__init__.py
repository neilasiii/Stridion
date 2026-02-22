"""
Brain interface — LLM planner for the running coach system.

The Brain reads ONLY the Context Packet (from memory.build_context_packet).
It outputs validated Pydantic objects that are immediately persisted to SQLite.

Authority: internal plan in SQLite is authoritative. FinalSurge is not.
"""

from .planner import plan_week, adjust_today
from .schemas import PlanDecision, TodayAdjustment, PlanDay, WorkoutStep
from .schemas import MacroPlan, MacroWeek, MacroPaces
from .macro_plan import generate_macro_plan, validate_macro_plan, MacroValidationError

__all__ = [
    "plan_week",
    "adjust_today",
    "PlanDecision",
    "TodayAdjustment",
    "PlanDay",
    "WorkoutStep",
    "MacroPlan",
    "MacroWeek",
    "MacroPaces",
    "generate_macro_plan",
    "validate_macro_plan",
    "MacroValidationError",
]
