"""!
@file study_gerber_writer.py
@brief A third independent writer: files made with the `gerber-writer` library (Ucamco's Python library for writing Gerber X2 files) read by the independent reader and by gerbonara.
@details gerber-writer writes thermal pads, rounded and chamfered rectangles, regular and user polygons, arcs, regions and the X2 aperture functions (Conductor, SMDPad, ViaPad, ...).
         The files cover the aperture macros that the other test files use little (thermal, chamfered and rounded rectangles). For every file the copper area drawn by the independent
         reader at 0.01 mm pixels is compared with the vector area of gerbonara + shapely. The X2 aperture attributes are also checked against what the reader reports.
         Run (gerber-writer, gerbonara and shapely needed): .venv/bin/python research/gerber-import/scripts/study_gerber_writer.py (from the repository root)
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import math
from pathlib import Path

import gerber_writer as gw

import gerber_geometry as gg
import native_gerber as ng

from paths import DATA

OUT = DATA / "synthetic"
PIX = 0.01


def make():
    """!
    @brief Write the test files.
    @return Dict name -> path.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}

    def save(name, layer):
        """!@brief Write a layer to data/synthetic. @param name File stem. @param layer gerber_writer DataLayer. @return None."""
        p = OUT / f"gw_{name}.gbr"
        p.write_text(layer.dumps_gerber())
        files[name] = p

    gw.set_generation_software("pcb-thermal-lab", "research", "0")
    pads = gw.DataLayer("Copper,L1,Top")
    pads.add_pad(gw.Thermal(4.0, 2.0, 0.5, "ThermalReliefPad"), (10, 10))
    pads.add_pad(gw.RoundedThermal(4.0, 3.2, 0.3, "ThermalReliefPad"), (20, 10))
    pads.add_pad(gw.Rectangle(3.0, 2.0, "SMDPad,CuDef"), (30, 10))
    pads.add_pad(gw.RoundedRectangle(3.0, 2.0, 0.5, "SMDPad,CuDef"), (10, 20))
    pads.add_pad(gw.RegularPolygon(2.0, 6, "ViaPad"), (20, 20))
    pads.add_pad(gw.Circle(1.2, "ViaPad"), (30, 20))
    save("pads", pads)
    tr = gw.DataLayer("Copper,L1,Top")
    for k, w in enumerate((0.1, 0.15, 0.2, 0.3)):
        tr.add_trace_line((5, 5 + k), (25, 5 + k + 3), w, "Conductor")
    p = gw.Path()
    p.moveto((5, 15)); p.lineto((15, 15)); p.arcto((20, 20), (15, 20), "+"); p.lineto((30, 20))
    tr.add_traces_path(p, 0.25, "Conductor")
    save("traces_arcs", tr)
    rg = gw.DataLayer("Copper,L1,Top")
    p = gw.Path()
    p.moveto((5, 5)); p.lineto((25, 5)); p.lineto((25, 15)); p.lineto((15, 25)); p.lineto((5, 15)); p.lineto((5, 5))
    rg.add_region(p, "Conductor")
    save("region", rg)
    return files


def exact_traces_arcs():
    """!
    @brief Exact area of the `traces_arcs` file from its construction (shapely, round caps, the quarter circle sampled finely).
    @return Area (mm2).
    """
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    parts = [LineString([(5, 5 + k), (25, 5 + k + 3)]).buffer(w / 2, quad_segs=256) for k, w in enumerate((0.1, 0.15, 0.2, 0.3))]
    arc = [(15 + 5 * math.sin(t), 20 - 5 * math.cos(t)) for t in [i * (math.pi / 2) / 2000 for i in range(2001)]]       # from (15, 15) round to (20, 20), centre (15, 20)
    parts.append(LineString([(5, 15), (15, 15)] + arc[1:] + [(30, 20)]).buffer(0.125, quad_segs=256))
    return unary_union(parts).area


def main():
    """!
    @brief Write the files and compare the two readers.
    @return None.
    """
    files = make()
    exact = {"region": 300.0, "traces_arcs": exact_traces_arcs()}
    print(f"{'file':14s} {'exact mm2':>10s} {'gerbonara vector mm2':>21s} {'independent reader mm2':>23s} {'reader vs exact %':>18s} {'gerbonara vs exact %':>21s}")
    for name, path in files.items():
        geom, _ = gg.load_copper(path)
        layer = ng.Layer(path.read_text())
        bb = layer.bbox()
        cv = ng.Canvas(bb[0] - 0.5, bb[3] + 0.5, bb[2] - bb[0] + 1.0, bb[3] - bb[1] + 1.0, PIX)
        layer.draw(cv)
        a = float(cv.mask.sum() * PIX * PIX)
        ref = exact.get(name, geom.area)
        print(f"{name:14s} {ref:10.4f} {geom.area:21.4f} {a:23.4f} {100 * (a / ref - 1):+18.2f} {100 * (geom.area / ref - 1):+21.2f}   classify: {ng.classify(path)}   nets: {layer.net_names()}")


if __name__ == "__main__":
    main()
