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


PROJECT_ROOT   = Path(__file__).parent.parent
HEALTH_CACHE   = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
VAULT_ROOT     = PROJECT_ROOT / "vault"
UPCOMING_RACES = PROJECT_ROOT / "data" / "athlete" / "upcoming_races.md"

# Hard size caps (characters)
MAX_PACKET_CHARS      = 8_000
MAX_TRAINING_CHARS    = 2_000
MAX_READINESS_CHARS   = 1_200
MAX_PLAN_CHARS        = 2_000
MAX_CONSTRAINTS_CHARS =   600
MAX_DECISIONS_CHARS   =   900   # shared across 3 decisions
MAX_EXCERPTS_CHARS    = 1_200   # shared across up to 5 excerpts
MAX_MACRO_CHARS       =   800


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

def _rollup_activities(health: Dict, days_back: int) -> Dict:
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    running_types = {"running", "trail_running", "treadmill_running"}

    activities = [
        a for a in health.get("activities", [])
        if (
            a.get("startTimeLocal", "") >= cutoff
            and a.get("activityType", {}).get("typeKey", "") in running_types
        )
    ]

    if not activities:
        return {"count": 0, "total_miles": 0.0, "period_days": days_back, "recent_runs": []}

    total_mi = sum(a.get("distance", 0) for a in activities) / 1609.34

    # Last 7 runs max (prevents token bloat)
    recent = sorted(activities, key=lambda x: x.get("startTimeLocal", ""))[-7:]
    runs = [
        {
            "date":        a.get("startTimeLocal", "")[:10],
            "distance_mi": round(a.get("distance", 0) / 1609.34, 2),
            "duration_min": round(a.get("duration", 0) / 60, 1),
            "avg_hr":      a.get("averageHR"),
            "type":        a.get("activityType", {}).get("typeKey", "running"),
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


def _enforce_size_caps(packet: Dict) -> Dict:
    packet["training_summary"] = _cap_field(packet["training_summary"], MAX_TRAINING_CHARS)
    packet["readiness_trend"]  = _cap_field(packet["readiness_trend"],  MAX_READINESS_CHARS)
    packet["active_plan"]      = _cap_field(packet["active_plan"],       MAX_PLAN_CHARS)
    packet["constraints"]      = _cap_field(packet["constraints"],       MAX_CONSTRAINTS_CHARS)
    if packet.get("macro_guidance") is not None:
        packet["macro_guidance"] = _cap_field(packet["macro_guidance"],  MAX_MACRO_CHARS)

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
            "target_volume_miles":      current_week.target_volume_miles,
            "long_run_max_min":         current_week.long_run_max_min,
            "intensity_budget":         current_week.intensity_budget,
            "quality_sessions_allowed": current_week.quality_sessions_allowed,
            "key_workout_type":         current_week.key_workout_type,
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

    # Cap the activities list to days_back before any rollup.
    # Avoids iterating full 60-day history when only 14 days are needed.
    # Other health sections (sleep, HRV, etc.) are already date-filtered
    # inside _rollup_readiness so they don't need trimming here.
    if "activities" in health:
        _act_cutoff = (today - timedelta(days=days_back)).isoformat()
        health["activities"] = [
            a for a in health["activities"]
            if a.get("startTimeLocal", "") >= _act_cutoff
        ]

    # Athlete snapshot (lightweight — just key scalars)
    vo2_raw = health.get("vo2_max")
    vdot_approx = None
    if isinstance(vo2_raw, dict):
        vdot_approx = vo2_raw.get("generic", {}).get("vo2MaxPreciseValue")
    rhr_rows = health.get("resting_hr", [])
    rhr_latest = rhr_rows[-1].get("restingHeartRate") if rhr_rows else None

    athlete = {
        "vo2_max":    vdot_approx,
        "rhr_latest": rhr_latest,
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
