# OpenClaw Migration Plan

## Why Migrate Now?

Existing ClawHub skills cover **60-70% of current functionality**, dramatically reducing migration effort.

## Architecture Comparison

### Current System
```
Discord Bot (UI/automation)
    ↓
Custom Python Scripts
    ↓
garminconnect library → Health Data Cache
    ↓
Claude Code headless → AI coaching
    ↓
FinalSurge ICS parsing → Workout generation
```

### Proposed OpenClaw System
```
Discord Bot (UI/automation) - KEEP
    ↓
OpenClaw Skills
    ├─ garmin-health-analysis (EXISTING - eversonl)
    ├─ caldav-calendar (EXISTING - Asleep123)
    ├─ vdot-running-coach (NEW - custom)
    ├─ strength-coach (NEW - custom)
    ├─ mobility-coach (NEW - custom)
    └─ nutrition-coach (NEW - custom)
    ↓
Claude with MCP → Coaching decisions
```

## Migration Strategy

### Phase 1: Leverage Existing Skills (Week 1-2)

**Use garmin-health-analysis skill:**
- ✅ Replace `src/garmin_sync.py`
- ✅ Replace `data/health/health_data_cache.json` (use skill queries instead)
- ✅ Natural language health queries
- ✅ Dashboard generation

**Use caldav-calendar skill:**
- ✅ Replace `src/ics_parser.py`
- ✅ Sync FinalSurge calendar via CalDAV
- ✅ Query scheduled workouts

**Keep as-is:**
- Discord bot (your UI)
- Systemd automation
- Morning report orchestration

### Phase 2: Build Custom Coaching Skills (Week 3-4)

**Create domain-specific skills:**

1. **vdot-running-coach** skill
   - Wrap your existing `.claude/agents/vdot-running-coach.md` logic
   - Use VDOT calculator from `src/vdot_calculator.py`
   - Query garmin-health-analysis for recovery data
   - Query caldav-calendar for scheduled workouts

2. **strength-coach** skill
   - Wrap `.claude/agents/runner-strength-coach.md`
   - Integrate with streprogen if still using

3. **mobility-coach** skill
   - Wrap `.claude/agents/mobility-coach-runner.md`

4. **nutrition-coach** skill
   - Wrap `.claude/agents/endurance-nutrition-coach.md`
   - Include gluten-free/dairy-free constraints

### Phase 3: Workout Generation (Week 5)

**Custom skill: workout-generator**
- Parse FinalSurge workout descriptions (keep `src/workout_parser.py` logic)
- Generate Garmin structured workouts
- Upload via Garmin Connect API
- Track generated workouts

**Challenge:** garmin-health-analysis may not support workout upload
- Check if skill supports write operations
- May need custom MCP server for upload
- Alternative: Keep `src/workout_uploader.py` as wrapper script

### Phase 4: Morning Report Automation (Week 6)

**Update `bin/morning_report.sh`:**
```bash
#!/bin/bash
# New approach: Discord bot calls OpenClaw skills

# Query health data via garmin-health-analysis skill
# Query scheduled workout via caldav-calendar skill
# Invoke vdot-running-coach skill with health + workout context
# Generate report
```

**Keep Discord bot scheduling** - OpenClaw doesn't replace automation

## What You Gain

### Immediate Benefits
1. **Less Code to Maintain**
   - Delete ~500 lines from `garmin_sync.py`
   - Delete ICS parsing code
   - Focus on coaching logic, not data plumbing

2. **Better Garmin Integration**
   - More metrics than your current system
   - Interactive dashboard
   - Natural language queries
   - Community maintained

3. **Standards-Based**
   - MCP protocol future-proof
   - Reusable skills
   - Better separation of concerns

4. **Community Benefits**
   - garmin-health-analysis gets updates from eversonl
   - Can contribute improvements back
   - Other skills appear on ClawHub

### Challenges to Solve

1. **Workout Upload**
   - garmin-health-analysis may be read-only
   - Need to verify write capabilities
   - Might need custom MCP server for upload

2. **Automation Layer**
   - OpenClaw skills are request/response
   - Still need Discord bot for scheduling
   - Still need systemd service

3. **Caching Strategy**
   - Your smart_sync.sh has intelligent caching
   - Need to understand garmin-health-analysis caching
   - May need wrapper for efficiency

4. **Personalization**
   - Generic skills need athlete context
   - Need to pass dietary restrictions, schedule constraints
   - May need context management system

## Validation Testing

Before full migration, test existing skills:

### Test garmin-health-analysis
```bash
# Can it fetch your data?
# Does it support all metrics you need?
# What's the query performance?
# Does it cache intelligently?
# Can it upload workouts?
```

### Test caldav-calendar
```bash
# Can it sync FinalSurge ICS feed?
# Does it handle constraint calendars (e.g. NurseGrid, custom ICS)?
# Can it query by date range?
```

### Test clawd-coach
```bash
# How good are training plans?
# Does it understand VDOT methodology?
# Can you customize for your philosophy?
```

## Decision Points

### Go/No-Go Criteria

**Proceed if:**
- ✅ garmin-health-analysis supports your core metrics
- ✅ Calendar sync works with FinalSurge
- ✅ You can maintain automation layer
- ✅ Migration effort < 2 weeks

**Abort if:**
- ❌ garmin-health-analysis missing critical metrics
- ❌ Can't upload workouts to Garmin
- ❌ Skills don't support your use case
- ❌ Performance/caching inadequate

## Rollback Plan

Maintain current system in parallel during migration:
- Keep all `src/*.py` files
- Keep Discord bot working with old code
- Test OpenClaw via separate Discord commands
- Switch over only when fully validated

## Next Steps

1. **Install and test existing skills** (this weekend)
2. **Document gaps** (what skills don't cover)
3. **Prototype one coaching skill** (vdot-running-coach)
4. **Evaluate effort vs benefit** (reassess after prototype)
5. **Decide:** full migration or hybrid approach

## Resources

- **ClawHub**: https://clawhub.ai
- **OpenClaw Docs**: https://docs.openclaw.ai
- **Existing Skills**:
  - garmin-health-analysis: https://clawhub.ai/eversonl/garmin-health-analysis
  - caldav-calendar: https://clawhub.ai/Asleep123/caldav-calendar
  - clawd-coach: https://clawhub.ai/shiv19/clawd-coach
