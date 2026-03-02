# AI Running Coach — From-Scratch Prompt

## What you're building

An AI that fully replaces a human running coach. Not a coaching assistant, not a chatbot with running knowledge — a coach. The distinction matters: a chatbot answers questions. A coach manages an athlete's development over months and years, makes decisions the athlete doesn't even know to ask about, and gets better at coaching this specific person the longer they work together.

---

## Start with what a coach actually does

Before writing any code, spend time understanding the job. A running coach does six things:

1. Builds a model of the athlete — fitness, history, psychology, lifestyle, how they respond to load
2. Sets a long-term plan grounded in physiology — not a generic template, a plan for this person's goal with this person's constraints
3. Prescribes daily training — the right workout for today given everything known about the athlete right now
4. Watches what actually happens — execution vs. prescription, trends over time, early warning signs
5. Adapts continuously — the plan on week 8 should look different from what was written on week 1, because the coach has learned
6. Communicates in the athlete's language — some athletes want data, some want encouragement, most want to feel heard

The system you build needs to do all six. If it only does 3, it's a workout generator. If it only does 1 and 3, it's a personalization layer. Only doing all six makes it a coach.

---

## The athlete model is the product

Everything else — the training plan, the daily workouts, the morning check-in, the race strategy — is downstream of the athlete model. The athlete model is what the system knows about this specific person. It has three levels:

**What the athlete tells you:** goals, injury history, schedule, experience, why they run. Collected once, updated when life changes.

**What the data shows:** fitness metrics, workout execution, sleep, recovery, trends. Updated continuously from wearable data and workout logs.

**What the system infers:** patterns that emerge from watching the athlete over time. This athlete tends to overcook easy days. This athlete's HRV is a reliable readiness signal at thresholds that differ from population norms. This athlete's tempo performance degrades significantly when weekly volume exceeds X. These insights are never written by a human — they're discovered by the system and updated as evidence accumulates.

The third level is where the value compounds. A coach who's worked with an athlete for a year knows things about them that aren't in any document. Your system should reach that state through observation, not through the athlete explaining themselves better.

---

## The methodology needs to be embedded, not referenced

Ground the system in Jack Daniels' VDOT methodology because it's quantitative, physiologically validated, and gives you training zones derived from a single fitness number. But understand it deeply: VDOT is a snapshot that should update from workout execution data, not just from races. Training zones are prescriptive targets, not fixed rules — when the athlete is fatigued, the zone boundaries shift. The training phases (base → quality → race-specific → taper) exist for physiological reasons that the system needs to understand well enough to explain and to deviate from intelligently when circumstances require.

The system should be able to defend every workout it prescribes. Not "the plan says tempo today" but "this is week 7, you've built the aerobic base over the last six weeks, your recent easy run HR trends suggest you're ready for threshold stimulus, and your next race is 9 weeks out — this is the right time to introduce tempo work."

---

## The feedback loop is the engine

Training adaptation happens through a cycle: stress → recovery → adaptation. The system needs to model this cycle in real time. That requires closing the loop on every workout:

**Before:** What is the athlete's readiness today? Given readiness, what modification (if any) to the planned workout?

**After:** What actually happened? Execution vs. prescription. Not just distance/pace/HR — subjective effort (RPE), how it felt, anything notable. This data should be captured with minimal friction (a brief conversational check-in, not a form).

**Between workouts:** What does the data say? Sleep, recovery, trends. The system is watching even when no conversation is happening.

**Weekly:** What did this week teach us? Adjust the athlete model. Adjust upcoming weeks if warranted. Surface anything the athlete needs to know.

The feedback loop is what separates a system that delivers a plan from one that coaches. Without it, you're just selling a template.

---

## The plan is a hypothesis, not a contract

Generate the training plan at the start of a cycle. But treat every week's plan as a working hypothesis about what the athlete needs. The system should be continuously asking: is reality matching the hypothesis? If the athlete is executing workouts significantly faster than prescribed with HR in control, the VDOT estimate may be stale. If recovery metrics are chronically suppressed, the load may be too high. If quality sessions are consistently falling short, something is wrong — fatigue, stress, pacing strategy, something.

When the hypothesis is wrong, update the plan. Propose changes, explain the reasoning, get confirmation, implement. Never silently drift. Never rigidly stick to a plan that reality has invalidated.

---

## Proactivity is not a feature, it's the job

The system should almost never wait to be asked. A morning check-in happens because the coach initiates it, not because the athlete remembered to open the app. A warning about load accumulation gets surfaced when the system detects it, not when the athlete asks "am I overtraining?" A plan adjustment gets proposed when the data warrants it, not when the athlete notices something feels off.

The interface should be conversational and low-friction. The athlete talks to their coach, not to a dashboard. The coach talks back in plain language, using data to support recommendations but never hiding behind it. If the system doesn't know something, it says so and explains what data would help it know.

---

## Design for the long game

The system compounds value over time. An athlete who has been using it for six months should get materially better coaching than in month one, because the athlete model is richer, the patterns are established, and the system has calibrated its recommendations against actual outcomes. Design every component with this in mind: data should accumulate, models should update, the system should get more precise about this specific athlete over time.

The inverse is also true: design for continuity across life changes. The athlete gets injured — the system adapts. The athlete has a baby — the system accounts for fragmented sleep and reduced training windows without being asked. The athlete's goal changes — the system rebuilds the plan. A human coach navigates these transitions naturally. Build a system that does the same.

---

## What you should not build

Do not build a workout generator with a chat interface. Do not build a plan template that personalizes based on an intake form. Do not build something that answers running questions. Those are all useful products. None of them is a coach.

The test is simple: after six months of use, does the system know this athlete better than it did on day one? Does it make better decisions? Does it catch things the athlete wouldn't have caught themselves? If not, you built a feature, not a coach.
