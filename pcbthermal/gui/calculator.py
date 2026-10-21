"""!
@file calculator.py
@brief Power calculator: the power of a part from a measured temperature, by the board model or by a datasheet thermal parameter.
@details Two routes (docs/models.md section 6):
         * Board model: the temperature measured at a point (board 1 mm from the part, hottest point under it, its mean, or the junction with theta) and the
           ambient give the power that makes the drawn board reproduce it (inverse.power_from_temperature, run in the calculation process).
         * Datasheet: P = (Tj - T_reference) / parameter for a known junction temperature (a sense diode) with psi_JB, psi_JT or theta.
"""

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox, QLabel, QPushButton,
                               QVBoxLayout)

from ..inverse import power_from_theta
from .compute import ProcessWorker


def _spin(lo, hi, value, decimals, suffix, tip):
    """!
    @brief A spin box with a unit and a tooltip.
    @param lo Minimum.
    @param hi Maximum.
    @param value Initial value.
    @param decimals Decimals.
    @param suffix Unit text.
    @param tip Tooltip.
    @return QDoubleSpinBox.
    """
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setValue(value)
    s.setSuffix(" " + suffix)
    s.setToolTip(tip)
    s.setKeyboardTracking(False)
    return s


class PowerCalculator(QDialog):
    """!
    @brief Dialog of the power calculator.
    """

    def __init__(self, doc, parent=None):
        """!
        @param doc The Document (its heaters are the parts to choose from).
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("Power from a measured temperature")
        self.doc, self.worker, self.result_power = doc, None, None
        lay = QVBoxLayout(self)

        g = QGroupBox("1. From a temperature measured on the board (uses the drawn board)")
        f = QFormLayout(g)
        self.heater = QComboBox()
        for k, h in enumerate(doc.problem.heaters):
            self.heater.addItem(h.name or f"Heater {k + 1}", k)
        self.heater.setToolTip("The part whose power is unknown. The other heaters keep the powers typed in the program.")
        self.point = QComboBox()
        for label, key in (("Board temperature 1 mm around the part (ring)", "ring"), ("Hottest board point under the part", "max"),
                           ("Mean board temperature under the part", "mean"), ("Junction (needs θ junction-pad)", "junction")):
            self.point.addItem(label, key)
        self.point.setToolTip("Where the temperature was measured. The ring is the board 0.5 to 1.5 mm outside the package (the JEDEC point for ψJB): "
                              "use a thermocouple or an IR camera; an IR gun's spot is too large for a small part.")
        self.measured = _spin(-50, 400, 60.0, 1, "°C", "Measured temperature at that point.")
        self.ambient = _spin(-60, 200, doc.problem.board.ambient, 1, "°C", "Air temperature at the time of the measurement (the board's ambient is the default).")
        self.compute = QPushButton("Calculate")
        self.compute.setToolTip("Runs the board model (two or three solves) and finds the power that reproduces the measurement. The result is as good as the board drawn: "
                                "copper, vias, stack-up, heat transfer coefficients, and the probe (it cools the board a little).")
        self.compute.clicked.connect(self._run)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        self.use = QPushButton("Use as the power of this part")
        self.use.setToolTip("Write the calculated power in the heater and keep the other settings.")
        self.use.setEnabled(False)
        self.use.clicked.connect(self._use)
        for label, w in (("Part", self.heater), ("Measured at", self.point), ("Temperature", self.measured), ("Ambient", self.ambient)):
            f.addRow(label, w)
        f.addRow(self.compute)
        f.addRow(self.result)
        f.addRow(self.use)
        lay.addWidget(g)

        g = QGroupBox("2. From a datasheet parameter (junction temperature known)")
        f = QFormLayout(g)
        self.tj = _spin(-50, 500, 100.0, 1, "°C", "Junction temperature, for example from the part's sense diode or temperature output.")
        self.tref = _spin(-50, 500, 80.0, 1, "°C", "Temperature of the reference point: the board 1 mm from the package for ψJB or θJB, the top of the case for ψJT.")
        self.par = _spin(0.01, 2000, 10.0, 2, "K/W", "ψJB, ψJT or θ from the datasheet. They belong to the datasheet's test board: on yours they are an estimate (ψJB within about 15 % of θJB).")
        self.out2 = QLabel("")
        for label, w in (("Junction Tj", self.tj), ("Reference point", self.tref), ("Parameter", self.par)):
            f.addRow(label, w)
        f.addRow("Power", self.out2)
        for w in (self.tj, self.tref, self.par):
            w.valueChanged.connect(self._theta)
        self._theta()
        lay.addWidget(g)
        note = QLabel("Both routes give an estimate: the board model assumes the board drawn is the real one; ψ parameters are not thermal resistances and come from the "
                      "datasheet's board (JEDEC JESD51-12).")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: gray;")
        lay.addWidget(note)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.button(QDialogButtonBox.Close).setToolTip("Close the calculator.")
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        if not doc.problem.heaters:
            self.compute.setEnabled(False)
            self.result.setText("Draw a heater first.")

    def _theta(self, *_):
        """!
        @brief Update the datasheet route.
        """
        try:
            self.out2.setText(f"<b>{power_from_theta(self.tj.value(), self.tref.value(), self.par.value()):.3f} W</b>")
        except ValueError as exc:
            self.out2.setText(str(exc))

    def _run(self):
        """!
        @brief Start the board-model calculation in the calculation process.
        """
        if self.worker is not None and self.worker.isRunning():
            return
        import copy
        self.use.setEnabled(False)
        self.result.setText("Calculating…")
        self.compute.setEnabled(False)
        self.worker = ProcessWorker("inverse", copy.deepcopy(self.doc.problem), self.heater.currentData(), self.measured.value(), self.point.currentData(),
                                    self.ambient.value(), max(self.doc.options.cell_mm, 0.5))
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.cancelled.connect(lambda: self._failed("Cancelled."))
        self.worker.start()

    def _done(self, out):
        """!
        @brief Show the calculated power.
        @param out Dict of inverse.power_from_temperature.
        """
        self.compute.setEnabled(True)
        self.result_power = out["power_w"]
        self.result.setText(f"<b>{out['power_w']:.3f} W</b> reproduce {out['temperature_c']:.1f} °C ({out['runs']} model runs"
                            f"{', linear' if out['linear'] else ', iterated: the heat transfer depends on the temperature'}).")
        self.use.setEnabled(True)

    def _failed(self, message):
        """!
        @brief Show why the calculation failed.
        @param message Error text.
        """
        self.compute.setEnabled(True)
        self.result.setText(message)

    def _use(self):
        """!
        @brief Write the power in the heater.
        """
        if self.result_power is not None:
            self.doc.set_props("heater", self.heater.currentData(), power=float(self.result_power), merge=False)
            self.use.setEnabled(False)

    def done(self, code):
        """!
        @brief Cancel a running calculation when the dialog closes.
        @param code Dialog result code.
        """
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
        super().done(code)
