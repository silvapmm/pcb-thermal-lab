#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file window_shots.py
@brief Offscreen screenshots of the import window prototype (hybrid layout, light theme): the three steps and the three re-import dialogs, joined into two pictures.
@details The windows are real PySide 6 widgets with the program's own theme, fed with the RP2040 board of data/rp2040 (read in place) and the stored import "demo" (the same board with edits).
         Run through scripts/make_figures.py; needs QT_QPA_PLATFORM=offscreen. The powers on U1, U3 and U2 and the Tj limit are typed demo values, not results.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "prototypes" / "import_window"))


def _png8(img, path, width):
    """!
    @brief Save a PIL image scaled to a width, reduced to a 256-colour palette to keep the file small.
    @param img PIL image.
    @param path output PNG path.
    @param width width in pixels.
    @return None
    """
    h = round(img.height * width / img.width)
    img.convert("RGB").resize((width, h)).quantize(256, dither=0).save(path, optimize=True)


def draw_window_figures(out_steps, out_reimport):
    """!
    @brief Grab the three steps of the hybrid window and the three re-import dialogs and write the two pictures.
    @param out_steps path of the picture with the three steps stacked.
    @param out_reimport path of the picture with the three dialogs side by side.
    @return None
    """
    from PIL import Image
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import backend as be
    import ui
    from pcbthermal.gui import theme as th
    th.fix_number_locale()
    th.apply_theme(app, "light")
    wd = tempfile.mkdtemp()
    sx = ui.Session(wd, wd + "/out", "demo")
    sx.open(be.DEFAULT_BOARD, "RP2040 (git-ignored data)")
    for ref, pw in (("U1", 1.0), ("U3", 0.3), ("U2", 0.05)):
        q = sx.part(ref)
        if q and q["box"] is not None:
            q.update(use=True, power=pw, tj=125.0)
    sel = next((q for q in sx.parts if q["groups"] and q["use"]), None) or next(q for q in sx.parts if q["groups"])
    sx.selected = sel["ref"]
    sx.parts_changed.emit()
    w = ui.create_window("hybrid", sx, "light", "RP2040 board")
    w.confirm = lambda t, x: True
    w.notify = lambda t, x: None
    w.show()
    app.processEvents()
    shots = []
    tmp = Path(wd)
    for i in range(3):
        w.go(i)
        app.processEvents()
        w.repaint()
        f = tmp / f"s{i}.png"
        w.grab().save(str(f))
        shots.append(Image.open(f))
    rec = be.build_record(sx.name, sx.board, sx.files, sx.parts)
    sx.make_previous()
    dl = []
    for mode in ("replace", "update", "add"):
        d = ui.ReimportDialog(sx.previous, rec, "light", w)
        d.radios[mode].setChecked(True)
        d.show()
        app.processEvents()
        f = tmp / f"r_{mode}.png"
        d.grab().save(str(f))
        dl.append(Image.open(f))
        d.close()
    w.close()
    # the three steps one under the other, a thin white gap between them
    gap = 12
    st = Image.new("RGB", (shots[0].width, sum(s.height for s in shots) + gap * 2), "white")
    y = 0
    for s in shots:
        st.paste(s.convert("RGB"), (0, y))
        y += s.height + gap
    _png8(st, out_steps, 1100)
    rd = Image.new("RGB", (sum(s.width for s in dl) + gap * 2, dl[0].height), "white")
    x = 0
    for s in dl:
        rd.paste(s.convert("RGB"), (x, 0))
        x += s.width + gap
    _png8(rd, out_reimport, 1500)
