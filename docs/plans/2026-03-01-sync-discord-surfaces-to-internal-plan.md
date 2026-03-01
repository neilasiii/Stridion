# Sync Discord Surfaces to Internal Coach Plan — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the morning report, `/workout` command, and daily workout formatter all read from the internal SQLite plan instead of the FinalSurge health cache; morning report explicitly shows original plan vs recommended adjustment.

**Architecture:** Each surface gets a try-internal-plan-first / fall-back-to-health-cache pattern. A shared `_session_to_workout()` helper converts SQLite session dicts to the workout format each surface already understands. No new modules created.

**Tech Stack:** Python 3, SQLite via `skills/plans.py`, pytest with `unittest.mock`.

---

### Task 1: `morning_report.py` — try internal plan for today's and upcoming workouts

**Files:**
- Modify: `src/morning_report.py` — `get_todays_workout()`, `get_upcoming_workouts()`, add `_session_to_workout()`
- Create: `tests/test_morning_report_sources.py`

**Context:** `get_todays_workout(cache)` currently scans `cache["scheduled_workouts"]`. Replace it to call `skills.plans.get_active_sessions()` first. Same pattern for `get_upcoming_workouts()`.

**Step 1: Write the failing tests**

Create `tests/test_morning_report_sources.py`:

```python
"""Tests: morning_report reads internal plan before health cache."""
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _make_session(d: str, wtype: str = "easy", dur: int = 45, intent: str = "Easy effort", steps=None):
    return {
        "date": d,
        "workout_type": wtype,
        "duration_min": dur,
        "intent": intent,
        "structure_steps": steps or [],
        "safety_flags": [],
        "plan_id": "test-plan",
    }


class TestSessionToWorkout:
    """_session_to_workout converts SQLite session → workout dict."""

    def _convert(self, session):
        from morning_report import _session_to_workout
        return _session_to_workout(session)

    def test_sets_source_to_internal_plan(self):
        w = self._convert(_make_session("2026-03-01"))
        assert w["source"] == "internal_plan"

    def test_easy_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="easy"))
        assert w["name"] == "Easy Run"

    def test_tempo_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="tempo"))
        assert w["name"] == "Tempo Run"

    def test_long_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="long"))
        assert w["name"] == "Long Run"

    def test_interval_label(self):
        w = self._convert(_make_session("2026-03-01", wtype="interval"))
        assert w["name"] == "Interval Run"

    def test_intent_in_description(self):
        w = self._convert(_make_session("2026-03-01", intent="Keep it easy, conversational"))
        assert "Keep it easy, conversational" in w["description"]

    def test_duration_min_preserved(self):
        w = self._convert(_make_session("2026-03-01", dur=60))
        assert w["duration_min"] == 60

    def test_steps_in_description(self):
        steps = [
            {"label": "warmup", "duration_min": 10, "reps": None, "target_value": "easy"},
            {"label": "main", "duration_min": 25, "reps": None, "target_value": "tempo"},
            {"label": "cooldown", "duration_min": 10, "reps": None, "target_value": "easy"},
        ]
        w = self._convert(_make_session("2026-03-01", steps=steps))
        assert "Warmup" in w["description"]
        assert "10min" in w["description"]
        assert "Main" in w["description"]
        assert "25min" in w["description"]

    def test_no_steps_no_structure_section(self):
        w = self._convert(_make_session("2026-03-01", steps=[]))
        assert "Structure:" not in w["description"]


class TestGetTodaysWorkout:
    """get_todays_workout prefers internal plan over health cache."""

    def _call(self, sessions, cache_workouts, today_str=None):
        from morning_report import get_todays_workout
        cache = {"scheduled_workouts": cache_workouts}
        today = today_str or date.today().isoformat()
        with patch("morning_report.get_active_sessions", return_value=sessions):
            with patch("morning_report.date") as mock_date:
                mock_date.today.return_value = date.fromisoformat(today)
                # date.isoformat() still needs to work
                return get_todays_workout(cache)

    def test_returns_internal_plan_when_available(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="tempo", dur=55)]
        result = self._call(sessions, [])
        assert result is not None
        assert result[0]["source"] == "internal_plan"
        assert result[0]["name"] == "Tempo Run"

    def test_falls_back_to_cache_when_no_plan(self):
        today = date.today().isoformat()
        cache_workouts = [{
            "scheduled_date": today,
            "name": "Easy 30min",
            "description": "Easy run",
            "source": "ics_calendar",
        }]
        result = self._call([], cache_workouts)
        assert result is not None
        assert result[0]["source"] != "internal_plan"

    def test_rest_day_returns_none(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="rest", dur=0)]
        result = self._call(sessions, [])
        assert result is None

    def test_wrong_date_session_ignored(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        sessions = [_make_session(yesterday, wtype="easy")]
        result = self._call(sessions, [])
        assert result is None


class TestGetUpcomingWorkouts:
    """get_upcoming_workouts prefers internal plan over health cache."""

    def _call(self, sessions, cache_workouts, days=3):
        from morning_report import get_upcoming_workouts
        cache = {"scheduled_workouts": cache_workouts}
        with patch("morning_report.get_active_sessions", return_value=sessions):
            return get_upcoming_workouts(cache, days=days)

    def test_returns_internal_plan_sessions(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = [_make_session(tomorrow, wtype="long", dur=90, intent="Long easy run")]
        result = self._call(sessions, [])
        assert len(result) == 1
        assert result[0]["source"] == "internal_plan"
        assert result[0]["name"] == "Long Run"

    def test_excludes_today_and_past(self):
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        sessions = [_make_session(today), _make_session(yesterday)]
        result = self._call(sessions, [])
        assert result == []

    def test_excludes_beyond_window(self):
        far = (date.today() + timedelta(days=10)).isoformat()
        sessions = [_make_session(far)]
        result = self._call(sessions, [], days=5)
        assert result == []

    def test_rest_days_excluded(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = [_make_session(tomorrow, wtype="rest")]
        result = self._call(sessions, [])
        assert result == []

    def test_falls_back_to_cache_when_no_plan(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        cache_workouts = [{"scheduled_date": tomorrow, "name": "Easy run", "description": "", "domain": "running"}]
        result = self._call([], cache_workouts)
        assert len(result) == 1
```

**Step 2: Run tests to confirm they fail**

```bash
cd /home/coach/running-coach
python -m pytest tests/test_morning_report_sources.py -v 2>&1 | head -40
```

Expected: failures on import (`_session_to_workout not found`, `get_active_sessions not found in morning_report`).

**Step 3: Implement `_session_to_workout` in `morning_report.py`**

Add after the existing imports, before `load_health_data()`:

```python
# ── Internal plan helpers ──────────────────────────────────────────────────────

_WORKOUT_TYPE_LABELS = {
    "easy": "Easy Run",
    "long": "Long Run",
    "tempo": "Tempo Run",
    "interval": "Interval Run",
    "rest": "Rest Day",
}


def _session_to_workout(session):
    """Convert an internal plan session dict to a morning_report workout dict."""
    wtype = session.get("workout_type", "rest")
    label = _WORKOUT_TYPE_LABELS.get(wtype, wtype.title())
    intent = session.get("intent", "")
    steps = session.get("structure_steps", [])

    # Build description: intent + optional structure block
    description = intent
    if steps:
        step_lines = []
        for i, s in enumerate(steps, 1):
            rep_str = f" ×{s['reps']}" if s.get("reps") else ""
            target = f"  [{s.get('target_value', '')}]" if s.get("target_value") else ""
            step_lines.append(
                f"{i}. {s.get('label', '').title()} {s.get('duration_min', 0)}min{rep_str}{target}"
            )
        structure = "\n".join(step_lines)
        description = f"{intent}\n\nStructure:\n{structure}" if intent else f"Structure:\n{structure}"

    return {
        "name": label,
        "description": description,
        "duration_min": session.get("duration_min", 0),
        "source": "internal_plan",
        "domain": "running",
        "workout_type": wtype,
        "structure_steps": steps,
        "intent": intent,
    }


def _get_active_sessions_safe():
    """Import and call skills.plans.get_active_sessions(), returning [] on any error."""
    try:
        from skills.plans import get_active_sessions
        return get_active_sessions()
    except Exception:
        return []
```

Also add at the top of the file:
```python
from datetime import date as _date
```
(needed for date comparisons without conflicting with the existing `datetime` import)

**Step 4: Rewrite `get_todays_workout(cache)`**

Replace the existing function body (lines 89–112):

```python
def get_todays_workout(cache):
    """Get today's workout — internal plan first, health cache fallback."""
    today_str = datetime.now().date().isoformat()

    # Internal plan (authoritative)
    sessions = _get_active_sessions_safe()
    today_session = next((s for s in sessions if s["date"] == today_str), None)
    if today_session is not None and today_session.get("workout_type") != "rest":
        return [_session_to_workout(today_session)]

    # Health cache fallback (FinalSurge / ICS)
    workouts = []
    for workout in cache.get('scheduled_workouts', []):
        workout_date = workout.get('scheduled_date') or workout.get('date', '')
        if workout_date.startswith(today_str):
            workouts.append({
                'name': workout.get('workout_name') or workout.get('name', 'Workout'),
                'description': workout.get('description', ''),
                'source': workout.get('source', 'unknown'),
                'domain': workout.get('domain', 'unknown'),
            })

    seen = set()
    unique_workouts = []
    for w in workouts:
        if w['name'] not in seen:
            seen.add(w['name'])
            unique_workouts.append(w)

    return unique_workouts if unique_workouts else None
```

**Step 5: Rewrite `get_upcoming_workouts(cache, days=5)`**

Replace the existing function body (lines 115–152):

```python
def get_upcoming_workouts(cache, days=5):
    """Get upcoming workouts — internal plan first, health cache fallback."""
    today = datetime.now().date()

    # Internal plan (authoritative)
    sessions = _get_active_sessions_safe()
    if sessions:
        upcoming = []
        for s in sessions:
            try:
                session_date = datetime.fromisoformat(s["date"]).date()
            except (ValueError, KeyError):
                continue
            days_ahead = (session_date - today).days
            if 1 <= days_ahead <= days and s.get("workout_type") != "rest":
                wo = _session_to_workout(s)
                upcoming.append({
                    "date": s["date"],
                    "days_ahead": days_ahead,
                    "name": wo["name"],
                    "description": wo["description"],
                    "domain": "running",
                    "source": "internal_plan",
                })
        upcoming.sort(key=lambda x: x["date"])
        return upcoming

    # Health cache fallback
    upcoming = []
    for workout in cache.get('scheduled_workouts', []):
        workout_date_str = workout.get('scheduled_date') or workout.get('date', '')
        if not workout_date_str:
            continue
        try:
            workout_date = datetime.fromisoformat(workout_date_str.split('T')[0]).date()
        except (ValueError, KeyError):
            continue
        days_ahead = (workout_date - today).days
        if 1 <= days_ahead <= days:
            upcoming.append({
                'date': workout_date_str[:10],
                'days_ahead': days_ahead,
                'name': workout.get('workout_name') or workout.get('name', 'Workout'),
                'description': workout.get('description', ''),
                'domain': workout.get('domain', 'unknown'),
            })

    upcoming.sort(key=lambda x: x['date'])
    seen = set()
    unique_upcoming = []
    for w in upcoming:
        key = (w['date'], w['name'])
        if key not in seen:
            seen.add(key)
            unique_upcoming.append(w)
    return unique_upcoming
```

**Step 6: Run tests to confirm they pass**

```bash
python -m pytest tests/test_morning_report_sources.py -v
```

Expected: all green. Fix any failures before continuing.

**Step 7: Run existing morning report tests to confirm no regression**

```bash
python -m pytest tests/test_morning_report_cmd.py -v
```

Expected: all green.

**Step 8: Commit**

```bash
git add src/morning_report.py tests/test_morning_report_sources.py
git commit -m "feat(morning-report): read today's/upcoming workouts from internal plan first"
```

---

### Task 2: `morning_report.py` — ORIGINAL_PLAN section + ADJUSTMENT output

**Files:**
- Modify: `src/morning_report.py` — `build_ai_prompt()`, `parse_ai_response()`
- Modify: `tests/test_morning_report_sources.py` — add tests for parse_ai_response

**Context:** The AI prompt needs an `ORIGINAL PLAN` block so Claude sees exactly what was planned. The output format adds an `ADJUSTMENT:` section between NOTIFICATION and FULL_REPORT. `parse_ai_response()` extracts it and prepends it to the full report when a modification was made.

**Step 1: Write tests for parse_ai_response**

Add to `tests/test_morning_report_sources.py`:

```python
class TestParseAiResponse:
    """parse_ai_response extracts notification, adjustment, and full report."""

    def _parse(self, text):
        from morning_report import parse_ai_response
        return parse_ai_response(text)

    def test_extracts_notification(self):
        text = "NOTIFICATION:\n45min E as planned. Recovery excellent.\nADJUSTMENT:\nAs planned\nFULL_REPORT:\n## Recovery\nAll good."
        notif, report = self._parse(text)
        assert "45min E as planned" in notif

    def test_as_planned_not_prepended_to_report(self):
        text = "NOTIFICATION:\nAs planned.\nADJUSTMENT:\nAs planned\nFULL_REPORT:\n## Recovery\nGood numbers."
        _, report = self._parse(text)
        assert "## Adjustment" not in report
        assert "As planned" not in report.split("## Recovery")[0]

    def test_modification_prepended_to_full_report(self):
        text = (
            "NOTIFICATION:\n45min E → 30min E (HRV low).\n"
            "ADJUSTMENT:\nOriginal: Easy 45min\nRecommended: Easy 30min\nReason: HRV well below norm.\n"
            "FULL_REPORT:\n## Recovery\nHRV tanked."
        )
        _, report = self._parse(text)
        assert report.startswith("## Adjustment")
        assert "Original: Easy 45min" in report
        assert "## Recovery" in report

    def test_missing_adjustment_section_still_parses(self):
        """Backwards compat: AI skips ADJUSTMENT — report still parses."""
        text = "NOTIFICATION:\nAs planned.\nFULL_REPORT:\n## Recovery\nAll good."
        notif, report = self._parse(text)
        assert "As planned" in notif
        assert "## Recovery" in report
```

**Step 2: Run tests to confirm failures**

```bash
python -m pytest tests/test_morning_report_sources.py::TestParseAiResponse -v
```

Expected: FAIL (parse_ai_response doesn't yet handle ADJUSTMENT).

**Step 3: Update `build_ai_prompt()` in `morning_report.py`**

In `build_ai_prompt()`, after the `workout_text` block (around line 467), add:

```python
# Format ORIGINAL PLAN block (only for internal plan sessions)
original_plan_text = "Not available (health cache source)"
if workout and isinstance(workout, list) and workout[0].get("source") == "internal_plan":
    w = workout[0]
    wtype = w.get("workout_type", "unknown")
    dur = w.get("duration_min", 0)
    intent = w.get("intent", "")
    steps = w.get("structure_steps", [])
    original_plan_text = f"Type: {wtype}  Duration: {dur}min\nIntent: {intent}"
    if steps:
        slines = []
        for s in steps:
            rep_str = f" ×{s.get('reps')}" if s.get("reps") else ""
            tv = f"  [{s.get('target_value','')}]" if s.get("target_value") else ""
            slines.append(f"  - {s.get('label','').title()} {s.get('duration_min',0)}min{rep_str}{tv}")
        original_plan_text += "\nSteps:\n" + "\n".join(slines)
```

Then in the `prompt = f"""..."""` string, add a new section after RECOVERY METRICS and before TODAY'S WORKOUT:

```
ORIGINAL PLAN (from internal coach system — what was prescribed):
{original_plan_text}
```

And update the OUTPUT FORMAT section to add ADJUSTMENT between NOTIFICATION and FULL_REPORT:

```
OUTPUT FORMAT - You MUST follow this EXACTLY:

NOTIFICATION:
[Single line, max 200 chars. Format: "Original → Recommendation (key reason). Recovery metric"]

ADJUSTMENT:
[If recommending the workout as-is, write exactly: "As planned"]
[If recommending a modification, write exactly:
  Original: <what was planned, e.g. "Easy 45min">
  Recommended: <what to do instead, e.g. "Easy 30min, skip strides">
  Reason: <one sentence — the single metric or combination driving this>]

FULL_REPORT:
[Detailed markdown report...]
```

**Step 4: Update `parse_ai_response()` in `morning_report.py`**

Replace the existing function:

```python
def parse_ai_response(response):
    """Parse AI response into notification and full report (with adjustment prepended if modified)."""
    notification = ""
    adjustment = ""
    full_report = ""

    # Try to extract all three sections
    if 'ADJUSTMENT:' in response:
        # Split on ADJUSTMENT first
        before_adj, rest_adj = response.split('ADJUSTMENT:', 1)
        # Extract notification from before ADJUSTMENT
        if 'NOTIFICATION:' in before_adj:
            notification = before_adj.split('NOTIFICATION:', 1)[1].strip()
        else:
            notification = before_adj.strip()
        # Extract adjustment and full report
        if 'FULL_REPORT:' in rest_adj:
            adjustment = rest_adj.split('FULL_REPORT:', 1)[0].strip()
            full_report = rest_adj.split('FULL_REPORT:', 1)[1].strip()
        else:
            adjustment = rest_adj.strip()
    elif 'NOTIFICATION:' in response:
        # No ADJUSTMENT section — original parse logic
        parts = response.split('NOTIFICATION:', 1)
        if len(parts) > 1:
            rest = parts[1]
            if 'FULL_REPORT:' in rest:
                notification = rest.split('FULL_REPORT:', 1)[0].strip()
                full_report = rest.split('FULL_REPORT:', 1)[1].strip()
            else:
                lines = rest.strip().split('\n')
                notification = lines[0].strip() if lines else ""
                full_report = '\n'.join(lines[1:]).strip()
    else:
        lines = response.strip().split('\n')
        notification = lines[0][:200] if lines else "Check full report"
        full_report = response

    # Prepend adjustment block to full report when a modification was recommended
    if adjustment and adjustment.lower().strip() != "as planned":
        full_report = f"## Adjustment\n{adjustment}\n\n---\n\n{full_report}"

    # Clean up notification
    notification = notification.strip('"\'').strip()
    if len(notification) > 240:
        notification = notification[:237] + "..."

    return notification, full_report
```

**Step 5: Run the new tests**

```bash
python -m pytest tests/test_morning_report_sources.py -v
```

Expected: all green.

**Step 6: Run full test suite**

```bash
python -m pytest tests/test_morning_report_cmd.py tests/test_morning_report_sources.py -v
```

Expected: all green.

**Step 7: Commit**

```bash
git add src/morning_report.py tests/test_morning_report_sources.py
git commit -m "feat(morning-report): add ORIGINAL_PLAN + ADJUSTMENT sections to prompt and report"
```

---

### Task 3: `/workout` Discord command uses internal plan

**Files:**
- Modify: `src/discord_bot.py` — `/workout` command handler (~line 487)

**Context:** The `/workout` command handler (lines 487–540) reads directly from the health cache JSON. Replace the inner logic to try `skills.plans.get_schedule(days=1)` first. Discord bot tests are hard to unit-test directly; the existing bot migration tests in `test_morning_report_cmd.py` verify bot structure. Manual verification via Discord after deployment.

**Step 1: Find the exact line range to replace**

The `/workout` command starts at the `@bot.tree.command(name="workout"` decorator and ends around line 545. The section to replace is the `try:` block inside `workout_command()`.

**Step 2: Replace the workout command handler body**

Replace the `try:` block in `workout_command()` (approximately lines 491–545):

```python
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        embeds = []

        # ── Internal plan (authoritative) ──────────────────────────────────────
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from skills.plans import get_schedule
            schedule = get_schedule(days=1)
            today_row = next(
                (r for r in schedule.get("rows", []) if r["date"] == today),
                None,
            )
        except Exception:
            today_row = None

        if today_row and today_row.get("workout_type") not in ("none", "rest", None):
            row = today_row
            wtype = row["workout_type"]
            dur = row.get("duration_min") or 0
            intent = row.get("intent", "")
            steps = row.get("structure_steps", [])

            _EMOJI = {"easy": "🏃", "long": "🏃", "tempo": "⚡", "interval": "⚡"}
            _COLOR = {
                "easy": discord.Color.green(),
                "long": discord.Color.green(),
                "tempo": discord.Color.orange(),
                "interval": discord.Color.orange(),
            }
            _LABEL = {
                "easy": "Easy Run",
                "long": "Long Run",
                "tempo": "Tempo Run",
                "interval": "Interval Run",
            }
            emoji = _EMOJI.get(wtype, "📋")
            color = _COLOR.get(wtype, discord.Color.blue())
            label = _LABEL.get(wtype, wtype.title())

            embed = discord.Embed(
                title=f"{emoji} {label}",
                color=color,
                timestamp=datetime.now(),
            )
            if intent:
                embed.description = intent
            if dur:
                embed.add_field(name="Duration", value=f"{dur} min", inline=True)
            if steps:
                step_lines = []
                for i, s in enumerate(steps, 1):
                    rep_str = f" ×{s['reps']}" if s.get("reps") else ""
                    tv = f"  [{s.get('target_value', '')}]" if s.get("target_value") else ""
                    step_lines.append(f"{i}. {s.get('label','').title()} {s.get('duration_min',0)}min{rep_str}{tv}")
                embed.add_field(name="Structure", value="\n".join(step_lines), inline=False)

            plan_id = schedule.get("plan_id") or "unknown"
            embed.set_footer(text=f"Plan: {plan_id}")
            embeds.append(embed)

        else:
            # ── Health cache fallback (FinalSurge / ICS) ───────────────────────
            cache_path = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
            with open(cache_path) as f:
                cache = json.load(f)

            workouts = [
                w for w in cache.get("scheduled_workouts", [])
                if w.get("scheduled_date", "").startswith(today)
            ]

            if not workouts:
                await interaction.followup.send("📭 No workouts scheduled for today")
                return

            for w in workouts:
                source = w.get("source", "unknown")
                domain = w.get("domain", "")

                if "ics_calendar" in source or domain == "running":
                    emoji = "🏃"
                    color = discord.Color.green()
                elif "strength" in domain or "strength" in w.get("name", "").lower():
                    emoji = "💪"
                    color = discord.Color.orange()
                elif "mobility" in domain or "mobility" in w.get("name", "").lower():
                    emoji = "🧘"
                    color = discord.Color.purple()
                else:
                    emoji = "📋"
                    color = discord.Color.blue()

                embed = discord.Embed(
                    title=f"{emoji} {w.get('name', 'Workout')}",
                    color=color,
                    timestamp=datetime.now(),
                )
                if w.get("description"):
                    embed.description = w["description"][:3900]
                if w.get("duration_min"):
                    embed.add_field(name="Duration", value=f"{w['duration_min']} min", inline=True)
                embeds.append(embed)

        if not embeds:
            await interaction.followup.send("📭 No workouts scheduled for today")
            return

        # Discord limit: max 10 embeds per message
        await interaction.followup.send(embeds=embeds[:10])
```

**Step 3: Verify bot still imports cleanly**

```bash
cd /home/coach/running-coach
python -c "import sys; sys.path.insert(0,'src'); import ast; ast.parse(open('src/discord_bot.py').read()); print('syntax ok')"
```

Expected: `syntax ok`

**Step 4: Run existing tests**

```bash
python -m pytest tests/test_morning_report_cmd.py -v
```

Expected: all green (the bot migration test checks structure, not workout logic).

**Step 5: Commit**

```bash
git add src/discord_bot.py
git commit -m "feat(discord): /workout command reads from internal plan first"
```

---

### Task 4: `daily_workout_formatter.py` uses internal plan for running

**Files:**
- Modify: `src/daily_workout_formatter.py` — `get_scheduled_workouts()`, `format_running_workout()`
- Create: `tests/test_daily_workout_formatter.py`

**Context:** `get_scheduled_workouts(date_str)` reads `health_data["scheduled_workouts"]`. Replace to try internal plan first. Add a branch in `format_running_workout()` for `source == "internal_plan"` that formats from `workout_type + intent + structure_steps` without regex parsing.

**Step 1: Write the failing tests**

Create `tests/test_daily_workout_formatter.py`:

```python
"""Tests: daily_workout_formatter reads internal plan before health cache."""
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _make_session(d: str, wtype: str = "easy", dur: int = 45, intent: str = "Easy run", steps=None):
    return {
        "date": d,
        "workout_type": wtype,
        "duration_min": dur,
        "intent": intent,
        "structure_steps": steps or [],
        "safety_flags": [],
        "plan_id": "test-plan",
    }


class TestGetScheduledWorkoutsInternalPlan:
    """get_scheduled_workouts uses internal plan when available."""

    def _call(self, sessions, health_data=None, date_str=None):
        from daily_workout_formatter import get_scheduled_workouts
        date_str = date_str or date.today().isoformat()
        with patch("daily_workout_formatter.get_active_sessions", return_value=sessions):
            with patch("daily_workout_formatter.load_health_data", return_value=health_data or {}):
                return get_scheduled_workouts(date_str)

    def test_returns_internal_session_for_matching_date(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="tempo", dur=55, intent="Tempo effort")]
        result = self._call(sessions, date_str=today)
        assert len(result) == 1
        assert result[0]["source"] == "internal_plan"
        assert result[0]["domain"] == "running"

    def test_rest_day_returns_empty(self):
        today = date.today().isoformat()
        sessions = [_make_session(today, wtype="rest", dur=0)]
        result = self._call(sessions, date_str=today)
        assert result == []

    def test_wrong_date_session_not_returned(self):
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = [_make_session(tomorrow)]
        result = self._call(sessions, date_str=today)
        assert result == []

    def test_falls_back_to_health_cache_when_no_sessions(self):
        today = date.today().isoformat()
        cache_workouts = [{"scheduled_date": today, "name": "Easy 30min", "domain": "running"}]
        result = self._call([], health_data={"scheduled_workouts": cache_workouts}, date_str=today)
        assert len(result) == 1
        assert result[0]["name"] == "Easy 30min"


class TestFormatRunningWorkoutInternalPlan:
    """format_running_workout renders internal_plan source correctly."""

    def _format(self, workout):
        from daily_workout_formatter import format_running_workout
        return format_running_workout(workout)

    def _internal_workout(self, wtype="easy", dur=45, intent="Easy run", steps=None):
        return {
            "name": "Easy Run",
            "description": intent,
            "duration_min": dur,
            "source": "internal_plan",
            "domain": "running",
            "workout_type": wtype,
            "structure_steps": steps or [],
            "intent": intent,
        }

    def test_easy_run_shows_duration(self):
        result = self._format(self._internal_workout(wtype="easy", dur=45))
        assert "45" in result

    def test_easy_run_shows_intent(self):
        result = self._format(self._internal_workout(intent="Conversational, aerobic base"))
        assert "Conversational, aerobic base" in result

    def test_tempo_shows_structure_steps(self):
        steps = [
            {"label": "warmup", "duration_min": 15, "reps": None, "target_value": "easy"},
            {"label": "main", "duration_min": 25, "reps": None, "target_value": "tempo"},
            {"label": "cooldown", "duration_min": 15, "reps": None, "target_value": "easy"},
        ]
        result = self._format(self._internal_workout(wtype="tempo", dur=55, steps=steps))
        assert "Warmup" in result
        assert "Main" in result
        assert "25" in result

    def test_no_steps_no_structure_section(self):
        result = self._format(self._internal_workout(steps=[]))
        assert "Structure" not in result
```

**Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_daily_workout_formatter.py -v 2>&1 | head -30
```

Expected: failures on import (`get_active_sessions` not in `daily_workout_formatter`).

**Step 3: Add internal plan lookup to `daily_workout_formatter.py`**

After the existing imports at the top of `daily_workout_formatter.py`, add:

```python
PROJECT_ROOT = Path(__file__).parent.parent


def _get_active_sessions_safe():
    """Import and call skills.plans.get_active_sessions(), returning [] on any error."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from skills.plans import get_active_sessions
        return get_active_sessions()
    except Exception:
        return []
```

Note: `REPO_ROOT` is already defined at line 14 as `Path(__file__).parent.parent` — use `REPO_ROOT` instead of defining a new `PROJECT_ROOT`. So just add the function:

```python
def _get_active_sessions_safe():
    """Import and call skills.plans.get_active_sessions(), returning [] on any error."""
    try:
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from skills.plans import get_active_sessions
        return get_active_sessions()
    except Exception:
        return []
```

And add a module-level alias for tests to patch:
```python
get_active_sessions = _get_active_sessions_safe  # patchable alias for tests
```

**Step 4: Rewrite `get_scheduled_workouts(date_str)`**

Replace the existing function body:

```python
def get_scheduled_workouts(date_str):
    """Get all scheduled workouts for a specific date — internal plan first, cache fallback."""
    _RUNNING_TYPES = {"easy", "long", "tempo", "interval"}
    _LABELS = {"easy": "Easy Run", "long": "Long Run", "tempo": "Tempo Run", "interval": "Interval Run"}

    # Internal plan (authoritative)
    sessions = _get_active_sessions_safe()
    today_sessions = [s for s in sessions if s.get("date") == date_str]
    if today_sessions:
        workouts = []
        for s in today_sessions:
            wtype = s.get("workout_type", "rest")
            if wtype not in _RUNNING_TYPES:
                continue  # skip rest / strength
            steps = s.get("structure_steps", [])
            intent = s.get("intent", "")
            workouts.append({
                "name": _LABELS.get(wtype, wtype.title()),
                "description": intent,
                "duration_min": s.get("duration_min", 0),
                "domain": "running",
                "source": "internal_plan",
                "workout_type": wtype,
                "structure_steps": steps,
                "intent": intent,
            })
        return workouts  # may be empty (pure rest day) — caller handles

    # Health cache fallback
    health_data = load_health_data()
    if not health_data:
        return []

    scheduled = health_data.get('scheduled_workouts', [])
    workouts = [w for w in scheduled if w.get('scheduled_date') == date_str]

    # Infer domain for workouts without it
    for w in workouts:
        if not w.get('domain'):
            name = w.get('name', '').lower()
            if any(k in name for k in ('run', 'tempo', 'interval', 'easy', 'long')):
                w['domain'] = 'running'
            elif any(k in name for k in ('strength', 'lift')):
                w['domain'] = 'strength'
            elif any(k in name for k in ('mobility', 'stretch', 'yoga')):
                w['domain'] = 'mobility'

    return workouts
```

**Step 5: Add internal plan branch to `format_running_workout(workout)`**

Add an early-return branch at the top of `format_running_workout()` (before the existing duration parsing):

```python
def format_running_workout(workout):
    """Format a running workout for display."""
    # ── Internal plan: format directly without regex parsing ──────────────────
    if workout.get("source") == "internal_plan":
        wtype = workout.get("workout_type", "easy")
        dur = workout.get("duration_min", 0)
        intent = workout.get("intent", "")
        steps = workout.get("structure_steps", [])

        _LABELS = {
            "easy": "Easy Run", "long": "Long Run",
            "tempo": "Tempo Run", "interval": "Interval Run",
        }
        label = _LABELS.get(wtype, wtype.title())
        output = f"## 🏃 {label}\n"
        if dur:
            output += f"**Duration:** {dur} minutes\n"
        output += "\n"
        if intent:
            output += f"**Workout:** {intent}\n"
        if steps:
            output += "\n**Structure:**\n"
            for i, s in enumerate(steps, 1):
                rep_str = f" ×{s['reps']}" if s.get("reps") else ""
                tv = f"  [{s.get('target_value', '')}]" if s.get("target_value") else ""
                output += f"{i}. {s.get('label','').title()} {s.get('duration_min',0)}min{rep_str}{tv}\n"
        return output

    # ── Health cache / FinalSurge: existing regex-based logic ─────────────────
    name = workout.get('name', 'Unknown')
    # ... (keep all existing code from here unchanged)
```

**Step 6: Run the tests**

```bash
python -m pytest tests/test_daily_workout_formatter.py -v
```

Expected: all green.

**Step 7: Run full test suite for regressions**

```bash
python -m pytest tests/ -v --ignore=tests/test_ai_call.py --ignore=tests/test_location_fix.py --ignore=tests/test_location_geocoding.py --ignore=tests/test_session.py 2>&1 | tail -20
```

Expected: all green.

**Step 8: Commit**

```bash
git add src/daily_workout_formatter.py tests/test_daily_workout_formatter.py
git commit -m "feat(formatter): daily workout formatter reads internal plan first"
```

---

### Task 5: Restart bot and smoke-test

**Files:** None changed.

**Step 1: Restart the Discord bot**

```bash
sudo systemctl restart running-coach-bot
```

**Step 2: Check bot logs for startup errors**

```bash
journalctl -u running-coach-bot -n 50 --no-pager
```

Expected: no import errors, no traceback on startup.

**Step 3: Verify `/workout` in Discord**

Type `/workout` in Discord. Expected: embed shows workout from internal plan (with plan ID in footer), not FinalSurge name.

**Step 4: Verify `/coach_today` still works**

Type `/coach_today`. Expected: same workout content as `/workout` (both now reading same SQLite source).

**Step 5: Final commit (if any fixups needed)**

```bash
git add -p
git commit -m "fix: post-restart smoke-test fixups"
```

---

### Task 6: Run full regression suite

```bash
cd /home/coach/running-coach
python -m pytest tests/ -v \
  --ignore=tests/test_ai_call.py \
  --ignore=tests/test_location_fix.py \
  --ignore=tests/test_location_geocoding.py \
  --ignore=tests/test_session.py \
  2>&1 | tail -30
```

Expected: all green. If any fail, fix before declaring done.
