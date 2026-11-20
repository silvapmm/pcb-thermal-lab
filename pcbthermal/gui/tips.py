#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file tips.py
@brief Tooltips for every control: one table keyed by the label of the control, applied to a whole panel.
@details Every field, check box, button and combo box of the application explains what it is for when the pointer rests on it. Controls built in code already
         carry their own text; this module adds the text of the controls that are described by their label in a form (the label and the control get the same
         tooltip) and of check boxes and buttons described by their own text. A test (tests/test_tooltips.py) scans the whole application and fails for a control
         without a tooltip.
"""

from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox, QComboBox, QFormLayout, QLabel, QLayout, QLineEdit, QPushButton, QRadioButton, QSlider,
                               QTableWidget, QTreeWidget)

from ..results import MODEL_LABELS, model_label  # noqa: E402,F401  (the names live in the core, the plots use them too)

# The toolbar Layer box is one choice for the editor and every map; its hint depends on where it is used (keys: MainWindow._layer_ctx)
SURFACE_ENTRY_TIP = ("Temperature of the outer face of the copper, what a thermocouple or an IR camera on the metal reads, in steady state: an estimate from the layer "
                     "mean and the heat flowing in and out for the FVM, the FDM and the Analytic, computed from the copper slabs (above 105 µm) or estimated from the links (one slab) for the 3D solid, "
                     "resolved by the elements for the FEM. The LPTN has none. Milli-kelvins from the layer mean on 35 µm copper, "
                     "tenths of a kelvin to percent of the rise on thick metal. The title gives the difference in K and in % of the rise. Maps, tables, Tj and margins use the "
                     "layer mean. On patterned copper the difference includes the rise across the bare laminate under a source.")      # Tooltip of the Layer-box entries Surface (top) and Surface (bottom)

SURFACE_TRAP_TIP = ("On a board with patterned copper the difference includes the rise across the bare laminate under a source; the part's column maximum already includes it, "
                    "so for a part the difference is the copper term only.")

# Tooltips of the columns of the Components table (docs: user guide 'Surface temperature and column mean')
COLUMN_HEADER_TIP = ("Column read-out: the temperature of the node, the mean of the copper through its thickness (plus the laminate face term under a source over absent copper). "
                     "Tables, junction temperature, margin, power limit and top path all use it. The surface column on the right is the outer face (an estimate for the FVM, the FDM, "
                     "the Analytic and the 3D solid on one slab, computed from the copper slabs for the 3D solid above 105 µm, resolved for the FEM), hotter under a source on thick copper.")
SURFACE_MAX_TIP = ("Hottest temperature of the outer face of the copper under the part, in °C; the face is the one the part sits on. FVM and FDM: an estimate from the "
                   "layer mean and the heat fluxes through the faces (layer mean + t (2 q_in - q_out) / (6 k), t and k the thickness and conductivity of the copper); "
                   "'(upper)' marks a part whose narrowest width a (the narrow side, the arm of an L) is small against the plate (t/a above 0.5): the estimate is then high, by about 1.15 (a long part) "
                   "to 1.4 (a square) times at t/a = 1. Analytic: the same estimate from its own field and its uniform conductances (vias, blocks and heatsinks are not in the fluxes; n/a on a face "
                   "with a part over absent copper, where the model has no bare-laminate term). 3D solid: computed from the copper slabs above 105 µm (the half slab above the outer one), an estimate from its "
                   "links on one slab; on a thick plate under a narrow part the computed value is the closer one and the FVM and Analytic parabola the upper estimate (10 mm Al plate: "
                   "13.5 K above the column against 17.1 K). FEM: resolved by "
                   "the elements (the element mean on the face, not an estimate); the tooltip of a cell also gives the hottest mesh node under the part (a node value, not a "
                   "cell mean). Steady state, also on thin copper, where it equals the column at one decimal; hover a cell for the difference in K and in % of the rise and "
                   "for the surface mean. Junction, margin and power limit stay on the column. n/a: the LPTN (it has no heat flux through the face: the hover text gives the through-thickness term "
                   "as a measured upper value, not a temperature), a time simulation, or a part on an inner layer.")
# Tooltips of the other tables of the Components tab and of the Summary table: they name the read-out of their temperatures (every number names its read-out)
COLUMN_TABLE_TIP = ("Column read-out: the temperature of the copper layer in each cell, the mean through its thickness (the layer mean), the read-out of the maps and of the "
                    "part table. The surface of the outer copper is in the Layer box (Surface entries) and in the last column of the part table.")
BLOCK_TABLE_TIP = ("Metal block read-out: the block temperature, the mean through its thickness in each cell (every model, the FEM too: a block has no surface "
                   "read-out); Mean and Max are over the plan of the blocks on that side of the board (Face: top or bottom).")
MODEL_TABLE_TIP = ("One row per model. Tmax (column) and Tmean (all layers) are column read-outs (the copper layer averaged through its thickness); Tmax (surface) is the hottest "
                   "point of the top face of the copper (FVM, FDM, FEM only); ΔT = Tmax (column) - ambient. Hover a column title for its meaning; the bottom face and, for the FEM, "
                   "the hottest mesh node are in the report.")

LAYER_TIPS = {
    "editor": "Layer that new zones and heaters go on (others faded); also the layer of the board map and the Results maps.",
    "profile page": "Copper layer; the same choice as in the editor and the Results maps.",
    "temperature": "Layer of the Temperature map: all side by side, all in 2 × 2, one layer, the metal block, or Surface (top) / Surface (bottom), the outer face of "
                   "the copper (an estimate for the FVM and the FDM, resolved for the FEM; a view of the map only: the tables keep the layer mean). A single layer is also "
                   "the drawing layer.",
    "gradient": "Copper layer of the gradient map, shared with the editor. All layers and the block: Temperature tab only.",
    "animation": "Copper layer of the animation, shared with the editor. All layers and the block: Temperature tab only.",
    "profiles": "Copper layer of the cut or the time maps, shared with the editor. All layers and the block: Temperature tab only.",
    "results": "Copper layer; the same choice as in the editor and the Results maps.",
}

TIPS = {
    # Board
    "ambient": "Air temperature around the board, °C. Results are rises above it.",
    "orientation": "Mounting for the computed convection: horizontal (face up) or vertical (plate correlation, board height).",
    "edges lose heat": "The four edges exchange heat with the air through the edge coefficient. Off = insulated edges.",
    "h edges": "Heat transfer coefficient of the edges, W/m²K (convection plus radiation).",
    # Simulation
    "cell size": "Solver cell, mm. Smaller: more accurate, slower (unknowns shown below). Auto: a quarter of the smallest part.",
    "fvm solver": "Solver of the FVM system: sparse direct (exact, default), conjugate gradients, or SOR (comparison, slow).",
    "lptn rings": "Rings of each heater's thermal network. Rings under one cell are merged: 10 is enough.",
    "analytic modes": "Cosine modes per direction of the analytical series (more resolve smaller parts).",
    "local via and heatsink corrections": "Apply vias and heatsinks locally in the analytical model (Green function) instead of smearing them. Steady run only: the time run (power profiles) always treats vias and heatsinks locally.",
    "hotspot limit": "Temperature, °C, above which an area is a hotspot (outlined on the map).",
    # Elements
    "name": "Label of the element on the board, in the list and in the reports.",
    "layer": "Copper layer (1 = top). Heatsinks: top or bottom layer only.",
    "x": "Horizontal position, mm from the board's lower-left corner.",
    "y": "Vertical position, mm from the board's lower-left corner.",
    "width": "Width of the rectangle along x, mm.",
    "height": "Height of the rectangle along y, mm.",
    "power": "Power dissipated by the part, W. With a power profile: the average.",
    "drill diameter": "Drill diameter of the via, mm. The plating is inside it (finished hole = drill − 2 × plating; plating in Stack-up, Materials).",
    "fill": "Barrel fill: open, epoxy resin (usual filled via, almost no heat), conductive paste (+5 %) or plated copper (3.3 × the plating).",
    "block material": "Metal of the block (a preset sets k below; Custom keeps your value).",
    "cooling model": "Manual input (h or datasheet θSA) or a metal block the program computes (spreading, interface, fins; FVM/FDM also in time).",
    "block thickness": "Thickness of the metal block, mm (plates 1 to 10). Thickness and area matter more than the metal.",
    "fin height": "Fin height, mm (0 = plain plate; extrusions 10 to 50). Fin efficiency applied.",
    "fin thickness": "Thickness of one fin, mm (extrusions 0.5 to 3).",
    "fin pitch": "Fin axis spacing, mm. Gap = pitch − thickness; a narrow gap in still air chokes convection (warned after the run, not modelled).",
    "block k": "Conductivity of the block, W/mK (aluminium 204, copper 386, brass 111, steel 54, stainless 14).",
    # Power profile page
    "profile": "Power of the part in time: constant, square wave, or a CSV table.",
    "repeats every": "Period of the square wave (unit on the left, or the frequency).",
    "duty (time on)": "Share of the period at the on power, %. Average = on power × duty.",
    "power while on": "Power during the on part of the period, W.",
    "power while off": "Power during the off part of the period, W (0 = pure on/off).",
    "type the average power": "Type the average power instead; the on power follows from the duty.",
    "average power": "Mean power over a period, W: what the steady-state models use.",
    "repeat the table": "Repeat the table every cycle; unticked, it runs once and holds the last power.",
    "start from": "Initial state: the steady state of the average power, or a typed temperature.",
    "initial temperature": "Temperature of the whole board at t = 0, °C (typed start).",
    "simulate": "Run length: until the cycle repeats, a number of cycles, or a fixed time.",
    "cycles": "Number of power cycles to simulate.",
    "time": "Duration of the time simulation, s.",
    "step limit": "Most time steps (a guard against a very long run).",
    "steady-state models use": "Power the steady-state models take for a profiled part: average, on peak or first power.",
    # Results and animation
    "duration": "Length of the animated power step, s.",
    "frames": "Number of frames computed.",
    "model": "Model whose result is shown.",
    "scheme": "Time stepping: implicit Euler (robust) or Crank-Nicolson (more accurate).",
    "spacing": "Frame spacing in time: logarithmic (more frames early) or uniform.",
    "colour map": "Colour scale of the map.",
    "axis": "Direction of the cut through the board.",
    "position": "Position of the cut, mm.",
    "layer ": "Layer shown.",
    "hotspot contour": "Draw the hotspot-limit contour on the map.",
    "auto range": "Scale the colours to the picture; off = type the limits.",
    "min": "Lowest temperature of the colour scale, °C.",
    "max": "Highest temperature of the colour scale, °C.",
    "compute": "Compute the animation of the power step (cancel: Ctrl+.).",
    "play": "Play or pause the animation.",
    "export gif…": "Save the animation as a GIF file.",
    "speed": "Playback speed, frames per second.",
}


def _widgets(item):
    """!
    @brief The widgets of a layout item (a widget, or the widgets inside a layout).
    @param item QLayoutItem.
    @return List of QWidget.
    """
    if item is None:
        return []
    if item.widget():
        return [item.widget()]
    lay = item.layout()
    out = []
    if lay is not None:
        for i in range(lay.count()):
            out += _widgets(lay.itemAt(i))
    return out


def _key(text):
    """!
    @brief Normalised label text.
    @param text Label or button text.
    @return Lower case text without the trailing colon.
    """
    return text.strip().rstrip(":").lower()


def _suffix_key(w):
    """!
    @brief Key of a control without a label: its own text, or its suffix for a spin box.
    @param w The widget.
    @return Normalised text or "".
    """
    if isinstance(w, (QCheckBox, QPushButton, QRadioButton)):
        return _key(w.text().replace("&", ""))
    return ""


def apply(root):
    """!
    @brief Give a tooltip to every control under `root` that has none and whose label or text is in TIPS.
    @param root A QWidget (a panel, a page or a whole window).
    @return Number of tooltips added.
    """
    added = 0
    for form in root.findChildren(QFormLayout):
        for r in range(form.rowCount()):
            li = form.itemAt(r, QFormLayout.LabelRole)
            label = li.widget() if li is not None else None
            text = _key(label.text()) if isinstance(label, QLabel) else ""
            tip = TIPS.get(text)
            fields = _widgets(form.itemAt(r, QFormLayout.FieldRole))
            for w in fields + ([label] if label is not None else []):
                t = tip or TIPS.get(_suffix_key(w), "")
                if t and not w.toolTip():
                    w.setToolTip(t)
                    added += 1
    for kind in (QCheckBox, QPushButton, QRadioButton):
        for w in root.findChildren(kind):
            t = TIPS.get(_suffix_key(w), "")
            if t and not w.toolTip():
                w.setToolTip(t)
                added += 1
    return added


CONTROLS = (QAbstractSpinBox, QComboBox, QCheckBox, QPushButton, QLineEdit, QSlider, QRadioButton, QTableWidget, QTreeWidget)
