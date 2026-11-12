#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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

from PySide6.QtCore import QEvent, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                               QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QToolTip, QListWidget, QStackedWidget, QVBoxLayout, QWidget)

from .. import defaults, memory
from .. import model
from .. import package
from ..gerber import limits
from ..numfmt import eng, num
from . import theme as th
from . import tips


def _cell_text(value):
    """!
    @brief Text of a library table cell: a number in plain decimal or engineering notation (never "1e-05"), anything else as it is.
    @param value Cell value (number or text).
    @return str Text shown in the cell; reads back with float().
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        text = num(value, 9)
        if "E" in text and float(text) != float(value):   # Engineering notation with two decimals would change the stored number: keep its digits
            text = eng(value, 8)
        return text
    return str(value)


class _LibraryTable(QTableWidget):
    """!
    @brief Table of a library whose columns share the width: a cell whose text does not fit (elided) shows its full text as the tooltip;
           elsewhere the table's own tooltip (what the library is) is shown.
    """

    def viewportEvent(self, event):
        """!
        @brief Show the full text of an elided cell on a tooltip event.
        @param event The viewport event.
        @return bool True when the event was handled here.
        """
        if event.type() == QEvent.ToolTip:
            item = self.itemAt(event.pos())
            if item is not None and item.text():
                rect = self.visualItemRect(item)
                if self.fontMetrics().horizontalAdvance(item.text()) > rect.width() - 6:        # Elided: the cell text minus its margins
                    QToolTip.showText(event.globalPos(), item.text(), self.viewport(), rect)
                    return True
        return super().viewportEvent(event)


SECTION_LIST_WIDTH = 240          # Pixels: wide enough for the longest section title

LIBRARY_TITLES = {"via_fills": "Via fills", "metals": "Metals (heatsink blocks)", "interfaces": "Interface materials", "dielectrics": "Dielectrics (stack-up)",
                  "package_theta": "Package families (typical θ)", "heatsinks": "Package heatsinks (typical θSA)"}
LIBRARY_TIPS = {"via_fills": "Via barrel fills: the name is listed in the via's Fill box, k (W/mK) is its typical value.",
                "metals": "Metals of a heatsink block: conductivity (W/mK) and volumetric heat capacity (J/m³K).",
                "interfaces": "Pastes and gap pads: apparent k (W/mK) and thickness (mm); R = thickness / k.",
                "dielectrics": "Stack-up dielectrics: k across and along the plane (W/mK), density (kg/m³), specific heat (J/kgK).",
                "package_theta": "Typical θ junction-pad, θJC(top) (K/W) and Tj max (°C) per package family: a starting value, not the datasheet.",
                "heatsinks": "Package-top heatsinks with catalogue θSA (K/W), source and test conditions: a starting value; yours depends on air flow and mounting."}
SECTION_TITLES = {"new_board": "New board", "new_elements": "New elements", "materials": "Materials of a new board", "calculator": "Power Calculator", "solver": "Solver of a new project", "gerber": "Gerber import (this machine)", "package": "Project package (this machine)"}
SECTION_HINTS = {"new_board": "Values of a board from File - New board (and at start-up).",
                 "new_elements": "Values of an element drawn or added from the right-click menu.",
                 "materials": "Copper and simple-stack-up dielectric of a new board (advanced dielectrics: a library).",
                 "calculator": "Uncertainty of the Power Calculator inputs: each is moved to both ends, effects added as root sum of squares.",
                 "solver": "The models and settings a new project starts with.",
                 "gerber": "Gerber reader limits; this machine only, not saved in project files.",
                 "package": "Size limit of a .pcbtz package; this machine only, not saved in project files."}
MACHINE_NOTES = {"solver": "The models and settings a new project starts with, and the memory limit of this machine. The memory limit is a machine preference: "
                           "it is not saved in project files.",
                 "gerber": "Limits of the Gerber reader. A machine preference: not saved in project files.",
                 "package": "Size limit of a project package. A machine preference: not saved in project files."}
# Shown under the package page when the limit is above the shipped 512 MB
PACKAGE_MEMORY_NOTE = ("Above 512 MB: the whole package is held in memory while it is read and written (the files it holds, their compressed copy and the project), "
                       "so a package of this size needs several times its size in free memory.")
CHOICES = {"heater_kind": ("source", "component"), "h_mode": ("manual", "computed"), "orientation": ("horizontal", "vertical"), "natural_form": ("general", "laminar"), "linear_solver": ("direct", "cg", "sor"), "design_level": ("none", "cad", "hand", "estimated")}
MODELS = ("fvm", "lumped", "analytic", "fdm", "solid3d")
# Labels with units for the fields of the defaults (the JSON key, which a hand-edited file uses, is given in each tooltip)
LABELS = {
    "width_mm": "Width (mm)", "height_mm": "Height (mm)", "layers": "Copper layers", "ambient_c": "Ambient (°C)", "h_top": "h top (W/m²K)",
    "h_bottom": "h bottom (W/m²K)", "edges_lose_heat": "Edges lose heat", "h_side": "h edges (W/m²K)", "via_plating_um": "Via plating (µm)",
    "h_mode": "Heat transfer", "emissivity_top": "Emissivity top", "emissivity_bottom": "Emissivity bottom", "orientation": "Orientation",
    "natural_form": "Vertical natural convection", "air_speed": "Air speed (m/s)", "h_calibration": "Convection ×",
    "heater_power_w": "Heater power (W)", "heater_kind": "Heater type", "heater_size_mm": "Heater size (mm)", "zone_fill": "Zone copper fill (0 to 1)",
    "zone_size_mm": "Zone size (mm)", "via_diameter_mm": "Via diameter (mm)", "via_fill": "Via fill", "heatsink_h_extra": "Heatsink extra h (W/m²K)",
    "heatsink_size_mm": "Heatsink size (mm)", "block_thickness_mm": "Block thickness (mm)", "block_metal": "Block metal", "block_interface": "Block interface",
    "k_copper": "Copper k (W/mK)", "rho_copper": "Copper density (kg/m³)", "cp_copper": "Copper specific heat (J/kgK)",
    "k_fr4_through": "Dielectric k through (W/mK)", "k_fr4_inplane": "Dielectric k in-plane (W/mK)", "rho_fr4": "Dielectric density (kg/m³)",
    "cp_fr4": "Dielectric specific heat (J/kgK)",
    "copper_uncertainty_pct": "Copper (± %)", "h_uncertainty_pct": "Heat transfer h (± %)", "theta_uncertainty_pct": "θ junction-pad (± %)",
    "psi_jt_uncertainty_pct": "ψJT (± %)", "reading_uncertainty_k": "Temperature reading (± K)", "design_level": "Board description",
    "design_coverage_pct": "Design: copper coverage (± %)", "design_weight_pct": "Design: copper weight (± %)", "design_planes_pct": "Design: inner planes (± %)",
    "design_vias_pct": "Design: vias (± %)", "design_scale_cad": "Multiplier, fabrication files", "design_scale_hand": "Multiplier, drawn by hand",
    "design_scale_estimated": "Multiplier, estimated",
    "models": "Models", "cell_mm": "Cell size (mm)", "linear_solver": "FVM solver", "lumped_rings": "Lumped rings", "analytic_modes": "Analytic modes",
    "hotspot_c": "Hotspot limit (°C)", "memory_fraction": "Memory limit (fraction of the physical memory)", "max_file_mb": "Largest Gerber or drill file (MB)", "max_mb": "Largest package (MB)",
}
# Column titles with units for the library tables (the JSON key is in the tooltip of the column title)
COLUMNS = {"name": "Name", "note": "Note", "k_w_per_mk": "k (W/mK)", "rho_cp_j_per_m3k": "ρ·cp (J/m³K)", "thickness_mm": "Thickness (mm)",
           "k_through": "k through (W/mK)", "k_inplane": "k in-plane (W/mK)", "rho": "Density (kg/m³)", "cp": "Specific heat (J/kgK)",
           "theta_k_per_w": "θ junction-pad (K/W)", "theta_jc_top_k_per_w": "θJC top (K/W)", "tj_max_c": "Tj max (°C)", "heatsink": "Heatsink",
           "flow": "Air flow", "theta_sa_k_per_w": "θSA (K/W)"}
TIPS = {
    "width_mm": "Width of a new board, mm.", "height_mm": "Height of a new board, mm.", "layers": "Copper layers of a new board.",
    "ambient_c": "Ambient temperature of a new board, °C.", "h_top": "Typed top-face h, W/m²K.",
    "h_bottom": "Typed bottom-face h, W/m²K.", "edges_lose_heat": "Whether the edges exchange heat with the air.",
    "h_side": "Edge h, W/m²K.", "via_plating_um": "Via barrel plating, µm.",
    "h_mode": "Face h typed, or computed (convection and radiation).", "emissivity_top": "Emissivity of the top face (0 to 1).",
    "emissivity_bottom": "Emissivity of the bottom face (0 to 1).", "orientation": "Mounting of the board for the computed coefficients.",
    "natural_form": "Vertical-board natural convection: general (Churchill and Chu) or laminar (Ra below 1.00E9); under 1 % on the example.",
    "air_speed": "Air speed along the board, m/s (computed h).", "h_calibration": "Multiplier of the computed convection.",
    "heater_power_w": "Power of a new heater in W.", "heater_kind": "A new heater: heat source (power only) or component (junction, package, top path).", "heater_size_mm": "Side of a heater added from the right-click menu, mm.",
    "zone_fill": "Copper fill (0 to 1) of a new zone.", "zone_size_mm": "Side of a zone added from the right-click menu, mm.",
    "via_diameter_mm": "Hole diameter of a new via, mm.", "via_fill": "Fill of a new via (from the via fills library).",
    "heatsink_h_extra": "Extra h of a new heatsink, W/m²K.", "heatsink_size_mm": "Side of a heatsink added from the right-click menu, mm.",
    "block_thickness_mm": "Thickness of a new metal block, mm.", "block_metal": "Metal of a new block (from the metals library).",
    "block_interface": "Interface of a new block (from the interface library).",
    "k_copper": "Conductivity of copper (W/mK).", "rho_copper": "Density of copper (kg/m³).", "cp_copper": "Specific heat of copper (J/kgK).",
    "k_fr4_through": "Simple-stack-up dielectric k across the board, W/mK.", "k_fr4_inplane": "Simple-stack-up dielectric k along the plane, W/mK.",
    "rho_fr4": "Simple-stack-up dielectric density, kg/m³.", "cp_fr4": "Simple-stack-up dielectric specific heat, J/kgK.",
    "copper_uncertainty_pct": "Uncertainty of the copper thickness of every layer, % (at most 99).",
    "h_uncertainty_pct": "Uncertainty of the heat transfer coefficients, % (correlations: 20 to 30).",
    "theta_uncertainty_pct": "Uncertainty of θ junction-pad, %.",
    "psi_jt_uncertainty_pct": "Uncertainty of the datasheet ψJT, % (it varies with board and air flow).",
    "reading_uncertainty_k": "Error of the temperature reading, K (thermocouple contact, IR emissivity; typically 1 to 3).",
    "design_level": "Default board description in the calculator: none, cad (from fabrication files), hand (from the layout) or estimated.",
    "design_coverage_pct": "Design uncertainty of the outer-layer copper fill at 'estimated', % (hatched drawn solid: 50). Half the top pad: -13 % of power.",
    "design_weight_pct": "Design uncertainty of the copper weight at 'estimated', % (0.5 oz for 1 oz: 50; at most 99). Half the copper: -24 % of power.",
    "design_planes_pct": "Design uncertainty of the inner planes at 'estimated', % (smaller or undrawn). No inner planes: -34 % of power.",
    "design_vias_pct": "Design uncertainty of the via barrel copper at 'estimated', %. No vias under the part: -11 % of power.",
    "design_scale_cad": "Design multiplier for a board from fabrication files (0 to 1; assumed).",
    "design_scale_hand": "Design multiplier for a board drawn by hand (0 to 1; assumed).",
    "design_scale_estimated": "Design multiplier for an estimated board (normally 1).",
    "models": "Models selected in a new project.", "cell_mm": "Cell size in mm.", "linear_solver": "Solver of the FVM linear system.",
    "lumped_rings": "Rings of the Lumped model.", "analytic_modes": "Cosine modes of the Analytic model.", "hotspot_c": "Hotspot limit, °C.",
    "max_file_mb": "Largest Gerber, drill or ZIP member read, MB (16 to 4096, shipped 256; real files 0.01 to 2 MB). Decoding takes about twice the file in memory. "
                   "This machine only: not saved in project files.",
    "max_mb": "Largest .pcbtz package read or written, MB uncompressed (64 to 4096, shipped 512; real ones under 10 MB). It is held in memory whole. "
              "This machine only: not saved in project files.",
    "memory_fraction": "Share of physical memory a solve may use (0.10 to 0.95, shipped 0.60); an FVM, FDM or 3D run estimated above it is refused, with the cell that fits. "
                       "This machine only: not saved in project files. PCBTHERMAL_MEMORY_BYTES sets the memory when it cannot be read.",
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
        self.resize(980, 600)                                      # The list of sections takes 240 px; the Defaults page needs the rest
        self.data = defaults.load()                         # The working copy: shipped plus the user's file
        self.saved = False                                  # True once Save or Reset changed the files
        lay = QVBoxLayout(self)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.RichText)
        self.info.setToolTip("Where your defaults are kept; without that file the shipped values are used.")
        lay.addWidget(self.info)
        # The sections are a list on the left and their pages are stacked on the right (as tabs they needed scroll arrows in a narrow window)
        self.sections = QListWidget()
        self.sections.setObjectName("sections")
        self.sections.setFixedWidth(SECTION_LIST_WIDTH)
        self.sections.setTextElideMode(Qt.ElideNone)
        # No tooltip on the list: the section names say it all (the maintainer found the old one added nothing); the controls of the pages keep theirs
        self.pages = QStackedWidget()
        body = QHBoxLayout()
        body.addWidget(self.sections)
        body.addWidget(self.pages, 1)
        lay.addLayout(body, 1)
        self.tables, self.widgets = {}, {}
        for lib in defaults.LIBRARIES:
            self._add_section(LIBRARY_TITLES[lib], self._library_tab(lib))
        self._add_section("Defaults for new projects", self._defaults_tab())
        # Solver and Gerber import have their own sections (they sat at the bottom of the long defaults page, hard to find)
        self._add_section("Solver", self._machine_tab("solver"))
        self._add_section("Gerber import", self._machine_tab("gerber"))
        self._add_section("Project package", self._machine_tab("package"))
        self._add_section("Power Calculator", self._calculator_tab())
        self.sections.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sections.setCurrentRow(0)                      # The first page is shown
        self.sections.setFocus()                            # Up and Down change the page from the start
        row = QHBoxLayout()
        self.save_btn = QPushButton("Save as my defaults")
        self.save_btn.setToolTip("Save your changes as the defaults for new projects.")
        self.reset_btn = QPushButton("Reset to shipped")
        self.reset_btn.setToolTip("Delete your defaults: back to the shipped values.")
        self.folder_btn = QPushButton("Open folder")
        self.folder_btn.setToolTip("Open the configuration folder.")
        self.export_btn = QPushButton("Export…")
        self.export_btn.setToolTip("Save a copy of your defaults to share.")
        self.import_btn = QPushButton("Import…")
        self.import_btn.setToolTip("Replace your defaults with a shared file.")
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

    def _add_section(self, title, page):
        """!
        @brief Add a section: an entry of the list and its page.
        @param title Name of the section shown in the list.
        @param page Widget with the controls of the section.
        """
        self.sections.addItem(title)
        self.pages.addWidget(page)

    def section_titles(self):
        """!
        @brief Names of the sections, in the order of the list.
        @return List of str.
        """
        return [self.sections.item(i).text() for i in range(self.sections.count())]

    # ------------------------------------------------------------------ pages
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
        th.hint(note)
        lay.addWidget(note)
        rows = self.data["libraries"][lib]
        cols = list(defaults.shipped()["libraries"][lib][0].keys())
        t = _LibraryTable(len(rows), len(cols))
        t.setHorizontalHeaderLabels([COLUMNS.get(c, c) for c in cols])          # Readable titles with units, not the JSON keys
        for c, key in enumerate(cols):
            t.horizontalHeaderItem(c).setToolTip(f"JSON key: {key}")
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setToolTip(LIBRARY_TIPS[lib])
        for r, e in enumerate(rows):
            for c, key in enumerate(cols):
                t.setItem(r, c, QTableWidgetItem(_cell_text(e.get(key, ""))))
        # Columns share the width so that the table never scrolls sideways (number-width columns overflowed the Dielectrics page at 800 px);
        # a cell that does not fit is elided and shows its full text as the tooltip (_LibraryTable)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.horizontalHeader().setMinimumSectionSize(24)
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        t.itemChanged.connect(lambda _item, lib=lib: self._read_table(lib))
        self.tables[lib] = (t, cols)
        lay.addWidget(t, 1)
        row = QHBoxLayout()
        add = QPushButton("Add row")
        add.setToolTip("Add an entry: give it a name and values.")
        rem = QPushButton("Delete row")
        rem.setToolTip("Remove the selected entry (Reset restores shipped ones).")
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
        for section in ("new_board", "new_elements", "materials"):
            box = QGroupBox(SECTION_TITLES[section])
            box.setToolTip(SECTION_HINTS[section])
            inner = QVBoxLayout(box)
            inner.addWidget(self._section_tab(section))
            lay.addWidget(box)
        lay.addStretch(1)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)       # The page scrolls vertically only; its content is laid out to fit the width
        area.setWidget(host)
        return area

    def _machine_tab(self, section):
        """!
        @brief A page of its own for the Solver, Gerber import or Project package settings, with a header line.
        @param section "solver", "gerber" or "package".
        @return QWidget (a scroll area that never scrolls sideways).
        """
        from PySide6.QtWidgets import QScrollArea
        host = QWidget()
        lay = QVBoxLayout(host)
        note = QLabel(MACHINE_NOTES[section])
        note.setWordWrap(True)
        th.hint(note)
        note.setToolTip(SECTION_HINTS[section])
        lay.addWidget(note)
        lay.addWidget(self._section_tab(section))
        if section == "package":
            # The memory note appears only above the shipped limit; it follows the field
            self.package_note = QLabel(PACKAGE_MEMORY_NOTE)
            self.package_note.setWordWrap(True)
            th.hint(self.package_note)
            self.package_note.setToolTip(TIPS["max_mb"])
            lay.addWidget(self.package_note)
            self._refresh_package_note()
        lay.addStretch(1)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(host)
        return area

    def _calculator_tab(self):
        """!
        @brief The tab of the power calculator: how uncertain each input is (the band best case / nominal / worst case).
        @return QWidget.
        """
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel("The Power Calculator gives a best case, a nominal and a worst case power. Each source of doubt is moved alone to both ends of its uncertainty (±, below) "
                      "and the effects are added as the root of the sum of squares. Change the percentages to what you know about your board and your measurement.")
        note.setWordWrap(True)
        th.hint(note)
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
        # A row that does not fit puts its field under the label (two-line form) instead of widening the page: no horizontal scroll bar
        f.setRowWrapPolicy(QFormLayout.WrapLongRows)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        values = self.data[section]
        lib_names = {"via_fill": [e["name"] for e in self.data["libraries"]["via_fills"]], "block_metal": [e["name"] for e in self.data["libraries"]["metals"]],
                     "block_interface": [e["name"] for e in self.data["libraries"]["interfaces"]]}
        for key, val in values.items():
            if key == "models":
                row = QWidget()
                rl = QGridLayout(row)                      # Two columns: the five long model names in one line were wider than the page
                rl.setContentsMargins(0, 0, 0, 0)
                boxes = {}
                for n, m in enumerate(MODELS):
                    c = QCheckBox(tips.model_label(m))
                    c.setChecked(m in val)
                    c.setToolTip(TIPS["models"])
                    c.toggled.connect(lambda _on, section=section: self._read_models(section))
                    boxes[m] = c
                    rl.addWidget(c, n // 2, n % 2)
                self.widgets[(section, key)] = boxes
                f.addRow(LABELS.get(key, key), row)
                continue
            if key in CHOICES or key in lib_names:
                wdg = QComboBox()
                for item in (CHOICES.get(key) or lib_names[key]):
                    wdg.addItem(item)
                if str(val) not in [wdg.itemText(i) for i in range(wdg.count())]:
                    wdg.addItem(str(val))
                wdg.setCurrentText(str(val))
                # The width of a combo box follows its longest item; let it shrink and elide so that a long name never widens the page
                wdg.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
                wdg.setMinimumContentsLength(10)
                wdg.currentTextChanged.connect(lambda text, section=section, key=key: self._set(section, key, text))
            elif isinstance(val, bool):
                wdg = QCheckBox()
                wdg.setChecked(val)
                wdg.toggled.connect(lambda on, section=section, key=key: self._set(section, key, bool(on)))
            elif isinstance(val, int):
                wdg = QSpinBox()
                wdg.setRange(*((limits.MIN_FILE_MB, limits.MAX_FILE_MB) if key == "max_file_mb" else (package.MIN_TOTAL_MB, package.MAX_TOTAL_MB) if key == "max_mb" else (0, 100000)))
                wdg.setValue(val)
                wdg.valueChanged.connect(lambda v, section=section, key=key: self._set(section, key, int(v)))
            else:
                wdg = QDoubleSpinBox()
                # Amplitudes of the design uncertainty and the copper uncertainty stay below 100 %, so a thickness never reaches 0
                wdg.setRange(*((0.0, 99.0) if section == "calculator" and key in ("copper_uncertainty_pct", "design_coverage_pct", "design_weight_pct", "design_planes_pct", "design_vias_pct") else (0.0, 1.0) if key.startswith("design_scale_") else (memory.MIN_FRACTION, memory.MAX_FRACTION) if key == "memory_fraction" else (-1e9, 1e9)))
                # Three decimals for small numbers (a via diameter, an emissivity, a multiplier), one for the large ones: "100,0000 mm" was hard to read.
                # The choice follows the shipped value, not the user's (a user value of 10 W must not take the decimals away from the heater power),
                # and grows to show a saved value in full (a spin box rounds its value to its decimals, and a reset would write the rounded number)
                shipped = defaults.shipped().get(section, {}).get(key, val)
                places = 3 if abs(float(shipped)) < 10 else 1
                while places < 6 and round(float(val), places) != float(val):
                    places += 1
                wdg.setDecimals(places)
                wdg.setValue(float(val))
                wdg.valueChanged.connect(lambda v, section=section, key=key: self._set(section, key, float(v)))
            tip = f"{TIPS.get(key, key)}\nJSON key: {key}"
            if key == "memory_fraction":
                ram = memory.ram_bytes()
                tip += f"\nMemory detected: {ram / memory.GB:.1f} GB (limit now {memory.limit_bytes(float(val), ram) / memory.GB:.1f} GB)." if ram else "\nThe memory of this machine could not be read: a fixed limit is used."
            wdg.setToolTip(tip)
            self.widgets[(section, key)] = wdg
            f.addRow(LABELS.get(key, key), wdg)
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
        if (section, key) == ("package", "max_mb"):
            self._refresh_package_note()

    def _refresh_package_note(self):
        """!
        @brief Show the memory note of the package page only while the limit is above the shipped 512 MB.
        @return None.
        """
        note = getattr(self, "package_note", None)
        if note is not None:
            note.setVisible(float(self.data["package"].get("max_mb", package.DEFAULT_TOTAL_MB)) > package.DEFAULT_TOTAL_MB)

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
        previous = self.data["libraries"][lib]
        rows = []
        for r in range(t.rowCount()):
            entry = {}
            for c, key in enumerate(cols):
                item = t.item(r, c)
                text = item.text().strip() if item else ""
                if isinstance(sample[key], (int, float)):
                    try:
                        entry[key] = float(text.replace(",", "."))      # A decimal comma is read as a point
                    except ValueError:
                        # Not a number: keep the value the row had (it used to become the value of the first shipped entry, silently)
                        old = previous[r].get(key, sample[key]) if r < len(previous) else sample[key]
                        entry[key] = float(old)
                        if item is not None:
                            t.blockSignals(True)
                            item.setText(_cell_text(entry[key]))
                            t.blockSignals(False)
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
                    t.setItem(r, c, QTableWidgetItem(_cell_text(e.get(key, ""))))
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
