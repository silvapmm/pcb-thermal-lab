#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_units_rule.py
@brief The one place of the unit rule (`pcbthermal/units.py`): the symbols, the layer label, the forbidden forms, and that the Layer box uses the one label.
"""

import re

from pcbthermal import units
from pcbthermal.gui import layerchoice


def test_symbols_and_texts():
    """!
    @brief The symbols are the proper characters and the text helpers use the on-screen minus.
    """
    assert (units.TEMP, units.DELTA, units.MICRO_M, units.TIMES, units.ELLIPSIS) == ("°C", "K", "µm", "×", "…")
    assert units.MICRO_M == "µm" and units.MINUS == "−"
    assert units.delta_text(12.34) == "12.3 K" and units.delta_text(-0.4) == "−0.4 K" and units.temp_text(85.26) == "85.3 °C"


def test_layer_labels_come_from_the_one_function():
    """!
    @brief `1 (top)`, `2`, `4 (bottom)`, and the Layer box takes them from the same function.
    """
    assert [units.layer_label(i, 4) for i in range(4)] == ["1 (top)", "2", "3", "4 (bottom)"]
    assert [t for t, _d in layerchoice.items("single", 4)] == [units.layer_label(i, 4) for i in range(4)]


def test_forbidden_forms_are_listed_with_a_reason_and_match_what_they_name():
    """!
    @brief Every FORBIDDEN entry is a valid pattern with a replacement and a reason, and it matches the old form it names.
    """
    assert len(units.FORBIDDEN) >= 8
    samples = ["degC", "dT C", "ΔT °C", "Osc. °C", "35 um", "100 x 80", "Rth K/W", "Cancel calculation", "1 top", "a rise of 12.5 °C", "Preset shape..."]
    for (pattern, instead, why), sample in zip(units.FORBIDDEN, samples):
        assert instead and why and re.search(pattern, sample), (pattern, sample)
