#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s0_four_treatments.py
@brief S0: the four treatments of the laminate that the program's investigations proposed, side by side with the program and with the one rule of this folder, on the simple boards first.
@details Question answered: on the same boards and the same independent reference, what does each of the four old treatments do (gap-subdivision n = 4 graded in the bare cells + margin;
         bare-spot-under-source n by cuts with the vertical correction and the face term; the two laminate nodes of laminate.py on a one-layer board; the program as it is), and where does the
         one rule (lib/rule.py default) stand? Boards: boards.simple_set() (one-layer full / pad / window, two-layer pad and window on gaps 0.2 to 3.2 mm, windows 2 to 12 mm, the typical 4- and
         6-layer stack-ups, uniform boards). Printed: the reference peak (face of the part, resolved 3D at 0.25 mm, 8 sub-slabs per gap), the error in percent of every treatment, the unknown
         ratio (ragged) of the proposed rule. Cell 0.5 mm. Output: out/s0_four_treatments.json.
         Run from the repository root: .venv/bin/python research/laminate-nodes/scripts/study_s0_four_treatments.py [--quick]
"""

import _bootstrap  # noqa: F401  (import paths)

import sys

import boards as BD
import report as RP
import rule as RU
import runner as RN

RULES = {**{k: v for k, v in RU.PRESETS.items()}, "proposed": RU.Rule(name="proposed")}


def main():
    """!
    @brief Run the set and print the table.
    @return None.
    """
    specs = BD.simple_set()
    if "--quick" in sys.argv:
        specs = [s for s in specs if "1.6 mm" in s.name or "typical" in s.name][:8]
    rows = []
    for spec in specs:
        r = RN.row(spec, RULES)
        flat = {"board": spec.name, "ref K": (".2f", r["ref"])}
        for k in RULES:
            flat[k] = r[k]["err"]
        flat["unk x"] = (".2f", r["proposed"]["ratio"])
        rows.append(flat)
    RP.table(rows, ["board", "ref K"] + list(RULES) + ["unk x"], title="Error of the peak under the part against the resolved 3D face value, percent (cell 0.5 mm)")
    RP.save("s0_four_treatments", rows)


if __name__ == "__main__":
    main()
