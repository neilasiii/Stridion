"""
Obsidian-compatible Markdown vault for the running coach Memory OS.

Directory layout (all under ./vault/):
  daily/YYYY-MM-DD.md   - daily brief + free-form notes
  coach/DECISIONS.md    - append-only coaching decisions log
  coach/PLANS.md        - training plan snapshots / links
  inbox/*.md            - user-authored notes parsed for constraints

Rules:
  - write_daily_note  : overwrites (idempotent for same date)
  - append_decision   : always appends (never overwrites existing entries)
  - ingest_inbox_notes: moves processed files to inbox/processed/
  - All files are human-editable; the system never deletes vault content.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).parent.parent
VAULT_ROOT    = PROJECT_ROOT / "vault"
DAILY_DIR     = VAULT_ROOT / "daily"
COACH_DIR     = VAULT_ROOT / "coach"
INBOX_DIR     = VAULT_ROOT / "inbox"

DECISIONS_FILE = COACH_DIR / "DECISIONS.md"
PLANS_FILE     = COACH_DIR / "PLANS.md"


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def _ensure_vault() -> None:
    """Create vault directory structure and stub files if absent."""
    for d in (DAILY_DIR, COACH_DIR, INBOX_DIR, INBOX_DIR / "processed"):
        d.mkdir(parents=True, exist_ok=True)

    if not DECISIONS_FILE.exists():
        DECISIONS_FILE.write_text(
            "# Coaching Decisions Log\n\n"
            "> Append-only. Newest entries at the bottom.\n\n"
        )
    if not PLANS_FILE.exists():
        PLANS_FILE.write_text(
            "# Training Plans\n\n"
            "> Each plan block links to a plan_id in data/coach.sqlite.\n\n"
        )


# ── Daily Notes ───────────────────────────────────────────────────────────────

def write_daily_note(note_date: date, content: str) -> Path:
    """
    Write (or overwrite) the daily note for note_date.
    Content is written verbatim after a date header.
    Returns the path to the written file.
    """
    _ensure_vault()
    path = DAILY_DIR / f"{note_date.isoformat()}.md"
    header = (
        f"# Daily Brief: {note_date.strftime('%A, %B %d, %Y')}\n\n"
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*\n\n"
    )
    path.write_text(header + content, encoding="utf-8")
    return path


# ── Decisions Log ─────────────────────────────────────────────────────────────

def append_decision(
    decision: Dict[str, Any],
    rationale: str,
) -> None:
    """
    Append a structured coaching decision to DECISIONS.md.

    decision dict should include at minimum:
      type    - e.g. "plan_adjustment", "intensity_reduction"
      date    - ISO date string the decision applies to
      summary - one-line human description
    """
    _ensure_vault()
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    decision_type = decision.get("type", "decision")
    summary = decision.get("summary", "")

    block = (
        f"\n## [{ts}] {decision_type}"
        + (f" — {summary}" if summary else "")
        + f"\n\n"
        f"**Rationale:** {rationale}\n\n"
        f"```json\n{json.dumps(decision, indent=2, sort_keys=True, default=str)}\n```\n"
    )
    with DECISIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(block)


# ── Plan Snapshots ────────────────────────────────────────────────────────────

def write_plan_snapshot(
    plan_id: str,
    summary: str,
    plan_data: Any,
) -> Path:
    """
    Append a human-readable plan snapshot to PLANS.md.
    plan_data can be a dict (serialised as JSON) or a string (used verbatim).
    Returns the path to PLANS.md.
    """
    _ensure_vault()
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if isinstance(plan_data, dict):
        data_block = f"```json\n{json.dumps(plan_data, indent=2, default=str)}\n```"
    else:
        data_block = str(plan_data)

    block = (
        f"\n## [{ts}] `{plan_id}`\n\n"
        f"{summary}\n\n"
        f"<details><summary>Full plan</summary>\n\n{data_block}\n\n</details>\n"
    )
    with PLANS_FILE.open("a", encoding="utf-8") as f:
        f.write(block)
    return PLANS_FILE


# ── Decisions Reader ──────────────────────────────────────────────────────────

def get_recent_decisions(limit: int = 3) -> List[str]:
    """
    Return the last `limit` decision entries from DECISIONS.md as
    plain-text excerpts (newest-first, each capped at 500 chars).
    """
    _ensure_vault()
    if not DECISIONS_FILE.exists():
        return []

    text = DECISIONS_FILE.read_text(encoding="utf-8")
    # Split on level-2 headers produced by append_decision
    blocks = re.split(r"\n## ", text)
    # Drop the preamble (everything before the first ##)
    decision_blocks = [b.strip() for b in blocks[1:] if b.strip()]
    recent = decision_blocks[-limit:] if len(decision_blocks) >= limit else decision_blocks
    return [b[:500] for b in reversed(recent)]  # newest first


# ── Inbox Ingestion ───────────────────────────────────────────────────────────

# Date patterns: ISO, US numeric, month-name
_DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,?\s*\d{4})?)\b",
    re.IGNORECASE,
)

_CONSTRAINT_KEYWORDS = [
    "no workout", "no run", "rest day", "unavailable", "busy",
    "travel", "off day", "skip", "childcare", "spouse works",
    "shift", "night shift", "on call", "blocked", "can't run",
    "cannot run", "not available",
]


def _parse_date_str(text: str) -> Optional[date]:
    text = text.strip().rstrip(".")
    for fmt in (
        "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m/%d",
        "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y",
        "%B %d", "%b %d",
    ):
        try:
            d = datetime.strptime(text, fmt)
            if fmt in ("%m/%d", "%B %d", "%b %d"):
                d = d.replace(year=datetime.now().year)
            return d.date()
        except ValueError:
            continue
    return None


def _is_constraint_line(line: str) -> bool:
    lower = line.lower()
    return any(kw in lower for kw in _CONSTRAINT_KEYWORDS)


def _make_constraint_stable_id(constraint_date: Optional[str], raw_text: str) -> str:
    """
    Content-addressable id for a constraint event.
    Keyed on (date, raw_text) only — excludes source and timestamp so that
    re-ingesting identical content from a different filename is still idempotent.
    """
    import hashlib
    raw = f"constraint:{constraint_date}:{raw_text.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _parse_constraints_from_text(text: str, source: str) -> List[Dict]:
    """
    Extract zero or more constraint event payloads from free-form markdown text.
    Each returned dict has: type, payload, source, ts, stable_id.
    stable_id ensures re-ingesting the same file produces the same event ids.
    """
    events: List[Dict] = []
    now = datetime.utcnow()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not _is_constraint_line(line):
            continue

        date_matches = _DATE_RE.findall(line)
        found_any = False
        for dm in date_matches:
            parsed = _parse_date_str(dm)
            if parsed:
                date_str = parsed.isoformat()
                events.append({
                    "type":      "constraint",
                    "payload":   {"date": date_str, "raw_text": line, "source": source},
                    "source":    source,
                    "ts":        now,
                    "stable_id": _make_constraint_stable_id(date_str, line),
                })
                found_any = True

        if not found_any:
            # Keyword present but no parseable date — capture for manual review
            events.append({
                "type":      "constraint",
                "payload":   {"date": None, "raw_text": line, "source": source, "note": "date_unparseable"},
                "source":    source,
                "ts":        now,
                "stable_id": _make_constraint_stable_id(None, line),
            })

    return events


def ingest_inbox_notes(db_path=None) -> List[Dict]:
    """
    Parse all *.md files in vault/inbox/ for constraint keywords.
    Inserts parsed events into SQLite via insert_event().
    Moves processed files to vault/inbox/processed/.

    Skips README.md and any file whose name starts with '_' or '.'.

    Returns list of inserted event dicts (including their generated ids).
    """
    from .db import insert_event, DB_PATH as _DB_PATH

    if db_path is None:
        db_path = _DB_PATH

    _ensure_vault()
    processed_dir = INBOX_DIR / "processed"
    processed_dir.mkdir(exist_ok=True)

    all_inserted: List[Dict] = []

    for note_path in sorted(INBOX_DIR.glob("*.md")):
        # Skip meta / documentation files
        if note_path.name.upper() in ("README.MD",) or note_path.name.startswith(("_", ".")):
            continue
        text = note_path.read_text(encoding="utf-8")
        raw_events = _parse_constraints_from_text(
            text, source=f"inbox:{note_path.name}"
        )
        for ev in raw_events:
            event_id = insert_event(
                event_type=ev["type"],
                payload=ev["payload"],
                source=ev["source"],
                ts=ev["ts"],
                stable_id=ev.get("stable_id"),
                db_path=db_path,
            )
            all_inserted.append({**ev, "id": event_id})

        # Move to processed/ so we don't re-ingest
        dest = processed_dir / note_path.name
        # If dest exists, suffix with timestamp
        if dest.exists():
            ts_suffix = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            dest = processed_dir / f"{note_path.stem}_{ts_suffix}{note_path.suffix}"
        note_path.rename(dest)

    return all_inserted
