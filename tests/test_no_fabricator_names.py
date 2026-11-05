#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_no_fabricator_names.py
@brief The text shown to the user names no PCB manufacturer (maintainer's rule; CAD programs such as Altium, KiCad and Eagle are allowed),
       and the Summary puts a blank line between warnings.
"""

import json
import os
import re

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget

from pcbthermal.examples import example_block_board
from pcbthermal.gui import tips
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

PKG = os.path.join(os.path.dirname(__file__), "..", "pcbthermal")
FORBIDDEN = re.compile(r"JLC\s?PCB|JLC0\d|PCBWay|PCBGOGO|Bittele|AdvancedPCB|OSH\s?Park|Eurocircuits|Multi-?CB|Aisler|Seeed|Elecrow|Sierra\s+Circuits", re.I)


def _read(path):
    """!
    @brief Read a text file.
    @param path File path.
    @return File text.
    """
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_shipped_text_has_no_fabricator_name():
    """!
    @brief The tips table, the user guide, the calculator help, the shipped data files and the README hold no fabricator name.
    @return None.
    """
    texts = {"tips": "\n".join(str(v) for obj in vars(tips).values() if isinstance(obj, dict) for v in obj.values())}
    for rel in ("help/index.html", "help/calculator.html", "data/stackups.json", "data/defaults.json"):
        texts[rel] = _read(os.path.join(PKG, rel))
    texts["README"] = _read(os.path.join(PKG, "..", "README.md"))
    for name, text in texts.items():
        m = FORBIDDEN.search(text)
        assert not m, (name, m.group(0))
    json.loads(texts["data/stackups.json"])                                  # Still valid JSON


def test_window_tooltips_and_templates_have_no_fabricator_name(qtbot, tmp_path):
    """!
    @brief Every tooltip of a constructed window and the stack-up template names are free of fabricator names.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    @return None.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win._load_problem(example_block_board(), "names")
    win.stackup_page.mode.setCurrentIndex(1)
    for w in [win] + win.findChildren(QWidget):
        m = FORBIDDEN.search(w.toolTip())
        assert not m, (type(w).__name__, w.toolTip()[:80])
    from pcbthermal.model import stackup_template
    for n in (4, 6, 8, 10, 12):
        for oz in (0.5, 1):
            assert not FORBIDDEN.search(stackup_template(n, inner_oz=oz)["name"])


def test_summary_warnings_have_a_blank_line_between_them(qtbot):
    """!
    @brief The Summary tab puts one blank line between warnings, and the text table does the same.
    @param qtbot pytest-qt fixture.
    @return None.
    """
    from pcbthermal.gui.results_view import ResultsView
    view = ResultsView("light")
    qtbot.addWidget(view)
    view._show_warnings(["first", "second"])
    text = view.warnings.text()
    assert "first</span><br><br><span" in text and text.count("<br>") == 2
