#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fetch_manifest.py
@brief Download every sample set of the CAD-profile study that comes from a public repository.

Question answered: how to reproduce the data/ folder.  The MANIFEST lists, per tool key, the
repository and the folder of a real Gerber/drill output; `fetch_repo.cmd_get` downloads it
(files up to the size limit) and writes the licence reported by the GitHub API next to it.
The sets found by banner search (`search_code.py`) are the ones listed here.  The gerbonara
test resources are fetched by `fetch_samples.py` (a sparse clone, see the README).

Run: .venv-research/bin/python research/gerber-cad-profiles/scripts/fetch_manifest.py [tool ...]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_repo  # noqa: E402

# (tool key, sample name, repository, folder, size limit in kB)
MANIFEST = [
    ("xpedition", "bouled", "bouLED/bouled", "design/LED_Panel/Assembly/LED_Panel/", 400),
    ("xpedition", "spirose", "friendshipismagic/SpiROSE", "PCB/LED_Panel/Assembly/LED_Panel/", 2500),
    ("xpedition", "hw0004", "jgrobis/HW-0004", "HARDWARE/MAIN_PCB/Gerber/", 400),
    ("proteus", "ottosdiy", "intechstudio/ottosdiy", "Core/Powerbrick/Panel/", 600),
    ("proteus", "breath", "TengoCharlie/breath-analyzer", "PCB-Breathe Anlyer wo led/Proteus/", 600),
    ("pulsonix", "zx81", "ehajo/ZX81", "tastatur/003-CAM/", 600),
    ("pulsonix", "rabbit", "terminele/rabbit", "gerber/150413/", 600),
    ("kicad8", "oneinchEye", "will127534/OneInchEye", "Gerber/", 800),
    ("kicad7", "watchy", "sqfmi/watchy-hardware", "GERBER/", 800),
    ("kicad9", "badgemagic", "fossasia/badgemagic-hardware", "output/gerber/", 800),
    ("kicad6", "tdrgb", "tdaede/td-crt", "td-rgb/v1.0/", 800),
    ("altium-x2", "simplefoc", "simplefoc/Arduino-SimpleFOC-PowerShield", "Gerber/", 800),
    ("altium-x2", "note", "blues/note-hardware", "Mojo/v1.1/Fabrication/Gerber/", 800),
    ("altium-x2", "linkcard", "peng-zhihui/L-ink_Card", "Hardware/release/Gerber/", 800),
    ("circuitmaker", "yaduino", "hishamk/yaduino", "gerber/", 800),
    ("librepcb", "desklift", "dbrgn/desklift", "output/v1/gerber/", 800),
    ("eagle-x2", "16n", "16n-faderbank/16n", "electronics/gerbers/", 800),
    ("fusion", "arduTouch", "maltman23/ArduTouch", "Gerbers/outputs/", 800),
    ("designspark", "picovdp", "alastairpatrick/pico-vdp", "hardware/Plots/", 800),
    ("orcad", "cc1310", "sangphanthanh/CP_SmartGarden", "OrCAD/Gerber/", 800),
]


def main(argv):
    """!
    @brief Download the sets of the requested tools (all by default).

    @param argv  Command line; the names after the program are tool keys.

    @return int Exit code.
    """
    wanted = set(argv[1:])
    for tool, name, repo, prefix, kb in MANIFEST:
        if wanted and tool not in wanted:
            continue
        fetch_repo.cmd_get(tool, name, repo, prefix, kb)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
