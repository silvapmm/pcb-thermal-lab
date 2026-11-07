#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file smoke.py
@brief Quick check that the variants run: one edge case.
@details Run: .venv/bin/python research/lumped-near-edge/scripts/smoke.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402


def main():
    """!
    @brief Print FVM and the variants for a 5 mm part at the edge and at the centre.
    @return None.
    """
    for d in (0.0, 5.0, 40.0):
        pos = (d + 2.5, 40.0)
        p = B.board(100, 80, 5, pos)
        f = B.fvm(f"smoke|{d}", p, 0.5, 5, pos)
        out = []
        for n in ("program", "image", "potlinks"):
            V.install(n)
            out.append(B.readout(p, "lumped", 0.5, 5, pos))
        print(d, f, out)


if __name__ == "__main__":
    main()
