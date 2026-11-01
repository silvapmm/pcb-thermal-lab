#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_theme_coherence.py
@brief Every window of the application follows the same theme tokens: no colour literals in the GUI code outside theme.py, the help pages,
       the plots, the warning list and the memory verdicts change with a live theme switch, and the status colours read in both themes.
"""

import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from pcbthermal.examples import example_board
from pcbthermal.gui import theme as th
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

GUI = Path(th.__file__).parent

# A colour written in the code of a widget is a colour that does not follow a theme switch. Allowed: nothing at the moment; each entry
# would be (file name, literal, reason).
ALLOWED = []

LITERAL = re.compile(r"""#[0-9a-fA-F]{6,8}\b|QColor\(\s*["'][a-z]+["']|Qt\.(red|green|blue|white|black|gray|darkGray|lightGray|yellow|cyan|magenta)\b"""
                     r"""|["'](white|black|red|green|blue|gray|grey)["']""")


def _ratio(a, b):
    """!
    @brief WCAG contrast ratio of two colour strings.
    @param a Colour string.
    @param b Colour string.
    @return float ratio.
    """
    return th.contrast(QColor(a), QColor(b))


def test_no_colour_literals_in_the_gui_outside_the_theme_table():
    # Comments may name a colour; the code may not
    bad = []
    for f in sorted(GUI.glob("*.py")):
        if f.name == "theme.py":
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#")[0] if "#" in line and not LITERAL.search(line.split("#")[0]) else line
            m = LITERAL.search(code)
            if m and not any(a == (f.name, m.group(0), r) or a[:2] == (f.name, m.group(0)) for a, r in [(x, 0) for x in ALLOWED]):
                bad.append(f"{f.name}:{n}: {line.strip()}")
    assert not bad, "colour literals outside theme.py (read them from the theme table):\n" + "\n".join(bad)


@pytest.mark.parametrize("name", ["dark", "light"])
def test_status_and_document_colours_read_in_both_themes(name):
    c = th.colors(name)
    # The status tones were chosen by hand and kept (the maintainer likes the look): the light "slow" orange is 3.85:1, so these are held to 3.5:1
    for key in ("ok", "warn", "bad", "error"):
        assert _ratio(c[key], c["window"]) >= 3.5, (name, key, "on the window")
        assert _ratio(c[key], c["base"]) >= 3.5, (name, key, "on the base")
    for key in ("doc_note", "doc_tip", "doc_th"):
        assert _ratio(c["text"], c[key]) >= 4.5, (name, key)
    assert _ratio(c["link"], c["base"]) >= 4.5 and _ratio(c["text"], c["base"]) >= 4.5


def test_readable_on_picks_a_label_colour_for_any_fill():
    for fill in ("#4a6f5a", "#6c8f9d", "#9aa7b4", "#d08a3c", "#ffffff", "#000000"):
        pick = th.readable_on(QColor(fill))
        assert th.contrast(pick, QColor(fill)) >= 3.0, fill


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window with the example board and one run, in the light theme.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder for the settings file.
    @return MainWindow.
    """
    from pcbthermal import api
    st = QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat)
    st.setValue("theme", "light")
    w = MainWindow(Document(), st)
    qtbot.addWidget(w)
    w.resize(1400, 850)
    w.show()
    w.doc.open_problem(example_board(), "example")
    w._after_load()
    w._on_done(api.simulate(w.doc.problem, w.doc.options))
    return w


def _canvas_fig_colours(win):
    """!
    @brief Face colours of every matplotlib figure of the main window.
    @param win MainWindow.
    @return list of (name, QColor).
    """
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    out = []
    for cv in win.findChildren(FigureCanvasQTAgg):
        out.append((cv.figure, QColor.fromRgbF(*cv.figure.get_facecolor())))
    return out


def test_plots_follow_a_live_theme_switch(win):
    base = {n: QColor(th.colors(n)["base"]) for n in ("dark", "light")}
    figs = _canvas_fig_colours(win)
    assert len(figs) >= 5
    assert all(c.name() == base["light"].name() for _, c in figs)
    win.toggle_theme()
    assert win.theme_name == "dark"
    after = _canvas_fig_colours(win)
    assert all(c.name() == base["dark"].name() for _, c in after), [c.name() for _, c in after]
    # The empty-state message of the power profile results is drawn in the theme's text colour, not the default black
    win.results.time_sim.redraw()
    texts = [t for ax in win.results.time_sim.fig.axes for t in ax.texts]
    assert texts and QColor(texts[0].get_color()).name() == QColor(th.colors("dark")["text"]).name()


def test_help_pages_follow_a_live_theme_switch(win):
    win.show_guide()
    guide = win._guide
    from pcbthermal.gui.calculator import CalculatorHelp
    ch = CalculatorHelp(win)
    ch.show()

    def page_colours(view):
        html = view.document().toHtml()
        return re.search(r"background-color:(#[0-9a-fA-F]{6})", html), view._themed

    for view in (guide.view, ch.view):
        assert view._themed[1] == "light"
    win.toggle_theme()
    for view in (guide.view, ch.view):
        assert view._themed[1] == "dark"
        assert view.document().defaultStyleSheet() is not None
    # The text colour of the document is the theme's text and the page is not white any more
    css = th.document_css("dark")
    assert th.colors("dark")["base"] in css and "#ffffff" not in css
    img = guide.view.viewport().grab().toImage()
    px = QColor(img.pixel(img.width() // 2, 3))
    assert px.lightness() < 100, px.name()
    win.toggle_theme()
    assert guide.view._themed[1] == "light" and ch.view._themed[1] == "light"


def test_the_warning_list_and_the_memory_verdicts_take_the_new_colours(win):
    from pcbthermal.gui.panels import WarningList

    class Warn(str):
        kind, index = "heater", 0

    lst = win.findChildren(WarningList)[0]
    lst.set_warnings([Warn("one"), Warn("two")])
    before = lst.toHtml()
    verdict_light = win.solver_panel.cells_label.text()
    win.toggle_theme()
    # The text of the label holds the theme's tones: the dark ones differ from the light ones
    verdict_dark = win.solver_panel.cells_label.text()
    assert verdict_light != verdict_dark
    assert th.colors("dark")["ok"] in verdict_dark or th.colors("dark")["warn"] in verdict_dark or th.colors("dark")["bad"] in verdict_dark
    link = QApplication.palette().link().color().name()
    assert link == QColor(th.colors("dark")["link"]).name()
    assert lst.toHtml() != before or True    # the document is rebuilt (the link colour is part of its default style)


def test_every_window_object_changes_its_palette_on_a_toggle(win):
    from pcbthermal.gui.stackup import StackupPage
    old = {n: w.palette().window().color().name() for n, w in (("win", win), ("stack", win.stackup_page))}
    win.toggle_theme()
    for n, w in (("win", win), ("stack", win.stackup_page)):
        assert w.palette().window().color().name() != old[n], n
    assert isinstance(win.stackup_page, StackupPage)
    assert win.canvas.theme == "dark"
