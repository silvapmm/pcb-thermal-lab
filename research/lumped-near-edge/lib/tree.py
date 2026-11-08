#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file tree.py
@brief Choose which checkout of the program the studies import (environment variable PCBT_TREE) and put it first on sys.path.
@details The studies concern the Lumped model of the 2.6.0 integration (capped first ring, cut cells). PCBT_TREE names a checkout of that tree (default: the repository this file is in).
         Nothing in the tree is edited. Import this module before importing pcbthermal.
"""

import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("PCBT_TREE", Path(__file__).resolve().parents[3])).resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
