#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_onesheet_and_real_boards.py
@brief Tests of the one-sheet comparison on synthetic copper (needs SciPy and the gerber-models library, no download) and of the readers on the downloaded open boards (skipped with a message when data/ is empty).
"""

import numpy as np
import pytest

import onesheet
import registry

NEEDS_DATA = pytest.mark.skipif(not registry.available(), reason="no board in research/gerber-real-boards/data: run scripts/fetch_boards.py")


def test_uniform_window_all_mappings_agree():
    """!@brief On a window of solid copper every mapping gives the same answer (nothing to map); what differs from the pixel reference is the coarse grid, the same for all. @return None."""
    cov = np.ones((120, 120))
    res = onesheet.run_window(cov, 0.1, cells_mm=(1.0,), heater_mm=2.0, with_reference9=False)
    errs = [v["5"] for m, v in res["errors"][1.0].items() if "diagonal" not in m]       # the diagonal variant adds conduction on purpose
    assert max(errs) - min(errs) < 1.0, errs
    assert all(abs(e) < 10.0 for e in errs), errs


def test_fine_copper_makes_the_fill_fraction_cool():
    """!@brief Stripes across the heat flow: the arithmetic fill gives a cooler heater than the pixel reference (the known bias of README 4.4 of gerber-models). @return None."""
    cov = np.zeros((120, 120))
    for y in range(0, 120, 4):                               # horizontal stripes 0.2 mm wide at 0.4 mm pitch (2 px of 4)
        cov[y:y + 2, :] = 1.0
    res = onesheet.run_window(cov, 0.1, cells_mm=(1.0,), heater_mm=2.0, with_reference9=False)
    e = res["errors"][1.0]
    assert e["fill fraction (today)"]["5"] < -3.0            # cooler than the resolved stripes
    assert abs(e["flow-based faces"]["5"]) < abs(e["fill fraction (today)"]["5"])


@NEEDS_DATA
def test_every_board_has_its_files_and_reads():
    """!@brief Every downloaded board imports its copper with the independent reader and has an outline. @return None."""
    import native_gerber as ng
    for key in registry.available():
        r = registry.roles(key)
        assert r["copper"], key
        for p in r["copper"]:
            ng.Layer(p.read_text(errors="replace"))          # raises when the reader refuses the file
        assert ng.layer_bbox(r["outline"] or r["copper"][0]) is not None


@NEEDS_DATA
def test_kicad_paste_files_carry_references():
    """!@brief The KiCad boards write the reference designator (TO.C) in the paste file, and placement files read. @return None."""
    import paste
    import pnp
    seen = 0
    for key in registry.available():
        r = registry.roles(key)
        if r["paste_top"] is not None and r["paste_top"].stat().st_size > 400:
            refs = paste.by_reference(r["paste_top"])
            seen += len(refs)
        if r["placement"] is not None:
            parts = pnp.read_placement(r["placement"])
            assert all(p["ref"] for p in parts)
    assert seen > 0, "no paste file with TO.C found"


@NEEDS_DATA
def test_placement_registers_on_paste_groups():
    """!@brief For the first board with a paste file and a placement file, most top parts fall within 2 mm of a group after registration. @return None."""
    import native_gerber as ng
    import paste
    import pnp
    for key in registry.available():
        r = registry.roles(key)
        if r["paste_top"] is None or r["placement"] is None or r["paste_top"].stat().st_size < 400:
            continue
        box = ng.layer_bbox(r["outline"] or r["copper"][0])
        groups = paste.by_proximity(r["paste_top"], box, pix=0.1, link_mm=1.0)
        parts = [p for p in pnp.read_placement(r["placement"]) if p["side"] == "top"]
        if len(parts) < 5:
            continue
        gc = np.array([[g["x"], g["y"]] for g in groups])
        pc = np.array([[p["x"], p["y"]] for p in parts])
        tr = pnp.register(gc, pc, tol_mm=2.0)
        assert tr["matched"] >= 0.8 * len(parts), (key, tr)
        return
    pytest.skip("no board with both a paste file and a placement file of at least five top parts")
