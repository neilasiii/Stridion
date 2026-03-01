"""Unit tests for Discord mobile formatting helpers."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Comprehensive discord stub so we can import src/discord_bot.py helpers
# without a real bot token or installed discord.py.
# ---------------------------------------------------------------------------
import types


# ---- tasks.loop stub ----
# discord.py tasks.loop() returns a decorator; the decorated function becomes
# a Loop object with .before_loop, .after_loop, .start(), .stop(), .cancel().
class _Loop:
    """Minimal stub for discord.ext.tasks.Loop."""
    def __init__(self, fn):
        self._fn = fn
        self.__name__ = getattr(fn, "__name__", "loop")

    # Allow the loop itself to be used as a decorator on before/after hooks
    def before_loop(self, fn):
        return fn

    def after_loop(self, fn):
        return fn

    def start(self, *a, **kw):
        pass

    def stop(self):
        pass

    def cancel(self):
        pass

    def __call__(self, *a, **kw):
        pass


def _tasks_loop(*a, **kw):
    """Simulate tasks.loop(): returns a decorator that wraps fn in _Loop."""
    def decorator(fn):
        return _Loop(fn)
    return decorator


# ---- app_commands.describe stub ----
def _describe(**kw):
    def decorator(fn):
        return fn
    return decorator


# ---- discord.Color ----
class _Color:
    @staticmethod
    def blue(): return "blue"
    @staticmethod
    def green(): return "green"
    @staticmethod
    def red(): return "red"
    @staticmethod
    def orange(): return "orange"
    @staticmethod
    def purple(): return "purple"
    @staticmethod
    def yellow(): return "yellow"
    @staticmethod
    def blurple(): return "blurple"


# ---- discord.Embed ----
class _Embed:
    def __init__(self, title="", description="", color=None, timestamp=None):
        self.title = title
        self.description = description
        self.color = color
        self.timestamp = timestamp


# ---- discord.Intents ----
class _Intents:
    def __init__(self):
        self.message_content = True

    @staticmethod
    def default():
        return _Intents()


# ---- app_commands tree stub ----
class _AppCommandsTree:
    def command(self, *a, **kw):
        def decorator(fn):
            return fn
        return decorator


# ---- commands.Bot ----
class _Bot:
    def __init__(self, command_prefix="!", intents=None):
        self.tree = _AppCommandsTree()
        self.user = None

    def event(self, fn):
        return fn


# ---- commands module ----
_commands_mod = types.SimpleNamespace()
_commands_mod.Bot = _Bot

# ---- tasks module ----
_tasks_mod = types.SimpleNamespace()
_tasks_mod.loop = _tasks_loop

# ---- app_commands module ----
_app_commands_mod = types.SimpleNamespace()
_app_commands_mod.describe = _describe

# ---- discord.ext ----
_ext_mod = types.SimpleNamespace()
_ext_mod.commands = _commands_mod
_ext_mod.tasks = _tasks_mod

# ---- discord root ----
_discord_mod = types.SimpleNamespace()
_discord_mod.Color = _Color
_discord_mod.Embed = _Embed
_discord_mod.Intents = _Intents
_discord_mod.Interaction = object
_discord_mod.Message = object
_discord_mod.Object = object
_discord_mod.LoginFailure = Exception
_discord_mod.app_commands = _app_commands_mod
_discord_mod.ext = _ext_mod

# Register all stubs before any import of discord_bot
sys.modules["discord"] = _discord_mod
sys.modules["discord.ext"] = _ext_mod
sys.modules["discord.ext.commands"] = _commands_mod
sys.modules["discord.ext.tasks"] = _tasks_mod
sys.modules["discord.app_commands"] = _app_commands_mod

# Now import the helpers
from src.discord_bot import split_embeds, bullet_fields, MOBILE_DESC_LIMIT


class TestSplitEmbeds:
    def test_short_content_returns_single_embed(self):
        embeds = split_embeds("Hello world", "Title", "blue")
        assert len(embeds) == 1
        assert embeds[0].title == "Title"
        assert embeds[0].description == "Hello world"

    def test_long_content_splits_at_paragraph_boundary(self):
        chunk = "x" * 600
        content = chunk + "\n\n" + chunk  # two 600-char paras = 1202 chars total
        embeds = split_embeds(content, "Title", "blue", chunk_size=1200)
        assert len(embeds) == 2
        assert embeds[0].title == "Title"
        assert embeds[1].title == ""  # continuation embeds have no title

    def test_only_first_embed_has_title(self):
        content = "\n\n".join(["word " * 100] * 5)
        embeds = split_embeds(content, "MyTitle", "blue", chunk_size=300)
        assert embeds[0].title == "MyTitle"
        for embed in embeds[1:]:
            assert embed.title == ""

    def test_empty_content_returns_one_embed(self):
        embeds = split_embeds("", "Title", "blue")
        assert len(embeds) == 1

    def test_each_embed_under_chunk_size(self):
        content = " ".join(["word"] * 2000)
        embeds = split_embeds(content, "T", "blue", chunk_size=500)
        for embed in embeds:
            assert len(embed.description) <= 500

    def test_oversized_paragraph_no_sentence_boundary(self):
        # A single paragraph with no ". " -- should not exceed chunk_size
        content = "x" * 2000  # no periods, no paragraph breaks
        embeds = split_embeds(content, "T", "blue", chunk_size=500)
        for embed in embeds:
            assert len(embed.description) <= 500


class TestBulletFields:
    def test_basic_formatting(self):
        result = bullet_fields([("\U0001f634", "Sleep", "78/100"), ("\U0001f50b", "Battery", "62%")])
        assert result == "\U0001f634 Sleep: 78/100\n\U0001f50b Battery: 62%"

    def test_na_value_shows_dash(self):
        result = bullet_fields([("\u2764\ufe0f", "RHR", "N/A")])
        assert result == "\u2764\ufe0f RHR: \u2014"

    def test_none_value_shows_dash(self):
        result = bullet_fields([("\U0001f4c8", "HRV", None)])
        assert result == "\U0001f4c8 HRV: \u2014"

    def test_empty_list(self):
        result = bullet_fields([])
        assert result == ""
