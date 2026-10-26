"""!
@file profile_page.py
@brief The Power profile page: edit a square-wave power per heater, see the average-or-resolve decision, set the time run.
"""

import math

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .. import plots, profiles
from ..api import TIME_MODELS, step_response
from ..model import SquareWave
from ..profile_io import ProfileFileError, read_profile_csv, write_profile_csv
from . import compute
from .compute import ProcessWorker
from .panels import compact_combos
from .results_view import _mpl_theme, _paint_figure
from ..numfmt import num

_PERIOD_UNITS = {"µs": 1e-6, "ms": 1e-3, "s": 1.0, "min": 60.0, "h": 3600.0}
_FREQUENCY_UNITS = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6}


class ProfilePage(QWidget):
    """!
    @brief Editor of the power profile of every heater, with the regime decision and the run settings.
    """

    def __init__(self, doc, theme="dark", parent=None):
        """!
        @param doc The Document.
        @param theme Colour theme name.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.doc, self.theme, self._updating = doc, theme, False
        self.current = -1
        self.decisions, self.worker = [], None

        # ---- left: heater list
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Heater", "Profile", "Average", "Regime"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setToolTip("Heaters with their power profile, the average power and the regime chosen for each (averaged or resolved in time). Click one to edit it.")
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_row)

        # ---- editor of the selected heater
        self.kind = QComboBox()
        self.kind.addItem("Constant", "constant")
        self.kind.addItem("Square wave", "square")
        self.kind.addItem("Table (CSV file)", "table")
        self.const_power = QDoubleSpinBox()
        self._spin(self.const_power, 0, 10000, 3, " W")
        self.by = QComboBox()
        self.by.addItem("Period", "period")
        self.by.addItem("Frequency", "frequency")
        self.value = QDoubleSpinBox()
        self._spin(self.value, 1e-6, 1e9, 6, "")
        self.unit = QComboBox()
        self.duty = QDoubleSpinBox()
        self._spin(self.duty, 0.01, 100, 2, " %")
        self.p_on = QDoubleSpinBox()
        self._spin(self.p_on, 0, 100000, 4, " W")
        self.p_off = QDoubleSpinBox()
        self._spin(self.p_off, 0, 100000, 4, " W")
        self.avg_mode = QCheckBox("Type the average power")      # Short label; the tooltip says it replaces the power while on
        self.avg = QDoubleSpinBox()
        self._spin(self.avg, 0, 100000, 4, " W")
        self.repeat = QCheckBox("Repeat the table")             # Short label: the long one set the width of the page; the rest is in the tooltip
        self.import_btn = QPushButton("Import CSV…")
        self.import_btn.setToolTip("Read a power profile (time_s,power_w) from a CSV file; see examples/csv_profiles/")
        self.export_btn = QPushButton("Export CSV…")
        self.export_btn.setToolTip("Write the profile of this heater to a CSV file (a square wave is written as a table)")
        self.import_btn.clicked.connect(lambda: self.import_csv())
        self.export_btn.clicked.connect(lambda: self.export_csv())
        self.repeat.toggled.connect(self._apply_repeat)
        self.derived = QLabel()
        self.derived.setWordWrap(True)
        self.error = QLabel()
        self.error.setStyleSheet("color: #e5534b;")
        self.editor = QGroupBox("Power profile of the selected heater")
        form = QFormLayout(self.editor)
        form.addRow("Profile", self.kind)
        form.addRow("Power", self.const_power)
        row = QHBoxLayout()
        row.addWidget(self.by)
        row.addWidget(self.value, 1)
        row.addWidget(self.unit)
        self.wave_widgets = [self.by, self.value, self.unit, self.duty, self.p_on, self.p_off, self.avg_mode, self.avg]
        self.period_label = QLabel("Repeats every")
        form.addRow(self.period_label, row)
        form.addRow("Duty (time on)", self.duty)
        form.addRow("Power while on", self.p_on)
        form.addRow("Power while off", self.p_off)
        form.addRow("", self.avg_mode)
        form.addRow("Average power", self.avg)
        form.addRow("", self.repeat)
        files = QHBoxLayout()
        files.addWidget(self.import_btn)
        files.addWidget(self.export_btn)
        form.addRow("File", files)
        form.addRow(self.derived)
        form.addRow(self.error)
        for w in (self.value, self.duty, self.p_on, self.p_off, self.avg):
            w.valueChanged.connect(self._apply)
        self.const_power.valueChanged.connect(self._apply_constant)
        self.kind.currentIndexChanged.connect(self._apply_kind)
        self.by.currentIndexChanged.connect(self._on_by)
        self.unit.currentIndexChanged.connect(self._apply)
        self.avg_mode.toggled.connect(self._on_avg_mode)

        # ---- run settings
        self.run_box = QGroupBox("Time simulation")
        rf = QFormLayout(self.run_box)
        self.threshold = QDoubleSpinBox()
        self._spin(self.threshold, 0, 1000, 2, " °C")
        self.threshold.setToolTip("Oscillations (in total) smaller than this are ignored: the heater is replaced by its "
                                  "average power. Larger oscillations are simulated in time.")
        self.start = QComboBox()
        self.start.addItem("Steady state of the average power", "average")
        self.start.addItem("A temperature I choose", "temperature")
        self.start_c = QDoubleSpinBox()
        self._spin(self.start_c, -100, 1000, 1, " °C")
        self.duration = QComboBox()
        self.duration.addItem("Until the cycle repeats", "stable")
        self.duration.addItem("A number of cycles", "cycles")
        self.duration.addItem("A fixed time", "time")
        self.cycles = QSpinBox()
        self.cycles.setRange(1, 10000)
        self.time_s = QDoubleSpinBox()
        self._spin(self.time_s, 0.001, 1e7, 3, " s")
        self.max_steps = QSpinBox()
        self.max_steps.setRange(100, 10_000_000)
        self.max_steps.setSingleStep(50000)
        self.steady_mode = QComboBox()
        self.steady_mode.addItem("Average power", "average")
        self.steady_mode.addItem("Peak power (worst-case bound)", "peak")
        rf.addRow("Ignore oscillations below", self.threshold)
        rf.addRow("Start from", self.start)
        rf.addRow("Initial temperature", self.start_c)
        rf.addRow("Simulate", self.duration)
        rf.addRow("Cycles", self.cycles)
        rf.addRow("Time", self.time_s)
        rf.addRow("Step limit", self.max_steps)
        rf.addRow("Steady-state models use", self.steady_mode)
        self.analyze = QPushButton("Analyze regimes")
        self.analyze.setToolTip("Compute, for every heater, whether its wave is replaced by the average or simulated in time")
        self.analyze.clicked.connect(self.run_analysis)
        self.status = QLabel("Press Analyze to see which heaters need a time simulation; F5 runs everything.")
        self.status.setWordWrap(True)
        rf.addRow(self.analyze)
        rf.addRow(self.status)
        for w in (self.threshold, self.start_c, self.cycles, self.time_s, self.max_steps):
            w.valueChanged.connect(self._apply_options)
        for w in (self.start, self.duration, self.steady_mode):
            w.currentIndexChanged.connect(self._apply_options)

        # ---- decision table and waveform
        self.dec_table = QTableWidget(0, 7)
        self.dec_table.setHorizontalHeaderLabels(["Heater", "Period", "Duty", "Avg W", "Osc. °C", "% rise", "Regime"])
        self.dec_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dec_table.setToolTip("Decision for every heater: period, duty, average power, the temperature oscillation it would cause (°C and % of the rise) and the regime chosen.")
        self.dec_table.verticalHeader().setVisible(False)
        self.dec_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dec_table.setMaximumHeight(150)
        self.fig = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.fig)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("Heaters"))
        lv.addWidget(self.table, 1)
        lv.addWidget(self.run_box)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.addWidget(self.editor)
        rv.addWidget(self.canvas, 1)
        rv.addWidget(self.dec_table)
        split = QSplitter(Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([420, 760])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(split)
        doc.changed.connect(self.refresh)
        doc.state_changed.connect(self._load_options)
        compact_combos(self, 16)                          # The page must not be wider than it needs: the tab widget takes its width from the docks
        self.refresh()
        self._load_options()

    @staticmethod
    def _spin(spin, lo, hi, decimals, suffix):
        """!
        @brief Configure a QDoubleSpinBox.
        @param spin The spin box.
        @param lo Minimum.
        @param hi Maximum.
        @param decimals Decimals shown.
        @param suffix Unit suffix (with its leading space).
        """
        spin.setRange(lo, hi)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        spin.setKeyboardTracking(False)

    def set_theme(self, theme):
        """!
        @brief Change the plot theme.
        @param theme "dark" or "light".
        """
        self.theme = theme
        self._draw_waveforms()

    # ------------------------------------------------------------------ list and editor
    def refresh(self):
        """!
        @brief Rebuild the heater list and reload the editor from the document.
        """
        self._updating = True
        pr = self.doc.problem
        sel = self.current
        self.table.setRowCount(len(pr.heaters))
        for i, h in enumerate(pr.heaters):
            if h.profile is None:
                kind = "Constant"
            elif h.profile.kind == "table":
                kind = f"Table, {len(h.profile.powers)} stretches, {num(h.profile.period)} s{'' if h.profile.repeat else ', once'}"
            else:
                kind = f"Square wave, {self._describe_period(h.profile.period)}, {h.profile.duty:.0%}"
            regime = ""
            if i < len(self.decisions) and self.decisions[i].index == i:
                regime = self.decisions[i].regime
            for c, text in enumerate((h.name or f"Heater {i + 1}", kind, f"{num(h.average_power(), 3)} W", regime)):
                self.table.setItem(i, c, QTableWidgetItem(text))
        if pr.heaters:
            self.current = min(max(sel, 0), len(pr.heaters) - 1)
            self.table.selectRow(self.current)
        else:
            self.current = -1
        self._updating = False
        self._load_heater()
        self._draw_waveforms()
        self._mark_stale()

    @staticmethod
    def _describe_period(seconds):
        """!
        @brief Human-readable period.
        @param seconds Period in seconds.
        @return Text such as "20 s", "10 ms" or "100 Hz".
        """
        if seconds < 1.0:
            return f"{num(1.0 / seconds)} Hz"
        return f"{num(seconds)} s" if seconds < 600 else f"{num(seconds / 60)} min"

    def _on_row(self):
        """!
        @brief A different heater was selected in the list.
        """
        if self._updating:
            return
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self.current = rows[0].row()
            self._load_heater()

    def _fill_units(self):
        """!
        @brief Fill the unit chooser for the current "period or frequency" choice.
        """
        units = _PERIOD_UNITS if self.by.currentData() == "period" else _FREQUENCY_UNITS
        self.unit.blockSignals(True)
        self.unit.clear()
        self.unit.addItems(list(units))
        self.unit.blockSignals(False)

    def _load_heater(self):
        """!
        @brief Show the profile of the current heater in the editor.
        """
        self._updating = True
        pr = self.doc.problem
        ok = 0 <= self.current < len(pr.heaters)
        self.editor.setEnabled(ok)
        if ok:
            h = pr.heaters[self.current]
            self.kind.setCurrentIndex(0 if h.profile is None else (2 if h.profile.kind == "table" else 1))
            self.const_power.setValue(h.power)
            w = h.profile
            self.repeat.setChecked(True if w is None else bool(w.repeat))
            if w is not None and w.kind == "table":
                pass                                                          # Summarised by _derived; edited in the CSV file
            elif w is not None:
                # Show the period in the most natural unit
                if self.by.currentData() == "period":
                    unit = "µs" if w.period < 1e-3 else "ms" if w.period < 1 else "s" if w.period < 600 else "min"
                    self._fill_units()
                    self.unit.setCurrentText(unit)
                    self.value.setValue(w.period / _PERIOD_UNITS[unit])
                else:
                    f = 1.0 / w.period
                    unit = "Hz" if f < 1e3 else "kHz" if f < 1e6 else "MHz"
                    self._fill_units()
                    self.unit.setCurrentText(unit)
                    self.value.setValue(f / _FREQUENCY_UNITS[unit])
                self.duty.setValue(w.duty * 100.0)
                self.p_on.setValue(w.p_on)
                self.p_off.setValue(w.p_off)
                self.avg.setValue(w.average())
            else:
                self._fill_units()
                self.unit.setCurrentText("s")
                self.value.setValue(10.0)
                self.duty.setValue(50.0)
                self.p_on.setValue(h.power)
                self.p_off.setValue(0.0)
                self.avg.setValue(h.power / 2.0)
        self._show_kind()
        self._updating = False
        self._derived()

    def _show_kind(self):
        """!
        @brief Enable the widgets that belong to the chosen kind of profile.
        """
        wave = self.kind.currentData() == "square"
        table = self.kind.currentData() == "table"
        self.const_power.setEnabled(not wave and not table)
        for w in self.wave_widgets:
            w.setEnabled(wave)
        self.p_on.setEnabled(wave and not self.avg_mode.isChecked())
        self.avg.setEnabled(wave and self.avg_mode.isChecked())
        self.repeat.setVisible(table)
        self.export_btn.setEnabled(wave or table)
        # Show only the rows of the chosen kind of profile (a table is edited in its CSV file)
        form = self.editor.layout()
        for widget in self.wave_widgets + [self.p_off, self.duty]:
            widget.setVisible(wave)
            label = form.labelForField(widget)
            if label is not None:
                label.setVisible(wave)
        self.period_label.setVisible(wave)
        for widget, show in ((self.const_power, not wave and not table),):
            widget.setVisible(show)
            label = form.labelForField(widget)
            if label is not None:
                label.setVisible(show)

    def _on_by(self, _index=None):
        """!
        @brief Switch between specifying a period and a frequency (the same wave, shown the other way).
        @param _index Ignored (the Qt signal argument).
        """
        if self._updating or self.current < 0:
            return
        self._load_heater()

    def _on_avg_mode(self, _checked=None):
        """!
        @brief Switch between entering the power while on and the average power.
        @param _checked Ignored (the Qt signal argument).
        """
        self._show_kind()

    def _period_seconds(self):
        """!
        @brief Period of the wave entered in the editor.
        @return Seconds.
        """
        v, u = self.value.value(), self.unit.currentText()
        return v * _PERIOD_UNITS[u] if self.by.currentData() == "period" else 1.0 / (v * _FREQUENCY_UNITS[u])

    def _wave_from_editor(self):
        """!
        @brief Square wave described by the editor widgets.
        @return SquareWave (not validated).
        """
        duty = self.duty.value() / 100.0
        p_off = self.p_off.value()
        p_on = p_off + (self.avg.value() - p_off) / duty if self.avg_mode.isChecked() else self.p_on.value()
        return SquareWave(p_on=p_on, period=self._period_seconds(), duty=duty, p_off=p_off)

    def _derived(self):
        """!
        @brief Update the derived values (average, on-time, frequency) and the validity message.
        """
        self.error.setText("")
        if self.kind.currentData() == "table" and 0 <= self.current < len(self.doc.problem.heaters):
            w = self.doc.problem.heaters[self.current].profile
            if w is not None and w.kind == "table":
                self.derived.setText(f"{len(w.powers)} stretches over {num(w.period)} s (shortest {num(w.shortest_feature())} s); "
                                     f"average {num(w.average(), 4)} W, peak {num(w.peak(), 4)} W, energy {num(w.average() * w.period, 4)} J. "
                                     "Edit the CSV file and import it again to change the table.")
            return
        if self.kind.currentData() != "square" or self.current < 0:
            self.derived.setText("")
            return
        w = self._wave_from_editor()
        try:
            w.validate()
        except ValueError as exc:
            self.error.setText(str(exc))
            self.derived.setText("")
            return
        self._updating = True
        (self.avg if not self.avg_mode.isChecked() else self.p_on).setValue(w.average() if not self.avg_mode.isChecked() else w.p_on)
        self._updating = False
        self.derived.setText(f"Period {num(w.period)} s = {num(1.0 / w.period)} Hz; on for {num(w.on_time())} s, off for {num(w.off_time())} s; "
                             f"average {num(w.average(), 4)} W, power while on {num(w.p_on, 4)} W, energy per period {num(w.average() * w.period, 4)} J")

    def _apply(self, *_):
        """!
        @brief Write the wave of the editor to the heater (undoable).
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating or self.current < 0 or self.kind.currentData() != "square":
            return
        w = self._wave_from_editor()
        try:
            w.validate()
        except ValueError:
            self._derived()
            return
        i = self.current
        self.doc.edit("Power profile", lambda proj: proj.problem.heaters[i].set_profile(w), merge_key=f"profile{i}")
        self._derived()

    def _apply_constant(self, value):
        """!
        @brief Write a constant power to the heater.
        @param value Power in watts.
        """
        if self._updating or self.current < 0 or self.kind.currentData() != "constant":
            return
        self.doc.set_props("heater", self.current, power=float(value))

    def _apply_kind(self, _index=None):
        """!
        @brief The kind of profile was changed: create or remove the square wave.
        @param _index Ignored (the Qt signal argument).
        """
        if self._updating or self.current < 0:
            return
        i = self.current
        if self.kind.currentData() == "constant":
            def to_constant(proj):
                h = proj.problem.heaters[i]
                h.profile = None
            self.doc.edit("Constant power", to_constant)
        elif self.kind.currentData() == "table":
            h = self.doc.problem.heaters[i]
            if h.profile is None or h.profile.kind != "table":
                # A table needs a file: ask for it, and go back to the previous kind if nothing was loaded
                if not self.import_csv():
                    self._load_heater()
            else:
                self._show_kind()
        else:
            self._show_kind()
            self._apply()

    def _apply_repeat(self, checked):
        """!
        @brief Change whether the table repeats.
        @param checked True to repeat.
        """
        if self._updating or self.current < 0:
            return
        i = self.current
        h = self.doc.problem.heaters[i]
        if h.profile is None or h.profile.kind != "table" or h.profile.repeat == checked:
            return

        def mutate(proj):
            proj.problem.heaters[i].profile.repeat = bool(checked)

        self.doc.edit("Repeat table", mutate)

    def import_csv(self, path=None):
        """!
        @brief Load a power profile for the selected heater from a CSV file.
        @param path File to read; if None a file dialog is shown.
        @return True if a profile was loaded.
        """
        if self.current < 0:
            return False
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import power profile", "", "CSV files (*.csv *.txt);;All files (*)")
            if not path:
                return False
        try:
            profile = read_profile_csv(path)
        except (ProfileFileError, OSError) as exc:
            QMessageBox.warning(self, "Cannot import the profile", str(exc))
            return False
        i = self.current
        self.doc.edit("Import power profile", lambda proj: proj.problem.heaters[i].set_profile(profile))
        return True

    def export_csv(self, path=None):
        """!
        @brief Write the profile of the selected heater to a CSV file.
        @param path File to write; if None a file dialog is shown.
        @return True if a file was written.
        """
        if self.current < 0 or self.doc.problem.heaters[self.current].profile is None:
            QMessageBox.information(self, "Nothing to export", "This heater has a constant power: choose a square wave or a table first.")
            return False
        h = self.doc.problem.heaters[self.current]
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export power profile", f"{h.name or 'heater'}_profile.csv", "CSV files (*.csv)")
            if not path:
                return False
        try:
            write_profile_csv(h.profile, path, h.name)
        except OSError as exc:
            QMessageBox.warning(self, "Cannot export the profile", str(exc))
            return False
        return True

    # ------------------------------------------------------------------ run settings
    def _load_options(self):
        """!
        @brief Load the time-simulation settings from the document options.
        """
        o = self.doc.options
        po = o.profile
        self._updating = True
        self.threshold.setValue(po.threshold_c)
        self.start.setCurrentIndex(max(self.start.findData(po.initial), 0))
        self.start_c.setValue(self.doc.problem.board.ambient if po.initial_c is None else po.initial_c)
        self.duration.setCurrentIndex(max(self.duration.findData(po.duration), 0))
        self.cycles.setValue(po.cycles)
        self.time_s.setValue(po.time_s)
        self.max_steps.setValue(po.max_steps)
        self.steady_mode.setCurrentIndex(max(self.steady_mode.findData(o.steady_power), 0))
        self._updating = False
        self._enable_options()

    def _enable_options(self):
        """!
        @brief Enable only the settings that apply to the chosen start and duration.
        """
        self.start_c.setEnabled(self.start.currentData() == "temperature")
        self.cycles.setEnabled(self.duration.currentData() == "cycles")
        self.time_s.setEnabled(self.duration.currentData() == "time")

    def _apply_options(self, *_):
        """!
        @brief Write the settings to the document options.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating:
            return
        po = self.doc.options.profile
        po.threshold_c = self.threshold.value()
        po.initial = self.start.currentData()
        po.initial_c = self.start_c.value() if po.initial == "temperature" else None
        po.duration = self.duration.currentData()
        po.cycles, po.time_s, po.max_steps = self.cycles.value(), self.time_s.value(), self.max_steps.value()
        self.doc.set_options(steady_power=self.steady_mode.currentData())
        self._enable_options()
        self._mark_stale()

    # ------------------------------------------------------------------ analysis
    def _mark_stale(self):
        """!
        @brief Forget the decisions when the design or the threshold changed.
        """
        if self.decisions:
            self.decisions = []
            self.dec_table.setRowCount(0)
            self.status.setText("The design changed: press Analyze again.")
            for i in range(self.table.rowCount()):
                if self.table.item(i, 3):
                    self.table.item(i, 3).setText("")

    def run_analysis(self):
        """!
        @brief Compute the decisions in the background.
        """
        if self.worker is not None and self.worker.isRunning():
            return
        pr = self.doc.problem
        if not pr.heaters:
            self.status.setText("Add a heater first.")
            return
        import copy
        self.analyze.setEnabled(False)
        self.status.setText("Computing the thermal response of the heaters…")
        self.worker = ProcessWorker("analyze", copy.deepcopy(pr), copy.deepcopy(self.doc.options))
        self.worker.done.connect(lambda out: self._on_analysis(*out))
        self.worker.failed.connect(self._on_analysis_failed)
        self.worker.cancelled.connect(lambda: self._on_analysis_failed("Cancelled."))
        compute.start(self.worker)

    def _on_analysis(self, resp, decisions, ref):
        """!
        @brief Show the decisions.
        @param resp StepResponse used.
        @param decisions List of HeaterDecision.
        @param ref Name of the model that produced the step response.
        """
        self.analyze.setEnabled(True)
        self.decisions = decisions
        self.dec_table.setRowCount(len(decisions))
        for r, d in enumerate(decisions):
            cells = [d.name, "-" if d.kind == "constant" else f"{num(d.period)} s" + ("" if d.repeat else " (once)"),
                     "-" if (d.kind == "constant" or d.duty != d.duty) else f"{d.duty:.0%}",
                     f"{num(d.average_power, 3)}", "-" if d.kind == "constant" else f"{d.oscillation:.2f}",
                     "-" if d.kind == "constant" else f"{d.oscillation_percent:.1f} %", d.regime]
            for c, text in enumerate(cells):
                self.dec_table.setItem(r, c, QTableWidgetItem(text))
        self.refresh_regimes()
        try:
            plan = profiles.plan_run(self.doc.problem, decisions, self.doc.options.profile)
            if plan["resolved"]:
                self.status.setText(f"Decision from the {ref} step response. About {plan['steps']} steps of {num(plan['dt'], 3)} s "
                                    f"({num(plan['window'])} s per window); press F5 to run.")
            else:
                self.status.setText(f"Decision from the {ref} step response: every heater is replaced by its average power; "
                                    "no time simulation is needed.")
        except profiles.ProfileError as exc:
            self.status.setText(str(exc))

    def refresh_regimes(self):
        """!
        @brief Put the regime of every heater in the heater list.
        """
        for i, d in enumerate(self.decisions):
            if i < self.table.rowCount() and self.table.item(i, 3):
                self.table.item(i, 3).setText(d.regime)

    def _on_analysis_failed(self, message):
        """!
        @brief Report a failed analysis.
        @param message Error text.
        """
        self.analyze.setEnabled(True)
        self.status.setText(f"Analysis failed: {message}")

    def show_decisions(self, decisions, reference):
        """!
        @brief Display decisions that came with a finished simulation.
        @param decisions List of HeaterDecision.
        @param reference Name of the reference model.
        """
        self._on_analysis(None, decisions, reference)

    def _draw_waveforms(self):
        """!
        @brief Draw the power of every heater with a profile.
        """
        with _mpl_theme(self.theme):
            plots.draw_waveforms(self.fig, self.doc.problem)
        _paint_figure(self.fig, self.theme)
        self.canvas.draw_idle()
