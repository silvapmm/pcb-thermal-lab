#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file results_view.py
@brief Results area: summary table, temperature maps, gradients, profiles and component statistics.
"""

import contextlib
import html

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QFrame, QHeaderView, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .. import analysis, compare, defaults, plots, thickness
from . import layerchoice
from . import theme as th
from . import tips
from .elided import ElidedLabel
from .toolbar_icons import ThemedToolbar
from .display import DisplayState
from .flow import FlowLayout
from .warning_box import WarningAccordion
from ..api import SUMMARY_COLUMNS
from ..numfmt import num, signed_fixed
from ..results import model_full_label, model_label


@contextlib.contextmanager
def _mpl_theme(name):
    """!
    @brief Temporarily style matplotlib to match the application theme.
    @param name "dark" or "light".
    """
    c = th.colors(name)
    rc = {"figure.facecolor": c["base"], "axes.facecolor": c["alt"], "savefig.facecolor": c["base"],
          "text.color": c["text"], "axes.labelcolor": c["text"], "axes.edgecolor": c["border"],
          "xtick.color": c["text"], "ytick.color": c["text"], "grid.color": c["muted"],
          "legend.facecolor": c["base"], "legend.edgecolor": c["border"]}
    with matplotlib.rc_context(rc):
        yield


def _paint_figure(fig, name):
    """!
    @brief Give a figure and its axes the theme background (artists made later use the rc colours).
    @param fig Figure.
    @param name "dark" or "light".
    """
    c = th.colors(name)
    fig.patch.set_facecolor(c["base"])
    for ax in fig.axes:
        ax.set_facecolor(c["alt"])


MIN_SECTION = 56   # Logical px: the narrowest column of a results table
SUMMARY_WARNINGS_GAP_PX = 8   # Logical px between the Warnings box and the report console on the Summary page (the 8 px the dock leaves between boxes)


def _table(headers):
    """!
    @brief Create a read-only table with the given column headers.
    @param headers List of column titles.
    @return QTableWidget.
    """
    t = QTableWidget(0, len(headers))
    t.setToolTip("Values of the reference model; hover a column title for its meaning.")   # _fill_components names the model once there is a run
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.verticalHeader().setVisible(False)
    # Columns as wide as their header or text (at least MIN_SECTION px); a narrow window gets a horizontal scroll bar, never a cut header. No column stretches (review: the
    # appended read-out columns, such as 'Max °C (surface)', took the whole spare width and looked like the main column of the table); the spare width stays empty on the right
    head = t.horizontalHeader()
    head.setMinimumSectionSize(MIN_SECTION)
    head.setSectionResizeMode(QHeaderView.ResizeToContents)
    head.setStretchLastSection(False)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    t.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    t.setAlternatingRowColors(True)
    return t


def _fill(table, rows):
    """!
    @brief Fill a table with rows of already formatted strings.
    @param table QTableWidget.
    @param rows List of lists of str.
    """
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            item = QTableWidgetItem(text)
            if c > 0:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r, c, item)


def _fit_height(table, min_rows=3, max_rows=12):
    """!
    @brief Give a table the height of its rows, so that it shows them all without a scroll bar while there are at most max_rows of them.
    @details The table of the models had a fixed ceiling of 170 px, which showed a scroll bar as soon as five models ran although the window had room for
             more: the height now follows the number of rows (at least min_rows, so that an empty table does not collapse) and only above max_rows the
             vertical scroll bar appears.
    @param table QTableWidget (header on top, no horizontal scroll bar: its columns stretch).
    @param min_rows Rows of height reserved even when the table has fewer.
    @param max_rows Largest number of rows shown without a scroll bar.
    @return None.
    """
    rows = min(max(table.rowCount(), min_rows), max_rows)
    h = table.horizontalHeader().height() + rows * table.verticalHeader().defaultSectionSize() + 2 * table.frameWidth() + 2
    bar = table.horizontalScrollBar()
    if bar.maximum() > 0:                                  # A table with a horizontal scroll bar needs its height as well (nothing cut)
        h += bar.sizeHint().height()
    table.setFixedHeight(h)


class _SummaryTable(QTableWidget):
    """!
    @brief The models table of the Summary: columns as wide as their content, a horizontal scroll bar when they do not fit, the height of its rows.
    """

    def resizeEvent(self, event):
        """!
        @brief Fit the height again: the horizontal scroll bar appears or goes away with the width.
        @param event QResizeEvent.
        """
        super().resizeEvent(event)
        _fit_height(self, min_rows=self.rowCount() or 1)


def summary_table(ref_label="FVM"):
    """!
    @brief Create the models table of the Summary with the headers of the one column definition of the API (api.SUMMARY_COLUMNS).
    @details Headers in two lines name the read-out; every column is as wide as its header or its longest cell (at least MIN_SECTION px) and only the last one
             stretches, so that a narrow window shows a horizontal scroll bar instead of a cut header or number.
    @param ref_label Name of the reference model for the error column.
    @return QTableWidget.
    """
    t = _SummaryTable(0, 0)
    t.setToolTip(tips.MODEL_TABLE_TIP)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    t.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    set_summary_headers(t, list(SUMMARY_COLUMNS), ref_label)
    return t


def set_summary_headers(table, cols, ref_label):
    """!
    @brief Put the headers, the tooltips and the resize modes of the models table.
    @param table QTableWidget of summary_table.
    @param cols List of api.SummaryColumn.
    @param ref_label Name of the reference model for the error column.
    """
    table.setColumnCount(len(cols))
    table.setHorizontalHeaderLabels(["\n".join(c.header_lines(ref_label)) for c in cols])
    head = table.horizontalHeader()
    head.setMinimumSectionSize(MIN_SECTION)
    head.setSectionResizeMode(QHeaderView.ResizeToContents)
    head.setStretchLastSection(True)
    for i, c in enumerate(cols):
        table.horizontalHeaderItem(i).setToolTip(c.tip)


def recolour_toolbar(toolbar, theme):
    """!
    @brief Paint the icons of a Matplotlib navigation toolbar with the text token of the theme.
    @param toolbar NavigationToolbar2QT.
    @param theme "dark" or "light".
    @note Matplotlib picks the icon colour from the palette (a light cream in the dark theme); the shape (alpha) of the first icon of
          each action is kept and filled with the token, so a theme switch can recolour it again.
    """
    if hasattr(toolbar, "set_theme"):               # ThemedToolbar paints its own icons in the token colour
        toolbar.set_theme(theme)
        return
    colour = QColor(th.colors(theme)["text"])
    for act in toolbar.actions():
        if act.isSeparator() or act.icon().isNull():
            continue
        # The original shape is kept on the action once, a recoloured icon would lose nothing but this stays independent of the colour
        pm = act.property("_shape")
        if pm is None:
            pm = act.icon().pixmap(48, 48)
            act.setProperty("_shape", pm)
        out = QPixmap(pm.size())
        out.setDevicePixelRatio(pm.devicePixelRatio())
        out.fill(Qt.transparent)
        p = QPainter(out)
        p.drawPixmap(0, 0, pm)
        p.setCompositionMode(QPainter.CompositionMode_SourceIn)     # Keep the alpha, replace the colour
        p.fillRect(out.rect(), colour)
        p.end()
        act.setIcon(QIcon(out))


def redraw_when_shown(widget, redraw):
    """!
    @brief Redraw a tab now when it can be seen, or mark it to be drawn when it is shown.
    @details The toolbar Layer box moves every map at once; drawing the hidden tabs (a Matplotlib figure each) made a layer change in the editor about 30 times
             slower (0.004 to 0.11 s on the example board at 1 mm), so a hidden tab is drawn by its showEvent instead.
    @param widget The tab (QWidget).
    @param redraw Callable that draws the tab.
    """
    # Visible to its window: the current page of every tab widget above it (also before the window is first shown, and a tab without a parent)
    if widget.window() is widget or widget.isVisibleTo(widget.window()):
        widget._redraw_pending = False
        redraw()
    else:
        widget._redraw_pending = True


def redraw_pending(widget, redraw):
    """!
    @brief Draw a tab whose redraw was left for the moment it is shown.
    @param widget The tab (QWidget).
    @param redraw Callable that draws the tab.
    """
    if getattr(widget, "_redraw_pending", False):
        widget._redraw_pending = False
        redraw()


class CollapseSafeCanvas(FigureCanvasQTAgg):
    """!
    @brief Matplotlib canvas that paints a blank chart, without the Matplotlib warning, while it is too small for its decorations.
    @details A window dragged very small (or an offscreen test) leaves the constrained layout no room: the base canvas would warn at every paint. See `plots.draw_unless_collapsed`;
             the chart comes back by itself at the next paint after the canvas grew. Used by every chart of the Results tabs (maps, gradient, profile, Models,
             Components, power profile): measured in the review, each of them warned at a tiny canvas, and the Components chart already in a window of 900 x 600
             (its pane is then about 20 px tall). At a size where the layout succeeds the paint is the base one, pixel for pixel.
    """

    def draw(self):
        """!
        @brief Paint the figure, blank when the layout has no room.
        """
        plots.draw_unless_collapsed(self.figure, super().draw)


class PlotTab(QWidget):
    """!
    @brief A matplotlib canvas with the controls of one kind of plot.
    @details How the map is drawn (underlay, opacity, View, contour step, colour map) is not a control of the tab: it is the shared `DisplayState`, edited in the
             Display popover of the main toolbar, so the temperature and gradient maps, the Animation and the board can never disagree. The tab keeps Model, Layer,
             Hotspot and the colour limits.
    """

    CUT_SLIDER_MIN_PX = 100                             # Narrowest the Cut slider may be on a line shared with other controls; below it the slider gets a line of its own

    def __init__(self, kind, theme="dark", parent=None, display=None):
        """!
        @param kind "temperature", "gradient", "profile" or "compare".
        @param theme Colour theme name.
        @param parent Qt parent.
        @param display The shared DisplayState (a private one when None).
        """
        super().__init__(parent)
        self.kind, self.theme, self.sim = kind, theme, None
        self.display = display if display is not None else DisplayState(self)
        self._updating = False
        self.fig = Figure(layout="constrained")
        self.canvas = CollapseSafeCanvas(self.fig)      # Blank instead of a Matplotlib warning at every paint while the canvas is too small
        _paint_figure(self.fig, self.theme)             # An empty figure would be white on the dark theme
        self.toolbar = ThemedToolbar(self.canvas, self, self.theme)
        recolour_toolbar(self.toolbar, self.theme)

        self.model = QComboBox()
        self.model.setAccessibleName("Model")                  # Screen readers: the boxes of this row have a text label beside them, not a buddy
        self.layer_value = 0                            # The layer of the toolbar choice (see layerchoice): -1 / -2 all layers, 100 + face a metal block
        self.hot = QCheckBox("Hotspot contour")
        self.hot.setChecked(True)
        self.equiv = QCheckBox("Equiv. rect.")
        self.equiv.setChecked(True)
        self.equiv.setVisible(False)                    # Shown only for a LPTN or Analytic result of a board with an outline
        self.auto = QCheckBox("Auto range")
        self.auto.setChecked(True)
        self.vmin, self.vmax = QDoubleSpinBox(), QDoubleSpinBox()
        self.vmin.setAccessibleName("Lowest temperature of the colour scale"); self.vmax.setAccessibleName("Highest temperature of the colour scale")
        for s in (self.vmin, self.vmax):
            s.setRange(-100, 2000)
            s.setDecimals(1)
            s.setKeyboardTracking(False)
        self.axis = QComboBox()
        self.axis.setAccessibleName("Cut direction")
        self.axis.addItem("Along x", "x")
        self.axis.addItem("Along y", "y")
        self.pos = QSlider(Qt.Horizontal)
        self.pos.setAccessibleName("Cut position")
        self.pos.setRange(0, 1000)
        self.pos_label = QLabel()
        self.cut_overlay = QCheckBox("Cut overlay")      # Profiles: the board picture over the curves (content: toolbar Layer, Display, Map button); session only
        self.cut_overlay.setChecked(True)
        self.map_on = lambda: False                      # The main window says whether the Map button (T) is on
        self.model.setToolTip("Model whose result is drawn.")
        # The Difference view (temperature maps only): the map of (Model - reference) in K, read with the same definition for both models
        self.diff_on = QCheckBox("Difference to")
        self.diff_on.setAccessibleName("Show the difference between the model and a reference model")
        self.diff_ref = QComboBox()
        self.diff_ref.setAccessibleName("Reference model of the difference")
        # One line, the verdict first: is the gap between the hottest points usual for this pair (documented range)? The range, the scenarios, the cases outside and the
        # evidence are in its tooltip; the caveats of the figure are in the figure title. Its width never sets the page width (ElidedLabel).
        self.diff_note = ElidedLabel("", max_lines=1)
        self.diff_note.setAccessibleName("Whether the difference of the hottest points is usual for this pair of models")
        self.diff_row = self.diff_note
        # Writes the statistics of the Difference on view (largest, smallest, mean, RMS, where, models, read-out, cell, verdict line) as a small CSV; shown with the view only
        self.diff_export = QPushButton("Export statistics…")
        self.diff_export.setAccessibleName("Export the statistics of the Difference view to a CSV file")
        self.diff_export.setToolTip("Write the statistics of the Difference on view to a small CSV file: the largest and the smallest difference with their positions (mm), the mean and the "
                                    "RMS (K), the difference of the hottest points, the two models, the read-out, the cell and the verdict line. One row, the units are in the header.")
        self.diff_export.setVisible(False)
        self._diff_last = None                          # (DifferenceField, cell in mm, Agreement or None) of the view on screen, what the export writes
        self._ref_chosen = None                         # The reference the user picked (None: the default, `compare.default_reference`, follows the model shown)
        self.diff_row.setVisible(False)
        self._diff_tip = ("Draw the map of (Model minus the reference model) in K instead of the temperature: the same read-out for both models "
                                "(the layer's column mean, or the surface when the toolbar Layer box shows one), a diverging scale centred on zero. "
                                "Needs two or more models run. A difference between models is not always an error. The line below says whether the gap at the "
                                "hottest point is usual for that pair (the user guide has the evidence).")
        self.diff_on.setToolTip(self._diff_tip)
        self.diff_ref.setToolTip("The model subtracted: the map shows Model minus this one. The FVM is the reference of the program; a model that has no field "
                                 "or no value of the read-out shown is greyed out, with the reason as its tip.")
        self.equiv.setToolTip("LPTN and Analytic solve an outline board as a rectangle of the same area. Ticked: that rectangle as solved (dashed). "
                              "Unticked: the field stretched back onto the box (parts look larger).")
        self.vmin.setToolTip("Lowest temperature of the colour scale, °C (Auto range off).")
        self.vmax.setToolTip("Highest temperature of the colour scale, °C (Auto range off).")
        self.axis.setToolTip("Direction of the line the temperature is plotted along.")
        self.pos.setToolTip("Position of the cut: drag to move it.")
        self.cut_overlay.setToolTip("Board picture over the curves with the cut line. Hide it if it covers a curve.")

        # The temperature and gradient rows wrap (Auto range, min and max go to a second line in a narrow centre area); the profile row has a stretching slider
        controls = FlowLayout() if kind in ("temperature", "gradient") else QHBoxLayout()
        if kind in ("temperature", "gradient"):
            controls.addWidget(QLabel("Model"))                # The layer is the one choice of the main toolbar
            controls.addWidget(self.model)
            controls.addWidget(self.equiv)
            if kind == "temperature":
                controls.addWidget(self.diff_on)
                controls.addWidget(self.diff_ref)
                controls.addWidget(self.diff_export)
                controls.addWidget(self.hot)
                controls.addWidget(self.auto)
                controls.addWidget(self.vmin)
                controls.addWidget(self.vmax)
        elif kind == "profile":
            self._cut_label = QLabel("Cut")
            controls.addWidget(self._cut_label)
            controls.addWidget(self.axis)
            controls.addWidget(self.pos, 1)
            # The position text may be clipped in a very narrow centre area; its width must not set the minimum width of the Results page
            self.pos_label.setMinimumWidth(40)
            controls.addWidget(self.pos_label)
            controls.addWidget(self.cut_overlay)
            # In a narrow centre area the Cut overlay box goes to a line of its own (`_place_cut_overlay`); its width must not set the minimum width of the page
            self.cut_overlay.setMinimumWidth(1)
        if kind not in ("temperature", "gradient"):
            controls.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addLayout(controls)
        if kind == "temperature":
            lay.addWidget(self.diff_row)
        self._controls = controls
        if kind == "profile":
            self._controls3 = QHBoxLayout()             # Slider line, used only in a narrow tab (the slider then has the whole width); placed before the overlay line
            lay.addLayout(self._controls3)
            self._controls2 = QHBoxLayout()             # Second line of the profile controls, used only when the first does not hold the Cut overlay box
            lay.addLayout(self._controls2)
            self._cut_mode = None
        lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas, 1)

        for w in (self.model, self.axis):
            w.currentIndexChanged.connect(self.redraw)
        if kind in ("temperature", "gradient", "profile"):
            self.display.changed.connect(lambda _what: redraw_when_shown(self, self.redraw))     # A change of the shared display choice draws the map again
        for w in (self.hot, self.auto, self.equiv, self.cut_overlay, self.diff_on):
            w.toggled.connect(self.redraw)
        self.diff_ref.currentIndexChanged.connect(self._on_reference_changed)
        self.diff_export.clicked.connect(lambda: self.export_difference_statistics())
        for w in (self.vmin, self.vmax):
            w.valueChanged.connect(self.redraw)
        self.pos.valueChanged.connect(self.redraw)
        if kind == "profile":
            # The cut picture is an inset over the curves or a strip above them by the width of the canvas, so a resize that crosses that width draws the figure again
            self._thumb_strip = None
            self.canvas.mpl_connect("resize_event", self._on_canvas_resized)
        elif kind == "temperature":
            self.canvas.mpl_connect("resize_event", self._on_canvas_resized)      # The title of the Difference figure is wrapped for one width: fit it again

    def resizeEvent(self, e):
        """!
        @brief Lay out the control lines of the Profiles tab for the new width (`_place_cut_overlay`: one, two or three lines).
        @param e QResizeEvent.
        """
        super().resizeEvent(e)
        if self.kind == "profile":
            self._place_cut_overlay(e.size().width())

    def _place_cut_overlay(self, width):
        """!
        @brief Lay out the control lines of the Profiles tab by the width of the tab: all on one line, the Cut overlay box on a line of its own, or the
               slider and its position text on a line of their own as well (a slider squeezed to its handle cannot be used).
        @param width Width of the tab in pixels.
        """
        m = self.layout().contentsMargins()
        row = self._controls
        sp = row.spacing()
        # The position text is measured at a wide value, not at its current text: the text is empty before a run and changes with every move of the slider,
        # and a threshold that moved with it would put the slider on another line while it is dragged (the layout is chosen again at the next resize only)
        label_w = max(self.pos_label.sizeHint().width(), self.pos_label.minimumWidth(),
                      self.pos_label.fontMetrics().horizontalAdvance("y = 888.8 mm") + 2 * self.pos_label.margin())
        # Natural width of the line without the slider and the box (every widget at its size hint), plus the spacing and the margins
        base = self._cut_label.sizeHint().width() + self.axis.sizeHint().width() + label_w + m.left() + m.right() + 3 * sp
        # Mid: Cut, direction, slider, text, with no stretch after them, so the slider takes all the free width
        mid = base + self.CUT_SLIDER_MIN_PX
        # Wide (the line of a wide window, kept as it was): the slider shares the free width with the stretch after the box, about half each, so it needs twice
        wide = base + self.cut_overlay.sizeHint().width() + 2 * sp + 2 * self.CUT_SLIDER_MIN_PX
        mode = "wide" if width >= wide else "mid" if width >= mid else "narrow"
        if mode == getattr(self, "_cut_mode", None):
            return
        self._cut_mode = mode
        for lay in (row, self._controls2, self._controls3):
            while lay.count():
                lay.takeAt(0)                                                   # The widgets stay children of the tab; they are placed again below
        row.addWidget(self._cut_label)
        row.addWidget(self.axis)
        if mode == "narrow":
            row.addStretch(1)
            self._controls3.addWidget(self.pos, 1)
            self._controls3.addWidget(self.pos_label)
            self._controls2.addWidget(self.cut_overlay)
            self._controls2.addStretch(1)
            return
        row.addWidget(self.pos, 1)
        row.addWidget(self.pos_label)
        if mode == "wide":
            row.addWidget(self.cut_overlay)
            row.addStretch(1)
        else:
            self._controls2.addWidget(self.cut_overlay)
            self._controls2.addStretch(1)

    def _on_canvas_resized(self, _event):
        """!
        @brief On the Temperature page fit the title of the Difference figure again to the new size. On the Profiles page draw the figure again when the canvas crossed the width between the inset picture over the curves and the strip above them; otherwise fit
               the title and the y label again to the new size (their wrapping is measured for one size, and a window shrunk after the draw cut them again).
        @param _event Matplotlib ResizeEvent (unused).
        """
        if self.kind != "profile":
            if self.sim is not None:
                plots.refit_texts(self.fig)             # The Difference figure's title (any other map has nothing to fit: a no-op)
            return
        strip = plots.profile_has_strip(self.fig)
        if self._thumb_strip is not None and strip != self._thumb_strip and self.sim is not None:
            self.redraw()
        elif self.sim is not None:
            plots.refit_texts(self.fig)                 # The canvas paints right after this event (draw_idle of the Qt canvas)

    def map_view(self):
        """!
        @brief The MapView of the shared display choice, with the colours of the theme.
        @return plots.MapView, or None when the map is drawn as always (Current without an underlay).
        """
        return self.display.map_view(self.kind, self.theme)

    def set_theme(self, theme):
        """!
        @brief Change the plot theme.
        @param theme "dark" or "light".
        """
        self.theme = theme
        _paint_figure(self.fig, theme)                  # Also when nothing is drawn yet
        recolour_toolbar(self.toolbar, theme)
        self.canvas.draw_idle()
        self.redraw()

    def set_simulation(self, sim):
        """!
        @brief Show the results of a simulation.
        @param sim Simulation.
        """
        self.sim = sim
        self._diff_last = None                          # A new run: the statistics of the Difference of the old one are not exportable (the redraw sets them again)
        self.display.clear_cache()                      # The copper pictures belong to the problem of the simulation
        self._updating = True
        have = [k for k, r in sim.results.items() if r.T is not None]
        self.model.clear()
        for k in have:
            self.model.addItem(tips.model_label(k), k)        # The name of the Simulation panel, the key as data
        self.model.setCurrentIndex(max(self.model.findData("fvm"), 0))
        self.diff_ref.clear()
        for k, r in sim.results.items():                # Every model that ran, with or without a field: the ones that cannot be used are greyed out with the reason
            self.diff_ref.addItem(tips.model_label(k), k)
        self._ref_chosen = None                         # A new simulation: no choice of the user yet
        self.diff_ref.setCurrentIndex(max(self.diff_ref.findData(compare.default_reference(sim.results, self.model.currentData()) or ""), 0))
        ref = sim.reference
        if self.kind == "temperature":
            self.vmin.setValue(ref.ambient)
            self.vmax.setValue(round(ref.t_max + 0.5))
        if self.kind == "profile":
            self.pos.setValue(500)
        self._updating = False
        self.redraw()

    def block_faces(self):
        """!
        @brief Faces of the metal blocks that the models of the result drew (entries of the toolbar Layer box in Temperature).
        @return Sorted list of 0 (top) and 1 (bottom).
        """
        if self.sim is None:
            return []
        # The metal blocks of the finite-volume and finite-difference models are views of their own (data 100 and 101)
        return sorted({f for r in self.sim.results.values() for f in (0, 1) if f"block_{'top' if f == 0 else 'bottom'}_max" in r.extras})

    def surface_faces(self):
        """!
        @brief Faces of the outer copper whose surface read-out the result holds (entries 'Surface (top)' and 'Surface (bottom)' of the toolbar Layer box in Temperature).
        @details Present for the steady FVM, FDM, Analytic, 3D solid and FEM results (no thickness or size threshold; thin copper gives a milli-kelvin difference that the map title states);
                 a view of the map, never a mode: no number of any table changes with it. The LPTN and a time simulation give no entry, nor a face the Analytic leaves n/a (a part over absent copper).
        @return Sorted list of 0 (top) and 1 (bottom).
        """
        if self.sim is None:
            return []
        out = set()
        for r in self.sim.results.values():
            if "T_surface" in r.arrays:
                out |= {f for f in (0, 1) if np.isfinite(r.arrays["T_surface"][f]).any()}
        return sorted(out)

    def set_layer(self, value):
        """!
        @brief Show the layer chosen in the toolbar (or the fallback for this tab).
        @param value -1 all layers, -2 all in a 2 x 2 grid (temperature only), 100 + face a metal block (temperature only) or a layer index (0-based).
        """
        value = int(value)
        if value != self.layer_value:
            self.layer_value = value
            redraw_when_shown(self, self.redraw)

    def showEvent(self, e):
        """!
        @brief Draw the figure that a layer change left pending while the tab was hidden.
        @param e QShowEvent.
        """
        super().showEvent(e)
        redraw_pending(self, self.redraw)

    @staticmethod
    def _model_hot_point(r, layer):
        """!
        @brief Where the model reports its hottest point, when that is on the layer drawn.
        @param r SteadyResult shown.
        @param layer 0-based layer drawn.
        @return (x_m, y_m) of `SteadyResult.t_max_location`, or None (another layer, or no location: the map then computes its own hottest sample).
        """
        loc = r.t_max_location
        return (loc[1], loc[2]) if loc is not None and int(loc[0]) == layer else None

    def _layer_index(self):
        """!
        @brief The copper layer a single-layer picture shows (the stored choice kept on the board).
        @return int in 0..layers-1.
        """
        n = self.sim.problem.board.layers if self.sim is not None else 1
        return min(max(self.layer_value, 0), n - 1) if self.layer_value < 100 else 0

    def _result(self):
        """!
        @brief The result selected in the model combo.
        @return SteadyResult or None.
        """
        if self.sim is None:
            return None
        return self.sim.results.get(self.model.currentData()) if self.model.count() else None

    def current_field(self):
        """!
        @brief The temperature field currently displayed, for the board overlay.
        @return Tuple (field, dx, dy, cmap, vmin, vmax) or None.
        """
        r = self._result()
        if r is None or self.kind != "temperature":
            return None
        if self.layer_value >= 100:
            return None                                                # The overlay on the board shows the board layers only
        layer = self._layer_index()
        vmin = None if self.auto.isChecked() else self.vmin.value()
        vmax = None if self.auto.isChecked() else self.vmax.value()
        return r.T[layer], r.dx, r.dy, self.display.cmap, vmin, vmax

    def _difference_request(self):
        """!
        @brief What the Difference view would compare for the current toolbar Layer choice.
        @return Tuple (readout, layer, face, why): "column" with the layer shown (the first layer for the All-layers views), or "surface" with its face;
                `why` is a sentence when the choice has no difference (a metal block), else None.
        """
        v = self.layer_value
        if v >= layerchoice.SURFACE_BASE:
            return compare.SURFACE, 0, v - layerchoice.SURFACE_BASE, None
        if v >= layerchoice.BLOCK_BASE:
            return compare.COLUMN, 0, 0, "the Difference view does not apply to a metal block: choose a copper layer or a surface in the Layer box"
        return compare.COLUMN, self._layer_index(), 0, None

    def _refresh_difference_controls(self):
        """!
        @brief Enable or grey out the Difference controls and their reference items for the current model, layer and read-out; keep the reference valid.
        @return The key of the reference to use, or None when the view is off or impossible (the note then says why).
        """
        sim = self.sim
        was, self._updating = self._updating, True
        try:
            keys = list(sim.results) if sim is not None else []
            usable = [k for k in keys if sim.results[k].T is not None]
            self.diff_on.setEnabled(len(usable) >= 2)
            self.diff_on.setToolTip(self._diff_tip if len(usable) >= 2 else
                                    "Run two or more models with a field to compare them (Simulation panel). This run has " + (", ".join(tips.model_label(k) for k in usable) or "none") + ".")
            if sim is None or len(usable) < 2:
                return None
            current = self.model.currentData()
            readout, layer, face, why = self._difference_request()
            cur_res = sim.results.get(current)
            item_model = self.diff_ref.model()
            for i in range(self.diff_ref.count()):
                key = self.diff_ref.itemData(i)
                item = item_model.item(i)
                reason = why or (compare.unavailable_reason(cur_res, sim.results[key], sim.problem, readout, layer, face) if cur_res is not None else "no model shown")
                if key == current:
                    reason = "this is the model shown"
                item.setEnabled(reason is None)
                item.setToolTip(reason or f"Show {tips.model_label(current)} minus {tips.model_label(key)}")
            # The user's own choice stays while it is possible; a reference that the user did not choose is the default for the model now shown (the FVM, else the
            # first other model with a field), whichever model was shown when the box was first filled: moved silently, the title names the pair
            wanted = self._ref_chosen
            if wanted is None or wanted == current or not item_model.item(self.diff_ref.findData(wanted)).isEnabled():
                wanted = compare.default_reference(sim.results, current)
            enabled = lambda key: key is not None and self.diff_ref.findData(key) >= 0 and item_model.item(self.diff_ref.findData(key)).isEnabled()
            if not enabled(wanted):
                # The default cannot be used (an outline board refuses the LPTN and the Analytic against the FVM, a model without a surface ...): the first usable
                # reference in the order of the box; with none, the default itself, so that the refusal names the real reason and never 'the same model' (review:
                # the LPTN shown on an outline board kept the LPTN as its reference)
                usable_refs = [self.diff_ref.itemData(i) for i in range(self.diff_ref.count()) if enabled(self.diff_ref.itemData(i))]
                fallback = compare.default_reference(sim.results, current)
                wanted = usable_refs[0] if usable_refs else fallback
            if wanted is not None and self.diff_ref.findData(wanted) >= 0:
                self.diff_ref.setCurrentIndex(self.diff_ref.findData(wanted))
            return self.diff_ref.currentData()
        finally:
            self._updating = was

    def _on_reference_changed(self, _index):
        """!
        @brief The reference box changed: a change that is not the program's own (those run with `_updating` set) is the user's choice, kept until the model it names is the
               model shown or becomes impossible.
        @param _index New index (unused).
        """
        if not self._updating:
            self._ref_chosen = self.diff_ref.currentData()
        self.redraw()

    def _difference(self):
        """!
        @brief The Difference of the model shown and the chosen reference, when the view is on and possible; sets the note under the controls.
        @return compare.DifferenceField, or None (the map is then drawn as always).
        """
        ref = self._refresh_difference_controls()
        self.diff_row.setVisible(False)
        self.diff_export.setVisible(False)             # Back on only when a Difference is drawn (below)
        self._diff_last = None
        on = self.diff_on.isEnabled() and self.diff_on.isChecked()
        # The scale of a difference is symmetric and set by the data, and a hotspot contour is a temperature: those controls are hidden while the view is on
        for w in (self.hot, self.auto, self.vmin, self.vmax):
            w.setVisible(not on)
        if not on or self.kind != "temperature":
            return None
        sim, r = self.sim, self._result()
        readout, layer, face, why = self._difference_request()
        if why is None and ref is not None and r is not None:
            why = compare.unavailable_reason(r, sim.results[ref], sim.problem, readout, layer, face)
        if why is not None or ref is None:
            text = "Difference not shown: " + (why or "no other model has a field") + ". The temperature map is drawn."
            self._set_difference_line(text, text, True)
            return None
        d = compare.difference_field(r, sim.results[ref], sim.problem, readout, layer, face)
        caveat = ""
        if layer != self.layer_value and self.layer_value in (layerchoice.ALL_LAYERS, layerchoice.ALL_GRID):
            caveat = f"The Difference shows one layer at a time: layer {layer + 1} (choose another in the Layer box)."
        # The cell the user ran (the option, not the spacing of the grid, which round(width / cell) moves off it on a board that is not a whole number of cells)
        opts = getattr(sim, "options", None)
        cell = float(opts.cell_mm) if opts is not None else 1000.0 * d.dx
        agreement = compare.expected_agreement(d.model, d.reference, d.peak_k, d.peak_pct, cell)
        if agreement is not None:
            tip = agreement.tooltip + ("\n" + caveat if caveat else "") + ("\n" + "; ".join(d.notes) if d.notes else "")
            self._set_difference_line(agreement.line, tip, agreement.outside)
        elif caveat:
            self._set_difference_line(caveat, caveat, False)       # No documented range for the pair: no verdict, only the caveat of the layer
        self._diff_last = (d, cell, agreement)
        self.diff_export.setVisible(True)
        return d

    def export_difference_statistics(self, path=None):
        """!
        @brief Write the statistics of the Difference on view to a CSV file (`compare.write_statistics_csv`): one row, the units in the header names.
        @param path Output file path; None asks with a save dialog (tests pass a path).
        @return The path written, or None when no Difference is on view or the dialog was cancelled.
        """
        if self._diff_last is None:
            return None
        d, cell, agreement = self._diff_last
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export Difference statistics", f"difference_{d.model}_minus_{d.reference}.csv", "CSV files (*.csv)")
            if not path:
                return None
        return compare.write_statistics_csv(path, d, cell, agreement)

    def _set_difference_line(self, line, tooltip, warn):
        """!
        @brief Show the one line under the Difference controls.
        @param line The text of the line (the verdict first).
        @param tooltip Its tooltip (the range, the cases, the evidence).
        @param warn True for the warning colour of the theme (a gap outside the usual range, or a refusal).
        """
        self.diff_note.setText(line)
        self.diff_note.setToolTip(tooltip)                         # setText of the label puts the line itself in the tooltip
        self.diff_note.setStyleSheet(f"color: {th.colors(self.theme)['alert_note']};" if warn else "")
        self.diff_row.setVisible(True)

    def redraw(self, *_):
        """!
        @brief Redraw the figure from the current controls.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating or self.sim is None:
            return
        sim, prob = self.sim, self.sim.problem
        r0 = self._result()
        eq = r0.equivalent_scale if r0 is not None and prob.board.has_outline() else None
        self.equiv.setVisible(eq is not None and self.kind in ("temperature", "gradient"))
        # Ticked: the map as solved (the rectangle of the same area, its parts, dashed edge); amber token of the dark theme, readable on every colour map
        eq_args = {"equivalent_scale": eq if self.equiv.isChecked() else None, "equivalent_color": th.colors("dark")["alert"]}
        self.vmin.setEnabled(not self.auto.isChecked())
        self.vmax.setEnabled(not self.auto.isChecked())
        view = self.map_view() if self.kind in ("temperature", "gradient") else None    # None: the original picture, call for call
        diff = self._difference() if self.kind == "temperature" else None
        with _mpl_theme(self.theme):
            if diff is not None:
                plots.draw_difference(self.fig, diff, prob)
            elif self.kind == "temperature" and self._result() is not None:
                r = self._result()
                layer = self.layer_value
                cmap = self.display.cmap
                if layer in (-1, -2):
                    plots.draw_fields(self.fig, r, prob, cmap=cmap, show_equivalent=self.equiv.isChecked(), equivalent_color=eq_args["equivalent_color"],
                                      view=view, grid=layer == -2)
                elif layer >= layerchoice.SURFACE_BASE:
                    plots.draw_surface(self.fig, r, prob, layer - layerchoice.SURFACE_BASE, cmap=cmap)
                elif layer >= 100:
                    plots.draw_block(self.fig, r, prob, layer - 100, cmap=cmap)
                else:
                    layer = self._layer_index()
                    vmin = None if self.auto.isChecked() else self.vmin.value()
                    vmax = None if self.auto.isChecked() else self.vmax.value()
                    ax = plots.draw_field(self.fig, r.T[layer], prob, r.dx, r.dy, cmap=cmap, vmin=vmin, vmax=vmax, label=plots.COLUMN_LABEL,
                                          layer=layer, extremes=True, marker=self._model_hot_point(r, layer),
                                          hotspot=sim.options.hotspot_c if self.hot.isChecked() else None, **eq_args,
                                          title=f"{tips.model_label(r.model)} - layer {layer + 1}, column mean\n"
                                                f"Tmax {r.t_max:.1f} °C   Tmin {r.t_min:.1f} °C   Tmean {r.t_mean:.1f} °C", view=view)
                    ext = getattr(ax, "extreme_marks", None)
                    if ext is not None:
                        # The title quotes the two ringed values of THIS layer (the board Tmax, Tmin and Tmean are in the Summary): on a layer that does not hold
                        # the model's Tmax or the coolest point of the board, the board numbers contradicted the rings (0.2 to 0.5 K on the example board)
                        ax.set_title(f"{tips.model_label(r.model)} - layer {layer + 1}, column mean\n"        # Two lines: one line was cut at both ends in a 1200 px window
                                     f"max {ext['tmax']:.1f} °C   min {ext['tmin']:.1f} °C   mean {r.layer_mean[layer]:.1f} °C", fontsize=10)
            elif self.kind == "gradient" and self._result() is not None:
                r = self._result()
                layer = self._layer_index()
                g = analysis.gradient_magnitude(r)[layer]
                plots.draw_field(self.fig, g, prob, r.dx, r.dy, cmap=self.display.cmap, layer=layer,
                                 label="|∇T| (K/mm)", **eq_args, view=view,
                                 title=f"{tips.model_label(r.model)} - layer {layer + 1}   max gradient {g.max():.2f} K/mm")
            elif self.kind == "profile":
                axis = self.axis.currentData()
                b = prob.board
                length = (b.height if axis == "x" else b.width) * 1000.0
                pos = self.pos.value() / 1000.0 * length
                self.pos_label.setText(f"{'y' if axis == 'x' else 'x'} = {pos:.1f} mm")
                res = {k: r for k, r in sim.results.items() if r.T is not None}
                # The picture follows the shared Display choice (underlay, opacity, colour map) and the Map button; the Cut overlay box only shows or hides it
                under = self.display.apply(plots.MapView(), self.theme)
                picture = "off" if not self.cut_overlay.isChecked() else "map" if self.map_on() else "board"
                self._thumb_strip = plots.profile_has_strip(self.fig)
                plots.draw_profile(self.fig, res, prob, layer=self._layer_index(), axis=axis, position_mm=pos,
                                   picture=picture, underlay=under, map_alpha=self.display.value(), cmap=self.display.cmap)
            elif self.kind == "compare":
                plots.draw_comparison(self.fig, sim.results, sim.reference.model)
        _paint_figure(self.fig, self.theme)
        self.canvas.draw_idle()


MODELS_FIRST_COLUMN_MAX_PX = 120   # Logical px: the first column of the parts tables (longer part names are elided, the full name is the tooltip)
MODELS_CHART_MIN_PX = 280          # Logical px: the least height of the chart of the Models tab, toolbar included
MODELS_TABLES_MAX_PX = 300         # Logical px: the height the tables area asks for at most; beyond it the two tables scroll together in their one area


class ModelsTab(PlotTab):
    """!
    @brief The Models page: the temperature under every part in every model (two tables) and the whole board in every model (one chart).
    @details Top: one scroll area with two stacked tables, "Tmax: hottest point under the part" and "Tmean: mean under the part" (column read-out), one row per part and one column
             per model that ran (the reference first, in bold, headed "FVM (ref.)"). The cells hold plain values with one decimal and no colour; the difference from the reference
             is in the tooltip of the cell. Below a splitter: the bar chart of the whole board (`plots.draw_comparison`), at least MODELS_CHART_MIN_PX tall with its toolbar.
             The numbers are those of `Simulation.part_comparison()`, the one definition also used by the report and the CSV file.
    """

    def __init__(self, theme="dark", parent=None, display=None):
        """!
        @param theme Colour theme name.
        @param parent Qt parent.
        @param display The shared DisplayState (a private one when None).
        """
        super().__init__("compare", theme, parent, display)
        self.table_max = self._parts_table()
        self.table_mean = self._parts_table()
        self.title_max = QLabel("<b>Tmax</b>: hottest point under the part, °C (column)")
        self.title_mean = QLabel("<b>Tmean</b>: mean under the part, °C (column)")
        for title in (self.title_max, self.title_mean):
            # Wrapped: an unwrapped title holds the page at its text width (about 280 px), and in a narrower centre the area (no sideways bar) would cut the tables
            # and their own scroll bars at the right; wrapped, the tables take the width there is and scroll sideways by themselves
            title.setWordWrap(True)
        self.title_max.setToolTip("Hottest point of the column read-out under the footprint of each part, in every model that ran. The reference model is the first column, in bold; "
                                  "hover a cell for the difference from it.")
        self.title_mean.setToolTip("Mean of the column read-out under the footprint of each part, in every model that ran. The reference model is the first column, in bold; "
                                   "hover a cell for the difference from it. The LPTN has one node per part (two, the core and the rest, for a part over a group of vias): "
                                   "its mean is that node painted under the part.")
        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setVisible(False)
        self.models_shown = []                          # Keys of the model columns now shown (the reference first)
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        for w in (self.title_max, self.table_max, self.title_mean, self.table_mean, self.message):
            il.addWidget(w)
        il.addStretch(1)
        self._inner = inner
        self.area = QScrollArea()
        self.area.setWidget(inner)
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)   # The columns fit the page at 1200 px (tested); a table scrolls by itself in a narrower one
        # The toolbar and the chart move under a splitter, so that the user gives height to the tables or to the chart
        lay = self.layout()
        lay.removeWidget(self.toolbar)
        lay.removeWidget(self.canvas)
        self.chart_box = QWidget()
        cl = QVBoxLayout(self.chart_box)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self.toolbar)
        cl.addWidget(self.canvas, 1)
        self.chart_box.setMinimumHeight(MODELS_CHART_MIN_PX)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.area)
        self.splitter.addWidget(self.chart_box)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        lay.addWidget(self.splitter, 1)

    @staticmethod
    def _parts_table():
        """!
        @brief One table of the page: read-only, columns of the width we set (no stretching), no vertical scroll bar (the page's area scrolls).
        @return QTableWidget.
        """
        t = _table(["Part"])
        t.setToolTip("One row per part, one column per model that ran, the reference model first (in bold). Hover a cell for its value with two decimals and the "
                     "difference from the reference; hover a column title for the model.")      # Each cell and header says more
        head = t.horizontalHeader()
        head.setSectionResizeMode(QHeaderView.Interactive)
        head.setStretchLastSection(False)
        t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        t.setTextElideMode(Qt.ElideRight)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        return t

    def clear_results(self):
        """!
        @brief Empty the tables (the board was changed: the run no longer belongs to it).
        """
        self.models_shown = []
        for t in (self.table_max, self.table_mean):
            t.setRowCount(0)
            t.setColumnCount(1)
            t.setHorizontalHeaderLabels(["Part"])
        self.message.setVisible(False)
        self._fit_heights()

    def set_simulation(self, sim):
        """!
        @brief Show a simulation: the chart (as every tab) and the two tables of the parts.
        @param sim Simulation.
        """
        super().set_simulation(sim)
        self._fill_parts(sim)

    @staticmethod
    def _cell_tip(model, part, key, value, delta, ref):
        """!
        @brief Tooltip of a cell: what the number is, its two decimals and the difference from the reference.
        @param model Model key of the column.
        @param part Dict of one part of `Simulation.part_comparison()`.
        @param key "t_max" or "t_mean".
        @param value Temperature in degC or None.
        @param delta Difference from the reference in K or None.
        @param ref Key of the reference model.
        @return str.
        """
        what = "max under" if key == "t_max" else "mean under"
        head = f"{model_label(model)}{' (reference)' if model == ref else ''}, {what} {part['name']} (column)"
        if value is None:
            return f"{head}: no value in this model."
        text = f"{head}: {value:.2f} °C"
        if delta is not None:
            text += f", {delta:+.2f} K vs {model_label(ref)} (reference)"
        if model == "lumped":
            text += ("." + (" The LPTN has one node per part (two, the core and the rest, for a part over a group of vias): the part's mean is that node, "
                            "painted under the part." if key == "t_mean" else
                            " The LPTN maximum is the network's own peak of the part: its node plus the peak term plus the rise the other parts give at its centre."))
        return text

    def _fill_parts(self, sim):
        """!
        @brief Fill the two tables from `Simulation.part_comparison()`: the reference column first and in bold, plain numbers, the differences in the tooltips.
        @param sim Simulation.
        """
        cmp = sim.part_comparison()
        models, ref, parts = cmp["models"], cmp["reference"], cmp["parts"]
        self.models_shown = list(models)
        bold = QFont()
        bold.setBold(True)
        for t, key in ((self.table_max, "t_max"), (self.table_mean, "t_mean")):
            t.setRowCount(0)
            t.setColumnCount(1 + len(models))
            t.setHorizontalHeaderLabels(["Part"] + [f"{model_label(m)} (ref.)" if m == ref else model_label(m) for m in models])
            t.horizontalHeaderItem(0).setToolTip("The part (its name and its power, W); a long name is cut here, the whole name is the tooltip of the cell.")
            for j, m in enumerate(models):
                head = t.horizontalHeaderItem(1 + j)
                head.setToolTip(f"{model_full_label(m)}" + (": the reference model, the one of the Components page and the report. Other columns: hover a cell for the difference from it." if m == ref else
                                                           f". Hover a cell for the difference from {model_label(ref)} (reference)."))
                if m == ref:
                    f = head.font()
                    f.setBold(True)
                    head.setFont(f)
            t.setRowCount(len(parts))
            for r, part in enumerate(parts):
                label = f"{part['name']}  {part['power_w']:.2f} W"
                first = QTableWidgetItem(label)
                first.setToolTip(f"{part['name']} (layer {part['layer']}), {part['power_w']:.2f} W in the reference model")
                t.setItem(r, 0, first)
                for j, m in enumerate(models):
                    v = part[key][m]
                    cell = QTableWidgetItem("n/a" if v is None else f"{v:.1f}")
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    cell.setToolTip(self._cell_tip(m, part, key, v, part[key + "_delta"][m], ref))
                    if m == ref:
                        cell.setFont(bold)
                    t.setItem(r, 1 + j, cell)
        if parts:
            self.message.setVisible(False)
        else:
            self.message.setText("This board has no part (heater), so there is no temperature under a part to compare. The chart below compares the whole board in every model.")
            self.message.setVisible(True)
        self._set_widths()
        self._fit_heights()

    def _set_widths(self):
        """!
        @brief Give the two tables the same column widths: each column as wide as its widest text in either table, the first one at most MODELS_FIRST_COLUMN_MAX_PX.
        """
        for t in (self.table_max, self.table_mean):
            t.resizeColumnsToContents()
        for c in range(self.table_max.columnCount()):
            w = max(self.table_max.columnWidth(c), self.table_mean.columnWidth(c), MIN_SECTION)
            if c == 0:
                w = min(w, MODELS_FIRST_COLUMN_MAX_PX)
            for t in (self.table_max, self.table_mean):
                t.setColumnWidth(c, w)

    def _fit_heights(self):
        """!
        @brief Give each table the height of its rows (the area scrolls them together) and the area the height of its content up to MODELS_TABLES_MAX_PX.
        """
        for t in (self.table_max, self.table_mean):
            h = t.horizontalHeader().height() + sum(t.rowHeight(r) for r in range(t.rowCount())) + 2 * t.frameWidth() + 2
            if t.horizontalScrollBar().maximum() > 0:               # A table in a page too narrow for its columns keeps its own bar, and the height for it
                h += t.horizontalScrollBar().sizeHint().height()
            t.setFixedHeight(h)
        # The wrapped titles have a height for the width they get: ask for it at the width of the area (the plain size hint assumes a narrower title on two lines)
        width = self.area.viewport().width()
        need = self._inner.heightForWidth(width) if (self._inner.hasHeightForWidth() and width > 0) else -1
        if need <= 0:
            need = self._inner.sizeHint().height()
        self.area.setMinimumHeight(min(need, MODELS_TABLES_MAX_PX))

    def resizeEvent(self, e):
        """!
        @brief Refit the table heights when the page changes size (a table that gets a horizontal bar needs the room for it).
        @param e QResizeEvent.
        """
        super().resizeEvent(e)
        if self.table_max.rowCount() or self.table_max.columnCount() > 1:
            self._fit_heights()

    def showEvent(self, e):
        """!
        @brief Size the tables and give the splitter its first division when the page is first shown (the sizes are those of a shown widget).
        @param e QShowEvent.
        """
        super().showEvent(e)
        self._fit_heights()
        if not getattr(self, "_split_done", False):
            self._split_done = True
            self.splitter.setSizes([self.area.minimumHeight(), 10000])


class Cover(QLabel):
    """!
    @brief An opaque note laid over a results page (the page keeps its widgets): used when the results belong to another board than the one now open.
    """

    def __init__(self, page, text):
        """!
        @param page The page (QWidget) the note covers.
        @param text The note.
        """
        super().__init__(text, page)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMargin(24)
        self.setAutoFillBackground(True)                # The page below must not show through
        page.installEventFilter(self)                   # Follow the size of the page
        self.hide()

    def eventFilter(self, obj, event):
        """!
        @brief Keep the note the size of its page.
        @param obj The page.
        @param event The event.
        @return False (the page handles its own events).
        """
        # isHidden, not isVisible: a cover over a page that is not the current tab is not 'visible' while its page is hidden, so it kept the size the page had
        # when the cover was made (review of branch C: before the first run the note of the Temperature page was cut at 1200 x 800 and was a small grey box
        # at 1500 x 900); the size is also taken again when the page is shown
        if event.type() in (QEvent.Resize, QEvent.Show) and not self.isHidden():
            self.setGeometry(obj.rect())
        return False

    def cover(self, on):
        """!
        @brief Show or hide the note.
        @param on True to cover the page.
        """
        if on:
            self.setGeometry(self.parentWidget().rect())
            self.raise_()
        self.setVisible(on)


class ResultsView(QWidget):
    """!
    @brief The whole results area.
    """

    START_NOTE = "No results yet. Draw at least one heater with a power above zero on the Board tab and press Run simulation (F5)."
    CLEARED_NOTE = "No results for this board yet. Press Run simulation (F5)."           # The notes over the plot pages: before any run, and after another board was opened

    show_on_board = Signal()

    def __init__(self, theme="dark", parent=None, display=None):
        """!
        @param theme Colour theme name.
        @param parent Qt parent.
        @param display The shared DisplayState of the maps (a private one when None).
        """
        super().__init__(parent)
        self.theme, self.sim = theme, None
        self.display = display if display is not None else DisplayState(self)     # One choice of how the maps are drawn, for every tab that draws one
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        # One short line over the maps when the tab cannot show the layer choice of the toolbar (it shows the last single layer and says so)
        self.layer_note = QLabel()
        self.layer_note.setWordWrap(True)
        self.layer_note.setVisible(False)
        self._layer_note_text = ""
        lay.addWidget(self.layer_note)
        self.tabs = QTabWidget()
        self.tabs.tabBar().setElideMode(Qt.ElideNone)             # "Components" was cut to "Compone…" in a narrow window
        self.tabs.tabBar().setUsesScrollButtons(True)
        lay.addWidget(self.tabs)

        # Summary: models table, warnings and the text report
        summary = QWidget()
        sl = QVBoxLayout(summary)
        # Headers in two lines name the read-out; the columns come from the one definition of the API (api.SUMMARY_COLUMNS), as wide as their content
        self.model_table = summary_table()
        _fit_height(self.model_table, min_rows=1)            # The height follows the rows (as many as there are models), see _fit_height
        self.warnings = WarningAccordion("summary", select=False)       # The notes of the run: 'Warnings (N)' with closed rows
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        # An empty Results tab said nothing: it now tells a first-time user what to do
        self.report.setPlaceholderText("No results yet. Draw at least one heater with a power above zero on the Board tab and press Run simulation (F5): "
                                       "the table above compares the models and the report of the run appears here.")
        self.report.setStyleSheet("font-family: Menlo, Consolas, monospace;")
        # Room under the Warnings box so it is not stuck to the report console; a margin of the (hidden when empty) accordion, so no gap shows without notes
        self.warnings.layout().setContentsMargins(0, 0, 0, SUMMARY_WARNINGS_GAP_PX)
        sl.addWidget(self.model_table)
        sl.addWidget(self.warnings)
        sl.addWidget(self.report, 1)
        self.tabs.addTab(summary, "Summary")

        self.temp = PlotTab("temperature", theme, display=self.display)
        self.grad = PlotTab("gradient", theme, display=self.display)
        self.profile = PlotTab("profile", theme, display=self.display)
        self.compare = ModelsTab(theme, display=self.display)
        self.tabs.addTab(self.temp, "Temperature")
        self.tabs.addTab(self.grad, "Gradients")
        self.tabs.addTab(self.profile, "Profiles")

        # Components: heater and zone statistics plus a bar chart
        comp = QWidget()
        cl = QVBoxLayout(comp)
        split = QSplitter(Qt.Vertical)
        tables = QWidget()
        tl = QVBoxLayout(tables)
        # One line naming the model of every number on this page (first widget of the pane the user resizes, so it adds no fixed height to the page);
        # ElidedLabel never wraps and never asks for width, the long explanation is its tooltip. Hidden until a run.
        self.reference_line = th.hint(ElidedLabel("", max_lines=1))
        self.reference_line.setVisible(False)
        tl.addWidget(self.reference_line)
        self.heater_table = _table(["Heater", "Layer", "Power W", "Mean °C", "Max °C", "Junction °C", "Margin K", "Power limit W", "Top path W"])
        # Every temperature the user sees names its read-out: these tables are all column values (the layer mean through the copper thickness), like the part table
        self.zone_table = _table(["Zone", "Layer", "Mean °C\n(column)", "Max °C\n(column)", "Min °C\n(column)"])
        self.hot_table = _table(["Hotspot", "Layer", "Tmax °C\n(column)", "x mm", "y mm", "Area mm²"])
        self.block_table = _table(["Metal block", "Face", "Mean °C\n(block)", "Max °C\n(block)", "Heat in W", "Heat to air W"])     # The block read-out: the mean through the block
        self.block_table.setMaximumHeight(110)                 # Two rows (a block on each side) under the two-line header that names the read-out
        # The headers name the read-out; their tooltips say what it is (the part table sets its own when it is filled; the models table has one per column)
        for t, cols, tip in ((self.zone_table, (2, 3, 4), tips.COLUMN_TABLE_TIP), (self.hot_table, (2,), tips.COLUMN_TABLE_TIP), (self.block_table, (2, 3), tips.BLOCK_TABLE_TIP)):
            for c in cols:
                t.horizontalHeaderItem(c).setToolTip(tip)
        for t in (self.heater_table, self.zone_table, self.hot_table, self.block_table):
            tl.addWidget(t)
        split.addWidget(tables)
        self.comp_fig = Figure(layout="constrained")
        self.comp_canvas = CollapseSafeCanvas(self.comp_fig)    # Its pane is about 20 px tall in a 900 x 600 window: blank there, no warning
        split.addWidget(self.comp_canvas)
        split.setSizes([360, 260])
        split.setStretchFactor(1, 1)            # A taller window gives its extra height to the chart; no minimum height (it would bring the page scroll bar back)
        cl.addWidget(split)
        self.tabs.addTab(comp, "Components")
        self.tabs.addTab(self.compare, "Models")
        from .animation import AnimationTab        # Imported here: animation imports helpers from this module
        self.animation = AnimationTab(theme, display=self.display)
        self._anim_warns = []                                   # Notes of the last animation, listed in the summary after those of the run
        self.animation.warnings_changed.connect(self._on_animation_warnings)
        self.tabs.addTab(self.animation, "Animation")
        from .profile_results import ProfileResultsTab
        self.time_sim = ProfileResultsTab(theme)
        self.tabs.addTab(self.time_sim, "Power profile")
        # The pages that show a run are covered by a note while the results belong to another board (see clear)
        self._covers = [Cover(page, "No results for this board yet. Press Run simulation (F5).") for page in (summary, self.temp, self.grad, self.profile, comp, self.compare, self.time_sim)]
        # Before the first run every plot page says what to do (review of the window: only the Summary had an empty state, the maps were blank figures);
        # the Summary keeps its own note in the report box
        for cover in self._covers[1:]:
            cover.setText(self.START_NOTE)
            cover.cover(True)
        # The stack takes the largest minimum width of its pages: the Animation and Power profile controls (about 530 px) made the whole Results page scroll
        # sideways in a narrow centre area, also on the Profiles tab. Only the page shown counts: the hidden pages ignore their size hints, so a narrow tab
        # never scrolls and a wide one (Animation) still scrolls to reach its controls instead of clipping them.
        self.tabs.currentChanged.connect(self._size_to_current_page)
        self._size_to_current_page(self.tabs.currentIndex())

    def _size_to_current_page(self, index):
        """!
        @brief Let only the page shown set the minimum size of the Results tabs (the hidden pages get the Ignored size policy).
        @param index Index of the page shown.
        """
        for i in range(self.tabs.count()):
            policy = QSizePolicy.Preferred if i == index else QSizePolicy.Ignored
            self.tabs.widget(i).setSizePolicy(policy, policy)
        self.tabs.updateGeometry()

    def set_layer_note(self, text):
        """!
        @brief Show or hide the one-line note over the maps about the layer fallback.
        @param text The note, or "" to hide it.
        """
        self._layer_note_text = text
        tone = th.colors(self.theme)["alert_note"]
        self.layer_note.setTextFormat(Qt.RichText)
        self.layer_note.setText(f"<span style='color:{tone}'>{html.escape(text)}</span>" if text else "")
        self.layer_note.setVisible(bool(text))

    def set_layer(self, temperature, single):
        """!
        @brief Hand the layer choice of the toolbar to every tab that draws a layer.
        @param temperature Entry for the Temperature tab (-1, -2, 100 + face or a layer index).
        @param single The single layer for the other tabs (0-based).
        """
        self.temp.set_layer(temperature)
        for t in (self.grad, self.profile, self.animation, self.time_sim):
            t.set_layer(single)

    def _on_animation_warnings(self, warns):
        """!
        @brief Keep the notes of a finished animation and show them in the summary under those of the run.
        @param warns List of warning strings of the animation.
        """
        self._anim_warns = list(warns)                 # Keep the objects: they carry their severity
        if getattr(self, "sim", None) is not None:
            self._show_warnings(self.sim.warnings)
            self.warnings.setVisible(bool(self.warnings.warnings))

    def _show_warnings(self, warns):
        """!
        @brief Write the notes of the run in the Warnings box under the models table (closed rows with clean titles; a row the user opened stays open).
        @param warns List of warning strings.
        """
        warns = list(warns) + [w for w in self._anim_warns if w not in warns]
        self.warnings.set_warnings(warns)

    def set_underlay_source(self, imported, cfg):
        """!
        @brief Tell the display choice what the project offers under the map (copper, and the image of a hand-drawn project); the maps are drawn again when it changed.
        @param imported True when the project comes from Gerber files (Copper only).
        @param cfg The `view["background"]` dict of the project or None (the Image entry exists for a hand-drawn project with an image).
        @return True when something changed.
        """
        return self.display.set_source(imported, cfg)         # Its `changed` signal draws the maps

    def set_theme(self, theme):
        """!
        @brief Change the theme of all plots.
        @param theme "dark" or "light".
        """
        self.theme = theme
        self.set_layer_note(self._layer_note_text)
        if getattr(self, "sim", None) is not None:
            self._show_warnings(self.sim.warnings)             # The notes take the colour of the new theme
        for t in (self.temp, self.grad, self.profile, self.compare):
            t.set_theme(theme)
        self.animation.set_theme(theme)
        self.time_sim.set_theme(theme)
        self._draw_components()

    def clear(self):
        """!
        @brief Forget the run: another board was opened or created, so the pages that show a run say there are no results for it yet.
        """
        self.sim = None
        self.reference_line.setVisible(False)       # No run, no reference model to name
        # The covered Temperature page keeps its old figure: the Difference it showed must not be exportable (nor its button shown) for a board it does not belong to
        self.temp._diff_last = None
        self.temp.diff_export.setVisible(False)
        self.compare.clear_results()
        for cover in self._covers:
            cover.setText(self.CLEARED_NOTE)
            cover.cover(True)

    def set_simulation(self, sim):
        """!
        @brief Display a finished simulation.
        @param sim Simulation.
        """
        self.sim = sim
        for cover in self._covers:
            cover.cover(False)
        cols, rows, cell_tips = sim.summary_grid(tips.model_label)
        set_summary_headers(self.model_table, cols, tips.model_label(sim.reference.model))
        _fill(self.model_table, rows)
        for r, per_cell in enumerate(cell_tips):                # The raw energy balance is in the tooltip of its cell (the cell shows a percentage with a floor)
            for c, tip in per_cell.items():
                self.model_table.item(r, c).setToolTip(tip)
        self.model_table.resizeColumnsToContents()
        _fit_height(self.model_table, min_rows=len(rows))
        self._anim_warns = []                                   # A new run: the notes of the old animation are gone
        warns = sim.warnings
        self._show_warnings(warns)
        self.warnings.setVisible(bool(warns))
        self._fill_report()
        for t in (self.temp, self.grad, self.profile, self.compare):
            t.set_simulation(sim)
        self._fill_components()
        self._draw_components()
        self.time_sim.set_simulation(sim)
        if sim.decisions:
            self.tabs.setCurrentWidget(self.time_sim if sim.profile_results else self.tabs.widget(0))

    def _fill_report(self):
        """!
        @brief Write the report text of the Summary page for the shown simulation, following the Preferences setting `results.summary_table_in_report`.
        @details Off (shipped): no table in the text, since the models table is the widget above it. On: the text also holds the aligned table. The warnings are
                 never repeated in the text (the box above it shows them). Only the way the text is written depends on the setting; no number does.
        @return None.
        """
        if self.sim is None:
            return
        try:
            # Only a JSON true turns it on: a hand-edited "false" (a non-empty string) must not read as on
            with_table = defaults.value("results", "summary_table_in_report") is True
        except (KeyError, TypeError, OSError):
            with_table = False                                  # An unreadable preference falls back to the shipped behaviour
        self.report.setPlainText(self.sim.report(inline_warnings=False, table=with_table))

    def refresh_report(self):
        """!
        @brief Rewrite the report text after the preferences changed (called by the main window when Preferences were saved); nothing to do without a result.
        @return None.
        """
        self._fill_report()

    def _name_reference(self, key):
        """!
        @brief Say which model every number of the Components page comes from: the line above the tables, their tooltips and (in _draw_components) the chart title.
        @param key Model key of the reference model (fvm, lumped, analytic, fdm, solid3d, fem).
        """
        self.reference_line.setText(f"Reference model: {model_full_label(key)}. Other models: the Models tab.")
        # setText sets the tooltip to the text; the long explanation replaces it
        self.reference_line.setToolTip(
            "Every number on this page (heaters, zones, hotspots, metal block and the chart) comes from the reference model: the FVM when it runs, "
            f"otherwise the first model that ran (here: {model_label(key)}). The Model box of the maps does not change this page; "
            "compare the models in the Models tab or the Summary.")
        self.reference_line.setVisible(True)
        tip = f"Values of the reference model ({model_label(key)}); hover a column title for its meaning."
        for t in (self.heater_table, self.zone_table, self.hot_table, self.block_table):
            t.setToolTip(tip)

    def _fill_components(self):
        """!
        @brief Fill the heater, zone and hotspot tables from the reference model.
        """
        sim, ref = self.sim, self.sim.reference
        if ref.T is None:
            self.reference_line.setVisible(False)       # No field to fill the tables from: never leave the name of the previous run's model on the line
            return
        self._name_reference(ref.model)
        heaters = sim.heater_rows()
        # Every temperature column names its read-out and ONE surface column always follows (decision: the surface is always shown beside the column mean, no threshold):
        # the hottest point of the outer face under the part, in the face of its source. The difference to the column in K and in % of the rise is in the tooltip of the
        # cell (a narrow column is not worth a second table column). Junction, margin and power limit stay on the column. 'n/a' where the model or the layer has no surface.
        # Two-line headers: the stretched columns of this table are too narrow for one line of these names (they were cut in a screenshot)
        heads = ["Heater", "Layer", "Power W", "Mean °C\n(column)", "Max °C\n(column)", "Junction °C", "Margin K", "Power limit W", "Top path W",
                 f"Max °C\n(surface,\n{thickness.surface_kind(ref)})" if "T_surface" in ref.arrays else "Max °C\n(surface)"]
        self.heater_table.setColumnCount(len(heads))
        self.heater_table.setHorizontalHeaderLabels(heads)
        hi = self.heater_table.horizontalHeaderItem
        hi(3).setToolTip(tips.COLUMN_HEADER_TIP)
        hi(4).setToolTip(tips.COLUMN_HEADER_TIP)
        hi(len(heads) - 1).setToolTip(tips.SURFACE_MAX_TIP)
        rows, notes = [], []
        n_layers = sim.problem.board.layers
        rise = max(ref.t_max - ref.ambient, 1e-9)
        for h in heaters:
            row = [h["name"], str(h["layer"]), f"{h['power_w']:.2f}", f"{h['t_mean']:.1f}", f"{h['t_max']:.1f}",
                   f"{h['t_junction']:.1f}" if h["t_junction"] is not None else "-",
                   f"{h['margin_k']:.1f}" if h["margin_k"] is not None else "-",
                   f"{h['p_limit_w']:.2f}" if h["p_limit_w"] is not None else "-",
                   f"{h['power_top_w']:.2f}" if h["power_top_w"] > 0 else "-"]
            if "t_max_surface" in h:
                d = h["t_max_surface"] - h["t_max"]
                face = "top face of its layer" if h["layer"] == 1 else "bottom face of its layer"
                row.append(f"{h['t_max_surface']:.1f}" + (" (upper)" if h["surface_upper"] else ""))
                hf = 0 if h["layer"] == 1 else 1
                kind = thickness.surface_kind(ref, hf)
                how = ("Resolved by the finite elements (not an estimate). " if kind == "resolved" else
                       "Computed from the copper slabs of the 3D solid (the half slab above the outer one; not an estimate by a parabola). " if kind == "computed" else
                       thickness.surface_how(ref, h["surface_upper"], hf)[0].upper() + thickness.surface_how(ref, h["surface_upper"], hf)[1:] + ". ")
                hot_node = ""
                if ref.model == "fem" and "T_point" in ref.arrays:
                    # The hottest mesh node under the part, a read-out of its own (the element mean is what the maps and tables show)
                    pt = analysis.point_max(ref, sim.problem.heaters[len(rows)].polygon, sim.problem.heaters[len(rows)].layer, sim.problem.board.outline)
                    if pt is not None:
                        hot_node = f" Hottest node under the part: {pt:.3f} °C."
                notes.append(how + f"{face}: {h['t_max_surface']:.3f} °C, {signed_fixed(d, 3)} K ({signed_fixed(100 * d / rise, 3)} % of the rise) from the column max {h['t_max']:.3f} °C. "
                             "Surface mean " + f"{h['t_mean_surface']:.3f} °C." + hot_node + " " + tips.SURFACE_TRAP_TIP)
            else:
                row.append("n/a")
                if "surface_bound_k" in h:
                    notes.append(thickness.lumped_surface_note(h["surface_bound_k"], h["layer"]))
                elif ref.model not in ("fvm", "fdm", "fem", "analytic", "solid3d"):
                    notes.append(f"The {tips.model_label(ref.model)} model has no surface read-out (steady FVM, FDM, Analytic, 3D solid and FEM only); the column is the only read-out.")
                elif 1 < h["layer"] < n_layers:
                    notes.append("A part on an inner copper layer has no outer face: its surface is the column (the temperature is continuous across the interface).")
                elif thickness.surface_na_reason(ref, 0 if h["layer"] == 1 else 1):
                    # The Analytic does not show a surface on a face with a part over absent copper (thickness.attach_field): say why
                    notes.append("No surface value: " + thickness.surface_na_reason(ref, 0 if h["layer"] == 1 else 1) + ".")
                else:
                    notes.append("No surface value under this part.")
            rows.append(row)
        _fill(self.heater_table, rows)
        for r, note in enumerate(notes):
            self.heater_table.item(r, len(heads) - 1).setToolTip(note)
        # The heater table keeps room for two rows AND its horizontal scroll bar (review of the branch: at 1200 x 800 the bar took the height of the second
        # row of the example board, so U2 was behind a vertical scroll bar)
        t = self.heater_table
        t.setMinimumHeight(t.horizontalHeader().sizeHint().height() + min(max(t.rowCount(), 1), 2) * t.verticalHeader().defaultSectionSize()
                           + t.horizontalScrollBar().sizeHint().height() + 2 * t.frameWidth() + 2)
        # The zone and hotspot tables: column values as always; the surface (and, for the FEM, the hottest node) of the same area or point is APPENDED, never in place of them
        zones = analysis.zone_stats(ref, sim.problem)
        has_surface = "T_surface" in ref.arrays
        zheads = ["Zone", "Layer", "Mean °C\n(column)", "Max °C\n(column)", "Min °C\n(column)"] + (["Max °C\n(surface)"] if has_surface else [])
        self.zone_table.setColumnCount(len(zheads))
        self.zone_table.setHorizontalHeaderLabels(zheads)
        for c in (2, 3, 4):
            self.zone_table.horizontalHeaderItem(c).setToolTip(tips.COLUMN_TABLE_TIP)
        if has_surface:
            self.zone_table.horizontalHeaderItem(5).setToolTip(tips.SURFACE_MAX_TIP)
        zrows = []
        for z in zones:
            row = [z["name"], str(z["layer"]), f"{z['t_mean']:.1f}", f"{z['t_max']:.1f}", f"{z['t_min']:.1f}"]
            if has_surface:
                row.append("n/a" if z["t_max_surface"] is None else f"{z['t_max_surface']:.1f}")
            zrows.append(row)
        _fill(self.zone_table, zrows)
        if has_surface:
            for r, z in enumerate(zones):
                outer = z["layer"] in (1, sim.problem.board.layers)       # No value on an outer face: the model reads none there (the Analytic over absent copper); an inner layer has no face
                self.zone_table.item(r, 5).setToolTip(("No surface value under this zone." if outer else "Inner copper layer: no outer face, the surface is the column.") if z["t_max_surface"] is None else
                                                      f"Surface ({z['surface_kind']}) of the outer face under the zone: mean {z['t_mean_surface']:.3f} °C, max {z['t_max_surface']:.3f} °C. " + tips.SURFACE_TRAP_TIP)
        blocks_ = analysis.block_stats(ref, sim.problem)
        self.block_table.setVisible(bool(blocks_))
        _fill(self.block_table, [[k["name"], k["face"], f"{k['t_mean']:.1f}", f"{k['t_max']:.1f}", f"{k['w_to_block']:.2f}",
                                  f"{k['w_to_air']:.2f}"] for k in blocks_])
        hs = analysis.hotspots(ref, sim.options.hotspot_c)[:50]
        has_point = "T_point" in ref.arrays
        hheads = (["Hotspot", "Layer", "Tmax °C\n(column)", "x mm", "y mm", "Area mm²"] + (["Tmax °C\n(surface)"] if has_surface else []) + (["Node °C\n(point)"] if has_point else []))
        self.hot_table.setColumnCount(len(hheads))
        self.hot_table.setHorizontalHeaderLabels(hheads)
        self.hot_table.horizontalHeaderItem(2).setToolTip(tips.COLUMN_TABLE_TIP)
        c = 6
        if has_surface:
            self.hot_table.horizontalHeaderItem(c).setToolTip("The hottest surface read-out (outer face of the copper) of the SAME hot area, °C; n/a for a hotspot on an "
                                                              "inner layer. " + tips.SURFACE_MAX_TIP)
            c += 1
        if has_point:
            self.hot_table.horizontalHeaderItem(c).setToolTip("Point read-out (FEM): the hottest mesh node of the hot area, °C, on the outer face; a node value, not a cell mean. "
                                                              "n/a on an inner layer.")
        hrows = []
        for k, h in enumerate(hs):
            row = [f"#{k + 1}", str(h["layer"]), f"{h['t_max']:.1f}", f"{h['x_mm']:.1f}", f"{h['y_mm']:.1f}", f"{h['area_mm2']:.1f}"]
            if has_surface:
                row.append("n/a" if h["t_surface"] is None else f"{h['t_surface']:.1f}")
            if has_point:
                row.append("n/a" if h["t_point"] is None else f"{h['t_point']:.1f}")
            hrows.append(row)
        _fill(self.hot_table, hrows or [["none above limit"] + [""] * (len(hheads) - 1)])

    def _draw_components(self):
        """!
        @brief Bar chart of heater temperatures (and junctions) of the reference model.
        """
        if self.sim is None or self.sim.reference.T is None:
            return
        heaters = self.sim.heater_rows()
        with _mpl_theme(self.theme):
            if heaters:
                # The bars are the column read-out, like the table (the surface is the last column of the table and its tooltip)
                series = {"mean under footprint (column)": [h["t_mean"] for h in heaters],
                          "max under footprint (column)": [h["t_max"] for h in heaters]}
                if any(h["t_junction"] is not None for h in heaters):
                    series["junction"] = [float("nan") if h["t_junction"] is None else h["t_junction"] for h in heaters]
                plots.draw_bars(self.comp_fig, [h["name"] for h in heaters], series, title=f"Heater temperatures (column mean)\nReference model: {model_label(self.sim.reference.model)}")
            else:
                self.comp_fig.clear()
        _paint_figure(self.comp_fig, self.theme)
        self.comp_canvas.draw_idle()
