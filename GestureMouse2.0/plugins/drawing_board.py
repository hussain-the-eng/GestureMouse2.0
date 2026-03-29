"""
plugins/drawing_board.py
Full-screen hand-drawing canvas that overlays the webcam feed.

Activation
──────────
  Press  A          keyboard shortcut
  ✌️ Peace sign      gesture (index + middle up, others folded)
  Press  A / ESC    to exit back to mouse control

Two-hand drawing
────────────────
  Right hand  →  draws in Red   (default, changeable from toolbar)
  Left  hand  →  draws in Green (default, changeable from toolbar)
  Both hands draw simultaneously.

Drawing gesture
───────────────
  ☝ Index finger up only  →  draw / erase / fill stroke
  Any other hand shape     →  pen lifted (no mark)

Toolbar (top 64 px strip)
──────────────────────────
  Hover index fingertip over a button for DRAW_DWELL_TIME seconds  → auto-click
  Or pinch (thumb ↔ index) while hovering                          → instant click

  Buttons: ✏ Draw | 🪣 Fill | ⬜ Erase | − Size | Size+ | [8 colours]
           | Undo | Clear | Save | ✕ Exit

Keyboard shortcuts (while board is active)
──────────────────────────────────────────
  A / ESC   exit drawing board
  Z         undo last stroke
"""

import os
import time
import datetime
from collections import deque
from typing import List, Optional, Tuple

import cv2
import numpy as np

from plugins.plugin_manager import BasePlugin


# ── Constants ─────────────────────────────────────────────────────────────────

TOOLBAR_H = 64
BTN_PAD   = 6

# Colour palette  name → BGR
PALETTE = {
    "Red":    (0,   0,   220),
    "Green":  (0,   180,  60),
    "Blue":   (220,  80,   0),
    "Yellow": (0,   220, 220),
    "White":  (240, 240, 240),
    "Cyan":   (200, 200,   0),
    "Purple": (180,   0, 180),
    "Orange": (0,   140, 255),
}


# ── Internal button dataclass ─────────────────────────────────────────────────

class _Button:
    __slots__ = ("label", "x", "y", "w", "h", "swatch", "action",
                 "hovered", "hover_start")

    def __init__(self, label: str, x: int, y: int, w: int, h: int,
                 swatch=None, action: str = ""):
        self.label       = label
        self.x           = x
        self.y           = y
        self.w           = w
        self.h           = h
        self.swatch      = swatch      # BGR colour or None
        self.action      = action
        self.hovered     = False
        self.hover_start = 0.0


# ── Plugin ────────────────────────────────────────────────────────────────────

class DrawingBoardPlugin(BasePlugin):
    """
    Full-screen drawing canvas.
    Registered last in the plugin pipeline so it renders on top of everything.
    """

    name   = "DrawingBoard"
    visual = False   # never toggled by the V key — it has its own toggle

    def __init__(self, settings):
        super().__init__(settings)

        self.active = False

        self._W = settings.FRAME_WIDTH
        self._H = settings.FRAME_HEIGHT

        # Drawing canvas (black, BGR)
        self._canvas = np.zeros((self._H, self._W, 3), dtype=np.uint8)

        # Tool state
        self._mode       = "draw"              # "draw" | "erase" | "fill"
        self._brush_size = settings.DRAW_DEFAULT_SIZE
        self._color_r    = PALETTE["Red"]      # right-hand pen colour
        self._color_l    = PALETTE["Green"]    # left-hand pen colour

        # Previous fingertip positions for continuous strokes
        self._prev_r: Optional[Tuple[int, int]] = None
        self._prev_l: Optional[Tuple[int, int]] = None

        # Pinch state (to detect leading edge only)
        self._pinching_r = False
        self._pinching_l = False

        # Undo stack
        self._undo: deque = deque(maxlen=20)

        # Toolbar
        self._buttons: List[_Button] = []
        self._build_toolbar()

        # Peace-sign 3-second hold state
        self._peace_start    = 0.0   # time.time() when hold began, 0 = not holding
        self._peace_cooldown = 0     # frames after open so it doesn't re-trigger

        # Dwell time for toolbar buttons
        self._dwell = settings.DRAW_DWELL_TIME

        # Where to save drawings — os.path.join handles Windows \ vs Unix / separators
        self._save_dir = os.path.join(os.path.expanduser("~"), "Pictures", "GestureMouse")

        # Status message overlay
        self._status_text = ""
        self._status_time = 0.0

    # ── Toolbar builder ───────────────────────────────────────────────────────

    def _build_toolbar(self):
        self._buttons.clear()
        bh = TOOLBAR_H - BTN_PAD * 2
        x  = BTN_PAD
        y  = BTN_PAD

        def add(label, action, swatch=None, w=72):
            nonlocal x
            self._buttons.append(
                _Button(label, x, y, w, bh, swatch=swatch, action=action)
            )
            x += w + BTN_PAD

        # Mode buttons
        add("✏ Draw",  "draw",  w=76)
        add("🪣 Fill",  "fill",  w=70)
        add("⬜ Erase", "erase", w=76)

        # Brush size
        add("─",     "size_down", w=38)
        add("Size",  "_display",  w=52)
        add("+",     "size_up",   w=38)

        x += 8   # small gap before palette

        # Colour swatches
        for name, bgr in PALETTE.items():
            add(name, f"color:{name}", swatch=bgr, w=44)

        x += 8   # gap before action buttons

        # Action buttons
        add("Undo",  "undo",  w=56)
        add("Clear", "clear", w=56)
        add("Save",  "save",  w=56)
        add("✕ Exit","exit",  w=62)

    # ── Activation ────────────────────────────────────────────────────────────

    def enter(self):
        if not self.active:
            self._push_undo()
            self.active  = True
            self.enabled = True
            self._status("✏  Drawing Board  —  index finger to draw  |  pinch toolbar to select tools")

    def exit_board(self):
        self.active = False

    def toggle(self):
        self.exit_board() if self.active else self.enter()

    # ── Plugin entry point ────────────────────────────────────────────────────

    def process(self, frame: np.ndarray, ctx: dict) -> np.ndarray:

        # ── Peace-sign 3-second hold to open ────────────────────────
        if self._peace_cooldown > 0:
            self._peace_cooldown -= 1

        primary = ctx.get("hand_data")
        if primary and primary.detected and self._peace_cooldown == 0 and not self.active:
            fu      = primary.fingers_up
            is_peace = fu[1] and fu[2] and not fu[3] and not fu[4] and not fu[0]
            if is_peace:
                if self._peace_start == 0.0:
                    self._peace_start = time.time()
                elapsed  = time.time() - self._peace_start
                progress = min(1.0, elapsed / 3.0)
                # Draw fill arc around index fingertip
                fh2, fw2 = frame.shape[:2]
                tx = int(primary.index_tip[0] * fw2)
                ty = int(primary.index_tip[1] * fh2)
                arc_col = (0, int(180 * progress), 255)
                cv2.ellipse(frame, (tx, ty), (24, 24), -90,
                            0, int(360 * progress), arc_col, 3, cv2.LINE_AA)
                pct_txt = f"{int(progress*100)}%"
                cv2.putText(frame, pct_txt, (tx - 14, ty + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, arc_col, 1, cv2.LINE_AA)
                if elapsed >= 3.0:
                    self._peace_start = 0.0
                    self.enter()
                    self._peace_cooldown = 90   # ~3 s guard at 30 fps
            else:
                self._peace_start = 0.0   # reset if hand shape changes

        if not self.active:
            return frame

        fh, fw = frame.shape[:2]

        # Resize canvas if camera resolution changed
        if self._canvas.shape[:2] != (fh, fw):
            self._W, self._H = fw, fh
            self._canvas = np.zeros((fh, fw, 3), dtype=np.uint8)
            self._build_toolbar()

        # ── Sort hands ────────────────────────────────────────────────
        all_hands = ctx.get("_all_hands", [])
        right_hd  = None
        left_hd   = None
        for hd in all_hands:
            if hd.detected:
                if hd.handedness == "Right" and right_hd is None:
                    right_hd = hd
                elif hd.handedness == "Left" and left_hd is None:
                    left_hd = hd

        # Fallback: if list is empty, use primary hand
        if right_hd is None and left_hd is None:
            if primary and primary.detected:
                right_hd = primary

        # ── Process each hand ─────────────────────────────────────────
        r_tip = self._process_hand(right_hd, "right", fw, fh)
        l_tip = self._process_hand(left_hd,  "left",  fw, fh)

        return self._render(frame, fw, fh, r_tip, l_tip)

    # ── Per-hand drawing logic ────────────────────────────────────────────────

    def _process_hand(self, hd, side: str, fw: int, fh: int):
        """
        Process one hand.  Draws to self._canvas if conditions are met.
        Returns tip pixel position or None.
        """
        prev_attr  = "_prev_r"     if side == "right" else "_prev_l"
        pinch_attr = "_pinching_r" if side == "right" else "_pinching_l"
        color      = self._color_r if side == "right" else self._color_l

        if hd is None or not hd.detected:
            setattr(self, prev_attr, None)
            return None

        tip_px   = (int(hd.index_tip[0] * fw), int(hd.index_tip[1] * fh))
        pinching = hd.pinch_index_dist < self.settings.PINCH_CLICK_THRESHOLD * 1.15

        # ── Toolbar zone ──────────────────────────────────────────────
        if tip_px[1] < TOOLBAR_H:
            btn = self._hit_button(tip_px[0])
            if btn:
                btn.hovered = True
                if btn.hover_start == 0.0:
                    btn.hover_start = time.time()
                elapsed = time.time() - btn.hover_start
                if pinching or elapsed >= self._dwell:
                    self._fire_button(btn, side)
                    btn.hover_start = 0.0
                    btn.hovered     = False
            # Lift pen when in toolbar
            setattr(self, prev_attr, None)
            setattr(self, pinch_attr, pinching)
            return tip_px

        # Reset hover for all buttons when finger leaves toolbar
        for b in self._buttons:
            b.hovered     = False
            b.hover_start = 0.0

        # ── Drawing zone ──────────────────────────────────────────────
        fu        = hd.fingers_up
        index_up  = fu[1] and not fu[2] and not fu[3] and not fu[4]
        prev_pt   = getattr(self, prev_attr)
        was_pinch = getattr(self, pinch_attr)

        if index_up:
            if self._mode == "erase":
                radius = self._brush_size * 3
                cv2.circle(self._canvas, tip_px, radius, (0, 0, 0), -1)
                setattr(self, prev_attr, tip_px)

            elif self._mode == "fill":
                # Flood fill on the leading edge of a pinch
                if pinching and not was_pinch:
                    self._flood_fill(tip_px, color)
                setattr(self, prev_attr, tip_px)

            else:  # draw
                if prev_pt is not None:
                    cv2.line(self._canvas, prev_pt, tip_px,
                             color, self._brush_size, cv2.LINE_AA)
                else:
                    cv2.circle(self._canvas, tip_px,
                               max(1, self._brush_size // 2), color, -1)
                setattr(self, prev_attr, tip_px)

        else:
            # Pen lifted
            setattr(self, prev_attr, None)

        setattr(self, pinch_attr, pinching)
        return tip_px

    # ── Button helpers ────────────────────────────────────────────────────────

    def _hit_button(self, x: int) -> Optional[_Button]:
        for btn in self._buttons:
            if btn.x <= x <= btn.x + btn.w:
                return btn
        return None

    def _fire_button(self, btn: _Button, side: str):
        a = btn.action
        if   a == "draw":       self._mode = "draw"
        elif a == "erase":      self._mode = "erase"
        elif a == "fill":       self._mode = "fill"
        elif a == "size_up":    self._brush_size = min(60, self._brush_size + 2)
        elif a == "size_down":  self._brush_size = max(2,  self._brush_size - 2)
        elif a == "undo":       self._pop_undo()
        elif a == "clear":
            self._push_undo()
            self._canvas[:] = 0
            self._status("Canvas cleared")
        elif a == "save":       self._save()
        elif a == "exit":       self.exit_board()
        elif a.startswith("color:"):
            name = a.split(":", 1)[1]
            if side == "right":
                self._color_r = PALETTE[name]
                self._status(f"Right hand → {name}")
            else:
                self._color_l = PALETTE[name]
                self._status(f"Left hand → {name}")

    # ── Undo / fill / save ────────────────────────────────────────────────────

    def _push_undo(self):
        self._undo.append(self._canvas.copy())

    def _pop_undo(self):
        if self._undo:
            self._canvas = self._undo.pop()
            self._status("Undo")

    def _flood_fill(self, pt: Tuple[int, int], color: Tuple[int, int, int]):
        self._push_undo()
        h, w = self._canvas.shape[:2]
        mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
        fill = (int(color[0]), int(color[1]), int(color[2]))
        cv2.floodFill(self._canvas, mask, pt, fill,
                      loDiff=(20, 20, 20), upDiff=(20, 20, 20))

    def _save(self):
        os.makedirs(self._save_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path  = os.path.join(self._save_dir, f"drawing_{stamp}.png")
        cv2.imwrite(path, self._canvas)
        self._status(f"Saved → {path}")

    # ── Status ────────────────────────────────────────────────────────────────

    def _status(self, text: str):
        self._status_text = text
        self._status_time = time.time()

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self, frame: np.ndarray, fw: int, fh: int,
                r_tip, l_tip) -> np.ndarray:

        # Dim the camera feed so the drawing stands out
        out = (frame.astype(np.float32) * 0.35).astype(np.uint8)

        # Composite canvas strokes on top
        grey  = cv2.cvtColor(self._canvas, cv2.COLOR_BGR2GRAY)
        _, m  = cv2.threshold(grey, 5, 255, cv2.THRESH_BINARY)
        m3    = cv2.cvtColor(m, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0
        out   = (out.astype(np.float32) * (1 - m3) +
                 self._canvas.astype(np.float32) * m3).astype(np.uint8)

        # ── Toolbar background ────────────────────────────────────────
        tb_bg = np.full((TOOLBAR_H, fw, 3), (28, 28, 28), dtype=np.uint8)
        out[:TOOLBAR_H] = cv2.addWeighted(out[:TOOLBAR_H], 0.15, tb_bg, 0.85, 0)

        # ── Draw buttons ──────────────────────────────────────────────
        for btn in self._buttons:
            bx, by, bw, bh = btn.x, btn.y, btn.w, btn.h

            # Background colour
            if btn.action == "_display":
                bg = (40, 40, 40)
            elif btn.swatch is not None:
                bg = btn.swatch
            elif btn.action == self._mode:
                bg = (55, 110, 190)     # active mode highlight
            elif btn.hovered:
                bg = (75, 75, 75)
            else:
                bg = (48, 48, 48)

            cv2.rectangle(out, (bx, by), (bx + bw, by + bh), bg, -1)

            # Dwell progress bar at button bottom
            if btn.hovered and btn.hover_start > 0:
                progress = min(1.0, (time.time() - btn.hover_start) / self._dwell)
                bar_w    = int(bw * progress)
                cv2.rectangle(out,
                               (bx, by + bh - 4),
                               (bx + bar_w, by + bh),
                               (0, 200, 255), -1)

            # Border
            border_col = (0, 200, 255) if btn.hovered else (70, 70, 70)
            cv2.rectangle(out, (bx, by), (bx + bw, by + bh), border_col, 1)

            # Label text
            if btn.action == "_display":
                label = f"S:{self._brush_size}"
            elif btn.swatch is not None:
                label = ""
            else:
                label = btn.label

            if label:
                fs = 0.36
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
                tx = bx + (bw - tw) // 2
                ty = by + (bh + th) // 2
                cv2.putText(out, label, (tx, ty),
                            cv2.FONT_HERSHEY_SIMPLEX, fs,
                            (215, 215, 215), 1, cv2.LINE_AA)

        # ── Cursor rings ──────────────────────────────────────────────
        for tip, col in [(r_tip, self._color_r), (l_tip, self._color_l)]:
            if tip is None:
                continue
            ring_r = self._brush_size + 6
            if self._mode == "erase":
                ring_r = self._brush_size * 3
            cv2.circle(out, tip, ring_r, col, 2, cv2.LINE_AA)
            cv2.circle(out, tip, 3, (255, 255, 255), -1)

        # ── Hand colour legend (top-right) ────────────────────────────
        lx = fw - 148
        ly = TOOLBAR_H + 22
        cv2.circle(out, (lx, ly), 8, self._color_r, -1)
        cv2.putText(out, "Right hand", (lx + 14, ly + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (190, 190, 190), 1)
        cv2.circle(out, (lx, ly + 22), 8, self._color_l, -1)
        cv2.putText(out, "Left hand",  (lx + 14, ly + 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (190, 190, 190), 1)

        # ── Status message ────────────────────────────────────────────
        if self._status_text and time.time() - self._status_time < 3.5:
            fade  = min(1.0, (3.5 - (time.time() - self._status_time)) / 0.4)
            scol  = tuple(int(c * fade) for c in (0, 200, 255))
            cv2.putText(out, self._status_text, (16, fh - 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, scol, 2, cv2.LINE_AA)

        # ── Corner hint ───────────────────────────────────────────────
        hint = "DRAWING BOARD  |  [A]/[ESC] exit   [Z] undo"
        cv2.putText(out, hint, (fw - 390, fh - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 100, 100), 1)

        return out

    # ── Keyboard handler (called from main.py) ────────────────────────────────

    def on_key(self, key: int) -> bool:
        """
        Returns True if the key was consumed so main.py can skip other handlers.
        """
        if key == ord('a') or key == ord('A'):
            self.toggle()
            return True
        if self.active:
            if key == 27:                        # ESC
                self.exit_board()
                return True
            if key == ord('z') or key == ord('Z'):
                self._pop_undo()
                return True
        return False
