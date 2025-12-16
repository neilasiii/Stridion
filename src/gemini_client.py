#!/usr/bin/env python3
"""
Google Gemini API Client

Fallback AI provider for when Claude is unavailable due to outages or usage limits.
Uses the free tier of Google Gemini API.
"""

import os
import json
import subprocess
from pathlib import Path


def call_gemini(prompt, max_tokens=2048, temperature=0.7):
    """
    Call Google Gemini API with the given prompt.

    Args:
        prompt: The prompt to send to Gemini
        max_tokens: Maximum tokens in response (default 2048)
        temperature: Sampling temperature 0-1 (default 0.7)

    Returns:
        (response_text, error_message) - one will be None
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        # Try loading from config file
        project_root = Path(__file__).parent.parent
        env_file = project_root / "config" / "gemini_api.env"

        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line.startswith('GEMINI_API_KEY='):
                                api_key = line.split('=', 1)[1].strip()
                                break
            except Exception as e:
                return None, f"Failed to load API key from config: {e}"

    if not api_key:
        return None, "GEMINI_API_KEY not set (export GEMINI_API_KEY=your_key or add to config/gemini_api.env)"

    # Use curl to call Gemini API (generativelanguage.googleapis.com)
    # Endpoint: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent

    request_body = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
    }

    try:
        # Use gemini-2.0-flash for free tier (v1 API)
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}"

        result = subprocess.run(
            [
                'curl', '-s', '-X', 'POST',
                url,
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(request_body)
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return None, f"curl failed: {result.stderr[:200]}"

        # Parse response
        try:
            response_data = json.loads(result.stdout)

            # Check for error
            if 'error' in response_data:
                error_msg = response_data['error'].get('message', 'Unknown error')
                return None, f"Gemini API error: {error_msg}"

            # Extract text from response
            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        return parts[0]['text'].strip(), None

            return None, "No valid response from Gemini API"

        except json.JSONDecodeError as e:
            return None, f"Failed to parse Gemini response: {e}"

    except subprocess.TimeoutExpired:
        return None, "Gemini API request timed out after 60s"
    except Exception as e:
        return None, f"Unexpected error calling Gemini: {e}"


def test_gemini():
    """Test Gemini API connection."""
    print("Testing Gemini API...")
    response, error = call_gemini("Say 'Hello, I am Gemini!' and nothing else.", max_tokens=50)

    if error:
        print(f"❌ Error: {error}")
        return False
    else:
        print(f"✓ Success: {response}")
        return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        success = test_gemini()
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        prompt = input("Prompt: ")
        response, error = call_gemini(prompt)

        if error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)
        else:
            print(response)
