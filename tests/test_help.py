#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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
    for word in ("FVM", "FDM", "Lumped", "Analytic", "3D solid", "θ junction-pad", "Tj max", "ψJB", "Power coefficient", "Heatsink θSA", "Board outline", "Manual input", "Preferences: defaults and libraries", "everything depends on the copper", "empty board", "epoxy resin plug", "Side panels", "remembers the size and place of the docks", "goes to the next field", "the key of the JSON file", "shows what zero means", "No results yet", "Direct contact", "Greyed fields", "Add a vertex here", "rectangle of the same area", "laminate under the copper", "two laminate nodes", "Rings narrower than one cell", "Zones of a part over a group of vias", "rest of the footprint", "core", "zone", "Memory limit", "--memory-fraction", "PCBTHERMAL_MEMORY_BYTES", "Largest Gerber or drill file", "exits with code 3", "Paste of its right-click menu", "until then a click does nothing",
                 "project format 2", "copper over only part of its footprint", "never overwriting an older copy", "Stack-up", "Power Calculator", "Cancel", "F1", "Cooling model", "Metal block", "Edge of the board in the Analytic model", "eigenfunctions of the convective edge", "interface sheet", "contact area", "Prepreg", "Load typical stack-up", "Inner copper", "stackups.json", "Board description", "design uncertainty", "Vertical natural convection", "low face Rayleigh number", "--natural-form", "--laminate-n-max", "Laminate sub-gap", "hottest at the face", "thick and poorly conducting", "channel Rayleigh number", "top-path split", "Model-limit warnings", "ignored</b> by every model", "bare laminate", "engineering notation", "list of the eight sections", "thousands separator", "click a warning", "Via warnings", "touching the board edge", "mirror image of the edge", "coarse for the vias", "SOR not used", "relaxation factor", "constriction", "tile of the via correction", "sub-gaps of at most 0.4 mm", "face value", "each plan column", "unsafe for a design", "small against the sub-layer of laminate", "limits of the models you selected", "hold the mouse on", "the list under Run shows a one-line form", __version__ if False else "Quick start", "Imported copper", "replaces the zones of its layer", "faces", "pixels per cell", "Mapping", "Import Gerber board", "stepper", "Import now", "claim one function", "detected from", "never extracted to disk", "which CAD tool wrote the files", "Tool not recognised", "Help us test your CAD tool", "by position (approx.)", "legend</b> of the diameter classes", "Element names", "View - Imported copper", "paste TO.C + placement", "match no part", "orphan", "Update</b> after a layout revision", "job file", "keep what you did in the editor", "not taken: use Replace or Update", "Equiv. rect.", "Exposed pad.", "exposed pad (proposed)", "dominant group of paste openings", "dashed amber line", "largest opening only</i> is gone", "thick dashed outline", "Computed coefficients are not measured", "2.5.0 or later", "Live or after the run", "Light / dark theme", "Select all on the layer", "Import Gerber board</b> (<a href=\"#import\">section 13</a>)", "never been compared with a measured copper board", "Views of the maps", "Underlay", "All (2 x 2)", "the solver resolution is the cell", "colour bar", "4096 pixels", "invisible to them", "Terrain is greyed in the Animation", "Contour every</b> is greyed unless View is Terrain", "Display</b> button", "Map opacity", "Colour map</b>: one choice for every map", "does not take the keyboard", "Run a simulation first", "The result is outdated: run the simulation again", "card</b> at the top left", "not drawn on an outline board", "display_popover.png", "a change of tab"):
        assert word in html, word
    for entry in DIELECTRICS:
        assert entry[0].split(" (")[0].split(" high")[0].split(" ceramic")[0] in html or entry[0] in html, entry[0]
    assert "<script" not in html                                       # Nothing external, nothing running


def test_guide_gerber_walkthrough_glossary_and_validity():
    """!
    @brief The guide has the Gerber quick start, the glossary of the warnings and the validity table, in reading order.

    @return None
    """
    html = GUIDE.read_text(encoding="utf-8")
    # Anchors that the walkthrough, the table of contents and the cross references need
    for anchor in ("start-gerber", "import", "imported", "prefs", "files", "keys", "limits", "warnings", "validity"):
        assert 'id="%s"' % anchor in html, anchor
    # The sections are numbered in the order they appear (no 12b, 13b or 13c left)
    numbers = [int(n) for n in re.findall(r'<h2 id="[^"]+">(\d+)\. ', html)]
    assert numbers == list(range(1, len(numbers) + 1)), numbers
    assert not re.search(r'<h2 id="[^"]+">\d+[a-z]\.', html)
    # The table of contents lists every section once
    toc = re.search(r"<nav>.*?</nav>", html, re.S).group(0)
    assert len(re.findall(r'href="#', toc)) >= len(numbers)
    # Stale statements of the time when only the reader existed must be gone
    for stale in ("no import window", "no interface yet", "reader only", "moves the edge loss to the faces", "Largest opening only</i> is for"):
        assert stale not in html, stale
    for word in ("Quick start: import a Gerber board", "Glossary of the warnings", "What is validated and what is not", "solver.memory_fraction", "gerber.max_file_mb",
                 "copper over only part of its footprint", "Analytic time simulation with a heatsink", "mirror image of the edge", "heater_shapes_rp2040.png",
                 "passive parts offer the hull and the box", "No measured copper board", "Orphan part"):
        assert word in html, word
    # The picture of the walkthrough ships beside the guide
    assert (GUIDE.parent / "heater_shapes_rp2040.png").exists()
    # Every picture the guide points to ships beside it, and the README pictures exist in docs/images
    for name in re.findall(r'<img src="([^"]+)"', html):
        assert (GUIDE.parent / name).exists(), name
    for name in ("import_step1", "import_step2", "import_step3", "import_reimport", "editor_imported", "editor_warnings", "preferences_solver_gerber",
                 "results_views", "results_views_dark", "results_terrain", "results_gradient", "animation_underlay", "editor_overlay", "background_dialog",
                 "editor_background", "import_reimport_different"):
        assert 'src="%s.png"' % name in html, name


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
    assert __version__ in txt and __author__ in txt and __project_url__ in txt
    assert "Gerber" in txt and "not against a measured board" in txt          # The import and the honest note about the validation
    # The tab shortcuts exist (Ctrl+1 to Ctrl+4) and switch the tab
    from PySide6.QtGui import QKeySequence
    by_key = {a.shortcut().toString(): a for a in win.actions()}
    for n, idx in ((2, 1), (4, 3), (1, 0)):
        by_key[f"Ctrl+{n}"].trigger()
        assert win.tabs.currentIndex() == idx
    assert win.a_guide.shortcut() == QKeySequence("F1")


def test_guide_states_the_background_image_rule():
    """!
    @brief The guide says the background image is for hand-drawn boards and disabled for Gerber projects.

    @return None
    """
    html = GUIDE.read_text(encoding="utf-8")
    assert "View - Background image" in html and "only remove the image" in html
