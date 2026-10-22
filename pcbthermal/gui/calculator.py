"""!
@file calculator.py
@brief Power calculator: the watts a part dissipates, from a temperature you measured.
@details Two routes (docs/calculators.md):
         * **From the drawn board** (inverse.power_from_temperature, run in the calculation process): the board you drew (its copper, vias, stack-up, heat transfer) is solved at two
           powers and the power that makes the model read your temperature at the chosen point is found. The copper does not "give" the heat: it decides how many kelvin each watt
           raises at that point (the board resistance shown in the result). Points: the board ring 1 mm around the part, the hottest board point or the mean under it, the
           junction (needs the part's theta) or the top of the package (needs theta and the datasheet psi_JT).
         * **From a datasheet parameter**: P = (Tj - T_reference) / parameter for a known junction temperature (a sense diode) with psi_JB, psi_JT or theta.
"""

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox, QLabel, QPushButton,
                               QVBoxLayout)

from ..inverse import power_from_theta
from .compute import ProcessWorker

POINTS = (("Board temperature 1 mm around the part (ring)", "ring",
           "The board 0.5 to 1.5 mm outside the package: the point where the datasheet's ψJB takes the board temperature. Measure it with a thermocouple taped on the copper "
           "next to the part. Needs nothing from the datasheet."),
          ("Hottest board point under the part", "max",
           "The hottest copper under the footprint (what a probe under the package would read). Needs nothing from the datasheet."),
          ("Mean board temperature under the part", "mean", "The average board temperature under the footprint. Needs nothing from the datasheet."),
          ("Junction (needs θ junction-pad)", "junction",
           "The junction temperature itself, from a sense diode or the part's own sensor. The program adds θ·P between the board and the junction, so it needs the part's "
           "junction-to-pad resistance θ."),
          ("Top of the package (needs θ and ψJT)", "top",
           "The temperature of the top of the package (thermocouple or IR). The datasheet's ψJT says how far below the junction it is: Ttop = Tj − ψJT·P, with Tj = board + θ·P. "
           "Needs the part's θ and the datasheet's ψJT."))


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
        self.setWindowTitle("Power calculator")
        self.doc, self.worker, self.result_power = doc, None, None
        lay = QVBoxLayout(self)
        intro = QLabel("Finds the power a part dissipates from a temperature you measured. <b>Route 1</b> solves the board you drew (copper, vias, stack-up, air) and finds "
                       "the watts that make it read your temperature; the copper decides how many kelvin each watt gives. <b>Route 2</b> applies a datasheet parameter to a "
                       "known junction temperature.")
        intro.setWordWrap(True)
        intro.setToolTip("How the calculator works. The board model is the same one the simulation uses, run backwards. Details, formulas, validation and limits: docs/calculators.md.")
        lay.addWidget(intro)

        g = QGroupBox("1. From the drawn board")
        g.setToolTip("Uses the board in the editor: change the copper, vias or stack-up there and the answer changes.")
        f = QFormLayout(g)
        self.heater = QComboBox()
        for k, h in enumerate(doc.problem.heaters):
            self.heater.addItem(h.name or f"Heater {k + 1}", k)
        self.heater.setToolTip("The part whose power is unknown. The other heaters keep the powers typed in the program.")
        self.point = QComboBox()
        for label, key, tip in POINTS:
            self.point.addItem(label, key)
            self.point.setItemData(self.point.count() - 1, tip, 3)           # Qt.ToolTipRole: the hint of each option
        self.point.setToolTip("Where you measured. Each option has a hint; the last two also use datasheet parameters, which appear below when you choose them.")
        self.measured = _spin(-50, 400, 60.0, 1, "°C", "The temperature you measured at that point, in °C.")
        self.ambient = _spin(-60, 200, doc.problem.board.ambient, 1, "°C", "Air temperature at the time of the measurement (the board's ambient is the default).")
        self.theta = _spin(0, 5000, 0.0, 2, "K/W", "θ junction-to-pad of the part: the datasheet's junction-to-case (bottom / exposed pad), junction-to-lead or junction-to-solder-point "
                           "resistance. Never θJA. It starts at the value typed in the part's Properties and is used for this calculation only.")
        self.psi_jt = _spin(0, 500, 2.0, 2, "K/W", "ψJT of the datasheet (junction-to-top characterisation parameter): Tj − Ttop = ψJT·P. Typically 0.3 to 5 K/W. It belongs to the "
                            "datasheet's test board: on yours it is an estimate.")
        self.compute = QPushButton("Calculate")
        self.compute.setToolTip("Runs the board model (two or three solves) and finds the power that reproduces the measurement. The result is as good as the board drawn "
                                "(copper, vias, stack-up, heat transfer coefficients) and as the measurement (a probe that touches the board cools it a little).")
        self.compute.clicked.connect(self._run)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        self.result.setToolTip("The power found, what the model reads at that power, and the board resistance (kelvin per watt) at the measured point.")
        self.use = QPushButton("Use as the power of this part")
        self.use.setToolTip("Write the calculated power in the heater and keep the other settings.")
        self.use.setEnabled(False)
        self.use.clicked.connect(self._use)
        self.theta_label = QLabel("θ junction-pad")
        self.psi_label = QLabel("ψJT (datasheet)")
        for label, w in (("Part", self.heater), ("Measured at", self.point), ("Temperature", self.measured)):
            f.addRow(label, w)
        f.addRow(self.theta_label, self.theta)
        f.addRow(self.psi_label, self.psi_jt)
        f.addRow("Ambient", self.ambient)
        f.addRow(self.compute)
        f.addRow(self.result)
        f.addRow(self.use)
        lay.addWidget(g)
        self.heater.currentIndexChanged.connect(self._part_changed)
        self.point.currentIndexChanged.connect(self._point_changed)
        self._part_changed()

        g = QGroupBox("2. From a datasheet parameter (junction temperature known)")
        g.setToolTip("No board model: the datasheet relation P = (Tj − Treference) / parameter. Quick, but the parameter belongs to the datasheet's own test board.")
        f = QFormLayout(g)
        self.tj = _spin(-50, 500, 100.0, 1, "°C", "Junction temperature, for example from the part's sense diode or temperature output.")
        self.tref = _spin(-50, 500, 80.0, 1, "°C", "Temperature of the reference point: the board 1 mm from the package for ψJB or θJB, the top of the case for ψJT.")
        self.par = _spin(0.01, 2000, 10.0, 2, "K/W", "ψJB, ψJT or θ from the datasheet. They belong to the datasheet's test board: on yours they are an estimate (ψJB within about 15 % of θJB).")
        self.out2 = QLabel("")
        self.out2.setToolTip("P = (Tj − Treference) / parameter.")
        for label, w in (("Junction Tj", self.tj), ("Reference point", self.tref), ("Parameter", self.par)):
            f.addRow(label, w)
        f.addRow("Power", self.out2)
        for w in (self.tj, self.tref, self.par):
            w.valueChanged.connect(self._theta)
        self._theta()
        lay.addWidget(g)
        note = QLabel("Both routes give an estimate. Route 1 is only as good as the drawn board; ψ parameters are not thermal resistances and come from the datasheet's board "
                      "(JEDEC JESD51-12). The datasheet shortcut P = (Ttop − Tamb)/(θJA − ψJT) is not offered: with a θJA 30 % away from your board's it is 25 to 50 % off.")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: gray;")
        note.setToolTip("Why the answers are estimates. Validation against datasheets and the sensitivity to the copper: docs/calculators.md.")
        lay.addWidget(note)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.button(QDialogButtonBox.Close).setToolTip("Close the calculator.")
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        if not doc.problem.heaters:
            self.compute.setEnabled(False)
            self.result.setText("Draw a heater first.")
        self._point_changed()

    def _part_changed(self, *_):
        """!
        @brief Load the part's junction resistance into the θ field.
        @param _ Ignored (the Qt signal argument).
        """
        k = self.heater.currentData()
        if k is not None and 0 <= k < len(self.doc.problem.heaters):
            self.theta.setValue(self.doc.problem.heaters[k].theta)

    def _point_changed(self, *_):
        """!
        @brief Show only the parameters the chosen measurement point needs (θ for the junction, θ and ψJT for the top).
        @param _ Ignored (the Qt signal argument).
        """
        key = self.point.currentData()
        for w in (self.theta, self.theta_label):
            w.setVisible(key in ("junction", "top"))
        for w in (self.psi_jt, self.psi_label):
            w.setVisible(key == "top")

    def _theta(self, *_):
        """!
        @brief Update the datasheet route.
        @param _ Ignored (the value of the Qt signal).
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
        problem = copy.deepcopy(self.doc.problem)
        k = self.heater.currentData()
        if self.point.currentData() in ("junction", "top"):
            problem.heaters[k].theta = self.theta.value()                  # The θ typed here is used for this calculation only
        self.worker = ProcessWorker("inverse", problem, k, self.measured.value(), self.point.currentData(),
                                    self.ambient.value(), max(self.doc.options.cell_mm, 0.5), self.psi_jt.value())
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.cancelled.connect(lambda: self._failed("Cancelled."))
        self.worker.start()

    def _done(self, out):
        """!
        @brief Show the calculated power and what the model reads at that power.
        @param out Dict of inverse.power_from_temperature.
        """
        self.compute.setEnabled(True)
        self.result_power = out["power_w"]
        st = out.get("at_power", {})
        names = (("board_max", "hottest board point"), ("ring", "board ring"), ("junction", "junction"), ("top", "top of the package"))
        reads = ", ".join(f"{label} {st[key]:.1f} °C" for key, label in names if st.get(key) is not None)
        self.result.setText(f"<b>{out['power_w']:.3f} W</b> reproduce {out['temperature_c']:.1f} °C "
                            f"({out['runs']} model runs{', linear' if out['linear'] else ', iterated: the heat transfer depends on the temperature'}).<br>"
                            f"At that power the model reads: {reads}.<br>"
                            f"Board resistance at the measured point: <b>{out.get('resistance_k_per_w', 0.0):.1f} K/W</b> (kelvin per watt: set by the copper, vias, stack-up and air).")
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
