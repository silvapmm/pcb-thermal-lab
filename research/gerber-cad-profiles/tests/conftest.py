#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file conftest.py
@brief Put the library of the investigation, its scripts and the repository root on the import path.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
for p in (os.path.join(BASE, "lib"), os.path.join(BASE, "scripts"), ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)
