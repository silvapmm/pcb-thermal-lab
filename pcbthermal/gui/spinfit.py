#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file spinfit.py
@brief A spin box never clamps silently a value that was loaded from a project: its range grows to hold it.
"""

import math

from PySide6.QtWidgets import QSpinBox

# A QSpinBox holds a C int: a value beyond it cannot be shown at all (PySide raises OverflowError), so the range stops there
INT_MIN, INT_MAX = -(2 ** 31), 2 ** 31 - 1


def fit_range(spin, value):
    """!
    @brief Widen the range of a spin box so that it can hold a value that was loaded from a project, never clamping it.
    @details A box whose range is narrower than the model (a 10 mm copper plate in a box that stops at 210 um) used to show the clamped value and, on the next
             edit of ANY field of the panel, write that clamped value back into the project. The range now follows the loaded value instead. A value that is not a
             finite number is left alone (a project file cannot hold one), and an integer box never grows beyond the C int it stores.
    @param spin QDoubleSpinBox or QSpinBox.
    @param value The value about to be shown, in the unit of the box.
    @return None.
    """
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError):
        return
    if not math.isfinite(v):                                    # NaN or infinity: nothing a box can hold
        return
    if isinstance(spin, QSpinBox):
        # Integer box: whole bounds, inside the C int
        if v > spin.maximum():
            spin.setMaximum(min(INT_MAX, math.ceil(v)))
        if v < spin.minimum():
            spin.setMinimum(max(INT_MIN, math.floor(v)))
        return
    if v > spin.maximum():
        spin.setMaximum(v)
    if v < spin.minimum():
        spin.setMinimum(v)


def show_value(spin, value):
    """!
    @brief Show a loaded value in a spin box: widen the range first, then set it (an integer box gets the nearest whole number inside its C int).
    @param spin QDoubleSpinBox or QSpinBox.
    @param value The value to show, in the unit of the box.
    @return None.
    """
    fit_range(spin, value)
    if isinstance(spin, QSpinBox):
        try:
            v = float(value)
        except (TypeError, ValueError, OverflowError):
            return
        if not math.isfinite(v):
            return
        spin.setValue(int(min(max(round(v), INT_MIN), INT_MAX)))
        return
    spin.setValue(value)
