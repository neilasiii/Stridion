# Screenshot Guide

This guide explains how to capture a screenshot of the Running Coach web interface for the README.

## Quick Method (Browser Screenshot)

1. **Start the service**
   ```bash
   # Configure your AI provider first
   cp .env.example .env
   nano .env  # Add your API key

   # Start service
   docker-compose up -d
   ```

2. **Open the interface**
   ```
   http://localhost:5000
   ```

3. **Take a screenshot**
   - **macOS**: `Cmd + Shift + 4` then select the browser window
   - **Windows**: `Win + Shift + S` then select area
   - **Linux**: `Shift + PrtScn` then select area

4. **Save the screenshot**
   ```bash
   # Save as:
   docs/images/web-interface-screenshot.png

   # Recommended dimensions: 1200x800 or larger
   ```

5. **Optional: Have a sample conversation visible**
   - Type a query like "What should I run today?"
   - Wait for response to appear
   - Take screenshot showing the conversation

## Automated Screenshot (using Chrome/Chromium)

If you have Chrome or Chromium installed:

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install chromium-browser

# Or on macOS with Homebrew
brew install chromium

# Use the capture script
bash bin/capture_screenshot.sh
```

## What to Show in the Screenshot

**Good screenshot should include:**
- ✅ The header with "Running Coach Service" title
- ✅ The AI provider badge (showing which AI is being used)
- ✅ The agent selector dropdown
- ✅ At least one example query and response
- ✅ The input field at the bottom
- ✅ Clean, professional appearance

**Example conversation to show:**
```
User: "What should I run today?"
Coach: "Based on your current training phase and recent workouts,
       I recommend a 45-minute easy run at 10:00-11:10 pace..."
```

## Tips for Best Results

1. **Clean browser window** - Hide bookmarks bar, close unnecessary tabs
2. **Good lighting** - Make sure the screenshot is bright and readable
3. **Appropriate zoom** - Browser at 100% zoom (not zoomed in/out)
4. **Show functionality** - Have a conversation visible to demonstrate the chat interface
5. **Resolution** - Aim for at least 1200px wide for good clarity

## Alternative: Using Browser DevTools

Some browsers allow screenshots via DevTools:

**Chrome/Edge:**
1. Open DevTools (F12)
2. Press `Cmd/Ctrl + Shift + P`
3. Type "screenshot"
4. Select "Capture full size screenshot" or "Capture screenshot"

**Firefox:**
1. Open DevTools (F12)
2. Click the "..." menu
3. Select "Take a screenshot"
4. Choose "Save full page" or "Save visible"

## Optimizing the Screenshot

After capturing, you may want to:

```bash
# Resize if too large (using ImageMagick)
convert docs/images/web-interface-screenshot.png \
  -resize 1200x \
  docs/images/web-interface-screenshot-optimized.png

# Or compress (using pngquant)
pngquant --quality=80-95 docs/images/web-interface-screenshot.png
```

## Verify Screenshot is Included

After adding the screenshot, verify it appears in the README:

```bash
# View the README locally
open README.md  # macOS
xdg-open README.md  # Linux

# Or push to GitHub and view online
git add docs/images/web-interface-screenshot.png README.md
git commit -m "Add web interface screenshot"
git push
```
