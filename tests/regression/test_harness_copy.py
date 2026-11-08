#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_harness_copy.py
@brief The harness files of this folder are byte-identical to the ones in releases/regression-harness/lib/ (one source of truth, two places).
"""

from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
LIB = HERE.parents[1] / "releases" / "regression-harness" / "lib"


@pytest.mark.parametrize("name", ["regress_boards.py", "regress_harness.py", "regress_classify.py", "regress_frozen.py"])
def test_harness_file_equals_the_harness_copy(name):
    """!
    @brief A harness file edited in one place only would make the studies and the permanent test disagree about the tolerance or the boards.
    @param name File name.
    @return None.
    """
    if not (LIB / name).exists():
        pytest.skip("the research folder is not present")
    assert (HERE / name).read_bytes() == (LIB / name).read_bytes(), f"{name} differs from releases/regression-harness/lib/{name}: copy one over the other"
