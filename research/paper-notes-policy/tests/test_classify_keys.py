#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_classify_keys.py
@brief Regression tests of the key classification: the strict classes hold only the keys the review checked by hand.

The first version put a textbook (Lienhard2024) among the standards, a SIAM article among the confidential sources and
magazine articles among the standards; the review read every key of the strict classes. Needs only the tracked
bibliography (no third-party text). A new bibliography key that the rules put in a strict class makes the test fail
until someone reads it and adds it to MANUAL or to the sets below.

Run: .venv/bin/python -m pytest -q research/paper-notes-policy/tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import study_classify_keys as s  # noqa: E402

STANDARDS = {"JESD15-3", "JESD51family", "ASTMD5470", "IPC2152", "IPC4761", "ASMEVV20", "UcamcoGerber", "Gerber2026",
             "Gerber2016Mirror", "GerberSpecAttributes", "XNC2021", "IPC2581", "IPC7351"}
US_GOVERNMENT = {"Ostrach1953", "NISTIR7648", "DTIC-AD1011632", "Ostrach1952TN2635"}


def _classes():
    """!
    @brief Class of every key of the bibliography.

    @return dict Key to class.
    """
    return {k: s.classify(k, t)[0] for k, t in s.entries()}


def test_pilot_keys_have_their_class():
    """!
    @brief The three pilot keys fall in the classes their notes state.

    @return None
    """
    cls = _classes()
    assert cls["Lienhard2024"] == "book / lecture notes"
    assert cls["YovanovichJafarpur1993"] == "journal / conference article"


def test_strict_classes_are_the_checked_keys():
    """!
    @brief Only the hand-checked keys sit in the confidential, standard and US government classes.

    @return None
    """
    cls = _classes()
    # The confidential key is not named here: tests/test_third_party_text.py forbids it in any tracked file.
    conf = [k for k, c in cls.items() if c == "confidential"]
    assert len(conf) == 1 and conf[0].startswith("Odbpp")
    assert {k for k, c in cls.items() if c == "standard"} == STANDARDS
    assert {k for k, c in cls.items() if c == "US government"} == US_GOVERNMENT
