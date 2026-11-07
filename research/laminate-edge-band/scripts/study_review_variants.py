#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_variants.py
@brief Review: which part of the half-cell film does the work, and does it double count with the edge film of the 2.6.0 integration tree? The margin band with no film term, with the
       film on the interior laminate nodes only, on the laminate of the copper nodes only, on both (the first prototype), and the band with 8 and 16 sub-gaps, against the converged
       reference of study_review_reference.py.
@details The tree measured is LAMEDGE_TREE (default this one). On a tree whose FVM has `Network._cut_edge_film` (the cut-cell branch of 2.6.0) that function already puts the film of
         EVERY node layer, the laminate nodes included, behind half a cell, so there "band" is the reviewed rule and "band+hcint" counts the factor twice; the sub-gap rows add the
         interior film only where the tree does not (develop's FVM). The FDM has its node on the edge, so its sub-gap rows carry no film term. Writes out/review_variants_<model>_<tree>.json.
         Run (repository root): [LAMEDGE_TREE=<worktree>] .venv/bin/python research/laminate-edge-band/scripts/study_review_variants.py [--model fvm|fdm] [--cells 1,0.5,0.25]
"""

import json
import sys

import _bootband

import cases
import edge_rules as ER
from pcbthermal import SolverOptions, fvm, simulate

VARIANTS = {"default": dict(), "band": dict(band_width="margin"), "band+hcint": dict(band_width="margin", halfcell="interior"),
            "band+hccu": dict(band_width="margin", halfcell="copper"), "band+hc(prototype)": dict(band_width="margin", halfcell=True)}


def rise(p, model, cell, kw, n_max=None):
    """!
    @brief Hottest rise of one model under one rule.
    @param p Problem.
    @param model "fvm" or "fdm".
    @param cell Cell in mm.
    @param kw Arguments of edge_rules.rule.
    @param n_max None for the program's sub-gaps, or the most sub-gaps (with sub-gaps of at most 0.05 mm, so that the count is n_max on these gaps).
    @return float Rise in K.
    """
    opts = SolverOptions(cell_mm=cell, models=(model,)) if n_max is None else SolverOptions(cell_mm=cell, models=(model,), laminate_n_max=n_max, laminate_s_max_mm=0.05)
    with ER.rule(**kw):
        return simulate(p, opts).results[model].t_max - cases.T0


def main(argv=None):
    """!
    @brief Run the variants on the reviewed cases.
    @param argv Command line.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    model = argv[argv.index("--model") + 1] if "--model" in argv else "fvm"
    cells = [float(x) for x in (argv[argv.index("--cells") + 1] if "--cells" in argv else "1,0.5,0.25").split(",")]
    tree_film = hasattr(fvm.Network, "_cut_edge_film")
    interior = "interior" if (model == "fvm" and not tree_film) else False         # the film the sub-gap rows add (none for the FDM or a tree that has it)
    variants = dict(VARIANTS)
    for nm in (8, 16):
        variants[f"band n{nm}"] = (dict(band_width="margin", halfcell=interior), nm)
    refs = json.loads((_bootband.OUT / "refs_review.json").read_text())
    out = {}
    tag = "int" if tree_film else "dev"
    print(f"tree {_bootband.REPO} ({'FVM with the cut-cell edge film' if tree_film else 'develop'}), model {model}, sub-gap rows with film {interior}")
    for key, ref in refs.items():
        t, hs, pos = key.split("|")[3:]
        p, _ = cases.board(30, 20, 2, float(t), float(hs), pos)
        for cell in cells:
            row = {}
            for name, v in variants.items():
                kw, nm = v if isinstance(v, tuple) else (v, None)
                row[name] = 100.0 * (rise(p, model, cell, kw, nm) / ref - 1.0)
            out[f"{key}|{cell}"] = row
            print(key, cell, " ".join(f"{n}={e:+.2f}" for n, e in row.items()), flush=True)
    (_bootband.OUT / f"review_variants_{model}_{tag}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
