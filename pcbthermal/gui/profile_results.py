#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file profile_results.py
@brief Results of the time simulation with power profiles: temperature versus time, peak map and the last window as frames.
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from .. import plots
from .results_view import _mpl_theme, _paint_figure, redraw_pending, redraw_when_shown
from . import tips
from ..numfmt import num


class ProfileResultsTab(QWidget):
    """!
    @brief Plots of a power-profile time simulation, one model at a time.
    """

    def __init__(self, theme="dark", parent=None):
        """!
        @param theme Colour theme name.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.theme, self.sim, self._updating = theme, None, False
        self.model = QComboBox()
        self.view = QComboBox()
        self.view.addItem("Temperature versus time", "series")
        self.view.addItem("Peak temperature map", "peak")
        self.view.addItem("Last window, frame by frame", "frames")
        self.layer_value = 0                            # The layer of the toolbar choice (a single layer here)
        self.slider = QSlider(Qt.Horizontal)
        self.model.setToolTip("Model whose time simulation is shown.")
        self.view.setToolTip("Temperature against time, the peak map, or the last window frame by frame.")
        self.slider.setToolTip("Drag to a moment of the simulation.")
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.fig = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.fig)
        _paint_figure(self.fig, self.theme)             # An empty figure would be white on the dark theme
        bar = QHBoxLayout()
        for text, w in (("Model", self.model), ("Show", self.view)):
            bar.addWidget(QLabel(text))
            bar.addWidget(w)
        bar.addStretch(1)
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.info)
        lay.addWidget(self.canvas, 1)
        lay.addWidget(self.slider)
        for w in (self.model, self.view):
            w.currentIndexChanged.connect(self.redraw)
        self.slider.valueChanged.connect(self.redraw)
        self.redraw()

    def set_theme(self, theme):
        """!
        @brief Change the plot theme.
        @param theme "dark" or "light".
        """
        self.theme = theme
        _paint_figure(self.fig, theme)                  # Also when nothing is drawn yet
        self.canvas.draw_idle()
        self.redraw()

    def set_simulation(self, sim):
        """!
        @brief Show the time simulations of a finished Simulation.
        @param sim Simulation (may have no profile results).
        """
        self.sim = sim
        self._updating = True
        self.model.clear()
        for name, r in sim.profile_results.items():
            if r.resolved:
                self.model.addItem(tips.model_label(name), name)
        self._updating = False
        self.redraw()

    def set_layer(self, value):
        """!
        @brief Show the layer chosen in the toolbar.
        @param value Layer index (0-based).
        """
        value = max(int(value), 0)
        if value != self.layer_value:
            self.layer_value = value
            redraw_when_shown(self, self.redraw)           # A hidden tab is drawn when it is shown (the layer box moves every map at once)

    def showEvent(self, e):
        """!
        @brief Draw the view that a layer change left pending while the tab was hidden.
        @param e QShowEvent.
        """
        super().showEvent(e)
        redraw_pending(self, self.redraw)

    def _result(self):
        """!
        @brief The result of the chosen model.
        @return ProfileResult or None.
        """
        if self.sim is None or self.model.currentData() is None:
            return None
        return self.sim.profile_results.get(self.model.currentData())

    def redraw(self, *_):
        """!
        @brief Draw the chosen view.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating:
            return
        r = self._result()
        self.fig.clear()
        frames = self.view.currentData() == "frames"
        self.slider.setVisible(frames and r is not None)
        if r is None:
            msg = "No time simulation yet."
            if self.sim is not None:
                msg = self.sim.profile_error or ("Every heater was replaced by its average power: no time simulation was needed."
                                                 if self.sim.decisions else "No heater has a power profile.")
            with _mpl_theme(self.theme):                  # The message took the default (black) text colour on the dark theme
                self.fig.add_subplot(111).text(0.5, 0.5, msg, ha="center", va="center", wrap=True)
            self.info.setText("")
        else:
            layer = min(max(self.layer_value, 0), self.sim.problem.board.layers - 1)
            with _mpl_theme(self.theme):
                if self.view.currentData() == "series":
                    plots.draw_profile_series(self.fig, r, self.sim.problem, self.sim.options.hotspot_c)
                elif self.view.currentData() == "peak":
                    plots.draw_peak_map(self.fig, r, self.sim.problem, layer)
                else:
                    self.slider.setRange(0, len(r.frames) - 1)
                    k = min(self.slider.value(), len(r.frames) - 1)
                    plots.draw_field(self.fig, r.frames[k][layer], self.sim.problem, r.dx, r.dy, layer=layer,
                                     title=f"{r.model.upper()} - layer {layer + 1} at t = {num(r.frame_times[k], 4)} s",
                                     label="Temperature (°C)")
            self.info.setText(f"Peak {r.peak:.1f} °C, minimum {r.minimum:.1f} °C, oscillation {r.oscillation:.1f} °C; "
                              f"{r.windows} windows of {num(r.window)} s, {r.steps} steps of {num(r.dt, 3)} s, "
                              f"{'the cycle repeats' if r.converged else 'the cycle did not settle'}; "
                              f"steady (hottest at the face of a part) with the average power {r.steady_average_max:.1f} °C, with the peak power "
                              f"{r.steady_peak_max:.1f} °C."
                              + (" Heaters with a ripple ("
                                 + ", ".join(f"{x['name']} {num(x['swing_c'], 3)} K" for x in r.ripple)
                                 + ") are held at their average power in the board run; their wave is added at the heater (curve, peak and minimum), not in the maps."
                                 if r.ripple else ""))
        _paint_figure(self.fig, self.theme)
        self.canvas.draw_idle()
