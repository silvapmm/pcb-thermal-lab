#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file patch_program.py
@brief The change of INTEGRATION.md 1 (first ring at most one equivalent radius of the footprint wide) applied to a COPY of the program, outside the repository.
@details Two uses, both written by the review so that the claims "nothing existing moves" and "the time runs follow the steady state" rest on the change exactly as it would be
         merged, not on the switches of lib/lumped_log.py:
         - copy_tree(dst): `git archive HEAD pcbthermal tests examples` into dst (a scratch folder), then the patch on dst/pcbthermal/lumped.py; the frozen-numbers test can then be run
           in dst as the release runs it (scripts/study_frozen_patched_copy.py);
         - load_patched(): the patched lumped.py of the current checkout as a module `pcbthermal.lumped_capped` (relative imports resolve in the program's package), to swap into
           pcbthermal.api for a run.
         The program in the repository is never written.
"""

import importlib.util
import subprocess
import sys
import tarfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The three edits of INTEGRATION.md 1, as (anchor, replacement); every anchor must occur the stated number of times
EDITS = (
    ("def ring_edges(rho_max, dx, dy, rings, min_width=None):", "def ring_edges(rho_max, dx, dy, rings, min_width=None, a_eq=None):", 1),
    ("    rho1 = max(1.5 * min(dx, dy), 0.04 * rho_max)\n",
     "    rho1 = max(1.5 * min(dx, dy), 0.04 * rho_max)\n"
     "    if a_eq is not None:                                   # the first ring is at most one equivalent radius of the footprint wide\n"
     "        rho1 = min(rho1, max(1.5 * min(dx, dy), a_eq))\n", 1),
    ("ring_edges(rho_max, net.dx, net.dy, rings)",
     "ring_edges(rho_max, net.dx, net.dy, rings, a_eq=math.sqrt(max(float((cov > 0).sum()), 1.0) * net.dx * net.dy / math.pi))", 2),
)


def patch_text(text):
    """!
    @brief Apply the change to the text of pcbthermal/lumped.py.
    @param text Source of lumped.py.
    @return The patched source.
    @throws RuntimeError When an anchor is not found the expected number of times (the program changed).
    """
    if "\nimport math\n" not in text:
        raise RuntimeError("lumped.py does not import math")
    for old, new, n in EDITS:
        if text.count(old) != n:
            raise RuntimeError(f"anchor found {text.count(old)} times, expected {n}: {old[:60]}")
        text = text.replace(old, new)
    return text


def copy_tree(dst):
    """!
    @brief Export the committed program, tests and examples into dst and patch dst/pcbthermal/lumped.py.
    @param dst Destination folder (created; must be outside the repository).
    @return Path of dst.
    @throws RuntimeError When dst lies inside the repository.
    """
    dst = Path(dst).resolve()
    if ROOT in dst.parents or dst == ROOT:
        raise RuntimeError("the patched copy must be outside the repository")
    dst.mkdir(parents=True, exist_ok=True)
    blob = subprocess.run(["git", "archive", "HEAD", "pcbthermal", "tests", "examples"], cwd=ROOT, check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        tar.extractall(dst, filter="data")
    target = dst / "pcbthermal" / "lumped.py"
    target.write_text(patch_text(target.read_text()))
    return dst


def load_patched():
    """!
    @brief The patched lumped.py of this checkout as the module pcbthermal.lumped_capped.
    @return Module object.
    """
    import pcbthermal.lumped as orig
    name = "pcbthermal.lumped_capped"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_loader(name, loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "pcbthermal"
    mod.__file__ = orig.__file__
    sys.modules[name] = mod
    exec(compile(patch_text(Path(orig.__file__).read_text()), "lumped_capped", "exec"), mod.__dict__)
    return mod
