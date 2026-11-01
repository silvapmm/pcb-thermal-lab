#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file conftest.py
@brief Setup of the frozen-numbers regression test: the harness files of this folder on `sys.path` and a private, empty program configuration with the libraries reloaded.
"""

import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
# the harness (regress_*.py) lives next to the tests; it is also kept in research/release-regression-245/lib/ (test_harness_copy.py checks they are identical)
sys.path.insert(0, str(HERE))


@pytest.fixture(scope="module", autouse=True)
def private_config():
    """!
    @brief Run every module of this folder with an empty program configuration (no user defaults) and the shipped libraries, as the frozen numbers were made.
    @details The libraries (`model.DIELECTRICS`, `VIA_FILLS`, ...) are module lists refilled in place, so setting the environment variable is not enough: a test that changed
             them earlier would change the frozen numbers. The fixture reloads them after setting the private folder and again after restoring the environment.
    @return None (the environment and the libraries are restored after the module).
    """
    from pcbthermal import defaults, model
    with pytest.MonkeyPatch().context() as mp:
        mp.setenv("PCBTHERMAL_CONFIG", tempfile.mkdtemp(prefix="pcbt_frozen_cfg_"))
        mp.setenv("QT_QPA_PLATFORM", "offscreen")
        defaults._CACHE.pop("stamp", None)
        model.reload_libraries()
        yield
    # the monkeypatch context has restored the environment; refill the libraries from it for the tests that follow
    defaults._CACHE.pop("stamp", None)
    model.reload_libraries()
