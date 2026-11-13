#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_report.py
@brief Prints the comparison tables: the finite-element values (three meshes, observed order, Richardson extrapolation, GCI) against the finite-volume references of
       the repository and against the program (FVM, FDM) on the strong-edge plate, the via, the squares, the disc and the T.
@details Run from the repository root after `study_fem_cases.py`, `study_program.py` and `study_fv_refs.py`: `.venv/bin/python research/independent-fem-edge/scripts/study_report.py`.
         Reads `research/independent-fem-edge/out/{fem_cache,prog,fv}.json`, writes `research/independent-fem-edge/out/report.json` and prints Markdown tables.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import refine                                                            # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
HF_PLATE = (0.2, 0.1, 0.05)
HF_SQ = (0.4, 0.2, 0.1)
N_DISC = (8, 16, 32)
SETTINGS = ((None, False, "default (2 sub-gaps)"), (8, False, "8 sub-gaps"))     # the simple and the advanced stack-up are bit-identical on this tree (validation 43), checked below


def pct(a, b):
    """!
    @brief Percentage difference of a against b.
    @param a Value.
    @param b Reference.
    @return str.
    """
    return f"{100 * (a / b - 1):+.2f}"


def zcorr(fem, keys, field="tmax"):
    """!
    @brief Through-thickness correction from a 3 / 6 / 12 (and 24) elements-per-gap sequence on one plan mesh: Richardson limit minus the 6-element value.
    @param fem Cache.
    @param keys Keys of the 3, 6, 12 (optionally 24) element solves on the same plan mesh.
    @param field Value field.
    @return Tuple (correction K, dict of the sequence) or (0.0, None) when the keys are missing.
    """
    if not all(k in fem for k in keys):
        return 0.0, None
    vals = [fem[k][field] for k in keys]
    r = refine.richardson(vals[-3:])
    return r["ext"] - vals[1], {"vals": vals, "p": r["p"], "ext": r["ext"]}


def ext_of(fem, keys, field="tmax"):
    """!
    @brief Richardson result of three cached FEM values.
    @param fem Cache.
    @param keys Three keys, coarse to fine.
    @param field Value field.
    @return dict of refine.richardson plus 'vals'.
    """
    vals = [fem[k][field] for k in keys]
    r = refine.richardson(vals)
    r["vals"] = vals
    return r


def main():
    """!
    @brief Print every table.
    @return None.
    """
    fem = json.load(open(os.path.join(OUT, "fem_cache.json")))
    prog = json.load(open(os.path.join(OUT, "prog.json"))) if os.path.exists(os.path.join(OUT, "prog.json")) else {}
    fv = json.load(open(os.path.join(OUT, "fv.json"))) if os.path.exists(os.path.join(OUT, "fv.json")) else {}
    rep = {}
    print("## (a) Strong-edge plate: hottest rise (K)\n")
    for k, v in list(prog.items()):                                        # simple == physical on this tree: assert it, so the collapsed columns are honest
        if k.startswith("strong|") and k.split("|")[6] == "False":
            kp = k.replace("|False|", "|True|")
            assert kp in prog and abs(prog[kp] - v) < 1e-9, (k, v, prog.get(kp))
    print("| h_side | inset | FEM 0.2 / 0.1 / 0.05 mm (6 per gap) | p | plan ext | GCI | z corr | FEM ext | FV 1/4 | FV 1/8 | FVM 0.5: default / 8 sub-gaps | FVM 0.25 | FDM 0.5 | FDM 0.25 |")
    print("| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for inset in (0.0, 0.5):
        for h in (10.0, 200.0, 1000.0):
            keys = [f"plate|{h}|{inset}|{hf}|6" for hf in HF_PLATE]
            if not all(k in fem for k in keys):
                continue
            r = ext_of(fem, keys)
            zc, zseq = zcorr(fem, [f"plate|{h}|0.0|0.1|{n}" for n in (3, 6, 12, 24)])
            e = r["ext"] + zc
            rep[f"plate|{h}|{inset}"] = {"fem": r["vals"], "p": r["p"], "ext_plan": r["ext"], "zcorr": zc, "zseq": zseq, "ext": e, "gci": r["gci"]}
            fvc = [fv.get(f"{h}|None|{inset * 1e-3 if inset else 0.0}|{dx}", {}).get("tmax") for dx in (0.00025, 0.000125)]
            fvs = [f"{v:.4f} ({pct(v, e)})" if v else "-" for v in fvc]
            cols = []
            for cell in (0.5, 0.25):
                vals = [prog.get(f"strong|{h}|None|{inset}|{cell}|{n}|{phys}|fvm") for n, phys, _ in SETTINGS]
                cols.append(" / ".join(pct(v, e) if v else "-" for v in vals))
            fdm = []
            for cell in (0.5, 0.25):
                v = prog.get(f"strong|{h}|None|{inset}|{cell}|None|False|fdm")
                fdm.append(pct(v, e) if v else "-")
            rep[f"plate|{h}|{inset}"].update({"fv": fvc, "prog_fvm": cols, "prog_fdm": fdm})
            print(f"| {h:.0f} | {inset} | {' / '.join(f'{v:.4f}' for v in r['vals'])} | {r['p']:.2f} | {r['ext']:.4f} | {100 * r['gci']:.2f} % | {zc:+.4f} | {e:.4f} | {fvs[0]} | {fvs[1]} | {cols[0]} | {cols[1]} | {fdm[0]} | {fdm[1]} |")
    for h in (200.0, 1000.0):
        th = [fem.get(f"plate|{h}|0.0|0.1|{n}", {}).get("tmax") for n in (3, 4, 6, 12, 24)]
        print(f"\nThickness sequence at {h:.0f} W/m2K, plan 0.1 mm: 3 / 4 / 6 / 12 / 24 graded elements per gap {th}")
        rep[f"thickness|{h}"] = th
    print(f"6 uniform elements per gap at 1000: {fem.get('plate|1000.0|0.0|0.1|6|uniformgap', {}).get('tmax')}")

    print("\n## (b) Via effect E = hottest rise without the via minus with it (K), via 0.16 and 3 mm from the wall\n")
    print("| h_side | d (mm) | FEM E 0.2 / 0.1 / 0.05 (same mesh, copper off/on) | ext | GCI | FV 1/4 | FV 1/8 | FVM 0.5: default / 8 sub-gaps | FVM 0.25 | FDM 0.5 ; 0.25 (default) |")
    print("| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for h in (200.0, 1000.0):
        for d in (0.16, 3.0):
            kv = [f"via|{h}|{d}|{hf}|6" for hf in HF_PLATE]
            kn = [f"via|{h}|{d}|{hf}|6|nocopper" for hf in HF_PLATE]
            if not all(k in fem for k in kv):
                continue
            if all(k in fem for k in kn):
                E = [fem[a]["tmax"] - fem[b]["tmax"] for a, b in zip(kn, kv)]
                how = "same mesh"
            else:
                E = [fem[f"plate|{h}|0.0|{hf}|6"]["tmax"] - fem[b]["tmax"] for hf, b in zip(HF_PLATE, kv)]
                how = "plate mesh minus via mesh"
            r = refine.richardson(E)
            e = r["ext"]
            fvE = []
            for dx in (0.00025, 0.000125):
                a, b = fv.get(f"{h}|None|0.0|{dx}", {}).get("tmax"), fv.get(f"{h}|{d * 1e-3}|0.0|{dx}", {}).get("tmax")
                fvE.append(a - b if a and b else None)
            cols = []
            for cell in (0.5, 0.25):
                vals = []
                for n, phys, _ in SETTINGS:
                    a, b = prog.get(f"strong|{h}|None|0.0|{cell}|{n}|{phys}|fvm"), prog.get(f"strong|{h}|{d}|0.0|{cell}|{n}|{phys}|fvm")
                    vals.append(a - b if a and b else None)
                cols.append(" / ".join(pct(v, e) if v else "-" for v in vals))
            fdm = []
            for cell in (0.5, 0.25):
                a, b = prog.get(f"strong|{h}|None|0.0|{cell}|None|False|fdm"), prog.get(f"strong|{h}|{d}|0.0|{cell}|None|False|fdm")
                fdm.append(pct(a - b, e) if a and b else "-")
            rep[f"via|{h}|{d}"] = {"E": E, "how": how, "p": r["p"], "ext": e, "gci": r["gci"], "fv": fvE, "prog_fvm": cols, "prog_fdm": fdm}
            print(f"| {h:.0f} | {d} | {' / '.join(f'{v:.4f}' for v in E)} ({how}) | {e:.4f} (p {r['p']:.2f}) | {100 * r['gci']:.2f} % | " +
                  " | ".join(f"{v:.4f} ({pct(v, e)})" if v else "-" for v in fvE) + f" | {cols[0]} | {cols[1]} | {' ; '.join(fdm)} |")

    print("\n## (c) Squares and disc: heater mean rise (K); program = ten turned/shifted boards (mean error, worst), disc = shifts 0 and 0.3 cell\n")
    print("| board | h_side | FEM coarse / mid / fine (12 per gap) | p | plan ext + z corr (6/12/24) = ext | GCI | FV truth | FVM 1 mm vs FEM (worst) [vs truth] | FVM 0.5 | FDM 1 | FDM 0.5 |")
    print("| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for name, hs, seq in (("sq_in", (10.0, 200.0, 1000.0), HF_SQ), ("sq_wall", (200.0, 1000.0), HF_SQ), ("T_wall", (200.0,), HF_SQ),
                          ("disc_wall", (200.0, 1000.0), N_DISC), ("disc_in", (200.0, 1000.0), N_DISC)):
        for h in hs:
            if name.startswith("disc"):
                keys = [f"disc|{h}|{0.0 if name == 'disc_wall' else 1.2}|{n}|g12" for n in seq]
            else:
                keys = [f"{name}|{h}|{hf}|g12" for hf in seq]
            if not all(k in fem for k in keys):
                continue
            r = ext_of(fem, keys, "heater_mean")
            zk = f"disc|{h}|{0.0 if name == 'disc_wall' else 1.2}|16" if name.startswith("disc") else f"{name}|{h}|0.2"
            zc, zseq = zcorr(fem, [f"{zk}|g6", f"{zk}|g12", f"{zk}|g24"], "heater_mean")
            e = r["ext"] + zc
            truth = fv.get(f"truth|{name}|{h}")
            cells = []
            for model in ("fvm", "fdm"):
                for cell in (1.0, 0.5):
                    pk = f"{name if not name.startswith('disc') else 'disc'}|{h}|{(0.0 if name == 'disc_wall' else 1.2) if name.startswith('disc') else ''}|{cell}|{model}"
                    pk = pk.replace("||", "|") if not name.startswith("disc") else pk
                    v = prog.get(pk)
                    if v is None:
                        cells.append("-")
                        continue
                    arr = np.asarray(v["mean"])
                    err = 100 * (arr / e - 1)
                    s = f"{err.mean():+.2f} ({np.abs(err).max():.2f})"
                    if truth:
                        et = 100 * (arr / truth - 1)
                        s += f" [{et.mean():+.2f}]"
                    cells.append(s)
            rep[f"{name}|{h}"] = {"fem": r["vals"], "p": r["p"], "ext_plan": r["ext"], "zcorr": zc, "zseq": zseq, "ext": e, "gci": r["gci"], "truth": truth, "prog": cells}
            print(f"| {name} | {h:.0f} | {' / '.join(f'{v:.4f}' for v in r['vals'])} | {r['p']:.2f} | {r['ext']:.4f} {zc:+.4f} = {e:.4f} | {100 * r['gci']:.2f} % | " +
                  (f"{truth:.4f} ({pct(truth, e)})" if truth else "-") + " | " + " | ".join(cells) + " |")
    full = fem.get("T_wall|200.0|0.4|full|g12")
    if full:
        print(f"\nT whole domain at 0.4 mm: heater mean {full['heater_mean']:.4f} against the half domain {fem['T_wall|200.0|0.4|g12']['heater_mean']:.4f}")
    # the disc: hottest rise too (the program's t_max against the FEM node maximum)
    print("\n## (c') Disc: hottest rise (K), FEM extrapolated against the program's t_max\n")
    print("| board | h_side | FEM ext | FVM 1 mm (shift 0 / 0.3) | FVM 0.5 | FDM 1 | FDM 0.5 |")
    print("| :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for name, inset in (("disc_wall", 0.0), ("disc_in", 1.2)):
        for h in (200.0, 1000.0):
            keys = [f"disc|{h}|{inset}|{n}|g12" for n in N_DISC]
            if not all(k in fem for k in keys):
                continue
            r = ext_of(fem, keys, "tmax")
            zc, _ = zcorr(fem, [f"disc|{h}|{inset}|16|g6", f"disc|{h}|{inset}|16|g12", f"disc|{h}|{inset}|16|g24"], "tmax")
            r["ext"] += zc
            cells = []
            for model in ("fvm", "fdm"):
                for cell in (1.0, 0.5):
                    v = prog.get(f"disc|{h}|{inset}|{cell}|{model}")
                    cells.append(" / ".join(pct(x, r["ext"]) for x in v["tmax"]) if v else "-")
            rep[f"{name}|{h}|tmax"] = {"ext": r["ext"], "p": r["p"], "prog": cells}
            print(f"| {name} | {h:.0f} | {r['ext']:.4f} (p {r['p']:.2f}, GCI {100 * r['gci']:.2f} %) | " + " | ".join(cells) + " |")
    json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
