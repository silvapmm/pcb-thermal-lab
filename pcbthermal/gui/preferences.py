"""!
@file preferences.py
@brief Preferences: the defaults and the material libraries of the program, kept in a JSON file the user can edit here or by hand.

@details The window edits the same structure as `pcbthermal/data/defaults.json` (see pcbthermal/defaults.py): five libraries (via fills, metals, interface materials,
         dielectrics, package families) as tables, and the defaults of a new board, of new elements, of the materials and of the solver as forms. *Save* writes only what differs
         from the shipped defaults to the user file in the configuration folder; *Reset* deletes that file. The program reads it at start-up and says in the status bar when it
         is in use.
"""

import copy
import os
import shutil

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .. import defaults
from .. import model

LIBRARY_TITLES = {"via_fills": "Via fills", "metals": "Metals (heatsink blocks)", "interfaces": "Interface materials", "dielectrics": "Dielectrics (stack-up)",
                  "package_theta": "Package families (typical θ)"}
LIBRARY_TIPS = {"via_fills": "What a via barrel can be filled with: the name appears in the via's Fill list and the conductivity is its typical value (W/mK). Edit a cell to change it, "
                             "add a row for a new fill.",
                "metals": "Metals of a heatsink block: conductivity (W/mK) and volumetric heat capacity (J/m³K).",
                "interfaces": "Pastes and gap pads under a heatsink or a package: apparent conductivity (W/mK) and thickness (mm); the resistance is thickness / conductivity.",
                "dielectrics": "Dielectrics of the stack-up: conductivity across and along the plane (W/mK), density (kg/m³) and specific heat (J/kgK).",
                "package_theta": "Typical junction-to-pad resistance by package family (K/W): a starting value, never the datasheet's."}
SECTION_TITLES = {"new_board": "New board", "new_elements": "New elements", "materials": "Materials of a new board", "calculator": "Power calculator", "solver": "Solver of a new project"}
SECTION_HINTS = {"new_board": "The values a board starts with when you choose File - New board (and when the program starts).",
                 "new_elements": "The values of an element when you draw it or add it from the right-click menu.",
                 "materials": "Copper and the simple-stack-up dielectric of a new board. The dielectrics of the advanced stack-up are a library.",
                 "calculator": "How uncertain the inputs of the power calculator are. The band (best case / nominal / worst case) moves each one to both ends and adds the effects as the root of the sum of squares.",
                 "solver": "The models and settings a new project starts with."}
CHOICES = {"h_mode": ("manual", "computed"), "orientation": ("horizontal", "vertical"), "linear_solver": ("direct", "cg", "sor")}
MODELS = ("fvm", "lumped", "analytic", "fdm", "solid3d")
TIPS = {
    "width_mm": "Width of a new board in mm.", "height_mm": "Height of a new board in mm.", "layers": "Copper layers of a new board.",
    "ambient_c": "Ambient temperature of a new board in °C.", "h_top": "Heat transfer coefficient of the top face (W/m²K), typed mode.",
    "h_bottom": "Heat transfer coefficient of the bottom face (W/m²K), typed mode.", "edges_lose_heat": "Whether the board edges exchange heat with the air.",
    "h_side": "Heat transfer coefficient of the edges (W/m²K).", "via_plating_um": "Copper plating of the via barrel in µm.",
    "h_mode": "How the face coefficients are found: typed, or computed from convection and radiation.", "emissivity_top": "Emissivity of the top face (0 to 1).",
    "emissivity_bottom": "Emissivity of the bottom face (0 to 1).", "orientation": "Mounting of the board for the computed coefficients.",
    "air_speed": "Air speed along the board in m/s (computed mode).", "h_calibration": "Multiplier of the computed convection.",
    "heater_power_w": "Power of a new heater in W.", "heater_size_mm": "Side of a heater dropped from the right-click menu, in mm.",
    "zone_fill": "Copper fill (0 to 1) of a new zone.", "zone_size_mm": "Side of a zone dropped from the right-click menu, in mm.",
    "via_diameter_mm": "Hole diameter of a new via in mm.", "via_fill": "Fill of a new via (a name of the via fills library).",
    "heatsink_h_extra": "Extra heat transfer coefficient of a new heatsink in W/m²K.", "heatsink_size_mm": "Side of a heatsink dropped from the right-click menu, in mm.",
    "block_thickness_mm": "Thickness of a metal block when a heatsink is switched to a block, in mm.", "block_metal": "Metal of a new block (a name of the metals library).",
    "block_interface": "Interface material of a new block (a name of the interface library).",
    "k_copper": "Conductivity of copper (W/mK).", "rho_copper": "Density of copper (kg/m³).", "cp_copper": "Specific heat of copper (J/kgK).",
    "k_fr4_through": "Conductivity of the simple-stack-up dielectric across the board (W/mK).", "k_fr4_inplane": "Conductivity of the simple-stack-up dielectric along the plane (W/mK).",
    "rho_fr4": "Density of the simple-stack-up dielectric (kg/m³).", "cp_fr4": "Specific heat of the simple-stack-up dielectric (J/kgK).",
    "copper_uncertainty_pct": "Uncertainty of the copper (thickness of every layer) in the drawn board, in percent: how far the real copper may be from what you drew.",
    "h_uncertainty_pct": "Uncertainty of the heat transfer coefficients (or of the computed convection) in percent; natural convection correlations are good to 20 to 30 %.",
    "theta_uncertainty_pct": "Uncertainty of the part's junction-to-pad resistance θ in percent (datasheet numbers belong to the datasheet's board).",
    "psi_jt_uncertainty_pct": "Uncertainty of the datasheet ψJT in percent (it changes with the board and the air flow).",
    "reading_uncertainty_k": "Error of the temperature reading in kelvin: a thermocouple that touches the board, an infrared emissivity error. Typically 1 to 3 K.",
    "models": "Models selected in a new project.", "cell_mm": "Cell size in mm.", "linear_solver": "Solver of the FVM linear system.",
    "lumped_rings": "Rings of the Lumped model.", "analytic_modes": "Cosine modes of the Analytic model.", "hotspot_c": "Temperature limit for hotspot detection in °C.",
}


class PreferencesDialog(QDialog):
    """!
    @brief The window that edits the defaults and the libraries.
    """

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(760, 560)
        self.data = defaults.load()                         # The working copy: shipped plus the user's file
        self.saved = False                                  # True once Save or Reset changed the files
        lay = QVBoxLayout(self)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.RichText)
        self.info.setToolTip("Where the user's defaults are kept and what they change. Without that file the program uses the values shipped with it.")
        lay.addWidget(self.info)
        self.tabs = QTabWidget()
        self.tabs.setToolTip("Libraries are tables of materials (they appear in the lists of the program); the last tab holds the values a new board, a new element and a new project start with.")
        lay.addWidget(self.tabs, 1)
        self.tables, self.widgets = {}, {}
        for lib in defaults.LIBRARIES:
            self.tabs.addTab(self._library_tab(lib), LIBRARY_TITLES[lib])
        self.tabs.addTab(self._defaults_tab(), "Defaults for new projects")
        self.tabs.addTab(self._calculator_tab(), "Power calculator")
        row = QHBoxLayout()
        self.save_btn = QPushButton("Save as my defaults")
        self.save_btn.setToolTip("Write what differs from the shipped defaults to the user file. New projects and the lists of the forms use it from now on.")
        self.reset_btn = QPushButton("Reset to shipped")
        self.reset_btn.setToolTip("Delete the user file: every default and library goes back to the values shipped with the program.")
        self.folder_btn = QPushButton("Open folder")
        self.folder_btn.setToolTip("Open the configuration folder with the user file (and, if you put one there, your own stackups.json).")
        self.export_btn = QPushButton("Export…")
        self.export_btn.setToolTip("Save a copy of the user's defaults file to share it with someone else.")
        self.import_btn = QPushButton("Import…")
        self.import_btn.setToolTip("Replace the user's defaults by a file someone shared (it is checked first).")
        for b in (self.save_btn, self.reset_btn, self.folder_btn, self.export_btn, self.import_btn):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.button(QDialogButtonBox.Close).setToolTip("Close the window.")
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        self.save_btn.clicked.connect(self.save)
        self.reset_btn.clicked.connect(self.reset)
        self.folder_btn.clicked.connect(lambda: self._open_folder())
        self.export_btn.clicked.connect(self.export_file)
        self.import_btn.clicked.connect(self.import_file)
        self._refresh_info()

    # ------------------------------------------------------------------ tabs
    def _library_tab(self, lib):
        """!
        @brief A table that edits one library.
        @param lib Library name.
        @return QWidget.
        """
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel(LIBRARY_TIPS[lib])
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: gray;")
        lay.addWidget(note)
        rows = self.data["libraries"][lib]
        cols = list(defaults.shipped()["libraries"][lib][0].keys())
        t = QTableWidget(len(rows), len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setToolTip(LIBRARY_TIPS[lib])
        for r, e in enumerate(rows):
            for c, key in enumerate(cols):
                t.setItem(r, c, QTableWidgetItem(str(e.get(key, ""))))
        t.resizeColumnsToContents()
        t.horizontalHeader().setStretchLastSection(True)
        t.itemChanged.connect(lambda _item, lib=lib: self._read_table(lib))
        self.tables[lib] = (t, cols)
        lay.addWidget(t, 1)
        row = QHBoxLayout()
        add = QPushButton("Add row")
        add.setToolTip("Add an entry at the end: give it a name and its values.")
        rem = QPushButton("Delete row")
        rem.setToolTip("Remove the selected entry from the list (a shipped entry comes back with Reset).")
        add.clicked.connect(lambda _c=False, lib=lib: self._add_row(lib))
        rem.clicked.connect(lambda _c=False, lib=lib: self._delete_row(lib))
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        lay.addLayout(row)
        return w

    def _defaults_tab(self):
        """!
        @brief One tab with the four groups of defaults (new board, new elements, materials, solver), each in its own box.
        @return QWidget.
        """
        from PySide6.QtWidgets import QGroupBox, QScrollArea
        host = QWidget()
        lay = QVBoxLayout(host)
        for section in ("new_board", "new_elements", "materials", "solver"):
            box = QGroupBox(SECTION_TITLES[section])
            box.setToolTip(SECTION_HINTS[section])
            inner = QVBoxLayout(box)
            inner.addWidget(self._section_tab(section))
            lay.addWidget(box)
        lay.addStretch(1)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(host)
        return area

    def _calculator_tab(self):
        """!
        @brief The tab of the power calculator: how uncertain each input is (the band best case / nominal / worst case).
        @return QWidget.
        """
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel("The Power calculator gives a best case, a nominal and a worst case power. Each source of doubt is moved alone to both ends of its uncertainty (±, below) "
                      "and the effects are added as the root of the sum of squares. Change the percentages to what you know about your board and your measurement.")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: gray;")
        note.setToolTip(SECTION_HINTS["calculator"])
        lay.addWidget(note)
        lay.addWidget(self._section_tab("calculator"))
        lay.addStretch(1)
        return w

    def _section_tab(self, section):
        """!
        @brief A form that edits one section of scalar defaults.
        @param section One of new_board, new_elements, materials, solver.
        @return QWidget.
        """
        w = QWidget()
        f = QFormLayout(w)
        values = self.data[section]
        lib_names = {"via_fill": [e["name"] for e in self.data["libraries"]["via_fills"]], "block_metal": [e["name"] for e in self.data["libraries"]["metals"]],
                     "block_interface": [e["name"] for e in self.data["libraries"]["interfaces"]]}
        for key, val in values.items():
            if key == "models":
                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                boxes = {}
                for m in MODELS:
                    c = QCheckBox(m)
                    c.setChecked(m in val)
                    c.setToolTip(TIPS["models"])
                    c.toggled.connect(lambda _on, section=section: self._read_models(section))
                    boxes[m] = c
                    rl.addWidget(c)
                self.widgets[(section, key)] = boxes
                f.addRow(key, row)
                continue
            if key in CHOICES or key in lib_names:
                wdg = QComboBox()
                for item in (CHOICES.get(key) or lib_names[key]):
                    wdg.addItem(item)
                if str(val) not in [wdg.itemText(i) for i in range(wdg.count())]:
                    wdg.addItem(str(val))
                wdg.setCurrentText(str(val))
                wdg.currentTextChanged.connect(lambda text, section=section, key=key: self._set(section, key, text))
            elif isinstance(val, bool):
                wdg = QCheckBox()
                wdg.setChecked(val)
                wdg.toggled.connect(lambda on, section=section, key=key: self._set(section, key, bool(on)))
            elif isinstance(val, int):
                wdg = QSpinBox()
                wdg.setRange(0, 100000)
                wdg.setValue(val)
                wdg.valueChanged.connect(lambda v, section=section, key=key: self._set(section, key, int(v)))
            else:
                wdg = QDoubleSpinBox()
                wdg.setRange(-1e9, 1e9)
                wdg.setDecimals(4)
                wdg.setValue(float(val))
                wdg.valueChanged.connect(lambda v, section=section, key=key: self._set(section, key, float(v)))
            wdg.setToolTip(TIPS.get(key, key))
            self.widgets[(section, key)] = wdg
            f.addRow(key, wdg)
        return w

    # ------------------------------------------------------------------ editing
    def _set(self, section, key, value):
        """!
        @brief Store one scalar of the working copy.
        @param section Section name.
        @param key Key inside the section.
        @param value New value.
        """
        self.data[section][key] = value

    def _read_models(self, section):
        """!
        @brief Store the models ticked in the solver tab.
        @param section "solver".
        """
        boxes = self.widgets[(section, "models")]
        chosen = [m for m, c in boxes.items() if c.isChecked()]
        self.data[section]["models"] = chosen or ["fvm"]

    def _read_table(self, lib):
        """!
        @brief Read a library table back into the working copy (numbers where the shipped entry has numbers; rows without a name are ignored).
        @param lib Library name.
        """
        t, cols = self.tables[lib]
        sample = defaults.shipped()["libraries"][lib][0]
        rows = []
        for r in range(t.rowCount()):
            entry = {}
            for c, key in enumerate(cols):
                item = t.item(r, c)
                text = item.text().strip() if item else ""
                if isinstance(sample[key], (int, float)):
                    try:
                        entry[key] = float(text)
                    except ValueError:
                        entry[key] = float(sample[key])
                else:
                    entry[key] = text
            if entry.get("name"):
                rows.append(entry)
        names = [e["name"] for e in rows]
        if len(set(names)) == len(names) and rows:
            self.data["libraries"][lib] = rows

    def _add_row(self, lib):
        """!
        @brief Append an empty entry to a library table.
        @param lib Library name.
        """
        t, cols = self.tables[lib]
        sample = defaults.shipped()["libraries"][lib][0]
        t.blockSignals(True)
        r = t.rowCount()
        t.insertRow(r)
        for c, key in enumerate(cols):
            t.setItem(r, c, QTableWidgetItem("New entry" if key == "name" else ("1.0" if isinstance(sample[key], (int, float)) else "")))
        t.blockSignals(False)
        self._read_table(lib)

    def _delete_row(self, lib):
        """!
        @brief Remove the selected rows of a library table (at least one stays).
        @param lib Library name.
        """
        t, _ = self.tables[lib]
        rows = sorted({i.row() for i in t.selectedIndexes()}, reverse=True)
        for r in rows:
            if t.rowCount() > 1:
                t.removeRow(r)
        self._read_table(lib)

    # ------------------------------------------------------------------ files
    def _refresh_info(self):
        """!
        @brief Show where the user file is and what it changes.
        """
        text = defaults.diff_text()
        path = defaults.user_file()
        self.info.setText(f"User file: <code>{path}</code> — " + (f"in use, it changes {text}." if text else "not in use: the shipped defaults apply."))

    def save(self):
        """!
        @brief Write the user file with the differences, refresh the libraries and report.
        """
        defaults.save_user(self.data)
        self._after_change()

    def reset(self):
        """!
        @brief Delete the user file after asking.
        """
        if defaults.has_user_file() and QMessageBox.question(self, "Reset to shipped", "Delete your defaults file and go back to the shipped values?") != QMessageBox.Yes:
            return
        defaults.reset_user()
        self._after_change()
        self.data = defaults.load()
        for lib, (t, cols) in self.tables.items():
            t.blockSignals(True)
            t.setRowCount(len(self.data["libraries"][lib]))
            for r, e in enumerate(self.data["libraries"][lib]):
                for c, key in enumerate(cols):
                    t.setItem(r, c, QTableWidgetItem(str(e.get(key, ""))))
            t.blockSignals(False)
        for (section, key), wdg in self.widgets.items():
            val = self.data[section][key]
            if isinstance(wdg, dict):
                for m, c in wdg.items():
                    c.setChecked(m in val)
            elif isinstance(wdg, QComboBox):
                wdg.setCurrentText(str(val))
            elif isinstance(wdg, QCheckBox):
                wdg.setChecked(bool(val))
            else:
                wdg.setValue(val)

    def _after_change(self):
        """!
        @brief Reload the libraries of the model in place and refresh the message.
        """
        model.reload_libraries()
        self.saved = True
        self._refresh_info()

    def _open_folder(self):
        """!
        @brief Open the configuration folder in the file manager (created if needed).
        """
        os.makedirs(defaults.user_dir(), exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(defaults.user_dir()))

    def export_file(self):
        """!
        @brief Save a copy of the user's defaults (the current working copy's differences) to a file chosen by the user.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Export my defaults", "my_defaults.json", "JSON (*.json)")
        if not path:
            return
        import json
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(defaults.diff(self.data), fh, indent=2, ensure_ascii=False)

    def import_file(self):
        """!
        @brief Replace the user's defaults by a shared file after checking that it merges into valid defaults.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Import defaults", "", "JSON (*.json)")
        if not path:
            return
        import json
        try:
            with open(path, encoding="utf-8") as fh:
                over = json.load(fh)
            merged = defaults.merged(over)                          # Fails here, before anything is written, if the structure is wrong
            for lib in defaults.LIBRARIES:
                for e in merged["libraries"][lib]:
                    e["name"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "Import defaults", f"That file is not a valid defaults file: {exc}")
            return
        os.makedirs(defaults.user_dir(), exist_ok=True)
        shutil.copyfile(path, defaults.user_file())
        self._after_change()
        self.accept()
