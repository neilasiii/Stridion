"""
Context Packet builder — assembles structured, size-capped context for the Brain.

The context packet is the ONLY input the Brain (LLM planner) reads.
It must be:
  - Deterministic given the same underlying data
  - Hashable for cache invalidation
  - Capped in size so it fits comfortably in a prompt

Authority model:
  - Active plan from SQLite is PRIMARY source of workout prescriptions.
  - FinalSurge/ICS data (health_data_cache.json["scheduled_workouts"]) is
    treated as an OPTIONAL supplemental input, not authoritative.
  - If no internal plan exists, active_plan is None and the Brain must generate one.

Size caps (characters):
  MAX_PACKET_CHARS       = 8 000   (total serialised packet)
  MAX_TRAINING_CHARS     = 2 000   (activities rollup)
  MAX_READINESS_CHARS    = 1 200   (readiness trend)
  MAX_PLAN_CHARS         = 2 000   (active plan days)
  MAX_CONSTRAINTS_CHARS  =   600   (constraint events)
  MAX_DECISIONS_CHARS    =   900   (3 × 300 each)
  MAX_EXCERPTS_CHARS     = 1 200   (5 × 240 each)
"""

import hashlib
import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


PROJECT_ROOT          = Path(__file__).parent.parent
HEALTH_CACHE          = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
VAULT_ROOT            = PROJECT_ROOT / "vault"
UPCOMING_RACES        = PROJECT_ROOT / "data" / "athlete" / "upcoming_races.md"
_ATHLETE_PATTERNS_PATH = PROJECT_ROOT / "data" / "athlete" / "learned_patterns.md"

# Hard size caps (characters)
MAX_PACKET_CHARS      = 8_000
MAX_TRAINING_CHARS    = 2_000
MAX_READINESS_CHARS   = 1_200
MAX_PLAN_CHARS        = 2_000
MAX_CONSTRAINTS_CHARS =   600
MAX_DECISIONS_CHARS   =   900   # shared across 3 decisions
MAX_EXCERPTS_CHARS    = 1_200   # shared across up to 5 excerpts
MAX_MACRO_CHARS       =   800
MAX_RPE_CHARS         =   600   # RPE history (last 4 weeks)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_health_cache() -> Dict:
    if not HEALTH_CACHE.exists():
        return {}
    with HEALTH_CACHE.open(encoding="utf-8") as f:
        return json.load(f)


def _trunc(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f" …[+{len(text) - max_chars} chars]"


def _safe_avg(lst: List) -> Optional[float]:
    clean = [v for v in lst if v is not None]
    return round(sum(clean) / len(clean), 1) if clean else None


# ── Training Summary (last N days of running activities) ─────────────────────

# The health cache may be in either of two formats:
#   "new"  (garmin_sync.py simplified): date, activity_type (UPPER), distance_miles, duration_seconds, avg_heart_rate
#   "old"  (raw Garmin API):            startTimeLocal, activityType.typeKey (lower), distance (m), duration (s), averageHR
# All helpers below handle both transparently.

def _act_date_str(a: Dict) -> str:
    """Return the activity's ISO date string regardless of schema."""
    return a.get("date") or a.get("startTimeLocal") or ""

def _act_type_key(a: Dict) -> str:
    """Return the activity type key, lowercase, regardless of schema."""
    # new schema: activity_type = "RUNNING"
    flat = a.get("activity_type")
    if flat:
        return flat.lower()
    # old schema: activityType.typeKey = "running"
    return a.get("activityType", {}).get("typeKey", "")

def _act_miles(a: Dict) -> float:
    """Return distance in miles regardless of schema."""
    dm = a.get("distance_miles")
    if dm is not None:
        return float(dm)
    return a.get("distance", 0) / 1609.34

def _act_dur_min(a: Dict) -> float:
    """Return duration in minutes regardless of schema."""
    ds = a.get("duration_seconds")
    if ds is not None:
        return float(ds) / 60
    return a.get("duration", 0) / 60

def _act_avg_hr(a: Dict) -> Optional[float]:
    """Return average HR regardless of schema."""
    hr = a.get("avg_heart_rate") or a.get("averageHR")
    return float(hr) if hr is not None else None


def _rollup_activities(health: Dict, days_back: int) -> Dict:
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    running_types = {"running", "trail_running", "treadmill_running"}

    activities = [
        a for a in health.get("activities", [])
        if (
            _act_date_str(a) >= cutoff
            and _act_type_key(a) in running_types
        )
    ]

    if not activities:
        return {"count": 0, "total_miles": 0.0, "period_days": days_back, "recent_runs": []}

    total_mi = sum(_act_miles(a) for a in activities)

    # Last 7 runs max (prevents token bloat)
    recent = sorted(activities, key=_act_date_str)[-7:]
    runs = [
        {
            "date":         _act_date_str(a)[:10],
            "distance_mi":  round(_act_miles(a), 2),
            "duration_min": round(_act_dur_min(a), 1),
            "avg_hr":       _act_avg_hr(a),
            "type":         _act_type_key(a),
        }
        for a in recent
    ]

    return {
        "count":       len(activities),
        "total_miles": round(total_mi, 1),
        "period_days": days_back,
        "recent_runs": runs,
    }


# ── Readiness Trend (last 7 days of recovery metrics) ────────────────────────

def _rollup_readiness_from_sqlite(days_back: int, db_path) -> Optional[Dict]:
    """
    Build the readiness trend dict from the daily_metrics SQLite table.

    Returns None if the table is empty or unavailable (caller falls back to JSON).
    When rows are present, returns the same shape as _rollup_readiness() with
    an extra source="sqlite" field for auditability.
    """
    from .db import get_daily_metrics

    today = date.today()
    start = today - timedelta(days=days_back)

    try:
        rows = get_daily_metrics(start, today, db_path=db_path)
    except Exception as exc:
        log.warning("readiness source=json_fallback reason=sqlite_error(%s)", type(exc).__name__)
        return None

    if not rows:
        log.warning("readiness source=json_fallback reason=sqlite_empty")
        return None

    hrv_vals  = [r["hrv_rmssd"]          for r in rows if r.get("hrv_rmssd")          is not None]
    sleep_h   = [r["sleep_duration_h"]   for r in rows if r.get("sleep_duration_h")   is not None]
    sleep_sc  = [r["sleep_score"]        for r in rows if r.get("sleep_score")        is not None]
    bb_max    = [r["body_battery"]       for r in rows if r.get("body_battery")       is not None]
    tr_scores = [r["training_readiness"] for r in rows if r.get("training_readiness") is not None]
    rhr_vals  = [r["resting_hr"]         for r in rows if r.get("resting_hr")         is not None]

    # Most-recent row = "today" snapshot (rows ordered ASC by day)
    latest = rows[-1]
    log.info(
        "readiness source=sqlite days_back=%d latest_date=%s",
        days_back, latest.get("day", "?"),
    )

    return {
        "period_days": days_back,
        "source": "sqlite",
        "today": {
            "sleep_hours":        latest.get("sleep_duration_h"),
            "sleep_score":        latest.get("sleep_score"),
            "hrv":                latest.get("hrv_rmssd"),
            "body_battery_max":   latest.get("body_battery"),
            "training_readiness": latest.get("training_readiness"),
            "rhr":                latest.get("resting_hr"),
        },
        "trend": {
            "avg_sleep_hours":        _safe_avg(sleep_h),
            "avg_sleep_score":        _safe_avg(sleep_sc),
            "avg_hrv":                _safe_avg(hrv_vals),
            "avg_body_battery_max":   _safe_avg(bb_max),
            "avg_training_readiness": _safe_avg(tr_scores),
            "avg_rhr":                _safe_avg(rhr_vals),
        },
    }


def _rollup_readiness(health: Dict, days_back: int = 7) -> Dict:
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()

    def _date_key(row: Dict, *keys: str) -> str:
        for k in keys:
            if k in row:
                return str(row[k])[:10]
        return ""

    # HRV
    hrv_rows = [
        h for h in health.get("hrv", [])
        if _date_key(h, "startTimestampLocal", "calendarDate") >= cutoff
    ]
    hrv_vals = [
        h.get("lastNight5MinHigh") or h.get("weeklyAvg")
        for h in hrv_rows
    ]
    hrv_vals = [v for v in hrv_vals if v is not None]

    # Sleep
    sleep_rows = [
        s for s in health.get("sleep", [])
        if _date_key(s, "calendarDate", "sleepStartTimestampLocal") >= cutoff
    ]
    sleep_hours = [s.get("sleepTimeSeconds", 0) / 3600 for s in sleep_rows]
    sleep_scores = [
        s.get("overallScore", {}).get("value") if isinstance(s.get("overallScore"), dict)
        else s.get("sleepScoreValue")
        for s in sleep_rows
    ]

    # Body Battery
    bb_rows = [
        b for b in health.get("body_battery", [])
        if _date_key(b, "date", "calendarDate") >= cutoff
    ]
    bb_max = [b.get("charged") for b in bb_rows if b.get("charged")]

    # Training Readiness
    tr_rows = [
        r for r in health.get("training_readiness", [])
        if _date_key(r, "calendarDate") >= cutoff
    ]
    tr_scores = [r.get("score") for r in tr_rows if r.get("score") is not None]

    # RHR
    rhr_rows = [
        r for r in health.get("resting_hr", [])
        if _date_key(r, "calendarDate", "startTimestampLocal") >= cutoff
    ]
    rhr_vals = [r.get("restingHeartRate") for r in rhr_rows if r.get("restingHeartRate")]

    # Today snapshots (most recent available)
    today_sleep = sleep_rows[-1] if sleep_rows else {}
    today_sleep_score = (
        today_sleep.get("overallScore", {}).get("value")
        if isinstance(today_sleep.get("overallScore"), dict)
        else today_sleep.get("sleepScoreValue")
    )

    return {
        "period_days": days_back,
        "today": {
            "sleep_hours":        round(today_sleep.get("sleepTimeSeconds", 0) / 3600, 1) if today_sleep else None,
            "sleep_score":        today_sleep_score,
            "hrv":                hrv_vals[-1] if hrv_vals else None,
            "body_battery_max":   bb_max[-1] if bb_max else None,
            "training_readiness": tr_scores[-1] if tr_scores else None,
            "rhr":                rhr_vals[-1] if rhr_vals else None,
        },
        "trend": {
            "avg_sleep_hours":        _safe_avg(sleep_hours),
            "avg_sleep_score":        _safe_avg(sleep_scores),
            "avg_hrv":                _safe_avg(hrv_vals),
            "avg_body_battery_max":   _safe_avg(bb_max),
            "avg_training_readiness": _safe_avg(tr_scores),
            "avg_rhr":                _safe_avg(rhr_vals),
        },
    }


# ── Constraints ───────────────────────────────────────────────────────────────

def _get_constraints(days_forward: int, db_path) -> List[Dict]:
    """Pull future constraint events from SQLite."""
    from .db import query_events

    today = date.today()
    until = today + timedelta(days=days_forward)

    events = query_events(
        event_type="constraint",
        since=datetime.combine(today, datetime.min.time()),
        until=datetime.combine(until, datetime.max.time()),
        db_path=db_path,
    )

    constraints = []
    for e in events:
        try:
            payload = json.loads(e["payload_json"])
            constraints.append({
                "date":   payload.get("date"),
                "reason": payload.get("raw_text", "")[:120],
                "source": e["source"],
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return constraints


# ── Active Plan ───────────────────────────────────────────────────────────────

def _get_plan_section(days_forward: int, db_path) -> Optional[Dict]:
    """Return the active internal plan days for the forward window."""
    from .db import get_active_plan

    today = date.today()
    end = today + timedelta(days=days_forward)
    return get_active_plan(start=today, end=end, db_path=db_path)


def _get_plan_authority(db_path) -> Dict:
    """
    Build the plan_authority block — always fully populated, never absent.

    Rules:
      - source is always 'internal' (FinalSurge is not authoritative).
      - finalsurge_authoritative is always False.
      - If no active plan exists, id/range/created_at are None but keys are present.
    """
    from .db import get_active_plan_id, get_active_plan_range, get_plan_meta

    active_id    = get_active_plan_id(db_path=db_path)
    active_range = get_active_plan_range(db_path=db_path)

    last_created = None
    if active_id:
        meta = get_plan_meta(active_id, db_path=db_path)
        if meta:
            last_created = meta.get("created_at")

    return {
        "source":               "internal",
        "active_plan_id":       active_id,
        "active_plan_range":    list(active_range) if active_range else None,
        "last_plan_created_at": last_created,
        "finalsurge_authoritative": False,
    }


# ── Vault Excerpts ─────────────────────────────────────────────────────────────

_DEFAULT_KEYWORDS = [
    "tired", "sore", "sick", "injury", "pain", "skip", "missed",
    "race", "goal", "travel", "work", "busy", "family", "constraint",
    "rest", "fatigue", "recovery", "poor sleep",
]


def _keyword_score(text: str, keywords: List[str]) -> int:
    lower = text.lower()
    return sum(1 for kw in keywords if kw in lower)


def _search_vault_excerpts(
    days_back: int,
    keywords: Optional[List[str]] = None,
    max_results: int = 5,
) -> List[str]:
    """
    Keyword-score vault notes and return top N relevant short excerpts.
    Searches: vault/daily/ (last days_back), vault/coach/.
    Each excerpt is capped at 240 chars.
    """
    kws = keywords or _DEFAULT_KEYWORDS
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    candidates: List[tuple] = []

    def _extract_best_para(text: str, max_para_chars: int = 240) -> str:
        paras = [
            p.strip() for p in text.split("\n\n")
            if p.strip() and not p.strip().startswith("#")
        ]
        if not paras:
            return text[:max_para_chars]
        return max(paras, key=lambda p: _keyword_score(p, kws))[:max_para_chars]

    daily_dir = VAULT_ROOT / "daily"
    if daily_dir.exists():
        for note in sorted(daily_dir.glob("*.md"), reverse=True):
            # Filename is YYYY-MM-DD.md — compare as string is safe
            if note.stem < cutoff:
                continue
            try:
                text = note.read_text(encoding="utf-8")
                score = _keyword_score(text, kws)
                if score > 0:
                    excerpt = _extract_best_para(text)
                    candidates.append((score, f"[{note.stem}] {excerpt}"))
            except OSError:
                continue

    coach_dir = VAULT_ROOT / "coach"
    if coach_dir.exists():
        for note in coach_dir.glob("*.md"):
            try:
                text = note.read_text(encoding="utf-8")
                score = _keyword_score(text, kws)
                if score > 0:
                    excerpt = _extract_best_para(text)
                    candidates.append((score, f"[{note.name}] {excerpt}"))
            except OSError:
                continue

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [excerpt for _, excerpt in candidates[:max_results]]


# ── Data Quality ──────────────────────────────────────────────────────────────

def _build_data_quality(health: Dict, enforced_packet: Dict) -> Dict:
    """
    Derive a data_quality block from the health cache and the already-enforced packet.

    Fields:
      has_health_cache        - health_data_cache.json existed and parsed OK
      has_activities          - at least one activity present
      has_readiness           - training_readiness rows present
      readiness_confidence    - "low|medium|high" based on field presence + recency
      constraints_confidence  - "low|medium|high" based on constraint count
      packet_size_chars       - len(json.dumps(enforced_packet)) for prompt budgeting

    packet_size_chars reflects the coaching-content size (excludes data_quality
    overhead) so it's useful for prompt token estimates.
    """
    has_cache      = bool(health)
    has_activities = bool(health.get("activities"))

    tr_rows = health.get("training_readiness", [])
    has_readiness = bool(tr_rows)

    if not tr_rows or not has_cache:
        readiness_confidence = "low"
    else:
        cutoff = (date.today() - timedelta(days=2)).isoformat()
        recent = [r for r in tr_rows if r.get("calendarDate", "") >= cutoff]
        readiness_confidence = "high" if recent else "medium"

    constraints = enforced_packet.get("constraints", [])
    if isinstance(constraints, list) and len(constraints) > 0:
        constraints_confidence = "high"
    elif isinstance(constraints, dict) and constraints.get("_truncated"):
        constraints_confidence = "medium"   # truncated → data present but capped
    else:
        constraints_confidence = "low"      # empty list or missing

    return {
        "has_health_cache":       has_cache,
        "has_activities":         has_activities,
        "has_readiness":          has_readiness,
        "readiness_confidence":   readiness_confidence,
        "constraints_confidence": constraints_confidence,
        "packet_size_chars":      len(json.dumps(enforced_packet, default=str)),
    }


# ── Size Enforcement ──────────────────────────────────────────────────────────

def _cap_field(obj: Any, max_chars: int) -> Any:
    """
    If obj serialises to more than max_chars, replace with a truncation marker.
    Small objects pass through unchanged (preserves type for the Brain).
    """
    s = json.dumps(obj, default=str)
    if len(s) <= max_chars:
        return obj
    preview = s[:max_chars]
    return {"_truncated": True, "preview": preview, "full_chars": len(s)}


def _build_rpe_history(db_path, weeks: int = 4) -> Optional[Dict]:
    """
    Summarise the last `weeks` weeks of RPE checkin data for the Brain.

    Returns None if no sessions with RPE data exist.
    Returns a compact dict with:
      weeks          list of {week_start, sessions: [{date, type, rpe, notes}]}
      flags          list of signal strings the planner should act on
      session_count  total sessions with RPE data
    """
    try:
        from .db import get_weekly_rpe_summary
    except Exception:
        return None

    today = date.today()
    all_sessions = []
    weekly_data = []

    for w in range(weeks):
        # Walk backwards week by week
        week_end   = today - timedelta(days=w * 7)
        week_start = week_end - timedelta(days=6)
        rows = get_weekly_rpe_summary(week_start, db_path=db_path)
        # Include sessions that have ANY RPE data (coach or watch)
        sessions_with_rpe = [
            r for r in rows
            if r.get("rpe") is not None or r.get("rpe_watch") is not None
        ]
        if sessions_with_rpe:
            weekly_data.append({
                "week_start": week_start.isoformat(),
                "sessions": [
                    {
                        "date":       r["activity_date"],
                        "type":       r["activity_type"],
                        "rpe":        r.get("rpe"),        # coach-reported (Discord)
                        "rpe_watch":  r.get("rpe_watch"),  # watch self-evaluation
                        "feel":       r.get("workout_feel"),  # 0=bad,50=ok,75=good,100=excellent
                        "notes":      (r.get("effort_notes") or "")[:60],
                    }
                    for r in sessions_with_rpe
                ],
            })
            all_sessions.extend(sessions_with_rpe)

    if not all_sessions:
        return None

    # Derive actionable flags from coach RPE
    flags = []
    easy_rpes    = [r["rpe"] for r in all_sessions if r.get("rpe") and r.get("activity_type") == "running"
                    and "easy" in (r.get("activity_name") or "").lower()]
    quality_rpes = [r["rpe"] for r in all_sessions if r.get("rpe") and r.get("activity_type") == "running"
                    and any(k in (r.get("activity_name") or "").lower()
                            for k in ("tempo", "interval", "quality", "threshold"))]
    all_rpes     = [r["rpe"] for r in all_sessions if r.get("rpe")]

    if easy_rpes and (sum(easy_rpes) / len(easy_rpes)) > 7.0:
        flags.append("easy_rpe_elevated")
    if quality_rpes and (sum(quality_rpes) / len(quality_rpes)) < 5.0:
        flags.append("quality_rpe_low")
    if all_rpes and (sum(all_rpes) / len(all_rpes)) >= 8.0:
        flags.append("high_overall_effort")

    # Watch vs coach divergence: athlete may underreport effort to coach
    # Flag if abs(rpe_watch - rpe) >= 2 in 2+ sessions
    divergent = [
        r for r in all_sessions
        if r.get("rpe") is not None and r.get("rpe_watch") is not None
        and abs(r["rpe_watch"] - r["rpe"]) >= 2.0
    ]
    if len(divergent) >= 2:
        avg_watch  = sum(r["rpe_watch"] for r in divergent) / len(divergent)
        avg_coach  = sum(r["rpe"]       for r in divergent) / len(divergent)
        if avg_watch > avg_coach:
            flags.append("watch_harder_than_reported")  # watch says harder than told coach
        else:
            flags.append("watch_easier_than_reported")  # watch says easier than told coach

    return {
        "session_count": len(all_sessions),
        "flags":         flags,
        "weeks":         weekly_data[:weeks],  # newest first
    }


def _enforce_size_caps(packet: Dict) -> Dict:
    packet["training_summary"] = _cap_field(packet["training_summary"], MAX_TRAINING_CHARS)
    packet["readiness_trend"]  = _cap_field(packet["readiness_trend"],  MAX_READINESS_CHARS)
    packet["active_plan"]      = _cap_field(packet["active_plan"],       MAX_PLAN_CHARS)
    packet["constraints"]      = _cap_field(packet["constraints"],       MAX_CONSTRAINTS_CHARS)
    if packet.get("macro_guidance") is not None:
        packet["macro_guidance"] = _cap_field(packet["macro_guidance"],  MAX_MACRO_CHARS)
    if packet.get("rpe_history") is not None:
        packet["rpe_history"]  = _cap_field(packet["rpe_history"],       MAX_RPE_CHARS)

    per_decision = MAX_DECISIONS_CHARS // 3
    packet["recent_decisions"] = [_trunc(d, per_decision) for d in packet["recent_decisions"]]

    per_excerpt = MAX_EXCERPTS_CHARS // 5
    packet["vault_excerpts"]   = [_trunc(e, per_excerpt) for e in packet["vault_excerpts"]]

    return packet


# ── Macro Plan Guidance ────────────────────────────────────────────────────────

def _get_macro_guidance(target_date: str, db_path) -> Optional[Dict]:
    """
    Load the active macro plan and return guidance for the week containing target_date.

    target_date should be the upcoming Sunday being planned (ISO YYYY-MM-DD).
    Returns None if no active macro plan exists or if target_date is outside the block.

    Uses lazy import of MacroPlan to avoid circular imports at module load time.

    Observability: logs at INFO level with source=sqlite and macro_id.
    """
    from .db import get_active_macro_plan

    row = get_active_macro_plan(db_path=db_path)
    if not row:
        return None

    try:
        # Lazy import to avoid circular import (brain → memory → brain)
        from brain.schemas import MacroPlan
        plan = MacroPlan.model_validate(row["plan"])
    except Exception as exc:
        log.warning("_get_macro_guidance: failed to validate macro plan: %s", exc)
        return None

    current_week = plan.get_week_for_date(target_date)
    if current_week is None:
        log.info(
            "macro_guidance: target_date=%s is outside macro block "
            "(start=%s total_weeks=%d)",
            target_date, plan.start_week, plan.total_weeks,
        )
        return None

    weeks_remaining = plan.total_weeks - current_week.week_number + 1

    log.info(
        "macro_guidance source=sqlite macro_id=%s mode=%s week=%d/%d",
        row["macro_id"], row["mode"], current_week.week_number, plan.total_weeks,
    )

    return {
        "macro_id":       row["macro_id"],
        "mode":           row["mode"],
        "race_date":      row.get("race_date"),
        "race_name":      row.get("race_name"),
        "total_weeks":    plan.total_weeks,
        "weeks_remaining": weeks_remaining,
        "current_week": {
            "week_number":              current_week.week_number,
            "week_start":               current_week.week_start,
            "phase":                    current_week.phase,
            "volume_floor_miles":       current_week.volume_floor_miles,
            "volume_target_miles":      current_week.volume_target_miles,
            "volume_ceiling_miles":     current_week.volume_ceiling_miles,
            "long_run_max_min":         current_week.long_run_max_min,
            "intensity_budget":         current_week.intensity_budget,
            "quality_sessions_allowed": current_week.quality_sessions_allowed,
            "key_workout_type":         current_week.key_workout_type,
            "recommended_session_types": list(current_week.recommended_session_types),
            "paces": {
                "easy":     current_week.paces.easy,
                "tempo":    current_week.paces.tempo,
                "interval": current_week.paces.interval,
                "long_run": current_week.paces.long_run,
            },
            "planner_notes":   current_week.planner_notes,
            "phase_rationale": current_week.phase_rationale,
        },
    }


# ── Race loader ───────────────────────────────────────────────────────────────

def _load_upcoming_races() -> list:
    """Parse upcoming_races.md and return races on or after today."""
    if not UPCOMING_RACES.exists():
        return []
    try:
        content = UPCOMING_RACES.read_text()
        today_iso = date.today().isoformat()
        races = []
        # Split on level-3 headers (### Race Name)
        for section in re.split(r"^###\s+", content, flags=re.MULTILINE)[1:]:
            lines = section.strip().splitlines()
            name = lines[0].strip()
            date_m = re.search(r"\*\*Date:\*\*\s+([A-Za-z]+ \d+,\s*\d{4}|\d{4}-\d{2}-\d{2})", section)
            dist_m = re.search(r"\*\*Distance:\*\*\s+(.+)", section)
            prio_m = re.search(r"\*\*Race Priority:\*\*\s+(.+)", section)
            if not date_m:
                continue
            raw = date_m.group(1).strip()
            try:
                race_date = (
                    raw if "-" in raw
                    else datetime.strptime(raw, "%B %d, %Y").date().isoformat()
                )
            except ValueError:
                continue
            if race_date < today_iso:
                continue
            races.append({
                "name":     name,
                "date":     race_date,
                "distance": dist_m.group(1).strip() if dist_m else None,
                "priority": prio_m.group(1).split("(")[0].strip() if prio_m else None,
            })
        return races
    except Exception as exc:
        log.warning("_load_upcoming_races failed: %s", exc)
        return []


def _load_athlete_patterns() -> Optional[str]:
    """
    Load learned athlete patterns from data/athlete/learned_patterns.md.
    Returns the file content as a string, or None if the file doesn't exist yet.
    Run `coach analyze-patterns` to generate this file.
    """
    if _ATHLETE_PATTERNS_PATH.exists():
        try:
            return _ATHLETE_PATTERNS_PATH.read_text()
        except Exception:
            pass
    return None


# ── Race-derived VDOT ─────────────────────────────────────────────────────────

# Standard race distances: (center_miles, tolerance_miles).
# An activity whose distance falls within tolerance MAY be classified as a race.
# Short-race bands (5k/10k/15k) require BOTH a distance match AND a keyword match
# because easy training runs of 3–6 miles are common and would otherwise pollute
# VDOT with slow-paced non-race efforts.
# Long-race bands (half/marathon) accept distance match alone — it is very unusual
# to do a 13–26 mile training run without it being race-level effort.
_RACE_DISTANCE_BANDS: tuple = (
    (3.107, 0.20),   # 5k   — keyword required (see _is_race_distance_long_only)
    (6.214, 0.30),   # 10k  — keyword required
    (9.321, 0.40),   # 15k  — keyword required
    (13.109, 0.60),  # Half marathon  (covers 12.5–13.7 mi) — distance match OK
    (26.219, 1.00),  # Marathon       (covers 25.2–27.2 mi) — distance match OK
)
_RACE_DISTANCE_BANDS_LONG_ONLY: tuple = _RACE_DISTANCE_BANDS[3:]  # half + marathon only

# Activity name keywords that indicate a race (case-insensitive).
# Checked against activity_name / name / title fields.
_RACE_KEYWORDS_VDOT: frozenset = frozenset([
    "race", "5k", "10k", "5 km", "10 km",
    "half marathon", "half-marathon", "marathon", "hm",
])


def _is_race_distance(dist_mi: float) -> bool:
    """
    Return True if dist_mi qualifies as a race by distance alone.

    Only half-marathon and marathon distances qualify on distance alone.
    Shorter races (5k/10k/15k) require a keyword match because training runs
    of similar length are common and would contaminate VDOT with easy-pace data.
    """
    return any(
        abs(dist_mi - center) <= tol
        for center, tol in _RACE_DISTANCE_BANDS_LONG_ONLY
    )


def _has_race_keyword_activity(a: Dict) -> bool:
    """Return True if any name field of the activity contains a race keyword."""
    name = (
        a.get("activity_name") or a.get("name") or a.get("title") or ""
    ).lower()
    return any(kw in name for kw in _RACE_KEYWORDS_VDOT)


def _derive_vdot_from_activities(health: Dict, lookback_days: int = 90) -> Optional[float]:
    """
    Derive VDOT from recent *race* running activities only.

    An activity qualifies as a race if:
      - Its distance is within tolerance of a standard race distance (5k, 10k,
        15k, half marathon, marathon), OR
      - Its name/title contains a race keyword ("race", "5k", "marathon", etc.)

    HR thresholds are intentionally NOT used — they would include hard tempo and
    interval training sessions, which are not races.

    From qualifying candidates, returns the VDOT of the most recent one.
    Returns None when no qualifying race is found (caller falls back to Garmin
    VO2max estimate or 38.0 default).
    """
    try:
        from src.vdot_calculator import calculate_vdot as _calc_vdot
    except ImportError:
        log.warning("vdot_calculator not importable — skipping race VDOT derivation")
        return None

    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    running_types = {"running", "trail_running", "treadmill_running"}

    candidates: List[tuple] = []  # (date_str, vdot)
    for a in health.get("activities", []):
        date_str = _act_date_str(a)
        if date_str < cutoff:
            continue
        if _act_type_key(a) not in running_types:
            continue

        dist_mi = _act_miles(a)
        dur_min = _act_dur_min(a)

        if dist_mi <= 0 or dur_min <= 0:
            continue

        # Time trial detection — treat as race-equivalent for VDOT
        name_lower = (
            a.get("activity_name") or a.get("name") or a.get("title") or ""
        ).lower()
        _TIME_TRIAL_KEYWORDS = ["time trial", " tt ", "timed mile", "test effort", "race effort"]
        is_time_trial = any(kw in name_lower for kw in _TIME_TRIAL_KEYWORDS)

        if not (_is_race_distance(dist_mi) or _has_race_keyword_activity(a) or is_time_trial):
            continue

        try:
            vdot = _calc_vdot(dist_mi * 1609.34, dur_min * 60)
            candidates.append((date_str, round(vdot, 1)))
        except Exception:
            continue

    if not candidates:
        log.debug("race VDOT: no qualifying race activities in last %d days", lookback_days)
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_date, best_vdot = candidates[0]
    log.info(
        "race VDOT derived: %.1f from race activity on %s",
        best_vdot, best_date[:10],
    )
    return best_vdot


# ── Public API ────────────────────────────────────────────────────────────────

def build_context_packet(
    days_back: int = 14,
    days_forward: int = 14,
    keywords: Optional[List[str]] = None,
    db_path=None,
) -> Dict:
    """
    Assemble the full context packet for the Brain (LLM planner).

    Returns a dict containing:
      generated_at       ISO timestamp
      today              YYYY-MM-DD
      athlete            snapshot of key athlete metrics from health cache
      training_summary   rolling activities rollup (last days_back)
      readiness_trend    recovery metrics (last 7 days)
      plan_authority     authority declaration (always present; see below)
      active_plan        internal plan days (today → today + days_forward), or None
      constraints        upcoming constraint events from SQLite
      recent_decisions   last 3 coaching decisions from vault
      vault_excerpts     top 3–5 keyword-matched note excerpts

    plan_authority shape (always fully populated):
      {
        "source":               "internal",
        "active_plan_id":       str | null,
        "active_plan_range":    [start_iso, end_iso] | null,
        "last_plan_created_at": iso_str | null,
        "finalsurge_authoritative": false   ← always false
      }

    All fields are truncated to hard size caps before return.
    """
    from .db import DB_PATH as _DEFAULT_DB

    if db_path is None:
        db_path = _DEFAULT_DB

    health = _load_health_cache()
    today  = date.today()

    # Derive race-based VDOT from the FULL activity list (90-day window) BEFORE
    # truncating to days_back.  Garmin's physiological VO2max estimate inflates
    # fitness by ~25–35%; race-derived VDOT from actual performance is authoritative.
    vdot_race_derived = _derive_vdot_from_activities(health, lookback_days=90)

    # Cap the activities list to days_back before any rollup.
    # Avoids iterating full 60-day history when only 14 days are needed.
    # Other health sections (sleep, HRV, etc.) are already date-filtered
    # inside _rollup_readiness so they don't need trimming here.
    if "activities" in health:
        _act_cutoff = (today - timedelta(days=days_back)).isoformat()
        health["activities"] = [
            a for a in health["activities"]
            if _act_date_str(a) >= _act_cutoff
        ]

    # Athlete snapshot (lightweight — just key scalars)
    # VO2 max — handle two schemas:
    #   new (simplified): vo2_max_readings = [{date, vo2_max}, ...]  (float value)
    #   old (raw Garmin): vo2_max = {generic: {vo2MaxPreciseValue: float}}
    vdot_approx = None
    vo2_raw = health.get("vo2_max")
    if isinstance(vo2_raw, dict):
        vdot_approx = vo2_raw.get("generic", {}).get("vo2MaxPreciseValue")
    if vdot_approx is None:
        readings = health.get("vo2_max_readings", [])
        if readings:
            # readings may be newest-first or oldest-first depending on source;
            # always pick the entry with the latest date to get the current VDOT.
            latest = max(readings, key=lambda r: r.get("date", ""))
            vdot_approx = latest.get("vo2_max")
    rhr_rows = health.get("resting_hr", [])
    rhr_latest = rhr_rows[-1].get("restingHeartRate") if rhr_rows else None

    athlete = {
        "vo2_max":          vdot_approx,       # Garmin physiological VO2max estimate
        "vdot_race_derived": vdot_race_derived, # Race-performance VDOT (preferred for planning)
        "rhr_latest":       rhr_latest,
        "weekly_structure": {
            "runs_per_week":        4,
            "min_runs_per_week":    3,
            "preferred_runs_per_week": 4,
            "max_runs_per_week":    5,
            "anchor_days":          ["wednesday", "thursday", "saturday"],
            "non_negotiable_blocked_days": [],
            "quality_sessions":     1,
            "long_runs":            1,
            "easy_runs":            2,
            "quality_must_progress": True,
            "note": (
                "4 runs/week is the consistent observed pattern. "
                "Days are flexible around constraint calendar. "
                "Quality must be harder than prior week — never regress."
            ),
        },
    }

    # Readiness trend: prefer SQLite (populated by post-sync ingest); fall back
    # to JSON cache if the daily_metrics table is empty or unavailable.
    readiness_days = min(days_back, 7)
    readiness_trend = _rollup_readiness_from_sqlite(readiness_days, db_path)
    if readiness_trend is None:
        readiness_trend = _rollup_readiness(health, readiness_days)

    # Upcoming Sunday — target date for macro guidance (week being planned)
    days_until_sunday = (6 - today.weekday()) % 7
    upcoming_sunday = (today + timedelta(days=days_until_sunday)).isoformat()

    # Macro guidance (silently None if no active macro plan or outside block)
    macro_guidance = None
    try:
        macro_guidance = _get_macro_guidance(upcoming_sunday, db_path)
    except Exception as exc:
        log.warning("_get_macro_guidance failed: %s", exc)

    packet = {
        "generated_at":     datetime.utcnow().isoformat(),
        "today":            today.isoformat(),
        "athlete":          athlete,
        "upcoming_races":   _load_upcoming_races(),
        "training_summary": _rollup_activities(health, days_back),
        "readiness_trend":  readiness_trend,
        "plan_authority":   _get_plan_authority(db_path),
        "active_plan":      _get_plan_section(days_forward, db_path),
        "macro_guidance":   macro_guidance,
        "constraints":      _get_constraints(days_forward, db_path),
        "rpe_history":      _build_rpe_history(db_path),
        "athlete_patterns": _load_athlete_patterns(),
        "recent_decisions": [],
        "vault_excerpts":   [],
    }

    # Vault reads (graceful if vault doesn't exist yet)
    try:
        from .vault import get_recent_decisions
        packet["recent_decisions"] = get_recent_decisions(limit=3)
    except Exception:
        pass

    try:
        packet["vault_excerpts"] = _search_vault_excerpts(days_back, keywords)
    except Exception:
        pass

    enforced = _enforce_size_caps(packet)
    # data_quality is added AFTER enforcement so packet_size_chars reflects
    # coaching-content size only (excludes data_quality overhead itself).
    enforced["data_quality"] = _build_data_quality(health, enforced)
    return enforced


def hash_context_packet(packet: Dict) -> str:
    """
    Return a stable SHA-256 hex digest of the context packet.

    Excluded from hash:
      - generated_at        (changes every call, not semantic)
      - data_quality.packet_size_chars  (derived/meta — changes when packet grows)

    data_quality fields like readiness_confidence ARE included so that a
    shift from "low" to "high" invalidates the cache and forces re-planning.
    """
    stable = {k: v for k, v in packet.items() if k != "generated_at"}
    if "data_quality" in stable and isinstance(stable["data_quality"], dict):
        dq = {k: v for k, v in stable["data_quality"].items() if k != "packet_size_chars"}
        stable = {**stable, "data_quality": dq}
    serialized = json.dumps(stable, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()
