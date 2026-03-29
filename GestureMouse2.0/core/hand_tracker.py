"""
core/hand_tracker.py
MediaPipe wrapper that tracks up to TWO hands and returns HandData objects.

Performance features
────────────────────
  • VIDEO mode   — inter-frame tracking (faster than IMAGE mode)
  • Frame skip   — MediaPipe runs every DETECTION_INTERVAL frames;
                   last result reused in between (halves CPU load)
  • Small input  — detection runs on DETECTION_SCALE × frame;
                   display stays full resolution

Supports both MediaPipe API generations automatically:
  • 0.10+  Tasks API  (HandLandmarker)
  • 0.9.x  Solutions API (mp.solutions.hands)

On first run with 0.10+, the hand model (~10 MB) is downloaded once
and saved as:  core/hand_landmarker.task  (next to this file)

HandData fields
───────────────
  detected          bool
  handedness        "Left" | "Right"
  landmarks         list of (nx, ny, nz)   — normalised 0-1
  fingertips        list of (nx, ny)        — 5 fingertips
  fingers_up        list of 5 bools
  pinch_index_dist  float   thumb ↔ index distance (normalised)
  pinch_middle_dist float   thumb ↔ middle distance (normalised)
  index_tip         (nx, ny)
  wrist             (nx, ny)
"""

import os
import math
import time
import urllib.request

# ── Perf constants ────────────────────────────────────────────────────────────
DETECTION_INTERVAL = 2      # run MediaPipe every N frames (1 = every frame)
DETECTION_SCALE    = 0.5    # resize to this fraction before detection

# ── Landmark indices ──────────────────────────────────────────────────────────
FINGER_TIPS = [4, 8, 12, 16, 20]
FINGER_PIPS = [3, 7, 11, 15, 19]

# ── Model path / URLs ─────────────────────────────────────────────────────────
_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "hand_landmarker.task")
_MODEL_URLS = [
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
    "https://github.com/google-ai-edge/mediapipe/releases/download/v0.10.14/hand_landmarker.task",
    "https://huggingface.co/Xenova/mediapipe-hand-landmarker/resolve/main/hand_landmarker.task",
]
_MODEL_MIN_BYTES = 5_000_000
_CHUNK           = 32_768
_TIMEOUT         = 30


# ── HandData ──────────────────────────────────────────────────────────────────

class HandData:
    __slots__ = (
        "detected", "handedness",
        "landmarks", "fingertips",
        "fingers_up",
        "pinch_index_dist",
        "pinch_middle_dist",
        "index_tip",
        "wrist",
    )

    def __init__(self):
        self.detected          = False
        self.handedness        = "Right"
        self.landmarks         = []
        self.fingertips        = []
        self.fingers_up        = [False] * 5
        self.pinch_index_dist  = 1.0
        self.pinch_middle_dist = 1.0
        self.index_tip         = (0.5, 0.5)
        self.wrist             = (0.5, 0.9)


def _build_from_landmarks(lm, handedness_label: str) -> HandData:
    hd            = HandData()
    hd.detected   = True
    hd.handedness = handedness_label

    hd.landmarks  = [(p.x, p.y, p.z) for p in lm]
    hd.fingertips = [(lm[i].x, lm[i].y) for i in FINGER_TIPS]
    hd.index_tip  = (lm[8].x, lm[8].y)
    hd.wrist      = (lm[0].x, lm[0].y)

    fu    = [False] * 5
    fu[0] = lm[4].x < lm[3].x if handedness_label == "Right" else lm[4].x > lm[3].x
    for i in range(1, 5):
        fu[i] = lm[FINGER_TIPS[i]].y < lm[FINGER_PIPS[i]].y
    hd.fingers_up = fu

    def d(a, b):
        return math.hypot(lm[a].x - lm[b].x, lm[a].y - lm[b].y)

    hd.pinch_index_dist  = d(4, 8)
    hd.pinch_middle_dist = d(4, 12)
    return hd


# ── Model download ────────────────────────────────────────────────────────────

def _model_valid() -> bool:
    if not os.path.exists(_MODEL_PATH):
        return False
    if os.path.getsize(_MODEL_PATH) < _MODEL_MIN_BYTES:
        print("[HandTracker] Corrupt/partial model — removing.")
        os.remove(_MODEL_PATH)
        return False
    return True


def _try_download(url: str, tmp: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GestureMouse/2.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(_CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = min(100, downloaded * 100 // total)
                        bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                        print(f"\r  [{bar}] {pct:3d}%  {downloaded/1e6:.1f} MB",
                              end="", flush=True)
                    else:
                        print(f"\r  {downloaded/1e6:.1f} MB...", end="", flush=True)
        print()
        if os.path.getsize(tmp) < _MODEL_MIN_BYTES:
            os.remove(tmp)
            return False
        return True
    except Exception as e:
        print(f"\n  Error: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def _ensure_model() -> bool:
    if _model_valid():
        return True
    tmp = _MODEL_PATH + ".tmp"
    print()
    print("=" * 62)
    print("  GestureMouse 2.0 — downloading hand landmark model (~10 MB)")
    print(f"  Destination: {_MODEL_PATH}")
    print("=" * 62)
    for i, url in enumerate(_MODEL_URLS, 1):
        print(f"\n  Source {i}/{len(_MODEL_URLS)}: {url[:70]}")
        if _try_download(url, tmp):
            if os.path.exists(_MODEL_PATH):
                os.remove(_MODEL_PATH)
            os.rename(tmp, _MODEL_PATH)
            print(f"  Saved OK ({os.path.getsize(_MODEL_PATH)/1e6:.1f} MB)\n")
            return True
        print(f"  Source {i} failed, trying next...")
    print()
    print("=" * 62)
    print("  All sources failed.  Manual download options:")
    print(f"  1) Download: {_MODEL_URLS[0]}")
    print(f"     Save as:  {_MODEL_PATH}")
    print("  2) Downgrade:  pip install mediapipe==0.9.3")
    print("=" * 62)
    return False


# ── Tasks backend (mediapipe 0.10+) ──────────────────────────────────────────
# Uses VIDEO mode: MediaPipe maintains temporal state between calls,
# which is faster and smoother than IMAGE mode (re-detects from scratch every frame).

class _TasksBackend:
    def __init__(self, settings):
        import mediapipe as mp
        from mediapipe.tasks.python import vision
        from mediapipe.tasks        import python as mp_python

        if not _ensure_model():
            raise RuntimeError("Hand landmark model unavailable.")

        options = vision.HandLandmarkerOptions(
            base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode                  = vision.RunningMode.VIDEO,   # ← VIDEO mode
            num_hands                     = 2,
            min_hand_detection_confidence = settings.MIN_DETECTION_CONF,
            min_hand_presence_confidence  = settings.MIN_TRACKING_CONF,
            min_tracking_confidence       = settings.MIN_TRACKING_CONF,
        )
        self._detector  = vision.HandLandmarker.create_from_options(options)
        self._mp        = mp
        self._timestamp = 0   # VIDEO mode needs monotonically increasing timestamps

    def process(self, frame) -> list:
        import cv2
        # Resize frame before detection — much cheaper for MediaPipe
        small  = cv2.resize(frame,
                            (int(frame.shape[1] * DETECTION_SCALE),
                             int(frame.shape[0] * DETECTION_SCALE)))
        rgb    = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        mp_img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        # VIDEO mode requires a timestamp in milliseconds
        self._timestamp += 1
        result = self._detector.detect_for_video(mp_img, self._timestamp)

        hands = []
        for lm_list, handedness_list in zip(result.hand_landmarks, result.handedness):
            label = handedness_list[0].category_name
            hands.append(_build_from_landmarks(lm_list, label))
        return hands


# ── Solutions backend (mediapipe 0.9.x) ──────────────────────────────────────

class _SolutionsBackend:
    def __init__(self, settings):
        import mediapipe as mp
        self._hands = mp.solutions.hands.Hands(
            static_image_mode        = False,
            max_num_hands            = 2,
            min_detection_confidence = settings.MIN_DETECTION_CONF,
            min_tracking_confidence  = settings.MIN_TRACKING_CONF,
        )

    def process(self, frame) -> list:
        import cv2
        small   = cv2.resize(frame,
                             (int(frame.shape[1] * DETECTION_SCALE),
                              int(frame.shape[0] * DETECTION_SCALE)))
        rgb     = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        hands   = []
        if results.multi_hand_landmarks:
            for lm, cls in zip(results.multi_hand_landmarks,
                               results.multi_handedness):
                label = cls.classification[0].label
                hands.append(_build_from_landmarks(lm.landmark, label))
        return hands


# ── HandTracker ───────────────────────────────────────────────────────────────

class HandTracker:
    """
    Tracks up to 2 hands per frame.

    Performance optimisations applied here:
      1. Frame skipping  — MediaPipe only runs every DETECTION_INTERVAL frames.
                           Intermediate frames reuse the cached result.
      2. Scaled input    — frame shrunk to DETECTION_SCALE before detection.
      3. VIDEO mode      — Tasks backend maintains temporal state (faster tracking).
    """

    def __init__(self, settings):
        self.settings      = settings
        self._backend      = None
        self._frame_count  = 0
        self._cached       = []   # last detection result, reused on skip frames

        try:
            import mediapipe as mp
        except ImportError:
            print("[ERROR] mediapipe not installed.  Run:  pip install mediapipe")
            return

        has_tasks     = hasattr(mp, "tasks")
        has_solutions = hasattr(mp, "solutions") and hasattr(mp.solutions, "hands")

        if has_tasks:
            try:
                self._backend = _TasksBackend(settings)
                print("[HandTracker] Ready — Tasks API (VIDEO mode, frame-skip, scaled input)")
            except Exception as e:
                print(f"[HandTracker] Tasks backend failed: {e}")
                if has_solutions:
                    print("[HandTracker] Falling back to Solutions API")
                    self._backend = _SolutionsBackend(settings)
                else:
                    print("[ERROR] No working MediaPipe backend found.")
                    print("        Try:  pip install mediapipe==0.9.3")
        elif has_solutions:
            self._backend = _SolutionsBackend(settings)
            print("[HandTracker] Ready — Solutions API (frame-skip, scaled input)")
        else:
            print("[ERROR] Unrecognised MediaPipe version.")

    def process(self, frame) -> list:
        """
        Returns list[HandData] (0-2 items).
        Runs MediaPipe every DETECTION_INTERVAL frames; returns cached result otherwise.
        """
        if self._backend is None:
            return []

        self._frame_count += 1
        if self._frame_count % DETECTION_INTERVAL == 0:
            try:
                self._cached = self._backend.process(frame)
            except Exception as e:
                print(f"[HandTracker] detection error: {e}")
                self._cached = []

        return self._cached

    def process_primary(self, frame) -> HandData:
        hands = self.process(frame)
        return hands[0] if hands else HandData()
