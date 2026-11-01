#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_thick_laminate.py
@brief Study S2 "thick anisotropic laminate": does the laminate sub-gap rule of 2.4.5 (at most 4 sub-gaps of 0.4 mm) carry a thick, anisotropic FR-4 under a small source, judged against the
       published closed form of Muzychka, Yovanovich and Culham (2004, equation 50) and against an independent resolved 3D solver? Written and checked only; not yet run.
@details Question: the error of the layered models under a small source on a thick anisotropic laminate (our own 3D reference gave -18.44 % to -3.07 % at 1.6 mm and -34.19 % to -9.13 % at 3.2 mm
         for a 6 mm window, README of research/laminate-nodes); is that error real, and does a finer rule (the new options laminate_s_max_mm, laminate_n_max) remove it?
         Independent references (nothing of the program): (1) the closed form `lib/flux_channel.py` (equation 50 with the orthotropic transformation, read from the page image), valid for a source on
         bare laminate with a cooled base; (2) `research/gerber-real-boards/lib/ref3d.py`, the resolved anisotropic 3D finite-volume solver (it imports nothing from the program; checked by a
         test), first validated against (1), then used where no closed form exists (a copper pad under the source).
         Cases: source S x S centred on a W x W board (S, W) in {(2, 20), (5, 20), (10, 40)} mm, thickness t in {0.8, 1.6, 3.2} mm, FR-4 (k_xy, k_z) in {(0.3, 0.3), (0.9, 0.3) [the FR-4 of the
         program], (2.7, 0.3)} W/mK, base film h in {10, 1e3, 1e6} W/m2K, top face and sides adiabatic. The full sweep is run for the program's FR-4 (0.9, 0.3); the other two ratios at
         S = 5 mm, h = 1e3 only (33 combinations). Two boards per case: "bare" (two copper layers of 35 um with no copper drawn: exactly the geometry of equation 50) and "pad" (copper under the source on
         layer 1 only: the real case, no closed form).
         Metric: the mean temperature of the source AT THE FACE per watt of the whole source, minus the film term 1 / (h W^2) which is the same in every model (energy balance), called R'.
         The face is where equation 50 reads its temperature. The 3D reference injects the heat in the cells of its top copper slab and reads them there (the node of the program's copper
         layer); on bare laminate the half slab of FR-4 above that node adds q'' t_cu / (2 k_z), 1.0 to 4.6 % of R' for these cases (review), so it is added to the reference (exact for the
         one-dimensional drop through a slab of 17.5 um under a uniform flux). The program is read with `analysis.heater_stats` (the part's mean temperature as the program reports it: the
         FVM and FDM add the same face term over absent copper; it also weights the nodes of the FDM correctly). Reported: R' of the reference, error of every model in % of R', the closed
         form against the 3D reference, and the error of the rule as a function of the options.
         Success and failure criteria (written before any run; README 3):
           L1 the 3D reference (with the face term) agrees with equation 50 to 1 % of R' for all 33 bare combinations (n_sub = 16, pixel = S / 16), and its own refinement (pixel S / 32 and
              n_sub = 32, S = 2 mm, t = 1.6 and 3.2 mm) changes it by less than 0.5 %; otherwise it is not a reference and the study stops (a defect of the reference or a transcription error
              of the equation, told apart by the limit a = c, b = d where R_s = 0, by the isotropic case and by the published deep-channel correlation of Yovanovich, Muzychka and Culham 1999,
              equation 20, which the closed form reproduces within the correlation's own 0.3 % (0.003 % for a source of 0.02 to 0.25 of the channel; tests)). R', not the total: at h = 10 the film term is 28 to 62 % of the total and would halve or hide an error.
           L2 the default rule (0.4 mm, 4) keeps the layered models (fvm, fdm) at the 0.25 mm cell within 5 % of R' at t = 1.6 and 3.2 mm, S >= 5 mm, FR-4 (0.9, 0.3), and within 10 % everywhere:
              then the rule stays and the text of theory 1.4 only gets the published check. The 0.5 mm row shows the plan grid's share of the error.
           L3 if L2 fails and a pair of options brings every row within 3 % with at most 3 times the unknowns of the default: that pair is proposed (a `fix/`, with its cost); if none does, the limit text.
           L4 solid3d within 3 %, analytic within 15 % of R' (reported, not decisive); lumped reported.
         Declared cost: closed form and the 3D reference of the 33 bare + 33 pad combinations about 10 minutes, under 1 GB (pixel S / 16, 18 slabs, at most 115 000 unknowns); the program part about 15
         minutes, at most about 3 GB (the pair (0.1, 16) on the 40 mm board at 3.2 mm: 160 x 160 cells x 17 node layers = 435 000 unknowns, about 7 GB per million for the layered models);
         `--convergence` (pixel S / 32 and n_sub = 32) about 5 minutes and at most 3 GB, to be run alone.
         Run (from the repository root): .venv/bin/python research/paper-case-studies/scripts/study_thick_laminate.py [--dry-run] [--convergence] [--no-program]
"""

import argparse
import itertools
import json
import sys

import _bootstrap
import numpy as np

import flux_channel as FC

OUT = _bootstrap.OUT
SOURCES = ((2.0, 20.0), (5.0, 20.0), (10.0, 40.0))     # (source side S, board side W) in mm
THICKNESS_MM = (0.8, 1.6, 3.2)
RATIOS = ((0.3, 0.3), (0.9, 0.3), (2.7, 0.3))          # (k_xy, k_z) in W/mK
FILMS = (10.0, 1.0e3, 1.0e6)                           # W/m2K
T_CU = 35e-6                                           # copper layer thickness of both layers (the program's default), in the "bare" board a layer of FR-4 of this thickness
OPTIONS = ((0.4, 4), (0.4, 1), (0.2, 8), (0.1, 16), (0.8, 2))   # (laminate_s_max_mm, laminate_n_max); the first is the default of 2.4.5, the second turns the cutting off
CELLS_MM = (0.5, 0.25)


def combos():
    """!
    @brief The 33 combinations of the study: the full sweep at the program's FR-4 plus the other two ratios at S = 5 mm, h = 1e3.
    @return list of dicts with S, W (mm), t (mm), kxy, kz (W/mK), h (W/m2K).
    """
    out = []
    for (s, w), t, h in itertools.product(SOURCES, THICKNESS_MM, FILMS):
        out.append({"S": s, "W": w, "t": t, "kxy": 0.9, "kz": 0.3, "h": h})
    for (kxy, kz), t in itertools.product((RATIOS[0], RATIOS[2]), THICKNESS_MM):
        out.append({"S": 5.0, "W": 20.0, "t": t, "kxy": kxy, "kz": kz, "h": 1.0e3})
    return out


def closed_form(c, n_max=2000):
    """!
    @brief Equation 50 for a combination (quarter: source S/2, channel W/2).
    @param c One dict of combos().
    @param n_max Terms of each series.
    @return tuple (R_s, R_total, R') in K/W per watt of the whole source, R' = R_total - 1 / (h W^2) (the film term of the base).
    """
    a, cc, t = c["S"] / 2e3, c["W"] / 2e3, c["t"] * 1e-3
    rs = FC.spreading_resistance(a, a, cc, cc, t, c["kxy"], c["kz"], c["h"], n_max)
    rt = FC.total_resistance(a, a, cc, cc, t, c["kxy"], c["kz"], c["h"], n_max)
    return rs, rt, rt - 1.0 / (c["h"] * (2.0 * cc) ** 2)


def reference_3d(c, pad=False, px_div=16, n_sub=16):
    """!
    @brief The resolved anisotropic 3D reference of the quarter board (source at the corner, adiabatic sides, film on the base), the mean source temperature per watt minus the film term.
    @param c One dict of combos().
    @param pad True for a copper pad under the source on layer 1 (no closed form), False for the bare board of equation 50.
    @param px_div Pixels per source side (pixel = S / px_div).
    @param n_sub Sub-slabs of the laminate gap.
    @return float R' in K/W per watt of the whole source (the quarter's rise per watt at the face, divided by 4, minus the film term of the base).
    """
    import ref3d
    s, w, t = c["S"] * 1e-3, c["W"] * 1e-3, c["t"] * 1e-3
    dx = s / px_div
    n = int(round((w / 2.0) / dx))
    xs = (np.arange(n) + 0.5) * dx
    src = (xs[None, :] < s / 2.0) & (xs[:, None] < s / 2.0)                 # the source quarter at the corner (rows from the bottom, x to the right)
    mask_top = src.copy() if pad else np.zeros((n, n), bool)
    masks = [mask_top, np.zeros((n, n), bool)]
    model = ref3d.build(masks, dx, [T_CU, T_CU], [t - 2 * T_CU], kxy_lam=c["kxy"], kz_lam=c["kz"], n_sub=n_sub, h_top=0.0, h_bottom=c["h"])
    sol = ref3d.solve(model, src, 1.0)
    mean_src, _mx = ref3d.heater_block(sol["top"], dx, 0.0, 0.0, s / 2.0, s / 2.0)
    # the face term: ref3d injects and reads at the centre of the top slab; equation 50 reads at the face, half a slab higher (FR-4 on bare laminate, copper under a pad)
    face = (1.0 / (src.sum() * dx * dx)) * (T_CU / 2.0) / (ref3d.K_CU if pad else c["kz"])
    return (mean_src + face - 1.0 / (c["h"] * (w / 2.0) ** 2)) / 4.0    # 1 W in the quarter = 4 W in the board: the same rise, a quarter of the resistance per watt


def reference_3d_extrap(c, pad=False, pxs=(6, 8, 12), nss=(16, 32)):
    """!
    @brief The 3D reference extrapolated to the continuum: Richardson in the number of sub-slabs (error 1/n^2, measured: successive differences fall by 3.3, 3.7, 3.9 for n = 4 to 64), then a quadratic in 1/pixels.
    @param c One dict of combos().
    @param pad True for the pad board.
    @param pxs Three pixel counts per source side (small ones: at most 130 000 unknowns, about 2 GB).
    @param nss Two numbers of sub-slabs for the Richardson step.
    @return float R' in K/W (the extrapolated value); the single-grid value at S/16 (reference_3d) was 1.2 to 2.6 % high on the bare cases because of the slow pixel convergence of the flux jump at the source edge.
    """
    vals = []
    for px in pxs:
        a = reference_3d(c, pad, px, nss[0])
        b = reference_3d(c, pad, px, nss[1])
        vals.append(b - (a - b) / ((nss[1] / nss[0]) ** 2 - 1.0))        # error ~ 1/n^2
    coef = np.polyfit([1.0 / px for px in pxs], vals, 2)
    return float(coef[2])


def run_program(c, model, cell_mm, s_max=0.4, n_max=4, pad=False):
    """!
    @brief The program on the full board (4 W, so that the quarter carries 1 W; R' is per watt of the board): bare laminate (two layers, nothing drawn) or a copper pad on layer 1; the same quantity R'.
    @param c One dict of combos().
    @param model "fvm", "fdm", "solid3d", "analytic" or "lumped".
    @param cell_mm Grid cell in mm.
    @param s_max laminate_s_max_mm.
    @param n_max laminate_n_max.
    @param pad True for the pad board.
    @return float R' in K/W, the mean rise of the part as the program reports it (analysis.heater_stats: face terms included, FDM nodes weighted) minus the film term; raises if the model
            refuses the board.
    """
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal import analysis
    from pcbthermal.model import Materials
    s, w = c["S"], c["W"]
    p = Problem.new(w, w, layers=2, thickness_mm=c["t"], copper_um=T_CU * 1e6, ambient=0.0, h_top=0.0, h_bottom=c["h"], h_side=0.0,
                    materials=Materials(k_copper=385.0, k_fr4_through=c["kz"], k_fr4_inplane=c["kxy"]))
    x0, x1 = (w - s) / 2.0, (w + s) / 2.0
    if pad:
        p.add_zone(1, rect=(x0, x0, x1, x1))
    p.add_heater(1, 4.0, rect=(x0, x0, x1, x1), name="U")
    opts = SolverOptions(models=(model,), cell_mm=cell_mm, laminate_s_max_mm=s_max, laminate_n_max=n_max)
    res = simulate(p, opts).results[model]
    # the part's mean as the program reports it (an earlier draft read T[0] with cell centres, wrong by half a node for the FDM node field and without the face term)
    mean_src = analysis.heater_stats(res, p)[0]["t_mean"] - p.board.ambient
    # the mean film rise of the base is 4 W / (h W^2), the same in every model (energy balance); per watt of the board
    return mean_src / 4.0 - 1.0 / (c["h"] * (w * 1e-3) ** 2)


def part_l1(convergence, heavy=False):
    """!
    @brief L1: the 3D reference against equation 50 on the 33 bare combinations (and its own refinement when asked).
    @param convergence True to add the convergence grid (cheap, about 2 GB).
    @param heavy True to add the pixel S/32 runs (8 GB resident: alone).
    @return list of rows.
    """
    rows = []
    print("\nL1.0  truncation of equation 50 for the smallest source (S = 2 mm on 20 mm), R' against the number of terms of each series")
    for t, h in ((0.8, 10.0), (3.2, 1.0e6)):
        c = {"S": 2.0, "W": 20.0, "t": t, "kxy": 0.9, "kz": 0.3, "h": h}
        vals = [closed_form(c, n)[2] for n in (1000, 2000, 4000)]
        print(f"  t {t} h {h:7.0e}: " + "  ".join(f"n {n}: {v:.5f}" for n, v in zip((1000, 2000, 4000), vals)) + f"   2000 -> 4000: {(vals[2] / vals[1] - 1) * 100:+.5f} %")
    print("\nL1  equation 50 against the resolved 3D reference (bare laminate, at the face; R' = R_total - film term, K/W)")
    print("  S   W   t    kxy  kz   h      R_s(eq50)  R'(eq50)   R'(3D)    diff % of R'   diff % of total")
    for c in combos():
        rs, rt, rp = closed_form(c)
        r3 = reference_3d(c)
        rx = reference_3d_extrap(c)
        film = 1.0 / (c["h"] * (c["W"] * 1e-3) ** 2)
        diff = (r3 - rp) / rp * 100.0
        diff_total = (r3 - rp) / (rp + film) * 100.0
        diff_x = (rx - rp) / rp * 100.0
        rows.append({**c, "rs": rs, "r_eq50": rp, "r_3d": r3, "r_3d_extrap": rx, "diff_extrap_pct": diff_x, "diff_rprime_pct": diff, "diff_total_pct": diff_total})
        print(f"  {c['S']:3.0f} {c['W']:3.0f} {c['t']:4.1f} {c['kxy']:4.1f} {c['kz']:4.1f} {c['h']:7.0e}  {rs:9.3f}  {rp:9.3f}  {r3:9.3f}   {diff:9.3f}      {diff_total:9.3f}   extrapolated {rx:9.3f} {diff_x:+7.3f} %")
    if convergence:
        print("\n  convergence grid of the 3D reference (S = 2, W = 20, kxy 0.9, h = 1e6; at most 130 000 unknowns, about 2 GB): R' per pixels per source side (rows) and sub-slabs (columns)")
        for t in (1.6, 3.2):
            c = {"S": 2.0, "W": 20.0, "t": t, "kxy": 0.9, "kz": 0.3, "h": 1.0e6}
            rp = closed_form(c)[2]
            print(f"   t = {t} mm, equation 50: {rp:.4f}")
            for px in (6, 8, 12, 16):
                cells = []
                for ns in (4, 8, 16, 32, 64):
                    if 25 * px * px * (ns + 2) > 130000:
                        continue
                    cells.append(f"ns {ns}: {reference_3d(c, px_div=px, n_sub=ns):.3f}")
                print(f"    pixel S/{px}: " + "  ".join(cells))
            print(f"    extrapolated (Richardson in n_sub, quadratic in 1/pixels): {reference_3d_extrap(c):.4f}")
    if heavy:
        print("\n  heavy refinement (alone: pixel S/32 is 460 000 unknowns, 8 GB resident measured): S = 2, W = 20, kxy 0.9, h = 1e6")
        for t in (1.6, 3.2):
            c = {"S": 2.0, "W": 20.0, "t": t, "kxy": 0.9, "kz": 0.3, "h": 1.0e6}
            base = reference_3d(c)
            for px, ns in ((32, 16), (16, 32)):
                v = reference_3d(c, px_div=px, n_sub=ns)
                print(f"    t {t}: pixel S/{px}, n_sub {ns}: {v:.4f} against {base:.4f} ({(v / base - 1) * 100:+.3f} %)")
    return rows


def part_programs(use_pad):
    """!
    @brief The program's models and option pairs against the 3D reference, on the 33 combinations.
    @param use_pad True to run the pad board (no closed form) instead of the bare one.
    @return list of rows.
    """
    rows = []
    kind = "pad" if use_pad else "bare"
    print(f"\nL2-L4  the program against the 3D reference ({kind} board); error in % of R'")
    print("  S   W   t    kxy  h      R'(3D)   model    cell  s_max n_max  R'(prog)   error %")
    for c in combos():
        ref = reference_3d_extrap(c, pad=use_pad)       # the extrapolated reference: the single grid S/16 is 1 to 2.6 % high (L1, README 11)
        jobs = [("fvm", cell, s, n) for cell in CELLS_MM for (s, n) in (OPTIONS if cell == 0.25 else OPTIONS[:1])]
        jobs += [("fdm", 0.25, 0.4, 4), ("solid3d", 0.5 if c["W"] > 20 else 0.25, 0.4, 4), ("analytic", 0.5, 0.4, 4), ("lumped", 0.5, 0.4, 4)]
        for model, cell, s, n in jobs:
            try:
                v = run_program(c, model, cell, s, n, use_pad)
            except Exception as exc:                                  # a model that refuses the board is reported, not hidden
                print(f"  {c['S']:3.0f} {c['W']:3.0f} {c['t']:4.1f} {c['kxy']:4.1f} {c['h']:7.0e}  {ref:8.3f}  {model:8s} {cell:5.2f}  refused: {type(exc).__name__}: {exc}")
                continue
            rows.append({**c, "board": kind, "model": model, "cell": cell, "s_max": s, "n_max": n, "r_prog": v, "r_ref": ref, "err_pct": (v / ref - 1) * 100})
            print(f"  {c['S']:3.0f} {c['W']:3.0f} {c['t']:4.1f} {c['kxy']:4.1f} {c['h']:7.0e}  {ref:8.3f}  {model:8s} {cell:5.2f}  {s:4.1f}  {n:3d}  {v:9.3f}  {(v / ref - 1) * 100:8.2f}")
    return rows


def plan():
    """!
    @brief Print what the study would do (for --dry-run), with the declared cost.
    @return None.
    """
    cs = combos()
    print("study_thick_laminate: DRY RUN (nothing is solved)")
    print(f"  {len(cs)} combinations: sources/boards {SOURCES} mm, t {THICKNESS_MM} mm, (k_xy, k_z) {RATIOS}, h {FILMS}")
    print("  L1: equation 50 (lib/flux_channel.py, 2000 terms each way) against research/gerber-real-boards/lib/ref3d.py plus the face term, pixel S/16, 16 sub-slabs; ~115 000 unknowns, < 1 GB, ~10 min")
    print(f"  L2-L4: fvm at cells {CELLS_MM} (option pairs {OPTIONS} at 0.25 mm), fdm 0.25, solid3d 0.25 (0.5 for the 40 mm board), analytic, lumped; bare and pad boards; ~15 min, <= 3 GB "
          "(the pair (0.1, 16) on the 40 mm board, 435 000 unknowns)")
    print("  --convergence: pixel S/32 (460 000 unknowns) and n_sub 32, alone, ~5 min, <= 3 GB")
    print("  outputs: research/paper-case-studies/out/study_thick_laminate.json (git-ignored)")
    print("  expected rise of the first combination from the closed form needs no solve; use --dry-run only to list: " + str(cs[0]))


def main(argv=None):
    """!
    @brief Entry point.
    @param argv Optional argument list.
    @return int Exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the declared cost, solve nothing")
    ap.add_argument("--convergence", action="store_true", help="add the convergence grid of the 3D reference (about 2 GB)")
    ap.add_argument("--heavy", action="store_true", help="add the pixel S/32 runs (8 GB resident, alone)")
    ap.add_argument("--no-program", action="store_true", help="only L1 (the reference against equation 50)")
    args = ap.parse_args(argv)
    if args.dry_run:
        plan()
        return 0
    result = {"L1": part_l1(args.convergence, args.heavy)}
    if not args.no_program:
        result["bare"] = part_programs(False)
        result["pad"] = part_programs(True)
    with open(OUT / "study_thick_laminate.json", "w") as f:
        json.dump(result, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
