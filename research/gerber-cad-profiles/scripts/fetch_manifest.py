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

# Held-out sets: found after the rules of cad_markers.json were frozen, never read before the first run of study_heldout.py.
# (truth tool, sample name, repository, folder, size limit in kB); stored in data/heldout/<truth>__<name>/
HELDOUT = [
    ("easyeda", "simplefoc", "simplefoc/Arduino-SimpleFOCShield", "Gerber/", 1500),
    ("easyeda", "dagor", "byDagor/Dagor-Brushless-Controller", "HW/Alpha Programmer 1.0/Gerber/", 1500),
    ("easyeda", "datenzwerg", "romses/Datenzwerg", "hardware/pcbs/v1.0/", 1500),
    ("diptrace", "midtbot", "bdring/midTbot_esp32", "PCB/V1/Gerbers/", 1500),
    ("diptrace", "fdskey", "ClusterM/fdskey", "PCB_gerbers/", 1500),
    ("xpedition", "irled", "sensics/IR_LED_DRV", "Schematics/PCB production files/Gerber/", 1500),
    ("xpedition", "swarm", "rose-projects/SwARM", "hardware/SwARM_Schematics/PCB/Output/", 1500),
    ("xpedition", "banshee", "minet/banshee_router", "ClearFog Gerber/", 1500),
    ("eagle", "smogbuster", "dshop-gliwice/smogbusters", "pcb/small/CAMOutputs/layout/", 1500),
    ("eagle", "oscbox", "cmoore42/oscbox", "hardware/EncoderBoard/Gerber/", 1500),
    ("altium", "electronbot", "peng-zhihui/ElectronBot", "1.Hardware/ServoDrive/Gerber/", 1500),
    ("altium", "opensimplelidar", "iliasam/OpenSimpleLidar", "PCB/CommonPCB_v1.2/Gerber_files_v1.2/", 1500),
    ("altium", "kfdtool", "KFDtool/KFDtool", "hw/KFD100/PT101 Front Panel/REV C/out/", 1500),
    ("kicad", "bparasite", "rbaron/b-parasite", "kicad/gerber/", 1500),
    ("kicad", "voltlink", "voltlog/VoltLink", "gerbers/", 1500),
    ("kicad", "librevna", "jankae/LibreVNA", "Hardware/Kicad/Production/", 1500),
    ("designspark", "crowdclock", "Inclusive-Bytes/CrowdClock", "Hardware/Plots/", 1500),
    ("circuitmaker", "hydro", "kawasakizx10rr/HydroControllerV5.0", "PCB/PCB/Gerber/", 1500),
    ("librepcb", "hydrocharger", "ubruhin/hydro-battery-charger", "pcb/output/v4/gerber/", 1500),
    ("librepcb", "nixie", "coredump-ch/nixie-counter", "output/v2.0/gerber/", 1500),
    ("pulsonix", "openplc", "leocat3/open-plc", "source/pcb/main_stm32f100/gerber/", 1500),
    ("pulsonix", "senseha", "ehajo/SenseHaJo", "mkI/Hardware/CAM/", 1500),
    ("proteus", "lockdown", "Mmessiter/LockDownRadioControl", "Circuits/Transmitter - CADCAM/", 1500),
    ("proteus", "esr", "latchdevel/C_ESR_METER", "Gerber/", 1500),
    ("allegro", "parallella", "parallella/parallella-hw", "paracluster/Design Files/", 1500),
    ("allegro", "beaglebone", "beagleboard/beaglebone-ai", "MFG/", 1500),
    ("allegro", "pixy2", "charmedlabs/pixy2", "documents/pcb/gerbers/", 1500),
    ("pads", "psdr", "MichaelRColton/PSDR", "Hardware/Test Boards/MultiTest2 Gerbers/", 1500),
]


def main(argv):
    """!
    @brief Download the sets of the requested tools (all by default).

    @param argv  Command line; the names after the program are tool keys.

    @return int Exit code.
    """
    if argv[1:2] == ["--heldout"]:
        for truth, name, repo, prefix, kb in HELDOUT:
            fetch_repo.cmd_get("heldout", truth + "__" + name, repo, prefix, kb)
        return 0
    wanted = set(argv[1:])
    for tool, name, repo, prefix, kb in MANIFEST:
        if wanted and tool not in wanted:
            continue
        fetch_repo.cmd_get(tool, name, repo, prefix, kb)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
