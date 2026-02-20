# Backlog Runner Prompt

_Paste this entire document into Claude Code to execute one backlog item._

---

## Instructions for Claude Code

You are executing exactly **one** item from the running-coach refactor backlog at `docs/BACKLOG.md`.

### Step 1 — Read current state

Read these files before doing anything else:
- `docs/BACKLOG.md` (backlog table + safety gates)
- `docs/PHASE_11_AUDIT.md` (architecture context and rationale)

### Step 2 — Pick the next item

Select the **highest-priority unblocked item** by these rules:
1. Status must be `TODO` (not `DONE`, `IN PROGRESS`, `BLOCKED`, or `DEFERRED`)
2. All items listed in its `Dependencies` column must be `DONE`
3. Prefer lower-numbered IDs (B11-001 before B11-002, etc.)
4. If two items have the same priority, pick the one with lower Risk first (L before M before H)

If no unblocked items exist, stop and say: "All unblocked backlog items are done. Awaiting user approval to add new items."

### Step 3 — Mark as IN PROGRESS

Update `docs/BACKLOG.md`: change the selected item's status from `TODO` to `IN PROGRESS`.

### Step 4 — Run Safety Gates (if required)

If the item's **Risk** is `M` or `H`, run all three safety gates **before** any file changes:

```bash
python -m pytest tests/ -x -q
gitleaks detect --source . --no-git --log-level warn 2>&1 | tail -20
python -m compileall . -q 2>&1 | grep -v "^Listing"
```

Report all gate results. If any gate fails, stop and ask the user how to proceed.

**Do not continue if gates fail.**

### Step 5 — Implement

Execute the work described in the item's `Acceptance Criteria`.

**Constraints:**
- Touch only the files listed in the item's `Files Touched` column.
- If you discover you need to touch additional files to meet the acceptance criteria, stop and ask before proceeding.
- Do not refactor, rename, add docstrings, or "improve" code beyond what the item requires.
- Do not invoke the Brain LLM (Claude/Gemini API) unless the item explicitly requires it.

### Step 6 — Verify

Run the safety gates again (all three, regardless of Risk level):

```bash
python -m pytest tests/ -x -q
gitleaks detect --source . --no-git --log-level warn 2>&1 | tail -20
python -m compileall . -q 2>&1 | grep -v "^Listing"
```

Also run any item-specific verification commands listed in its `Acceptance Criteria`.

Report: PASS or FAIL for each gate. If any fail, fix the issue first, then re-run.

### Step 7 — Update BACKLOG.md

Update `docs/BACKLOG.md`:
1. Change the item status to `DONE`
2. Add a `Notes` entry: date completed + one sentence describing what was done
3. If the item uncovered new issues or opportunities, add them to the **Suggestions** section below the table (do NOT add them to the main table yet — that requires user approval)

### Step 8 — Stop

Do not proceed to the next item. Print a summary:

```
✓ Completed: <item ID> — <item title>
  Files changed: <list>
  Tests: PASS / FAIL
  Gitleaks: PASS / FAIL

Suggested new items (requires your approval before adding to backlog):
  1. <suggestion>
  2. <suggestion>

To continue: paste this runner prompt into a new Claude Code session.
```

---

## Blocker Protocol

If at any point you are missing information needed to complete the item:

1. **Stop immediately.**
2. Do not guess. Do not make assumptions about files you haven't read.
3. Ask a **single, specific question** in this format:
   ```
   BLOCKER: <item ID>
   Question: <exact question>
   Options: <option A> | <option B> | <other: ...>
   ```

Do not ask multiple questions at once. Wait for the user's answer before proceeding.

---

## Token Discipline Protocol

- Do NOT call `brain/planner.py` (Claude LLM) unless the backlog item explicitly says "invoke Brain" or "LLM call".
- Do NOT load `data/health/health_data_cache.json` unless you need to inspect its schema.
- Do NOT run `coach plan --week` or any LLM planning command.
- Prefer `rg` (ripgrep via Grep tool) over reading entire files to verify callers.
- If a file exceeds 500 lines, read only the relevant sections using offset+limit.

---

## Stop Conditions

Stop and do nothing further if:

1. **All unblocked TODO items are done** — report this and wait for user to add more.
2. **Safety gate fails and you cannot fix it** — report the failure and wait for user.
3. **Blocker encountered** — ask the single blocker question and wait.
4. **The item's scope is larger than expected** (touching more than 3x the listed files) — stop, report the scope expansion, and ask user to confirm before proceeding.
5. **You have completed exactly 1 backlog item** — this is the normal stop condition.

---

## Architecture Quick Reference

(For context when implementing — do not modify these invariants)

**Sacred paths (never bypass):**
- All Garmin publishing: `skills/publish_to_garmin.py` only
- Health cache writes: `src/garmin_sync.py` only
- Skip gate: `data/generated_workouts.json` managed by `skills/publish_to_garmin.py` only

**Authoritative sources:**
- Training plan: `data/coach.sqlite` → `plans` + `plan_days`
- Health data: `data/health/health_data_cache.json` (migrating to SQLite `daily_metrics` + `activities`)
- Constraint calendars: optional input to Brain context; never plan-authoritative

**CLI is king:**
- All bot commands route through `python3 cli/coach.py <subcommand>` as subprocess
- `src/morning_report.py` is an exception (not yet migrated — see B11-016)
- Bot is a thin router; it does not contain business logic

**Memory OS:**
- SQLite at `data/coach.sqlite`
- Write via `memory/db.py` functions only
- Read via `skills/plans.py` (plan data) or direct sqlite3 for agent status

---

## Example Session

```
User: [pastes this prompt]

Claude: Reading docs/BACKLOG.md and docs/PHASE_11_AUDIT.md...

Next unblocked TODO item: B11-001 (Delete broken security tests) — Risk: L

Marking B11-001 as IN PROGRESS...

Risk is L, no safety gate required before changes.

Implementing: deleting tests/test_security.py (imports src.web.app which does not exist)...

Running post-implementation safety gates:
  pytest tests/: PASS (4 tests, 0 failures)
  gitleaks: PASS (no leaks)
  compileall: PASS

Updating BACKLOG.md: B11-001 → DONE

✓ Completed: B11-001 — Delete broken security tests
  Files changed: tests/test_security.py (deleted)
  Tests: PASS
  Gitleaks: PASS

Suggested new items (requires your approval):
  1. Add a test for src/config/logging_config.py SensitiveDataFilter (the only useful test logic from the deleted file)

To continue: paste this runner prompt into a new Claude Code session.
```
