"""
plugins/hand_visualizer.py
Draws the hand skeleton and landmark dots for every detected hand.
Right hand → cyan  |  Left hand → green
"""

import cv2
from plugins.plugin_manager import BasePlugin

# MediaPipe hand connections
_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17),
]

_TIPS = {4, 8, 12, 16, 20}


class HandVisualizerPlugin(BasePlugin):
    name   = "HandVisualizer"
    visual = True

    def process(self, frame, ctx):
        all_hands = ctx.get("_all_hands", [])

        # Fallback to primary hand if list not populated
        if not all_hands:
            hd = ctx.get("hand_data")
            if hd and hd.detected:
                all_hands = [hd]

        h, w = frame.shape[:2]

        for hd in all_hands:
            if not hd.detected:
                continue

            # Right hand = cyan, Left hand = lime green
            colour = (0, 220, 255) if hd.handedness == "Right" else (80, 255, 80)
            lm     = hd.landmarks

            # Skeleton lines
            for a, b in _CONNECTIONS:
                ax, ay = int(lm[a][0] * w), int(lm[a][1] * h)
                bx, by = int(lm[b][0] * w), int(lm[b][1] * h)
                cv2.line(frame, (ax, ay), (bx, by), colour, 2, cv2.LINE_AA)

            # Landmark dots
            for i, (nx, ny, _) in enumerate(lm):
                px, py = int(nx * w), int(ny * h)
                radius = 5 if i in _TIPS else 3
                cv2.circle(frame, (px, py), radius, (255, 255, 255), -1)
                cv2.circle(frame, (px, py), radius, colour, 1)

        return frame
