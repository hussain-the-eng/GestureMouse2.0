"""
plugins/trail_effect.py
Draws a fading gradient trail behind the index fingertip.
Trail length is controlled by settings.TRAIL_LENGTH.
"""

import cv2
from collections import deque
from plugins.plugin_manager import BasePlugin


class TrailEffectPlugin(BasePlugin):
    name   = "TrailEffect"
    visual = True

    def __init__(self, settings):
        super().__init__(settings)
        self._trail = deque(maxlen=settings.TRAIL_LENGTH)

    def process(self, frame, ctx):
        hd = ctx.get("hand_data")
        if not (hd and hd.detected):
            return frame

        h, w = frame.shape[:2]
        px   = int(hd.index_tip[0] * w)
        py   = int(hd.index_tip[1] * h)
        self._trail.append((px, py))

        pts = list(self._trail)
        n   = len(pts)
        for i in range(1, n):
            alpha  = i / n
            colour = (
                int(255 * alpha),       # B
                int(100 * alpha),       # G
                int(50  * (1 - alpha)), # R
            )
            thickness = max(1, int(alpha * 4))
            cv2.line(frame, pts[i - 1], pts[i], colour, thickness, cv2.LINE_AA)

        return frame
