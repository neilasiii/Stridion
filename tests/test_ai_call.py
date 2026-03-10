#!/usr/bin/env python3
"""Test AI call exactly as Discord bot does it"""

import subprocess
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"CLAUDE_PATH: {CLAUDE_PATH}")
print(f"CLAUDE exists: {os.path.exists(CLAUDE_PATH)}")

prompt = "What is 2+2?"
allowed_tools = "Bash(python3:*),Read,Grep,Glob"

print(f"\nTesting Claude...")
if os.path.exists(CLAUDE_PATH):
    try:
        args = [
            CLAUDE_PATH, '-p', prompt,
            '--output-format', 'text'
        ]

        if allowed_tools:
            args.extend(['--allowedTools', allowed_tools])

        print(f"Running: {' '.join(args)}")

        result = subprocess.run(
            args,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=180
        )

        print(f"Return code: {result.returncode}")
        print(f"Stdout length: {len(result.stdout)}")
        print(f"Stdout (first 500 chars): {result.stdout[:500]}")
        print(f"Stderr: {result.stderr[:500] if result.stderr else 'None'}")

        if result.returncode == 0 and result.stdout.strip():
            print("\n✓ Claude would succeed")
        else:
            print(f"\n✗ Claude would FAIL - returncode={result.returncode}, stdout_empty={not result.stdout.strip()}")

    except Exception as e:
        print(f"\n✗ Claude exception: {e}")
else:
    print("\n✗ Claude path doesn't exist")

# Test Gemini
print("\n\nTesting Gemini...")
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
try:
    from brain.llm import call_gemini
    response, error = call_gemini(prompt, max_tokens=4096)

    if error:
        print(f"✗ Gemini would FAIL: {error}")
    else:
        print(f"✓ Gemini would succeed: {response[:100]}")
except Exception as e:
    print(f"✗ Gemini exception: {e}")
