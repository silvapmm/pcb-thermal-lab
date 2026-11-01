#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file variant.py
@brief Builds, outside the program, a copy of `pcbthermal` in which the way the zones are combined can be chosen (env ZONE_RULE), and puts it first on the import path.
@details The program is never edited: the copy lives in research/zone-union/out/variant/pcbthermal. It is made from the working tree by (1) copying lib/zone_rules.py to pcbthermal/_zone_rules.py and (2) appending
         to geometry.py a zone_fill that dispatches on os.environ["ZONE_RULE"] (default max_point, the prototype). With ZONE_RULE=max_cell the copy gives the rule of the program BEFORE 2.4.5.
         Frozen history (2.4.5): `fix/zone-union` was merged, so the program itself now calls `geometry.zone_fill` (rule max_point) at all the call sites and the
         step "apply lib/zone_union_prototype.patch" was dropped (the patch no longer applies: every hunk is already in the program). The patch file is kept as the record of the
         prototype. The "old" column of the studies is therefore the variant with max_cell, no longer the unmodified program, and the unmodified program equals max_point. The rule is read at every call, so one process can sweep all the rules.
         Use: `import variant; variant.use()` before importing pcbthermal; `variant.use(False)` keeps the program of the repository as it is.
"""

import os
import shutil
import sys
from pathlib import Path

from paths import LIB, OUT, REPO

## The patch of the prototype, kept as the record only (the program has the change since 2.4.5; it is not applied any more).
PATCH = LIB / "zone_union_prototype.patch"
## Where the copy is built.
VARIANT = OUT / "variant"

## Appended to the copy's geometry.py: the rule is chosen by the environment variable at every call.
DISPATCH = '''

# --- Research variant (research/zone-union/lib/variant.py): the rule that combines the zones is chosen by ZONE_RULE
import os as _os
from ._zone_rules import combine as _combine


def zone_fill(zones, layers, nx, ny, dx, dy, samples=4):
    """!
    @brief Copper fill of every layer under the rule named in ZONE_RULE (default max_point, the prototype) with ZONE_SAMPLES sub-samples per side (default the caller's 4).
    @param zones Zones.
    @param layers Number of layers.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side.
    @return Array (layers, ny, nx).
    """
    return _combine(zones, layers, nx, ny, dx, dy, int(_os.environ.get("ZONE_SAMPLES", samples)), _os.environ.get("ZONE_RULE", "max_point"))
'''


def build(force=False):
    """!
    @brief Make the copy of the program with the choosable rule.
    @param force Rebuild even when it exists.
    @return Path of the folder to put on sys.path.
    @throws RuntimeError If the program has no geometry.zone_fill.
    """
    target = VARIANT / "pcbthermal"
    if target.exists() and not force:
        return VARIANT
    if VARIANT.exists():
        shutil.rmtree(VARIANT)
    VARIANT.mkdir(parents=True)
    # Copy the package without caches (the data and the user guide are needed by the imports)
    shutil.copytree(REPO / "pcbthermal", target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # The program already calls geometry.zone_fill (max_point) everywhere; the dispatch below replaces that one function in the copy
    if "def zone_fill" not in (target / "geometry.py").read_text():
        raise RuntimeError("this tree has no geometry.zone_fill: the variant needs the program with fix/zone-union merged")
    shutil.copy(LIB / "zone_rules.py", target / "_zone_rules.py")
    with open(target / "geometry.py", "a") as fh:
        fh.write(DISPATCH)
    return VARIANT


def use(variant=True, rule=None):
    """!
    @brief Put the copy (or the program as it is) first on the import path; call before importing pcbthermal.
    @param variant True for the copy with the choosable rule, False for the repository's program.
    @param rule Optional rule to set in ZONE_RULE.
    @return None.
    @throws RuntimeError If pcbthermal was already imported from somewhere else.
    """
    if "pcbthermal" in sys.modules:
        here = Path(sys.modules["pcbthermal"].__file__).resolve()
        want = (VARIANT if variant else REPO) / "pcbthermal" / "__init__.py"
        if here != want.resolve():
            raise RuntimeError(f"pcbthermal already imported from {here}")
    path = str(build() if variant else REPO)
    if path not in sys.path[:1]:
        sys.path.insert(0, path)
    if rule:
        os.environ["ZONE_RULE"] = rule


def set_rule(rule):
    """!
    @brief Choose the rule for the next calls.
    @param rule One of zone_rules.RULES.
    @return None.
    """
    os.environ["ZONE_RULE"] = rule
