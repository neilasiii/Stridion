# Schedule Constraints

## Personal Work Schedule

- **Employer:** In-office position, Mon-Thu, 0700-1730
- **Current Status:** On paid parental leave through January 5, 2026
- **Return to Work:** January 6, 2026
- **Fitness Time:** 3 hours/week of work-granted fitness time (typically morning sessions)
- **Preference:** Early morning workouts on workdays

## Spouse Work Schedule (Childcare Constraint)

**Wife's Employment:**
- Occupation: Registered Nurse
- Shift Type: 12-hour shifts (7:00 AM - 7:00 PM)
- Return Date: January 4, 2026 (after maternity leave)
- Schedule Source: NurseGrid ICS calendar (integrated into system)

**Impact on Training:**
- **Cannot workout on wife's work days** due to childcare responsibilities
- Must care for newborn during 12-hour shifts
- No morning or evening workout windows available on these days

**System Integration:**
- Wife's nursing schedule automatically synced via ICS feed
- Calendar type: `constraint` (vs `training`)
- Running workouts scheduled on wife's work days are **automatically rescheduled**
- Rescheduling logic:
  - Moves workout to another day in the same week (Mon-Sun)
  - Prefers nearby days (minimal disruption to weekly structure)
  - Avoids other constrained days
  - Adds detailed note explaining the reschedule

**Example Reschedule Note:**
```
--- RESCHEDULED ---
Originally scheduled: 2026-01-04
Moved to: 2026-01-03
Reason: Conflict with spouse work schedule (childcare needs)
---
```

## Workout Type Flexibility

**Inflexible (must reschedule):**
- Running workouts - require dedicated time blocks and specific conditions
- Cannot be easily shortened or moved to different time of day

**Flexible (can adapt):**
- Strength training - can be done in shorter blocks, at home
- Mobility work - can be done while caring for baby (floor exercises)
- These are NOT automatically rescheduled by the system

## Calendar Configuration

The system is configured in `config/calendar_sources.json`:

```json
{
  "calendar_urls": [
    {
      "name": "FinalSurge Training Calendar",
      "url": "https://log.finalsurge.com/delivery/ical/...",
      "enabled": true,
      "type": "training"
    },
    {
      "name": "Wife's Nursing Schedule",
      "url": "https://app.nursegrid.com/calendars/...",
      "enabled": true,
      "type": "constraint"
    }
  ]
}
```

## Future Considerations

As baby grows and childcare situation evolves:
- May be able to do shorter workouts during naps on constrained days
- May gain access to childcare options (grandparents, daycare)
- System can be easily updated by:
  - Disabling constraint calendar (`"enabled": false`)
  - Removing constraint calendar entirely
  - Updating calendar URL if schedule source changes

## Last Updated

- **Date:** December 27, 2025
- **Reason:** Wife starting back to work January 4, 2026 after maternity leave
