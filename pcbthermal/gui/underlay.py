#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file underlay.py
@brief The helpers of the underlay (what is drawn under the temperature map: None, the copper, or the project's background image) shared by the Results maps, the
       Animation tab and the editor map: the background image read once per file and the slider-and-box pair that redraws once per finished edit.
@details The choice itself (the entry, the opacity, the View, the contour steps and the colour map) lives in `display.DisplayState`, edited in the Display popover.
         The image is read once per file (`load_underlay_image`), reduced to at most `IMAGE_MAX_PX` pixels on its longest side, and shared by every map
         (`cached_underlay_image`). `ReleaseSync` keeps the opacity slider and its 0 to 100 % box in step and calls back when the user has finished.
"""

import os

import numpy as np
from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QImage

from .. import plots

OPACITY_DEBOUNCE_MS = 250                               # Wait after the last key, wheel or arrow step before the maps are drawn again
IMAGE_MAX_PX = 2048                                     # Longest side of the picture kept for the underlay
DEFAULT_OPACITY = 70                                    # Percent of the map over the underlay

UNDERLAY_TIP = ("What is drawn under the temperature map. None: the map alone. Copper: the copper of the layer shown (grey, from the drawn zones or the "
                "imported copper) on the laminate. Image: the background image of the project, at the place and size it has on the Board tab. "
                "Only the entries that exist for this project are listed. Display only: nothing is solved again.")
OPACITY_TIP = ("Opacity of the temperature map over the underlay, 0 to 100 % (0: only the underlay, 100: the map hides it; default 70 %). "
               "The slider and the box show the same value. In the Results maps it works with an underlay; on the board it always works.")


def load_underlay_image(cfg):
    """!
    @brief Read the background image of a project for the underlay.
    @param cfg The `view["background"]` dict of the project (path, x_mm, y_mm, w_mm, h_mm) or None.
    @return plots.UnderlayImage reduced to at most IMAGE_MAX_PX pixels on its longest side, or None when there is no readable image.
    """
    if not cfg or not cfg.get("path"):
        return None
    img = QImage(cfg["path"])
    if img.isNull():
        return None
    if max(img.width(), img.height()) > IMAGE_MAX_PX:
        img = img.scaled(IMAGE_MAX_PX, IMAGE_MAX_PX, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    img = img.convertToFormat(QImage.Format_RGBA8888)
    w, h = img.width(), img.height()
    # bytesPerLine can be larger than 4 w (row padding): read the rows with their stride
    buf = np.frombuffer(img.constBits(), dtype=np.uint8, count=img.sizeInBytes()).reshape(h, img.bytesPerLine())[:, :4 * w]
    # A COPY: the buffer belongs to the QImage, which is freed when this function returns (a view would read freed memory: a garbled or
    # flipped picture, or a crash; np.ascontiguousarray returns the view itself when the rows have no padding)
    rgba = np.array(buf.reshape(h, w, 4), dtype=np.uint8, copy=True)
    return plots.UnderlayImage(rgba=rgba, x_mm=float(cfg.get("x_mm", 0.0)), y_mm=float(cfg.get("y_mm", 0.0)),
                               w_mm=float(cfg["w_mm"]), h_mm=float(cfg["h_mm"]))


def background_key(cfg):
    """!
    @brief A key that changes when the image file or its placement changes.
    @param cfg The `view["background"]` dict or None.
    @return Tuple, or None without an image.
    """
    if not cfg or not cfg.get("path"):
        return None
    try:
        stamp = os.path.getmtime(cfg["path"])
    except OSError:
        stamp = None
    return (cfg["path"], stamp, cfg.get("x_mm"), cfg.get("y_mm"), cfg.get("w_mm"), cfg.get("h_mm"))


_LAST = [None, None]                                    # [key, UnderlayImage] of the last image read: every tab shares one picture


def cached_underlay_image(cfg):
    """!
    @brief The underlay picture of a project, read once per file and placement and shared by all the tabs.
    @param cfg The `view["background"]` dict or None.
    @return plots.UnderlayImage or None.
    """
    key = background_key(cfg)
    if key is None:
        return None
    if _LAST[0] != key:
        _LAST[0], _LAST[1] = key, load_underlay_image(cfg)
    return _LAST[1]


class ReleaseSync(QObject):
    """!
    @brief Keeps a slider and a box in step and calls back only when the user has finished: the mouse is released, Enter is pressed, or a pause follows a key or the wheel.
    @details A drag redraws nothing (the box shows the value live); key, wheel and arrow steps are debounced by OPACITY_DEBOUNCE_MS so that a run of steps draws once.
    """

    def __init__(self, slider, spin, callback, parent=None):
        """!
        @param slider QSlider with the value.
        @param spin QSpinBox with the same value (typed); its keyboard tracking should be off.
        @param callback Callable(value) called once per finished edit.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.slider, self.spin, self.callback = slider, spin, callback
        self._pending = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(OPACITY_DEBOUNCE_MS)
        self.timer.timeout.connect(self.flush)
        slider.valueChanged.connect(self._slider_moved)
        slider.sliderReleased.connect(self.flush)
        spin.valueChanged.connect(self._spin_changed)
        spin.editingFinished.connect(self.flush)

    def _slider_moved(self, value):
        """!
        @brief The slider changed: show the value in the box at once; draw after the release, or after a pause for a key or the wheel.
        @param value Slider value in percent.
        """
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self._pending = True
        if not self.slider.isSliderDown():
            self.timer.start()

    def _spin_changed(self, value):
        """!
        @brief The box changed (typed and confirmed, or an arrow step): move the slider silently and draw after a pause (at once on Enter or focus loss).
        @param value Box value in percent.
        """
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self._pending = True
        self.timer.start()

    def flush(self):
        """!
        @brief Call back now if an edit is waiting.
        """
        self.timer.stop()
        if self._pending:
            self._pending = False
            self.callback(self.slider.value())

    def set_silently(self, percent):
        """!
        @brief Set both widgets without any callback and forget a waiting edit.
        @param percent Opacity 0 to 100.
        """
        self.timer.stop()
        self._pending = False
        for w in (self.slider, self.spin):
            w.blockSignals(True)
            w.setValue(percent)
            w.blockSignals(False)
