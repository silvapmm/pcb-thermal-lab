"""!
@file calculator.py
@brief Power calculator: the watts a part dissipates, from a temperature you measured.
@details Two independent routes, one per tab (docs/calculators.md, and the Help button of the window):
         * **From the drawn board** (inverse.power_from_temperature / power_band, run in the calculation process): the board you drew (its copper, vias, stack-up, heat transfer)
           is solved at two powers and the power that makes the model read your temperature at the chosen point is found. The copper does not "give" the heat: it decides how
           many kelvin each watt raises at that point (the board resistance shown in the result). Points: the board ring 1 mm around the part, the hottest board point or the
           mean under it, the junction (needs the part's theta) or the top of the package (needs theta and the datasheet psi_JT). The result has a band: best case, nominal and
           worst case, and the selector says which one is written into the part.
         * **From a datasheet parameter**: P = (Tj - T_reference) / parameter for a known junction temperature (a sense diode) with psi_JB, psi_JT or theta.
"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTabWidget,
                               QTextBrowser, QVBoxLayout, QWidget)

from .. import defaults
from ..inverse import power_from_theta
from .compute import ProcessWorker

HELP_FILE = Path(__file__).resolve().parents[1] / "help" / "calculator.html"
DESIGN = (("None (numbers only)", "none", "No design uncertainty: the band covers only the doubt about numbers (copper thickness, heat transfer, θ, ψJT, reading). It does not cover a wrongly drawn board."),
          ("Drawn from the real fabrication files", "cad", "The board was drawn from the real fabrication files (the copper, vias and planes as manufactured): a small doubt about the description (20 % of the 'estimated' amplitudes by default)."),
          ("Drawn by hand from the layout", "hand", "You drew the zones, pads and vias from the layout by hand: half of the 'estimated' amplitudes by default (copper coverage, copper weight, inner planes, vias)."),
          ("Estimated (no layout at hand)", "estimated", "The board is a guess (a hatched pour drawn solid, unknown copper weight, planes or vias not known): the full amplitudes of Preferences - Power calculator."))
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
           "The temperature of the top of the package (thermocouple or infrared). The datasheet's ψJT says how far below the junction it is: Ttop = Tj − ψJT·P, with Tj = board + θ·P. "
           "Needs the part's θ and the datasheet's ψJT."))
CASES = (("Best case (lowest power)", "best", "The lowest plausible power: the coolest assumptions inside the uncertainty. The optimistic end of the band."),
         ("Nominal", "nominal", "The power from your inputs as typed: the best single estimate."),
         ("Worst case (highest power)", "worst", "The highest plausible power: the hottest assumptions inside the uncertainty. Use it to check margins (Tj, power limit, hotspots)."))


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


class CalculatorHelp(QDialog):
    """!
    @brief The detailed, formatted help of the power calculator (pcbthermal/help/calculator.html).
    """

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("Power calculator - help")
        self.resize(820, 700)
        lay = QVBoxLayout(self)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.setToolTip("How the calculator works, what each field means, the uncertainty band, the validation and the limits.")
        self.view.setSource(QUrl.fromLocalFile(str(HELP_FILE)))
        lay.addWidget(self.view, 1)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.button(QDialogButtonBox.Close).setToolTip("Close the help.")
        box.rejected.connect(self.reject)
        lay.addWidget(box)


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
        self.doc, self.worker, self.out = doc, None, None
        lay = QVBoxLayout(self)
        intro = QLabel("Finds the watts a part dissipates from a temperature you measured. Choose <b>one</b> of the two routes.")
        intro.setToolTip("The routes are independent: you do not fill both. Press Help for how they work, the fields, the uncertainty band and the validation.")
        lay.addWidget(intro)
        self.tabs = QTabWidget()
        self.tabs.setToolTip("Route 1 solves the board you drew. Route 2 is the datasheet formula. Use one of them.")
        self.tabs.addTab(self._board_tab(), "Route 1: from the drawn board")
        self.tabs.addTab(self._datasheet_tab(), "Route 2: from a datasheet parameter")
        lay.addWidget(self.tabs, 1)
        bottom = QHBoxLayout()
        self.help_btn = QPushButton("Help")
        self.help_btn.setToolTip("Open the detailed help of the calculator: the routes, the parameters, the band, the validation, the limits.")
        self.help_btn.clicked.connect(lambda: CalculatorHelp(self).exec())
        self.close_btn = QPushButton("Close")
        self.close_btn.setToolTip("Close the calculator.")
        self.close_btn.clicked.connect(self.reject)
        bottom.addStretch(1)
        bottom.addWidget(self.help_btn)                                      # Help sits right before Close
        bottom.addWidget(self.close_btn)
        lay.addLayout(bottom)
        if not doc.problem.heaters:
            self.compute.setEnabled(False)
            self.result.setText("Draw a heater first.")
        self.heater.currentIndexChanged.connect(self._part_changed)
        self.point.currentIndexChanged.connect(self._point_changed)
        self._part_changed()
        self._point_changed()
        # The window keeps one size for every point: the parameters a point does not use are greyed, not removed
        self.setMinimumSize(self.sizeHint())

    # ------------------------------------------------------------------ route 1
    def _board_tab(self):
        """!
        @brief The tab of route 1 (the drawn board).
        @return QWidget.
        """
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel("Uses the board in the editor: change the copper, vias or stack-up there and the answer changes.")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: gray;")
        note.setToolTip("The board model is the same one the simulation uses, run backwards.")
        lay.addWidget(note)
        f = QFormLayout()
        self.heater = QComboBox()
        for k, h in enumerate(self.doc.problem.heaters):
            self.heater.addItem(h.name or f"Heater {k + 1}", k)
        self.heater.setToolTip("The part whose power is unknown. The other heaters keep the powers typed in the program.")
        self.point = QComboBox()
        for label, key, tip in POINTS:
            self.point.addItem(label, key)
            self.point.setItemData(self.point.count() - 1, tip, 3)           # Qt.ToolTipRole: the hint of each option
        self.point.setToolTip("Where you measured. Each option has a hint; the last two also use datasheet parameters, which appear below when you choose them.")
        self.measured = _spin(-50, 400, 60.0, 1, "°C", "The temperature you measured at that point, in °C.")
        self.ambient = _spin(-60, 200, self.doc.problem.board.ambient, 1, "°C", "Air temperature at the time of the measurement (the board's ambient is the default).")
        self.theta = _spin(0, 5000, 0.0, 2, "K/W", "θ junction-to-pad of the part: the datasheet's junction-to-case (bottom / exposed pad), junction-to-lead or junction-to-solder-point "
                           "resistance. Never θJA. It starts at the value typed in the part's Properties and is used for this calculation only.")
        self.psi_jt = _spin(0, 500, 2.0, 2, "K/W", "ψJT of the datasheet (junction-to-top characterisation parameter): Tj − Ttop = ψJT·P. Typically 0.3 to 5 K/W. It belongs to the "
                            "datasheet's test board: on yours it is an estimate.")
        self.theta.setProperty("base_tip", self.theta.toolTip())
        self.psi_jt.setProperty("base_tip", self.psi_jt.toolTip())
        self.theta_label = QLabel("θ junction-pad")
        self.psi_label = QLabel("ψJT (datasheet)")
        for label, wd in (("Part", self.heater), ("Measured at", self.point), ("Temperature", self.measured)):
            f.addRow(label, wd)
        f.addRow(self.theta_label, self.theta)
        f.addRow(self.psi_label, self.psi_jt)
        f.addRow("Ambient", self.ambient)
        self.design = QComboBox()
        for label, key, tip in DESIGN:
            self.design.addItem(label, key)
            self.design.setItemData(self.design.count() - 1, tip, 3)
        self.design.setCurrentIndex(max(0, self.design.findData(defaults.value("calculator", "design_level"))))
        self.design.setToolTip("How well the drawn board matches the real one (the design uncertainty of the band). The copper coverage, copper weight, inner planes and vias are "
                               "moved one at a time and added to the other sources as the root of the sum of squares. Amplitudes: Preferences - Power calculator. "
                               "Without it the band does not cover a wrongly drawn board. Each option has a hint.")
        f.addRow("Board description", self.design)
        lay.addLayout(f)
        self.band = QCheckBox("Uncertainty band (best case / worst case)")
        self.band.setChecked(True)
        self.band.setToolTip("Also compute the best and worst case: the copper, heat transfer, θ, ψJT and the reading are moved to both ends of their uncertainty (Preferences) "
                             "and the effects added as the root of the sum of squares. Slower: about ten times the nominal calculation, about twice as long again with the board description on.")
        self.band.toggled.connect(self.design.setEnabled)                  # The board description only acts on the band: greyed without it
        lay.addWidget(self.band)
        row = QHBoxLayout()
        self.compute = QPushButton("Calculate")
        self.compute.setToolTip("Runs the board model and finds the power that reproduces the measurement. The result is as good as the board drawn "
                                "(copper, vias, stack-up, heat transfer coefficients) and as the measurement (a probe that touches the board cools it a little).")
        self.compute.clicked.connect(self._run)
        row.addWidget(self.compute)
        row.addStretch(1)
        lay.addLayout(row)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        self.result.setMinimumHeight(self.result.fontMetrics().lineSpacing() * 9)       # Room for the longest result: the window does not grow when it appears
        self.result.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self.result.setToolTip("The power (best case, nominal, worst case), what the model reads at the nominal power, the board resistance at the measured point and what each "
                               "source of doubt contributes.")
        lay.addWidget(self.result)
        row = QHBoxLayout()
        self.case = QComboBox()
        for label, key, tip in CASES:
            self.case.addItem(label, key)
            self.case.setItemData(self.case.count() - 1, tip, 3)
        self.case.setCurrentIndex(1)
        self.case.setToolTip("Which power goes into the part: the best case (lowest), the nominal, or the worst case (highest, to check margins). Each option has a hint.")
        self.use = QPushButton("Use as the power of this part")
        self.use.setMinimumWidth(240)
        self.use.setToolTip("Write the selected power in the heater (it can be undone); the next simulation uses it. Nothing else changes.")
        self.use.setEnabled(False)
        self.use.clicked.connect(self._use)
        row.addWidget(QLabel("Power to use"))
        row.addWidget(self.case, 1)
        row.addWidget(self.use)
        lay.addLayout(row)
        return w

    # ------------------------------------------------------------------ route 2
    def _datasheet_tab(self):
        """!
        @brief The tab of route 2 (a datasheet parameter).
        @return QWidget.
        """
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel("No board model: the datasheet relation P = (Tj − Treference) / parameter. The result updates as you type.")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: gray;")
        note.setToolTip("Quick, but the parameter belongs to the datasheet's own test board: on yours it is an estimate.")
        lay.addWidget(note)
        f = QFormLayout()
        self.tj = _spin(-50, 500, 100.0, 1, "°C", "Junction temperature, for example from the part's sense diode or temperature output.")
        self.tref = _spin(-50, 500, 80.0, 1, "°C", "Temperature of the reference point: the board 1 mm from the package for ψJB or θJB, the top of the case for ψJT.")
        self.par = _spin(0.01, 2000, 10.0, 2, "K/W", "ψJB, ψJT or θ from the datasheet. They belong to the datasheet's test board: on yours they are an estimate (ψJB within about 15 % of θJB).")
        self.out2 = QLabel("")
        self.out2.setToolTip("P = (Tj − Treference) / parameter.")
        for label, wd in (("Junction Tj", self.tj), ("Reference point", self.tref), ("Parameter", self.par)):
            f.addRow(label, wd)
        f.addRow("Power", self.out2)
        lay.addLayout(f)
        self.use2 = QPushButton("Use as the power of a part")
        self.use2.setMinimumWidth(260)
        self.use2.setMinimumHeight(30)
        self.use2.setToolTip("Write this power in the part chosen in Route 1 (it can be undone).")
        self.use2.clicked.connect(self._use2)
        row = QHBoxLayout()
        row.addWidget(self.use2)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        for wd in (self.tj, self.tref, self.par):
            wd.valueChanged.connect(self._theta)
        self._theta()
        return w

    # ------------------------------------------------------------------ behaviour
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
        @brief Grey out the parameters the chosen measurement point does not use (θ is used by the junction and the top, ψJT by the top only). They stay in place, so the
               window never changes size when the point changes.
        @param _ Ignored (the Qt signal argument).
        """
        key = self.point.currentData()
        for wd, on, why in ((self.theta, key in ("junction", "top"), "junction or the top of the package"), (self.psi_jt, key == "top", "top of the package")):
            wd.setEnabled(on)
            label = self.theta_label if wd is self.theta else self.psi_label
            label.setEnabled(on)
            suffix = "" if on else f"\n\nGreyed: this point does not use it (it is used by the {why})."
            wd.setToolTip(wd.property("base_tip") + suffix)

    def _theta(self, *_):
        """!
        @brief Update the datasheet route.
        @param _ Ignored (the value of the Qt signal).
        """
        try:
            self.power2 = power_from_theta(self.tj.value(), self.tref.value(), self.par.value())
            self.out2.setText(f"<b>{self.power2:.3f} W</b>")
            self.use2.setEnabled(bool(self.doc.problem.heaters))
        except ValueError as exc:
            self.power2 = None
            self.out2.setText(str(exc))
            self.use2.setEnabled(False)

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
        self.worker = ProcessWorker("inverse", problem, k, self.measured.value(), self.point.currentData(), self.ambient.value(),
                                    max(self.doc.options.cell_mm, 0.5), self.psi_jt.value(), self.band.isChecked(), {"design_level": self.design.currentData()})
        self.worker.progress.connect(lambda text, _f: self.result.setText(f"Calculating… {text}"))
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.cancelled.connect(lambda: self._failed("Cancelled."))
        self.worker.start()

    def _done(self, out):
        """!
        @brief Show the calculated power (with its band) and what the model reads at that power.
        @param out Dict of inverse.power_from_temperature or inverse.power_band.
        """
        self.compute.setEnabled(True)
        self.out = out
        st = out.get("at_power", {})
        names = (("board_max", "hottest board point"), ("ring", "board ring"), ("junction", "junction"), ("top", "top of the package"))
        reads = ", ".join(f"{label} {st[key]:.1f} °C" for key, label in names if st.get(key) is not None)
        if "best_w" in out:
            head = (f"<b>Nominal {out['power_w']:.3f} W</b> &nbsp; (best case {out['best_w']:.3f} W, worst case {out['worst_w']:.3f} W)<br>")
            # The design terms are named "design: ..." and listed apart, so the reader sees what comes from the numbers and what from the description of the board
            num = "".join(f"{c['factor']}: {c['low_w']:.2f} to {c['high_w']:.2f} W; " for c in out.get("contributions", []) if not c.get("design"))
            des = "".join(f"{c['factor'][len('design: '):]}: {c['low_w']:.2f} to {c['high_w']:.2f} W; " for c in out.get("contributions", []) if c.get("design"))
            band = f"<br>What each source of doubt moves: {num.rstrip('; ')}."
            if des:
                band += f"<br>Board description ({out.get('uncertainty', {}).get('design_level', '')}): {des.rstrip('; ')}."
        else:
            head, band = f"<b>{out['power_w']:.3f} W</b><br>", ""
        self.result.setText(head + f"reproduces {out['temperature_c']:.1f} °C ({out['runs']} model runs"
                            f"{', linear' if out['linear'] else ', iterated: the heat transfer depends on the temperature'}).<br>"
                            f"At the nominal power the model reads: {reads}.<br>"
                            f"Board resistance at the measured point: <b>{out.get('resistance_k_per_w', 0.0):.1f} K/W</b> (kelvin per watt: set by the copper, vias, stack-up and air)."
                            + band)
        self.use.setEnabled(True)

    def selected_power(self):
        """!
        @brief The power chosen by the case selector (best case, nominal or worst case).
        @return Watts, or None when there is no result yet.
        """
        if not self.out:
            return None
        key = self.case.currentData()
        if key == "best" and "best_w" in self.out:
            return float(self.out["best_w"])
        if key == "worst" and "worst_w" in self.out:
            return float(self.out["worst_w"])
        return float(self.out["power_w"])

    def _failed(self, message):
        """!
        @brief Show why the calculation failed.
        @param message Error text.
        """
        self.compute.setEnabled(True)
        self.result.setText(message)

    def _use(self):
        """!
        @brief Write the selected power in the heater.
        """
        p = self.selected_power()
        if p is not None:
            self.doc.set_props("heater", self.heater.currentData(), power=p, merge=False)
            self.use.setEnabled(False)

    def _use2(self):
        """!
        @brief Write the power of the datasheet route in the part chosen in route 1.
        """
        if self.power2 is not None and self.heater.currentData() is not None:
            self.doc.set_props("heater", self.heater.currentData(), power=float(self.power2), merge=False)

    def done(self, code):
        """!
        @brief Cancel a running calculation when the dialog closes.
        @param code Dialog result code.
        """
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
        super().done(code)
