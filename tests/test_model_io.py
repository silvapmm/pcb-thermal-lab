"""!
@file test_model_io.py
@brief Tests of the JSON readers, the legacy converter and the command line.
"""

import json

import numpy as np
import pytest

from pcbthermal import cli
from pcbthermal.model import (problem_from_dict, problem_from_legacy, problem_to_dict,
                              reference_problem)


def test_roundtrip_native_json():
    p = reference_problem()
    q = problem_from_dict(json.loads(json.dumps(problem_to_dict(p))))
    assert q.total_power() == pytest.approx(p.total_power())
    assert q.board.width == pytest.approx(p.board.width)
    assert len(q.zones) == len(p.zones)


def test_legacy_conversion_flips_y_and_scales():
    legacy = {
        "pcb_params": {"width": 100, "height": 100, "thickness": 1.6, "layers": 2,
                       "copper_thickness": 0.035, "copper_conductivity": 385.0,
                       "fr4_conductivity": 0.3, "ambient_temp_global": 25.0,
                       "convection_h_global": 10.0, "convection_h_top": 10.0,
                       "convection_h_bottom": 15.0, "boundary_mode": "Convective",
                       "pcb_corners": [[100, 100], [600, 600]]},
        "elements": [
            {"type": "Heater", "id": 1, "layer": 1, "power": 5.0,
             "points": [[100, 100], [200, 100], [200, 200], [100, 200]]},
        ],
    }
    p = problem_from_legacy(legacy)
    poly = p.heaters[0].polygon * 1000.0       # back to mm
    # Canvas top-left corner (100, 100) is the top of the board: y = 100 mm after the flip
    assert poly[:, 0].min() == pytest.approx(0.0) and poly[:, 0].max() == pytest.approx(20.0)
    assert poly[:, 1].max() == pytest.approx(100.0) and poly[:, 1].min() == pytest.approx(80.0)


def test_bad_inputs_are_rejected():
    d = problem_to_dict(reference_problem())
    d["heaters"][0]["layer"] = 5
    with pytest.raises(ValueError):
        problem_from_dict(d)
    d = problem_to_dict(reference_problem())
    d["sinks"] = [{"layer": 2, "polygon_mm": [[0, 0], [10, 0], [10, 10]], "h_extra": 5}]
    d["board"]["layers"] = 4
    d["board"]["copper_thickness_mm"] = 0.035
    d["zones"] = []
    with pytest.raises(ValueError):
        problem_from_dict(d)


def test_cli_run_writes_outputs(tmp_path):
    cfg = tmp_path / "board.json"
    cfg.write_text(json.dumps(problem_to_dict(reference_problem())))
    out = tmp_path / "out"
    assert cli.main(["run", str(cfg), "--out", str(out), "--cell-mm", "4"]) == 0
    summary = json.loads((out / "summary.json").read_text())
    assert set(summary) == {"fvm", "lumped", "analytic"}
    assert (out / "fields_fvm.png").exists() and (out / "comparison.png").exists()
