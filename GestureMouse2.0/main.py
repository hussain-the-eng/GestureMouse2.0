"""
GestureMouse 2.0 — Real-Time Webcam Mouse Controller
Run:  python main.py

Controls
────────
  Q          Quit
  V          Toggle visual effects (trail, skeleton, ripples, HUD)
  D          Toggle debug overlay
  A          Open / close Drawing Board  (instant)
  ✌ 3 sec    Hold peace sign 3 s to open Drawing Board
  ESC        Exit Drawing Board
  Z          Undo last stroke (Drawing Board)
  Fist 2 s   Open / close Settings panel
"""

import cv2

from config.settings          import Settings
from core.hand_tracker        import HandTracker, HandData
from core.gesture_engine      import GestureEngine
from core.mouse_controller    import MouseController, MouseAction
from core.display             import Display
from plugins.plugin_manager   import PluginManager
from plugins.hand_visualizer  import HandVisualizerPlugin
from plugins.gesture_hud      import GestureHUDPlugin
from plugins.trail_effect     import TrailEffectPlugin
from plugins.click_ripple     import ClickRipplePlugin
from plugins.drawing_board    import DrawingBoardPlugin
from plugins.settings_tuner   import SettingsTunerPlugin


def main():
    settings = Settings()

    # ── Camera ────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(settings.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  settings.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          settings.CAMERA_FPS)

    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {settings.CAMERA_INDEX}.")
        print("        Try changing CAMERA_INDEX in config/settings.py")
        return

    # ── Core components ───────────────────────────────────────────────
    tracker = HandTracker(settings)
    engine  = GestureEngine(settings)
    mouse   = MouseController(settings)
    display = Display(settings)
    plugins = PluginManager(settings)

    # ── Register plugins (order = render order) ───────────────────────
    plugins.register(HandVisualizerPlugin(settings))
    plugins.register(GestureHUDPlugin(settings))
    plugins.register(TrailEffectPlugin(settings))
    plugins.register(ClickRipplePlugin(settings))

    settings_tuner = SettingsTunerPlugin(settings)
    plugins.register(settings_tuner)          # before drawing board

    drawing_board  = DrawingBoardPlugin(settings)
    plugins.register(drawing_board)           # last → renders on top

    # ── Startup message ───────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║           GestureMouse 2.0  started 🖐            ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  Q            Quit                               ║")
    print("║  V            Toggle visual effects              ║")
    print("║  A            Open / close Drawing Board         ║")
    print("║  ✌ hold 3 s   Open Drawing Board (gesture)       ║")
    print("║  Fist 2 s     Open / close Settings panel        ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    # ── Main loop ─────────────────────────────────────────────────────
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Failed to read frame — retrying…")
            continue

        frame = cv2.flip(frame, 1)

        # ── Hand detection ────────────────────────────────────────────
        all_hands = tracker.process(frame)
        hand_data = all_hands[0] if all_hands else HandData()

        # ── Gesture classification ────────────────────────────────────
        gesture = engine.classify(hand_data)

        # ── Mouse control (disabled while Drawing Board is open) ──────
        if drawing_board.active:
            action = MouseAction()
        else:
            action = mouse.execute(gesture, hand_data)

        # ── Plugin context ────────────────────────────────────────────
        ctx = {
            "hand_data":  hand_data,
            "gesture":    gesture,
            "action":     action,
            "mouse":      mouse,
            "_all_hands": all_hands,
        }

        # ── Plugin pipeline ───────────────────────────────────────────
        frame = plugins.run(frame, ctx)

        # ── Display ───────────────────────────────────────────────────
        display.show(frame)

        # ── Keyboard ──────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('v'):
            plugins.toggle_visuals()
        elif key == ord('d'):
            display.toggle_debug()
        elif drawing_board.on_key(key):
            pass

    cap.release()
    cv2.destroyAllWindows()
    print("GestureMouse 2.0 stopped.")


if __name__ == "__main__":
    main()
