"""!
@file study_vias_nets.py
@brief Do the plated holes of a Gerber set map to the program's vias, and to the nets of the polygons? Run on the KiCad X2 test set of gerbonara's resources (copper layers with net names and aperture functions, plated and non-plated drill files) and on an older KiCad set without attributes.
@details For every plated hole the pad on each copper layer, its aperture function and its net are looked up by position (nets.py). Reported: holes, plated and non-plated, kinds, pads on both layers, the net on both layers agreeing.
         Run: .venv/bin/python research/gerber-import/scripts/study_vias_nets.py (from the repository root) (needs data/conformance from study_reader_conformance.py and study_reader_scope.py).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

from pathlib import Path

import native_gerber as ng
import nets

from paths import DATA

D = DATA / "conformance"


def run(variant):
    """!
    @brief One variant of the KiCad X2 test set.
    @param variant One of x2ap, x2noap, nox2ap, nox2noap (X2 attributes on or off, aperture attributes on or off).
    @return None (prints).
    """
    layers = [(n, ng.Layer((D / f"kicad-x2-tests__{variant}__Flashpads-{n}_Cu.gbr").read_text())) for n in ("F", "B")]
    holes = []
    for kind in ("PTH", "NPTH"):
        holes += ng.read_drill(D / f"drill__kicad-x2-tests__{variant}__Flashpads-{kind}.drl")
    rep = nets.hole_report(holes, layers)
    s = nets.summarize(rep)
    print(f"{variant:10s} holes {s['holes']:3d} (plated {s['plated']:3d})  kinds {s['kinds']}  pad on both layers {s['pad_on_every_layer']:3d}  same net on both {s['same_net']:3d}  conflicting {s['conflicting_nets']}  no net {s['no_net']:3d}")
    return rep


def charliewatch():
    """!
    @brief The four copper layers of the KiCad panel `charliewatch-v2` (no drill file in the test set, but via pads with aperture functions and net names): vias seen from their pads.
    @return None (prints).
    """
    names = ("F", "In1", "In2", "B")
    layers = [(n, ng.Layer((D / f"zero-length-lines__charliewatch-v2.panel-{n}_Cu.gbr").read_text())) for n in names]
    g = nets.via_pads(layers)
    s = nets.via_summary(g, len(names))
    print(f"\ncharliewatch-v2 (4 copper layers): via pads grouped by position -> {s['vias']} vias, {s['on_every_layer']} with a pad on all four layers, "
          f"{s['same_net']} whose pads agree on the net, {s['conflicting']} with conflicting nets, {s['no_net']} without a net, {s['join_more_than_two']} joining more than two layers")
    nets_of = {}
    for pos, d in g.items():
        for n in {v for v in d.values() if v}:
            nets_of[n] = nets_of.get(n, 0) + 1
    top = sorted(nets_of.items(), key=lambda kv: -kv[1])[:5]
    print("  nets with the most vias:", ", ".join(f"{k.split('-')[-1]} ({v})" for k, v in top))


def main():
    """!
    @brief Run the four variants and list a few plated holes.
    @return None.
    """
    reps = {v: run(v) for v in ("x2ap", "x2noap", "nox2ap", "nox2noap")}
    charliewatch()
    print("\nfirst plated holes of x2ap (position mm, diameter mm, kind, net, pads F/B):")
    for r in [r for r in reps["x2ap"] if r["plated"]][:6]:
        print(f"  ({r['x']:.2f}, {r['y']:.2f}) d {r['d']:.2f}  {r['kind']:10s} net {r['net']}  F {r['pads']['F']}  B {r['pads']['B']}")


if __name__ == "__main__":
    main()
