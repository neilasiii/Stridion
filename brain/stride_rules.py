"""
Stride validation and deterministic rewrite utilities.

Strides are short acceleration bursts (15–40 seconds) within easy runs.
They are NOT sustained tempo efforts or sub-threshold intervals.

Hard limits
-----------
  Rep duration:       ≤ 40 seconds  (STRIDE_REP_MAX_SEC)
  Rep count:          2–10
  Total stride time:  ≤ 300 seconds (5 minutes)

Schema constraint
-----------------
The Brain schema stores duration_min in whole minutes (ge=1 = 60 s minimum).
On easy+strides days, any interval-like rep (duration_min ≥ 1) is invalid as a
stride rep and triggers rewrite — 60 s already exceeds the 40 s stride cap.

Rewrite
-------
rewrite_strides() replaces invalid interval steps with a canonical note-bearing
"main" step.  Sub-minute stride durations are expressed only via the notes text;
duration_min stays ≥ 1 (schema constraint).  The renderer reads the notes text
to emit the correct description string.
"""

from typing import Any, Dict, List, Tuple

# ── Hard limits ────────────────────────────────────────────────────────────────

STRIDE_REP_MAX_SEC    = 40     # Hard max per rep (40 s)
STRIDE_REPS_MIN       = 2
STRIDE_REPS_MAX       = 10
STRIDE_TOTAL_MAX_SEC  = 300    # 5 minutes total

# ── Canonical rewrite constants ────────────────────────────────────────────────

CANONICAL_REPS         = 6
CANONICAL_REP_SEC      = 20    # 20 seconds
CANONICAL_RECOVERY_SEC = 60    # 60 s easy jog

# Notes field for the rewritten main step (≤ 80 chars per schema)
CANONICAL_NOTE = (
    f"{CANONICAL_REPS}x{CANONICAL_REP_SEC}s strides @ 5K pace "
    f"on {CANONICAL_RECOVERY_SEC}s easy jog"
)

# Keywords that signal a stride day
_STRIDE_KEYWORDS = ("stride", "strides")


# ── Public API ─────────────────────────────────────────────────────────────────

def is_stride_intent(intent: str) -> bool:
    """Return True if the intent text suggests strides-within-easy-run."""
    lower = intent.lower()
    return any(k in lower for k in _STRIDE_KEYWORDS)


def validate_strides(steps: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Return (ok, reason).

    ok=False means the steps represent intervals (not strides) and must not
    be presented as stride work.  Only "interval" steps and reps > 1 "main"
    steps are evaluated; warmup/cooldown/plain-main are skipped.

    On easy+strides days, any interval-like rep with duration_min ≥ 1 (= 60 s)
    is invalid as a stride rep — 60 s already exceeds the 40 s stride cap.
    """
    candidates = [
        s for s in steps
        if s.get("label") == "interval"
        or (s.get("label") == "main" and (s.get("reps") or 0) > 1)
    ]

    if not candidates:
        return True, "no interval steps present"

    for s in candidates:
        dur_min = s.get("duration_min", 0)
        dur_sec = dur_min * 60
        reps    = s.get("reps") or 1

        # On easy+strides days, any interval-like rep ≥ 1 min is invalid as a stride rep
        if dur_min >= 1:
            return False, (
                f"rep duration {dur_min}min ({dur_sec}s) > {STRIDE_REP_MAX_SEC}s max — "
                f"reps of {dur_min}+ min are intervals, not strides"
            )

        if dur_sec > STRIDE_REP_MAX_SEC:
            return False, (
                f"rep duration {dur_sec}s > {STRIDE_REP_MAX_SEC}s max per stride rep"
            )

        total_sec = dur_sec * reps
        if total_sec > STRIDE_TOTAL_MAX_SEC:
            return False, (
                f"total stride time {total_sec}s > {STRIDE_TOTAL_MAX_SEC}s "
                f"({reps} × {dur_sec}s)"
            )

        if reps > STRIDE_REPS_MAX:
            return False, f"{reps} reps > {STRIDE_REPS_MAX} max stride reps"

        if reps < STRIDE_REPS_MIN:
            return False, f"{reps} reps < {STRIDE_REPS_MIN} minimum stride reps"

    return True, "ok"


def rewrite_strides(
    steps: List[Dict[str, Any]],
    duration_min: int,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Replace invalid interval steps with a canonical note-bearing main step.

    Returns (new_steps, rewrite_description).

    Preserves warmup and cooldown.  All "interval" steps are removed.
    The replacement "main" step carries CANONICAL_NOTE so the renderer can
    emit "N min E + 6x20 sec strides @ ~5K effort on 60 sec easy jog recovery".

    duration_min stays ≥ 1 throughout (schema constraint).
    """
    warmup   = next((s for s in steps if s.get("label") == "warmup"),   None)
    cooldown = next((s for s in steps if s.get("label") == "cooldown"), None)

    wu_min = warmup  ["duration_min"] if warmup   else 0
    cd_min = cooldown["duration_min"] if cooldown else 0
    main_dur = max(duration_min - wu_min - cd_min, 1)

    canonical_main: Dict[str, Any] = {
        "label":         "main",
        "duration_min":  main_dur,
        "target_metric": "rpe",
        "target_value":  "easy + strides",
        "reps":          None,
        "notes":         CANONICAL_NOTE,
    }

    new_steps: List[Dict[str, Any]] = []
    if warmup:
        new_steps.append(dict(warmup))
    new_steps.append(canonical_main)
    if cooldown:
        new_steps.append(dict(cooldown))

    reason = (
        f"invalid interval steps replaced with canonical "
        f"{CANONICAL_REPS}x{CANONICAL_REP_SEC}s strides"
    )
    return new_steps, reason
