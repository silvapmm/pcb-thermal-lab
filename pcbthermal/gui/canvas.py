#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file canvas.py
@brief Interactive board editor: zoom, pan, grid, drawing tools, selection, vertex editing.

The scene is in millimetres with the y axis pointing up (the view flips it), so scene
coordinates are the board coordinates the physics core uses.
"""

import os
import numpy as np
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QFontMetrics, QPainterPath, QBrush, QColor, QCursor, QImage, QPainter, QPen, QPixmap, QPolygonF,
                           QMouseEvent, QTransform)
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsPixmapItem, QGraphicsPolygonItem,
                               QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView,
                               QMenu, QStyle)

from .. import copper, defaults
from ..geometry import insert_vertex, nearest_vertex, polygon_is_simple
from . import theme as th
from ..numfmt import num
from ..package import background_bytes as package_background_bytes

OVERLAY_SMOOTH_FACTOR = 8              # View Smooth on the board: the temperatures are interpolated on a grid this many times finer than the cells ...
OVERLAY_SMOOTH_PIXELS = 2048           # ... with at most this many pixels on the longest side (a 0.25 mm cell on a 200 mm board: 2 times, 6 MB of colours)
COPPER_DISPLAY_PIXELS = 4096          # Longest side (pixels) of the reduced mask that is drawn under the elements (4096 keeps the 0.1 mm pixel of the 285 x 95 mm CO60 whole: 2850 x 951)
_GRID_STEPS = (0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100, 200)


def _is_axis_aligned_rect(pts):
    """!
    @brief True if four points form an axis-aligned rectangle (in drawing order).
    @param pts Array (4, 2).
    @return bool.
    """
    if len(pts) != 4:
        return False
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        if not (abs(a[0] - b[0]) < 1e-9 or abs(a[1] - b[1]) < 1e-9):
            return False
    return True


def _clamped_position(item, value):
    """!
    @brief Position for a dragged item: snapped to the grid and kept inside the board.
    @details The shape of the item (in its own coordinates) must stay inside the board rectangle, so a part, a zone or a via cannot be dragged off the board.
    @param item ElementItem or ViaItem being moved (has `origin`, the position at which its shape is at the document coordinates).
    @param value The position proposed by Qt (QPointF).
    @return QPointF to apply.
    """
    view = item.view
    x, y = value.x(), value.y()
    if view.snap > 0:
        s = view.snap
        x, y = round(x / s) * s, round(y / s) * s
    b = view.doc.problem.board
    box = item.polygon().boundingRect() if hasattr(item, "polygon") else item.rect()      # Geometry only, without the pen
    # Allowed range of the position: the shape's bounding box must lie in [0, W] x [0, H] (mm)
    lo_x, hi_x = -box.left(), b.width * 1000.0 - box.right()
    lo_y, hi_y = -box.top(), b.height * 1000.0 - box.bottom()
    # A shape larger than the board cannot be placed inside it: it stays where it is
    x = min(max(x, lo_x), hi_x) if lo_x <= hi_x + 1e-9 else item.origin.x()
    y = min(max(y, lo_y), hi_y) if lo_y <= hi_y + 1e-9 else item.origin.y()
    return QPointF(x, y)


def reduced_coverage(coverage, target=COPPER_DISPLAY_PIXELS):
    """!
    @brief Reduce a coverage mask for display by the integer factor that brings its longest side to at most `target` pixels (block mean).
    @details The reduction is done once per mask and cached by the canvas; only the rows and columns that fill whole blocks are used (less than one block, a fraction of a
             percent of the board, is left out at the right and bottom edges), and the sum runs in 32 bits, so no temporary larger than the result is made.
    @param coverage uint8 array (rows, columns), 0 to 255.
    @param target Largest side of the result in pixels.
    @return tuple (uint8 array (rows', columns'), factor) with factor the number of mask pixels per displayed pixel.
    """
    f = max(1, int(np.ceil(max(coverage.shape) / float(target))))
    if f == 1:
        return np.ascontiguousarray(coverage), 1
    r, c = (coverage.shape[0] // f) * f, (coverage.shape[1] // f) * f
    if r == 0 or c == 0:                                     # A mask thinner than one block: keep it as it is
        return np.ascontiguousarray(coverage), 1
    blocks = coverage[:r, :c].reshape(r // f, f, c // f, f)
    return (blocks.sum(axis=(1, 3), dtype=np.uint32) // (f * f)).astype(np.uint8), f


class ElementItem(QGraphicsPolygonItem):
    """!
    @brief A zone, heater or heatsink polygon on the canvas.
    """

    def __init__(self, view, kind, index, polygon_mm, label, layer):
        """!
        @param view Owning BoardView.
        @param kind "zone", "heater" or "heatsink".
        @param index Index in the problem list.
        @param polygon_mm Array (n, 2) in mm.
        @param label Text shown at the centroid.
        @param layer 0-based layer of the element.
        """
        super().__init__(QPolygonF([QPointF(x, y) for x, y in polygon_mm]))
        self.view, self.kind, self.index, self.layer = view, kind, index, layer
        self.origin = QPointF(0.0, 0.0)                 # The polygon holds absolute coordinates: a move is the position
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.label = None
        if label:
            self.label = QGraphicsSimpleTextItem(label, self)
            self.label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            br = self.boundingRect()
            # Heaters are labelled at the centre; zones and heatsinks in the top-left corner so labels do not collide
            if kind == "heater":
                self.label.setPos(br.center().x(), br.center().y())
            else:
                self.label.setPos(br.left() + 0.5, br.bottom() - 0.5)     # y points up: bottom() is the top edge
            self.label.setBrush(QBrush(QColor(th.colors(self.view.theme)["on_element"])))
        self.restyle()

    def lift_label(self):
        """!
        @brief Make the name a top-level item above the vias (z 6): as a child it would stay inside the z of its element (3) and the vias (4) would cover it.
        @details The label takes no mouse button, so the hit-testing of the elements is unchanged; it follows the element when it moves (`itemChange`).
        """
        if self.label is None or self.label.parentItem() is None:
            return
        self._label_base = QPointF(self.label.pos())            # The element sits at the origin when the scene is built
        self.label.setParentItem(None)
        self.label.setZValue(6)
        self.label.setOpacity(self.opacity())
        self.label.setAcceptedMouseButtons(Qt.NoButton)
        self.label.setPos(self._label_base + self.pos())

    def restyle(self):
        """!
        @brief Apply the fill and outline of the element kind and its selection state.
        """
        c = th.colors(self.view.theme)
        base = {"zone": c["copper"], "heater": c["heater"], "heatsink": c["heatsink"]}[self.kind]
        alpha = {"zone": 70, "heater": 120, "heatsink": 70}[self.kind]
        self.setBrush(QBrush(th.qcolor(base, alpha)))
        pen = QPen(QColor(c["selection"]) if self.isSelected() else QColor(base), 0)
        pen.setCosmetic(True)
        pen.setWidthF(2.2 if self.isSelected() else 1.4)
        if self.kind == "heatsink" and not getattr(self, "is_block", False):
            pen.setStyle(Qt.DashLine)
        self.setPen(pen)
        self.setZValue({"zone": 1, "heatsink": 2, "heater": 3}[self.kind] + (0.5 if self.isSelected() else 0))

    def itemChange(self, change, value):
        """!
        @brief Snap the position while dragging and restyle on selection changes.
        @param change Kind of change announced by Qt (QGraphicsItem.GraphicsItemChange).
        @param value The value proposed by Qt (a QPointF position or the new selection state).
        @return The value Qt should apply (the position is snapped to the grid while dragging).
        """
        if change == QGraphicsItem.ItemPositionChange and self.scene() is not None and not self.view._rebuilding:
            return _clamped_position(self, value)
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.restyle()
        if change == QGraphicsItem.ItemPositionHasChanged and getattr(self, "_label_base", None) is not None and self.label.parentItem() is None:
            self.label.setPos(self._label_base + self.pos())
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        """!
        @brief Paint without Qt's default dashed selection rectangle (the outline shows the selection).
        @param painter QPainter to draw with.
        @param option QStyleOptionGraphicsItem; its selected flag is cleared so Qt draws no default selection box.
        @param widget Optional widget being painted on.
        """
        option.state &= ~QStyle.State_Selected
        super().paint(painter, option, widget)


class ViaItem(QGraphicsEllipseItem):
    """!
    @brief A via drawn as a ring.
    """

    def __init__(self, view, index, x_mm, y_mm, diameter_mm):
        """!
        @param view Owning BoardView.
        @param index Index in the problem list.
        @param x_mm X in mm.
        @param y_mm Y in mm.
        @param diameter_mm Hole diameter in mm.
        """
        r = max(diameter_mm / 2.0, 0.3)
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.view, self.kind, self.index, self.layer = view, "via", index, -1
        self.origin = QPointF(x_mm, y_mm)               # Its position is absolute: a move is the position minus this origin
        self.setPos(x_mm, y_mm)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(4)
        self.restyle()

    def shape(self):
        """!
        @brief The area that answers a click: the drawn disc, without the pen.
        @details The default shape strokes the outline with the pen width in scene units, and the cosmetic pen is 2 (mm here), so a via of 0.3 mm answered clicks 1.3 mm away
                 and in a dense array the neighbour was picked. The tolerance around the centre is handled by BoardView.nearest_via, in pixels.
        @return QPainterPath of the disc.
        """
        path = QPainterPath()
        path.addEllipse(self.rect())
        return path

    def restyle(self):
        """!
        @brief Apply the via colours and the selection highlight.
        """
        c = th.colors(self.view.theme)
        pen = QPen(QColor(c["selection"]) if self.isSelected() else QColor(c["via"]))
        pen.setCosmetic(True)
        pen.setWidthF(2.0)
        self.setPen(pen)
        self.setBrush(QBrush(th.qcolor(c["via"], 200)))

    def itemChange(self, change, value):
        """!
        @brief Snap while dragging and restyle on selection changes.
        @param change Kind of change announced by Qt (QGraphicsItem.GraphicsItemChange).
        @param value The value proposed by Qt (a QPointF position or the new selection state).
        @return The value Qt should apply (the position is snapped to the grid while dragging).
        """
        if change == QGraphicsItem.ItemPositionChange and self.scene() is not None and not self.view._rebuilding:
            return _clamped_position(self, value)
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.restyle()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        """!
        @brief Paint without Qt's default selection rectangle.
        @param painter QPainter to draw with.
        @param option QStyleOptionGraphicsItem; its selected flag is cleared so Qt draws no default selection box.
        @param widget Optional widget being painted on.
        """
        option.state &= ~QStyle.State_Selected
        super().paint(painter, option, widget)


class VertexHandle(QGraphicsRectItem):
    """!
    @brief A draggable handle on a vertex of the selected polygon.
    """

    def __init__(self, view, index, pos):
        """!
        @param view Owning BoardView.
        @param index Vertex index.
        @param pos QPointF in mm.
        """
        super().__init__(-4, -4, 8, 8)
        self.view, self.index = view, index
        # Not ItemIsMovable: Qt moves every selected movable item with the one that is dragged, which dragged the whole selected polygon along with its handle.
        # The handle follows the mouse by itself (mouseMoveEvent) and only reshapes the polygon.
        self.setFlags(QGraphicsItem.ItemIgnoresTransformations | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        c = th.colors(view.theme)
        self.setBrush(QBrush(QColor(c["selection"])))
        pen = QPen(QColor(c["accent"]))
        pen.setWidthF(1.5)
        self.setPen(pen)
        self.setZValue(20)
        self.setPos(pos)
        self.setCursor(Qt.SizeAllCursor)

    def itemChange(self, change, value):
        """!
        @brief Snap and forward the move to the view so the polygon follows the handle.
        @param change Kind of change announced by Qt (QGraphicsItem.GraphicsItemChange).
        @param value The value proposed by Qt (a QPointF position or the new selection state).
        @return The value Qt should apply (the position is snapped to the grid while dragging).
        """
        if change == QGraphicsItem.ItemPositionChange and self.scene() is not None:
            s = self.view.snap
            if s > 0:
                value = QPointF(round(value.x() / s) * s, round(value.y() / s) * s)
            if not self.view._handle_lock:
                self.view._handle_moved(self.index, value)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        """!
        @brief Take the click so the polygon under the handle is not dragged or reselected.
        @param event QGraphicsSceneMouseEvent of the press.
        """
        event.accept()

    def mouseMoveEvent(self, event):
        """!
        @brief Follow the mouse; itemChange snaps the position and reshapes the polygon live.
        @param event QGraphicsSceneMouseEvent of the move.
        """
        self.setPos(event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event):
        """!
        @brief Commit the new polygon when the drag ends.
        @param event QGraphicsSceneMouseEvent of the release.
        """
        super().mouseReleaseEvent(event)
        self.view._handles_committed()


class BoardView(QGraphicsView):
    """!
    @brief The board canvas.
    """

    COLOURBAR_STRIP = 96                   # Pixels kept free at the right at fit zoom while the temperature overlay is shown
    selection_changed = Signal(list)       # [(kind, index), ...]
    cursor_moved = Signal(float, float)    # mm
    message = Signal(str)                  # status text
    element_created = Signal(str, int)     # kind, index
    card_clicked = Signal(object)          # QPoint (global) under the model name of the card of the map: the window opens its model menu

    TOOLS = ("select", "zone", "heater", "heatsink", "via", "outline")

    def __init__(self, doc, theme="dark", parent=None):
        """!
        @param doc The Document to edit.
        @param theme "dark" or "light".
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.doc, self.theme = doc, theme
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scale(1, -1)                       # y axis up

        self.tool, self.polygon_mode, self.layer = "select", False, 0
        self.snap, self.show_grid, self.show_solver_grid, self.solver_cell = 1.0, True, False, 1.0
        self.via_diameter = None                    # None: the default via diameter of the user's defaults
        self._space = self._panning = self._external = self._rebuilding = False
        self._via_shift = None            # (dx, dy) in pixels from the real press to the centre of the via it was redirected to, while that press is held
        self._handle_lock = False
        self._pan_last = QPointF()
        self._draw_start, self._poly_pts, self._preview = None, [], None
        self._handles, self._handle_item = [], None
        self._overlay = self._background = None
        self.background_full = False                             # True while a map is over the Image underlay: the image is then drawn at 100 %
        self.background_problem = ""                             # Text for the status bar while the stored background image cannot be read ("" when fine)
        self._bg_reported = None                                 # The path already reported, so that a redraw does not repeat the message
        self.background_visible = True                           # False while a map is on the board over another underlay
        self._overlay_args = None
        self._card_hit = None                               # Rectangle (viewport pixels) of the model name of the card: the click target
        self._overlay_card = None                           # Card of the map on the board (model name, max and min), see set_overlay_card
        self._copper_item = None                    # The pixmap item of the imported copper of the active layer (None without one)
        self._copper_cache = {}                     # (layer index, mask token, theme) -> (QPixmap, millimetres per displayed pixel)
        self.show_imported_copper = True            # View - Imported copper
        self.copper_under_map = True                # False while a map is on the board and the Underlay is not Copper: the imported copper is hidden
        self.show_labels = True                     # Names of the heaters on the active layer
        self._fitted = False

        doc.changed.connect(self.rebuild)
        self.scene().selectionChanged.connect(self._on_scene_selection)
        self.rebuild()

    # ------------------------------------------------------------------ configuration
    def set_theme(self, theme):
        """!
        @brief Change the colour theme and repaint.
        @param theme "dark" or "light".
        """
        self.theme = theme
        self.rebuild()

    def set_tool(self, tool):
        """!
        @brief Choose the active tool and cancel any drawing in progress.
        @param tool One of TOOLS.
        """
        self._cancel_drawing()
        self.tool = tool
        self.setDragMode(QGraphicsView.RubberBandDrag if tool == "select" else QGraphicsView.NoDrag)
        self.viewport().setCursor(Qt.ArrowCursor if tool == "select" else Qt.CrossCursor)
        self._update_handles()
        hints = {"select": "Select: click, drag to move, drag a corner handle to reshape, Delete to remove.",
                 "zone": "Zone: drag a rectangle (or click points in polygon mode).",
                 "heater": "Heater: drag a rectangle (or click points in polygon mode).",
                 "heatsink": "Heatsink: drag a rectangle on the top or bottom layer.",
                 "via": "Via: click to place.",
                 "outline": "Board outline: drag a rectangle or click the vertices (polygon mode); the board takes that shape. Esc cancels."}
        self.message.emit(hints[tool])

    def set_layer(self, layer):
        """!
        @brief Choose the layer that is edited; other layers are shown dimmed.
        @param layer 0-based layer.
        """
        self.layer = layer
        self.rebuild()

    def set_snap(self, snap_mm):
        """!
        @brief Set the snap distance (0 disables snapping).
        @param snap_mm Snap in mm.
        """
        self.snap = max(float(snap_mm), 0.0)

    # ------------------------------------------------------------------ scene building
    def rebuild(self):
        """!
        @brief Recreate all items from the document and restore the selection.
        """
        if self._rebuilding:
            return
        self._rebuilding = True
        try:
            selected = set(self.selected_elements())
            self._clear_handles()
            sc = self.scene()
            sc.blockSignals(True)
            sc.clear()
            keep = getattr(self, "_overlay_args", None)             # The map outlives a rebuild of the items (layer change, selection)
            self._overlay = self._background = self._copper_item = None
            pr = self.doc.problem
            W, H = pr.board.width * 1000.0, pr.board.height * 1000.0
            m = max(W, H) * 0.6
            sc.setSceneRect(QRectF(-m, -m, W + 2 * m, H + 2 * m))
            self._add_background()
            self._add_imported_copper()
            if keep is not None:
                self.set_overlay(**keep)
            active = self.layer
            for kind, lst in (("zone", pr.zones), ("heatsink", pr.heatsinks), ("heater", pr.heaters)):
                for i, el in enumerate(lst):
                    poly = self.doc.polygon_mm(el)
                    label = el.name if el.layer == active and self.show_labels else ""
                    if kind == "heatsink" and el.is_block() and label:
                        label = f"{label} ({num(el.thickness * 1000)} mm block)"
                    it = ElementItem(self, kind, i, poly, label, el.layer)
                    if kind == "heatsink" and el.is_block():
                        it.is_block = True
                        it.restyle()
                    if el.layer != active:
                        it.setOpacity(0.22)
                        it.setFlags(it.flags() & ~(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable))
                    sc.addItem(it)
                    it.lift_label()
                    if (kind, i) in selected and el.layer == active:
                        it.setSelected(True)
            for i, v in enumerate(pr.vias):
                it = ViaItem(self, i, v.x * 1000.0, v.y * 1000.0, v.diameter * 1000.0)
                sc.addItem(it)
                if ("via", i) in selected:
                    it.setSelected(True)
            sc.blockSignals(False)
        finally:
            self._rebuilding = False
        self._update_handles()
        self._fit_labels()
        self.viewport().update()
        self.selection_changed.emit(self.selected_elements())

    def _add_imported_copper(self):
        """!
        @brief Draw the imported copper of the active layer under the elements, from a reduced mask that is built once and cached.
        @details The item is a pixmap in the copper colour whose alpha is the coverage, placed like the raster of the import (top-left corner of the board, rows downwards), so
                 panning and zooming only move a texture. A project without imported copper, a layer without a mask and the switch View - Imported copper off add nothing.
        """
        imp = self.doc.problem.imported
        self._copper_item = None
        if imp is None or not self.show_imported_copper or imp.pix_mm <= 0:
            if imp is None:
                self._copper_cache = {}                       # A project without imported copper: nothing cached is of use any more
            return
        # The token of a mask is its layer and its packed text (length and hash; the hash of a str is computed once and kept by Python, so this is cheap on every rebuild)
        tokens = {(int(e.get("index", -1)), len(d), hash(d)) for e in imp.layers if copper.has_mask(e) for d in (str(e["mask"].get("data", "")),)}
        # Keep only the pixmaps of the masks of the open problem in the current theme: a new import, a re-import, another project or a theme change drops the old ones
        # (without this every import added up to 16 MB per layer visited to the cache for the life of the window)
        self._copper_cache = {k: v for k, v in self._copper_cache.items() if k[3] == self.theme and k[:3] in tokens}
        entry = next((e for e in imp.layers if int(e.get("index", -1)) == self.layer and copper.has_mask(e)), None)
        if entry is None:
            return
        data = str(entry["mask"].get("data", ""))
        key = (self.layer, len(data), hash(data), self.theme)
        if key not in self._copper_cache:
            try:
                red, f = reduced_coverage(copper.unpack_coverage(entry["mask"]))
            except ValueError:                                # A damaged mask: the canvas shows no copper rather than failing
                return
            col = QColor(th.colors(self.theme)["copper"])
            rgba = np.zeros(red.shape + (4,), np.uint8)
            rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3] = col.red(), col.green(), col.blue(), red
            img = QImage(rgba.data, red.shape[1], red.shape[0], 4 * red.shape[1], QImage.Format_RGBA8888)
            self._copper_cache[key] = (QPixmap.fromImage(img), imp.pix_mm * f)    # fromImage copies, so rgba may go
        pm, mm = self._copper_cache[key]
        item = QGraphicsPixmapItem(pm)
        # Smooth (bilinear) sampling: seen whole, a displayed pixel covers several pixels of the pixmap and the nearest-pixel default would drop or alias the thin tracks;
        # measured on the 10.8 Mpx board, the frame costs the same (about 10 ms whole, 2 to 3 ms zoomed in, offscreen)
        item.setTransformationMode(Qt.SmoothTransformation)
        item.setTransform(QTransform().scale(mm, -mm))            # Rows go downwards, the scene upwards
        item.setPos(0.0, self.doc.problem.board.height * 1000.0)
        item.setOpacity(0.55)
        item.setZValue(0.3)                                       # Over the background photo, under the temperature map and the elements
        item.setAcceptedMouseButtons(Qt.NoButton)
        item.setVisible(self.copper_under_map)
        self.scene().addItem(item)
        self._copper_item = item

    def set_copper_under_map(self, on):
        """!
        @brief Show the imported copper (True) or hide it while a map is on the board over another underlay (False).
        @param on True to show the copper.
        """
        self.copper_under_map = bool(on)
        if self._copper_item is not None:
            self._copper_item.setVisible(self.copper_under_map)

    def set_show_imported_copper(self, on):
        """!
        @brief Show or hide the imported copper (View - Imported copper).
        @param on True to show.
        """
        self.show_imported_copper = bool(on)
        self.rebuild()

    def set_show_labels(self, on):
        """!
        @brief Show or hide the names of the elements: zones, heatsinks and heaters (View - Element names).
        @param on True to show.
        """
        self.show_labels = bool(on)
        self.rebuild()

    def _fit_labels(self):
        """!
        @brief In a project with imported parts centre the name of each heater on it and hide a name that is wider than the heater on the screen or that would overlap a name already
               shown (27 names on a board seen whole would be a smear); zooming in shows them. Larger heaters are named first.
        @details Drawn boards are left alone: their labels always show, from the centre to the right as before. The selected heater keeps its name. The size of a heater is that of its
                 polygon: `boundingRect()` of the item adds the width of its cosmetic pen in scene millimetres (1.4 to 2.2 mm), which let a name wider than a small part show.
        """
        if self.doc.problem.imported is None:
            return
        scale = abs(self.transform().m11())
        heaters = [it for it in self.scene().items() if isinstance(it, ElementItem) and it.kind == "heater" and it.label is not None]
        heaters.sort(key=lambda it: (not it.isSelected(), -it.polygon().boundingRect().width() * it.polygon().boundingRect().height()))
        taken = []
        for it in heaters:
            lab = it.label
            fm = QFontMetrics(lab.font())
            w, h = fm.horizontalAdvance(lab.text()) + 4, fm.height()
            lab.setTransform(QTransform.fromTranslate(-w / 2.0 + 2.0, -h / 2.0))    # In pixels (the label ignores the view's scale): centred on the heater
            pt = self.mapFromScene(lab.scenePos())                # The centre of the heater on the screen
            r = QRectF(pt.x() - w / 2.0, pt.y() - h / 2.0, w, h)
            show = it.isSelected() or (it.polygon().boundingRect().width() * scale >= w and not any(r.intersects(t) for t in taken))
            lab.setVisible(show)
            if show:
                taken.append(r)

    def _add_background(self):
        """!
        @brief Add the background photo (from the project view settings) below everything else.
        """
        self.background_error = ""
        cfg = self.doc.project.view.get("background")
        if not cfg:
            return
        path = cfg.get("path", "")
        pm = QPixmap()
        data = package_background_bytes(self.doc.project, path)   # an image stored in the project package is read from memory
        if data is not None:
            pm.loadFromData(data)
        else:
            pm = QPixmap(path)
        if pm.isNull():
            # The stored path is kept (the dialog shows it): only say, once per load, that the picture cannot be drawn
            name = os.path.basename(path) or "(no file name)"
            what = "not found" if not os.path.exists(path) else "could not be read"
            self.background_problem = f"Background image {what}: {name}; use View - Background image… to choose it again."
            if self._bg_reported != path:
                self._bg_reported = path
                self.message.emit(self.background_problem)
            return
        self.background_problem = ""
        self._bg_reported = None
        item = QGraphicsPixmapItem(pm)
        # Image rows go downward, the scene goes upward: flip y and anchor at the top-left corner
        item.setTransform(QTransform().scale(cfg["w_mm"] / pm.width(), -cfg["h_mm"] / pm.height()))
        item.setPos(cfg.get("x_mm", 0.0), cfg.get("y_mm", 0.0) + cfg["h_mm"])
        item.setOpacity(1.0 if self.background_full else cfg.get("opacity", 0.5))
        item.setZValue(0.2)
        item.setAcceptedMouseButtons(Qt.NoButton)
        item.setVisible(self.background_visible)
        self.scene().addItem(item)
        self._background = item

    def set_background_full(self, full):
        """!
        @brief Draw the background image at 100 % (a map is on the board over the Image underlay, so the map opacity alone sets what shows) or at its stored opacity.
        @param full True for 100 %.
        """
        self.background_full = bool(full)
        if self._background is not None:
            cfg = self.doc.project.view.get("background") or {}
            self._background.setOpacity(1.0 if self.background_full else cfg.get("opacity", 0.5))

    def set_background_visible(self, visible):
        """!
        @brief Show or hide the background image (the editor hides it while a temperature map is on the board and the Underlay is not Image).
        @param visible True to show it.
        """
        self.background_visible = bool(visible)
        if self._background is not None:
            self._background.setVisible(self.background_visible)

    def set_overlay(self, field, dx, dy, cmap="inferno", vmin=None, vmax=None, opacity=0.7, nodes=False, mask=None, unit="°C", smooth=False):
        """!
        @brief Draw a temperature map over the board, with a small colour bar in the corner of the view.
        @param field Array (ny, nx) in degC (row 0 at y = 0).
        @param dx Cell width in metres.
        @param dy Cell height in metres.
        @param cmap Matplotlib colormap name.
        @param vmin Lower colour limit in the unit of the field.
        @param vmax Upper colour limit in the unit of the field.
        @param opacity Overlay opacity (0..1).
        @param nodes True if the field holds values at grid points (the first sample sits at 0, not at half a cell).
        @param mask Boolean array (ny, nx), True for the cells on the board; the others are transparent (None: every cell is drawn).
        @param unit Unit written on the colour bar.
        @param smooth True for the View Smooth: the temperatures are interpolated between the cells (cubic spline on a grid OVERLAY_SMOOTH_FACTOR times finer,
                      at most OVERLAY_SMOOTH_PIXELS a side), as the Smooth of the Results maps, and the picture is scaled smoothly; False for the cells as solved.
        """
        from matplotlib import colormaps
        from .fieldscale import colour_limits

        self.clear_overlay(keep_card=True)                # The card of the map is set by the caller and survives a rebuild of the scene
        ny, nx = field.shape
        lo, hi = colour_limits(field, vmin is None or vmax is None, vmin, vmax)
        # Cells without a value (NaN) or off the outline get alpha 0 so that the board shows through
        ok = np.isfinite(field) if mask is None else (np.isfinite(field) & np.asarray(mask, bool))
        values, k = field, 1
        if smooth and ok.any():
            # Smooth means what it means in the Results maps: the TEMPERATURES are interpolated (cubic spline, the cells off the board filled with the
            # nearest value so they do not eat the kernel), then coloured; blending the colours of the cells would draw colours that are not on the bar
            from scipy import ndimage
            k = int(max(1, min(OVERLAY_SMOOTH_FACTOR, OVERLAY_SMOOTH_PIXELS // max(nx, ny))))
            idx = ndimage.distance_transform_edt(~ok, return_distances=False, return_indices=True)
            filled = np.asarray(field, np.float32)[tuple(idx)]
            values = ndimage.zoom(filled, k, order=3, mode="nearest", grid_mode=True) if k > 1 else filled
            ok = np.kron(ok, np.ones((k, k), bool))                        # The cells on the board keep their edges (Current draws the same)
        norm = np.clip((np.nan_to_num(values, nan=lo) - lo) / max(hi - lo, 1e-9), 0, 1)
        rgba = (colormaps[cmap](norm) * 255).astype(np.uint8)
        rgba[..., 3] = np.where(ok, 255, 0)
        rgba = np.ascontiguousarray(rgba)
        h, w = rgba.shape[:2]
        img = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888).copy()
        item = QGraphicsPixmapItem(QPixmap.fromImage(img))
        sx, sy = dx * 1000.0 / k, dy * 1000.0 / k                          # One pixel is a cell, or 1/k of a cell when smoothed
        tr = QTransform().scale(sx, sy)                                    # Row 0 sits at y = 0
        if nodes:
            tr = QTransform().translate(-0.5 * dx * 1000.0, -0.5 * dy * 1000.0).scale(sx, sy)
        item.setTransform(tr)
        item.setTransformationMode(Qt.SmoothTransformation if smooth else Qt.FastTransformation)
        item.setOpacity(float(opacity))
        item.setZValue(0.5)
        item.setAcceptedMouseButtons(Qt.NoButton)
        self.scene().addItem(item)
        self._overlay = item
        # Kept so that a rebuild of the scene (layer change, selection, theme) draws the same map again, and for the colour bar
        self._overlay_args = dict(field=field, dx=dx, dy=dy, cmap=cmap, vmin=lo, vmax=hi, opacity=float(opacity), nodes=nodes, mask=mask, unit=unit, smooth=bool(smooth))
        if self._at_fit_zoom() and not self._rebuilding:
            self.fit()                                                    # Leave the strip of the colour bar free
        self.viewport().update()

    def set_overlay_opacity(self, opacity):
        """!
        @brief Change the opacity of the temperature map without building it again.
        @param opacity Opacity (0..1).
        """
        if self._overlay is not None:
            self._overlay.setOpacity(float(opacity))
            self._overlay_args["opacity"] = float(opacity)

    def set_overlay_card(self, title, tmax=None, pmax_mm=None, tmin=None, pmin_mm=None):
        """!
        @brief Set the card at the top left of the map on the board: the model name and, when the model can be drawn, the hottest and coolest point with a ring on each.
        @details With `tmax` the card shows `max T` and `min T` lines and the rings are painted on the map at the two points; without it the card is only the title, in the
                 alert colour (a model that cannot be drawn on this board). Cleared by `clear_overlay`.
        @param title Model short name (FVM, FDM, Lumped, Analytic, 3D solid) or the note of a refused model.
        @param tmax Highest temperature of the displayed layer in degC (None: refused, title only).
        @param pmax_mm Position (x, y) of the hottest point on the board in millimetres.
        @param tmin Lowest temperature of the displayed layer in degC.
        @param pmin_mm Position (x, y) of the coolest point on the board in millimetres.
        """
        self._overlay_card = dict(title=str(title), tmax=tmax, pmax=pmax_mm, tmin=tmin, pmin=pmin_mm)
        self.viewport().update()

    def card_hit_rect(self):
        """!
        @brief The clickable part of the card of the map (its model name), in viewport pixels.
        @return QRectF or None when no card is shown.
        """
        return QRectF(self._card_hit) if getattr(self, "_card_hit", None) is not None and self._overlay_card else None

    def clear_overlay(self, keep_card=False):
        """!
        @brief Remove the temperature overlay, its colour bar and its card.
        @param keep_card True to leave the card (the overlay is about to be set again).
        """
        if not keep_card:
            self._overlay_card = None
        if self._overlay is not None and self._overlay.scene() is not None:
            self.scene().removeItem(self._overlay)
        had = self._overlay is not None
        self._overlay = None
        self._overlay_args = None
        if had and self._at_fit_zoom() and not self._rebuilding:
            self.fit()                                                    # Give the strip back to the board
        self.viewport().update()

    def colourbar_geometry(self):
        """!
        @brief Box of the colour bar of the temperature overlay, in viewport pixels.
        @details It is placed by `fieldscale.place_colourbar` where it covers neither the board nor the scale bar (right column, then left; top, middle, bottom).
        @return tuple (x, y, w, h, covers_board), or None when no overlay is shown.
        """
        from .fieldscale import place_colourbar

        if getattr(self, "_overlay_args", None) is None or self._overlay is None:
            return None
        w, h = self.viewport().width(), self.viewport().height()
        bh = min(140, max(h - 90, 40))
        b = self._board_pixel_rect()
        return place_colourbar((w, h), b, [self._scale_bar_rect()], (74 + 14, bh + 24))

    def _board_pixel_rect(self):
        """!
        @brief The board rectangle in viewport pixels.
        @return tuple (x, y, w, h).
        """
        r = self.mapFromScene(QRectF(0.0, 0.0, self.doc.problem.board.width * 1000.0, self.doc.problem.board.height * 1000.0)).boundingRect()
        return (r.x(), r.y(), r.width(), r.height())

    def _scale_step(self):
        """!
        @brief Step of the rulers in millimetres and the screen length of the scale bar.
        @return tuple (step_mm, pixels) or None when the view has no scale.
        """
        scale = abs(self.transform().m11())
        if scale <= 0:
            return None
        step = next((s for s in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if s * scale >= 60), 1000)
        return step, step * scale

    def _scale_bar_rect(self):
        """!
        @brief Rectangle taken by the scale bar and its label at the bottom left, in viewport pixels.
        @return tuple (x, y, w, h).
        """
        st = self._scale_step()
        bar = st[1] if st else 60.0
        return (18 + 12 - 4, self.viewport().height() - 14 - 20, max(bar, 60.0) + 8, 28)

    def _ring(self, painter, point, colour, halo):
        """!
        @brief Paint a small ring (screen pixels, a halo under it so that it reads on any map colour, no fill and no text).
        @param painter QPainter in screen pixels.
        @param point QPointF centre in screen pixels.
        @param colour Ring colour.
        @param halo Halo colour.
        """
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(halo), 3.4))
        painter.drawEllipse(point, 5.0, 5.0)
        painter.setPen(QPen(QColor(colour), 1.7))
        painter.drawEllipse(point, 5.0, 5.0)

    def _paint_overlay_card(self, painter):
        """!
        @brief Paint the card of the map on the board and the two rings on the hottest and the coolest point of the displayed layer.
        @details The card is at the top left, over the base colour at about 85 % with the border token; the title is the model in the accent colour and the two lines
                 below carry the rings in the colours of the points. A refused model is only the title in the alert colour. The rings are small and carry no text, so
                 the names of the elements stay readable.
        @param painter QPainter of the foreground (scene coordinates, reset here).
        """
        card = getattr(self, "_overlay_card", None)
        if not card:
            self._card_hit = None
            return
        c = th.colors(self.theme)
        painter.save()
        painter.resetTransform()
        font = painter.font()
        bold = painter.font()
        bold.setBold(True)
        fm, fmb = QFontMetrics(font), QFontMetrics(bold)
        pad, row = 8, fm.height() + 3
        x0, y0 = 26.0, 26.0
        refused = card["tmax"] is None
        lines = []
        if not refused:
            lines = [(c["bad"], f"max {num(round(card['tmax'], 1))} °C"), (c["heatsink"], f"min {num(round(card['tmin'], 1))} °C")]
        title = card["title"] + " \u25be"                # The small arrow says that the name opens the list of models
        w = max([fmb.horizontalAdvance(title)] + [fm.horizontalAdvance(t) + 16 for _col, t in lines]) + 2 * pad
        h = fmb.height() + 2 * pad - 2 + row * len(lines)
        self._card_hit = QRectF(x0, y0, w, fmb.height() + pad)
        bg = QColor(c["base"])
        bg.setAlphaF(0.85)
        painter.setPen(QPen(QColor(c["border"]), 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(QRectF(x0, y0, w, h), 4, 4)
        painter.setFont(bold)
        painter.setPen(QColor(c["alert"] if refused else c["accent"]))
        painter.drawText(QPointF(x0 + pad, y0 + pad + fmb.ascent() - 1), title)
        painter.setFont(font)
        for k, (col, text) in enumerate(lines):
            yy = y0 + pad - 2 + fmb.height() + row * k
            self._ring(painter, QPointF(x0 + pad + 5, yy + row / 2.0), col, c["selection"])
            painter.setPen(QColor(c["text"]))
            painter.drawText(QPointF(x0 + pad + 16, yy + row / 2.0 + fm.ascent() / 2.0 - 1), text)
        if not refused:
            for key, col in (("pmax", c["bad"]), ("pmin", c["heatsink"])):
                pos = card[key]
                if pos is not None:
                    pt = self.mapFromScene(QPointF(pos[0], pos[1]))
                    self._ring(painter, QPointF(pt), col, c["selection"])
        painter.restore()

    def drawForeground(self, painter, rect):
        """!
        @brief Paint the colour bar of the temperature overlay (in screen pixels, whatever the zoom) where it does not cover the board.
        @param painter QPainter to draw with.
        @param rect Exposed rectangle in scene coordinates (mm), not used.
        """
        self._paint_overlay_card(painter)
        g = self.colourbar_geometry()
        if g is None:
            return
        from matplotlib import colormaps
        from .fieldscale import nice_ticks, tick_label

        a = self._overlay_args
        c = th.colors(self.theme)
        x0b, y0b, wb, hb, covers = g
        painter.save()
        painter.resetTransform()                                          # Screen pixels from here on
        bw, bh = 14, int(hb - 24)
        x0, y0 = x0b + 6, y0b + 16
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(c["canvas"]))
        painter.setOpacity(0.6 if covers else 0.85)                       # Translucent only when the board leaves no free place for it
        painter.drawRoundedRect(QRectF(x0b, y0b, wb, hb), 4, 4)           # Backing plate so the labels read over any copper
        painter.setOpacity(1.0)
        cm = colormaps[a["cmap"]]
        # One column of the colour map as an image (no colour literals: the values come from matplotlib), highest temperature on top
        strip = np.ascontiguousarray((cm(np.linspace(1.0, 0.0, bh)[:, None]) * 255).astype(np.uint8))
        painter.drawImage(QRectF(x0, y0, bw, bh), QImage(strip.data, 1, bh, 4, QImage.Format_RGBA8888).copy())
        painter.setPen(QColor(c["text"]))
        painter.drawText(QPointF(x0, y0 - 4), a["unit"])
        # Round ticks (1, 2, 5 times a power of ten) placed at their value on the bar, labelled with the digits the step needs
        lo, hi = a["vmin"], a["vmax"]
        vals, step = nice_ticks(lo, hi, 4)
        self._colourbar_labels = []
        for v in vals:
            yy = y0 + bh * (1.0 - (v - lo) / max(hi - lo, 1e-12))
            painter.drawLine(QPointF(x0 + bw, yy), QPointF(x0 + bw + 3, yy))
            text = f"{tick_label(v, step)}"
            self._colourbar_labels.append(text)
            painter.drawText(QPointF(x0 + bw + 5, yy + 4), text)
        painter.restore()

    # ------------------------------------------------------------------ selection
    def selected_elements(self):
        """!
        @brief The selected elements.
        @return List of (kind, index).
        """
        return [(it.kind, it.index) for it in self.scene().selectedItems() if hasattr(it, "kind")]

    def set_selection(self, items):
        """!
        @brief Select elements from outside (for example from the element list).
        @param items Iterable of (kind, index).
        """
        want = set(items)
        self._external = True
        self.scene().blockSignals(True)
        for it in self.scene().items():
            if hasattr(it, "kind"):
                it.setSelected(bool((it.kind, it.index) in want and (it.flags() & QGraphicsItem.ItemIsSelectable)))
        self.scene().blockSignals(False)
        self._external = False
        self._update_handles()
        self._fit_labels()

    def _on_scene_selection(self):
        """!
        @brief Forward scene selection changes and refresh the vertex handles.
        """
        if self._rebuilding or self._external:
            return
        self._update_handles()
        self._fit_labels()                                     # A selected heater shows its name even when it does not fit
        self.selection_changed.emit(self.selected_elements())

    # ------------------------------------------------------------------ vertex handles
    def _clear_handles(self):
        """!
        @brief Remove the vertex handles.
        """
        for h in self._handles:
            if h.scene() is not None:
                self.scene().removeItem(h)
        self._handles, self._handle_item = [], None

    def _update_handles(self):
        """!
        @brief Show handles on the vertices of the single selected polygon.
        """
        self._clear_handles()
        if self.tool != "select":
            return
        sel = [it for it in self.scene().selectedItems() if isinstance(it, ElementItem)]
        if len(sel) != 1 or len(self.scene().selectedItems()) != 1:
            return
        it = sel[0]
        self._handle_item = it
        self._handle_lock = True
        for i in range(it.polygon().count()):
            h = VertexHandle(self, i, it.polygon().at(i) + it.pos())
            self.scene().addItem(h)
            self._handles.append(h)
        self._handle_lock = False

    def _handle_moved(self, index, pos):
        """!
        @brief Reshape the selected polygon live while a handle is dragged.
        @param index Vertex index being dragged.
        @param pos New position of that vertex (mm).
        """
        it = self._handle_item
        if it is None:
            return
        pts = np.array([[p.x(), p.y()] for p in (it.polygon().at(i) for i in range(it.polygon().count()))]) + \
            np.array([it.pos().x(), it.pos().y()])
        q = np.array([pos.x(), pos.y()])
        if _is_axis_aligned_rect(pts):
            o = pts[(index + 2) % 4]
            a, b = (index + 1) % 4, (index - 1) % 4
            horizontal = abs(pts[index][1] - pts[a][1]) < 1e-9       # Edge index -> a is horizontal
            new = pts.copy()
            new[index] = q
            new[a] = [o[0], q[1]] if horizontal else [q[0], o[1]]
            new[b] = [q[0], o[1]] if horizontal else [o[0], q[1]]
            pts = new
            self._handle_lock = True
            for k, h in enumerate(self._handles):
                if k != index:
                    h.setPos(QPointF(*pts[k]))
            self._handle_lock = False
        else:
            pts[index] = q
        it.setPolygon(QPolygonF([QPointF(x - it.pos().x(), y - it.pos().y()) for x, y in pts]))

    def _handles_committed(self):
        """!
        @brief Store the reshaped polygon in the document.
        """
        it = self._handle_item
        if it is None:
            return
        pts = [[h.pos().x(), h.pos().y()] for h in self._handles]
        self.doc.set_polygon(it.kind, it.index, pts)

    # ------------------------------------------------------------------ view control
    def fit(self):
        """!
        @brief Zoom so that the whole board fits in the view.
        @details While the temperature overlay is shown, a strip on the right (`COLOURBAR_STRIP` pixels) is left free for its colour bar, so that the bar never covers the board.
        """
        b = self.doc.problem.board
        W, H = b.width * 1000.0, b.height * 1000.0
        vw, vh = max(self.viewport().width(), 50), max(self.viewport().height(), 50)
        strip = self.COLOURBAR_STRIP if getattr(self, "_overlay", None) is not None and vw > 3 * self.COLOURBAR_STRIP else 0
        s = 0.9 * min((vw - strip) / W, vh / H)
        self.setTransform(QTransform().scale(s, -s))
        self.centerOn(W / 2 + strip / (2.0 * s), H / 2)
        self._fit_scale = s
        self._fitted = True
        self._fit_labels()

    def _at_fit_zoom(self):
        """!
        @brief True while the view still has the zoom that `fit` set (the user has not zoomed since), so that it may be fitted again without undoing a zoom.
        @return bool.
        """
        s = getattr(self, "_fit_scale", None)
        return s is not None and abs(abs(self.transform().m11()) - s) <= 1e-9 * s

    def showEvent(self, e):
        """!
        @brief Fit the board the first time the view becomes visible.
        @param e QShowEvent.
        """
        super().showEvent(e)
        if not self._fitted:
            self.fit()

    def zoom(self, factor):
        """!
        @brief Zoom around the view centre.
        @param factor Scale factor (greater than 1 zooms in).
        """
        self.scale(factor, factor)
        self._fit_labels()

    def wheelEvent(self, e):
        """!
        @brief Mouse wheel zooms around the cursor.
        @param e QWheelEvent (the vertical angle delta sets the zoom).
        """
        self.scale(1.15 ** (e.angleDelta().y() / 120.0), 1.15 ** (e.angleDelta().y() / 120.0))
        self._fit_labels()

    # ------------------------------------------------------------------ painting
    def drawBackground(self, painter, rect):
        """!
        @brief Paint the workspace, the board and the grids.
        @param painter QPainter to draw with.
        @param rect Exposed rectangle in scene coordinates (mm).
        """
        c = th.colors(self.theme)
        painter.fillRect(rect, QColor(c["canvas"]))
        b = self.doc.problem.board
        W, H = b.width * 1000.0, b.height * 1000.0
        board = QRectF(0, 0, W, H)
        path = None
        if b.has_outline():
            path = QPainterPath()
            path.addPolygon(QPolygonF([QPointF(x * 1000.0, y * 1000.0) for x, y in b.outline]))
            path.closeSubpath()
            dash = QPen(QColor(c["muted"]), 0, Qt.DashLine)           # The box the outline sits in
            dash.setCosmetic(True)
            painter.setPen(dash)
            painter.drawRect(board)
            painter.fillPath(path, QColor(c["board"]))
        else:
            painter.fillRect(board, QColor(c["board"]))
        scale = abs(self.transform().m11())
        vis = rect.intersected(board)
        if vis.isEmpty():
            return
        if path is not None:
            painter.save()
            painter.setClipPath(path)
        if self.show_grid:
            step = next((s for s in _GRID_STEPS if s * scale >= 14), _GRID_STEPS[-1])
            for width_step, key in ((step, "grid_minor"), (step * 5, "grid_major")):
                pen = QPen(th.qcolor(c[key]))
                pen.setCosmetic(True)
                painter.setPen(pen)
                x = np.floor(vis.left() / width_step) * width_step
                lines = []
                while x <= vis.right():
                    lines.append(QLineF(x, vis.top(), x, vis.bottom()))
                    x += width_step
                y = np.floor(vis.top() / width_step) * width_step
                while y <= vis.bottom():
                    lines.append(QLineF(vis.left(), y, vis.right(), y))
                    y += width_step
                painter.drawLines(lines)
        if self.show_solver_grid:
            nx = max(int(round(W / self.solver_cell)), 1)
            ny = max(int(round(H / self.solver_cell)), 1)
            if W / nx * scale >= 3 and H / ny * scale >= 3:
                pen = QPen(th.qcolor(c["solver_grid"]))
                pen.setCosmetic(True)
                painter.setPen(pen)
                painter.drawLines([QLineF(i * W / nx, 0, i * W / nx, H) for i in range(nx + 1)] +
                                  [QLineF(0, j * H / ny, W, j * H / ny) for j in range(ny + 1)])
        if path is not None:
            painter.restore()
        pen = QPen(QColor(c["accent"]))
        pen.setCosmetic(True)
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        if path is not None:
            painter.drawPath(path)
        else:
            painter.drawRect(board)

    def paintEvent(self, e):
        """!
        @brief Paint the scene, then the rulers on top of it.
        @param e QPaintEvent.
        """
        super().paintEvent(e)
        painter = QPainter(self.viewport())
        try:
            self._paint_rulers(painter)
        finally:
            painter.end()

    def _paint_rulers(self, painter):
        """!
        @brief Rulers along the top and left edges (board millimetres) and a scale bar, adapted to the zoom.
        @details The tick spacing is the smallest step from 1-2-5 series that leaves at least 60 pixels between labelled ticks, so the scale
                 is readable at every zoom; the rulers always show the coordinates of the board, not of the window.
        @param painter QPainter on the viewport.
        """
        c = th.colors(self.theme)
        scale = abs(self.transform().m11())                 # Pixels per millimetre
        if scale <= 0:
            return
        size = 18
        w, h = self.viewport().width(), self.viewport().height()
        bg = QColor(c["canvas"])
        bg.setAlpha(225)
        fg = QColor(c["text"])
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(0, 0, w, size, bg)
        painter.fillRect(0, 0, size, h, bg)
        painter.setPen(QPen(fg))
        font = painter.font()
        font.setPointSizeF(7.5)
        painter.setFont(font)
        step = self._scale_step()[0]
        minor = step / 5.0 if step * scale >= 100 else step / 2.0
        origin = self.mapFromScene(QPointF(0.0, 0.0))        # Pixel of the board corner (0, 0)
        # Horizontal ruler: x grows to the right
        x0, x1 = (0 - origin.x()) / scale, (w - origin.x()) / scale
        k = int(np.floor(x0 / minor))
        while k * minor <= x1:
            v = k * minor
            px = origin.x() + v * scale
            major = abs(v / step - round(v / step)) < 1e-6
            painter.drawLine(int(px), size - (9 if major else 4), int(px), size)
            if major and px > size:
                painter.drawText(int(px) + 2, 10, f"{num(v)}")
            k += 1
        # Vertical ruler: y grows upward in the board, downward on the screen
        y_top, y_bot = (origin.y() - 0) / scale, (origin.y() - h) / scale      # Board y at the top and bottom of the window
        k = int(np.floor(y_bot / minor))
        while k * minor <= y_top:
            v = k * minor
            py = origin.y() - v * scale
            major = abs(v / step - round(v / step)) < 1e-6
            painter.drawLine(size - (9 if major else 4), int(py), size, int(py))
            text = num(v)
            # The rotated label runs upward from its tick: leave it out when it would reach the corner square where "mm" is written
            if major and py - 2 - painter.fontMetrics().horizontalAdvance(text) > size:
                painter.save()
                painter.translate(11, int(py) - 2)
                painter.rotate(-90)
                painter.drawText(0, 0, text)
                painter.restore()
            k += 1
        painter.drawText(2, 12, "mm")
        # Scale bar at the bottom left
        bar = step * scale
        x, y = size + 12, h - 14
        painter.drawLine(int(x), y, int(x + bar), y)
        painter.drawLine(int(x), y - 4, int(x), y + 4)
        painter.drawLine(int(x + bar), y - 4, int(x + bar), y + 4)
        painter.drawText(int(x + bar / 2 - 18), y - 6, f"{num(step)} mm")

    # ------------------------------------------------------------------ mouse and keys
    def _snapped(self, p):
        """!
        @brief Snap a scene point to the grid.
        @param p QPointF in mm.
        @return QPointF.
        """
        if self.snap > 0:
            return QPointF(round(p.x() / self.snap) * self.snap, round(p.y() / self.snap) * self.snap)
        return p

    def mousePressEvent(self, e):
        """!
        @brief Start panning, drawing or the default selection and drag handling.
        @param e QMouseEvent of the press.
        """
        self.setFocus()
        hit = self.card_hit_rect()
        if e.button() == Qt.LeftButton and hit is not None and hit.contains(e.position()):
            self.card_clicked.emit(e.globalPosition().toPoint())      # The model name of the card: the window lists the models (focus stays on the board)
            return
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self._space):
            self._panning, self._pan_last = True, e.position()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.RightButton and self._poly_pts:
            self._finish_polygon()
            return
        if e.button() == Qt.LeftButton and self.tool != "select":
            p = self._snapped(self.mapToScene(e.position().toPoint()))
            if self.tool == "via":
                self.element_created.emit("via", self.doc.add_via(p.x(), p.y(), self.via_diameter))
            elif self.polygon_mode:
                self._poly_pts.append(p)
                self._update_preview(p)
            else:
                self._draw_start = p
            return
        if e.button() == Qt.LeftButton and self.tool == "select":
            # Vertex handles keep their priority; otherwise a via near the cursor beats whatever polygon lies under it (the via is tiny at low zoom)
            if not isinstance(self.itemAt(e.position().toPoint()), VertexHandle):
                near = self.nearest_via(self.mapToScene(e.position().toPoint()))
                if near is not None:
                    # Hand Qt a press at the centre of that via, so that exactly this via takes the press (selection, Ctrl toggle and drag are Qt's)
                    centre = self.mapFromScene(QPointF(*near))
                    self._via_shift = QPointF(centre) - e.position()
                    e = self._shifted(e)
        super().mousePressEvent(e)

    def _shifted(self, e):
        """!
        @brief The mouse event moved by the redirect of the press to a via, so that the pointer keeps its distance to the via centre (no jump when the via is dragged).
        @param e QMouseEvent as received.
        @return The same event when no redirect is active, otherwise a copy shifted by the redirect.
        """
        if self._via_shift is None:
            return e
        pos = e.position() + self._via_shift
        # The scene finds the items under the press from the GLOBAL position, so that one moves too
        return QMouseEvent(e.type(), pos, pos, e.globalPosition() + self._via_shift, e.button(), e.buttons(), e.modifiers())

    def nearest_via(self, scene_pt):
        """!
        @brief The via whose centre is nearest to a point, within the pick tolerance of that via.
        @details The tolerance of a via is its drawn radius or 6 screen pixels, whichever is larger, so a via stays pickable at low zoom and in a dense array the nearest centre
                 wins (the item under the cursor would be the first one drawn that reaches it).
        @param scene_pt QPointF in mm (scene coordinates).
        @return (x, y) of the via centre in mm, or None when no via is within its tolerance.
        """
        scale = max(abs(self.transform().m11()), 1e-9)                        # Pixels per mm
        px, py = scene_pt.x(), scene_pt.y()
        best, best_d = None, None
        for v in self.doc.problem.vias:
            x, y = v.x * 1000.0, v.y * 1000.0
            tol = max(max(v.diameter * 1000.0 / 2.0, 0.3), 6.0 / scale)       # Same radius as ViaItem draws, in mm
            d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if d <= tol and (best_d is None or d < best_d):
                best, best_d = (x, y), d
        return best

    # ------------------------------------------------------------------ context menu
    @staticmethod
    def default_size_mm(kind):
        """!
        @brief Side of the square shape dropped from the right-click menu, from the user's defaults.
        @param kind "heater", "zone" or "heatsink".
        @return Side in mm.
        """
        return float(defaults.load()["new_elements"][f"{kind}_size_mm"])

    def contextMenuEvent(self, e):
        """!
        @brief Right click: edit the vertices of the shape under the cursor, or add an element on an empty spot.
        @param e QContextMenuEvent.
        """
        if self.tool != "select" or self._poly_pts or self._draw_start is not None:
            e.accept()
            return
        menu = self.build_context_menu(self.mapToScene(e.pos()))
        if menu is not None:
            menu.exec(e.globalPos())
        e.accept()

    def build_context_menu(self, scene_pt):
        """!
        @brief The right-click menu for a point of the board.
        @details On a polygon (zone, heater, heatsink): add a vertex on the nearest edge, delete the vertex under the cursor (three stay at least), duplicate and delete the
                 element. On a via: duplicate and delete. On an empty spot: add a heater, zone, heatsink or via centred there. The element under the cursor is selected first.
        @param scene_pt QPointF in mm.
        @return QMenu with the actions, or None when the point is outside every element and outside the board.
        """
        tol = 8.0 / max(abs(self.transform().m11()), 1e-9)                       # Eight pixels in mm
        # Several elements can lie under the cursor (a full-board zone below a part below a via): the smallest kind wins
        rank = {"via": 0, "heater": 1, "heatsink": 2, "zone": 3}
        under = sorted((it for it in self.items(self.mapFromScene(scene_pt)) if hasattr(it, "kind")), key=lambda it: rank.get(it.kind, 9))
        target = under[0] if under else None
        menu = QMenu(self)
        if target is not None:
            self.set_selection([(target.kind, target.index)])
            self.selection_changed.emit(self.selected_elements())
            kind, i = target.kind, target.index
            if kind != "via":
                pts = self.doc.polygon_mm(getattr(self.doc.problem, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks"}[kind])[i])
                add = menu.addAction("Add a vertex here")
                add.setToolTip("Add a point on the nearest edge.")
                add.triggered.connect(lambda: self.add_vertex(kind, i, (scene_pt.x(), scene_pt.y())))
                k, d = nearest_vertex(pts, (scene_pt.x(), scene_pt.y()))
                dele = menu.addAction("Delete this vertex")
                dele.setToolTip("Delete the vertex under the cursor (a polygon keeps at least three).")
                dele.setEnabled(d <= tol * 1.5 and len(pts) > 3)
                dele.triggered.connect(lambda: self.remove_vertex(kind, i, k))
                menu.addSeparator()
            dup = menu.addAction("Duplicate")
            dup.triggered.connect(lambda: self.set_selection(self.doc.duplicate([(kind, i)])))
            rem = menu.addAction(f"Delete {kind}")
            rem.triggered.connect(lambda: self.doc.delete([(kind, i)]))
            menu.addSeparator()
        b = self.doc.problem.board
        if not (0 <= scene_pt.x() <= b.width * 1000.0 and 0 <= scene_pt.y() <= b.height * 1000.0):
            return menu if target is not None else None
        p = self._snapped(scene_pt)
        if target is None:
            self.scene().clearSelection()
        # On an element the new-element entries sit in a submenu; on an empty spot they are the menu
        add_to = menu.addMenu("Add here") if target is not None else menu
        for new_kind in ("heater", "zone", "heatsink"):                      # Not `kind`: the lambdas above close over it
            act = add_to.addAction(f"Add {new_kind} here")
            act.triggered.connect(lambda _c=False, k=new_kind: self.add_centered(k, p))
        act = add_to.addAction("Add via here")
        act.triggered.connect(lambda: self.element_created.emit("via", self.doc.add_via(p.x(), p.y(), self.via_diameter)))
        return menu

    def add_centered(self, kind, centre):
        """!
        @brief Drop a square heater, zone or heatsink centred on a point (kept inside the board).
        @param kind "heater", "zone" or "heatsink".
        @param centre QPointF in mm.
        """
        b = self.doc.problem.board
        s = min(self.default_size_mm(kind), b.width * 1000.0, b.height * 1000.0)
        x0 = min(max(centre.x() - s / 2, 0.0), b.width * 1000.0 - s)
        y0 = min(max(centre.y() - s / 2, 0.0), b.height * 1000.0 - s)
        self._create(kind, [[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]])

    def add_vertex(self, kind, index, point_mm):
        """!
        @brief Add a vertex on the edge of a shape nearest to a point.
        @param kind "zone", "heater" or "heatsink".
        @param index Element index.
        @param point_mm (x, y) in mm.
        """
        el = getattr(self.doc.problem, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks"}[kind])[index]
        pts, _ = insert_vertex(self.doc.polygon_mm(el), point_mm)
        self.doc.set_polygon(kind, index, pts)
        self.set_selection([(kind, index)])
        self.message.emit("Vertex added: drag its handle to reshape the polygon.")

    def remove_vertex(self, kind, index, vertex):
        """!
        @brief Delete one vertex of a shape (a polygon keeps at least three).
        @param kind "zone", "heater" or "heatsink".
        @param index Element index.
        @param vertex Vertex index.
        """
        el = getattr(self.doc.problem, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks"}[kind])[index]
        pts = self.doc.polygon_mm(el)
        if len(pts) <= 3:
            self.message.emit("A polygon needs at least three vertices.")
            return
        new = np.delete(pts, vertex, axis=0)
        if not polygon_is_simple(new):
            self.message.emit("Not deleted: the polygon would cross itself.")
            return
        self.doc.set_polygon(kind, index, new)
        self.set_selection([(kind, index)])

    def mouseDoubleClickEvent(self, e):
        """!
        @brief A double click finishes a polygon.
        @param e QMouseEvent of the double click.
        """
        if self._poly_pts:
            # A real double click is press, release, double-click: the press already added the last vertex.
            # Some event sources send the double-click alone, so add the vertex if it is not there yet.
            p = self._snapped(self.mapToScene(e.position().toPoint()))
            last = self._poly_pts[-1]
            if abs(last.x() - p.x()) > 1e-6 or abs(last.y() - p.y()) > 1e-6:
                self._poly_pts.append(p)
            self._finish_polygon()
            return
        super().mouseDoubleClickEvent(e)

    def mouseMoveEvent(self, e):
        """!
        @brief Pan, update drawing previews and report the cursor position.
        @param e QMouseEvent of the move.
        """
        scene_p = self.mapToScene(e.position().toPoint())
        self.cursor_moved.emit(scene_p.x(), scene_p.y())
        if self._panning:
            d = e.position() - self._pan_last
            self._pan_last = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            return
        if self.tool != "select":
            p = self._snapped(scene_p)
            if self._draw_start is not None:
                self._update_preview(p)
                return
            if self._poly_pts:
                self._update_preview(p)
                return
        super().mouseMoveEvent(self._shifted(e))

    def mouseReleaseEvent(self, e):
        """!
        @brief Finish panning, a rectangle, or commit element moves.
        @param e QMouseEvent of the release.
        """
        if self._panning and e.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._panning = False
            self.viewport().setCursor(Qt.ArrowCursor if self.tool == "select" else Qt.CrossCursor)
            return
        if self.tool != "select" and e.button() == Qt.LeftButton and self._draw_start is not None:
            a, b = self._draw_start, self._snapped(self.mapToScene(e.position().toPoint()))
            self._draw_start = None
            self._clear_preview()
            if abs(b.x() - a.x()) > 0.2 and abs(b.y() - a.y()) > 0.2:
                x0, x1 = sorted((a.x(), b.x()))
                y0, y1 = sorted((a.y(), b.y()))
                self._create(self.tool, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
            return
        super().mouseReleaseEvent(self._shifted(e))
        if e.button() == Qt.LeftButton:
            self._via_shift = None                                  # The press that was redirected to a via is over
        if self.tool == "select" and e.button() == Qt.LeftButton:
            moved = [it for it in self.scene().selectedItems() if hasattr(it, "kind") and it.pos() != it.origin]
            if moved:
                # Each item reports its own shift (a via's position is absolute, a polygon's is relative)
                shifts = {}
                for it in moved:
                    d = it.pos() - it.origin
                    shifts.setdefault((round(d.x(), 9), round(d.y(), 9)), []).append((it.kind, it.index))
                for (dx, dy), group in shifts.items():
                    self.doc.move(group, dx, dy)

    def keyPressEvent(self, e):
        """!
        @brief Keys of the canvas: Backspace, arrows, Enter, Esc, Space (pan).
        @param e QKeyEvent of the key press.
        @note Del and Ctrl+D are shortcuts of the window actions Delete and Duplicate, which take the key before the canvas sees it, so they are not handled
              here (tests/test_shortcuts.py checks that the canvas never receives them). Backspace (the Mac "delete" key) is the second key of the Delete action too.
        """
        key = e.key()
        if key == Qt.Key_Space and not e.isAutoRepeat():
            self._space = True
            self.viewport().setCursor(Qt.OpenHandCursor)
        elif key == Qt.Key_Escape:
            self._cancel_drawing()
            self.scene().clearSelection()
        elif key in (Qt.Key_Return, Qt.Key_Enter) and self._poly_pts:
            self._finish_polygon()
        elif key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down) and self.selected_elements():
            s = self.snap if self.snap > 0 else 1.0
            dx = {Qt.Key_Left: -s, Qt.Key_Right: s}.get(key, 0.0)
            dy = {Qt.Key_Down: -s, Qt.Key_Up: s}.get(key, 0.0)
            self.doc.move(self.selected_elements(), dx, dy)
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        """!
        @brief Releasing Space ends hand-pan mode.
        @param e QKeyEvent of the key release.
        """
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._space = False
            self.viewport().setCursor(Qt.ArrowCursor if self.tool == "select" else Qt.CrossCursor)
        super().keyReleaseEvent(e)

    # ------------------------------------------------------------------ drawing helpers
    def _create(self, kind, polygon_mm):
        """!
        @brief Create an element from a finished shape.
        @param kind "zone", "heater" or "heatsink".
        @param polygon_mm Vertices in mm.
        """
        layer = self.layer
        if kind == "outline":
            b = self.doc.problem.board
            pts = np.clip(np.asarray(polygon_mm, dtype=float), [0.0, 0.0], [b.width * 1000.0, b.height * 1000.0])
            if len(pts) < 3:
                return
            self.doc.set_outline(pts.tolist())
            self.message.emit("Board outline set. Edit its vertices in the Board panel; the cells outside it are not solved.")
            return
        if kind == "heatsink":
            last = self.doc.problem.board.layers - 1
            if layer not in (0, last):
                self.message.emit("A heatsink must be on the top or the bottom layer: switch the layer first.")
                return
        idx = self.doc.add_shape(kind, layer, polygon_mm)
        self.element_created.emit(kind, idx)

    def _update_preview(self, cursor):
        """!
        @brief Draw the rubber-band rectangle or the polygon being built.
        @param cursor Current snapped cursor position.
        """
        self._clear_preview()
        # The text colour: it reads on the canvas of both themes (white was 1.3:1 on the light canvas)
        pen = QPen(QColor(th.colors(self.theme)["text"]))
        pen.setCosmetic(True)
        pen.setStyle(Qt.DashLine)
        pen.setWidthF(1.5)
        if self._draw_start is not None:
            a = self._draw_start
            self._preview = self.scene().addRect(QRectF(a, cursor).normalized(), pen)
        elif self._poly_pts:
            pts = self._poly_pts + [cursor]
            self._preview = self.scene().addPolygon(QPolygonF(pts), pen)
        if self._preview is not None:
            self._preview.setZValue(30)

    def _clear_preview(self):
        """!
        @brief Remove the drawing preview item.
        """
        if self._preview is not None and self._preview.scene() is not None:
            self.scene().removeItem(self._preview)
        self._preview = None

    def _finish_polygon(self):
        """!
        @brief Create an element from the clicked polygon if it has at least three points.
        """
        pts = [[p.x(), p.y()] for p in self._poly_pts]
        self._cancel_drawing()
        if len(pts) >= 3:
            self._create(self.tool, pts)

    def _cancel_drawing(self):
        """!
        @brief Abort any drawing in progress.
        """
        self._draw_start, self._poly_pts = None, []
        self._clear_preview()
