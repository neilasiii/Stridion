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
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).parent.parent
HEALTH_CACHE = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
VAULT_ROOT   = PROJECT_ROOT / "vault"

# Hard size caps (characters)
MAX_PACKET_CHARS      = 8_000
MAX_TRAINING_CHARS    = 2_000
MAX_READINESS_CHARS   = 1_200
MAX_PLAN_CHARS        = 2_000
MAX_CONSTRAINTS_CHARS =   600
MAX_DECISIONS_CHARS   =   900   # shared across 3 decisions
MAX_EXCERPTS_CHARS    = 1_200   # shared across up to 5 excerpts


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

    per_decision = MAX_DECISIONS_CHARS // 3
    packet["recent_decisions"] = [_trunc(d, per_decision) for d in packet["recent_decisions"]]

    per_excerpt = MAX_EXCERPTS_CHARS // 5
    packet["vault_excerpts"]   = [_trunc(e, per_excerpt) for e in packet["vault_excerpts"]]

    return packet


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
      active_plan        internal plan days (today → today + days_forward), or None
      constraints        upcoming constraint events from SQLite
      recent_decisions   last 3 coaching decisions from vault
      vault_excerpts     top 3–5 keyword-matched note excerpts

    All fields are truncated to hard size caps before return.
    """
    from .db import DB_PATH as _DEFAULT_DB

    if db_path is None:
        db_path = _DEFAULT_DB

    health = _load_health_cache()
    today  = date.today()

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

    packet = {
        "generated_at":     datetime.utcnow().isoformat(),
        "today":            today.isoformat(),
        "athlete":          athlete,
        "training_summary": _rollup_activities(health, days_back),
        "readiness_trend":  _rollup_readiness(health, min(days_back, 7)),
        "active_plan":      _get_plan_section(days_forward, db_path),
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

    return _enforce_size_caps(packet)


def hash_context_packet(packet: Dict) -> str:
    """
    Return a stable SHA-256 hex digest of the context packet.
    generated_at is excluded so two packets built from identical data match.
    Used by the Brain to skip re-planning when context hasn't changed.
    """
    stable = {k: v for k, v in packet.items() if k != "generated_at"}
    serialized = json.dumps(stable, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()
