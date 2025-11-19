# Screenshots

This directory contains screenshots and images for documentation.

## Adding the Web Interface Screenshot

To add a screenshot of the Running Coach web interface:

### Option 1: Automated Capture (Recommended)

```bash
# From the project root
bash bin/capture_screenshot.sh
```

This will:
1. Start the service if not running
2. Capture a screenshot using Chrome/Chromium
3. Save it as `web-interface-screenshot.png`

### Option 2: Manual Capture

1. **Start the service**
   ```bash
   cp .env.example .env
   nano .env  # Add your API key
   docker-compose up -d
   ```

2. **Open http://localhost:5000 in your browser**

3. **Have a sample conversation**
   - Type: "What should I run today?"
   - Wait for the coach's response

4. **Take a screenshot**
   - macOS: `Cmd + Shift + 4`
   - Windows: `Win + Shift + S`
   - Linux: `Shift + PrtScn`

5. **Save as `web-interface-screenshot.png` in this directory**

### Screenshot Guidelines

**Good screenshot should include:**
- Header with "Running Coach Service" title
- AI provider badge
- Agent selector dropdown
- Example conversation (user query + coach response)
- Input field at bottom

**Recommended:**
- Dimensions: 1200x800 or larger
- Browser at 100% zoom
- Clean window (no browser UI clutter)
- Bright, readable text

See [SCREENSHOT_GUIDE.md](../SCREENSHOT_GUIDE.md) for detailed instructions.

## Current Images

- `web-interface-screenshot.png` - Main web interface (placeholder - needs to be captured)
