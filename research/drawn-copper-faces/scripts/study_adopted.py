#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_adopted.py
@brief The closing review after the adoption (README 12): the shipped program (`copper.drawn_source` in `fvm.Network` and `fdm.Network`) against its earlier path, the copy of this folder and the references.
@details The program now reads drawn copper the way `lib/patched.py` did, so the 'drawn' or 'program' columns of the older scripts of this folder print the ADOPTED path when they are re-run.
         The earlier path is reproduced here by replacing `copper.drawn_source` with a function that returns None for the length of a run (a runtime attribute of the imported
         module; no file of the program is touched). Subcommands (run from the repository root with the program's `.venv`):
         * `decomp`: seven boards of README 3, FVM and FDM at 1 / 0.5 / 0.25 mm: earlier path, shipped program and the import reading, against the finite elements of `out/fem.json`.
         * `copy`: the shipped program against the copy (`patched.use('faces')`), six boards at 1 and 0.5 mm, and the rasters of the two constructions compared.
         * `outline`: nine rows of README 4 (ten turned and shifted boards each) against the 3D truths of `research/imported-copper-edge-film`.
         * `pad`: the four-layer 10 mm board with 5 x 4 mm outer pads of the 2.8.0 audit (`research/strong-edge-laminate` builder), hottest rise, FVM and FDM, before and now.
"""
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, HERE)
import numpy as np                                                        # noqa: E402
from pcbthermal import copper                                             # noqa: E402
import dc_cases as D                                                      # noqa: E402
import patched as P                                                       # noqa: E402
import study_decomposition as SD                                          # noqa: E402


@contextlib.contextmanager
def earlier_path():
    """!
    @brief Run the program's networks without the drawn-copper source (the path before `fix/drawn-copper-faces`).
    @return Context manager.
    """
    old = copper.drawn_source
    copper.drawn_source = lambda *a, **k: None                             # the hooks in fvm.py and fdm.py fall back on `or self.copper`
    try:
        yield
    finally:
        copper.drawn_source = old


def decomp():
    """!
    @brief Earlier path, shipped program and import reading against the finite elements (README 12.1).
    @return None.
    """
    cases = [("plain_inset", 200, 2), ("plain_inset", 1000, 2), ("plain_wall", 200, 2), ("stripes", 200, 2), ("stripes", 1000, 2), ("ell", 200, 2), ("plain_inset", 200, 4)]
    for model in ("fvm", "fdm"):
        run = D.heater_mean_fvm if model == "fvm" else D.heater_mean_fdm
        for name, hs, layers in cases:
            ref = SD.fem_ref(name, hs, layers)[1]
            p = D.problem(D.case(name, hs, layers))
            row = {"before": [], "now": [], "import": []}
            bal = 0.0
            for cell in (1.0, 0.5, 0.25):
                with earlier_path():
                    row["before"].append(run(p, cell)[0])
                v, b = run(p, cell)
                row["now"].append(v)
                bal = max(bal, abs(b))
                row["import"].append(run(D.zones_to_imported(p, cell, "faces"), cell)[0])
            e = {k: " / ".join(f"{100 * (x / ref - 1):+.1f}" for x in v) for k, v in row.items()}
            print(f"{model} {name},{hs},{layers} ref {ref:.3f}: before {e['before']}  now {e['now']}  import {e['import']}  balance {bal:.1e}", flush=True)


def copy():
    """!
    @brief The shipped program against the copy of this folder (README 12.2).
    @return None.
    """
    worst = 0.0
    for name, hs, layers in [("plain_inset", 200, 2), ("stripes", 200, 2), ("stripes", 1000, 2), ("ell", 200, 2), ("plain_inset", 200, 4), ("hatch", 200, 2)]:
        p = D.problem(D.case(name, hs, layers))
        for cell in (1.0, 0.5):
            for run in (D.heater_mean_fvm, D.heater_mean_fdm):
                a = run(p, cell)[0]
                with P.use("faces"):
                    b = run(p, cell)[0]
                worst = max(worst, abs(a - b) / a)
        n = int(round(D.A / 1.0))
        src, new = P.source_of(p, 1.0, "faces"), copper.drawn_source(p, n, n)
        diff = max(float(np.abs(src.raster(l).astype(float) - new.raster(l).astype(float)).max()) for l in src.entries)
        print(f"{name},{hs},{layers}: raster difference at 1 mm {diff:.1e} (of 255)", flush=True)
    print(f"largest relative difference of the heater mean, program against the copy: {worst:.1e}")


def outline():
    """!
    @brief Nine rows of README 4 before and now (README 12.3).
    @return None.
    """
    sys.path.insert(0, os.path.join(ROOT, "research", "imported-copper-edge-film", "scripts"))
    import study_drawn_film as S
    rows = [("sq_in", 1.0), ("sq_in", 0.5), ("sq_stripes", 1.0), ("sq_pad", 1.0), ("sq_4l", 1.0), ("T_in", 1.0), ("T_wall", 1.0), ("L_in", 1.0), ("L_wall", 1.0)]
    for name, cell in rows:
        h = 200.0
        spec, tr = S.CASES[name], S.truth_of(name, h)

        def vals():
            """!
            @brief Heater means of the ten placements.
            @return numpy array.
            """
            return np.array([S.heater_rise(S.build(spec, h, a, sh * cell, spec.get("imported", ())), cell)[0] for sh in S.SHIFTS for a in S.ANGLES])
        with earlier_path():
            a = vals()
        b = vals()
        ea, eb = 100 * (a / tr - 1), 100 * (b / tr - 1)
        print(f"{name}|{h:g}|{cell:g}: before {ea.mean():+.2f} / {np.ptp(ea):.2f} / {np.abs(ea).max():.2f} -> now {eb.mean():+.2f} / {np.ptp(eb):.2f} / {np.abs(eb).max():.2f}", flush=True)


def pad():
    """!
    @brief The small outer pads of the audit, hottest rise before and now (README 12.4).
    @return None.
    """
    sys.path.insert(0, os.path.join(ROOT, "research", "strong-edge-laminate", "scripts"))
    import study_thin_laminate as st
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal.model import Materials
    w = st.W * 1e3
    for hs in (10, 200, 1000):
        for model in ("fvm", "fdm"):
            for cell in (1.0, 0.5):
                out = []
                for ctx in (earlier_path, contextlib.nullcontext):
                    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=st.HTOP, h_bottom=st.HBOT, h_side=hs, materials=Materials(k_fr4_inplane=st.KFR))
                    p.board.make_advanced()
                    for layer in range(1, 5):
                        p.add_zone(layer, rect=tuple(v * 1e3 for v in st.PAD) if layer in (1, 4) else (0, 0, w, w))
                    p.add_heater(1, st.POWER, rect=(1, 4, 4, 6))
                    with ctx():
                        out.append(float(simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - p.board.ambient))
                print(f"pad 4 layers, h_side {hs}, {model} {cell:g} mm: before {out[0]:.3f} K, now {out[1]:.3f} K", flush=True)


if __name__ == "__main__":
    {"decomp": decomp, "copy": copy, "outline": outline, "pad": pad}[sys.argv[1]]()
