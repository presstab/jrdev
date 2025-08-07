#!/usr/bin/env bash
set -euo pipefail

# 1. Start Textual in the background
echo "Starting Textual server..."
textual serve "python3 src/jrdev/ui/tui/textual_ui.py" &
textual_pid=$!

# 2. Optional: Wait a moment to let the server initialize
echo "Waiting for Textual server to become available..."
sleep 2

# 3. Run Playwright script
echo "Running Playwright script..."
python3 playwright_script.py
playwright_exit=$?

# 4. Clean up: kill the Textual server
echo "Stopping Textual server (PID $textual_pid)..."
kill "$textual_pid" 2>/dev/null || true

exit "$playwright_exit"
