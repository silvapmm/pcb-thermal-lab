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
LAYER_TIPS = {
    "editor": "Layer that new zones and heaters go on (others faded); also the layer of the board map and the Results maps.",
    "profile page": "Copper layer; the same choice as in the editor and the Results maps.",
    "temperature": "Layer of the Temperature map: all side by side, all in 2 x 2, one layer or the metal block. A single layer is also the drawing layer.",
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
    "lumped rings": "Rings of each heater's thermal network. Rings under one cell are merged: 10 is enough.",
    "analytic modes": "Cosine modes per direction of the analytical series (more resolve smaller parts).",
    "local via and heatsink corrections": "Apply vias and heatsinks locally in the analytical model (Green function) instead of smearing them.",
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
