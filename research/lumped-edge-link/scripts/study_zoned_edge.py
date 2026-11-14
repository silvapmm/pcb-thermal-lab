#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_zoned_edge.py
@brief The near-edge deficit of a part over a dense group of vias (the zoned footprint of the Lumped) and what the first-link variants do there.
@details Board of research/lumped-dense-via-group (100 x 80 mm, 2 layers, 8 mm part, 5 x 5 vias at 1 mm pitch under it, 3 W, 10 W/m2K) translated so that the gap from the part to the
         left side is 3, 6, 12, 25 mm and, as a control, centred. Peak and mean of the part against the FVM at 0.5 mm; "one node" is the Lumped with the zone model switched off.
         The variants patch the ONE-node link only (first), the one-node link and the zone model's A to ring 1 (expo_peak, first:zone): the zoned numbers say whether a first-link correction
         must reach the zone model too. Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-edge-link/scripts/study_zoned_edge.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lumped-dense-via-group" / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402
import viastudy as VS  # noqa: E402

VARIANTS = ("program", "expo_peak", "first", "first:zone")


def case(gap):
    """!
    @brief The board with the part and the via array translated to a gap from the left side.
    @param gap Gap in mm (None: centred, the original board).
    @return Problem.
    """
    p = VS.board(layers=2, n=5, pitch=1.0, part=8.0, power=3.0, h=10.0)
    if gap is not None:
        dx = (gap + 4.0) - p.board.width * 1e3 / 2.0 if False else (gap + 4.0) * 1e-3 - p.board.width / 2.0
        for v in p.vias:
            v.x += dx
        for h in p.heaters:
            h.polygon[:, 0] += dx
    return p


def main():
    """!
    @brief Run the cases and print the errors.
    @return None.
    """
    rows = []
    for gap in (3.0, 6.0, 12.0, 25.0, None):
        p = case(gap)
        f = B.part_read(p, "fvm", 0.5)
        row = {"gap": gap, "fvm": f}
        for v in VARIANTS:
            V.install(v)
            m = V.load(v)
            for zones in (True, False):
                m.ZONES = zones
                r = B.part_read(p, "lumped", 0.5)
                row[f"{v}{'' if zones else ' one node'}"] = [100 * (r[0] / f[0] - 1), 100 * (r[1] / f[1] - 1)]
            m.ZONES = True
        rows.append(row)
        print(gap, "fvm %.2f/%.2f" % f[:2], {k: [round(x, 1) for x in v] for k, v in row.items() if k not in ("gap", "fvm")}, flush=True)
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / "zoned_edge.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
