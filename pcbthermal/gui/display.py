#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file display.py
@brief How the temperature maps are drawn, as one shared choice: the display state and the Display popover of the main toolbar.
@details `DisplayState` holds what is drawn under the map (None, the copper, or the project's background image), the opacity of the map over it, the View (Current,
         Smooth, Terrain), the contour step of each map type and the colour map. The Temperature and Gradients tabs, the Animation tab and the temperature map on the
         board of the editor all read it, so they can never disagree. `DisplayPopover` is the floating panel with the controls; it is anchored under the Display button
         of the toolbar and does not take the keyboard focus away from the window (the key T still works while it is open). Display only: nothing is solved again.
"""

from PySide6.QtCore import QObject, QPoint, QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QSlider, QSpinBox, QToolButton, QVBoxLayout,
                               QWidget)

from .. import plots
from . import theme as th
from .underlay import DEFAULT_OPACITY, OPACITY_TIP, UNDERLAY_TIP, ReleaseSync, cached_underlay_image

CONTEXTS = ("editor", "temperature", "gradient", "animation", "other")   # Where the popover is opened from

VIEW_TIP = ("How the map is drawn. Current: the cells as solved. Smooth: bicubic interpolation between the cells, cosmetic (the solver resolution is the cell, "
            "nothing finer is computed). Terrain: shaded relief with contour lines, for the Temperature and Gradients maps. Nothing is solved again.")
CONTOUR_TIP = ("Distance between the contour lines of the Terrain view; every second line is thicker and labelled. One value for each kind of map: the Temperature "
               "map in K and the Gradients map in K/mm, where 'auto' (the lowest value) picks a round step from the range of the map. Used only when View is Terrain.")
CMAP_TIP = "Colour scale of every map: the Temperature and Gradients maps, the Animation and the map on the board."
OPEN_TIP = ("Display: what is drawn under the temperature map (copper or the background image), the opacity of the map, how it is drawn (Current, Smooth, Terrain), "
            "the contour step and the colour map. One choice for the Temperature, Gradients and Animation maps and the map on the board. A dot marks an active underlay.")


class DisplayState(QObject):
    """!
    @brief The single choice of how maps are drawn, shared by the Results maps, the Animation and the editor.
    """

    changed = Signal(str)                               # Name of what changed: "underlay", "opacity", "view", "contour", "cmap" or "source"

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.kind = "none"                              # What is under the map: "none", "copper" or "image"
        self.opacity = DEFAULT_OPACITY                  # Percent of the map over the underlay, 0 to 100
        self.view = "current"                           # One of plots.VIEW_MODES
        self.contour_temp = 5.0                         # Terrain contour step of the Temperature map in K
        self.contour_grad = 0.0                         # Terrain contour step of the Gradients map in K/mm (0 = auto)
        self.cmap = plots.CMAPS[0]
        self.image = None                               # plots.UnderlayImage of the project, or None
        self.cache = {}                                 # {layer: copper picture, "image": picture}: valid for one problem and one image
        self.imported, self.has_image = False, False

    def entries(self):
        """!
        @brief The underlay entries that are valid for the project.
        @return List of (label, key): None and Copper always, Image only for a hand-drawn project that has a background image.
        """
        out = [("None", "none"), ("Copper", "copper")]
        if self.has_image and not self.imported:
            out.append(("Image", "image"))
        return out

    def set_source(self, imported, cfg):
        """!
        @brief Tell the state what the project offers under the map.
        @details A Gerber (imported) project offers None and Copper only, even when it still stores an old image. The choice is kept when it is still valid and goes
                 back to None otherwise. The picture cache is emptied when the image changed.
        @param imported True when the project comes from Gerber files.
        @param cfg The `view["background"]` dict or None.
        @return True when the entries, the selection or the image changed (the maps must be drawn again).
        """
        before = ([k for _l, k in self.entries()], self.kind, self.image)
        img = None if imported else cached_underlay_image(cfg)
        if img is not self.image:
            self.cache.clear()
        self.image = img
        self.imported, self.has_image = bool(imported), img is not None
        if self.kind not in [k for _l, k in self.entries()]:
            self.kind = "none"
        after = ([k for _l, k in self.entries()], self.kind, self.image)
        if before != after:
            self.changed.emit("source")
        return before != after

    def clear_cache(self):
        """!
        @brief Forget the pictures drawn under the map (the problem changed).
        """
        self.cache.clear()

    def value(self):
        """!
        @brief The opacity of the map over the underlay.
        @return Opacity 0 to 1.
        """
        return self.opacity / 100.0

    def contour_step(self, map_kind):
        """!
        @brief The Terrain contour step of a kind of map.
        @param map_kind "temperature" or "gradient".
        @return Step in K, or in K/mm for the gradient (0 picks a round step).
        """
        return self.contour_grad if map_kind == "gradient" else self.contour_temp

    def set_kind(self, kind, notify=True):
        """!
        @brief Choose what is under the map.
        @param kind "none", "copper" or "image" (an entry that is not valid selects None).
        @param notify True to emit `changed`.
        """
        kind = kind if kind in [k for _l, k in self.entries()] else "none"
        if kind != self.kind:
            self.kind = kind
            if notify:
                self.changed.emit("underlay")

    def set_opacity(self, percent, notify=True):
        """!
        @brief Set the opacity of the map over the underlay.
        @param percent Opacity 0 to 100 (clamped).
        @param notify True to emit `changed`.
        """
        v = int(max(0, min(100, round(percent))))
        if v != self.opacity:
            self.opacity = v
            if notify:
                self.changed.emit("opacity")

    def set_view(self, mode, notify=True):
        """!
        @brief Choose how the map is drawn.
        @param mode One of plots.VIEW_MODES.
        @param notify True to emit `changed`.
        """
        if mode in plots.VIEW_MODES and mode != self.view:
            self.view = mode
            if notify:
                self.changed.emit("view")

    def set_contour(self, map_kind, value, notify=True):
        """!
        @brief Set the contour step of a kind of map.
        @param map_kind "temperature" or "gradient".
        @param value Step in K (temperature) or K/mm (gradient, 0 = auto).
        @param notify True to emit `changed`.
        """
        if map_kind == "gradient":
            if value != self.contour_grad:
                self.contour_grad = float(value)
                notify and self.changed.emit("contour")
        elif value != self.contour_temp:
            self.contour_temp = float(value)
            notify and self.changed.emit("contour")

    def set_cmap(self, name, notify=True):
        """!
        @brief Choose the colour map of every map.
        @param name Matplotlib colour map name from plots.CMAPS.
        @param notify True to emit `changed`.
        """
        if name in plots.CMAPS and name != self.cmap:
            self.cmap = name
            if notify:
                self.changed.emit("cmap")

    def reset(self):
        """!
        @brief Back to the defaults of a new project (opacity 70 %, Current view, no underlay); the colour map and the contour steps are kept.
        """
        before = (self.kind, self.opacity, self.view)
        self.kind, self.opacity, self.view = "none", DEFAULT_OPACITY, "current"
        self.cache.clear()
        if before != (self.kind, self.opacity, self.view):
            self.changed.emit("underlay")

    def active(self):
        """!
        @brief True when something is drawn under the map (the Display button shows its dot).
        @return bool.
        """
        return self.kind != "none"

    def apply(self, view, theme, map_kind="temperature"):
        """!
        @brief Put the underlay settings and the theme colours of the map into a MapView.
        @param view plots.MapView to complete.
        @param theme Theme name.
        @param map_kind "temperature" or "gradient" (not used by the view itself; kept for symmetry with `contour_step`).
        @return The same MapView.
        """
        c = th.colors(theme)

        def triplet(name):
            return tuple(QColor(c[name]).getRgbF()[:3])

        view.show_copper = self.kind != "none"
        view.underlay = "image" if self.kind == "image" else "copper"
        view.image = self.image
        view.opacity = self.value()
        view.copper_rgb, view.laminate_rgb, view.contour_color = triplet("map_copper"), triplet("map_laminate"), c["map_contour"]
        view.cache = self.cache
        return view

    def map_view(self, map_kind, theme, allow_terrain=True):
        """!
        @brief The MapView of the current choice for one kind of map.
        @param map_kind "temperature", "gradient" or "animation".
        @param theme Theme name.
        @param allow_terrain False for the Animation (the relief makes no sense in motion; Current is drawn instead).
        @return plots.MapView, or None when the map is drawn as always (Current without an underlay: the original picture, call for call).
        """
        mode = self.view if (allow_terrain or self.view != "terrain") else "current"
        step = self.contour_step(map_kind) if map_kind in ("temperature", "gradient") else 0.0
        view = self.apply(plots.MapView(mode=mode, contour_step=step), theme)
        return None if view.mode == "current" and not view.show_copper else view


class DisplayPopover(QFrame):
    """!
    @brief The floating panel of the Display button: the controls that say HOW the maps are drawn.
    @details A frameless tool window that never takes the activation or the keyboard focus on opening, so the window keeps its focus and the key T. The controls that
             do not apply in the context (the View and the Contour step in the editor, Terrain in the Animation, the Contour step unless View is Terrain) are greyed, not hidden.
    """

    def __init__(self, state, parent=None):
        """!
        @param state DisplayState to edit.
        @param parent The main window (the popover is its tool window).
        """
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)       # Does not steal the focus (macOS) when it opens
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("displayPopover")
        self.state, self.context = state, "temperature"
        self.last_control = None                                   # The control used last: the popover reopens on it
        self._busy = False

        self.underlay = QComboBox()
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(DEFAULT_OPACITY)
        self.opacity.setFixedWidth(120)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(DEFAULT_OPACITY)
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.setKeyboardTracking(False)
        self.view = QComboBox()
        for mode in plots.VIEW_MODES:
            self.view.addItem(plots.VIEW_LABELS[mode], mode)
        self.contour = QDoubleSpinBox()
        self.contour.setKeyboardTracking(False)
        self.contour_label = QLabel("Contour every")
        self.cmap = QComboBox()
        self.cmap.addItems(plots.CMAPS)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet("")                                # Colour from the palette: set in refresh()

        self.underlay.setToolTip(UNDERLAY_TIP)
        self.opacity.setToolTip(OPACITY_TIP)
        self.opacity_spin.setToolTip(OPACITY_TIP)
        self.view.setToolTip(VIEW_TIP)
        self.contour.setToolTip(CONTOUR_TIP)
        self.contour_label.setToolTip(CONTOUR_TIP)
        self.cmap.setToolTip(CMAP_TIP)

        op = QHBoxLayout()
        op.setContentsMargins(0, 0, 0, 0)
        op.addWidget(self.opacity)
        op.addWidget(self.opacity_spin)
        opw = QWidget()
        opw.setLayout(op)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self.rows = {}
        for key, label, w in (("underlay", "Underlay", self.underlay), ("opacity", "Map opacity", opw), ("view", "View", self.view),
                              ("contour", None, self.contour), ("cmap", "Colour map", self.cmap)):
            lab = self.contour_label if key == "contour" else QLabel(label)
            lab.setToolTip({"underlay": UNDERLAY_TIP, "opacity": OPACITY_TIP, "view": VIEW_TIP, "contour": CONTOUR_TIP, "cmap": CMAP_TIP}[key])
            form.addRow(lab, w)
            self.rows[key] = (lab, w)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.addLayout(form)
        lay.addWidget(self.note)

        # Opacity redraws once per finished edit (mouse released, Enter, or a pause after keys and the wheel); the box follows a drag live
        self.sync = ReleaseSync(self.opacity, self.opacity_spin, self._opacity_done, self)
        self.underlay.currentIndexChanged.connect(self._underlay_edited)
        self.view.currentIndexChanged.connect(self._view_edited)
        self.contour.valueChanged.connect(self._contour_edited)
        self.cmap.currentIndexChanged.connect(self._cmap_edited)
        for w in (self.underlay, self.opacity, self.opacity_spin, self.view, self.contour, self.cmap):
            w.installEventFilter(self)
        state.changed.connect(lambda _what: self.refresh())
        self.refresh()

    def eventFilter(self, obj, event):
        """!
        @brief Remember the control the user touched last (the popover reopens on it).
        @param obj Object that receives the event.
        @param event The event.
        @return False (the event is never consumed).
        """
        if event.type() in (event.Type.FocusIn, event.Type.MouseButtonPress, event.Type.Wheel):
            self.last_control = obj
        return False

    def set_context(self, context):
        """!
        @brief Say where the popover is opened from; the controls that apply there are enabled.
        @param context One of CONTEXTS.
        """
        self.context = context if context in CONTEXTS else "other"
        self.refresh()

    def refresh(self):
        """!
        @brief Show the state in the controls and enable the ones that apply in the context.
        """
        if self._busy:
            return
        self._busy = True
        s, ctx = self.state, self.context
        self.underlay.blockSignals(True)
        self.underlay.clear()
        for label, key in s.entries():
            self.underlay.addItem(label, key)
        self.underlay.setCurrentIndex(max(self.underlay.findData(s.kind), 0))
        self.underlay.blockSignals(False)
        self.sync.set_silently(s.opacity)
        for w in (self.view, self.cmap):
            w.blockSignals(True)
        self.view.setCurrentIndex(max(self.view.findData(s.view), 0))
        self.cmap.setCurrentIndex(max(self.cmap.findText(s.cmap), 0))
        for w in (self.view, self.cmap):
            w.blockSignals(False)
        # The contour step of the kind of map of the tab one is in; the label names it
        grad = ctx == "gradient"
        self.contour.blockSignals(True)
        if grad:
            self.contour.setRange(0.0, 20.0)
            self.contour.setDecimals(2)
            self.contour.setSingleStep(0.1)
            self.contour.setSpecialValueText("auto")
            self.contour.setSuffix(" K/mm")
            self.contour.setValue(s.contour_grad)
        else:
            self.contour.setSpecialValueText("")
            self.contour.setRange(0.5, 50.0)
            self.contour.setDecimals(1)
            self.contour.setSingleStep(0.5)
            self.contour.setSuffix(" K")
            self.contour.setValue(s.contour_temp)
        self.contour.blockSignals(False)
        self.contour_label.setText("Contour every (Gradients)" if grad else "Contour every (Temperature)")
        # What applies where: the editor map has no View or Contour; the Animation has no Terrain; the Contour step only matters with Terrain
        editor, anim = ctx == "editor", ctx == "animation"
        self.view.setEnabled(not editor)
        item = self.view.model().item(self.view.findData("terrain"))
        if item is not None:
            item.setEnabled(not anim and not editor)
        terrain = s.view == "terrain" and not anim and not editor
        self.contour.setEnabled(terrain)
        self.contour_label.setEnabled(terrain)
        # The opacity matters on the board always (the map over the copper and the parts); in the Results maps only when something is under the map
        for w in (self.opacity, self.opacity_spin, self.rows["opacity"][0]):
            w.setEnabled(editor or s.kind != "none")
        text = ""
        if editor:
            text = "On the board the map uses Underlay, Map opacity and Colour map; View and Contour apply to the Results maps."
        elif anim:
            text = "The Terrain relief is not drawn in the Animation (Current is used)."
        elif not terrain:
            text = "Contour every applies with View = Terrain."
        self.note.setText(text)
        self.note.setVisible(bool(text))
        self._busy = False

    def apply_theme(self, theme):
        """!
        @brief Give the note the muted colour of the theme.
        @param theme Theme name.
        """
        self.note.setStyleSheet(f"color: {th.colors(theme)['muted']};")

    def _underlay_edited(self, *_):
        """!
        @brief The Underlay entry changed.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if not self._busy:
            self.state.set_kind(self.underlay.currentData())

    def _opacity_done(self, percent):
        """!
        @brief The opacity edit is finished (mouse released, Enter, or a pause).
        @param percent Opacity 0 to 100.
        """
        self.state.set_opacity(percent)

    def _view_edited(self, *_):
        """!
        @brief The View entry changed.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if not self._busy:
            self.state.set_view(self.view.currentData())

    def _contour_edited(self, value):
        """!
        @brief The contour step changed: it belongs to the kind of map of the context.
        @param value Step in K or K/mm.
        """
        if not self._busy:
            self.state.set_contour("gradient" if self.context == "gradient" else "temperature", value)

    def _cmap_edited(self, *_):
        """!
        @brief The colour map changed.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if not self._busy:
            self.state.set_cmap(self.cmap.currentText())

    def flush(self):
        """!
        @brief Apply an opacity edit that is still waiting for its pause (tests and shutdown).
        """
        self.sync.flush()

    def show_under(self, button, activate=False):
        """!
        @brief Open the popover under a button, on the control used last; by default without taking the activation.
        @details The popover is kept on the screen of the button: near the right or the bottom edge it is moved left or up (the review found it drawn half off a
                 1280-pixel screen when the window sat at the right edge).
        @param button The toolbar button the popover hangs from.
        @param activate True to make the popover the active window with the keyboard in its control used last (opened from the menu, so that a keyboard user can
                        reach the controls); False for a mouse click on the button (the canvas keeps the keyboard and the key T).
        """
        self.refresh()
        self.adjustSize()
        pos = button.mapToGlobal(button.rect().bottomLeft())
        screen = button.screen()
        if screen is not None:
            area = screen.availableGeometry()
            x = min(pos.x(), area.right() + 1 - self.width())
            y = pos.y() if pos.y() + self.height() <= area.bottom() + 1 else button.mapToGlobal(button.rect().topLeft()).y() - self.height()
            pos = QPoint(max(x, area.left()), max(y, area.top()))
        self.move(pos)
        self.show()
        self.raise_()
        target = self.last_control if self.last_control is not None and self.last_control.isEnabled() else None
        if activate:
            self.activateWindow()
            target = target or next((w for w in (self.underlay, self.opacity_spin, self.cmap) if w.isEnabled()), None)
        if target is not None:
            target.setFocus(Qt.OtherFocusReason)


class DisplayButton(QToolButton):
    """!
    @brief The Display button of the toolbar: an icon with a small menu arrow, and a dot on the icon while an underlay is active.
    """

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self._theme, self._dot = "dark", False
        self.setAutoRaise(True)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setFocusPolicy(Qt.NoFocus)                       # Clicking it never takes the keyboard from the canvas (the key T)
        # The button has an icon only and paints its arrow itself: give screen readers a name (the keyboard route is View - Display settings)
        self.setAccessibleName("Display")
        self.setAccessibleDescription("Opens the Display panel: underlay, map opacity, view, contour step and colour map of the temperature maps")
        self._icon()

    def _icon(self):
        """!
        @brief Paint the icon for the theme and the dot state.
        """
        self.setIcon(th.tool_icon("display_dot" if self._dot else "display", self._theme))

    def set_theme(self, theme):
        """!
        @brief Change the theme of the icon and of the arrow.
        @param theme Theme name.
        """
        self._theme = theme
        self._icon()
        self.update()

    def set_dot(self, on):
        """!
        @brief Show or hide the dot of an active underlay.
        @param on True when an underlay is active.
        """
        if bool(on) != self._dot:
            self._dot = bool(on)
            self._icon()
        self.setProperty("dot", self._dot)

    def sizeHint(self):
        """!
        @brief Room for the icon and the arrow.
        @return QSize.
        """
        s = super().sizeHint()
        return QSize(s.width() + 10, s.height())

    def paintEvent(self, event):
        """!
        @brief Paint the button and a small downward arrow at its right edge.
        @param event The paint event.
        """
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(th.colors(self._theme)["text"])
        x, y = self.width() - 9.0, self.height() / 2.0 + 3.0
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawPolygon(QPolygonF([QPointF(x - 3, y - 1.5), QPointF(x + 3, y - 1.5), QPointF(x, y + 1.5)]))
        p.end()
