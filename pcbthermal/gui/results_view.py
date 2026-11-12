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
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QPlainTextEdit, QSlider, QSpinBox, QSplitter, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .. import analysis, plots
from . import theme as th
from . import tips
from .toolbar_icons import ThemedToolbar
from .display import DisplayState
from .flow import FlowLayout
from ..numfmt import num


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


def _table(headers):
    """!
    @brief Create a read-only table with the given column headers.
    @param headers List of column titles.
    @return QTableWidget.
    """
    t = QTableWidget(0, len(headers))
    t.setToolTip("Values of the reference model; hover a column title for its meaning.")
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
    table.setFixedHeight(h)


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


class PlotTab(QWidget):
    """!
    @brief A matplotlib canvas with the controls of one kind of plot.
    @details How the map is drawn (underlay, opacity, View, contour step, colour map) is not a control of the tab: it is the shared `DisplayState`, edited in the
             Display popover of the main toolbar, so the temperature and gradient maps, the Animation and the board can never disagree. The tab keeps Model, Layer,
             Hotspot and the colour limits.
    """

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
        self.canvas = FigureCanvasQTAgg(self.fig)
        _paint_figure(self.fig, self.theme)             # An empty figure would be white on the dark theme
        self.toolbar = ThemedToolbar(self.canvas, self, self.theme)
        recolour_toolbar(self.toolbar, self.theme)

        self.model = QComboBox()
        self.layer_value = 0                            # The layer of the toolbar choice (see layerchoice): -1 / -2 all layers, 100 + face a metal block
        self.hot = QCheckBox("Hotspot contour")
        self.hot.setChecked(True)
        self.equiv = QCheckBox("Equiv. rect.")
        self.equiv.setChecked(True)
        self.equiv.setVisible(False)                    # Shown only for a Lumped or Analytic result of a board with an outline
        self.auto = QCheckBox("Auto range")
        self.auto.setChecked(True)
        self.vmin, self.vmax = QDoubleSpinBox(), QDoubleSpinBox()
        for s in (self.vmin, self.vmax):
            s.setRange(-100, 2000)
            s.setDecimals(1)
            s.setKeyboardTracking(False)
        self.axis = QComboBox()
        self.axis.addItem("Along x", "x")
        self.axis.addItem("Along y", "y")
        self.pos = QSlider(Qt.Horizontal)
        self.pos.setRange(0, 1000)
        self.pos_label = QLabel()
        self.model.setToolTip("Model whose result is drawn.")
        self.equiv.setToolTip("Lumped and Analytic solve an outline board as a rectangle of the same area. Ticked: that rectangle as solved (dashed). "
                              "Unticked: the field stretched back onto the box (parts look larger).")
        self.vmin.setToolTip("Lowest temperature of the colour scale, °C (Auto range off).")
        self.vmax.setToolTip("Highest temperature of the colour scale, °C (Auto range off).")
        self.axis.setToolTip("Direction of the line the temperature is plotted along.")
        self.pos.setToolTip("Position of the cut: drag to move it.")

        # The temperature and gradient rows wrap (Auto range, min and max go to a second line in a narrow centre area); the profile row has a stretching slider
        controls = FlowLayout() if kind in ("temperature", "gradient") else QHBoxLayout()
        if kind in ("temperature", "gradient"):
            controls.addWidget(QLabel("Model"))                # The layer is the one choice of the main toolbar
            controls.addWidget(self.model)
            controls.addWidget(self.equiv)
            if kind == "temperature":
                controls.addWidget(self.hot)
                controls.addWidget(self.auto)
                controls.addWidget(self.vmin)
                controls.addWidget(self.vmax)
        elif kind == "profile":
            controls.addWidget(QLabel("Cut"))
            controls.addWidget(self.axis)
            controls.addWidget(self.pos, 1)
            controls.addWidget(self.pos_label)
        if kind not in ("temperature", "gradient"):
            controls.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addLayout(controls)
        lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas, 1)

        for w in (self.model, self.axis):
            w.currentIndexChanged.connect(self.redraw)
        if kind in ("temperature", "gradient"):
            self.display.changed.connect(lambda _what: self.redraw())     # A change of the shared display choice draws the map again
        for w in (self.hot, self.auto, self.equiv):
            w.toggled.connect(self.redraw)
        for w in (self.vmin, self.vmax):
            w.valueChanged.connect(self.redraw)
        self.pos.valueChanged.connect(self.redraw)

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
        self.display.clear_cache()                      # The copper pictures belong to the problem of the simulation
        self._updating = True
        have = [k for k, r in sim.results.items() if r.T is not None]
        self.model.clear()
        for k in have:
            self.model.addItem(tips.model_label(k), k)        # The name of the Simulation panel, the key as data
        self.model.setCurrentIndex(max(self.model.findData("fvm"), 0))
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
        with _mpl_theme(self.theme):
            if self.kind == "temperature" and self._result() is not None:
                r = self._result()
                layer = self.layer_value
                cmap = self.display.cmap
                if layer in (-1, -2):
                    plots.draw_fields(self.fig, r, prob, cmap=cmap, show_equivalent=self.equiv.isChecked(), equivalent_color=eq_args["equivalent_color"],
                                      view=view, grid=layer == -2)
                elif layer >= 100:
                    plots.draw_block(self.fig, r, prob, layer - 100, cmap=cmap)
                else:
                    layer = self._layer_index()
                    vmin = None if self.auto.isChecked() else self.vmin.value()
                    vmax = None if self.auto.isChecked() else self.vmax.value()
                    plots.draw_field(self.fig, r.T[layer], prob, r.dx, r.dy, cmap=cmap, vmin=vmin, vmax=vmax,
                                     layer=layer, extremes=True, marker=self._model_hot_point(r, layer),
                                     hotspot=sim.options.hotspot_c if self.hot.isChecked() else None, **eq_args,
                                     title=f"{r.model.upper()} - layer {layer + 1}   "
                                           f"Tmax {r.t_max:.1f} °C   Tmin {r.t_min:.1f} °C   Tmean {r.t_mean:.1f} °C", view=view)
            elif self.kind == "gradient" and self._result() is not None:
                r = self._result()
                layer = self._layer_index()
                g = analysis.gradient_magnitude(r)[layer]
                plots.draw_field(self.fig, g, prob, r.dx, r.dy, cmap=self.display.cmap, layer=layer,
                                 label="|∇T| (K/mm)", **eq_args, view=view,
                                 title=f"{r.model.upper()} - layer {layer + 1}   max gradient {g.max():.2f} K/mm")
            elif self.kind == "profile":
                axis = self.axis.currentData()
                b = prob.board
                length = (b.height if axis == "x" else b.width) * 1000.0
                pos = self.pos.value() / 1000.0 * length
                self.pos_label.setText(f"{'y' if axis == 'x' else 'x'} = {pos:.1f} mm")
                res = {k: r for k, r in sim.results.items() if r.T is not None}
                plots.draw_profile(self.fig, res, prob, layer=self._layer_index(),
                                   axis=axis, position_mm=pos)
            elif self.kind == "compare":
                plots.draw_comparison(self.fig, sim.results)
        _paint_figure(self.fig, self.theme)
        self.canvas.draw_idle()


class ResultsView(QWidget):
    """!
    @brief The whole results area.
    """

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
        self.model_table = _table(["Model", "Tmax °C", "Tmean °C", "ΔT °C", "Rθ K/W", "Power W",
                                   "Balance", "Error vs ref", "Time s"])
        _fit_height(self.model_table)                        # The height follows the rows (no scroll bar below 12 rows), see _fit_height
        # The model names of the Simulation panel ("Lumped (LPTN)") were cut to "Lumped ..." in a column of the same width as the numbers
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.warnings = QLabel()
        self.warnings.setWordWrap(True)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        # An empty Results tab said nothing: it now tells a first-time user what to do
        self.report.setPlaceholderText("No results yet. Draw at least one heater with a power above zero on the Board tab and press Run simulation (F5): "
                                       "the table above compares the models and the report of the run appears here.")
        self.report.setStyleSheet("font-family: Menlo, Consolas, monospace;")
        sl.addWidget(self.model_table)
        sl.addWidget(self.warnings)
        sl.addWidget(self.report, 1)
        self.tabs.addTab(summary, "Summary")

        self.temp = PlotTab("temperature", theme, display=self.display)
        self.grad = PlotTab("gradient", theme, display=self.display)
        self.profile = PlotTab("profile", theme, display=self.display)
        self.compare = PlotTab("compare", theme, display=self.display)
        self.tabs.addTab(self.temp, "Temperature")
        self.tabs.addTab(self.grad, "Gradients")
        self.tabs.addTab(self.profile, "Profiles")

        # Components: heater and zone statistics plus a bar chart
        comp = QWidget()
        cl = QVBoxLayout(comp)
        split = QSplitter(Qt.Vertical)
        tables = QWidget()
        tl = QVBoxLayout(tables)
        self.heater_table = _table(["Heater", "Layer", "Power W", "Mean °C", "Max °C", "Junction °C", "Margin K", "Power limit W", "Top path W"])
        self.zone_table = _table(["Zone", "Layer", "Mean °C", "Max °C", "Min °C"])
        self.hot_table = _table(["Hotspot", "Layer", "Tmax °C", "x mm", "y mm", "Area mm²"])
        self.block_table = _table(["Metal block", "Face", "Mean °C", "Max °C", "Heat in W", "Heat to air W"])
        self.block_table.setMaximumHeight(90)
        for t in (self.heater_table, self.zone_table, self.hot_table, self.block_table):
            tl.addWidget(t)
        split.addWidget(tables)
        self.comp_fig = Figure(layout="constrained")
        self.comp_canvas = FigureCanvasQTAgg(self.comp_fig)
        split.addWidget(self.comp_canvas)
        split.setSizes([360, 260])
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
        self._anim_warns = [str(w) for w in warns]
        if getattr(self, "sim", None) is not None:
            self._show_warnings(self.sim.warnings)
            self.warnings.setVisible(True)

    def _show_warnings(self, warns):
        """!
        @brief Write the notes of the run under the models table, text and symbol in the same theme token.
        @param warns List of warning strings.
        """
        warns = list(warns) + [w for w in self._anim_warns if w not in warns]
        tone = th.colors(self.theme)["alert_note"]
        self.warnings.setTextFormat(Qt.RichText)
        # Two line breaks = one blank line between warnings, so that a long list is easy to read
        self.warnings.setText("<br><br>".join(f"<span style='color:{tone}'>⚠ {html.escape(str(w))}</span>" for w in warns))

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

    def set_simulation(self, sim):
        """!
        @brief Display a finished simulation.
        @param sim Simulation.
        """
        self.sim = sim
        rows = [[tips.model_label(r["model"]), f"{r['t_max_c']:.2f}", f"{r['t_mean_c']:.2f}", f"{r['delta_t_k']:.2f}",
                 f"{r['r_theta_k_per_w']:.3f}", f"{r['power_in_w']:.3f}", f"{num(r['energy_balance'], sign=True)}",
                 "reference" if r["model"] == sim.reference.model else f"{r['error_vs_reference'] * 100:+.1f} %",
                 f"{r['seconds']:.2f}"] for r in sim.table()]
        _fill(self.model_table, rows)
        _fit_height(self.model_table)
        self._anim_warns = []                                   # A new run: the notes of the old animation are gone
        warns = sim.warnings
        self._show_warnings(warns)
        self.warnings.setVisible(bool(warns))
        self.report.setPlainText(sim.report())
        for t in (self.temp, self.grad, self.profile, self.compare):
            t.set_simulation(sim)
        self._fill_components()
        self._draw_components()
        self.time_sim.set_simulation(sim)
        if sim.decisions:
            self.tabs.setCurrentWidget(self.time_sim if sim.profile_results else self.tabs.widget(0))

    def _fill_components(self):
        """!
        @brief Fill the heater, zone and hotspot tables from the reference model.
        """
        sim, ref = self.sim, self.sim.reference
        if ref.T is None:
            return
        heaters = sim.heater_rows()
        _fill(self.heater_table, [[h["name"], str(h["layer"]), f"{h['power_w']:.2f}", f"{h['t_mean']:.1f}",
                                   f"{h['t_max']:.1f}",
                                   f"{h['t_junction']:.1f}" if h["t_junction"] is not None else "-",
                                   f"{h['margin_k']:.1f}" if h["margin_k"] is not None else "-",
                                   f"{h['p_limit_w']:.2f}" if h["p_limit_w"] is not None else "-",
                                   f"{h['power_top_w']:.2f}" if h["power_top_w"] > 0 else "-"]
                                  for h in heaters])
        zones = analysis.zone_stats(ref, sim.problem)
        _fill(self.zone_table, [[z["name"], str(z["layer"]), f"{z['t_mean']:.1f}", f"{z['t_max']:.1f}",
                                 f"{z['t_min']:.1f}"] for z in zones])
        blocks_ = analysis.block_stats(ref, sim.problem)
        self.block_table.setVisible(bool(blocks_))
        _fill(self.block_table, [[k["name"], k["face"], f"{k['t_mean']:.1f}", f"{k['t_max']:.1f}", f"{k['w_to_block']:.2f}",
                                  f"{k['w_to_air']:.2f}"] for k in blocks_])
        hs = analysis.hotspots(ref, sim.options.hotspot_c)
        _fill(self.hot_table, [[f"#{k + 1}", str(h["layer"]), f"{h['t_max']:.1f}", f"{h['x_mm']:.1f}",
                                f"{h['y_mm']:.1f}", f"{h['area_mm2']:.1f}"] for k, h in enumerate(hs[:50])]
              or [["none above limit", "", "", "", "", ""]])

    def _draw_components(self):
        """!
        @brief Bar chart of heater temperatures (and junctions) of the reference model.
        """
        if self.sim is None or self.sim.reference.T is None:
            return
        heaters = self.sim.heater_rows()
        with _mpl_theme(self.theme):
            if heaters:
                series = {"mean under footprint": [h["t_mean"] for h in heaters],
                          "max under footprint": [h["t_max"] for h in heaters]}
                if any(h["t_junction"] is not None for h in heaters):
                    series["junction"] = [float("nan") if h["t_junction"] is None else h["t_junction"] for h in heaters]
                plots.draw_bars(self.comp_fig, [h["name"] for h in heaters], series, title="Heater temperatures")
            else:
                self.comp_fig.clear()
        _paint_figure(self.comp_fig, self.theme)
        self.comp_canvas.draw_idle()
