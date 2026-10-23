"""!
@file test_kicad_nets.py
@brief The Stormduino check of the nets against its `.kicad_pcb` file (needs data/storm: scripts/fetch_boards.py and the KiCad file; skipped otherwise).
"""

import pytest

import kicad_pcb
from paths import DATA


def test_kicad_reader_on_a_small_file(tmp_path):
    """!
    @brief The reader finds nets, a track, a via and a pad with its world position.
    @param tmp_path pytest folder.
    @return None.
    """
    f = tmp_path / "a.kicad_pcb"
    f.write_text('(kicad_pcb (net 0 "") (net 1 "A") (segment (start 0 0) (end 1 0) (width 0.2) (layer F.Cu) (net 1))'
                 ' (via (at 1 0) (size 0.8) (drill 0.4) (layers F.Cu B.Cu) (net 1))'
                 ' (module M (at 10 5 90) (pad 1 smd rect (at 2 0) (size 1 1) (layers F.Cu) (net 1 "A"))))')
    r = kicad_pcb.read(f)
    assert r["nets"][1] == "A" and len(r["segments"]) == 1 and len(r["vias"]) == 1
    x, y = r["pads"][0]["p"]
    assert abs(x - 10) < 1e-9 and abs(y - 3) < 1e-9                  # rotated by 90 degrees in the y-down axis


def test_stormduino_nets_agree_with_the_cad_file():
    """!
    @brief On the Stormduino every object of the CAD file lies on our copper, no group of copper joined through the plated holes holds two nets, and the nets of the Gerber and of the CAD file split the same way.
    @return None.
    """
    pcb = DATA / "storm" / "stormduino.kicad_pcb"
    if not pcb.exists() or not (DATA / "storm" / "F.gbr").exists():
        pytest.skip("the Stormduino files are not downloaded")
    import study_kicad_nets as s
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s.main()
    out = buf.getvalue()
    assert "track 1380 of 1380, via 48 of 48, pad 281 of 281" in out
    assert "with more than one net: 0" in out
    assert "different: 1" in out
