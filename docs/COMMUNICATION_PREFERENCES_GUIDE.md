# Communication Preferences Guide

## Quick Start

**Current Setting:** BRIEF mode (set in [data/athlete/communication_preferences.md](../data/athlete/communication_preferences.md))

All coaching agents will automatically adapt their response style based on your preference.

---

## Detail Level Options

### BRIEF Mode (Recommended for Daily Use)
**Best for:** Quick workout checks, daily training execution, time-constrained sessions

**What you get:**
- Workout schedules in compact format
- Just the essential information (time, intensity, paces)
- Minimal explanatory text
- Fast, scannable responses

**Examples:**

**Running:**
```
Tomorrow: 45 min E (10:00-11:10)
Tuesday: 15 min E warmup, 3x10 min T (8:35) w/ 2 min jog, 10 min E cooldown
```

**Strength:**
```
Monday: Goblet squat 3x8, RDL 3x8, Bulgarian split squat 2x8/leg, Plank 3x45s
```

**Mobility:**
```
Post-run: Hip circles 10/side, 90/90 stretch 60s/side, Calf stretch 45s/side
```

**Nutrition:**
```
Pre-run (2hrs): GF toast + almond butter
During (>90min): 30g carbs/hour
Post (30min): Recovery smoothie (banana + protein + GF oats)
```

---

### STANDARD Mode (Balanced)
**Best for:** Weekly planning sessions, understanding context, learning the system

**What you get:**
- Brief rationale for recommendations
- Short purpose statements
- Key recovery/scheduling considerations
- Balanced detail without overwhelming information

**Examples:**

**Running:**
```
Tomorrow: 45 min E (10:00-11:10) for recovery from yesterday's threshold work

Tuesday: Threshold Workout
- Warmup: 15 min E
- Main: 3 × 10 min T (8:35) with 2 min easy jog recovery
- Cooldown: 10 min E
- Purpose: Lactate threshold development, Phase 2 training
```

**Strength:**
```
Monday (heavier session, 48hrs before threshold run):
- Goblet squat 3x8 RPE7
- RDL 3x8 RPE7
- Bulgarian split squat 2x8/leg
- Core circuit
Purpose: Posterior chain strength development
```

---

### DETAILED Mode (Comprehensive)
**Best for:** Learning new workouts, planning training blocks, troubleshooting issues

**What you get:**
- Full physiological reasoning
- Multiple modification options (conservative/moderate/full)
- Environmental and scheduling considerations
- Complete warm-up/cool-down protocols
- Equipment alternatives
- Coordination notes across training domains

**Examples:**

**Running:**
```
Tomorrow: 45 min E (10:00-11:10 pace)

This easy run supports recovery from yesterday's threshold session. Keep HR below 145 bpm.
The conversational pace promotes blood flow for recovery while minimizing neuromuscular fatigue.
Avoid pushing pace - this is true recovery work.

Tuesday: Threshold Workout
- Warmup: 15 min E + 4 strides (20s relaxed acceleration)
- Main: 3 × 10 min T (8:35 pace, ~155-165 HR) with 2 min easy jog recovery
- Cooldown: 10 min E
- Total time: ~60 minutes

Purpose: Improve lactate clearance capacity and raise sustainable pace threshold.
This workout aligns with your Phase 2 (Early Quality) training. The 10-minute intervals
provide sufficient stimulus (30 min total at T) without excessive fatigue. Recovery jogs
allow HR to drop to 130-140 before the next rep.

Modification options if recovery is compromised:
- Conservative: 2 × 12 min T (same total time, less reps, easier mentally)
- Moderate: 3 × 8 min T (maintain rep structure, reduce duration)
- Full: As prescribed (only if sleep >7 hrs, RHR normal, feeling fresh)

Check RHR tomorrow morning. If elevated >3 bpm, consider the moderate option.
```

---

## How to Change Detail Level

### Method 1: Ask During Any Coaching Session
Simply request the change:
- "Switch to brief mode"
- "Give me detailed explanations for this workout"
- "Use standard detail level from now on"
- "Just give me the schedule, skip the explanations"

The coach will update your preference file and adapt immediately.

### Method 2: Edit the File Directly
Open [data/athlete/communication_preferences.md](../data/athlete/communication_preferences.md) and change line 3:

```markdown
## Detail Level: BRIEF
```

Change `BRIEF` to `STANDARD` or `DETAILED` as desired.

### Method 3: Request Different Detail for Specific Sessions
You can ask for more or less detail on a case-by-case basis without changing your default:
- "Give me the full detailed breakdown for this workout"
- "Just the quick version for today's plan"
- "Explain why I'm doing this workout" (even in BRIEF mode)

---

## Tips for Using Each Mode

### BRIEF Mode Tips
- Perfect for executing pre-planned training
- Great when you're short on time
- Ideal for familiar workout types
- If you need clarification, just ask - the coach will provide detail on request
- Works best when you understand the training philosophy

### STANDARD Mode Tips
- Good balance for most athletes
- Provides enough context to understand decisions
- Helps you learn the training system over time
- Sufficient detail for independent training execution

### DETAILED Mode Tips
- Use when learning new workout types
- Helpful when adjusting to new training phases
- Great for understanding the "why" behind programming
- Can be overwhelming for daily use - consider switching to BRIEF once familiar
- Excellent for planning multi-week training blocks

---

## Mixing Modes Strategically

**Recommended approach:**
- **Default to BRIEF** for daily training execution
- **Request STANDARD** for weekly planning sessions
- **Request DETAILED** when:
  - Starting a new training phase
  - Learning a new workout type
  - Troubleshooting performance issues
  - Planning race-specific training blocks

**Example workflow:**
```
Monday morning: "What's my workout today?" (BRIEF response)
Sunday planning: "Switch to standard mode - what's my week look like?" (STANDARD response)
New phase: "I'm starting race-specific training - give me the detailed breakdown" (DETAILED response)
```

---

## Agent-Specific Behaviors

All four coaching agents (running, strength, mobility, nutrition) respect the same detail level setting, but adapt it to their domain:

### Running Coach (BRIEF)
- Time, intensity, pace only
- No periodization explanations unless asked
- Assumes you understand E/M/T/I/R zones

### Strength Coach (BRIEF)
- Exercise, sets, reps, load guidance
- No movement cues unless needed for safety
- Assumes familiarity with exercises

### Mobility Coach (BRIEF)
- Exercise list with duration/reps
- No anatomical explanations
- Assumes you know the movements

### Nutrition Coach (BRIEF)
- Meal/snack timing and content
- No macro breakdowns or rationale
- Assumes you understand your dietary needs (GF/DF)

---

## FAQ

**Q: Will the coach be less helpful in BRIEF mode?**
A: No - the coach has the same knowledge and decision-making quality. BRIEF mode just reduces explanatory text. You can always ask follow-up questions for more detail.

**Q: Can I change modes mid-conversation?**
A: Yes! Just ask. The coach will adapt immediately.

**Q: Does this affect training plan quality?**
A: Not at all. Detail level only affects communication style, not the underlying training decisions.

**Q: What if I forget which mode I'm in?**
A: Check [data/athlete/communication_preferences.md](../data/athlete/communication_preferences.md) line 3, or just ask the coach.

**Q: Can different agents use different detail levels?**
A: Currently all agents share the same setting, but you can request different detail levels during specific sessions (e.g., "Give me brief strength workouts but detailed running workouts").

---

## Implementation Notes

- Setting persists across all coaching sessions
- Agents check preference file at start of each session
- Changes take effect immediately
- Default setting is BRIEF (optimized for daily use)
- You can override on a per-request basis without changing the default

---

**Last Updated:** 2025-11-17
