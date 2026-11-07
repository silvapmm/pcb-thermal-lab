#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_patched_copy.py
@brief Review: run the program's own frozen-numbers test (all five models, the times to 63 %, cells 2, 1 and 0.5 mm) on a copy of the tree with the capped first ring applied.
@details study_frozen_impact.py compares the Lumped maximum of the 17 boards with and without the change through lib/lumped_log.py; this script checks the claim "no frozen record
         moves" the way the release does: lib/patch_program.copy_tree exports the committed pcbthermal/, tests/ and examples/ into a folder OUTSIDE the repository, applies the
         change of INTEGRATION.md 1 to that copy's lumped.py, and runs `pytest tests/regression/test_frozen_numbers.py` there with PCBT_FROZEN_CELLS (default 2,1,0.5). The
         records are compared with tests/regression/data/v2.5.0.json under the test's one tolerance policy (temperatures 1e-8 K, times to 63 % 1e-6 relative). The program in the
         repository is not touched. Usage, from the repository root (about 100 s, peak about 2.3 GB; one pytest at a time on the machine):
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_frozen_patched_copy.py <scratch folder> [cells]
"""

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import patch_program as PP  # noqa: E402


def main(argv):
    """!
    @brief Build the patched copy and run the frozen test in it.
    @param argv [scratch folder, optional cells such as "2,1,0.5"].
    @return Exit code of pytest.
    """
    if not argv:
        print(__doc__)
        return 2
    dst = PP.copy_tree(Path(argv[0]) / "lumped_capped_tree")
    src = (dst / "pcbthermal" / "lumped.py").read_text()
    assert "a_eq=None" in src and src.count("a_eq=math.sqrt") == 2         # the change is really in the copy
    env = dict(os.environ, PCBT_FROZEN_CELLS=argv[1] if len(argv) > 1 else "2,1,0.5", QT_QPA_PLATFORM="offscreen")
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/regression/test_frozen_numbers.py"]
    print("running in", dst, ":", " ".join(cmd[2:]), flush=True)
    return subprocess.run(cmd, cwd=dst, env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
