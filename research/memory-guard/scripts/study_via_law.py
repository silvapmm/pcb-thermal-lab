#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_law.py
@brief Question: how much peak memory do the via couplings (Kron reduction in viawell.py) add to a direct FVM or FDM solve, beyond the law of memory.CONTINUOUS?
@details Each case runs in its own child process (lib/measure.py: kernel peak, one case at a time) and is appended to out/via_law.jsonl; finished cases are skipped, so the run can
         be repeated after a stop. Families: viagrid (a plate with an n x n array of 0.3 mm vias) and co60 (the CO60 board or a window of it with its plated holes as vias, copper
         full or in stripes; needs PCBT_REAL_BOARDS, the folder of the downloaded boards). The run stops when the swap in use is above 3.0 GB.
         Run: .venv/bin/python research/memory-guard/scripts/study_via_law.py [--set small|windows|big] [--model fvm|fdm]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[2]))

import cases                                          # noqa: E402
import measure                                        # noqa: E402

OUT = HERE.parent / "out" / "via_law.jsonl"
CUTOFF = 9.0e9


def _swap_used_gb():
    """!
    @brief Swap in use now in GB (macOS sysctl), or 0 when it cannot be read.
    @return float GB.
    """
    try:
        txt = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True).stdout
        m = re.search(r"used = ([\d.,]+)M", txt)
        return float(m.group(1).replace(",", ".")) / 1000.0 if m else 0.0
    except (OSError, ValueError):
        return 0.0


def specs(which, model):
    """!
    @brief The list of case specs of a set.
    @param which "small", "windows" or "big".
    @param model "fvm" or "fdm".
    @return List of dicts.
    """
    out = []
    if which == "small":
        # A 150 mm plate (180 000 to 360 000 unknowns at 0.5 mm) with 0, 25, 100 and 400 vias of 0.3 mm in a square of 30 mm (pitch 6, 3, 1.5 mm) and 400 in 12 mm (pitch 0.6 mm,
        # footprints that overlap), 2 and 4 layers, at 1, 0.7 and 0.5 mm
        for layers in (2, 4):
            for c in (1.0, 0.7, 0.5):
                for nv, arr in ((0, 30.0), (5, 30.0), (10, 30.0), (20, 30.0), (20, 12.0)):
                    out.append(dict(family="viagrid", layers=layers, size_mm=150.0, cell_mm=c, model=model, nvias=nv, array_mm=arr, order="layer"))
    elif which == "scan":
        # Pitch and count scan at 0.5 mm: where does the extra peak start? (n per side 10 to 40, arrays of 20 to 90 mm)
        for layers in (2, 4):
            for nv in (10, 20, 30, 40):
                for arr in (20.0, 30.0, 45.0, 60.0, 90.0):
                    out.append(dict(family="viagrid", layers=layers, size_mm=150.0, cell_mm=0.5, model=model, nvias=nv, array_mm=arr, order="layer"))
    elif which == "striped":
        # The same plate with copper stripes: bare laminate next to copper, so the laminate nodes of the rule make the graph thick; the vias then join the copper layers across them
        for layers in (2, 4):
            for c in (1.0, 0.7, 0.5):
                for nv, arr in ((0, 30.0), (10, 30.0), (20, 30.0), (20, 12.0)):
                    out.append(dict(family="viagrid", pattern="stripes", layers=layers, size_mm=150.0, cell_mm=c, model=model, nvias=nv, array_mm=arr, order="layer"))
    elif which == "windows":
        for s in (40.0, 80.0):
            for c in (1.0, 0.7, 0.5):
                for pat in ("", "stripes"):
                    out.append(dict(family="co60", layers=2, size_mm=s, cell_mm=c, model=model, pattern=pat, order="layer"))
    else:
        for c in (1.0, 0.7, 0.5):
            for pat in ("", "stripes"):
                for nov in (False, True):
                    out.append(dict(family="co60", layers=2, size_mm=0.0, cell_mm=c, model=model, pattern=pat, novias=nov, order="layer"))
    return out


def main():
    """!
    @brief Run the cases of a set that are not in the output file yet.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="small")
    ap.add_argument("--model", default="fvm")
    ap.add_argument("--pattern", default=None, help="only the cases with this copper pattern ('' full copper, 'stripes')")
    ap.add_argument("--cells", default="", help="comma list of cell sizes in mm to run (default: all of the set)")
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        done = {json.dumps(json.loads(line)["spec"], sort_keys=True) for line in OUT.read_text().splitlines() if line.strip()}
    only = {float(c) for c in args.cells.split(",") if c}
    for spec in specs(args.set, args.model):
        if only and spec["cell_mm"] not in only:
            continue
        if args.pattern is not None and spec.get("pattern", "") != args.pattern:
            continue
        if json.dumps(spec, sort_keys=True) in done:
            continue
        if _swap_used_gb() > 3.0:
            print("swap above 3.0 GB: stop")
            return
        n, _ = cases.count(spec)
        rec = measure.run_case(spec, CUTOFF)
        rec["unknowns_counted"] = n
        rec["n_vias"] = len(cases.build(spec).vias)
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{spec['family']} {spec['layers']}L size {spec['size_mm']} cell {spec['cell_mm']} vias {rec['n_vias']} {spec.get('pattern', '')}: n={n} {rec['status']} "
              f"peak {rec['peak_bytes'] / 1e9:.2f} GB solve {rec.get('t_solve', float('nan')):.1f} s", flush=True)


if __name__ == "__main__":
    main()
