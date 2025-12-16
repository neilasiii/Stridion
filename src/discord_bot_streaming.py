"""
Streaming version of Discord bot AI functions.

Replace the call_ai_with_fallback() function in discord_bot.py with this
to get real-time status updates.
"""

import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def call_ai_with_fallback_streaming(prompt, allowed_tools=None, timeout=180, status_callback=None):
    """
    Call Claude Code with streaming status updates and Gemini fallback.

    Args:
        prompt: The prompt to send
        allowed_tools: Tools to allow Claude to use (e.g., "Bash(python3:*),Read,Grep,Glob")
        timeout: Timeout in seconds
        status_callback: Function to call with status updates (e.g., async function to update Discord message)

    Returns:
        (response_text, provider) - provider is 'claude', 'gemini', or None on error

    Example usage in Discord command:
        status_msg = await ctx.send("🔄 Thinking...")

        def update_status(msg):
            asyncio.create_task(status_msg.edit(content=f"🔄 {msg}"))

        response, provider = call_ai_with_fallback_streaming(
            prompt=prompt,
            status_callback=update_status
        )
    """
    # Try Claude with streaming
    sys.path.insert(0, str(PROJECT_ROOT / 'src'))

    try:
        from claude_headless_stream import call_claude_streaming

        if status_callback:
            status_callback("Starting Claude...")

        response, error = call_claude_streaming(
            prompt=prompt,
            allowed_tools=allowed_tools,
            timeout=timeout,
            status_callback=status_callback
        )

        if response and not error:
            logger.info(f"[AI] Claude responded successfully (len={len(response)})")
            return response, 'claude'
        else:
            logger.warning(f"[AI] Claude failed: {error}")

    except Exception as e:
        logger.error(f"[AI] Claude exception: {e}")

    # Fallback to Gemini
    if status_callback:
        status_callback("Claude unavailable, trying Gemini...")

    try:
        from gemini_client import call_gemini

        response, error = call_gemini(prompt, max_tokens=4096)

        if error:
            logger.warning(f"[AI] Gemini failed: {error}")
            return None, None
        else:
            logger.info(f"[AI] Gemini responded (len={len(response)})")
            return response, 'gemini'

    except Exception as e:
        logger.error(f"[AI] Gemini exception: {e}")
        return None, None


# Example Discord command using streaming:
"""
@bot.command(name='ask')
async def ask_command(ctx, *, question: str):
    '''Ask the coach a question with live status updates'''

    # Create status message
    status_msg = await ctx.send("🔄 Thinking...")

    # Define status callback
    def update_status(msg: str):
        try:
            # Update Discord message (fire and forget)
            asyncio.create_task(status_msg.edit(content=f"🔄 {msg}"))
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")

    # Build prompt
    prompt = f'''
You are a running coach. Answer this question:

{question}

Be concise and helpful.
'''

    # Call AI with streaming
    response, provider = call_ai_with_fallback_streaming(
        prompt=prompt,
        allowed_tools="Read,Bash(python3:*),Grep,Glob",
        timeout=180,
        status_callback=update_status
    )

    # Delete status message
    await status_msg.delete()

    # Send response
    if response:
        color = discord.Color.green() if provider == 'claude' else discord.Color.blue()
        embed = discord.Embed(
            title="Coach Response",
            description=response[:4000],  # Discord limit
            color=color
        )
        embed.set_footer(text=f"Powered by {provider.title()}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ AI is currently unavailable. Please try again later.")


@bot.command(name='report')
async def report_command(ctx):
    '''Generate morning report with live status updates'''

    # Create status message
    status_msg = await ctx.send("🔄 Syncing health data...")

    # Define status callback
    import asyncio

    def update_status(msg: str):
        try:
            asyncio.create_task(status_msg.edit(content=f"🔄 {msg}"))
        except:
            pass

    # Sync data first
    result = subprocess.run(
        ['bash', 'bin/smart_sync.sh'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        timeout=60
    )

    # Load health data
    health_cache = PROJECT_ROOT / 'data' / 'health' / 'health_data_cache.json'
    with open(health_cache) as f:
        health_data = json.load(f)

    # Build prompt
    prompt = build_morning_report_prompt(health_data)  # Your existing function

    # Call AI with streaming
    response, provider = call_ai_with_fallback_streaming(
        prompt=prompt,
        allowed_tools="Read,Bash(python3:*)",
        timeout=180,
        status_callback=update_status
    )

    # Update with final response
    if response:
        if len(response) <= 1900:
            await status_msg.edit(content=response)
        else:
            await status_msg.delete()
            # Split into chunks
            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            for chunk in chunks:
                await ctx.send(chunk)
    else:
        await status_msg.edit(content="❌ Failed to generate report")
"""
