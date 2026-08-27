"""Small discord.py stand-in used only when the real package is unavailable in CI."""
import sys
import types

try:
    import discord  # noqa: F401
except ModuleNotFoundError:
    discord = types.ModuleType("discord")

    class Embed:
        def __init__(self, *, title=None, description=None):
            self.title = title
            self.description = description
            self.fields = []
            self.image = None

        def add_field(self, *, name, value, inline=False):
            self.fields.append({"name": name, "value": value, "inline": inline})

        def set_image(self, *, url):
            self.image = {"url": url}

    class ButtonStyle:
        success = 1
        danger = 2
        secondary = 3

    class Button:
        def __init__(self, *, label, style, custom_id, disabled=False):
            self.label = label
            self.style = style
            self.custom_id = custom_id
            self.disabled = disabled
            self.callback = None

    class View:
        def __init__(self, *, timeout=None):
            self.timeout = timeout
            self.children = []

        def add_item(self, item):
            self.children.append(item)

    class Intents:
        @classmethod
        def default(cls):
            return cls()

    class Forbidden(Exception):
        pass

    class HTTPException(Exception):
        pass

    ui = types.ModuleType("discord.ui")
    ui.View = View
    ui.Button = Button
    discord.ui = ui
    discord.Embed = Embed
    discord.ButtonStyle = ButtonStyle
    discord.Intents = Intents
    discord.Forbidden = Forbidden
    discord.HTTPException = HTTPException
    discord.Client = object
    discord.Interaction = object
    discord.Attachment = object
    discord.Role = object

    class AllowedMentions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        def none(cls):
            return cls(everyone=False, users=False, roles=False, replied_user=False)

    discord.AllowedMentions = AllowedMentions

    app_commands = types.ModuleType("discord.app_commands")

    def describe(**_kwargs):
        def deco(fn):
            return fn
        return deco

    class CommandTree:
        def command(self, **_kwargs):
            def deco(fn):
                return fn
            return deco

    app_commands.describe = describe
    app_commands.CommandTree = CommandTree
    discord.app_commands = app_commands

    ext = types.ModuleType("discord.ext")
    commands = types.ModuleType("discord.ext.commands")
    tasks = types.ModuleType("discord.ext.tasks")

    class Bot:
        def __init__(self, *args, **kwargs):
            self.tree = CommandTree()
            self.user = None

        def event(self, fn):
            return fn

        def run(self, _token):
            return None

    commands.Bot = Bot

    class Loop:
        def __init__(self, fn, seconds):
            self.fn = fn
            self.seconds = seconds
            self._running = False

        def start(self):
            self._running = True

        def is_running(self):
            return self._running

    def loop(*, seconds):
        def deco(fn):
            return Loop(fn, seconds)
        return deco

    tasks.loop = loop
    ext.commands = commands
    ext.tasks = tasks

    sys.modules["discord"] = discord
    sys.modules["discord.ui"] = ui
    sys.modules["discord.app_commands"] = app_commands
    sys.modules["discord.ext"] = ext
    sys.modules["discord.ext.commands"] = commands
    sys.modules["discord.ext.tasks"] = tasks
