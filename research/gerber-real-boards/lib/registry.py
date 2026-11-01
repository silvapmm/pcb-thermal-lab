#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file registry.py
@brief The open boards of this investigation (GitHub projects that publish Gerbers together with paste layers and a placement file), their licences, files and the roles of the files on disk.
@details Nothing here is stored in the repository: `scripts/fetch_boards.py` downloads the files into `data/<key>/` (git-ignored) under fixed local names, so the studies and tests find them the same way:
         F.gbr (top copper), L2.gbr, L3.gbr (inner copper, stack order), B.gbr (bottom copper), edge.gbr (outline), drill.drl (plated holes), pasteF.gbr and pasteB.gbr (solder paste),
         pos.csv (placement file of the CAD tool) and job.gbrjob (Gerber job file, when the project has one). Licences were read from the GitHub repository metadata (spdx id); the layer counts,
         sizes and file lists come from the repository listing and, for ISASTM, the job file; the size of the others is printed by `fetch_boards.py` from the outline once downloaded.
"""

from pathlib import Path

import rb_paths

RAW = "https://raw.githubusercontent.com/{repo}/HEAD/{path}/{name}"

# key -> dict(repo, path, licence, layers, tool, files {local name: remote name}, note)
BOARDS = {
    "isastm": dict(
        repo="Manawyrm/ISASTM", path="gerbers/RevA/ISASTM", licence="GPL-3.0", layers=4, tool="KiCad 5.1.6",
        note="STM32 ISA-over-USB adapter, 101.65 x 101.65 mm (job file), 1.6 mm; the paste file carries the component attribute TO.C (reference designator) of every pad group",
        files={"F.gbr": "ISASTM-F_Cu.gtl", "L2.gbr": "ISASTM-In1_Cu.g2", "L3.gbr": "ISASTM-In2_Cu.g3", "B.gbr": "ISASTM-B_Cu.gbl", "edge.gbr": "ISASTM-Edge_Cuts.gm1",
               "drill.drl": "ISASTM-PTH.drl", "pasteF.gbr": "ISASTM-F_Paste.gtp", "pasteB.gbr": "ISASTM-B_Paste.gbp", "pos.csv": "ISASTM-all-pos.csv",
               "cpl_jlc.csv": "ISASTM_cpl_jlc.csv", "job.gbrjob": "ISASTM-job.gbrjob"}),
    "cmm2": dict(
        repo="Manawyrm/CMM2-JLC", path="gerbers/RevE/CMM2-JLC", licence="GPL-3.0", layers=4, tool="KiCad (version in the file header)",
        note="Colour Maximite 2 (unofficial, for automated assembly); inner layers named GND and POWER; size read at fetch",
        files={"F.gbr": "CMM2-JLC-F_Cu.gtl", "L2.gbr": "CMM2-JLC-GND.g2", "L3.gbr": "CMM2-JLC-POWER.g3", "B.gbr": "CMM2-JLC-B_Cu.gbl", "edge.gbr": "CMM2-JLC-Edge_Cuts.gm1",
               "drill.drl": "CMM2-JLC-PTH.drl", "pasteF.gbr": "CMM2-JLC-F_Paste.gtp", "pasteB.gbr": "CMM2-JLC-B_Paste.gbp", "pos.csv": "CMM2-JLC-all-pos.csv",
               "cpl_jlc.csv": "CMM2-JLC_cpl_jlc.csv"}),
    "oswlight": dict(
        repo="Open-Smartwatch/open-smartwatch-light", path="gerbers", licence="GPL-3.0", layers=4, tool="KiCad (version in the file header)",
        note="smartwatch, small board; every KiCad layer is exported as .gbr; the outline file is tiny; size read at fetch",
        files={"F.gbr": "osw-light-F_Cu.gbr", "L2.gbr": "osw-light-In1_Cu.gbr", "L3.gbr": "osw-light-In2_Cu.gbr", "B.gbr": "osw-light-B_Cu.gbr", "edge.gbr": "osw-light-Edge_Cuts.gbr",
               "drill.drl": "osw-light-PTH_drill.drl", "pasteF.gbr": "osw-light-F_Paste.gbr", "pasteB.gbr": "osw-light-B_Paste.gbr", "pos.csv": "osw-light-both_pos.csv"}),
    "rp2040": dict(
        repo="tommy-gilligan/RP2040-minimal-design", path="gerbers", licence="BSD-3-Clause", layers=2, tool="KiCad 7",
        note="Raspberry Pi RP2040 minimal design (updated for KiCad 7 and JLCPCB): a QFN with an exposed pad, the case of a hot part with an exposed paste window",
        files={"F.gbr": "RP2040_minimal-F_Cu.gtl", "B.gbr": "RP2040_minimal-B_Cu.gbl", "edge.gbr": "RP2040_minimal-Edge_Cuts.gm1", "drill.drl": "RP2040_minimal-PTH.drl",
               "pasteF.gbr": "RP2040_minimal-F_Paste.gtp", "pasteB.gbr": "RP2040_minimal-B_Paste.gbp", "pos.csv": "RP2040_minimal-top-pos.csv"}),
    "co60": dict(
        repo="jmdaly/CO60", path="Gerbers", licence="CC-BY-SA-4.0", layers=2, tool="KiCad", note="60 % keyboard, hand-soldered mostly (paste file of the bottom only); the copper is a large two-layer pour",
        files={"F.gbr": "co60-F_Cu.gtl", "B.gbr": "co60-B_Cu.gbl", "edge.gbr": "co60-Edge_Cuts.gm1", "drill.drl": "co60-PTH.drl", "pasteF.gbr": "co60-F_Paste.gtp",
               "pasteB.gbr": "co60-B_Paste.gbp", "pos.csv": "co60-bottom-pos.csv"}),
    "vstcm": dict(
        repo="english1234/vstcm", path="Gerbers", licence="GPL-2.0", layers=2, tool="KiCad", note="colour vector generator; paste files empty (through-hole board), position file present",
        files={"F.gbr": "vstcm V3_0FC-F_Cu.gbr", "B.gbr": "vstcm V3_0FC-B_Cu.gbr", "edge.gbr": "vstcm V3_0FC-Edge_Cuts.gbr", "drill.drl": "vstcm V3_0FC-PTH.drl",
               "pasteF.gbr": "vstcm V3_0FC-F_Paste.gbr", "pos.csv": "vstcm V3_0FC-all-pos.csv", "job.gbrjob": "vstcm V3_0FC-job.gbrjob"}),
    # Ucamco's Gerber X3 sample (KiCad 8 output): the layer files come from a zip on ucamco.com (see UCAMCO_ZIP); a component layer (X3) with the reference, footprint, value, rotation,
    # origin, courtyard and pins of every part. The licence is NOT stated on the download page: data only, never committed.
    "stickhub": dict(
        repo=None, path=None, licence="not stated (Ucamco sample)", layers=2, tool="KiCad 8.99 (Gerber X3)",
        zip_url="https://www.ucamco.com/files/downloads/file_en/514/gerber-layer-format-x3-stickhub_en.zip",
        note="StickHub, 16.6 x 40.1 mm, 1.6 mm (job file): a USB hub; component layer with TO.C, TO.CFtp, TO.CVal, TO.CRot, a courtyard outline and TO.P pins; the paste files carry TO.C",
        files={"F.gbr": "StickHub-F_Cu.gbr", "B.gbr": "StickHub-B_Cu.gbr", "edge.gbr": "StickHub-Edge_Cuts.gbr", "drill.drl": "StickHub-PTH-drl.gbr", "pasteF.gbr": "StickHub-F_Paste.gbr",
               "pasteB.gbr": "StickHub-B_Paste.gbr", "compF.gbr": "StickHub-pnp_top.gbr", "compB.gbr": "StickHub-pnp_bottom.gbr", "job.gbrjob": "StickHub-job.gbrjob"}),
}

# Other Ucamco sample archives (licence not stated; data only): the Gerber layer-format test files (rare primitives and aperture blocks, 21 files), two PCB fabrication data examples with an IPC-2581 file
# (4 and 10 copper layers) and the other X3 examples. Extracted whole into data/ucamco/<key>/ by `fetch_boards.py --ucamco`.
UCAMCO_ZIP = {
    "layer_format_tests": "https://www.ucamco.com/files/downloads/file_en/423/gerber-layer-format-test-files_en.zip",
    "fabrication_example_1": "https://www.ucamco.com/files/downloads/file_en/220/pcb-fabrication-data-test-file-1_en.zip",
    "fabrication_example_2": "https://www.ucamco.com/files/downloads/file_en/221/pcb-fabrication-data-test-file-2_en.zip",
    "x3_coldfire": "https://www.ucamco.com/files/downloads/file_en/513/gerber-layer-format-x3-kit-dev-coldfire-xilinx_en.zip",
    "x3_liion": "https://www.ucamco.com/files/downloads/file_en/515/gerber-layer-format-x3-li-ion-charger_en.zip",
}

# Sample ODB++ archives published by a library (MIT); the licence of the archives themselves is NOT stated by the repository: data only, never committed
ODB_SAMPLES = {
    "odb_wifi": dict(repo="mcix/odbpp", path="examples", name="sandbox-odb_wifi.tgz", size_kb=68),
    "odb_flat": dict(repo="mcix/odbpp", path="examples", name="flat_hierarchy-odb.tgz", size_kb=237),
    "odb_pc4": dict(repo="mcix/odbpp", path="examples", name="sandbox-odb_pc4.tgz", size_kb=616),
}


def url(key, local):
    """!
    @brief The download address of one file of one board.
    @param key Board key of BOARDS.
    @param local Local file name of the role (a key of the board's `files`).
    @return str URL on raw.githubusercontent.com (default branch of the repository).
    @throws ValueError For a board that comes from a zip (use its zip_url).
    """
    import urllib.parse
    b = BOARDS[key]
    if b.get("repo") is None:
        raise ValueError(f"{key} comes from a zip: {b.get('zip_url')}")
    return RAW.format(repo=b["repo"], path=b["path"], name=urllib.parse.quote(b["files"][local]))


def folder(key):
    """!
    @brief The local folder of a board.
    @param key Board key.
    @return pathlib.Path data/<key>.
    """
    return rb_paths.DATA / key


def roles(key):
    """!
    @brief The files of a downloaded board in the form the importer takes, plus the paste and placement files.
    @param key Board key.
    @return Dict with "copper" (paths from the top layer down), "outline" (path or None), "drills" (list), "paste_top", "paste_bottom", "placement" (paths or None), "job" (path or None),
            "component_top", "component_bottom" (Gerber X3 component layers, or None).
    @throws FileNotFoundError If the top copper file is not on disk (run scripts/fetch_boards.py).
    """
    d = folder(key)
    if not (d / "F.gbr").exists():
        raise FileNotFoundError(f"board {key!r} is not in {d}: run research/gerber-real-boards/scripts/fetch_boards.py {key}")

    def pick(name):
        """!@brief The path when the file exists, else None. @param name Local name. @return Path or None."""
        p = d / name
        return p if p.exists() else None

    copper = [p for p in (pick("F.gbr"), pick("L2.gbr"), pick("L3.gbr"), pick("B.gbr")) if p is not None]
    drills = [p for p in (pick("drill.drl"),) if p is not None]
    # A drill file written in the Gerber format (X2 file function PTH/NPTH, as KiCad's X3 output does) is not Excellon: the importer's drill reader would fail on it, so it is kept apart
    gerber_drills = [p for p in drills if p.read_text(errors="replace")[:400].lstrip().startswith("%")]
    drills = [p for p in drills if p not in gerber_drills]
    return {"copper": copper, "outline": pick("edge.gbr"), "drills": drills, "drills_gerber": gerber_drills,
            "paste_top": pick("pasteF.gbr"), "paste_bottom": pick("pasteB.gbr"), "placement": pick("pos.csv"), "job": pick("job.gbrjob"),
            "component_top": pick("compF.gbr"), "component_bottom": pick("compB.gbr")}


def available():
    """!
    @brief The boards that are on disk.
    @return List of keys of BOARDS whose top copper file exists in data/.
    """
    return [k for k in BOARDS if (folder(k) / "F.gbr").exists()]
