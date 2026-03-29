"""
core/display.py
OpenCV window wrapper.
"""

import cv2


class Display:
    def __init__(self, settings):
        self.settings  = settings
        self._debug    = False
        self._win_name = "GestureMouse 2.0"
        cv2.namedWindow(self._win_name, cv2.WINDOW_NORMAL)

    def show(self, frame):
        cv2.imshow(self._win_name, frame)

    def toggle_debug(self):
        self._debug = not self._debug

    @property
    def debug(self):
        return self._debug
