#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_typical_marks.py
@brief The shipped library notes and Preferences tooltips say 'typical value, no source' where the value has no source (no number is changed by these marks).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pcbthermal import defaults
from pcbthermal.gui import preferences


def test_unsourced_library_entries_carry_the_mark_and_the_values_are_unchanged():
    lib = defaults.shipped()["libraries"]
    for e in lib["dielectrics"]:
        assert "no source" in e["note"].lower(), e["name"]
    fr4 = lib["dielectrics"][0]
    assert (fr4["k_through"], fr4["k_inplane"]) == (0.3, 0.9) and "Azar and Graebner" in fr4["note"]
    for e in lib["interfaces"]:
        if e["name"].startswith(("Paste, typical", "Gap pad", "Hard gap pad")):
            assert "no source" in e["note"].lower(), e["name"]
    bga = next(e for e in lib["heatsinks"] if e["name"] == "BGA 40×40×18, natural")
    assert bga["theta_sa_k_per_w"] == 7.68 and bga["note"].startswith("Catalogue value at a 75 K rise")
    assert next(e for e in lib["metals"] if e["name"] == "Copper")["k_w_per_mk"] == 386.0


def test_preferences_tooltips_mark_the_unsourced_defaults():
    for key in ("k_copper", "k_fr4_inplane", "emissivity_top", "emissivity_bottom", "h_top", "h_bottom", "h_side"):
        assert "no " in preferences.TIPS[key].lower() and "source" in preferences.TIPS[key].lower(), key
    assert "398" in preferences.TIPS["k_copper"]
    assert defaults.shipped()["materials"]["k_copper"] == 385.0
