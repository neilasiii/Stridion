# Claude Code Streaming Status Updates

When calling Claude in headless mode, it can take several minutes to complete complex tasks. Without status updates, it appears "hung up" even though it's actively working.

## Problem

Current non-streaming approach:
```python
result = subprocess.run(['claude', '-p', prompt, '--output-format', 'text'])
# ⏳ Blocks for 2-5 minutes with no feedback
# User thinks: "Is it frozen? Should I kill it?"
```

## Solution: Streaming with Status Updates

Use `--output-format stream-json --verbose` to get real-time updates:

```python
from claude_headless_stream import call_claude_streaming

def print_status(msg):
    print(f"🔄 {msg}")

response, error = call_claude_streaming(
    prompt="Generate morning report",
    status_callback=print_status
)

# Output:
# 🔄 Claude session initialized
# 🔄 Reading health_data_cache.json...
# 🔄 Running: python3 src/vdot_calculator.py...
# 🔄 Searching for: scheduled_workouts
# 🔄 Generating response...
# 🔄 Complete (47.3s, 4 turns)
```

## Status Updates Provided

The streaming wrapper automatically shows:

| Tool | Status Message |
|------|----------------|
| **Read** | `Reading <filename>...` |
| **Bash** | `Running: <command preview>` |
| **Grep** | `Searching for: <pattern>` |
| **Glob** | `Finding files: <pattern>` |
| **Task** | `Launching <agent> agent...` |
| **WebSearch** | `Searching web: <query>` |
| **WebFetch** | `Fetching: <url>` |
| Other tools | `Using tool: <name>` |
| Final | `Complete (<duration>s, <turns> turns)` |

## Discord Bot Integration

### Basic Usage

```python
from claude_headless_stream import call_claude_streaming

@bot.command(name='ask')
async def ask(ctx, *, question: str):
    # Send initial status
    status_msg = await ctx.send("🔄 Thinking...")

    def update_status(status: str):
        # Update Discord message
        asyncio.create_task(status_msg.edit(content=f"🔄 {status}"))

    # Call Claude with streaming
    response, error = call_claude_streaming(
        prompt=question,
        status_callback=update_status
    )

    # Show final response
    if error:
        await status_msg.edit(content=f"❌ {error}")
    else:
        await status_msg.edit(content=response)
```

### Advanced: Multiple Status Messages

For long operations, you can send multiple status updates instead of editing:

```python
async def ask_with_progress(ctx, prompt):
    last_update = time.time()

    async def status_callback(status: str):
        nonlocal last_update
        # Only send update every 5 seconds
        if time.time() - last_update > 5:
            await ctx.send(f"🔄 {status}")
            last_update = time.time()

    response, error = call_claude_streaming(
        prompt=prompt,
        status_callback=status_callback
    )

    return response, error
```

## Standalone CLI Usage

You can also use the streaming wrapper directly from command line:

```bash
python3 src/claude_headless_stream.py "What's today's workout?"

# Output:
# 🔄 Claude session initialized
# 🔄 Reading health_data_cache.json...
# 🔄 Generating response...
# 🔄 Complete (12.4s, 2 turns)
#
# Today's workout is an easy 30-45 minute run...
```

## Benefits

1. **User Confidence** - Shows Claude is actively working, not frozen
2. **Progress Tracking** - See which files/tools Claude is using
3. **Debugging** - Identify slow operations (e.g., "why is this taking so long?")
4. **Better UX** - Real-time feedback instead of multi-minute silence

## Technical Details

### Stream Format

Claude's `--output-format stream-json` outputs JSONL (JSON Lines):

```json
{"type":"system","subtype":"init",...}
{"type":"assistant","content":[{"type":"tool_use","name":"Read",...}]}
{"type":"user","content":[{"type":"tool_result",...}]}
{"type":"assistant","content":[{"type":"text","text":"Final answer"}]}
{"type":"result","subtype":"success","duration_ms":12450,...}
```

Each line is parsed to extract:
- Tool calls (show status)
- Text responses (accumulate)
- Final result (show duration/cost)

### Performance

Streaming adds **no overhead** - you get the same response at the same time, just with progress updates along the way.

### Timeout Handling

Default timeout is 180 seconds (3 minutes). For long operations:

```python
response, error = call_claude_streaming(
    prompt=prompt,
    timeout=300,  # 5 minutes
    status_callback=print_status
)
```

## Migration from Non-Streaming

### Before (blocking with no feedback):

```python
result = subprocess.run(
    ['claude', '-p', prompt, '--output-format', 'text'],
    capture_output=True,
    text=True,
    timeout=180
)
response = result.stdout.strip()
```

### After (streaming with status):

```python
from claude_headless_stream import call_claude_streaming

response, error = call_claude_streaming(
    prompt=prompt,
    status_callback=lambda msg: print(f"Status: {msg}")
)
```

## See Also

- `src/claude_headless_stream.py` - Implementation
- `examples/discord_streaming_example.py` - Discord bot integration
- Claude Code docs: `claude --help`
