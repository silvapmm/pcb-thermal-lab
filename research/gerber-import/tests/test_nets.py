#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_nets.py
@brief Holes, pads and nets matched by position, on small synthetic files written by the tests (a plated via, a component hole, a non-plated hole, a conflicting net).
"""

import native_gerber as ng
import nets
from boards_synthetic import HEAD, mm


def layer(pads):
    """!
    @brief A copper layer with attribute-carrying pads.
    @param pads List of (x, y, function, net).
    @return Parsed Layer.
    """
    t = HEAD
    for k, (x, y, func, net) in enumerate(pads):
        t += f"%TA.AperFunction,{func}*%\n%ADD{10 + k}C,1.0*%\n%TD.AperFunction*%\n"
    for k, (x, y, func, net) in enumerate(pads):
        t += f"%TO.N,{net}*%\nD{10 + k}*\nX{mm(x)}Y{mm(y)}D03*\n%TD*%\n"
    return ng.Layer(t + "M02*\n")


def drill(tmp_path, holes, function="Plated,1,2,PTH"):
    """!
    @brief An Excellon file with the X2 file function in a comment.
    @param tmp_path pytest temp dir.
    @param holes List of (x, y, diameter).
    @param function Text after TF.FileFunction,.
    @return Path.
    """
    p = tmp_path / "d.drl"
    p.write_text(f"M48\n; #@! TF.FileFunction,{function}\nMETRIC\n" + "".join(f"T{k + 1}C{d}\n" for k, (x, y, d) in enumerate(holes)) + "%\n"
                 + "".join(f"T{k + 1}\nX{x}Y{y}\n" for k, (x, y, d) in enumerate(holes)) + "M30\n")
    return p


def test_drill_function_and_plating(tmp_path):
    """!@brief The X2 comment of a drill file gives plated or not and the layer span, and the holes inherit it. @param tmp_path pytest temp dir. @return None."""
    p = drill(tmp_path, [(5.0, 5.0, 0.3)])
    assert ng.drill_function(p) == (True, 1, 2)
    assert ng.read_drill(p)[0][3] is True
    q = drill(tmp_path, [(5.0, 5.0, 0.3)], "NonPlated,1,2,NPTH")
    assert ng.read_drill(q)[0][3] is False


def test_via_and_component_holes_match_pads_and_nets(tmp_path):
    """!@brief A via with ViaPad pads on both layers, a lead hole with ComponentPad pads, and a non-plated hole: kind, net and agreement. @param tmp_path pytest temp dir. @return None."""
    top = layer([(5, 5, "ViaPad", "5V"), (10, 5, "ComponentPad", "GND")])
    bottom = layer([(5, 5, "ViaPad", "5V"), (10, 5, "ComponentPad", "GND")])
    holes = ng.read_drill(drill(tmp_path, [(5.0, 5.0, 0.3), (10.0, 5.0, 0.8)])) + [(20.0, 20.0, 2.0, False)]
    rep = nets.hole_report(holes, [("F", top), ("B", bottom)])
    assert [r["kind"] for r in rep] == ["via", "component", "unplated"]
    assert rep[0]["net"] == "5V" and rep[0]["same_net"] is True
    assert rep[1]["net"] == "GND"
    s = nets.summarize(rep)
    assert s["plated"] == 2 and s["same_net"] == 2 and s["conflicting_nets"] == 0


def test_conflicting_nets_and_via_pad_groups():
    """!@brief A hole whose pads carry different nets is flagged, and via pads are grouped by position across layers. @return None."""
    top = layer([(5, 5, "ViaPad", "5V")])
    bottom = layer([(5, 5, "ViaPad", "3V3")])
    rep = nets.hole_report([(5.0, 5.0, 0.3, True)], [("F", top), ("B", bottom)])
    assert rep[0]["same_net"] is False and rep[0]["net"] is None
    g = nets.via_pads([("F", top), ("B", bottom)])
    assert g == {(5.0, 5.0): {"F": "5V", "B": "3V3"}}
    s = nets.via_summary(g, 2)
    assert s["vias"] == 1 and s["conflicting"] == 1 and s["on_every_layer"] == 1
