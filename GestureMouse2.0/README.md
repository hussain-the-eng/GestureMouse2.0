<div align="center">

# GestureMouse 2.0

**Control your computer with hand gestures — no mouse, no touchpad, just a webcam.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-FF6F00?style=flat-square&logo=google&logoColor=white)](https://mediapipe.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)]()

</div>

---

## Overview

GestureMouse is a real-time computer vision application that replaces traditional mouse input with hand gestures captured from a standard webcam. It uses **MediaPipe** for 21-point hand landmark detection and maps fingertip positions and pinch distances to OS-level mouse events — move, click, right-click, drag, and scroll — all at webcam framerate with no special hardware required.

The project also ships a **two-hand gesture drawing board** that activates with a peace sign, letting both hands paint on a canvas overlaid on the camera feed.

Built as a third-year Computer Engineering project exploring the intersection of **computer vision**, **human-computer interaction**, and **real-time systems design**.

---

## Demo

> Point your index finger to move the cursor. Pinch to click. Two fingers to scroll.

| Gesture | Action |
|---|---|
| ☝️ Index finger up | Move cursor |
| 🤏 Thumb ↔ Index pinch | Left click |
| 🤏 Thumb ↔ Middle pinch | Right click |
| 🤏 Hold pinch · 6 frames | Drag |
| ✌️ Two fingers + vertical move | Scroll |
| ✌️ Peace sign (stationary) | Open Drawing Board |
| ✊ Fist | Extensible — no action by default |

---

## Features

- **Real-time cursor control** using index fingertip position mapped to screen coordinates with exponential smoothing to eliminate jitter
- **Gesture classification pipeline** — rule-based classifier operating on normalised landmark distances and finger-state vectors, running at webcam FPS
- **Two-hand drawing board** — both hands draw simultaneously on a canvas overlaid on the live camera feed, with an 8-colour toolbar, flood fill, undo stack, and PNG export
- **Plugin architecture** — every visual effect and feature is a self-contained plugin; add new features by dropping a single file into `plugins/` and registering it in `main.py`
- **MediaPipe version agnostic** — automatically detects whether the installed version uses the Tasks API (0.10+) or the legacy Solutions API (0.9.x) and selects the right backend
- **Cross-platform** — tested on Windows 10/11, macOS 13+, and Ubuntu 22.04

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/GestureMouse2.0.git
cd GestureMouse2.0

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

> **Note — MediaPipe 0.10+ first run:** The hand landmark model (~10 MB) is downloaded automatically on first launch and cached at `core/hand_landmarker.task`. Requires an internet connection once.

---

## Requirements

| Package | Version | Purpose |
|---|---|---|
| `mediapipe` | any | Hand landmark detection |
| `opencv-python` | ≥ 4.8 | Camera capture and frame rendering |
| `pyautogui` | ≥ 0.9.54 | OS-level mouse events |
| `screeninfo` | ≥ 0.8.1 | Screen resolution detection |
| `numpy` | ≥ 1.24 | Frame and canvas array operations |

Python 3.8 or higher required.

---

## Project Structure

```
GestureMouse2.0/
├── main.py                      # Entry point — wires all components together
├── requirements.txt
│
├── config/
│   └── settings.py              # All tunable parameters in one place
│
├── core/                        # Core processing pipeline
│   ├── hand_tracker.py          # MediaPipe wrapper → HandData (supports 2 hands)
│   ├── gesture_engine.py        # HandData → GestureState (rule-based classifier)
│   ├── mouse_controller.py      # GestureState → OS mouse actions via pyautogui
│   └── display.py               # OpenCV window management
│
├── plugins/                     # Self-contained feature modules
│   ├── plugin_manager.py        # BasePlugin interface + PluginManager registry
│   ├── template_plugin.py       # Starter template — copy to add a new feature
│   ├── hand_visualizer.py       # Skeleton overlay + landmark dots (both hands)
│   ├── gesture_hud.py           # On-screen HUD showing current gesture + action
│   ├── trail_effect.py          # Fading gradient trail behind the fingertip
│   ├── click_ripple.py          # Expanding ring animation on click events
│   └── drawing_board.py         # Full two-hand drawing canvas
│
└── utils/
    └── geometry.py              # Shared math helpers (dist, lerp, clamp)
```

### Architecture

The application runs as a single-threaded pipeline executed every frame:

```
Webcam frame
    └─▶  HandTracker       — MediaPipe landmark detection → list[HandData]
              └─▶  GestureEngine    — classify primary hand → GestureState
                        └─▶  MouseController  — map gesture to OS mouse event → MouseAction
                                  └─▶  PluginManager    — each plugin renders overlays onto frame
                                            └─▶  Display         — imshow
```

`HandData` is the central data structure — a normalised snapshot of one hand containing 21 landmark positions, 5 finger-up booleans, two pinch distances, and handedness. Everything downstream reads from it.

---

## Configuration

All parameters live in `config/settings.py`. No other files need changing.

| Parameter | Default | Effect |
|---|---|---|
| `CAMERA_INDEX` | `0` | Camera device index |
| `SMOOTHING_FACTOR` | `0.25` | Cursor smoothing — higher = smoother, more lag |
| `PINCH_CLICK_THRESHOLD` | `0.045` | Normalised thumb-index distance to register a click |
| `DRAG_DWELL_FRAMES` | `6` | Frames held in pinch before drag activates |
| `CLICK_COOLDOWN_FRAMES` | `12` | Minimum frames between clicks — prevents double-fire |
| `MARGIN_*` | `0.10` | Dead-zone fraction on each edge of the frame |
| `TRAIL_LENGTH` | `25` | Number of frames kept in the cursor trail |
| `DRAW_DWELL_TIME` | `0.8` | Seconds hovering a toolbar button before auto-click |
| `DRAW_DEFAULT_SIZE` | `8` | Initial brush size in pixels |

---

## Drawing Board

Activate with the **`A`** key or hold a **✌️ peace sign**.

Both hands draw simultaneously — right hand defaults to red, left hand to green. Colours are changed per-hand from the toolbar.

**Drawing gesture:** extend only the index finger. Any other hand shape lifts the pen. Hover the index fingertip over a toolbar button for 0.8 s (dwell) or pinch to click it instantly.

| Toolbar Button | Function |
|---|---|
| ✏ Draw | Freehand stroke |
| 🪣 Fill | Flood-fill region on pinch |
| ⬜ Erase | Erase (3× brush radius) |
| `─` / `+` | Brush size down / up |
| Colour swatches | Set active hand colour |
| Undo | Revert last stroke (up to 20 steps) |
| Clear | Wipe canvas |
| Save | Export PNG → `~/Pictures/GestureMouse/` |
| ✕ Exit | Return to mouse mode |

**Keyboard shortcuts inside the board:**

| Key | Action |
|---|---|
| `A` or `ESC` | Exit drawing board |
| `Z` | Undo |

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `Q` | Quit |
| `V` | Toggle all visual effects |
| `D` | Toggle debug overlay |
| `A` | Open / close Drawing Board |

---

## Extending the Project

### Adding a plugin

1. Copy `plugins/template_plugin.py` → `plugins/my_feature.py`
2. Set `name = "MyFeature"` and implement `process(frame, ctx)`
3. Register it in `main.py`:

```python
from plugins.my_feature import MyFeaturePlugin
plugins.register(MyFeaturePlugin(settings))
```

The `ctx` dictionary available inside every plugin:

```python
ctx["hand_data"]    # HandData  — primary hand (first detected)
ctx["gesture"]      # GestureState  — .gesture, .label, .scroll_delta
ctx["action"]       # MouseAction   — .moved, .left_click, .right_click, .drag_active, .screen_pos
ctx["mouse"]        # MouseController — .last_screen_pos
ctx["_all_hands"]   # list[HandData] — all detected hands (0–2)
```

### Adding a gesture

Open `core/gesture_engine.py` and insert a rule in `GestureEngine.classify()`:

```python
# Example: thumb + pinky extended ("call me" 🤙)
if fu[0] and fu[4] and not fu[1] and not fu[2] and not fu[3]:
    state.gesture = Gesture.NONE  # or define a new Gesture constant
    state.label   = "Call Me 🤙"
    return state
```

Handle the new gesture in `core/mouse_controller.py` or a dedicated plugin.

---

## Troubleshooting

**Camera not opening**
Try setting `CAMERA_INDEX = 1` or `2` in `config/settings.py`.

**Cursor jitter**
Increase `SMOOTHING_FACTOR` to `0.4`–`0.6`. Good, even lighting also makes a significant difference — MediaPipe landmark confidence drops sharply in low light.

**Clicks firing constantly**
Increase `PINCH_CLICK_THRESHOLD` (try `0.06`) and `CLICK_COOLDOWN_FRAMES` (try `20`).

**Slow / laggy**
Lower `FRAME_WIDTH` and `FRAME_HEIGHT` in settings. If running on a CPU-only machine, also try reducing `CAMERA_FPS` to `15`.

**Drawing Board only detects one hand**
Both hands must be fully visible in the frame and well-lit. MediaPipe assigns Left/Right labels relative to the mirrored frame — ensure the camera is flipped (already done by default in `main.py`).

**macOS — cursor doesn't move**
Grant Accessibility permission: System Settings → Privacy & Security → Accessibility → Terminal ✓
Grant Camera permission: System Settings → Privacy & Security → Camera → Terminal ✓

**Windows — permission error**
Run the terminal as Administrator, or whitelist `python.exe` in your antivirus if pyautogui mouse events are being blocked.

---

## Future Work

- [ ] VIDEO mode tracking for improved FPS (MediaPipe temporal optimisation)
- [ ] Frame-skip option to reduce CPU load on slower machines  
- [ ] Real-time settings tuning panel (adjust thresholds without restarting)
- [ ] Additional brush types in the drawing board (spray, calligraphy)
- [ ] Multi-monitor support — select target screen from settings
- [ ] Gesture macro recorder — map a gesture sequence to a keyboard shortcut
- [ ] Mirror/symmetry drawing mode on the canvas

---

## License

MIT License — see `LICENSE` for details.

---

<div align="center">
Built with Python · MediaPipe · OpenCV
</div>
