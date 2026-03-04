#!/usr/bin/env python3
"""
Coach CLI — unified entrypoint for the running coach system.

Commands:
    sync                     Sync Garmin health data
    plan --week [--force]    Generate + persist a 7-day plan via Brain
    export-garmin [opts]     Publish internal plan to Garmin Connect
    brief --today            Print today's planned workout
    memory search "query"    Search SQLite events and plan days

Authority (non-negotiable):
    Internal SQLite plan is authoritative. FinalSurge/ICS is optional input only.
    Garmin publishing uses the sacred upload path (src/auto_workout_generator +
    src/workout_uploader) and NEVER writes data/generated_workouts.json directly.
"""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s [%(name)s] %(message)s",
)

# ── sync ──────────────────────────────────────────────────────────────────────


def cmd_sync(args) -> int:
    from skills.garmin_sync import run

    result = run(
        force=getattr(args, "force", False),
        source="cli",
        days=getattr(args, "days", None),
        check_only=getattr(args, "check_only", False),
    )
    if result["success"]:
        print(f"✓ Garmin sync complete (event_id={result['event_id'][:8]})")
        if result["summary"]:
            for line in result["summary"].splitlines()[:10]:
                print(f"  {line}")
    else:
        print(f"✗ Garmin sync failed (rc={result['returncode']})", file=sys.stderr)
        print(result["stderr"][:300], file=sys.stderr)
        return 1
    return 0


# ── plan ──────────────────────────────────────────────────────────────────────


def cmd_plan(args) -> int:
    # Route --macro to cmd_macro
    if getattr(args, "macro", False):
        return cmd_macro(args)

    if not getattr(args, "week", False):
        print("Error: specify --week or --macro", file=sys.stderr)
        return 1

    from memory.retrieval import build_context_packet
    from brain import plan_week

    print("Building context packet…")
    ctx = build_context_packet()

    dq = ctx.get("data_quality", {})
    conf = dq.get("readiness_confidence", "unknown")
    print(f"  data_quality.readiness_confidence = {conf}")
    mg = ctx.get("macro_guidance")
    if mg and isinstance(mg, dict) and not mg.get("_truncated"):
        cw = mg.get("current_week", {})
        print(
            f"  macro_guidance = {mg.get('macro_id')} "
            f"week {cw.get('week_number')}/{mg.get('total_weeks')} "
            f"phase={cw.get('phase')} vol={cw.get('volume_floor_miles')}-{cw.get('volume_target_miles')}-{cw.get('volume_ceiling_miles')}mi"
        )

    print("Calling Brain (LLM)…")
    try:
        decision = plan_week(ctx, force=getattr(args, "force", False))
    except Exception as exc:
        print(f"✗ Brain failed: {exc}", file=sys.stderr)
        return 1

    print(f"\n✓ Plan generated: {decision.week_start} → {decision.week_end}")
    print(f"  Phase: {decision.phase} | Volume: {decision.weekly_volume_miles:.1f} mi")
    if decision.safety_flags:
        print(f"  Safety flags: {', '.join(decision.safety_flags)}")

    # Print day summary
    print()
    for d in decision.days:
        flag = " [!]" if d.safety_flags else ""
        print(
            f"  {d.date}  {d.workout_type:10s}  {d.duration_min:3d}min  {d.intent}{flag}"
        )

    return 0


# ── macro ──────────────────────────────────────────────────────────────────────


def cmd_macro(args) -> int:
    """Generate or display the long-range periodized training block."""
    from brain.macro_plan import generate_macro_plan, MacroValidationError
    from memory.db import get_active_macro_plan

    show_only = getattr(args, "show", False)
    force = getattr(args, "force", False)

    if show_only:
        row = get_active_macro_plan()
        if row is None:
            print("No active macro plan. Run 'coach plan --macro' to generate one.")
            return 1
        try:
            from brain.schemas import MacroPlan

            plan = MacroPlan.model_validate(row["plan"])
            _print_macro_plan(plan, row["macro_id"])
            return 0
        except Exception as exc:
            print(f"✗ Could not parse active macro plan: {exc}", file=sys.stderr)
            return 1

    from memory.retrieval import build_context_packet

    print("Building context packet…")
    ctx = build_context_packet()

    print("Calling Brain (LLM) to generate macro plan…")
    print("  (This may take up to 4 minutes — macro plan covers the full block)")
    try:
        plan = generate_macro_plan(ctx, force=force)
    except MacroValidationError as exc:
        print(f"\n✗ Macro plan validation failed:", file=sys.stderr)
        for err in exc.errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"✗ Macro plan generation failed: {exc}", file=sys.stderr)
        return 1

    # Fetch the macro_id that was just activated
    from memory.db import get_active_macro_plan_id

    macro_id = get_active_macro_plan_id() or "unknown"
    _print_macro_plan(plan, macro_id)
    return 0


def _print_macro_plan(plan, macro_id: str, today=None) -> None:
    """Print a human-readable tabular summary of the macro plan."""
    from datetime import date, timedelta

    today_str = today or date.today().isoformat()
    current_week = plan.get_week_for_date(today_str)

    try:
        start_d = date.fromisoformat(plan.start_week)
        end_d = start_d + timedelta(days=7 * plan.total_weeks - 1)
        block_range = f"{plan.start_week} → {end_d.isoformat()}"
    except ValueError:
        block_range = plan.start_week

    race_info = ""
    if plan.mode == "race_targeted" and plan.race_date:
        race_info = f"  Race: {plan.race_name} on {plan.race_date}"

    print(f"✓ Macro plan: {macro_id}  mode={plan.mode}")
    print(
        f"  Block: {block_range}  {plan.total_weeks} weeks  "
        f"VDOT: {plan.vdot:.1f}  Peak: {plan.peak_weekly_miles:.1f} mi/wk" + race_info
    )
    print()
    print(
        f"  {'WK':>2}  {'START':<12} {'PHASE':<13} {'MILES':>5}  {'LR_MIN':>6}  {'INTENSITY':<10} NOTES"
    )
    print("  " + "─" * 76)

    for w in plan.weeks:
        notes = w.planner_notes[:35] if w.planner_notes else ""
        if len(w.planner_notes) > 35:
            notes = notes.rstrip() + "…"
        is_current = (
            current_week is not None and w.week_number == current_week.week_number
        )
        marker = "→" if is_current else " "
        print(
            f"{marker} {w.week_number:>2}  {w.week_start:<12} {w.phase:<13} "
            f"{w.volume_target_miles:>5.1f}  {w.long_run_max_min:>6}  "
            f"{w.intensity_budget:<10} {notes}"
        )


# ── export-garmin ─────────────────────────────────────────────────────────────


def cmd_export_garmin(args) -> int:
    source = getattr(args, "source", "internal")
    dry_run = not getattr(args, "live", False)  # default is dry_run=True
    days = getattr(args, "days", 7)

    if source == "ics":
        print(
            "Error: --source ics is not supported. "
            "The internal plan is authoritative; ICS is optional input only.",
            file=sys.stderr,
        )
        return 1

    from skills.publish_to_garmin import publish

    if dry_run:
        print(f"[DRY RUN] Preparing workouts from internal plan (next {days} days)…")
    else:
        print(f"Publishing workouts from internal plan (next {days} days)…")

    result = publish(days=days, dry_run=dry_run)

    if not dry_run:
        if result["published"]:
            print(
                f"\n✓ Published {len(result['published'])} workout(s): {result['published']}"
            )
        if result["skipped"]:
            print(f"\nSkipped {len(result['skipped'])}:")
            for s in result["skipped"]:
                print(f"  {s['date']}: {s['reason']}")

    if result["degraded"]:
        print(
            f"\n⚠ {len(result['degraded'])} workout(s) fell back to easy-run rendering "
            f"(render_degraded events recorded in SQLite): {result['degraded']}"
        )

    # Summary line for smoke test
    prepared = len(result["prepared"])
    print(f"\nSummary: {prepared} workout(s) prepared for Garmin")
    return 0


# ── brief ─────────────────────────────────────────────────────────────────────


def cmd_brief(args) -> int:
    if not getattr(args, "today", False):
        print("Error: specify --today", file=sys.stderr)
        return 1

    from skills.plans import get_active_sessions, get_active_plan_meta

    meta = get_active_plan_meta()
    if meta is None:
        print("No active plan. Run 'coach plan --week' first.")
        return 1

    today_str = date.today().isoformat()
    sessions = get_active_sessions()
    today_session = next((s for s in sessions if s["date"] == today_str), None)

    print(
        f"Plan: {meta['plan_id']}  {meta['week_start']} → {meta['week_end']}  "
        f"phase={meta['phase']}  volume={meta['weekly_volume_miles']:.1f}mi"
    )

    if today_session is None:
        print(f"\nToday ({today_str}): not found in active plan")
        return 0

    s = today_session
    flags = f"  flags={s['safety_flags']}" if s["safety_flags"] else ""
    print(f"\nToday ({today_str}): {s['workout_type'].upper()}  {s['duration_min']}min")
    print(f"  Intent: {s['intent']}{flags}")
    if s["structure_steps"]:
        print("  Steps:")
        for step in s["structure_steps"]:
            reps = f" x{step['reps']}" if step.get("reps") else ""
            print(
                f"    {step['label']:10s} {step['duration_min']}min{reps}  {step['target_value']}"
            )
    return 0


# ── schedule ──────────────────────────────────────────────────────────────────


def cmd_schedule(args) -> int:
    """Export the active plan's next N days in a human-readable format."""
    if not getattr(args, "week", False):
        print("Error: specify --week", file=sys.stderr)
        return 1

    days = getattr(args, "days", 7)
    fmt = getattr(args, "format", "mobile")

    from skills.plans import get_schedule

    sched = get_schedule(days=days)

    if sched["plan_id"] is None:
        print("No active plan. Run 'coach plan --week' first.", file=sys.stderr)
        return 1

    if fmt == "table":
        print(_fmt_table(sched))
    elif fmt == "text":
        print(_fmt_text(sched))
    elif fmt == "md":
        print(_fmt_md(sched))
    elif fmt == "mobile":
        print(_fmt_mobile(sched))
    else:
        print(f"Unknown format: {fmt!r}", file=sys.stderr)
        return 1

    return 0


def _clamp60(s: str) -> str:
    """Clamp intent to 60 chars for stable table width."""
    return s if len(s) <= 60 else s[:57] + "..."


def _fmt_table(sched: dict) -> str:
    lines = []
    pid = sched["plan_id"] or "?"
    ps = sched.get("plan_start") or "?"
    pe = sched.get("plan_end") or "?"
    ca = sched.get("created_at") or "?"
    # Trim created_at to date+time without microseconds
    if len(ca) > 19:
        ca = ca[:19]
    lines.append(f"Active plan: {pid}  {ps} → {pe}  (created_at={ca})")
    lines.append(
        f"Range: {sched['range_start']} → {sched['range_end']}  "
        f"Days: {len(sched['rows'])}"
    )
    lines.append("")
    lines.append(f"{'DATE':<12} {'DAY':<4} {'TYPE':<10} {'MIN':>4}  INTENT")
    lines.append("─" * 74)

    for row in sched["rows"]:
        min_val = str(row["duration_min"]) if row["duration_min"] != "" else ""
        lines.append(
            f"{row['date']:<12} {row['weekday']:<4} "
            f"{row['workout_type']:<10} {min_val:>4}  "
            f"{_clamp60(row['intent'])}"
        )
        if row["safety_flags"]:
            flags_str = "; ".join(row["safety_flags"])
            lines.append(f"           ↳ flags: {flags_str}")

    return "\n".join(lines)


def _fmt_text(sched: dict) -> str:
    lines = []
    pid = sched["plan_id"] or "?"
    lines.append(
        f"Schedule — plan {pid}  {sched['range_start']} to {sched['range_end']}"
    )
    lines.append("")
    for row in sched["rows"]:
        flag_part = (
            f" [flags: {'; '.join(row['safety_flags'])}]" if row["safety_flags"] else ""
        )
        lines.append(
            f"{row['weekday']} {row['date']} — " f"{_clamp60(row['intent'])}{flag_part}"
        )
    return "\n".join(lines)


_TYPE_EMOJI = {
    "rest": ("⚪", "Rest"),
    "easy": ("🟢", "Easy"),
    "long": ("🔵", "Long"),
    "race": ("🟣", "Race"),
    "tempo": ("🟠", "Quality"),
    "interval": ("🟠", "Quality"),
    "workout": ("🟠", "Quality"),
    "strength": ("🟠", "Quality"),
    "cross": ("🟠", "Quality"),
    "none": ("⚫", "No entry"),
}


def _fmt_mobile(sched: dict) -> str:
    """Mobile/Discord-friendly 'day cards' format — no code fences."""
    pid = (sched["plan_id"] or "?")[:16]
    ps = sched.get("plan_start") or "?"
    pe = sched.get("plan_end") or "?"
    n = len(sched["rows"])

    lines = [
        f"📅 Week Schedule ({n} days)",
        f"Plan: {pid}  {ps}→{pe}",
        f"Range: {sched['range_start']}→{sched['range_end']}",
    ]

    for row in sched["rows"]:
        lines.append("")  # blank separator between days
        emoji, label = _TYPE_EMOJI.get(
            row["workout_type"], ("🔘", row["workout_type"].title())
        )
        dur = row["duration_min"]
        dur_part = f" · {dur}m" if dur not in ("", 0) else ""
        # Bold day header line
        lines.append(f"**{row['weekday']} {row['date']}** — {emoji} {label}{dur_part}")
        # Intent (clamped to 120 chars)
        intent = row["intent"]
        if len(intent) > 120:
            intent = intent[:117] + "…"
        if intent and intent != "(no entry)":
            lines.append(intent)
        # Flags — one line each, clamped to 180 chars
        for flag in row["safety_flags"]:
            flag_line = f"⚑ {flag}"
            if len(flag_line) > 180:
                flag_line = flag_line[:177] + "…"
            lines.append(flag_line)

    return "\n".join(lines)


def _fmt_md(sched: dict) -> str:
    lines = []
    pid = sched["plan_id"] or "?"
    lines.append(f"## Schedule — plan `{pid}`")
    lines.append(
        f"Range: **{sched['range_start']}** → **{sched['range_end']}**  "
        f"({len(sched['rows'])} days)"
    )
    lines.append("")
    for row in sched["rows"]:
        wtype = row["workout_type"]
        dur = f" {row['duration_min']}min" if row["duration_min"] not in ("", 0) else ""
        intent = _clamp60(row["intent"])
        flags_part = (
            f"\n  - *flags: {'; '.join(row['safety_flags'])}*"
            if row["safety_flags"]
            else ""
        )
        lines.append(
            f"- **{row['date']} ({row['weekday']})** — {wtype}{dur}: {intent}"
            f"{flags_part}"
        )
    return "\n".join(lines)


# ── db sanity ─────────────────────────────────────────────────────────────────


def cmd_db(args) -> int:
    subcmd = getattr(args, "db_command", None)
    if subcmd == "sanity":
        return _db_sanity()
    print("Unknown db subcommand", file=sys.stderr)
    return 1


def _json_cache_age_minutes() -> float | None:
    """Return age of health_data_cache.json in minutes, or None on failure."""
    try:
        import json as _json
        from datetime import datetime, timezone
        from memory.retrieval import HEALTH_CACHE

        data = _json.loads(HEALTH_CACHE.read_text())
        ts_str = data.get("last_updated", "")
        if not ts_str:
            return None
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
        return (datetime.utcnow() - ts).total_seconds() / 60
    except Exception:
        return None


def _db_sanity() -> int:
    import sqlite3
    from datetime import datetime, timedelta
    from memory.db import DB_PATH, init_db, get_last_sync_run
    from memory.retrieval import _rollup_readiness_from_sqlite

    init_db()

    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()
    today_str = today.isoformat()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    issues = []

    print(f"DB: {DB_PATH}")
    print()

    # Last successful sync
    last_ok = get_last_sync_run(status="success")
    if last_ok:
        ts_str = last_ok["finished_at"] or last_ok["started_at"]
        try:
            ts = datetime.fromisoformat(ts_str)
            age_min = int((datetime.utcnow() - ts).total_seconds() / 60)
            age_str = f"{age_min} min ago"
            if age_min > 60:
                # External processes (morning report, Discord bot) sync Garmin
                # via sync_garmin_data.sh without writing to sync_runs. So
                # sync_runs age alone is not a reliable health signal — also
                # check JSON cache freshness before flagging DEGRADED.
                cache_age_min = _json_cache_age_minutes()
                if cache_age_min is not None and cache_age_min <= 60:
                    age_str += f"  (cache {int(cache_age_min)}min old — ok)"
                else:
                    stale = (
                        f"{int(cache_age_min)}min"
                        if cache_age_min is not None
                        else "unknown"
                    )
                    issues.append(
                        f"last sync {age_min}min ago and cache {stale} old (both stale)"
                    )
        except Exception:
            age_str = ts_str
        print(f"Sync:  last success {age_str}  (source={last_ok.get('source','?')})")
    else:
        print("Sync:  no successful sync recorded")
        issues.append("no sync recorded")

    print()

    # daily_metrics
    dm_count = conn.execute(
        "SELECT COUNT(*) FROM daily_metrics WHERE day >= ?", (week_ago,)
    ).fetchone()[0]
    dm_latest = conn.execute("SELECT MAX(day) FROM daily_metrics").fetchone()[0]
    has_today = conn.execute(
        "SELECT 1 FROM daily_metrics WHERE day = ?", (today_str,)
    ).fetchone()
    today_flag = "" if has_today else "  ← today missing"
    print(
        f"daily_metrics (7d):  {dm_count} rows  latest {dm_latest or 'none'}{today_flag}"
    )
    if not has_today:
        issues.append("today missing from daily_metrics")

    # activities
    act_count = conn.execute(
        "SELECT COUNT(*) FROM activities WHERE activity_date >= ?", (week_ago,)
    ).fetchone()[0]
    act_latest = conn.execute("SELECT MAX(activity_date) FROM activities").fetchone()[0]
    print(f"activities (7d):     {act_count} rows  latest {act_latest or 'none'}")

    print()
    conn.close()

    # Retrieval source
    rt = _rollup_readiness_from_sqlite(7, DB_PATH)
    if rt is not None:
        print("Retrieval: source=sqlite")
    else:
        print("Retrieval: source=json_fallback")
        issues.append("retrieval falling back to JSON")

    print()

    # Macro plan status
    from memory.db import get_active_macro_plan

    macro = get_active_macro_plan()
    if macro:
        macro_id = macro["macro_id"]
        mode = macro["mode"]
        total_weeks = macro["total_weeks"]
        status_str = macro["status"]
        try:
            from brain.schemas import MacroPlan

            mp = MacroPlan.model_validate(macro["plan"])
            cw = mp.get_week_for_date(today_str)
            weeks_remaining = (total_weeks - cw.week_number + 1) if cw else "N/A"
        except Exception:
            weeks_remaining = "?"
        print(
            f"macro_plan:  {macro_id}  mode={mode}  "
            f"weeks_remaining={weeks_remaining}  status={status_str}"
        )
    else:
        print("macro_plan:  none")

    print()

    if issues:
        print(f"Status: DEGRADED ({'; '.join(issues)})")
        return 1
    print("Status: HEALTHY")
    return 0


# ── parity ────────────────────────────────────────────────────────────────────


def cmd_parity(args) -> int:
    day_str = args.day
    try:
        target = date.fromisoformat(day_str)
    except ValueError:
        print(f"Error: invalid date {day_str!r} (expected YYYY-MM-DD)", file=sys.stderr)
        return 1

    from memory.db import DB_PATH, init_db, get_daily_metrics
    from memory.retrieval import HEALTH_CACHE

    init_db()

    # SQLite row for that day
    rows = get_daily_metrics(target, target)
    sq = rows[0] if rows else None

    # JSON cache
    json_cache = None
    json_missing = False
    try:
        with HEALTH_CACHE.open(encoding="utf-8") as f:
            json_cache = json.load(f)
    except FileNotFoundError:
        print("JSON cache: file not found")
        json_missing = True
    except Exception as exc:
        print(f"JSON cache: unreadable ({exc})")
        json_missing = True

    def _find(lst, date_key, day):
        return next((r for r in lst if str(r.get(date_key, ""))[:10] == day), None)

    if json_cache:
        tr_e = _find(json_cache.get("training_readiness", []), "date", day_str)
        bb_e = _find(json_cache.get("body_battery", []), "date", day_str)
        hrv_e = _find(json_cache.get("hrv_readings", []), "date", day_str)
        j_tr = tr_e["score"] if tr_e else None
        j_bb = bb_e["latest_level"] if bb_e else None
        j_hrv = hrv_e["last_night_avg"] if hrv_e else None
    else:
        j_tr = j_bb = j_hrv = None

    s_tr = sq["training_readiness"] if sq else None
    s_bb = sq["body_battery"] if sq else None
    s_hrv = sq["hrv_rmssd"] if sq else None

    metrics = [
        ("training_readiness", s_tr, j_tr),
        ("body_battery_max", s_bb, j_bb),
        ("hrv", s_hrv, j_hrv),
    ]

    mismatch = False
    for name, s_val, j_val in metrics:
        if s_val is not None and j_val is not None:
            if abs(float(s_val) - float(j_val)) > 0.5:
                mark = "✗"
                mismatch = True
            else:
                mark = "✓"
        else:
            mark = "✓"  # one or both sides absent — informational, not an error
        s_str = str(int(round(s_val))) if s_val is not None else "None"
        j_str = str(int(round(j_val))) if j_val is not None else "None"
        print(f"{name:<22} sqlite={s_str:<6} json={j_str:<6} {mark}")

    return 2 if mismatch else 0


# ── morning-report ────────────────────────────────────────────────────────────


def cmd_morning_report(args) -> int:
    # Add src/ to sys.path so morning_report can import environmental_adjustments
    src_dir = str(PROJECT_ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from morning_report import run as _mr_run

    return _mr_run(
        check_sleep=getattr(args, "check_sleep", False),
        as_json=getattr(args, "json", False),
        notification_only=getattr(args, "notification_only", False),
        full_only=getattr(args, "full_only", False),
        no_weather=getattr(args, "no_weather", False),
    )


# ── analyze-patterns ──────────────────────────────────────────────────────────


def cmd_analyze_patterns(args) -> int:
    src_dir = str(PROJECT_ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from athlete_pattern_analyzer import run_analysis

    patterns = run_analysis()
    hrv = patterns["hrv_calibration"]
    aero = patterns["aerobic_efficiency"]
    rec = patterns["recovery_signature"]
    vol = patterns["volume_tolerance"]
    print("✓ Patterns written to data/athlete/learned_patterns.md")
    print(f"  HRV baseline: {hrv['median_hrv']} ms (range {hrv['hrv_range']})")
    print(f"  Aerobic efficiency: {len(aero['pace_at_hr'])} HR buckets computed")
    print(f"  Recovery signature: {rec['days_to_hrv_recovery']} days to HRV recovery")
    print(f"  Volume tolerance: ~{vol['sustainable_weekly_miles']} mi/week sustainable")
    return 0


# ── memory search ─────────────────────────────────────────────────────────────


def cmd_memory(args) -> int:
    subcmd = getattr(args, "mem_command", None)
    if subcmd == "search":
        return _memory_search(args.query)
    print("Unknown memory subcommand", file=sys.stderr)
    return 1


# ── agent ─────────────────────────────────────────────────────────────────────


def cmd_agent(args) -> int:
    subcmd = getattr(args, "agent_command", None)
    if subcmd == "status":
        return _agent_status()
    if subcmd == "run-once":
        return _agent_run_once()
    print("Unknown agent subcommand", file=sys.stderr)
    return 1


def _agent_status() -> int:
    import sqlite3
    from datetime import datetime, timezone
    from memory.db import DB_PATH, init_db, get_last_sync_run
    from agent.lock import get_lock_state

    init_db()

    # Lock state
    lock = get_lock_state()
    if lock is None:
        print("Lock:  FREE")
    elif lock.get("expired"):
        print(
            f"Lock:  EXPIRED (was held by {lock['owner']} until {lock['expires_at']})"
        )
    else:
        print(f"Lock:  HELD by {lock['owner']}  expires {lock['expires_at']}")

    print()

    # Sync freshness
    last_ok = get_last_sync_run(status="success")
    last_run = get_last_sync_run()
    if last_ok:
        ts_str = last_ok["finished_at"] or last_ok["started_at"]
        try:
            ts = datetime.fromisoformat(ts_str)
            age_min = int((datetime.utcnow() - ts).total_seconds() / 60)
            age_str = f"{age_min} min ago"
        except Exception:
            age_str = ts_str or "unknown"
        src = last_ok.get("source", "?")
        print(f"Sync:  last success {age_str}  (source={src})")
    else:
        print("Sync:  no successful sync recorded yet")

    if last_run and last_run.get("status") not in ("success", "running"):
        err = last_run.get("error_summary") or ""
        print(f"Sync:  last run status={last_run['status']}  {err[:80]}")

    print()

    # Recent task_runs
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT task, started_at, finished_at, status, details_json "
        "FROM task_runs ORDER BY started_at DESC LIMIT 15"
    ).fetchall()

    if rows:
        print(f"{'Task':<22} {'Started':<20} {'Status':<10} Details")
        print("─" * 80)
        for r in rows:
            details = ""
            if r["details_json"]:
                try:
                    d = json.loads(r["details_json"])
                    # Extract a short summary
                    if "summary" in d:
                        details = str(d["summary"])[:40]
                    elif "error" in d:
                        details = f"ERROR: {d['error'][:40]}"
                    elif "new_plan_id" in d and d["new_plan_id"]:
                        details = f"new_plan={d['new_plan_id']}"
                    elif "hash_changed" in d:
                        details = f"hash_changed={d['hash_changed']} hooks={d.get('hooks_run', [])}"
                except Exception:
                    pass
            started = (r["started_at"] or "")[:16]
            print(f"  {r['task']:<20} {started:<20} {r['status']:<10} {details}")
    else:
        print("No task_runs recorded yet.")

    # State keys summary
    print()
    state_keys = [
        "runner_last_context_hash",
        "runner_last_daily_rollover",
        "runner_lock",
    ]
    state_rows = conn.execute(
        f"SELECT key, value FROM state WHERE key IN ({','.join('?'*len(state_keys))})",
        state_keys,
    ).fetchall()
    if state_rows:
        print("State:")
        for r in state_rows:
            val = r["value"]
            if len(val) > 60:
                val = val[:60] + "…"
            print(f"  {r['key']:<35} {val}")

    conn.close()
    return 0


def _agent_run_once() -> int:
    """Run one complete heartbeat cycle."""
    from agent.runner import run_cycle

    print("Running one agent heartbeat cycle…")
    result = run_cycle()
    print()
    print(f"  lock_acquired:       {result['lock_acquired']}")
    print(f"  sync_success:        {result['sync_success']}")
    print(f"  hash_changed:        {result['hash_changed']}")
    print(f"  hooks_run:           {result['hooks_run']}")
    print(f"  readiness_triggered: {result['readiness_triggered']}")
    print(f"  needs_replan:        {result['needs_replan']}")
    print(f"  new_context_hash:    {result['new_context_hash']}")
    return 0


def _memory_search(query: str) -> int:
    import sqlite3
    from memory.db import DB_PATH, init_db

    init_db()
    q = f"%{query}%"

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    hits = 0

    # Search plan_days.intent
    rows = conn.execute(
        "SELECT plan_id, day, intent FROM plan_days WHERE intent LIKE ? ORDER BY day DESC LIMIT 20",
        (q,),
    ).fetchall()
    if rows:
        print(f"── Plan days matching {query!r} ──")
        for r in rows:
            print(f"  {r['day']}  [{r['plan_id'][:12]}]  {r['intent']}")
        hits += len(rows)

    # Search events.payload_json
    rows = conn.execute(
        "SELECT id, type, ts, payload_json FROM events WHERE payload_json LIKE ? ORDER BY ts DESC LIMIT 20",
        (q,),
    ).fetchall()
    if rows:
        print(f"\n── Events matching {query!r} ──")
        for r in rows:
            try:
                payload = json.loads(r["payload_json"])
            except Exception:
                payload = r["payload_json"]
            print(f"  {r['ts'][:16]}  {r['type']:30s}  {json.dumps(payload)[:80]}")
        hits += len(rows)

    conn.close()

    if hits == 0:
        print(f"No results for {query!r}")
    else:
        print(f"\n{hits} result(s)")
    return 0


# ── CLI wiring ────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser (extracted for testability)."""
    parser = argparse.ArgumentParser(
        prog="coach",
        description="Running coach CLI — Brain + Body system",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # sync
    p_sync = sub.add_parser("sync", help="Sync Garmin health data")
    p_sync.add_argument("--force", action="store_true", help="Skip cache-age check")
    p_sync.add_argument(
        "--days", type=int, metavar="N", help="Number of days to sync (default: 30)"
    )
    p_sync.add_argument(
        "--check-only",
        action="store_true",
        help="Preview what would be synced without updating cache",
    )
    p_sync.set_defaults(func=cmd_sync)

    # plan
    p_plan = sub.add_parser(
        "plan", help="Generate a training week or macro block via Brain LLM"
    )
    p_plan.add_argument("--week", action="store_true", help="Plan current week")
    p_plan.add_argument(
        "--macro", action="store_true", help="Generate full periodized macro block"
    )
    p_plan.add_argument(
        "--show",
        action="store_true",
        help="Show active macro plan without regenerating (use with --macro)",
    )
    p_plan.add_argument("--force", action="store_true", help="Bypass LLM cache")
    p_plan.set_defaults(func=cmd_plan)

    # export-garmin
    p_exp = sub.add_parser(
        "export-garmin", help="Publish internal plan to Garmin Connect"
    )
    p_exp.add_argument(
        "--days", type=int, default=7, metavar="N", help="Days ahead (default 7)"
    )
    p_exp.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=True,
        help="Preview only — no Garmin API calls (default)",
    )
    p_exp.add_argument(
        "--live",
        action="store_true",
        help="Actually upload to Garmin (overrides --dry-run)",
    )
    p_exp.add_argument(
        "--source",
        choices=["internal", "ics"],
        default="internal",
        help="Workout source (only 'internal' supported; 'ics' is rejected)",
    )
    p_exp.set_defaults(func=cmd_export_garmin)

    # brief
    p_brief = sub.add_parser("brief", help="Print today's planned workout")
    p_brief.add_argument("--today", action="store_true", required=True)
    p_brief.set_defaults(func=cmd_brief)

    # schedule
    p_sched = sub.add_parser("schedule", help="Export the active plan's week schedule")
    p_sched.add_argument(
        "--week", action="store_true", required=True, help="Export next N days"
    )
    p_sched.add_argument(
        "--days", type=int, default=7, metavar="N", help="Number of days (default 7)"
    )
    p_sched.add_argument(
        "--format",
        choices=["table", "text", "md", "mobile"],
        default="mobile",
        help="Output format (default: mobile = Discord-friendly day cards; table = desktop-aligned)",
    )
    p_sched.set_defaults(func=cmd_schedule)

    # db
    p_db = sub.add_parser("db", help="SQLite pipeline diagnostics")
    db_sub = p_db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("sanity", help="Check SQLite ingest + retrieval health")
    p_db.set_defaults(func=cmd_db)

    # parity
    p_parity = sub.add_parser("parity", help="Compare SQLite vs JSON cache for a day")
    p_parity.add_argument(
        "--day",
        required=True,
        metavar="YYYY-MM-DD",
        help="Date to compare (e.g. 2026-02-20)",
    )
    p_parity.set_defaults(func=cmd_parity)

    # morning-report
    p_mr = sub.add_parser("morning-report", help="Generate AI morning training report")
    p_mr.add_argument("--json", action="store_true", help="Output as JSON")
    p_mr.add_argument(
        "--notification-only", action="store_true", help="Only output notification text"
    )
    p_mr.add_argument(
        "--full-only", action="store_true", help="Only output full report"
    )
    p_mr.add_argument("--no-weather", action="store_true", help="Skip weather fetch")
    p_mr.add_argument(
        "--check-sleep",
        action="store_true",
        help="Exit 0 if today's sleep data exists, 1 otherwise",
    )
    p_mr.set_defaults(func=cmd_morning_report)

    # memory
    p_mem = sub.add_parser("memory", help="Query the Memory OS")
    mem_sub = p_mem.add_subparsers(dest="mem_command", required=True)
    p_search = mem_sub.add_parser(
        "search", help="Full-text search events and plan days"
    )
    p_search.add_argument("query", help="Search term")
    p_mem.set_defaults(func=cmd_memory)

    # agent
    p_agent = sub.add_parser("agent", help="Heartbeat agent controls")
    agent_sub = p_agent.add_subparsers(dest="agent_command", required=True)
    agent_sub.add_parser("status", help="Show lock state + recent task_runs")
    agent_sub.add_parser("run-once", help="Run one heartbeat cycle")
    p_agent.set_defaults(func=cmd_agent)

    p_patterns = sub.add_parser(
        "analyze-patterns",
        help="Mine historical Garmin data to discover athlete-specific training patterns",
    )
    p_patterns.set_defaults(func=cmd_analyze_patterns)

    return parser


def main() -> int:
    args = _build_parser().parse_args()
    rc = args.func(args)
    return rc if rc is not None else 0


if __name__ == "__main__":
    sys.exit(main())
