"""
core/mouse_controller.py
Translates GestureState + HandData into real OS mouse actions via pyautogui.

MouseAction fields (read by plugins)
──────────────────────────────────────
  moved        bool   — cursor was moved this frame
  left_click   bool   — left click fired this frame
  right_click  bool   — right click fired this frame
  drag_active  bool   — drag is currently held
  screen_pos   (x, y) — current screen position in pixels
"""

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE    = 0
    _PAUTOGUI = True
except ImportError:
    print("[WARN] pyautogui not installed — mouse control disabled.")
    _PAUTOGUI = False


class MouseAction:
    def __init__(self):
        self.moved       = False
        self.left_click  = False
        self.right_click = False
        self.drag_active = False
        self.screen_pos  = (0, 0)


class MouseController:
    def __init__(self, settings):
        self.settings        = settings
        self._smooth_x       = 0.0
        self._smooth_y       = 0.0
        self._click_cooldown = 0
        self._drag_active    = False
        self.last_screen_pos = (0, 0)

    def execute(self, gesture, hd) -> MouseAction:
        """
        gesture : GestureState
        hd      : HandData
        Returns MouseAction.
        """
        from core.gesture_engine import Gesture

        action = MouseAction()
        if not hd.detected:
            return action

        s = self.settings

        # ── Map normalised tip position → screen ──────────────────────
        ml, mr = s.MARGIN_LEFT, s.MARGIN_RIGHT
        mt, mb = s.MARGIN_TOP,  s.MARGIN_BOTTOM

        nx = (hd.index_tip[0] - ml) / max(1e-6, 1.0 - ml - mr)
        ny = (hd.index_tip[1] - mt) / max(1e-6, 1.0 - mt - mb)
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))

        sf = s.SMOOTHING_FACTOR
        self._smooth_x += sf * (nx - self._smooth_x)
        self._smooth_y += sf * (ny - self._smooth_y)

        sx = int(self._smooth_x * s.SCREEN_W)
        sy = int(self._smooth_y * s.SCREEN_H)
        self.last_screen_pos = (sx, sy)
        action.screen_pos    = (sx, sy)

        g = gesture.gesture

        # Move cursor for all gesture types that need positioning
        if g in (Gesture.MOVE, Gesture.LEFT_CLICK, Gesture.DRAG,
                 Gesture.RIGHT_CLICK, Gesture.SCROLL):
            if _PAUTOGUI:
                pyautogui.moveTo(sx, sy)
            action.moved = True

        # Cooldown tick
        if self._click_cooldown > 0:
            self._click_cooldown -= 1

        # ── Left click ────────────────────────────────────────────────
        if g == Gesture.LEFT_CLICK and self._click_cooldown == 0:
            if self._drag_active:
                if _PAUTOGUI:
                    pyautogui.mouseUp()
                self._drag_active = False
            if _PAUTOGUI:
                pyautogui.click()
            action.left_click    = True
            self._click_cooldown = s.CLICK_COOLDOWN_FRAMES

        # ── Right click ───────────────────────────────────────────────
        elif g == Gesture.RIGHT_CLICK and self._click_cooldown == 0:
            if _PAUTOGUI:
                pyautogui.rightClick()
            action.right_click   = True
            self._click_cooldown = s.CLICK_COOLDOWN_FRAMES

        # ── Drag ──────────────────────────────────────────────────────
        elif g == Gesture.DRAG:
            if not self._drag_active:
                if _PAUTOGUI:
                    pyautogui.mouseDown()
                self._drag_active = True
            action.drag_active = True

        # ── Release drag if gesture ended ─────────────────────────────
        else:
            if self._drag_active:
                if _PAUTOGUI:
                    pyautogui.mouseUp()
                self._drag_active = False

        # ── Scroll ────────────────────────────────────────────────────
        if g == Gesture.SCROLL and abs(gesture.scroll_delta) > 0.5:
            if _PAUTOGUI:
                pyautogui.scroll(int(gesture.scroll_delta))

        return action
