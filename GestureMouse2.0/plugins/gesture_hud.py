"""
plugins/gesture_hud.py
Draws a semi-transparent HUD panel in the bottom-left corner showing
the current gesture label and active mouse actions.
"""

import cv2
import numpy as np
from plugins.plugin_manager import BasePlugin


class GestureHUDPlugin(BasePlugin):
    name   = "GestureHUD"
    visual = True

    def process(self, frame, ctx):
        gesture = ctx.get("gesture")
        action  = ctx.get("action")
        if gesture is None:
            return frame

        h, w = frame.shape[:2]

        # ── Panel ─────────────────────────────────────────────────────
        ph, pw = 94, 230
        px, py = 12, h - ph - 12

        overlay = frame.copy()
        cv2.rectangle(overlay, (px, py), (px + pw, py + ph), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        # Thin border
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), (60, 60, 60), 1)

        # Gesture label
        label = gesture.label or "—"
        cv2.putText(frame, label,
                    (px + 10, py + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (0, 220, 255), 2, cv2.LINE_AA)

        # Action lines
        if action:
            lines = []
            if action.left_click:   lines.append("LEFT CLICK")
            if action.right_click:  lines.append("RIGHT CLICK")
            if action.drag_active:  lines.append("DRAGGING")
            if action.moved:
                lines.append(f"pos {action.screen_pos[0]}, {action.screen_pos[1]}")
            for i, txt in enumerate(lines):
                cv2.putText(frame, txt,
                            (px + 10, py + 56 + i * 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                            (180, 180, 180), 1, cv2.LINE_AA)

        return frame
