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
from pcbthermal import bundle_info
from pcbthermal.gui.help import GUIDE, AboutDialog, GuideWindow, LicencesDialog
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.model import DIELECTRICS


def test_guide_file_links_and_content():
    html = GUIDE.read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    links = re.findall(r'href="#([^"]+)"', html)
    assert links and all(l in ids for l in links), [l for l in links if l not in ids]
    # The guide mentions every model, every part field, every tool key and every dielectric preset of the program
    for word in ("FVM", "FDM", "LPTN", "Analytic", "3D solid", "θ junction-pad", "Tj max", "ψJB", "Power coefficient", "Heatsink θSA", "Board outline", "Manual input", "Preferences: defaults and libraries", "everything depends on the copper", "empty board", "epoxy resin plug", "Side panels", "remembers the size and place of the docks", "goes to the next field", "the key of the JSON file", "shows what zero means", "No results yet", "Direct contact", "Greyed fields", "Add a vertex here", "rectangle of the same area", "laminate under the copper", "two laminate nodes", "Rings narrower than one cell", "Zones of a part over a group of vias", "rest of the footprint", "core", "zone", "Memory limit", "--memory-fraction", "PCBTHERMAL_MEMORY_BYTES", "Largest Gerber or drill file", "exits with code 3", "Paste of its right-click menu", "project format 2", "copper over only part of its footprint", "never overwriting an older copy", "Stack-up", "Power Calculator", "Cancel", "F1", "Cooling model", "Metal block", "Edge of the board in the Analytic model", "eigenfunctions of the convective edge", "interface sheet", "contact area", "Prepreg", "Load typical stack-up", "Inner copper", "stackups.json", "Board description", "design uncertainty", "Vertical natural convection", "low face Rayleigh number", "--natural-form", "--laminate-n-max", "Laminate sub-gap", "hottest at the face", "thick and poorly conducting", "channel Rayleigh number", "top-path split", "Model-limit warnings", "ignored</b> by every model", "bare laminate", "engineering notation", "list of the sections", "thousands separator", "Via warnings", "touching the board edge", "mirror image of the edge", "coarse for the vias", "SOR not used", "relaxation factor", "constriction", "tile of the via correction", "sub-gaps of at most 0.4 mm", "face value", "each plan column", "unsafe for a design", "small against the sub-layer of laminate", "limits of the models you selected", "Warnings box of the Simulation settings", __version__ if False else "Quick start", "Imported copper", "replaces the zones of its layer", "faces", "pixels per cell", "Mapping", "Import Gerber board", "stepper", "Import now", "claim one function", "detected from", "never extracted to disk", "which CAD tool wrote the files", "Tool not recognised", "Help us test your CAD tool", "by position (approx.)", "legend</b> of the diameter classes", "Element names", "View - Imported copper", "paste TO.C + placement", "match no part", "orphan", "Update</b> after a layout revision", "job file", "keep what you did in the editor", "not taken: use Replace or Update", "Equiv. rect.", "Exposed pad.", "exposed pad (proposed)", "dominant group of paste openings", "dashed amber line", "largest opening only</i> is gone", "thick dashed outline", "Computed coefficients are not measured", "2.5.0 or later", "Live or after the run", "Light / dark theme", "Select all on the layer", "Import Gerber board</b> (<a href=\"#import\">section 13</a>)", "never been compared with a measured copper board", "Views of the maps", "Underlay", "All (2 × 2)", "the solver resolution is the cell", "colour bar", "4096 pixels", "invisible to them", "Terrain is greyed in the Animation", "Contour every</b> is greyed unless View is Terrain", "Display</b> button", "Map opacity", "Colour map</b>: one choice for every map", "does not take the keyboard", "Run a simulation first", "The result is outdated: run the simulation again", "card</b> at the top left", "not drawn on an outline board", "display_popover.png", "a change of tab", "New project from these files", "Carry the parts of the stored import over by designator", "Another board or a revision?", "That value was refused", "above 1 km (1e6 mm)", "byte for byte as they were read", "never the text itself", "Project packages", "Include the source files (Gerbers, drills, placement, BOM)", "Export package", "Use the stored files", "ZIP without <code>manifest.json</code> is refused", "one choice for the whole program", "the latest pick wins", "click the name", "The part is near a side of the board", "A heat source narrower than two cells", "laminate band along the board edge", "no gap is cut", "Fast waves: average + ripple", "added at the heater</b>", "quarter of the narrow side of the smallest part", "Markers on the temperature maps", "red ring</b> and the coolest with a <b>blue ring", "is greyed for another board", "greyed on an imported board", "layer span", "treated as through vias", "Cut overlay</b> box of the tab shows or hides it", "until then the label is greyed", "at the end of its row", "two-line headers that name the read-out", "Tmax °C (surface)", "Tmean °C (all layers)", "Error vs FVM (of ΔT)", "0.00 %", "accordion", "Warnings (N)", "Next layer, previous layer", "click a row", "Holes: vias / component / non-plated", "round dot", "Run / Stop", "reads <b>Stop</b>", "There is no Pause", "Warning:</i> or <i>Note:", "Filter elements", "never fires the window letters", "never deletes the selected element", "hidden by the filter", "indication, not a verification", "Typical values with no source", "Azar and Graebner", "depends on it", "surface read-out", "always computes and always shows both numbers", "What was decided, and why", "SURFACE_DECISIONS", "--surface-files", "column</b> read-out", "Surface (top)", "upper estimate</b> beyond", "Surface temperature and column mean", "My result differs from the paper", "Film through the copper (always on)", "a view, never a mode", "Max &deg;C (surface, estimate)", "results_surface.png", "Finite elements (FEM)", "FEM in time", "the one to believe from about 0.3 s", "choose Crank-Nicolson to read the first seconds", "predicted to take more than 10 minutes", "capacity inventory", "FEM: refused", "surface read-out</b> (the face", "pyamg", "--model fem", "FEM gap elements", "FEM refinement", "hottest mesh node", "Solving FEM", "never greyed", "the line above the tables and the chart title name it", "Tmax: hottest point under the part", "FVM (ref.)", "Parts by model", "parts_by_model.csv", "scroll together", "Tmax (column)</i> and <i>Tmean (all layers)", "copper thicker than 105 &micro;m is cut into several slabs"):
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
    for word in ("Quick start: import a Gerber board", "Glossary of the warnings", "What is validated and what is not", "solver.memory_fraction", "results.summary_table_in_report", "Summary table in the report text", "gerber.max_file_mb", "package.max_mb",
                 "copper over only part of its footprint", "Via touches no copper on a layer", "Analytic time simulation with a heatsink", "mirror image of the edge", "heater_shapes_rp2040.png",
                 "passive parts offer the hull and the box", "No measured copper board", "Orphan part"):
        assert word in html, word
    # The picture of the walkthrough ships beside the guide
    assert (GUIDE.parent / "heater_shapes_rp2040.png").exists()
    # Every picture the guide points to ships beside it, and the README pictures exist in docs/images
    for name in re.findall(r'<img src="([^"]+)"', html):
        assert (GUIDE.parent / name).exists(), name
    for name in ("import_step1", "import_step2", "import_step3", "import_reimport", "editor_imported", "editor_warnings", "preferences_solver_gerber",
                 "results_views", "results_views_dark", "results_terrain", "results_gradient", "animation_underlay", "editor_overlay", "background_dialog",
                 "editor_background", "import_reimport_different", "results_profile_cut"):
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
    assert "pyamg" in txt and "optional" in txt                              # The optional library of the finite-element model
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


def test_guide_says_drawn_copper_is_read_like_imported_copper():
    """!
    @brief The copper zone row of the guide says that a layer whose edges cut the cells is read like imported copper, and what it costs.

    @return None
    """
    html = GUIDE.read_text(encoding="utf-8")
    for word in ("read like imported copper", "exact area of the zones", "flow-based faces"):
        assert word in html, word


def test_about_box_states_qt_and_opens_the_licences(qtbot):
    """!
    @brief LGPL 3.0 section 4(c): the About box carries the copyright line of Qt with its loaded versions and a way to the licence texts; the live line and the copy button work.
    @param qtbot pytest-qt fixture.
    """
    from PySide6.QtCore import qVersion
    from PySide6.QtGui import QGuiApplication

    about = AboutDialog()
    qtbot.addWidget(about)
    txt = about.text.text()
    assert "Qt" in txt and "GNU Lesser General Public License version 3" in txt and "The Qt Company Ltd." in txt and qVersion() in txt
    assert "from source" in txt or "packaged build" in txt
    assert 'href="mailto:silva.pmm@gmail.com"' in txt and "Pedro Silva (PMS Labs)" in txt      # The contact line, published on purpose (maintainer)
    assert about.b_licences.toolTip() and about.b_licences.text().startswith("Licences")
    about.copy_version_info()
    clip = QGuiApplication.clipboard().text()
    assert __version__ in clip and qVersion() in clip
    dlg = LicencesDialog(about)
    qtbot.addWidget(dlg)
    assert len(dlg.leaves) >= 3 and "MIT License" in dlg.view.toPlainText()            # From source the first entry is the LICENSE of the program
    assert all(len(e) == 3 and e[2] for e in dlg.entries)                              # Every entry has a tooltip text (the full path or a description)


def test_packaged_licences_are_listed_by_library(tmp_path, monkeypatch):
    """!
    @brief In a packaged build the Licences list has one entry per library folder (its files joined under headings), not one per file.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    """
    lic = tmp_path / "licenses"
    for sub, files in {"Qt": ["LGPL-3.0.txt", "GPL-3.0.txt"], "numpy-2.5.5": ["licenses/LICENSE.txt"], "scipy-1.18.1": ["LICENSE.txt", "LICENSES_bundled.txt"]}.items():
        for f in files:
            (lic / sub / f).parent.mkdir(parents=True, exist_ok=True)
            (lic / sub / f).write_text(f"text of {f}")
    (lic / "INDEX.txt").write_text("index")
    (tmp_path / "LICENSE").write_text("MIT")
    monkeypatch.setattr(bundle_info, "packaged", lambda: True)
    monkeypatch.setattr(bundle_info, "licences_folder", lambda: lic)
    titles = [e[0] for e in bundle_info.licence_entries()]
    assert titles.count("numpy-2.5.5") == 1 and "scipy-1.18.1" in titles and "LGPL-3.0, GPL-3.0 and notices" in titles
    assert not any("/" in t and t != "licenses/INDEX.txt" for t in titles)
    scipy_text = next(e[1] for e in bundle_info.licence_entries() if e[0] == "scipy-1.18.1")
    assert "===== LICENSE.txt =====" in scipy_text and "===== LICENSES_bundled.txt =====" in scipy_text


def _fake_package(tmp_path, monkeypatch):
    """!
    @brief A fake packaged build: the top-level notices, licenses/INDEX.txt, a Qt folder and two library folders.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @return pathlib.Path of the licenses folder.
    """
    lic = tmp_path / "licenses"
    for sub, files in {"Qt": ["LGPL-3.0.txt", "GPL-3.0.txt"], "numpy-2.5.5": ["LICENSE.txt"], "scipy-1.18.1": ["LICENSE.txt"]}.items():
        for f in files:
            (lic / sub / f).parent.mkdir(parents=True, exist_ok=True)
            (lic / sub / f).write_text(f"text of {sub}/{f}")
    (lic / "INDEX.txt").write_text("index")
    for name in bundle_info.TEXT_FILES:
        (tmp_path / name).write_text(f"text of {name}")
    monkeypatch.setattr(bundle_info, "packaged", lambda: True)
    monkeypatch.setattr(bundle_info, "licences_folder", lambda: lic)
    return lic


def test_licences_groups_packaged_and_from_source(tmp_path, monkeypatch):
    """!
    @brief The Licences window has three groups in a fixed order; every packaged entry is under the right one and none is lost from the flat list.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    """
    names = {g: [e[0] for e in items] for g, items in bundle_info.licence_groups()}      # From source: LICENSE, Qt, the table
    assert list(names) == list(bundle_info.GROUPS)
    assert names["The package"] == ["LICENSE"] and len(names["Qt and PySide"]) == 1 and names["Bundled libraries"] == [bundle_info.TABLE_TITLES[1]]
    _fake_package(tmp_path, monkeypatch)
    groups = dict(bundle_info.licence_groups())
    assert [e[0] for e in groups["The package"]] == list(bundle_info.TEXT_FILES)
    assert [e[0] for e in groups["Qt and PySide"]] == ["LGPL-3.0, GPL-3.0 and notices"]
    assert groups["Qt and PySide"][0][1].startswith("===== LGPL-3.0.txt =====")                      # The LGPL text first (the licence Qt is used under), then the GPL
    assert [e[0] for e in groups["Bundled libraries"]] == [bundle_info.TABLE_TITLES[0], "licenses/INDEX.txt", "numpy-2.5.5", "scipy-1.18.1"]
    flat = [e[0] for e in bundle_info.licence_entries()]
    assert flat == [e[0] for _, items in bundle_info.licence_groups() for e in items] and len(flat) == 5 + 1 + 4      # Nothing lost, nothing twice


def test_licences_window_is_a_tree_with_headers(qtbot, tmp_path, monkeypatch):
    """!
    @brief The window shows three non-selectable headers with the entries as children; choosing a child shows its text, a header shows none, the keyboard skips headers.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    """
    from PySide6.QtCore import Qt

    _fake_package(tmp_path, monkeypatch)
    dlg = LicencesDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    tree = dlg.tree
    assert [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())] == list(bundle_info.GROUPS)
    assert [tree.topLevelItem(i).childCount() for i in range(3)] == [5, 1, 4]
    for i in range(3):
        assert not (tree.topLevelItem(i).flags() & Qt.ItemIsSelectable)
    assert len(dlg.leaves) == len(dlg.entries) == 10
    assert all(leaf.toolTip(0) for leaf in dlg.leaves)
    assert dlg.leaves[0].toolTip(0).endswith("LICENSE") and dlg.view.toPlainText() == "text of LICENSE"       # The first entry is selected at the start
    qtbot.keyClick(tree, Qt.Key_Down)
    assert tree.currentItem() is dlg.leaves[1]
    for _ in range(4):
        qtbot.keyClick(tree, Qt.Key_Down)
    assert tree.currentItem().parent().text(0) == "Qt and PySide"                    # Down from the last of the package jumps the header, to the first of the next group
    assert "text of Qt/" in dlg.view.toPlainText()
    qtbot.keyClick(tree, Qt.Key_Up)
    assert tree.currentItem() is dlg.leaves[4]                                        # Up skips the header too
    for _ in range(12):
        qtbot.keyClick(tree, Qt.Key_Up)
    assert tree.currentItem() is dlg.leaves[0]                                        # At the top it stays on the first entry, not on a header
    dlg.show_entry(tree.topLevelItem(0))
    assert dlg.view.toPlainText() == ""


def test_library_table_wrapping_keeps_every_word_and_the_limit():
    """!
    @brief The wrapped table has no line longer than the width, keeps every library, version and licence word of the unwrapped one, and continuation lines sit under the licence column.
    @return None
    """
    flat = bundle_info.table_text(None)
    for width in (100, 80, 60):
        wrapped = bundle_info.table_text(width)
        assert max(len(ln) for ln in wrapped.splitlines()) <= width
        assert wrapped.split() == flat.split()                                       # The same words in the same order: nothing lost, nothing cut
        assert len(wrapped.splitlines()) >= len(flat.splitlines())
    narrow = bundle_info.table_text(60).splitlines()
    lead = max(len(r[0]) for r in bundle_info.libraries()) + 14
    continuation = [ln for ln in narrow if ln.startswith(" ")]
    assert continuation and all(ln.startswith(" " * lead) and not ln[lead].isspace() for ln in continuation)
    assert len(flat.splitlines()) == len(bundle_info.libraries())                   # Unwrapped: one line per library


def test_licences_table_needs_no_horizontal_scroll_at_natural_size(qtbot, tmp_path, monkeypatch):
    """!
    @brief At the natural size (900 x 600) and at the minimum size the library table fits the text view with no horizontal scroll bar, and the window can be that small.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    """
    _fake_package(tmp_path, monkeypatch)
    dlg = LicencesDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    table = next(leaf for leaf in dlg.leaves if leaf.text(0) in bundle_info.TABLE_TITLES)
    for size in ((900, 600), (dlg.minimumWidth(), dlg.minimumHeight())):
        dlg.resize(*size)
        dlg.tree.setCurrentItem(dlg.leaves[0])
        dlg.tree.setCurrentItem(table)
        qtbot.wait(20)
        text = dlg.view.toPlainText()
        char = dlg.view.fontMetrics().horizontalAdvance("0")
        longest = max(len(ln) for ln in text.splitlines())
        assert longest * char <= dlg.view.viewport().width(), (size, longest, char, dlg.view.viewport().width())
        assert not dlg.view.horizontalScrollBar().isVisible() or dlg.view.horizontalScrollBar().maximum() == 0
        assert text.split() == bundle_info.table_text(None).split()
    assert dlg.minimumSizeHint().width() <= 900 and dlg.minimumSizeHint().height() <= 600


def test_library_table_edge_cases():
    """!
    @brief No metadata gives a sentence instead of an exception (the Licences window must still open); a version longer than 10 characters widens its column so that
           every licence line, first or continued, starts in the same column; a single word longer than the licence column is kept whole.
    @return None
    """
    assert "No library metadata" in bundle_info.table_text(80, [])
    rows = [("a", "1.0", "MIT"), ("longer-name", "2026.10.1.post12", "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only AND ünïcödé ≥ 1"),
            ("b", "2.0", "X" * 90 + " AND MIT")]
    lines = bundle_info.table_text(60, rows).splitlines()
    lead = len("longer-name") + 2 + len("2026.10.1.post12") + 2
    assert all(len(ln) > lead and not ln[lead].isspace() and not ln[lead - 1].strip() for ln in lines)       # Every licence fragment starts at the same column
    assert "X" * 90 in bundle_info.table_text(60, rows)                                                      # Not cut inside the word
    assert bundle_info.table_text(60, rows).split() == bundle_info.table_text(None, rows).split()


def test_licences_window_home_end_page_keys_and_header_clicks(qtbot, tmp_path, monkeypatch):
    """!
    @brief Home, End and the page keys land on entries, never on a header (Home from the last entry once stayed there); a click on a header opens the first entry of that
           group; a resize re-wraps the table from the rows read once, without reading the metadata again.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    """
    from PySide6.QtCore import Qt

    _fake_package(tmp_path, monkeypatch)
    dlg = LicencesDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    tree = dlg.tree
    qtbot.keyClick(tree, Qt.Key_End)
    assert tree.currentItem() is dlg.leaves[-1]
    qtbot.keyClick(tree, Qt.Key_Home)
    assert tree.currentItem() is dlg.leaves[0]
    for key in (Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_PageDown):
        qtbot.keyClick(tree, key)
        assert tree.currentItem().parent() is not None
    for i, first in ((0, 0), (1, 5), (2, 6), (0, 0)):
        tree.setCurrentItem(dlg.leaves[3 if i else -1])
        qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=tree.visualItemRect(tree.topLevelItem(i)).center())
        assert tree.currentItem() is dlg.leaves[first], (i, tree.currentItem().text(0))
    calls = []
    monkeypatch.setattr(bundle_info, "libraries", lambda: calls.append(1) or [])
    tree.setCurrentItem(dlg.leaves[6])                                                # The library table
    for w in range(780, 900, 20):
        dlg.resize(w, 500)
        qtbot.wait(5)
    assert not calls and "numpy" in dlg.view.toPlainText().lower()                   # Re-wrapped from the rows read when the window opened


def test_licences_table_fits_with_a_proportional_fallback_font(qtbot, tmp_path, monkeypatch):
    """!
    @brief If none of the fixed-width fonts of the style sheet exists and a proportional font stands in, the wrapped table still needs no horizontal scroll bar
           (the width is measured in pixels, not assumed from the advance of one character).
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    """
    _fake_package(tmp_path, monkeypatch)
    dlg = LicencesDialog()
    qtbot.addWidget(dlg)
    dlg.rows = [("numpy", "2.5.5", "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 " * 3), ("PySide6", "6.12.0", "WWWW MMMM " * 12)]
    dlg.view.setStyleSheet("font-family: 'Helvetica', 'Arial', 'DejaVu Sans', sans-serif; font-size: 15px;")
    dlg.show()
    dlg.resize(760, 400)
    dlg.tree.setCurrentItem(dlg.leaves[0])
    dlg.tree.setCurrentItem(dlg.leaves[6])
    qtbot.wait(20)
    fm = dlg.view.fontMetrics()
    widest = max(fm.horizontalAdvance(ln) for ln in dlg.view.toPlainText().splitlines())
    assert widest <= dlg.view.viewport().width(), (widest, dlg.view.viewport().width(), dlg.view.font().family())


def test_library_table_covers_every_runtime_requirement_with_a_licence():
    """!
    @brief The table of the About box is generated from the metadata and holds every run-time line of requirements.txt, each with a recognised licence.
    @return None
    """
    root = pathlib_root()
    names = []
    for raw in (root / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and not line.lower().startswith("pytest"):
            names.append(re.match(r"[A-Za-z0-9._-]+", line).group(0))
    table = {bundle_info.normal(n): lic for n, v, lic in bundle_info.libraries()}
    assert set(bundle_info.normal(r) for r in bundle_info.ROOTS) >= set(bundle_info.normal(n) for n in names)            # The roots of the table are the requirements
    for n in names:
        key = bundle_info.normal(n)
        found = next((k for k in table if k == key or (key == "pyside6" and k.startswith("pyside6"))), None)
        assert found is not None, f"{n} is not in the library table"
        assert table[found], f"{n} has no recognised licence in the table"
    assert all(lic for lic in table.values()), [k for k, lic in table.items() if not lic]


def pathlib_root():
    """!
    @brief The repository folder.
    @return pathlib.Path.
    """
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent
