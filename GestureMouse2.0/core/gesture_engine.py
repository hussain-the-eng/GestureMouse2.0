"""
core/gesture_engine.py
Converts HandData into a GestureState (gesture label + scroll delta).

Gesture priority (highest → lowest)
─────────────────────────────────────
  FIST          all fingers folded
  RIGHT_CLICK   thumb ↔ middle pinch
  DRAG          thumb ↔ index pinch held for DRAG_DWELL_FRAMES
  LEFT_CLICK    thumb ↔ index pinch (short)
  SCROLL        index + middle up, moving vertically
  PEACE         index + middle up, stationary
  MOVE          index up only
  NONE          anything else

To add a new gesture: insert a new rule inside GestureEngine.classify()
before the final NONE return, then handle it in mouse_controller.py or a plugin.
"""


class Gesture:
    NONE        = "NONE"
    MOVE        = "MOVE"
    LEFT_CLICK  = "LEFT_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    DRAG        = "DRAG"
    SCROLL      = "SCROLL"
    FIST        = "FIST"
    PEACE       = "PEACE"


class GestureState:
    def __init__(self):
        self.gesture      = Gesture.NONE
        self.label        = ""
        self.scroll_delta = 0.0   # positive = scroll up


class GestureEngine:
    def __init__(self, settings):
        self.settings      = settings
        self._pinch_frames = 0
        self._prev_index_y = None

    def classify(self, hd) -> GestureState:
        """
        hd : HandData
        Returns GestureState.
        """
        state = GestureState()
        if not hd.detected:
            return state

        fu = hd.fingers_up
        pi = hd.pinch_index_dist
        pm = hd.pinch_middle_dist
        th = self.settings.PINCH_CLICK_THRESHOLD

        # ── Fist ──────────────────────────────────────────────────────
        if not any(fu):
            state.gesture      = Gesture.FIST
            state.label        = "Fist ✊"
            self._pinch_frames = 0
            self._prev_index_y = None
            return state

        # ── Two-finger gestures (index + middle up) ───────────────────
        if fu[1] and fu[2] and not fu[3] and not fu[4]:

            # Scroll — detect vertical movement of index tip
            if self._prev_index_y is not None:
                delta = self._prev_index_y - hd.index_tip[1]
                if abs(delta) > 0.004:
                    state.gesture      = Gesture.SCROLL
                    state.label        = "Scroll 📜"
                    state.scroll_delta = delta * 18
                    self._prev_index_y = hd.index_tip[1]
                    self._pinch_frames = 0
                    return state

            self._prev_index_y = hd.index_tip[1]
            state.gesture      = Gesture.PEACE
            state.label        = "Peace ✌️"
            self._pinch_frames = 0
            return state

        self._prev_index_y = None

        # ── Right click — thumb ↔ middle pinch ────────────────────────
        if pm < th and pi >= th:
            state.gesture      = Gesture.RIGHT_CLICK
            state.label        = "Right Click 🖱️"
            self._pinch_frames = 0
            return state

        # ── Left click / drag — thumb ↔ index pinch ──────────────────
        if pi < th:
            self._pinch_frames += 1
            if self._pinch_frames >= self.settings.DRAG_DWELL_FRAMES:
                state.gesture = Gesture.DRAG
                state.label   = "Drag 🤌"
            else:
                state.gesture = Gesture.LEFT_CLICK
                state.label   = "Click 👆"
            return state

        self._pinch_frames = 0

        # ── Move — index finger only ──────────────────────────────────
        if fu[1] and not fu[2] and not fu[3] and not fu[4]:
            state.gesture = Gesture.MOVE
            state.label   = "Move ☝️"
            return state

        # ── Open hand / unknown ───────────────────────────────────────
        state.gesture = Gesture.NONE
        state.label   = "Open 🖐"
        return state
