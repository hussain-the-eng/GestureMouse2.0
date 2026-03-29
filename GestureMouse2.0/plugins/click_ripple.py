"""
plugins/click_ripple.py
Draws an expanding, fading ring at the fingertip on each click.
Left click  → cyan ring
Right click → purple ring
"""

import cv2
from plugins.plugin_manager import BasePlugin


class ClickRipplePlugin(BasePlugin):
    name   = "ClickRipple"
    visual = True

    def __init__(self, settings):
        super().__init__(settings)
        self._ripples = []   # each entry: [x, y, radius, max_radius, colour]

    def process(self, frame, ctx):
        action = ctx.get("action")
        hd     = ctx.get("hand_data")

        # Spawn new ripples on click
        if action and hd and hd.detected:
            h, w = frame.shape[:2]
            px   = int(hd.index_tip[0] * w)
            py   = int(hd.index_tip[1] * h)
            if action.left_click:
                self._ripples.append([px, py, 2, 44, (0, 220, 255)])
            if action.right_click:
                self._ripples.append([px, py, 2, 44, (180, 60, 255)])

        # Draw and advance all active ripples
        live = []
        for r in self._ripples:
            x, y, rad, max_r, col = r
            if rad < max_r:
                alpha  = 1.0 - rad / max_r
                colour = tuple(int(v * alpha) for v in col)
                cv2.circle(frame, (x, y), rad, colour, 2, cv2.LINE_AA)
                r[2] += 3
                live.append(r)
        self._ripples = live

        return frame
