"""
plugins/template_plugin.py
COPY THIS FILE to create a new plugin.

Steps
─────
1. Copy this file → plugins/my_feature.py
2. Rename the class and set  name = "MyFeature"
3. Write your logic inside process()
4. In main.py add:
       from plugins.my_feature import MyFeaturePlugin
       plugins.register(MyFeaturePlugin(settings))

That's all — no other files need changing.
"""

from plugins.plugin_manager import BasePlugin


class TemplatePlugin(BasePlugin):
    name   = "Template"
    visual = True   # set False if this plugin should NOT be toggled by V

    def __init__(self, settings):
        super().__init__(settings)
        # initialise your state here

    def process(self, frame, ctx):
        """
        frame   — current BGR numpy array (modify and return it)
        ctx     — dict with keys:
                    hand_data   HandData (primary hand)
                    gesture     GestureState
                    action      MouseAction
                    mouse       MouseController
                    _all_hands  list[HandData]  (both hands)
        """
        # --- your code here ---
        return frame
