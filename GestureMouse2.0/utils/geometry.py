"""
utils/geometry.py
Shared geometry helper functions used across core and plugins.
"""

import math
from typing import Tuple


def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Euclidean distance between two (x, y) points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def normalised_to_pixel(nx: float, ny: float,
                         width: int, height: int) -> Tuple[int, int]:
    """Convert a normalised (0-1) coordinate to pixel coordinates."""
    return int(nx * width), int(ny * height)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, value))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * t
