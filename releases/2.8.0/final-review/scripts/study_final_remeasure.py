#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_final_remeasure.py
@brief Final review of 2.8.0: re-measure, on the final tree, the Lumped numbers of docs/validation.md 18.2, 31, 35.3, 42.1/42.3, 48 and the imported-copper warning that were measured before the images of the sides in the Lumped first link (section 53) or the film term (section 55).
@details Every run goes through `pcbthermal.api.simulate` with the program as it ships (no patch, no copy). Sub-commands, one per section (each prints a Markdown table):
         * `ring`     validation 31.1 (simple boards, 1 and 3 mm sources), 31.6 (the hot rectangles and the tab), the 1 mm part against the independent layered solver
                      `tests/helpers/layered3d.py`, and the reconstructed boards of 31.4 (Lumped at 0.5 mm against the FVM at 0.5 mm, or 0.25 mm where the section says so);
         * `subcell`  validation 35.3 (24 x 24 mm, sources of 0.2 to 2 mm on a cell corner and inside a cell, Lumped at the 0.5 and 1 mm requests against the FVM at 0.0625 mm);
         * `zones`    validation 18.2 (the 36 family and 26 held-out via boards of `research/lumped-via-groups`, built by its `lib/refs.make_problem`): via effect and hottest
                      temperature of the Lumped at 0.5 mm against the FVM at 0.25 mm (not the 1/16 mm layered reference of the research, which is not re-run here);
         * `farvia`   validation 42.1 and 42.3 (the 60 x 60 mm board of `research/small-model-defects`, one far via, 1 mm cell);
         * `readout`  validation 48.1 and the reconstructable rows of 48.3 (Lumped-only part rows against the FVM part rows at 0.5 mm);
         * `unrefined` the small-part warning text (`checks.check_lumped_small_part`): sources of 0.1 to 0.5 mm on the 0.5 mm raster that is not refined;
         * `imported` the warning on imported copper (`copper.REDUCED_MODEL_WARNING`): one part at a time, 1 W, 0.5 mm, FVM / Lumped / Analytic board maximum on the
                      imported board of the library (`PCBT_REAL_BOARDS`); arguments: board name and an optional comma-separated list of designators.
         Run from the repository root, one sub-command at a time (peaks: ring 1.5 GB, subcell 1 GB, zones 1.5 GB, imported 0.7 GB for rp2040 and oswlight, about 4 GB for co60):
         QT_QPA_PLATFORM=offscreen .venv/bin/python releases/2.8.0/final-review/scripts/study_final_remeasure.py ring
"""

import copy
import importlib.util
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pcbthermal import Problem, SolverOptions, simulate  # noqa: E402
from pcbthermal.model import Materials  # noqa: E402


def rise(p, model, cell, **opts):
    """!
    @brief Rise of the board maximum of one model above the ambient.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @param opts Further SolverOptions fields.
    @return float K.
    """
    r = simulate(p, SolverOptions(models=(model,), cell_mm=cell, **opts)).results[model]
    return float(r.t_max - p.board.ambient)


def pct(model, ref):
    """!
    @brief Error of a rise in percent of the reference rise.
    @param model Rise of the model in K.
    @param ref Rise of the reference in K.
    @return float percent.
    """
    return 100.0 * (model / ref - 1.0)


def simple(w, h, side_x, side_y=None, pos=None, h_top=10.0, h_bot=15.0, h_side=10.0, layers=2, materials=None, thickness_mm=1.6, ambient=25.0):
    """!
    @brief A two-layer full-copper board with one 1 W rectangular source on layer 1 (the boards of validation 31).
    @param w Width in mm.
    @param h Height in mm.
    @param side_x Side of the source along x in mm.
    @param side_y Side along y in mm (None: square).
    @param pos Centre (x, y) in mm (None: the board centre).
    @param h_top Top film in W/m2K.
    @param h_bot Bottom film in W/m2K.
    @param h_side Edge film in W/m2K (None: insulated).
    @param layers Copper layers.
    @param materials Materials or None (defaults).
    @param thickness_mm Board thickness in mm.
    @param ambient Ambient in degC.
    @return Problem.
    """
    side_y = side_x if side_y is None else side_y
    cx, cy = pos if pos is not None else (w / 2, h / 2)
    kw = dict(materials=materials) if materials is not None else {}
    p = Problem.new(w, h, layers=layers, thickness_mm=thickness_mm, copper_um=35.0, h_top=h_top, h_bottom=h_bot, h_side=h_side, ambient=ambient, **kw)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(cx - side_x / 2, cy - side_y / 2, cx + side_x / 2, cy + side_y / 2), name="U")
    return p


def cmd_ring():
    """!
    @brief Validation 31: the first ring on simple boards, the hot rectangles, the independent 3D check and the reconstructed review boards.
    @return None.
    """
    print("### 31.1 board size: Lumped 0.5 mm against the FVM 0.5 mm (hottest rise)")
    print("| board (mm) | source (mm) | FVM (K) | Lumped (K) | Lumped % |")
    print("| :-- | --: | --: | --: | --: |")
    for w, h in [(30, 20), (60, 40), (100, 80), (200, 150)]:
        for s in (1.0, 3.0):
            p = simple(w, h, s)
            f, l = rise(p, "fvm", 0.5), rise(p, "lumped", 0.5)
            print(f"| {w} x {h} | {s:g} | {f:.2f} | {l:.2f} | {pct(l, f):+.1f} |", flush=True)
    print("\n### 31.6 hot rectangles and the tab (2 layers, films 10/15, edge 10; reference FVM 0.25 mm for sources up to 3 mm on 100 x 80, else 0.5 mm)")
    print("| board | source | Lumped cell | FVM (K) | Lumped (K) | Lumped % |")
    print("| :-- | :-- | --: | --: | --: | --: |")
    cases = [((60, 40), (3, 1), 0.5), ((100, 80), (3, 1), 0.5), ((200, 150), (3, 1), 0.5), ((100, 80), (6, 2), 0.5), ((100, 80), (6, 2), 1.0),
             ((200, 150), (6, 2), 0.5), ((200, 150), (6, 2), 1.0), ((100, 80), (10, 0.5), 0.5), ((100, 80), (1, 1), 1.0), ((200, 150), (1, 1), 1.0)]
    refs = {}
    for (w, h), (sx, sy), cell in cases:
        p = simple(w, h, sx, sy)
        ref_cell = 0.25 if (w == 100 and max(sx, sy) <= 3) else 0.5
        key = (w, h, sx, sy, ref_cell)
        if key not in refs:
            refs[key] = rise(p, "fvm", ref_cell)
        l = rise(p, "lumped", cell)
        print(f"| {w} x {h} | {sx:g} x {sy:g} | {cell:g} | {refs[key]:.2f} ({ref_cell:g}) | {l:.2f} | {pct(l, refs[key]):+.1f} |", flush=True)
    print("\n### 31, the 1 mm part on 100 x 80 mm against the independent layered solver (films 10/10 also under the source, insulated sides, isotropic laminate 0.4, copper 400, 0.5 mm, 2 sub-slabs)")
    sys.path.insert(0, str(ROOT / "tests" / "helpers"))
    import layered3d as L3
    mat = Materials(k_copper=400.0, k_fr4_through=0.4, k_fr4_inplane=0.4)
    p = simple(100, 80, 1.0, h_top=10.0, h_bot=10.0, h_side=None, materials=mat, ambient=0.0)
    gap = 1.6e-3 - 2 * 35e-6
    for sub in (2, 8):
        res = L3.solve(0.5e-3, 200, 160, [(35e-6, 400.0, 1), (gap, 0.4, sub), (35e-6, 400.0, 1)], (49.5e-3, 39.5e-3, 50.5e-3, 40.5e-3), 1.0, 10.0, 10.0, film_under_source=True)
        print(f"3D ({sub} sub-slabs): hottest source cell {res['cell_max_source']:.3f} K, surface max {res['max_source']:.3f} K", flush=True)
    f, l = rise(p, "fvm", 0.5), rise(p, "lumped", 0.5)
    print(f"program: FVM 0.5 {f:.3f} K, Lumped {l:.3f} K", flush=True)
    print("\n### 31.4 reconstructed review boards (Lumped 0.5 against FVM 0.5)")
    print("| board | FVM (K) | Lumped (K) | Lumped % |")
    print("| :-- | --: | --: | --: |")
    rows = []
    q = simple(150, 100, 2.0, h_bot=10.0)
    q.add_heatsink(2, 0.0, rect=(45, 25, 105, 75), thickness_mm=3.0, k=204.0, contact_r=5e-4)
    rows.append(("2 mm part, 150 x 100 mm, films 10/10, 60 x 50 x 3 mm Al block (contact 5 K cm2/W assumed)", q))
    rows.append(("1 mm part in the corner of 200 x 150 mm (centre 0.5 mm from both sides)", simple(200, 150, 1.0, pos=(0.5, 0.5))))
    rows.append(("1 mm part at (1.5, 75) on 200 x 150 mm (1 mm from the side)", simple(200, 150, 1.0, pos=(1.5, 75.0))))
    rows.append(("2 mm part half off the edge of 200 x 150 mm (centre on the side)", simple(200, 150, 2.0, pos=(0.0, 75.0))))
    rows.append(("1 mm part across cell edges of 200 x 150 mm (nine cells touched)", simple(200, 150, 1.0, pos=(100.25, 75.25))))
    rows.append(("40 x 0.5 mm strip at the centre of 200 x 150 mm", simple(200, 150, 40.0, 0.5)))
    for name, q in rows:
        f, l = rise(q, "fvm", 0.5), rise(q, "lumped", 0.5)
        print(f"| {name} | {f:.2f} | {l:.2f} | {pct(l, f):+.1f} |", flush=True)


def cmd_subcell():
    """!
    @brief Validation 35.3: a source under two cells, the finer raster, against the FVM at 0.0625 mm.
    @return None.
    """
    for request, shift_in in ((0.5, 0.25), (1.0, 0.5)):
        print(f"\n### 35.3 request {request:g} mm (corner = shift 0, in a cell = shift {shift_in:g} mm)")
        print("| side mm | FVM 0.0625 corner / in a cell (K) | Lumped corner % | Lumped in a cell % |")
        print("| --: | :-- | --: | --: |")
        for side in (0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0):
            out = []
            for sh in (0.0, shift_in):
                p = simple(24.0, 24.0, side, pos=(12.0 + sh, 12.0 + sh))
                f = rise(p, "fvm", 0.0625)
                l = rise(p, "lumped", request)
                out.append((f, pct(l, f)))
            print(f"| {side:g} | {out[0][0]:.2f} / {out[1][0]:.2f} | {out[0][1]:+.1f} | {out[1][1]:+.1f} |", flush=True)


def _load(path, name):
    """!
    @brief Import a research script by path (it is guarded by `if __name__ == "__main__"`).
    @param path Path of the file.
    @param name Module name to give it.
    @return module.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_zones():
    """!
    @brief Validation 18.2: the 62 via boards, Lumped at 0.5 mm against the FVM at 0.25 mm (via effect and hottest temperature).
    @return None.
    """
    folder = ROOT / "research" / "lumped-via-groups"
    sys.path.insert(0, str(folder / "lib"))
    import refs
    fam = _load(folder / "scripts" / "study_family.py", "study_family")
    hold = _load(folder / "scripts" / "study_holdout.py", "study_holdout")
    sets = [("family", [(None, s) for s in fam.specs(False)]), ("held-out", hold.holdout_specs())]
    out = {}
    print("| set | board | zoned | FVM rise (K) | E FVM (K) | E Lumped (K) | via effect % | hottest % |")
    print("| :-- | :-- | :-- | --: | --: | --: | --: | --: |")
    for label, items in sets:
        rows = []
        for name, spec in items:
            p = refs.make_problem(spec)
            q = copy.deepcopy(p)
            q.vias = []
            amb = p.board.ambient
            sl = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
            tl = float(sl.t_max - amb)
            zoned = bool(np.asarray(sl.arrays.get("zoned_heaters", [[0]]))[0][0]) if "zoned_heaters" in sl.arrays else False
            tl0 = rise(q, "lumped", 0.5)
            tf, tf0 = rise(p, "fvm", 0.25), rise(q, "fvm", 0.25)
            ef, el = tf0 - tf, tl0 - tl
            row = dict(name=name or json.dumps(spec), zoned=zoned, tf=tf, ef=ef, el=el, e_pct=pct(el, ef), t_pct=pct(tl, tf))
            rows.append(row)
            print(f"| {label} | {row['name']} | {'yes' if zoned else 'no'} | {tf:.2f} | {ef:.3f} | {el:.3f} | {row['e_pct']:+.1f} | {row['t_pct']:+.2f} |", flush=True)
        out[label] = rows
    print()
    for label, rows in out.items():
        for sub, sel in (("all", rows), ("zoned", [r for r in rows if r["zoned"]]), ("one node", [r for r in rows if not r["zoned"]])):
            if not sel:
                continue
            e = np.array([abs(r["e_pct"]) for r in sel])
            t = np.array([r["t_pct"] for r in sel])
            print(f"{label} {sub} (n {len(sel)}): via effect |err| mean {e.mean():.1f} max {e.max():.1f} ({int((e <= 10).sum())} within 10 %); hottest |err| mean {np.abs(t).mean():.2f} "
                  f"max {np.abs(t).max():.2f}, range {t.min():+.2f} .. {t.max():+.2f} ({int((t < -2).sum())} more than 2 % too cool)")


def cmd_farvia():
    """!
    @brief Validation 42.1 and 42.3: one via far from the part, 60 x 60 mm board, cell 1 mm (and the 4 x 4 array at 0.5 mm).
    @return None.
    """
    def board(vias, layers=2):
        """!
        @brief The board of research/small-model-defects study_far_via.py.
        @param vias List of (x, y) in mm.
        @param layers Copper layers.
        @return Problem.
        """
        p = Problem.new(60, 60, layers=layers, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
        p.add_full_copper()
        p.add_heater(1, 5.0, rect=(26, 26, 34, 34), name="U")
        for v in vias:
            p.add_via(*v, diameter=0.3)
        return p

    def array(n):
        """!
        @brief The via group under the part (study_far_via.array).
        @param n Number of vias (0, 1, 2, 4, 16).
        @return list of (x, y).
        """
        if n == 0:
            return []
        if n == 1:
            return [(30.0, 30.0)]
        side = {2: (2, 1), 4: (2, 2), 16: (4, 4)}[n]
        return [(30 - (side[0] - 1) + 2 * i, 30 - (side[1] - 1) + 2 * j) for i in range(side[0]) for j in range(side[1])]

    def tm(vias, cell, model):
        """!
        @brief Board maximum of one model.
        @param vias List of vias.
        @param cell Cell in mm.
        @param model Model key.
        @return float degC.
        """
        return float(simulate(board(vias), SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max)

    print("### 42.1 change of the hottest temperature (K) when one via is added 25 mm from the part centre, 1 mm")
    print("| vias under the part | FVM | Lumped |")
    print("| --: | --: | --: |")
    for n in (0, 1, 2, 4, 16):
        d = {m: tm(array(n) + [(5.0, 30.0)], 1.0, m) - tm(array(n), 1.0, m) for m in ("fvm", "lumped")}
        print(f"| {n} | {d['fvm']:+.3f} | {d['lumped']:+.3f} |", flush=True)
    d = {m: tm(array(16) + [(5.0, 30.0)], 0.5, m) - tm(array(16), 0.5, m) for m in ("fvm", "lumped")}
    print(f"4 x 4 and one far via at 0.5 mm: FVM {d['fvm']:+.3f}, Lumped {d['lumped']:+.3f}")
    print("\n### 42.3 a via one, two, three pitches beyond the edge of the 4 x 4 array at 2 mm pitch (edge vias at 27 and 33 mm), 1 mm")
    for k, dist in ((1, 2.0), (2, 4.0), (3, 6.0)):
        d = {m: tm(array(16) + [(33.0 + dist, 30.0)], 1.0, m) - tm(array(16), 1.0, m) for m in ("fvm", "lumped")}
        print(f"{k} pitch(es) ({dist:g} mm beyond the edge): FVM {d['fvm']:+.3f}, Lumped {d['lumped']:+.3f}", flush=True)


def cmd_readout():
    """!
    @brief Validation 48.1 and 48.3: part rows of a Lumped-only run against the FVM part rows, cell 0.5 mm.
    @return None.
    """
    def rows(p, model):
        """!
        @brief Part rows of one model run alone.
        @param p Problem.
        @param model Model key.
        @return list of part rises in K.
        """
        sim = simulate(p, SolverOptions(models=(model,), cell_mm=0.5))
        return [r["t_max"] - p.board.ambient for r in sim.heater_rows()]

    boards = []
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80)).add_zone(2, rect=(44, 34, 56, 46))
    p.add_heater(1, 5.0, rect=(47, 37, 53, 43))
    p.add_heatsink(2, 0.0, rect=(10, 10, 90, 70), thickness_mm=1.5, k=204.0, contact_r=5e-4)
    boards.append(("one 12 mm pad, aluminium plate 80 x 60 x 1.5 mm, 5 W", p))
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80))
    p.add_heater(1, 3.0, rect=(47, 37, 53, 43))
    boards.append(("plain plane, one 6 mm part, 3 W", p))
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80))
    p.add_heater(1, 2.0, rect=(30, 37, 36, 43))
    p.add_heater(1, 1.0, rect=(64, 37, 70, 43))
    p.heaters[0].theta = 5.0
    boards.append(("two parts (2 W and 1 W, the first with theta 5 K/W)", p))
    p = Problem.new(100.0, 80.0, 2).add_full_copper()
    p.add_heater(1, 3.0, rect=(47, 37, 53, 43))
    boards.append(("6 mm part on two full planes, 3 W", p))
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80))
    p.add_heater(1, 2.0, rect=(40, 37, 46, 43))
    p.add_heater(1, 2.0, rect=(48, 37, 54, 43))
    boards.append(("two 2 W parts 2 mm apart", p))
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80)).add_zone(2, rect=(0, 0, 100, 80))
    p.set_outline([[0, 0], [100, 0], [100, 40], [50, 40], [50, 80], [0, 80]])
    p.add_heater(1, 2.0, rect=(22, 37, 28, 43))
    boards.append(("L-shaped outline (equivalent rectangle), 2 W", p))
    p = Problem.new(100.0, 80.0, 4).add_full_copper()
    p.add_heater(1, 4.0, rect=(47, 37, 53, 43))
    boards.append(("4 layers of full planes, 4 W", p))
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(30, 20, 70, 60))
    p.add_heater(1, 3.0, rect=(47, 37, 53, 43), theta=2.0, theta_jc_top=5.0, theta_sa=10.0)
    boards.append(("top path (theta 2, theta_JC 5, theta_SA 10 K/W), 40 mm pad, 3 W", p))
    print("| board | FVM part rise (K) | Lumped part row (K) | % |")
    print("| :-- | :-- | :-- | :-- |")
    for name, p in boards:
        f, l = rows(p, "fvm"), rows(p, "lumped")
        print(f"| {name} | {' / '.join(f'{v:.1f}' for v in f)} | {' / '.join(f'{v:.1f}' for v in l)} | {' / '.join(f'{pct(b, a):+.1f}' for a, b in zip(f, l))} |", flush=True)


def cmd_imported(board, only=None):
    """!
    @brief The imported-copper warning: one part at a time, 1 W, 0.5 mm, FVM / Lumped / Analytic board maximum.
    @param board Library board name (rp2040, oswlight, co60).
    @param only Optional list of designators.
    @return None.
    """
    sys.path.insert(0, str(ROOT / "research" / "reduced-models-imported-passives" / "lib"))
    import variants as V
    sx, prob = V.open_board(board, 0.5)
    names = [h.name for h in prob.heaters if only is None or h.name in only]
    print(f"### {board}: {len(names)} heat sources, 1 W each, 0.5 mm")
    print("| part | side mm | FVM (K) | Lumped (K) | Lumped % | Analytic (K) | Analytic % | s |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: |")
    res = []
    for n in names:
        t0 = time.time()
        q = V.only_heater(prob, n)
        poly = np.asarray(q.heaters[0].polygon) * 1e3
        side = float(min(np.ptp(poly[:, 0]), np.ptp(poly[:, 1])))
        sim = simulate(q, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=0.5))
        r = {m: float(sim.results[m].t_max - q.board.ambient) for m in ("fvm", "lumped", "analytic")}
        res.append(dict(part=n, side=side, **r))
        print(f"| {n} | {side:.2f} | {r['fvm']:.1f} | {r['lumped']:.1f} | {pct(r['lumped'], r['fvm']):+.1f} | {r['analytic']:.1f} | {pct(r['analytic'], r['fvm']):+.1f} | "
              f"{time.time() - t0:.0f} |", flush=True)
    el = [pct(r["lumped"], r["fvm"]) for r in res]
    ea = [pct(r["analytic"], r["fvm"]) for r in res]
    small = [r for r in res if r["side"] < 1.5]
    print(f"{board}: Lumped {min(el):+.1f} .. {max(el):+.1f} %, Analytic {min(ea):+.1f} .. {max(ea):+.1f} %", end="")
    if small:
        print(f"; side < 1.5 mm (n {len(small)}): Lumped {min(pct(r['lumped'], r['fvm']) for r in small):+.1f} .. {max(pct(r['lumped'], r['fvm']) for r in small):+.1f} %, "
              f"Analytic {min(pct(r['analytic'], r['fvm']) for r in small):+.1f} .. {max(pct(r['analytic'], r['fvm']) for r in small):+.1f} %", end="")
    print(f"; peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30:.2f} GB")


def cmd_unrefined():
    """!
    @brief The text of the small-part warning (a raster that cannot be refined): the Lumped at its 0.5 and 1 mm rasters, called directly (no refinement), against the FVM at 0.0625 mm.
    @return None.
    """
    from pcbthermal import lumped
    refs = {}
    for raster in (0.5, 1.0):
        print(f"### small part on the unrefined {raster:g} mm raster (24 x 24 mm, 1 W)")
        print("| side mm | shift mm | FVM 0.0625 (K) | Lumped unrefined % |")
        print("| --: | --: | --: | --: |")
        errs = []
        for side in (0.1, 0.2, 0.3, 0.5):
            for sh in (0.0, raster / 4, raster / 2):
                p = simple(24.0, 24.0, side, pos=(12.0 + sh, 12.0 + sh))
                if (side, sh) not in refs:
                    refs[(side, sh)] = rise(p, "fvm", 0.0625)
                f = refs[(side, sh)]
                l = float(lumped.solve_steady(p, cell_mm=raster).t_max - p.board.ambient)
                errs.append(pct(l, f))
                print(f"| {side:g} | {sh:g} | {f:.2f} | {errs[-1]:+.1f} |", flush=True)
        print(f"raster {raster:g} mm: range {min(errs):+.1f} .. {max(errs):+.1f} %\n")

def main(argv):
    """!
    @brief Dispatch the sub-command.
    @param argv Command line.
    @return int Exit code.
    """
    cmd = argv[1] if len(argv) > 1 else "ring"
    t0 = time.time()
    if cmd == "imported":
        cmd_imported(argv[2], argv[3].split(",") if len(argv) > 3 else None)
    else:
        {"ring": cmd_ring, "subcell": cmd_subcell, "zones": cmd_zones, "farvia": cmd_farvia, "readout": cmd_readout, "unrefined": cmd_unrefined}[cmd]()
    print(f"\n{cmd}: {time.time() - t0:.0f} s, peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30:.2f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
