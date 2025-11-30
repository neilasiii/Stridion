# Enhanced Morning Reports - Feature Summary

## What Was Built

Three complementary morning report formats to give you comprehensive daily training insights:

### 1. AI-Powered Brief Report (`bin/morning_report.sh`)
- **Already existed** - Uses Claude Code for intelligent recommendations
- Sends Termux notification with concise summary
- Includes "View Details" button to open full HTML report
- Perfect for automated cron jobs (0715 daily)

### 2. Enhanced Text Report (`bin/show_detailed_report.sh`)
**NEW** - Terminal-based dashboard with rich formatting

**Features:**
- Visual recovery indicators (✓ ⚡ ⚠️)
- Sleep quality score with hours
- RHR trend vs baseline (shows +/- elevation)
- Training readiness score with recovery hours needed
- Days since last hard effort
- Training load metrics (ATL/CTL/TSB) when available
- Weekly activity summary (last 7 days by type)
- Gear mileage alerts (shoes >350mi)
- Weather-adjusted pacing recommendations
- Heat/humidity compensations
- Optimal timing guidance (early AM, mid-day, etc.)
- Today's scheduled workout

**Example Output:**
```
════════════════════════════════════════════════════════════
MORNING TRAINING REPORT
Sunday, November 30, 2025
════════════════════════════════════════════════════════════

📊 RECOVERY STATUS
────────────────────────────────────────────────────────────
Sleep: 6.9h | Quality: 48/100 ⚠️
RHR: 44 bpm (-1.7 vs baseline) ✓
Last hard effort: 7 days ago

📈 TRAINING LOAD (7-Day Trend)
────────────────────────────────────────────────────────────
Acute Load (ATL): 45.2
Chronic Load (CTL): 52.8
Form (TSB): +7.6 - Good form (ready to perform)

Last 7 Days:
  RUNNING: 3 activities, 22.5mi, 3h15m
  STRENGTH: 2 activities, 45m
```

### 3. Enhanced HTML Report (`bin/view_morning_report.sh`)
**NEW** - Beautiful mobile-friendly dashboard

**Features:**
- Recovery status gauge (0-100 with color-coded indicator)
- Interactive 7-day activity chart (Chart.js bar chart)
- Training stress balance visualization
- Metric cards for key stats (sleep, RHR, training load)
- Today's workout in highlighted purple gradient card
- Weather conditions with 6-hour forecast
- Responsive design (works great on mobile)
- Gradient purple/blue theme
- Automatically opens in browser
- Saved to Downloads folder

**Visual Elements:**
- Animated gauge needle for recovery score
- Color-coded TSB indicator (blue/green/orange/red)
- Stacked bar chart for running vs other activities
- Clean card-based layout
- Professional typography and spacing

**Opening Method:**
- Uses `termux-share` (most reliable method in Termux)
- Report saved to Downloads folder at `~/storage/downloads/morning_report.html`
- Can be re-opened quickly with `bin/open_morning_report.sh`

## Usage

```bash
# Terminal report (quick check)
bash bin/show_detailed_report.sh

# HTML report (generate fresh and open)
bash bin/view_morning_report.sh

# HTML report (open existing without regenerating)
bash bin/open_morning_report.sh

# AI notification (automated/cron)
bash bin/morning_report.sh
```

## Files Created

**Python Scripts:**
- `src/generate_enhanced_report.py` - Terminal report generator
- `src/generate_enhanced_html.py` - HTML report generator

**Shell Scripts:**
- `bin/show_detailed_report.sh` - Terminal report wrapper
- `bin/view_morning_report.sh` - HTML report generator + opener (uses termux-share)
- `bin/open_morning_report.sh` - Quick opener for existing HTML report

**Documentation:**
- Updated `CLAUDE.md` with morning report details
- Updated `README.md` with usage examples and feature descriptions

## Key Improvements Over Basic Report

1. **Visual Indicators** - At-a-glance status symbols
2. **Training Load** - ATL/CTL/TSB metrics (when available from Garmin)
3. **Weather Integration** - Pace adjustments for conditions
4. **Weekly Summary** - 7-day activity breakdown
5. **Gear Tracking** - Shoe mileage alerts
6. **Better Recovery Assessment** - Multi-metric scoring
7. **Interactive Charts** - Visual training trends
8. **Mobile-Friendly** - HTML report works great on phone

## Technical Details

**Dependencies:**
- Chart.js CDN for interactive charts
- Termux API for location/notifications
- Open-Meteo API for weather data

**Data Sources:**
- `data/health/health_data_cache.json` - All metrics
- `src/get_weather.py` - Current conditions
- `data/athlete/current_training_status.md` - Training paces

**Recovery Score Calculation:**
- Sleep quality (30 points)
- RHR trend (30 points)
- Training readiness (40 points)
- Composite 0-100 score

**Weather Adjustments:**
- 80°F+ or 70%+ humidity: +30 sec/mi, early AM/evening recommended
- 70-79°F: +15 sec/mi
- Under 40°F: mid-day recommended
- UV >7: avoid midday

## Next Steps

Consider adding:
- Heart rate variability (HRV) trend visualization
- Body Battery tracking
- Stress level monitoring
- Multi-day TSB trend chart
- Export report as PDF option
- Voice summary via termux-tts-speak
