"""!
@file animation.py
@brief Animation tab: compute the power-step transient and play the evolution of the temperature field.

The frames come from the implicit time stepping of the same matrices as the steady solution
(`fvm.solve_transient`), so the time axis is real time in seconds.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QSlider,
                               QSpinBox, QVBoxLayout, QWidget)

from .. import analytic, fdm, fvm, plots
from .results_view import _mpl_theme, _paint_figure


class AnimationTab(QWidget):
    """!
    @brief Controls, canvas and playback of the heat evolution.
    """

    compute_requested = Signal(dict)

    def __init__(self, theme="dark", parent=None):
        """!
        @param theme Colour theme name.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.theme, self.tr, self.problem = theme, None, None
        self._frame, self._updating = 0, False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)

        self.t_end = QDoubleSpinBox()
        self.t_end.setRange(0.1, 1e6)
        self.t_end.setDecimals(1)
        self.t_end.setValue(300.0)
        self.t_end.setSuffix(" s")
        self.frames = QSpinBox()
        self.frames.setRange(10, 400)
        self.frames.setValue(60)
        self.model = QComboBox()
        self.model.addItem("Finite volume (FVM)", "fvm")
        self.model.addItem("Finite difference (FDM)", "fdm")
        self.model.addItem("Analytical (Fourier series)", "analytic")
        self.model.setToolTip("The analytical model gives the response instantly (vias and heatsinks are calibrated per heater); the FDM uses the same time stepping as the FVM on grid points.")
        self.scheme = QComboBox()
        self.scheme.addItem("Implicit Euler (robust)", 1.0)
        self.scheme.addItem("Crank-Nicolson (accurate)", 0.5)
        self.spacing = QComboBox()
        self.spacing.addItem("Logarithmic time", True)
        self.spacing.addItem("Linear time", False)
        self.t_end.setToolTip("Length of the animated power step in seconds (preset to a few time constants of the board).")
        self.frames.setToolTip("Number of frames computed for the animation.")
        self.scheme.setToolTip("Time stepping: implicit Euler is robust, Crank-Nicolson is more accurate.")
        self.spacing.setToolTip("Spacing of the frames in time: logarithmic shows the early heating in detail, linear spaces them evenly.")
        self.compute = QPushButton("Compute")
        self.compute.setToolTip("Compute the response to the heater power switched on at t = 0 (runs in the background; Ctrl+. cancels it).")
        self.compute.setObjectName("primary")
        self.compute.clicked.connect(self._request)
        self.status = QLabel("Set the duration and compute the response to the heater power switched on at t = 0.")
        self.status.setWordWrap(True)

        self.layer = QComboBox()
        self.cmap = QComboBox()
        self.cmap.addItems(plots.CMAPS)
        self.play = QPushButton("Play")
        self.play.setCheckable(True)
        self.play.toggled.connect(self._toggle_play)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self._show_frame)
        self.fps = QSpinBox()
        self.fps.setRange(1, 60)
        self.fps.setValue(12)
        self.fps.setSuffix(" fps")
        self.layer.setToolTip("Copper layer shown in the animation.")
        self.cmap.setToolTip("Colour scale of the animation.")
        self.slider.setToolTip("Drag to go to a moment of the response.")
        self.fps.setToolTip("Playback speed in frames per second.")
        self.play.setToolTip("Play or pause the animation.")
        self.export = QPushButton("Export GIF…")
        self.export.setToolTip("Save the animation as a GIF file.")
        self.export.clicked.connect(self._export_gif)

        # Two rows (what is computed, then how): in one row the settings made the Results tab about 1040 px wide, which the
        # main window took from its side docks
        top = QHBoxLayout()
        for lbl, w in (("Model", self.model), ("Duration", self.t_end), ("Frames", self.frames)):
            top.addWidget(QLabel(lbl))
            top.addWidget(w)
        top.addStretch(1)
        how = QHBoxLayout()
        for lbl, w in (("Scheme", self.scheme), ("Spacing", self.spacing)):
            how.addWidget(QLabel(lbl))
            how.addWidget(w)
        how.addWidget(self.compute)
        how.addStretch(1)
        play = QHBoxLayout()
        for w in (self.play, self.slider):
            play.addWidget(w, 1 if w is self.slider else 0)
        for lbl, w in (("Layer", self.layer), ("Colours", self.cmap), ("Speed", self.fps)):
            play.addWidget(QLabel(lbl))
            play.addWidget(w)
        play.addWidget(self.export)

        self.fig = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.fig)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addLayout(top)
        lay.addLayout(how)
        lay.addWidget(self.status)
        lay.addWidget(self.canvas, 1)
        lay.addLayout(play)
        self._set_enabled(False)
        self.layer.currentIndexChanged.connect(self._redraw)
        self.cmap.currentIndexChanged.connect(self._redraw)
        self.fps.valueChanged.connect(lambda v: self.timer.setInterval(int(1000 / v)))

    def _set_enabled(self, on):
        """!
        @brief Enable the playback controls only when a transient result exists.
        @param on True when a result is available.
        """
        for w in (self.play, self.slider, self.layer, self.cmap, self.fps, self.export):
            w.setEnabled(on)

    def set_theme(self, theme):
        """!
        @brief Change the plot theme.
        @param theme "dark" or "light".
        """
        self.theme = theme
        self._redraw()

    def suggest_duration(self, seconds):
        """!
        @brief Put a sensible default duration (a few time constants) into the control.
        @param seconds Duration in seconds.
        """
        self.t_end.setValue(float(round(seconds, 1)))

    def _request(self):
        """!
        @brief Ask the main window to compute the transient with the current controls.
        """
        self.compute.setEnabled(False)
        self.status.setText("Computing…")
        self.compute_requested.emit({"t_end": self.t_end.value(), "n_out": self.frames.value(),
                                     "theta_scheme": self.scheme.currentData(), "model": self.model.currentData(),
                                     "log_times": self.spacing.currentData()})

    def computing_failed(self, message):
        """!
        @brief Show a failure and re-enable the button.
        @param message Error text.
        """
        self.compute.setEnabled(True)
        self.status.setText(f"Failed: {message}")

    def set_result(self, tr, problem):
        """!
        @brief Show a computed transient and start at the last frame.
        @param tr TransientResult.
        @param problem The Problem it belongs to.
        """
        self.timer.stop()
        self.play.setChecked(False)
        self.tr, self.problem = tr, problem
        self._updating = True
        self.layer.clear()
        for l in range(problem.board.layers):
            self.layer.addItem(f"Layer {l + 1}", l)
        self.slider.setRange(0, len(tr.times) - 1)
        self._updating = False
        self.compute.setEnabled(True)
        self._set_enabled(True)
        tau = tr.time_constant()
        self.status.setText(f"Steady Tmax {tr.steady_t_max:.1f} °C; the hottest point reaches 63 % at "
                            f"{tau:.1f} s. {len(tr.times) - 1} frames up to {tr.times[-1]:.0f} s.")
        self._frame = len(tr.times) - 1
        self.slider.setValue(self._frame)
        self._redraw()

    def _redraw(self, *_):
        """!
        @brief Draw the current frame with a colour scale fixed over the whole animation.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating or self.tr is None:
            return
        tr, l = self.tr, max(self.layer.currentData() or 0, 0)
        dx, dy = plots.frame_spacing(tr, self.problem)
        k = self.slider.value()
        with _mpl_theme(self.theme):
            plots.draw_field(self.fig, tr.frames[k, l], self.problem, dx, dy, cmap=self.cmap.currentText(),
                             vmin=tr.ambient, vmax=float(tr.frames[:, l].max()), layer=l,
                             title=f"Layer {l + 1}   t = {tr.times[k]:.2f} s   Tmax = {tr.t_max[k]:.1f} °C")
        _paint_figure(self.fig, self.theme)
        self.canvas.draw_idle()

    def _show_frame(self, k):
        """!
        @brief Slider moved.
        @param k Frame index.
        """
        self._frame = k
        self._redraw()

    def _toggle_play(self, on):
        """!
        @brief Start or stop the playback.
        @param on True to play.
        """
        self.play.setText("Pause" if on else "Play")
        if on and self.tr is not None:
            if self.slider.value() >= self.slider.maximum():
                self.slider.setValue(0)
            self.timer.start(int(1000 / self.fps.value()))
        else:
            self.timer.stop()

    def _advance(self):
        """!
        @brief Timer tick: next frame, stop at the end.
        """
        if self.slider.value() >= self.slider.maximum():
            self.play.setChecked(False)
        else:
            self.slider.setValue(self.slider.value() + 1)

    def _export_gif(self):
        """!
        @brief Save the animation of the chosen layer as a GIF.
        """
        if self.tr is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export animation", "heat_evolution.gif", "GIF (*.gif)")
        if path:
            plots.save_transient_gif(self.tr, self.problem, path, layer=max(self.layer.currentData() or 0, 0),
                                     fps=self.fps.value(), cmap=self.cmap.currentText())
            self.status.setText(f"Saved {path}")
