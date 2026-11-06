#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file underlay.py
@brief The underlay selector shared by the Results maps, the Animation tab and the editor overlay: what is drawn under the temperature map
       (None, the copper, or the project's background image) and the opacity of the map over it.
@details One combo (`UnderlayControls.combo`) lists only the entries that are valid for the project: Copper always (the drawn zones, or the
         imported copper of a Gerber project) and Image only for a hand-drawn project that has a background image. The opacity is a slider and a
         0 to 100 % box holding one value (default 70 %). The image is read once per file (`load_underlay_image`), reduced to at most
         `IMAGE_MAX_PX` pixels on its longest side, and kept in the controls with the cache of the pictures drawn under the map.
"""

import os

import numpy as np
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QComboBox, QLabel, QSlider, QSpinBox

from .. import plots
from . import theme as th

OPACITY_DEBOUNCE_MS = 250                               # Wait after the last key, wheel or arrow step before the maps are drawn again
IMAGE_MAX_PX = 2048                                     # Longest side of the picture kept for the underlay
DEFAULT_OPACITY = 70                                    # Percent of the map over the underlay

UNDERLAY_TIP = ("What is drawn under the temperature map. None: the map alone. Copper: the copper of the layer shown (grey, from the drawn zones or the "
                "imported copper) on the laminate. Image: the background image of the project, at the place and size it has on the Board tab. "
                "Only the entries that exist for this project are listed. Display only: nothing is solved again.")
OPACITY_TIP = ("Opacity of the temperature map over the underlay, 0 to 100 % (0: only the underlay, 100: the map hides it; default 70 %). "
               "The slider and the box show the same value. Used only when the underlay is not None.")


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


class UnderlayControls(QObject):
    """!
    @brief The Underlay combo and the opacity pair (slider and box), with the image and the cache of the pictures drawn under the map.
    """

    changed = Signal()                                  # The user changed the underlay or the opacity

    def __init__(self, parent=None):
        """!
        @param parent Qt parent (the tab that lays the widgets out).
        """
        super().__init__(parent)
        self.combo = QComboBox()
        self.label = QLabel("Underlay")
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(DEFAULT_OPACITY)
        self.opacity.setFixedWidth(110)
        self.opacity_spin = QSpinBox()                  # The same value as the slider, typed
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(DEFAULT_OPACITY)
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.setKeyboardTracking(False)
        self.opacity_label = QLabel("Opacity")
        self.combo.setToolTip(UNDERLAY_TIP)
        self.opacity.setToolTip(OPACITY_TIP)
        self.opacity_spin.setToolTip(OPACITY_TIP)
        self.image = None                               # plots.UnderlayImage of the project, or None
        self.cache = {}                                 # {layer: copper picture, "image": picture}: valid for one problem and one image
        self._imported, self._has_image = False, False
        self._fill()
        self.combo.currentIndexChanged.connect(self._edited)
        # The opacity redraws the maps once per finished edit (mouse released, Enter, or a pause after keys and the wheel), the box follows a drag live
        self.sync = ReleaseSync(self.opacity, self.opacity_spin, lambda _v: self._edited(), self)

    def widgets(self):
        """!
        @brief The widgets to lay out, in order.
        @return List: label, combo, opacity label, slider, box.
        """
        return [self.label, self.combo, self.opacity_label, self.opacity, self.opacity_spin]

    def kind(self):
        """!
        @brief What is drawn under the map now.
        @return "none", "copper" or "image".
        """
        return self.combo.currentData() or "none"

    def value(self):
        """!
        @brief The opacity of the map over the underlay.
        @return Opacity 0 to 1.
        """
        return self.opacity.value() / 100.0

    def _fill(self, keep="none"):
        """!
        @brief Fill the combo with the entries that are valid for the project and select `keep` when it is still valid (else None).
        @param keep Data of the entry to select.
        """
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("None", "none")
        self.combo.addItem("Copper", "copper")
        if self._has_image and not self._imported:
            self.combo.addItem("Image", "image")
        i = self.combo.findData(keep)
        self.combo.setCurrentIndex(max(i, 0))
        self.combo.blockSignals(False)
        self._enable()

    def set_source(self, imported, cfg, image=None):
        """!
        @brief Tell the controls what the project offers: which entries are valid and the image.
        @details A Gerber (imported) project offers None and Copper only, even when it still stores an old image. The choice is kept when it is
                 still valid and goes back to None otherwise. The picture cache is emptied when the image changed.
        @param imported True when the project comes from Gerber files.
        @param cfg The `view["background"]` dict or None.
        @param image The plots.UnderlayImage already read for `cfg` (None: read it here).
        @return True when the list, the selection or the image changed (the maps must be drawn again).
        """
        before = ([self.combo.itemData(i) for i in range(self.combo.count())], self.kind(), self.image)
        img = image if image is not None else (None if imported else cached_underlay_image(cfg))
        changed_image = (img is None) != (self.image is None) or (img is not None and self.image is not None and img is not self.image)
        self.image = img
        self._imported, self._has_image = bool(imported), img is not None
        if changed_image:
            self.cache.clear()
        self._fill(self.kind())
        return before != ([self.combo.itemData(i) for i in range(self.combo.count())], self.kind(), self.image)

    def clear_cache(self):
        """!
        @brief Forget the pictures drawn under the map (the problem changed).
        """
        self.cache.clear()

    def _enable(self):
        """!
        @brief The opacity matters only when something is drawn under the map.
        """
        on = self.kind() != "none"
        for w in (self.opacity_label, self.opacity, self.opacity_spin):
            w.setEnabled(on)

    def flush(self):
        """!
        @brief Apply an opacity edit that is still waiting for its pause (tests and shutdown).
        """
        self.sync.flush()

    def _edited(self, *_):
        """!
        @brief The user edited a control.
        @param _ Ignored (the value carried by the Qt signal).
        """
        self._enable()
        self.changed.emit()

    def set_opacity(self, percent):
        """!
        @brief Set the opacity pair without a signal.
        @param percent Opacity 0 to 100.
        """
        self.sync.set_silently(int(max(0, min(100, round(percent)))))

    def set_kind(self, kind):
        """!
        @brief Select an entry without a signal.
        @param kind "none", "copper" or "image" (an entry that is not listed selects None).
        """
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(max(self.combo.findData(kind), 0))
        self.combo.blockSignals(False)
        self._enable()

    def copy_from(self, other):
        """!
        @brief Take the choice and the opacity of other controls (no signal).
        @param other UnderlayControls.
        """
        self.set_kind(other.kind())
        self.set_opacity(other.opacity.value())

    def apply(self, view, theme):
        """!
        @brief Put the underlay settings and the theme colours of the map into a MapView.
        @param view plots.MapView to complete.
        @param theme Theme name.
        @return The same MapView.
        """
        c = th.colors(theme)

        def triplet(name):
            return tuple(QColor(c[name]).getRgbF()[:3])

        kind = self.kind()
        view.show_copper = kind != "none"
        view.underlay = "image" if kind == "image" else "copper"
        view.image = self.image
        view.opacity = self.value()
        view.copper_rgb, view.laminate_rgb, view.contour_color = triplet("map_copper"), triplet("map_laminate"), c["map_contour"]
        view.cache = self.cache
        return view
