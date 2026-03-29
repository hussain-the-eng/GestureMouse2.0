"""
plugins/plugin_manager.py
BasePlugin interface and PluginManager registry.

Every plugin must:
  1. Inherit BasePlugin
  2. Set a unique  name  string
  3. Implement    process(frame, ctx) -> frame

The ctx dict contains:
  ctx["hand_data"]    HandData  — primary (first) hand
  ctx["gesture"]      GestureState
  ctx["action"]       MouseAction
  ctx["mouse"]        MouseController
  ctx["_all_hands"]   list[HandData]  — both hands (for DrawingBoard etc.)
"""


class BasePlugin:
    name    = "Base"
    enabled = True
    visual  = True   # False = not toggled by V key

    def __init__(self, settings):
        self.settings = settings

    def process(self, frame, ctx):
        """Override this. Must return the (modified) frame."""
        return frame


class PluginManager:
    def __init__(self, settings):
        self.settings  = settings
        self._plugins  = []

    def register(self, plugin: BasePlugin):
        self._plugins.append(plugin)

    def run(self, frame, ctx):
        for plugin in self._plugins:
            if plugin.enabled:
                frame = plugin.process(frame, ctx)
        return frame

    def toggle_visuals(self):
        """Toggle all plugins whose visual flag is True."""
        for plugin in self._plugins:
            if plugin.visual:
                plugin.enabled = not plugin.enabled
