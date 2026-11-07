#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file conftest.py
@brief Paths for the tests of via-contact-geometry (the folder's lib and scripts, the lib of via-partial-copper, the repository root).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))      # _bootstrap sets the rest of the paths and a private configuration
import _bootstrap  # noqa: E402,F401
