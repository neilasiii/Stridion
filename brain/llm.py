"""
brain/llm.py — Unified LLM calling and JSON extraction for the brain subsystem.

All LLM calls from brain/, hooks/, and src/ modules should import from here
rather than implementing their own subprocess/fallback logic.

Public API:
    call_llm(system, user, *, timeout=120, model=None) -> str
    _try_strict_extract(text) -> str | None
    _brace_search_last(text) -> str
    _JSON_FENCE_RE
"""

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger("brain.llm")

# ── LLM config ─────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048

# ── Shared LLM prompt constants ─────────────────────────────────────────────────

FIX_JSON_PROMPT = (
    "The JSON you returned failed schema validation. "
    "Return ONLY a corrected JSON object. No explanation. No markdown. "
    "Error: {error}"
)
CLAUDE_PATHS = [
    Path.home() / ".local" / "bin" / "claude",
    Path("/usr/local/bin/claude"),
    Path("/usr/bin/claude"),
]

PROJECT_ROOT = Path(__file__).parent.parent


# ── Claude discovery ────────────────────────────────────────────────────────────

def _find_claude() -> Optional[str]:
    path_hit = shutil.which("claude")
    if path_hit:
        return path_hit
    for p in CLAUDE_PATHS:
        if p.exists():
            return str(p)
    return None


# ── Primary LLM call ────────────────────────────────────────────────────────────

def call_llm(
    system: str, user: str, *, timeout: int = 120, model: Optional[str] = None
) -> str:
    """
    Call Claude CLI in headless mode. Returns raw text output.
    Raises RuntimeError on non-zero exit or empty response.

    Args:
        system: System prompt passed to the model.
        user: User prompt (the actual request).
        timeout: Subprocess timeout in seconds.
        model: Optional model alias or full ID (e.g. "haiku", "sonnet",
               "claude-haiku-4-5-20251001"). When None, the CLI uses its
               default model (currently Sonnet 4.6).

    SDK fallback is opt-in: set BRAIN_ALLOW_SDK_FALLBACK=1 to enable.
    When set, the SDK is used directly (bypassing the CLI entirely).
    Useful when running inside a Claude Code session where nested CLI
    calls are blocked.
    """
    if os.environ.get("BRAIN_ALLOW_SDK_FALLBACK") == "1":
        return _call_anthropic_sdk(system, user, model=model)

    claude = _find_claude()
    if claude is None:
        raise RuntimeError(
            "claude CLI not found. Searched:\n  "
            + "\n  ".join(str(p) for p in CLAUDE_PATHS)
            + "\nFix: install claude CLI at one of the above paths, "
            "or set BRAIN_ALLOW_SDK_FALLBACK=1 to enable the anthropic SDK fallback."
        )

    full_prompt = f"{system}\n\n{user}"
    log.debug(
        "Calling claude CLI, prompt_len=%d chars, model=%s",
        len(full_prompt),
        model or "default",
    )

    # Strip CLAUDECODE so the subprocess is not treated as a nested session.
    # This is the documented bypass: the child process is headless/one-shot
    # and does not share interactive state with the parent session.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    cmd = [claude, "-p", full_prompt, "--output-format", "text"]
    if model:
        cmd += ["--model", model]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude CLI timed out after {timeout}s")

    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited {result.returncode}: {result.stderr[:300]}"
        )

    text = result.stdout.strip()
    if not text:
        raise RuntimeError("claude CLI returned empty response")

    log.debug("LLM response_len=%d chars", len(text))
    return text


def _call_anthropic_sdk(system: str, user: str, model: Optional[str] = None) -> str:
    """Fallback LLM call: tries anthropic SDK first, then Gemini."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            import anthropic  # type: ignore

            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=model or MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text
        except Exception as e:
            log.warning("anthropic SDK call failed (%s), trying Gemini", e)

    # Gemini fallback
    return _call_gemini(system, user)


def _call_gemini(system: str, user: str) -> str:
    """Call Gemini API using the project's configured key."""
    import urllib.request as _req
    import urllib.error as _uerr

    gemini_env = PROJECT_ROOT / "config" / "gemini_api.env"
    gemini_key = ""
    if gemini_env.exists():
        for line in gemini_env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                gemini_key = line.split("=", 1)[1].strip()
    gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY", "")
    if not gemini_key:
        raise RuntimeError(
            "No LLM backend available: no ANTHROPIC_API_KEY and no GEMINI_API_KEY"
        )

    import json as _json

    url = (
        f"https://generativelanguage.googleapis.com/v1/models/"
        f"gemini-2.0-flash:generateContent?key={gemini_key}"
    )
    # v1 API does not support system_instruction — prepend system as context
    combined = f"{system}\n\n{user}"
    payload = _json.dumps(
        {
            "contents": [{"parts": [{"text": combined}]}],
            "generationConfig": {"maxOutputTokens": 4096},
        }
    ).encode()
    request = _req.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with _req.urlopen(request, timeout=120) as resp:
            data = _json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except _uerr.HTTPError as e:
        raise RuntimeError(f"Gemini API error {e.code}: {e.read()[:300]}")


# ── JSON extraction ─────────────────────────────────────────────────────────────

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```$", re.MULTILINE)


def _try_strict_extract(text: str) -> Optional[str]:
    """
    Strict extraction: strip fences, then accept ONLY if the result starts
    with '{' and ends with '}'. Returns None if the output is not clean JSON.
    """
    s = _JSON_FENCE_RE.sub("", text).strip()
    if s.startswith("{") and s.endswith("}"):
        return s
    return None


def _brace_search_last(text: str) -> str:
    """
    Last-resort extraction: find the LAST top-level balanced JSON object.

    Scans BACKWARD from the last '}' to its matching '{'.  This correctly
    handles nested braces (rfind('{') would land inside a nested object and
    return a fragment, not the root object).

    Raises ValueError if no balanced object is found.
    """
    last_close = text.rfind("}")
    if last_close == -1:
        raise ValueError(f"No JSON object found in output:\n{text[:300]}")
    depth = 0
    for i in range(last_close, -1, -1):
        ch = text[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                return text[i : last_close + 1]
    raise ValueError(f"Unbalanced JSON braces in output:\n{text[:300]}")


# ── Public Gemini shim (drop-in replacement for gemini_client.call_gemini) ────

def call_gemini(
    prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> "tuple[Optional[str], Optional[str]]":
    """
    Public wrapper around _call_gemini with the same interface as the old
    gemini_client.call_gemini: returns (response_text, None) on success,
    (None, error_message) on failure.

    Import from here instead of src/gemini_client:
        from brain.llm import call_gemini
    """
    try:
        text = _call_gemini("", prompt)
        return text, None
    except Exception as exc:
        return None, str(exc)
