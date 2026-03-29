"""
plugins/settings_tuner.py
Real-time settings panel — adjust key values without restarting.

Activation
──────────
  Hold a FIST  for 2 seconds  →  panel opens / closes
  A progress arc fills around your wrist as you hold.

Controls (panel open)
─────────────────────
  ☝ Point at a slider row      →  row highlights
  🤏 Pinch + move left/right   →  drag the slider value
  Release pinch                →  value is committed to settings

Sliders
───────
  Smoothing        0.05 – 0.80   (settings.SMOOTHING_FACTOR)
  Click Threshold  0.02 – 0.10   (settings.PINCH_CLICK_THRESHOLD)
  Brush Size       2   – 60      (settings.DRAW_DEFAULT_SIZE / drawing board live)

The panel is semi-transparent and drawn in the top-right corner.
Mouse control continues normally while the panel is open.
"""

import time
import math
from typing import Optional

import cv2
import numpy as np

from plugins.plugin_manager import BasePlugin


# ── Layout ────────────────────────────────────────────────────────────────────

PANEL_W   = 300
PANEL_H   = 220
PANEL_X   = 20    # from right edge
PANEL_Y   = 80    # from top
FIST_HOLD = 2.0   # seconds to hold fist before panel opens


# ── Slider definition ─────────────────────────────────────────────────────────

class _Slider:
    __slots__ = ("label", "attr", "lo", "hi", "fmt", "value",
                 "dragging", "drag_start_x", "drag_start_val")

    def __init__(self, label: str, attr: str,
                 lo: float, hi: float, fmt: str, value: float):
        self.label         = label
        self.attr          = attr      # attribute name on Settings instance
        self.lo            = lo
        self.hi            = hi
        self.fmt           = fmt       # e.g. "{:.2f}" or "{:.0f}"
        self.value         = value
        self.dragging      = False
        self.drag_start_x  = 0.0      # normalised x when pinch started
        self.drag_start_val= 0.0      # value when pinch started


# ── Plugin ────────────────────────────────────────────────────────────────────

class SettingsTunerPlugin(BasePlugin):
    """
    Real-time slider panel.
    Hold fist 2 s to open/close.
    Point + pinch-drag to change values.
    """

    name   = "SettingsTuner"
    visual = False   # not toggled by V — always available

    def __init__(self, settings):
        super().__init__(settings)
        self.panel_open = False

        self._fist_start: Optional[float] = None   # time fist hold began
        self._close_cooldown = 0                    # frames after close

        self._sliders = [
            _Slider("Smoothing",       "SMOOTHING_FACTOR",
                    0.05, 0.80, "{:.2f}", settings.SMOOTHING_FACTOR),
            _Slider("Click Threshold", "PINCH_CLICK_THRESHOLD",
                    0.02, 0.10, "{:.3f}", settings.PINCH_CLICK_THRESHOLD),
            _Slider("Brush Size",      "DRAW_DEFAULT_SIZE",
                    2.0,  60.0, "{:.0f}", float(settings.DRAW_DEFAULT_SIZE)),
        ]

        self._hovered_idx: Optional[int] = None   # slider row under fingertip

    # ── helpers ───────────────────────────────────────────────────────────────

    def _commit(self, slider: _Slider):
        """Write slider value back to the live settings object."""
        v = slider.value
        if slider.fmt == "{:.0f}":
            v = int(round(v))
        setattr(self.settings, slider.attr, v)
        # Special case: brush size also syncs to drawing board at runtime
        # (drawing board reads settings.DRAW_DEFAULT_SIZE only at init,
        #  but we can propagate via settings for next open)

    # ── plugin entry ──────────────────────────────────────────────────────────

    def process(self, frame: np.ndarray, ctx: dict) -> np.ndarray:
        hd = ctx.get("hand_data")
        fh, fw = frame.shape[:2]

        # ── Fist-hold detection ───────────────────────────────────────
        if self._close_cooldown > 0:
            self._close_cooldown -= 1

        is_fist = (hd and hd.detected and not any(hd.fingers_up))

        if is_fist and self._close_cooldown == 0:
            if self._fist_start is None:
                self._fist_start = time.time()
            elapsed = time.time() - self._fist_start

            # Draw progress arc around wrist while holding
            wx = int(hd.wrist[0] * fw)
            wy = int(hd.wrist[1] * fh)
            progress = min(1.0, elapsed / FIST_HOLD)
            self._draw_arc(frame, wx, wy, progress)

            if elapsed >= FIST_HOLD:
                self.panel_open  = not self.panel_open
                self._fist_start = None
                self._close_cooldown = 60   # ~2 s guard
        else:
            self._fist_start = None

        if not self.panel_open:
            return frame

        # ── Panel position (top-right, avoids toolbar) ────────────────
        px = fw - PANEL_W - PANEL_X
        py = PANEL_Y

        # ── Finger tip for interaction ────────────────────────────────
        tip = None
        pinching = False
        if hd and hd.detected:
            tip      = (hd.index_tip[0], hd.index_tip[1])   # normalised
            pinching = hd.pinch_index_dist < self.settings.PINCH_CLICK_THRESHOLD * 1.2

        # ── Slider interaction ────────────────────────────────────────
        ROW_H     = 54
        TRACK_X   = px + 16
        TRACK_W   = PANEL_W - 32
        FIRST_ROW = py + 52

        self._hovered_idx = None
        for i, sl in enumerate(self._sliders):
            row_top    = FIRST_ROW + i * ROW_H
            row_bottom = row_top + ROW_H

            # Check if fingertip is over this row
            if tip is not None:
                tx_px = tip[0] * fw
                ty_px = tip[1] * fh
                if (TRACK_X <= tx_px <= TRACK_X + TRACK_W and
                        row_top <= ty_px <= row_bottom):
                    self._hovered_idx = i

                    if pinching:
                        if not sl.dragging:
                            # Start drag — record baseline
                            sl.dragging       = True
                            sl.drag_start_x   = tip[0]
                            sl.drag_start_val = sl.value
                        else:
                            # Drag: map horizontal movement to value range
                            dx       = tip[0] - sl.drag_start_x
                            span     = sl.hi - sl.lo
                            sl.value = sl.drag_start_val + dx * span * 2.5
                            sl.value = max(sl.lo, min(sl.hi, sl.value))
                            self._commit(sl)
                    else:
                        if sl.dragging:
                            sl.dragging = False   # released
                else:
                    if sl.dragging and not pinching:
                        sl.dragging = False

        # ── Draw panel ────────────────────────────────────────────────
        frame = self._draw_panel(frame, px, py, fw, fh,
                                 TRACK_X, TRACK_W, FIRST_ROW, ROW_H)

        # ── Fist hint (when panel is closed) ─────────────────────────
        return frame

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_arc(self, frame, cx, cy, progress):
        """Fill arc around a point as a hold-progress indicator."""
        radius   = 28
        end_angle = int(360 * progress)
        colour   = (0, int(200 * progress), 255)
        cv2.ellipse(frame, (cx, cy), (radius, radius),
                    -90, 0, end_angle, colour, 3, cv2.LINE_AA)
        # Label
        pct = int(progress * 100)
        cv2.putText(frame, f"{pct}%", (cx - 14, cy + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, colour, 1, cv2.LINE_AA)

    def _draw_panel(self, frame, px, py, fw, fh,
                    track_x, track_w, first_row, row_h):
        overlay = frame.copy()

        # Panel background
        cv2.rectangle(overlay, (px, py),
                      (px + PANEL_W, py + PANEL_H),
                      (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

        # Panel border
        cv2.rectangle(frame, (px, py),
                      (px + PANEL_W, py + PANEL_H),
                      (70, 70, 70), 1)

        # Title
        cv2.putText(frame, "SETTINGS  (fist 2s to close)",
                    (px + 10, py + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                    (160, 160, 160), 1, cv2.LINE_AA)
        cv2.line(frame, (px + 8, py + 30),
                 (px + PANEL_W - 8, py + 30), (55, 55, 55), 1)

        for i, sl in enumerate(self._sliders):
            row_y     = first_row + i * row_h
            is_hover  = (self._hovered_idx == i)
            is_drag   = sl.dragging

            label_col = (0, 200, 255) if is_drag else (
                        (200, 220, 255) if is_hover else (160, 160, 160))

            # Label + value
            val_str = sl.fmt.format(sl.value)
            cv2.putText(frame, sl.label,
                        (track_x, row_y + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, label_col, 1, cv2.LINE_AA)
            cv2.putText(frame, val_str,
                        (track_x + track_w - 48, row_y + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, label_col, 1, cv2.LINE_AA)

            # Track background
            track_y = row_y + 24
            cv2.rectangle(frame,
                          (track_x, track_y),
                          (track_x + track_w, track_y + 10),
                          (50, 50, 50), -1)
            cv2.rectangle(frame,
                          (track_x, track_y),
                          (track_x + track_w, track_y + 10),
                          (75, 75, 75), 1)

            # Fill
            ratio   = (sl.value - sl.lo) / max(1e-6, sl.hi - sl.lo)
            fill_w  = int(track_w * ratio)
            fill_col = (0, 180, 255) if is_drag else (
                        (0, 140, 200) if is_hover else (0, 100, 160))
            if fill_w > 0:
                cv2.rectangle(frame,
                              (track_x, track_y),
                              (track_x + fill_w, track_y + 10),
                              fill_col, -1)

            # Thumb
            thumb_x = track_x + fill_w
            cv2.circle(frame, (thumb_x, track_y + 5), 7,
                       (255, 255, 255) if is_drag else (180, 180, 180), -1)
            cv2.circle(frame, (thumb_x, track_y + 5), 7, (80, 80, 80), 1)

        # Hint at bottom
        cv2.putText(frame, "point + pinch-drag to change",
                    (px + 14, py + PANEL_H - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.33,
                    (90, 90, 90), 1, cv2.LINE_AA)

        # Closed-panel fist hint (rendered outside panel when closed)
        return frame
