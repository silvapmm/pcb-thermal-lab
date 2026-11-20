#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_icon.py
@brief The application icon files in `ico/`, their sizes and the icon the window uses.
"""

import os
import struct
import subprocess
from pathlib import Path

import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
ICO = ROOT / "ico"
PNG_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def test_master_and_png_set_have_the_size_in_their_name():
    """!
    @brief The master is 1024 px and every file of the PNG set has the pixel size its name says, with transparency.
    @return None
    """
    with Image.open(ICO / "pcb-board.png") as im:
        assert im.size == (1024, 1024)
    for s in PNG_SIZES:
        with Image.open(ICO / "png" / f"pcb-board_{s}.png") as im:
            assert im.size == (s, s), s
            assert im.mode == "RGBA"
            # The corners of the rounded tile are transparent (a tile on any background)
            assert im.getpixel((0, 0))[3] == 0
    assert sorted(p.name for p in (ICO / "png").iterdir()) == sorted(f"pcb-board_{s}.png" for s in PNG_SIZES)


def test_ico_holds_every_size():
    """!
    @brief The single Windows .ico stores the sizes 16 to 256 px (read from its directory).
    @return None
    """
    data = (ICO / "pcb-board.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1)
    sizes = set()
    for i in range(count):
        w, h = struct.unpack("<BB", data[6 + 16 * i:8 + 16 * i])
        sizes.add((w or 256, h or 256))
    assert sizes == {(s, s) for s in ICO_SIZES}


def test_icns_is_a_real_icns():
    """!
    @brief The macOS .icns exists, is not empty and starts with the icns magic.
    @return None
    """
    data = (ICO / "pcb-board.icns").read_bytes()
    assert len(data) > 10000 and data[:4] == b"icns"


def test_old_icons_are_gone_and_not_referenced():
    """!
    @brief The two old .ico files are deleted and no tracked text file names them.
    @return None
    """
    assert not (ICO / "pcb-board_128x128.ico").exists() and not (ICO / "pcb-board_256x256.ico").exists()
    out = subprocess.run(["git", "grep", "-l", "-I", "-e", "pcb-board_128x128", "-e", "pcb-board_256x256", "--", ".",
                          ":(exclude)tests/test_icon.py"], cwd=ROOT, capture_output=True, text=True)
    assert out.stdout.strip() == "", out.stdout


def test_window_icon_offers_every_size():
    """!
    @brief The QIcon of the window is built from the PNG set and offers every size without scaling the master.
    @return None
    """
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from pcbthermal.gui.help import app_icon
    app = QApplication.instance() or QApplication([])
    assert app is not None
    icon = app_icon()
    assert not icon.isNull()
    avail = {(s.width(), s.height()) for s in icon.availableSizes()}
    assert avail == {(s, s) for s in PNG_SIZES}
    # A pixmap of an available size is that file, not a scaled copy
    assert icon.pixmap(16, 16).width() == 16
