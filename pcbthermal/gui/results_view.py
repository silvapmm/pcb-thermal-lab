"""!
@file results_view.py
@brief Results area: summary table, temperature maps, gradients, profiles and component statistics.
"""

import contextlib

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QPlainTextEdit, QSlider, QSplitter, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .. import analysis, plots
from . import theme as th


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


class PlotTab(QWidget):
    """!
    @brief A matplotlib canvas with the controls of one kind of plot.
    """

    def __init__(self, kind, theme="dark", parent=None):
        """!
        @param kind "temperature", "gradient", "profile" or "compare".
        @param theme Colour theme name.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.kind, self.theme, self.sim = kind, theme, None
        self._updating = False
        self.fig = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        self.model = QComboBox()
        self.layer = QComboBox()
        self.cmap = QComboBox()
        self.cmap.addItems(plots.CMAPS)
        self.hot = QCheckBox("Hotspot contour")
        self.hot.setChecked(True)
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

        controls = QHBoxLayout()
        if kind in ("temperature", "gradient"):
            for lbl, w in (("Model", self.model), ("Layer", self.layer), ("Colours", self.cmap)):
                controls.addWidget(QLabel(lbl))
                controls.addWidget(w)
            if kind == "temperature":
                controls.addWidget(self.hot)
                controls.addWidget(self.auto)
                controls.addWidget(self.vmin)
                controls.addWidget(self.vmax)
        elif kind == "profile":
            for lbl, w in (("Layer", self.layer), ("Cut", self.axis)):
                controls.addWidget(QLabel(lbl))
                controls.addWidget(w)
            controls.addWidget(self.pos, 1)
            controls.addWidget(self.pos_label)
        controls.addStretch(1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addLayout(controls)
        lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas, 1)

        for w in (self.model, self.layer, self.cmap, self.axis):
            w.currentIndexChanged.connect(self.redraw)
        for w in (self.hot, self.auto):
            w.toggled.connect(self.redraw)
        for w in (self.vmin, self.vmax):
            w.valueChanged.connect(self.redraw)
        self.pos.valueChanged.connect(self.redraw)

    def set_theme(self, theme):
        """!
        @brief Change the plot theme.
        @param theme "dark" or "light".
        """
        self.theme = theme
        self.redraw()

    def set_simulation(self, sim):
        """!
        @brief Show the results of a simulation.
        @param sim Simulation.
        """
        self.sim = sim
        self._updating = True
        have = [k for k, r in sim.results.items() if r.T is not None]
        self.model.clear()
        for k in have:
            self.model.addItem(k, k)
        self.model.setCurrentIndex(max(self.model.findData("fvm"), 0))
        n = sim.problem.board.layers
        self.layer.clear()
        if self.kind == "temperature":
            self.layer.addItem("All layers", -1)
        for l in range(n):
            self.layer.addItem(f"Layer {l + 1}", l)
        if self.kind == "temperature":
            # The metal blocks of the finite-volume and finite-difference models are views of their own (data 100 and 101)
            faces = sorted({f for r in sim.results.values() for f in (0, 1) if f"block_{'top' if f == 0 else 'bottom'}_max" in r.extras})
            for f in faces:
                self.layer.addItem(f"Metal block ({'top' if f == 0 else 'bottom'})", 100 + f)
        self.layer.setCurrentIndex(0 if self.kind != "temperature" else 1 if n > 1 else 0)
        ref = sim.reference
        if self.kind == "temperature":
            self.vmin.setValue(ref.ambient)
            self.vmax.setValue(round(ref.t_max + 0.5))
        if self.kind == "profile":
            self.pos.setValue(500)
        self._updating = False
        self.redraw()

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
        layer = max(self.layer.currentData() if self.layer.currentData() is not None else 0, 0)
        if layer >= 100:
            return None                                                # The overlay on the board shows the board layers only
        vmin = None if self.auto.isChecked() else self.vmin.value()
        vmax = None if self.auto.isChecked() else self.vmax.value()
        return r.T[layer], r.dx, r.dy, self.cmap.currentText(), vmin, vmax

    def redraw(self, *_):
        """!
        @brief Redraw the figure from the current controls.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating or self.sim is None:
            return
        sim, prob = self.sim, self.sim.problem
        self.vmin.setEnabled(not self.auto.isChecked())
        self.vmax.setEnabled(not self.auto.isChecked())
        with _mpl_theme(self.theme):
            if self.kind == "temperature" and self._result() is not None:
                r = self._result()
                layer = self.layer.currentData()
                cmap = self.cmap.currentText()
                if layer == -1:
                    plots.draw_fields(self.fig, r, prob, cmap=cmap)
                elif layer >= 100:
                    plots.draw_block(self.fig, r, prob, layer - 100, cmap=cmap)
                else:
                    vmin = None if self.auto.isChecked() else self.vmin.value()
                    vmax = None if self.auto.isChecked() else self.vmax.value()
                    loc = r.t_max_location
                    plots.draw_field(self.fig, r.T[layer], prob, r.dx, r.dy, cmap=cmap, vmin=vmin, vmax=vmax,
                                     layer=layer, marker=(loc[1], loc[2]) if loc and loc[0] == layer else None,
                                     hotspot=sim.options.hotspot_c if self.hot.isChecked() else None,
                                     title=f"{r.model.upper()} - layer {layer + 1}   "
                                           f"Tmax {r.t_max:.1f} °C   Tmean {r.t_mean:.1f} °C")
            elif self.kind == "gradient" and self._result() is not None:
                r = self._result()
                layer = max(self.layer.currentData(), 0)
                g = analysis.gradient_magnitude(r)[layer]
                plots.draw_field(self.fig, g, prob, r.dx, r.dy, cmap=self.cmap.currentText(), layer=layer,
                                 label="|∇T| (K/mm)",
                                 title=f"{r.model.upper()} - layer {layer + 1}   max gradient {g.max():.2f} K/mm")
            elif self.kind == "profile":
                axis = self.axis.currentData()
                b = prob.board
                length = (b.height if axis == "x" else b.width) * 1000.0
                pos = self.pos.value() / 1000.0 * length
                self.pos_label.setText(f"{'y' if axis == 'x' else 'x'} = {pos:.1f} mm")
                res = {k: r for k, r in sim.results.items() if r.T is not None}
                plots.draw_profile(self.fig, res, prob, layer=max(self.layer.currentData() or 0, 0),
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

    def __init__(self, theme="dark", parent=None):
        """!
        @param theme Colour theme name.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.theme, self.sim = theme, None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)

        # Summary: models table, warnings and the text report
        summary = QWidget()
        sl = QVBoxLayout(summary)
        self.model_table = _table(["Model", "Tmax °C", "Tmean °C", "ΔT °C", "Rθ K/W", "Power W",
                                   "Balance", "Error vs ref", "Time s"])
        self.model_table.setMaximumHeight(170)
        self.warnings = QLabel()
        self.warnings.setWordWrap(True)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setStyleSheet("font-family: Menlo, Consolas, monospace;")
        sl.addWidget(self.model_table)
        sl.addWidget(self.warnings)
        sl.addWidget(self.report, 1)
        self.tabs.addTab(summary, "Summary")

        self.temp = PlotTab("temperature", theme)
        self.grad = PlotTab("gradient", theme)
        self.profile = PlotTab("profile", theme)
        self.compare = PlotTab("compare", theme)
        self.tabs.addTab(self.temp, "Temperature")
        self.tabs.addTab(self.grad, "Gradients")
        self.tabs.addTab(self.profile, "Profiles")

        # Components: heater and zone statistics plus a bar chart
        comp = QWidget()
        cl = QVBoxLayout(comp)
        split = QSplitter(Qt.Vertical)
        tables = QWidget()
        tl = QVBoxLayout(tables)
        self.heater_table = _table(["Heater", "Layer", "Power W", "Mean °C", "Max °C", "Junction °C", "Margin K", "Power limit W"])
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
        self.animation = AnimationTab(theme)
        self.tabs.addTab(self.animation, "Animation")
        from .profile_results import ProfileResultsTab
        self.time_sim = ProfileResultsTab(theme)
        self.tabs.addTab(self.time_sim, "Power profile")

    def set_theme(self, theme):
        """!
        @brief Change the theme of all plots.
        @param theme "dark" or "light".
        """
        self.theme = theme
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
        rows = [[r["model"], f"{r['t_max_c']:.2f}", f"{r['t_mean_c']:.2f}", f"{r['delta_t_k']:.2f}",
                 f"{r['r_theta_k_per_w']:.3f}", f"{r['power_in_w']:.3f}", f"{r['energy_balance']:+.0e}",
                 "reference" if r["model"] == sim.reference.model else f"{r['error_vs_reference'] * 100:+.1f} %",
                 f"{r['seconds']:.2f}"] for r in sim.table()]
        _fill(self.model_table, rows)
        warns = sim.warnings
        self.warnings.setText("<br>".join(f"⚠ {w}" for w in warns))
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
                                   f"{h['p_limit_w']:.2f}" if h["p_limit_w"] is not None else "-"]
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
