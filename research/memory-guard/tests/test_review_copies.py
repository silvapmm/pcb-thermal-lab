#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_review_copies.py
@brief Tests of the review's copies (lib/review_copies.py): the one-factor transient gives the program's answer bit for bit, and the dense SOR inverse holds the same numbers as the program's sparse one.
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parent / "lib"))

import cases                                               # noqa: E402
import review_copies                                       # noqa: E402
from pcbthermal import fvm                                 # noqa: E402


def test_one_factor_transient_is_bit_identical(monkeypatch):
    """!
    @brief The animation transient with one factor kept gives the same frames as the program (same steps, same factors, same order of operations).
    @param monkeypatch pytest fixture that swaps the network transient for the copy.
    @return None.
    """
    spec = dict(family="partial", layers=4, size_mm=40, cell_mm=2.0, model="fvm")
    a = fvm.solve_transient(cases.build(spec), t_end=200.0, n_out=10, cell_mm=2.0)
    monkeypatch.setattr(fvm, "transient_from_network", review_copies.transient_from_network_one_factor)
    b = fvm.solve_transient(cases.build(spec), t_end=200.0, n_out=10, cell_mm=2.0)
    assert np.array_equal(a.frames, b.frames) and np.array_equal(a.times, b.times)


def test_dense_sor_inverse_holds_the_same_numbers():
    """!
    @brief The block inverse kept dense equals the program's sparse block-diagonal one.
    @return None.
    """
    import scipy.sparse as sp
    n = 60
    A = sp.random(n, n, density=0.1, format="csr", random_state=3)
    A = (A + A.T + sp.identity(n) * 20.0).tocsr()
    assert np.array_equal(review_copies.sor_inverse_program(A).toarray(), review_copies.sor_inverse_dense(A))
