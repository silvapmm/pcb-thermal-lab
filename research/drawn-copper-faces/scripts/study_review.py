#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The independent checks of the review (README 11): the decomposition fill / faces with the laminate rule at 4 and 1 sub-gaps, the spread of the outline boards against the pixels per cell,
       vias, a metal block and overlapping zones through the copy, and the memory of the copy against the guard's estimate plus a proposed raster term.
@details Subcommands (run from the repository root with the program's `.venv`; one at a time):
         * `decomp [n4|n1]`: FVM and FDM, five boards, cells 1 and 0.5 mm; readings drawn, exact fill with the program's face rules kept (`exactfill`, the drawn path with
           `geometry.zone_fill` replaced by the exact coverage), the flow faces with the 4 x 4 fill kept (`faces_4x4fill`, `copper.override_fill` disabled), the flow faces with the
           exact fill (`faces`, the copy), the import with the `fill` and `faces` mappings, and for the FDM the drawn board with `face_fill=False`. Error against `out/fem.json`.
         * `spread`: the ten turned and shifted boards of validation 40 (`sq_in` 200 W/m2K at 0.5 and 1 mm, `sq_pad` 1 mm, `L_in` 0.5 mm), program and copy at 10, 20 and 40 pixels per cell.
         * `neigh`: vias under the part on stripes, a 2 mm metal block on the bottom, three parts and a hatch zone over a solid zone; FVM and FDM, program against the copy; the rim shares;
           the fill of the copy against the program's maximum rule sampled 64 x 64.
         * `mem one <board> <fvm|fdm> <program|patched> <cell>` / `mem all`: peak resident memory of a fresh process against `memory.check` plus the term
           4 B per pixel per cut layer (the float32 raster held) + `FACES_BYTES_PER_PIXEL` x pixels + `FACES_FIXED_BYTES`.
         The frozen-number check of the review (README 11.1) runs `tests/regression/test_frozen_numbers.py` on a copy of the tree OUTSIDE the repository whose
         `fvm.Network.__init__` and `fdm.Network.__init__` call `patched.source_of` when `faces is None`; it is described in the README, not scripted here (it edits a copy of the program).
"""
import contextlib
import os
import resource
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "imported-copper-edge-film", "scripts"))
import numpy as np                                                        # noqa: E402
import dc_cases as D                                                      # noqa: E402
import patched as P                                                       # noqa: E402
from pcbthermal import copper, fdm, fvm, laminate                         # noqa: E402
from pcbthermal.geometry import exact_coverage                            # noqa: E402


def exact_zone_fill(zones, L, nx, ny, dx, dy, samples=4):
    """!
    @brief Drop-in for `geometry.zone_fill` with the exact area (sum of the exact shares clipped to the largest fill, as the copy).
    @param zones Zones.
    @param L Layers.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width m.
    @param dy Cell height m.
    @param samples Unused (signature of zone_fill).
    @return array (L, ny, nx).
    """
    out = np.zeros((L, ny, nx))
    top = np.zeros(L)
    for z in zones:
        e = exact_coverage(np.asarray(z.polygon), nx, ny, dx, dy) * z.fill
        top[z.layer] = max(top[z.layer], z.fill)
        out[z.layer] = np.minimum(out[z.layer] + e, top[z.layer])
    return out


@contextlib.contextmanager
def exact_fill():
    """!
    @brief The drawn path with the exact cell fill and the program's own face rules.
    @return Context manager.
    """
    a, b, c = fvm.zone_fill, fdm.zone_fill, copper.zone_fill
    fvm.zone_fill = fdm.zone_fill = copper.zone_fill = exact_zone_fill
    try:
        yield
    finally:
        fvm.zone_fill, fdm.zone_fill, copper.zone_fill = a, b, c


@contextlib.contextmanager
def no_override():
    """!
    @brief Keep the 4 x 4 fill of the zones under the imported faces (the raster sets the faces only).
    @return Context manager.
    """
    a = copper.override_fill
    copper.override_fill = lambda *x, **k: None
    try:
        yield
    finally:
        copper.override_fill = a


def fdm_mean(p, cell, face_fill=True):
    """!
    @brief FDM heater mean rise with the face-fill switch.
    @param p Problem.
    @param cell Cell mm.
    @param face_fill The FDM face rule of validation 47.
    @return float K.
    """
    net = fdm.Network(p, cell, face_fill=face_fill)
    r = fdm.solve_steady(p, cell_mm=cell, face_fill=face_fill)
    T = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - r.ambient)).sum() / w.sum())


def reading(model, p, cell, var):
    """!
    @brief Heater mean of one reading.
    @param model 'fvm' or 'fdm'.
    @param p Problem.
    @param cell Cell mm.
    @param var Reading name (see the file header).
    @return float K.
    """
    f = (lambda q, c: D.heater_mean_fvm(q, c)[0]) if model == "fvm" else fdm_mean
    if var == "drawn":
        return f(p, cell)
    if var == "exactfill":
        with exact_fill():
            return f(p, cell)
    if var == "faces":
        with P.use("faces"):
            return f(p, cell)
    if var == "faces_4x4fill":
        with P.use("faces"), no_override():
            return f(p, cell)
    if var == "fdm_noface":
        return fdm_mean(p, cell, face_fill=False)
    return f(D.zones_to_imported(p, cell, var[4:]), cell)                # imp_fill, imp_faces


def decomp(lam):
    """!
    @brief Print the decomposition table.
    @param lam 'n4' (default rule) or 'n1' (one sub-gap).
    @return None.
    """
    import study_decomposition as SD
    for model in ("fvm", "fdm"):
        vars_ = ["drawn", "exactfill", "faces_4x4fill", "faces", "imp_fill", "imp_faces"] + (["fdm_noface"] if model == "fdm" else [])
        for name, hs in (("plain_inset", 200), ("stripes", 200), ("ell", 200), ("plain_inset", 1000), ("stripes", 1000)):
            ref = SD.fem_ref(name, hs, 2)[1]
            p = D.problem(D.case(name, float(hs)))
            line = f"{model} {name:11s} {hs:4d} "
            for var in vars_:
                vals = []
                for cell in (1.0, 0.5):
                    if lam == "n1":
                        with laminate.using(10.0, 1):
                            v = reading(model, p, cell, var)
                    else:
                        v = reading(model, p, cell, var)
                    vals.append(100 * (v / ref - 1))
                line += f"| {var} {vals[0]:+.1f}/{vals[1]:+.1f} "
            print(line, flush=True)


def spread():
    """!
    @brief Print the spread of the ten outline boards against the pixels per cell.
    @return None.
    """
    import study_drawn_film as S
    for name, h, cell in (("sq_in", 200.0, 0.5), ("sq_pad", 200.0, 1.0), ("L_in", 200.0, 0.5), ("sq_in", 200.0, 1.0)):
        spec, tr = S.CASES[name], S.truth_of(name, h)
        for mode in ("base", 10, 20, 40):
            vals = []
            for sh in S.SHIFTS:
                for ang in S.ANGLES:
                    p = S.build(spec, h, ang, sh * cell)
                    if mode == "base":
                        vals.append(S.heater_rise(p, cell)[0])
                    else:
                        P.STATE["pix"] = mode
                        with P.use("faces"):
                            vals.append(S.heater_rise(p, cell)[0])
                        P.STATE["pix"] = P.PIX_PER_CELL
            e = 100 * (np.array(vals) / tr - 1)
            print(f"{name} {h:g} {cell:g} pix={mode}: mean {e.mean():+.2f} spread {np.ptp(e):.2f} worst {np.abs(e).max():.2f} | " + " ".join(f"{x:+.2f}" for x in e), flush=True)


def neigh():
    """!
    @brief Vias, a metal block, several parts and overlapping zones through the copy.
    @return None.
    """
    from pcbthermal import Problem, geometry, viawell

    def vias():
        p = D.problem(D.case("stripes", 200.0))
        p.add_via_array((7.3, 7.3, 12.7, 12.7), 3, 3, diameter=0.3)
        p.add_via(3.0, 2.0, diameter=0.3)
        return p

    def block():
        p = D.problem(D.case("stripes", 200.0))
        p.add_heatsink(2, 20.0, rect=(4, 4, 16, 16), thickness_mm=2.0)
        return p

    def parts_overlap():
        p = Problem.new(30.0, 20.0, 2, h_side=200.0)
        p.board.h_top = p.board.h_bottom = 10.0
        p.add_zone(1, rect=(1.3, 1.3, 28.7, 18.7), fill=1.0)
        p.add_zone(1, rect=(10.1, 5.1, 20.3, 15.3), fill=0.5)
        p.add_zone(1, rect=(21.7, 3.3, 27.7, 9.3), fill=0.3)
        p.add_zone(2, rect=(0.7, 0.7, 29.3, 19.3), fill=1.0)
        for i, (x, y) in enumerate(((5.2, 5.2), (15.1, 10.1), (24.6, 6.4))):
            p.add_heater(1, 1.0, rect=(x - 1.5, y - 1.5, x + 1.5, y + 1.5), name=f"U{i}")
        return p

    for name, mk in (("vias", vias), ("block", block), ("parts_overlap", parts_overlap)):
        p = mk()
        for cell in (1.0, 0.5, 0.25):
            for mod in (fvm, fdm):
                a = mod.solve_steady(p, cell_mm=cell)
                with P.use("faces"):
                    b = mod.solve_steady(p, cell_mm=cell)
                print(f"{name} {mod.__name__[-3:]} {cell:g}: hottest rise {a.t_max - a.ambient:.2f} -> {b.t_max - b.ambient:.2f} K, balance {a.balance_error:.1e} -> {b.balance_error:.1e}", flush=True)
        if p.vias:
            zi = viawell._zone_index(p, p.board.layers)
            print("  rim shares of the last two vias", [viawell.rim_copper_shares(p, v, p.board.layers, zi) for v in p.vias[-2:]])
    p = parts_overlap()
    r = D.zone_rasters(p, 0.1, quantise=False)[0][::-1] / 255.0
    cop = r.reshape(20, 10, 30, 10).mean(axis=(1, 3))
    ref = geometry.zone_fill(p.zones, 2, 30, 20, 1e-3, 1e-3, 64)[0]
    print("overlapping zones, top layer: largest difference of the cell fill, copy against the maximum rule (64 x 64 samples):", float(np.abs(cop - ref).max()))


def mem_board(name):
    """!
    @brief The boards of the memory check.
    @param name 'ell' (60 x 40 mm, turned L), 'cost' (the board of study_cost.py), 'big2l' (200 x 150 mm, stripes, 8 parts).
    @return Problem.
    """
    import math
    from pcbthermal import Problem
    if name == "cost":
        import study_cost
        return study_cost.big()
    if name == "big2l":
        p = Problem.new(200.0, 150.0, 2, h_side=10.0)
        p.board.h_top = p.board.h_bottom = 10.0
        p.add_zone(2, polygon=[[1.5, 1.5], [198.5, 1.5], [198.5, 148.5], [1.5, 148.5]])
        y = 1.5
        while y < 148.5 - 1e-9:
            p.add_zone(1, polygon=[[1.5, y], [198.5, y], [198.5, min(y + 1.2, 148.5)], [1.5, min(y + 1.2, 148.5)]])
            y += 2.4
        for i in range(8):
            cx, cy = 25 + 50 * (i % 4), 40 + 70 * (i // 4)
            p.add_heater(1, 1.0, polygon=[[cx - 3, cy - 3], [cx + 3, cy - 3], [cx + 3, cy + 3], [cx - 3, cy + 3]], name=f"U{i}")
        return p
    p = Problem.new(60.0, 40.0, 2, h_side=50.0)
    p.board.h_top = p.board.h_bottom = 10.0
    a = math.radians(20)
    c, s = math.cos(a), math.sin(a)
    ell = [[5, 5], [45, 5], [45, 15], [15, 15], [15, 35], [5, 35]]
    p.add_zone(1, polygon=[[30 + (x - 25) * c - (y - 20) * s, 20 + (x - 25) * s + (y - 20) * c] for x, y in ell])
    p.add_zone(2, polygon=[[1.3, 1.3], [58.7, 1.3], [58.7, 38.7], [1.3, 38.7]])
    p.add_heater(1, 2.0, polygon=[[8, 8], [12, 8], [12, 12], [8, 12]], name="U")
    return p


def mem_one(bname, model, mode, cell):
    """!
    @brief One run in this process: peak memory against the estimate.
    @param bname Board name.
    @param model 'fvm' or 'fdm'.
    @param mode 'program' or 'patched'.
    @param cell Cell mm.
    @return None.
    """
    from pcbthermal import memory
    p = mem_board(bname)
    v = memory.check(p, [model], cell, refuse="none", quiet=True, base=memory.resident_bytes())[0]
    nx, ny = int(round(p.board.width * 1e3 / cell)), int(round(p.board.height * 1e3 / cell))
    cut = P.layers_with_cut_cells(p, nx, ny)
    px = nx * ny * P.PIX_PER_CELL ** 2
    term = (4.0 * px * len(cut) + memory.FACES_BYTES_PER_PIXEL * px + memory.FACES_FIXED_BYTES) if cut else 0.0
    t0 = time.time()
    mod = fvm if model == "fvm" else fdm
    if mode == "patched":
        with P.use("faces"):
            r = mod.solve_steady(p, cell_mm=cell)
    else:
        r = mod.solve_steady(p, cell_mm=cell)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss                    # bytes on macOS
    est = v.estimate + (term if mode == "patched" else 0.0)
    print(f"{bname} {model} {mode} {cell:g} mm: {time.time() - t0:.1f} s peak {peak / 1e6:.0f} MB, estimate {est / 1e6:.0f} MB (term {term / 1e6:.0f} MB, cut layers {len(cut)}), "
          f"peak/estimate {peak / est:.2f}, rise {r.t_max - r.ambient:.2f} K", flush=True)


def main():
    """!
    @brief Dispatch the subcommands.
    @return None.
    """
    cmd = sys.argv[1]
    if cmd == "decomp":
        decomp(sys.argv[2] if len(sys.argv) > 2 else "n4")
    elif cmd == "spread":
        spread()
    elif cmd == "neigh":
        neigh()
    elif cmd == "mem" and sys.argv[2] == "one":
        mem_one(sys.argv[3], sys.argv[4], sys.argv[5], float(sys.argv[6]))
    elif cmd == "mem":
        for b in ("ell", "cost", "big2l"):
            for cell in (1.0, 0.5):
                for model in ("fvm", "fdm"):
                    for mode in ("program", "patched"):
                        subprocess.run([sys.executable, __file__, "mem", "one", b, model, mode, str(cell)], check=False)


if __name__ == "__main__":
    main()
