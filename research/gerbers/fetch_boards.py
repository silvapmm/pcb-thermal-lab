"""!
@file fetch_boards.py
@brief Download the public boards used by the Gerber research into data/ (git-ignored).
@details The boards are NOT stored in this repository because their licences differ (MIT, BSD, GPL-2, GPL-3, CC BY-SA, unknown).
         They are used here only to run the studies on a private machine; the results quoted in the documents are statistics, not copies.
         Usage: python fetch_boards.py [board ...]   (no argument = all)
"""

import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
GERBONARA = "https://gitlab.com/gerbolyze/gerbonara/-/raw/main/tests/resources/"

# name -> (base URL, {role file on disk: remote file name}, licence, origin)
BOARDS = {
    "storm": ("https://raw.githubusercontent.com/Chromico/stormduino/master/Rev%202.2%20Gerbers/",
              {"F.gbr": "stormduino Rev2-F_Cu.gbr", "B.gbr": "stormduino Rev2-B_Cu.gbr", "edge.gbr": "stormduino Rev2-Edge_Cuts.gbr",
               "drill.drl": "stormduino Rev2-PTH.drl"},
              "MIT", "https://github.com/Chromico/stormduino (an Arduino Uno clone, KiCad, 2 layers)"),
    "chibi": (GERBONARA + "kicad-older/", {"F.gbr": "chibi_2024-F.Cu.gbr", "edge.gbr": "chibi_2024-Edge.Cuts.gbr"},
              "CC BY-SA", "https://github.com/jaseg/7segstuff/tree/master/hw/chibi/chibi_2024"),
    "easyeda": (GERBONARA + "easyeda/", {"F.gbr": "Gerber_TopLayer.GTL", "edge.gbr": "Gerber_BoardOutline.GKO"},
                "not stated", "https://github.com/tracespace/tracespace/issues/367"),
    "pcbrnd": (GERBONARA + "pcb-rnd/", {"F.gbr": "power-art.gtl", "edge.gbr": "power-art.gko"},
               "GPL-2", "https://github.com/EPL-Engineering/epl_isolatedpwr"),
    "pcad": (GERBONARA + "p-cad/", {"F.gbr": "ZXINET.GTL", "edge.gbr": "ZXINET.GKO"},
             "GPL-3", "https://github.com/lvd2/zxnet_usb"),
    "dip": (GERBONARA + "diptrace/", {"F.gbr": "mainboard_Top.gbr", "edge.gbr": "mainboard_BoardOutline.gbr"},
            "BSD", "https://github.com/codepainters/FD1/tree/master/hardware"),
    "alleg": (GERBONARA + "allegro/", {"F.gbr": "l1_primary.art", "L2.gbr": "l2_gnd.art", "L3.gbr": "l3_vcc.art", "B.gbr": "l4_secondary.art",
                                      "drill.drl": "ncdrill-1-4.drl"},
              "not stated", "https://github.com/tracespace/tracespace/issues/371 (a 4-layer Cadence Allegro board, 101.7 x 81.1 mm, inches)"),
    "fritz": (GERBONARA + "fritzing/", {"F.gbr": "combined.gtl", "edge.gbr": "combined.GKO"},
              "MIT", "https://github.com/ohguma/analog_gyro_2021"),
}


def fetch(name):
    """!
    @brief Download the files of one board.
    @param name Key of BOARDS.
    @return None (files are written to data/<name>/).
    """
    base, files, lic, origin = BOARDS[name]
    out = DATA / name
    out.mkdir(parents=True, exist_ok=True)
    for local, remote in files.items():
        url = base + urllib.parse.quote(remote)
        dest = out / local
        if dest.exists():
            continue
        with urllib.request.urlopen(url, timeout=60) as r:
            dest.write_bytes(r.read())
        print(f"  {name}/{local}  <- {remote}")
    print(f"{name}: licence {lic}; {origin}")


def main(argv):
    """!
    @brief Download the boards named on the command line, or all of them.
    @param argv List of board keys (empty = all).
    @return None.
    """
    for name in (argv or list(BOARDS)):
        if name not in BOARDS:
            raise SystemExit(f"unknown board {name!r}; known: {', '.join(BOARDS)}")
        fetch(name)


if __name__ == "__main__":
    main(sys.argv[1:])
