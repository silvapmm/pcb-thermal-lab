#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Puts the import paths of research/zone-union in order; every script imports it first, so scripts run from any folder.
@details The own `lib` and the folder of the independent solver come first; the program (or its variant) is put on the path by `variant.use()` in the script.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for extra in (str(HERE / "lib"), str(HERE / "scripts"), str(HERE.parents[1] / "tests" / "helpers"), str(HERE.parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)
