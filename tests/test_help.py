"""!
@file test_help.py
@brief Help menu: the user guide opens (in the program), its links work, it documents what the program has, and the About box shows the program data.
"""

import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from pcbthermal import __author__, __project_url__, __version__
from pcbthermal.gui.document import Document
from pcbthermal.gui.help import GUIDE, AboutDialog, GuideWindow
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.model import DIELECTRICS


def test_guide_file_links_and_content():
    html = GUIDE.read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    links = re.findall(r'href="#([^"]+)"', html)
    assert links and all(l in ids for l in links), [l for l in links if l not in ids]
    # The guide mentions every model, every part field, every tool key and every dielectric preset of the program
    for word in ("FVM", "FDM", "Lumped", "Analytic", "3D solid", "θ junction-pad", "Tj max", "ψJB", "Power coefficient", "Heatsink θSA", "Board outline",
                 "Stack-up", "Power calculator", "Cancel", "F1", "Cooling model", "Metal block", "contact area", "Prepreg", "Load typical stack-up", "stackups.json", __version__ if False else "Quick start"):
        assert word in html, word
    for entry in DIELECTRICS:
        assert entry[0].split(" (")[0].split(" high")[0].split(" ceramic")[0] in html or entry[0] in html, entry[0]
    assert "<script" not in html                                       # Nothing external, nothing running


def test_guide_window_about_and_menu(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    win = MainWindow(Document(), QSettings(str(tmp_path / "h.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    menus = {a.text().replace("&", ""): a.menu() for a in win.menuBar().actions()}
    help_items = [a.text() for a in menus["Help"].actions() if a.text()]
    assert "User guide" in help_items and any(t.startswith("About") for t in help_items)
    win.show_guide()
    g = win._guide
    assert isinstance(g, GuideWindow) and "Quick start" in g.view.toPlainText() and g.isVisible()
    g.search.setText("Board outline")
    g.find_next()
    assert g.view.textCursor().selectedText() == "Board outline"
    g.search.setText("no such phrase anywhere")
    g.find_next()                                                      # Not found: no crash
    g.close()
    about = AboutDialog(win)
    qtbot.addWidget(about)
    txt = about.text.text()
    assert __version__ in txt and __author__ in txt and __project_url__ in txt and "Python" in about.libs.text()
    # The tab shortcuts exist (Ctrl+1 to Ctrl+4) and switch the tab
    from PySide6.QtGui import QKeySequence
    by_key = {a.shortcut().toString(): a for a in win.actions()}
    for n, idx in ((2, 1), (4, 3), (1, 0)):
        by_key[f"Ctrl+{n}"].trigger()
        assert win.tabs.currentIndex() == idx
    assert win.a_guide.shortcut() == QKeySequence("F1")
