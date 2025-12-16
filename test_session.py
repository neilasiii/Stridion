#!/usr/bin/env python3
"""Test if claude command supports --session-id flag with UUID."""

import subprocess
import os
import uuid

CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")
PROJECT_ROOT = "/home/coach/running-coach"

# Generate a proper UUID
session_id = str(uuid.uuid4())
print(f"Testing with UUID: {session_id}\n")

# Test 1: First message in session
print("=== Test 1: First Message ===")
result = subprocess.run(
    [
        CLAUDE_PATH, "-p", "My favorite color is purple. Please remember this.",
        "--session-id", session_id,
        "--allowedTools", "Read",
        "--output-format", "text"
    ],
    cwd=PROJECT_ROOT,
    capture_output=True,
    text=True,
    timeout=30
)

print("STDOUT:", result.stdout[:200] if result.stdout else "(empty)")
print("STDERR:", result.stderr[:200] if result.stderr else "(empty)")
print("Return Code:", result.returncode)

# Test 2: Second message in same session (should remember)
print("\n=== Test 2: Second Message (Same Session) ===")
result2 = subprocess.run(
    [
        CLAUDE_PATH, "-p", "What is my favorite color?",
        "--session-id", session_id,
        "--allowedTools", "Read",
        "--output-format", "text"
    ],
    cwd=PROJECT_ROOT,
    capture_output=True,
    text=True,
    timeout=30
)

print("STDOUT:", result2.stdout[:200] if result2.stdout else "(empty)")
print("STDERR:", result2.stderr[:200] if result2.stderr else "(empty)")
print("Return Code:", result2.returncode)
