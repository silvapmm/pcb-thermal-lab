#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file tree.py
@brief Put the checkout of the program on sys.path (PCBT_TREE, default: the repository this file is in) and select the offscreen Qt platform. Import before pcbthermal.
"""

import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("PCBT_TREE", Path(__file__).resolve().parents[3])).resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
