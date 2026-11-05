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
    # The common offset is the scenario, not the mapping: the held ring is imposed at the centre of its cells, so the ring sits half a cell inside (16.5 % at 1 mm, 5 % at 0.5 mm on this 12 mm board; 2.5 % and 0.8 % on a 36 mm window, README 4.1); only the differences between mappings mean something
    assert all(abs(e) < 20.0 for e in errs), errs


def test_uniform_36mm_window_offset_is_small_and_common():
    """!@brief The review's regression of README 4.1: on a solid 36 mm window (the size of the study windows) the held-ring offset is +2.5 % at 1 mm and +0.8 % at 0.5 mm against the pixel reference (21.49 K), the same for every mapping; the 16.5 % of the first block belonged to the 12 mm unit-test board. @return None."""
    res = onesheet.run_window(np.ones((360, 360)), 0.1, cells_mm=(0.5, 1.0), with_reference9=False)
    assert abs(res["ref5"] - 21.49) < 0.01, res["ref5"]
    for cell, expected in ((0.5, 0.83), (1.0, 2.47)):
        errs = [v["5"] for m, v in res["errors"][cell].items()]
        assert max(errs) - min(errs) < 0.01, errs                     # nothing to map on solid copper: every mapping is the same network
        assert abs(errs[0] - expected) < 0.05, (cell, errs[0])


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
def test_placement_origin_is_on_the_named_paste_group():
    """!@brief Where the paste file names its parts (TO.C), the placement origin of each part is at the centre of its own paste group, with no registration at all (the frames are the same in KiCad output); the registration by the votes of unnamed proximity groups was found unreliable (study_paste_footprints, README 4.4), so it is not what is tested. @return None."""
    import paste
    import pnp
    for key in registry.available():
        r = registry.roles(key)
        if r["paste_top"] is None or r["placement"] is None or r["paste_top"].stat().st_size < 400:
            continue
        refs = paste.by_reference(r["paste_top"])
        parts = {p["ref"]: p for p in pnp.read_placement(r["placement"]) if p["side"] == "top"}
        common = [k for k in refs if k in parts]
        if len(common) < 5:
            continue
        d = np.array([np.hypot(refs[k]["x"] - parts[k]["x"], refs[k]["y"] - parts[k]["y"]) for k in common])
        assert (d <= 0.5).mean() >= 0.9, (key, np.percentile(d, [50, 90, 100]))
        return
    pytest.skip("no board with both a paste file with TO.C and a placement file of at least five top parts")
