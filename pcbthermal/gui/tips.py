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

TIPS = {
    # Board
    "ambient": "Air temperature around the board in °C. Every temperature is a rise above it.",
    "orientation": "Board orientation for the computed convection: horizontal (face up) or vertical (plate correlation with the board height).",
    "edges lose heat": "Let the four board edges exchange heat with the air through the edge coefficient (a thin strip next to the copper). Off = insulated edges.",
    "h edges": "Heat transfer coefficient of the board edges in W/m²K (convection plus radiation).",
    # Simulation
    "cell size": "Size of a solver cell in millimetres. Smaller is more accurate and slower; the number of unknowns is shown below. Auto picks a quarter of the smallest part.",
    "fvm solver": "How the finite-volume system is solved: sparse direct (exact, default), conjugate gradients, or SOR (to compare; slow).",
    "lumped rings": "Number of rings of the thermal network of each heater (thermal resistance steps by distance from the footprint).",
    "analytic modes": "Cosine modes per direction of the analytical series (more modes resolve smaller parts).",
    "local via and heatsink corrections": "Apply the vias and heatsinks locally in the analytical model (Green-function update) instead of smearing them over the board.",
    "hotspot limit": "Temperature in °C above which an area is reported as a hotspot and outlined in the temperature map.",
    # Elements
    "name": "Label of the element, shown on the board, in the list and in the reports.",
    "layer": "Copper layer of the element (1 = top). Heatsinks are only on the top or the bottom layer.",
    "x": "Horizontal position in millimetres from the board's lower-left corner.",
    "y": "Vertical position in millimetres from the board's lower-left corner.",
    "width": "Width of the rectangle along x in millimetres.",
    "height": "Height of the rectangle along y in millimetres.",
    "power": "Power dissipated by the part in watts. With a power profile this is the average.",
    "diameter": "Finished hole diameter of the via in millimetres; the plating thickness is in the Board panel.",
    "filled with copper": "A via filled with copper (solid rod) instead of a hollow plated barrel: much more conductive.",
    "block material": "Metal of the block pressed on the board (a preset sets the conductivity below; Custom keeps your value).",
    "block k": "Thermal conductivity of the metal block in W/mK.",
    # Power profile page
    "profile": "Power of the part in time: constant, square wave, or a table from a CSV file.",
    "repeats every": "Period of the square wave (choose the unit on the left, or the frequency).",
    "duty (time on)": "Fraction of every period spent at the on-state power, in percent.",
    "power while on": "Power during the on part of the period, in watts.",
    "power while off": "Power during the off part of the period, in watts (0 for a pure on/off wave).",
    "enter the average power instead of the power while on": "Type the average power and let the program compute the on-state power from the duty.",
    "average power": "Mean power over a period in watts: what the steady-state models use.",
    "repeat the table (otherwise it runs once and the last power is held)": "Repeat the power table every cycle, or run it once and hold the last power.",
    "start from": "Initial state of the time simulation: the steady state of the average power, or a temperature you type.",
    "initial temperature": "Temperature in °C of the whole board at t = 0 (when starting from a typed temperature).",
    "simulate": "How long the time simulation runs: until the cycle repeats, a number of cycles, or a fixed time.",
    "cycles": "Number of power cycles to simulate.",
    "time": "Duration of the time simulation in seconds.",
    "step limit": "Largest number of time steps (a guard against a run that would take too long).",
    "steady-state models use": "Power the steady-state models take for a part with a profile: its average, its on-state peak or its first power.",
    # Results and animation
    "duration": "Length of the animated power step in seconds.",
    "frames": "Number of frames computed.",
    "model": "Model whose result is shown.",
    "scheme": "Time stepping scheme: implicit Euler (robust) or Crank-Nicolson (more accurate).",
    "spacing": "Spacing of the frames in time: logarithmic (more frames early) or uniform.",
    "colour map": "Colour scale of the map.",
    "axis": "Direction of the cut through the board.",
    "position": "Position of the cut in millimetres.",
    "layer ": "Layer shown.",
    "hotspot contour": "Draw the contour at the hotspot limit on the map.",
    "auto range": "Scale the colours to the temperatures of the picture; off = type the limits.",
    "min": "Lowest temperature of the colour scale in °C.",
    "max": "Highest temperature of the colour scale in °C.",
    "compute": "Compute the animation of the power step (runs in the background; cancel with Ctrl+.).",
    "play": "Play or pause the animation.",
    "export gif…": "Save the animation as a GIF file.",
    "speed": "Playback speed in frames per second.",
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
