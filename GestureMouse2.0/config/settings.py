"""
config/settings.py
All tunable parameters for GestureMouse 2.0.
Edit values here — no other files need to change.
These values can also be changed live via the Settings panel
(hold a fist for 2 seconds to open it).
"""

try:
    from screeninfo import get_monitors
    _mon = get_monitors()[0]
    _SCR_W, _SCR_H = _mon.width, _mon.height
except Exception:
    _SCR_W, _SCR_H = 1920, 1080


class Settings:
    # ── Camera ────────────────────────────────────────────────────────
    CAMERA_INDEX  = 0       # try 1 or 2 if camera doesn't open
    FRAME_WIDTH   = 1280
    FRAME_HEIGHT  = 720
    CAMERA_FPS    = 30

    # ── Cursor smoothing ──────────────────────────────────────────────
    SMOOTHING_FACTOR = 0.25  # higher = smoother but laggier (0.05–0.80)

    # ── Pinch / gesture thresholds ────────────────────────────────────
    PINCH_CLICK_THRESHOLD  = 0.045   # lower = harder to trigger (0.02–0.10)
    DRAG_DWELL_FRAMES      = 6       # frames of pinch before drag starts
    CLICK_COOLDOWN_FRAMES  = 12      # prevents double-fire

    # ── Cursor dead-zone margins (fraction of frame) ──────────────────
    MARGIN_LEFT   = 0.10
    MARGIN_RIGHT  = 0.10
    MARGIN_TOP    = 0.10
    MARGIN_BOTTOM = 0.10

    # ── Visuals ───────────────────────────────────────────────────────
    VISUALS_ENABLED = True
    TRAIL_LENGTH    = 25

    # ── MediaPipe confidence ──────────────────────────────────────────
    MIN_DETECTION_CONF = 0.70
    MIN_TRACKING_CONF  = 0.60

    # ── Screen (auto-detected) ────────────────────────────────────────
    SCREEN_W = _SCR_W
    SCREEN_H = _SCR_H

    # ── Drawing board ─────────────────────────────────────────────────
    DRAW_DWELL_TIME    = 0.8    # seconds hovering toolbar before auto-click
    DRAW_DEFAULT_SIZE  = 8      # default brush size (2–60) — tunable live
