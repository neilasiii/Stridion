#!/usr/bin/env python3
"""
Claude Code headless streaming wrapper.

Provides real-time status updates when calling Claude in headless mode,
so users can see what Claude is working on instead of waiting for
the complete response.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Tuple


def call_claude_streaming(
    prompt: str,
    allowed_tools: Optional[str] = None,
    timeout: int = 180,
    status_callback: Optional[Callable[[str], None]] = None
) -> Tuple[str, Optional[str]]:
    """
    Call Claude Code in streaming mode with status updates.

    Args:
        prompt: The prompt to send to Claude
        allowed_tools: Tools to allow (e.g., "Bash(python3:*),Read,Grep,Glob")
        timeout: Timeout in seconds
        status_callback: Function to call with status updates (e.g., "Reading file...")

    Returns:
        (response_text, error) - error is None on success

    Example:
        def print_status(msg):
            print(f"[Status] {msg}")

        response, error = call_claude_streaming(
            "What's in goals.md?",
            status_callback=print_status
        )
    """
    # Find claude binary
    claude_path = None
    for path in [
        Path.home() / '.local' / 'bin' / 'claude',
        Path('/usr/local/bin/claude'),
        Path('/usr/bin/claude')
    ]:
        if path.exists():
            claude_path = str(path)
            break

    if not claude_path:
        return None, "Claude binary not found"

    # Build command
    args = [
        claude_path, '-p', prompt,
        '--output-format', 'stream-json',
        '--verbose'
    ]

    if allowed_tools:
        args.extend(['--allowedTools', allowed_tools])

    # Run with streaming output
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )

        final_response = None
        error = None

        # Process stream line by line
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)

                # Handle different message types
                if data.get('type') == 'system' and data.get('subtype') == 'init':
                    if status_callback:
                        status_callback("Claude session initialized")

                elif data.get('type') == 'assistant':
                    message = data.get('message', {})
                    content = message.get('content', [])

                    for item in content:
                        # Tool use
                        if item.get('type') == 'tool_use':
                            tool_name = item.get('name', 'Unknown')

                            # Provide user-friendly status
                            if tool_name == 'Read':
                                file_path = item.get('input', {}).get('file_path', '')
                                file_name = Path(file_path).name if file_path else 'file'
                                if status_callback:
                                    status_callback(f"Reading {file_name}...")

                            elif tool_name == 'Bash':
                                command = item.get('input', {}).get('command', '')
                                # Show first 50 chars of command
                                cmd_preview = command[:50] + ('...' if len(command) > 50 else '')
                                if status_callback:
                                    status_callback(f"Running: {cmd_preview}")

                            elif tool_name == 'Grep':
                                pattern = item.get('input', {}).get('pattern', '')
                                if status_callback:
                                    status_callback(f"Searching for: {pattern}")

                            elif tool_name == 'Glob':
                                pattern = item.get('input', {}).get('pattern', '')
                                if status_callback:
                                    status_callback(f"Finding files: {pattern}")

                            elif tool_name == 'Task':
                                agent = item.get('input', {}).get('subagent_type', 'agent')
                                if status_callback:
                                    status_callback(f"Launching {agent} agent...")

                            elif tool_name == 'WebSearch':
                                query = item.get('input', {}).get('query', '')
                                if status_callback:
                                    status_callback(f"Searching web: {query}")

                            elif tool_name == 'WebFetch':
                                url = item.get('input', {}).get('url', '')
                                if status_callback:
                                    status_callback(f"Fetching: {url}")

                            else:
                                if status_callback:
                                    status_callback(f"Using tool: {tool_name}")

                        # Text response (final answer)
                        elif item.get('type') == 'text':
                            text = item.get('text', '')
                            if text:
                                # Accumulate all text (may come in multiple parts)
                                if final_response:
                                    final_response += text
                                else:
                                    final_response = text
                                    if status_callback:
                                        status_callback("Generating response...")

                elif data.get('type') == 'result':
                    # Final result metadata
                    if status_callback:
                        duration = data.get('duration_ms', 0) / 1000
                        turns = data.get('num_turns', 0)
                        status_callback(f"Complete ({duration:.1f}s, {turns} turns)")

                    # Get final result text if we don't have it yet
                    if not final_response and 'result' in data:
                        final_response = data['result']

                    if data.get('is_error'):
                        error = "Claude returned an error"

            except json.JSONDecodeError:
                # Skip malformed lines
                continue

        # Wait for process to finish
        process.wait(timeout=timeout)

        if process.returncode != 0:
            stderr = process.stderr.read()
            return None, f"Claude exited with code {process.returncode}: {stderr}"

        return final_response, error

    except subprocess.TimeoutExpired:
        process.kill()
        return None, f"Claude timed out after {timeout}s"

    except Exception as e:
        return None, f"Error calling Claude: {e}"


def main():
    """Test the streaming wrapper."""
    def print_status(msg: str):
        print(f"🔄 {msg}", file=sys.stderr)

    if len(sys.argv) < 2:
        print("Usage: python3 claude_headless_stream.py <prompt>")
        sys.exit(1)

    prompt = sys.argv[1]

    print(f"Prompt: {prompt}\n", file=sys.stderr)

    response, error = call_claude_streaming(
        prompt=prompt,
        status_callback=print_status
    )

    print("\n" + "="*60 + "\n", file=sys.stderr)

    if error:
        print(f"❌ Error: {error}", file=sys.stderr)
        sys.exit(1)

    if response:
        print(response)
    else:
        print("No response received", file=sys.stderr)


if __name__ == '__main__':
    main()
