#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file spinfit.py
@brief A spin box never clamps silently a value that was loaded from a project: its range grows to hold it.
"""

import math

from PySide6.QtWidgets import QSpinBox


def fit_range(spin, value):
    """!
    @brief Widen the range of a spin box so that it can hold a value that was loaded from a project, never clamping it.
    @details A box whose range is narrower than the model (a 10 mm copper plate in a box that stops at 210 um) used to show the clamped value and, on the next
             edit of ANY field of the panel, write that clamped value back into the project. The range now follows the loaded value instead.
    @param spin QDoubleSpinBox or QSpinBox.
    @param value The value about to be shown, in the unit of the box.
    @return None.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return
    if v != v:                                                  # NaN: nothing to hold
        return
    if v > spin.maximum():
        spin.setMaximum(type(spin.maximum())(math.ceil(v)) if isinstance(spin, QSpinBox) else v)
    if v < spin.minimum():
        spin.setMinimum(type(spin.minimum())(math.floor(v)) if isinstance(spin, QSpinBox) else v)
