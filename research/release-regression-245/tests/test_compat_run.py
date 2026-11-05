#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_compat_run.py
@brief Tests of the compatibility helpers of `compat_run.py` that need no program: the refusal of an unknown model becomes `not_available`, and the features of a problem without the newest API.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE.parent / "lib"))

import compat_run as K                                                      # noqa: E402


def test_unknown_model_becomes_not_available():
    """!
    @brief The ValueError of a release that lacks a model is recorded as not_available with a plain reason; other errors stay errors.
    @return None.
    """
    rec = {"board": "b", "model": "fdm", "status": "error", "reason": "ValueError: models must be a non-empty subset of ('fvm', 'lumped', 'analytic'), got ('fdm',)"}
    assert K.mark_missing_model(rec)["status"] == "not_available" and "'fdm' does not exist" in rec["reason"]
    other = {"board": "b", "model": "fvm", "status": "error", "reason": "MemoryError: x"}
    assert K.mark_missing_model(other)["status"] == "error"


def test_features_without_outline_or_profiles():
    """!
    @brief A problem of an old release (no has_outline, no has_profiles, `sinks` instead of `heatsinks`) still gives its features.
    @return None.
    """
    board = SimpleNamespace(layers=2, ambient=25.0, width=0.06, height=0.04)
    problem = SimpleNamespace(board=board, vias=[1, 2], heaters=[1], sinks=[1, 2, 3])
    f = K.compat_features(problem)
    assert f["outline"] is False and f["profiles"] is False and f["heatsinks"] == 3 and f["vias"] == 2 and f["size_mm"] == [60.0, 40.0]


def test_steady_problem_without_profiles():
    """!
    @brief The steady copy works on parts that have no average_power or profile (releases before 2.1.0).
    @return None.
    """
    p = SimpleNamespace(heaters=[SimpleNamespace(power=3.0)])
    q = K.compat_steady_problem(p)
    assert q.heaters[0].power == 3.0 and q is not p
