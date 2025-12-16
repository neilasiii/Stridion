#!/usr/bin/env python3
"""
Example: Using Claude streaming in Discord bot

Shows how to update Discord message with status while Claude is working.
This prevents the bot from appearing "hung up" during long operations.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_headless_stream import call_claude_streaming


async def ask_claude_with_status(ctx, prompt: str, allowed_tools: str = None):
    """
    Call Claude and update Discord message with status.

    Args:
        ctx: Discord context (has ctx.send and ctx.message.edit)
        prompt: Prompt to send to Claude
        allowed_tools: Tools to allow

    Example usage in Discord command:
        @bot.command()
        async def report(ctx):
            await ask_claude_with_status(ctx, "Generate morning report")
    """
    # Send initial status message
    status_msg = await ctx.send("🔄 Starting Claude...")

    last_status = ""

    def update_status(status: str):
        """Callback for status updates"""
        nonlocal last_status
        last_status = status

    # Start Claude in background with status callback
    response, error = call_claude_streaming(
        prompt=prompt,
        allowed_tools=allowed_tools,
        timeout=180,
        status_callback=update_status
    )

    # Delete status message
    await status_msg.delete()

    # Send final response
    if error:
        await ctx.send(f"❌ Error: {error}")
    elif response:
        # Split into chunks if needed (Discord 2000 char limit)
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send("No response received from Claude")


# Alternative: Update single message in place
async def ask_claude_with_inline_status(ctx, prompt: str, allowed_tools: str = None):
    """
    Call Claude and update the same message with status + final response.

    This is cleaner - single message that shows status then final answer.
    """
    # Send initial status message
    status_msg = await ctx.send("🔄 Starting Claude...")

    def update_status(status: str):
        """Update Discord message with current status"""
        try:
            # Update message asynchronously
            import asyncio
            asyncio.create_task(status_msg.edit(content=f"🔄 {status}"))
        except:
            pass  # Message might be deleted already

    # Call Claude
    response, error = call_claude_streaming(
        prompt=prompt,
        allowed_tools=allowed_tools,
        timeout=180,
        status_callback=update_status
    )

    # Update with final response
    if error:
        await status_msg.edit(content=f"❌ Error: {error}")
    elif response:
        # Update with final response (or send separate message if too long)
        if len(response) <= 1900:
            await status_msg.edit(content=response)
        else:
            await status_msg.delete()
            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            for chunk in chunks:
                await ctx.send(chunk)
    else:
        await status_msg.edit(content="No response received")


# Example usage in actual Discord bot command:
"""
@bot.command(name='ask')
async def ask_command(ctx, *, question: str):
    '''Ask Claude a question with status updates'''
    prompt = f'''
    Answer this question about the running coach system:
    {question}

    Be concise and helpful.
    '''
    await ask_claude_with_inline_status(ctx, prompt)


@bot.command(name='report')
async def report_command(ctx):
    '''Generate morning report with status updates'''
    # Build prompt with health data
    health_data = load_health_data()  # Your function
    prompt = build_morning_report_prompt(health_data)  # Your function

    await ask_claude_with_inline_status(
        ctx,
        prompt,
        allowed_tools="Read,Bash(python3:*)"
    )
"""
