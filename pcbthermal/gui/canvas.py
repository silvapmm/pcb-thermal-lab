"""!
@file canvas.py
@brief Interactive board editor: zoom, pan, grid, drawing tools, selection, vertex editing.

The scene is in millimetres with the y axis pointing up (the view flips it), so scene
coordinates are the board coordinates the physics core uses.
"""

import numpy as np
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QPainterPath, QBrush, QColor, QCursor, QImage, QPainter, QPen, QPixmap, QPolygonF,
                           QTransform)
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsPixmapItem, QGraphicsPolygonItem,
                               QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView,
                               QStyle)

from . import theme as th

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
            self.label.setBrush(QBrush(QColor("white")))
        self.restyle()

    def restyle(self):
        """!
        @brief Apply the fill and outline of the element kind and its selection state.
        """
        c = th.colors(self.view.theme)
        base = {"zone": c["copper"], "heater": c["heater"], "heatsink": c["heatsink"]}[self.kind]
        alpha = {"zone": 70, "heater": 120, "heatsink": 70}[self.kind]
        self.setBrush(QBrush(th.qcolor(base, alpha)))
        pen = QPen(QColor("white") if self.isSelected() else QColor(base), 0)
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

    def restyle(self):
        """!
        @brief Apply the via colours and the selection highlight.
        """
        c = th.colors(self.view.theme)
        pen = QPen(QColor("white") if self.isSelected() else QColor(c["via"]))
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
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIgnoresTransformations |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setBrush(QBrush(QColor("white")))
        pen = QPen(QColor("#4c8dff"))
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

    selection_changed = Signal(list)       # [(kind, index), ...]
    cursor_moved = Signal(float, float)    # mm
    message = Signal(str)                  # status text
    element_created = Signal(str, int)     # kind, index

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
        self.via_diameter = 0.3
        self._space = self._panning = self._external = self._rebuilding = False
        self._handle_lock = False
        self._pan_last = QPointF()
        self._draw_start, self._poly_pts, self._preview = None, [], None
        self._handles, self._handle_item = [], None
        self._overlay = self._background = None
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
            self._overlay = self._background = None
            pr = self.doc.problem
            W, H = pr.board.width * 1000.0, pr.board.height * 1000.0
            m = max(W, H) * 0.6
            sc.setSceneRect(QRectF(-m, -m, W + 2 * m, H + 2 * m))
            self._add_background()
            active = self.layer
            for kind, lst in (("zone", pr.zones), ("heatsink", pr.heatsinks), ("heater", pr.heaters)):
                for i, el in enumerate(lst):
                    poly = self.doc.polygon_mm(el)
                    label = el.name if el.layer == active else ""
                    if kind == "heatsink" and el.is_block() and label:
                        label = f"{label} ({el.thickness * 1000:g} mm block)"
                    it = ElementItem(self, kind, i, poly, label, el.layer)
                    if kind == "heatsink" and el.is_block():
                        it.is_block = True
                        it.restyle()
                    if el.layer != active:
                        it.setOpacity(0.22)
                        it.setFlags(it.flags() & ~(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable))
                    sc.addItem(it)
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
        self.viewport().update()
        self.selection_changed.emit(self.selected_elements())

    def _add_background(self):
        """!
        @brief Add the background photo (from the project view settings) below everything else.
        """
        cfg = self.doc.project.view.get("background")
        if not cfg:
            return
        pm = QPixmap(cfg.get("path", ""))
        if pm.isNull():
            return
        item = QGraphicsPixmapItem(pm)
        # Image rows go downward, the scene goes upward: flip y and anchor at the top-left corner
        item.setTransform(QTransform().scale(cfg["w_mm"] / pm.width(), -cfg["h_mm"] / pm.height()))
        item.setPos(cfg.get("x_mm", 0.0), cfg.get("y_mm", 0.0) + cfg["h_mm"])
        item.setOpacity(cfg.get("opacity", 0.5))
        item.setZValue(0.2)
        item.setAcceptedMouseButtons(Qt.NoButton)
        self.scene().addItem(item)
        self._background = item

    def set_overlay(self, field, dx, dy, cmap="inferno", vmin=None, vmax=None, opacity=0.8, nodes=False):
        """!
        @brief Draw a temperature map over the board.
        @param field Array (ny, nx) in degC (row 0 at y = 0).
        @param dx Cell width in metres.
        @param dy Cell height in metres.
        @param cmap Matplotlib colormap name.
        @param vmin Lower colour limit.
        @param vmax Upper colour limit.
        @param opacity Overlay opacity (0..1).
        @param nodes True if the field holds values at grid points (the first sample sits at 0, not at half a cell).
        """
        from matplotlib import colormaps

        self.clear_overlay()
        ny, nx = field.shape
        lo = float(np.nanmin(field)) if vmin is None else vmin
        hi = float(np.nanmax(field)) if vmax is None else vmax
        norm = np.clip((field - lo) / max(hi - lo, 1e-9), 0, 1)
        rgba = (colormaps[cmap](norm) * 255).astype(np.uint8)
        rgba = np.ascontiguousarray(rgba)
        img = QImage(rgba.data, nx, ny, 4 * nx, QImage.Format_RGBA8888).copy()
        item = QGraphicsPixmapItem(QPixmap.fromImage(img))
        tr = QTransform().scale(dx * 1000.0, dy * 1000.0)                 # Row 0 sits at y = 0
        if nodes:
            tr = QTransform().translate(-0.5 * dx * 1000.0, -0.5 * dy * 1000.0).scale(dx * 1000.0, dy * 1000.0)
        item.setTransform(tr)
        item.setOpacity(opacity)
        item.setZValue(0.5)
        item.setAcceptedMouseButtons(Qt.NoButton)
        self.scene().addItem(item)
        self._overlay = item

    def clear_overlay(self):
        """!
        @brief Remove the temperature overlay.
        """
        if self._overlay is not None and self._overlay.scene() is not None:
            self.scene().removeItem(self._overlay)
        self._overlay = None

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

    def _on_scene_selection(self):
        """!
        @brief Forward scene selection changes and refresh the vertex handles.
        """
        if self._rebuilding or self._external:
            return
        self._update_handles()
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
        """
        b = self.doc.problem.board
        W, H = b.width * 1000.0, b.height * 1000.0
        vw, vh = max(self.viewport().width(), 50), max(self.viewport().height(), 50)
        s = 0.9 * min(vw / W, vh / H)
        self.setTransform(QTransform().scale(s, -s))
        self.centerOn(W / 2, H / 2)
        self._fitted = True

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

    def wheelEvent(self, e):
        """!
        @brief Mouse wheel zooms around the cursor.
        @param e QWheelEvent (the vertical angle delta sets the zoom).
        """
        self.scale(1.15 ** (e.angleDelta().y() / 120.0), 1.15 ** (e.angleDelta().y() / 120.0))

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
        step = next((s for s in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if s * scale >= 60), 1000)
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
                painter.drawText(int(px) + 2, 10, f"{v:g}")
            k += 1
        # Vertical ruler: y grows upward in the board, downward on the screen
        y_top, y_bot = (origin.y() - 0) / scale, (origin.y() - h) / scale      # Board y at the top and bottom of the window
        k = int(np.floor(y_bot / minor))
        while k * minor <= y_top:
            v = k * minor
            py = origin.y() - v * scale
            major = abs(v / step - round(v / step)) < 1e-6
            painter.drawLine(size - (9 if major else 4), int(py), size, int(py))
            if major and py > size:
                painter.save()
                painter.translate(11, int(py) - 2)
                painter.rotate(-90)
                painter.drawText(0, 0, f"{v:g}")
                painter.restore()
            k += 1
        painter.drawText(2, 12, "mm")
        # Scale bar at the bottom left
        bar = step * scale
        x, y = size + 12, h - 14
        painter.drawLine(int(x), y, int(x + bar), y)
        painter.drawLine(int(x), y - 4, int(x), y + 4)
        painter.drawLine(int(x + bar), y - 4, int(x + bar), y + 4)
        painter.drawText(int(x + bar / 2 - 18), y - 6, f"{step:g} mm")

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
        super().mousePressEvent(e)

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
        super().mouseMoveEvent(e)

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
        super().mouseReleaseEvent(e)
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
        @brief Keyboard shortcuts: Delete, Ctrl+D, arrows, Enter, Esc, Space (pan).
        @param e QKeyEvent of the key press.
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
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.doc.delete(self.selected_elements())
        elif key == Qt.Key_D and e.modifiers() & Qt.ControlModifier:
            new = self.doc.duplicate(self.selected_elements())
            self.set_selection(new)
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
        pen = QPen(QColor("white"))
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
