#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_similarity.py
@brief Tests of the illustrative similarity checker on synthetic text (no third-party text is used).

Run: .venv/bin/python -m pytest -q research/paper-notes-policy/tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_note_similarity as c  # noqa: E402

PAPER = ("the heat leaves the plate through a thin boundary layer whose thickness grows along the surface "
         "and the average coefficient follows from integrating the local value over the length")
NOTE = """Key: X
Reading status: R
Licence of the source: test
## Summary
{body}
## Used in the program
none
"""


def test_copied_run_is_flagged():
    """!
    @brief A note that repeats a long run of the paper is flagged.

    @return None
    """
    body = "a thin boundary layer whose thickness grows along the surface and the average coefficient follows"
    flags = c.check(NOTE.format(body=body), PAPER)
    assert any("in a row" in f for f in flags)


def test_own_words_pass():
    """!
    @brief A re-worded summary has no flag and a formula may match.

    @return None
    """
    body = "The paper integrates a local coefficient over the plate to get the mean one, `Nu = 0.5 Ra^(1/4)`."
    assert c.check(NOTE.format(body=body), PAPER) == []


def test_template_rules():
    """!
    @brief Long quotations, images and missing fields are flagged without any paper text.

    @return None
    """
    q = "> " + " ".join(["word"] * 30)
    flags = c.check(NOTE.format(body="ok") + q + "\n![fig](x.png)\n")
    assert any("quotation" in f for f in flags) and any("forbidden" in f for f in flags)
    assert any("missing field" in f for f in c.check("nothing here"))
