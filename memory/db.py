"""
SQLite-backed persistent storage for the running coach Memory OS.

Tables:
  athlete_profile  - key/value athlete context
  events           - immutable event log with idempotency keys
  state            - mutable key/value (last sync, active plan id, etc.)
  metrics          - daily health metric rollups (one row per day, legacy)
  plans            - versioned training plans (never overwritten)
  plan_days        - per-day plan prescriptions
  task_runs        - heartbeat / cron task audit log
  sync_runs        - Garmin sync provenance / freshness log
  daily_metrics    - structured daily health metrics (typed columns + raw JSON)
  activities       - individual workout/activity records from Garmin

All writes are idempotent. Plans are append-only (new plan_id per version).
"""

import json
import hashlib
import uuid
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "coach.sqlite"


# ── Connection ─────────────────────────────────────────────────────────────────

def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS athlete_profile (
    key        TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id           TEXT PRIMARY KEY,
    type         TEXT NOT NULL,
    ts           DATETIME NOT NULL,
    payload_json TEXT NOT NULL,
    source       TEXT NOT NULL DEFAULT 'system',
    hash         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS events_type_ts ON events(type, ts);
CREATE INDEX IF NOT EXISTS events_ts      ON events(ts);

CREATE TABLE IF NOT EXISTS state (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS metrics (
    day          DATE PRIMARY KEY,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id      TEXT PRIMARY KEY,
    start_date   DATE     NOT NULL,
    end_date     DATE     NOT NULL,
    created_at   DATETIME NOT NULL DEFAULT (datetime('now')),
    context_hash TEXT,
    status       TEXT NOT NULL DEFAULT 'draft',
    plan_json    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS plans_status ON plans(status);
CREATE INDEX IF NOT EXISTS plans_dates  ON plans(start_date, end_date);

CREATE TABLE IF NOT EXISTS plan_days (
    plan_id      TEXT NOT NULL,
    day          DATE NOT NULL,
    intent       TEXT,
    workout_json TEXT,
    PRIMARY KEY (plan_id, day),
    FOREIGN KEY (plan_id) REFERENCES plans(plan_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS plan_days_day ON plan_days(day);

CREATE TABLE IF NOT EXISTS task_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task         TEXT    NOT NULL,
    started_at   DATETIME NOT NULL,
    finished_at  DATETIME,
    status       TEXT NOT NULL,
    details_json TEXT
);

CREATE INDEX IF NOT EXISTS task_runs_task ON task_runs(task, started_at);

CREATE TABLE IF NOT EXISTS sync_runs (
    run_id         TEXT PRIMARY KEY,
    started_at     DATETIME NOT NULL DEFAULT (datetime('now')),
    finished_at    DATETIME,
    status         TEXT NOT NULL DEFAULT 'running',
    source         TEXT NOT NULL DEFAULT 'agent',
    days_requested INTEGER,
    days_synced    INTEGER,
    error_summary  TEXT
);

CREATE INDEX IF NOT EXISTS sync_runs_started ON sync_runs(started_at);

CREATE TABLE IF NOT EXISTS daily_metrics (
    day              DATE PRIMARY KEY,
    hrv_rmssd        REAL,
    resting_hr       REAL,
    sleep_score      REAL,
    sleep_duration_h REAL,
    body_battery     REAL,
    training_readiness REAL,
    stress_avg       REAL,
    raw_json         TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS daily_metrics_day ON daily_metrics(day);

CREATE TABLE IF NOT EXISTS activities (
    activity_id  TEXT PRIMARY KEY,
    activity_date DATE NOT NULL,
    activity_type TEXT NOT NULL DEFAULT 'unknown',
    name         TEXT,
    duration_s   REAL,
    distance_m   REAL,
    avg_hr       REAL,
    max_hr       REAL,
    avg_pace_s   REAL,
    calories     REAL,
    raw_json     TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS activities_date ON activities(activity_date);
CREATE INDEX IF NOT EXISTS activities_type ON activities(activity_type, activity_date);

CREATE TABLE IF NOT EXISTS macro_plans (
    macro_id    TEXT PRIMARY KEY,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    mode        TEXT NOT NULL,
    race_date   DATE,
    race_name   TEXT,
    start_week  DATE NOT NULL,
    total_weeks INTEGER NOT NULL,
    vdot        REAL NOT NULL,
    status      TEXT NOT NULL DEFAULT 'draft',
    plan_json   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS macro_plans_status    ON macro_plans(status);
CREATE INDEX IF NOT EXISTS macro_plans_race_date ON macro_plans(race_date);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """Create all tables. Safe to call multiple times (idempotent)."""
    conn = _connect(db_path)
    try:
        conn.executescript(_DDL)
        conn.commit()
    finally:
        conn.close()


# ── Athlete Profile ─────────────────────────────────────────────────────────────

def upsert_athlete_profile(key: str, value: Any, db_path: Path = DB_PATH) -> None:
    """Store or update a named athlete profile value."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO athlete_profile(key, value_json, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET
                 value_json = excluded.value_json,
                 updated_at = excluded.updated_at""",
            (key, json.dumps(value)),
        )
        conn.commit()
    finally:
        conn.close()


def get_athlete_profile(key: str, db_path: Path = DB_PATH) -> Optional[Any]:
    """Retrieve an athlete profile value by key. Returns None if absent."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT value_json FROM athlete_profile WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row["value_json"]) if row else None
    finally:
        conn.close()


# ── Events ──────────────────────────────────────────────────────────────────────

def _make_event_id(event_type: str, payload: Dict, ts: str) -> str:
    """Stable deterministic 32-char hex id for event idempotency."""
    raw = f"{event_type}:{ts}:{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def insert_event(
    event_type: str,
    payload: Dict,
    source: str = "system",
    ts: Optional[datetime] = None,
    stable_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> str:
    """
    Insert an event. Returns the event id.
    Duplicate events are silently ignored.

    stable_id: if provided, used as the idempotency key directly (for
      content-addressable events like constraints where the timestamp is
      arbitrary). If absent, id is derived from type+ts+payload.
    """
    ts_val = ts or datetime.utcnow()
    ts_str = ts_val.isoformat()
    event_id = stable_id or _make_event_id(event_type, payload, ts_str)
    payload_str = json.dumps(payload, sort_keys=True)

    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT OR IGNORE INTO events(id, type, ts, payload_json, source, hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (event_id, event_type, ts_str, payload_str, source, event_id),
        )
        conn.commit()
    finally:
        conn.close()
    return event_id


def query_events(
    event_type: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    source: Optional[str] = None,
    limit: int = 100,
    db_path: Path = DB_PATH,
) -> List[Dict]:
    """Query events with optional filters. Returns list of row dicts."""
    wheres: List[str] = []
    params: List[Any] = []

    if event_type:
        wheres.append("type = ?")
        params.append(event_type)
    if since:
        wheres.append("ts >= ?")
        params.append(since.isoformat())
    if until:
        wheres.append("ts <= ?")
        params.append(until.isoformat())
    if source:
        wheres.append("source = ?")
        params.append(source)

    where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    params.append(limit)

    conn = _connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT * FROM events {where_clause} ORDER BY ts DESC LIMIT ?", params
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_events_by_source(
    source: str,
    since_date: Optional[date] = None,
    event_type: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> int:
    """
    Delete events matching source (and optionally event_type and payload date).

    If since_date is provided, only deletes events where
    json_extract(payload_json, '$.date') >= since_date.isoformat().

    Returns number of rows deleted.
    """
    clauses: List[str] = ["source = ?"]
    params: List[Any] = [source]

    if event_type:
        clauses.append("type = ?")
        params.append(event_type)
    if since_date:
        clauses.append("json_extract(payload_json, '$.date') >= ?")
        params.append(since_date.isoformat())

    sql = f"DELETE FROM events WHERE {' AND '.join(clauses)}"
    conn = _connect(db_path)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ── State ────────────────────────────────────────────────────────────────────────

def set_state(key: str, value: str, db_path: Path = DB_PATH) -> None:
    """Set a mutable state value."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO state(key, value, updated_at) VALUES(?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET
                 value      = excluded.value,
                 updated_at = excluded.updated_at""",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def get_state(
    key: str, default: Optional[str] = None, db_path: Path = DB_PATH
) -> Optional[str]:
    """Get a state value, or default if absent."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


# ── Metrics ──────────────────────────────────────────────────────────────────────

def upsert_metrics(day: date, payload: Dict, db_path: Path = DB_PATH) -> None:
    """Upsert daily health metric rollup for a given calendar date."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO metrics(day, payload_json) VALUES(?, ?)
               ON CONFLICT(day) DO UPDATE SET payload_json = excluded.payload_json""",
            (day.isoformat(), json.dumps(payload)),
        )
        conn.commit()
    finally:
        conn.close()


def get_metrics_range(
    start: date, end: date, db_path: Path = DB_PATH
) -> List[Dict]:
    """Return daily metric rows between start and end (inclusive)."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT day, payload_json FROM metrics WHERE day BETWEEN ? AND ? ORDER BY day",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [{"day": r["day"], **json.loads(r["payload_json"])} for r in rows]
    finally:
        conn.close()


# ── Plans ─────────────────────────────────────────────────────────────────────────

def _new_plan_id(start_date: date, context_hash: Optional[str] = None) -> str:
    """Generate a human-readable, unique plan id."""
    suffix = (context_hash[:8] if context_hash else uuid.uuid4().hex[:8])
    return f"{start_date.strftime('%Y%m%d')}-{suffix}"


def insert_plan(
    start_date: date,
    end_date: date,
    plan_json: Dict,
    context_hash: Optional[str] = None,
    status: str = "draft",
    db_path: Path = DB_PATH,
) -> str:
    """
    Create a new versioned plan. NEVER overwrites existing plans.
    Returns the new plan_id.

    Versioning guarantee: each call produces a distinct plan_id even if
    context_hash collides (uuid4 fallback ensures uniqueness).
    """
    plan_id = _new_plan_id(start_date, context_hash)
    conn = _connect(db_path)
    try:
        # Guarantee uniqueness if id collides (astronomically rare but safe)
        while conn.execute(
            "SELECT 1 FROM plans WHERE plan_id = ?", (plan_id,)
        ).fetchone():
            plan_id = f"{start_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

        conn.execute(
            """INSERT INTO plans(plan_id, start_date, end_date, context_hash, status, plan_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                plan_id,
                start_date.isoformat(),
                end_date.isoformat(),
                context_hash,
                status,
                json.dumps(plan_json),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return plan_id


def insert_plan_days(
    plan_id: str, days: List[Dict], db_path: Path = DB_PATH
) -> None:
    """
    Insert (or replace) day rows for a plan.

    Each dict in days must contain:
      day          - date or ISO string  "YYYY-MM-DD"
      intent       - str  e.g. "Easy 60 min"
      workout_json - dict  structured workout description
    """
    def _day_str(d: Any) -> str:
        return d.isoformat() if isinstance(d, date) else str(d)

    conn = _connect(db_path)
    try:
        conn.executemany(
            """INSERT OR REPLACE INTO plan_days(plan_id, day, intent, workout_json)
               VALUES (?, ?, ?, ?)""",
            [
                (
                    plan_id,
                    _day_str(row["day"]),
                    row.get("intent", ""),
                    json.dumps(row.get("workout_json") or {}),
                )
                for row in days
            ],
        )
        conn.commit()
    finally:
        conn.close()


def set_active_plan(plan_id: str, db_path: Path = DB_PATH) -> None:
    """
    Promote plan_id to 'active'. ATOMIC: all four steps run in one transaction.

      1) Verify plan_id exists — raises ValueError if not.
      2) Capture previous active plan id (for the event payload).
      3) Archive any currently-active plan (status → 'archived').
      4) Set the new plan to status='active'.
      5) Write a 'plan_activated' event (inline, same connection).
      6) Update state['active_plan_id'] for fast lookup.

    Raises:
        ValueError: if plan_id does not exist in the plans table.
    """
    ts = datetime.utcnow().isoformat()
    conn = _connect(db_path)
    try:
        # 1) Guard: plan must exist
        if not conn.execute(
            "SELECT 1 FROM plans WHERE plan_id = ?", (plan_id,)
        ).fetchone():
            raise ValueError(f"set_active_plan: plan_id {plan_id!r} not found")

        # 2) Capture previous active plan (may be None)
        prev = conn.execute(
            "SELECT plan_id FROM plans WHERE status = 'active'"
        ).fetchone()
        previous_plan_id: Optional[str] = prev["plan_id"] if prev else None

        # 3) Archive current active plan(s)
        conn.execute("UPDATE plans SET status = 'archived' WHERE status = 'active'")

        # 4) Activate new plan
        conn.execute(
            "UPDATE plans SET status = 'active' WHERE plan_id = ?", (plan_id,)
        )

        # 5) Write plan_activated event — inline to stay in the same transaction.
        #    Use uuid4 as the event_id so every activation is unconditionally
        #    recorded (no INSERT OR IGNORE silently dropping a duplicate hash).
        event_payload = {
            "plan_id":          plan_id,
            "previous_plan_id": previous_plan_id,
            "activated_at":     ts,
        }
        event_payload_str = json.dumps(event_payload, sort_keys=True)
        event_id = uuid.uuid4().hex  # guaranteed unique — never dropped
        conn.execute(
            """INSERT INTO events(id, type, ts, payload_json, source, hash)
               VALUES (?, 'plan_activated', ?, ?, 'system', ?)""",
            (event_id, ts, event_payload_str, event_id),
        )

        # 6) Fast-lookup state entry
        conn.execute(
            """INSERT INTO state(key, value, updated_at) VALUES('active_plan_id', ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET
                 value      = excluded.value,
                 updated_at = excluded.updated_at""",
            (plan_id,),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_active_plan_id(db_path: Path = DB_PATH) -> Optional[str]:
    """Return the active plan's plan_id from the state table, or None."""
    return get_state("active_plan_id", db_path=db_path)


def get_active_plan_range(db_path: Path = DB_PATH) -> Optional[Tuple[str, str]]:
    """Return (start_date, end_date) ISO strings for the active plan, or None."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT start_date, end_date FROM plans WHERE status = 'active' LIMIT 1"
        ).fetchone()
        return (row["start_date"], row["end_date"]) if row else None
    finally:
        conn.close()


def get_plan_meta(plan_id: str, db_path: Path = DB_PATH) -> Optional[Dict]:
    """Return plan header fields (no plan_json or day rows) for a given plan_id."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT plan_id, start_date, end_date, created_at, status, context_hash "
            "FROM plans WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_active_plan(
    start: Optional[date] = None,
    end: Optional[date] = None,
    db_path: Path = DB_PATH,
) -> Optional[Dict]:
    """
    Return the active plan with its day rows, optionally filtered by date range.
    Returns None if no active plan exists.
    """
    conn = _connect(db_path)
    try:
        plan_row = conn.execute(
            "SELECT * FROM plans WHERE status = 'active' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not plan_row:
            return None

        plan_id = plan_row["plan_id"]
        day_wheres: List[str] = ["plan_id = ?"]
        day_params: List[Any] = [plan_id]

        if start:
            day_wheres.append("day >= ?")
            day_params.append(start.isoformat())
        if end:
            day_wheres.append("day <= ?")
            day_params.append(end.isoformat())

        days = conn.execute(
            f"SELECT * FROM plan_days WHERE {' AND '.join(day_wheres)} ORDER BY day",
            day_params,
        ).fetchall()

        return {
            "plan_id":      plan_row["plan_id"],
            "start_date":   plan_row["start_date"],
            "end_date":     plan_row["end_date"],
            "created_at":   plan_row["created_at"],
            "context_hash": plan_row["context_hash"],
            "status":       plan_row["status"],
            "plan":         json.loads(plan_row["plan_json"]),
            "days": [
                {
                    "day":     d["day"],
                    "intent":  d["intent"],
                    "workout": json.loads(d["workout_json"]) if d["workout_json"] else {},
                }
                for d in days
            ],
        }
    finally:
        conn.close()


def list_plans(
    status: Optional[str] = None,
    limit: int = 20,
    db_path: Path = DB_PATH,
) -> List[Dict]:
    """List plans ordered by creation date descending."""
    conn = _connect(db_path)
    try:
        where = "WHERE status = ?" if status else ""
        params: List[Any] = ([status] if status else []) + [limit]
        rows = conn.execute(
            f"SELECT plan_id, start_date, end_date, created_at, status, context_hash "
            f"FROM plans {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Task Runs ────────────────────────────────────────────────────────────────────

def log_task_start(task: str, db_path: Path = DB_PATH) -> int:
    """Log task start. Returns row id for later finish update."""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO task_runs(task, started_at, status) VALUES(?, datetime('now'), 'running')",
            (task,),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def log_task_finish(
    row_id: int,
    status: str,
    details: Optional[Dict] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Update a task_run row with completion info."""
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE task_runs SET finished_at = datetime('now'), status = ?, details_json = ? WHERE id = ?",
            (status, json.dumps(details) if details else None, row_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_last_task_run(task: str, db_path: Path = DB_PATH) -> Optional[Dict]:
    """Return the most recent task_run record for a given task name."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM task_runs WHERE task = ? ORDER BY started_at DESC LIMIT 1",
            (task,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── Sync Runs ─────────────────────────────────────────────────────────────────

def record_sync_start(
    source: str = "agent",
    days_requested: Optional[int] = None,
    run_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> str:
    """Insert a sync_runs row with status='running'. Returns run_id."""
    rid = run_id or uuid.uuid4().hex
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO sync_runs(run_id, started_at, status, source, days_requested)
               VALUES (?, datetime('now'), 'running', ?, ?)""",
            (rid, source, days_requested),
        )
        conn.commit()
    finally:
        conn.close()
    return rid


def record_sync_finish(
    run_id: str,
    status: str,
    days_synced: Optional[int] = None,
    error_summary: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Update a sync_run row with completion info."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """UPDATE sync_runs
               SET finished_at = datetime('now'),
                   status = ?,
                   days_synced = ?,
                   error_summary = ?
               WHERE run_id = ?""",
            (status, days_synced, error_summary, run_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_last_sync_run(
    status: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> Optional[Dict]:
    """Return the most recent sync_run row, optionally filtered by status."""
    conn = _connect(db_path)
    try:
        if status:
            row = conn.execute(
                "SELECT * FROM sync_runs WHERE status = ? ORDER BY started_at DESC LIMIT 1",
                (status,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── Daily Metrics ──────────────────────────────────────────────────────────────

def upsert_daily_metrics(
    day: date,
    hrv_rmssd: Optional[float] = None,
    resting_hr: Optional[float] = None,
    sleep_score: Optional[float] = None,
    sleep_duration_h: Optional[float] = None,
    body_battery: Optional[float] = None,
    training_readiness: Optional[float] = None,
    stress_avg: Optional[float] = None,
    raw: Optional[Dict] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Insert or update a daily_metrics row for a given date."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO daily_metrics(
                   day, hrv_rmssd, resting_hr, sleep_score, sleep_duration_h,
                   body_battery, training_readiness, stress_avg, raw_json
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(day) DO UPDATE SET
                   hrv_rmssd          = excluded.hrv_rmssd,
                   resting_hr         = excluded.resting_hr,
                   sleep_score        = excluded.sleep_score,
                   sleep_duration_h   = excluded.sleep_duration_h,
                   body_battery       = excluded.body_battery,
                   training_readiness = excluded.training_readiness,
                   stress_avg         = excluded.stress_avg,
                   raw_json           = excluded.raw_json""",
            (
                day.isoformat(),
                hrv_rmssd,
                resting_hr,
                sleep_score,
                sleep_duration_h,
                body_battery,
                training_readiness,
                stress_avg,
                json.dumps(raw or {}),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_daily_metrics(
    start: date,
    end: date,
    db_path: Path = DB_PATH,
) -> List[Dict]:
    """Return daily_metrics rows between start and end (inclusive), ordered by date."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM daily_metrics WHERE day BETWEEN ? AND ? ORDER BY day",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Activities ────────────────────────────────────────────────────────────────

def upsert_activity(
    activity_id: str,
    activity_date: date,
    activity_type: str = "unknown",
    name: Optional[str] = None,
    duration_s: Optional[float] = None,
    distance_m: Optional[float] = None,
    avg_hr: Optional[float] = None,
    max_hr: Optional[float] = None,
    avg_pace_s: Optional[float] = None,
    calories: Optional[float] = None,
    raw: Optional[Dict] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Insert or update an activity row keyed by activity_id."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO activities(
                   activity_id, activity_date, activity_type, name,
                   duration_s, distance_m, avg_hr, max_hr, avg_pace_s,
                   calories, raw_json
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(activity_id) DO UPDATE SET
                   activity_date = excluded.activity_date,
                   activity_type = excluded.activity_type,
                   name          = excluded.name,
                   duration_s    = excluded.duration_s,
                   distance_m    = excluded.distance_m,
                   avg_hr        = excluded.avg_hr,
                   max_hr        = excluded.max_hr,
                   avg_pace_s    = excluded.avg_pace_s,
                   calories      = excluded.calories,
                   raw_json      = excluded.raw_json""",
            (
                activity_id,
                activity_date.isoformat(),
                activity_type,
                name,
                duration_s,
                distance_m,
                avg_hr,
                max_hr,
                avg_pace_s,
                calories,
                json.dumps(raw or {}),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_activities(
    start: date,
    end: date,
    activity_type: Optional[str] = None,
    limit: int = 200,
    db_path: Path = DB_PATH,
) -> List[Dict]:
    """Return activities between start and end (inclusive), optionally filtered by type."""
    wheres = ["activity_date BETWEEN ? AND ?"]
    params: List[Any] = [start.isoformat(), end.isoformat()]
    if activity_type:
        wheres.append("activity_type = ?")
        params.append(activity_type)
    params.append(limit)
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT * FROM activities WHERE {' AND '.join(wheres)} "
            f"ORDER BY activity_date DESC LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Macro Plans ────────────────────────────────────────────────────────────────

def _new_macro_id(mode: str, race_date_or_none: Optional[str], vdot: float) -> str:
    """Generate a human-readable, unique macro plan id.

    Examples:
      base_block  → "base-v38-a1b2c3d4"
      race_targeted with 2026-06-01 → "20260601-v38-a1b2c3d4"
    """
    suffix = uuid.uuid4().hex[:8]
    vdot_int = int(round(float(vdot)))
    if mode == "base_block" or not race_date_or_none:
        return f"base-v{vdot_int}-{suffix}"
    # Strip dashes from race date prefix (YYYYMMDD)
    date_prefix = race_date_or_none.replace("-", "")[:8]
    return f"{date_prefix}-v{vdot_int}-{suffix}"


def insert_macro_plan(
    mode: str,
    race_date: Optional[str],
    race_name: Optional[str],
    start_week: str,
    total_weeks: int,
    vdot: float,
    plan_json: Dict,
    status: str = "draft",
    db_path: Path = DB_PATH,
) -> str:
    """Insert a new macro plan row. Returns the macro_id."""
    macro_id = _new_macro_id(mode, race_date, vdot)
    conn = _connect(db_path)
    try:
        # Guarantee uniqueness on collision (astronomically rare)
        while conn.execute(
            "SELECT 1 FROM macro_plans WHERE macro_id = ?", (macro_id,)
        ).fetchone():
            macro_id = _new_macro_id(mode, race_date, vdot)

        conn.execute(
            """INSERT INTO macro_plans(macro_id, mode, race_date, race_name,
                   start_week, total_weeks, vdot, status, plan_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                macro_id,
                mode,
                race_date,
                race_name,
                start_week,
                total_weeks,
                vdot,
                status,
                json.dumps(plan_json),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return macro_id


def set_active_macro_plan(macro_id: str, db_path: Path = DB_PATH) -> None:
    """
    Promote macro_id to 'active'. ATOMIC: all steps run in one transaction.

      1) Verify macro_id exists — raises ValueError if not.
      2) Capture previous active macro_id (for event payload).
      3) Archive any currently-active macro plan (status → 'archived').
      4) Set the new plan to status='active'.
      5) Write a 'macro_plan_activated' event (inline, same connection).
      6) Update state['active_macro_plan_id'] for fast lookup.

    Only call this AFTER validate_macro_plan() passes.

    Raises:
        ValueError: if macro_id does not exist in macro_plans table.
    """
    ts = datetime.utcnow().isoformat()
    conn = _connect(db_path)
    try:
        # 1) Guard: macro plan must exist
        if not conn.execute(
            "SELECT 1 FROM macro_plans WHERE macro_id = ?", (macro_id,)
        ).fetchone():
            raise ValueError(f"set_active_macro_plan: macro_id {macro_id!r} not found")

        # 2) Capture previous active macro plan (may be None)
        prev = conn.execute(
            "SELECT macro_id FROM macro_plans WHERE status = 'active'"
        ).fetchone()
        previous_macro_id: Optional[str] = prev["macro_id"] if prev else None

        # 3) Archive current active macro plan(s)
        conn.execute(
            "UPDATE macro_plans SET status = 'archived' WHERE status = 'active'"
        )

        # 4) Activate new macro plan
        conn.execute(
            "UPDATE macro_plans SET status = 'active' WHERE macro_id = ?", (macro_id,)
        )

        # 5) Write macro_plan_activated event (inline, same transaction)
        event_payload = {
            "macro_id":          macro_id,
            "previous_macro_id": previous_macro_id,
            "activated_at":      ts,
        }
        event_payload_str = json.dumps(event_payload, sort_keys=True)
        event_id = uuid.uuid4().hex  # guaranteed unique
        conn.execute(
            """INSERT INTO events(id, type, ts, payload_json, source, hash)
               VALUES (?, 'macro_plan_activated', ?, ?, 'system', ?)""",
            (event_id, ts, event_payload_str, event_id),
        )

        # 6) Fast-lookup state entry
        conn.execute(
            """INSERT INTO state(key, value, updated_at)
               VALUES('active_macro_plan_id', ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET
                 value      = excluded.value,
                 updated_at = excluded.updated_at""",
            (macro_id,),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_active_macro_plan(db_path: Path = DB_PATH) -> Optional[Dict]:
    """
    Return the active macro plan as a dict, or None if no active plan exists.

    Shape: {macro_id, mode, race_date, race_name, start_week, total_weeks,
            vdot, status, plan: <dict>}
    """
    active_id = get_active_macro_plan_id(db_path=db_path)
    if not active_id:
        return None

    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM macro_plans WHERE macro_id = ?", (active_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "macro_id":    row["macro_id"],
            "mode":        row["mode"],
            "race_date":   row["race_date"],
            "race_name":   row["race_name"],
            "start_week":  row["start_week"],
            "total_weeks": row["total_weeks"],
            "vdot":        row["vdot"],
            "status":      row["status"],
            "plan":        json.loads(row["plan_json"]),
        }
    finally:
        conn.close()


def get_active_macro_plan_id(db_path: Path = DB_PATH) -> Optional[str]:
    """Return the active macro plan's macro_id from the state table, or None."""
    return get_state("active_macro_plan_id", db_path=db_path)
