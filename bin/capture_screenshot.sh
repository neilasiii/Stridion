#!/bin/bash
#
# Capture screenshot of the Running Coach web interface
#
# This script starts the service and captures a screenshot using Chrome/Chromium
# in headless mode.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_FILE="$PROJECT_ROOT/docs/images/web-interface-screenshot.png"

# Check if service is running
check_service() {
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✓ Service is running"
        return 0
    else
        echo "✗ Service is not running"
        return 1
    fi
}

# Find Chrome/Chromium executable
find_chrome() {
    local chrome_paths=(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        "/Applications/Chromium.app/Contents/MacOS/Chromium"
        "google-chrome"
        "chromium"
        "chromium-browser"
    )

    for chrome in "${chrome_paths[@]}"; do
        if command -v "$chrome" &> /dev/null || [ -f "$chrome" ]; then
            echo "$chrome"
            return 0
        fi
    done

    return 1
}

echo "Running Coach Screenshot Capture"
echo "=================================="
echo ""

# Check if service is running
if ! check_service; then
    echo ""
    echo "Starting service..."
    cd "$PROJECT_ROOT"
    docker-compose up -d
    echo "Waiting for service to be ready..."
    sleep 10
fi

# Verify service is up
if ! check_service; then
    echo "Error: Service failed to start. Check docker-compose logs."
    exit 1
fi

# Find Chrome
echo ""
echo "Looking for Chrome/Chromium..."
if ! CHROME=$(find_chrome); then
    echo "Error: Chrome or Chromium not found."
    echo "Please install Chrome or Chromium, or take a manual screenshot."
    echo "See docs/SCREENSHOT_GUIDE.md for manual instructions."
    exit 1
fi

echo "Found: $CHROME"

# Create output directory
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Capture screenshot
echo ""
echo "Capturing screenshot..."

"$CHROME" --headless \
    --disable-gpu \
    --window-size=1400,900 \
    --screenshot="$OUTPUT_FILE" \
    http://localhost:5000

if [ -f "$OUTPUT_FILE" ]; then
    echo "✓ Screenshot saved to: $OUTPUT_FILE"
    echo ""
    echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"

    # Show image dimensions if 'file' command is available
    if command -v file &> /dev/null; then
        file "$OUTPUT_FILE" | grep -o '[0-9]* x [0-9]*' || true
    fi

    echo ""
    echo "Next steps:"
    echo "1. Review the screenshot: open $OUTPUT_FILE"
    echo "2. If you want a conversation visible, take a manual screenshot"
    echo "3. Commit the screenshot: git add $OUTPUT_FILE && git commit -m 'Add screenshot'"
else
    echo "Error: Screenshot was not created"
    exit 1
fi
