#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file synthetic_board.py
@brief A small synthetic fabrication set (outline, copper layers, paste, drills, placement table) for the tests of the import window.
@details Own files, written by the test: a 40 x 30 mm board with a copper pour and a clear window, a track and three pads on the top layer, a plane on the bottom (and on inner layers
         when asked), two vias of 0.3 mm and a 3 mm component hole, three paste flashes with TO.C designators and a placement table. Nothing of a third party.
"""

import zipfile
from pathlib import Path

HEAD = "%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n"
APERTURES = "%ADD10C,0.250000*%\n%ADD11R,1.000000X1.000000*%\n%ADD12R,3.000000X2.500000*%\n%ADD13C,1.500000*%\n"
WIDTH, HEIGHT = 40.0, 30.0                                      # Board size (mm)


def _c(v):
    """!
    @brief A coordinate in the 4.6 format.
    @param v Value (mm).
    @return int
    """
    return int(round(v * 1e6))


def _flash(x, y, a):
    """!
    @brief A flash block.
    @param x X (mm).
    @param y Y (mm).
    @param a Aperture number.
    @return str
    """
    return f"D{a}*\nX{_c(x)}Y{_c(y)}D03*\n"


def _rect(x0, y0, x1, y1):
    """!
    @brief A filled rectangle region.
    @param x0 Left (mm).
    @param y0 Bottom (mm).
    @param x1 Right (mm).
    @param y1 Top (mm).
    @return str
    """
    return f"G36*\nX{_c(x0)}Y{_c(y0)}D02*\nG01*\nX{_c(x1)}Y{_c(y0)}D01*\nX{_c(x1)}Y{_c(y1)}D01*\nX{_c(x0)}Y{_c(y1)}D01*\nX{_c(x0)}Y{_c(y0)}D01*\nG37*\n"


def _line(pts, a="10"):
    """!
    @brief A polyline drawn with an aperture.
    @param pts List of (x, y) in mm.
    @param a Aperture number text.
    @return str
    """
    return f"D{a}*\nX{_c(pts[0][0])}Y{_c(pts[0][1])}D02*\n" + "".join(f"X{_c(x)}Y{_c(y)}D01*\n" for x, y in pts[1:])


def make_board(folder, inner=0, placement=True, drills=True):
    """!
    @brief Write the synthetic fabrication set into a folder.
    @param folder Folder (created).
    @param inner Number of inner copper layers (X2 `Copper,L<n>,Inr`).
    @param placement True to write the placement table.
    @param drills True to write the drill file.
    @return pathlib.Path of the folder.
    """
    d = Path(folder)
    d.mkdir(parents=True, exist_ok=True)
    n = inner + 2
    (d / "edge.gbr").write_text("%TF.FileFunction,Profile,NP*%\n" + HEAD + APERTURES + _line([(0, 0), (WIDTH, 0), (WIDTH, HEIGHT), (0, HEIGHT), (0, 0)]) + "M02*\n")
    (d / "F.gbr").write_text(f"%TF.FileFunction,Copper,L1,Top*%\n" + HEAD + APERTURES + _rect(1, 1, 39, 29) + "%LPC*%\n" + _rect(8, 10, 10, 20) + "%LPD*%\n"
                             + _line([(5, 5), (35, 5), (35, 25)]) + _flash(12, 15, 12) + _flash(25, 12, 11) + _flash(30, 20, 13) + "M02*\n")
    for k in range(inner):
        (d / f"In{k + 1}.gbr").write_text(f"%TF.FileFunction,Copper,L{k + 2},Inr*%\n" + HEAD + APERTURES + _rect(1, 1, 39, 29) + "M02*\n")
    (d / "B.gbr").write_text(f"%TF.FileFunction,Copper,L{n},Bot*%\n" + HEAD + APERTURES + _rect(1, 1, 39, 29) + "M02*\n")
    paste = "%TF.FileFunction,Paste,Top*%\n" + HEAD + APERTURES
    for ref, x, y, a in (("U1", 12, 15, 12), ("Q1", 25, 12, 11), ("D1", 30, 20, 11)):
        paste += f"%TO.C,{ref}*%\n" + _flash(x, y, a) + "%TD*%\n"
    (d / "pasteF.gbr").write_text(paste + "M02*\n")
    if drills:
        (d / "drill.drl").write_text("M48\n; #@! TF.FileFunction,Plated,1,2,PTH\nMETRIC,TZ\nT1C0.300\nT2C3.000\n%\nT1\nX20.0Y10.0\nX22.0Y10.0\nT2\nX30.0Y25.0\nM30\n")
    if placement:
        (d / "pos.csv").write_text('Ref,Val,Package,PosX,PosY,Rot,Side\n"U1","reg","SOT-223",12.0,15.0,0,top\n"Q1","fet","SOT-23",25.0,12.0,0,top\n'
                                   '"D1","led","D_0603",30.0,20.0,0,top\n"R1","1k","R_0603",20.0,25.0,0,top\n')
    return d


def make_zip(folder, zip_path):
    """!
    @brief Pack the files of a folder into a ZIP archive.
    @param folder Folder with the files.
    @param zip_path Archive path.
    @return pathlib.Path of the archive.
    """
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(Path(folder).iterdir()):
            z.write(f, f.name)
    return Path(zip_path)
