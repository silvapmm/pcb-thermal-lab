#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_references.py
@brief How good are the references of the investigation: the exact series against two published solutions, the graded 3D solver against the exact series, the medium preset against the fine one, and the same-cell 3D solver against its own sub-slab count.
@details Question: can the numbers of the baseline and of the node sweeps be trusted to a tenth of a percent? Four checks, all printed:
         1. lib/series.py against Eq. 27 of Muzychka, Culham and Yovanovich (2003) (one layer, mean source rise) and against Eqs. 14 and 15 of Yovanovich, Muzychka and Culham (1999) (two
            layers of very different conductivity, spreading resistance);
         2. lib/graded_pad3d.py (fine and medium presets, three scales, fitted limit) against the exact series on uniform boards of 2, 4 and 8 layers;
         3. the fine against the medium preset on a pad board (two layers);
         4. the 3D solver on the model's own in-plane cell against its number of sub-slabs (the reference used to isolate the through-thickness error).
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_references.py   (from the repository root; a few minutes).
"""

import _bootstrap as BS                                                     # noqa: F401
import boards as B
import closed_forms as CF
import series as S
import yovanovich1999 as Y


def check_published():
    """!
    @brief Check 1: the series against the two published solutions.
    @return None.
    """
    a, k, t, h = 10e-3, 0.3, 1e-3, 500.0
    want = CF.plate_mean_rise(a, a, 4e-3, 4e-3, a / 2, a / 2, t, k, h, 1.0)
    got = S.source_rise(a, a, [(t, k, k)], 0.0, h, 1.0, (a / 2, 4e-3), (a / 2, 4e-3), window=(4e-3, 4e-3), nmax=800)[0]
    print(f"1a. one layer, Muzychka 2003 Eq. 27: mean rise {want:.6f} K, series {got:.6f} K, difference {100 * (got / want - 1):+.5f} %")
    for t1, t2, k1, k2, h in [(1e-3, 1e-3, 10, 1, 500), (0.5e-3, 1.5e-3, 200, 0.3, 10), (0.035e-3, 1.6e-3, 385, 0.3, 10)]:
        w = Y.spreading_resistance(3e-3, 3e-3, 15e-3, 15e-3, t1, t2, k1, k2, h, terms=800)
        g = S.spreading_resistance(30e-3, 30e-3, 6e-3, 6e-3, [(t1, k1, k1), (t2, k2, k2)], h, nmax=800)
        print(f"1b. two layers t1 {t1 * 1e3:.3f} mm k1 {k1} / t2 {t2 * 1e3:.3f} mm k2 {k2}, h {h}: Rs Eq. 14 {w:.6f} K/W, series {g:.6f} K/W, difference {100 * (g / w - 1):+.5f} %")


def check_graded():
    """!
    @brief Check 2: the graded solver against the exact series on uniform boards.
    @return None.
    """
    for l, gap in ((2, 1.6), (4, 0.4), (8, 0.2)):
        bd = B.Board("u", layers=l, gap=gap, source=3.0)
        ex = B.exact_peak(bd, 0.5)
        for preset in ("fine", "medium"):
            if preset == "fine" and l == 8:
                continue                                                     # about a million unknowns
            r = B.graded_peak(bd, 0.5, preset=preset)
            print(f"2.  uniform L{l} gap {gap}: exact {ex:.4f} K, graded {preset} {r['peak']:.4f} K ({100 * (r['peak'] / ex - 1):+.3f} %), finest grid {r['finest']:.4f} (spread {r['spread']:+.3f} %), p {r['order']:.2f}, balance {r['balance']:.8f}, unknowns {r['unknowns']}")


def check_presets_and_slabs():
    """!
    @brief Checks 3 and 4: fine against coarse on a pad board, and the same-cell solver against its sub-slabs.
    @return None.
    """
    bd = B.Board("pad", layers=2, gap=1.6, source=3.0, pad=10.0, pad_layers=(0,))
    f, c = B.graded_peak(bd, 0.5, preset="fine"), B.graded_peak(bd, 0.5, preset="medium")
    print(f"3.  pad10-full: fine {f['peak']:.4f} K, medium {c['peak']:.4f} K ({100 * (c['peak'] / f['peak'] - 1):+.3f} %)")
    p = B.problem(bd)
    for ns in (8, 16, 32, 64):
        print(f"4.  same-cell 3D (0.5 mm) with {ns} sub-slabs per gap: {B.samecell_peak(bd, 0.5, ns, p):.4f} K")
    r = B.resolved_peak(bd, 0.5, 0.25, 8, p)
    print(f"    resolved3d at 0.25 mm / 8 sub-slabs read on the 0.5 mm cell: {r['peak']:.4f} K (converged graded {f['peak']:.4f} K)")


if __name__ == "__main__":
    check_published()
    check_graded()
    check_presets_and_slabs()
